#!/usr/bin/env python3
"""PreToolUse hook for Edit/Write: blocks writes to secrets, git internals, cct.json "protected_paths" and paths the
user pinned with /pin ("never edit:", "only edit:"), and asks before touching lockfiles and CI, and before edits that
weaken tests (skips, removed test cases or assertions, changed expected values; see test_guard.py)."""
import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import decide, defer_to_project, load_config, project_dir, read_input  # noqa: E402
import pins  # noqa: E402
import test_guard  # noqa: E402

SECRET_OK = {".env.example", ".env.sample", ".env.template", ".env.dist"}
SECRET_PATTERNS = ["*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "*.keystore", "credentials.json"]
LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock", "poetry.lock",
    "uv.lock", "Pipfile.lock", "Cargo.lock", "Gemfile.lock", "composer.lock", "go.sum",
}


def protected_match(rel, patterns):
    """Return the first cct.json protected_paths glob that matches rel (a /-separated project path), or None.

    A pattern ending in "/" covers everything under that folder. "*" also matches across folders.
    """
    if not isinstance(patterns, list) or rel == ".." or rel.startswith("../"):
        return None
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        p = pattern.strip().replace("\\", "/")
        while p.startswith("./"):
            p = p[2:]
        if not p:
            continue
        if p.endswith("/"):
            p += "*"
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p + "/*"):
            return pattern
    return None


def check_pins(rel_slash, rel):
    """Path pins from .claude-pins.md: the user set them for this task, so they block rather than ask."""
    if rel_slash in pins.ALWAYS_EDITABLE or rel_slash == ".." or rel_slash.startswith("../"):
        return
    never, only = pins.path_pins(pins.read(project_dir()))
    hit = protected_match(rel_slash, never)
    if hit:
        decide("deny", f"Blocked by a pin: the user said never to edit '{hit}' (in .claude-pins.md). Tell the user "
                       "if the task needs it; they can change the pin with /pin.")
    if only and not protected_match(rel_slash, only):
        decide("deny", f"Blocked by a pin: the user said to only edit {', '.join(only)} (in .claude-pins.md), and "
                       f"{rel} is outside that. Tell the user if the task needs it; they can widen it with /pin.")


def edit_texts(tool_input, path):
    """(old, new) text of this edit. A Write is compared with the file on disk."""
    if "new_string" in tool_input:
        return str(tool_input.get("old_string") or ""), str(tool_input.get("new_string") or "")
    if isinstance(tool_input.get("edits"), list):
        edits = [e for e in tool_input["edits"] if isinstance(e, dict)]
        return ("\n".join(str(e.get("old_string") or "") for e in edits),
                "\n".join(str(e.get("new_string") or "") for e in edits))
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            old = f.read()
    except OSError:
        old = ""
    return old, str(tool_input.get("content") or "")


def check_tests(cfg, tool_input, path, rel_slash, level):
    if not cfg.get("test_guard", True) or not test_guard.is_test_path(rel_slash):
        return
    why = test_guard.problem(rel_slash, *edit_texts(tool_input, path))
    if why:
        decide("deny" if level == "strict" else "ask",
               f"cct test guard: this edit to {rel_slash} {why}. If the test is wrong, say why; if the code is wrong, "
               "fix the code.")


def main():
    if defer_to_project(__file__):
        return
    cfg = load_config()
    level = str(cfg.get("guard_level", "standard")).lower()
    if level == "off":
        return
    tool_input = read_input().get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return
    name = os.path.basename(path)
    try:
        rel = os.path.relpath(os.path.abspath(path), project_dir())
    except ValueError:
        rel = path
    parts = rel.replace("\\", "/").split("/")

    if (name == ".env" or name.startswith(".env.")) and name not in SECRET_OK:
        decide("deny", f"Blocked by cct guard: {name} holds secrets. Edit it yourself, or use .env.example for templates.")
    if any(fnmatch.fnmatch(name, p) for p in SECRET_PATTERNS) or "secrets" in parts:
        decide("deny", f"Blocked by cct guard: {rel} looks like a key or secret file.")
    if ".git" in parts:
        decide("deny", "Blocked by cct guard: don't edit git internals directly; use git commands.")
    pattern = protected_match("/".join(parts), cfg.get("protected_paths"))
    if pattern:
        decide("deny", f"Blocked by cct guard: {rel} matches protected path '{pattern}' in cct.json. "
                       "Regenerate it with its tool, or edit it yourself.")
    check_pins("/".join(parts), rel)
    check_tests(cfg, tool_input, path, "/".join(parts), level)

    if cfg.get("protect_lockfiles", True) and name in LOCKFILES:
        decide("ask", f"cct guard: {name} is generated by the package manager. Prefer running it instead of editing by hand. Confirm to continue.")
    if len(parts) >= 3 and parts[0] == ".github" and parts[1] == "workflows":
        decide("ask", f"cct guard: {rel} changes CI. Confirm to continue.")


if __name__ == "__main__":
    main()
