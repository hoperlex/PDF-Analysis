# Task EXEC2-GROUP-STORE-01 — executor group and rule commands, homogeneity validation, and the least-loaded selection function

## Outcome
An administrator creates a two-member group whose revisions have the same `pin_id`, `gateway_model`, billing and rates. A mismatched pin, gateway model or billing is refused with a typed validation error. Rules can be set per `work_kind`. Archived groups and their revisions stay readable. A pure `least_loaded` selection and a capacity reader exist for stage 3.

## Depends on
- EXEC2-SEAL-2

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2` after the `EXEC2-SEAL-2` merge
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 10, 11, 14, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: six work kinds exist and every kind serves every connection kind

### P-01 — the work kinds
- captured_at: 2026-11-02
- command: `git grep -n -A7 '^WORK_KINDS' origin/dev -- src/auditmanager/executors/model.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/executors/model.py:71:WORK_KINDS: Final[tuple[str, ...]] = (
  origin/dev:src/auditmanager/executors/model.py-72-    "text_analysis",
  origin/dev:src/auditmanager/executors/model.py-73-    "comparison_pair_check",
  origin/dev:src/auditmanager/executors/model.py-74-    "comparison_sheet_changes",
  origin/dev:src/auditmanager/executors/model.py-75-    "comparison_spec",
  origin/dev:src/auditmanager/executors/model.py-76-    "comparison_report",
  origin/dev:src/auditmanager/executors/model.py-77-    "comparison_stage_review",
  origin/dev:src/auditmanager/executors/model.py-78-)
  exit=0
  ```
- interpretation: rules are one per value of this tuple; no new kind is added.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/groups.py`
- `src/auditmanager/executors/group_repository.py`
- `src/auditmanager/executors/group_commands.py`
- `src/auditmanager/executors/group_selection.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/api/routers/executor_groups.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/security.py`
- `tests/unit/executors/test_groups.py`
- `tests/unit/executors/test_group_selection.py`
- `tests/integration/executors/test_groups.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- in `src/auditmanager/bootstrap/adapters.py` and `src/auditmanager/api/routers/ports.py`, which three stage-1 lanes share: any function or class outside this task's own port; new code goes in a section headed with this task id, and the integrator merges the lanes one by one
- `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`, `src/auditmanager/comparison/**` (stage 3)

## Non-goals
- no dispatch, no admission, no cut-over

## Deliverables
- Commands with idempotency keys and journal events, validation per decision 10, and archive semantics.
- `group_selection.choose(members, used, capacity, rotation)`: pure; minimum `used/capacity`; no division by zero; persisted rotation tie-break.
- `capacity` read for a group, built on `EXEC2-CAP-01`'s readers.
- Tests for B3 §11 items 1, 2 and 19.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: B3 §11 tests 1, 2 and 19 exist

## Integration contract
- `EXEC2-GROUP-RUN-01` and `EXEC2-GROUP-CMP-01` call `executors.public` for rule resolution, eligibility and selection; they never read the group tables directly

## Failure/idempotency/security cases
- a member revision that is not the connection's current one at creation: refused
- a duplicate member: refused

## Rollback / feature flag
Groups and rules have no effect while the routing mode is `legacy`.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
