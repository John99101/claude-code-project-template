#!/bin/sh
# macOS/Linux launcher for install.py: finds Python 3 and runs the installer with your arguments.
# Usage:  ./install.sh --project ~/code/my-app      (see: ./install.sh --help)
dir=$(cd "$(dirname "$0")" && pwd)
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    exec "$py" "$dir/install.py" "$@"
  fi
done
echo "Python 3.8 or newer is required (the kit's hooks use it). Install it and run this again." >&2
exit 1
