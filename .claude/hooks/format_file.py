#!/usr/bin/env python3
"""PostToolUse hook for Edit/Write: formats the edited file with the project's own formatter, if one is installed.

Never downloads tools and never fails the edit. Turn off with cct.json "format_on_edit": false.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import load_config, project_dir, read_input  # noqa: E402

PRETTIER_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".css", ".scss",
                ".less", ".html", ".vue", ".svelte", ".yaml", ".yml", ".graphql"}


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


def tool(name, start):
    local = find_up(start, os.path.join(".venv", "bin", name)) or find_up(start, os.path.join("node_modules", ".bin", name))
    return local or shutil.which(name)


def formatter_for(path):
    ext = os.path.splitext(path)[1].lower()
    here = os.path.dirname(path)
    if ext in PRETTIER_EXT:
        p = find_up(here, os.path.join("node_modules", ".bin", "prettier"))
        if p:
            return [p, "--write", "--log-level", "warn", path]
        if ext in {".js", ".jsx", ".ts", ".tsx", ".json", ".css"}:
            b = find_up(here, os.path.join("node_modules", ".bin", "biome"))
            if b:
                return [b, "format", "--write", path]
    if ext == ".py":
        r = tool("ruff", here)
        if r:
            return [r, "format", "--quiet", path]
        b = tool("black", here)
        if b:
            return [b, "--quiet", path]
    if ext == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", path]
    if ext == ".rs" and shutil.which("rustfmt"):
        return ["rustfmt", "--edition", "2021", path]
    if ext in {".sh", ".bash"} and shutil.which("shfmt"):
        return ["shfmt", "-w", path]
    return None


def main():
    if not load_config().get("format_on_edit", True):
        return
    tool_input = read_input().get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not path or not os.path.isfile(path):
        return
    cmd = formatter_for(path)
    if not cmd:
        return
    try:
        subprocess.run(cmd, cwd=project_dir(), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


if __name__ == "__main__":
    main()
