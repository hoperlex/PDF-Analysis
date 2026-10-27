# CMP-PROFILE-QUEUE-01 — the `page_profile` work kind: a handler on the comparison queue and the call that enqueues a version's profiles

Written 2026-10-28 by the Sonnet lane `CMP-PROFILE-QUEUE-01` (branch `agent/cmp-profile-queue-01`, base `b774856c` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-PROFILE-QUEUE-01.md`](tasks/CMP-PROFILE-QUEUE-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (4, 6, 7, 8, 9); the two parts this lane joins are [`CMP-WORK-01`](CMP-WORK-01.md) (the queue, its handler registry and outcomes) and [`CMP-PROFILE-01`](CMP-PROFILE-01.md) (`build_version_page_profiles`); the wave brief is [`dispatch/CMP-WAVE-C0.md`](dispatch/CMP-WAVE-C0.md).

## 1. Result

A version's page profiles are built by the comparison worker. `HANDLER_FACTORIES` holds one factory, `page_profile_handler`, whose handler has the kind `page_profile` (equal to `PAGE_PROFILE_WORK_KIND`). For an item `{"version_uid": "ver_..."}` it runs `build_version_page_profiles` and, **after every page**, extends the lease, proves it still holds the item and reads whether a cancel was requested; either of the two ends the build there (the page just stored stays, nothing after it is started) and the item answers `Yielded` (the queue then ends it `cancelled` when a cancel was requested and drops the answer of an attempt that lost its lease). A `ChildStartError` is the server's fault and fails the attempt with a retry; the item completes only when every page of the version has a row (`ready`, `needs_review` or `refused`). `enqueue_version_page_profiles(...)` puts a version on the queue for `CMP-INGEST-02` to call after a set is confirmed. **No contract, migration or dependency changed; no file of `comparison/work/**`, `comparison/profile/**` or the composition root was touched.**

## 2. Base facts, printed before any edit

`contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes`, `VERSION` `0.9.0`, head `0038_comparison_foundation`, base `b774856cfe640add88ba996d0fe56d08c5266a25` (`P-01` of the task file). They equal the premise of the wave brief, so the lane went on.

## 3. What was built

`src/auditmanager/comparison/profile_queue/` (new, 304 lines):

| file | what it holds |
| --- | --- |
| `handler.py` | `PageProfileHandler` (a `WorkHandler`, kind `page_profile`), its factory `page_profile_handler`, the payload (`page_profile_payload`, `read_payload`) and the five failure reasons (`REASON_PAYLOAD_INVALID`, `REASON_VERSION_NOT_FOUND`, `REASON_SOURCE_UNREADABLE`, `REASON_CHILD_START_FAILED`, `REASON_INCOMPLETE`). The constructor takes optional `runner=` (a `ChildRunner`; the builder starts its own `SubprocessChildRunner` otherwise) and `build=` (a test's stand-in for the builder) |
| `enqueue.py` | `enqueue_version_page_profiles` and `page_profile_dedupe_key` |

Wiring: `comparison/public.py` (appends of this lane's names only): the imports, `page_profile_handler` as the one member of `HANDLER_FACTORIES` (written one factory per line so that the next lane appends a line), and `PageProfileHandler`, `enqueue_version_page_profiles`, `page_profile_dedupe_key`, `page_profile_handler` in `__all__`. The comment above `HANDLER_FACTORIES` lost its last sentence ("None is registered yet"), which is no longer true.

## 4. The enqueue API (for `CMP-INGEST-02`)

```python
from auditmanager.comparison.public import enqueue_version_page_profiles, Enqueued

enqueued: Enqueued = enqueue_version_page_profiles(
    session,                      # the caller's transaction; the caller commits
    project_uid="prj_...",
    version_uid="ver_...",
    created_by_user_uid="usr_...",
    retry_failed=False,           # True: build again the pages that ended without a result
)
enqueued.work_id, enqueued.created   # created=False: a live item of the same key was returned, not doubled
```

* The item is module `versions`, kind `page_profile`, priority 0, `max_attempts` 3, payload `{"version_uid": ...}` (plus `"retry_failed": true` for a retry), dedupe key **`page_profile:<version_uid>`** (**`page_profile:<version_uid>:retry_failed`** for a retry). A live item of the same project, kind and key is returned instead of a second one (`ComparisonWorkRepository.enqueue`); once it has ended the key is free and the next call makes a new item, which finds every page stored and completes at once. A retry has a key of its own so that a live ordinary build, which would not touch the failed pages, cannot swallow it.
* Refusals before anything is written: a malformed or foreign-entity identity is `validation_failed` (`field: version_uid`); an unknown version, or one that belongs to another project, is `not_found` (the item is owned by the project and the project's erase waits for its live items, so an item that named another project's version would be filed under the wrong owner).
* The call commits nothing; a caller that rolls back leaves no item (shown).
* **Not carried: `comparison_upload_id`.** The brief's signature has none, and the item is therefore not touched by `pause_for_upload` / `resume_for_upload` / `cancel_for_upload`. If `CMP-INGEST-02` wants a cancelled upload to cancel its profile items, it adds one optional keyword to `enqueue.py` (one line, passed to `ComparisonWorkRepository.enqueue`); that file is this lane's, so it is a hunk for the integrator to take from here.

## 5. Behaviour the integrator can rely on

* **Between pages.** `build_version_page_profiles` calls `on_page` after each page it stores. The handler's `on_page` (and one call before the first page) does, in one short transaction: `WorkItem.check_current` (lock-free: the item and attempt are the current ones, the token is the attempt's, the lease is current), `ComparisonWorkRepository.heartbeat` (extends the lease on database time, refuses an expired one), and `cancel_requested` (read from the database, not only from the heartbeat thread's flag, so a build stops after the page it is on and not at the next beat). The thread's flags (`item.lease_lost`, `item.cancelled`) are looked at first and are set by the handler when it learns the same facts. The runner's own heartbeat thread keeps beating every 20 s as before; the per-page check is in addition, and is what the tests rely on (they silence the thread with an interval of an hour).
* **Outcomes.**

  | the build | the item |
  | --- | --- |
  | returns and `report.complete` | `Completed` (a page that ended without a result is a stored `needs_review` row, not a failed item) |
  | `on_page` found a cancel or a lost lease | `Yielded()`; `finish` ends the item `cancelled` for a requested cancel, drops the answer of an attempt that lost its lease (the reclaim re-queues the item) |
  | `ChildStartError` | `Failed("page_profile_child_start_failed", retry=True)` |
  | `NOT_FOUND` (unknown version) | `Failed("page_profile_version_not_found")`, no retry |
  | `ANALYSIS_INPUT_INVALID` or `STORAGE_INTEGRITY_ERROR` (no source document in the manifest, an unreadable object, bytes whose digest is not the recorded one) | `Failed("page_profile_source_unreadable", retry=True)`: a storage outage is transient, a corrupted object spends the 3 attempts and ends the item |
  | a payload that is not `{"version_uid": "ver_...", "retry_failed"?: bool}` | `Failed("page_profile_payload_invalid")`, no retry, no child started |
  | `report.complete` false (never produced by the builder with no page subset; a guard) | `Failed("page_profile_incomplete", retry=True)` |
  | anything else | not caught: the runner ends the attempt with a retryable `handler_error` and logs it |
* **Resumption.** A stopped, failed or reclaimed item costs time, not rows: the builder skips every page that has a row (unique keys of CMP-PROFILE-01), so the next item or attempt builds the pages after the last stored one and leaves the earlier rows (ids and content keys) as they were (shown for a cancel, a lost lease and a child that never started).
* **The factory costs nothing.** The registry builds a handler to learn its kind, and the shipped-tuple test of `CMP-WORK-01` builds it over an empty namespace, so the handler reads its dependencies when an item runs, not when the factory is applied.
* **Module flag.** With `AUDITMANAGER_COMPARISON_MODULES=none` (the default) the item stays `queued` and nothing runs; the worker's start check (`UnhandledKindError`) refuses a start of a build that has no handler for a live `page_profile` item of an enabled module, so the handler and the first enqueue ship in the same build, and a rollback to a build without the handler while such items are live is refused at start, by design.

## 6. Checks (light acceptance)

Commands from the lane worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src`; database tests on the lane's own PostgreSQL (`57790`) and MinIO (`61790`) after `make migrate` (head `0038`). Code tree measured: `99f506b8` (the report and the task file's handoff change nothing else).

| what | command | result |
| --- | --- | --- |
| diff hygiene | `git diff --check b774856c..HEAD` | clean (exit 0) |
| this lane's unit directory | `pytest -q tests/unit/comparison/profile_queue` | **45 passed** (handler 33, enqueue 12), no container |
| this lane's integration directory | `pytest -q tests/integration/comparison/profile_queue` | **18 passed** (end to end 2, stops/failures/retries 9, enqueue rows and dedupe 7) |
| the two together | the same two directories | **63 passed** in 15.8 s, 14.7 s and 14.9 s on three runs in a row (shared host) |
| the neighbours | `pytest -q tests/unit/comparison tests/unit/workers tests/unit/jobs tests/integration/comparison tests/integration/workers tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py tests/integration/recovery/test_grant_classification.py` | **880 passed, 1 skipped** in 170 s (the skip is not in this lane's files, whose 63 tests all pass; `CMP-WORK-01` and `CMP-PROFILE-01` recorded one skip in the same neighbours). It contains `CMP-WORK-01`'s shipped-tuple test over the now non-empty `HANDLER_FACTORIES`, its composition and worker-hosting tests, and `CMP-PROFILE-01`'s integration tests |
| contract battery | `pytest -c pyproject.toml --rootdir=. -q tests/contract --ignore=` the three `D-220` files | **1 307 passed**, 19 283 subtests, 0 failed, 133 s on the tree before this report was written. A rerun with the report still untracked had **1 failed**: `test_alpha_acceptance_command.py::test_release_command_cannot_turn_skips_recorded_mode_or_outage_into_pass`, which refuses a checkout that holds an untracked file (`FAIL: checkout содержит untracked-файлы`); it is not about this lane's code, and the rerun on the committed tree is in the next row |
| contract battery on the committed tree | the same command after the commit of this report | CONTRACT_RESULT |

Not run, by the brief and `R-135`: `make gate`, the web battery (no web change), the live journey, the whole `tests/integration/composition` directory. Disk (`df -h /`) before the container start and before each long run: 2.3 to 3.0 GiB free (the stop line is 1.5 GiB). The stack was started twice (the second time for the digest-mismatch test and its mutation) and removed twice.

**What the integration tests prove, against what.** The e2e test builds VS-1 `v1.pdf` (six sheets, the A1 plan among them) through the runner that `build_comparison_work` makes from the shipped tuple (`runner.kinds` holds `page_profile`; `verify()` passes): enqueue, claim, `execute` answers `succeeded`, six `ready` rows with their three blobs each, the stamp of every text page equals the answer key's designation, sheet number and sheet title, the scan flags equal the key's, the attempt is `succeeded`; a second enqueue after the item ended is a new item that costs time and writes no row (ids and content keys unchanged). The stop tests use the real children and the real gates with a spy that acts at a chosen `(mode, page)` call: **cancel** (the cancel requested while page 2 renders: pages 1 and 2 are stored, no child was started for page 3, the item ends `cancelled`, a later item builds pages 3 to 6 and leaves 1 and 2 as they were); **lease** (the lease expires while page 3 renders: pages 1 to 3 stored, nothing for page 4, `execute` answers `None` (the answer of a holder that lost its lease is dropped), the item is still `running` until `reclaim()` re-queues it, the next attempt finishes the version and the first three rows are unchanged); **a child that never started** (after pages 1 and 2: the attempt fails with the reason, the item is `queued`, the next attempt resumes; at page 1 three times: `queued`, `queued`, `failed` with the reason); **a page that ended without a result** (stored `needs_review` / `RENDER_FAILED` without blobs, the item `succeeded`, a plain item builds nothing, the retry item builds only that page: the other rows keep their ids); **a version unknown to the database**, **a source with no document in its manifest** and **a source whose recorded digest is not its blob's** (each retried to the budget, then `failed` with `page_profile_source_unreadable`, no child ever started) and **three payloads of the wrong shape** (failed at once, no child started).

## 7. Mutation proofs

Each row: the quoted mutation, the tests it was run against, the red result, then the file restored (`git checkout`) and the same tests green (every restored run exited 0; the tree was clean afterwards). Tool: a script that applies the replacement, runs `pytest -B -p no:cacheprovider` on the named files, restores, and runs them again. "U" is the handler or enqueue unit file, "I" an integration file of this lane.

| # | commitment | mutation | red |
| --- | --- | --- | --- |
| M1 | the kind is `page_profile` (= `PAGE_PROFILE_WORK_KIND`) | `PAGE_PROFILE_KIND = "pageprofile"` | U: 4 failed (kind, shipped tuple, both enqueue payload tests) |
| M2 | the handler is registered through `HANDLER_FACTORIES` | the factory line removed from the tuple | U 2 + I 2 failed (the worker runner has no such kind) |
| M3 | one handler per kind | the factory listed twice | U 1 + `tests/unit/comparison/work/test_handler_registry.py` 1 failed (`CMP-WORK-01`'s shipped-tuple guard) |
| M4 | a child that never started retries | `retry=True` becomes `retry=False` | U 2 + I 2 failed (attempt 2 never comes; the budget test) |
| M5 | complete only when every page has a row | `if not report.complete` becomes `if False` | U 1 failed (unit only: the real builder never returns an incomplete report) |
| M6 | a cancel stops the build between pages | the database cancel read is replaced by `False` | U 3 + I 1 failed (the cancel test builds all six pages and the item `succeeds`) |
| M7a | a lost lease stops the build | `WorkItem.check_current` skipped | U 4 failed; **I green** (the heartbeat layer still refuses an expired lease) |
| M7b | the same | the heartbeat's answer ignored | U 1 failed; **I green** (the `check_current` layer holds) |
| M7c | the same, both layers | M7a and M7b together | U 5 + I 1 failed (the lease test builds all six pages) |
| M8 | the builder is told to call back | `on_page=None` | U 7 + I 2 failed (cancel and lease tests) |
| M9 | a retry item rebuilds the failed pages | `retry_failed=False` passed on | U 1 + I 1 failed |
| M10 | a stop is looked for before the first page | the pre-build checkpoint removed | U 8 failed; I green (no integration test cancels or loses the lease before the first page) |
| M11 | an unknown version is not retried | `retry=True` on the not-found failure | U 1 + I 1 failed |
| M12 | an unreadable source is retried | `retry=False` on it | U 2 + I 2 failed (no source in the manifest; digest mismatch) |
| M13 | a payload names a `ver_` identity | the identity check removed | U 3 + I 1 failed |
| M14 | a payload holds no other key | the unknown-key refusal removed | U 2 + I 1 failed (`pages`, `path` accepted) |
| M15 | the dedupe key is per version | the version dropped from the key | U 3 + I 2 failed |
| M16 | a retry has a key of its own | the retry suffix dropped | U 2 + I 1 failed |
| M17 | a version of another project is refused | the project comparison removed | U 1 + I 1 failed |
| M18 | module `versions` | `module="stages"` | U 1 + I 1 failed |
| M19 | a retry item says so in its payload | the flag left out of the payload | U 1 + I 1 failed |
| M20 | the call commits nothing | `session.commit()` after the enqueue | U 3 + I 1 failed (`test_the_call_writes_in_the_callers_transaction_and_commits_nothing_of_its_own`) |
| M21 | the lease is extended after every page | the heartbeat replaced by `True` | U 2 failed; I green (the lease test's stop is made by the `check_current` layer) |
| M22 | the version is proved to exist | the lookup replaced by an object that says what the caller says | U 3 + I 2 failed |
| M23 | a source that is not the recorded bytes is the same failure | `STORAGE_INTEGRITY_ERROR` removed from the set of source faults | U 1 failed (`[storage_integrity_error]`); **I green**: through the real store a digest mismatch reaches the handler as `analysis_input_invalid`, so the integration test holds that member of the set and the `storage_integrity_error` member is held by the unit test alone |

The layering in M7 and M21 is shown rather than hidden: a lost lease is caught by two independent reads (`check_current` and the heartbeat's own refusal of an expired lease), so removing one leaves the integration test green and only the unit tests, which fake each layer alone, turn red; removing both turns the integration test red too. M5 is a unit proof because the builder never produces an incomplete report for a build with no page subset, which is also why the guard cannot be reached from the database. M10 and M23 are likewise unit proofs for the reasons in their rows.

## 8. Findings, deviations and limits

1. **The page is not stored under `WorkItem.require_current`.** The builder (`CMP-PROFILE-01`, forbidden for this lane) stores each page in its own transaction and knows nothing of the queue, so the fence of ADR-0025 decision 7 ("the publishing transaction locks the item") is applied here at page granularity: a worker that lost its lease or was cancelled stores **at most the page it was on** and starts no other. That page is the row a later run would write (unique keys, deterministic content, `ON CONFLICT DO NOTHING`) and `document_version` is never deleted, so nothing dangles and nothing is wrong in content; but a project erase racing a running item is held off by the item's live state, not by a lock taken in the page's transaction. If the owner wants the strict form, the builder needs a pre-store hook (a change in `comparison/profile/builder.py`).
2. **A cancel noticed after the last page ends the item `cancelled`.** The check follows every page, the last included, and a stop answers `Yielded`; `ComparisonWorkRepository.finish` lets only `Completed` win over a requested cancel. Every page is stored in that case, so a later item completes at once; the item's state says what the operator asked for.
3. **`retry_failed` is asked again at each attempt of the same item.** A page that failed again in an earlier attempt is built once more. It is bounded by the attempt budget (3) and deletes only rows that ended without a result; the alternative (apply it on attempt 1 only) would silently skip the retry when attempt 1 never reached the delete.
4. **A permanently bad source costs three attempts.** The builder raises the same `analysis_input_invalid` / `source_unreadable` for a version with no PDF in its manifest or bytes that are not the recorded ones (permanent) as for an object store that failed (transient), so the handler retries all of them and the budget ends the permanent ones with `page_profile_source_unreadable`. A storage outage that raises `dependency_unavailable` is not mapped here: it reaches the runner, which ends the attempt with a retryable `handler_error` and logs it. `CMP-INGEST-02` enqueues versions it has just written with a source document, so the permanent case is a defect, not a path.
5. **Not carried: `comparison_upload_id`** (section 4). `CMP-INGEST-02` decides whether a cancelled upload cancels its profile items.
6. **`CMP-WORK-01` §7.1 still stands.** `workers/__main__.py` must pass `comparison_work=runtime.comparison_work` to `WorkerService` for any comparison item to run in a worker process; without that integrator's line the items of this kind wait in the queue. The tests drive the runner (`claim`, `execute`, `reclaim`) directly, as `CMP-WORK-01`'s do, and the hosting by the service is `CMP-WORK-01`'s proof.
7. **Not measured:** the wall time of a whole version through a worker on the stand (the e2e test ran in 6 s on this shared host for six sheets and a three-page version, seeding included, which is a statement about the test, not about the product), a worker killed by a real signal mid-page (the tests write the state it leaves: a lease nobody renews), several workers building different versions at once.
8. The lane's database keeps the versions and page profiles the tests wrote (`document_version` refuses DELETE); it was dropped with `make down`.

## 9. Instructions for the integrator

1. Merge order is the wave's (brief §3): this lane needs `CMP-WORK-01` and `CMP-PROFILE-01` (both already on the base). The one shared-file hunk is `comparison/public.py`: an import block after `ComparisonWorkRunner`, `HANDLER_FACTORIES` as a one-member tuple with the factory on its own line, four names in `__all__`. Lanes that append their own factory add a line under it.
2. `CMP-INGEST-02` calls `enqueue_version_page_profiles(session, project_uid=, version_uid=, created_by_user_uid=)` once per version of a confirmed set, in the transaction that confirms it (section 4).
3. Apply `CMP-WORK-01` §7.1 (the `comparison_work=` argument in `workers/__main__.py`) before expecting a worker process to run the item.
4. The lane's stack was `auditmanager-cmp-profile-queue-01` (ports 57790 / 61790 / 61791); `make down` ran and its two named volumes were removed by name (section 10).

## 10. Proof that the forbidden hotspots were not touched, and the resources

`git diff --name-only b774856c..HEAD` lists 11 files, all inside the task file's allowed paths: the new `src/auditmanager/comparison/profile_queue/**` (3 files), `src/auditmanager/comparison/public.py`, `tests/unit/comparison/profile_queue/**` (2), `tests/integration/comparison/profile_queue/**` (4), this report and the task file. `git diff --name-only b774856c..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web infra Makefile src/auditmanager/comparison/work src/auditmanager/comparison/profile src/auditmanager/bootstrap src/auditmanager/workers src/auditmanager/api src/auditmanager/ingest src/auditmanager/storage src/auditmanager/jobs` prints nothing.

Containers `auditmanager-cmp-profile-queue-01-{postgres,s3,s3-init}-1` and the network `auditmanager-cmp-profile-queue-01-net` were removed with `make down`; the volumes `auditmanager-cmp-profile-queue-01-postgres-data` and `auditmanager-cmp-profile-queue-01-s3-data` were removed by those exact names (`docker ps -a`, `docker volume ls` and `docker network ls` list nothing of the lane afterwards); the lane's git-ignored `.env` was deleted. No process was killed by a pattern or at all; the only signals sent are the child runner's own `SIGKILL` of its child by PID at a wall clock, and none was needed.
