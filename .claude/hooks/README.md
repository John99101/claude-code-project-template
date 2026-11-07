# Hooks

Event-driven scripts registered in `.claude/settings.json`. They need `python3` and nothing else.

| Script | Event | What it does |
|---|---|---|
| `session_start.py` | `SessionStart` | Tells Claude when setup is unfinished (`.claude/cct-pending`) so it offers `/setup`. |
| `guard_bash.py` | `PreToolUse` · `Bash` | Blocks destructive commands (`rm -rf /`, `mkfs`, force-push to main, `curl … \| sh`). Asks before risky ones (`git reset --hard`, `sudo`, `DROP TABLE`, publishing). |
| `protect_files.py` | `PreToolUse` · `Edit\|Write` | Blocks writes to `.env`, keys and `secrets/`. Asks before editing lockfiles or CI workflows. |
| `format_file.py` | `PostToolUse` · `Edit\|Write` | Formats the edited file with the project's own formatter (prettier, biome, ruff, black, gofmt, rustfmt, shfmt) if installed. Never downloads anything. |
| `cct_config.py` | — | Shared helper that loads `cct.json`. |

## Tuning

Change behaviour in `.claude/cct.json` (project) or `~/.claude/cct.json` (all projects). The project file wins.

```json
{
  "guard_level": "standard",
  "format_on_edit": true,
  "protect_lockfiles": true,
  "setup_reminder": true
}
```

- `guard_level`: `off` disables both guards; `strict` also asks before `git push`, adding dependencies and any `rm`.
- Hooks load when a session starts. After changing `settings.json`, restart Claude Code or review them with `/hooks`.

## Adding your own

Drop a script here and register it in `settings.json`:

```json
{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/my_hook.py\"" }] }
```

A `PreToolUse` hook blocks a tool call by exiting with code 2 (stderr goes to Claude), or by printing a `permissionDecision` JSON as `cct_config.decide()` does.
