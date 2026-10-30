# Task CMP-SEAL-C4 — stage AI, repair, review and full-run boundary

## Outcome
API 1.13.0 and migration 0042 provide typed module-gated contracts and durable project-scoped storage for C4 runtime lanes, including the C3 reverse-hint/profile-viewer seams.

## Depends on
- CMP-SEAL-C3

## Frozen inputs
- domain: ADR-0025 decisions 2–7, 16–19, 21–26; COMPARE-MODULES-PLAN C4
- API: additive successor to 1.12.0 (204 paths, 230 operations, 570 schemas)
- migration head: 0041_comparison_stage_core
- base commit: `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`
- owner override 2026-10-30: write functional code today; full gates and heavy verification tomorrow; root remains sole integrator and origin/dev writer

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: src/auditmanager/api/routers/comparison_stage_c4.py
- enumerator_owner: CMP-SEAL-C4
- totality_query: `rg -n 'operation_id=' src/auditmanager/api/routers/comparison_stage_c4.py`

## Captured premise evidence
- premise: C3 has no C4 API or tables; executor stage-review kind and AI job scope are absent.

### P-01 — base
- captured_at: 2026-10-30
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e
  ```
- interpretation: this additive seal owns the contract/migration slot on the C3 implementation base.

## Historical evidence
- correction_mode: addendum
- source_record: ADR-0025 and CMP-SEAL-C3
- addendum_path: docs/program/CMP-SEAL-C4.md

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `contracts/**`
- `db/migrations/**`
- `src/auditmanager/api/schemas/**`
- `src/auditmanager/api/routers/**`
- `src/auditmanager/api/security.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/comparison/ai_jobs/model.py`
- `src/auditmanager/comparison/ai_jobs/repository.py`
- `src/auditmanager/comparison/ai_jobs/service.py`
- `src/auditmanager/comparison/work/repository.py`
- `src/auditmanager/executors/model.py`
- `src/auditmanager/shared/identity/ids.py`
- `src/auditmanager/shared/identity/__init__.py`
- `src/auditmanager/shared/errors/catalog.py`
- `src/auditmanager/access/references.py`
- `web/src/shared/api/generated/**`
- `web/src/shared/api/authorization.ts`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/entities/version-series/model/ai-words.ts`
- `web/src/entities/version-series/model/estimate.ts`
- `web/tests/**`
- `web/src/entities/executor-connection/model/vocabulary.ts`
- `web/src/widgets/executor-routes/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/openapi/openapi.json`
- `web/FRONTEND_LOCK.json`
- `scripts/recovery/grant_classification.py`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/project_erase.py`
- `scripts/recovery/blob_reference_audit.py`
- `infra/deploy/apply-grants.sh`
- `tests/contract/api_v1/test_cmp_seal_c4.py`
- `tests/contract/api_v1/test_stage_seal.py`
- `tests/integration/composition/test_comparison_stage_stub_operations.py`
- `tests/unit/comparison/ai_jobs/test_model_and_estimate.py`
- `tests/support/expected_facts.json`
- `docs/program/tasks/CMP-SEAL-C4.md`
- `docs/program/CMP-SEAL-C4.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `.venv`
- `.env`
- `web/node_modules`

## Lane resources
- foundation_instance: `auditmanager-cmp-seal-c4`
- postgres_port: `58040`
- s3_api_port: `62040`
- s3_console_port: `62041`
- postgres_db: `auditmanager_cmp_seal_c4`
- s3_bucket: `auditmanager-cmp-seal-c4`

## Forbidden hotspots
- root dependencies/locks, global styles, C2 runtime except explicit AI-scope seam, C3 implementation, deployment execution/policy, remote refs

## Non-goals
- no C4 algorithms, live model calls, generic exports writer, full gate, deployment or publication

## Deliverables
- typed C4 API/models/stubs, additive IDs and closed system/category vocabulary
- 0042 project-scoped evidence/repair/card/verdict/batch storage, AI-job stage scope and reverse hints
- generated client and focused seal evidence for downstream runtime lanes

## Required tests
- schema import/OpenAPI generation, client verify, focused seal tests, git diff --check
- full contract/database/recovery/gate windows explicitly deferred by owner to tomorrow

## Integration contract
Root merges the local seal before runtime lanes. Every new operation is bearer-authenticated and module gated; every write is keyed and expert-only. C4 AI uses shared consent/spend under stage_review scoped to stage_chain_run_id. Cards and raw evidence remain separate; exports are deterministic read streams.

## Failure/idempotency/security cases
- module off refuses before work; typed stubs refuse without side effects
- cross-project FK/scope guards; immutable evidence; keyed expert history; populated downgrade refusal

## Rollback / feature flag
AUDITMANAGER_COMPARISON_MODULES=none/versions keeps stage operations unavailable; no populated schema downgrade.

## Handoff
- changed files: API/domain/analysis/event version family, C4 models/router/port/stubs, shared AI/work scope seams, 0042 migration, identities, recovery/actor/grants inventories, generated API mirror/client and narrow web enum/version pins; exact list follows in SHA-bound evidence
- checks: focused provider 57 passed; identifier catalogue 32 passed; isolated migration up/down/reup and12-table rollback insert smoke passed; client/typecheck/C2-consent final figures in report/evidence
- contracts: API 1.13.0 / migration 0042
- known limits: runtime remains lane-owned; heavy windows tomorrow
- integration: local commit only; root owns merge and dev
