# PROD-11D-V3-GROUP-QUEUE-01 — the AR v3 group start queues its six Runs and hands them to the carrier

Task: `docs/program/tasks/PROD-11D-V3-GROUP-QUEUE-01.md`. Branch `agent/prod-11d-v3-group-queue-01`, base `23d7e8ac` (`integration/ar-close-1026`). Defect found by `AR-V3-BETA-ACCEPT-RECORDED-01` (fact 5).

## Result

`RunAdapter.start_ar_v3_group` now does what `RunAdapter.start_run` does, six times, in the same order and under the same replay rule:

1. inside the command transaction, when the start is not a replay: for each member (scope order) `RunRepository().advance(created -> queued)` and `JobRepository().enqueue(...)`, in one transaction with the group (`D-20`: the edge is taken where the Runs are accepted; a crash after the 202 leaves claimable rows);
2. still in that transaction, the group is re-read so the 202 says `queued` (a read of the same session, no race with a worker);
3. after the commit, only when the start was not a replay: `self._carrier.submit(self._job(run_id))` for each member.

The decision (command or adapter) is the adapter, from the premise (task P-03): the ordinary start puts the edge there, the existing `tests/integration/db/test_ar_v3_run_group.py:391` pins that the domain command returns `created` Runs, and the command's contract keeps it free of the Job table and the carrier. `runs/v3_group.py` is not touched. The diff in `bootstrap/adapters.py` is 45 insertions and 11 deletions, all inside `start_ar_v3_group`.

## Files (`git diff --name-only 23d7e8ac..HEAD`)

```text
docs/program/PROD-11D-V3-GROUP-QUEUE-01.md
docs/program/tasks/PROD-11D-V3-GROUP-QUEUE-01.md
src/auditmanager/bootstrap/adapters.py                                  RunAdapter.start_ar_v3_group only
tests/integration/runs/test_v3_group_start_queues_the_runs.py           new, 8 tests
tests/integration/runs/test_v3_recorded_group_over_http.py              55 -> 64 tests
```

## The new module (8 tests, `test_v3_group_start_queues_the_runs.py`)

Stock composition (`build_application`), the sealed synthetic pack installed from a manifest file, a private migrated database, the carrier seam recorded (`HeldCarrier`, which here never forwards, so nothing executes and every reading is deterministic). One module-scoped measurement; the poller thread is not started.

| Test | Claim |
| --- | --- |
| `test_the_start_is_accepted_with_six_queued_runs` | 202, labels `F1..S2`, every member `queued` in the answer and in the database |
| `test_the_start_enqueues_one_queued_job_per_run_in_the_same_transaction` | counts group 1, Runs 6, Jobs 6; six `queued` Jobs |
| `test_the_pollers_query_finds_the_first_run_right_after_the_start` | `JobRepository.next_queued_run` returns the first Run (it returned `None` before) |
| `test_the_carrier_received_one_submission_per_run_in_scope_order` | the recorder got six jobs built by `RunAdapter._job`, one per Run, in group order |
| `test_every_submission_was_made_after_the_commit` | at each `submit`, another connection already sees that Run `queued` with a `queued` Job |
| `test_a_replay_of_the_same_key_adds_no_job_and_no_submission` | same group, no new Run or Job, Run and Job states unchanged, no new submission |
| `test_after_a_restart_the_pollers_query_finds_all_six_runs_one_after_another` | a second composition on the same database (the accepting process died after the 202) walks the poller's query: the six Runs in scope order, then nothing |
| `test_a_restarted_process_submits_nothing_by_itself_and_still_reads_queued` | the restarted adapter submitted nothing; `getArV3BetaGroup` reads six `queued` |

## Mutation proofs (source mutations on `adapters.py`, each applied alone, both modules run, then restored)

Baseline with the fix: new module 8 passed, HTTP module 64 passed. `HTTP` red counts include the cases of `test_every_check_can_fail` that go red only because the real answer no longer passes their precondition.

