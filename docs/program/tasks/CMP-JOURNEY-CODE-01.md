# Task CMP-JOURNEY-CODE-01 — runnable comparison journey and static API exposure review

## Outcome
The existing journey harness can execute concrete version/stage comparison actions and assert their persisted effects against the synthetic corpus and recorded provider. A static exposure table identifies the 32 C3 and 23 C4 operations and their auth, role, body, key, scope, cost and stream boundaries without claiming executed acceptance.

## Depends on
- CMP-STAGE-REVIEW-UI-01
- CMP-SEAL-C4

## Frozen inputs
- domain contract: ADR-0025 and `docs/program/dispatch/COMPARE-MODULES-PLAN.md`
- API contract: C4 `1.13.0`; generated client/contract and runtime wiring belong to root
- migration head: `0042_comparison_stage_review`
- base commit: `88525cd93067184d77f6fc4a76ab54205097db71`
- existing journey manifest/harness and synthetic comparison corpus; recorded providers only

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/e2e/pc01/journey/manifest.json`
- enumerator_owner: CMP-JOURNEY-CODE-01
- totality_query: parse all manifest write step IDs, require uniqueness and preserved pre-existing IDs; compare new comparison operation IDs with sealed OpenAPI

## Captured premise evidence
- premise: the existing journey has module read routes but no dedicated C3/C4 comparison write walkthrough.

### P-01 — assigned base and existing routes
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n '"name": "(stage-compare|version-comparison)"' tests/e2e/pc01/journey/manifest.json`
- captured_output:
  ```text
  88525cd93067184d77f6fc4a76ab54205097db71
  804:      "name": "stage-compare",
  825:      "name": "version-comparison",
  ```
- interpretation: extend the maintained instrument and retain old routes/steps; no second planner or fake success path.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/e2e/pc01/journey/**`
- `docs/program/tasks/CMP-JOURNEY-CODE-01.md`
- `docs/program/CMP-JOURNEY-CODE-01.md`
- `docs/program/compare/EXPOSURE-REVIEW-CMP.md`

## Forbidden hotspots
- application/shared/generated source, contracts, migrations, dependency/lock files, page mounts, composition root, global styles, remote refs and deployment

## Non-goals
- no browser run, build, full gate, heavy test window or live paid model call today
- no skip/PASS masking, no deletion of existing journey paths, no fabricated canonical IDs
- exposure review is static and must distinguish code pointers from unexecuted runtime evidence

## Deliverables
1. Real journey actions/assertions for version upload/matrix/viewer/recorded AI/export and stage assembly/map/batch/repair undo/verdict/journal.
2. Manifest entries and runnable implementation using the existing harness, corpus and recorder.
3. A 55-operation static exposure table with exact code pointers and explicitly unverified integration claims.
4. Focused syntax/manifest conformance evidence and integration instructions.

## Required tests
- `node --check` for edited/new modules
- short manifest conformance only; no browser/build/full gate
- `git diff --check`

## Integration contract
Root integrates the local commit and completes runtime wiring. The journey must fail on missing UI/API effects and may be unexecuted today; no code-complete or syntax check is acceptance. Existing partial/pending/failure accounting remains intact.

## Failure/idempotency/security cases
- new comparison steps require recorded provider mode and fail closed for missing corpus/module/route prerequisites
- request capture checks command keys and retained identities; downloads assert real response type/content
- anonymous/role and scope exposure findings are static until a runtime request proves them

## Rollback / feature flag
Journey-only changes do not alter product behavior. Removing the newly named comparison steps restores the earlier instrument while keeping existing route paths and step IDs intact.

## Handoff
- state: in progress; root reprioritised the C4 page mount lane after this independently runnable version/exposure slice
- changed files: journey `manifest.json`, `write.mjs`, `cdp.mjs`, `comparison-conformance.mjs`, README, task/report and dated exposure table
- checks: node syntax checks and existing manifest conformance (135 passed); static comparison/corpus census checked separately
- outstanding: concrete C4 assembly/map/batch/repair/verdict/journal steps after the root's UI mounts; this task is not complete and no browser acceptance is claimed
- contracts: none
- integration notes: no remote authority; tomorrow execute against the exact integrated recorded-provider candidate
