#!/usr/bin/env python3
"""Stop hook: Claude may only say tests pass, or that it verified something, when it ran a check in that turn.

Agents often announce "all tests pass" or "verified" without having run anything. When Claude is about to finish,
this reads the session transcript: if the final reply makes such a claim but no test, lint, build or type-check
command ran since the user's last message, Claude is sent back once to run the check or correct the claim.
At most once per turn, so it costs a little only when it catches something. Turn off with cct.json "claim_check": false.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cct_config import defer_to_project, load_config, read_input  # noqa: E402

CLAIM = re.compile(
    r"\b(?:all (?:the )?(?:\d+ )?tests (?:now )?pass(?:ed)?"
    r"|tests? (?:are |is )?(?:now |all )?(?:passing|pass(?:es|ed)?|green|succeed(?:s|ed)?)"
    r"|(?:lint(?:er|ing)?|build|type ?check(?:s|ing)?|ci|checks?) (?:is |are |now )*(?:clean|passing|pass(?:es|ed)?|green|succeed(?:s|ed)?)"
    r"|i(?:'ve| have) (?:also )?(?:verified|tested|confirmed|checked) (?:that|it|the|this|everything)"
    r"|verified (?:that|it works|the fix)|everything (?:works|passes))\b", re.I)
HEDGE = re.compile(r"(?:n't\b|\b(?:not|never|should|make sure|once|after you|if|whether|until|to verify|"
                   r"to check|please|you can|you could|try)\b|run `)", re.I)
CHECK_COMMAND = re.compile(
    r"\b(?:test|tests|pytest|jest|vitest|mocha|ava|tap|rspec|phpunit|tox|nox|unittest|ctest|"
    r"go (?:test|vet|build)|cargo (?:test|build|check|clippy|nextest)|tsc|typecheck|type-check|mypy|pyright|"
    r"ruff|eslint|biome|lint|build|make|just|gradle|gradlew|mvn|dotnet (?:test|build)|swift (?:test|build)|"
    r"check|verify|done_gate\.py)\b", re.I)


def content_blocks(entry):
    message = entry.get("message") if isinstance(entry, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def is_user_prompt(entry):
    """A message the user typed, as opposed to a tool result fed back to Claude."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    blocks = content_blocks(entry)
    return bool(blocks) and not all(b.get("type") == "tool_result" for b in blocks if isinstance(b, dict))


def this_turn(path):
    """The transcript entries since the user's last message."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        return []
    for i in range(len(entries) - 1, -1, -1):
        if isinstance(entries[i], dict) and is_user_prompt(entries[i]):
            return entries[i + 1:]
    return entries


def final_text(turn):
    for entry in reversed(turn):
        if isinstance(entry, dict) and entry.get("type") == "assistant":
            texts = [b.get("text", "") for b in content_blocks(entry) if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in texts):
                return "\n".join(texts)
    return ""


def ran_a_check(turn):
    for entry in turn:
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        for b in content_blocks(entry):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Bash", "PowerShell"):
                if CHECK_COMMAND.search(str((b.get("input") or {}).get("command", ""))):
                    return True
    return False


def unbacked_claim(text):
    """The first sentence that claims a passing check without hedging, or None."""
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if CLAIM.search(sentence) and not HEDGE.search(sentence):
            return sentence.strip()[:160]
    return None


def main():
    if defer_to_project(__file__):
        return
    if not load_config().get("claim_check", True):
        return
    payload = read_input()
    if payload.get("stop_hook_active"):
        return  # once per turn: after being sent back, Claude may finish
    turn = this_turn(payload.get("transcript_path") or "")
    claim = unbacked_claim(final_text(turn))
    if not claim or ran_a_check(turn):
        return
    print(json.dumps({
        "decision": "block",
        "reason": (f"cct claim check: your reply says \"{claim}\", but no test, lint, build or type-check command "
                   f"ran in this turn. Run the check now and report the real result, or say plainly that it "
                   f"wasn't verified."),
    }))


if __name__ == "__main__":
    main()
