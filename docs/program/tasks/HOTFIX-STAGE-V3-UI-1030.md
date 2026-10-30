# HOTFIX-STAGE-V3-UI-1030

## Outcome
Expose separate experimental native-text V3 selection, actual procedure progress and typed parameter verification beside classic stage comparison.

## Depends on
- PDF-PROVERKA-FUNCTIONAL-COMPARISON-1030

## Frozen inputs
- Owner emergency poll in HOTFIX-PRESENTATION-INT-1030; native TEXT experiment and source-copy provenance, no fullV3claim.
- API1.14provider233/259/620,engine classic|v3_native_text_experimental; StageChainRun.engine/experimental_progress,StageChangeCard.experimental.
- Backend source in sharedtree owned exclusively by HOTFIX-STAGE-V3-1030.

## Allowed paths
- web/src/widgets/stage-run-controls/**
- web/src/widgets/stage-changes/**
- web/src/widgets/stage-v3-experimental/**
- web/src/_pages/stage-compare/**
- docs/program/tasks/HOTFIX-STAGE-V3-UI-1030.md
- docs/program/HOTFIX-STAGE-V3-UI-1030.md

## Forbidden hotspots
- Backend, contracts, generated, bootstrap, global styles, dependencies, Gitrefs.

## Non-goals
- No fullV3GRAPHIC/Consolidator/normativevalidation promise; no provider/browser/fullgate.

## Deliverables
- Mode selector requiresAI forV3; pinnedengine included inestimatequery/querykey/startbody/idempotencyintent; resumeusesrunengine.
- Show experimental provenance/nativeTEXT bounds16pages80kchars andactualprocedures; hideoldsevenstepstripforV3.
- Render card.experimental.parameters name/old_value/new_value/unit/location/verification safely; never callPENDINGverified.

## Required tests
- Typecheck/scopedlint andminimalpurechecksifuseful. No fullsuite.

## Integration contract
RoottransfersUIownershipfromrootto c4_seal_plan agent, priorversionsworkstable. NootheragenteditsUI. Backendfreezesexperimental_progress {engine,source_version,procedure,status,procedures:[{name,state}],coverage,limitations}; card.experimental {engine,event_id,engineering_subject,parameters:[{name,old_value,new_value,unit,location,verification?}],quality,source_sha256}. Deadline09:50UTC. OnlyrootGitwrites.

## Failure/idempotency/security cases
- Everychangedengineinvalidatesagreement; noAIoffV3; unknownstructuresdisplayexplicitunavailable, notfabricatedsuccess.

## Rollback / feature flag
Classic remains availableanddefault.

## Handoff
Inprogress.

Rootgrant2026-10-30: exactexistingweb/tests/unit/stage-run-controls/runs.test.ts andweb/tests/unit/stage-changes/screen.test.ts for meaningfulengine/PENDING/trueprocedure render guards.
