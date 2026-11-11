# Setup question bank

Ask only what you couldn't detect and isn't in `~/.claude/cct-preferences.md`. Device mode asks the **Personal** and **Safety** groups; project mode asks **Project**, plus **Personal** only if nothing is saved.

## How to write each question

Every AskUserQuestion call should let the user decide without opening a file.

- **Lead with evidence.** Start the question with what you found and where: file, value, count. "pyproject.toml configures ruff (line-length 100) and black. Which formatter should run after each edit?" If you found nothing relevant to the choice, say so: "No formatter config found."
- **Only facts that inform the choice.** No filler about the setup process itself: never "No saved preference found", "Currently not set", "Asking because…" or a restatement of the question. Questions without a detectable fact (verbosity, experience, autonomy) are just the question and its target.
- **Say where the answer goes.** End the question with the target in brackets: `[→ .claude/cct.json]`, `[→ CLAUDE.md]`, `[saved for all projects]`.
- **Fill every option's `description`** with its concrete effect and its trade-off. Use the descriptions below, and swap in detected names (the real test command, the real linter).
- **Recommended option first**, with "(Recommended)" at the end of its label. If detection points to a different option than the default, recommend that one and say why.
- **Use `preview`** where the difference is easier to see than to describe. The questions below that have one say so.
- **Header** is a 12-character-or-shorter chip, given per question below.
- Group up to 4 related questions per round: personal style, then safety, then project facts.

## Personal (saved across projects)

### `language` · header `Language`
Q: "Which language should I reply in? You're writing in {detected language}. [saved for all projects]"
- **Same as you write (Recommended)**: I mirror each message. Code, commits and file contents stay in English.
- **English**: always English, even if you write in another language.
- **{detected language}**: always this language, even if you write in English. Code and commits stay English.

### `verbosity` · header `Detail`
Q: "How long should my replies be? [→ ~/.claude/CLAUDE.md]"
- **Short summaries (Recommended)**: outcome first, a few bullets, no basics. Ask for detail when you want it.
- **Detailed explanations**: reasoning, alternatives considered, and what to watch for.
- **Minimal**: one or two lines plus file references. Best if you read the diffs yourself.

### `experience` · header `Level`
Q: "How should I pitch technical explanations? [→ ~/.claude/CLAUDE.md]"
- **Experienced developer**: skip fundamentals, use precise terms, link to code instead of explaining it.
- **Learning, explain more**: explain why, name the concepts, point to docs.
- **Non-technical**: plain language, no jargon, focus on what changed for you rather than how.

### `autonomy` · header `Autonomy`
Q: "How independently should I work? [→ ~/.claude/CLAUDE.md]"
- **Ask before big or risky changes (Recommended)**: small edits go ahead. I ask before multi-file refactors, deletions, new dependencies and anything in the next question.
- **Ask before every change**: I show a plan or diff and wait each time. Safest, but slow.
- **Work independently, report after**: I finish the task and summarise. The safety guard still applies.

### `ask_before` · header `Ask first` · multi-select
Q: "Which actions should always need your OK, even in auto-accept mode? [→ ~/.claude/CLAUDE.md]"
- **Adding dependencies**: any `npm add`, `pip install`, `cargo add`… or a manual edit of the dependency list.
- **Deleting files**: removing tracked files or folders, including generated ones.
- **Changing public APIs**: exported functions, HTTP routes, CLI flags, DB schema.
- **Database migrations**: creating or running migrations.

Pre-select the first two. These are instructions to Claude. To enforce them with a hook, use `guard_level: strict`.

### `test_approach` · header `Tests`
Q: "How should I handle tests? {Found: pytest, 42 test files in tests/ | No tests found.} [→ ~/.claude/CLAUDE.md]"
- **Tests with every change (Recommended)**: each feature or bug fix gets tests, and I run the suite before saying I'm done.
- **Test-first (TDD)**: I write a failing test, then the code, then refactor. Slower, catches more.
- **Only when asked**: no tests unless you request them. Fine for prototypes.

