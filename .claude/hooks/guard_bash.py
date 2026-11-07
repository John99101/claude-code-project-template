#!/usr/bin/env python3
"""PreToolUse hook for Bash: blocks destructive commands and asks before risky ones.

Level comes from cct.json "guard_level": off | standard | strict.
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import decide, load_config, read_input  # noqa: E402

DANGEROUS_RM_TARGETS = {
    "/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "$HOME/*", "*", ".", "./", "..",
    "/home", "/usr", "/etc", "/var", "/bin", "/boot", "/lib", "/opt", "/root",
}

DENY = [
    (r"\bmkfs(\.\w+)?\b", "Formats a filesystem."),
    (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd|disk|mmcblk)", "Writes directly to a disk device."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb."),
    (r"\bchmod\s+(-\w+\s+)*-R\s+(-\w+\s+)*0?777\s+/(\s|$)", "Makes the whole system world-writable."),
    (r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b", "Pipes a download straight into a shell. Download it, read it, then run it."),
    (r"\bgit\s+push\b[^\n]*(\s--force\b|\s-f\b|\s--force-with-lease\b)[^\n]*\b(main|master)\b", "Force-push to main/master."),
    (r"\bgit\s+push\b[^\n]*\b(main|master)\b[^\n]*(\s--force\b|\s-f\b)", "Force-push to main/master."),
    (r"\bgit\s+push\b[^\n]*\s\+(main|master)\b", "Force-push to main/master."),
]

ASK = [
    (r"\bgit\s+reset\s+--hard\b", "Discards uncommitted changes."),
    (r"\bgit\s+clean\s+-\w*f", "Deletes untracked files."),
    (r"\bgit\s+push\b[^\n]*(\s--force\b|\s-f\b|\s--force-with-lease\b)", "Force-push rewrites remote history."),
    (r"\bgit\s+branch\s+-D\b", "Deletes a branch even if unmerged."),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "Discards all unstaged changes."),
    (r"\bsudo\b", "Runs with administrator rights."),
    (r"(?i)\b(drop|truncate)\s+(table|database|schema)\b", "Destroys database data."),
    (r"\b(npm|pnpm|yarn)\s+publish\b|\bcargo\s+publish\b|\btwine\s+upload\b|\bgem\s+push\b", "Publishes a package."),
    (r"\b(cat|less|more|head|tail|grep)\b[^\n]*(^|[\s/])\.env(\.(?!example|sample|template)\w+)?(\s|$)", "Reads a secrets file."),
]

STRICT_ASK = [
    (r"\bgit\s+push\b", "Pushes to a remote."),
    (r"\b(npm|pnpm|yarn|bun)\s+(add|install|i)\s+[^-\s]", "Adds a dependency."),
    (r"\b(pip|pip3|uv\s+pip)\s+install\b|\buv\s+add\b|\bpoetry\s+add\b", "Adds a dependency."),
    (r"\bcargo\s+add\b|\bgo\s+get\b|\bgem\s+install\b|\bcomposer\s+require\b", "Adds a dependency."),
    (r"\brm\b", "Deletes files."),
]

PREFIXES = {"sudo", "command", "env", "nohup", "time", "nice", "exec", "xargs"}


def split_segments(cmd):
    return [s for s in re.split(r"\s*(?:;|&&|\|\||\||\n)\s*", cmd) if s.strip()]


def check_rm(segment):
    try:
        toks = shlex.split(segment)
    except ValueError:
        toks = segment.split()
    while toks and (toks[0] in PREFIXES or "=" in toks[0]):
        toks = toks[1:]
    if not toks or os.path.basename(toks[0]) != "rm":
        return None
    args = toks[1:]
    short = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
    recursive = "r" in short or "R" in short or "--recursive" in args
    if "--no-preserve-root" in args:
        return "deny"
    targets = [a for a in args if not a.startswith("-")]
    if recursive and any(t.rstrip() in DANGEROUS_RM_TARGETS for t in targets):
        return "deny"
    if recursive:
        return "ask"
    return None


def main():
    cfg = load_config()
    level = str(cfg.get("guard_level", "standard")).lower()
    if level == "off":
        return
    cmd = (read_input().get("tool_input") or {}).get("command") or ""
    if not cmd:
        return

    for pattern, reason in DENY:
        if re.search(pattern, cmd):
            decide("deny", f"Blocked by cct guard: {reason}")

    rm_results = [check_rm(s) for s in split_segments(cmd)]
    if "deny" in rm_results:
        decide("deny", "Blocked by cct guard: recursive delete of a root, home or wildcard path.")

    for pattern, reason in ASK:
        if re.search(pattern, cmd):
            decide("ask", f"cct guard: {reason} Confirm to continue.")
    if "ask" in rm_results:
        decide("ask", "cct guard: recursive delete. Confirm to continue.")

    if level == "strict":
        for pattern, reason in STRICT_ASK:
            if re.search(pattern, cmd):
                decide("ask", f"cct guard (strict): {reason} Confirm to continue.")


if __name__ == "__main__":
    main()
