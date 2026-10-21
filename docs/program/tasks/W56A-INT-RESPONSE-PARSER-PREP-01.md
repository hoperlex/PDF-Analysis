# Task W56A-INT-RESPONSE-PARSER-PREP-01 — parse offline AR v2 proposals

## Outcome

A pure AR v2 parser accepts only complete, schema-shaped proposals with
sealed category/severity values and page/quote evidence. It salvages complete
elements only when the provider explicitly reports truncation; an ordinary
malformed JSON response fails loudly. No proposal is a published finding.

## Depends on

- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-RESPONSE-SCHEMA-PREP-01` — complete at `07d10abb`.

## Frozen inputs

- base `origin/dev=07d10abb371da460ec6f1cf7e95cb0a542b7cf6a`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`, W56 §A3.4, R-129/R-130/R-135/R-136.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/api/v1/openapi.json` (read-only)
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `tests/integration/analysis/test_ar_v2_response_parser.py`

## Captured premise evidence

- premise: AR v2's sealed response schema exists on the development tip,
  but the package has no parser for proposed severity or complete-element
  truncation handling.

### P-01 — committed parser path absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/response.py`
- captured_output:
  ```text
  07d10abb371da460ec6f1cf7e95cb0a542b7cf6a
  07d10abb371da460ec6f1cf7e95cb0a542b7cf6a
  ```
- interpretation: only the named path is absent; the task still must use
  the sealed schema and cannot activate a runtime stage.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/response.py` (new);
- `tests/integration/analysis/test_ar_v2_response_parser.py` (new);
- this task file, `docs/program/W56A-INT-RESPONSE-PARSER-PREP-01.md` (new);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing application/run/text
modules, provider, root dependencies/locks, composition roots, global
styles, `VERSION`, recordings, stand state, `origin/main` and tags.

## Non-goals

No provider/recorded adapter, active profile, prompt, grounding, offset,
finding publication, expert decision, full local gate, acceptance or beta
claim. An invalid proposal is not repaired by guessing a category, severity
or missing quotation.

## Deliverables

Pure parser and focused tests for valid proposals, closed enums, bad fields,
truncation boundaries and malformed nontruncated responses; report with
exact changed-path proof and dev read-back.

## Required tests

Focused pytest including the preceding AR v2 schema/content tests; module
compilation, direct task governance, `git diff --check`, exact path proof.
Do not run `make gate`.

## Integration contract

`W56A-PROFILES-01` may use this parser after a provider response, then pass
its structurally valid proposals to the existing grounding gate. The parser
never asserts that a quote occurs in a source page. Later publication must
exclude ungrounded observations and take the canonical proposal's severity.
Malformed nontruncated JSON raises `V2ResponseError`; explicit truncation
retains only complete array elements and reports that salvage happened.

## Failure/idempotency/security cases

The parser has no IO; repeated calls have equal results. Extra object
fields, invalid enum values, booleans as page numbers, empty quotes and
incomplete trailing JSON are refused or counted, never filled in. No
gateway route, token or model answer is written to a report.

## Rollback / feature flag

Revert this additive parser before runtime wiring; no flag or DB rollback.
After wiring, correct forward under the profile owner.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: profile lane binds parser and schema to a new profile identity only
  after its own grant; MODEL-PIN remains blocked.
