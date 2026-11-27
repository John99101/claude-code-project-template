"""Drift check, run by session_start.py: do the commands in CLAUDE.md and cct.json still match the project?

Static and local: it reads files and looks tools up on PATH, and never runs the commands. It finds definite drift
only, so a command it can't judge (shell variables, workspace filters, package-manager subcommands) passes. The
result goes to the user only, never to Claude, so it uses no credits.

Checked: the done_gate commands in cct.json, and the backticked commands in CLAUDE.md's "Commands" table and
"Before you say a task is done" section, including files CLAUDE.md imports with a line like `@AGENTS.md`. Also the
files named in the acceptance criteria of specs written by /spec ("spec_dir", default specs/). Turn off with cct.json "drift_check": false.
"""
import json
import os
import re
import shlex
import shutil

SECTIONS = ("commands", "before you say a task is done")
SEPARATORS = {"&&", "||", ";", "|", "&"}
NODE_RUNNERS = {"npm", "pnpm", "yarn", "bun"}
SKIP = {"cd", "export", "env", "sudo", "time", "exec", "source", ".", "echo", "true", "false", "test", "["}
PATH_PREFIX = re.compile(r"^(\.{1,2}[\\/]|/|[A-Za-z]:[\\/])")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MAX_SHOWN = 8


def claude_md(proj):
    for rel in ("CLAUDE.md", os.path.join(".claude", "CLAUDE.md")):
        path = os.path.join(proj, rel)
        if os.path.isfile(path):
            return path, rel.replace(os.sep, "/")
    return None, None


def md_commands(path):
    """Backticked commands from the Commands table and the done-checklist section."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return []
    found, section = [], None
    for line in text.splitlines():
        heading = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if heading:
            section = heading.group(1).strip().lower()
            continue
        if section not in SECTIONS:
            continue
        if section == "commands" and not line.lstrip().startswith("|"):
            continue
        if section != "commands" and not re.match(r"^\s*[-*]\s", line):
            continue
        for cmd in re.findall(r"`([^`]+)`", line):
            if "{{" not in cmd and not cmd.startswith("/"):  # placeholders and slash commands aren't shell
                found.append(cmd.strip())
    return found


def unquote(token):
    """Windows-style splitting keeps the quotes around a token, e.g. "C:\\Program Files\\x.exe"."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def segments(command, posix=None):
    """The simple commands in a command line, as token lists, or None if it can't be judged statically.
    On Windows, backslashes are path separators, not escapes, so the command is split the Windows way."""
    if any(s in command for s in ("$(", "`", "${", "<(")):
        return None
    posix = os.name != "nt" if posix is None else posix
    try:
        tokens = shlex.split(command, posix=posix)
    except ValueError:
        return None
    if not posix:
        tokens = [unquote(t) for t in tokens]
    out, current = [], []
    for t in tokens:
        if t in SEPARATORS:
            out.append(current)
            current = []
        else:
            current.append(t)
    out.append(current)
    return [s for s in out if s]


def local_tool(cwd, proj, name):
    """A tool in the project's virtualenv or node_modules, looking up from cwd to the project root, or on PATH."""
    exts = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)
    d, root = os.path.abspath(cwd), os.path.abspath(proj)
    while True:
        for folder in ((".venv", "bin"), (".venv", "Scripts"), ("node_modules", ".bin")):
            for ext in exts:
                if os.path.isfile(os.path.join(d, *folder, name + ext)):
                    return True
        if d == root or os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    return shutil.which(name) is not None


