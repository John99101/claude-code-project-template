# Installing this kit — instructions for Claude

Follow this when a user asks Claude Code to install this kit (`John99101/claude-code-project-template`) into a project or onto their device.

1. **Pick the target.** If it's unclear, ask with AskUserQuestion:
   - *This project only* (recommended inside a project): config lives in the repo and is shared with the team.
   - *All projects on this device*: installs into `~/.claude`; each project gets set up the first time you open it.
2. **Get the kit** into a new, empty temp directory:
   `git clone --depth 1 https://github.com/John99101/claude-code-project-template <tmp>/kit`
   The repo is public, so no GitHub login is needed.
3. **Preview**, show the user, and get their OK:
   `bash <tmp>/kit/install.sh --project <dir> --dry-run` or `bash <tmp>/kit/install.sh --global --dry-run`
4. **Install** with the same command without `--dry-run`. Existing files are never overwritten; settings are merged with a backup.
5. **Run setup now.** Read the installed `.claude/skills/setup/SKILL.md` (device: `~/.claude/skills/setup/SKILL.md`) and follow it. Don't wait for a restart.
6. Tell the user to restart Claude Code afterwards so the new hooks, commands and MCP servers load.

To remove the kit, run `bash <tmp>/kit/install.sh --project <dir> --uninstall` (or `--global --uninstall`). Add `--dry-run` first to preview. Files the user changed are kept and listed.
