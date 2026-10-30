# Task CMP-STAGE-AI-GRAPHIC-01 — source-bound graphical AI and read seam

## Outcome
Stage AI exposes bounded immutable answer pages and can estimate/interpret reliable graphical evidence, including scans, through the shared consent/spend runtime with verified crops and complete cursor traversal.

## Depends on
- CMP-STAGE-AI-CORE-01
- CMP-STAGE-AI-LOOP-01

## Frozen inputs
- domain contract: ADR-0025, COMPARE-MODULES-PLAN D-2/D-3; root explicitly owns chain/bridge wiring
- API contract: C4 `1.13.0` existing StageAiReview/Classification/Synthesis pages
- migration head: `0042`; no shared edits in this lane
- graphical provider: negotiated StageGraphicService evidence/crop/crop_plan, real sge IDs, reliable1:1 registration and canonical source boxes
- base commit: `5a449308cb2b3c144b9e513699dbd49a588f8c47`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: root assigned GRAPHIC wiring after completed D-3; graphical provider is serially integrated by root before SQL replay.

### P-01 — initial read seam and serial root providers
- captured_at: 2026-10-30
- command: `git log -3 --oneline`
- captured_output:
  ```text
  5a449308 merge: consume effective-map graphic evidence and anchors
  c6267061 fix(comparison): isolate graphic evidence by effective repair revision
  93645da4 fix(comparison): bind graphic card carryover to engine evidence and source boxes
  ```
- interpretation: owned read milestone `263c90a5` preceded parent-owned graphical provider merges; final path proof begins after those merges, preserving their separate ownership.

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
- `docs/program/tasks/CMP-STAGE-AI-GRAPHIC-01.md`
- `docs/program/CMP-STAGE-AI-GRAPHIC-01.md`

## Forbidden hotspots
- shared contracts/migrations/ai_jobs/spend, provider stage_graphic files, registry/composition, root dependencies/locks, raw evidence, remote refs

## Non-goals
- no graphical registration or crop renderer; no false TEXT/SAME interpretation for scans
- no expert verdict or raw mutation; no silent omission of regions

## Deliverables
- public immutable answer keyset page seam for existing C4 API
- conservative potential graphical preflight, graphic-only classifier/synthesis groups
- verified image attachment bounded to at most8images/request, cursor traversal without dropped remaining regions
- rolling one-page consent window, explicit fresh LEFT consent before a remainder window or repaired effective source; no estimated maximum2000-region block
- recorded focused tests and report

## Required tests
- short owned Stage AI unit/recorded SQL cases, compile/whitespace
- no full gates/heavy windows or live provider calls

## Integration contract
Root provides StageGraphicService and advances it before AI step4. Constructor accepts optional graphic_source; answer page accepts run_id/kind/after/limit, checks run existence and returns API dictionaries with stable keyset IDs. Reliable graphical evidence uses real sge IDs; absent bridge/crops stays explicitly not checked. All paid requests remain shared consent/spend calls.

## Failure/idempotency/security cases
- unreliable/non1:1 registration never produces graphic proof
- crop identity/profile/box/digest mismatch refuses before provider execution
- each cursor remainder is processed or explicitly paused/failed, never silently dropped
- saved content keys replay without provider calls; model output never becomes an expert verdict

## Rollback / feature flag
Root stages module scheduling flag remains the rollback boundary; immutable source/answers retained.

## Handoff
- changed files: stage_ai graphic/runtime/planning/repository/reviewer, scoped unit/SQL tests, this task/report; earlier read milestone263c90a5
- commands/results:59ownedunit tests PASS;7recordedSQL tests PASS on assigned PostgreSQL58050; compile/whitespace PASS
- known limits: recorded model interpretation and injected PNG material; this lane does not claim live provider or actual renderer acceptance, which belong to the graphical provider's separate smoke evidence
- integration notes: root sole integrator and publisher
