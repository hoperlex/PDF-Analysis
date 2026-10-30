# Task CMP-INT-CODE-1030 — finish CMP functional code and publish development

## Outcome
The remaining C3/C4 functional roadmap is implemented, integrated by one owner and fast-forward published to `origin/dev`, with focused smoke evidence and an explicit list of deferred heavy acceptance work.

## Depends on
- CMP-C2-FIX-01
- CMP-SEAL-C3

## Frozen inputs
- roadmap/domain: `COMPARE-MODULES-PLAN.md`, ADR-0025 and the owner's Q-CMP answers
- base commit: `97c8dcf2ced12ceea9a7c924e297aa397e7da612`
- C2 API/migration: `1.11.0` / `0040_comparison_ai_reports`
- C3 API/migration: `CMP-SEAL-C3`, `1.12.0` / `0041_comparison_stage_core`
- C4 shared contract/migration slot: assigned serially to `CMP-SEAL-C4`; implementation lanes consume its committed output
- owner instruction 2026-10-30: finish functional roadmap code today and deliver it to dev; all gates and heavy verification windows are deferred to tomorrow. This direct instruction supersedes the earlier dev gate requirement for this code publication only. It does not claim acceptance or authorise main.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: prior C2 candidate remains local, the interrupted gate log is no longer present, and remote dev still names the pre-C2 tree.

### P-01 — local and remote refs
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  97c8dcf2ced12ceea9a7c924e297aa397e7da612
  e8567a1981cbe35cf66bae4ce79b2877224df1be refs/heads/dev
  3449265338e341e6f14e02fe55260030b38bdd14 refs/heads/main
  ```
- interpretation: only the appointed integrator publishes dev; no gate success or deployed state is inferred.

## Historical evidence
- correction_mode: addendum
- source_record: `docs/program/tasks/CMP-WAVE-C2-INT.md`
- addendum_path: `docs/program/CMP-INT-CODE-1030.md`

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `docs/program/tasks/CMP-INT-CODE-1030.md`
- `docs/program/CMP-INT-CODE-1030.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/compare/**`
- `docs/program/dispatch/**`
- `src/auditmanager/bootstrap/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/comparison/stage_run/**`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/unit/comparison/work/test_handler_registry.py`
- `web/src/_pages/stage-compare/**`
- `web/src/widgets/comparison-viewer/**`
- `web/src/widgets/stage-sheet-map/**`
- `web/src/widgets/stage-text-evidence/**`
- `web/src/widgets/stage-changes/**` (bounded polling integration only)
- `web/src/widgets/stage-run-controls/**` (bounded polling integration only)
- `web/tests/unit/run/polling.test.ts`
- `tests/integration/composition/**`

## Forbidden hotspots
- `origin/main`, force-push, deployment, unrelated worktree changes and owner files
- contracts/migration head/root locks/global styles outside their explicitly assigned serial slot

## Non-goals
- no full gate, whole integration battery, exposure/journey acceptance or live spend today
- no production deployment or claim that focused checks replace tomorrow's acceptance

## Deliverables
- completed functional lanes with isolated ownership and short implementation checks
- one integrated candidate and report listing exact commits, contract versions, known limitations and tomorrow's required checks
- clean candidate, remote-ref recheck, proven fast-forward and exact-SHA push to origin/dev

## Required tests
- focused tests and build/typecheck appropriate to changed functionality; no whole gate
- `git diff --check`, clean candidate, remote ancestry and before/after ref verification

## Integration contract
Root is the sole integrator and dev writer. Subagents implement independent owned directories in isolated worktrees; root serialises shared wiring, contract and migration slots. The user's 2026-10-30 instruction defers full gates/heavy windows to 2026-10-31; incomplete acceptance is recorded honestly. Main remains subject to its separate policy and is unauthorised.

## Failure/idempotency/security cases
- no force push; a moved dev ref is fetched and reconciled before publication
- module flags preserve a rollback path; AI never rewrites raw deterministic evidence
- focused failures are fixed before publishing the affected code

## Rollback / feature flag
Comparison modules can be disabled with `AUDITMANAGER_COMPARISON_MODULES=none`; immutable data remains. A rollback is a forward commit, never a forced ref rewrite.

## Handoff
- changed files: pending
- checks/results: pending; full acceptance deferred by owner
- contracts: C3 and serial C4 seal outputs
- known limits: tomorrow's full gate, exposure and browser journey remain required
- integration notes: origin/dev only