### `commit_style` · header `Commits`
Q: "Commit message style? {Last 30 commits: 24 Conventional Commits, 6 plain | No history yet.} [→ .claude/rules/git-workflow.md]"
Recommend **Match existing history** if history has a clear pattern, otherwise Conventional Commits. Use `preview` with an example message for each option, built from a real recent change.
- **Conventional Commits**: `feat(auth): add token refresh`. Works with changelog and release tools.
- **Plain sentences**: `Add token refresh to the auth client`. Short and readable.
- **Match existing history**: I copy the pattern in `git log`: prefix, tense, length.

### `model` · header `Model`
Q: "Default model for sessions? Currently {value of "model" in settings.json | Claude Code's default}. [→ settings.json "model"]"
- **Claude Code's default (Recommended)**: no setting written, so you follow Anthropic's default as it changes. Switch per session with `/model`.
- **Opus**: strongest reasoning, for hard debugging and architecture. Slower and uses your limits fastest.
- **Sonnet**: fast and capable for everyday coding. Uses your limits much more slowly than Opus.
- **Haiku**: fastest and cheapest, for simple edits and lookups. Weaker on multi-step work.

### `agent_models` · header `Agents`
Q: "Models for the helper agents (planner, reviewer, security-auditor, test-writer)? [→ .claude/agents/*.md model:]"
Use `preview` with the agent → model table for each option.
- **Kit defaults (Recommended)**: planner on Opus, test-writer on Sonnet, reviewer and security-auditor use your session model. Strong planning, cheap test writing.
- **All use my session model**: every agent follows `/model`. Simplest, and costs follow your choice.
- **All on Sonnet**: cheapest predictable setup. Plans and reviews are a little weaker.

## Safety

### `guard_level` · header `Guard`
Q: "How strict should the Bash and file guard be? [→ .claude/cct.json guard_level]"
Use `preview` with what each level blocks and asks about, as below.
- **Standard (Recommended)**: blocks disk formatting, `rm -rf` on root or home, `curl | sh`, and force-pushes to main. Asks before `git reset --hard`, `git clean -f`, other force-pushes, `sudo`, `DROP TABLE`, publishing a package, and reading `.env`. Blocks writes to `.env`, keys and `.git/`.
- **Strict**: everything in Standard, plus it asks before every `git push`, every dependency install (`npm add`, `pip install`, `cargo add`…) and every `rm`. Good for unfamiliar repos and production code.
- **Off**: no guard, only Claude Code's own permission prompts. Not recommended.

Preview text for Standard:
```
BLOCK  mkfs, dd to disk, rm -rf / ~ *, curl|sh,
       git push --force main, writes to .env/*.pem/.git
ASK    git reset --hard, git clean -f, push --force,
       branch -D, sudo, DROP/TRUNCATE, npm publish,
       cat .env, edits to lockfiles and CI workflows
```

### `format_on_edit` · header `Format`
Q: "Format each file right after I edit it? {Found: ruff format via pyproject.toml | prettier in node_modules | Nothing installed.} [→ .claude/cct.json]"
- **Yes, with {detected formatter} (Recommended)**: runs only tools already installed (prettier, biome, ruff, black, gofmt, rustfmt, shfmt) and never downloads anything. Keeps diffs consistent.
- **No**: files stay as I write them. Choose this if formatting runs in a pre-commit hook or the project has no formatter.

If nothing is installed, say that Yes has no effect until one is.

### `lint_on_edit` · header `Lint`
Q: "Lint each file after I edit it and fix the problems right away? {Found: ruff check | eslint.config.js | none.} [→ .claude/cct.json]"
- **Yes, with {detected linter} (Recommended)**: lint errors come straight back to me, up to 40 lines, and I fix them before moving on.
- **No**: lint only when you or CI runs it. Choose this if the linter is slow or the code has many existing warnings.

