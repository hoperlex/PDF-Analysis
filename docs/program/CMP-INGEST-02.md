# CMP-INGEST-02 — the batch operations over comparison work: list, exclude, retry, pause, resume, cancel

Written 2026-10-28 by the Sonnet lane `CMP-INGEST-02` (branch `agent/cmp-ingest-02`, base `ae5873e9` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-INGEST-02.md`](tasks/CMP-INGEST-02.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (9, 10, 16); the tables and operations are those of [`CMP-SEAL-C0`](CMP-SEAL-C0.md); the upload this lane builds on is [`CMP-INGEST-01`](CMP-INGEST-01.md) section 3, the queue is [`CMP-WORK-01`](CMP-WORK-01.md), the page-profile item is [`CMP-PROFILE-QUEUE-01`](CMP-PROFILE-QUEUE-01.md) and the abort is [`CMP-STORAGE-PARTS-01`](CMP-STORAGE-PARTS-01.md).

Six sealed operations of contract `1.9.0` answer instead of `503`: `listComparisonUploads`, `excludeComparisonUploadSet`, `retryComparisonUploadSet`, `pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload`. The two enumerators that held the last stub rows (`SEALED_STUB_GETS`, `SEALED_STUB_ADDRESSED`) are empty. No contract, migration or dependency file changed; `api/routers/ports.py` and `comparison_uploads.py` already carried the six signatures and are untouched.

## 1. Base facts, printed before any edit

`git show HEAD:contracts/api/v1/openapi.json` read with `json`: contract `1.9.0`, **115 paths / 130 operations / 351 schemas**, 27 error codes; head `0038_comparison_foundation`; `HEAD` `ae5873e9` (the merge of `CMP-INGEST-01`). They equal the premise (task file P-01), so the lane went on. After the lane: `git diff --name-only ae5873e9..HEAD -- contracts db pyproject.toml uv.lock web` prints nothing.

## 2. The decision this lane had to make, and why

Two facts of the base shaped the design. (1) `CMP-INGEST-01` admits a confirmed set **in one transaction** (the document, one version per file, the set `done`), so there is no asynchronous "admitting" to pause; what a batch still has to do after a confirmation is the derived work: the page profiles of the new versions (and, in wave C1, the comparison of neighbours). (2) The contract says a pause "finishes the set it is processing and then stops", and the brief says upload pause and cancel must reach the profile items.

**One set at a time.** A confirmed set is *released*, not enqueued at confirmation: the lifecycle puts one `page_profile` item per version of the set on the queue (`enqueue_version_page_profiles(..., comparison_upload_id=...)`) **only when no item of the batch is live**. The set in hand therefore always finishes before the next one starts, and a pause is exactly "stop releasing": the item in flight and every item of the set in hand still run (shown), nothing of the next set is on the queue until the resume. `pause_for_upload` (which would pause the waiting items of the set in hand too) is deliberately **not** used by the pause (mutation `M15` shows the set-in-hand test red when it is); cancel reaches every item of the batch through `cancel_for_upload`, which is what the attachment of an item to its batch is for.

**The drive.** Something has to notice that the set in hand has ended (the queue has no completion callback, and `comparison/profile_queue/handler.py` is not this lane's). One polling item per batch, kind `comparison_batch_drive`, is enqueued when the batch is declared. It is **not attached to the batch's identity** so that the batch's own count of live items never includes it. It releases the next set, completes the batch, and cancels a batch that has been `uploading` and untouched for 24 h (the abandoned upload of the brief: its multipart parts are aborted and its slot freed exactly as a person's cancel would). It polls every 10 s while items are live and every 60 s otherwise, and ends when the batch is finished. Every action the hooks take is also taken by the drive, so a process killed between a confirmation's commit and its hook (or a declaration's and its hook) is repaired without a client.

**The sweep.** The cancel writes the database's decision in one transaction (files, parts, sets, the batch, its items) **and enqueues the work kind `upload_abort_sweep` in the same transaction** (an outbox: the abort of the store's uploads is owed durably, it is not a side effect that can be lost with the process). The sweep runs five minutes later (a part whose request began before the cancel may still be on its way; the browser edge's longest request is 290 s) and hands the tokens of the files that were never verified to `abort_multipart_sweep`. It refuses a batch that is not `cancelled`, never names a verified file and never touches a published blob.

## 3. The state machine

`uploading` → `proposed` and `proposed` → `completed` (all sets decided) are `CMP-INGEST-01`'s. This lane adds:

| act or event | from | to | what else |
| --- | --- | --- | --- |
| first confirmed set (hook, or the drive, or an exclusion that finds one) | `proposed` | `processing` | the batch's drive is ensured; the first set is released |
| pause (expert) | `processing` | `paused` | `pause_requested` true; nothing else: the set in hand finishes |
| resume (expert) | `paused` | `processing` | `pause_requested` false; the drive is ensured; the next set is released at once if none is in flight |
| drive / exclusion / resume: every set `done` or `excluded`, every `done` set released, no item of the batch live | `processing` | `completed` | |
| cancel (expert) / abandonment | `uploading`, `proposed`, `processing`, `paused` | `cancelled` | files that never completed `failed` with `batch_cancelled`; their declared and staged parts `aborted`; every set that made no versions `excluded`; waiting items of the batch cancelled, items in flight asked to stop; the sweep owed; the account's slot is free (`cancelled` is not an active state) |
| exclude a set (expert) | set `needs_confirmation` or `failed` of a `proposed`, `processing` or `paused` batch | `excluded` | the actor is kept in the set's record; a batch with nothing left to decide completes |
| retry a set (expert) | set `failed` for a retryable reason of a `proposed`, `processing` or `paused` batch | `reading` then `needs_confirmation` | the reason is cleared |

Refusals (all `409 conflict`): `comparison_upload_state` for a batch that is not in the state the act needs (pause needs `processing`, resume `paused`, cancel any active state, a set act a proposed or processing or paused batch); `comparison_set_state` for a set that is not in the state the act needs (`done`, `excluded` and `admitting` cannot be excluded; only `failed` can be retried, and only for a reason in `RETRYABLE_SET_REASONS`, which is today `comparison_sets_limit` while the batch has fewer than 100 sets that are neither `failed` nor `excluded`; every other reason is the document's or a decision's and a retry would meet it again). **No edge leaves `excluded`**: nothing in this lane asks for one and the database has none (shown).

Every act is an expert's (`require_expert` before anything is read; an administrator without `expert` is `permission_denied` and leaves nothing), keyed (the key is claimed in the transaction that acts; a repeat answers the recorded outcome with the batch's or the set's current state; a different payload under the key is `idempotency_key_reuse`; a refused act leaves no record, so the client retries under the same key when the state allows) and recorded with its actor in the command outcome (a batch has no per-act actor column and `audit_event` types are a contract registry; see section 7).

## 4. What was built

`src/auditmanager/ingest/comparison_batch/` (new, 1 097 lines; reached from outside through `public.py` only):

| module | what it holds |
| --- | --- |
| `rules.py` | the five command types, the two work kinds, the poll and grace times, the abandonment age, the retryable set reasons, the live item states |
| `repository.py` | the statements `CMP-INGEST-01`'s repository does not have: the keyset listing, the pause flag, the cancel's four updates, the open tokens, the release mark and the exclusion note of a set |
| `lifecycle.py` | `BatchLifecycle`: release a set, advance (release, complete or wait), promote a batch whose hook was missed, cancel, the drive's decision; stateless, in the caller's transaction |
| `handlers.py` | `BatchDriveHandler` (`comparison_batch_drive`) and `UploadSweepHandler` (`upload_abort_sweep`), both `WorkHandler`s; each publishes only in a transaction that first proves its attempt still holds the item |
| `service.py` | `ComparisonBatchService`: `list_uploads`, `exclude_set`, `retry_set`, `pause_upload`, `resume_upload`, `cancel_upload`, and the two hooks `after_declaration`, `after_confirmation` |
| `views.py`, `public.py` | `UploadPageView`; `BATCH_HANDLER_FACTORIES`, `ComparisonBatchService`, `BatchLifecycle` and the constants |

Outside the package (the wiring hunks of the wave brief section 1 rule 4, each minimal):

* `comparison/profile_queue/enqueue.py`: the optional keyword `comparison_upload_id` (8 lines, a docstring and one argument passed to `ComparisonWorkRepository.enqueue`). It is not part of an item's identity: the dedupe key stays `page_profile:<version_uid>`.
* `bootstrap/adapters.py`: `ComparisonUploadAdapter` takes `batches=`, its six sealed bodies are replaced (the listing's cursor is `(created_at, id)` of the last row), the hook after a declaration runs after `create_upload`, the hook after a confirmation after `confirm_set`. `import re`.
* `bootstrap/composition.py`: one import, one shared `ComparisonUploadService`, the adapter's `batches=`, and `(*COMPARISON_HANDLER_FACTORIES, *BATCH_HANDLER_FACTORIES)` in `build_comparison_work`. **The two work kinds are registered by the composition root, not appended to `comparison.public.HANDLER_FACTORIES`**: ALR-05 allows a context to import another's `public` only, so `comparison.public` could import `ingest.public` (not this lane's file) but never `ingest.comparison_batch.public`; and the batch handlers import `comparison.public`, so the reverse edge would also be a cycle. The registry still refuses a duplicate kind, and `verify()` still refuses a start that has live items of a kind it has no handler for (both shown).
* the three composition tests: `SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED` are empty, `WIRED` of `test_comparison_stub_operations.py` names the six.

## 5. Tests

Commands run from the worktree root with the lane's `.env` loaded, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider`:

| Run | Result |
| --- | --- |
| `tests/integration/ingest/comparison_batch` (the suite of this lane: the real upload service, the real runner and gates, the real handlers of this lane, a stand-in for the `page_profile` handler, PostgreSQL 17 and MinIO) | **150 passed**, 75 s = cancel 25, pause and resume 21, release and drive 21, exclude and retry 37, sweep 13, listing 11, registration 7, over HTTP 15 |
| `tests/unit/ingest/comparison_pdf tests/integration/ingest/comparison_pdf tests/unit/comparison/profile_queue tests/integration/comparison/profile_queue` (INGEST-01 and PROFILE-QUEUE, on the tree that changed their adapter and their enqueue) | **325 passed**, 146 s |
| `tests/integration/composition/{test_router_answers,test_an_absent_parent_is_not_an_empty_page,test_comparison_stub_operations,test_every_port_implementation_is_whole}.py`, `tests/integration/recovery/{test_grant_classification,test_comparison_foundation_erase,test_schema_coverage,test_blob_reference_audit}.py`, `tests/integration/api/{test_role_register,test_authorization}.py` | **287 passed, 1 skipped, 6 failed** in 1 002 s. The 6 failures are the file `test_comparison_stub_operations.py` of item 11 of section 7, **identical on the base** (6 failed, 54 passed there too, shown on the stashed base before the first edit was committed) |
| `tests/contract` minus the three `D-220` files, on the committed tree | **1307 passed**, 19283 subtests passed (130 s); the same figure the seal and `CMP-INGEST-01` recorded |
| `git diff --check ae5873e9..HEAD` | clean (exit 0) |

Not run, by `R-135` and the wave brief: the whole `tests/integration/composition` directory, the live journey, the full gate, the web battery (no web file changed).

**What the suite proves, against what.** The upload is driven through the real `ComparisonUploadService` to a state (declared, a file with its only part staged so that a multipart upload is open in the bucket, proposed with several sets, confirmed); the queue is the real `ComparisonWorkRunner` with the real gates, a worker registered in the database and the two real handlers of this lane, the only stand-in being the `page_profile` handler (which records which version it was asked for and by which batch). The bucket is read back through a plain `boto3` client for open multipart uploads and object keys; every queue row is read from the table. The decisive scenario for the pause: two sets are confirmed (Alpha with two versions, Beta with one), Alpha's first item is in flight, the batch is paused, the item finishes, **Alpha's second item still runs**, the drive polls and releases nothing, the resume releases Beta at once, Beta runs and the batch completes.

## 6. Mutation proofs

Each row: the one-occurrence replacement applied to the committed file, the named tests run (red), the file restored with `git checkout --`, `git status --short --untracked-files=no` empty, the same tests run again (green). The harness and the specifications are the lane's scratch (`mut.py`, `specs.py`); every row was run on the final code of its guard.

**The guards the brief names, and the rows that show each red:** cancel frees the slot `M01`; cancel never deletes a completed version `M02`, `M03` (the database refuses a verified file or a `done` set the cancel is made to touch, and the test reads the versions, blobs, current-version column, bucket keys and bytes back before and after the cancel and its sweep); pause stops after the current set `M14`, `M15`, `M16`, `M17`, `M18`; retry only for retryable reasons `M23`, `M24`, `M25`; exclude cannot be undone silently `M25`, `M26` (and the five edges out of `excluded` the database refuses, tested against it directly); expert-only writes `M29`; keyed replays `M30`, `M31`; the sweep `M06`-`M10`, `M13`; the drive `M11`, `M12`, `M32`-`M35`; the wiring `M37`, `M41`-`M46`.

| id | mutation | red | restored |
| --- | --- | --- | --- |
| M01 | cancel does not move the batch to cancelled (the slot stays held) | 6 failed, 1 passed | 7 passed |
| M02 | cancel also fails the files that are already verified (published bytes) | 3 failed | 3 passed |
| M03 | cancel also leaves out the sets that already made versions | 2 failed | 2 passed |
| M04 | cancel leaves the staged parts staged | 1 failed | 1 passed |
| M05 | cancel leaves no set out (a late confirmation would be admitted) | 2 failed | 2 passed |
| M06 | cancel owes no sweep | 7 failed, 13 passed | 20 passed |
| M07 | the sweep is enqueued before the batch's items are cancelled (it cancels itself) | 2 failed | 2 passed |
| M08 | the sweep never aborts anything | 7 failed, 13 passed | 20 passed |
| M09 | the sweep acts on a batch that is not cancelled | 1 failed, 1 passed | 2 passed |
| M10 | the sweep offers the token of a verified file too | 1 failed | 1 passed |
| M11 | every uploading batch is taken as abandoned | 1 failed, 2 passed | 3 passed |
| M12 | the drive publishes without proving its attempt holds the item | 1 failed | 1 passed |
| M13 | the sweep grace is zero (a part still on its way would be missed) | 1 failed | 1 passed |
| M14 | the drive releases the next set while the batch is paused | 2 failed, 1 passed | 3 passed |
| M15 | pause also pauses the waiting items (the set in hand would not finish) | 1 failed, 2 passed | 3 passed |
| M16 | pause changes nothing | 2 failed, 1 passed | 3 passed |
| M17 | the resume does not look at the queue (the next set waits for the drive) | 2 failed, 1 passed | 3 passed |
| M18 | a set is released although items of the batch are live | 2 failed, 3 passed | 5 passed |
| M19 | the batch completes while items are live | 1 failed | 1 passed |
| M20 | pause is allowed in any state | 5 failed | 5 passed |
| M21 | resume is allowed in any state | 5 failed | 5 passed |
| M22 | cancel is allowed on a finished batch | 2 failed | 2 passed |
| M23 | retry accepts any failure reason | 7 failed | 7 passed |
| M24 | retry ignores whether the batch has room | 1 failed | 1 passed |
| M25 | retry accepts a set in any state (an exclusion could be undone) | 4 failed, 5 passed | 9 passed |
| M26 | exclude accepts a set that made versions | 2 failed | 2 passed |
| M27 | exclude acts on a batch that is still uploading | 3 failed, 1 passed | 4 passed |
| M28 | the last set left out does not finish the batch | 1 failed, 2 passed | 3 passed |
| M29 | the expert check is gone from every act | 5 failed | 5 passed |
| M30 | the outcome of an act is never recorded (a replay finds the key in progress) | 5 failed | 5 passed |
| M31 | the set is not part of the payload that a key is held to | 1 failed | 1 passed |
| M32 | a confirmed set is never released by its hook | 4 failed, 5 passed | 9 passed |
| M33 | a set that was released is released again | 1 failed | 1 passed |
| M34 | the drive does not release the sets of a batch completed at its last confirmation | 1 failed | 1 passed |
| M35 | a proposed batch with a done set is not promoted (the missed hook is never repaired) | 2 failed, 2 passed | 4 passed |
| M36 | the cancel leaves the batch's waiting items alone | 2 failed | 2 passed |
| M37 | the enqueue forgets which batch an item belongs to | 3 failed, 1 passed | 4 passed |
| M38 | the listing is oldest first | 8 failed, 3 passed | 11 passed |
| M39 | the keyset repeats the last row of the previous page | 5 failed, 6 passed | 11 passed |
| M40 | the listing ignores the project | 1 failed | 1 passed |
| M41 | the adapter does not run the hook after a declaration | 1 failed | 1 passed |
| M42 | the adapter does not run the hook after a confirmation | 1 failed | 1 passed |
| M43 | the composition root registers none of the batch kinds | 1 failed | 1 passed |
| M44 | the stub row of listComparisonUploads is put back in the addressed enumerator | 1 failed, 11 passed | 12 passed |
| M45 | the stub row of the project listing is put back in the GET enumerator | 1 failed, 12 passed, 1 skipped | 13 passed, 1 skipped |
| M46 | the adapter's cancel answers the sealed stub again | 2 failed, 2 passed | 4 passed |

The mutation `M39` first hung the suite (a keyset that repeats the last row never ends its walk); the walk is now bounded and fails instead of hanging.

## 7. Risks, known limits, findings

1. **`excluded` is a state with no actor column; acts are not in `audit_event`.** The actor of each act is kept in the command outcome (`command_record.outcome.actor_user_uid`) and, for an exclusion, in the set's own record (`proposal.exclusion.by`). An `audit_event` for them needs new event types, which are a contract registry (`contracts/events/v1`), so it is a seal or FIX slot item, not this lane's.
2. **The flag «После подготовки сравнить все соседние версии» is not recorded anywhere.** The frozen contract has neither a field on `CreateComparisonUploadRequest` nor on any of the six operations (`additionalProperties: false`), and no column holds it. Wave C1, which needs it, asks the FIX slot for the field; the drive's `advance` is where its release step would also enqueue the comparison items of a prepared set.
3. **A pause is not honoured by items already on the queue for a set that was released before it.** By design: a pause stops the release of the *next* set. Wave C1's comparison items, if they are enqueued by the same release step, inherit this; if they are enqueued elsewhere they must carry the batch's identity so that `cancel_for_upload` reaches them.
4. **A part whose request began before a cancel may fail with a database refusal, not a typed conflict.** `CMP-INGEST-01`'s second transaction (`mark_part_staged`) does not re-check the batch's state; a part of a cancelled batch is `aborted` and the edge `aborted` → `staged` does not exist, so the request meets the database's undeclared-transition refusal (the catalogue code `state_transition_not_allowed`) rather than the typed `comparison_upload_state`. The bytes it sent are removed by the sweep (five minutes later, which is why the sweep waits). Not shown by a test: it needs a request that is mid-flight.
5. **A pause on a batch that is `processing` shows `paused` at once while an item of the set in hand may still be running.** The contract's words ("finishes the set it is processing and then stops") are satisfied in effect (nothing new starts, the set in hand finishes) but the state does not wait for the set to end; a client that needs "nothing is running" reads the batch's queue, which no operation exposes yet.
6. **A confirmed set of a batch that is `proposed`, `paused` or `processing` waits for the next poll if the hook does not run, up to 60 s.** A client's retry of the confirmation under the same key runs the hook at once (shown).
7. **With the module set `none` (the default) nothing of this lane's work runs**: the drive and the sweep stay `queued` (the runner claims nothing), so a batch is never completed by the drive and an abandoned upload is never swept. The six operations themselves work (the module flag does not gate them, as for `CMP-INGEST-01`). A queued item of a project blocks the project's erase until it ends (`CMP-WORK-01`'s `NON_TERMINAL_STATES`); an operator cancels the batch first, and the drive then ends itself at its next poll.
8. **Abandonment is for `uploading` only.** A `proposed` batch whose person walked away still holds the account's slot (`CMP-INGEST-01` risk 4); cancel frees it. Twenty-four hours is a constant (`ABANDON_AFTER_SECONDS`), not an owner ruling.
9. **`RETRYABLE_SET_REASONS` has one member.** `CMP-INGEST-01` writes one failed-set reason (`comparison_sets_limit`); the other reasons that a future asynchronous step may write are added to the set by the lane that writes them, with the test of its own. A non-retryable reason answers the registered `comparison_set_state`, which says "this set is not in a state this act needs": the contract's registered reasons have no word for "failed for a reason a retry cannot fix".
10. **Intra-context imports of three row types.** The package imports `UploadRow` and `SetRow` from `ingest/comparison_pdf/repository.py` (same bounded context, so ALR-05 allows it) because `comparison_pdf.public` does not export them; the other names come from its `public`. A one-line export in `comparison_pdf/public.py` removes the deep import.
11. **A pre-existing red outside this lane.** `tests/integration/composition/test_comparison_stub_operations.py` has six failures on the base `ae5873e9` and on this tree alike (the five `CMP-PROFILE-01` page reads, still listed as stubs in its register, and the tile-bounds test that asks one of them for `503`); shown by running the file on the stashed base (6 failed, 54 passed) and on this tree (6 failed, 54 passed). The lane that serves a read adds it to that file's `WIRED`; this lane added its six and left the five.
12. **Not measured:** the throughput of the drive's polling on a real worker (one claim and one attempt row per poll, 10 s while items are live and 60 s otherwise); a real worker killed mid-item (the tests write the state a kill leaves); a batch of 10 000 files (the cancel's four updates are set-based, but none was timed at that size).

## 8. Instructions for the integrator

1. **Merge position:** `WORK → STORAGE-PARTS → SPEND → EXEC-IMAGES → INGEST-ZIP → INGEST-01 → INGEST-02 → PROFILE → VERSION-MARK`. This lane's hunks in shared files: `bootstrap/adapters.py` (`ComparisonUploadAdapter`: constructor, the two hooks, the six bodies, `_upload_cursor`, `import re`), `bootstrap/composition.py` (import, `comparison_upload_service`, the adapter's `batches=`, the registry line of `build_comparison_work`), and the three composition tests (`SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED` become empty; `WIRED` gains six names, which `CMP-PROFILE-01` extends with its five).
2. **`CMP-PROFILE-01`** removes its five rows from `STUBS` the same way; with this lane's six, the register file then has no stub left and its stub test can go.
3. **Wave C1** reads `BatchLifecycle.advance` (the one place that decides "release the next set / complete") and the drive; its comparison items must carry `comparison_upload_id`.
4. **Contract notes** (a seal or FIX slot, not this lane): the `comparison_set_state` reason is used for a failed set that a retry cannot fix; the flag of item 2 of section 7; `audit_event` types of item 1.
5. **Compose and settings:** nothing new. The two work kinds claim only under a module set that names `versions` (`AUDITMANAGER_COMPARISON_MODULES`).
6. **A revert** while live items of the two kinds exist is refused by the worker's start check (`CMP-WORK-01`); cancel the batches (or let them end) first.

