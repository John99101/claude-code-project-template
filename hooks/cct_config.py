"""Shared helpers for the cct hooks: config loading, hook I/O, and device/project de-duplication.

Credit rule: whatever sends text to Claude makes it do follow-up work, which uses the user's credits. Useful ones (lint
feedback, the done gate) run, but each has a cap (lint_max_repeats, done_gate.attempts). Plain notices go to the user
only, via notify(), which Claude never sees, so they cost nothing.
"""
import hashlib
import json
import os
import sys
import time

DEFAULTS = {
    "guard_level": "standard",      # off | standard | strict
    "format_on_edit": True,
    "lint_on_edit": True,           # sends lint problems to Claude, whose fixes use credits...
    "lint_max_repeats": 3,          # ...so a file stops reporting after this many reports in a row (0: no cap)
    "protect_lockfiles": True,
    "protected_paths": [],          # globs relative to the project, e.g. "vendor/", "src/gen/**"
    "setup_reminder": True,
    "drift_check": True,            # session start: commands in CLAUDE.md and cct.json still exist (no credits)
    "update_check": False,          # session start: weekly look at the kit's latest GitHub release (no credits)
    "env_check": True,              # session start: stale installs, .env keys, runtime versions (no credits)
    "team_notice": True,            # session start: teammates changed CLAUDE.md, .claude/ or .mcp.json (no credits)
    "statusline_cost": True,        # status line shows the session's cost as Claude Code reports it
    "done_gate": {"commands": [], "timeout": 120, "attempts": 3},  # checks run before Claude finishes
}
STATE_DAYS = 7  # state files untouched for this long are deleted


def project_dir():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def home_claude():
    return os.path.join(os.path.expanduser("~"), ".claude")


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_config():
    """Defaults, then ~/.claude/cct.json, then <project>/.claude/cct.json."""
    cfg = dict(DEFAULTS)
    cfg.update(_read_json(os.path.join(home_claude(), "cct.json")))
    cfg.update(_read_json(os.path.join(project_dir(), ".claude", "cct.json")))
    return cfg


def _norm(path):
    """Absolute, case-normalised path (Windows paths are case-insensitive)."""
    return os.path.normcase(os.path.abspath(path))


def is_plugin_copy(script_path):
    """True when this script runs from the installed cct plugin."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root:
        return False
    return _norm(script_path).startswith(_norm(root) + os.sep)


def is_device_copy(script_path):
    """True when this script is installed for all projects: device-wide in ~/.claude/hooks/, or as the plugin."""
    if is_plugin_copy(script_path):
        return True
    return _norm(os.path.dirname(script_path)).startswith(_norm(os.path.join(home_claude(), "hooks")) + os.sep)


def setup_command(script_path):
    """How the user invokes setup: plugin skills are namespaced."""
    return "/cct:setup" if is_plugin_copy(script_path) else "/setup"


def defer_to_project(script_path):
    """Keep each hook running once when the kit is installed in several places.

    Precedence: project copy, then device copy (~/.claude/hooks/cct/), then plugin copy.
    """
    if not is_device_copy(script_path):
        return False
    name = os.path.basename(script_path)
    me = _norm(script_path)
    candidates = [os.path.join(project_dir(), ".claude", "hooks", name)]
    if is_plugin_copy(script_path):
        candidates.append(os.path.join(home_claude(), "hooks", "cct", name))
    return any(os.path.exists(c) and _norm(c) != me for c in candidates)


def read_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def notify(*messages):
    """Show a message to the user only. A hook's systemMessage isn't added to Claude's context, so it costs nothing."""
    text = "\n\n".join(m for m in messages if m)
    if text:
        print(json.dumps({"systemMessage": text}))


# Small JSON state files in ~/.claude/cct-state/, shared by the hooks.

def state_dir():
    return os.path.join(home_claude(), "cct-state")


def state_path(kind, *key):
    """A state file for `kind`, keyed by e.g. the session and project. No key: one file for the device."""
    if not key:
        return os.path.join(state_dir(), f"{kind}.json")
    digest = hashlib.sha256("\0".join(str(k) for k in key).encode()).hexdigest()[:24]
    return os.path.join(state_dir(), f"{kind}-{digest}.json")


def read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path, state):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def once(kind, scope, text, repeat_days=7):
    """`text` if it wasn't shown for this kind and scope (e.g. the project), or was shown over `repeat_days` ago;
    else None. A text that changes counts as new. With no text, the record is cleared, so the next problem shows."""
    path = state_path(kind, scope)
    state = read_state(path)
    if not text:
        if state:
            write_state(path, {})
        return None
    digest = hashlib.sha256(text.encode()).hexdigest()
    now = time.time()
    if state.get("shown") == digest and now - float(state.get("at", 0) or 0) < repeat_days * 86400:
        return None
    write_state(path, {"shown": digest, "at": now})
    return text


def prune_state():
    """Every session leaves state files behind; drop the ones nobody touched for STATE_DAYS."""
    folder = state_dir()
    cutoff = time.time() - STATE_DAYS * 86400
    try:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if name.endswith(".json") and os.path.getmtime(full) < cutoff:
                os.remove(full)
    except OSError:
        pass


def decide(decision, reason):
    """Return a PreToolUse permission decision (allow | ask | deny) and exit."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)
