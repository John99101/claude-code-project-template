#!/usr/bin/env python3
"""SessionStart hook: tells Claude when this kit's setup is unfinished, so it can offer /setup.

Prints nothing when there is nothing to do. Turn off with cct.json "setup_reminder": false.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import load_config, project_dir  # noqa: E402

HOME_CLAUDE = os.path.expanduser("~/.claude")
SOURCE_REPO = "claude-code-project-template"
PROJECT_SIGNS = [".git", "package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml",
                 "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "pubspec.yaml",
                 "Package.swift", "CMakeLists.txt", "Makefile", "deno.json"]


def is_global_install():
    here = os.path.abspath(os.path.dirname(__file__))
    return here.startswith(os.path.join(HOME_CLAUDE, "hooks"))


def is_template_source(proj):
    """Don't nag inside the template's own repo."""
    try:
        url = subprocess.run(["git", "-C", proj, "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return SOURCE_REPO in url


def main():
    if not load_config().get("setup_reminder", True):
        return
    proj = project_dir()
    if is_template_source(proj):
        return
    global_mode = is_global_install()
    if global_mode and os.path.exists(os.path.join(proj, ".claude", "hooks", "session_start.py")):
        return  # the project's own copy of this hook handles it

    ask = "Don't start until the user agrees."
    if os.path.exists(os.path.join(proj, ".claude", "cct-pending")):
        print("[cct] The Claude Code project kit was installed here but setup isn't finished. "
              "At the start of your first reply, tell the user in one sentence and offer to run /setup "
              f"(the project-setup skill). {ask}")
    elif os.path.exists(os.path.join(HOME_CLAUDE, "cct-pending")):
        print("[cct] The Claude Code kit was installed on this device but device setup isn't finished. "
              "At the start of your first reply, tell the user in one sentence and offer to run /setup "
              f"in device mode. {ask}")
    elif (global_mode
          and proj != os.path.expanduser("~")
          and any(os.path.exists(os.path.join(proj, s)) for s in PROJECT_SIGNS)
          and not os.path.exists(os.path.join(proj, "CLAUDE.md"))
          and not os.path.exists(os.path.join(proj, ".claude", "CLAUDE.md"))
          and not os.path.exists(os.path.join(proj, ".claude", "cct-ignore"))):
        print("[cct] This project has no CLAUDE.md yet. Near the start of your first reply, offer once to run "
              "/setup to configure Claude Code for it. If the user declines, offer to create .claude/cct-ignore "
              f"so you don't ask again. {ask}")


if __name__ == "__main__":
    main()
