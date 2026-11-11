#!/usr/bin/env python3
"""Checks the questions /setup would ask on the sample projects, without answering them.

For each project in tests/fixtures/: copy it to a temp folder, install the kit, and run Claude Code headless with a
dry-run /setup that prints its AskUserQuestion payloads as JSON instead of asking them. Then check each payload
against the rules in skills/setup/questions.md: round and option counts, a description on every option, the
recommended option first, short headers, no filler, previews where required, and the right questions for the depth.

Needs the `claude` CLI, logged in or with ANTHROPIC_API_KEY set. Costs about $0.15 per project.
Claude can only read in this run (no writes, no permission bypass).

Usage: python3 tests/eval_questions.py [fixture ...] [--depth thorough|quick] [--model sonnet] [--keep]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_setup  # noqa: E402

READ_ONLY_TOOLS = "Read,Glob,Grep,Skill,Bash(git:*),Bash(ls:*),Bash(cat:*),Bash(python3 --version)"
PROMPT = (
    "/setup project — DRY RUN to test the questions. Do NOT call AskUserQuestion and do NOT write, edit or delete any "
    "file. Treat ~/.claude/cct-preferences.md as absent. Do steps 0–3: put the depth question alone in the first round, "
    "then assume the user answered {depth} and pick the remaining questions. Output ONLY the exact AskUserQuestion "
    "payloads you would send, as a JSON array of rounds, each round {{\"questions\": [...]}} with question, header, "
    "multiSelect and options [{{label, description, preview?}}]. Stop after that."
)

FILLER = re.compile(r"no saved preference|currently not set|not set in|asking because|no preference", re.I)
NEED_PREVIEW = {"Guard", "Commits", "Agents", "Statusline"}
ALWAYS = {"Depth", "Guard", "Never edit", "Done when"}
THOROUGH_ONLY = {"Level", "Ask first", "Commits", "Model", "Agents", "Plan first", "Format", "Lint", "Lockfiles",
                 "Statusline", "Conventions", "Branches", "Versions", "Deploy", "Docs"}
THOROUGH_REQUIRED = {"Lockfiles", "Deploy", "Versions", "Plan first"}


def extract_rounds(text):
    """The JSON array of rounds in Claude's answer, or None."""
    m = re.search(r"\[\s*\{.*\}\s*\]", text or "", re.S)
    if not m:
        return None
    try:
        rounds = json.loads(m.group(0))
    except ValueError:
        return None
    return rounds if isinstance(rounds, list) else None


def check_questions(rounds, depth):
    """Return a list of problems with the planned question rounds (empty means they pass)."""
    if not rounds:
        return ["no question rounds found in the output"]
    problems = []
    questions = []
    for i, r in enumerate(rounds, 1):
        qs = r.get("questions") if isinstance(r, dict) else None
        if not qs:
            problems.append(f"round {i} has no questions")
            continue
        if len(qs) > 4:
            problems.append(f"round {i} has {len(qs)} questions (max 4)")
        questions += qs
    first = (rounds[0].get("questions") or [{}]) if isinstance(rounds[0], dict) else [{}]
    if len(first) != 1 or first[0].get("header") != "Depth":
        problems.append("the depth question isn't alone in the first round")

    for q in questions:
        h = q.get("header", "")
        text = q.get("question", "")
        opts = q.get("options") or []
        if len(h) > 12:
            problems.append(f"header longer than 12 characters: {h!r}")
        if FILLER.search(text):
            problems.append(f"{h}: filler in {text!r}")
        if h != "Depth" and "[" not in text:
            problems.append(f"{h}: doesn't say where the answer goes")
        if not 2 <= len(opts) <= 4:
            problems.append(f"{h}: {len(opts)} options (must be 2–4)")
        for o in opts:
            if not str(o.get("description", "")).strip():
                problems.append(f"{h}: option {o.get('label')!r} has no description")
        recommended = [n for n, o in enumerate(opts) if "(Recommended)" in o.get("label", "")]
        if recommended and recommended[0] != 0 and not q.get("multiSelect"):
            problems.append(f"{h}: recommended option isn't first")
        if h in NEED_PREVIEW and not any(o.get("preview") for o in opts):
            problems.append(f"{h}: missing preview")

    headers = {q.get("header") for q in questions}
    required = ALWAYS | (THOROUGH_REQUIRED if depth == "thorough" else set())
    for h in sorted(required - headers):
        problems.append(f"missing question: {h}")
    if depth == "quick":
        for h in sorted(headers & THOROUGH_ONLY):
            problems.append(f"Thorough-only question asked in Quick mode: {h}")
    return problems


def run_dry(project, model, depth):
    cmd = ["claude", "-p", PROMPT.format(depth=depth.capitalize()), "--model", model, "--max-turns", "40",
           "--output-format", "json", "--setting-sources", "project,local", "--allowedTools", READ_ONLY_TOOLS]
    env = dict(os.environ, ECC_GATEGUARD="off")
    r = subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=900, env=env)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"is_error": True, "result": (r.stdout + r.stderr)[-2000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixtures", nargs="*", help="fixture names (default: all)")
    parser.add_argument("--depth", choices=["thorough", "quick"], default="thorough")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--keep", action="store_true", help="keep the temp projects and outputs for inspection")
    args = parser.parse_args()

    if not shutil.which("claude"):
        sys.exit("The `claude` CLI isn't on PATH. Install Claude Code first.")
    names = args.fixtures or sorted(eval_setup.load_expectations())
    workdir = tempfile.mkdtemp(prefix="cct-questions-")
    failed, total_cost = 0, 0.0
    try:
        for name in names:
            project = eval_setup.prepare(name, workdir)
            result = run_dry(project, args.model, args.depth)
            message = str(result.get("result", ""))
            if result.get("is_error") and any(w in message.lower() for w in ("auth", "login", "api key", "credit")):
                print(f"Claude Code couldn't log in:\n  {message[:400]}")
                sys.exit(2)
            cost = float(result.get("total_cost_usd") or 0)
            total_cost += cost
            rounds = extract_rounds(message)
            problems = check_questions(rounds, args.depth)
            n = sum(len(r.get("questions") or []) for r in rounds or [] if isinstance(r, dict))
            failed += bool(problems)
            print(f"{'PASS' if not problems else 'FAIL'}  {name}  ({n} questions, ${cost:.2f})")
            for p in problems:
                print(f"      - {p}")
            if args.keep:
                with open(os.path.join(workdir, name + ".questions.json"), "w", encoding="utf-8") as f:
                    json.dump(rounds, f, indent=2, ensure_ascii=False)
            if problems and not rounds:
                print("      last message: " + message[-400:].replace("\n", " "))
    finally:
        if args.keep:
            print(f"\nProjects and question files kept in {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    print(f"\n{len(names) - failed}/{len(names)} passed ({args.depth}) · total cost ${total_cost:.2f}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