def package_scripts(cwd):
    try:
        with open(os.path.join(cwd, "package.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return scripts if isinstance(scripts, dict) else {}


def node_problem(runner, args, cwd, proj):
    if any(a in ("--filter", "-F", "-r", "--recursive", "-w", "--workspace", "--workspaces", "--prefix", "-C", "--cwd")
           or a.startswith(("--filter=", "--workspace=", "--prefix=", "--cwd=")) for a in args):
        return None  # runs in other packages
    if not args:
        return None
    if args[0] in ("run", "run-script") and len(args) > 1:
        script = args[1]
    elif args[0] == "test" or (runner == "npm" and args[0] in ("start", "stop", "restart")):
        script = args[0]
    else:
        return None  # a built-in subcommand, or a bin we can't tell from a script
    if runner == "bun" and args[0] == "test":
        return None  # bun has a built-in test runner
    scripts = package_scripts(cwd)
    rel = os.path.relpath(os.path.join(cwd, "package.json"), proj).replace(os.sep, "/")
    if scripts is None:
        return f"there's no {rel}"
    if script not in scripts:
        return f'{rel} has no "{script}" script'
    return None


def make_problem(args, cwd, proj):
    folder, targets, i = cwd, [], 0
    while i < len(args):
        a = args[i]
        if a in ("-C", "--directory") and i + 1 < len(args):
            folder = os.path.join(cwd, args[i + 1])
            i += 2
            continue
        if a.startswith("--directory="):
            folder = os.path.join(cwd, a.split("=", 1)[1])
        elif a in ("-f", "--file", "--makefile"):
            return None  # a custom makefile: don't guess
        elif not a.startswith("-") and "=" not in a:
            targets.append(a)
        i += 1
    names = ("GNUmakefile", "makefile", "Makefile")
    path = next((os.path.join(folder, n) for n in names if os.path.isfile(os.path.join(folder, n))), None)
    rel = os.path.relpath(folder, proj).replace(os.sep, "/")
    if not path:
        return f"there's no Makefile in {'the project root' if rel == '.' else rel}"
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    if re.search(r"^-?include\s", text, re.M) or re.search(r"^[^\s#:=]*%[^:=]*:", text, re.M):
        return None  # targets may come from elsewhere or from a pattern rule
    defined = set()
    for m in re.finditer(r"^([^\s:#=][^:=]*?)\s*::?(?!=)", text, re.M):
        defined.update(m.group(1).split())
    missing = [t for t in targets if t not in defined]
    return f"the Makefile has no `{missing[0]}` target" if missing else None


def just_problem(args, cwd):
    recipes = [a for a in args if not a.startswith("-")][:1]
    names = ("justfile", "Justfile", ".justfile")
    path = next((os.path.join(cwd, n) for n in names if os.path.isfile(os.path.join(cwd, n))), None)
    if not path:
        return "there's no justfile"
    if not recipes:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    if re.search(r"^(import|mod)\s", text, re.M):
        return None
    if not re.search(rf"^@?{re.escape(recipes[0])}(\s|:)", text, re.M):
        return f"the justfile has no `{recipes[0]}` recipe"
    return None


def problem(command, proj, posix=None):
    """Why `command` no longer fits the project, or None."""
    parts = segments(command, posix)
    if parts is None:
        return None
    cwd = proj
    for seg in parts:
        while seg and ENV_ASSIGN.match(seg[0]):
            seg = seg[1:]
        if not seg:
            continue
        name, args = seg[0], seg[1:]
        if name == "cd":
            if args and not args[0].startswith(("-", "~", "$")):
                cwd = os.path.join(cwd, args[0])
                if not os.path.isdir(cwd):
                    return f"the folder `{args[0]}` doesn't exist"
            continue
        if name in SKIP:
            continue
        if PATH_PREFIX.match(name) or (("/" in name or "\\" in name) and not name.startswith("@")):
            if not os.path.exists(os.path.join(cwd, name)):
                return f"`{name}` doesn't exist"
            continue
        if not local_tool(cwd, proj, name):
            return f"`{name}` isn't installed (not on PATH or in the project)"
        if name in NODE_RUNNERS:
            why = node_problem(name, args, cwd, proj)
        elif name == "make":
            why = make_problem(args, cwd, proj)
        elif name == "just":
            why = just_problem(args, cwd)
        else:
            why = None
        if why:
            return why
    return None


def md_sources(proj):
    """[(path, display name)]: CLAUDE.md and the Markdown files it imports with `@file.md` lines."""
    path, rel = claude_md(proj)
    if not path:
        agents = os.path.join(proj, "AGENTS.md")
        return [(agents, "AGENTS.md")] if os.path.isfile(agents) else []
    sources = [(path, rel)]
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            imports = re.findall(r"^\s*@(\.?/?[\w./-]+\.md)\s*$", f.read(), re.M)
    except OSError:
        imports = []
    for imp in imports[:5]:
        full = os.path.normpath(os.path.join(os.path.dirname(path), imp))
        if os.path.isfile(full) and full.startswith(os.path.abspath(proj)):
            sources.append((full, os.path.relpath(full, proj).replace(os.sep, "/")))
    return sources


def commands_to_check(cfg, proj):
    """[(command, where it's written)] from done_gate and the Markdown instructions."""
    to_check = []
    gate = cfg.get("done_gate")
    if isinstance(gate, dict):
        for c in gate.get("commands") or []:
            if isinstance(c, str) and c.strip():
                to_check.append((c.strip(), ".claude/cct.json done_gate"))
    for path, rel in md_sources(proj):
        to_check += [(c, rel) for c in md_commands(path)]
    return to_check


SPEC_PATH = re.compile(r"`([\w.@-]+(?:/[\w.@-]+)+|[\w-]+\.[A-Za-z]{1,5})`")


def spec_problems(cfg, proj):
    """[(path, spec, why)] for files named in specs' acceptance criteria that no longer exist."""
    folder = os.path.join(proj, str(cfg.get("spec_dir") or "specs/"))
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(".md"))
    except OSError:
        return []
    found = []
    for name in names[:50]:
        try:
            with open(os.path.join(folder, name), encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r"^##\s+Acceptance criteria\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
        rel = os.path.relpath(os.path.join(folder, name), proj).replace(os.sep, "/")
        for path in SPEC_PATH.findall(m.group(1) if m else ""):
            if not os.path.exists(os.path.join(proj, path)):
                found.append((path, rel, "the file no longer exists"))
    return found


def find_drift(cfg, proj):
    """[(command or path, where it's written, why it drifted)]."""
    to_check = commands_to_check(cfg, proj)
    seen, found = set(), list(spec_problems(cfg, proj))
    for command, where in to_check:
        if command in seen:
            continue
        seen.add(command)
        why = problem(command, proj)
        if why:
            found.append((command, where, why))
    return found


def message(found):
    lines = [f"- `{c}` in {where}: {why}" for c, where, why in found[:MAX_SHOWN]]
    if len(found) > MAX_SHOWN:
        lines.append(f"- … and {len(found) - MAX_SHOWN} more")
    return ("[cct] Some commands and paths in your Claude config or specs no longer match this project:\n" + "\n".join(lines)
            + "\nFix them in the file, or run /setup to re-tune. Turn this check off with \"drift_check\": false "
              "in .claude/cct.json.")
