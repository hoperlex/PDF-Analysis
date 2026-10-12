# Task W54-WORKER-01 — A separate worker service claims and runs jobs with a registry, drain and intake control, so the API process no longer executes runs

## Outcome
A separate worker service claims and runs jobs with a registry, drain and intake control, so the API process no longer executes runs.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: `contracts/domain/v1` after `W54-SEAL-01`
- API contract: `contracts/api/v1/openapi.json` after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers` (not yet DB-tested; the integrator runs it in the window)
- base commit: the Stage-A merge on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W54-WORKER-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 5, except: in `src/auditmanager/jobs/repository.py` leave the D-142 settlement code to CUSTODY, and in `tests/integration/qa_w53/test_queue_and_effect_journal.py` change only the D-150 assertion (CUSTODY owns settlement assertions, in parallel); plus `src/auditmanager/shared/identity/ids.py` and `docs/program/P02_SEAMS.md` for removing `worker_id` from `UNALLOCATED_IN_PC01` (SEAL's note), plus `docs/program/W54-WORKER-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations (SEAL's); `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/**`

## Non-goals
- «Исполнители» screens (WORKERS-WEB); remote workers; custody.

## Deliverables
- Per plan §3.6, §3.7 and §4 Stage B item 5, with the freeze's D-150 decision (recorded effects reclaim as `not_processed`): only the worker claims; both reclaim; an API restart leaves the worker's run alone; a killed worker's lease reclaimed; lost `LISTEN` logged; drain; the token exemption; a compose file without the role refused; a final transaction longer than the lease is not reclaimed (D-141); recorded reclaim (D-150); D-152's test isolation; W53's drivers pass under `all`; `listWorkers`/`setWorkerIntake` stubs get real bodies.

## Required tests
- command: container-free tests now; DB/S3-backed tests are heavy steps on PostgreSQL `57130`, S3 `60730/60731` and run only when the integrator opens the owner's window (`R-102`, `W54-FREEZE-01`) — write them and list exact commands in the report.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report, and runs the listed heavy steps in the window.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started; never touch the stand, published refs or other worktrees; no container before the window.
