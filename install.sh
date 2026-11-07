#!/usr/bin/env bash
# Installs the Claude Code kit into a project (--project) or onto this device (--global), or removes it (--uninstall).
# Never overwrites existing files. Run /setup in Claude Code afterwards to finish.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="John99101/claude-code-project-template"
VERSION="$(cat "$SRC/VERSION" 2>/dev/null || echo unknown)"
MODE=""
ACTION=install
TARGET="."
DRY=0

usage() {
  cat <<EOF
Claude Code kit $VERSION

Usage: install.sh --project [DIR] | --global   [--dry-run] [--uninstall]
       install.sh --adopt [--dry-run]

  --project [DIR]  Install into one project (default: current directory).
                   Shared with your team through git.
  --global         Install for every project on this device (~/.claude).
  --dry-run        Show what would happen without changing anything.
  --uninstall      Remove the kit. Files you changed are kept and listed.
  --adopt          Run inside a repo created with GitHub's "Use this template": turns the copy into a
                   normal project install and removes the kit's own development files (tests, CI, docs).

Existing files are never overwritten. After installing, open Claude Code and run /setup.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)
      MODE=project
      if [ $# -gt 1 ] && [ "${2#-}" = "$2" ]; then TARGET="$2"; shift; fi ;;
    --global) MODE=global ;;
    --dry-run) DRY=1 ;;
    --uninstall) ACTION=uninstall ;;
    --adopt) ACTION=adopt; MODE=project ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

if [ -z "$MODE" ]; then usage >&2; exit 1; fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (the hooks use it). Install it and run again." >&2
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  SHA256=(sha256sum)
else
  SHA256=(shasum -a 256)  # macOS
fi

COPIED=()
SKIPPED=()

copy_file() { # src dst
  if [ -e "$2" ]; then
    SKIPPED+=("$2")
    return 0
  fi
  COPIED+=("$2")
  if [ "$DRY" -eq 0 ]; then
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
  fi
}

