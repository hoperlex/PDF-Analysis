# Task EXEC2-GROUP-CMP-01 — admit the five comparison kinds by rule or group and bind each job at its first dispatched call

## Outcome
A comparison AI job of any of the five `comparison_*` kinds shows the rule, the group and the planned model in its estimate, and stores consent without a connection. It binds to one member at its first dispatched call, after a consent re-check and the USD 10 job and USD 50 day ceilings against that member, and stays on it. `not_metered` is shown as «без поминутной цены», never as zero. Existing comparison jobs are unchanged.

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
- premise: comparison estimates price the route's primary, and 24 comparison lines read a job's revision

### P-01 — the estimate prices the primary
- captured_at: 2026-11-02
- command: `git grep -n 'resolved.primary' origin/dev -- src/auditmanager/comparison/ai_jobs/estimate.py`
- captured_output:
  ```text
  origin/dev:src/auditmanager/comparison/ai_jobs/estimate.py:63:    if resolved is None or resolved.primary is None:
  origin/dev:src/auditmanager/comparison/ai_jobs/estimate.py:65:    revision = resolved.primary
  exit=0
  ```
- interpretation: the estimate moves to the rule's group revision under mode `rules`.

### P-02 — comparison readers of the revision
- captured_at: 2026-11-02
- command: `git grep -c connection_revision_id origin/dev -- src/auditmanager/comparison`
- captured_output:
  ```text
  origin/dev:src/auditmanager/comparison/ai_jobs/model.py:1
  origin/dev:src/auditmanager/comparison/ai_jobs/repository.py:3
  origin/dev:src/auditmanager/comparison/ai_jobs/service.py:1
  origin/dev:src/auditmanager/comparison/report/handler.py:1
  origin/dev:src/auditmanager/comparison/spend/caller.py:4
  origin/dev:src/auditmanager/comparison/spend/model.py:7
  origin/dev:src/auditmanager/comparison/spend/repository.py:6
  origin/dev:src/auditmanager/comparison/stage_ai/repository.py:1
  exit=0
  ```
- interpretation: every listed file must handle a `pending` job.

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/ai_jobs/**`
- `src/auditmanager/comparison/spend/**`
- `src/auditmanager/comparison/stage_ai/**`
- `src/auditmanager/comparison/report/**`
- `src/auditmanager/comparison/specification/**`
- `src/auditmanager/comparison/stage_review/**`
- `src/auditmanager/comparison/ai_pairs/**`
- `src/auditmanager/comparison/ai_sheets/**`
- `tests/unit/comparison/**`
- `tests/integration/comparison/test_group_binding.py`

## Forbidden hotspots
- `contracts/**`, generated models and client, the migration head, root dependency/lock files and global styles (owned by the stage's SEAL task)
- `src/auditmanager/shared/errors/**`: EXEC-2 adds no error code (ADR-0026 decision 18)
- paths another EXEC-2 task owns in the same stage (`EXEC2-PLAN.md` section 5)
- `src/auditmanager/jobs/**`, `src/auditmanager/runs/**` (`EXEC2-GROUP-RUN-01`)

## Non-goals
- no change to raw deterministic comparison evidence
- no per-call balancing inside one job

## Deliverables
- First, a list of the binding path of each of the five kinds (`ai_jobs`, `stage_ai`, `report`, `specification`, `stage_review`, and the `ai_pairs` and `ai_sheets` handlers) in the lane report.
- Group estimate and consent per decision 13; first-call binding per decision 14; ceilings against the selected member.
- `pending` handling at every line of premise P-02.
- Tests for B3 §11 items 3–5, 9–14 and 17 for comparison jobs, including simultaneous dispatch of two jobs under the day ceiling.

## Required tests
- command: not run in EXEC-2 (`R-149d`); write the tests below and mark those that need PostgreSQL with the suite's existing database marker
- expected: the listed B3 §11 tests exist

## Integration contract
- comparison jobs reuse `executors.public` selection and `EXEC2-CAP-01` units; they take the same advisory locks in the same order

## Failure/idempotency/security cases
- `spend_unknown` is never resent to another member
- a resume after `overrun` keeps the bound member

## Rollback / feature flag
As `EXEC2-GROUP-RUN-01`: mode `legacy` admits nothing by group.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
