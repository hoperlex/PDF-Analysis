# Task CMP-WORK-01 — the comparison durable queue: claim, lease, heartbeat, reclaim, pause, cancel, handler registry, worker loop

## Outcome
On `integration/compare-modules` the comparison context owns a durable queue over the sealed tables
`comparison_work` / `comparison_work_attempt` (ADR-0025 decisions 4, 6, 7, 23): an item is enqueued, claimed once
by one worker under a lease, kept alive by a heartbeat, fenced by an execution token, reclaimed when the lease
expires, paused (queued items), cancelled and ended with a typed outcome; the worker hosts the comparison loop as a
second claimant that takes an item only when no Run is claimable, honours `execution_control.paused` and the module
flag, and holds one handler per `kind`. Each guard is shown failing under a quoted mutation.

## Depends on
- CMP-SEAL-C0 (merged on `integration/compare-modules` as `0990de4b`): contract `1.9.0`, migration `0038_comparison_foundation`,
  the module flag `src/auditmanager/comparison/modules.py`, `SEALED_NOT_YET_WRITTEN`

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at `cc3dd36b` (prefixes `cq_` and `cqa_` exist; `ComparisonWorkId`, `ComparisonWorkAttemptId`)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas (this lane changes none)
- analysis/comparison/event contract: ADR-0025 decisions 4, 6, 7, 23 and the 2026-10-27 addendum
- migration head: `0038_comparison_foundation` (this lane changes none; a missing column is a STOP)
- base commit: `cc3dd36b` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

(The one set this lane touches is `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py`: it removes its own
two tables, `comparison_work` and `comparison_work_attempt`, by the wave brief's wiring rule 4.)

## Captured premise evidence
- premise: contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`, base `cc3dd36b` (wave brief section 1.1); the lane
  re-read them before any edit and STOPs if they differ

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git rev-parse HEAD; python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n "^revision: str" db/migrations/versions/20261028_0038_comparison_foundation.py`
- captured_output:
  ```text
  cc3dd36b5b05b28ed0232107c8d0a437e304f07b
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  81:revision: str = "0038_comparison_foundation"
  ```
- interpretation: equal to the premise (contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the lane did not STOP

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/work/**`
- `src/auditmanager/workers/service.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/unit/comparison/work/**`
- `tests/integration/comparison/work/**`
- `src/auditmanager/comparison/public.py`
- `scripts/recovery/grant_classification.py`
- `docs/program/CMP-WORK-01.md`
- `docs/program/tasks/CMP-WORK-01.md`

The last four are the wave brief's wiring rule 4 (appends to `comparison/public.py` for this lane's names only; the removal of
`comparison_work` and `comparison_work_attempt` from `SEALED_NOT_YET_WRITTEN`) and the lane's own two documents. Two further
hunks are not on the brief's row and are listed in the report as out-of-row, each minimal: the one argument in
`src/auditmanager/workers/__main__.py` that hands the built runner to `WorkerService` (without it the worker loop hook is not
reachable from the process entry point), and the pin in `tests/integration/recovery/test_grant_classification.py` that names
`comparison_work` as its example of a sealed table (it goes red the moment the set stops naming it).

## Lane resources
- foundation_instance: `auditmanager-cmp-work-01`
- postgres_port: `57720`
- s3_api_port: `61720`
- s3_console_port: `61721`
- postgres_db: `auditmanager_cmp_work_01`
- s3_bucket: `auditmanager-cmp-work-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**` (no column is missing; a missing one is a STOP and the wave's FIX slot)
- `src/auditmanager/jobs/**` (PROD-20), `src/auditmanager/execution/**` (read through its `public.py` only)
- `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/api/routers/ports.py` (this lane implements no sealed operation)
- root dependency / lock files, global styles, `web/**`
- `infra/**`

## Non-goals
- no handler for any kind (each later lane appends its own factory to the tuple in `comparison/public.py`)
- no spend journal and no `spend_unknown` decision of its own (CMP-SPEND-01 appends a probe; this lane only provides the hook and the state change)
- no screen: the read-only «Сравнение» block of «Очередь» named in ADR-0025 decision 6 is on the web side and is not on this row; the report records it as open
- no API operation and no change of the product contract

## Deliverables
1. `src/auditmanager/comparison/work/` — model (states, outcomes, `WorkItem`), repository (enqueue with the live dedupe key, claim,
   heartbeat, `require_current`, finish, pause / resume / cancel, reclaim, reads), handler registry, claim gates, per-item heartbeat,
   the runner the worker hosts.
2. The worker hook: `WorkerService(comparison_work=...)`, the second claimant inside the dispatch loop (counted against the slots),
   the reclaim pass, the drain; `build_worker_runtime` builds the runner from the module flag and the handler tuple.
3. Names exported from `comparison/public.py` for the later lanes (handler factories tuple, spend probes tuple, `ComparisonWorkRepository`, the outcomes).
4. Unit and integration tests with a mutation proof for each of: no double claim under concurrency; reclaim after lease expiry; the pause
   honoured (global and module off); strict priority; one handler per kind.
5. The report `docs/program/CMP-WORK-01.md`.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/work`
- expected: all pass, no container needed
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/integration/comparison/work`
- expected: all pass on the lane's own stack (`make up`, `make migrate`)

## Integration contract
The integrator can rely on: `ComparisonWorkRepository` is the only writer of `comparison_work` and `comparison_work_attempt`; a handler is
`kind: str` plus `run(item: WorkItem) -> Completed | Failed | Yielded`, built by a factory `Callable[[WorkDependencies], WorkHandler]`
appended to `HANDLER_FACTORIES`; the worker claims an item only when `execution_control.paused` is false, the item's module is on, no
Run is claimable and a slot is free; an item in flight when the process dies is reclaimed after the lease (60 s) and re-queued, failed
when its attempt budget is spent, cancelled when a cancel was requested, or `spend_unknown` when a registered spend probe says so.

## Failure/idempotency/security cases
- two workers claim concurrently: exactly one gets the item (row lock, `SKIP LOCKED`), the other the next or nothing
- a worker that lost its lease cannot finish or publish: `require_current` refuses with `stale_attempt` / `execution_token_invalid`
- the execution token is never logged, repr'd or returned
- an enqueue with a live dedupe key returns the existing item and creates no second one
- a `failure_reason` is a typed code, never free text

## Rollback / feature flag
`AUDITMANAGER_COMPARISON_MODULES=none` (the default) turns every claim off: the worker still reclaims expired comparison leases (so a
project erase is not blocked by a dead worker) but takes nothing. No handler is registered by this lane.

## Handoff
- changed files: (filled in the last commit)
- commands/results: (filled in the last commit)
- known limits: (filled in the last commit)
- integration notes: (filled in the last commit)
