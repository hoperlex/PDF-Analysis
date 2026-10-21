# Task GATE-FIX-CONTRACT-01 — repair the stale contract-level reds before the complete gate

task_id: GATE-FIX-CONTRACT-01

## Outcome

`tests/contract` is green on the night tree except the environment-only families: the error-kernel count pin (24 vs the 25 codes now in the catalogue) and the AR v2 seeded fixture (7 categories vs the 12-value sealed `FindingCategory`) follow the current truth.

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

- `tests/contract/shared_kernel/**`
- `tests/contract/fixtures_seeded/**`
- `tools/seeded/**`
- `tools/ar_corpus/**`
- `fixtures/validation/**`
- `fixtures/synthetic/**`
- `docs/program/GATE-FIX-CONTRACT-01.md`
- `docs/program/tasks/GATE-FIX-CONTRACT-01.md`
0
## Forbidden hotspots

`contracts/**`, migrations, `src/**`, `web/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No contract or product change; no relaxing of a guard.

## Deliverables

The repaired tests/code, and a report `docs/program/GATE-FIX-CONTRACT-01.md` with the failing list before and after, the cause of each red and the decision (stale pin vs real defect).

## Required tests

`tests/contract` whole directory (container-free; `.venv/bootstrap` symlink for the governance interpreter), `git diff --check`. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020` and re-runs the named checks on the merged tree.

## Failure/idempotency/security cases

A red that is a real product defect is fixed in code with a regression test; a red that pins a stale value is fixed in the test with the current truth quoted from the contract. Never weaken a guard to make it pass.

## Rollback / feature flag

Revert the merge.
