"""Shared helpers for the cct hooks: config loading and hook I/O."""
import json
import os
import sys

DEFAULTS = {
    "guard_level": "standard",      # off | standard | strict
    "format_on_edit": True,
    "protect_lockfiles": True,
    "setup_reminder": True,
}


def project_dir():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


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
    cfg.update(_read_json(os.path.expanduser("~/.claude/cct.json")))
    cfg.update(_read_json(os.path.join(project_dir(), ".claude", "cct.json")))
    return cfg


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
