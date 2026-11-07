# Contributing

Thanks for improving the kit. Small, focused pull requests are easiest to review.

## Layout

| Path | Copied into projects? | Notes |
|---|---|---|
| `.claude/`, `CLAUDE.md`, `.mcp.json`, `CLAUDE.local.md.example` | Yes | What users get. Keep it generic: no project-specific content. |
| `rule-packs/`, `templates/CLAUDE.package.md` | Yes, into `.claude/cct/` | Language rules and the monorepo package template. Setup copies what a project needs. |
| `templates/CLAUDE.user.md`, `templates/settings.global.json` | Device installs only | Device-wide `CLAUDE.md` and settings. |
| `install.sh`, `scripts/`, `VERSION` | No | Installer, settings merger, release and catalog tooling. |
| `tests/`, `.github/`, `docs/` | No | Tests, sample projects, CI and documentation. |

## Development

```bash
python3 tests/test_kit.py -v              # fast tests; your real ~/.claude is never touched
shellcheck -S warning install.sh          # lint the installer
python3 scripts/check_mcp_catalog.py      # check every MCP catalog entry still exists
python3 tests/eval_setup.py python-app    # run /setup for real on a sample project (uses API credits)
bash install.sh --project /tmp/demo --dry-run
```

## Guidelines

- **Hooks** must use only the Python standard library, exit 0 (or 2 to send a message to Claude), and never crash on bad input. Add a test case for every new guard pattern, including one that should *not* match.
- **The installer** must never overwrite a user's file. It must stay idempotent, work on Linux and macOS (bash 3.2), and anything it installs must be removable with `--uninstall`.
- **Skills and agents** need frontmatter with `name` and `description`; a skill's `name` must match its folder. Write descriptions that say *when* to use them, since that's how Claude decides. Workflow skills the user triggers (like `/commit`) get `disable-model-invocation: true`.
- **Rule packs** need a `paths:` frontmatter, a "Project specifics" section with `{{placeholders}}`, and an "Always" section.
- **Setup changes**: run the setup eval on at least one sample project. Add a sample to `tests/fixtures/` (plus its entry in `expectations.json`) when you add support for a new kind of project.
- **Setup questions** go in `.claude/skills/setup/questions.md`, with the recommended option first.
- **MCP catalog** entries need a `docs` link and must use `${ENV_VAR}` for every credential. Run the catalog check.
- Add a line to `CHANGELOG.md` under **Unreleased**.

## Releasing

1. Move the **Unreleased** entries in `CHANGELOG.md` under a new `## [x.y.z] - date` heading and add its link at the bottom.
2. Set `VERSION` to `x.y.z` and commit.
3. `git tag -a vx.y.z -m vx.y.z && git push origin vx.y.z`

The release workflow checks the tag matches `VERSION`, runs the tests, and publishes the GitHub release with that changelog section as notes.
