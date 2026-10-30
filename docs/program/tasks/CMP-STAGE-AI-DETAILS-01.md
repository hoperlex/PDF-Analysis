# Task CMP-STAGE-AI-DETAILS-01 — validated model classification hints

## Outcome
Stage classifier returns genuine model-supplied materiality, importance and detail-increased hints with strict closed values, neutral legacy defaults and new prompt/cache identity. Hints never become expert verdicts.

## Depends on
- CMP-STAGE-AI-LOOP-01
- CMP-STAGE-AI-GRAPHIC-01

## Frozen inputs
- domain contract: ADR-0025/A-10, parent explicit additive classification-hints dispatch2026-10-30
- API contract: root owns optional fields on StageClassificationCard/StageChangeCard; no contract edits in this lane
- migration head:0042, existing immutable classification JSONB, no DDL
- base commit: `dc4eef71d6a2ea92d2e7c9545aabbe49f1131610`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: parent assigns materiality=material/non_material/unknown, importance=high/normal/unknown, detail_increased boolean; closed categories unchanged, no category-based inference.

### P-01 — additive root transport provider consumed
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; git log -2 --oneline`
- captured_output:
  ```text
  dc4eef71d6a2ea92d2e7c9545aabbe49f1131610
  dc4eef71 merge: consume root additive escalation and detail contracts
  80b6b9e3 chore(web): pin C4 escalation contract and generated client bytes
  ```
- interpretation: initial owned input7203521f is retained; root merged its additive models/contracts/client before metadata SQL validation; final path proof excludes those shared changes.

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
- `docs/program/tasks/CMP-STAGE-AI-DETAILS-01.md`
- `docs/program/CMP-STAGE-AI-DETAILS-01.md`

## Forbidden hotspots
- shared contracts/migrations/services, stage_review/provider paths, composition/registry, root dependencies/locks, raw evidence and remote refs

## Non-goals
- no expert verdicts, canonical engineering conclusions or category-derived importance
- no category vocabulary change or migration

## Deliverables
- typed immutable card defaults unknown/unknown/false and strict parser/schema
- explicit classifier prompt/version/content-key changes and conservative graphical-page aggregation
- tests for present/missing/invalid metadata and preserved caps; report

## Required tests
- scoped Stage AI unit/recordedSQL checks, compile/whitespace; no full gate/heavy/live window

## Integration contract
Dataclass fields and persisted classification JSON use materiality,importance,detail_increased unchanged. Missing older answers decode with neutral defaults. Root seals optional transport fields; review owner reads the same immutable source-answer metadata. Classification/card evidence IDs, raw evidence and verdict digests retain existing semantics.

## Failure/idempotency/security cases
- foreign enum values, non-boolean detail flags and unknown keys refuse the whole classification group
- prompt/schema versions prevent semantic cache mixing
- conflicting graphical page hints aggregate conservatively; metadata never authorizes a verdict

## Rollback / feature flag
Stages module scheduling remains the behavior boundary; legacy rows retain neutral defaults without rewriting immutable JSON.

## Handoff
- changed files: stage_ai model/classifier/graphic aggregation, scoped metadata unit tests and recorded SQL fixture assertions, this task/report
- commands/results: 75 unit PASS; 7 recorded SQL PASS; compile/whitespace PASS
- known limits: AI interpretation, not expert acceptance
- integration notes: root owns additive transport seal and final integration
