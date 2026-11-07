# Claude Code Project Kit

A self-installing Claude Code setup. Drop it into a project, or onto your machine for all projects, and Claude finishes the configuration for you: it detects your stack, **asks about anything it isn't sure of**, fills in `CLAUDE.md`, rules, settings, MCP servers and agents, and remembers your answers for the next project.

## Install

**Ask Claude** (easiest). In Claude Code, say:

> Install github.com/John99101/claude-code-project-template into this project, following its INSTALL.md

or "…onto this device for all my projects". Claude follows [INSTALL.md](INSTALL.md): it previews, installs, then runs setup with you.

**Or use the script:**

```bash
gh repo clone John99101/claude-code-project-template /tmp/cct -- --depth 1
bash /tmp/cct/install.sh --project ~/code/my-app   # one project, shared via git
bash /tmp/cct/install.sh --global                  # all projects on this device
```

Add `--dry-run` to preview. Existing files are never overwritten; `settings.json` is merged, with a backup. Then open Claude Code and run **`/setup`**.

**Or start a new repo from it:** click **Use this template** on GitHub. Setup starts on the first session.

Requires `python3` (the hooks use it) and Claude Code.

## How setup works

1. Install leaves a marker (`.claude/cct-pending`). On the next session, a hook tells Claude, and Claude offers `/setup`.
2. The **project-setup** skill reads your manifests, lockfiles, linters, CI, git history and any existing `CLAUDE.md`, `AGENTS.md` or `.cursorrules`.
3. It asks only what it couldn't detect, in short multiple-choice rounds: preferences, test approach, guard strictness, models, MCP integrations.
4. It shows the plan, applies it after your OK, verifies it, and removes the marker.
5. It offers to save your general answers to `~/.claude/cct-preferences.md`, so the next project only asks project questions.

Run `/setup` again any time to change something.

## What's inside

| Path | What it does |
|---|---|
| `CLAUDE.md` | **Loaded at session start.** Project overview, tech stack, commands, architecture, conventions. Personal overrides go in `CLAUDE.local.md` (git-ignored). |
| `.mcp.json` | **MCP integrations** (GitHub, Jira, Slack, databases…), shared with the team via git. Setup fills it from [`mcp-catalog.json`](.claude/skills/project-setup/mcp-catalog.json); tokens come from `${ENV_VARS}`, never the file. |
| `.claude/settings.json` | **Permissions, tool access, model, hooks.** Personal overrides go in `.claude/settings.local.json` (git-ignored; see the `.example`). |
| `.claude/rules/` | **Modular rules by topic:** `code-style`, `testing`, `api-design`, `security`, `git-workflow`. `testing` and `api-design` load only for matching paths (`paths:` frontmatter). Setup adds a rule for each main language. |
| `.claude/commands/` | **Slash commands for repeatable workflows**, some running shell commands for live context: `/setup`, `/check`, `/review-changes`, `/commit`, `/template-update`. |
| `.claude/skills/` | **Auto-triggered by task context**, loaded only when needed: `project-setup`, `remember-preference`, `write-tests`, `debug-issue`, `release-notes`. |
| `.claude/agents/` | **Specialised subagents** with their own context, tools and model: `planner` (Opus, read-only), `reviewer`, `security-auditor`, `test-writer` (Sonnet). |
| `.claude/hooks/` | **Event-driven scripts:** a setup reminder at session start; a guard that blocks destructive shell commands and secret-file edits; auto-formatting with your project's formatter. See [hooks/README](.claude/hooks/README.md). |
| `.claude/cct.json` | Kit switches: `guard_level` (`off` / `standard` / `strict`), `format_on_edit`, `protect_lockfiles`, `setup_reminder`. |
| `install.sh`, `scripts/`, `templates/` | Installer, settings merger, and device-wide templates. Not copied into projects. |

## Project vs device install

| | `--project` | `--global` |
|---|---|---|
| Where | `<project>/.claude/`, `CLAUDE.md`, `.mcp.json` | `~/.claude/` (hooks in `~/.claude/hooks/cct/`) |
| Shared with team | Yes, via git | No, just you |
| Setup | Once for the project | Once for your preferences; then each new project without a `CLAUDE.md` gets offered `/setup` |

Both can be combined: device install for your personal defaults, project install for team-shared config. When a project has its own hooks, the device hooks step aside for the setup reminder.

## Updating and removing

- **Update:** `/template-update`. It compares installed files with the latest kit using `.claude/cct/manifest.txt`, updates the files you haven't changed, and asks about the ones you have.
- **Remove:** delete the files listed in `.claude/cct/manifest.txt` and the `cct` hook entries in `settings.json`.
