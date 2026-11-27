"""Pinned constraints: what the user told Claude to always respect in this task, kept in .claude-pins.md.

/pin writes the file. session_start.py puts it back into Claude's context after compaction and at each session
start, so a constraint can't get lost when the conversation is summarised. protect_files.py enforces the path pins:

    - never edit: src/api/public/**, migrations/
    - only edit: src/billing/**, tests/billing/**
    - Don't change the public API.        (any other line is a reminder for Claude)

Globs follow cct.json protected_paths: "dir/" covers a whole folder. The file is personal and gitignored.
"""
import os
import re

PINS_FILE = ".claude-pins.md"
ALWAYS_EDITABLE = {PINS_FILE, ".claude-handoff.md"}
PATH_PIN = re.compile(r"^\s*[-*]\s*(never edit|only edit)\s*:\s*(.+?)\s*$", re.I)


def read(proj):
    """The pins file's text, or None."""
    try:
        with open(os.path.join(proj, PINS_FILE), encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
    except OSError:
        return None
    return text or None


def path_pins(text):
    """(never, only): lists of globs from the pin lines."""
    never, only = [], []
    for line in (text or "").splitlines():
        m = PATH_PIN.match(line)
        if m:
            globs = [g.strip().strip("`") for g in m.group(2).split(",") if g.strip()]
            (never if m.group(1).lower() == "never edit" else only).extend(globs)
    return never, only


def count(text):
    return sum(1 for line in (text or "").splitlines() if re.match(r"^\s*[-*]\s+\S", line))


def context(text):
    return ("The user pinned these constraints for the current task (from .claude-pins.md). Follow them until the "
            "user removes them with /pin clear:\n" + text)
