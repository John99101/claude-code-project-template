# Hooks

Put scripts here that Claude Code should run automatically, then register them in `.claude/settings.json`.

Example: run a formatter after every file edit.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format.sh" }
        ]
      }
    ]
  }
}
```

Make scripts executable with `chmod +x`.
