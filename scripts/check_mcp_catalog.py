#!/usr/bin/env python3
"""Check that every server in the MCP catalog still exists.

- http/sse servers: the URL must answer (any status below 500 counts, since 401/405 just mean "log in first")
- npx servers: the npm package must exist and not be deprecated
- uvx servers: the PyPI package must exist
Prints a report and exits 1 if anything is broken. Uses only the standard library.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "skills", "setup", "mcp-catalog.json")
UA = {"User-Agent": "claude-code-project-kit-catalog-check"}


def fetch(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e).encode()


def package_name(args):
    """First argument that isn't a flag, with any @version suffix removed."""
    for a in args:
        if a.startswith("-") or a.startswith("${"):
            continue
        if a.startswith("@"):
            scope, _, rest = a[1:].partition("/")
            return "@" + scope + "/" + rest.split("@")[0]
        return a.split("@")[0]
    return None


def check(name, config):
    if config.get("url"):
        status, body = fetch(config["url"])
        if status is None:
            return False, f"unreachable: {body.decode(errors='replace')[:80]}"
        return status < 500, f"HTTP {status}"
    cmd, args = config.get("command"), config.get("args", [])
    pkg = package_name(args)
    if cmd == "npx" and pkg:
        status, body = fetch("https://registry.npmjs.org/" + urllib.parse.quote(pkg, safe="@"))
        if status != 200:
            return False, f"npm package {pkg} not found (HTTP {status})"
        data = json.loads(body)
        latest = data.get("dist-tags", {}).get("latest")
        deprecated = data.get("versions", {}).get(latest, {}).get("deprecated")
        if deprecated:
            return False, f"npm package {pkg}@{latest} is deprecated: {deprecated[:100]}"
        return True, f"npm {pkg}@{latest}"
    if cmd == "uvx" and pkg:
        status, _ = fetch(f"https://pypi.org/pypi/{pkg}/json")
        return status == 200, f"PyPI {pkg} (HTTP {status})"
    return True, "not checked (unknown launcher)"


def main():
    with open(CATALOG, encoding="utf-8") as f:
        servers = json.load(f)["servers"]
    failures = 0
    for name, entry in servers.items():
        ok, detail = check(name, entry["config"])
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {name:<12} {detail}")
    if failures:
        print(f"\n{failures} catalog entr{'y' if failures == 1 else 'ies'} need updating in {os.path.relpath(CATALOG, ROOT)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
