# Hooks

Event-driven scripts registered in `.claude/settings.json`. They need `python3` and nothing else.

| Script | Event | What it does |
|---|---|---|
| `session_start.py` | `SessionStart` | Tells **you** (not Claude, so no credits) when setup is unfinished, when commands in `CLAUDE.md` or `done_gate` no longer match the project (`drift.py`), when installs are stale, `.env` keys are missing or runtime versions are wrong (`env_check.py`), when teammates changed the Claude config (`team_notice.py`), when a `/handoff` note is waiting, and, if you turned on `update_check`, when a newer kit release is out (`update_check.py`). Quiet after `/clear` and compaction. |
| `guard_bash.py` | `PreToolUse` · `Bash\|PowerShell` | Blocks destructive commands (`rm -rf /`, `find / -delete`, `mkfs`, force-push or deleting `main`, `curl … \| sh`), including when they're hidden in `sh -c`, `eval`, `$(…)` or backticks. Asks before risky ones (`rm -r`, `git reset --hard`, `sudo`, `DROP TABLE`, publishing). |
| `protect_files.py` | `PreToolUse` · `Edit\|Write` | Blocks writes to `.env`, keys, `secrets/`, `.git/` and your `protected_paths`. Asks before editing lockfiles or CI workflows. |
| `format_file.py` | `PostToolUse` · `Edit\|Write` | Formats the edited file with the project's formatter (prettier, biome, ruff, black, gofmt, rustfmt, shfmt), then lints it (eslint, biome, ruff, shellcheck, golangci-lint or go vet, cargo clippy) and **sends problems back to Claude** to fix right away. Go and Rust linters check the whole package or crate, but only problems in the edited file are reported. A file that still has problems after `lint_max_repeats` reports in a row (default 3) stops being reported for the session, and you're told. When the project configures a tool that isn't installed, tells you once per session. Never downloads anything. |
| `done_gate.py` | `Stop` | Off until `done_gate.commands` is set in `cct.json`. A command may use `{files}` for the changed files, to run only related tests. `python3 done_gate.py --check` runs the commands once and reports each, without Claude. When Claude finishes a turn that changed files (Edit/Write, or any git working-tree change, so shell edits count too), runs those commands and **blocks finishing** while one fails, sending the output tail back. Lets Claude finish when it changes nothing after being blocked, after `attempts` tries, or when the commands exceed `timeout`. |
| `statusline.py` | `statusLine` | Shows `model · folder (branch) · session cost · guard level · setup state`. |
| `cct_config.py` | — | Shared helper: loads `cct.json`, user-only notices, state files, and makes device-wide hooks step aside when the project has its own copy. |
| `drift.py`, `env_check.py`, `team_notice.py`, `update_check.py` | — | Helpers for `session_start.py`. |

## Tuning

Change behaviour in `.claude/cct.json` (project) or `~/.claude/cct.json` (all projects). The project file wins.

```json
{
  "guard_level": "standard",
  "format_on_edit": true,
  "lint_on_edit": true,
  "lint_max_repeats": 3,
  "protect_lockfiles": true,
  "protected_paths": ["vendor/", "src/gen/**"],
  "setup_reminder": true,
  "drift_check": true,
  "env_check": true,
  "team_notice": true,
  "statusline_cost": true,
  "update_check": false
}
```

- **Credits:** `lint_on_edit` and `done_gate` send text to Claude, and its follow-up work uses your Claude usage. Both are capped: `lint_max_repeats` (default 3, `0` for no cap) per file and session, and `done_gate.attempts` (default 3) per turn. Everything else here costs nothing.

- `guard_level`: `off` disables both guards; `strict` also asks before `git push`, adding dependencies and any `rm`.
- `protected_paths`: project-relative globs Claude must never edit, such as generated or vendored code. A folder written as `dir/` covers everything in it. `/setup` asks about these. Default: none.
- Hooks load when a session starts. After changing `settings.json`, restart Claude Code or review them with `/hooks`.
- The guard is a safety net, not a sandbox. For untrusted work, also turn on Claude Code's built-in sandbox (`/sandbox`).

## Adding your own

Drop a script into the project's `.claude/hooks/` and register it in `.claude/settings.json`. Use exec form (`command` plus `args`), which runs without a shell, so it works the same on macOS, Linux and Windows and handles paths with spaces:

```json
{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/my_hook.py"] }] }
```

To ship a hook with the kit itself, add the script to the kit's `hooks/` folder and an entry to `hooks/hooks.json` (with `${CLAUDE_PLUGIN_ROOT}/hooks/…`). The installer builds project and device settings from that same file.

A `PreToolUse` hook blocks a tool call by printing a `permissionDecision` JSON, as `cct_config.decide()` does. Any hook can send a message to Claude by writing to stderr and exiting with code 2, as the lint step does, but that costs the user credits: give it a cap, as the lint step and done gate have. To tell the user something, use `cct_config.notify()`, which prints a `systemMessage` that Claude never sees. Add a test in `tests/test_kit.py`.
