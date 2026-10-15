# Task W56A-INT-GROUNDING-PREP-01 — classify OCR-only AR v2 quotes offline

## Outcome

A pure AR v2 helper resolves quotations only against the PDF text layer and
labels a same-page OCR-only quotation as `quote_in_recognised_text`, without
creating evidence offsets or publishing a finding.

## Depends on

- `W56A-INT-RESPONSE-PARSER-PREP-01` — complete at `c6f8c254`;
- `W56A-INT-RECOGNISED-CONTEXT-PREP-01` — complete at `d4a8621f`;
- `W56A-INT-PROMPT-MATERIAL-PREP-01` — complete at `a1b0e81f`.

## Frozen inputs

- base `origin/dev=3a8de1299ade011a8a653a9cfd0c18f3ea3571bb`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; `P02_SEAMS.md` §5.1, W56 §A3.4,
  R-133–R-136.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `db/migrations/versions/20261015_0022_findings_v2.py` (read-only)
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `tests/integration/analysis/test_ar_v2_grounding_prep.py`

## Captured premise evidence

- premise: the sealed reason exists but the AR v2 package has no OCR-only
  quotation resolver.

### P-01 — additive helper path absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/grounding.py`
- captured_output:
  ```text
  3a8de1299ade011a8a653a9cfd0c18f3ea3571bb
  3a8de1299ade011a8a653a9cfd0c18f3ea3571bb
  ```
- interpretation: this helper was absent on the frozen dev tip; the existing
  v1 resolver and frozen reason remain independently owned.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/grounding.py` (new);
- `tests/integration/analysis/test_ar_v2_grounding_prep.py` (new);
- this task file and `docs/program/W56A-INT-GROUNDING-PREP-01.md` (new);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing text/grounding/runtime
modules, provider, root dependencies/locks, composition roots, global
styles, recordings, `VERSION`, stand state, tags and `origin/main`.

## Non-goals

No finding artifact, database diagnostic, new reason vocabulary, active v2
stage, provider call, MODEL-PIN verdict, full local gate or acceptance.

## Deliverables

Pure wrapper around the existing exact PDF resolver, OCR-only diagnostic,
focused tests, report and exact dev read-back.

## Required tests

Run focused tests for PDF precedence, OCR-only absence, wrong PDF page,
different OCR page and near match; compile the module; run direct task
governance and `git diff --check`; prove exact changed paths. No full gate.

## Integration contract

`W56A-PROFILES-01` may consume this helper after a fresh grant. Only a
`ResolvedAnchor` from PDF text can become evidence. An OCR-only result is
an `UnresolvedAnchor` without offsets; runtime must preserve the sealed
diagnostic and reject the observation from publication when any required
evidence is unresolved. It must not silently drop one side of a conflict.

## Failure/idempotency/security cases

An OCR context page absent from the PDF text layer is refused. Same input
returns the same result. No fuzzy or case-folded matching, cross-page OCR
repair, file access, network access or side effect occurs.

## Rollback / feature flag

Revert the additive helper before runtime wiring; no flag or database
rollback is needed. Later changes to matching semantics require a profile
revision and new recordings.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: full PROFILES lane after MODEL-PIN and PROVIDER, with OCR diagnostic
  persistence and whole-observation rejection.
