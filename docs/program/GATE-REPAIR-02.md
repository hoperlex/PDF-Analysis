# GATE-REPAIR-02 — the four reds of the second complete gate on `7cb317b0`, and the qa_w55b flake

Task: `docs/program/tasks/GATE-REPAIR-02.md` (and the integrator's addendum: a minimal fix in
`src/auditmanager/{jobs,workers,runs}` was granted if the cause were there; it was not, so **no
`src/**` file changed**). Branch `agent/gate-repair-01`, fast-forwarded to `origin/dev` `b1154df2`
before work. Lane `auditmanager-gate-repair` (PostgreSQL 57600, MinIO 61400/61401, QA child
28520/28521). Debt `D-190` reopened by the gate; `D-189` touched.

## Result

All four reds are test-side and each has a cause that is shown, not guessed. Neither is a regression
of `f6fce7eb`/`9d116215` or of the access/storage slice: the four tests pass in isolation and fail
only inside the battery, for two different reasons that the battery's order creates.

| red in the gate | cause | repair (tests only) |
|---|---|---|
| `workers/test_worker_service.py` three tests (`wakes_the_worker_before_its_poll`, `drain_finishes_the_run_in_flight_and_claims_no_more`, `intake_off_leaves_new_runs_queued_and_on_resumes`) | the served child of `qa_w55b` (the in-process claimant of `EXECUTION_ROLE=all`) lived to the end of the pytest **session** and claimed the queued runs of the directories that follow it (`recovery`, `runs`, `shared_kernel`, `workers`), failing them | `qa_w55b/conftest.py`: the child is stopped when the last test of the directory ends; `qa_support.ApiControl` parks the Jobs other suites left queued while the child lives and gives them back |
| `jobs/test_d141_final_transaction_keeps_the_lease.py` test 2 | the text stage runs a full `gc.collect()` per page; after the eight directories before `jobs` the process heap makes that cost seconds with the GIL held, so the lease heartbeat never beats and the lease ends | the test freezes the collector for its duration (`gc.freeze()`/`gc.unfreeze()`), asserts a collection is then cheap, and cancels its run in a `finally` |
| `qa_w55b/test_p1_upload_to_version.py` test 11 (run 1 only) | not reproduced; the same family as the first row (see below) | the same parking |

## The three workers reds

* The file alone, on a fresh lane database: **11 passed**, rc 0 (`w1`).
* `qa_w55b/test_p1_upload_to_version.py` then `workers/test_worker_service.py`, one process (`w2`,
  37 s): **3 failed, 28 passed**: `test_the_api_role_claims_nothing_and_the_worker_runs_it`,
  `test_drain_finishes_the_run_in_flight_and_claims_no_more` (`assert 'failed' == 'queued'`),
  `test_intake_off_leaves_new_runs_queued_and_on_resumes` (`assert 'failed' == 'published'`). The
  gate's three differ by one test; the shape is the same.
* The failed runs: `audit_run.state = failed`, `terminal_reason = analysis_failed`, the Job
  `queued -> cancelled`, the run `queued -> failed`, **no Attempt row** (events 304-306 of the lane
  database: `job.priority_changed`, `job.transition queued->cancelled`, `audit_run.transition
  queued->failed`).
* Who did it, shown by a scratch script (`gr-child-steals.py`): the harness's own `ApiControl`
  started the child on 28520/28521, one worker-suite-style run was queued by the helpers, and after
  6 s the run was `failed / analysis_failed`, the Job `cancelled`, 0 attempts; the child's log:
  `DomainError: the run's pinned analysis profile is not registered in this deployment; no other
  profile is substituted` (`runs/executor.py:737 _pinned_text_profile`, through
  `carrier.run_to_terminal`: "did not reach a terminal by itself"). After `control.stop()` an
  identical queued run stays `queued`.
* Why only in the battery: `api_control` is session scoped (`qa_w55b/conftest.py`), so its
  `finally: control.stop()` ran at the end of the **session**. `GATE-FIX`/`R-125` ran the battery by
  directory, where each directory is its own session, so no earlier gate could see it.

Repair, with the before/after the integrator asked for:

| run | before | after |
|---|---|---|
| `qa_w55b/test_p1_upload_to_version.py` then `workers/test_worker_service.py`, one process | `w2`: 3 failed, 28 passed (rc 1) | `v1`: **31 passed**, 45 s (rc 0) |
| `tests/integration/qa_w52 qa_w55b recovery runs shared_kernel workers`, one process (the battery's tail) | not run on the unrepaired tree (the three reds are the gate's own) | `t1`: **894 passed**, 244 subtests, 30 min 10 s (rc 0): `qa_w55b` 78, `recovery` 308, `runs` 456, `shared_kernel` 10, `workers` 40 |
| `tests/integration/qa_w55b` alone | `m15`/`m16` of `GATE-REPAIR-01`: 78 passed | `t2`: **78 passed** in 417 s (rc 0) |

