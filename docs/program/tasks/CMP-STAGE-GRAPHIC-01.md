# Task CMP-STAGE-GRAPHIC-01 — real stage graphic evidence and source crops

## Outcome
Full stage-chain step3 computes real bounded per-sheet engine results for degree-one links, stores reliable graphic regions with registration proof and serves exact source-profile crops to the AI caller. Unsupported/unreliable links explicitly say graphics were not checked.

## Depends on
- CMP-SEAL-C4
- CMP-ENGINE-01
- CMP-STAGE-TEXT-RECOMPUTE-01
- CMP-STAGE-REVIEW-01

## Frozen inputs
- domain: ADR-0025 stage evidence / no raw rewrite; COMPARE-MODULES-PLAN GRAPHIC bridge
- API: 1.13.0, existing StageGraphicEvidence and list operation; no API change
- migration head: 0042_comparison_stage_review
- base commit: `646a9e17bfa552eb251253b9e8415966088fbc74`
- public engine: compare_sheet_pair accepts two profile IDs and returns a real cached comparison_sheet_pair_result_id without a sheet pair/transition
- owner override 2026-10-30: functional dev code today, full gates/heavy windows tomorrow

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: existing engine accepts profile identities directly; C4 graphic evidence table references its real result.

### P-01 — isolated base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  646a9e17bfa552eb251253b9e8415966088fbc74
  ```
- interpretation: root owns integration/wiring; no synthetic sheet-pair identity is needed.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage_graphic/**`
- `tests/unit/comparison/stage_graphic/**`
- `tests/integration/comparison/stage_graphic/**`
- `docs/program/tasks/CMP-STAGE-GRAPHIC-01.md`
- `docs/program/CMP-STAGE-GRAPHIC-01.md`
- `.venv`
- `.env`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

Root explicitly reassigned this now-idle stack sequentially after completed seal/review lanes.

## Forbidden hotspots
- contracts, migrations, shared public/wiring/composition, dependency/lock files, global styles, remote refs

## Non-goals
- no model interpretation as raw evidence, no fake comparison pair/transition ID, no PyMuPDF, no generic renderer/export abstraction, no whole battery/build/gate

## Deliverables
- StageGraphicService bounded advance, immutable per-link receipts, raw region/proof projection and exact profile/box crops
- focused pure geometry/policy tests and small real-engine/DB smoke
- report and local commit for root integration

## Required tests
- focused unit and isolated DB/actual-engine tests; git diff --check
- expected: reliable 1↔1 produces evidence, unsupported/failed registration never produces a graphic change claim

## Integration contract
StageGraphicService(sessions,*,blob_store,runner=None,material=None) has constructor-only dependency assignment. advance(item,run_id) processes at most one map link, returns Yielded until every link has a durable receipt, then counts. Root owns step3 wiring. evidence(run_id) returns reliable nonempty sge atomic evidence with stored raw regions/registration; crop(run_id,evidence_id,region_key,side,long_side_px=1400) returns exact native-profile PNG bytes and coordinates. No external side effect is dual-written: existing engine owns its blob-first result publication, stage receipt is DB-only and lease-fenced.

## Failure/idempotency/security cases
- one-sided/many-to-many links are explicit not_checked, no fake absence or graphic claim
- unreadable/render-failed profiles and unreliable/partial registration are explicit non-reliable outcomes
- source identities and inverse affine boxes remain within profile dimensions, no caller-supplied arbitrary source path
- lost/foreign work cannot publish; content-key replay never recomputes a completed link
- a lost lease between engine result and stage receipt leaves a valid engine cache row for the next attempt

## Rollback / feature flag
Root retains stages module gate and previous explicit not_checked projection until integration; immutable raw evidence remains stored.

## Handoff
- status: completed
- changed files/checks/limits: `docs/program/CMP-STAGE-GRAPHIC-01.md`; 12 unit, 2 DB and 1 actual-engine smoke passed
- contracts: none
- integration: local commit only, root wires/merges/publishes
