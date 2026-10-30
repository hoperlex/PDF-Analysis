# CMP-STAGE-AI-GENERATIONS-SEAL-01

## Outcome
A cancelled/failed/completed AI job can be followed by a new explicitly consented generation within its stage chain, retaining every old unit, answer and spend receipt without altering source/request fingerprints. This enables AI resume after cancel, safe failure and repair undo.

## Depends on
- CMP-SEAL-C4
- CMP-STAGE-AI-GRAPHIC-01

## Frozen inputs
API1.13.0 at228/254/614; migration0042; StageAiRuntime owner implements recovery. Root exclusively owns serial migration/shared service slot.

## Allowed paths
- db/migrations/versions/20261030_0043_stage_ai_generations.py
- src/auditmanager/comparison/ai_jobs/service.py
- tests/support/expected_facts.json
- tests/integration/composition/test_stage_ai_generations.py
- docs/program/tasks/CMP-STAGE-AI-GENERATIONS-SEAL-01.md
- docs/program/CMP-STAGE-AI-GENERATIONS-SEAL-01.md

## Forbidden hotspots
Root dependencies, global styles, unrelated contracts and remote main.

## Deliverables
0043 adds frozen nonnegative generation0 and extends unit source uniqueness by generation. Existing rows remain generation0. Shared start_in_session accepts LEFT only for caller-owned stage recovery with a terminal previous job in the same run/project/document. START/default behavior stays unchanged.

## Non-goals
No automatic retry of unknown/paid outcomes; no budget reset without new explicit consent; no full gate or deployment.

## Verification
Isolated0042→0043 apply; focused recorded recovery cases delegated to AI runtime lane; downgrade refuses used generations. Full gates/heavy checks deferred by owner.

## Integration contract
StageAiRuntime uses new generation units while preserving original group/source/request identity and checking the whole run’s spend journal. No old frozen job pin is rewritten. Root migrates test lanes before consumption.

## Rollback
Disable stages flag; migration downgrade allowed only with all generations0.
