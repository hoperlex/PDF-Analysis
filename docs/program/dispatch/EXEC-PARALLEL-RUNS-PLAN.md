# EXEC-PARALLEL-RUNS — checks of different documents at once, each on an executor chosen in the UI

Planning record, written 2026-10-26 on `f6ee66ee` (`origin/main`). Documentation only: no slice
below is started, frozen or dispatched, and nothing here changes a contract, a migration or a
ruling. It **replaces** the cross-check plan of the same day (commits `2812e914`, `c1e04114` on
this branch), which rested on a misreading.

## What the owner asked for

«Можно запустить по одному документу проверку на одном исполнителе и параллельно другую
проверку другого документа на другом. И это было явно в UI.»

So: two runs over two different documents are in progress at the same moment, each on its own
executor connection, and the person who starts a run **sees and chooses** that executor. It is
not a cross-check of one document on several executors, and it is not image recognition.

## Facts of the tree on `f6ee66ee`

Each line was read in the code.

| Fact | Where |
| --- | --- |
| `startRun` takes `version_uid` and `provider_mode` only: a run cannot name an executor. | `contracts/api/v1/openapi.json`, schema `StartRunRequest` |
| The executor is the one global route (a primary and an optional standby for `text_analysis`), resolved at run start and frozen in `audit_run.connection_revision_id`. | `executors/resolver.py:103` (`freeze_connection`); `runs/commands.py:592`, `:816`; `bootstrap/providers.py:123` |
| The standby is used only at run start, and every use is journalled. | `executors/README.md`, «The run path» |
| The worker service already runs `slots` runs at once on a thread pool. | `workers/service.py:200`, `:236` |
| The composition root fixes `slots=1`, citing «RUN_CONCURRENCY: one run at a time». | `bootstrap/composition.py:225` |
| The owner's `R-146j` (2026-10-26) chose «один воркер без SLO». | `OWNER_RULINGS_2026-09-17.md` §3.46 |
| The queue picks the next job by priority and age and knows nothing about executors. | `jobs/repository.py`, `_NEXT_JOB` |
| Every Attempt has its own 900 s watchdog and lease; they do not interact between runs. | `jobs/lease.py:21` |
| Reading connections and routes is open to any role; writing is an administrator's act. | `api/routers/executors.py:3` |
| The start control has no selector by design (no provider-mode choice). | `web/src/features/start-run/ui/start-run-control.tsx` |
| PDFium use is serialised by the process's one lock; extraction counts the documents being read in the process at once, so it expects concurrent readers. | `ingest/envelope.py:171` (`PDFIUM_LOCK`); `analysis/stages/extraction.py:249` (`_HEAP_LOCK`) |

Consequence: the stage is one call, so the model wait is where two runs overlap. Whether
extraction and geometry rendering overlap inside one process is not established; they
serialise on `PDFIUM_LOCK` at least where PDFium is called.

## Design

1. **An explicit choice at run start.** `StartRunRequest` gets an optional
   `executor_connection_id`. Absent: today's route, unchanged. Present: the run freezes **that
   connection's current revision** through the same usability test as today (served by this
   release, probed `ok` on its current key). If it fails the test the start is refused with a
   typed `dependency_unavailable`; **an explicit choice never falls back to the standby or to
   another executor**. The choice is journalled with the start, and the run's page names the
   executor and its pinned model.
2. **Concurrency that the queue understands.**
   - The worker's slot count becomes a setting (`AUDITMANAGER_WORKER_SLOTS`, default `1`, which
     is today's behaviour and the rollback).
   - A connection has a limit `L` of simultaneously active runs (default `1`). The claim skips a
     queued job whose connection is at its limit, so a slot is never spent waiting for a busy
     executor and a second document for the same executor waits in the queue, visibly. A run
     without a choice counts against the route's connection.
   - The limit check and the claim are one atomic step (a lock per connection), proven by a
     concurrent-claim test that can fail.
3. **The UI says it.**
   - The start control gets an «Исполнитель» selector: «По умолчанию (маршрут)» and the usable
     connections, each with kind, model and the state of its last probe; an unusable one is
     shown with its reason and cannot be picked.
   - The run list and the run page show the executor of every run.
   - A queued run says which executor it is waiting for.
4. **What does not change.** One document is one run; the stage is one call; the cost ceiling,
   the 900 s watchdog and the pinned-model rule (`R-133`) are per run as before; the standby
   rule for runs without a choice is unchanged.

## Slices

One owner per shared slot (`AGENTS.md` §3). In this order:

1. `EXEC-PAR-DECISION-01`: the decision record (`docs/program/EXEC-PAR-DECISION-01.md`, done with this
   plan). It names the supersession of `R-146j` (slots), the per-connection limit and the
   no-fallback rule for an explicit choice. Documentation only.
2. `EXEC-PAR-START-01`: the optional field, `freeze_connection` for a named connection, the
   start command and its journal event. **Owns the contract slot.** The product purge and the
   event registry classify the new event (`scripts/recovery/product_purge.py` stops on an
   unclassified one). No migration is expected: `audit_run.connection_revision_id` exists.
3. `EXEC-PAR-QUEUE-01`: the slot setting and the claim with the per-connection limit.
   **Owns the composition-root slot** and, if the claim needs an index, the migration slot.
4. `EXEC-PAR-WEB-01`: the selector, the executor on the run list and page, the waiting state.
5. `EXEC-PAR-V3-01` (optional, after 2–4): the same choice for the AR v3 group, which starts six
   runs at once; one executor for the group is the proposal.

Every slice's checks include a mutation proof that its guard can fail. The journey (two
connections on one stand, two documents, two runs in progress at once) is an operator check.

## Risks

- PDFium calls serialise on one lock per process; measure two simultaneous runs before promising
  speed, and consider a second worker process instead of more slots.
- More slots mean more database connections and more load on the single host (`R-146a`);
  size the pool and measure the host before raising the default.
- A drain waits for every run in flight (at most 270 s per run today).
- A pull agent answers one task at a time by default, so the limit `L = 1` matches it.

## Owner answers (poll, 2026-10-26)

4 worker slots (default stays 1), one run at a time per executor, implement the slices. See
`docs/program/EXEC-PAR-DECISION-01.md`.

## Still open for the owner

- **How many runs at once** (the slot count), and that this supersedes `R-146j`.
- **The per-executor limit `L`.** The plan proposes `1`.
- Whether «Повторить прогон» (`reauditRun`) keeps the original run's executor (proposal: yes,
  unless the owner picks another).
- Whether the AR v3 group is in the first release (proposal: no, slice 5 later).

## Non-goals

No cross-check of one document on several executors, no image recognition, no automatic choice
of the least busy executor, no silent fallback, no change to the stage's single model call.
