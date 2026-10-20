# Task SECTION-READ-MODEL-01 — the dashboard and the section Form-7 view read the confirmed classification

task_id: SECTION-READ-MODEL-01

## Outcome

The dashboard's section breakdown counts a document in the section its **current version** is confirmed in (unclassified → its own bucket), instead of the legacy document-level `document.section`; the section Form-7 view finds its member document sets through a documents-side query «current versions confirmed in section X» instead of scanning every project; a price-list upload refreshes an open Form-7 page.

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

- `src/auditmanager/dashboard/**`
- `src/auditmanager/documents/**`
- `src/auditmanager/optimisation/section_specification.py`
- `tests/integration/dashboard/**`
- `tests/integration/documents/**`
- `tests/integration/optimisation/test_section_specification.py`
- `tests/unit/optimisation/test_section_specification.py`
- `web/src/features/upload-price-list/**`
- `web/tests/unit/optimisation/**`
- `docs/program/SECTION-READ-MODEL-01.md`
- `docs/program/tasks/SECTION-READ-MODEL-01.md`

## Lane resources

- foundation_instance: `auditmanager-section-read-model`
- postgres_port: `57640`
- s3_api_port: `61240`
- s3_console_port: `61241`
- postgres_db: `auditmanager_section_read_model`
- s3_bucket: `auditmanager-section-read-model`

## Forbidden hotspots

`contracts/**`, migrations, `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, other `src/**`, `tests/support/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand.

## Non-goals

No change of any wire shape (the dashboard's schema stays as it is, even where prose still says fourteen sections); no backfill; no classification correction (that is a later slice).

## Deliverables

The change, its tests and a report `docs/program/SECTION-READ-MODEL-01.md` (what changed, commands run with results, deferred checks, risks).

## Required tests

Focused tests of the three contexts on the lane's own containers; web: `lint --quiet`, `typecheck`, the changed vitest files; `tests/contract/api_v1/test_surface_counts_in_prose.py`. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`. No contract, migration or reseal: if the change seems to need one, stop and report.

## Failure/idempotency/security cases

Stated per behaviour in the report; every new guard is shown failing under a quoted mutation.

## Rollback / feature flag

Revert the merge.
