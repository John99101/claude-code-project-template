#!/usr/bin/env python3
"""Turn the kit's status line on (or off) for plugin installs.

Plugins can't set a status line themselves, so this copies the status line script into the plugin's data folder,
which survives plugin updates, and points ~/.claude/settings.json at it. The plugin's SessionStart hook keeps
the copy current after updates. A status line of your own is never replaced unless you pass --force.

Usage (run by /cct:setup):  python3 enable_statusline.py <plugin-data-dir> [--force] [--disable] [--dry-run]
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kitlib  # noqa: E402
import merge_settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_dir", help="the plugin's data folder (${CLAUDE_PLUGIN_DATA})")
    parser.add_argument("--force", action="store_true", help="replace a status line that isn't the kit's")
    parser.add_argument("--disable", action="store_true", help="remove the kit's status line")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--settings", default=str(Path.home() / ".claude" / "settings.json"), help=argparse.SUPPRESS)
    args = parser.parse_args()

    if "${" in args.data_dir:
        sys.exit("Pass the real plugin data folder. This only works when run from the cct plugin.")
    settings = merge_settings.load(args.settings)
    target = Path(args.data_dir) / "statusline"

    if args.disable:
        current = settings.get("statusLine")
        if current and merge_settings.is_kit_entry(current):
            if not args.dry_run:
                del settings["statusLine"]
                merge_settings.write(args.settings, settings)
            print("Status line removed from settings.")
        else:
            print("No kit status line was set; nothing changed.")
        return

    current = settings.get("statusLine")
    if current and not merge_settings.is_kit_entry(current) and not args.force:
        print("You already have your own status line, so it was left alone. Run with --force to replace it.")
        sys.exit(3)

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)
        for name in ("statusline.py", "cct_config.py"):
            shutil.copy2(kitlib.KIT / "hooks" / name, target / name)
    command = kitlib.statusline_command(kitlib.python_command(), kitlib.fwd(target / "statusline.py"))
    if settings.get("statusLine") == command:
        print("Status line already on.")
        return
    settings["statusLine"] = command
    if not args.dry_run:
        merge_settings.write(args.settings, settings)
    print(f"Status line {'would be ' if args.dry_run else ''}on: {command['command']}")
    print("It appears after the next restart of Claude Code (or the next session).")


if __name__ == "__main__":
    main()
