# Task DEBT-RECLAIM-RECORDED-01 — prove and pin D-150 and D-152, which the code already closed

task_id: DEBT-RECLAIM-RECORDED-01
status: completed in development candidate

## Outcome

`D-150` (a recorded Run's lost Attempt must not fence the Run) and `D-152` (the serving-lifespan composition test must not depend on leftover queued Jobs) are shown, against a real lane database, to be **already implemented** by `W54-WORKER-01` (`3ff68419`, 2026-10-12); only their register rows were never struck. This task adds the tests that were missing from that closure, each shown failing under one mutation:

- a recorded `prepared` effect left by a lost Attempt is settled `not_processed`/`not_sent` and the next Attempt can claim, pass the recorded text-stage fence and prepare the call again (retryable);
- a live `prepared` effect is still settled `outcome_unknown` and fails the Run, in the independent QA file as well as in the jobs suite;
- the D-152 queue isolation is a pair of helpers pinned by deterministic leftover scenarios (late reclaim, pre-start reclaim, queued-in-between), not only by an unrepeatable race.

No product code changed: `src/auditmanager/jobs/repository.py` is untouched.

## Depends on

- `W54-WORKER-01` — completed; implemented the `reclaim_expired` rule and the D-152 test steps.
- `W54-FREEZE-01` — completed; decided D-150.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.4.0`, unchanged
- analysis/comparison/event contract: unchanged; events `provider.not_processed` and `provider.outcome_unknown` already exist
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: D-150 and D-152 are implemented at the base commit while the register still lists them as open

### P-01 — the register still lists both rows as open

- captured_at: 2026-10-25
- command: `git grep -n -E "D-150|D-152" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- docs/program/DEBT_REGISTER.md`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:docs/program/DEBT_REGISTER.md:17:**`W53-CLOSE-INT` (2026-10-12) opened `D-141` … `D-152`:** the findings of the 2026-10-12
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:docs/program/DEBT_REGISTER.md:67:| **D-150** | a recorded run's prepared effect still reclaims as `outcome_unknown` | W54 worker-service freeze |
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:docs/program/DEBT_REGISTER.md:69:| **D-152** | one composition test is order-sensitive to leftover queued Jobs | test isolation |
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:docs/program/DEBT_REGISTER.md:376:### D-152 — one composition test assumes no other queued job is claimable
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:docs/program/DEBT_REGISTER.md:401:### D-150 — a recorded run's prepared effect still reclaims as `outcome_unknown`
  ```
- interpretation: neither row is struck through, unlike `D-146` and `D-147` in the same table.

### P-02 — `reclaim_expired` already settles a recorded effect `not_processed` and ignores it as ambiguity

- captured_at: 2026-10-25
- command: `git grep -n -E "settled_recorded|provider_mode = 'recorded'|provider_mode <> 'recorded'" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/repository.py:601:            settled_recorded = session.execute(text(
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/repository.py:606:                "AND provider_mode = 'recorded' "
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/repository.py:610:            for effect in settled_recorded:
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/repository.py:622:                "AND provider_mode <> 'recorded')"
  ```
- interpretation: the rule keys on the effect row's `provider_mode`. The executor refuses an adapter whose mode differs from `audit_run.provider_mode` (`runs/executor.py`, binding check and final check), so for any effect the executor wrote the two are equal.

### P-03 — the change came with `W54-WORKER-01`

- captured_at: 2026-10-25
- command: `git log --format='%h %ad %s' --date=short -1 -S"settled_recorded" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  3ff68419 2026-10-12 feat(W54-WORKER-01): worker service, registry, intake and the API's reclaim-only role
  ```
- interpretation: the first commit that contains the settle statement; `docs/program/W54-WORKER-01.md` table row "D-150" and "D-152" names both.

### P-04 — the independent QA test already asserts the recorded outcome as `not_processed`

- captured_at: 2026-10-25
- command: `git grep -n -E "not_processed|D-150" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- tests/integration/qa_w53/test_queue_and_effect_journal.py`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/qa_w53/test_queue_and_effect_journal.py:147:    # D-150, decided at `W54-FREEZE-01`: a recorded call spends nothing, so the lost
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/qa_w53/test_queue_and_effect_journal.py:148:    # Attempt's prepared recorded effect is settled `not_processed` (not `outcome_unknown`)
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/qa_w53/test_queue_and_effect_journal.py:152:    ), {"effect": str(effect)}).scalar_one() == "not_processed"
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/qa_w53/test_queue_and_effect_journal.py:156:        and item.event_type == "provider.not_processed"
  ```
- interpretation: the QA test no longer pins `outcome_unknown`; it pins the recorded case only. The QA file had no live twin.

### P-05 — the D-152 steps already exist in the composition test

- captured_at: 2026-10-25
- command: `git grep -n -E "D-152|priority = 100|reclaim_expired" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- tests/integration/composition/test_the_run_leaves_the_request_thread.py`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:424:    D-152 (`W54-WORKER-01`): earlier suites leave Jobs behind in the shared lane da
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:434:        JobRepository().reclaim_expired(setup)
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:456:                # this run first in the dispatcher's order before unpausing (D-152)
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:467:                    "UPDATE job SET priority = 100 WHERE run_id = :run_id "
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:722:        JobRepository().reclaim_expired(observer)
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:tests/integration/composition/test_the_run_leaves_the_request_thread.py:734:        assert JobRepository().reclaim_expired(recoverer) >= 1
  ```
