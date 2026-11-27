"""Test-integrity guard: catches edits that make tests pass by weakening them.

Agents under pressure to get a green run sometimes skip, delete or loosen the failing test instead of fixing the
code (Kent Beck: "the genie cheats"). protect_files.py asks the user before an edit to a test file that:
- adds a skip or disable marker (pytest, unittest, Jest/Vitest/Mocha, Go, Rust, JUnit, RSpec);
- removes test cases, or assertions without adding any;
- only changes the expected value of an assertion.
guard_bash.py asks before `rm` / `git rm` of test files, and claim_check.py treats "tests pass" in a turn that added a
skip as an unbacked claim. No credits: it's a permission prompt. Turn off with cct.json "test_guard": false.
"""
import re

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|testing)/"
    r"|(^|/)test_[^/]*\.py$|_test\.(py|go)$|(^|/)conftest\.py$"
    r"|\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs|mts|cts)$"
    r"|(Test|Tests|Spec|IT)\.(java|kt|cs|swift|scala)$|_spec\.rb$|_test\.(rb|exs)$", re.I)
SKIPS = [
    re.compile(r"@pytest\.mark\.(skip|skipif|xfail)\b|\bpytest\.(skip|xfail)\(|@unittest\.(skip|expectedFailure)"
               r"|\bself\.skipTest\("),
    re.compile(r"\b(it|test|describe|context|suite)\.(skip|todo|failing)\s*\(|\bx(it|describe|test|context)\s*\("
               r"|\b(it|test|describe)\.only\s*\("),
    re.compile(r"\bt\.Skip(f|Now)?\s*\("),
    re.compile(r"#\[ignore\b"),
    re.compile(r"@(Disabled|Ignore)\b"),
    re.compile(r"^\s*(skip|pending)\b[\s(\"']", re.M),
]
TEST_CASE = re.compile(
    r"^\s*(async\s+)?def\s+test\w*\s*\(|\b(it|test)\s*\(\s*[\"'`]|^\s*func\s+(Test|Benchmark|Fuzz)\w*\s*\("
    r"|#\[(tokio::)?test\]|@Test\b|^\s*it\s+[\"']", re.M)
ASSERTION = re.compile(
    r"\bassert\w*\b|\bexpect\s*\(|\.should\b|\brequire\.\w+\(|\bt\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\("
    r"|\bassert(_eq|_ne)?!\(|\bself\.assert\w+\(|\bAssert\.\w+\(")
LITERAL = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`[^`]*`|\b\d+(?:\.\d+)?\b"
                     r"|\b(?:true|false|True|False|None|null|nil)\b")


def is_test_path(rel):
    return bool(TEST_PATH.search(rel.replace("\\", "/")))


def count(pattern, text):
    return len(pattern.findall(text or ""))


def added_skip(old, new):
    return any(count(p, new) > count(p, old) for p in SKIPS)


def changed_expectation(old, new):
    """The new line, when the edit's only change is a literal value inside an assertion (the expected result)."""
    old_lines = [line.strip() for line in (old or "").splitlines() if line.strip()]
    new_lines = [line.strip() for line in (new or "").splitlines() if line.strip()]
    if len(old_lines) != len(new_lines):
        return None
    changed = [(a, b) for a, b in zip(old_lines, new_lines) if a != b]
    if not changed:
        return None
    for a, b in changed:
        if not (ASSERTION.search(a) and ASSERTION.search(b)) or LITERAL.sub("_", a) != LITERAL.sub("_", b):
            return None
    return changed[0][1]


def problem(rel, old, new):
    """Why this edit to a test file weakens the tests, or None."""
    if not is_test_path(rel):
        return None
    if added_skip(old, new):
        return "adds a skip or disable marker, which hides the failure instead of fixing it"
    cases_before, cases_after = count(TEST_CASE, old), count(TEST_CASE, new)
    if cases_after < cases_before:
        gone = cases_before - cases_after
        return f"removes {gone} test case{'s' if gone != 1 else ''}"
    if count(ASSERTION, new) < count(ASSERTION, old) and cases_after == cases_before:
        return "removes assertions without adding any, so the test checks less"
    line = changed_expectation(old, new)
    if line:
        return f"changes only what the test expects (`{line[:80]}`)"
    return None