## 9. Forbidden hotspots

`git diff --name-only ae5873e9..HEAD` lists exactly: the task file and this report; `src/auditmanager/ingest/comparison_batch/**` (new); `src/auditmanager/comparison/profile_queue/enqueue.py` (the keyword only); the wiring hunks (`src/auditmanager/bootstrap/{adapters,composition}.py`, `tests/integration/composition/{test_router_answers,test_an_absent_parent_is_not_an_empty_page,test_comparison_stub_operations}.py`); and the lane's tests under `tests/integration/ingest/comparison_batch/`. No file of `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `web/**`, `src/auditmanager/ingest/comparison_pdf/**`, `src/auditmanager/ingest/public.py`, `src/auditmanager/storage/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/public.py`, `src/auditmanager/comparison/profile_queue/handler.py`, `src/auditmanager/workers/**`, `api/routers/**` or any `conftest.py` outside the lane's own directory.

## 10. Environment

Stack `auditmanager-cmp-ingest-02` (PostgreSQL `57770`, MinIO `61770`/`61771`, database `auditmanager_cmp_ingest_02`, bucket `auditmanager-cmp-ingest-02`), started with `make up FOUNDATION_PYTHON=/usr/bin/python3.12` and stopped with `make down` (then its two named volumes removed by name); `.env` on the lane only (git-ignored); `df -h /` before the start (3.1 G) and before every long run, never below 3.0 G; the stop line is 1.5 G. `.venv` is the shared `cmp-seal-c0` environment, used read-only; no `node_modules` was linked. No process of another lane was touched; the one background run of this lane that hung (mutation `M39`) was stopped by its task id.
