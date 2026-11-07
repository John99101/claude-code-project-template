# {{PROJECT_NAME}}

<!-- cct: Loaded at the start of every Claude Code session in this project. /setup fills in the {{…}} parts.
     Keep this file under ~150 lines; topic details belong in .claude/rules/. -->

{{ONE_PARAGRAPH_OVERVIEW: what this project is, who uses it, what matters most}}

## Tech stack

- Languages: {{LANGUAGES}}
- Frameworks: {{FRAMEWORKS}}
- Package manager: {{PACKAGE_MANAGER}}
- Data and services: {{DATABASES_AND_SERVICES}}

## Commands

| Task | Command |
|---|---|
| Install | `{{INSTALL_CMD}}` |
| Run (dev) | `{{RUN_CMD}}` |
| Test (all) | `{{TEST_CMD}}` |
| Test (one) | `{{TEST_ONE_CMD}}` |
| Lint | `{{LINT_CMD}}` |
| Type check | `{{TYPECHECK_CMD}}` |
| Format | `{{FORMAT_CMD}}` |
| Build | `{{BUILD_CMD}}` |

## Architecture

{{ARCHITECTURE: main folders and what lives where, entry points, how a request or data flows through the system, key design decisions}}

## Conventions

Topic rules in `.claude/rules/` load automatically; some load only when you work on matching files:

- `code-style.md` — formatting, naming, structure
- `testing.md` — how tests are written and run
- `api-design.md` — API conventions
- `security.md` — secrets, input handling, dependencies
- `git-workflow.md` — branches, commits, pull requests

{{PROJECT_CONVENTIONS: anything important that isn't obvious from the code}}

## Working agreements

{{WORKING_AGREEMENTS: from the user's answers, e.g. autonomy level, what to ask before doing}}

## Tools for Claude

- Commands: `/setup` re-tunes this config · `/check` runs lint and tests · `/review-changes` reviews the diff · `/commit` commits in house style · `/template-update` updates the kit
- Agents: `planner`, `reviewer`, `test-writer`, `security-auditor`
- Personal, uncommitted notes: `CLAUDE.local.md` (see `CLAUDE.local.md.example`)
