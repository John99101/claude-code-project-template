#!/usr/bin/env bash
# Installs the Claude Code kit into a project (--project) or onto this device (--global).
# Never overwrites existing files. Run /setup in Claude Code afterwards to finish.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="John99101/claude-code-project-template"
MODE=""
TARGET="."
DRY=0

usage() {
  cat <<EOF
Usage: install.sh --project [DIR] | --global   [--dry-run]

  --project [DIR]  Install into one project (default: current directory).
                   Shared with your team through git.
  --global         Install for every project on this device (~/.claude).
  --dry-run        Show what would happen without changing anything.

Existing files are never overwritten. Then open Claude Code and run /setup.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)
      MODE=project
      if [ $# -gt 1 ] && [ "${2#-}" = "$2" ]; then TARGET="$2"; shift; fi ;;
    --global) MODE=global ;;
    --dry-run) DRY=1 ;;
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

merge_settings() { # src dst
  if [ "$DRY" -eq 1 ]; then
    python3 "$SRC/scripts/merge_settings.py" "$1" "$2" --dry-run
  else
    python3 "$SRC/scripts/merge_settings.py" "$1" "$2"
  fi
}

write_marker() { # path
  if [ "$DRY" -eq 0 ]; then cp "$SRC/.claude/cct-pending" "$1"; fi
}

record_source() { # base_dir subdir
  local base="$1" dir="$1/$2" commit f
  if [ "$DRY" -eq 1 ]; then return 0; fi
  commit="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
  mkdir -p "$dir"
  cat > "$dir/source.json" <<EOF
{
  "repo": "$REPO",
  "commit": "$commit",
  "mode": "$MODE",
  "installed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
  touch "$dir/manifest.txt"  # append only: keeps entries from earlier installs
  for f in "${COPIED[@]+"${COPIED[@]}"}"; do
    (cd "$base" && sha256sum "${f#"$base"/}") >> "$dir/manifest.txt"
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

if [ "$DRY" -eq 1 ]; then
  echo "Claude Code kit: dry run ($MODE mode). Nothing will be changed."
else
  echo "Claude Code kit: installing ($MODE mode)"
fi

if [ "$MODE" = project ]; then
  T="$(cd "$TARGET" && pwd)"
  if [ "$T" = "$SRC" ]; then echo "Target is the kit itself. Pick a project directory." >&2; exit 1; fi
  for d in rules commands skills agents hooks; do
    copy_tree "$SRC/.claude/$d" "$T/.claude/$d"
  done
  copy_file "$SRC/.claude/cct.json" "$T/.claude/cct.json"
  copy_file "$SRC/.claude/settings.local.json.example" "$T/.claude/settings.local.json.example"
  copy_file "$SRC/CLAUDE.local.md.example" "$T/CLAUDE.local.md.example"
  copy_file "$SRC/.mcp.json" "$T/.mcp.json"
  if [ -e "$T/CLAUDE.md" ]; then
    put_file "$SRC/CLAUDE.md" "$T/.claude/cct/CLAUDE.template.md"
  else
    copy_file "$SRC/CLAUDE.md" "$T/CLAUDE.md"
  fi
  merge_settings "$SRC/.claude/settings.json" "$T/.claude/settings.json"
  ensure_gitignore "$T"
  write_marker "$T/.claude/cct-pending"
  record_source "$T" ".claude/cct"
  WHERE="$T"
else
  C="$HOME/.claude"
  for d in rules commands skills agents; do
    copy_tree "$SRC/.claude/$d" "$C/$d"
  done
  copy_tree "$SRC/.claude/hooks" "$C/hooks/cct"
  copy_file "$SRC/.claude/cct.json" "$C/cct.json"
  if [ -e "$C/CLAUDE.md" ]; then
    put_file "$SRC/templates/CLAUDE.user.md" "$C/cct/CLAUDE.user.template.md"
  else
    copy_file "$SRC/templates/CLAUDE.user.md" "$C/CLAUDE.md"
  fi
  merge_settings "$SRC/templates/settings.global.json" "$C/settings.json"
  write_marker "$C/cct-pending"
  record_source "$C" "cct"
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
