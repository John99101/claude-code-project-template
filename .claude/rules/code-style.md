# Code style

<!-- cct: /setup fills in the "Project specifics" section from detected config and your answers. -->

## Project specifics
- Formatter: {{FORMATTER}}. Code is formatted automatically after edits; never hand-format against it.
- Linter: {{LINTER}}. Fix lint errors in code you touch.
- Naming: {{NAMING_CONVENTIONS}}
- Imports: {{IMPORT_ORDER}}

## Always
- Match the style of the surrounding code over general preferences.
- Prefer small functions, early returns and descriptive names.
- Comments explain *why*, not *what*. No commented-out code.
- Remove unused imports, variables and dead code you create.
- Handle errors explicitly; never swallow them silently.
- Don't add a dependency to save a few lines. Ask first.
