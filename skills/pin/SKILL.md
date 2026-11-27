---
name: pin
description: Pin a constraint for the current task so it survives compaction and new sessions; path pins are enforced by the file guard
argument-hint: "<constraint> | only edit: <globs> | never edit: <globs> | list | clear | remove <n>"
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Pins live in `.claude-pins.md` in the project root (personal, gitignored). The kit puts them back into your context at every session start and after every compaction, and its file guard **blocks** edits that break a path pin. Pins are for the current task; `/pin clear` ends them.

## What to do

- **No arguments or `list`:** show the pins, numbered. None: say so, with an example.
- **`clear`:** delete `.claude-pins.md` and confirm.
- **`remove <n>`:** remove that pin and show the rest.
- **Anything else is a new pin.** Turn it into one line and append it under the heading `# Pinned for this task` (create the file if needed):
  - Paths the user must not have touched: `- never edit: src/api/public/**, migrations/`
  - The only area to work in: `- only edit: src/billing/**, tests/billing/**`
  - Anything else, in the user's words, as a short instruction: `- Don't change the public API.`
  Use project-relative globs; a folder is `dir/`. If one request holds several constraints, write one line each.
  - **"tests are the spec"** (test-first work): find the project's test locations (`tests/`, `__tests__/`, `*_test.go`, `*.test.ts`…) and pin them read-only as `- never edit: <those globs>`, plus the reminder `- The tests define the behaviour: change the code, not the tests.`
- If `.gitignore` doesn't cover `.claude-pins.md`, add that line.

Then show the pins and confirm in one line that they're in force. From now on, follow every pin until it's removed. If the task can't be done without breaking one, stop and ask the user instead of working around it.