| Mutation | New module | HTTP module | Facts that caught it (new module) |
| --- | --- | --- | --- |
| M1 remove the `advance` | 5 failed | 14 failed | six queued Runs; poller finds the first; after-the-commit; restart walk; restarted group read |
| M2 remove the `enqueue` | 5 failed | 15 failed | the same family (no Job: nothing for the poller) |
| M3 submit on replay | 1 failed | 4 failed | replay adds no submission (also the HTTP replay and start-after facts) |
| M4 submit before commit (loop moved into the transaction) | 1 failed | 64 passed | every submission after the commit (the HTTP module does not observe commit order; the new module does) |
| M5 skip one of six in the queue loop | 6 failed | 19 failed | six queued, six Jobs, after-the-commit, replay, restart walk, restart read |
| M6 skip one of six in the submit loop | 3 failed | 19 failed | one submission per Run, after-the-commit, replay |
| M7 no submission at all | 3 failed | 63 errors in 186 s | the three submission facts. In the HTTP module nothing is ever forwarded, so the barrier waits its 180 s and the fixture fails: red, but slow |
| M8 the answer read before the edge (members `created` in the 202) | 1 failed | 1 failed | accepted with six queued Runs |

Restored: `git diff` empty after every mutation, 8 and 64 passed.

### In-module cases (9 new cases of `test_every_check_can_fail` in the HTTP module)

Each pure check passes on the real measurement and refuses one flipped fact of a deep copy: a start that left a Run `created`; a start with only five Jobs; a Job not `queued`; a start the poller's query cannot see (`None`); a start that submitted five of six; a start that submitted in another order; a replay that submitted a Run again; a replay that enqueued a seventh Job; a refusal that submitted work. 9 of 9 raise `AssertionError`.

## Before and after of the modified tests (`test_v3_recorded_group_over_http.py`; no test deleted or weakened)

