#!/usr/bin/env python3
"""PreToolUse hook for Bash: blocks destructive commands and asks before risky ones.

Looks inside nested commands too: `sh -c '…'`, `eval …`, `$(…)` and backticks.
Level comes from cct.json "guard_level": off | standard | strict.
This is a safety net, not a sandbox: it catches common accidents, not deliberate obfuscation.
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import decide, defer_to_project, load_config, read_input  # noqa: E402

ALLOW, ASK, DENY = "allow", "ask", "deny"
RANK = {ALLOW: 0, ASK: 1, DENY: 2}

DANGEROUS_TARGETS = {
    "/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "$HOME/*", "*", ".", "./", "..",
    "/home", "/usr", "/etc", "/var", "/bin", "/boot", "/lib", "/opt", "/root", "/System", "/Users",
}
FIND_DANGEROUS = DANGEROUS_TARGETS - {".", "./", "..", "*"}
PROTECTED_BRANCHES = {"main", "master"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
PREFIXES = {"sudo", "command", "env", "nohup", "time", "nice", "exec", "xargs", "doas", "(", "{"}
OPERATORS = {";", "&&", "||", "|", "&", "|&", ";;"}

DENY_PATTERNS = [
    (r"\bmkfs(\.\w+)?\b", "Formats a filesystem."),
    (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd|disk|mmcblk)", "Writes directly to a disk device."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb."),
    (r"\bchmod\s+(-\w+\s+)*-R\s+(-\w+\s+)*0?777\s+/(\s|$)", "Makes the whole system world-writable."),
    (r"\b(curl|wget)\b[^|\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b", "Pipes a download straight into a shell. Download it, read it, then run it."),
    (r"\bgit\s+push\b[^\n]*(\s--force\b|\s-f\b|\s--force-with-lease\b)[^\n]*\b(main|master)\b", "Force-push to main/master."),
    (r"\bgit\s+push\b[^\n]*\b(main|master)\b[^\n]*(\s--force\b|\s-f\b)", "Force-push to main/master."),
    (r"\bgit\s+push\b[^\n]*\s\+(main|master)\b", "Force-push to main/master."),
]

ASK_PATTERNS = [
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

STRICT_PATTERNS = [
    (r"\bgit\s+push\b", "Pushes to a remote."),
    (r"\b(npm|pnpm|yarn|bun)\s+(add|install|i)\s+[^-\s]", "Adds a dependency."),
    (r"\b(pip|pip3|uv\s+pip)\s+install\b|\buv\s+add\b|\bpoetry\s+add\b", "Adds a dependency."),
    (r"\bcargo\s+add\b|\bgo\s+get\b|\bgem\s+install\b|\bcomposer\s+require\b", "Adds a dependency."),
    (r"(^|[\s;&|(])rm\s", "Deletes files."),
]


def worst(a, b):
    return a if RANK[a[0]] >= RANK[b[0]] else b


def segments(cmd):
    """Split a command line into simple commands (token lists), respecting quotes."""
    out = []
    for line in cmd.splitlines():
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
            lex.whitespace_split = True
            tokens = list(lex)
        except ValueError:  # unbalanced quotes: fall back to a rough split
            tokens = re.split(r"\s+", line.strip())
            tokens = [t for t in tokens if t]
        current = []
        for t in tokens:
            if t in OPERATORS or t == ")":
                if current:
                    out.append(current)
                current = []
            else:
                current.append(t)
        if current:
            out.append(current)
    return out


def strip_prefixes(toks):
    while toks and (toks[0] in PREFIXES or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0])):
        toks = toks[1:]
    return toks


def nested_commands(cmd, segs):
    """Command strings hidden inside this one."""
    for toks in segs:
        toks = strip_prefixes(toks)
        if not toks:
            continue
        name = os.path.basename(toks[0])
        if name in SHELLS:
            for i, t in enumerate(toks[1:-1], start=1):
                if re.match(r"^-[a-zA-Z]*c[a-zA-Z]*$", t):
                    yield toks[i + 1]
                    break
        elif name == "eval":
            yield " ".join(toks[1:])
    for m in re.finditer(r"\$\(([^()]*)\)|`([^`]*)`", cmd):
        yield m.group(1) or m.group(2) or ""


def check_rm(args):
    short = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
    recursive = "r" in short or "R" in short or "--recursive" in args
    targets = [a for a in args if not a.startswith("-")]
    if "--no-preserve-root" in args:
        return DENY, "Blocked by cct guard: rm --no-preserve-root."
    if recursive and any(t.rstrip("/") in DANGEROUS_TARGETS or t in DANGEROUS_TARGETS for t in targets):
        return DENY, "Blocked by cct guard: recursive delete of a root, home or wildcard path."
    if recursive:
        return ASK, "cct guard: recursive delete. Confirm to continue."
    return ALLOW, ""


def check_find(args):
    deletes = "-delete" in args or any(
        a in ("-exec", "-execdir", "-ok") and i + 1 < len(args) and os.path.basename(args[i + 1]) == "rm"
        for i, a in enumerate(args))
    if not deletes:
        return ALLOW, ""
    roots = []
    for a in args:
        if a.startswith("-") or a in ("(", "!"):
            break
        roots.append(a)
    # Unlike `rm -rf .`, `find . -delete` is a normal scoped cleanup, so only roots and home count here.
    if any(r.rstrip("/") in FIND_DANGEROUS or r in FIND_DANGEROUS for r in roots):
        return DENY, "Blocked by cct guard: find deleting from a root or home path."
    return ASK, "cct guard: find will delete files. Confirm to continue."


def check_git_push(args):
    if "push" not in args:
        return ALLOW, ""
    rest = args[args.index("push") + 1:]
    deleting = "--delete" in rest or "-d" in rest
    refs = [r for r in rest if not r.startswith("-")]
    deleted = [r.lstrip(":") for r in refs if r.startswith(":")] + (refs[1:] if deleting else [])
    if not deleted:
        return ALLOW, ""
    if any(r.replace("refs/heads/", "") in PROTECTED_BRANCHES for r in deleted):
        return DENY, "Blocked by cct guard: deletes the remote main/master branch."
    return ASK, "cct guard: deletes a remote branch. Confirm to continue."


def check_segment(toks):
    toks = strip_prefixes(toks)
    if not toks:
        return ALLOW, ""
    name, args = os.path.basename(toks[0]), toks[1:]
    if name == "rm":
        return check_rm(args)
    if name == "find":
        return check_find(args)
    if name == "git":
        return check_git_push(args)
    return ALLOW, ""


def evaluate(cmd, level, depth=0):
    result = (ALLOW, "")
    for pattern, reason in DENY_PATTERNS:
        if re.search(pattern, cmd):
            return DENY, f"Blocked by cct guard: {reason}"
    segs = segments(cmd)
    for toks in segs:
        result = worst(result, check_segment(toks))
    for pattern, reason in ASK_PATTERNS:
        if re.search(pattern, cmd):
            result = worst(result, (ASK, f"cct guard: {reason} Confirm to continue."))
    if level == "strict":
        for pattern, reason in STRICT_PATTERNS:
            if re.search(pattern, cmd):
                result = worst(result, (ASK, f"cct guard (strict): {reason} Confirm to continue."))
    if depth < 3:
        for inner in nested_commands(cmd, segs):
            if inner.strip():
                result = worst(result, evaluate(inner, level, depth + 1))
    return result


def main():
    if defer_to_project(__file__):
        return
    level = str(load_config().get("guard_level", "standard")).lower()
    if level == "off":
        return
    cmd = (read_input().get("tool_input") or {}).get("command") or ""
    if not cmd:
        return
    decision, reason = evaluate(cmd, level)
    if decision != ALLOW:
        decide(decision, reason)


if __name__ == "__main__":
    main()
