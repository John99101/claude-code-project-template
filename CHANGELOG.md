# Changelog

All notable changes to this kit. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/John99101/claude-code-project-template/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.1.0
[1.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.0.0
