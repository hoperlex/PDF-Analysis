# Task EXEC2-WEB-GROUPS-01 — «Группы» and «Правила» tabs, the three-way start selector, waiting and binding on queue and run screens

## Outcome
«Исполнители» has «Группы» (create, revise and archive homogeneous groups with model, capacity and eligibility reasons) and «Правила», a table of exactly six `work_kind` rows that replaces «Назначения» after cut-over; legacy routes show as history. Run start offers «Автоматически (по типу задачи)», «Группа исполнителей» and «Конкретное подключение». Queue and run screens show the waiting reason, and «плановая модель» before dispatch versus «фактическая модель и подключение» after it.

## Depends on
- EXEC2-INT-2

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2` after `EXEC2-INT-2` is on `origin/dev`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 10–17, 19; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `web/src/_pages/workers/model/tabs.ts`
- enumerator_owner: EXEC2-WEB-GROUPS-01
- totality_query: `git grep -n "WORKERS_TABS = " -- web/src/_pages/workers/model/tabs.ts`

## Captured premise evidence
- premise: the workers screen enumerates its tabs in one tuple, and the start selector and routes widget exist

### P-01 — the tab enumerator
- captured_at: 2026-11-02
- command: `git grep -n 'WORKERS_TABS = ' 27fb952e -- web/src/_pages/workers/model/tabs.ts`
- captured_output:
  ```text
  27fb952e:web/src/_pages/workers/model/tabs.ts:13:export const WORKERS_TABS = ['connections', 'processes', 'routes'] as const;
  exit=0
  ```
- interpretation: this task owns the tab set and adds «Группы» and «Правила».

### P-02 — the files to change
- captured_at: 2026-11-02
- command: `git ls-tree -r --name-only origin/dev web/src/_pages/workers web/src/widgets/executor-routes web/src/features/start-run`
- captured_output:
  ```text
  web/src/_pages/workers/index.ts
  web/src/_pages/workers/model/tabs.ts
  web/src/_pages/workers/ui/workers-page.module.css
  web/src/_pages/workers/ui/workers-page.tsx
  web/src/_pages/workers/ui/workers-tabs.tsx
  web/src/features/start-run/index.ts
  web/src/features/start-run/model/start-run-intent.ts
  web/src/features/start-run/model/use-run-cost-approval.ts
  web/src/features/start-run/model/use-start-run.ts
  web/src/features/start-run/ui/executor-select.tsx
  web/src/features/start-run/ui/preset-select.tsx
  web/src/features/start-run/ui/start-run-control.module.css
  web/src/features/start-run/ui/start-run-control.tsx
  web/src/features/start-run/ui/start-run-failure.tsx
  web/src/widgets/executor-routes/index.ts
  web/src/widgets/executor-routes/ui/executor-routes.module.css
  web/src/widgets/executor-routes/ui/executor-routes.tsx
  exit=0
  ```
- interpretation: the routes widget becomes the legacy history view; the start control gains the group selector.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/_pages/workers/**`
- `web/src/widgets/executor-routes/**`
- `web/src/widgets/executor-groups/**`
- `web/src/widgets/executor-rules/**`
- `web/src/features/manage-executor-group/**`
- `web/src/features/start-run/**`
- `web/src/entities/audit-run/**`
- `web/src/entities/executor-group/**`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `web/src/widgets/executor-connections/**` (frozen after stage 2)

## Non-goals
- no general rule language
- no claim that a model ran before dispatch

## Deliverables
- The screens above, the `R-149a` notice on groups, and Russian refusals.
- Component tests for the selector exclusivity, the six-row rules table and the planned/actual distinction.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: component tests exist

## Integration contract
- reads only the 1.16.0 generated client

## Failure/idempotency/security cases
- an invalid member combination is blocked in the form before the server refuses it

## Rollback / feature flag
UI only; revert the merge.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
