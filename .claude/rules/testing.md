---
paths:
  - "tests/**"
  - "test/**"
  - "__tests__/**"
  - "spec/**"
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/*_test.*"
  - "**/test_*.py"
---

# Testing

<!-- cct: /setup sets the paths above to this project's real test locations and fills in the specifics. -->

## Project specifics
- Framework: {{TEST_FRAMEWORK}}
- Run all: `{{TEST_CMD}}` · run one file: `{{TEST_ONE_CMD}}`
- Approach: {{TEST_APPROACH}}
- Coverage expectation: {{COVERAGE}}

## Always
- Every bug fix gets a test that fails before the fix and passes after.
- Test behaviour through public interfaces, not implementation details.
- One reason to fail per test; name tests after the behaviour they check.
- No real network, clock or randomness in unit tests. Fake them.
- Never delete or weaken a failing test to make the suite pass. Fix the code or ask.
