# Task EXEC2-CUTOVER-01 — preview, confirm and switch the routing mode; legacy routes read-only; rollback; operator guide

## Outcome
An administrator previews the six legacy routes as one-member groups and rules. Standbys are flagged, never converted, and incompatible routes are flagged. Confirming the mapping creates the groups, the rules and mode `rules` in one transaction. Under `rules`, `setExecutorRoute` answers `conflict` and an unmapped `work_kind` is refused with a typed error. Returning to `legacy` is explicit, and work admitted by rules finishes on its own group revisions.

## Depends on
- EXEC2-GROUP-RUN-01
- EXEC2-GROUP-CMP-01

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2` at `41514187` (GROUP-RUN-01 and GROUP-CMP-01 merged)
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 17, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the standby is used only at run start, with an event

### P-01 — standby use today
- captured_at: 2026-11-03
- command: `git grep -n 'standby_used' 41514187 -- src/auditmanager`
- captured_output:
  ```text
  41514187:src/auditmanager/executors/README.md:102:`audit_run.standby_used` event. `environment` keeps today's path, with `R-133` enforced.
  41514187:src/auditmanager/runs/commands.py:924:        session, event_type="audit_run.standby_used", aggregate_type="AuditRun",
  exit=0
  ```
- interpretation: the cut-over preview flags every standby; rules never use one.

The integrator re-captured this on `41514187` before dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/routing_mode.py`
- `src/auditmanager/executors/queries.py`
- `src/auditmanager/executors/commands.py`
- `src/auditmanager/api/routers/executors.py`
- `docs/manual-tests/EXEC2-CUTOVER.md`
- `tests/unit/executors/test_routing_mode.py`
- `tests/integration/executors/test_cutover.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/executors/group_repository.py`
- `src/auditmanager/executors/group_commands.py`
- `src/auditmanager/api/routers/executor_groups.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/bootstrap/adapters.py`
- `scripts/recovery/grant_classification.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/api/test_authorization.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one

## Non-goals
- no automatic cut-over at deploy
- no conversion of a standby

## Deliverables
- The preview, the confirmed cut-over and the rollback per decision 17.
- `docs/manual-tests/EXEC2-CUTOVER.md` (Russian operator steps, rollback, what a pending job does).
- Tests for B3 §11 items 15, 16 and 22.
- Serve `previewExecutorRouting` and `setExecutorRoutingMode` (contract 1.16.0) through `api/routers/executor_groups.py`, its port and adapter regions (`# EXEC2-CUTOVER-01`).
- Mode events are written under the advisory lock `hashtextextended('executor_routing_mode_event', 0)` with `event_no = max + 1` (the 0047 trigger verifies it); `executor_routing_mode_event` leaves `SEALED_NOT_YET_WRITTEN`.
- The confirmed cut-over creates the one-member groups and the six rules through the existing group commands' internals, in the same transaction as the `rules` event; the preview digest must match the current preview (`conflict` / `preview_stale`).
- Under `rules`, `setExecutorRoute` is refused with `conflict` / `routing_mode_rules`; `listExecutorRoutes` stays readable.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B3 §11 tests 15, 16 and 22 exist

## Integration contract
- the owner performs the cut-over on the stand after deployment (plan section 11)

## Failure/idempotency/security cases
- a confirmation whose mapping differs from the current preview: `conflict`
- a concurrent second cut-over: one wins, idempotently

## Rollback / feature flag
The mode switch is its own rollback; reverting the merge requires mode `legacy`.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
