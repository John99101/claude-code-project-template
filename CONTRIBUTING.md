# Contributing

Thanks for improving the kit. Small, focused pull requests are easiest to review.

## Layout

| Path | Copied into projects? | Notes |
|---|---|---|
| `.claude/`, `CLAUDE.md`, `.mcp.json`, `CLAUDE.local.md.example` | Yes | What users get. Keep it generic: no project-specific content. |
| `templates/` | Device installs only | Device-wide `CLAUDE.md` and settings. |
| `install.sh`, `scripts/` | No | Installer and settings merger. |
| `tests/`, `.github/`, `docs/` | No | Tests, CI and documentation. |

## Development

```bash
python3 tests/test_kit.py -v        # all tests; your real ~/.claude is never touched
shellcheck -S warning install.sh    # lint the installer
bash install.sh --project /tmp/demo --dry-run
```

## Guidelines

- **Hooks** must use only the Python standard library, exit 0, and never crash on bad input. Add a test case for every new guard pattern, including one that should *not* match.
- **The installer** must never overwrite a user's file. It must stay idempotent and work on Linux and macOS (bash 3.2).
- **Skills, commands and agents** need frontmatter (`name` and `description`; commands need `description`). Write descriptions that say *when* to use them, since that's how Claude decides.
- **Setup questions** go in `.claude/skills/project-setup/questions.md`, with the recommended option first.
- **MCP catalog** entries need a `docs` link and must use `${ENV_VAR}` for every credential.
- Add a line to `CHANGELOG.md` under **Unreleased**.
