<div align="center">

# Claude Code Project Kit

**A self-configuring setup for [Claude Code](https://docs.claude.com/en/docs/claude-code).**
Install it into a project or onto your machine, and Claude finishes the configuration for you,
asking about anything it isn't sure of.

[![CI](https://github.com/John99101/claude-code-project-template/actions/workflows/ci.yml/badge.svg)](https://github.com/John99101/claude-code-project-template/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/John99101/claude-code-project-template)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code](https://img.shields.io/badge/built%20for-Claude%20Code-D97757)](https://docs.claude.com/en/docs/claude-code)
[![Python 3](https://img.shields.io/badge/hooks-python%203-3776AB)](.claude/hooks/README.md)
[![M8ven Score](https://m8ven.ai/badge/mcp/john99101-claude-code-project-template-1leowc?v=0c6c47e43b32dc4a84be76945ec8ab42)](https://m8ven.ai/mcp/john99101-claude-code-project-template-1leowc?s=readme)

[Quick start](#quick-start) · [What setup looks like](#what-setup-looks-like) · [What's inside](#whats-inside) · [Full guide](docs/GUIDE.md)

</div>

---

## Why this exists

Claude Code is much more useful when it knows your project: how to run the tests, what the conventions are, what it must never touch, and which tools it may use. Claude Code supports all of this through `CLAUDE.md`, rules, settings, hooks, skills, agents and MCP servers. Setting them up by hand for every project is slow, easy to get wrong, and drifts over time.

This kit gives you:

- **A complete, tested structure.** Every part of Claude Code's configuration, organised so each piece loads only when it's needed.
- **A setup wizard that Claude runs itself.** It reads your project, fills in what it can detect, and asks you short multiple-choice questions about the rest. Monorepos get a brief per package.
- **Memory across projects.** Your answers are saved, so the next project only asks project-specific questions.
- **Safety and quality by default.** Hooks block destructive commands and secret-file edits, and send lint errors straight back to Claude to fix.

## Quick start

**Option 1: plugin** (easiest for personal use). In Claude Code:

```text
/plugin install cct --marketplace John99101/claude-code-project-template
```

Then run **`/cct:setup`** in any project. Updates arrive through `/plugin`, and `/plugin uninstall cct@cct-kit` removes it. On older Claude Code versions, add the marketplace first with `/plugin marketplace add John99101/claude-code-project-template`, then `/plugin install cct@cct-kit`.

**Option 2: ask Claude.** In Claude Code, inside your project:

```text
Install github.com/John99101/claude-code-project-template into this project, following its INSTALL.md
```

Claude previews the install, applies it, then walks you through setup. This puts the config in the repo, so your team shares it.

**Option 3: the install script.**

```bash
git clone --depth 1 https://github.com/John99101/claude-code-project-template /tmp/cct
python3 /tmp/cct/install.py --project ~/code/my-app   # one project, shared with your team via git
python3 /tmp/cct/install.py --global                  # every project on this device
```

On Windows, in PowerShell: `.\install.ps1 --project C:\code\my-app` (or `py -3 install.py …`).

Add `--dry-run` to preview. Existing files are never overwritten; `settings.json` is merged, with a backup. Then open Claude Code and run **`/setup`** (or `/setup --defaults` to skip the questions).

**Option 4: new repository.** Click **Use this template** on GitHub. Then run `python3 install.py --adopt` in it once. That turns the copy into a normal install and removes the kit's own tests, CI and docs. Restart Claude Code and run `/setup`.

<details>
<summary><b>Which option should I pick?</b></summary>

| | Plugin | Project install | Device script |
|---|---|---|---|
| Commands | `/cct:setup`, `/cct:commit`… | `/setup`, `/commit`… | `/setup`, `/commit`… |
| Shared with your team | Optional, via `.claude/settings.json` | Yes, committed to git | No |
| Updates | `/plugin` | `/template-update` (`install.py --update`) | `/template-update` |
| Status line | Yes, opt-in via `/cct:setup` | Yes | Yes |
| Clashes with a project install | Never (namespaced) | — | Its skills win over the project's |

</details>

Later: `--update` pulls kit updates and keeps your changes, and `--uninstall` removes the kit but keeps files you changed.

> **Requirements:** Claude Code and Python 3.8+. Tested on **Linux, macOS and Windows**. On Windows, install Python with the Python install manager from python.org, which provides the `python3` command ([details](docs/GUIDE.md#windows)).

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

Claude  Done. Set GITHUB_PERSONAL_ACCESS_TOKEN and DATABASE_URI, then restart Claude Code.
        Save your general answers for future projects? › Yes
```

See the [full walkthrough](docs/GUIDE.md#6-a-full-example) for the details.

## What's inside

The repository uses Claude Code's standard plugin layout, so nothing in it lives in `.claude/`. The plugin uses these folders directly; the installer copies them into a project's `.claude/` (shown after the arrow).

| Path | Role |
|---|---|
| [`templates/CLAUDE.project.md`](templates/CLAUDE.project.md) → `CLAUDE.md` | **Project brief, loaded every session.** Overview, tech stack, commands table, architecture, conventions. Personal overrides go in `CLAUDE.local.md` (git-ignored). |
| [`rules/`](rules) → `.claude/rules/` | **Conventions by topic:** code style, testing, API design, security, git workflow. Path-scoped rules load only for matching files. |
| [`rule-packs/`](rule-packs) → `.claude/cct/` | **Ready-made language rules** for Python, TypeScript/JavaScript, Go, Rust and Java/Kotlin. Setup installs the ones your project uses. |
| [`skills/`](skills) → `.claude/skills/` | **Slash commands and on-demand know-how.** You run `/setup`, `/check`, `/review-changes`, `/commit` and `/template-update`. Claude picks up `remember-preference`, `write-tests`, `debug-issue` and `release-notes` when relevant. |
| [`agents/`](agents) → `.claude/agents/` | **Specialist subagents** with their own context, tools and model: planner, reviewer, security auditor, test writer. |
| [`hooks/`](hooks) → `.claude/hooks/` | **Enforced behaviour:** setup reminder, shell-command guard, secret-file protection, format and lint on every edit, status line. |
| [`templates/settings.project.json`](templates/settings.project.json) → `.claude/settings.json` | **Permissions, tool access, model, hooks and status line** (hooks and status line are added by the installer). Personal overrides go in `settings.local.json`. |
| [`templates/mcp.json`](templates/mcp.json) → `.mcp.json` | **External tools** (GitHub, Jira, Slack, databases…), shared via git. Credentials stay in `${ENV_VARS}`. |
| [`templates/cct.json`](templates/cct.json) → `.claude/cct.json` | **Kit switches:** guard level, format and lint on edit, lockfile protection, setup reminder. |

<details>
<summary><b>Full file tree</b></summary>

```text
.
├── .claude-plugin/               # plugin manifest, marketplace entry, icon
├── skills/                       # setup (+ questions, MCP catalog), check, review-changes, commit,
│                                 # template-update, remember-preference, write-tests, debug-issue, release-notes
├── agents/                       # planner, reviewer, security-auditor, test-writer
├── hooks/                        # hooks.json + session_start, guard_bash, protect_files, format_file, statusline
├── rules/                        # code-style, testing, api-design, security, git-workflow
├── rule-packs/                   # python, typescript, go, rust, java
├── templates/                    # CLAUDE.md templates, base settings, cct.json, mcp.json, examples
├── install.py                    # install, update, adopt, uninstall (Linux, macOS, Windows)
├── install.sh, install.ps1       # launchers that find Python and run install.py
├── scripts/                      # settings merger, status line helper, MCP catalog check, changelog tool
├── tests/                        # test suite, setup eval, sample projects
└── docs/GUIDE.md                 # in-depth guide
```

What a project gets after `install.py --project`:

```text
my-app/
├── CLAUDE.md                     # project brief, filled in by /setup
├── CLAUDE.local.md.example       # personal overrides example
├── .mcp.json                     # MCP servers (filled by /setup)
└── .claude/
    ├── settings.json             # permissions, hooks, status line
    ├── cct.json                  # kit switches
    ├── rules/  skills/  agents/  hooks/
    └── cct/                      # rule packs, package template, install manifest
```

</details>

## Safety

| | Examples |
|---|---|
| **Blocked** | `rm -rf /` or `~` (also inside `sh -c`, `eval`, `$(…)`), `find / -delete`, `mkfs`, `curl … \| sh`, force-pushing or deleting `main`, editing `.env` or private keys |
| **Asks first** | `rm -r`, `find … -delete`, `git reset --hard`, `sudo`, `DROP TABLE`, publishing packages, editing lockfiles or CI |

Set `guard_level` to `strict` to also confirm pushes, new dependencies and any deletes. Details are in the [safety model](docs/GUIDE.md#7-the-safety-model).

## Quality checks

| Check | When |
|---|---|
| [Test suite](tests/test_kit.py): hooks (Bash and PowerShell), installer, update, uninstall, plugin, file formats | Every push, on Linux, macOS and Windows |
| [Setup eval](tests/eval_setup.py): runs `/setup` for real on four sample projects | Any time on your machine with your Claude subscription (`python3 tests/eval_setup.py`); weekly on GitHub with a `claude setup-token` secret ([how](docs/GUIDE.md#running-the-setup-eval)) |
| [MCP catalog check](scripts/check_mcp_catalog.py): every server URL and package still exists | Weekly; opens an issue if something breaks |

## Documentation

- **[Guide](docs/GUIDE.md):** why each part exists, the setup flow, configuration, using it with other plugins, troubleshooting, FAQ
- **[INSTALL.md](INSTALL.md):** install instructions written for Claude
- **[Hooks](.claude/hooks/README.md):** what each hook does and how to add your own
- **[Changelog](CHANGELOG.md)**

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Run the tests with `python3 tests/test_kit.py -v`.

## License

[MIT](LICENSE)
