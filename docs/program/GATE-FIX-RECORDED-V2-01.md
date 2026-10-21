# GATE-FIX-RECORDED-V2-01 — the recorded-v2 saved-plan reds and the profile category pin

Task: `docs/program/tasks/GATE-FIX-RECORDED-V2-01.md`. Branch `agent/gate-fix-v2-01`, based on
`c90d52f3` (`origin/dev` `a41cb90e` plus the two frozen task files); test commit `d409c761`.
Evidence: `.local/gates/night-43670efc/rerun.log` (the 15 real reds of the first complete gate on
`43670efc`). Debt `D-187`.

## Result

All 11 named tests pass, on the lane's own containers. All 11 were **stale pins; none was a product
defect**. No `src/**` file changed, and no `contracts/**`, migration, fixture, recording,
`tests/support/**`, `conftest.py`, `web/**` or dependency file. Three test files changed.

Two facts moved after these tests were last green, and the tests still asserted the old ones:

1. `text_analysis` was sealed at `1.0.0` and `W57A-SEAL-01B` (`56efead4`) moved it to `1.1.0` in
   `contracts/analysis/v1/stage-registry.json` (and `STAGE_VERSION` in `analysis/text/stage.py`). Both
   recorded-v2 consumers refuse a text-stage result whose `stage_version` is not the registry's
   (`_one_reference` in `findings/recorded_saved_plan.py`, `_text_reference` in
   `runs/recorded_v2_merge.py`), which is right. The tests built their saved `StageResult` /
   `StageResultRow` with the literal `"1.0.0"`.
2. The sealed `FindingCategory` grew from seven to twelve values (the contract's own description:
   "seven prior categories and five v3 normative categories"). AR v2 emits the original seven; the five
   normative ones belong to AR v3. The profile-content test compared the AR v2 prompt's seven names with
   the whole twelve-value enum.

The third suspect from the brief, `decided_severity` on the v2 decision ledger, is **not** involved: no
red touches a decision.

| Red | Cause | Decision |
| --- | --- | --- |
| `test_v2_recorded_saved_plan.py::test_saved_plan_preserves_finding_fields_and_rejections_without_replay` | `_case` built `StageResult("text_analysis", "1.0.0", ...)`; `_one_reference` raised `saved_stage_result_invalid` | stale pin |
| `...::test_all_rejected_is_a_complete_zero_finding_plan` | same | stale pin |
| `...::test_saved_plan_retains_two_merged_members_and_rejected_gap` | same | stale pin |
| `...::test_changed_source_or_stage_binding_is_refused` | the case was refused at the stage-version gate, so `match="saved_call_or_source_binding_invalid"` saw `saved_stage_result_invalid` | stale pin |
| `...::test_changed_blob_bytes_and_forged_merge_are_refused` | same, `saved_text_observations_invalid` expected | stale pin |
| `...::test_wrong_stage_and_metric_are_refused_before_publication` | the first half (`0.0.0`) passed for the right reason; the second half (`observation_count: 999`, `saved_merge_metrics_invalid`) was refused at the stage-version gate | stale pin |
| `...::test_merge_byte_digest_and_canonical_form_are_required` | same, `saved_merge_digest_mismatch` expected | stale pin |
| `test_v2_recorded_merge_stage.py::test_merge_uses_saved_text_blob_and_binds_only_after_exact_readback` | the `_Runs` row for `text_analysis` carried `"1.0.0"`; `_text_reference` raised `text_stage_not_complete` | stale pin |
| `...::test_ocr_only_diagnostic_has_empty_successful_merge` | same | stale pin |
| `...::test_wrong_merge_readback_cannot_commit_success` | same; the refusal's code is `analysis_input_invalid`, the test expected `storage_integrity_error` | stale pin |
| `test_ar_v2_profile_content.py::test_reviewed_sections_are_fixed_and_match_the_frozen_category_enum` | `named == frozen` compared AR v2's seven with the contract's twelve (`Right contains 5 more items, first extra item: 'evacuation'`) | stale pin |

## What changed

