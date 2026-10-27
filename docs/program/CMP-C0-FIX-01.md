# CMP-C0-FIX-01 — four fixes the wave C0 lanes left to the integrator

Written 2026-10-28 by the Sonnet lane `CMP-C0-FIX-01` (branch `agent/cmp-c0-fix-01`, base `ae5873e9` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-C0-FIX-01.md`](tasks/CMP-C0-FIX-01.md). The four items are those of the dispatch: [`CMP-SPEND-01`](CMP-SPEND-01.md) section 8 items 2 and 3 and section 9 item 2, and [`CMP-INGEST-01`](CMP-INGEST-01.md) section 6 items 8 and 9. No contract, migration or dependency file changed.

## 1. Base facts, printed before any edit

Contract `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes; migration head `0038_comparison_foundation`; `HEAD = ae5873e9`. Equal to the premise, so the lane did not STOP (task file, P-01).

## 2. What was changed

| item | change | commit |
| --- | --- | --- |
| 1 | `executors/pull.py` `PullAdapter._write_task`: origin `comparison_call` and `comparison_attempt_id` when the call's context carries `comparison_attempt_id`, else `run_call` exactly as before (the hunk of `CMP-SPEND-01` section 8.3). The strict xfail of `test_a_pull_adapter_writes_the_comparison_origin_for_a_comparison_call` is removed (it passes and is the permanent pin; the then-unused `import pytest` of that file with it). | `275190b0` |
| 2 | `comparison/work/repository.py` `reclaim_expired`: in the branch that ends a `cancelled` item, **every** registered settler is asked about the lost attempt first (a loop, not `any(...)`: none is skipped), then the item ends `cancelled`; the cancel still wins whatever a settler answers. The `spend_unknown` and requeue branches are untouched. | `34744cf3` |
| 3 | `tests/integration/documents/test_version_record_equality.py`: `"upload_kind": "comparison_pdf",` in `changed`. | `d943db60` |
| 4 | `runs/v3_group.py` `start_ar_v3_group`: `refuse_comparison_only_version(version)` right after `get_version`, before the classification check; the import joins the existing one from `runs.commands`. | `44feeb5d` |

Item 1 notes for the lane that calls a model. A comparison call's context must carry `comparison_attempt_id` **and** `remaining_seconds()` (what `answer_window` reads). A context with no `comparison_attempt_id` is written as a run call: without a run it is refused by the table's `ck_executor_task_origin_shape` (loud, not repaired); a context naming both a run and a comparison attempt is refused by the same CHECK.

## 3. Tests

New: `tests/unit/executors/test_pull_comparison_origin.py` (6, through `complete()`: the comparison task's origin, attempt id and no run; the context's `remaining_seconds()` cuts the written window; too little time writes no task; a run call and a call with no context are written as before; the run context has no such attribute), `tests/unit/comparison/work/test_reclaim_settlers_unit.py` (8, container-free: the settlers' order against the writes, every settler asked, the cancel wins, no settler, `leased`, unchanged branches, a live lease and a foreign attempt never settled), two integration tests in `tests/integration/comparison/work/test_lease_reclaim.py` (every settler asked and the item still `cancelled`; a settler's failure rolls the whole pass back), `tests/integration/runs/test_v3_group_refuses_a_comparison_only_version.py` (4: classified, unclassified and other-section comparison versions are refused by the kind and nothing is written; a portal version keeps `version_classification_required` / `missing_required_input`).

Changed: `tests/unit/comparison/spend/test_wiring_and_pins.py` (xfail removed); `tests/integration/comparison/spend/test_reclaim_spend_unknown.py` (see section 6, item 1: the test that pinned the defect now pins the fix, and a docstring that said the queue never settles on a cancel is corrected).

## 4. Checks (light acceptance; the lane's own stack `auditmanager-cmp-c0-fix-01`, ports 57810 / 61810 / 61811, head `0038`)

`df -h /` before every container start and long run: 3.2 GiB at the start, 3.0 GiB at the lowest, 3.1 GiB at the end (stop line 1.5 GiB). All commands from the worktree root with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`, on the committed tree `44feeb5d`.

| what | scope | result |
| --- | --- | --- |
| diff hygiene | `git diff --check ae5873e9..HEAD` | clean (exit 0) |
| unit, no container | `tests/unit/comparison tests/unit/executors` | **1244 passed**, 86 s |
| integration | `tests/integration/comparison tests/integration/documents tests/integration/ingest/comparison_pdf tests/integration/db/test_ar_v3_run_group.py tests/integration/executors` | **806 passed, 16 skipped** (the sshd opt-ins: `EXEC_SSHD_PORT`, `EXEC_LOCAL_SSHD`), 380 s; the whole `tests/integration/documents` is green, so the pre-existing red of `CMP-INGEST-01` item 9 is closed |
| integration | `tests/integration/runs` (the whole directory; it holds every `start_ar_v3_group` caller) | **948 passed**, 114 s |
| contract battery | `tests/contract` minus `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`) | **1307 passed**, 19283 subtests, 128 s |

Not run, by the brief and `R-135`: `make gate`, the web battery (no web change), the live journey. The integration run before the commits (`tests/integration/comparison`, 362 passed) was on the same source as the committed work/spend code.

## 5. Mutation proofs (each applied to the committed source or test, run, restored; the tree is clean after each)

Scratch tool `mutate.py` (outside the tree): replace one exact text, run the named tests, restore the file.

| item | mutation | result |
| --- | --- | --- |
| 1 | origin always `"run_call"` (the pre-fix source) | red: `test_a_comparison_call_writes_a_comparison_call_task...`, and the spend pin `test_a_pull_adapter_writes_the_comparison_origin_for_a_comparison_call` |
| 1 | `comparison_attempt_id` not passed to `insert_task` | red: the same two (`KeyError: 'comparison_attempt_id'`) |
| 1 | origin always `"comparison_call"` | red: `test_a_runs_call_is_written_exactly_as_before` |
| 1 | discriminator is `run_id is None` instead of the attempt id | red: `test_a_call_with_no_context_is_a_run_call_not_a_comparison_call` |
| 2 unit | the settler loop removed (the pre-fix source) | red: `test_a_cancelled_item_asks_the_settler_about_the_lost_attempt_before_it_ends` |
| 2 unit | `any(...)` instead of the loop | red: `test_every_settler_is_asked_for_a_cancelled_item_even_after_one_says_yes` |
| 2 unit | settlers asked after the item ends | red: the ordering test |
| 2 unit | the settlers' answer decides (`spend_unknown` instead of `cancelled`) | red: the ordering test |
| 2 unit | only the first settler asked | red: the every-settler test |
| 2 integration | loop removed | red: 3 (`test_a_cancelled_item_asks_every_settler...`, `test_a_settler_runs_in_the_reclaim_transaction...`, `test_a_cancel_that_arrives_with_a_lost_lease_is_settled_by_the_queues_reclaim_too`) |
| 2 integration | `any(...)` instead of the loop | red: `test_a_cancelled_item_asks_every_settler...` |
| 2 integration | the answer ends a cancelled item `spend_unknown` | red: that test and the spend test |
| 3 | `"upload_kind": "comparison_pdf",` removed (the base) | red: `compared == set(changed) | {"manifest"}` |
| 3 | the value set to the default `"portal_bundle"` | red: the `!=` loop (`replace(...) != base`) |
| 4 | the call removed (the base) | red: 3 of 4 (`missing_required_input`, `version_classification_required`, and `{}` for the other-section version) |
| 4 | the call moved after the classification check | red: the unclassified-version test |
| 4 | the refusal widened to every version | red: the portal-version test |

## 6. Findings, deviations and open items

1. **One hunk outside the brief's list.** `tests/integration/comparison/spend/test_reclaim_spend_unknown.py` is not in the lane's own paths, but its test `test_a_cancel_that_arrives_with_a_lost_lease_is_not_settled_by_the_queue_but_by_the_next_call` pinned the defect of item 2 (it asserted the call stayed `sent` after the reclaim), so it cannot stay green once the defect is fixed. The lane replaced that one test (and one docstring) and listed the file in its task file; **the integrator is asked to ratify the hunk**. No other file of that directory changed.
2. **`any(...)` stays in the `spend_unknown` branch.** With one registered settler it is equivalent; with several, a `True` from an earlier one would skip the later ones there too. The cancel branch does not have the problem (a loop). Left alone as a non-goal; one line if a second settler is ever registered.
3. **Not covered by a test: `PullAdapter` driving real `executor_task` rows with a comparison context.** The repository half is tested against PostgreSQL (`tests/integration/comparison/spend/test_comparison_task_origin.py`) and the adapter half container-free; the two meet in the shape CHECK of `0038`, which the argument lists in `_write_task` satisfy (a comparison call has no run, run attempt, model call or probe). A caller lane's first end-to-end test will exercise it. The journal-to-task link (`attach_task`) is still a later lane's.
4. **Commit trailer.** The wave brief (rule 8) names `Co-Authored-By: Claude Sonnet 4.6`; the lane followed it although the session runs on another Sonnet build. The integrator may rewrite the trailer on merge.
5. **No premise failed.** All four defects reproduced as the reports stated them (task file, P-02).

## 7. Instructions for the integrator

1. Merge `agent/cmp-c0-fix-01` into `integration/compare-modules`; the changes touch no wiring file (`bootstrap/**`, `comparison/public.py`, the routers), so nothing overlaps another lane's hunks.
2. Ratify the one test hunk of section 6, item 1, or ask for it to be redone differently.
3. Strike the four items from the open-items lists of `CMP-SPEND-01` (section 8 items 2 and 3, section 9 item 2) and `CMP-INGEST-01` (section 6 items 8 and 9).
4. Tell the lanes that call a model: a comparison call's context carries `comparison_attempt_id` and `remaining_seconds()` (section 2).
5. The lane's stack `auditmanager-cmp-c0-fix-01` was brought down with `make down`; its two volumes `auditmanager-cmp-c0-fix-01-postgres-data` and `auditmanager-cmp-c0-fix-01-s3-data` were removed by exact name; no container, volume or network of the lane remains.

## 8. Proof that the forbidden hotspots were not touched

`git diff --name-only ae5873e9..HEAD` lists only: the executor adapter `src/auditmanager/executors/pull.py`; the queue repository `src/auditmanager/comparison/work/repository.py`; `src/auditmanager/runs/v3_group.py`; the test files `tests/unit/comparison/spend/test_wiring_and_pins.py`, `tests/unit/comparison/work/test_reclaim_settlers_unit.py`, `tests/unit/executors/test_pull_comparison_origin.py`, `tests/integration/comparison/work/test_lease_reclaim.py`, `tests/integration/comparison/spend/test_reclaim_spend_unknown.py` (section 6, item 1), `tests/integration/documents/test_version_record_equality.py`, `tests/integration/runs/test_v3_group_refuses_a_comparison_only_version.py`; and the two documents. Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/bootstrap/`, `src/auditmanager/comparison/public.py`, `src/auditmanager/comparison/spend/`, `src/auditmanager/executors/runner_repository.py`, `src/auditmanager/runs/commands.py`, `web/`, `infra/`, `pyproject.toml`, `uv.lock` or `web/FRONTEND_LOCK.json`; no `conftest.py`.
