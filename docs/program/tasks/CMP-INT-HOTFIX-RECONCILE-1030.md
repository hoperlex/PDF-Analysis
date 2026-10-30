# CMP-INT-HOTFIX-RECONCILE-1030

## Outcome
Preserve the owner's newly published dev hotfixes99b337fb/06b94745 together with CMP C2–C4, instead of overwriting either line. The combined contract is1.13.0 at228/254/614 with migration0043.

## Depends on
- HOTFIX-SECTION-LIMITS-INT-20261030
- CMP-STAGE-AI-GENERATIONS-SEAL-01

## Frozen inputs
Remote dev99b337fb, remote main2c162f76, merge basee8567a19; CMP integration43b14217. Owner has authorised dev code publication and deferred full gates. Main is unauthorised.

## Allowed paths
- Completed incoming files named by `git diff --name-only e8567a19..99b337fb`
- contracts/** (serial root reconciliation of current version and additive fields)
- src/auditmanager/analysis/engine/result.py
- src/auditmanager/api/schemas/models.py
- src/auditmanager/comparison/stage_review/service.py (whole classifier evidence bound400)
- tests/contract/api_v1/test_contract_seal.py
- tests/support/expected_facts.json
- web/src/shared/api/generated/**
- web/openapi/openapi.json
- web/FRONTEND_LOCK.json
- web/src/shared/api/authorization.ts
- docs/program/tasks/CMP-INT-HOTFIX-RECONCILE-1030.md
- docs/program/CMP-INT-HOTFIX-RECONCILE-1030.md

## Forbidden hotspots
Remote main, force push, root dependency/lockfiles, deployment and unrelated owner files.

## Non-goals
No new default spending grant; preserve the owner's default-off relaxed_limits controls and their accounting. No full gate, browser window or live call.

## Deliverables
Three-way merge preserving all incoming source/UI behavior and every CMP API operation; regenerated client/lock; one coherent shared version1.13 and catalogue revision31; promoted source list bound400 so a whole classifier card can be reviewed.

## Verification
Focused contract-seal/client/compilation/typecheck and changed-area checks. Full gates deferred. Remote dev is fetched and must be an ancestor before publication.

## Integration contract
Root alone resolves shared hotspots and publishes dev. Incoming historical seal notes remain historical; combined current totals/version supersede them. Every relaxed-limit flag remains fingerprinted and persisted as in the owner's hotfixes.

## Rollback
Modules can be disabled. Rollback uses forward commits and never force-ref updates.
