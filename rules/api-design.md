---
paths:
  - "**/api/**"
  - "**/routes/**"
  - "**/controllers/**"
  - "**/handlers/**"
  - "**/endpoints/**"
  - "**/*.proto"
  - "**/openapi.*"
  - "**/schema.graphql"
---

# API design

<!-- cct: /setup adjusts the paths to this project's API code, fills in the specifics, or removes this file if the project has no API. -->

## Project specifics
- Style: {{API_STYLE}}
- Auth: {{API_AUTH}}
- Error format: {{API_ERROR_FORMAT}}
- Versioning: {{API_VERSIONING}}

## Always
- Resources are plural nouns (`/users/{id}`); actions are HTTP verbs, not URL verbs.
- Use correct status codes: 201 on create, 204 on empty success, 400 bad input, 401/403 auth, 404 missing, 409 conflict, 422 validation.
- Validate all input at the boundary. Return every validation error at once.
- Paginate list endpoints. Never return unbounded lists.
- Never break existing clients. Add fields; don't rename or remove them without a new version.
- Update the API spec or docs in the same change as the code.
