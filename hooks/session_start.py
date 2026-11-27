#!/usr/bin/env python3
"""SessionStart hook: tells the user when setup is unfinished, when commands in the config have drifted, and (opt-in)
when a newer kit release exists.

Everything here goes to the user as a systemMessage, which Claude never sees, so it uses no credits. Nothing is
printed when there is nothing to say, and nothing is shown after /clear or compaction.
Turn off with cct.json "setup_reminder": false, "drift_check": false and "update_check": false.
"""
import hashlib
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import (defer_to_project, home_claude, is_device_copy, load_config, notify,  # noqa: E402
                        project_dir, prune_state, read_input, read_state, setup_command, state_path, write_state)
from done_gate import record_baseline  # noqa: E402
import drift  # noqa: E402
import update_check  # noqa: E402

DRIFT_REPEAT_DAYS = 7

SOURCE_REPO = "claude-code-project-template"
PROJECT_SIGNS = [".git", "package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml",
                 "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "pubspec.yaml",
                 "Package.swift", "CMakeLists.txt", "Makefile", "deno.json"]


def is_template_source(proj):
    """Don't nag inside the template's own repo."""
    try:
        url = subprocess.run(["git", "-C", proj, "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return SOURCE_REPO in url


def refresh_plugin_statusline():
    """Plugins can't set a status line, so /cct:setup copies it into the plugin's data folder (which survives
    updates) and points settings.json there. Keep that copy current after each plugin update."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    target = os.path.join(data, "statusline") if data else None
    if not target or not os.path.isdir(target):
        return
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("statusline.py", "cct_config.py"):
        src, dst = os.path.join(here, name), os.path.join(target, name)
        try:
            with open(src, "rb") as f:
                new = f.read()
            old = None
            if os.path.exists(dst):
                with open(dst, "rb") as f:
                    old = f.read()
            if old != new:
                with open(dst, "wb") as f:
                    f.write(new)
        except OSError:
            pass


def setup_reminder(proj):
    """Setup isn't finished, or (device installs) this project has no CLAUDE.md yet."""
    setup = setup_command(__file__)
    off = "Hide this with \"setup_reminder\": false in .claude/cct.json."
    if os.path.exists(os.path.join(proj, ".claude", "cct-pending")):
        return f"[cct] The Claude Code kit is installed here, but setup isn't finished. Run {setup} to finish it. {off}"
    if os.path.exists(os.path.join(home_claude(), "cct-pending")):
        return (f"[cct] The Claude Code kit is installed on this device, but device setup isn't finished. Run "
                f"{setup} device to finish it. Hide this with \"setup_reminder\": false in ~/.claude/cct.json.")
    if (is_device_copy(__file__)
            and proj != os.path.expanduser("~")
            and any(os.path.exists(os.path.join(proj, s)) for s in PROJECT_SIGNS)
            and not os.path.exists(os.path.join(proj, "CLAUDE.md"))
            and not os.path.exists(os.path.join(proj, ".claude", "CLAUDE.md"))
            and not os.path.exists(os.path.join(proj, ".claude", "cct-ignore"))):
        return (f"[cct] This project has no CLAUDE.md yet. Run {setup} to configure Claude Code for it, or create "
                f"an empty .claude/cct-ignore file to stop this notice here.")
    return None


def drift_notice(cfg, proj):
    """Drifted commands, shown when the list changes and again after a week while it stays."""
    found = drift.find_drift(cfg, proj)
    path = state_path("drift", os.path.abspath(proj))
    if not found:
        if read_state(path):
            write_state(path, {})
        return None
    text = drift.message(found)
    digest = hashlib.sha256(text.encode()).hexdigest()
    state = read_state(path)
    now = time.time()
    if state.get("shown") == digest and now - float(state.get("at", 0) or 0) < DRIFT_REPEAT_DAYS * 86400:
        return None
    write_state(path, {"shown": digest, "at": now})
    return text


def main():
    refresh_plugin_statusline()
    if defer_to_project(__file__):
        return
    cfg = load_config()
    payload = read_input()
    record_baseline(payload, cfg)
    if payload.get("source", "startup") not in ("startup", "resume"):
        return  # /clear and compaction start a new context, not a new visit
    prune_state()
    proj = project_dir()
    messages = []
    pending = None
    if cfg.get("setup_reminder", True) and not is_template_source(proj):
        pending = setup_reminder(proj)
        messages.append(pending)
    setup_unfinished = os.path.exists(os.path.join(proj, ".claude", "cct-pending"))
    if cfg.get("drift_check", True) and not setup_unfinished and not pending:
        messages.append(drift_notice(cfg, proj))
    messages.append(update_check.notice(__file__, cfg))
    notify(*messages)


if __name__ == "__main__":
    main()
