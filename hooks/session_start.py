#!/usr/bin/env python3
"""SessionStart hook: tells the user what needs attention before work starts.

- setup isn't finished (setup_reminder)
- commands in CLAUDE.md or done_gate no longer fit the project (drift_check, drift.py)
- stale installs, missing .env keys, wrong runtime versions (env_check, env_check.py)
- teammates changed the Claude config since the last session (team_notice, team_notice.py)
- a handoff note from an earlier session is waiting (.claude-handoff.md, written by /handoff)
- AGENTS.md and other tools' instruction files disagree, or CLAUDE.md doesn't import it (agent_files.py)
- the shared config breaks on another platform the team uses (team_platforms, portability.py)
- a newer kit release is out (update_check, update_check.py; off by default)

Everything above goes to the user as a systemMessage, which Claude never sees, so it uses no credits. Nothing is
printed when there is nothing to say, and notices aren't repeated after /clear or compaction. Each notice repeats at
most weekly while nothing changes.

The one thing that does go to Claude is the user's own pins (.claude-pins.md, written by /pin): they're added to its
context at every session start and after every compaction, so a constraint survives the conversation being summarised.
"""
import datetime
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import (defer_to_project, home_claude, is_device_copy, load_config, notify, once,  # noqa: E402
                        project_dir, prune_state, read_input, setup_command)
from done_gate import record_baseline  # noqa: E402
import agent_files  # noqa: E402
import drift  # noqa: E402
import env_check  # noqa: E402
import pins  # noqa: E402
import portability  # noqa: E402
import team_notice  # noqa: E402
import update_check  # noqa: E402

HANDOFF = ".claude-handoff.md"  # not in .claude/, where Claude Code asks before every write

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
    return once("drift", os.path.abspath(proj), drift.message(found) if found else None)


def handoff_notice(proj):
    path = os.path.join(proj, HANDOFF)
    try:
        written = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return once("handoff", os.path.abspath(proj), None)
    return once("handoff", os.path.abspath(proj),
                f"[cct] There's a handoff note from {written} in {HANDOFF}. "
                f"Run /handoff resume to pick up where you left off.")


def safe(check, *args):
    """A notice must never break session start."""
    try:
        return check(*args)
    except Exception:  # noqa: BLE001
        return None


def main():
    refresh_plugin_statusline()
    if defer_to_project(__file__):
        return
    cfg = load_config()
    payload = read_input()
    record_baseline(payload, cfg)
    proj = project_dir()
    pinned = safe(pins.read, proj)
    context = pins.context(pinned) if pinned else None
    if payload.get("source", "startup") not in ("startup", "resume"):
        notify(context=context, event="SessionStart")  # /clear and compaction: only the pins come back
        return
    prune_state()
    messages = []
    pending = None
    if cfg.get("setup_reminder", True) and not is_template_source(proj):
        pending = setup_reminder(proj)
        messages.append(pending)
    setup_unfinished = os.path.exists(os.path.join(proj, ".claude", "cct-pending"))
    if not setup_unfinished and not pending:
        if cfg.get("drift_check", True):
            messages.append(safe(drift_notice, cfg, proj))
        if cfg.get("env_check", True):
            problems = safe(env_check.find_problems, proj)
            messages.append(once("env", os.path.abspath(proj), env_check.message(problems) if problems else None))
        if cfg.get("team_notice", True):
            messages.append(safe(team_notice.notice, proj))
        messages.append(safe(handoff_notice, proj))
        found = safe(agent_files.problems, proj, cfg)
        script = os.path.relpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_files.py"), proj)
        script = "python3 " + (script if not script.startswith("..") else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "agent_files.py")).replace(os.sep, "/")
        messages.append(once("agents", os.path.abspath(proj), agent_files.message(found, script) if found else None))
        found = safe(portability.find_problems, cfg, proj)
        messages.append(once("portability", os.path.abspath(proj), portability.message(found) if found else None))
    if pinned:
        n = pins.count(pinned)
        messages.append(f"[cct] {n} pin{'' if n == 1 else 's'} active from {pins.PINS_FILE}; Claude has "
                        f"{'it' if n == 1 else 'them'}. /pin clear removes them.")
    messages.append(safe(update_check.notice, __file__, cfg))
    notify(*messages, context=context, event="SessionStart")


if __name__ == "__main__":
    main()
