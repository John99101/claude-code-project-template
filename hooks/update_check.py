"""Update notice, run by session_start.py for script installs when cct.json "update_check" is true (off by default).

At most once a week it asks GitHub for the kit's latest release. The request carries only a generic User-Agent,
nothing about the user or the project. When a newer release exists, the user (never Claude) gets a one-line notice
with the update commands. Nothing is ever downloaded or installed automatically, and no credits are used.

Plugin installs are skipped: Claude Code updates plugins through /plugin.
"""
import json
import os
import re
import time
import urllib.request

from cct_config import home_claude, is_device_copy, is_plugin_copy, project_dir, read_state, state_path, write_state

CHECK_DAYS = 7
TIMEOUT = 3  # seconds; the whole SessionStart hook has 10
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def installed(script_path):
    """(source.json data, mode) for this install, or (None, None) for the plugin or a missing manifest."""
    if is_plugin_copy(script_path):
        return None, None
    if is_device_copy(script_path):
        path, mode = os.path.join(home_claude(), "cct", "source.json"), "device"
    else:
        path, mode = os.path.join(project_dir(), ".claude", "cct", "source.json"), "project"
    data = read_state(path)
    if not REPO.match(str(data.get("repo", ""))) or not data.get("version"):
        return None, None
    return data, mode


def version_tuple(v):
    parts = str(v).strip().lstrip("vV").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def fetch_latest(repo):
    """The latest release tag, or None. CCT_RELEASES_URL overrides the URL (the tests use a file:// URL)."""
    url = os.environ.get("CCT_RELEASES_URL") or f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "cct-kit-update-check",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    tag = data.get("tag_name") if isinstance(data, dict) else None
    return tag.lstrip("vV") if isinstance(tag, str) and version_tuple(tag) else None


def notice(script_path, cfg):
    """A message for the user when a newer kit release exists, or None."""
    if not cfg.get("update_check", False):
        return None
    source, mode = installed(script_path)
    if not source:
        return None
    repo, current = source["repo"], str(source["version"])
    path = state_path("update-check")
    state = read_state(path)
    now = time.time()
    if state.get("repo") != repo or now - float(state.get("at", 0) or 0) > CHECK_DAYS * 86400:
        latest = fetch_latest(repo)
        state = {"repo": repo, "at": now, "latest": latest or state.get("latest"),
                 "shown": state.get("shown") if state.get("repo") == repo else {}}
        write_state(path, state)
    latest = state.get("latest")
    new, old = version_tuple(latest), version_tuple(current)
    if not (new and old and new > old):
        return None
    shown = state.get("shown") if isinstance(state.get("shown"), dict) else {}
    key = f"{mode}:{os.path.abspath(project_dir()) if mode == 'project' else '~'}:{latest}"
    if now - float(shown.get(key, 0) or 0) < CHECK_DAYS * 86400:
        return None  # once a week per install and version is enough
    shown[key] = now
    state["shown"] = shown
    write_state(path, state)
    target = "--project ." if mode == "project" else "--global"
    return (f"[cct] Kit {latest} is out (you have {current}). What changed: https://github.com/{repo}/releases\n"
            f"Update with /template-update (Claude walks you through it, using some credits), or without Claude:\n"
            f"  git clone --depth 1 https://github.com/{repo} <tmp> && python3 <tmp>/install.py {target} --update\n"
            f"Turn this notice off with \"update_check\": false in ~/.claude/cct.json.")
