"""Shared helpers for the kit's installer and scripts. Standard library only; works on Linux, macOS and Windows."""
import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
REPO = "John99101/claude-code-project-template"
KIT_SCRIPTS = ("session_start.py", "guard_bash.py", "protect_files.py", "format_file.py", "statusline.py")
_VERSION_CHECK = "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"


def version():
    try:
        return (KIT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def fwd(path):
    """Forward-slash path: works in exec-form hooks, Git Bash and PowerShell alike."""
    return str(path).replace("\\", "/")


def _works(cmd):
    if not shutil.which(cmd[0]):
        return False
    try:
        return subprocess.run(cmd + ["-c", _VERSION_CHECK], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def python_command(portable=False):
    """The command that starts Python 3 on this machine, as a list (e.g. ["python3"] or ["py", "-3"]).

    portable=True is for config shared through git (project installs): it always uses "python3", which macOS,
    Linux and the current python.org installer for Windows (the Python install manager) all provide.
    """
    if portable or os.name != "nt":
        return ["python3"]
    for cmd in (["python3"], ["py", "-3"], ["python"]):
        if _works(cmd):
            return cmd
    return ["python3"]


def warn_if_python3_missing():
    if os.name == "nt" and not _works(["python3"]):
        print("  note: `python3` isn't available on this machine. Project hooks use it so they work for every\n"
              "        teammate. Install Python with the Python install manager from python.org, which adds it.")


def plugin_hooks():
    with open(KIT / "hooks" / "hooks.json", encoding="utf-8") as f:
        return json.load(f)["hooks"]


def render_hooks(hooks_dir, py):
    """Hook entries for settings.json, built from the plugin's hooks/hooks.json so both stay identical."""
    hooks = copy.deepcopy(plugin_hooks())
    for groups in hooks.values():
        for group in groups:
            for hook in group["hooks"]:
                script = hook["args"][-1].rsplit("/", 1)[-1]
                hook["command"] = py[0]
                hook["args"] = py[1:] + [f"{hooks_dir}/{script}"]
    return hooks


def statusline_command(py, script_path):
    return {"type": "command", "command": " ".join(py) + f' "{script_path}"'}
