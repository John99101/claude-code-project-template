#!/usr/bin/env python3
"""Merge the kit's settings into an existing Claude Code settings file, or remove them again.

Usage: merge_settings.py SRC DST [--dry-run]            add the kit's entries from SRC (a JSON file)
       merge_settings.py SRC DST --remove [--dry-run]   remove the kit's hooks and status line

Adding:
- permissions.allow / ask / deny: adds missing rules, keeps existing ones and their order
- hooks: the kit's hooks (recognised by script name, in any format the kit ever wrote) are replaced with the
  current ones; the user's own hooks are left alone
- statusLine: set if missing, or replaced if it's the kit's; a status line of the user's own is kept
- any other key: set only if DST doesn't have it
Removing: the kit's hooks and status line. Permission rules are left alone, since the user may rely on them.
DST is backed up to DST.bak-<timestamp> before it is changed.
"""
import copy
import json
import os
import shutil
import sys
import time

KIT_SCRIPTS = ("session_start.py", "guard_bash.py", "protect_files.py", "format_file.py", "statusline.py")
KIT_DIRS = (".claude/hooks/", "hooks/cct/", "statusline/")


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)  # fail loudly on invalid JSON rather than clobbering it
    if not isinstance(data, dict):
        raise SystemExit(f"{path} is not a JSON object; not touching it.")
    return data


def _text(entry):
    return (str(entry.get("command", "")) + " " + " ".join(map(str, entry.get("args", [])))).replace("\\", "/")


def is_kit_entry(entry):
    text = _text(entry)
    return any(f"/{name}" in text for name in KIT_SCRIPTS) and any(d in text for d in KIT_DIRS)


def is_kit_group(group):
    hooks = group.get("hooks", [])
    return bool(hooks) and all(is_kit_entry(h) for h in hooks)


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
            for event in sorted(set(hooks) | set(value)):
                before = hooks.get(event, [])
                after = [g for g in before if not is_kit_group(g)] + copy.deepcopy(value.get(event, []))
                if after != before:
                    changes.append(f"hooks.{event}: kit hooks updated")
                if after:
                    hooks[event] = after
                else:
                    hooks.pop(event, None)
        elif key == "statusLine":
            current = dst.get("statusLine")
            if current is None or (is_kit_entry(current) and current != value):
                dst["statusLine"] = value
                changes.append("statusLine")
        elif key not in dst:
            dst[key] = value
            changes.append(key)
    return changes


def remove_entries(dst):
    changes = []
    hooks = dst.get("hooks") or {}
    for event in list(hooks):
        keep = [g for g in hooks[event] if not is_kit_group(g)]
        if len(keep) != len(hooks[event]):
            changes.append(f"hooks.{event}: kit hooks removed")
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    if "hooks" in dst and not dst["hooks"]:
        del dst["hooks"]
    if dst.get("statusLine") and is_kit_entry(dst["statusLine"]):
        del dst["statusLine"]
        changes.append("statusLine removed")
    return changes


def apply(src, dst_path, dry=False, remove=False):
    """Merge the settings dict `src` into the file at dst_path, or remove the kit's entries. Returns the changes."""
    removing = remove
    if removing and not os.path.exists(dst_path):
        print(f"settings: {dst_path} doesn't exist; nothing to remove")
        return []
    dst = load(dst_path)
    existed = os.path.exists(dst_path)
    changes = remove_entries(dst) if removing else merge(src, dst)
    if not changes:
        print(f"settings: no kit entries in {dst_path}" if removing else f"settings: {dst_path} already up to date")
        return []
    print(f"settings: {'would update' if dry else 'updated'} {dst_path}")
    for c in changes:
        print(f"  - {c}")
    if removing:
        print("  (permission rules were left in place)")
    if dry:
        return changes
    write(dst_path, dst, backup=existed)
    return changes


def write(dst_path, data, backup=True):
    """Write a settings file, keeping a timestamped backup of the previous version."""
    if backup and os.path.exists(dst_path):
        backup_path = f"{dst_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(dst_path, backup_path)
        print(f"  backup: {backup_path}")
    os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2 or flags - {"--dry-run", "--remove"}:
        raise SystemExit(__doc__)
    apply(load(args[0]), args[1], dry="--dry-run" in flags, remove="--remove" in flags)


if __name__ == "__main__":
    main()
