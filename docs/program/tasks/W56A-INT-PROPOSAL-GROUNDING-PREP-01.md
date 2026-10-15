# Task W56A-INT-PROPOSAL-GROUNDING-PREP-01 — ground complete AR v2 proposals offline

## Outcome

A pure AR v2 adapter grounds every proposed quotation against the PDF text
layer, retains a diagnostic for every unresolved item, and excludes the whole
proposal if even one quotation fails. Accepted proposals retain their parsed
proposal ordinals and proposed severity for later artifact wiring.

## Depends on

- `W56A-INT-RESPONSE-PARSER-PREP-01` — complete at `c6f8c254`;
- `W56A-INT-GROUNDING-PREP-01` — complete at `ccfb9735`.

## Frozen inputs

- base commit: `4e76d6fca3bdc961d9f82eee26efb65bb9903bbf` (`origin/dev`);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; W56 §A3.3–A3.4 and R-133–R-136.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed parser and single-anchor resolver are not yet joined.

### P-01 — proposal grounding path absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py tests/integration/analysis/test_ar_v2_proposal_grounding.py`
- captured_output:
  ```text
  4e76d6fca3bdc961d9f82eee26efb65bb9903bbf
  4e76d6fca3bdc961d9f82eee26efb65bb9903bbf
  ```
- interpretation: the two additive paths were absent on the frozen dev tip.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py`
- `tests/integration/analysis/test_ar_v2_proposal_grounding.py`
- `docs/program/tasks/W56A-INT-PROPOSAL-GROUNDING-PREP-01.md`
- `docs/program/W56A-INT-PROPOSAL-GROUNDING-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing parser/resolver/merge
modules, runtime provider or executor, root dependencies/locks, composition
roots, global styles, recordings, `VERSION`, stand state, tags and
`origin/main`.

## Non-goals

No active v2 stage, profile identity, model request, DB diagnostic, finding
publication, live evaluation, full local gate or acceptance.

## Deliverables

Pure whole-proposal grounding adapter, focused tests, report and dev ref
read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q tests/integration/analysis/test_ar_v2_proposal_grounding.py tests/integration/analysis/test_ar_v2_grounding_prep.py tests/integration/analysis/test_ar_v2_response_parser.py` — pass;
- `../../../.venv/bin/python -m compileall -q src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py` — pass;
- direct task governance, `git diff --check` and exact path proof — pass;
- no `make gate`.

## Integration contract

`W56A-PROFILES-01` may consume accepted proposals only after its fresh grant.
Parsed proposal ordinals are retained, including gaps for rejected items;
artifact ordinals are allocated separately after filtering.
Every evidence item is attempted and every failure is reported; a proposal
with one unresolved quote contributes no evidence to a finding or merge.
The adapter does not assign identities or expert severity.

## Failure/idempotency/security cases

OCR-only and wrong-page quotes remain ungrounded. A resolved PDF quote is
verified against the original text layer and carries offsets in code points.
Repeated inputs yield identical outputs; no I/O or side effect occurs.

## Rollback / feature flag

Revert the additive module before runtime wiring. No flag or database rollback
is required.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: profile runtime wiring after MODEL-PIN and PROVIDER grant.
