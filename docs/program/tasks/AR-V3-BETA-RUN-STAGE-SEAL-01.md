# Task AR-V3-BETA-RUN-STAGE-SEAL-01 — expose v3 CITE stage in RunStatus

## Outcome
The served `RunStatus` contract can represent the profile-specific `ar_v3_citation_review` stage and failed-stage degradation without widening the nine legacy analysis stages. The shared family contract advances additively to `1.3.0`, with synchronized source, mirror, generated client, lock and independent pins.

## Depends on
- `AR-V3-BETA-CITE-STAGE-CONTRACT-01`
- `AR-V3-BETA-CITE-WRITER-01`
- `AR-V3-BETA-SETTINGS-REPLAY-01`

## Frozen inputs
- prior shared family contract: `1.2.0`
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `220412634267037c8b5ad561df9b04bdf5c3801a`
- stage extension: `contracts/analysis/ar_v3_beta/v1/stage.json` `1.0.0`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `AR-V3-BETA-RUN-STAGE-SEAL-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface route error-code`

## Captured premise evidence
- premise: current API `StageId` lists nine legacy stages and `RunStatus` refers to it for stage states and degradation
### P-01 — stage surface
- captured_at: 2026-10-23
- command: `rg -n 'class StageId|stage_id: StageId|degradation_set: list\[StageId\]|"StageId"|"StageState"|"RunStatus"' src/auditmanager/api/schemas/models.py contracts/api/v1/openapi.json`
- captured_output: `StageId` at models.py 579 has nine values; `StageState.stage_id` at 1046 and `RunStatus.degradation_set` at 1078 use it. OpenAPI carries the same three schemas.
- interpretation: persisted v3 CITE rows cannot be represented without a profile-specific API extension.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `contracts/analysis/v1/**`
- `contracts/analysis/ar_v3_beta/v1/stage.json`
- `contracts/events/v1/**`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/runs/v3_cite_stage_contract.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `web/openapi/**`
- `web/src/shared/api/**`
- `web/FRONTEND_LOCK.json`
- `web/tests/**`
- `tests/contract/**`
- `tests/support/expected_facts.json`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/AR-V3-BETA-RUN-STAGE-SEAL-01.md`
- `docs/program/tasks/AR-V3-BETA-RUN-STAGE-SEAL-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- migration head, root dependencies/lockfiles, product VERSION, composition root, global styles
- provider transports, normative maps/source/set data, existing nine-stage registry membership
- `origin/main`, tag and deployment host

## Non-goals
- Serving v3 provider/CITE execution or claiming normative authority.
- Adding a route, new error code or database migration.

## Deliverables
- New `ArV3BetaStageId` API enum and union only in RunStatus stage/degradation positions.
- Family `1.3.0` reseal, generated client, frontend lock, pins and focused tests.
- Result note with exact changed-path and compatibility evidence.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1 tests/contract/analysis_packages -x --tb=short`
- command: `npm --prefix web run api:verify`
- command: `npm --prefix web run test:guards`
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface route error-code --check docs/program/tasks/AR-V3-BETA-RUN-STAGE-SEAL-01.md`
- expected: focused checks pass and exact changed paths fit this ownership slot. Full make gate deferred by R-135.

## Integration contract
Legacy `StageId` remains the same nine-member enum and its analysis registry unchanged. Only RunStatus StageState/degradation accepts the new profile-specific ID. Old clients continue to receive their known values on legacy runs; new clients can render v3 CITE. All machine documents and served `contract_version` holders agree on `1.3.0`.

## Failure/idempotency/security cases
- Unknown stage IDs still refuse schema validation.
- V3 CITE does not imply a canonical finding or expert decision.
- A frozen `1.2.0` client is not silently treated as proof of `1.3.0` compatibility.

## Rollback / feature flag
No served v3 path is enabled by this seal. Revert the synchronized seal as a unit before v3 execution activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: served wiring, approved pack and real acceptance remain
- integration notes: worker must use this sealed stage ID only for the v3 profile
