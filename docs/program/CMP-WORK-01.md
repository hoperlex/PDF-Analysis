# CMP-WORK-01 — the comparison durable queue: claim, lease, heartbeat, reclaim, pause, cancel, handler registry, worker loop

Written 2026-10-28 by the Sonnet lane `CMP-WORK-01` (branch `agent/cmp-work-01`, base `cc3dd36b` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-WORK-01.md`](tasks/CMP-WORK-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (4, 5, 6, 7, 23); the wave brief is [`dispatch/CMP-WAVE-C0.md`](dispatch/CMP-WAVE-C0.md); the tables are those the seal made ([`CMP-SEAL-C0.md`](CMP-SEAL-C0.md)).

## 1. Base facts, printed before any edit

Contract `1.9.0`, **115 paths / 130 operations / 351 schemas**, 27 error codes, `VERSION` `0.9.0`, head `0038_comparison_foundation`, base `cc3dd36b5b05b28ed0232107c8d0a437e304f07b`. They equal the brief's premise, so the lane went on. Nothing in `contracts/**` or `db/migrations/**` was changed; no column was missing.

## 2. What was built

`src/auditmanager/comparison/work/` (new, 1 272 lines):

| module | what it holds |
| --- | --- |
| `model.py` | states (pinned to the migration's constants by a test), the three typed outcomes `Completed` / `Failed(reason, retry)` / `Yielded(delay)`, `ItemAuthority` (the execution token, excluded from every `repr`), `WorkItem` (what a handler gets; `require_current` / `check_current` / `lease_lost` / `cancelled`), `WorkDependencies`, `HandlerFactory`, `SpendSettler`, the lease constants (60 s lease, 20 s heartbeat, 900 s watchdog: the `jobs` values) |
| `repository.py` | `ComparisonWorkRepository`, the only writer of `comparison_work` and `comparison_work_attempt`: `enqueue` (live dedupe key), `claim` (`FOR UPDATE ... SKIP LOCKED`), `heartbeat`, `check_current`, `require_current`, `finish`, `reclaim_expired`, `pause` / `resume`, `retry_spend_unknown`, `cancel`, `pause_for_upload` / `resume_for_upload` / `cancel_for_upload`, reads (`get`, `live_kinds`, `counts`) |
| `registry.py` | `HandlerRegistry`: one handler per `kind`; refuses a duplicate, a kind the column would refuse, a handler without `run` |
| `gates.py` | `ClaimGates`: the global pause through `execution/public.py` (`ExecutionRepository.dispatch_status`) and "a Run is claimable" through `jobs/public.py` (`JobRepository.next_queued_run`, the very hint the dispatch loop uses) |
| `heartbeat.py` | one thread per running item: extends the lease on database time, tells the handler the lease is gone or a cancel was requested, fences its own attempt past the 900 s watchdog |
| `runner.py` | `ComparisonWorkRunner`: `claim(worker_id)` (gates, then the lease), `execute(item)` (handler under a heartbeat, then `finish`), `reclaim()`, `verify()` |
| `errors.py` | `HandlerRegistryError`, `UnhandledKindError`, `WorkQueueError` |

Wiring: `workers/service.py` hosts the runner (§4); `bootstrap/composition.py` builds it (`build_comparison_work`, `WorkerRuntime.comparison_work`); `comparison/public.py` exports the names (§3); `scripts/recovery/grant_classification.py` no longer lists `comparison_work` and `comparison_work_attempt` in `SEALED_NOT_YET_WRITTEN`.

## 3. Names exported from `comparison/public.py` (for CMP-SPEND-01, CMP-INGEST-02 and later lanes)

* **Tuples a slice appends to** (the only edits other lanes make in this lane's area): `HANDLER_FACTORIES: tuple[HandlerFactory, ...]` (each factory is `Callable[[WorkDependencies], WorkHandler]`; the loop builds `{kind: handler}` and the worker refuses to start on a duplicate kind) and `SPEND_SETTLERS: tuple[SpendSettler, ...]` (`settle(session, attempt_id) -> bool`: mark the lost attempt's `prepared`/`sent` calls `unknown` and answer `True` if there were any; the item then ends `spend_unknown` and is never re-sent by itself).
* **Handler side:** `WorkHandler` (protocol: `kind: str`, `run(item) -> Outcome`), `WorkItem` (`work_id`, `attempt_id`, `attempt_no`, `project_uid`, `module`, `kind`, `payload`, `comparison_upload_id`, `created_by_user_uid`, `max_attempts`, `require_current(session)`, `check_current(session)`, `lease_lost`, `cancelled`), `WorkDependencies` (`engine`, `session_factory`, `blob_store`, `work`), `Completed`, `Failed(reason, retry=False)`, `Yielded(delay_seconds=0.0)`, `Outcome`, `ItemAuthority`.
* **Enqueue / control side:** `ComparisonWorkRepository` with `enqueue(session, *, project_uid, module, kind, payload=None, dedupe_key=None, priority=0, delay_seconds=0.0, max_attempts=3, comparison_upload_id=None, created_by_user_uid=None) -> Enqueued(work_id, created)`, `pause` / `resume` / `cancel` (answers `cancelled`, or `CANCEL_REQUESTED` for an item in flight, or the terminal state), `retry_spend_unknown`, `pause_for_upload` / `resume_for_upload` / `cancel_for_upload` (`CancelResult(cancelled, requested)`), `get` (`WorkRecord`), `counts(session, project_uid=..., upload_id=...)`, `live_kinds`; `Enqueued`, `WorkRecord`, `CancelResult`, `CANCEL_REQUESTED`.
* **Process side:** `ComparisonWorkRunner`, `HandlerRegistry`, `ClaimGates`, `default_gates`, `HandlerRegistryError`, `UnhandledKindError`, `WorkQueueError`, `HandlerFactory`, `SpendSettler`.

How a handler is written: it publishes only inside a transaction that first calls `item.require_current(session)` (the item's and its attempt's rows stay locked to the commit, so a worker that lost its lease writes nothing); it returns `Completed()`, `Failed("a_code", retry=True)` or `Yielded(delay_seconds=...)`; an item is one page or one pair, a series is enqueued item by item. `enqueue` is called from the API process, which holds no handlers, so it does not check the kind against the registry: the worker claims only kinds it has a handler for, and refuses to start while an enabled module has live items of another kind.

## 4. Behaviour the integrator can rely on

* **Priority.** The worker's dispatch loop asks for comparison work only when its own look at the Runs found *no Run to hand a slot* (a failed read or an intake that is off is not "no Run"). The runner then re-checks, in the claim itself, that no Run is claimable (`jobs/public.py`). An item in flight is never preempted: a Run waits at most one item.
* **Slots.** The item runs in the worker's pool: counted in `WorkerService.busy` and against `AUDITMANAGER_WORKER_SLOTS`; `drain` waits for it. (The ADR's "second loop the way `probe_runner` is hosted" is realised inside the dispatch loop rather than as a third thread, because the slot count has to be exact before the next look.)
* **Pause.** `execution_control.paused` stops every claim (read through `execution/public.py`; the context never queries the table). An item in flight finishes.
* **Module off.** `AUDITMANAGER_COMPARISON_MODULES` is read once by the worker's composition (an unknown value stops the start, as for the API). A module that is off *pauses its queued work by not being claimed*: the items stay `queued`, nothing is rewritten, and turning the module on resumes them with no un-pause to forget. With `none` (the default) the runner is still built: it claims nothing and **still reclaims expired leases**, so a dead worker's item never blocks a project erase because a module happens to be off.
* **Lease.** 60 s on database time, extended every 20 s by a thread of its own; past 900 s the heartbeat fences its own attempt. `reclaim_expired` (every 30 s in the worker, with the Runs' sweep): an expired attempt ends `lost`; the item returns to the queue, ends `failed` (`attempt_budget_exhausted`) when `max_attempts` is spent, `cancelled` when a cancel was requested, or `spend_unknown` when a registered settler says a call may have spent.
* **Attempt budget.** `attempt_count` counts the attempts *charged*: a claim charges one, a lost lease and a retryable failure keep the charge, a yield gives it back. Attempt rows are numbered `max(attempt_no) + 1`; none is deleted.
* **Start check.** `WorkerService.start()` calls `verify()` before it registers: live items of an enabled module whose kind has no handler refuse the start (`UnhandledKindError`). A kind registered twice stops the build of the runtime (`ConfigurationError`).

## 5. Checks (light acceptance, tree `35f7387c` plus the test-only commit after it)

| what | command | result |
| --- | --- | --- |
| diff hygiene | `git diff --check cc3dd36b..HEAD` | clean |
| this lane's unit directory | `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/work` | 76 passed, 1 xfailed (the strict pin of §7), no container |
| this lane's integration directory (own stack, head `0038`) | `... pytest -q tests/integration/comparison/work` | 60 passed; the two directories together passed three times in a row (136 passed, 1 xfailed) |
| the rest of the comparison integration suite | `DATABASE_URL=<lane> ... pytest -q tests/integration/comparison` | 239 passed (this lane's 60 included) |
| the classification guard | `... pytest -q tests/integration/recovery/test_grant_classification.py` | 35 passed |
| contract battery | `... pytest -q tests/contract --ignore=` the three `D-220` files | **1 307 passed**, 19 283 subtests, 0 failed, 192 s (includes the ALR-05 import boundary test and `tests/contract/program`) |
| neighbours of the changed `service.py` and `composition.py` | `... pytest -q tests/unit/comparison tests/unit/workers tests/unit/jobs tests/unit/shared/test_tempsweep.py tests/unit/executors/test_probe_loop.py` and `tests/integration/workers tests/integration/composition/test_router_answers.py` | 310 passed + 1 xfailed (unit side), 57 passed + 1 skipped (`tests/integration/workers` and the router answers, 44 s) |

Not run, by the brief: `make gate`, the web battery (no web change), the live journey. Disk before the runs: 2.8 GiB free on `/` (the brief's stop line is 1.5 GiB); the stack is the lane's own (`auditmanager-cmp-work-01`, ports 57720 / 61720 / 61721), brought down at the end.

## 6. Mutation proofs

Each row: the quoted mutation, the tests it was run against, the result, then the file restored (`git checkout`) and the suite green again. Tool: a script that applies the replacement, clears bytecode, runs `pytest -B -p no:cacheprovider` and restores. "Failed" counts are of the named files only.

| # | commitment | mutation | result |
| --- | --- | --- | --- |
| M1 | no double claim | the pick loses `FOR UPDATE OF w SKIP LOCKED` | `test_claim_concurrency.py`: **2 failed** (the deterministic skip test and the 8-worker / 40-item drain) |
| M2 | reclaim only after expiry | the reclaim's select *and* its in-lock re-check ignore expiry | `test_lease_reclaim.py`: **3 failed** (a live lease is taken, reaches the settlers, is fenced by the watchdog's test) |
| M3 | reclaim after expiry | the select never finds an expired lease | reclaim + hosting files: **9 failed** of 19 |
| M4 | reclaim after expiry | the attempt is fenced but the item is not re-queued | **7 failed** of 19 |
| M5 | the fence | an expired but not yet reclaimed holder may still publish (`lease_current` unchecked) | lifecycle + reclaim: **1 failed** of 35 |
| M6 | the fence | the execution token is not compared | **1 failed** |
| M7 | global pause | the runner skips the pause gate | gates (integration) + runner (unit): **5 failed** |
| M8 | global pause | the pause read always answers "not paused" | `test_claim_gates.py`: **1 failed** |
| M9 | module off | the claim ignores the module | **2 failed** |
| M10 | module off | the composition root ignores the flag (always `versions,stages`) | composition unit + wiring: **12 failed** |
| M11 | module off | the runner ignores an empty module set | **1 failed** |
| M12 | strict priority | "a Run is claimable" always answers no (the gate) | gates: **2 failed**; the service-level order test stays green (the dispatch loop's own look still takes the Run first) |
| M13 | strict priority | the runner never yields to a claimable Run | gates + hosting + runner: **5 failed**; the service-level order test again stays green |
| M33 | strict priority | M12 *and* the service asks for comparison work before it looks at the Runs | `test_worker_hosting.py`: **2 failed** (`test_runs_keep_strict_priority_at_the_service_level`, the Run that arrives while an item runs) |
| M14 | strict priority | the service asks for comparison work after an inconclusive look at the Runs | **1 failed** |
| M15 | one handler per kind | the registry accepts a second handler for a kind | **3 failed** (registry unit, composition unit, wiring) |
| M16 | one handler per kind | the shipped tuple registers one kind twice | **9 failed**, among them the shipped-tuple test |
| M17 | no kind without a handler | `verify` does not refuse an unhandled kind | **2 failed** (unit, and the worker that must refuse to start) |
| M18 | no kind without a handler | the claim takes kinds that have no handler | **1 failed** |
| M19 | slots | `busy` does not count comparison items | **4 failed** |
| M20 | slots | an item is registered after it is submitted | `test_an_item_is_counted_as_a_busy_slot_from_the_instant_it_starts`: **1 failed** (a race found while the lane was running, then fixed) |
| M21 | drain | a drain does not wait for comparison items | **4 failed** |
| M22 | reclaim in the worker | the worker's reclaim pass skips comparison leases | **3 failed** (including "module off still reclaims") |
| M23 | `SEALED_NOT_YET_WRITTEN` | the two tables put back in the set | `test_grant_classification.py`: **3 failed** |
| M24 | erase held off | the publishing transaction locks neither the item nor its attempt | **1 failed** |
| M25 | attempt budget | a yield spends the budget | **1 failed** |
| M26 | cancel | a cancel requested while the item runs is ignored at the end | **2 failed** |
| M27 | pause | an item in flight can be paused | **1 failed** |
| M28 | spend | the reclaim ignores the settlers | **1 failed** |
| M29 | dedupe | an enqueue with a live key creates a second item | **1 failed** |
| M30 | attempt budget | an exhausted budget re-queues | **1 failed** |
| M31 | heartbeat | a heartbeat that finds the lease gone does not say so | **1 failed** |
| M32 | handler fault | a handler that raises completes the item | **1 failed** |
| H1 | the pin of §7 | the integrator's one-argument hunk applied to `workers/__main__.py` | `test_entry_point_handover.py`: the strict xfail turns **red** (the assertion holds with the hunk) |

Two of the guards are layered, and the table shows it rather than hiding it: a single-layer mutation of the reclaim's expiry (M2 needs both the select and the in-lock re-check) or of the strict priority (M12 or M13 alone) leaves the other layer holding, and only the combined mutation turns the service-level test red (M33).

## 7. Findings, deviations and open items

1. **STOP item: `src/auditmanager/workers/__main__.py` is not on the brief's row.** `WorkerService` accepts `comparison_work=` and `WorkerRuntime.comparison_work` carries the runner, but the argument that joins them in `serve()` is the integrator's one line:
   `comparison_work=runtime.comparison_work,` after `probe_runner=runtime.probe_runner,`. Without it the worker process never runs comparison work (harmless today: the flag defaults to `none` and no handler is registered; fatal for the first lane that registers one). The two stand-in runtimes of `tests/unit/executors/test_probe_loop.py` (lines 79 and 117) then need `comparison_work=None`; that directory is `CMP-EXEC-IMAGES-01`'s in this wave. `tests/unit/comparison/work/test_entry_point_handover.py` is a **strict xfail** that says all of this: it turns red the moment the hunk is applied, and the marker is then removed so the test stays as the permanent pin (shown with H1).
2. **Out-of-row hunk made, minimal:** `tests/integration/recovery/test_grant_classification.py` named `comparison_work` as its example of a sealed table; it went red as soon as the table left the set (brief rule 4), so it now gives the set the table through `monkeypatch` and no longer depends on which tables the lanes have removed (the other lanes then need not touch it).
3. **A guard caught a production bug the lane had written.** The first version of `require_current` took `FOR SHARE` on the `project` row (ADR-0025 decision 7 words it so). `grant_classification` showed the code now locks `project`, which is append-only for the application role: a row lock needs the `UPDATE` privilege, so every publication would have failed with a permission error on the stand. Replaced: the item's and the attempt's rows stay locked to the commit, and the erase has to delete them before it can delete the project (`fk_comparison_work_project` is `ON DELETE RESTRICT`), so the project cannot vanish between the check and the publication (shown by a test and M24). The ADR's wording ("under a share lock") should be amended by its owner to name this.
4. **ADR decision 6, web side not built.** The read-only «Сравнение» block of «Очередь» (`web/src/widgets/execution-queue/**`) is named for this lane by the ADR, but the brief's row has no web path and no read operation exists in the contract; it stays open. `ComparisonWorkRepository.counts` and `get` are the reads such a block (and its operation) would use.
5. **Read-then-claim windows, accepted:** the pause and the "Run claimable" reads are made just before the claim transaction, not inside it (the `jobs` claim locks `execution_control`; the comparison loop does not), so an item claimed in the same millisecond that an operator pauses still runs, and a Run enqueued in that millisecond waits one item. The worker's `intake_enabled` check precedes the claim in the dispatch loop and is not under a `FOR SHARE` lock either. Both are the "one item" granularity the ADR accepts.
6. **`spend_unknown` is a hook, not a decision.** This lane provides the state change, the settler tuple and `retry_spend_unknown`; the settler that marks a call `unknown` is `CMP-SPEND-01`'s.
7. **Pre-existing race, not touched:** the Run path of `WorkerService` submits a future and registers it in `_in_flight` afterwards (the race M20 shows for the comparison path). The comparison path now submits and registers under one lock; the Run path is as it was.
8. **Not measured:** throughput of the loop (ADR decision 6 says `CMP-MEASURE-01` writes it), a worker killed by a real signal mid-item (the tests write the state a kill leaves: a lease that nobody renews), several worker processes at once beyond the eight threads of the claim test.
9. The lane's database keeps the `worker` rows that service-hosting tests registered (the registry has no delete); every item, attempt and project the tests made is removed by their fixtures.

## 8. Instructions for the integrator

1. Merge first in the wave's order (brief section 3). The hunks in shared files are small: `comparison/public.py` (an import block after `version_section_pair`, two tuples, 24 names at the top of `__all__`), `bootstrap/composition.py` (one import block, `build_comparison_work`, one field and one argument of `build_worker_runtime`), `workers/service.py` (the hook), `grant_classification.py` (two names out of the set).
2. Apply the hunk of §7.1 and remove the `xfail` marker of `test_entry_point_handover.py`.
3. Later lanes append to `HANDLER_FACTORIES` / `SPEND_SETTLERS` in `comparison/public.py` only; none of them needs a file of `comparison/work/**`.
4. `CMP-SPEND-01` uses `SPEND_SETTLERS`, `Failed` / `Completed` / `Yielded` and `item.require_current`; `CMP-INGEST-02` uses `enqueue(..., comparison_upload_id=...)`, `pause_for_upload`, `resume_for_upload`, `cancel_for_upload`, `counts(upload_id=...)`.
5. The stack of this lane is `auditmanager-cmp-work-01` (ports 57720 / 61720 / 61721); it was brought down with `make down`.

## 9. Proof that the forbidden hotspots were not touched

`git diff --name-only cc3dd36b..HEAD` lists only the paths of the task file's allowed list (and the two out-of-row paths named in section 7: the test pin in item 2, the new strict xfail in item 1, both under this lane's own or the recovery tests). Nothing under `contracts/`, `db/migrations/`, `src/auditmanager/jobs/`, `src/auditmanager/execution/`, `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/api/routers/ports.py`, `infra/`, `web/`, `pyproject.toml`, `uv.lock` or `web/FRONTEND_LOCK.json`.
