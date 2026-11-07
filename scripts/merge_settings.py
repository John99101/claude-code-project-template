#!/usr/bin/env python3
"""Merge the kit's settings into an existing Claude Code settings file, or remove them again.

Usage: merge_settings.py SRC DST [--dry-run]            add the kit's entries
       merge_settings.py SRC DST --remove [--dry-run]   remove the kit's hooks and status line

Adding:
- permissions.allow / ask / deny: adds missing rules, keeps existing ones and their order
- hooks: adds hook groups whose commands aren't registered yet for that event
- any other key (e.g. statusLine): set only if DST doesn't have it
Removing:
- hook groups made only of the kit's commands, and the kit's statusLine if unchanged
- permissions are left alone, since the user may rely on them
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


def remove(src, dst):
    changes = []
    kit = hook_commands([g for groups in (src.get("hooks") or {}).values() for g in groups])
    hooks = dst.get("hooks") or {}
    for event in list(hooks):
        keep = [g for g in hooks[event] if not (hook_commands([g]) and hook_commands([g]) <= kit)]
        if len(keep) != len(hooks[event]):
            changes.append(f"hooks.{event} -= {len(hooks[event]) - len(keep)} kit entr{'y' if len(hooks[event]) - len(keep) == 1 else 'ies'}")
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    if "hooks" in dst and not dst["hooks"]:
        del dst["hooks"]
    if "statusLine" in src and dst.get("statusLine") == src["statusLine"]:
        del dst["statusLine"]
        changes.append("statusLine removed")
    return changes


def main():
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2 or flags - {"--dry-run", "--remove"}:
        raise SystemExit(__doc__)
    dry, removing = "--dry-run" in flags, "--remove" in flags
    src_path, dst_path = args
    if removing and not os.path.exists(dst_path):
        print(f"settings: {dst_path} doesn't exist; nothing to remove")
        return
    src, dst = load(src_path), load(dst_path)
    existed = os.path.exists(dst_path)
    changes = remove(src, dst) if removing else merge(src, dst)

    if not changes:
        print(f"settings: {dst_path} already up to date" if not removing else f"settings: no kit entries in {dst_path}")
        return
    print(f"settings: {'would update' if dry else 'updated'} {dst_path}")
    for c in changes:
        print(f"  - {c}")
    if removing:
        print("  (permission rules were left in place)")
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
