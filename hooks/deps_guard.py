#!/usr/bin/env python3
"""PreToolUse hook for Bash and PowerShell: checks packages before Claude installs them.

AI models sometimes invent package names that sound right, and attackers register those names ("slopsquatting").
Before `npm/pnpm/yarn/bun add`, `pip install`, `uv add`, `poetry add`, `pdm add` or `cargo add`, each named package is
looked up in its registry (npm, PyPI, crates.io):
- it doesn't exist: blocked, since the name is probably made up;
- it's younger than "dependency_min_age_days" (default 30) or barely downloaded: the user is asked, with the facts.
Lookups that fail (offline, private registry) let the install through. Results are cached for a day. No credits:
nothing goes to Claude except the block or ask reason. Turn off with cct.json "dependency_check": false.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import decide, defer_to_project, load_config, read_input, read_state, state_path, write_state  # noqa: E402
from drift import segments  # noqa: E402

TIMEOUT = 3
MAX_PACKAGES = 6
CACHE_SECONDS = 86400
NPM_MIN_WEEKLY = 50
CRATES_MIN_RECENT = 100
MISSING, ERROR = "missing", "error"
UA = {"User-Agent": "cct-kit-dependency-check", "Accept": "application/json"}

NPM_ADD = {"npm": {"install", "i", "add", "isntall", "in"}, "pnpm": {"add"}, "yarn": {"add"}, "bun": {"add", "a"}}
NPM_VALUE_FLAGS = {"--tag", "--prefix", "-C", "--cwd", "--filter", "-F", "--workspace", "-w"}
PRIVATE_FLAGS = {"--registry", "-i", "--index-url", "--extra-index-url", "--index", "--default-index", "--find-links",
                 "-f", "--git", "--path", "--source"}
PIP_VALUE_FLAGS = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-t", "--target", "--python",
                   "-p", "--group", "-G", "--optional", "--extra", "--prefix", "--root", "--platform",
                   "--python-version", "--implementation", "--abi", "--src", "--upgrade-strategy", "--only-binary",
                   "--no-binary", "--progress-bar", "--trusted-host", "--proxy", "--cert", "--client-cert"}
CARGO_VALUE_FLAGS = {"-F", "--features", "--rename", "-p", "--package", "--manifest-path", "--target", "--branch",
                     "--tag", "--rev", "--vers"}
LABEL = {"npm": "npm", "pypi": "PyPI", "crates": "crates.io"}


def fetch(address):
    """Parsed JSON, MISSING for a 404 (or a missing file under CCT_REGISTRY_BASE), or ERROR."""
    try:
        with urllib.request.urlopen(urllib.request.Request(address, headers=UA), timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return MISSING if e.code == 404 else ERROR
    except urllib.error.URLError as e:
        return MISSING if isinstance(e.reason, FileNotFoundError) else ERROR
    except (OSError, ValueError):
        return ERROR


def url(kind, name):
    """CCT_REGISTRY_BASE (a file:// folder) replaces the registries; the tests use it."""
    base = os.environ.get("CCT_REGISTRY_BASE")
    if base:
        return f"{base}/{kind}/{urllib.parse.quote(name, safe='')}.json"
    quoted = urllib.parse.quote(name, safe="@/")
    return {
        "npm": f"https://registry.npmjs.org/{quoted.replace('/', '%2F')}",
        "npm-downloads": f"https://api.npmjs.org/downloads/point/last-week/{quoted}",
        "pypi": f"https://pypi.org/pypi/{quoted}/json",
        "crates": f"https://crates.io/api/v1/crates/{quoted}",
    }[kind]


def age_days(iso):
    try:
        when = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc) - when).days


def check_npm(name):
    downloads = fetch(url("npm-downloads", name))
    weekly = downloads.get("downloads") if isinstance(downloads, dict) else None
    if isinstance(weekly, int) and weekly >= NPM_MIN_WEEKLY * 20:
        return {"ok": True}  # clearly established: skip the (large) package document
    doc = fetch(url("npm", name))
    if doc == MISSING:
        return {"missing": True}
    if not isinstance(doc, dict):
        return None
    return {"age": age_days((doc.get("time") or {}).get("created")), "weekly": weekly}


def check_pypi(name):
    doc = fetch(url("pypi", name))
    if doc == MISSING:
        return {"missing": True}
    if not isinstance(doc, dict):
        return None
    uploads = [f.get("upload_time_iso_8601") or f.get("upload_time")
               for files in (doc.get("releases") or {}).values() for f in (files or [])]
    ages = [a for a in (age_days(u) for u in uploads if u) if a is not None]
    return {"age": max(ages) if ages else None}


def check_crates(name):
    doc = fetch(url("crates", name))
    if doc == MISSING:
        return {"missing": True}
    crate = doc.get("crate") if isinstance(doc, dict) else None
    if not isinstance(crate, dict):
        return None
    return {"age": age_days(crate.get("created_at")), "recent": crate.get("recent_downloads")}


CHECKS = {"npm": check_npm, "pypi": check_pypi, "crates": check_crates}
NOT_A_NAME = re.compile(r"^(\.|/|~|[a-z]+:|git\+|https?:)", re.I)


