# Task W48-FIX-C — commit the regressions W48-JUDGE-Z found missing

## Outcome

The four refusals the durable-effects repair added — `reject_unpublished`'s
`attempt_not_terminal` and `publication_not_stale`, and the sweep's terminal-owner and age
conditions — each have a committed test that fails when its condition is removed.

## Depends on

- `W48-JUDGE-Z` — verdict at `61896af`, merged at `89876ff`; findings F-8 and F-9

## Frozen inputs

- domain contract: W48 revision 8, unchanged
- API contract: 17 / 20 / 61, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0014_durable_analysis_effects`
- base commit: `89876ff` on `integration/w48-close`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: removing either refusal leaves the existing suites green

### P-01 — the judge's mutation record

- captured_at: 2026-10-05
- command: `git show 61896af:docs/program/reviews/W48-JUDGE-Z.md | grep -n 'F-8\|F-9'`
- captured_output:
  ```text
  F-8: reject_unpublished has no regression for attempt_not_terminal / publication_not_stale
  F-9: the provider-effect sweep has no regression for its terminal-owner and age conditions
  ```
- interpretation: behaviour is correct on the subject; the guard that proves it is absent.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-JUDGE-Z.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/runs/test_durable_effect_boundaries.py`
- `tests/integration/ingest/test_reconciliation.py`
- `docs/program/W48-FIX-C.md`

## Forbidden hotspots

- every source file, contract, migration, lock, composition root and global style

## Non-goals

- no behaviour change; the judge found the behaviour correct

## Deliverables

- one test per refusal, asserting the refusal's own reason, not only its error code

## Required tests

- the two files above
- mutations, each red: remove `src/auditmanager/ingest/reconciliation.py` `attempt_not_terminal`;
  remove `publication_not_stale`; remove the sweep's three terminal-state conditions in
  `src/auditmanager/jobs/repository.py`; remove its age condition
- `git diff --check`

## Integration contract

The integrator's full gate on the merged candidate covers the new tests.

## Failure/idempotency/security cases

- owned disposable services only; probes restored

## Rollback / feature flag

Test-only; revert the commit.

## Handoff

- changed files: the two test files and the report
- commands/results: each mutation with its red output
- known limits: none expected
- integration notes: merge before `W48-INT-CLOSE`
