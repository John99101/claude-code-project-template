# Changelog

All notable changes to this kit. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Demo GIF** at the top of the README: setup, then a made-up package blocked, a skipped test caught and an unverified "tests pass" sent back. `.github/demo/make_demo.py` redraws it from the hooks' real output (needs Pillow; maintainers only). `--adopt` removes the folder from "Use this template" copies.

## [2.2.1.2] - 2026-11-27

### Changed
- **Documentation brought up to date.** The FAQ now says exactly which lookups the hooks make (package names for the dependency check, the opt-in update notice) and how credits are capped. The guide's setup flow and example show the session-start notice and the newer questions, question counts are current, and the hooks table, safety model, testing and troubleshooting sections cover pins, the test guard, the trifecta and the dependency check. The plugin and marketplace descriptions name the new guards and skills.

## [2.2.1.1] - 2026-11-27

### Added
- **Dependency check against made-up packages.** Before `npm/pnpm/yarn/bun add`, `pip install`, `uv add`, `poetry add`, `pdm add` or `cargo add`, each package is looked up on npm, PyPI or crates.io. Names that don't exist are blocked; packages younger than `dependency_min_age_days` (30) or barely downloaded need your OK. Offline or with a private registry, installs go through. Imports an edit adds that no manifest declares are pointed out to Claude. `"dependency_check": false` turns both off.
- **Claim check:** a new `Stop` hook sends Claude back once when its final reply claims tests pass, a build works or something was verified, but no check ran in that turn. `"claim_check": false` turns it off.
- **`/pin`** pins constraints for the task in `.claude-pins.md` (gitignored). They're added back to Claude's context at every session start and after compaction, and `never edit:` / `only edit:` pins are enforced by the file guard.
- **One instructions file for every AI tool.** When the team also uses Cursor, Copilot, Codex or Gemini, setup makes `AGENTS.md` the shared source, `CLAUDE.md` imports it, and the files in `agent_files` are generated from it (`agent_files.py --write`, `--check` for CI). Session start flags a `CLAUDE.md` that doesn't import an existing `AGENTS.md`, and out-of-date copies. The drift check follows `@` imports.
- **Portability check** for teams with Windows (`team_platforms`): POSIX-only commands in `CLAUDE.md`, `AGENTS.md` or `done_gate`, hooks with backslash or machine-specific paths, and shell scripts with CRLF or no `.gitattributes` LF rule. Setup asks which systems the team uses.
- **Duplicate hints:** a function an edit adds that already exists elsewhere, under any casing, is pointed out to Claude. `"duplicate_hints": false` turns it off.
- **Test guard:** edits to test files that add skip or disable markers, remove test cases or assertions, or only change an expected value need your OK (blocked with `guard_level: strict`); deleting test files with `rm`/`git rm` asks too, and "tests pass" after adding a skip is an unbacked claim. `"test_guard": false` turns it off.
- **Lethal-trifecta check:** when MCP servers and allowed tools give Claude private data, untrusted content and a way to send data out, session start warns with concrete fixes, and outbound commands (`curl -d`, `gh api` writes, `nc`, `scp` to a host) need your OK. Catalog entries now say which legs they bring. Setup checks before writing `.mcp.json`. `"trifecta_check": false` turns it off.
- **Small-batch nudge:** a new `Stop` hook says when uncommitted changes pass `batch_max_lines` (300; lockfiles, snapshots and generated files excluded). `"batch_nudge": "claude"` also lets Claude propose a commit point. `batch_check.py --size` gives `/pr` the same count.
- **`/spec`** writes a behaviour spec with acceptance criteria for your OK before coding, then builds test-first against it. `/pr` repeats the criteria, `/start-issue` offers it for bigger issues, and the drift check flags criteria naming files that are gone (`spec_dir`, default `specs/`).
- **`/tidy`** proposes small behaviour-preserving cleanups for recently changed code and commits each separately; `/pr` lists them apart.
- **`/learn`** turns learning mode on or off: Claude explains concepts, lets you guess bugs first and leaves small parts for you. Setup asks about it (with Claude Code's Learning or Explanatory output style).
- **Review-ready `/pr`:** suggests splitting diffs over `pr_max_lines` (400) or 15 files, and adds a "For the reviewer" section: assumptions, what's untested, and the places to review first.

## [2.2.1] - 2026-11-27

### Added
- **Social preview image** for the repository, in `.github/social-preview/`, with `make.py` to redraw it (needs Pillow; maintainers only, the kit itself stays dependency-free). `install.py --adopt` removes the folder from "Use this template" copies, like the other kit-only files.

## [2.2.0] - 2026-11-27

### Added
- **`/pr`** pushes the branch and opens a pull request (GitLab: merge request) from the repo's PR template, with a summary, linked issues and a test plan that ticks only checks that actually ran. It shows the draft first and never merges.
- **`/start-issue <n>`** reads a GitHub or GitLab issue, creates a branch in house style, finds the code involved and shows a plan, then waits for your OK.
- **`/handoff`** saves where a task stands to `.claude-handoff.md` (gitignored), and `/handoff resume` picks it up in a later session. Session start tells you when a note is waiting.
- **Environment check** at session start: a lockfile newer than the last install (or nothing installed), a missing `.env` or keys that `.env.example` lists (names only, never values), and `node`/`python` versions that don't match `.nvmrc`, `.node-version`, `engines` or `.python-version`. Shown to you only. `"env_check": false` turns it off.
- **Team-change notice:** when teammates' commits since your last session changed `CLAUDE.md`, `.claude/` or `.mcp.json`, session start names the files and authors and gives the `git diff` to see them. `"team_notice": false` turns it off.
- **Session cost in the status line**, from Claude Code's own estimate. `"statusline_cost": false` hides it.
- **Related tests in the done gate:** a command may contain `{files}`, which the gate fills with the changed files (e.g. `npx vitest related --run {files}`). With no changes it's skipped. `/setup` now suggests related-only test commands.
- **Done gate.** A new `Stop` hook runs the commands in `done_gate.commands` (in `.claude/cct.json`) when Claude finishes a turn that changed files, and sends a failure back so Claude keeps working instead of saying it's done. In a git repository, edits made with shell commands count too. Claude may still finish when it judges a failure out of scope and changes nothing more, or after `done_gate.attempts` tries (default 3). Commands that exceed `done_gate.timeout` (default 120 s) are skipped, with a message. Off by default; `/setup` offers it with the done-checklist commands.
- **Drift check.** At session start, the kit checks that the commands in `CLAUDE.md` (the Commands table and the done checklist) and in `done_gate.commands` still fit the project: the `package.json` script, `Makefile` target, `justfile` recipe, file or tool still exists. It only reads files, never runs the commands, and tells you, not Claude. Turn off with `"drift_check": false`.
- **Done gate check without Claude:** `python3 .claude/hooks/done_gate.py --check` runs the gate's commands once and prints PASS, FAIL or TIMEOUT for each, with the total time. `/setup` runs it right after you turn the gate on, and asks whether to fix, keep or drop a failing command instead of changing code.
- **Lint repeat cap.** A file that still has lint problems after `lint_max_repeats` reports in a row (default 3) stops sending them to Claude for the rest of the session, so Claude doesn't burn credits on a linter it can't satisfy. You get a one-line notice, and a clean lint resets the count.
- **Missing-tool notices.** When the project configures a formatter or linter (ruff, black, prettier, eslint, biome, golangci-lint, rustfmt…) that isn't installed, you're told once per session instead of edits skipping it silently. Setup's summary lists them too.
- **Update notice (opt-in).** Script installs can get a session-start notice when a newer kit release is out. It asks GitHub at most once a week, sends nothing about you or the project, and never updates by itself. `/setup` asks; it's off otherwise (`"update_check"` in `~/.claude/cct.json`).
- **Go and Rust lint feedback.** After an edit, the format hook runs `golangci-lint` (or `go vet` when it isn't installed) on the edited file's package, and `cargo clippy` on its crate. Only problems in the edited file go back to Claude, so existing warnings elsewhere don't block every edit. Clippy warnings count, not just errors.

### Changed
- The session-start setup reminder is now a message to you instead of an instruction to Claude, so it no longer costs tokens. Claude doesn't bring setup up on its own any more.
- `/setup` names the credit cost of lint feedback and the done gate, and their caps, when it asks about them.
- Session-start notices no longer repeat after `/clear` or compaction.

### Fixed
- The drift check flagged quoted Windows paths in `done_gate.commands` (e.g. `"C:\…\python.exe"`) as missing tools.
- `rustfmt` used the 2021 edition for every crate. It now reads `edition` from the nearest `Cargo.toml`, and from the workspace root's `[workspace.package]` when the crate sets `edition.workspace = true`.

## [2.1.0] - 2026-11-11

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

[Unreleased]: https://github.com/John99101/claude-code-project-template/compare/v2.2.1.2...HEAD
[2.2.1.2]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.2.1.2
[2.2.1.1]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.2.1.1
[2.2.1]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.2.1
[2.2.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.2.0
[2.1.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.1.0
[2.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v2.0.0
[1.2.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.2.0
[1.1.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.1.0
[1.0.0]: https://github.com/John99101/claude-code-project-template/releases/tag/v1.0.0
