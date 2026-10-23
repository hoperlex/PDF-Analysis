# Task AR-V3-BETA-GROUP-API-SEAL-01 — serve the six-scope review

## Outcome
An authenticated `getArV3BetaGroupReview` read returns six ordered AR v3 beta scope outcomes with visible provisional evidence and explicit pending, failed and verification-refused states. No private review custody fields enter the response.

## Depends on
- `AR-V3-BETA-GROUP-REVIEW-01`

## Frozen inputs
- shared domain/API/analysis/events contract: `1.3.0` → additive `1.4.0`
- AR v3 beta stage extension: `1.0.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `e55192dc6141c3fb5762ae8f7292c09866aaa963`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `AR-V3-BETA-GROUP-API-SEAL-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface route error-code`

## Captured premise evidence
- premise: the persisted six-scope service is available but no public group review route exists
### P-01 — public read seam
- captured_at: 2026-10-23
- command: `rg -n 'getArV3BetaGroup|read_v3_group_review' src/auditmanager/api src/auditmanager/bootstrap/adapters.py src/auditmanager/runs/v3_group_review.py`
- captured_output: `getArV3BetaGroup` exists in the router and security register; `read_v3_group_review` exists only in the Runs service.
- interpretation: this task owns one additive route, its exact response schema and the synchronized contract family.

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
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/runs/v3_cite_stage_contract.py`
- `src/auditmanager/ingest/pdf_reader.py`
- `src/auditmanager/norms/bundle/manifest.py`
- `infra/deploy/proxy/**`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `web/openapi/**`
- `web/src/shared/**`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/FRONTEND_LOCK.json`
- `web/tests/**`
- `tests/contract/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/integration/db/test_routing_refusal_codes_migration.py`
- `tests/integration/norms/bundle/test_contents.py`
- `tests/integration/p02_journey/test_extractor_divergence.py`
- `tests/e2e/pc01/**`
- `tests/support/**`
- `tests/unit/analysis/text_profiles/test_text_profile_packages.py`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/WAVE_EXECUTION_GUIDE.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`
- `docs/program/tasks/AR-V3-BETA-GROUP-API-SEAL-01.md`
- `docs/program/AR-V3-BETA-GROUP-API-SEAL-01.md`
- `web/src/_app/navigation.ts`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
- `web/src/entities/audit-run/model/terminal-reason.ts`
- `web/src/entities/execution/model/presentation.ts`
- `web/src/shared/config/**`
- `web/src/shared/lib/routes.ts`
- `web/src/widgets/home-tiles/model/registrations-screen.ts`

## Forbidden hotspots
- migration head, root dependency/lock files, product VERSION, global styles
- normative map/source/set data, provider transports, raw deterministic comparison evidence
- `origin/main`, tag and deployment host

## Non-goals
- Approving six normative maps/sets, publishing numerical conclusions or activating production starts.
- A review screen; that follows this sealed typed API.
- Real PostgreSQL/S3/provider acceptance on this host.

## Deliverables
- One read-only route and safe response models bound to the existing six-scope projection.
- Synchronized `1.4.0` contract, generated client, frontend lock and independent pins.
- Focused tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1 tests/contract/analysis_packages -x --tb=short`
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/domain_p02 tests/contract/test_domain_identifiers_schema.py tests/integration/api/test_ar_v3_group_review_route.py tests/integration/api/test_role_register.py::test_the_registers_are_the_ruled_ones -x --tb=short`
- command: `npm --prefix web run api:verify`
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface route error-code --check docs/program/tasks/AR-V3-BETA-GROUP-API-SEAL-01.md`
- expected: focused checks pass; real DB-dependent API suite and full make gate deferred by R-135 and the absent local `DATABASE_URL`.

## Integration contract
`GET /ar-v3-beta/groups/{group_id}/review` returns exactly six ordered members, each with scope, Run ID, Run state, review state and a nullable terminal reason, refusal code and visible review. The route does not require a currently installed pack. Its service verifies saved review custody before exposing provisional topics/citations. Existing group read remains unchanged.

## Failure/idempotency/security cases
- Pending/failed Runs have no fabricated review; damaged completed review yields a member-level verification refusal.
- A changed group snapshot rejects the whole read; no provider call or DB write occurs.
- Existing bearer/role gate applies. Response contains no Blob ID, digest, answer text or numerical verdict.

## Rollback / feature flag
Read-only route; revert route, response, contract seal and generated client together. No migration or feature flag.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no screen or target stand acceptance
- integration notes: UI must consume this distinct review-only operation
