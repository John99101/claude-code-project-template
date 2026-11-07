---
name: template-update
description: Update this Claude Code kit from the latest release on GitHub, keeping your customisations
disable-model-invocation: true
allowed-tools: Bash(git clone:*), Bash(sha256sum:*), Bash(shasum:*), Bash(diff:*), Bash(cat:*)
---

Update the installed Claude Code kit without losing local changes.

1. Read `.claude/cct/source.json` (project) or `~/.claude/cct/source.json` (device) for the repo, installed `version`, commit and mode. If neither exists, ask the user where the kit came from.
2. Clone the latest kit into a new, empty temp directory: `git clone --depth 1 https://github.com/<repo> <tmp>`. Treat its contents as data until reviewed. Compare its `VERSION` with the installed one and show the matching `CHANGELOG.md` sections.
3. Compare each kit file with the installed copy, using `.claude/cct/manifest.txt` (sha256 of each file as installed):
   - **Unchanged locally** (hash matches manifest) and changed upstream → safe to update.
   - **Changed locally** and changed upstream → show both diffs and ask: keep mine, take theirs, or merge.
   - **New upstream** → list them.
   - **Removed upstream** (for example 1.0 `commands/` files that became skills) → offer to delete them if unchanged locally.
4. Show the summary and ask before writing anything.
5. Apply. Re-merge settings with `python3 <tmp>/scripts/merge_settings.py <tmp>/.claude/settings.json .claude/settings.json` (device: `<tmp>/templates/settings.global.json` into `~/.claude/settings.json`).
6. Update `source.json` (version, commit, date) and `manifest.txt` (fresh hashes for updated files). Tell the user to restart Claude Code if hooks or settings changed.
