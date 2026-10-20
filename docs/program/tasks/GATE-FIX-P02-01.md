# Task GATE-FIX-P02-01 — repair the P02 journey guards and the executor bridge head pin

task_id: GATE-FIX-P02-01

## Outcome

These 4 tests pass: `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py::test_persisted_recorded_executor_saves_five_stages_one_call_and_one_terminal` (hard-coded head `0022_findings_v2`: read it from `tests/support/expected_facts.json` as the neighbouring tests do), `tests/integration/p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` (new tables since 0023: add them to the counted list with the replay claim they deserve), `tests/integration/p02_journey/test_ungrounded_diagnostic_path.py::test_no_grounded_false_row_exists_anywhere` (rows with grounded=false now exist: decide which producer is legitimate — the W57a citation partitions — and restate the claim precisely) and `tests/integration/p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes` (modules such as `comparison/sheet_match_suggestions.py` mention `page_text_sha256`: decide whether they consume the portal manifest's hash that the pinned extractor cannot reproduce — a real defect to fix in `src/auditmanager/comparison/**` — or compute their own hash from the saved text, in which case the guard is refined with a named, justified allowance and still fails on a real consumer).

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

- `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py`
- `tests/integration/p02_journey/**`
- `src/auditmanager/comparison/**`
- `tests/integration/comparison/**`
- `docs/program/GATE-FIX-P02-01.md`
- `docs/program/tasks/GATE-FIX-P02-01.md`

## Lane resources

- foundation_instance: `auditmanager-gate-fix-p02`
- postgres_port: `57630`
- s3_api_port: `61230`
- s3_console_port: `61231`
- postgres_db: `auditmanager_gate_fix_p02`
- s3_bucket: `auditmanager-gate-fix-p02`

## Forbidden hotspots

`contracts/**`, migrations, `tests/support/**`, any `conftest.py` outside the allowed directories, `web/**`, dependency files, `CURRENT_STATE.md`, refs, tags, the stand. A fixture or recording under `fixtures/**` is not allowed here: if the repair seems to need one, stop and report.

## Non-goals

No product change unless a red proves a real defect (then: fix in the named source path with a regression test and say so loudly in the report). No relaxing of a guard: a guard whose claim became false is re-stated with the current truth and still shown failing under a quoted mutation.

## Deliverables

The repaired tests/code and a report `docs/program/GATE-FIX-P02-01.md` with, for each red: the cause, the decision (stale pin vs real defect), the fix, the quoted mutation.

## Required tests

The 4 tests, then `tests/integration/p02_journey`, `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py` and (if touched) `tests/integration/comparison`, whole, on the lane's own containers; `tests/contract/program`. No full gate.

## Integration contract

The integrator merges the branch (a real merge) into `integration/night-1020`; the candidate is then re-cut and the complete gate runs again on the exact new SHA.

## Failure/idempotency/security cases

As stated per red in the report.

## Rollback / feature flag

Revert the merge.
