# EXEC-PAR-QUEUE-01 — worker slots and one active run per executor connection

Lane `agent/exec-par-queue-01`, based on `a3e83f39`. Task file:
[`tasks/EXEC-PAR-QUEUE-01.md`](tasks/EXEC-PAR-QUEUE-01.md); decision record:
[`EXEC-PAR-DECISION-01.md`](EXEC-PAR-DECISION-01.md). No contract, migration, executor field on runs,
API or web change.

## What it does

* `AUDITMANAGER_WORKER_SLOTS` sets the worker's slot count: a plainly written whole number from 1 to
  16. **Unset is 1** (today's behaviour and the rollback). Anything else — a blank value, `0`, `17`,
  `04`, `+4`, `4.0`, non-ASCII digits — stops the process at start (`refusing to start:
  AUDITMANAGER_WORKER_SLOTS is …`, exit 2, before anything registers). It is never clamped or replaced
  by 1. Read once by `settings.load`; the composition root passes it to `WorkerService(slots=…)`.
* One executor connection has at most **one active run**. The connection of a run is the one its
  frozen revision belongs to (`audit_run.connection_revision_id` → `executor_connection_revision
  .connection_id`); a run without a connection is never limited. A queued job whose connection already
  has an active run is skipped by the hint (`next_queued_run`), so a slot is not spent on it and the
  next job in the unchanged priority-then-age order runs; the claim re-checks under a lock and a claim
  that loses raises `ExecutionNotClaimed` (`conflict`) having written nothing.

## States that count as "active"

A run is **active** while its Job is `leased`, `running` or `retry_wait`, i.e. while its Lease is
unreleased, **live or expired**. `queued` is waiting; `succeeded`, `failed`, `cancelled` and
`dead_letter` are terminal. An expired but unreleased Lease stays active until `reclaim_expired`
releases it (a killed worker's connection is not handed to a second run while the first might still
be sending). `leased` exists only inside the claim's own transaction and `retry_wait` only inside the
reclaim's, so a committed active job is in practice `running`; all three are listed so that no
committed state of an unfinished job escapes. Two revisions of one connection share its limit. The
tests read the table with their own SQL (`connection_limit_support.active_runs`), not through the code
they check.

## Atomicity

`JobRepository._claim` takes, in this order: worker-intake row (existing, `FOR SHARE`) → **the
connection's advisory transaction lock** (`pg_advisory_xact_lock(hashtextextended(
'auditmanager.executor_connection|' || connection_id, 0))`, held to the claim's commit) → the check
"another run of this connection is active" → the dispatch-control row (existing, `FOR UPDATE`) → run →
job. Every claim takes the locks in that one order. The existing control-row lock already serialises
all claim transactions, but the limit must not rest on a lock taken for another purpose, so the
connection lock and the check come **before** it: remove the lock and two claims both pass the check
(shown by the mutation table). A hash collision only serialises two connections that did not need it;
the check compares the real connection id. Runs without a connection take no lock. An inversion that
already exists is unchanged: a direct caller of a `created` run locks the run row (`advance`) before
the claim, so two claims of the *same* run could already deadlock (PostgreSQL aborts one). The new
lock adds no cycle between different runs: the holder of a connection lock asks only for the control
row and its own run and job.

## The dispatch loop (`workers/service.py`)

With one slot nothing changes. With more: after a successful hint the loop asks again at once instead
of waiting for the next poll (otherwise a second run would wait up to `POLL_SECONDS`); the runs
already handed to a slot are passed to the hint, which neither offers them again (they are still
`queued` until their slot claims) nor treats their connection as free; and a run whose claim is lost
`CLAIM_RETRY_LIMIT = 8` times in a row waits for the next timed poll. Each retry waits for the loop's
existing one-second tick, so without the bound a permanently lost claim would be retried about once a
second, forever.

The worker's database pool grows by two connections per slot beyond the first
(`pool_size = 5 + 2·(slots − 1)`, overflow 5): one slot is exactly today's pool. **This is a heuristic,
not a measurement** (see risks).

## Query plan (no index, no migration)

`EXPLAIN (ANALYZE, BUFFERS)` in a scratch database on the same PostgreSQL 17.11 container: 20 000 runs
(6 666 frozen to one of 6 revisions of 3 connections), 19 980 terminal jobs, 17 queued, 3 running.

| query | buffers | execution |
| --- | --- | --- |
| today's `_NEXT_JOB` (baseline) | 10 | 0.10 ms |
| first draft of the hint (correlated `NOT EXISTS` over `audit_run`) | 5 703 | 13.9 ms — **rejected**, it enumerated every run ever frozen to the connection and grows with the history |
| the hint as committed (`held` CTE from the active jobs and the submitted runs) | 53 | 0.45 ms |
| the claim's check (`_CONNECTION_HAS_OTHER_ACTIVE_RUN`) | 16 | 0.08 ms |

The committed plans use `ix_job_dispatch` (state prefix), `audit_run_pkey`, `uq_executor_revision_
connection`; the only sequential scan is the (tens of rows) revision table.

## Changed files

| File | Why |
| --- | --- |
| `src/auditmanager/bootstrap/settings.py` | the strict setting (`WORKER_SLOTS_ENV`, `_worker_slots`, `AppSettings.worker_slots`) — the settings module that reads worker variables |
| `src/auditmanager/bootstrap/composition.py` | `slots=resolved.worker_slots` (was the literal 1); pool sized by slots — the composition-root slot this task owns |
| `src/auditmanager/jobs/repository.py` | the hint's skip, the claim's lock and check, the definition of active |
| `src/auditmanager/workers/service.py` | immediate refill, in-flight exclusion, lost-claim bound |
| `src/auditmanager/jobs/README.md`, `src/auditmanager/workers/README.md` | boundary notes |
| `infra/deploy/compose.server.yml`, `infra/deploy/env/alpha.env.example` | the variable, by name, default 1, on the `worker` service only |
| `docs/program/PROTOTYPE_PROFILE.md`, `docs/program/DEPLOYMENT_RUNBOOK.md` | the concurrency statement and the setting (those lines only) |
| `tests/unit/workers/test_worker_slots_setting.py` | setting, composition, compose and env example (container-free) |
| `tests/integration/jobs/connection_limit_support.py`, `test_connection_limit_claim.py` | hint and claim against PostgreSQL |
| `tests/integration/workers/test_worker_slots.py` | the service with several slots against PostgreSQL |
| `tests/integration/workers/test_worker_composition.py` | **an existing test changed**: `worker − {state dir} == api − {token}` now also exempts the worker-only `AUDITMANAGER_WORKER_SLOTS`, and asserts the worker has it and the api does not (the exemption is the same kind as the state dir's; nothing was loosened for any other name) |
| `docs/program/EXEC-PAR-QUEUE-01.md` | this report |

Every path is inside the task's allowed list; none is beyond it. No `conftest.py`, `tests/support/**`,
`contracts/**`, `db/migrations/**`, lock file, `executors/**`, `runs/**`, `api/**`, `web/**` or
`CURRENT_STATE.md` was touched (`git diff --stat` below).

## Checks run

Database: one container `exec-par-queue-pg-1` (image `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`
already on the host, `127.0.0.1:58731`, data on a 512 MB tmpfs so no volume), migrated to head
`0032_ar_v3_run_group` with `alembic upgrade head`. No MinIO. `DATABASE_URL` was the only service
variable.

| Command (from the worktree, `nice -n 19`) | Result |
| --- | --- |
| `python -m pytest -q -p no:cacheprovider tests/unit/jobs tests/unit/workers tests/contract` with the gate's three `--ignore=` | see "Final run" below |
| `… tests/integration/jobs/test_connection_limit_claim.py` | 10 passed (6 repeated runs, all green, host load average 15) |
| `… tests/integration/workers/test_worker_slots.py` | 4 passed (3 runs, ~21–25 s each) |
| `… tests/integration/jobs` | 64 passed, 29 errors — **all 29 are the missing object store** (`blob_store` fixture: `S3_ENDPOINT_URL` required), 0 failed |
| `… tests/integration/workers` | 33 passed, 11 errors — all 11 the missing object store, 0 failed |
| `… tests/integration/composition/test_settings_defaults.py test_api_token_channel.py` with dummy `S3_*` | 44 passed (without `S3_*` set in the shell, 21 tests in those two files fail with `S3_ENDPOINT_URL is unset`: environment, not the change; six other composition files that read the compose file or the env example passed without it) |
| `git diff --check` | exit 0 |
| `docker compose --env-file infra/deploy/env/alpha.env.example -f infra/deploy/compose.server.yml config` | worker gets `AUDITMANAGER_WORKER_SLOTS: "1"`; `AUDITMANAGER_WORKER_SLOTS=4` in the shell gives `"4"` |

**Not run** (needs MinIO, which the lane may not start): the pre-existing MinIO-backed tests of
`tests/integration/jobs` (29) and `tests/integration/workers` (11), which exercise `run_to_terminal`
and `execute_run` through the one-slot service (including its drain, intake and reclaim tests); and any
real run on two executors. The slot tests therefore use a stand-in for `run_to_terminal` that makes the
**shipped claim** and holds the run; `execute_run`, the lease heartbeat thread and the stages with
several slots in one process were not exercised.

## Tests of the three requested behaviours

* **Concurrent claim** — `test_two_claims_of_one_connection_cannot_both_win`: the first claim is held
  open uncommitted, the second starts in a thread and is seen waiting on a lock in `pg_stat_activity`,
  then the first commits: the second must refuse, leaving its job `queued` with no attempt.
  `test_claims_racing_for_one_connection_…`: three threads on a barrier (two runs of one connection,
  one of another): exactly one of the two wins, the other connection's run is claimed.
  `test_two_slots_run_different_connections_together_…` (service, two slots, queue order x1, x2, y1):
  x1 and y1 run together, x2 stays queued while x1 runs, runs once x1 ends; never two runs of one
  connection; a second run was started with a 30 s poll, so by the immediate refill.
* **Drain** — `test_a_drain_waits_for_every_run_in_flight_and_takes_no_new_one`: with two runs in
  flight `drain` is `False` (also after one of them ended), a run queued during the drain on a free
  connection is never claimed, and after both ended `drain` is `True` with both jobs `succeeded`.
* **Reclaim** — `test_an_expired_lease_keeps_the_connection_busy_until_the_reclaim_releases_it`: an
  expired, unreleased lease keeps the connection busy (hint returns nothing, a claim for the run behind
  it is refused); after `reclaim_expired` the killed run is queued again and offered first; once
  resumed it holds the connection against the run behind it again.

## Mutation table

Each row: the code was changed as shown, the named tests ran, the file was restored with
`git checkout -- <file>` and `git diff` was empty afterwards. Rows marked † ran on the final tree
(`efdb975b`); the others on the commit that introduced the file, which has not changed since.

| # | Mutation | Tests | Result |
| --- | --- | --- | --- |
| M1a | setting accepts `0` (`1 <=` → `0 <=`) | `tests/unit/workers` | red: `[0]` |
| M1b | setting accepts `17` (`MAX + 1`) | same | red: `[17]` and the process-refuses test |
| M1c | a blank value means the default | same | red: `[""]`, `["   "]` |
| M1d | composition ignores the setting (`slots=1`) | same | red: runtime test |
| M1e | pool not sized by slots | same | red: runtime test |
| M1f | compose hard-codes `1` | same | red: compose pass-through test |
| N2 † | hint skip removed (`WHERE FALSE AND`) | `test_connection_limit_claim.py` | red: 4 tests |
| N2w † | same | `test_worker_slots.py -k two_slots` | red: "timed out after 30 s waiting for x1 and y1 to run together" (x2 is offered and lost, y1 starves) |
| N8a † | submitted runs offered again (`<> ALL(:submitted)` → `TRUE`) | claim tests | red: submitted-run test |
| N8b † | submitted runs do not hold their connection | claim tests | red: submitted-run test |
| N5a † | claim counts only a **live** lease as active | claim tests | red: expired-lease test |
| N5b † | hint counts only a **live** lease as active | claim tests | red: expired-lease test |
| F3 † | connection lock removed from the claim | claim tests | red: `cannot_both_win` (`{'result': 'claimed'}`) and the racing test (three claimed) |
| F4 † | re-check removed, lock kept | claim tests | red: 6 tests |
| F11 † | limit made global (`OR TRUE` on the connection) | claim tests | red: a different connection's claim refused |
| F6 † | `drain` does not stop claims (`_draining.set()` removed) | `test_worker_slots.py -k drain` | red: the late run started |
| F6b † | `drain` returns when one run is still in flight | same | red |
| F7 † | lost-claim bound removed | `-k bounded` | red: 9 calls, expected 8 |
| F9 † | no immediate refill (`woken = False`) | `-k two_slots` | red: second run never starts within 30 s |

## Risks and known limits

* **Raising the slot count changes nothing until runs can name an executor.** With
  `AUDITMANAGER_PROVIDER_SOURCE=database` every run today is frozen to the route's connection, so N
  slots serialise on that one connection; with `environment` runs have no connection and N slots run N
  unlimited runs against the one global proxy. The per-executor choice is `EXEC-PAR-START-01`'s.
* **Restart window.** A restarted worker's queued connection-bound runs now wait until the dead
  process's unreleased lease is reclaimed (lease 60 s plus the 30 s sweep). Before, they could start
  beside an orphan. This is the behaviour the task asks for, and it applies with one slot too, but only
  to connection-bound runs.
* **The 900 s watchdog fences but does not free the slot or stop the thread** (`reclaim_expired`
  docstring). After the fence the job is `queued` or terminal, so the connection counts as free while a
  stuck call may still be in flight, until the revision's own `timeout_seconds`. Not tested.
* The control-row lock still serialises every claim transaction (existing). Each is short; I did not
  measure its cost with 16 slots.
* The pool rule (2 connections per slot) and the database's `max_connections` were not measured on the
  stand; extraction itself is GIL-bound: for the 8-page `ar_baseline.pdf`, `extract_document` takes
  0.09 s alone, 0.27 s for two threads at once and 0.52 s for four (minimum of 3, host load average
  ~16): it does not overlap in one process, and PDFium geometry holds `PDFIUM_LOCK` per operation by
  construction (not measured). Overlap is therefore in the model wait, as the plan said.
* The host disk was at 98 % (3.2 GiB free) throughout; nothing here wrote more than the test database
  on a tmpfs.

## Instruction for the integrator

1. Merge `agent/exec-par-queue-01` (7 commits on `a3e83f39`); no rebase was done. Order against
   `EXEC-PAR-START-01` does not matter for files: this lane touches none of its paths.
2. The change touches the composition root and `infra/**`, which `AGENTS.md` §8 case 3 lists for a
   full gate; under `R-135` that gate is deferred to the series' final candidate. Run
   `tests/integration/jobs`, `tests/integration/workers` and the MinIO-backed suites there: the
   29 + 11 tests listed above were **not** run in this lane.
3. Turning it on is data: `AUDITMANAGER_WORKER_SLOTS=4` in `alpha.env` and `restart worker` (it drains
   first). Rollback: `1` or delete the line.
4. Before raising the default, measure the pool and the host with real runs (two documents, two
   executors) — the operator journey of the plan.

## Forbidden hotspots

`git diff --stat a3e83f39 HEAD -- contracts db/migrations pyproject.toml uv.lock web
src/auditmanager/executors src/auditmanager/runs src/auditmanager/api docs/program/CURRENT_STATE.md
'**/conftest.py' tests/support` prints nothing (checked on the final tree).
