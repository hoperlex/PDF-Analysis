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
- base commit: `integration/exec2` after the GROUP-RUN-01 and GROUP-CMP-01 merges
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 17, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the standby is used only at run start, with an event

### P-01 — standby use today
- captured_at: 2026-11-02
- command: `git grep -n 'standby_used' origin/dev -- src/auditmanager`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/README.md:80:`audit_run.standby_used` event. `environment` keeps today's path, with `R-133` enforced.
  origin/dev:src/auditmanager/runs/commands.py:791:        session, event_type="audit_run.standby_used", aggregate_type="AuditRun",
  exit=0
  ```
- interpretation: the cut-over preview flags every standby; rules never use one.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

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
