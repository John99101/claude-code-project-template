---
name: project-setup
description: Set up, finish or re-tune the Claude Code configuration (CLAUDE.md, rules, settings, MCP servers, agents, hooks) for a project or for this device. Use when a "[cct]" session notice says setup is pending, right after installing the Claude Code kit, when the user runs /setup, or when they want to change how Claude works in a project.
---

# Project setup

Finish this Claude Code kit so it fits **this project** and **this user**. Detect what you can, ask about what you can't, show the plan, then write it.

## Ground rules

- **Ask when unsure. Never guess at preferences.** Use AskUserQuestion: up to 4 questions per round, recommended option first, and say in the question what you detected ("Found Jest and Vitest configs. Which is current?").
- **Don't ask what you already know.** Detect from files first. Reuse saved answers from `~/.claude/cct-preferences.md` and list them in the plan instead of asking again.
- **Never write secrets** into any file. MCP configs use `${ENV_VAR}` references.
- **Never drop user-written content** from an existing `CLAUDE.md` or rule without asking.
- Keep `CLAUDE.md` under ~150 lines. Put topic detail in `.claude/rules/`.
- Don't commit or push. Offer `/commit` at the end.

## 0. Pick the mode

| Mode | When |
|---|---|
| **Project** | `.claude/cct-pending` exists in the project, or the user wants this project set up. |
| **Device** | `~/.claude/cct-pending` exists, or the user wants defaults for all projects on this machine. |
| **Re-tune** | No marker; the user ran `/setup` again. Read the current config and ask what to change (`$ARGUMENTS` may say). |

If both markers exist, ask which to do first. Device first is usually better because its answers feed project mode.

## 1. Load what's known

Read, if present:
- `~/.claude/cct-preferences.md`: saved answers from earlier setups.
- `~/.claude/CLAUDE.md` and `~/.claude/rules/`: device-wide instructions.
- Project: `CLAUDE.md`, `.claude/cct/CLAUDE.template.md` (the installer saves the template there when a `CLAUDE.md` already existed), `CLAUDE.local.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, `README.md`. Carry over the conventions they contain.

## 2. Detect (project mode)

| Look at | To learn |
|---|---|
| `package.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `Gemfile`, `composer.json`, `pubspec.yaml`, `*.csproj`, `Package.swift`, `deno.json` | Languages, frameworks, scripts |
| Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock*`, `uv.lock`, `poetry.lock`…) | Package manager |
| `jest.config.*`, `vitest.config.*`, `pytest.ini`, `[tool.pytest]`, `*_test.go`, `playwright.config.*` | Test framework, test locations |
| `.eslintrc*`, `eslint.config.*`, `biome.json`, `.prettierrc*`, `[tool.ruff]`, `.golangci.yml`, `rustfmt.toml`, `.editorconfig` | Linter, formatter, style |
| `tsconfig.json`, `mypy.ini`, `[tool.mypy]` | Type checking |
| `Makefile`, `justfile`, `Taskfile.yml`, `package.json` scripts | Real install/run/test/lint/build commands |
| `.github/workflows/`, `.gitlab-ci.yml` | What CI runs (the source of truth for checks) |
| `docker-compose*.yml`, `.env.example`, ORM config (`prisma/`, `alembic/`, `migrations/`) | Databases and services, which MCP servers might help |
| Top-level dirs, entry points (`src/main.*`, `app/`, `cmd/`) | Architecture summary |
| `git log --oneline -30`, `git branch -a`, `git remote -v` | Commit style, branch naming, default branch, GitHub/GitLab |

Also check tools: `python3` (the hooks need it; warn if missing), and the formatter binaries the hooks would call.

Run read-only commands only. Ask before running install, build or test commands that are slow or change files.

## 3. Ask

Use the question bank in [questions.md](questions.md). Pick only questions whose answers you couldn't detect and that aren't saved. A first-time project typically takes 2–3 rounds; a re-tune often takes 1.

## 4. Show the plan and confirm

Show a short plan: each file to create or change, with the key values (commands, test framework, guard level, MCP servers, models, saved preferences reused). Then ask: **Apply** (recommended) / **Change something** / **Cancel**.

## 5. Write

**Project mode**
- `CLAUDE.md`: fill every `{{…}}`. Delete table rows for commands that don't exist. If the user had a `CLAUDE.md`, merge the template's sections into it instead of replacing it.
- `.claude/rules/*.md`: fill the "Project specifics" sections. Set `paths:` globs to the project's real directories. If a rule doesn't apply (e.g. `api-design.md` in a CLI with no API), ask, then remove it. Add one rule per main language, e.g. `rules/python.md` with `paths: ["**/*.py"]`, covering the idioms and tools this project actually uses.
- `.claude/settings.json`: add `allow` entries for the exact detected safe commands (test, lint, format, type check, e.g. `Bash(npm run test:*)`). Set `"model"` only if the user chose one. Keep the `hooks` block.
- `.claude/cct.json`: `guard_level`, `format_on_edit`, `protect_lockfiles` from the answers.
- `.mcp.json`: add the chosen servers from [mcp-catalog.json](mcp-catalog.json), copying only each entry's `config` object under `mcpServers.<name>`. The catalog may be out of date, so check the vendor's docs for the current URL or package if you can. List every env var the user must set.
- `.claude/agents/*.md`: set `model:` per the user's answers. Remove agents they don't want.
- `.gitignore`: make sure `.claude/settings.local.json`, `CLAUDE.local.md`, `.env` and `.env.*` (but not `.env.example`) are ignored.

**Device mode**
- `~/.claude/CLAUDE.md`: personal preferences for all projects, from `~/.claude/cct/CLAUDE.user.template.md`, merged into any existing file.
- `~/.claude/rules/`: keep only rules that make sense everywhere (security, git workflow, general code style). Remove project-specific placeholders or move them to "decide per project". Delete `api-design.md` and `testing.md` from the device rules unless the user wants global defaults.
- `~/.claude/cct.json` and, if chosen, `"model"` in `~/.claude/settings.json`.

## 6. Verify

- JSON parses: `python3 -m json.tool <file> >/dev/null` for every JSON you touched.
- No placeholders left: `grep -rn '{{' CLAUDE.md .claude/` (device: `~/.claude/CLAUDE.md ~/.claude/rules`).
- Hooks work: `echo '{"tool_input":{"command":"git status"}}' | python3 .claude/hooks/guard_bash.py` prints nothing; with `"rm -rf /"` it prints a `deny`.
- If the user agreed, run the detected test or lint command once to confirm it's right.

## 7. Finish

1. Delete the marker: `.claude/cct-pending` (project) or `~/.claude/cct-pending` (device).
2. Ask whether to save the general answers to `~/.claude/cct-preferences.md` for future projects (format in [questions.md](questions.md)). Save only preferences that apply across projects, never project facts.
3. Tell the user, briefly:
   - what was set up, plus anything you couldn't detect;
   - env vars to set for MCP servers;
   - to restart Claude Code (or open `/hooks` and `/mcp`) so new hooks and MCP servers load;
   - that `/setup` re-tunes anything, `CLAUDE.local.md` holds personal overrides, and `/template-update` pulls kit updates.
