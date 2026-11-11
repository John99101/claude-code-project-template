# Changelog

All notable changes to this kit. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Quick or Thorough setup.** `/setup` first asks how thorough to be. Quick asks about 10 questions; Thorough asks about 25, adding plan-first, model, formatting, commit and branch style, deploy access, docs duties and supported versions.
- **Never-edit paths:** new `protected_paths` setting in `cct.json` (e.g. `["vendor/", "src/gen/**"]`). The file guard blocks edits there, and setup offers the generated or vendored code it finds.
- **Done checklist:** setup asks which checks must pass before Claude calls a task done, and writes them to a new "Before you say a task is done" section in `CLAUDE.md`. `CLAUDE.md` also records supported versions.
- **Question eval:** `tests/eval_questions.py` runs a read-only dry run of `/setup` on the sample projects and checks the questions it would ask. It runs weekly on GitHub after the setup eval.

### Changed
- **More informative setup questions.** Each question opens with what setup found and where, names the file the answer goes to, and gives every option a description of its effect and trade-off. Guard level, commit style, agent models and the status line show previews. Project questions offer a sourced best guess first. Filler such as "No saved preference found" is gone.
- The rules question always keeps code-style, git-workflow and security, so it fits in four options.

### Fixed
- The agent-models option said "others inherit", but test-writer runs on Sonnet.

## [2.0.0] - 2026-11-07

### Changed
- **The kit's own files no longer live in `.claude/`.** The repository now uses Claude Code's standard plugin layout (`skills/`, `agents/`, `hooks/`, `rules/`, `templates/`). The installer copies them into a project's `.claude/` only when you install. This also fixes the plugin validator's warning about the root `CLAUDE.md`, which is now `templates/CLAUDE.project.md`.
- **New cross-platform installer, `install.py`.** It replaces the bash script and works on Linux, macOS and Windows. `install.sh` (macOS/Linux) and `install.ps1` (Windows) are small launchers that find Python and run it.
- Hooks are registered in exec form (no shell), so they behave the same in Git Bash, PowerShell and sh, and paths with spaces work. Installing or updating migrates hook entries from 1.x automatically, without touching your own hooks.

