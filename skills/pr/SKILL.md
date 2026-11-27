---
name: pr
description: Push the current branch and open a pull request (or GitLab merge request) with a summary and test plan in this project's style
argument-hint: "[draft] [base branch] [anything the description should mention]"
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git remote:*), Bash(git fetch:*), Bash(git push:*), Bash(gh pr:*), Bash(gh repo view:*), Bash(glab mr:*)
---

## State

!`git status --short --branch`

!`git log --oneline -15`

!`git remote -v`

## Task

Arguments: $ARGUMENTS

1. **Branch.** If you're on the default branch, stop: offer to create a branch for these commits (named as in `.claude/rules/git-workflow.md`), and don't push the default branch. If there are uncommitted changes, ask whether to run `/commit` first or open the PR without them.
2. **Base.** Use the base branch from the arguments, else the default branch (`gh repo view --json defaultBranchRef`, or `origin/HEAD`). Run `git fetch` and list the commits and `git diff --stat` between the base and `HEAD`. If a PR for this branch already exists (`gh pr view`), show its link and ask whether to update its description instead.
3. **Template.** Use the repo's PR template if there is one: `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/pull_request_template.md`, `PULL_REQUEST_TEMPLATE.md` (GitLab: `.gitlab/merge_request_templates/`). Fill its sections; don't drop any.
4. **Draft.**
   - Title in the style of `.claude/rules/git-workflow.md` and recent PRs (`gh pr list --state merged --limit 10`).
   - Summary: what changed and why, from the commits and the diff, a few bullets. Link issues the branch or commits name ("Closes #123" only when it really does).
   - Test plan: the checks from CLAUDE.md "Before you say a task is done". Tick only what was actually run in this session and passed; leave the rest unticked.
   - Breaking changes, migrations or config the reviewer must know about, if any.
   - Never include secrets, tokens or `.env` values.
5. **Confirm.** Show the title and description, the base and head branches, and whether it's a draft (`draft` in the arguments). Ask: **Open it** / **Change something** / **Cancel**.
6. **Open.** `git push -u origin <branch>` (never force-push without asking), then `gh pr create --base <base> --title … --body-file -` (add `--draft` if asked). GitLab remote: `glab mr create`. Without `gh` or `glab`, print the compare URL and the description to paste.
7. Show the link. Don't merge, and don't request reviewers unless the user named them.
