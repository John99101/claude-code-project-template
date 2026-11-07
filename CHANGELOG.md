# Changelog

All notable changes to this kit. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/John99101/claude-code-project-template/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.0.0
