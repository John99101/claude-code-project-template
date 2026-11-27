"""Team-change notice, run by session_start.py: did teammates change the Claude config since your last session?

It remembers the commit you were on, and at the next session start lists commits in between that changed CLAUDE.md
files, .claude/ or .mcp.json and were written by someone else (by git author email). Only git history is read. The
result goes to the user only, never to Claude, so it uses no credits. Turn off with cct.json "team_notice": false.
"""
import os
import subprocess

from cct_config import read_state, state_path, write_state

PATHS = ["CLAUDE.md", ":(glob)**/CLAUDE.md", ".claude", ".mcp.json", ":(exclude).claude/cct"]
MAX_FILES = 8


def git(proj, *args):
    try:
        r = subprocess.run(["git", "--no-optional-locks", *args], cwd=proj, capture_output=True, text=True,
                           timeout=5, errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def changes(proj, old, new, me):
    """{file: {authors}} for config files changed by others between two commits."""
    out = git(proj, "log", "--no-merges", "--name-only", "--format=%x01%an%x00%ae", f"{old}..{new}", "--", *PATHS)
    if not out:
        return {}
    found = {}
    for block in out.split("\x01")[1:]:
        lines = block.strip("\n").split("\n")
        name, _, email = lines[0].partition("\x00")
        if me and email.strip().lower() == me:
            continue
        for f in lines[1:]:
            if f.strip():
                found.setdefault(f.strip(), set()).add(name.strip())
    return found


def notice(proj):
    head = (git(proj, "rev-parse", "HEAD") or "").strip()
    if not head:
        return None
    path = state_path("team", os.path.abspath(proj))
    old = read_state(path).get("head")
    write_state(path, {"head": head})  # also keeps the file from being pruned while the project is in use
    if not old or old == head:
        return None
    if git(proj, "merge-base", "--is-ancestor", old, head) is None:
        return None  # switched to an unrelated branch or rewrote history: nothing to compare
    me = (git(proj, "config", "user.email") or "").strip().lower()
    found = changes(proj, old, head, me)
    if not found:
        return None
    files = sorted(found)
    authors = sorted({a for names in found.values() for a in names})
    shown = ", ".join(files[:MAX_FILES]) + (f" and {len(files) - MAX_FILES} more" if len(files) > MAX_FILES else "")
    return (f"[cct] Teammates ({', '.join(authors)}) changed the Claude config since your last session: {shown}.\n"
            f"See what changed: git diff {old[:7]}..{head[:7]} -- CLAUDE.md .claude .mcp.json\n"
            f"Turn this notice off with \"team_notice\": false in .claude/cct.json.")
