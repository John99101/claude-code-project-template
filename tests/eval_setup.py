#!/usr/bin/env python3
"""End-to-end test of /setup on sample projects.

For each project in tests/fixtures/: copy it to a temp folder, install the kit, run Claude Code headless with
`/setup --defaults`, then check the result against tests/fixtures/expectations.json.

Needs the `claude` CLI, logged in or with ANTHROPIC_API_KEY set. Uses API credits (a few cents to about a dollar per project).

Usage: python3 tests/eval_setup.py [fixture ...] [--model sonnet] [--keep]

Claude runs without permission prompts, because Claude Code asks before every write to .claude/ and a headless
run can't answer. It only ever works inside a fresh temp copy of a sample project, with the kit's guard hooks
active and your personal settings and plugins not loaded.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
ALLOWED_TOOLS = ",".join([
    "Read", "Write", "Edit", "Glob", "Grep", "Skill",
    "Bash(git:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)", "Bash(find:*)", "Bash(python3:*)",
    "Bash(rm:*)", "Bash(mkdir:*)", "Bash(cp:*)", "Bash(mv:*)",
    # Claude Code protects .claude/ and asks before every write there, even in acceptEdits mode,
    # so the files setup is meant to fill in need explicit rules.
    "Edit(./.claude/**)", "Write(./.claude/**)", "Edit(./CLAUDE.md)", "Write(./**/CLAUDE.md)",
])


def load_expectations():
    with open(os.path.join(FIXTURES, "expectations.json"), encoding="utf-8") as f:
        return json.load(f)


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_result(project, expect):
    """Return a list of problems with a finished setup (empty means it passed)."""
    problems = []
    if os.path.exists(os.path.join(project, ".claude", "cct-pending")):
        problems.append("setup marker .claude/cct-pending is still there")

    claude_md_path = os.path.join(project, "CLAUDE.md")
    claude_md = read(claude_md_path)
    if not claude_md:
        problems.append("CLAUDE.md is missing or empty")

    to_scan = [claude_md_path] + [os.path.join(project, p) for p in expect.get("package_claude_md", [])]
    rules_dir = os.path.join(project, ".claude", "rules")
    if os.path.isdir(rules_dir):
        to_scan += [os.path.join(rules_dir, f) for f in os.listdir(rules_dir) if f.endswith(".md")]
    for path in to_scan:
        if "{{" in read(path):
            problems.append(f"unfilled {{{{placeholders}}}} in {os.path.relpath(path, project)}")

    for rel in [".claude/settings.json", ".claude/cct.json", ".mcp.json"]:
        path = os.path.join(project, rel)
        try:
            with open(path, encoding="utf-8") as f:
                json.load(f)
        except (OSError, ValueError) as e:
            problems.append(f"{rel} is not valid JSON ({e.__class__.__name__})")

    lower = claude_md.lower()
    for needle in expect.get("claude_md_contains", []):
        if needle.lower() not in lower:
            problems.append(f"CLAUDE.md doesn't mention {needle!r}")
    for rule in expect.get("rules", []):
        if not os.path.exists(os.path.join(rules_dir, rule)):
            problems.append(f"missing rule .claude/rules/{rule}")
    for rel in expect.get("package_claude_md", []):
        if not os.path.exists(os.path.join(project, rel)):
            problems.append(f"missing package brief {rel}")

    guard = os.path.join(project, ".claude", "hooks", "guard_bash.py")
    if os.path.exists(guard):
        r = subprocess.run([sys.executable, guard], input=json.dumps({"tool_input": {"command": "rm -rf /"}}),
                           capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
        if '"deny"' not in r.stdout:
            problems.append("guard hook no longer blocks rm -rf /")
    else:
        problems.append("guard hook is missing")
    return problems


def prepare(name, workdir):
    project = os.path.join(workdir, name)
    shutil.copytree(os.path.join(FIXTURES, name), project)
    git = ["git", "-c", "user.name=cct-eval", "-c", "user.email=eval@example.invalid"]
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(git + ["add", "-A"], cwd=project, check=True)
    subprocess.run(git + ["commit", "-qm", "feat: initial commit"], cwd=project, check=True)
    subprocess.run(["bash", os.path.join(ROOT, "install.sh"), "--project", project],
                   check=True, capture_output=True)
    return project


def run_setup(project, model):
    # Load only the sample project's own settings, so the tester's personal plugins and hooks
    # (for example ECC's GateGuard) don't change the result.
    # Claude Code protects .claude/ and asks before every write there; allow rules don't lift that, so a
    # headless run has to skip permission prompts. This only ever runs in a fresh temp copy of a sample project.
    cmd = ["claude", "-p", "/setup --defaults", "--model", model, "--max-turns", "80", "--output-format", "json",
           "--setting-sources", "project,local"]
    if os.environ.get("CCT_EVAL_SAFE_MODE") == "1":
        cmd += ["--permission-mode", "acceptEdits", "--allowedTools", ALLOWED_TOOLS]  # will stop at .claude/ writes
    else:
        cmd.append("--dangerously-skip-permissions")
    env = dict(os.environ, ECC_GATEGUARD="off")
    r = subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=1500, env=env)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"is_error": True, "result": (r.stdout + r.stderr)[-2000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixtures", nargs="*", help="fixture names (default: all)")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--keep", action="store_true", help="keep the temp projects for inspection")
    args = parser.parse_args()

    if not shutil.which("claude"):
        sys.exit("The `claude` CLI isn't on PATH. Install Claude Code first.")
    expectations = load_expectations()
    names = args.fixtures or sorted(expectations)
    workdir = tempfile.mkdtemp(prefix="cct-eval-")
    failed, total_cost = 0, 0.0
    try:
        for name in names:
            project = prepare(name, workdir)
            result = run_setup(project, args.model)
            total_cost += float(result.get("total_cost_usd") or 0)
            problems = check_result(project, expectations[name])
            if result.get("is_error"):
                problems.insert(0, f"claude run failed: {str(result.get('result'))[:300]}")
            status = "PASS" if not problems else "FAIL"
            failed += bool(problems)
            print(f"{status}  {name}  ({result.get('num_turns', '?')} turns, ${float(result.get('total_cost_usd') or 0):.2f})")
            for p in problems:
                print(f"      - {p}")
            if problems:
                for d in result.get("permission_denials") or []:
                    target = json.dumps(d.get("tool_input", {}))[:120]
                    print(f"      ! blocked: {d.get('tool_name')} {target}")
                print("      last message: " + str(result.get("result", ""))[-400:].replace("\n", " "))
    finally:
        if args.keep:
            print(f"\nProjects kept in {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    print(f"\n{len(names) - failed}/{len(names)} passed · total cost ${total_cost:.2f}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
