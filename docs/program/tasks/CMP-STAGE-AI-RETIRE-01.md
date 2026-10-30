# Task CMP-STAGE-AI-RETIRE-01 — retire cancelled and obsolete AI units

## Outcome
Expert cancellation, terminal-generation replacement and fatal AI failure leave no obsolete queued/running Stage AI units that can indefinitely block project erasure, while saved responses and frozen source/job pins remain intact.

## Depends on
- CMP-STAGE-AI-RECOVERY-01

## Frozen inputs
- domain contract: parent explicit cancel/erase accounting fix dispatch2026-10-30
- API contract: existing C4 operations, no transport changes
- migration head:0043_stage_ai_generations, mutable unit state/progress and frozen source/job pins
- base commit: `ceb7b5084c509db9cc5a5be3dc250b465c342fe8`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: parent identified that cancel_in_session changes job/work but queued/running stage_ai_unit rows survive and erase accounting treats them as live; this lane owns unit lifecycle cleanup.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_ai/**`
- `tests/unit/comparison/stage_ai/**`
- `tests/integration/comparison/stage_ai/**`
- `docs/program/tasks/CMP-STAGE-AI-RETIRE-01.md`
- `docs/program/CMP-STAGE-AI-RETIRE-01.md`

## Forbidden hotspots
- shared erasure/job/work services, contracts/migrations, stage_run orchestration, composition/registry, root locks/dependencies, raw evidence, remote refs

## Non-goals
- no deletion or rewriting of saved responses, immutable answers, frozen payload/job pins or completed control units
- no change to expert verdicts or provider retry authority

## Deliverables
- caller-owned cancel_pending_units lifecycle helper
- cleanup on expert cancel including terminal/no-job branches, old-generation replacement and fatal failure
- short SQL assertions for no obsolete pending units and preserved saved-reply reuse

## Required tests
- focused owned unit/recordedSQL cases, compile/whitespace; no full gates/heavy/live checks

## Integration contract
Runtime performs retirement in the same caller transaction as cancellation/recovery/failure. New generation and current failed unit can be excluded where needed. Parent retains erasure accounting and orchestration ownership.

## Failure/idempotency/security cases
- repeated retirement is idempotent
- completed and failed units/immutable answers stay unchanged
- copied saved replies survive old unit cancellation and remain non-resendable under the run-wide journal fence

## Rollback / feature flag
Existing stages scheduling flag remains the boundary; retained evidence and progress stay auditable.

## Handoff
- changed files: owned stage_ai repository/runtime, scoped retirement SQL assertions and unit fake seam, this task/report
- commands/results:75unit PASS;8focused recovery/retirement SQL PASS; compile/whitespace PASS
- known limits: unit lifecycle only; parent owns wider project erasure
- integration notes: root sole integrator