**The stage versions are no longer typed.** `test_v2_recorded_saved_plan.py` and
`test_v2_recorded_merge_stage.py` get `_stage_version(stage_id)`, which reads
`contracts/analysis/v1/stage-registry.json` (the sealed contract, found from the test file's own path),
not the `default_registry()` object the code under test consults, and never a hand-copied value. Every
stage row the two files build uses it (`text_analysis`, `finding_merge`, `source_preparation`). A reseal
now moves the tests with the contract. `_RETIRED_TEXT_STAGE_VERSION = "1.0.0"` is kept as a named
constant only for the new guards below, each of which first asserts that it differs from the contract.

**The category claim is stated with the current truth** (`test_ar_v2_profile_content.py`, the test keeps
its name so the gate's id is unchanged). The claim was "the prompt names exactly the sealed enum". It is
now two claims: `named == list(ar_v2.response_schema.CATEGORIES)` (the prompt names the seven its own
schema allows, and the prompt says "exactly seven") and `frozen == named + list(ar_v3.response_schema.NORMATIVE_CATEGORIES)`
(the sealed enum is those seven followed by the five normative ones, in that order). The contract's
`enum` is still read from `contracts/api/v1/openapi.json`.

**New guards.**

- `test_text_stage_saved_under_the_retired_version_is_refused` (findings): a text result under `1.0.0`
  is refused with `saved_stage_result_invalid` **and no Blob was read**.
- `test_text_stage_saved_under_the_retired_version_refuses_before_effect` (runs): a `text_analysis` row
  under `1.0.0` is refused with reason `text_stage_not_complete`, with no text read, no `stage_started`,
  no merge Blob and no binding.

**Tightened guards (a finding of this lane, not asked for).** While the stale pin was in place, 13
tests *passed vacuously* (they were green in the gate and the rerun): every case failed at the same early
gate, and the tests only asserted the exception *type* or the *code*:

- the seven parametrized cases of `test_wrong_run_version_or_call_fact_is_refused` asserted a bare
  `SavedRecordedPlanError`, and `saved_stage_result_invalid` is one;
- `test_saved_source_reference_mismatch_refuses_before_effect`, `test_text_blob_bytes_must_match_saved_reference`,
  `test_unreadable_saved_blob_is_a_typed_refusal_before_effect` and the three
  `test_invalid_saved_text_refuses_before_merge_effect` cases asserted `ANALYSIS_INPUT_INVALID`, which
  `text_stage_not_complete` also carries, plus `stage_started not in events`, which was true because
  nothing ran.

Each now asserts the reason it is about (`^saved_text_observations_invalid$` for `run_id` and
`version_uid`; `^saved_call_or_source_binding_invalid$` for the five call facts;
`recorded_source_reference_mismatch`; `input_unreadable`; `recorded_observation_artifact_invalid`). The
claim that these tests can fail was checked: with the **original** test files and the real guard
deleted (`or recorded.model_id != model_id`, and the `recorded_source_reference_mismatch` check), the
`[model_id-...]` case and `test_saved_source_reference_mismatch_refuses_before_effect` still **pass**
(`10 failed, 14 passed`, the 10 being the stale-pin reds). The same deletions against the repaired
files are M2 and M6 below, and both fail.

## Quoted mutations (each repaired guard shown failing)

Method: the tree's `src tests contracts tools fixtures` and `pyproject.toml` copied to a scratch
directory, exactly one string replacement applied to the copy, the three files run from there
(`rootdir` = the copy, so `pythonpath = ["src"]` and the contract path are the copy's), the copy
restored from the real tree before the next mutation. An unmutated copy: `29 passed`. The real tree
was never mutated.

| # | Guard | File (in the copy) | Mutation | Result |
| --- | --- | --- | --- | --- |
| M1 | the saved text/merge result must carry the registry's `stage_version` | `findings/recorded_saved_plan.py` | delete `            or result.stage_version != definition.stage_version` | `2 failed`: `test_wrong_stage_and_metric_are_refused_before_publication`, `test_text_stage_saved_under_the_retired_version_is_refused` |
| M2 | model id is bound to the saved call | same | delete `            or recorded.model_id != model_id` | `1 failed`: `test_wrong_run_version_or_call_fact_is_refused[model_id-...]` |
| M3 | source binding digest is bound | same | `            or recorded.source_binding_sha256 != source_binding_sha256):` -> `            ):` | `1 failed`: `...[source_binding_sha256-...]` |
| M4 | merge result is bound to the text digest | same | `            or merge_result.metrics.get("text_artifact_sha256") != text_ref.sha256):` -> `            ):` | `1 failed`: `test_changed_source_or_stage_binding_is_refused` |
| M5 | the merge stage's text row must carry the registry's `stage_version` | `runs/recorded_v2_merge.py` | delete `            or row.stage_version != text_stage.stage_version` | `1 failed`: `test_text_stage_saved_under_the_retired_version_refuses_before_effect` |
| M6 | saved source references must match | same | delete `    if (prepared.text_layer_ref, prepared.recognised_ref) != source_refs:` and its `raise _refuse("recorded_source_reference_mismatch")` | `1 failed`: `test_saved_source_reference_mismatch_refuses_before_effect` |
| M7 | the sealed enum is the AR v2 seven plus the five | `contracts/api/v1/openapi.json` | `"insulation",\n          "sound"\n` -> `"insulation"\n` (`FindingCategory` loses `sound`) | `1 failed`: `test_reviewed_sections_are_fixed_and_match_the_frozen_category_enum` |
| M8 | the prompt names exactly AR v2's seven, in order | `analysis/profiles/ar_v2/response_schema.py` | `    "layout",\n    "facade",\n` -> `    "facade",\n    "layout",\n` | same test fails |
| M9 | the other five are AR v3's normative set | `analysis/profiles/ar_v3/response_schema.py` | drop `    "sound",` from `NORMATIVE_CATEGORIES` | same test fails |

## Failing list before and after

Lane stack: `foundation_instance auditmanager-gate-fix-v2`, PostgreSQL 57620, MinIO 61220/61221,
database `auditmanager_gate_fix_v2`, bucket `auditmanager-gate-fix-v2`; both `.env` sides (`DATABASE_URL`
port and database, `S3_ENDPOINT_URL` port) set to the lane; `make up`, then `make migrate` (head
`0027_optimisation_proposals`); `.venv` links to the shared interpreter, `.venv/bootstrap` linked. Started
only with 4673 MiB available (`free -m`); disk 5.8 GiB free (`df -h /`) at the start. Runs were detached
(`nohup setsid`, a log and an rc file each, git-ignored scratch). Command, with the lane's fifteen `.env`
names exported:
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider -rA <files>`, with
`PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`.

| run | tree | result |
| --- | --- | --- |
| the three files, before | `c90d52f3` | **11 failed**, 16 passed (the 11 named tests; the 16 are the vacuous ones above and the other cases) |
| the three files, after | `d409c761` | **29 passed** (27 + the two new guards) |
| `tests/integration/findings`, whole | `d409c761` | 197 passed |
| `tests/contract/program` | `d409c761` plus this report | 28 passed |

The `tests/integration/runs` and `tests/integration/analysis` files touched are
`test_v2_recorded_merge_stage.py` (11 passed) and `test_ar_v2_profile_content.py` (3 passed), run whole
inside the three-file run. The suites do not need the containers for these three files, but the findings
directory does, and ran on them.

## Risks and limits

- A run whose `text_analysis` row was **persisted under `1.0.0`** (before `W57A-SEAL-01B`) is now refused
  by both consumers (`text_stage_not_complete`, `saved_stage_result_invalid`). That is the registry binding
  working: a stage version changes the stage's meaning. The merge stage is wired in
  `runs/executor.py` and runs in the same executor invocation as the text stage, so a new run always
  carries the current version; only a run whose text stage was persisted before the reseal and which is
  resumed after it would hit the refusal, and it fails closed.
  Recorded in the new guards, not changed.
- `tests/characterization/w13_baseline/test_response_baseline.py:495` still carries the literal
  `"stage_version": "1.0.0"` for `text_analysis` as `_TEXT_STAGE_BEFORE`; it is the characterization
  suite's own, documented pin (F-1 in `W59-SEAL-FOLLOWUP-01.md`) and outside this task's paths. Not
  touched.
- The other four reds of `rerun.log` (`test_recorded_v2_executor_bridge_db_accept.py`,
  `test_extractor_divergence.py`, `test_ungrounded_diagnostic_path.py`,
  `test_whole_journey_idempotency.py`) belong to other tasks and were not looked at.
- The AR v2 profile-content test now imports `ar_v3.response_schema.NORMATIVE_CATEGORIES` (the same
  bounded context, `analysis`, and the import `test_ar_v3_response_schema.py` already makes the other way).

## Hotspot proof

`git diff --name-only c90d52f3..HEAD` names only: `docs/program/GATE-FIX-RECORDED-V2-01.md` and the
three test files `tests/integration/analysis/test_ar_v2_profile_content.py`,
`tests/integration/findings/test_v2_recorded_saved_plan.py`,
`tests/integration/runs/test_v2_recorded_merge_stage.py`, all inside the task's allowed paths. No
contract, migration, fixture, recording, `src/**`, `tests/support/**`, `conftest.py`, `web/**`,
dependency file, `CURRENT_STATE.md`, ref or tag.

## Instruction for the integrator

Merge `agent/gate-fix-v2-01` into `integration/night-1020` with a real merge; no contract or migration
moves, so no reseal. Light acceptance covers it (the three files, `tests/integration/findings`, and
`tests/contract/program`); the complete gate runs again on the re-cut candidate.
