# Task CMP-STAGE-AI-RECOVERY-01 — consented terminal job recovery

## Outcome
A completed, cancelled or safely failed Stage AI job can resume as a new shared job generation in the caller transaction under fresh LEFT consent, preserving prior journal/answers and refusing repeat unknown/paid-lost requests. Fatal AI errors also persist terminal run/step failure before shared cancellation.

## Depends on
- CMP-STAGE-AI-GRAPHIC-01
- CMP-STAGE-AI-DETAILS-01

## Frozen inputs
- domain contract: parent explicit terminal recovery and failure-persistence grant2026-10-30
- API contract: root owns orchestration/transport; no API edits in this lane
- migration head:0043_stage_ai_generations, root serial owner supplies frozen stage_ai_unit.generation and unique generation key
- shared runtime: public start_in_session/resume_in_session; root supplied optional LEFT estimate mode and terminal prior estimate_job for stage recovery
- base commit: `d802732877bb4b1dc9326caa01f015b282c4066f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: read-only audit of root36b0ae8d proves terminal shared job cannot take resume edge; repair undo reuses same full run and resets2–7. Parent explicitly assigns new-generation recovery and authorizes failure persistence before jobs.fail.

### P-01 — root generation and LEFT provider consumed
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git log -2 --oneline`
- captured_output:
  ```text
  d802732877bb4b1dc9326caa01f015b282c4066f
  d8027328 merge: consume durable generation and LEFT job recovery provider
  0ae3d34b feat(comparison): preserve stage AI units across consented recovery generations
  ```
- interpretation: root owns the shared migration/service provider; this lane authored only the following owned implementation. Isolated PostgreSQL58050 was migrated to0043 before replay.

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
- `docs/program/tasks/CMP-STAGE-AI-RECOVERY-01.md`
- `docs/program/CMP-STAGE-AI-RECOVERY-01.md`

## Forbidden hotspots
- shared services/contracts/migration, stage_run orchestration, registry/composition, dependency locks, raw evidence and remote refs

## Non-goals
- no automatic replay of unknown or paid missing responses, no mutation of immutable unit source/job pins or old answers
- no orchestration/work requeue changes; root owns new work/job pin propagation

## Deliverables
- terminal resume creates new shared job generation with current source and fresh LEFT digest
- durable saved-response reuse and run-wide request journal fencing across generations
- failure reason/step persisted before shared job cancellation
- focused recorded SQL recovery cases and report

## Required tests
- owned Stage AI unit and targeted recordedSQL cases, compile/whitespace; no full gates/heavy/live provider

## Integration contract
Root consumes shared generation/LEFT provider first and rereads run.comparison_ai_job_id after runtime.resume, cancelling/requeuing old-generation work. New generation does not alter group/source/request fingerprints. Runtime owns failure persistence before shared jobs.fail; root keeps lock ordering consistent.

## Failure/idempotency/security cases
- fresh consent binds route/current source/current prompts and remaining window
- unknown/prepared/sent or paid completed response without saved bytes cannot be resent
- only exact journal failed plus saved proof of definite non-processing permits the same request again
- old journal, frozen unit payload/job pin and immutable answers stay retained

## Rollback / feature flag
Stages scheduling flag remains the boundary; old generations remain auditable and are never rewritten.

## Handoff
- changed files: owned stage_ai runtime/repository/planning, focused failure unit assertion and recoverySQL cases, this task/report
- commands/results:75unit PASS;13recordedSQL PASS including6recovery cases; compile/whitespace PASS
- known limits: terminal zero-call recovery reuses cached job with no new consent/provider action; unknown/paid-lost same requests remain explicitly blocked; root owns work-generation rebinding and lock order
- integration notes: root sole shared-slot owner/integrator
