#!/usr/bin/env python3
"""Stop hook: before Claude finishes a turn that changed files, run the project's done-checklist commands and send
failures back so Claude keeps working.

Configure in cct.json:  "done_gate": {"commands": ["npm test", "npm run lint"], "timeout": 120, "attempts": 3}
An empty command list (the default) turns it off. Each block sends output to Claude, and its fix uses the user's
credits, so /setup only turns this on when the user chooses it.

`python3 done_gate.py --check` runs the commands once and prints pass or fail for each, without Claude: setup uses it
to confirm the commands work, and users can run it any time.

A turn counts as having changed files when format_file.py saw an Edit or Write (mark_edited), or when the git working
tree differs from the last time this hook looked (session_start.py records the first look), which also catches edits
made with shell commands. A turn that changed nothing finishes at once. Commands run in order and stop at the first
failure.

Claude may finish with failing checks, and the user is told, when it was blocked and then changed nothing (it judged
the failure out of scope and explained why), or after `attempts` blocked stops in a row. A command that times out
isn't treated as a failure: the turn finishes and the user is told it wasn't checked.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import (defer_to_project, load_config, project_dir, prune_state, read_input,  # noqa: E402
                        read_state, state_dir, write_state)
from cct_config import state_path as _state_path  # noqa: E402

MAX_LINES = 40
CHECK_LINES = 15    # --check shows less: its output is read during /setup
MAX_TIMEOUT = 580   # hooks.json gives this hook 600 s


def gate_config(cfg):
    """(commands, timeout, attempts) from cct.json, tolerating hand-edited values."""
    gate = cfg.get("done_gate")
    if not isinstance(gate, dict):
        return [], 0, 0
    commands = [c for c in gate.get("commands") or [] if isinstance(c, str) and c.strip()]

    def number(key, default, low, high):
        try:
            return max(low, min(high, int(gate.get(key, default))))
        except (TypeError, ValueError):
            return default

    return commands, number("timeout", 120, 1, MAX_TIMEOUT), number("attempts", 3, 1, 10)


# State, one small JSON file per session and project:
#   tree      fingerprint of the git working tree when this hook last looked
#   dirty     files changed since the checks last ran to completion
#   edited    an Edit or Write happened since the last block
#   attempts  blocked stops in a row in this turn

def state_path(session_id):
    return _state_path("done-gate", session_id, os.path.abspath(project_dir()))


def tree_fingerprint():
    """A hash of the git working tree's changed and untracked files (paths, sizes and modification times), or None
    outside git. Cheap: it reads `git status` and stats the files it lists, without reading their contents."""
    proj = project_dir()
    try:
        r = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                           cwd=proj, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    own = os.path.normcase(os.path.realpath(state_dir())) + os.sep  # this hook's state, when ~ is the project
    h = hashlib.sha256()
    entries = r.stdout.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1  # the original path of a rename or copy follows
        full = os.path.join(proj, entry[3:])
        if os.path.normcase(os.path.realpath(full)).startswith(own):
            continue
        h.update(entry.encode() + b"\0")
        try:
            st = os.stat(full)
            h.update(f"{st.st_mtime_ns}:{st.st_size}\0".encode())
        except OSError:
            h.update(b"-\0")
    return h.hexdigest()


def mark_edited(payload, cfg):
    """Called by format_file.py after each Edit or Write."""
    if not gate_config(cfg)[0]:
        return
    path = state_path(payload.get("session_id") or "")
    state = read_state(path)
    if not (state.get("dirty") and state.get("edited")):
        state.update(dirty=True, edited=True)
        write_state(path, state)


def record_baseline(payload, cfg):
    """Called by session_start.py: what the working tree looked like before Claude did anything."""
    if not gate_config(cfg)[0]:
        return
    path = state_path(payload.get("session_id") or "")
    state = read_state(path)
    if "tree" not in state:  # a resumed or compacted session keeps its earlier baseline
        state["tree"] = tree_fingerprint()
        write_state(path, state)


def run(command, timeout):
    """(exit code or None on timeout, output)."""
    env = dict(os.environ)
    env.setdefault("CI", "1")  # test runners skip watch mode and interactive prompts
    try:
        r = subprocess.run(command, shell=True, cwd=project_dir(), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, errors="replace", timeout=timeout)
        return r.returncode, (r.stdout + "\n" + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return None, ""
    except OSError as e:
        return 127, str(e)


def tail(output):
    lines = output.splitlines()
    if len(lines) <= MAX_LINES:
        return lines
    return [f"… {len(lines) - MAX_LINES} earlier lines"] + lines[-MAX_LINES:]


def main():
    if defer_to_project(__file__):
        return
    payload = read_input()
    commands, timeout, attempts = gate_config(load_config())
    if not commands:
        return
    path = state_path(payload.get("session_id") or "")
    state = read_state(path)
    tree = tree_fingerprint()
    tree_changed = tree is not None and state.get("tree") is not None and tree != state["tree"]
    if not (state.get("dirty") or tree_changed):
        if tree != state.get("tree"):
            state["tree"] = tree
            write_state(path, state)
        return
    prune_state()
    if not payload.get("stop_hook_active"):
        state["attempts"] = 0  # a new turn from the user gets a fresh budget
    changed_since_block = state.get("edited") or tree_changed

    def finish(message=None):
        write_state(path, {"tree": tree_fingerprint()})  # after the run, so files the checks wrote don't count
        if message:
            print(json.dumps({"systemMessage": f"cct done gate: {message}"}))
        sys.exit(0)

    deadline = time.monotonic() + timeout
    for command in commands:
        left = deadline - time.monotonic()
        code, output = run(command, left) if left >= 1 else (None, "")
        if code is None:
            finish(f"`{command}` didn't finish within {timeout} s, so the done checklist wasn't checked. Raise "
                   f"done_gate.timeout in .claude/cct.json if it's usually slower.")
        if code != 0:
            if payload.get("stop_hook_active") and not changed_since_block:
                finish(f"`{command}` still fails. Claude changed nothing after being told, so it was allowed to "
                       f"finish.")
            state["attempts"] = state.get("attempts", 0) + 1
            if state["attempts"] > attempts:
                finish(f"`{command}` still fails after {attempts} {'try' if attempts == 1 else 'tries'} to fix it. "
                       f"Claude was allowed to finish.")
            state.update(tree=tree_fingerprint(), dirty=True, edited=False)
            write_state(path, state)
            print(json.dumps({
                "decision": "block",
                "reason": f"cct done gate: `{command}` failed (exit {code}). Fix the cause, then finish again "
                          f"(try {state['attempts']} of {attempts}). If it can't pass for a reason outside this "
                          f"task, don't change any more files: tell the user what fails and why, and finish.\n"
                          + "\n".join(tail(output)),
            }))
            sys.exit(0)
    finish()


def check():
    """`--check`: run the commands once, as the gate would, and report each. Exit 1 if any failed or timed out."""
    commands, timeout, _ = gate_config(load_config())
    if not commands:
        print("No done_gate.commands set in .claude/cct.json, so the done gate is off.")
        return 0
    failed = False
    start = time.monotonic()
    deadline = start + timeout
    for command in commands:
        left = deadline - time.monotonic()
        began = time.monotonic()
        code, output = run(command, left) if left >= 1 else (None, "")
        took = time.monotonic() - began
        if code is None:
            print(f"TIMEOUT  {command}  (the {timeout} s limit for all commands ran out)")
            failed = True
            break
        if code == 0:
            print(f"PASS     {command}  ({took:.1f} s)")
            continue
        failed = True
        print(f"FAIL     {command}  (exit {code}, {took:.1f} s)")
        lines = output.splitlines()
        shown = lines[-CHECK_LINES:]
        if len(lines) > CHECK_LINES:
            print(f"         … {len(lines) - CHECK_LINES} earlier lines")
        for line in shown:
            print(f"         {line}")
        break  # the gate stops at the first failure too
    total = time.monotonic() - start
    print(f"Total {total:.1f} s of a {timeout} s limit. These run after every turn in which Claude changed files.")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        sys.exit(check())
    main()
