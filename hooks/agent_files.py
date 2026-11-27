#!/usr/bin/env python3
"""One instructions file for every AI tool in the team: AGENTS.md.

Teams that mix Claude Code, Cursor, Copilot, Codex or Gemini end up with an instructions file per tool, and they
drift: a build command changes in one and nobody updates the others. Here AGENTS.md is the single source:
- CLAUDE.md imports it with a line `@AGENTS.md` (Claude Code doesn't read AGENTS.md on its own);
- the files for the tools in cct.json "agent_files" are generated from it, with a header saying so.

    python3 agent_files.py --check   # exit 1 and list what's out of date (for CI)
    python3 agent_files.py --write   # regenerate the copies

session_start.py tells the user when they're out of date. No credits: nothing here goes to Claude.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import load_config, project_dir  # noqa: E402

SOURCE = "AGENTS.md"
TARGETS = {
    "copilot": os.path.join(".github", "copilot-instructions.md"),
    "cursor": os.path.join(".cursor", "rules", "agents.mdc"),
    "gemini": "GEMINI.md",
}
NAMES = {"copilot": "Copilot", "cursor": "Cursor", "gemini": "Gemini"}
NOTE = "<!-- Generated from AGENTS.md by the Claude Code kit. Edit AGENTS.md, then run agent_files.py --write. -->"
IMPORT = re.compile(r"^\s*@\.?/?AGENTS\.md\s*$", re.M)


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def targets(cfg):
    wanted = cfg.get("agent_files") or []
    return [t for t in wanted if isinstance(t, str) and t in TARGETS] if isinstance(wanted, list) else []


def generated(target, source):
    body = NOTE + "\n\n" + source.strip() + "\n"
    if target == "cursor":
        return "---\ndescription: Project instructions shared by all AI tools (generated from AGENTS.md)\n" \
               "alwaysApply: true\n---\n\n" + body
    return body


def problems(proj, cfg):
    """[(what, how to fix)] for a missing import or out-of-date copies."""
    source = read(os.path.join(proj, SOURCE))
    if source is None:
        return []
    found = []
    claude = read(os.path.join(proj, "CLAUDE.md"))
    if claude is None:
        claude = read(os.path.join(proj, ".claude", "CLAUDE.md"))
    if claude is not None and not IMPORT.search(claude):
        found.append(("Claude Code doesn't read AGENTS.md, and CLAUDE.md doesn't import it",
                      "add a line `@AGENTS.md` to CLAUDE.md"))
    stale = [NAMES[t] for t in targets(cfg) if read(os.path.join(proj, TARGETS[t])) != generated(t, source)]
    if stale:
        found.append((f"the {' and '.join(stale)} instructions are out of date with AGENTS.md",
                      "regenerate them with agent_files.py --write"))
    return found


def write(proj, cfg):
    source = read(os.path.join(proj, SOURCE))
    if source is None:
        return []
    written = []
    for t in targets(cfg):
        path = os.path.join(proj, TARGETS[t])
        text = generated(t, source)
        if read(path) != text:
            os.makedirs(os.path.dirname(path) or proj, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            written.append(TARGETS[t].replace(os.sep, "/"))
    return written


def message(found, script):
    lines = [f"- {what}: {how}" for what, how in found]
    return ("[cct] Your AI tools' instructions disagree:\n" + "\n".join(lines).replace("agent_files.py", script)
            + "\nAGENTS.md is the shared source for every tool.")


def main(argv):
    proj, cfg = project_dir(), load_config()
    if "--write" in argv:
        written = write(proj, cfg)
        print("Updated " + ", ".join(written) if written else "Everything is up to date.")
        return 0
    found = problems(proj, cfg)
    for what, how in found:
        print(f"{what}: {how}")
    if not found:
        print("AGENTS.md and the generated instructions agree.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
