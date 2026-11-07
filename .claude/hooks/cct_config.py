"""Shared helpers for the cct hooks: config loading, hook I/O, and device/project de-duplication."""
import json
import os
import sys

DEFAULTS = {
    "guard_level": "standard",      # off | standard | strict
    "format_on_edit": True,
    "lint_on_edit": True,
    "protect_lockfiles": True,
    "setup_reminder": True,
}


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


def is_device_copy(script_path):
    """True when this script is the device-wide install in ~/.claude/hooks/."""
    here = os.path.dirname(os.path.abspath(script_path))
    return here.startswith(os.path.join(home_claude(), "hooks") + os.sep)


def defer_to_project(script_path):
    """A device-wide hook stays silent when the project ships its own copy, so nothing runs twice."""
    if not is_device_copy(script_path):
        return False
    own = os.path.join(project_dir(), ".claude", "hooks", os.path.basename(script_path))
    return os.path.exists(own) and os.path.abspath(own) != os.path.abspath(script_path)


def read_input():
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


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