def npm_name(spec):
    """The package name in an npm spec, or None for paths, URLs, git and workspace specs."""
    if NOT_A_NAME.match(spec) or spec.endswith((".tgz", ".tar.gz")):
        return None
    if "@npm:" in spec:  # alias@npm:real@1.0
        spec = spec.split("@npm:", 1)[1]
    if spec.startswith("@"):
        scope, _, rest = spec[1:].partition("/")
        name = "@" + scope + "/" + rest.split("@", 1)[0] if rest else None
    elif "/" in spec:
        return None  # user/repo on GitHub
    else:
        name = spec.split("@", 1)[0]
    return name if name and re.match(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*$", name, re.I) else None


def pypi_name(spec):
    if NOT_A_NAME.match(spec) or spec.endswith((".whl", ".tar.gz", ".zip")):
        return None
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return re.sub(r"[-_.]+", "-", m.group(1)).lower() if m else None


def cargo_name(spec):
    m = re.match(r"^([A-Za-z0-9_-]+)(@.*)?$", spec)
    return m.group(1) if m else None


def packages_in(args, value_flags):
    """Positional arguments, skipping flags and their values. None when a private registry or source is named."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a.split("=", 1)[0] in PRIVATE_FLAGS:
            return None
        if a.startswith("-"):
            skip = "=" not in a and a in value_flags
            continue
        out.append(a)
    return out


def installs(command):
    """[(registry, name)] for the packages a command would add."""
    found = []
    for seg in segments(command) or []:
        while seg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
            seg = seg[1:]
        if seg and seg[0] == "sudo":
            seg = seg[1:]
        if not seg:
            continue
        tool = re.sub(r"\.(exe|cmd)$", "", os.path.basename(seg[0]).lower())
        args = seg[1:]
        if tool in ("python", "python3", "py") and args[:2] == ["-m", "pip"]:
            tool, args = "pip", args[2:]
        if tool in NPM_ADD and args and args[0] in NPM_ADD[tool]:
            found += [("npm", n) for n in map(npm_name, packages_in(args[1:], NPM_VALUE_FLAGS) or []) if n]
        elif tool in ("pip", "pip3") and args[:1] == ["install"]:
            found += [("pypi", n) for n in map(pypi_name, packages_in(args[1:], PIP_VALUE_FLAGS) or []) if n]
        elif tool == "uv" and (args[:1] == ["add"] or args[:2] == ["pip", "install"]):
            rest = args[1:] if args[0] == "add" else args[2:]
            found += [("pypi", n) for n in map(pypi_name, packages_in(rest, PIP_VALUE_FLAGS) or []) if n]
        elif tool in ("poetry", "pdm", "pipx") and args[:1] in (["add"], ["install"]):
            found += [("pypi", n) for n in map(pypi_name, packages_in(args[1:], PIP_VALUE_FLAGS) or []) if n]
        elif tool == "cargo" and args[:1] == ["add"]:
            found += [("crates", n) for n in map(cargo_name, packages_in(args[1:], CARGO_VALUE_FLAGS) or []) if n]
    unique = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique[:MAX_PACKAGES]


def lookup(registry, name, cache):
    key = f"{registry}:{name}"
    hit = cache.get(key)
    if isinstance(hit, dict) and time.time() - float(hit.get("t", 0) or 0) < CACHE_SECONDS:
        return hit.get("r")
    result = CHECKS[registry](name)
    if result is not None:  # network errors aren't cached
        cache[key] = {"t": time.time(), "r": result}
    return result


def judge(registry, name, result, min_age):
    """("deny" | "ask", reason) or None."""
    if not result or result.get("ok"):
        return None
    where = LABEL[registry]
    if result.get("missing"):
        return "deny", f"`{name}` doesn't exist on {where}. The name may be made up; check the package's real name."
    facts = []
    age = result.get("age")
    if isinstance(age, int) and age < min_age:
        facts.append(f"first published {age} day{'' if age == 1 else 's'} ago")
    weekly, recent = result.get("weekly"), result.get("recent")
    if registry == "npm" and isinstance(weekly, int) and weekly < NPM_MIN_WEEKLY:
        facts.append(f"{weekly} downloads last week")
    if registry == "crates" and isinstance(recent, int) and recent < CRATES_MIN_RECENT:
        facts.append(f"{recent} downloads in 90 days")
    if facts:
        return "ask", (f"`{name}` on {where}: {', '.join(facts)}. "
                       f"Brand-new or rarely used packages are how made-up names get exploited.")
    return None


def main():
    if defer_to_project(__file__):
        return
    cfg = load_config()
    if str(cfg.get("guard_level", "standard")).lower() == "off" or not cfg.get("dependency_check", True):
        return
    command = (read_input().get("tool_input") or {}).get("command") or ""
    wanted = installs(command)
    if not wanted:
        return
    try:
        min_age = max(0, int(cfg.get("dependency_min_age_days", 30)))
    except (TypeError, ValueError):
        min_age = 30
    path = state_path("deps-cache")
    cache = read_state(path)
    verdicts = [v for v in (judge(r, n, lookup(r, n, cache), min_age) for r, n in wanted) if v]
    now = time.time()
    write_state(path, {k: v for k, v in cache.items()
                       if isinstance(v, dict) and now - float(v.get("t", 0) or 0) < CACHE_SECONDS})
    denied = [reason for verdict, reason in verdicts if verdict == "deny"]
    if denied:
        decide("deny", "Blocked by cct dependency check: " + " ".join(denied))
    if verdicts:
        decide("ask", "cct dependency check: " + " ".join(reason for _, reason in verdicts))


if __name__ == "__main__":
    main()
