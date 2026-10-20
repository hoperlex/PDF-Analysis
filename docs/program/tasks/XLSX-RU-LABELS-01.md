# Task XLSX-RU-LABELS-01 — the Excel export writes Russian labels instead of raw enum values

task_id: XLSX-RU-LABELS-01

## Outcome

A run's Excel export shows severities, categories, decision verdicts and modality in the Russian labels the screens use (e.g. «критично», «пожарная безопасность», «ожидает решения») with a lockstep test against the web label tables, and identifiers stay as opaque ids; the zip/XML structure and the certified-chain digests are re-pinned deliberately and the writer stays free of formulas.

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

- `src/auditmanager/exports/xlsx/**`
- `tests/unit/exports/**`
- `tests/integration/exports/**`
- `web/src/entities/finding/model/severity-labels.ts`
- `web/src/entities/finding/model/category-labels.ts`
- `web/tests/unit/exports/**`
- `docs/program/XLSX-RU-LABELS-01.md`
- `docs/program/tasks/XLSX-RU-LABELS-01.md`

## Lane resources

- foundation_instance: `auditmanager-xlsx-ru`
- postgres_port: `57660`
- s3_api_port: `61260`
- s3_console_port: `61261`
- postgres_db: `auditmanager_xlsx_ru`
- s3_bucket: `auditmanager-xlsx-ru`

## Forbidden hotspots

`contracts/**`, migrations, `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**`, the CSV export, other `src/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No layout change, no new column, no CSV change, no contract change (the operation's description does not fix cell values).

## Deliverables

The change, its tests and a report `docs/program/XLSX-RU-LABELS-01.md` (what changed, commands run with results, deferred checks, risks).

## Required tests

Unit and integration tests of the exports on the lane's own containers; a structure check of the produced zip/XML; the `soffice --headless` probe if it is installed (report the result, do not fail the task on its absence); web label tests. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`. No contract, migration or reseal: if the change seems to need one, stop and report.

## Failure/idempotency/security cases

Stated per behaviour in the report; every new guard is shown failing under a quoted mutation.

## Rollback / feature flag

Revert the merge.
