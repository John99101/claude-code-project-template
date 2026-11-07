<div align="center">

# Claude Code Project Kit

**A self-configuring setup for [Claude Code](https://docs.claude.com/en/docs/claude-code).**
Install it into a project or onto your machine, and Claude finishes the configuration for you,
asking about anything it isn't sure of.

[![CI](https://github.com/John99101/claude-code-project-template/actions/workflows/ci.yml/badge.svg)](https://github.com/John99101/claude-code-project-template/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-D97757)](https://docs.claude.com/en/docs/claude-code)
[![Python 3](https://img.shields.io/badge/hooks-python%203-3776AB)](.claude/hooks/README.md)

[Quick start](#quick-start) · [What setup looks like](#what-setup-looks-like) · [What's inside](#whats-inside) · [Full guide](docs/GUIDE.md)

</div>

---

## Why this exists

Claude Code is much more useful when it knows your project: how to run the tests, what the conventions are, what it must never touch, and which tools it may use. Claude Code supports all of this through `CLAUDE.md`, rules, settings, hooks, skills, agents and MCP servers. Setting them up by hand for every project is slow, easy to get wrong, and drifts over time.

This kit gives you:

- **A complete, tested structure.** Every part of Claude Code's configuration, organised so each piece loads only when it's needed.
- **A setup wizard that Claude runs itself.** It reads your project, fills in what it can detect, and asks you short multiple-choice questions about the rest.
- **Memory across projects.** Your answers are saved, so the next project only asks project-specific questions.
- **Safety by default.** Hooks block destructive commands and secret-file edits before they happen.

## Quick start

**Option 1: ask Claude.** In Claude Code, inside your project:

```text
Install github.com/John99101/claude-code-project-template into this project, following its INSTALL.md
```

Or say *"…onto this device for all my projects"*. Claude previews the install, applies it, then walks you through setup.

**Option 2: the install script.**

```bash
gh repo clone John99101/claude-code-project-template /tmp/cct -- --depth 1
bash /tmp/cct/install.sh --project ~/code/my-app   # one project, shared with your team via git
bash /tmp/cct/install.sh --global                  # every project on this device
```

Add `--dry-run` to preview. Existing files are never overwritten; `settings.json` is merged, with a backup. Then open Claude Code and run **`/setup`**.

**Option 3: new repository.** Click **Use this template** on GitHub. Setup is offered on the first session.

> **Requirements:** Claude Code and `python3`. Tested on Linux and macOS.

## What setup looks like

*Illustrative run on a TypeScript API:*

```text
Claude  This project has the Claude Code kit installed, but setup isn't finished. Run /setup now?
You     yes
Claude  Found: TypeScript + Fastify, pnpm, Vitest, ESLint + Prettier, Postgres, Conventional Commits.
        ? How independently should I work?      › Ask before big or risky changes (recommended)
        ? How should tests be handled?          › Write tests with every change (recommended)
        ? Connect any tools via MCP?            › GitHub, Postgres
        ? Safety guard level?                   › Standard (recommended)

        Plan: CLAUDE.md (stack, 7 commands, architecture) · 5 rules + typescript.md
              settings: allow pnpm test/lint/typecheck · .mcp.json: GitHub, Postgres
        Apply? › Apply

Claude  Done. Set GITHUB_PERSONAL_ACCESS_TOKEN and DATABASE_URL, then restart Claude Code.
        Save your general answers for future projects? › Yes
```

See the [full walkthrough](docs/GUIDE.md#6-a-full-example) for the details.

## What's inside

| Path | Role |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | **Project brief, loaded every session.** Overview, tech stack, commands table, architecture, conventions. Personal overrides go in `CLAUDE.local.md` (git-ignored). |
| [`.claude/rules/`](.claude/rules) | **Conventions by topic:** code style, testing, API design, security, git workflow. Path-scoped rules load only for matching files. Setup adds one per language. |
| [`.claude/commands/`](.claude/commands) | **Slash commands:** `/setup`, `/check`, `/review-changes`, `/commit`, `/template-update`. They pull live shell output (git status, diffs) into the prompt. |
| [`.claude/skills/`](.claude/skills) | **Know-how that loads on demand:** project setup, remembering preferences, writing tests, debugging, release notes. |
| [`.claude/agents/`](.claude/agents) | **Specialist subagents** with their own context, tools and model: planner, reviewer, security auditor, test writer. |
| [`.claude/hooks/`](.claude/hooks) | **Enforced behaviour:** setup reminder, shell-command guard, secret-file protection, auto-formatting. |
| [`.claude/settings.json`](.claude/settings.json) | **Permissions, tool access, model and hook registration.** Personal overrides go in `settings.local.json`. |
| [`.mcp.json`](.mcp.json) | **External tools** (GitHub, Jira, Slack, databases…), shared via git. Credentials stay in `${ENV_VARS}`. |
| [`.claude/cct.json`](.claude/cct.json) | **Kit switches:** guard level, format-on-edit, lockfile protection, setup reminder. |

<details>
<summary><b>Full file tree</b></summary>

```text
.
├── CLAUDE.md                     # project brief (template)
├── CLAUDE.local.md.example       # personal overrides example
├── .mcp.json                     # MCP servers (filled by setup)
├── .claude/
│   ├── settings.json             # permissions + hooks
│   ├── settings.local.json.example
│   ├── cct.json                  # kit switches
│   ├── rules/                    # code-style, testing, api-design, security, git-workflow
│   ├── commands/                 # setup, check, review-changes, commit, template-update
│   ├── skills/                   # project-setup (+ questions, MCP catalog), remember-preference,
│   │                             # write-tests, debug-issue, release-notes
│   ├── agents/                   # planner, reviewer, security-auditor, test-writer
│   └── hooks/                    # session_start, guard_bash, protect_files, format_file
├── install.sh                    # installer (not copied into projects)
├── scripts/merge_settings.py     # safe settings merger
├── templates/                    # device-wide CLAUDE.md and settings
├── tests/test_kit.py             # test suite
└── docs/GUIDE.md                 # in-depth guide
```

</details>

## Safety

| | Examples |
|---|---|
| **Blocked** | `rm -rf /` or `~`, `mkfs`, `curl … \| sh`, force-push to `main`, editing `.env` or private keys |
| **Asks first** | `rm -r`, `git reset --hard`, `sudo`, `DROP TABLE`, publishing packages, editing lockfiles or CI |

Set `guard_level` to `strict` to also confirm pushes, new dependencies and any deletes. Details are in the [safety model](docs/GUIDE.md#7-the-safety-model).

## Documentation

- **[Guide](docs/GUIDE.md):** why each part exists, the setup flow, configuration, troubleshooting, FAQ
- **[INSTALL.md](INSTALL.md):** install instructions written for Claude
- **[Hooks](.claude/hooks/README.md):** what each hook does and how to add your own
- **[Changelog](CHANGELOG.md)**

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Run the tests with `python3 tests/test_kit.py -v`.

## License

[MIT](LICENSE)
