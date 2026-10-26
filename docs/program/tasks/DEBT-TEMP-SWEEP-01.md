# Task DEBT-TEMP-SWEEP-01 — a running worker reclaims a killed stage's temporaries (D-170)

task_id: DEBT-TEMP-SWEEP-01
status: completed in lane candidate `agent/debt-temp-sweep-01`, not merged

## Outcome

A worker process that stays up reclaims the stage temporaries (`am-source-*.pdf`, `am-geometry-*.pdf`, `auditmanager-bundle-*/`) a killed process left in its `/tmp`, once they are older than 1200 s (the attempt watchdog plus five minutes), at the next of its passes, which run every 300 s, and says so in its log. Before this task the only sweep ran at process start with a one-minute margin, so the files of the very kill that caused a restart stayed until some later start.

The lane brief asked for a new `shared/tempsweep.py` with a start hook. The premise was stale: the sweep, its guards, its tests and both start hooks exist since `RUN-ROBUSTNESS-01` (`jobs/temporaries.py`, P-01, P-02). This task therefore adds the one thing that was missing and does not write a second implementation of the sweep.

## Depends on

- `RUN-ROBUSTNESS-01` — completed: `jobs/temporaries.sweep_stale_temporaries`, wired at the worker's and the serving API's start.

## Frozen inputs

- domain contract: unchanged
- API contract: unchanged (shared contract `1.4.0`, 91 paths, 27 error codes)
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the sweep and both start hooks already exist; the start sweep cannot reach the leftovers of the kill that caused the restart; the API multipart spool leaves no named file

### P-01 — the sweep exists and is wired at both starts

- captured_at: 2026-10-26
- command: `git grep -n "sweep_stale_temporaries(" 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/jobs/temporaries.py:129:def sweep_stale_temporaries(
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/runs/public.py:59:        sweep_stale_temporaries()
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/workers/__main__.py:50:    sweep_stale_temporaries()
  ```
- interpretation: one definition (`jobs/temporaries.py`), one call in `start_serving_carrier` (API and all-in-one process) and one in the worker's `serve`. `src/auditmanager/shared/tempsweep.py` does not exist at the base and was not created: a second sweep with different semantics beside this one is what AGENTS.md section 4 forbids ("generic ... without proven semantics"). Its guards (exact names, age, owner, link, error handling) are the 27 tests of P-02.

### P-02 — the existing sweep is proved by 31 passing tests

- captured_at: 2026-10-26
- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/jobs/test_stale_temporaries.py tests/unit/runs/test_serving_start_sweeps_temporaries.py`
- captured_output:
  ```text
  ...............................                                          [100%]
  31 passed in 2.56s
  ```
- interpretation: young kept, stale removed, foreign names kept, links not followed, other owner skipped, one failing removal does not stop the others, and both start hooks call the sweep. Nothing in the brief's test list is missing there.

### P-03 — the start sweep never reaches the kill that caused the restart

- captured_at: 2026-10-26
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import os,shutil,tempfile;from auditmanager.jobs.temporaries import STALE_AFTER_SECONDS as S, sweep_stale_temporaries as sweep;d=tempfile.mkdtemp();p=os.path.join(d,'am-source-a1b2c3d4.pdf');open(p,'wb').write(b'x');t=os.stat(p).st_ctime;print('start-sweep threshold, s:',S);print('restart 5 s after a kill at the 900 s fence, removed:',sweep(directory=d,now=t+905).removed,'still there:',os.path.exists(p));print('a later restart 961 s after creation, removed:',sweep(directory=d,now=t+961).removed);shutil.rmtree(d)"`
- captured_output:
  ```text
  start-sweep threshold, s: 960.0
  restart 5 s after a kill at the 900 s fence, removed: () still there: True
  a later restart 961 s after creation, removed: ('am-source-a1b2c3d4.pdf',)
  ```
- interpretation: a stage's file is made after its claim and the attempt is fenced at 900 s, so a kill leaves a file at most about 900 s old; a restart within a minute sees it younger than 960 s and keeps it. It is reclaimed only by a start at least 960 s after its creation. A worker that is not restarted again keeps it for good. Whether the restarted container keeps its writable layer depends on the restart policy and the deploy; a recreated container loses it anyway. This is the gap the periodic sweep closes.

### P-04 — the API multipart spool has no name to leave behind

- captured_at: 2026-10-26
- command: `TMPDIR=$(mktemp -d) /root/projects/PDF-Analysis/.venv/bin/python -c 'import os,tempfile;f=tempfile.SpooledTemporaryFile(max_size=1<<20);f.write(b"x"*(5<<20));f.flush();print("rolled:",f._rolled,"names in TMPDIR:",os.listdir(tempfile.gettempdir()),"descriptor:",os.readlink("/proc/self/fd/%d"%f.fileno()))'`
- captured_output:
  ```text
  rolled: True names in TMPDIR: [] descriptor: <TMPDIR>/#2558 (deleted)
  ```
