"""Environment check, run by session_start.py: does this machine match what the project expects?

- Dependencies: a lockfile newer than the last install (node_modules, .venv), or no install at all.
- .env: missing, or missing keys that .env.example lists. Only key names are read and shown, never values.
- Runtime: node or python versions that don't match .nvmrc, .node-version, package.json engines or .python-version.

Local and cheap: it reads files and runs `node --version` / `python3 --version` at most. The result goes to the user
only, never to Claude, so it uses no credits. Turn off with cct.json "env_check": false.
"""
import glob
import json
import os
import re
import shutil
import subprocess

NODE_LOCKS = [  # lockfile, install command, files the package manager writes into node_modules on install
    ("pnpm-lock.yaml", "pnpm install", [".modules.yaml"]),
    ("package-lock.json", "npm install", [".package-lock.json"]),
    ("yarn.lock", "yarn install", [".yarn-state.yml", ".yarn-integrity"]),
    ("bun.lock", "bun install", []),
    ("bun.lockb", "bun install", []),
]
PY_LOCKS = [("uv.lock", "uv sync"), ("poetry.lock", "poetry install"), ("pdm.lock", "pdm install")]
ENV_EXAMPLES = (".env.example", ".env.sample", ".env.template")
SLACK = 2  # seconds: a checkout writes the lockfile and the install a moment apart
MAX_KEYS = 8


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def node_deps(proj):
    if not os.path.isfile(os.path.join(proj, "package.json")):
        return None
    for lock, cmd, markers in NODE_LOCKS:
        lock_time = mtime(os.path.join(proj, lock))
        if lock_time is None:
            continue
        modules = os.path.join(proj, "node_modules")
        if not os.path.isdir(modules):
            return f"Node dependencies aren't installed (no node_modules). Run `{cmd}`."
        installed = next((t for t in (mtime(os.path.join(modules, m)) for m in markers) if t), None) or mtime(modules)
        if installed and lock_time > installed + SLACK:
            return f"{lock} changed since the last install. Run `{cmd}`."
        return None
    return None


def venv_time(venv):
    times = [mtime(os.path.join(venv, "pyvenv.cfg"))]
    times += [mtime(p) for p in glob.glob(os.path.join(venv, "lib", "python*", "site-packages"))]
    times.append(mtime(os.path.join(venv, "Lib", "site-packages")))
    times = [t for t in times if t]
    return max(times) if times else None


def python_deps(proj):
    venv = os.path.join(proj, ".venv")
    for lock, cmd in PY_LOCKS:
        lock_time = mtime(os.path.join(proj, lock))
        if lock_time is None:
            continue
        if not os.path.isdir(venv):
            # uv always uses .venv; poetry and pdm may keep the environment elsewhere
            return f"Python dependencies aren't installed (no .venv). Run `{cmd}`." if lock == "uv.lock" else None
        installed = venv_time(venv)
        if installed and lock_time > installed + SLACK:
            return f"{lock} changed since the last install. Run `{cmd}`."
        return None
    return None


def env_keys(path):
    keys = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
                if m:
                    keys.append(m.group(1))  # the value is never kept
    except OSError:
        return None
    return keys


def dotenv(proj):
    example = next((n for n in ENV_EXAMPLES if os.path.isfile(os.path.join(proj, n))), None)
    if not example:
        return None
    wanted = env_keys(os.path.join(proj, example)) or []
    have = env_keys(os.path.join(proj, ".env"))
    if have is None:
        if not wanted or all(k in os.environ for k in wanted):
            return None
        return f"There's no .env. Copy {example} to .env and fill it in."
    missing = [k for k in wanted if k not in have and k not in os.environ]
    if not missing:
        return None
    shown = ", ".join(missing[:MAX_KEYS]) + (f" and {len(missing) - MAX_KEYS} more" if len(missing) > MAX_KEYS else "")
    return f".env is missing {shown} (listed in {example})."


def version_of(cmd):
    exe = shutil.which(cmd)
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+(?:\.\d+)+)", r.stdout + r.stderr)
    return m.group(1) if m else None


def parts(v):
    return [int(p) for p in re.findall(r"\d+", v)]


def matches(want, have):
    """`want` like "20", "20.11" or "3.12.1" matches `have` when its parts are a prefix of have's."""
    w, h = parts(want), parts(have)
    return bool(w) and h[:len(w)] == w


def engines_ok(spec, have):
    """Simple package.json engines ranges: >=X[.Y], ^X, ~X, X, X.x. Anything else counts as satisfied."""
    m = re.fullmatch(r"\s*(>=|\^|~)?\s*v?(\d+)(?:\.(\d+|x))?(?:\.(?:\d+|x))?\s*", spec or "")
    if not m:
        return True
    op, major = m.group(1), int(m.group(2))
    minor = int(m.group(3)) if m.group(3) and m.group(3) != "x" else 0
    h = parts(have) + [0, 0]
    if op == ">=":
        return (h[0], h[1]) >= (major, minor)
    return h[0] == major


def first_line(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return None


def node_version(proj):
    for name in (".nvmrc", ".node-version"):
        want = first_line(os.path.join(proj, name))
        if want is None:
            continue
        want = want.lstrip("vV")
        if not re.match(r"^\d", want):
            return None  # lts/*, node, …
        have = version_of("node")
        if not have:
            return f"Node {want} is required ({name}), but `node` isn't installed."
        if not matches(want, have):
            return f"Node {want} is required ({name}), but `node` is {have}."
        return None
    try:
        with open(os.path.join(proj, "package.json"), encoding="utf-8") as f:
            spec = ((json.load(f) or {}).get("engines") or {}).get("node")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(spec, str):
        return None
    have = version_of("node")
    if have and not engines_ok(spec, have):
        return f"package.json engines needs Node {spec.strip()}, but `node` is {have}."
    return None


def python_version(proj):
    want = first_line(os.path.join(proj, ".python-version"))
    if not want or not re.match(r"^\d", want):
        return None
    cfg = os.path.join(proj, ".venv", "pyvenv.cfg")
    if os.path.isfile(cfg):
        have = None
        try:
            with open(cfg, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(r"^\s*version(?:_info)?\s*=\s*(\d+(?:\.\d+)+)", line)
                    if m:
                        have = m.group(1)
                        break
        except OSError:
            return None
        if have and not matches(want, have):
            return f"Python {want} is required (.python-version), but .venv uses {have}. Recreate it."
        return None
    if any(os.path.isfile(os.path.join(proj, lock)) for lock, _ in PY_LOCKS):
        return None  # uv, poetry or pdm picks the interpreter
    have = version_of("python3") or version_of("python")
    if have and not matches(want, have):
        return f"Python {want} is required (.python-version), but `python3` is {have}."
    return None


def find_problems(proj):
    checks = (node_deps, python_deps, dotenv, node_version, python_version)
    return [p for p in (check(proj) for check in checks) if p]


def message(problems):
    return ("[cct] This machine doesn't quite match the project:\n" + "\n".join(f"- {p}" for p in problems)
            + "\nTurn this check off with \"env_check\": false in .claude/cct.json.")