The child stays shared across the `qa_w55b` modules: it is stopped by a `pytest_runtest_teardown`
hook in `qa_w55b/conftest.py` only when `nextitem` is outside the directory (or `None`); the fixture
finalizer still calls `close()`, which is idempotent. Nothing was found that outlives its directory
elsewhere (below).

### Other things that outlive a test or a directory (item 1 of the addendum)

A grep of `tests/` for `serve.py`, `EXECUTION_ROLE`, `uvicorn`, `DurableCarrier`, `ReclaimingCarrier`,
`WorkerService(`, `Popen`, `start_serving_carrier`, `scope="session"|"module"` and `with
TestClient(`; read, not run:

| where | what | stopped at teardown? |
|---|---|---|
| `qa_w55b/conftest.py:33` `api_control` (session) | the served child, a claimant | **was not until the session ended** (repaired here) |
| `workers/test_worker_service.py:136` `start_worker` (function) | `WorkerService` | yes: `drain(30)` and `stop()` in `finally` |
| `workers/test_worker_service.py:177,326,363` | `ReclaimingCarrier` + `start_serving_carrier` | yes: `carrier.shutdown()` in `finally` (:331, :373) |
| `composition/test_the_run_leaves_the_request_thread.py:447,849` and the other carriers there | `DurableCarrier` built and never `start()`ed (inert), `shutdown()` called | yes; but the `RunCarrier` pool leaves one idle daemon thread `auditmanager-run_0` per carrier alive in the process (7 seen by the `d141` test in the prefix run: not claimants, they only run what is `submit`ted) |
| `api/test_streaming_wire_response.py:161` | `with TestClient(app)`: a lifespan that starts a carrier | yes: the context exits |
| `recovery/purge_stand.py:43` (module) | a template database and bucket | yes: dropped in `finally` |
| every other `scope="session"`/`"module"` fixture found | engines, stores, templates, accounts | none starts a thread or a process |

No leak outside `tests/integration/{qa_w55b,jobs}` was found, so nothing is reported for a grant.

## `d141`

Reproduced on my own stack, one process, fresh database: `tests/integration/{analysis, analysis_engine,
analysis_text, api, auth, composition, db, ingest, jobs}` in the battery's order (48 min):
**1 failed, 4234 passed, 3 skipped** (`a2`); the failure is the gate's:
`DomainError STALE_ATTEMPT` at `jobs/repository.py:765`, from `bind_artifacts` in
`_persist_and_bind` after `source_preparation`. The file alone, `ingest` then the file (`a1`: 740
passed) and the file under six CPU burners all pass.