- interpretation: Starlette 1.6.0 (`formparsers.py:230`) spools an upload with `SpooledTemporaryFile(max_size=1 MiB)`; past the limit Python on Linux rolls it into an `O_TMPFILE` file that never has a directory entry. A `SIGKILL` of such a process (run with a private `TMPDIR`) left that directory empty, so no sweep by name could find or need to find it. `ingest/envelope.py:398` uses `tempfile.TemporaryFile()`, the same kind. The register's "not covered: the API multipart spool" is therefore a non-gap on Linux. The `auditmanager-bundle-*` directories the API makes do have names and stay covered by the start sweep only (see Integration contract). `<TMPDIR>` stands for the `mktemp -d` path.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/shared/tempsweep.py`
- `src/auditmanager/workers/service.py`
- `tests/unit/shared/test_tempsweep.py`
- `tests/integration/workers/test_worker_service.py`
- `docs/program/tasks/DEBT-TEMP-SWEEP-01.md`
- `docs/program/DEBT-TEMP-SWEEP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, root dependency and lock files, `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, `web/**`, `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`, `src/auditmanager/workers/__main__.py`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags and the deployment host.

## Non-goals

- No second implementation of the sweep: `src/auditmanager/shared/tempsweep.py` was granted and deliberately not created (P-01). `tests/integration/workers/test_worker_service.py` was granted and is unchanged: the loop is proved over the real `WorkerService.start()` with a registry and session factory that touch no database, and a DB-backed copy of the same proof would only be a test that could not be run here.
- No change to the sweep's rules (names, owner, links, age measure) in `jobs/temporaries.py`.
- No periodic sweep in the API process and no change to `workers/__main__.py` (not in the allowed paths; see Integration contract).
- No sweep of the `am-ssh-*` key directories (`executors/ssh_transport.py`, `/dev/shm`), of norms-export `incomplete-*` staging, or of anything with a name this application does not write.

## Deliverables

- `WorkerService` starts a fifth daemon thread, `auditmanager-worker-temporaries`, that calls an injectable sweep every `TEMPORARIES_SWEEP_SECONDS` (300 s) until the service stops. The default is `sweep_running_temporaries()`: `jobs.public.sweep_stale_temporaries` with `older_than = ATTEMPT_WATCHDOG_SECONDS + TEMPORARIES_LIVE_MARGIN_SECONDS` (900 + 300 s). The watchdog is imported through `jobs.public`, not copied.
- A sweep that raises is logged at ERROR with its traceback and the worker id and retried on the next pass; it never stops the worker, and the sweep's own removals and failures keep their existing log lines. A non-positive interval is refused at construction.
- `tests/unit/shared/test_tempsweep.py`: 8 tests, no database.

## Required tests

- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/shared/test_tempsweep.py tests/unit/jobs/test_stale_temporaries.py tests/unit/runs/test_serving_start_sweeps_temporaries.py tests/unit/executors/test_probe_loop.py`
- expected: 45 passed (8 + 31 + 6); `pytest --collect-only tests/integration/workers/test_worker_service.py` collects 11 tests (not run: it needs the lane database and object store).

## Integration contract

- Merge as is; no contract, migration, composition-root or dependency change. `WorkerService.__init__` gained two keyword parameters with defaults, so every existing caller is unchanged.
- The wiring is inside `workers/service.py` and needs no line in `__main__.py`. Disabling it is a revert of this commit.
- Not done, needs an owner of `src/auditmanager/runs/**` or `src/auditmanager/api/**`: the API process (`EXECUTION_ROLE` `api` and `all`) is swept only at its start, so `auditmanager-bundle-*` directories of a killed API stay until a later start. The same loop belongs beside `start_serving_carrier`; `workers.service.sweep_running_temporaries` shows the call and the margin.
- Found, not touched: `tests/contract/architecture/test_alr05_boundaries.py::test_backend_cross_context_imports_use_public_modules` is red on the base tree itself, for `workers/__main__.py:54-55` (deep imports of `auditmanager.executors.operations` and `.runtime`).

## Failure/idempotency/security cases

- A sweep pass is idempotent: a second pass over an empty directory removes nothing.
- A file a live attempt of this process could hold (younger than 1200 s) is never removed; the rule for what is removed is unchanged and unit-proved in `tests/unit/jobs/test_stale_temporaries.py`.
- A stage thread that outlives its fence and opens its temporary by name after 1200 s would find it gone; that attempt no longer holds authority, so nothing it produces can be published, and the stage's own `unlink(missing_ok=True)` tolerates the missing name.
- The thread is a daemon that sleeps on the service's stop event, so a drain or stop ends it; it reads one directory and holds no database connection.

## Rollback / feature flag

Forward-revert the commit. The thread removes only stale files this application named and is the single addition to `start()`.

## Handoff

- changed files: `src/auditmanager/workers/service.py`, `tests/unit/shared/test_tempsweep.py`, this task file, `docs/program/DEBT-TEMP-SWEEP-01.md`
- commands/results: see the report
- known limits: API process has no periodic sweep; DB-backed worker suite not run
- integration notes: see Integration contract
