# Task EXEC2-GROUP-RUN-01 — admit Runs by rule or group and bind their executor at dispatch, exactly once

## Outcome
A Run started «Автоматически (по типу задачи)» or on a group is admitted with its frozen rule and group revision, consent envelope and `binding_state = pending`. No connection is chosen at admission. When a member has a free unit, the claim transaction binds it exactly once and only then does model I/O start. While every member is busy the Run waits visibly. While every member is offline it waits 30 minutes, then ends `no_executor_online`. `environment` never runs it. Existing Runs, explicit connections and presets behave exactly as before.

## Depends on
- EXEC2-INT-2

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2` after `EXEC2-INT-2` is on `origin/dev`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 12–16, 18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: 57 lines outside `executors/` and `comparison/` read a Run's frozen revision, and a Run without one is never limited

### P-01 — readers of the frozen revision
- captured_at: 2026-11-02
- command: `git grep -c connection_revision_id origin/dev -- src/auditmanager ':!src/auditmanager/executors' ':!src/auditmanager/comparison'`
- captured_output:
  ```text
  origin/dev:src/auditmanager/analysis/text/binding.py:3
  origin/dev:src/auditmanager/analysis/text/config.py:1
  origin/dev:src/auditmanager/analysis/text/cost.py:2
  origin/dev:src/auditmanager/api/schemas/models.py:1
  origin/dev:src/auditmanager/bootstrap/adapters.py:2
  origin/dev:src/auditmanager/bootstrap/composition.py:3
  origin/dev:src/auditmanager/bootstrap/providers.py:3
  origin/dev:src/auditmanager/jobs/README.md:1
  origin/dev:src/auditmanager/jobs/repository.py:20
  origin/dev:src/auditmanager/runs/commands.py:2
  origin/dev:src/auditmanager/runs/cost_policy.py:3
  origin/dev:src/auditmanager/runs/executor.py:3
  origin/dev:src/auditmanager/runs/extended_review.py:2
  origin/dev:src/auditmanager/runs/preflight.py:3
  origin/dev:src/auditmanager/runs/repository.py:8
  origin/dev:src/auditmanager/runs/v3_group.py:1
  origin/dev:src/auditmanager/runs/v3_provider_call.py:2
  exit=0
  ```
- interpretation: every listed file must handle `pending` (no revision yet) distinctly from `environment` (no revision ever).

### P-02 — the no-revision shortcut of the claim
- captured_at: 2026-11-02
- command: `git grep -n 'A Run without a connection takes no lock' origin/dev -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/jobs/repository.py:969:        A Run without a connection takes no lock and is never limited.
  exit=0
  ```
- interpretation: today a NULL revision means `environment`; after this task it means that only when `binding_state` is `frozen_at_start`.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/jobs/README.md`
- `src/auditmanager/runs/**`
- `src/auditmanager/analysis/text/binding.py`
- `src/auditmanager/analysis/text/config.py`
- `src/auditmanager/analysis/text/cost.py`
- `src/auditmanager/executors/resolver.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/unit/runs/**`
- `tests/unit/jobs/**`
- `tests/integration/runs/test_group_binding.py`
- `tests/integration/jobs/test_group_dispatch.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- `src/auditmanager/comparison/**` (`EXEC2-GROUP-CMP-01`)
- `src/auditmanager/executors/group*.py` (frozen by `EXEC2-GROUP-STORE-01`; defects go back to the integrator)

## Non-goals
- no per-stage routing, no model swap, no heterogeneous group
- no group-targeting preset

## Deliverables
- Admission per decision 13 in `startRun` and `estimateRunCost`, mutually exclusive selectors, and refusal under `environment`.
- Each reader of premise P-01 handles `pending`; the inventory is closed line by line in the lane report.
- Dispatch in the claim per decision 14 (lock order, eligibility, selection, consent re-check, write-once binding, dispatch event), and the `_NEXT_JOB` hint for `pending` Runs.
- Durable waiting per decision 15, with `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS` (default 1800) read where the worker reads its settings.
- No re-routing per decision 16.
- Tests for B3 §11 items 3–12, 14, 17, 18 and 20 for Runs, including a two-process race for the last unit of a two-member group.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: the listed B3 §11 tests exist

## Integration contract
- a `bound` Run is indistinguishable from a `frozen_at_start` Run to every later reader

## Failure/idempotency/security cases
- two workers race for one last unit: one binding
- a member's current revision changed after admission: that member is ineligible, never adopted
- lease loss after binding: the retry stays on the bound member
- `outcome_unknown`: never redispatched

## Rollback / feature flag
The routing mode `legacy` (default) admits nothing by group, and an explicit group start is refused unless the mode or the selector allows it. Reverting the merge requires no `pending` Run to exist.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
