#!/usr/bin/env python3
"""Print the CHANGELOG.md section for one version (used for GitHub release notes).

Usage: changelog_section.py [VERSION]     (default: contents of VERSION)
Exits 1 if the version has no section, so a release can't go out without notes.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def section(changelog, version):
    pattern = rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)"
    m = re.search(pattern, changelog, re.S | re.M)
    return m.group(1).strip() if m else ""


def read_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else read_version()
    version = version.lstrip("v")
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = section(f.read(), version)
    if not text:
        sys.exit(f"CHANGELOG.md has no section for {version}")
    print(text)


if __name__ == "__main__":
    main()
