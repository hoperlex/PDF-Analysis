# Task NORMS-DISPLAY-DESIGNATION-01 — norm search and the norm document show the derived display designation

task_id: NORMS-DISPLAY-DESIGNATION-01

## Outcome

`searchNorms` and `getNormDocument` show the same readable designation the catalogue shows («СП 54.13330.2022»), not the undotted slug-derived text; when the derived text is longer than the schema allows (500 characters) the old text is used so no reseal is needed; persisted citations are untouched.

## Depends on

- `NIGHT-1020-INT-01` — the night window's merged candidate.

## Frozen inputs

- base commit: `7bdb254e06736369e4ddfebe065dfc59c252bfb7` (`origin/dev`);
- API 71 paths / 81 operations / 235 schemas, 25 error codes, migration head `0027_optimisation_proposals` — this task changes none of them;
- rulings `R-135`, `R-139`.

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

- `src/auditmanager/norms/search/**`
- `src/auditmanager/norms/catalogue/**`
- `src/auditmanager/norms/public.py`
- `tests/unit/norms/**`
- `tests/integration/norms/search/**`
- `tests/integration/norms/catalogue/**`
- `web/tests/unit/norms/**`
- `docs/program/NORMS-DISPLAY-DESIGNATION-01.md`
- `docs/program/tasks/NORMS-DISPLAY-DESIGNATION-01.md`

## Lane resources

- foundation_instance: `auditmanager-norms-display`
- postgres_port: `57650`
- s3_api_port: `61250`
- s3_console_port: `61251`
- postgres_db: `auditmanager_norms_display`
- s3_bucket: `auditmanager-norms-display`

## Forbidden hotspots

`contracts/**`, migrations, `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**`, persisted `NormCitation.designation`, snapshot rows, the bundle, other `src/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No schema change, no snapshot or ranking change, no new field.

## Deliverables

The change, its tests and a report `docs/program/NORMS-DISPLAY-DESIGNATION-01.md` (what changed, commands run with results, deferred checks, risks).

## Required tests

Unit tests of the derivation use; integration tests of search and catalogue on the lane's own containers (the local real-corpus stand is gone after the reboot: use the fixtures the existing norms tests use); `git diff --check`. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`. No contract, migration or reseal: if the change seems to need one, stop and report.

## Failure/idempotency/security cases

Stated per behaviour in the report; every new guard is shown failing under a quoted mutation.

## Rollback / feature flag

Revert the merge.
