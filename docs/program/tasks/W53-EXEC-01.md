# Task W53-EXEC-01 — durable execution behind the sealed API

task_id: W53-EXEC-01

## Outcome

Accepted runs are durably dispatched from PostgreSQL with lease heartbeat,
bounded recovery, safe provider retry classification, cancellation, re-audit,
priority and pause. The six sealed execution operations return real journal
and queue projections. Fault, concurrency and restart tests demonstrate the
boundaries in `dispatch/W53-PLAN.md` §3.1 and §4 Stage B.

## Depends on

- `W53-FREEZE-01`, completed at `3c527d363ee5a196fbd44bf2f5b187d544615dd6`.
- `W53-SEAL-01`, accepted and merged as `3132fcb861edbc86bb8bc9130034e7125f4e5bb3`.

## Frozen inputs

- Code base after ordered Stage-A merges: `806624e52a534f04a8b3510686ab1bfa28bbcc38`;
  the integrator supplies the exact dispatch commit containing this task.
- API 36 paths / 43 operations / 91 schemas, OpenAPI SHA-256
  `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- Domain candidate revision 9 / 29 identities; state-machine SHA-256
  `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`;
  23 API error codes; migration head `0017_execution_queue`;
  contract version `1.0.0-draft.1`.
- R-75…R-79; the W53 execution amendment in `dispatch/W53-PLAN.md`.
  Backup is deferred to a separate beta wave. MinIO image runtime acceptance
  and a working-stand upgrade are outside this grant.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The sealed API operations, roles, state names and migration are frozen. A
required new member or contract change is a stop condition and needs an
exact repair grant from the integrator.

## Captured premise evidence

- premise: Stage A sealed the six routes and 0017 migration; the implementation
  seams exist at the paths named below.

### P-01 — Stage-A merged tree and contracts

- captured_at: 2026-10-09
- command: `git rev-parse HEAD && sha256sum contracts/api/v1/openapi.json contracts/domain/v1/state-machines.json`
- captured_output:
  ```text
  806624e52a534f04a8b3510686ab1bfa28bbcc38
  008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193  contracts/api/v1/openapi.json
  cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466  contracts/domain/v1/state-machines.json
  ```
- interpretation: this identifies the code input; the task-file commit is a
  later dispatch SHA and must be read back before the worktree is created.

### P-02 — implementation seams

- captured_at: 2026-10-09
- command: `git grep -n 'class ModelRequest\|class RunCarrier\|def execute_run' -- src/auditmanager/analysis/text/adapter.py src/auditmanager/runs/carrier.py src/auditmanager/runs/executor.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/adapter.py:32:class ModelRequest:
  src/auditmanager/runs/carrier.py:118:class RunCarrier(Protocol):
  src/auditmanager/runs/executor.py:579:def execute_run(
  ```
- interpretation: the implementation must preserve the existing carrier,
  request and direct-execution compatibility interfaces.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`, `src/auditmanager/execution/**`
  (new bounded read projection): durable dispatch, authority, journal and commands.
- `src/auditmanager/api/app.py`: serving lifespan wiring only.
- `src/auditmanager/api/routers/runs.py`, `src/auditmanager/api/routers/execution.py`:
  sealed route bodies only; keep operation IDs, shapes and role policy.
- `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/bootstrap/composition.py`:
  replace SEAL stubs with concrete ports and carrier wiring only.
- `src/auditmanager/analysis/text/proxy.py`, `stage.py`, `adapter.py`:
  transport dispatch classification, optional run-scoped idempotency, and
  provider effect recording only.
- `tests/integration/jobs/**`, `tests/integration/runs/**`,
  `tests/integration/execution/**` (new); `tests/integration/analysis_text/test_proxy_adapter.py`,
  `test_live_adapter_shape.py`, `test_provider_modes.py`.
- `tests/integration/composition/test_the_run_leaves_the_request_thread.py`,
  `test_a_published_run_reports_itself.py`, `test_composition_root.py`;
  `tests/e2e/pc01/driver.py`; `fixtures/proxy/error-envelope-503.json` (new).
- `docs/program/W53-EXEC-01.md`: six-item handback and exact evidence.

## Forbidden hotspots

All other paths, especially `contracts/**`, the migration head and existing
migrations, error and identifier catalogs, generated client, root dependencies
and lockfiles, global styles, MinIO and backup files, custody implementation,
`VERSION`, `release-notes/**`, publication refs/tags and the working stand.
Do not relax contract tests or add a new required `RunCarrier`/`RunAdapter`
argument. The six sealed operations and current 0017 schema are the boundary.

## Non-goals

No worker service, UI, live queue push, database backup, MinIO rehearsal,
custody writes, release notes, version bump, stand deployment or release verdict.

## Deliverables

Durable dispatcher in the serving lifespan, safe lease ownership and bounded
resume, classified provider outcomes, journal and queue reads, command rules
in `runs`/`jobs`, six live port methods, narrow fixture and meaningful tests,
and `W53-EXEC-01.md`.

## Required tests

- No bytes written, own proxy 503 and capped 429 are `not_processed` and
  retry within three calls; 400/401 definite refusal ends failed without
  retry. A post-send reset, foreign 503 or 504 is `outcome_unknown` with no
  second spend. Preserve `ProxyAdapter(opener=...)` and SDK unknown-only path.
- A restart under 60 s leaves a live lease; expiry reclaims it. Resume only
  when the lost attempt has no effect other than `not_processed`; third
  attempt dead-letters. A seeded meter enforces the run ceiling across attempts.
- Two-connection cancel/claim, cancel/final-write and heartbeat/fenced-write
  races finish without deadlock or crash-path failure. The watchdog fences a
  blocked attempt without freeing its occupied slot until the thread returns.
- A second serving process respects the live lease; a test app outside the
  serving lifespan makes no database-wide claim. Existing direct
  `execute_run(cost_meter=..., sleep=...)` and `RunCarrier` drivers pass.
- Re-audit accepts only terminal sources, has its own idempotent command and
  at most one nonterminal successor per source. Cancel, priority and pause
  obey their role/state rules and write in lock order.
- Every transition produces one safe journal event in its own transaction;
  forced rollback leaves none. Journal payloads exclude non-identity values,
  secrets, provider text and paths.
- Run affected Python/contract integration tests and `git diff --check`.
  Check disk space under `AGENTS.md` §8 before any costly gate. Full `make gate`
  on a clean exact candidate and independent QA belong to the integrator.

## Integration contract

Use an isolated worktree and branch `agent/w53-exec-01` from the exact dispatch
SHA supplied by the integrator. `gate-w53exec` owns PostgreSQL 56860 and S3
60460/60461; recheck ports before use, use only own containers and logs, and
stop them at handback. Keep the 0017 lease default compatible with legacy
callers. Preserve `start_audit_run`, `execute_run(cost_meter=..., sleep=...)`,
`RunCarrier.submit/drain/shutdown`, `RunAdapter(..., carrier=...)` and
`ProxyAdapter(opener=...)` signatures. The integrator reviews and merges this
lane before W53-EXEC-WEB starts.

## Failure/idempotency/security cases

No untyped silent retry, no duplicate provider spend after an ambiguous
dispatch, no in-memory-only authority, and no DB plus external side effect
without durable reconciliation. Database lock order is `audit_run → job →
attempt → lease`, one table at a time. Heartbeats use database time, an
independent connection and `lock_timeout`; an expired lease cannot revive.
Journal data follows ADR-0015's allowlist and excludes all `non_identity`
values in `identifiers.json`.

## Rollback / feature flag

Revert the Stage-B implementation before a production rollout; retain or
restore migration 0017 according to its guarded downgrade rule. The serving
dispatcher has no independent production feature flag; the working stand is
not touched in this task.

## Handoff

Return branch and exact SHA; AGENTS.md §5's six items; a full changed-path
audit from the dispatch SHA and proof of forbidden hotspots; focused command
results and logs; contract changes (expected: none); known limitations and
precise integrator instructions. Do not push refs, tag or use the working stand.

## Executor handback — 2026-10-09

1. **Changed files.** `src/auditmanager/{analysis/text/{adapter,proxy,stage}.py,api/app.py,bootstrap/{adapters,composition}.py,execution/{__init__,public}.py,jobs/{commands,events,lease,public,repository}.py,runs/{__init__,carrier,commands,executor,reconciliation,repository}.py}`; `tests/integration/analysis_text/test_proxy_adapter.py`; `tests/integration/composition/test_the_run_leaves_the_request_thread.py`; `tests/integration/runs/{test_durable_effect_boundaries,test_w53_execution}.py`; this task file. The branch/commit SHA is supplied in the handback message after commit.
2. **Checks.** Fresh isolated PostgreSQL migrated to `0017_execution_queue`; the serial focused API contract, proxy, run, fault, command, race and composition suite passed `239` tests in `33.36s` (`/tmp/w53exec-final-focused.log`). After that, the validating refusal passed `1/1`, and the journal generic-row repair passed `10/10` in `tests/integration/runs/test_w53_execution.py` (`/tmp/w53exec-newdb.log`). `git diff --check` and Python `compileall` passed. Preflight `df -B1 .` reported more than 12 GB available before every costly run. Full `make gate` is the integrator's gate.
3. **Contracts.** None changed. Frozen OpenAPI SHA-256 remains `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`; state-machine SHA-256 remains `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`; migration head remains `0017_execution_queue`.
4. **Risks/known limits.** No measured own-proxy 503 discriminator exists in the frozen input, so every 503 remains `outcome_unknown` with no replay; see integrator stop record `W53-EXEC-STOP-01`. The frozen graph has no `validating -> cancelled`, so that command refuses without changing Run/Job/Attempt; see `W53-EXEC-STOP-02`. The pause actor is audited under `CommandRecord` in `audit_event`, outside `listExecutionJournal` because the sealed journal entry requires a Run ID. The active carrier's `drain` waits for all nonterminal Jobs in the disposable database, including jobs accepted by another process; it is a test/admin wait, not used by the request path.
5. **Integrator instructions.** Review the clean commit and exact path audit against this task, cherry-pick onto the integration SHA, then run independent QA and full gate on a clean exact tree. Keep own-proxy 503 and validating-cancel stops open until an owner decision or an exact repair grant. Do not deploy this executor branch or publish its ref.
6. **Forbidden hotspots.** The changed-path audit contains only this task's `allowed_paths`; it contains no `contracts/**`, migrations, root dependency/lock file, global styles, generated client, MinIO, backup, version, release notes, tag, publication ref or working-stand file. The two frozen contract hashes above were read back after the implementation.
