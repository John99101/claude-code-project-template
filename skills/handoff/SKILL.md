---
name: handoff
description: Save where the current task stands to .claude-handoff.md so a later session can pick it up, or resume from that note
argument-hint: "[resume]"
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*)
---

Arguments: $ARGUMENTS

## Write a handoff (no arguments)

Write `.claude-handoff.md` so that a new session can continue without this conversation. Keep it under ~60 lines and factual. Overwrite an older note (say so if it was about a different task).

```markdown
# Handoff — <task in a few words>
<date and time> · branch `<branch>` · last commit `<short hash> <subject>`

## Goal
What the user asked for, and what "done" means.

## Done
- What's finished and verified (name the checks that passed).

## In progress
- What's half-done, with file paths and line numbers. Uncommitted changes: list the files from `git status`.

## Decisions
- Choices made and why, including approaches that were tried and dropped.

## Open questions
- What's waiting for the user or someone else.

## Next steps
1. The very next thing to do, concrete enough to start without re-reading the code.

## How to verify
- Commands to run, and what they should show.
```

Never put secrets, tokens or `.env` values in it. `.claude-handoff.md` is personal and stays out of git: if `.gitignore` doesn't cover it, add the line `.claude-handoff.md`. Then tell the user it's saved and that the next session will show a notice; they continue with `/handoff resume`.

## Resume (`resume`)

1. Read `.claude-handoff.md`. If it's missing, say so and stop.
2. Compare it with now: `git status`, `git log` since its commit, the current branch. Point out anything that changed since (new commits, a different branch, files no longer modified).
3. Summarise in a few lines where things stand and propose the next step from the note. Wait for the user's OK before editing files.
4. Once the work is back on track, offer to delete the note so it doesn't come up again.
