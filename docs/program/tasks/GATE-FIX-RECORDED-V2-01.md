# Task GATE-FIX-RECORDED-V2-01 — repair the recorded-v2 saved-plan reds and the profile category pin

task_id: GATE-FIX-RECORDED-V2-01

## Outcome

These 11 tests pass on the lane's own containers: `tests/integration/findings/test_v2_recorded_saved_plan.py` (7: saved_stage_result_invalid, changed binding, forged merge, digest, wrong stage/metric, all-rejected, retained members), `tests/integration/runs/test_v2_recorded_merge_stage.py` (3: merge uses the saved text blob, OCR-only diagnostic, wrong merge readback) and `tests/integration/analysis/test_ar_v2_profile_content.py::test_reviewed_sections_are_fixed_and_match_the_frozen_category_enum` (the sealed `FindingCategory` now has 12 values; AR v2 emits the original 7 and the 5 normative ones belong to AR v3).

## Depends on

- the first complete gate of the main candidate `43670efc` (log `.local/gates/night-43670efc/gate.log`, rerun `rerun.log`): 146 red records, 131 of them infrastructure (object storage unavailable) that pass on rerun, 15 real.

## Frozen inputs

- base commit: `a41cb90eb62d5361aa43138ac3891ab7dd610b67` (`origin/dev`; the gated candidate `43670efc` plus docs only);
- API 71 paths / 81 operations / 235 schemas, 25 error codes, migration head `0027_optimisation_proposals`;
- rulings `R-135`, `R-139`; `D-187`.

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

- `tests/integration/findings/**`
- `tests/integration/runs/test_v2_recorded_merge_stage.py`
- `tests/integration/analysis/test_ar_v2_profile_content.py`
- `src/auditmanager/findings/recorded_saved_plan.py`
- `docs/program/GATE-FIX-RECORDED-V2-01.md`
- `docs/program/tasks/GATE-FIX-RECORDED-V2-01.md`

## Lane resources

- foundation_instance: `auditmanager-gate-fix-v2`
- postgres_port: `57620`
- s3_api_port: `61220`
- s3_console_port: `61221`
- postgres_db: `auditmanager_gate_fix_v2`
- s3_bucket: `auditmanager-gate-fix-v2`

## Forbidden hotspots

`contracts/**`, migrations, `tests/support/**`, any `conftest.py` outside the allowed directories, `web/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand. A fixture or recording under `fixtures/**` is not allowed here: if the repair seems to need one, stop and report.

## Non-goals

No product change unless a red proves a real defect (then: fix in the named source path with a regression test and say so loudly in the report). No relaxing of a guard: a guard whose claim became false is re-stated with the current truth and still shown failing under a quoted mutation.

## Deliverables

The repaired tests/code and a report `docs/program/GATE-FIX-RECORDED-V2-01.md` with, for each red: the cause, the decision (stale pin vs real defect), the fix, the quoted mutation.

## Required tests

The 11 tests, then `tests/integration/findings` and the runs/analysis files you touched, whole, on the lane's own containers; `tests/contract/program`. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`; the candidate is then re-cut and the complete gate runs again on the exact new SHA.

## Failure/idempotency/security cases

As stated per red in the report.

## Rollback / feature flag

Revert the merge.
