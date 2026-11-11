#!/usr/bin/env python3
"""Install, update or remove the Claude Code Project Kit. Works on Linux, macOS and Windows.

  python3 install.py --project [DIR]   install into one project (default: current folder), shared via git
  python3 install.py --global          install for every project on this device (~/.claude)
  python3 install.py --adopt           in a repo made with GitHub's "Use this template": turn it into a normal install

  --update     update an existing install; files you changed are kept and the new version is saved next to them
  --uninstall  remove the kit; files you changed are kept and listed
  --dry-run    show what would happen without changing anything

Existing files are never overwritten on install. Afterwards, open Claude Code and run /setup.
On Windows you can also use install.ps1, and on macOS/Linux install.sh; both just run this file.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import kitlib  # noqa: E402
import merge_settings  # noqa: E402

KIT = kitlib.KIT
# Kept by the user once installed (setup fills them in); never replaced by --update.
USER_OWNED = {"CLAUDE.md", ".mcp.json", ".claude/cct.json", "cct.json"}
GITIGNORE_LINES = [".claude/settings.local.json", "CLAUDE.local.md", ".env", ".env.*", "!.env.example"]
# The kit's own development files, removed by --adopt from a "Use this template" copy.
DEV_FILES = ["install.py", "install.sh", "install.ps1", "scripts", "templates", "rule-packs", "skills", "agents",
             "rules", "hooks", ".claude-plugin", "tests/test_kit.py", "tests/eval_setup.py",
             "tests/eval_questions.py", "tests/fixtures",
             ".github/workflows/ci.yml", ".github/workflows/eval-setup.yml", ".github/workflows/mcp-catalog.yml",
             ".github/workflows/release.yml", ".github/ISSUE_TEMPLATE", ".github/pull_request_template.md",
             "docs/GUIDE.md", "CHANGELOG.md", "CONTRIBUTING.md", "VERSION", "INSTALL.md", "LICENSE", "README.md"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree(src_dir, dst_rel, skip=()):
    """(source file, destination path relative to the install base) for every file in a kit folder."""
    out = []
    for path in sorted(Path(src_dir).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc" and path.name not in skip:
            out.append((path, f"{dst_rel}/{path.relative_to(src_dir).as_posix()}"))
    return out


class Install:
    def __init__(self, mode, base, dry):
        self.mode, self.base, self.dry = mode, Path(base), dry
        self.cct = self.base / (".claude/cct" if mode == "project" else "cct")
        self.manifest_path = self.cct / "manifest.txt"

    # ---- what goes where -------------------------------------------------------------------------------
    def files(self):
        t = KIT / "templates"
        if self.mode == "project":
            pairs = (tree(KIT / "skills", ".claude/skills") + tree(KIT / "agents", ".claude/agents")
                     + tree(KIT / "rules", ".claude/rules") + tree(KIT / "hooks", ".claude/hooks", skip={"hooks.json"})
                     + tree(KIT / "rule-packs", ".claude/cct/rule-packs"))
            pairs += [(t / "CLAUDE.package.md", ".claude/cct/CLAUDE.package.md"),
                      (t / "cct.json", ".claude/cct.json"),
                      (t / "settings.local.json.example", ".claude/settings.local.json.example"),
                      (t / "CLAUDE.local.md.example", "CLAUDE.local.md.example"),
                      (t / "mcp.json", ".mcp.json"),
                      (t / "CLAUDE.project.md", "CLAUDE.md")]
        else:
            pairs = (tree(KIT / "skills", "skills") + tree(KIT / "agents", "agents") + tree(KIT / "rules", "rules")
                     + tree(KIT / "hooks", "hooks/cct", skip={"hooks.json"}) + tree(KIT / "rule-packs", "cct/rule-packs"))
            pairs += [(t / "CLAUDE.package.md", "cct/CLAUDE.package.md"),
                      (t / "cct.json", "cct.json"),
                      (t / "CLAUDE.user.md", "CLAUDE.md")]
        return pairs

    def settings(self):
        """The kit's settings for this install, with hooks and status line pointing at the installed scripts."""
        if self.mode == "project":
            py = kitlib.python_command(portable=True)
            data = json.loads((KIT / "templates" / "settings.project.json").read_text(encoding="utf-8"))
            data["hooks"] = kitlib.render_hooks("${CLAUDE_PROJECT_DIR}/.claude/hooks", py)
            data["statusLine"] = kitlib.statusline_command(py, ".claude/hooks/statusline.py")
        else:
            py = kitlib.python_command()
            data = json.loads((KIT / "templates" / "settings.global.json").read_text(encoding="utf-8"))
            data["hooks"] = kitlib.render_hooks(kitlib.fwd(self.base / "hooks" / "cct"), py)
            # Absolute path: "~" isn't expanded inside quotes, and quotes are needed for paths with spaces.
            data["statusLine"] = kitlib.statusline_command(py, kitlib.fwd(self.base / "hooks" / "cct" / "statusline.py"))
        return data

    @property
    def settings_path(self):
        return self.base / (".claude/settings.json" if self.mode == "project" else "settings.json")

    @property
    def marker(self):
        return self.base / (".claude/cct-pending" if self.mode == "project" else "cct-pending")

    # ---- manifest ----------------------------------------------------------------------------------------
    def read_manifest(self):
        entries = {}
        if self.manifest_path.exists():
            for line in self.manifest_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    digest, rel = line.split(None, 1)
                    entries[rel.strip().replace("\\", "/")] = digest
        return entries

    def write_records(self, manifest, commit=None):
        if self.dry:
            return
        self.cct.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text("".join(f"{d}  {r}\n" for r, d in sorted(manifest.items())), encoding="utf-8")
        if commit is None:
            try:
                commit = subprocess.run(["git", "-C", str(KIT), "rev-parse", "HEAD"], capture_output=True,
                                        text=True, timeout=10).stdout.strip() or "unknown"
            except (OSError, subprocess.SubprocessError):
                commit = "unknown"
        source = {"repo": kitlib.REPO, "version": kitlib.version(), "commit": commit, "mode": self.mode,
                  "installed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        (self.cct / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

    # ---- small file helpers ------------------------------------------------------------------------------
    def copy(self, src, dst):
        if not self.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def remove(self, path):
        if not self.dry:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def merge_settings(self, remove=False):
        merge_settings.apply(self.settings(), str(self.settings_path), dry=self.dry, remove=remove)

    def ensure_gitignore(self):
        gi = self.base / ".gitignore"
        existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
        missing = [line for line in GITIGNORE_LINES if line not in existing]
        for line in missing:
            print(f"  .gitignore += {line}")
        if missing and not self.dry:
            with open(gi, "a", encoding="utf-8") as f:
                f.write("\n# Claude Code kit\n" + "".join(line + "\n" for line in missing))

    def write_marker(self):
        if not self.dry and not self.marker.exists():
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KIT / "templates" / "cct-pending", self.marker)

    def clean_empty(self, *dirs):
        if self.dry:
            return
        for d in dirs:
            d = self.base / d
            if not d.is_dir():
                continue
            for cache in list(d.rglob("__pycache__")):
                shutil.rmtree(cache, ignore_errors=True)
            for sub in sorted((p for p in d.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                if not any(sub.iterdir()):
                    sub.rmdir()
            if not any(d.iterdir()):
                d.rmdir()

    # ---- actions -----------------------------------------------------------------------------------------
    def install(self, commit=None):
        manifest, copied, kept = self.read_manifest(), 0, 0
        for src, rel in self.files():
            dst = self.base / rel
            if dst.exists():
                if rel == "CLAUDE.md":
                    name = "CLAUDE.template.md" if self.mode == "project" else "CLAUDE.user.template.md"
                    self.copy(src, self.cct / name)
                    print(f"  kept your CLAUDE.md; template saved to {kitlib.fwd(self.cct / name)}")
                else:
                    kept += 1
                continue
            self.copy(src, dst)
            manifest[rel] = sha256(src)
            copied += 1
        self.merge_settings()
        if self.mode == "project":
            self.ensure_gitignore()
            kitlib.warn_if_python3_missing()
        self.write_marker()
        self.write_records(manifest, commit)
        print(f"\n{'Would copy' if self.dry else 'Copied'} {copied} file(s).")
        if kept:
            print(f"Kept {kept} existing file(s) unchanged.")
        where = self.base if self.mode == "project" else "any project folder"
        print(f"\nNext: start (or restart) Claude Code in {where} and run /setup.")
        print("Claude will detect your stack and ask about anything it can't work out.")

    def update(self):
        manifest = self.read_manifest()
        if not manifest:
            sys.exit(f"No kit install found here ({kitlib.fwd(self.manifest_path)} is missing).")
        incoming = self.cct / "incoming"
        self.remove(incoming)
        added, updated, conflicts, removed, wanted = [], [], [], [], set()
        for src, rel in self.files():
            wanted.add(rel)
            dst, new = self.base / rel, sha256(src)
            if rel in USER_OWNED and dst.exists():
                continue
            if not dst.exists():
                if rel not in manifest:  # new in the kit (a file the user deleted stays deleted)
                    self.copy(src, dst)
                    manifest[rel] = new
                    added.append(rel)
                continue
            current = sha256(dst)
            if current == new:
                manifest[rel] = new
            elif manifest.get(rel) == current:
                self.copy(src, dst)
                manifest[rel] = new
                updated.append(rel)
            else:
                self.copy(src, incoming / rel)  # the user's version stays; the new one goes next to it
                conflicts.append(rel)
        for rel in sorted(set(manifest) - wanted):
            dst = self.base / rel
            if not dst.exists():
                del manifest[rel]
            elif sha256(dst) == manifest[rel]:
                self.remove(dst)
                del manifest[rel]
                removed.append(rel)
        self.merge_settings()
        if removed:  # tidy folders left empty, including 1.0's commands/
            if self.mode == "project":
                self.clean_empty(".claude/commands", ".claude/skills", ".claude/agents", ".claude/rules")
            else:
                self.clean_empty("commands", "skills", "agents", "rules")
        self.write_records(manifest)
        prefix = "Would be " if self.dry else ""
        for title, items in [("added", added), ("updated", updated), ("removed (no longer in the kit)", removed)]:
            if items:
                print(f"{prefix}{title}: {len(items)}" if self.dry else f"{title.capitalize()}: {len(items)}")
                for rel in items:
                    print(f"  {rel}")
        if conflicts:
            where = ".claude/cct/incoming" if self.mode == "project" else "cct/incoming"
            print(f"Changed by you and by the kit, so your version was kept: {len(conflicts)}")
            for rel in conflicts:
                print(f"  {rel}   (new version saved as {where}/{rel})")
        if not (added or updated or removed or conflicts):
            print("Everything is up to date.")
        print(f"\nKit version {kitlib.version()}. Restart Claude Code to load changed hooks and skills.")

    def uninstall(self):
        manifest = self.read_manifest()
        if not manifest:
            print(f"No kit install found here ({kitlib.fwd(self.manifest_path)} is missing).", file=sys.stderr)
            sys.exit(1)
        removed, kept = 0, []
        for rel, digest in sorted(manifest.items()):
            dst = self.base / rel
            if not dst.exists():
                continue
            if sha256(dst) == digest:
                self.remove(dst)
                removed += 1
            else:
                kept.append(rel)
        self.merge_settings(remove=True)
        for p in [self.marker, self.cct / "source.json", self.manifest_path, self.cct / "CLAUDE.template.md",
                  self.cct / "CLAUDE.user.template.md", self.cct / "incoming"]:
            self.remove(p)
        if self.mode == "project":
            self.clean_empty(".claude/rules", ".claude/skills", ".claude/agents", ".claude/hooks", ".claude/cct")
        else:
            self.clean_empty("rules", "skills", "agents", "hooks/cct", "cct")
        print(f"\n{'Would remove' if self.dry else 'Removed'} {removed} file(s).")
        if kept:
            print(f"Kept {len(kept)} file(s) you changed (delete them yourself if you don't need them):")
            for rel in kept:
                print(f"  ~ {rel}")
        if self.mode == "project":
            print("The kit's lines in .gitignore were left in place.")


def adopt(dry):
    """Turn a "Use this template" copy (the kit folder itself) into a normal project install."""
    try:
        remote = subprocess.run(["git", "-C", str(KIT), "config", "--get", "remote.origin.url"],
                                capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        remote = ""
    if kitlib.REPO in remote:
        sys.exit('This is the kit\'s own repository. --adopt is for repos created from it with "Use this template".')
    print(f"Claude Code kit {kitlib.version()}: adopting template copy in {KIT}{' (dry run)' if dry else ''}")
    inst = Install("project", KIT, dry)
    inst.install(commit="template-copy")
    print()
    for rel in DEV_FILES:
        path = KIT / rel
        if path.exists():
            print(f"  - remove {rel}")
            inst.remove(path)
    if dry:
        print("  + new README.md for your project")
        return
    (KIT / "README.md").write_text(f"# {KIT.name}\n\nConfigured for Claude Code with the "
                                   f"[Claude Code Project Kit](https://github.com/{kitlib.REPO}).\n", encoding="utf-8")
    inst.clean_empty("tests", "docs", ".github")
    print("\nRemoved the kit's development files. The kit's LICENSE was removed too; add your project's own if needed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--project", nargs="?", const=".", metavar="DIR", help="install into this project")
    where.add_argument("--global", dest="glob", action="store_true", help="install for every project on this device")
    where.add_argument("--adopt", action="store_true", help='convert a "Use this template" copy')
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--update", action="store_true")
    action.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.adopt:
        adopt(args.dry_run)
        return
    if args.glob:
        inst = Install("global", Path.home() / ".claude", args.dry_run)
    else:
        target = Path(args.project).expanduser().resolve()
        if not target.is_dir():
            sys.exit(f"{target} is not a folder.")
        if target == KIT:
            sys.exit('Target is the kit itself. Pick a project folder, or use --adopt in a "Use this template" copy.')
        inst = Install("project", target, args.dry_run)

    label = "uninstalling" if args.uninstall else "updating" if args.update else "installing"
    print(f"Claude Code kit {kitlib.version()}: {label} ({inst.mode} mode){' (dry run)' if args.dry_run else ''}")
    if args.uninstall:
        inst.uninstall()
    elif args.update:
        inst.update()
    else:
        inst.install()


if __name__ == "__main__":
    main()
