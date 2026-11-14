#!/usr/bin/env python3
"""PostToolUse hook for Edit/Write: formats the edited file, then lints it and reports problems back to Claude.

Uses only tools already installed in the project or on PATH; never downloads anything.
Lint problems are sent to Claude (exit code 2) so it fixes them right away.
Turn off with cct.json "format_on_edit": false / "lint_on_edit": false.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import defer_to_project, load_config, project_dir, read_input  # noqa: E402

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


def rust_edition(here):
    """The crate's edition from the nearest Cargo.toml, so rustfmt formats like `cargo fmt` would."""
    manifest = find_up(here, "Cargo.toml")
    if manifest:
        try:
            with open(manifest, encoding="utf-8") as f:
                m = re.search(r'^\s*edition\s*=\s*"(\d{4})"', f.read(), re.M)
            if m:
                return m.group(1)
        except (OSError, UnicodeDecodeError):
            pass
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


def run(cmd, cwd=None, timeout=30):
    try:
        return subprocess.run(cmd, cwd=cwd or project_dir(), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    if defer_to_project(__file__):
        return
    cfg = load_config()
    path = (read_input().get("tool_input") or {}).get("file_path") or ""
    if not path or not os.path.isfile(path):
        return

    if cfg.get("format_on_edit", True):
        cmd = formatter_for(path)
        if cmd:
            run(cmd)

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
        if lines:
            shown = lines[:MAX_LINES] + ([f"… {len(lines) - MAX_LINES} more lines"] if len(lines) > MAX_LINES else [])
            rel = os.path.relpath(path, project_dir())
            name = os.path.splitext(os.path.basename(lint.cmd[0]))[0]
            if lint.cmd[1:2] in (["vet"], ["clippy"]):
                name += " " + lint.cmd[1]
            print(f"cct lint: {name} found problems in {rel}. Fix them before moving on:\n"
                  + "\n".join(shown), file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