### Added
- **Windows support:**
  - the guard covers the PowerShell tool (`Remove-Item -Recurse` on drives and system folders, `rd /s`, `Format-Volume`, `diskpart`, `iwr | iex`, registry deletes, `Set-ExecutionPolicy`), Windows paths in Git Bash (`/c/`, `C:/`), and `powershell -Command` or `cmd /c` launched from Bash;
  - the formatter and linter find tools in `.venv\Scripts\` and `node_modules\.bin\*.cmd`;
  - device installs detect `python3`, `py -3` or `python`;
  - CI runs on Windows.
- **`install.py --update`** updates an install in place: files you haven't changed are updated, files you changed are kept and the new version is saved under `.claude/cct/incoming/`, and files removed from the kit are cleaned up (including 1.0's `commands/`). `/template-update` uses it.
- **Status line for plugin users:** `/cct:setup` can turn it on through `scripts/enable_statusline.py`. It lives in the plugin's data folder, survives updates, and is refreshed by the session-start hook.
- **Setup eval with your subscription:** runs locally with your normal Claude login, and on GitHub with a `CLAUDE_CODE_OAUTH_TOKEN` secret from `claude setup-token` (an API key still works).
- Scheduled workflows re-enable themselves on each run, so GitHub's 60-day inactivity pause doesn't stop the weekly checks.

## [1.2.0] - 2026-11-07

### Added
- **Claude Code plugin.** Install with `/plugin install cct --marketplace John99101/claude-code-project-template`. Skills are namespaced (`/cct:setup`, `/cct:commit`…), updates come through `/plugin`, and teams can enable it for everyone in `.claude/settings.json`. The plugin reuses the same skills, agents and hook scripts as the script install; nothing is duplicated.
- **`install.sh --adopt`:** turns a repo created with "Use this template" into a normal project install. It moves the language rules into `.claude/cct/`, records the manifest so `/template-update` and `--uninstall` work, and removes the kit's own tests, CI workflows, docs and license. `/setup` detects a template copy and offers this first.
- Plugin validation (`claude plugin validate`) in CI, and a plugin icon.

### Fixed
- Repos created with "Use this template" carried the kit's development files (tests, CI, release workflow, license) and lacked `.claude/cct/`, so setup couldn't find the language rules.
- Hooks now run once even when the kit is installed as a plugin *and* via the script (project copy, then device copy, then plugin).

### Documentation
- Personal skills override project skills with the same name, so a device install shadows a project install's skills. The guide now recommends the plugin for device-wide use, since its skills are namespaced and never clash.

## [1.1.0] - 2026-11-07

### Added
- **Setup eval:** `tests/eval_setup.py` runs `/setup --defaults` for real on four sample projects (Python, TypeScript, Go, pnpm monorepo) and checks the result. A weekly or on-demand workflow runs it when an `ANTHROPIC_API_KEY` secret is set.
- **`/setup --defaults`:** non-interactive mode that uses detected values and recommended answers.
- **Lint feedback:** after each edit, the format hook also runs the project's linter (ESLint, Biome, Ruff, ShellCheck) and sends problems back to Claude to fix right away. Toggle with `lint_on_edit`.
- **Language rule packs** for Python, TypeScript/JavaScript, Go, Rust and Java/Kotlin. Setup installs the ones a project uses.
- **Monorepo support:** setup detects pnpm/npm/yarn workspaces, Nx, Turborepo, Lerna, Cargo, Go and uv workspaces, and gives each package its own short `CLAUDE.md`.
- **Uninstall:** `install.sh --uninstall` removes exactly what was installed, keeps files you changed, and takes the kit's hooks out of `settings.json`.
- **Status line** showing model, folder, branch, guard level and setup state.
- **Weekly MCP catalog check** that opens an issue when an entry stops working.
- **Release automation:** pushing a `v*` tag creates the GitHub release from this changelog. `VERSION` is recorded in `source.json`.
- Guide section on using the kit alongside other plugins such as ECC.

### Changed
- Slash commands moved from `.claude/commands/` to skills (Claude Code merged the two). The names are unchanged; the workflow ones are manual-only.
- The `project-setup` skill is now `setup`, so `/setup` runs it directly.
- MCP catalog: Slack now uses Slack's official hosted server, and Postgres uses the maintained `postgres-mcp` in read-only mode. Both old packages are deprecated.

### Fixed
- The Bash guard now looks inside `sh -c '…'`, `eval`, `$(…)` and backticks, catches `find … -delete` / `-exec rm`, and catches deleting `main`/`master` on the remote (`git push origin :main`, `--delete`).
- With both a device and a project install, hooks no longer run twice.

## [1.0.0] - 2026-11-07

### Added
- `install.sh` for project (`--project`) and device-wide (`--global`) installs, with `--dry-run`. It never overwrites files and merges `settings.json` with a backup.
- `project-setup` skill and `/setup` command: detects the stack, asks about unclear preferences, fills in all config, and remembers answers across projects.
- Rules: `code-style`, `testing`, `api-design`, `security`, `git-workflow`, with path targeting.
- Commands: `/check`, `/review-changes`, `/commit`, `/template-update`.
- Skills: `remember-preference`, `write-tests`, `debug-issue`, `release-notes`.
- Agents: `planner`, `reviewer`, `security-auditor`, `test-writer`.
- Hooks: setup reminder, Bash guard, secret-file protection, auto-format; tunable via `cct.json`.
- MCP catalog: GitHub, Atlassian (Jira/Confluence), Slack, Postgres, SQLite, Playwright, Context7.
- Test suite and CI on Linux and macOS.

[Unreleased]: https://github.com/John99101/claude-code-project-template/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.0.0
[1.2.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.2.0
[1.1.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.1.0
[1.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.0.0
