# Task W54-WORKERS-WEB — The «Исполнители» screen lists workers with their state and lets an administrator switch intake; queue and run screens name the worker

## Outcome
The «Исполнители» screen lists workers with their state and lets an administrator switch intake; queue and run screens name the worker.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01`, `W54-TRANSPORT-01`, `W54-WORKER-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the WORKER merge on `integration/w54`

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
- Exactly the `W54-WORKERS-WEB` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 6, plus `docs/program/W54-WORKERS-WEB.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- BFF changes; any backend change (report contract gaps instead).

## Deliverables
- Per plan §3.7 and §4 Stage B item 6, on the real `listWorkers`/`setWorkerIntake` from `W54-WORKER-01`: online/stale/offline grouping (online/stale above offline), admin-only intake switch with confirmation and idempotency key, R-80 any-role gating, Russian copy, honest empty/error states; route placeholder text updated; journey manifest row.

## Required tests
- command: container-free: web lint, typecheck, Vitest (touched files, then one full run); the live journey is the integrator's window step.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees; no container before the window.
