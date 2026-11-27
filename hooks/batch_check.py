#!/usr/bin/env python3
"""Stop hook: says when uncommitted work has grown too big to review comfortably.

DORA's 2025 research finds AI raises delivery speed but lowers stability, and that small batches are one of the
practices that let teams keep the gains. When the uncommitted diff passes "batch_max_lines" (default 300; lockfiles,
snapshots, minified, generated and protected_paths files don't count), the user is told to commit the finished part
or split the work. Again at double, triple… the limit; the count starts over once the diff is small again.

"batch_nudge": "user" (default) shows it to the user only, at no cost. "claude" also sends it to Claude once, so it
proposes a commit point itself (a few tokens). "batch_max_lines": 0 turns it off.

`python3 batch_check.py --size [base]` prints the counted lines and files (against `base`, e.g. origin/main, or the
working tree), the same numbers /pr uses for its size check.
"""
import fnmatch
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import (defer_to_project, load_config, notify, project_dir, read_input, read_state,  # noqa: E402
                        state_path, write_state)

LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock", "poetry.lock", "uv.lock",
             "Pipfile.lock", "Cargo.lock", "Gemfile.lock", "composer.lock", "go.sum", "npm-shrinkwrap.json"}
NOT_REVIEWED = ["*.snap", "*/__snapshots__/*", "*.min.js", "*.min.css", "*.map", "*.lock", "*.pb.go", "*_pb2.py",
                "*/generated/*", "*/__generated__/*", "dist/*", "build/*", "vendor/*", "*.svg", "*.png", "*.jpg"]


def counted(rel, cfg):
    rel = rel.replace("\\", "/")
    if os.path.basename(rel) in LOCKFILES:
        return False
    patterns = NOT_REVIEWED + [p.rstrip("/") + ("/*" if p.endswith("/") else "")
                               for p in cfg.get("protected_paths") or [] if isinstance(p, str)]
    return not any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch("/" + rel, "*/" + p.lstrip("*/")) for p in patterns)


def git(proj, *args):
    try:
        r = subprocess.run(["git", "--no-optional-locks", *args], cwd=proj, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def diff_size(proj, cfg, base=None):
    """(lines changed, files changed) that a reviewer would read, or None outside git."""
    numstat = git(proj, "diff", "--numstat", base or "HEAD")
    if numstat is None:
        numstat = git(proj, "diff", "--numstat")  # a repo without commits yet
        if numstat is None:
            return None
    lines, files = 0, 0
    for row in numstat.splitlines():
        parts = row.split("\t")
        if len(parts) != 3 or not counted(parts[2], cfg):
            continue
        added, removed = parts[0], parts[1]
        if added == "-":  # binary
            continue
        lines += int(added) + int(removed)
        files += 1
    if not base:
        for rel in (git(proj, "ls-files", "--others", "--exclude-standard") or "").splitlines():
            if not counted(rel, cfg) or rel.replace("\\", "/").startswith(".claude/cct-state/"):
                continue
            try:
                with open(os.path.join(proj, rel), "rb") as f:
                    n = min(f.read(2_000_000).count(b"\n"), 5000)
            except OSError:
                continue
            if n:
                lines += n
                files += 1
    return lines, files


def limit(cfg):
    try:
        return max(0, int(cfg.get("batch_max_lines", 300)))
    except (TypeError, ValueError):
        return 300


def main():
    if defer_to_project(__file__):
        return
    cfg = load_config()
    payload = read_input()
    cap = limit(cfg)
    if not cap:
        return
    proj = project_dir()
    size = diff_size(proj, cfg)
    if not size:
        return
    lines, files = size
    path = state_path("batch", os.path.abspath(proj))
    level = lines // cap
    seen = int(read_state(path).get("level", 0) or 0)
    if level < 1:
        if seen:
            write_state(path, {"level": 0})
        return
    if level <= seen:
        return
    write_state(path, {"level": level})
    text = (f"[cct] {lines} lines in {files} files are uncommitted (limit {cap}). Small batches stay reviewable and "
            f"safe to revert: commit the finished part with /commit, or split the rest into a separate change. "
            f"Change the limit with \"batch_max_lines\" in .claude/cct.json.")
    if cfg.get("batch_nudge", "user") == "claude" and not payload.get("stop_hook_active"):
        print(json.dumps({"decision": "block", "systemMessage": text, "reason": (
            f"cct small-batch check: {lines} changed lines in {files} files are uncommitted. Before going on, propose "
            f"to the user where to make a commit (which files form a finished, working step), and don't start new "
            f"work in this change.")}))
        return
    notify(text)


if __name__ == "__main__":
    if "--size" in sys.argv[1:]:
        rest = [a for a in sys.argv[1:] if a != "--size"]
        found = diff_size(project_dir(), load_config(), rest[0] if rest else None)
        print("not a git repository" if found is None else f"{found[0]} lines in {found[1]} files")
        sys.exit(0 if found is not None else 1)
    main()
