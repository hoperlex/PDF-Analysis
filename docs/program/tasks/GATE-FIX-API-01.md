# Task GATE-FIX-API-01 — repair the API and composition suite reds before the complete gate

task_id: GATE-FIX-API-01

## Outcome

`tests/integration/api` and `tests/integration/composition` are green on the night tree: `test_query_surface` (the frozen `FindingCategory` filter vocabulary 12 vs 2; the declared query parameters of `compareDocumentVersions` and `listPriceListPositions` that no test drives) and the `DecisionAdapter` pre-decide test (`TypeError` instead of refusing a severity) follow the truth; any further red these directories reveal on a complete run is repaired or reported.

## Depends on

- `NIGHT-1020-INT-01` — the night window's merged candidate (`8697baea7727613c2bf470ac364cdc53c31faa45`).

## Frozen inputs

- base commit: `8697baea7727613c2bf470ac364cdc53c31faa45` (`origin/dev`);
- API 71 paths / 81 operations / 235 schemas, 25 error codes, migration head `0027_optimisation_proposals`;
- ruling `R-135`; debt `D-187` (the named reds are pre-existing on the night tree, not regressions of one lane).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/integration/api/**`
- `tests/integration/composition/**`
- `src/auditmanager/bootstrap/adapters.py`
- `docs/program/GATE-FIX-API-01.md`
- `docs/program/tasks/GATE-FIX-API-01.md`
1
## Forbidden hotspots

`contracts/**`, migrations, other `src/**`, `web/**`, `tests/support/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand. `adapters.py` may change only to repair `DecisionAdapter`'s pre-decide path.

## Non-goals

No contract change; no new operation.

## Deliverables

The repaired tests/code, and a report `docs/program/GATE-FIX-API-01.md` with the failing list before and after, the cause of each red and the decision (stale pin vs real defect).

## Required tests

The two directories whole, on the lane's own containers (run them in chunks if one run exceeds the tool timeout; record the chunks), before and after.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020` and re-runs the named checks on the merged tree.

## Failure/idempotency/security cases

A red that is a real product defect is fixed in code with a regression test; a red that pins a stale value is fixed in the test with the current truth quoted from the contract. Never weaken a guard to make it pass.

## Rollback / feature flag

Revert the merge.