What the lane database shows for that run (`GATE-REPAIR-01`'s reading, a host stall, was wrong):

* `lease.acquired_at = heartbeat_at = 21:41:54.73`: **not one heartbeat in 16 s**; `expires_at`
  21:42:02.73 (the 8 s lease); `released_at` 21:42:10.54;
* events: `stage.started source_preparation` 21:41:54.738, then the next event is the reclaimer's
  `attempt.transition running -> lost` at 21:42:10.535;
* so the main thread held the interpreter for 16 s inside the first stage while the heartbeat thread
  and the test's reclaimer, which need the GIL, could not run; the reclaimer took the lease the moment
  the main thread let go.

What held it: a run with `faulthandler.dump_traceback_later(2, repeat)` armed for the test (a
separate run, in which I had also grown the heap by hand, so the dumps prove the *stack*, not the
size): all 18 dumps over 36 s have the main thread at the top of
`analysis/stages/extraction.py::_release`, which is `page.close(); contents = []; gc.collect()`,
and the heartbeat and reclaimer threads inside psycopg (`_maybe_prepare_gen`, `_execute_send`,
`wait`). The per-page full collection holds the GIL for as long as the whole process heap takes to
traverse; a heartbeat needs the GIL back several times per beat (check out, execute, fetch,
commit), so one beat costs several collections.

Measured sizes (probe plugin `gr_leakplugin2.py`, same prefix, stopped by me at 66 % to run the
workers tests the integrator asked for first, so only the first rows exist): tracked objects after `analysis`
**424 k** (full `gc.collect()` **0.31 s**), after `analysis_engine` 430 k (0.31 s), after
`analysis_text` 436 k (0.31 s), after `api` **2.25 M** (**2.5 s**), after `auth` 2.25 M (**3.6 s**).
The battery process had 3 354 modules loaded from the start.

### Why the repair is a freeze, and what could not be shown smaller

`gc.freeze()` moves everything the process holds into a permanent generation that later collections
do not walk, so the stage's per-page collection costs what the test itself allocates, whatever ran
before it. `gc.collect()` before the freeze is the expensive one and runs in the fixture, before any
lease exists. The fixture then asserts that a collection is cheap (`LEASE_SECONDS / 4`, 2 s), so a
future heap the freeze cannot help names the collector instead of `STALE_ATTEMPT`.

Mutations, each on the real test file or a copy in `tests/integration/jobs/` removed afterwards:

| mutation | result |
|---|---|
| M-A the test without `collector_frozen`, a **modelled** collector (`gr_modelgc.py`: the stage's `gc` replaced by one that holds the GIL through `ctypes.PyDLL(None).sleep` for 1 s per 50 k unfrozen tracked objects; 181 k objects -> 3 s per page) | **1 failed** in 25.6 s: the same `STALE_ATTEMPT` at `repository.py:765`; the log shows 3 s collections back to back |
| M-B the repaired test, the same model | **2 passed** in 13 s: 17.7 k unfrozen objects, 0 s per collection |
| M-C the test without the freeze, the REAL collector, 2.0 M held simple objects (dicts of lists) | **passed**: a full collection of that heap costs **0.37 s**, not seconds |
| M-D the repaired test, the same real 2.0 M heap | 2 passed |
| earlier, before the integrator's ban: the unrepaired test with a real hand-grown heap whose full `gc.collect()` took 4.04 s | failed with the same `STALE_ATTEMPT`; killed by the integrator after its pytest summary |

**State plainly:** the failure does not appear at "2 M objects" as such. The cost of a full
collection depends on what the objects are, not on how many: 2.16 M cheap objects cost 0.37 s, and
the battery's 2.25 M real objects (modules, frames, SQLAlchemy and starlette graphs, test closures)
cost 2.5 to 3.6 s, ten times more per object. The failure appears when a collection costs about 3 s
or more with the lease at 8 s: the model at 3 s and the real hand-grown heap at 4 s both fail it, and
the battery's own heap is in that range. It cannot be shown smaller with synthetic objects; the model
is the smallest honest reproduction, and it is the mechanism the lane database and the stack dumps
show.

## The product-side number, for the debt row (item 2 of the addendum)

`analysis/stages/extraction.py::_release` runs a full `gc.collect()` after every page (`W55B-FIX`,
X-2: it keeps a 500-page vector document within the worker's memory). Measured by `gr-gc-cost.py`
(plain Python, no database):
| heap | tracked objects | one full `gc.collect()` |
|---|---|---|
| bare interpreter | 8.6 k | 0.4 ms |
| a worker-like process (imports of `runs.executor`, `workers.service`, `pdfplumber`, `boto3`, `sqlalchemy`, `psycopg`) | 122 k | **0.08 s** |
| the same plus 2.1 M simple objects | 2.12 M | 0.32 s |
| the same after `gc.freeze()` | 0 unfrozen | 0.0000 s |
| the battery's own process (the probe plugin, above) | 0.42 M / 2.25 M | 0.31 s / **2.5 to 3.6 s** |

and a heartbeat-shaped thread (a 0.25 s wait, then four steps that each need the GIL back) against a
main thread that does a little Python and then a collection that holds the GIL, 20 s each:

| collection holds the GIL | beats in 20 s | longest gap between beats |
|---|---|---|
| 0 s | 79 | 0.25 s |
| 1 s per page | 5 | **5.00 s** |
| 3 s per page | 2 | **15.00 s** |

so one beat waits for about **five** collections (the four steps and the wake-up), and the gap is
`wait + 5 x collection`.

Reading it, with the heap sizes I assume. A **worker** (`EXECUTION_ROLE=worker`, the process that
runs the stage) has no test session, no API application and no caches: I take the worker-like heap
above, 122 k objects, 0.08 s per collection. A beat is then delayed by about 5 x 0.08 = 0.4 s, and a
500-page document is 500 collections, 41 s of GIL-held time in slices of 0.08 s, against a 60 s lease
and a 20 s heartbeat (`jobs/lease.py`, `JobRepository.lease_seconds`): harmless. The lease is lost
only when `20 s + 5 x collection` exceeds 60 s, i.e. a collection of about 8 s or more. The
**all-in-one** process (`EXECUTION_ROLE=all`, the API and the claimant together) carries more: at the
battery's heap (2.25 M real objects, 2.5 to 3.6 s) a beat gap is about 32 to 38 s, inside the 60 s
lease with roughly half the margin gone; I did not measure that process's real heap. This is a
**low-severity debt row** for the register: *the per-page full collection should be generation-limited
or run every N pages, so that a large process cannot starve its own lease heartbeat*; no product
change was made here. (With the test's 8 s lease and 0.25 s heartbeat the same arithmetic gives
`0.25 + 5 x c > 8`, i.e. `c > 1.5 s`, which is why a battery-sized heap fails the test.)

## The `qa_w55b/test_p1_upload_to_version.py` flake

Test 11 of the file is `test_the_same_bundle_and_key_replay_the_same_version_and_create_nothing`,
which compares `SELECT count(*) FROM blob` and `FROM document_version` before and after the replay
(**global** counts in the shared database). Run 1's traceback was lost with the killed run, and I did
not reproduce it. **Classified: probable harness race, not independent flakiness**, because the same
child that failed the workers' runs is also a claimant of every Job left `queued` in the shared
database, and whatever runnable run another directory left behind (the gate had many: 15 `queued`
runs and 13 `running` after the tail alone) is executed in the background while a probe is counting
rows. A run that the child can execute writes `blob` rows (its artifacts). Whether one of those was
mid-flight at test 11 depends on timing, which fits "in run 1, not in run 2". The repair parks the
foreign queued Jobs while the child lives (`ApiControl.park_foreign_queue`, the step
`jobs/conftest.py::quiet_queue` already takes for its workers) and gives them back. **Not shown
failing before**: no rate, no reproduction; if it recurs after this repair the cause is something
else and the traceback is the first thing to read.

`d141` also used to leave a runnable Job behind when `execute_run` raised (its cleanup was after
the `try`/`finally`, not in it): in the gate that left a `queued` retry for the next suite's
claimant. It is now cancelled in a `finally`.

## Commands (all on the lane's own stack, `.env` sourced, output redirected, `rc` from `$?`)

Base command: `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths> -rf`
(`-p gr_leakplugin`/`gr_leakplugin2`/`gr_modelgc`/`gr_heap2m` are scratch diagnostics under the
session scratchpad, never committed). `W55B_QA_API_PORT=28520 W55B_QA_HEALTH_PORT=28521` for every
`qa_w55b` run.

| id | what | rc | result |
|---|---|---|---|
| `a1` | `ingest` then the `d141` file, fresh DB | 0 | 740 passed |
| `a2` | the eight directories before `jobs`, then `jobs`, fresh DB | 1 | 1 failed (`d141` test 2), 4234 passed, 3 skipped, 48 min |
| `w1` | `workers/test_worker_service.py` alone | 0 | 11 passed |
| `w2` | `qa_w55b/test_p1...` then `workers/test_worker_service.py`, unrepaired | 1 | 3 failed, 28 passed |
| `v1` | the same, repaired | 0 | 31 passed |
| `t1` | `qa_w52 qa_w55b recovery runs shared_kernel workers`, repaired | 0 | 894 passed, 244 subtests |
| `t2` | `qa_w55b` alone, repaired | 0 | 78 passed in 417 s |
| `y1`/`y2` | M-A / M-B | 1 / 0 | see the table |
| `z1`/`z2` | M-C / M-D | 0 / 0 | see the table |
| `x2` | the `d141` file repaired, alone | 0 | 2 passed |
| `d141-battery` | not re-run in the battery: 48 min; the mechanism is shown by M-A/M-B and the stack dumps | | |
| contract battery | `pytest tests/contract` with the three ignores, on the clean tree | 0 | 983 passed, 19283 subtests passed, measured on the clean committed tree of the report's own commit |
| `git diff --check` | | 0 | clean |

## Not exercised

* The `d141` repair was **not** re-run behind the eight preceding directories (48 min, the
  deadline); it was run alone and with the modelled and the synthetic heaps. The next complete gate is
  its measurement.
* No complete gate, no pressure test beyond the one the integrator stopped.
* The product's `_release` was not changed, and the all-in-one process's real heap was not measured.
* `D-189`'s harness and `d141`'s numbers from `GATE-REPAIR-01` stand; the 8 s / 12 s margin stays
  (harmless, 15 s per run).

## Changed files

- `docs/program/GATE-REPAIR-02.md`
- `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py`
- `tests/integration/qa_w55b/conftest.py`
- `tests/integration/qa_w55b/qa_support.py`

Nothing under `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `tests/support/**`, `tests/conftest.py`, `tests/e2e/**`, `web/**`, `docs/program/CURRENT_STATE.md` or `docs/program/DEBT_REGISTER.md`; no ref, tag or stand touched. `git diff --name-only b1154df2..HEAD` is exactly the list above.
