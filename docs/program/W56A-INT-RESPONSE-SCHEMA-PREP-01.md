# W56A-INT-RESPONSE-SCHEMA-PREP-01 — pure AR v2 reply schema

The sealed W56a API has seven `FindingCategory` values and five `Severity`
values. `response_schema()` now builds a fresh JSON Schema for a model
proposal: category, Russian finding and recommendation text, proposed
severity, and a nonempty list of page-number/verbatim-quote pairs. The
schema has no expert verdict, decided severity, anchor offsets or finding
identity. Its enums match the frozen OpenAPI values exactly.

This is a pure preparation for `W56A-PROFILES-01`. It does not choose a
profile, parse responses, assemble recognised text, call a provider or
publish findings. That later lane must bind this schema and the six reviewed
source resources into a new immutable prompt/profile identity while keeping
v1's bytes unchanged.

Checks: six focused AR v2 content/schema tests passed; the new module
compiled; direct task governance returned no findings; `git diff --check`
and exact allowed-path proof passed. The first pytest invocation emitted
only preexisting `/tmp/pytest-of-root` cleanup warnings. No full local gate,
paid call, service-backed acceptance or `origin/main` publication was run.

Changed paths: new `analysis/profiles/ar_v2/response_schema.py`, its focused
test, this task/report and top status in `CURRENT_STATE.md`. No shared
contract, migration, provider lock, existing runtime module, dependency,
composition root, style, recording, stand state, `VERSION` or release ref
changed. Rollback is a revert before profile wiring; after wiring, a schema
change requires a new content-hashed profile revision.

The MODEL-PIN block remains: the available stand config selects a stub, the
known catalog lacks the locked Opus model, and a distinct recording route
has not been found. This schema is not a beta or model-quality claim.
