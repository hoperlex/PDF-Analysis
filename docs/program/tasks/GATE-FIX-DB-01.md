# Task GATE-FIX-DB-01 — repair the database-suite reds before the complete gate

task_id: GATE-FIX-DB-01

## Outcome

`tests/integration/db` is green on the night tree: the downgrade chain through `0022_findings_v2` (23 tests fail with `cannot drop columns from view`) and `test_norms_corpus_migration` (missing `norm_retrieval_set`) follow the truth; any later migration whose downgrade breaks the chain is repaired too.

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

- `db/migrations/versions/20261015_0022_findings_v2.py`
- `db/migrations/versions/20261016_0023_norm_citations.py`
- `db/migrations/versions/20261020_0024_version_classification.py`
- `db/migrations/versions/20261020_0025_work_assignments.py`
- `db/migrations/versions/20261020_0026_price_lists.py`
- `db/migrations/versions/20261020_0027_optimisation_proposals.py`
- `tests/integration/db/**`
- `docs/program/GATE-FIX-DB-01.md`
- `docs/program/tasks/GATE-FIX-DB-01.md`
1
## Forbidden hotspots

Every other migration (`0001`…`0021` are released and immutable), `contracts/**`, `src/**`, `web/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand. Editing a migration is allowed only for its **downgrade** (and only for revisions not on `origin/main`); upgrade SQL stays byte-identical, proven by a test.

## Non-goals

No schema change; no new migration.

## Deliverables

The repaired tests/code, and a report `docs/program/GATE-FIX-DB-01.md` with the failing list before and after, the cause of each red and the decision (stale pin vs real defect).

## Required tests

`tests/integration/db` whole directory on the lane's own containers, before and after; a forward-then-backward-then-forward run of the full chain on a populated database.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020` and re-runs the named checks on the merged tree.

## Failure/idempotency/security cases

A red that is a real product defect is fixed in code with a regression test; a red that pins a stale value is fixed in the test with the current truth quoted from the contract. Never weaken a guard to make it pass.

## Rollback / feature flag

Revert the merge.
