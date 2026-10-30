# Task CMP-C4-READ-SEAMS-01 — assembly revision and stored page text

## Outcome
The C4 assembly GET returns the real membership-event revision, and stored profile words are available for per-panel search before a comparison run.

## Depends on
- CMP-SEAL-C4
- CMP-STAGE-PAIR-01

## Frozen inputs
- API `1.13.0`, 227 paths / 253 operations / 613 schemas; additive StageAssembly field only
- migration `0042_comparison_stage_review`, unchanged
- base commit `39f65c8d934a5d951b6a357b3b54a18e6b84584d`
- observed gap: assembly active members omit removal-event numbers, while revise checks max of every event

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: existing read/revise use different counters and C4 GETs are still typed stubs

## Historical evidence
- correction_mode: addendum
- source_record: `docs/program/CMP-SEAL-C4.md`
- addendum_path: `docs/program/CMP-C4-READ-SEAMS-01.md`

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/stage/assemblies.py`
- `src/auditmanager/comparison/stage/profile_text.py`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/routers/comparison_stage_c4.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `contracts/api/v1/openapi.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `tests/integration/comparison/stage/**`
- `tests/unit/comparison/stage/**`
- `tests/contract/api_v1/test_cmp_seal_c4.py`
- `docs/program/tasks/CMP-C4-READ-SEAMS-01.md`
- `docs/program/CMP-C4-READ-SEAMS-01.md`

## Forbidden hotspots
- migration head, root dependency locks, global styles, unrelated runtime and remote refs

## Non-goals
- no source PDF extraction/model call during a read; no heavy gate

## Deliverables
- `member_revision_no` from every membership event, read adapter and stored-word reader
- generated client/lock update and short checks

## Required tests
- focused read/revision tests, API client verification/typecheck; full gates deferred by owner

## Integration contract
UI sends `StageAssembly.member_revision_no` as revise.base_member_no. Page text reads the immutable profile archive through its public reader; no router accesses blobs. Root owns this serial additive contract slot before dev publication.

## Failure/idempotency/security cases
- missing assembly/profile refuses; unavailable archive never becomes a textless-page claim
- no silent text truncation

## Rollback / feature flag
Stages module gates both reads. Additive DTO field requires no data rollback.

## Handoff
- changed files: task/report, assembly/profile services, public export, schema/router/port, adapters/composition and generated API
- checks/results: focused assembly/C4 contract **9 passed**, client verify **253 operations OK**, web typecheck passed
- contracts: additive StageAssembly.member_revision_no, counts unchanged
- known limits: full acceptance tomorrow
- integration notes: root dev only
