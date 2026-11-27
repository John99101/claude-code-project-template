"""Hints about the code an edit just added, used by format_file.py. Only what this edit added is looked at, so
existing code never triggers a hint.

- Undeclared imports (JS/TS, Python): a package imported but not declared in package.json, pyproject.toml or
  requirements*.txt is often a made-up name, or a dependency someone forgot to add. ("dependency_check")
- Duplicates (Python, JS/TS, Go, Rust): a new function whose name, or near-same name (formatDate / format_date),
  is already defined elsewhere in the repo. Agents often rewrite helpers that exist. ("duplicate_hints")

Each hint goes to Claude, so it costs a little; each name is reported once per session.
"""
import json
import os
import re
import subprocess
import sys

from cct_config import relpath

JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte"}
JS_IMPORT = re.compile(r"""(?:\bimport\s+(?:type\s+)?(?:[\w*{}\s,$]+\s+from\s+)?|\bexport\s+[\w*{}\s,$]+\s+from\s+|"""
                       r"""\brequire\s*\(\s*|\bimport\s*\(\s*)["']([^"'\s]+)["']""")
PY_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import\b|import\s+([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*))",
                       re.M)
NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console", "constants", "crypto", "dgram",
    "diagnostics_channel", "dns", "domain", "events", "fs", "http", "http2", "https", "inspector", "module", "net",
    "os", "path", "perf_hooks", "process", "punycode", "querystring", "readline", "repl", "stream", "string_decoder",
    "sys", "timers", "tls", "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib", "test",
}
PY_DIST = {  # import name -> distribution name, where they differ
    "yaml": "pyyaml", "PIL": "pillow", "bs4": "beautifulsoup4", "sklearn": "scikit-learn", "cv2": "opencv-python",
    "dateutil": "python-dateutil", "dotenv": "python-dotenv", "jwt": "pyjwt", "attr": "attrs", "OpenSSL": "pyopenssl",
    "Crypto": "pycryptodome", "magic": "python-magic", "serial": "pyserial", "usb": "pyusb", "git": "gitpython",
    "jose": "python-jose", "multipart": "python-multipart", "docx": "python-docx", "pptx": "python-pptx",
    "slugify": "python-slugify", "fitz": "pymupdf", "telegram": "python-telegram-bot", "googleapiclient":
    "google-api-python-client", "dns": "dnspython", "Levenshtein": "python-levenshtein", "MySQLdb": "mysqlclient",
    "skimage": "scikit-image", "zmq": "pyzmq", "win32api": "pywin32", "pkg_resources": "setuptools",
    "lxml": "lxml", "markdown": "markdown", "websocket": "websocket-client",
}
DEFS = {
    "py": [r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", r"^\s*class\s+([A-Za-z_]\w*)"],
    "js": [r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(",
           r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*(?::\s*[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)",
           r"\bclass\s+([A-Za-z_$][\w$]*)"],
    "go": [r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*[\[(]"],
    "rs": [r"\bfn\s+([A-Za-z_]\w*)\s*[<(]"],
}
COMMON = {"main", "init", "setup", "teardown", "render", "handler", "handle", "constructor", "start", "stop",
          "update", "create", "delete", "build", "parse", "validate", "default", "index", "config", "toString",
          "string", "error", "close", "reset", "apply", "execute", "process", "callback", "wrapper", "inner",
          "helper", "setUp", "tearDown", "middleware", "loader", "action", "reducer", "fetchData", "getData"}
MIN_NAME = 6


def lang(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "py"
    if ext in JS_EXT:
        return "js"
    return {".go": "go", ".rs": "rs"}.get(ext)


def git(proj, *args):
    try:
        r = subprocess.run(["git", "--no-optional-locks", *args], cwd=proj, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def edit_texts(payload, path, proj):
    """(new text, old text) for what this edit changed. A Write is compared with the committed version."""
    tool_input = payload.get("tool_input") or {}
    if "new_string" in tool_input:
        return str(tool_input.get("new_string") or ""), str(tool_input.get("old_string") or "")
    if isinstance(tool_input.get("edits"), list):
        edits = [e for e in tool_input["edits"] if isinstance(e, dict)]
        return ("\n".join(str(e.get("new_string") or "") for e in edits),
                "\n".join(str(e.get("old_string") or "") for e in edits))
    if "content" in tool_input:
        rel = relpath(path, proj).replace(os.sep, "/")
        return str(tool_input.get("content") or ""), git(proj, "show", f"HEAD:{rel}") or ""
    return "", ""


# --- imports ----------------------------------------------------------------------------------------------------

def js_imports(text):
    names = set()
    for spec in JS_IMPORT.findall(text):
        if spec.startswith((".", "/", "~", "#", "$", "@/", "node:", "virtual:", "http:", "https:", "data:")):
            continue
        parts = spec.split("/")
        name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
        if name and name not in NODE_BUILTINS and not name.startswith("bun:"):
            names.add(name)
    return names


def py_imports(text):
    names = set()
    for frm, imps in PY_IMPORT.findall(text):
        for mod in ([frm] if frm else [m.strip() for m in imps.split(",")]):
            if mod and not mod.startswith("."):
                names.add(mod.split(".")[0])
    return names


def up_dirs(start, proj):
    d, root = os.path.abspath(start), os.path.abspath(proj)
    while True:
        yield d
        if d == root or os.path.dirname(d) == d:
            return
        d = os.path.dirname(d)


def js_declared(path, proj):
    """Declared package names from every package.json between the file and the project root, or None if none."""
    declared, found = set(), False
    for d in up_dirs(os.path.dirname(path), proj):
        try:
            with open(os.path.join(d, "package.json"), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        found = True
        if isinstance(data, dict):
            if isinstance(data.get("name"), str):
                declared.add(data["name"])
            for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                if isinstance(data.get(key), dict):
                    declared.update(data[key])
            imports = data.get("imports")
            if isinstance(imports, dict):
                declared.update(k for k in imports if isinstance(k, str))
    return declared if found else None


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def py_declared(proj):
    """Normalised distribution names from pyproject.toml and requirements*.txt, or None without either."""
    texts = []
    for name in ["pyproject.toml", "setup.cfg", "setup.py"] + sorted(
            f for f in os.listdir(proj) if re.match(r"requirements.*\.(txt|in)$", f)):
        try:
            with open(os.path.join(proj, name), encoding="utf-8", errors="replace") as f:
                texts.append(f.read())
        except OSError:
            continue
    if not texts:
        return None
    declared = set()
    for text in texts:
        for m in re.finditer(r"""(?:^|["'\s,\[])([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@]|["',\]]|$)""",
                             text, re.M):
            declared.add(norm(m.group(1)))
        for m in re.finditer(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*=", text, re.M):  # [tool.poetry.dependencies]
            declared.add(norm(m.group(1)))
    return declared


def py_local(top, path, proj):
    for d in list(up_dirs(os.path.dirname(path), proj)) + [os.path.join(proj, "src")]:
        if os.path.exists(os.path.join(d, top)) or os.path.exists(os.path.join(d, top + ".py")):
            return True
    return False


def py_stdlib():
    names = getattr(sys, "stdlib_module_names", None)
    return set(names) if names else None


def undeclared_imports(path, new, old, proj):
    """[(package, manifest)] imported by this edit but not declared."""
    kind = lang(path)
    if kind == "js":
        added = js_imports(new) - js_imports(old)
        declared = js_declared(path, proj) if added else None
        if declared is None:
            return []
        return [(n, "package.json") for n in sorted(added) if n not in declared]
    if kind == "py":
        added = py_imports(new) - py_imports(old)
        stdlib = py_stdlib() if added else None
        declared = py_declared(proj) if added else None
        if stdlib is None or declared is None:
            return []
        out = []
        for top in sorted(added):
            if top in stdlib or top == "__future__" or py_local(top, path, proj):
                continue
            dist = norm(PY_DIST.get(top, top))
            if dist in declared or norm(top) in declared or any(d.startswith(norm(top) + "-") for d in declared):
                continue
            out.append((top, "pyproject.toml or requirements"))
        return out
    return []


# --- duplicates -------------------------------------------------------------------------------------------------

def defined_names(text, kind):
    names = set()
    for pattern in DEFS.get(kind, []):
        names.update(re.findall(pattern, text, re.M))
    return names


def variants(name):
    snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()
    parts = [p for p in snake.split("_") if p]
    camel = parts[0] + "".join(p.title() for p in parts[1:]) if parts else name
    pascal = "".join(p.title() for p in parts) if parts else name
    return sorted({name, snake, camel, pascal})


def existing_definitions(name, rel, proj):
    alts = "|".join(re.escape(v) for v in variants(name))
    sp = "[[:space:]]"  # POSIX classes: git grep -E on macOS and Windows has no \s or \b
    pattern = (rf"(def|function|func|fn|class){sp}+(\([^)]*\){sp}*)?\*?{sp}*({alts})([^A-Za-z0-9_$]|$)"
               rf"|(const|let|var){sp}+({alts}){sp}*=")
    out = git(proj, "grep", "-n", "-I", "-E", pattern, "--", ".", f":(exclude){rel}",
              ":(exclude)*test*", ":(exclude)*spec*", ":(exclude)*.d.ts", ":(exclude)vendor", ":(exclude)node_modules")
    hits = []
    for line in (out or "").splitlines():
        file, _, rest = line.partition(":")
        lineno = rest.partition(":")[0]
        if file and lineno.isdigit():
            hits.append(f"{file}:{lineno}")
    return hits[:3]


def duplicates(path, new, old, proj):
    """[(new name, [file:line, …])] for functions this edit added that already exist elsewhere."""
    kind = lang(path)
    if not kind:
        return []
    added = defined_names(new, kind) - defined_names(old, kind)
    rel = relpath(path, proj).replace(os.sep, "/")
    found = []
    for name in sorted(added):
        if len(name) < MIN_NAME or name in COMMON or name.startswith(("test", "Test", "_")):
            continue
        hits = existing_definitions(name, rel, proj)
        if hits:
            found.append((name, hits))
    return found[:3]
