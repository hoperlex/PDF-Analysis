# GATE-REPAIR-03 — the notification test observes the claim, not the end of the run

Task: `docs/program/tasks/GATE-REPAIR-03.md`. Branch `agent/gate-repair-01`, fast-forwarded to
`origin/dev` `d410ac64` (the freeze of the task file) before work. Lane `auditmanager-gate-repair`
(PostgreSQL 57600, MinIO 61400/61401). Only `tests/integration/workers/test_worker_service.py` and this
report changed; no `src/**`, in particular not the `gc.collect()` of `D-200`.

## Result

`test_a_notification_wakes_the_worker_before_its_poll` now proves what its docstring says without
depending on how long a whole run takes in the battery's process: it waits **45 s for the claim**, then
gives the run the generous bound its siblings use. The same bound was added to the siblings that waited
60 s for a run, because behind a heap that costs seconds per collection they fail the same way.

## The cause (the integrator's measurement, confirmed)

The complete gate of `c58d62f6` left one red, `workers/test_worker_service.py::test_a_notification_wakes_the_worker_before_its_poll`
(battery index 5284). The worker had claimed the run promptly; the run took 55 s (job created
01:50:04.903, `terminal_at` 01:50:59.819), the test waited 45 s for a **terminal** state. A run that
takes about 10 s in a small process takes 55 to 58 s behind the eight large directories, because the text
stage runs a full `gc.collect()` per page and that holds the GIL for as long as the whole process heap
takes to walk (`D-200`, `GATE-REPAIR-02`).

## The repair

In `tests/integration/workers/test_worker_service.py`:

* `CLAIM_SECONDS = 45.0` and `RUN_SECONDS = 180.0`, with the reason in a comment;
* a helper `_claimed(sessions, run_id)`: the Job left `queued` **and** an Attempt exists (a queued Job has
  none; `test_drain_...` asserts `attempts == 0` for one);
* the notification test: `LISTEN` up, 0.5 s past the one immediate poll, queue the run, then
  `_wait_for(_claimed, timeout=CLAIM_SECONDS, "the claim on notification")`, then
  `_wait_for(terminal, timeout=RUN_SECONDS, "the claimed run to finish")`, then `published` and one lease
  naming this worker. With the poll at 120 s only the notification can explain a claim inside the first
  window, because the one poll that matters already ran before the run was queued;
* the siblings' bound: `_wait_for`'s default 60 s becomes `RUN_SECONDS`; `gated.entered.wait(60)` (two
  tests), `worker.drain(90)` after the release, the `GatedAdapter`'s own `release.wait(90)` and the
  fixture's teardown `service.drain(30)` take the same constant, so a test that ends with a run in flight
  no longer leaves the worker stopped around a running run for the next test.

Nothing is slower when the run is quick: these are upper bounds on a wait, and every assertion after them
is unchanged. The only assertion added is the lease's worker in the notification test.

## The siblings with the same shape (item 2)

Measured, not argued: the whole file behind a collector that costs about 3 s per page, with the old
waits, `gr_modelgc.py` (the stage's `gc` replaced by one that holds the GIL through
`ctypes.PyDLL(None).sleep` for 1 s per 50 k unfrozen tracked objects; 112 modelled collections over the
file): **7 failed, 4 passed**, 514 s. A run took 63 to 70 s there; the gate's real heap made it 55 to 58 s,
so the same waits passed in the gate with a margin of 2 to 5 s.

| test | the wait that depends on a run | at the model, old waits | now |
|---|---|---|---|
| `test_the_api_role_claims_nothing_and_the_worker_runs_it` | terminal, default 60 s | failed, 69.5 s | passes, 69.8 s |
| `test_a_notification_wakes_the_worker_before_its_poll` | terminal, 45 s | failed, 51 s | passes, 68.2 s |
| `test_a_lost_listen_is_logged_and_the_poll_still_claims` | terminal, default 60 s | failed, 67.5 s | passes, 67.8 s |
| `test_drain_finishes_the_run_in_flight_and_claims_no_more` | `entered.wait(60)`, `drain(90)` | failed ("never reached the provider") | passes, 69.4 s |
| `test_intake_off_leaves_new_runs_queued_and_on_resumes` | terminal, default 60 s | failed, 69.5 s | passes, 69.6 s |
| `test_an_api_restart_leaves_the_workers_run_alone` | `entered.wait(60)`, terminal 60 s | failed ("entered.wait(timeout=60)") | passes, 68.6 s |
| `test_a_killed_workers_run_is_reclaimed_and_finished_by_another_worker` | terminal, default 60 s | failed, 63.2 s | passes, 67.7 s |

The other four tests wait on events that no run's length decides (the `LISTEN` connection 15 s, the
registry heartbeat 10 s, the API's reclaim of a killed worker's lease 20 s, the worker noticing its
vanished row 10 s) and were not touched. `test_the_api_reclaims_a_killed_workers_lease` runs no run to a
terminal at all.

## The mutation (item 3)

In `make mutation-copy MUT=/root/gate-repair-03-mut` (the copy's `auditmanager.jobs.repository` was printed
and resolved under the copy before any mutation):

* baseline, the unmutated copy, the new test: **1 passed** in 4.6 s;
* **mutation**: in `jobs/repository.py::wake_workers`, the line
  `session.execute(_NOTIFY, {"channel": JOB_WAKEUP_CHANNEL})` replaced by `return  # MUTATION: no NOTIFY`
  (one occurrence; the poll stays at 120 s): the new test **fails inside its window**:
  `AssertionError: timed out after 45 s waiting for the claim on notification`, **1 failed in 46.75 s**;
* for comparison, the old test from the base commit under the same mutation fails the same way in
  46.73 s (`... waiting for a run claimed on notification`): the repair does not weaken the guard, it moves
  the observation from the end of the run to the claim.

## Before and after (item 4), the lane's own stack

Every run: `.env` sourced, `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, output redirected,
rc from `$?`.

| run | before | after |
|---|---|---|
| the file alone | 11 passed, 36.6 s, rc 0 (measured before a session restart; the log was lost with the scratchpad, the figure is from the terminal) | 11 passed, 35.7 s, rc 0 |
| the file behind the modelled heap (3 s per page) | **7 failed**, 4 passed, 514 s, rc 1 | **11 passed**, 488 s, rc 0 |
| `tests/integration/workers` as a whole (required test) | not run | 40 passed, 40 s, rc 0 |
| the notification test alone under the NOTIFY mutation | fails at 45 s (old test) | fails at 45 s (new test) |
| `pytest tests/contract` with the three ignores, clean tree | | CONTRACT |
| `git diff --check d410ac64..HEAD` | | clean |

## Not exercised

* The real prefix (the eight large directories, 48 min) was not re-run behind the file: the next complete
  gate is that measurement. The model is harsher than the gate's heap (63 to 70 s per run against 55 to
  58 s) and every test passes behind it.
* `D-200` itself is untouched; a quicker run in the battery would need the product's per-page collection
  to change, which is the debt row, not this task.
* No ballast or memory-pressure run; the model holds the GIL and allocates nothing.

## Changed files

- `docs/program/GATE-REPAIR-03.md`
- `tests/integration/workers/test_worker_service.py`

Nothing under `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `tests/support/**`, `tests/conftest.py`, `web/**`, `docs/program/CURRENT_STATE.md` or `docs/program/DEBT_REGISTER.md`; no ref, tag or stand touched. `git diff --name-only d410ac64..HEAD` is exactly the list above.
