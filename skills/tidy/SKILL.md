---
name: tidy
description: Propose small, behaviour-preserving cleanups for the code you just changed, and commit each separately from feature work (Kent Beck's "Tidy First?")
argument-hint: "[path | last change]"
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*), Bash(git grep:*), Bash(git restore:*)
---

Scope: $ARGUMENTS (default: the files changed in the working tree, or in the last commit if the tree is clean)

AI-assisted code tends to grow by copy-paste rather than refactoring (GitClear measured refactored lines falling from 24% to under 10% of changes while copy-pasted lines rose). Tidyings are the small fix: tiny structural improvements, each in its own commit, kept apart from behaviour changes so reviewers can skim them.

## 1. Find candidates

Look only at the scoped files and their direct neighbours, never the whole repo. Good tidyings:
- duplicated code that already exists elsewhere (`git grep` for the same logic or name) → reuse or extract one helper;
- unclear names; magic numbers → named constants;
- guard clauses instead of deep nesting; dead code and unused imports;
- one function doing two things → split;
- consistent ordering and grouping of related code.

## 2. Propose

List 3–7 tidyings, each with: what, where (`file:line`), why it helps, and risk (low / medium). Ask which to do (multi-select). Skip anything that changes behaviour; that's a feature or a fix, not a tidying.

## 3. Apply one at a time

For each chosen tidying:
1. Make the change, nothing else.
2. Run the project's tests (CLAUDE.md "Before you say a task is done"). If they fail, undo this tidying only (`git restore` the files) and report why.
3. Commit it alone, as `tidy: <what>` (or the project's style for refactors), never mixed with feature changes. If there are uncommitted feature changes, ask first whether to commit those before tidying.

End with the list of tidy commits. `/pr` lists them under "Tidyings (no behaviour change)".
