# Installing this kit — instructions for Claude

Follow this when a user asks Claude Code to install this kit (`John99101/claude-code-project-template`).

**Python command:** `python3` on macOS and Linux. On Windows, use whichever of `python3`, `py -3` or `python` works (try `<cmd> --version`). If none does, ask the user to install Python 3.8+ with the Python install manager from python.org.

## 1. Pick the install type

If it's unclear, ask with AskUserQuestion:

| Option | Best for | How |
|---|---|---|
| **Plugin** (recommended for personal use) | One person, all projects. Updates through `/plugin`. Skills are namespaced: `/cct:setup`, `/cct:commit`… | Step 2a |
| **This project only** (recommended for teams) | Config committed to the repo and shared with the team. Skills are `/setup`, `/commit`… | Step 2b |
| **All projects via script** | Like the plugin, but plain files in `~/.claude`. Its skills override a project's skills with the same name. | Step 2b with `--global` |

## 2a. Plugin

Tell the user to run this in Claude Code. Plugin installs need their confirmation in the `/plugin` panel:

```text
/plugin install cct --marketplace John99101/claude-code-project-template
```

On older Claude Code versions, use two steps: `/plugin marketplace add John99101/claude-code-project-template`, then `/plugin install cct@cct-kit`. After that, run `/reload-plugins` (or restart) and `/cct:setup`.

## 2b. Script

1. Clone the kit into a new, empty temp folder:
   `git clone --depth 1 https://github.com/John99101/claude-code-project-template <tmp>/kit`
   The repo is public, so no GitHub login is needed.
2. **Preview**, show the user, and get their OK:
   `python3 <tmp>/kit/install.py --project <dir> --dry-run` or `python3 <tmp>/kit/install.py --global --dry-run`
3. **Install** with the same command without `--dry-run`. Existing files are never overwritten; settings are merged with a backup.
4. **Run setup now.** Read the installed `.claude/skills/setup/SKILL.md` (device: `~/.claude/skills/setup/SKILL.md`) and follow it. Don't wait for a restart.
5. Tell the user to restart Claude Code afterwards so the new hooks, skills and MCP servers load.

## Repo created with "Use this template"

Run `python3 install.py --adopt --dry-run` in the repo, show the user, then `python3 install.py --adopt`. It turns the copy into a normal project install and removes the kit's own development files. Then the user restarts Claude Code and runs `/setup`.

## Updating and removing

- Plugin: update with `/plugin`; remove with `/plugin uninstall cct@cct-kit`.
- Script: `python3 <tmp>/kit/install.py --project <dir> --update` (or `--uninstall`, or `--global …`). Add `--dry-run` first to preview. Files the user changed are kept and listed.