| Test | Asserted before | Asserted after |
| --- | --- | --- |
| `test_the_start_creates_the_group_of_six_with_the_right_scope_labels` | members `created` x6; counts 1/6/**0** Jobs; DB states `created` | members `queued` x6; counts 1/6/**6**; DB states `queued` |
| `test_the_group_read_after_the_start_is_the_group_the_start_answered` | same group; states `created` x6 | same group; states `queued` x6 |
| fact 5, renamed `test_the_http_start_queues_the_six_runs_and_hands_them_to_the_carrier_like_start_run` (was `..._leaves_the_six_runs_created_and_unqueued_for_the_serving_poller`) | six `created`, Jobs 0, `next_queued_run` is `None` | counts 1/6/6, Run states and Job states `queued`, `next_queued_run` is the first Run, submissions equal the group's Run ids in order; a refusal submitted nothing |
| `test_the_review_read_before_the_runs_finish_says_pending` | `run_state` `created` x6, all `pending`, no review | `run_state` `queued` x6, all `pending`, no review |
| `test_a_read_while_the_first_run_is_at_the_provider_says_one_running_and_five_pending` | `running` + `created` x5 (group, review, DB) | `running` + `queued` x5 (group, review, DB); plus the first Job `leased`/`running` and the other five `queued` |
| `test_a_second_identical_start_is_the_same_group_and_creates_no_run` | same group; counts 1/6/0 | same group, `queued` x6; counts 1/6/6, Job and submission lists unchanged (`check_a_replay_adds_nothing`) |
| `test_the_same_key_with_another_version_is_a_conflict_and_creates_nothing` | nothing on the other version; counts 1/6/0 | nothing on the other version; counts 1/6/6 |
| `test_the_six_runs_reach_published_through_the_applications_own_carrier` | six `published`, six requests, call rows | the same, plus six Jobs `succeeded` |
| `test_a_start_after_the_runs_finished_is_still_the_same_group_with_no_new_work` | counts 1/6/6 (the six Jobs the carry step had created) | counts 1/6/6 (the six the start enqueued), plus no submission after the start |
| `test_every_check_can_fail` | 33 cases | 42 cases: 4 modified (`["created"]*6` -> `["queued"]*6`, `running + created x5` -> `running + queued x5`, two replay counts 0 -> 6 Jobs), 9 added |

The carry step is gone: `_drive` no longer calls `submit_existing`. The module still sits a `HeldCarrier` between the adapter and the application's own `DurableCarrier`, for the reason in the task file (an unstarted carrier runs a submitted job at once, which would move Run 1 off `queued` during the right-after-start readings); on `release()` it forwards exactly what the adapter submitted. The module itself submits nothing.

## Commands and results (lane stack, one pytest at a time, no docker, no process killed)

`P` = `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`. `Q` = the same through a private database (a script creates `prod11d_<hex>`, runs `alembic upgrade head`, points `DATABASE_URL` at it, drops it; "database left behind: 0" every time), used for suites that otherwise write into the shared lane database.

| Command | Result |
| --- | --- |
| `P tests/integration/runs/test_v3_recorded_group_over_http.py` on the base tree | 55 passed, 7.16 s |
| the same with only the adapter change | 11 failed, 44 passed (task P-04) |
| `P tests/integration/runs/test_v3_group_start_queues_the_runs.py` | 8 passed, 3.75 s |
| `P` the three v3 modules (probe, HTTP, queue), probe first and queue first | 90 passed in either order, about 21 s |
| `Q` `composition/test_the_run_leaves_the_request_thread.py`, `runs/test_input_budget_over_http.py`, `composition/test_v3_pack_install.py`, `composition/test_v3_worker_registry.py` (ordinary `start_run`, the carrier and the v3 composition) | 46 passed, 24.8 s |
| `Q` `composition/test_a_published_run_reports_itself.py`, `runs/test_w59_section_routing_over_http.py`, `composition/test_the_served_application_routes_by_section.py`, `composition/test_the_served_application_always_passes_a_budget.py`, `db/test_ar_v3_run_group.py`, `recovery/test_product_purge_run_group.py` | 49 passed, 22.4 s |
| `Q` `composition/test_every_port_implementation_is_whole.py` (slow; `bootstrap/` changed) | 32 passed, 640.75 s |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (clean committed tree) | 105 passed, 20 s |
| governance one-liner on the task file | `[]` |
| `git diff --check 23d7e8ac..HEAD` | exit 0 |

Free disk stayed between 2.1 and 2.3 GiB (above the 1.5 GiB line). No full gate and no whole `tests/integration` (`R-135`), no browser, no network. The only database found beyond this lane's own was `prod11_removal_951704a8`, which belongs to the parallel removal lane and was not touched.

## Integration notes (for the integrator)

1. Merge with `--no-ff`. The diff in `src/auditmanager/bootstrap/adapters.py` is confined to `RunAdapter.start_ar_v3_group` (the method gains a docstring, three local imports and a `work` closure); the parallel lane `PROD-11-AR-V1-V2-REMOVAL-01` edits other parts of the file. Check: `P tests/integration/runs/test_v3_group_start_queues_the_runs.py tests/integration/runs/test_v3_recorded_group_over_http.py` shows 72 passed on the lane stack.
2. The candidate debt row of `AR-V3-BETA-ACCEPT-RECORDED-01` («the AR v3 group start leaves its six Runs `created` with no Job; no served process executes them») is closed by this task. Its report (`docs/program/AR-V3-BETA-ACCEPT-RECORDED-01.md`, «A finding the integrator has to read» and the integration note 2) now describes a state that no longer exists; this lane may not edit it. The web hook comment («six queued Runs, six new queued jobs») is now literally true.
3. `bootstrap/**` changed: a named case of `AGENTS.md` section 8, deferred by `R-135` to the final gate. The targeted suites above ran.
4. Behaviour the integrator should know: the six Jobs have the default priority and are queued after any earlier Job, so a group occupies the single worker for six Runs in scope order, and an ordinary Run started afterwards waits behind them (`R-146j`, serial by design; no slot or priority was changed). The `api` role's `ReclaimingCarrier.submit` is a no-op by design: its worker service claims the committed Jobs, which now exist.

## Limits

- The served poller thread, a real worker process (`EXECUTION_ROLE=worker`) and the `api`-role reclaim-only carrier were not exercised; the claim «a served process now carries the group» rests on the poller's own repository query returning the six Runs (new module, including after a second composition), on the static reading of `DurableCarrier._poll`/`submit`, and on the HTTP module carrying all six to `published` through the application's own carrier with the Jobs the start enqueued (six `succeeded`). A long-running served process was not run.
- The right-after-start readings hold the product's submissions at `HeldCarrier`, so the carrier under test is the application's own carrier but its start is not the product's: the module forwards what the adapter submitted when it chooses.
- `M7` leaves the HTTP module red only after the 180 s barrier timeout, by design of that fixture.
- The cost of a mid-transaction failure is unchanged from `start_run`: a refusal inside the transaction rolls back the group, the Runs and the Jobs together; nothing is submitted.

## Forbidden paths untouched

```text
$ git diff --name-only 23d7e8ac..HEAD
docs/program/PROD-11D-V3-GROUP-QUEUE-01.md
docs/program/tasks/PROD-11D-V3-GROUP-QUEUE-01.md
src/auditmanager/bootstrap/adapters.py
tests/integration/runs/test_v3_group_start_queues_the_runs.py
tests/integration/runs/test_v3_recorded_group_over_http.py
```

`src/auditmanager/runs/v3_group.py`, `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency and lock files, the probe and every other existing test, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings and the ADRs are untouched; the only `src` change is inside `RunAdapter.start_ar_v3_group`.
