# Contributing

Thanks for improving the kit. Small, focused pull requests are easiest to review.

## Layout

The repository uses Claude Code's standard plugin layout. None of it lives in `.claude/`: the installer copies files into a project's `.claude/` (or `~/.claude/`) only when someone installs the kit.

| Path | Installed to (project / device) | Notes |
|---|---|---|
| `skills/`, `agents/` | `.claude/skills/`, `.claude/agents/` · `~/.claude/…` | The plugin loads them from here directly. |
| `hooks/*.py` | `.claude/hooks/` · `~/.claude/hooks/cct/` | `hooks/hooks.json` registers them for the plugin, and the installer builds settings entries from the same file. |
| `rules/` | `.claude/rules/` · `~/.claude/rules/` | Plugins can't ship rules, so `/cct:setup` copies them from here. |
| `rule-packs/`, `templates/CLAUDE.package.md` | `.claude/cct/` · `~/.claude/cct/` | Language rules and the monorepo package template. Setup installs what a project needs. |
| `templates/` | various | `CLAUDE.project.md` → `CLAUDE.md`, `CLAUDE.user.md` → `~/.claude/CLAUDE.md`, base settings, `cct.json`, `mcp.json` → `.mcp.json`, examples. |
| `.claude-plugin/` | — | Plugin manifest, marketplace entry and icon. |
| `install.py` (+ `install.sh`, `install.ps1` launchers), `scripts/`, `VERSION` | — | Installer, settings merger, status line helper, release and catalog tooling. |
| `tests/`, `.github/`, `docs/` | — | Tests, sample projects, CI and documentation. |

## Development

```bash
python3 tests/test_kit.py -v              # fast tests; your real ~/.claude is never touched
python3 install.py --project /tmp/demo --dry-run
claude plugin validate .                  # check the plugin and marketplace manifests
claude --plugin-dir .                     # try the plugin in a session without installing it
python3 scripts/check_mcp_catalog.py      # check every MCP catalog entry still exists
python3 tests/eval_setup.py python-app    # run /setup for real on a sample project (uses your Claude login)
shellcheck install.sh                     # lint the macOS/Linux launcher
```

## Guidelines

- **Cross-platform:** everything must work on Linux, macOS and Windows. Use `pathlib`/`os.path`, never hard-coded `/`, in Python. CI runs the tests on all three.
- **Hooks** must use only the Python standard library (3.8+), exit 0 (or 2 to send a message to Claude), and never crash on bad input. Add a test case for every new guard pattern, including one that should *not* match. New hook scripts go in `hooks/hooks.json` and in `KIT_SCRIPTS` in `scripts/merge_settings.py`.
- **The installer** must never overwrite a user's file on install, stay idempotent, and keep everything it installs removable with `--uninstall` and updatable with `--update`.
- **Skills and agents** need frontmatter with `name` and `description`; a skill's `name` must match its folder. Write descriptions that say *when* to use them, since that's how Claude decides. Workflow skills the user triggers (like `/commit`) get `disable-model-invocation: true`.
- **Rule packs** need a `paths:` frontmatter, a "Project specifics" section with `{{placeholders}}`, and an "Always" section.
- **Setup changes:** run the setup eval on at least one sample project. Add a sample to `tests/fixtures/` (plus its entry in `expectations.json`) when you add support for a new kind of project.
- **Setup questions** go in `skills/setup/questions.md`, with the recommended option first.
- **MCP catalog** entries need a `docs` link and must use `${ENV_VAR}` for every credential. Run the catalog check.
- Don't add a `CLAUDE.md` at the repo root: the plugin validator warns about it, because plugins don't load one.
- Add a line to `CHANGELOG.md` under **Unreleased**.

## Releasing

1. Move the **Unreleased** entries in `CHANGELOG.md` under a new `## [x.y.z] - date` heading and add its link at the bottom.
2. Set `VERSION` and the `version` in `.claude-plugin/plugin.json` to `x.y.z` (a test checks they match), and commit. Plugin users only get the update once `plugin.json`'s version changes.
3. `git tag -a vx.y.z -m vx.y.z && git push origin vx.y.z`

The release workflow checks the tag matches `VERSION`, runs the tests, and publishes the GitHub release with that changelog section as notes.
