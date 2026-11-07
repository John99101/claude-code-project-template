# Claude Code Project Template

A starter structure for projects built with [Claude Code](https://docs.claude.com/en/docs/claude-code). Use it as a GitHub template, or copy the folders you need.

## Structure

```
.
├── CLAUDE.md                  # Project instructions Claude reads every session
├── .mcp.json                  # MCP servers shared with the team
├── .claude/
│   ├── settings.json          # Shared settings: permissions, hooks, env
│   ├── agents/                # Custom subagents (one .md file each)
│   │   └── reviewer.md
│   ├── skills/                # Skills / slash commands (one folder each)
│   │   └── release-notes/
│   │       └── SKILL.md
│   └── hooks/                 # Scripts called from hooks in settings.json
│       └── README.md
├── docs/                      # Project docs Claude can reference
├── src/                       # Source code
└── tests/                     # Tests
```

## What each part does

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Commands, conventions and rules for this project. Keep it short and specific. |
| `.claude/settings.json` | Checked-in settings for everyone. Personal overrides go in `.claude/settings.local.json` (git-ignored). |
| `.claude/agents/` | Subagents with their own prompt, tools and model. Claude can delegate to them. |
| `.claude/skills/` | Reusable workflows. Each `SKILL.md` becomes a `/skill-name` command. |
| `.claude/hooks/` | Shell scripts run automatically on events like `PostToolUse`. Wire them up in `settings.json`. |
| `.mcp.json` | MCP servers (external tools) available to everyone on the project. |

## Getting started

1. Click **Use this template** on GitHub (or clone the repo).
2. Edit `CLAUDE.md` with your project's real commands and conventions.
3. Run `claude` in the project folder.

Personal, uncommitted notes for Claude can go in `CLAUDE.local.md` (git-ignored).
