#!/usr/bin/env python3
"""SessionStart hook: tells Claude when this kit's setup is unfinished, so it can offer /setup.

Prints nothing when there is nothing to do. Turn off with cct.json "setup_reminder": false.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import defer_to_project, home_claude, is_device_copy, load_config, project_dir  # noqa: E402

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


def main():
    if defer_to_project(__file__) or not load_config().get("setup_reminder", True):
        return
    proj = project_dir()
    if is_template_source(proj):
        return

    ask = "Don't start until the user agrees."
    if os.path.exists(os.path.join(proj, ".claude", "cct-pending")):
        print("[cct] The Claude Code project kit was installed here but setup isn't finished. "
              "At the start of your first reply, tell the user in one sentence and offer to run /setup. "
              f"{ask}")
    elif os.path.exists(os.path.join(home_claude(), "cct-pending")):
        print("[cct] The Claude Code kit was installed on this device but device setup isn't finished. "
              "At the start of your first reply, tell the user in one sentence and offer to run /setup "
              f"in device mode. {ask}")
    elif (is_device_copy(__file__)
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
