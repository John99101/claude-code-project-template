---
name: learn
description: Turn learning mode on or off - Claude teaches while it codes (explains concepts, lets you predict bugs first, leaves small parts for you to write)
argument-hint: "on | off | status [here | everywhere]"
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Learning mode exists because, in Anthropic's 2026 study, developers who let AI write the code learned noticeably less (50% vs 67% on a follow-up quiz, with debugging hit hardest), while those who asked conceptual questions kept their skills. It costs a little more per turn, since there's more explaining.

The rules are in [learning-mode.md](learning-mode.md). They're stored between markers in a `CLAUDE` file:
- **here** (default): `CLAUDE.local.md` in this project (personal and gitignored, so teammates aren't affected);
- **everywhere**: `~/.claude/CLAUDE.md`, for all projects.

## What to do

- **`on`**: copy the contents of learning-mode.md into the chosen file, between the lines `<!-- cct:learning -->` and `<!-- /cct:learning -->` (replace an existing block, never duplicate it). Create `CLAUDE.local.md` if needed and make sure `.gitignore` covers it. Then follow the rules from this moment on, and say they also apply to every new session. Mention that Claude Code's built-in **Explanatory** or **Learning** output style (`/config`) works well alongside it.
- **`off`**: remove the block from both files if present and confirm. Go back to working normally.
- **`status`** or no argument: say whether the block is present, and where.