- interpretation: the pre-start reclaim, the second parking and the priority raise are present, but only inline in one test body and checked only by the race itself.

### P-06 — the dispatcher's order is what the priority raise relies on

- captured_at: 2026-10-25
- command: `git grep -n "ORDER BY j.priority DESC" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/repository.py:44:    "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1 "
  ```
- interpretation: among claimable Jobs, higher priority wins, then the older Job. A foreign Job created earlier with the default priority outranks an own Job with the default priority.

### P-07 — the base tree is green on the lane database

- captured_at: 2026-10-25
- command: `pytest -q -p no:cacheprovider tests/integration/jobs tests/integration/qa_w53/test_queue_and_effect_journal.py -x` then `pytest -q -p no:cacheprovider tests/integration/composition/test_the_run_leaves_the_request_thread.py`, both on the lane stack `auditmanager-debt-reclaim` at the base tree, before any edit
- captured_output:
  ```text
  86 passed in 17.55s
  13 passed, 1 warning in 11.01s
  ```
- interpretation: the existing D-150 and D-152 behaviour holds on a real database; the work left is the missing pins.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/jobs/repository.py`
- `tests/integration/jobs/test_d150_and_worker_claims.py`
- `tests/integration/qa_w53/test_queue_and_effect_journal.py`
- `tests/integration/composition/test_the_run_leaves_the_request_thread.py`
- `docs/program/tasks/DEBT-RECLAIM-RECORDED-01.md`
- `docs/program/DEBT-RECLAIM-RECORDED-01.md`

## Lane resources

- foundation_instance: `auditmanager-debt-reclaim`
- postgres_port: `58620`
- s3_api_port: `62120`
- s3_console_port: `62121`
- postgres_db: `auditmanager_debt_reclaim`
- s3_bucket: `auditmanager-debt-reclaim`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, root dependency and lock files, `src/auditmanager/bootstrap/**`, `src/auditmanager/runs/**`, `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, and any other file.

## Non-goals

- No change to `reclaim_expired` or any product code: its behaviour already matches the orchestrator's decision.
- No new state, migration or contract; no live-mode behaviour change.
- No edit of `DEBT_REGISTER.md` or `CURRENT_STATE.md`; the report proposes the register text for the orchestrator.
- No run of the combined `tests/integration/runs` + `tests/integration/composition` check that the register row names (outside the lane's bounded scope, `R-135`).

## Deliverables

- `test_a_settled_recorded_effect_lets_a_fresh_attempt_retry_the_call` in `tests/integration/jobs/test_d150_and_worker_claims.py`.
- `test_lease_reclaim_of_a_live_effect_journals_outcome_unknown` and a queued-Job assertion on the recorded case in `tests/integration/qa_w53/test_queue_and_effect_journal.py`; `_queued_run` takes a `mode`.
- In `tests/integration/composition/test_the_run_leaves_the_request_thread.py`: the helpers `_quiet_the_queue`, `_resume_with_this_run_first`, `_restore_the_queue` extracted from the serving-lifespan test (same steps, same order), and three deterministic tests: late reclaim sorts behind this run, quieting reclaims before parking, a Job queued in between is parked and remembered.
- This task file and the report `docs/program/DEBT-RECLAIM-RECORDED-01.md`, which proposes the register text.

## Required tests

- command: `pytest -q -p no:cacheprovider tests/integration/jobs tests/integration/qa_w53/test_queue_and_effect_journal.py tests/integration/composition/test_the_run_leaves_the_request_thread.py` on the lane stack
- expected: 104 passed, twice in a row on the same database
- command: the governance check of this file (`governance_findings`)
- expected: `[]`

## Integration contract

Tests only. The integrator can rely on: a recorded `prepared` effect of a lost Attempt becomes `not_processed`/`not_sent`, journalled `provider.not_processed`, and the Job returns to `queued`; a live one becomes `outcome_unknown`, journalled `provider.outcome_unknown`, and the Run fails with `provider_outcome_unknown`. On the DB lane the three paths above must be re-run on the merged candidate. The orchestrator is the only writer of `DEBT_REGISTER.md` and `CURRENT_STATE.md`.

## Failure/idempotency/security cases

- A recorded effect that completed is left `completed`; it does not block the resume (already pinned).
- A recorded effect settled `not_processed` is not a durable call: the recorded text-stage fence ignores it, the retry prepares a new effect.
- A live effect is never settled `not_processed`; the mutation that settles every mode reddens two tests.
- The new composition tests restore availability and pause state, and cancel the Runs they create, so they leave no claimable Job for a later suite.

## Rollback / feature flag

Forward revert of the test edits. No data change, no flag; nothing in product code to roll back.

## Handoff

- changed files: three test files, this task file and the report
- commands/results: see the report; bounded set 104 passed twice in a row on the lane stack
- known limits: the register's own check (combined `runs` + `composition` directories twice) was not run; the real D-152 race is timing-dependent and is pinned by its deterministic reductions
- integration notes: strike `D-150` and `D-152` using the text proposed in the report
