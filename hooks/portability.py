"""Portability check, run by session_start.py when the team includes Windows (cct.json "team_platforms") or this
machine is Windows: things in the shared config that work on one platform and break on another.

- Commands in CLAUDE.md, AGENTS.md or done_gate that only exist in POSIX shells (rm -rf, cp, export, FOO=1 cmd, ./x.sh).
- Hooks in .claude/settings.json with backslashes or machine-specific absolute paths: Git Bash on Windows eats
  backslashes, and another machine doesn't have your home folder.
- Shell scripts with CRLF line endings, or no .gitattributes rule keeping them LF: a CRLF shebang fails with
  "$'\\r': command not found".

Static, local, shown to the user only: no credits. Turn off by leaving "team_platforms" without "windows".
"""
import json
import os
import re
import subprocess

import drift

POSIX_ONLY = {
    "rm": "a package script, `npx rimraf`, or `python -c \"import shutil; shutil.rmtree('dir')\"`",
    "cp": "a package script or `npx cpy-cli`",
    "mv": "a package script or `npx move-file-cli`",
    "export": "`npx cross-env NAME=value …`, or set it inside a package script",
    "chmod": "nothing: Windows has no execute bit; run the script with its interpreter",
    "touch": "a package script",
    "ls": "a package script",
    "cat": "a package script",
    "grep": "a package script",
    "sed": "a package script",
    "awk": "a package script",
    "source": "a package script",
    "which": "a package script",
}
ABSOLUTE = re.compile(r"(^|[\s\"'=])(/home/|/Users/|[A-Za-z]:[\\/])")
VARS = ("${CLAUDE_PROJECT_DIR}", "${CLAUDE_PLUGIN_ROOT}", "$CLAUDE_PROJECT_DIR", "%CLAUDE_PROJECT_DIR%")
MAX_SHOWN = 8


def wanted(cfg):
    platforms = cfg.get("team_platforms") or []
    return os.name == "nt" or (isinstance(platforms, list) and "windows" in [str(p).lower() for p in platforms])


def command_problems(cfg, proj):
    found = []
    for command, where in drift.commands_to_check(cfg, proj):
        for seg in drift.segments(command, posix=True) or []:
            if seg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
                found.append((f"`{command}` in {where}", "`NAME=value cmd` only works in POSIX shells; use "
                                                         "`npx cross-env NAME=value cmd` or a package script"))
                break
            name = seg[0] if seg else ""
            if name in POSIX_ONLY:
                found.append((f"`{command}` in {where}", f"`{name}` doesn't work this way in Windows shells; use "
                                                         f"{POSIX_ONLY[name]}"))
                break
            if name.endswith(".sh"):
                found.append((f"`{command}` in {where}", "shell scripts need Git Bash or WSL on Windows; run it "
                                                         "with `bash` explicitly, or port it to Python or Node"))
                break
    return found


def hook_problems(proj):
    try:
        with open(os.path.join(proj, ".claude", "settings.json"), encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, ValueError):
        return []
    found = []
    for event, groups in (settings.get("hooks") or {}).items() if isinstance(settings, dict) else []:
        for group in groups if isinstance(groups, list) else []:
            for hook in (group.get("hooks") or []) if isinstance(group, dict) else []:
                if not isinstance(hook, dict):
                    continue
                parts = [str(hook.get("command", ""))] + [str(a) for a in hook.get("args") or []]
                text = " ".join(parts)
                if "\\" in text:
                    found.append((f"a {event} hook in .claude/settings.json",
                                  "uses backslashes, which Git Bash strips on Windows; use forward slashes"))
                elif ABSOLUTE.search(text):
                    found.append((f"a {event} hook in .claude/settings.json",
                                  "uses an absolute path from one machine; use ${CLAUDE_PROJECT_DIR}/…"))
    return found


def git_files(proj, pattern):
    try:
        r = subprocess.run(["git", "--no-optional-locks", "ls-files", "-z", "--", pattern], cwd=proj,
                           capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    return [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p] if r.returncode == 0 else []


def script_problems(proj):
    scripts = git_files(proj, "*.sh")
    if not scripts:
        return []
    found = []
    try:
        with open(os.path.join(proj, ".gitattributes"), encoding="utf-8") as f:
            attributes = f.read()
    except OSError:
        attributes = ""
    if not re.search(r"^\s*(\*\.sh|\*)\s+.*\beol=lf\b", attributes, re.M):
        found.append((f"{len(scripts)} shell script{'s' if len(scripts) != 1 else ''}",
                      "no .gitattributes rule keeps them LF, so Windows checkouts can break them; add "
                      "`*.sh text eol=lf` to .gitattributes"))
    crlf = []
    for rel in scripts[:200]:
        try:
            with open(os.path.join(proj, rel), "rb") as f:
                if b"\r\n" in f.read(65536):
                    crlf.append(rel)
        except OSError:
            pass
    if crlf:
        found.append((", ".join(crlf[:3]) + (f" and {len(crlf) - 3} more" if len(crlf) > 3 else ""),
                      "CRLF line endings, which bash can't run; convert to LF"))
    return found


def find_problems(cfg, proj):
    if not wanted(cfg):
        return []
    return command_problems(cfg, proj) + hook_problems(proj) + script_problems(proj)


def message(found):
    lines = [f"- {what}: {why}" for what, why in found[:MAX_SHOWN]]
    if len(found) > MAX_SHOWN:
        lines.append(f"- … and {len(found) - MAX_SHOWN} more")
    return ("[cct] These will break for teammates on another platform:\n" + "\n".join(lines)
            + "\nThis check runs because \"team_platforms\" in .claude/cct.json includes windows.")
