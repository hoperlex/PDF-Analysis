# Task W48-DURABLE-FIX-2 — close upheld durable-effects blockers

## Outcome

Every release-blocking finding upheld by `W48-DURABLE-JUDGE-2` has a bounded repair and a test
whose revert reproduces the failure.

## Depends on

- `W48-DURABLE-JUDGE-2`

## Frozen inputs

- domain contract: W48 revision 8, unchanged
- API contract: 17 / 20 / 61, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0014_durable_analysis_effects`
- base commit: `411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: repair scope is conditional on the independent verdict

### P-01 — exact subject

- captured_at: 2026-10-05
- command: `git rev-parse 411c6d0`
- captured_output:
  ```text
  411c6d0a4fcc44a2b522dbb11f7ed726ef87fe12
  ```
- interpretation: this fixes the repair base, not which findings are upheld.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W48-DURABLE-01.md`
- addendum_path: `docs/program/W48-DURABLE-FIX-2.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/jobs/**`
- `src/auditmanager/runs/**`
- `src/auditmanager/storage/**`
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/analysis/text/**`
- `src/auditmanager/norms/__main__.py`
- `db/migrations/versions/20261002_0014_durable_analysis_effects.py` only for an upheld schema defect
- `tests/integration/runs/**`
- `tests/integration/db/**`
- `tests/integration/storage/**`
- `tests/integration/norms/**`
- `docs/program/W48-DURABLE-FIX-2.md`
- `docs/program/W48-DURABLE-01.md` (DJ-R2 addendum only)

## Forbidden hotspots

- contracts, API, error catalog, root locks, frontend, composition, global styles and earlier migrations
- task files, immutable review reports, refs, tags and deployment

## Non-goals

- no speculative repair of a finding the judge did not uphold

## Deliverables

- the minimum judged repairs, behavioural tests, report and prior-task addendum

## Required tests

- judge probes (a)–(e), focused suites, `make gate`, `git diff --check`, allowed-path diff

## Integration contract

Provider and blob crash windows are explicit, settled or reconcilable; live and legacy work is
never misclassified; schema invariants are behaviourally exercised.

## Failure/idempotency/security cases

- a needed contract/new migration/ungranted hotspot stops the task
- reruns settle or report existing effects and never duplicate an external effect

## Rollback / feature flag

No fallback to unsafe ordering. Before deployed data, revert plus database recreation; after
data, forward repair/restore only as required by `R-53`.

## Handoff

- changed files: allowed-path list only
- commands/results: report includes green and red mutation evidence
- known limits: unresolved items are returned, not guessed
- integration notes: merge before `W48-PUBLIC-01`
