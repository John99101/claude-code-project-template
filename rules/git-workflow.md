# Git workflow

<!-- cct: /setup fills in the specifics from git history and your answers. -->

## Project specifics
- Default branch: {{DEFAULT_BRANCH}}
- Branch names: {{BRANCH_NAMING}}
- Commit messages: {{COMMIT_STYLE}}
- Pull requests: {{PR_POLICY}}

## Always
- Commit only when asked. Never push unless asked.
- Never commit to the default branch directly if it's protected; create a branch.
- One logical change per commit. Don't mix refactors with behaviour changes.
- Never rewrite published history (force-push, rebase of pushed branches) without asking.
- Check `git status` before committing; never commit secrets, build output or local config.