copy_tree() { # srcdir dstdir
  local f
  while IFS= read -r -d '' f; do
    copy_file "$f" "$2/${f#"$1"/}"
  done < <(find "$1" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' -print0)
}

put_file() { # src dst, kit-owned file: always (re)written
  if [ "$DRY" -eq 0 ]; then
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
  fi
  echo "  template saved: $2"
}

settings() { # src dst [--remove]
  local args=("$1" "$2")
  if [ $# -gt 2 ]; then args+=("$3"); fi
  if [ "$DRY" -eq 1 ]; then args+=(--dry-run); fi
  python3 "$SRC/scripts/merge_settings.py" "${args[@]}"
}

write_marker() { # path
  if [ "$DRY" -eq 0 ]; then cp "$SRC/.claude/cct-pending" "$1"; fi
}

record_source() { # base_dir cct_dir
  local base="$1" dir="$2" commit f
  if [ "$DRY" -eq 1 ]; then return 0; fi
  commit="${KIT_COMMIT:-$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)}"
  mkdir -p "$dir"
  cat > "$dir/source.json" <<EOF
{
  "repo": "$REPO",
  "version": "$VERSION",
  "commit": "$commit",
  "mode": "$MODE",
  "installed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
  touch "$dir/manifest.txt"  # append only: keeps entries from earlier installs
  for f in "${COPIED[@]+"${COPIED[@]}"}"; do
    (cd "$base" && "${SHA256[@]}" "${f#"$base"/}") >> "$dir/manifest.txt"
  done
}

ensure_gitignore() { # project_dir
  local gi="$1/.gitignore" line added=0
  for line in ".claude/settings.local.json" "CLAUDE.local.md" ".env" ".env.*" "!.env.example"; do
    if ! grep -qxF -- "$line" "$gi" 2>/dev/null; then
      if [ "$DRY" -eq 0 ]; then
        if [ "$added" -eq 0 ]; then printf '\n# Claude Code kit\n' >> "$gi"; fi
        echo "$line" >> "$gi"
      fi
      added=1
      echo "  .gitignore += $line"
    fi
  done
}

uninstall() { # base cct_dir settings_src settings_dst marker kit_dirs...
  local base="$1" cct="$2" src="$3" dst="$4" marker="$5" hash rel f cur d
  shift 5
  if [ ! -f "$cct/manifest.txt" ]; then
    echo "No kit install found here ($cct/manifest.txt is missing)." >&2
    exit 1
  fi
  local removed=() kept=()
  while read -r hash rel; do
    [ -n "$rel" ] || continue
    f="$base/$rel"
    [ -e "$f" ] || continue
    cur="$("${SHA256[@]}" "$f" | cut -d' ' -f1)"
    if [ "$cur" = "$hash" ]; then
      removed+=("$f")
      if [ "$DRY" -eq 0 ]; then rm -f "$f"; fi
    else
      kept+=("$f")
    fi
  done < "$cct/manifest.txt"

  settings "$src" "$dst" --remove
  if [ "$DRY" -eq 0 ]; then
    rm -f "$marker" "$cct/source.json" "$cct/manifest.txt" "$cct/CLAUDE.template.md" "$cct/CLAUDE.user.template.md"
    for d in "$@"; do
      if [ -d "$d" ]; then
        find "$d" -type d -name __pycache__ -prune -exec rm -rf {} +  # left behind by running the hooks
        find "$d" -depth -type d -empty -delete
      fi
    done
  fi

  echo
  if [ "$DRY" -eq 1 ]; then echo "Would remove ${#removed[@]} file(s)."; else echo "Removed ${#removed[@]} file(s)."; fi
  if [ "${#kept[@]}" -gt 0 ]; then
    echo "Kept ${#kept[@]} file(s) you changed (delete them yourself if you don't need them):"
    for f in "${kept[@]}"; do echo "  ~ $f"; done
  fi
  if [ "$MODE" = project ]; then
    echo "The kit's lines in .gitignore were left in place."
  fi
}

# Kit development files that a "Use this template" copy doesn't need.
DEV_FILES=(install.sh scripts templates rule-packs plugin .claude-plugin
  tests/test_kit.py tests/eval_setup.py tests/fixtures
  .github/workflows/ci.yml .github/workflows/eval-setup.yml .github/workflows/mcp-catalog.yml
  .github/workflows/release.yml .github/ISSUE_TEMPLATE .github/pull_request_template.md
  docs/GUIDE.md CHANGELOG.md CONTRIBUTING.md VERSION INSTALL.md LICENSE README.md)

adopt() { # turn a template copy (the kit folder itself) into a normal project install
  local T="$SRC" CCT="$SRC/.claude/cct" f p
  if git -C "$T" config --get remote.origin.url 2>/dev/null | grep -q "$REPO"; then
    echo "This is the kit's own repository. --adopt is for repos created from it with \"Use this template\"." >&2
    exit 1
  fi
  echo "Claude Code kit $VERSION: adopting template copy in $T$( [ "$DRY" -eq 1 ] && echo ' (dry run)')"
  copy_tree "$SRC/rule-packs" "$CCT/rule-packs"
  copy_file "$SRC/templates/CLAUDE.package.md" "$CCT/CLAUDE.package.md"
  # The kit files are already in place; record them so /template-update and --uninstall work.
  while IFS= read -r -d '' f; do COPIED+=("$f"); done < <(find "$T/.claude/rules" "$T/.claude/skills" \
    "$T/.claude/agents" "$T/.claude/hooks" -type f ! -path '*/__pycache__/*' -print0)
  for f in .claude/cct.json CLAUDE.md .mcp.json CLAUDE.local.md.example .claude/settings.local.json.example; do
    if [ -e "$T/$f" ]; then COPIED+=("$T/$f"); fi
  done
  ensure_gitignore "$T"
  for p in "${DEV_FILES[@]}"; do
    if [ -e "$T/$p" ]; then
      echo "  - remove $p"
      if [ "$DRY" -eq 0 ]; then rm -rf "${T:?}/$p"; fi
    fi
  done
  if [ "$DRY" -eq 1 ]; then
    echo "  + new README.md stub"
    echo
    echo "Would record ${#COPIED[@]} kit file(s) and remove the kit's development files listed above."
    return 0
  fi
  printf '# %s\n\nConfigured for Claude Code with the [Claude Code Project Kit](https://github.com/%s).\n' \
    "$(basename "$T")" "$REPO" > "$T/README.md"
  for p in tests docs .github/workflows .github; do
    if [ -d "$T/$p" ]; then find "$T/$p" -depth -type d -empty -delete; fi
  done
  if [ ! -e "$T/.claude/cct-pending" ]; then
    echo "Setup for this Claude Code kit is not finished. Run /setup in Claude Code." > "$T/.claude/cct-pending"
  fi
  KIT_COMMIT="template-copy" record_source "$T" "$CCT"
  echo
  echo "Recorded ${#COPIED[@]} kit file(s) and removed the kit's development files."
  echo "Note: the kit's LICENSE was removed too. Add your own project's license if it needs one."
}

if [ "$ACTION" = adopt ]; then
  adopt
  exit 0
fi

if [ "$MODE" = project ]; then
  T="$(cd "$TARGET" && pwd)"
  if [ "$T" = "$SRC" ]; then
    echo "Target is the kit itself. Pick a project directory, or use --adopt in a \"Use this template\" copy." >&2
    exit 1
  fi
  CCT="$T/.claude/cct"
  if [ "$ACTION" = uninstall ]; then
    echo "Claude Code kit: uninstalling from $T$( [ "$DRY" -eq 1 ] && echo ' (dry run)')"
    uninstall "$T" "$CCT" "$SRC/.claude/settings.json" "$T/.claude/settings.json" "$T/.claude/cct-pending" \
      "$T/.claude/rules" "$T/.claude/skills" "$T/.claude/agents" "$T/.claude/hooks" "$CCT"
    exit 0
  fi
else
  C="$HOME/.claude"
  CCT="$C/cct"
  if [ "$ACTION" = uninstall ]; then
    echo "Claude Code kit: uninstalling from $C$( [ "$DRY" -eq 1 ] && echo ' (dry run)')"
    uninstall "$C" "$CCT" "$SRC/templates/settings.global.json" "$C/settings.json" "$C/cct-pending" \
      "$C/rules" "$C/skills" "$C/agents" "$C/hooks/cct" "$CCT"
    exit 0
  fi
fi

if [ "$DRY" -eq 1 ]; then
  echo "Claude Code kit $VERSION: dry run ($MODE mode). Nothing will be changed."
else
  echo "Claude Code kit $VERSION: installing ($MODE mode)"
fi

if [ "$MODE" = project ]; then
  for d in rules skills agents hooks; do
    copy_tree "$SRC/.claude/$d" "$T/.claude/$d"
  done
  copy_tree "$SRC/rule-packs" "$CCT/rule-packs"
  copy_file "$SRC/templates/CLAUDE.package.md" "$CCT/CLAUDE.package.md"
  copy_file "$SRC/.claude/cct.json" "$T/.claude/cct.json"
  copy_file "$SRC/.claude/settings.local.json.example" "$T/.claude/settings.local.json.example"
  copy_file "$SRC/CLAUDE.local.md.example" "$T/CLAUDE.local.md.example"
  copy_file "$SRC/.mcp.json" "$T/.mcp.json"
  if [ -e "$T/CLAUDE.md" ]; then
    put_file "$SRC/CLAUDE.md" "$CCT/CLAUDE.template.md"
  else
    copy_file "$SRC/CLAUDE.md" "$T/CLAUDE.md"
  fi
  settings "$SRC/.claude/settings.json" "$T/.claude/settings.json"
  ensure_gitignore "$T"
  write_marker "$T/.claude/cct-pending"
  record_source "$T" "$CCT"
  WHERE="$T"
else
  for d in rules skills agents; do
    copy_tree "$SRC/.claude/$d" "$C/$d"
  done
  copy_tree "$SRC/.claude/hooks" "$C/hooks/cct"
  copy_tree "$SRC/rule-packs" "$CCT/rule-packs"
  copy_file "$SRC/templates/CLAUDE.package.md" "$CCT/CLAUDE.package.md"
  copy_file "$SRC/.claude/cct.json" "$C/cct.json"
  if [ -e "$C/CLAUDE.md" ]; then
    put_file "$SRC/templates/CLAUDE.user.md" "$CCT/CLAUDE.user.template.md"
  else
    copy_file "$SRC/templates/CLAUDE.user.md" "$C/CLAUDE.md"
  fi
  settings "$SRC/templates/settings.global.json" "$C/settings.json"
  write_marker "$C/cct-pending"
  record_source "$C" "$CCT"
  WHERE="any project folder"
fi

echo
if [ "$DRY" -eq 1 ]; then
  echo "Would copy ${#COPIED[@]} file(s):"
  for f in "${COPIED[@]+"${COPIED[@]}"}"; do echo "  + $f"; done
else
  echo "Copied ${#COPIED[@]} file(s)."
fi
if [ "${#SKIPPED[@]}" -gt 0 ]; then
  echo "Kept ${#SKIPPED[@]} existing file(s) unchanged:"
  for f in "${SKIPPED[@]}"; do echo "  = $f"; done
fi
echo
echo "Next: start (or restart) Claude Code in $WHERE and run /setup."
echo "Claude will detect your stack and ask about anything it can't work out."
