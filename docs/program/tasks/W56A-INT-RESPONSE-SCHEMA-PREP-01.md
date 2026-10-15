# Task W56A-INT-RESPONSE-SCHEMA-PREP-01 — prepare AR v2 response schema

## Outcome

A pure, copy-on-read response schema for the sealed seven categories and five
severity proposals is available to `W56A-PROFILES-01`. It accepts only a
nonempty evidence list with page number and verbatim quote fields; it does
not activate a profile or parse a provider response.

## Depends on

- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-PROFILE-CONTENT-01` — complete at `d6d37e44`;
- `W56A-INT-PROBE-STUB-CORR-01` — complete at `20a0726c`.

## Frozen inputs

- base `origin/dev=20a0726c37297badf273a7c53efa23565f784947`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; R-129/R-130/R-135/R-136;
  `W56-PLAN.md` §A3.4 and §A4 Stage B.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/api/v1/openapi.json` (read-only)
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `tests/integration/analysis/test_ar_v2_response_schema.py`

## Captured premise evidence

- premise: the sealed OpenAPI surface already names seven categories and
  five severity values, but the prepared AR v2 package has no response schema.

### P-01 — contract and package shape

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && rg -n '"FindingCategory"|"Severity"' contracts/api/v1/openapi.json && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2`
- captured_output:
  ```text
  20a0726c37297badf273a7c53efa23565f784947
  20a0726c37297badf273a7c53efa23565f784947
  4009:      "FindingCategory": {
  4022:      "Severity": {
  src/auditmanager/analysis/profiles/ar_v2/__init__.py
  src/auditmanager/analysis/profiles/ar_v2/ar_checklist.md
  src/auditmanager/analysis/profiles/ar_v2/checklist.md
  src/auditmanager/analysis/profiles/ar_v2/content.py
  src/auditmanager/analysis/profiles/ar_v2/drawing_types.md
  src/auditmanager/analysis/profiles/ar_v2/finding_categories.md
  src/auditmanager/analysis/profiles/ar_v2/project_params.md
  src/auditmanager/analysis/profiles/ar_v2/role.md
  ```
- interpretation: this task can add a separate pure schema on a sealed
  enum, without writing the API contract or provider-dependent stage.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/response_schema.py` (new);
- `tests/integration/analysis/test_ar_v2_response_schema.py` (new);
- this task file, `docs/program/W56A-INT-RESPONSE-SCHEMA-PREP-01.md` (new);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing application/run/text
modules, provider, root dependencies/locks, composition roots, global
styles, `VERSION`, recordings, stand state, `origin/main` and tags.

## Non-goals

No profile ID, stage plan, prompt bundle activation, parsed-response
policy, provider call, finding publication, full local gate, acceptance or
beta claim.

## Deliverables

Pure schema builder and focused contract checks, report with changed-path
proof and dev read-back.

## Required tests

Focused pytest against the sealed OpenAPI enums and required field shape;
module compilation, direct task governance, `git diff --check` and exact
changed-path proof. Do not run `make gate`.

## Integration contract

`W56A-PROFILES-01` may call `response_schema()` when constructing a new
immutable v2 prompt bundle. Every call returns a fresh tree so a caller
cannot mutate another run's schema. The profile lane still owns parser,
grounding, recognised-text policy, identity/hash binding and v1 isolation.

## Failure/idempotency/security cases

No external state, network call, credential or paid response. Repeated
calls produce equal JSON but independent dict/list objects. Unknown
categories or severities are excluded by the schema's closed enums.

## Rollback / feature flag

Revert the additive module before runtime wiring; no feature flag or
database rollback is needed. Once wired, any schema change is a new
content-hashed prompt/profile revision.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: the full profile lane consumes this only after its fresh grant;
  MODEL-PIN remains a prerequisite to activation.
