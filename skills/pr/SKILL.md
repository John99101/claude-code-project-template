---
name: pr
description: Push the current branch and open a review-ready pull request (or GitLab merge request): size check, summary, honest test plan and notes for the reviewer
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
3. **Size.** Big PRs from agents are the ones reviewers abandon. Count changed lines with `python3 <hooks>/batch_check.py --size <base>...HEAD` (hooks: `.claude/hooks/`, `~/.claude/hooks/cct/` or `${CLAUDE_PLUGIN_ROOT}/hooks/`), which leaves out lockfiles, snapshots, generated and vendored files and `protected_paths`; without it, use `git diff --numstat <base>...HEAD` and leave those out yourself. The limit is `pr_max_lines` in `.claude/cct.json` (default 400), or 15 files. Over it: show the count, propose a split along the commit or folder boundaries you see (e.g. "1. the migration, 2. the API, 3. the UI"), and ask: **Split it** (create the branches and PRs in order, each based on the previous one) / **Open as one PR** / **Cancel**.
4. **Template.** Use the repo's PR template if there is one: `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/pull_request_template.md`, `PULL_REQUEST_TEMPLATE.md` (GitLab: `.gitlab/merge_request_templates/`). Fill its sections; don't drop any.
5. **Draft.**
   - Title in the style of `.claude/rules/git-workflow.md` and recent PRs (`gh pr list --state merged --limit 10`).
   - Summary: what changed and why, from the commits and the diff, a few bullets. Link issues the branch or commits name ("Closes #123" only when it really does).
   - Test plan: the checks from CLAUDE.md "Before you say a task is done". Tick only what was actually run in this session and passed; leave the rest unticked.
   - **For the reviewer**, always, short and honest:
     - *Assumptions:* decisions you made that the task or issue didn't settle.
     - *Not tested:* what no test or manual run covered.
     - *Review first:* the 1–3 riskiest places, as `file:line` with one line on why (security, data migration, concurrency, public API).
     - *Written with Claude Code;* name any part the user wrote or changed by hand if you know it.
   - **Spec:** if the branch implements a spec (`specs/…`, see `spec_dir` in `.claude/cct.json`, or one named in a commit), link it and repeat its acceptance criteria, ticked only when met and tested.
   - **Tidyings:** list `tidy:` commits separately under "Tidyings (no behaviour change)", so reviewers can skim them.
   - Breaking changes, migrations or config the reviewer must know about, if any.
   - Never include secrets, tokens or `.env` values.
6. **Confirm.** Show the title and description, the base and head branches, and whether it's a draft (`draft` in the arguments). Ask: **Open it** / **Change something** / **Cancel**.
7. **Open.** `git push -u origin <branch>` (never force-push without asking), then `gh pr create --base <base> --title … --body-file -` (add `--draft` if asked). GitLab remote: `glab mr create`. Without `gh` or `glab`, print the compare URL and the description to paste.
8. Show the link. Don't merge, and don't request reviewers unless the user named them.