### `protect_lockfiles` · header `Lockfiles`
Q: "Ask before I edit lockfiles by hand? {Found: uv.lock | No lockfile yet; uv creates uv.lock on the first `uv sync`.} [→ .claude/cct.json]"
Always ask this whenever the Safety group is asked, even if no lockfile exists: the setting outlives the repo's current state, and lockfiles usually appear later. Never skip it because nothing was found.
- **Yes (Recommended)**: I'm asked to use the package manager instead. Hand-edited lockfiles drift from the manifest.
- **No**: allow direct edits, e.g. for merge-conflict fixes.

### `statusline` · header `Statusline`
Q: "Show a status line? {You already have one: <command> | None configured.} [→ settings.json statusLine]"
Use `preview` with `Opus · my-app (main) · guard standard · setup done`.
- **Yes (Recommended)**: shows model, folder, branch, guard level and whether setup is pending. If one already exists, recommend No.
- **No, keep mine / none**: nothing changes.

## Project (not saved globally)

Always offer your best guess as option 1, labelled with where it came from.

| Key · header | Question | When to ask · how |
|---|---|---|
| overview · `Purpose` | "In one or two sentences, what is this project for? [→ CLAUDE.md overview]" | README missing or vague. Option 1 is your guess, built from the README, package description and entry points, quoted in full. Option 2: "Let me write it". |
| commands · `Commands` | "Which command runs the {tests / dev server / build}? [→ CLAUDE.md, settings.json allow]" | Several candidates or none. One option per candidate, each description naming its source: "`make test` (Makefile:12) · runs pytest with coverage". Recommend the one CI runs. |
| test framework · `Test tool` | "Found {jest.config.js and vitest.config.ts}. Which is current? [→ .claude/rules/testing.md]" | Several configs. Descriptions give each one's test-file count and last-modified date. |
| conventions · `Conventions` | "Any conventions not visible in the code? I noticed: {e.g. services in src/services/, no default exports}. [→ CLAUDE.md]" | Always once. Option 1: "None beyond what you found". Option 2: "Yes, let me add some". List what you inferred, so the user only adds what's missing. |
| rules · `Rules` (multi) | "Which rule files should this project keep? [→ .claude/rules/]" | Each option's description gives what the rule covers and why it fits ("api-design: found 14 FastAPI routes in app/api/"). Pre-select those that apply; for the rest, say why not ("no HTTP API found"). |
| packages · `Packages` (multi) | "{n} workspace packages found. Which get their own CLAUDE.md? [→ <pkg>/CLAUDE.md]" | Monorepo. Descriptions give path, language and kind (app, service, library). Pre-select apps and services. |
| mcp · `MCP` (multi) | "Connect any tools via MCP? [→ .mcp.json]" | Offer from `mcp-catalog.json` only what has evidence: "GitHub: remote is github.com/…", "Postgres: DATABASE_URL in .env.example". Each description names the env var the user must set. |
| branch policy · `Branches` | "History shows {n of 30 commits on main, branches like feat/*}. How should I work? [→ git-workflow.md]" | No clear pattern. Options: feature branches + PR · commit to default branch · ask each time. |

## Saved preferences file

Write `~/.claude/cct-preferences.md` like this, so later setups can reuse it:

```markdown
# Claude Code kit — saved preferences
<!-- Read by the setup skill. Edit freely. -->
updated: 2026-01-31

- language: same as user
- verbosity: short summaries
- experience: experienced developer
- autonomy: ask before big or risky changes
- ask_before: adding dependencies, deleting files
- test_approach: write tests with every change
- commit_style: conventional commits
- model: default
- agent_models: kit defaults
- guard_level: standard
- format_on_edit: yes
- lint_on_edit: yes
- protect_lockfiles: yes
- statusline: yes
```
