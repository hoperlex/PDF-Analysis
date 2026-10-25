# DEBT-TEMP-SWEEP-01 — a running worker reclaims a killed stage's temporaries

**Debt:** `D-170`. **Base:** `354a9092`. **Task:** [`tasks/DEBT-TEMP-SWEEP-01.md`](tasks/DEBT-TEMP-SWEEP-01.md). **No contract, migration, composition-root or dependency change.**

## 1. What was found before anything was written

The lane was dispatched to add a start-time sweep of `am-source-*`, `am-geometry-*` and `auditmanager-bundle-*`. That sweep has existed since `RUN-ROBUSTNESS-01`: `jobs/temporaries.sweep_stale_temporaries`, called from `workers/__main__.py` and from `runs.public.start_serving_carrier`, with 27 unit tests of its guards and 4 of its two call sites (31 passed). The register row of D-170 already says so. A second `shared/tempsweep.py` would have been a duplicate with different semantics, so none was written.

Two real gaps remained, one of which turned out to be no gap:

| gap | finding |
|---|---|
| the sweep runs only at process start, with a margin of one minute over the 900 s watchdog | **real.** A stage's file is at most about 900 s old when its process is killed, so a restart a few seconds later sees it younger than the 960 s threshold and keeps it; only a start 960 s or more after its creation takes it. A worker that stays up never does (task P-03). |
| the API's multipart spool | **not a gap on Linux.** Starlette's `SpooledTemporaryFile` rolls into an `O_TMPFILE` file with no directory entry; after a `SIGKILL` the temporary directory was empty (task P-04). |

## 2. What changed

`src/auditmanager/workers/service.py` only (plus the tests and these two documents):

* a fifth daemon thread, `auditmanager-worker-temporaries`, calls the sweep every `TEMPORARIES_SWEEP_SECONDS` = 300 s until `stop()`;
* the default sweep is `sweep_running_temporaries()`: the existing `sweep_stale_temporaries` with `older_than = ATTEMPT_WATCHDOG_SECONDS + TEMPORARIES_LIVE_MARGIN_SECONDS` = 900 + 300 s. The margin is five minutes, not the start sweep's one, because a running worker's own attempts may hold a file; the watchdog constant comes from `jobs.public`, not a copy;
* a sweep that raises is logged at ERROR with its traceback and the worker id, and retried at the next pass; the sweep's own removals ("reclaimed N stale temporaries (B bytes)") and per-item failures keep the existing log lines;
* `WorkerService(..., temporaries_sweep=..., temporaries_sweep_seconds=...)`: both injectable, defaulted, so every existing caller is unchanged; a non-positive interval raises `ValueError`.

`workers/__main__.py` is not touched: the existing start sweep stays, the new thread is inside `WorkerService.start()`.

## 3. Verification

| command (from the lane directory) | result |
|---|---|
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/shared/test_tempsweep.py` (repeated 8 times) | 8 passed each time, ~0.8 s |
| the same plus `tests/unit/jobs/test_stale_temporaries.py tests/unit/runs/test_serving_start_sweeps_temporaries.py tests/unit/executors/test_probe_loop.py` | 45 passed |
| `pytest --collect-only tests/integration/workers/test_worker_service.py` | 11 collected, **not run** (needs the lane PostgreSQL and MinIO; none were started) |
| `governance_findings` of the task file; `task_handoff.read_task` of it | `[]`; parses, six allowed paths, base `354a9092…` |
| `tests/contract/architecture` | 2 passed, 1 failed: `test_backend_cross_context_imports_use_public_modules`, **red on the base tree too** for `workers/__main__.py:54-55` (deep imports of `executors.operations`/`.runtime`); untouched by this task |

The tests run the real `WorkerService.start()` over a registry and session factory that touch no database. Eight tests: the started worker sweeps repeatedly and stops sweeping after `stop()`; a raising sweep is logged at ERROR once and the next pass still runs; a zero or negative interval is refused (2 cases); the default sweep is the running one and the interval is minutes; the real sweep, behind a clock moved forward, keeps a file 200 s past the watchdog (which the start sweep would remove), removes the stale stage PDFs and bundle directory at 400 s and leaves `drawing-notes.pdf`; and a started worker with no sweep passed does that removal by itself.

### Mutations (each: change `workers/service.py`, run `test_tempsweep.py`, see red, revert)

| mutation | red |
|---|---|
| M1 remove the `(self._temporaries_loop, …)` entry from `start()` | `test_a_started_worker_sweeps_again_and_again…` ("only 0 sweep(s) ran") |
| M2 `while not self._stopped.wait(n):` → `while True: self._stopped.wait(n)` | same test, "the sweep went on after the service stopped" |
| M3 call the sweep with no `try/except` | `test_a_sweep_that_raises_is_logged_at_error…` ("the loop died with the sweep's first failure") |
| M3b `_log.exception(` → `_log.info(` for that failure | same test, level/`exc_info` assertion |
| M4 `older_than` = watchdog only (no live margin) | `test_the_running_sweep_leaves_what_a_live_attempt_could_still_hold` |
| M4b `TEMPORARIES_LIVE_MARGIN_SECONDS` = 1000 | `test_the_running_sweep_removes_the_stale_stage_temporaries_and_only_those` |
| M5 delete the interval check | `test_a_service_refuses_an_interval_that_would_spin[0]` |
| M6 default `temporaries_sweep` = `lambda: SweepReport()` | `test_the_default_interval_is_minutes_…` and `test_a_started_worker_with_the_default_sweep_reclaims…` |

## 4. Not done

* The **API process** is still swept only at start. A killed API leaves `auditmanager-bundle-*` directories until a later start. The loop belongs next to `start_serving_carrier` (`runs/public.py`) or in the API lifespan: both outside this lane's paths. The call is `workers.service.sweep_running_temporaries`'s body.
* `tests/integration/workers/test_worker_service.py` is unchanged; a DB-backed copy of the proof was judged not worth an unrunnable test.
* `am-ssh-*` private-key directories (`executors/ssh_transport.py`, in `/dev/shm`) are never swept; whether a container restart clears `/dev/shm` was not checked here.
* A stage thread that outlives its fence by more than 1200 s and reopens its temporary by name would find it gone; that attempt is already fenced and `unlink(missing_ok=True)` tolerates the missing name.

## 5. Proposed `D-170` register row (the register is not edited here)

```text
| ~~D-170~~ | a killed stage leaves its temporary PDF (up to 250 MiB) in the worker's `/tmp`, never reclaimed (§4.2.9; X-1 for the API's spool) | **closed 2026-10-21** by `RUN-ROBUSTNESS-01` for the worker and the serving process (`jobs/temporaries.sweep_stale_temporaries`, exact names, older than the watchdog + 60 s, at start); **the start sweep could not reach the files of the kill that caused the restart (younger than 960 s) — closed for a running worker 2026-10-26 by `DEBT-TEMP-SWEEP-01`**: a worker thread repeats the sweep every 300 s with a margin of watchdog + 300 s; the API multipart spool needs no sweep (an unnamed `O_TMPFILE` file, a killed process leaves no entry: `docs/program/tasks/DEBT-TEMP-SWEEP-01.md` P-04). **Open:** the API process has no periodic sweep, so a killed API's `auditmanager-bundle-*` directories wait for a later start; check `pytest -q tests/unit/shared/test_tempsweep.py tests/unit/jobs/test_stale_temporaries.py tests/unit/runs/test_serving_start_sweeps_temporaries.py` |
```
