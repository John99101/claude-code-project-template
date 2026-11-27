#!/usr/bin/env python3
"""PostToolUse hook for Edit/Write: formats the edited file, then lints it and reports problems back to Claude.

Uses only tools already installed in the project or on PATH; never downloads anything.
Lint problems are sent to Claude (exit code 2) so it fixes them right away. That fix uses credits, so a file that
still has problems after "lint_max_repeats" reports in a row (default 3) stops being reported for the rest of the
session, and the user is told. Formatting sends nothing to Claude.
When the project configures a formatter or linter that isn't installed, the user (not Claude) is told once per
session, so the step isn't skipped silently.
It also points Claude to imports this edit added that no manifest declares (often made-up packages), and to new
functions that already exist elsewhere in the repo (code_hints.py). Each is reported once per session.
Turn off with cct.json "format_on_edit": false / "lint_on_edit": false.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import (defer_to_project, load_config, notify, project_dir, read_input, read_state, relpath,  # noqa: E402
                        state_path, write_state)
from done_gate import mark_edited  # noqa: E402
import code_hints  # noqa: E402

PRETTIER_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".css", ".scss",
                ".less", ".html", ".vue", ".svelte", ".yaml", ".yml", ".graphql"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte"}
ESLINT_CONFIGS = ["eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts",
                  ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml"]
MAX_LINES = 40
LINT_TIMEOUT = 25  # the whole hook has 40 s; Go and Rust linters compile the package, so a cold cache may not finish
# A compiler-style diagnostic: path:line[:col]: message (go vet prefixes type errors with "vet: ").
DIAG = re.compile(r"^(?:vet: )?(.+?\.(?:go|rs)):\d+(?::\d+)?: ")


def find_up(start, rel):
    d = os.path.abspath(start)
    root = os.path.abspath(project_dir())
    while True:
        cand = os.path.join(d, rel)
        if os.path.exists(cand):
            return cand
        if d == root or os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


EXTS = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)


def local_tool(start, folder, name):
    """A tool installed in the project, e.g. node_modules/.bin/prettier (prettier.cmd on Windows)."""
    for ext in EXTS:
        found = find_up(start, os.path.join(folder, name + ext))
        if found:
            return found
    return None


def tool(name, start):
    for folder in (os.path.join(".venv", "bin"), os.path.join(".venv", "Scripts"), os.path.join("node_modules", ".bin")):
        found = local_tool(start, folder, name)
        if found:
            return found
    return shutil.which(name)


def node_tool(start, name):
    return local_tool(start, os.path.join("node_modules", ".bin"), name)


def formatter_for(path):
    ext = os.path.splitext(path)[1].lower()
    here = os.path.dirname(path)
    if ext in PRETTIER_EXT:
        p = node_tool(here, "prettier")
        if p:
            return [p, "--write", "--log-level", "warn", path]
        b = node_tool(here, "biome")
        if b and ext in {".js", ".jsx", ".ts", ".tsx", ".json", ".css"}:
            return [b, "format", "--write", path]
    if ext == ".py":
        r = tool("ruff", here)
        if r:
            return [r, "format", "--quiet", path]
        b = tool("black", here)
        if b:
            return [b, "--quiet", path]
    if ext == ".go":
        g = shutil.which("gofmt")
        if g:
            return [g, "-w", path]
    if ext == ".rs":
        r = shutil.which("rustfmt")
        if r:
            return [r, "--edition", rust_edition(here), path]
    if ext in {".sh", ".bash"} and shutil.which("shfmt"):
        return ["shfmt", "-w", path]
    return None


EDITION = re.compile(r'^\s*edition\s*=\s*"(\d{4})"')
INHERITED_EDITION = re.compile(r"^\s*edition\s*(\.\s*workspace\s*=\s*true|=\s*\{[^}]*\bworkspace\s*=\s*true)")


def manifest_sections(manifest):
    """{section: [lines]} of a Cargo.toml; enough TOML for the edition keys (tomllib needs Python 3.11)."""
    sections, current = {}, ""
    try:
        with open(manifest, encoding="utf-8") as f:
            for line in f:
                header = re.match(r"^\s*\[([^\[\]]+)\]", line)
                if header:
                    current = header.group(1).strip()
                else:
                    sections.setdefault(current, []).append(line)
    except (OSError, UnicodeDecodeError):
        pass
    return sections


def rust_edition(here):
    """The crate's edition from the nearest Cargo.toml, so rustfmt formats like `cargo fmt` would.
    A crate with `edition.workspace = true` gets the edition from `[workspace.package]` further up."""
    manifest = find_up(here, "Cargo.toml")
    if not manifest:
        return "2021"
    package = manifest_sections(manifest).get("package", [])
    for line in package:
        m = EDITION.match(line)
        if m:
            return m.group(1)
    if not any(INHERITED_EDITION.match(line) for line in package):
        return "2021"
    root = os.path.abspath(project_dir())
    while manifest:
        for line in manifest_sections(manifest).get("workspace.package", []):
            m = EDITION.match(line)
            if m:
                return m.group(1)
        d = os.path.dirname(manifest)
        if same_file(d, root) or os.path.dirname(d) == d:
            break
        manifest = find_up(os.path.dirname(d), "Cargo.toml")
    return "2021"


class Lint:
    """How to lint a file.

    file_only: the linter checks the whole package or crate, so only diagnostics for the edited file are reported
    (problems that were already in other files shouldn't block every edit). Otherwise exit code 1 means problems.
    """

    def __init__(self, cmd, cwd=None, file_only=False):
        self.cmd, self.cwd, self.file_only = cmd, cwd or project_dir(), file_only


def go_linter(path, here):
    mod = find_up(here, "go.mod")
    if not mod:
        return None
    mod_dir = os.path.dirname(mod)
    pkg = "./" + os.path.relpath(here, mod_dir).replace(os.sep, "/")
    pkg = "." if pkg == "./." else pkg
    g = shutil.which("golangci-lint")
    if g:
        return Lint([g, "run", pkg], mod_dir, file_only=True)
    go = shutil.which("go")
    if go:
        return Lint([go, "vet", pkg], mod_dir, file_only=True)
    return None


def rust_linter(here):
    manifest = find_up(here, "Cargo.toml")
    cargo = shutil.which("cargo")
    if manifest and cargo:
        return Lint([cargo, "clippy", "--quiet", "--no-deps", "--message-format=short"],
                     os.path.dirname(manifest), file_only=True)
    return None


def linter_for(path):
    """How to lint a file, or None. Linters that check one file exit 1 when they found problems."""
    ext = os.path.splitext(path)[1].lower()
    here = os.path.dirname(path)
    if ext == ".go":
        return go_linter(path, here)
    if ext == ".rs":
        return rust_linter(here)
    lint = file_linter(ext, here, path)
    return Lint(lint) if lint else None


def file_linter(ext, here, path):
    if ext in JS_EXT:
        e = node_tool(here, "eslint")
        if e and any(find_up(here, c) for c in ESLINT_CONFIGS):
            return [e, path]
        b = node_tool(here, "biome")
        if b:
            return [b, "lint", path]
    if ext == ".py":
        r = tool("ruff", here)
        if r:
            return [r, "check", "--quiet", path]
    if ext in {".sh", ".bash"} and shutil.which("shellcheck"):
        return ["shellcheck", "-f", "gcc", path]
    return None


def same_file(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def diagnostics_for(path, lines, cwd):
    """Diagnostic lines about `path`. Tools print paths relative to where they ran, the workspace root
    (cargo) or the config file (golangci-lint), so a relative path is tried against each folder up to the project."""
    bases = []
    d = os.path.abspath(cwd)
    root = os.path.abspath(project_dir())
    while True:
        bases.append(d)
        if same_file(d, root) or os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    keep = []
    for line in lines:
        m = DIAG.match(line)
        if m:
            name = m.group(1)
            candidates = [name] if os.path.isabs(name) else [os.path.join(b, name) for b in bases]
            if any(os.path.exists(c) and same_file(c, path) for c in candidates):
                keep.append(line)
    return keep


PRETTIER_CONFIGS = [".prettierrc", ".prettierrc.json", ".prettierrc.yml", ".prettierrc.yaml", ".prettierrc.json5",
                    ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.mjs", ".prettierrc.toml", "prettier.config.js",
                    "prettier.config.cjs", "prettier.config.mjs", "prettier.config.ts"]
GOLANGCI_CONFIGS = [".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json"]


def file_mentions(path, pattern):
    if not path:
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return re.search(pattern, f.read(), re.M) is not None
    except OSError:
        return False


def missing_tools(path, cfg):
    """[(tool, what it would do, how to get it)] for tools the project configures but that aren't installed."""
    ext = os.path.splitext(path)[1].lower()
    here = os.path.dirname(path)
    fmt, lint = cfg.get("format_on_edit", True), cfg.get("lint_on_edit", True)
    pyproject = find_up(here, "pyproject.toml")
    deps = "install the project's dependencies"
    out = []
    if fmt and ext in PRETTIER_EXT and not node_tool(here, "prettier"):
        if any(find_up(here, c) for c in PRETTIER_CONFIGS) or file_mentions(find_up(here, "package.json"),
                                                                            r'"prettier"\s*:'):
            out.append(("prettier", "formatting", deps))
    if lint and ext in JS_EXT and not node_tool(here, "eslint") and not node_tool(here, "biome"):
        if any(find_up(here, c) for c in ESLINT_CONFIGS):
            out.append(("eslint", "linting", deps))
    biome_configured = find_up(here, "biome.json") or find_up(here, "biome.jsonc")
    if ext in JS_EXT | {".json", ".css"} and biome_configured and not node_tool(here, "biome"):
        if fmt and not node_tool(here, "prettier"):
            out.append(("biome", "formatting", deps))
        elif lint and ext in JS_EXT and not node_tool(here, "eslint"):
            out.append(("biome", "linting", deps))
    if ext == ".py" and (fmt or lint) and not tool("ruff", here):
        if (find_up(here, "ruff.toml") or find_up(here, ".ruff.toml")
                or file_mentions(pyproject, r"^\[tool\.ruff")):
            out.append(("ruff", "formatting and linting" if fmt and lint else "formatting" if fmt else "linting",
                        "e.g. `uv add --dev ruff` or `pip install ruff`"))
        elif fmt and file_mentions(pyproject, r"^\[tool\.black") and not tool("black", here):
            out.append(("black", "formatting", "e.g. `pip install black`"))
    if ext == ".go":
        if fmt and not shutil.which("gofmt"):
            out.append(("gofmt", "formatting", "it comes with Go: https://go.dev/dl/"))
        if lint and find_up(here, "go.mod"):
            if any(find_up(here, c) for c in GOLANGCI_CONFIGS) and not shutil.which("golangci-lint"):
                out.append(("golangci-lint", "linting (go vet runs instead, if Go is installed)",
                            "https://golangci-lint.run/welcome/install/"))
            elif not shutil.which("golangci-lint") and not shutil.which("go"):
                out.append(("go", "linting", "https://go.dev/dl/"))
    if ext == ".rs":
        if fmt and not shutil.which("rustfmt"):
            out.append(("rustfmt", "formatting", "`rustup component add rustfmt`"))
        if lint and find_up(here, "Cargo.toml") and not shutil.which("cargo"):
            out.append(("cargo", "linting with clippy", "https://rustup.rs"))
    return out


def missing_tools_notice(payload, path, cfg):
    """A message for the user about tools not yet reported in this session, or None."""
    found = missing_tools(path, cfg)
    if not found:
        return None
    state_file = state_path("missing-tools", payload.get("session_id") or "", os.path.abspath(project_dir()))
    state = read_state(state_file)
    told = set(state.get("told") or [])
    new = [t for t in found if t[0] not in told]
    if not new:
        return None
    write_state(state_file, {"told": sorted(told | {t[0] for t in new})})
    ext = os.path.splitext(path)[1] or os.path.basename(path)
    lines = [f"- {name}: no {what} for {ext} files. To get it: {how}." for name, what, how in new]
    return ("[cct] This project configures tools that aren't installed, so edits skip them:\n" + "\n".join(lines)
            + "\nOr turn the step off with \"format_on_edit\" / \"lint_on_edit\" in .claude/cct.json.")


def repeat_limit(cfg):
    try:
        return max(0, int(cfg.get("lint_max_repeats", 3)))
    except (TypeError, ValueError):
        return 3


def count_report(payload, cfg, rel, found):
    """Track lint reports in a row for one file. Returns (send to Claude, report number, limit, notice for the user)."""
    limit = repeat_limit(cfg)
    state_file = state_path("lint-repeats", payload.get("session_id") or "", os.path.abspath(project_dir()))
    state = read_state(state_file)
    counts = state.get("counts") if isinstance(state.get("counts"), dict) else {}
    if not found:
        if rel in counts:  # clean again: the next problem starts a new count
            del counts[rel]
            write_state(state_file, {"counts": counts})
        return True, 0, limit, None
    n = int(counts.get(rel, 0) or 0) + 1
    counts[rel] = n
    write_state(state_file, {"counts": counts})
    if limit and n > limit:
        notice = None
        if n == limit + 1:
            notice = (f"[cct] {rel} still has lint problems after {limit} reports in a row, so they're no longer sent "
                      f"to Claude in this session, to save credits. Check them yourself, or raise \"lint_max_repeats\" "
                      f"in .claude/cct.json.")
        return False, n, limit, notice
    return True, n, limit, None


def run(cmd, cwd=None, timeout=30):
    try:
        return subprocess.run(cmd, cwd=cwd or project_dir(), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def first_time(payload, kind, keys):
    """The keys not reported yet in this session, which are then marked as reported."""
    path = state_path(kind, payload.get("session_id") or "", os.path.abspath(project_dir()))
    state = read_state(path)
    told = set(state.get("told") or [])
    new = [k for k in keys if k not in told]
    if new:
        write_state(path, {"told": sorted(told | set(new))})
    return new


def code_feedback(payload, path, cfg):
    """Messages for Claude about undeclared imports and duplicated functions this edit added."""
    want_imports, want_dupes = cfg.get("dependency_check", True), cfg.get("duplicate_hints", True)
    if not (want_imports or want_dupes) or not code_hints.lang(path):
        return []
    proj = project_dir()
    new, old = code_hints.edit_texts(payload, path, proj)
    if not new:
        return []
    rel = relpath(path, proj).replace(os.sep, "/")
    out = []
    if want_imports:
        found = code_hints.undeclared_imports(path, new, old, proj)
        keys = first_time(payload, "imports-told", [name for name, _ in found])
        for name, manifest in found:
            if name in keys:
                out.append(f"cct: {rel} imports `{name}`, which isn't declared in {manifest}. If it's a real package, "
                           f"add it with the package manager (the install is checked against the registry); if the "
                           f"name might be made up, fix the import.")
    if want_dupes:
        found = code_hints.duplicates(path, new, old, proj)
        keys = first_time(payload, "dupes-told", [name for name, _ in found])
        for name, hits in found:
            if name in keys:
                out.append(f"cct: `{name}` is new in {rel}, but {', '.join(hits)} already define"
                           f"{'s' if len(hits) == 1 else ''} it or a near-same name. Reuse it unless it does "
                           f"something different, and say why if so.")
    return out


def main():
    if defer_to_project(__file__):
        return
    cfg = load_config()
    payload = read_input()
    path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not path or not os.path.isfile(path):
        return
    mark_edited(payload, cfg)

    if cfg.get("format_on_edit", True):
        cmd = formatter_for(path)
        if cmd:
            run(cmd)

    capped = None
    feedback = code_feedback(payload, path, cfg)
    if cfg.get("lint_on_edit", True):
        lint = linter_for(path)
        result = run(lint.cmd, lint.cwd, LINT_TIMEOUT if lint.file_only else 30) if lint else None
        lines = []
        if result is not None:
            output = (result.stdout + "\n" + result.stderr).strip().splitlines()
            if lint.file_only:
                lines = diagnostics_for(path, output, lint.cwd)
            elif result.returncode == 1:
                lines = output
        rel = relpath(path, project_dir())
        send, n, limit, capped = count_report(payload, cfg, rel, bool(lines)) if result is not None else (True, 0, 0, None)
        if lines and send:
            shown = lines[:MAX_LINES] + ([f"… {len(lines) - MAX_LINES} more lines"] if len(lines) > MAX_LINES else [])
            name = os.path.splitext(os.path.basename(lint.cmd[0]))[0]
            if lint.cmd[1:2] in (["vet"], ["clippy"]):
                name += " " + lint.cmd[1]
            last = (f" This is report {n} of {limit} for this file; after it, problems here aren't sent back. If they "
                    f"aren't yours to fix, leave them and tell the user." if limit and n == limit else "")
            feedback.insert(0, f"cct lint: {name} found problems in {rel}. Fix them before moving on.{last}\n"
                               + "\n".join(shown))
    if feedback:
        print("\n\n".join(feedback), file=sys.stderr)
        sys.exit(2)  # stdout is ignored with exit 2, so a missing-tool notice waits for the next edit

    notify(capped, missing_tools_notice(payload, path, cfg))


if __name__ == "__main__":
    main()
