#!/usr/bin/env python3
"""Merge the kit's settings.json into an existing Claude Code settings file without overwriting the user's values.

Usage: merge_settings.py SRC DST [--dry-run]

- permissions.allow / ask / deny: adds missing rules, keeps existing ones and their order
- hooks: adds hook groups whose commands aren't registered yet for that event
- any other key: set only if DST doesn't have it
DST is backed up to DST.bak-<timestamp> before it is changed.
"""
import json
import os
import shutil
import sys
import time


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)  # fail loudly on invalid JSON rather than clobbering it
    if not isinstance(data, dict):
        raise SystemExit(f"{path} is not a JSON object; not touching it.")
    return data


def hook_commands(groups):
    return {h.get("command") for g in groups for h in g.get("hooks", [])}


def merge(src, dst):
    changes = []
    for key, value in src.items():
        if key == "permissions" and isinstance(value, dict):
            perms = dst.setdefault("permissions", {})
            for kind, rules in value.items():
                if not isinstance(rules, list):
                    if kind not in perms:
                        perms[kind] = rules
                        changes.append(f"permissions.{kind}")
                    continue
                current = perms.setdefault(kind, [])
                for rule in rules:
                    if rule not in current:
                        current.append(rule)
                        changes.append(f"permissions.{kind} += {rule}")
        elif key == "hooks" and isinstance(value, dict):
            hooks = dst.setdefault("hooks", {})
            for event, groups in value.items():
                current = hooks.setdefault(event, [])
                for group in groups:
                    if hook_commands([group]) - hook_commands(current):
                        current.append(group)
                        changes.append(f"hooks.{event} += {group.get('matcher', '(all)')}")
        elif key not in dst:
            dst[key] = value
            changes.append(key)
    return changes


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) != 2:
        raise SystemExit(__doc__)
    src_path, dst_path = args
    src, dst = load(src_path), load(dst_path)
    existed = os.path.exists(dst_path)
    changes = merge(src, dst)

    if not changes:
        print(f"settings: {dst_path} already up to date")
        return
    print(f"settings: {'would update' if dry else 'updated'} {dst_path}")
    for c in changes:
        print(f"  - {c}")
    if dry:
        return
    if existed:
        backup = f"{dst_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(dst_path, backup)
        print(f"  backup: {backup}")
    os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(dst, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
