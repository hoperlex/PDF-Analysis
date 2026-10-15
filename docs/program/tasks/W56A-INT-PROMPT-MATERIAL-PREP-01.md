# Task W56A-INT-PROMPT-MATERIAL-PREP-01 — assemble immutable AR v2 prompt material

## Outcome

Pure functions assemble AR v2's six reviewed source sections, sealed
response schema, PDF text-layer pages and already selected marked OCR
context into deterministic request material. A hash binds the source
resources and schema. No active profile ID, provider selection or model
request is created.

## Depends on

- `W56A-INT-PROFILE-CONTENT-01` — complete at `d6d37e44`;
- `W56A-INT-RESPONSE-SCHEMA-PREP-01` — complete at `07d10abb`;
- `W56A-INT-RECOGNISED-CONTEXT-PREP-01` — complete at `d4a8621f`.

## Frozen inputs

- base `origin/dev=d4a8621fe82a5945e027b0e383dc05e8d8c8cda7`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; W56 §A3.4, R-129/R-130/R-134/R-135/R-136.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/api/v1/openapi.json` (read-only)
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `tests/integration/analysis/test_ar_v2_prompt_material.py`

## Captured premise evidence

- premise: the sealed code-first AR v2 package has reviewed source,
  schema and OCR selector modules but no joined prompt material.

### P-01 — committed material path absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/prompt_material.py`
- captured_output:
  ```text
  d4a8621fe82a5945e027b0e383dc05e8d8c8cda7
  d4a8621fe82a5945e027b0e383dc05e8d8c8cda7
  ```
- interpretation: the exact additive path is absent; no runtime profile
  or model identity follows from assembling its pure inputs.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/prompt_material.py` (new);
- `tests/integration/analysis/test_ar_v2_prompt_material.py` (new);
- this task file, `docs/program/W56A-INT-PROMPT-MATERIAL-PREP-01.md` (new);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing application/run/text
modules, provider, root dependencies/locks, composition roots, global
styles, `VERSION`, recordings, stand state, `origin/main` and tags.

## Non-goals

No generation parameters, profile or prompt-bundle ID, adapter call,
input-budget decision, parser/grounding change, finding publication,
full local gate, acceptance or beta claim.

## Deliverables

Deterministic prompt rendering and content digest; focused tests for six
sections, unchanged v1 inputs, page/OCR separation and hostile delimiter
text; report and dev ref read-back.

## Required tests

Focused pytest across AR v2 content/schema/parser/OCR/material modules,
module compilation, direct task governance, `git diff --check`, exact
changed-path proof. Do not run `make gate`.

## Integration contract

`W56A-PROFILES-01` may use the system/user strings and material hash only
after its fresh grant. It must add generation parameters, allocate immutable
profile/prompt identities, bind them to run-row stage plans and account for
PDF/OCR characters in the budget. Grounding remains against the PDF text
layer; OCR is never quote evidence. A changed material hash needs a new
recording and profile revision.

## Failure/idempotency/security cases

Missing/tampered reviewed resources fail via the source loader. An OCR
context page absent from the PDF text layer is refused; no fallback to
portal descriptions or an empty answer. PDF and OCR text are JSON-quoted
as untrusted data, and no offset is computed against prompt rendering.
Repeated inputs produce byte-identical material and digest.

## Rollback / feature flag

Revert this additive module before runtime wiring; no flag or DB rollback.
After wiring, change through a new profile/content revision.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: full profile lane with a fresh grant after MODEL-PIN/PROVIDER.
