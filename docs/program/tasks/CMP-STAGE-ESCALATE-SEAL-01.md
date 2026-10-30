# CMP-STAGE-ESCALATE-SEAL-01

## Outcome
An expert can create a REVIEW card over current raw stage evidence, including a service item or masked fragment, through one keyed authenticated command (roadmap R3-02). Stage cards also carry actual AI materiality/importance/detail labels for the required sections.

## Depends on
- CMP-SEAL-C4
- CMP-STAGE-REVIEW-01

## Frozen inputs
- base43538b03; unpublished C4 API1.13.0 /0042; ADR-0025 and COMPARE-MODULES-PLAN R3-02/§1.2
- serial shared contract owner: root; new additive C4 boundary before first dev publication

## Allowed paths
- contracts/api/v1/openapi.json
- src/auditmanager/api/schemas/models.py
- src/auditmanager/api/routers/comparison_stage_c4.py
- src/auditmanager/api/routers/ports.py
- src/auditmanager/api/security.py
- src/auditmanager/bootstrap/adapters.py
- src/auditmanager/comparison/stage_run/factories.py
- web/src/shared/api/generated/**
- web/openapi/openapi.json
- web/FRONTEND_LOCK.json
- web/src/shared/api/authorization.ts
- scripts/recovery/product_purge.py
- tests/integration/composition/test_comparison_stage_c4_wiring.py
- docs/program/tasks/CMP-STAGE-ESCALATE-SEAL-01.md
- docs/program/CMP-STAGE-ESCALATE-SEAL-01.md

## Forbidden hotspots
Migration head, root dependencies/locks, global styles, remote main.

## Non-goals
No evidence rewrite, model promotion to expert verdict, deployment or full gate.

## Deliverables
Typed createStageReviewCard port/route/authorization, additive AI label fields, generated client and exact input lock.

## Verification
Schema/client regeneration, focused role/key/module HTTP and generated-client checks; full gates deferred by owner to2026-10-31.

## Integration contract
POST /stage-chain-runs/{stage_chain_run_id}/review-cards, expert+Idempotency-Key, source_ids1..100, nonblankreason1..2000, returns201StageChangeCard. StageReviewService.promote owns validation/immutable insertion/audit. Schema remains unpublished1.13.0; no migration needed. New optional labels come from persisted model output; old/raw evidence stays unknown.

## Rollback
Comparison stages module flag gates operation; immutable cards/audit remain.
