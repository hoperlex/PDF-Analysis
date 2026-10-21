# W56A-SEAL-01 — contract and migration handoff

**Status:** implementation candidate on `w56a/seal`, based on development SHA
`56978669f6a618ac75f91dc803b27369e3b6cebe`. No provider model identity
was inferred. `P02_LOCK.json` remains read-only at SHA-256
`2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.

## Result

- Contract is additive at version `1.0.0-draft.1`: 47 paths, 54 operations,
  124 schemas, 25 API error codes and 23 stored error codes. New categories,
  severity, canonical/merged observation fields, typed mismatch refusal and
  caller-safe terminal-message slot are declared. v1's new optional properties
  are absent from its serializers.
- Migration head `0022_findings_v2` widens only the current constraints, adds
  severity and canonical identity, backfills a sole historical observation,
  and refuses ambiguous legacy rows and retained-data downgrade. No historical
  migration changed.
- The decision port carries severity explicitly; until `W56A-DECIDE-01`, a
  non-null severity gets a typed dependency refusal before any write. Default
  v1 calls continue to omit the new wire fields.
- The generated frontend client and `FRONTEND_LOCK.json` match OpenAPI SHA-256
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`.
  Domain error catalog SHA-256 is
  `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  stage registry SHA-256 is
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`.

## Addressed checks

- Isolated PostgreSQL with cached pgvector image: clean upgrade to 0022,
  populated 0021 upgrade/backfill, corrupt 0021 refusal, CHECK/FK/view probes,
  and refused retained-data downgrade; focused migration tests **3 passed**.
- Contract/API/domain/analysis focused suite **450 passed, 2 deselected**.
  The two deselected prose guards read `CURRENT_STATE.md`, which is reserved for
  the integration slot. They remain an explicit integration check.
- Finding contract tests **15 passed**; pre-DECIDE refusal test **1 passed**;
  seam and old-bundle focused tests **74 passed**.
- Frontend contract tests **139 passed**; rendered-language and terminal-reason
  tests **62 passed**; typecheck, lint and `api:verify` passed.
- `git diff --check` and Python compilation passed. No full local gate ran.
- Service-backed API integration tests could not set up without the private S3
  configuration; the first failure was missing `S3_ENDPOINT_URL`. The W13
  byte-for-byte journey is likewise deferred with service-backed acceptance.
  `scripts/validate_bootstrap.py` reported seven pre-existing broken Markdown
  links outside this lane.

## Integrator action

Merge this exact branch into a dedicated W56a integration slot, update the
live head and surface claims in `CURRENT_STATE.md` from 0021/123 to 0022/124,
then rerun the two prose guards. Keep `P02_LOCK.json` and provider selection
frozen until `W56A-MODEL-PIN-01` proves both gateways. Dispatch
`W56A-GENERATOR-01` from the merged SEAL SHA. No full local gate, live acceptance,
`origin/main` publication or tag is part of this handoff.

## Pin sweep register

Command: `.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code`.
Each of the 98 printed paths is classified below. `review-only` means the
matching text is a historical claim, pattern or unaffected pin; `integration-only`
means the live claim is known to need the next integration commit.

| Path | Disposition | Sweep evidence |
| --- | --- | --- |
| `contracts/api/v1/openapi.json` | changed | error-code: catalogue; reseal-surface: catalogue |
| `contracts/domain/v1/error-codes.json` | changed | error-code: catalogue |
| `db/migrations/versions/**` | changed | migration: catalogue; table: catalogue |
| `docs/manual-tests/PC-01_prototype.md` | changed | migration: catalogue; migration: prose |
| `docs/manual-tests/README.md` | review-only | migration: prose |
| `docs/program/ALPHA_ROADMAP.md` | changed | error-code: live claims; error-code: prose; migration: live claims; reseal-surface: live claims; reseal-surface: prose; table: live claims |
| `docs/program/CONTRACT_PIN_REGISTRY.md` | changed | error-code: registry; migration: registry; reseal-surface: registry; table: registry |
| `docs/program/CURRENT_STATE.md` | integration-only | error-code: live claims; error-code: prose; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims |
| `docs/program/P02_SEAMS.md` | changed | error-code: live claims; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims |
| `infra/deploy/README.md` | review-only | reseal-surface: catalogue |
| `infra/deploy/compose.server.yml` | review-only | table: catalogue |
| `infra/deploy/deploy.sh` | review-only | table: catalogue |
| `infra/deploy/proxy/nginx.conf` | review-only | reseal-surface: catalogue; reseal-surface: prose |
| `infra/deploy/reset.sh` | review-only | table: catalogue |
| `infra/deploy/serve.py` | review-only | reseal-surface: catalogue; reseal-surface: pattern |
| `src/auditmanager/api/README.md` | review-only | reseal-surface: catalogue |
| `src/auditmanager/api/app.py` | changed | reseal-surface: catalogue; reseal-surface: live claim; reseal-surface: pattern |
| `src/auditmanager/api/health.py` | review-only | reseal-surface: live claim |
| `src/auditmanager/api/routers/__init__.py` | review-only | reseal-surface: pattern |
| `src/auditmanager/api/routers/blocks.py` | review-only | reseal-surface: live claim |
| `src/auditmanager/api/routers/errors.py` | review-only | migration: live claim |
| `src/auditmanager/documents/refusals.py` | review-only | migration: live claim |
| `src/auditmanager/ingest/pdf_reader.py` | review-only | reseal-surface: pattern |
| `src/auditmanager/norms/__main__.py` | review-only | migration: live claim |
| `src/auditmanager/norms/bundle/__init__.py` | review-only | migration: pattern |
| `src/auditmanager/norms/bundle/copy_record.py` | review-only | migration: live claim; migration: pattern |
| `src/auditmanager/norms/bundle/export.py` | review-only | migration: pattern |
| `src/auditmanager/norms/bundle/manifest.py` | review-only | migration: pattern; reseal-surface: pattern |
| `src/auditmanager/norms/bundle/stand.py` | review-only | migration: live claim; migration: pattern |
| `src/auditmanager/shared/db/__init__.py` | review-only | migration: pattern |
| `src/auditmanager/shared/db/check.py` | review-only | migration: live claim |
| `src/auditmanager/shared/db/errors.py` | review-only | migration: live claim |
| `src/auditmanager/shared/db/migrations.py` | review-only | migration: live claim; migration: pattern |
| `src/auditmanager/shared/db/schema.py` | review-only | migration: live claim |
| `src/auditmanager/shared/statemachine/topology.py` | review-only | migration: live claim |
| `src/auditmanager/storage/check.py` | review-only | migration: live claim |
| `tests/contract/api_v1/test_doc_prose_facts.py` | review-only | error-code: pattern; migration: catalogue; migration: migration-application-head; migration: pattern; reseal-surface: pattern; reseal-surface: surface-doc-prose-triple |
| `tests/contract/api_v1/test_openapi_conformance.py` | review-only | reseal-surface: pattern; reseal-surface: surface-conformance-operation-count; reseal-surface: surface-conformance-operation-set; reseal-surface: surface-conformance-schema-count; reseal-surface: surface-conformance-schema-set |
| `tests/contract/api_v1/test_surface_counts_in_prose.py` | review-only | reseal-surface: pattern |
| `tests/contract/domain_p02/test_contract_vocabulary.py` | changed | error-code: error-migration-domain-count; error-code: pattern; migration: pattern |
| `tests/contract/domain_p02/test_openapi_document.py` | review-only | error-code: error-openapi-enum-count; error-code: pattern; reseal-surface: pattern |
| `tests/contract/domain_p02/test_seam_register.py` | review-only | reseal-surface: pattern |
| `tests/contract/test_cp00_candidate.py` | review-only | error-code: pattern; migration: pattern |
| `tests/contract/test_proxy_rate_limits.py` | review-only | table: pattern |
| `tests/contract/tools/test_pin_sweep.py` | review-only | migration: pattern; reseal-surface: pattern |
| `tests/e2e/pc01/journey/manifest.json` | review-only | reseal-surface: catalogue |
| `tests/e2e/pc01/test_acceptance.py` | review-only | reseal-surface: pattern; reseal-surface: surface-e2e-composition |
| `tests/integration/api/driver.py` | review-only | reseal-surface: pattern |
| `tests/integration/api/test_authorization.py` | review-only | reseal-surface: pattern |
| `tests/integration/api/test_envelope_screen_rules.py` | review-only | error-code: error-screen-source-count; error-code: pattern |
| `tests/integration/api/test_operation_surface.py` | review-only | reseal-surface: pattern; reseal-surface: surface-path-and-operation-count; reseal-surface: surface-router-and-document-count; reseal-surface: surface-router-count |
| `tests/integration/api/test_role_register.py` | review-only | reseal-surface: pattern |
| `tests/integration/api/test_router_and_body_rules.py` | review-only | reseal-surface: pattern; reseal-surface: surface-router-operation-id-count; reseal-surface: surface-router-route-count-control |
| `tests/integration/api/test_served_document_and_health_plane.py` | review-only | reseal-surface: pattern; reseal-surface: surface-served-operation-count; reseal-surface: surface-served-path-count; reseal-surface: surface-served-schema-count |
| `tests/integration/composition/test_api_token_channel.py` | review-only | reseal-surface: pattern; reseal-surface: surface-composition-token-case |
| `tests/integration/composition/test_bundle_transport_refusals.py` | review-only | migration: pattern |
| `tests/integration/composition/test_composition_root.py` | review-only | reseal-surface: pattern; reseal-surface: surface-composition-proxy; reseal-surface: surface-composition-recorded |
| `tests/integration/composition/test_deployed_stack_probe.py` | review-only | table: pattern |
| `tests/integration/composition/test_norms_worker_image_contract.py` | review-only | error-code: pattern |
| `tests/integration/composition/test_proxy_config_follows_checkout.py` | review-only | table: pattern |
| `tests/integration/composition/test_reset_rehearsal_counts_base_tables.py` | review-only | table: catalogue; table: pattern |
| `tests/integration/composition/test_reset_script_refusals.py` | review-only | table: pattern |
| `tests/integration/composition/test_session_register_volume.py` | review-only | table: catalogue |
| `tests/integration/composition/test_stand_copy_refusals.py` | review-only | migration: pattern |
| `tests/integration/db/test_accounts_migration.py` | review-only | migration: pattern |
| `tests/integration/db/test_durable_analysis_effects.py` | review-only | migration: pattern |
| `tests/integration/db/test_migration_lifecycle.py` | review-only | migration: catalogue; migration: pattern; table: pattern |
| `tests/integration/db/test_release_notes_migration.py` | review-only | migration: pattern |
| `tests/integration/db/test_schema_shape.py` | review-only | table: catalogue; table: pattern |
| `tests/integration/foundation/test_cross_provider_publication.py` | review-only | migration: pattern |
| `tests/integration/norms/bundle/conftest.py` | review-only | migration: pattern |
| `tests/integration/norms/bundle/support.py` | review-only | migration: pattern |
| `tests/integration/norms/bundle/test_bundle_postgres.py` | review-only | migration: pattern |
| `tests/integration/norms/bundle/test_contents.py` | review-only | reseal-surface: pattern |
| `tests/integration/norms/bundle/test_copy_record.py` | review-only | migration: pattern |
| `tests/integration/norms/bundle/test_manifest.py` | review-only | migration: pattern |
| `tests/integration/p02_journey/journey.py` | review-only | table: catalogue; table: pattern |
| `tests/integration/p02_journey/test_extractor_divergence.py` | review-only | error-code: pattern |
| `tests/support/expected_facts.json` | changed | error-code: expected facts (error_catalog.api_codes, error_catalog.stored_vocabulary); migration: expected facts (migration_head); reseal-surface: expected facts (surface.path_count, surface.operations, surface.schema_names); table: expected facts (no table field; review alongside schema) |
| `tests/support/expected_facts.py` | review-only | migration: pattern; reseal-surface: pattern |
| `web/FRONTEND_LOCK.json` | changed | error-code: catalogue; reseal-surface: catalogue |
| `web/openapi/openapi.json` | changed | error-code: catalogue; reseal-surface: catalogue |
| `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx` | review-only | reseal-surface: live claim |
| `web/src/app/bff/v1/[...path]/route.ts` | review-only | reseal-surface: live claim |
| `web/src/entities/audit-run/model/terminal-reason.ts` | changed | error-code: pattern |
| `web/src/entities/execution/model/presentation.ts` | review-only | error-code: pattern |
| `web/src/shared/api/catalog-message.ts` | changed | error-code: pattern |
| `web/src/shared/api/errors.ts` | changed | error-code: pattern |
| `web/src/shared/api/generated/**` | changed | error-code: catalogue; reseal-surface: catalogue |
| `web/src/shared/api/generated/operations.gen.ts` | changed | reseal-surface: pattern |
| `web/src/shared/api/generated/types.gen.ts` | changed | error-code: pattern |
| `web/tests/contract/catalog-message.contract.test.ts` | review-only | error-code: pattern |
| `web/tests/contract/pc01-error-codes.contract.test.ts` | review-only | error-code: pattern |
| `web/tests/contract/seam-operations.contract.test.ts` | review-only | error-code: error-frontend-contract-enum-count; error-code: pattern; reseal-surface: pattern |
| `web/tests/contract/terminal-reason-sentences.contract.test.ts` | review-only | error-code: pattern |
| `web/tests/guards/frontend-lock.guard.test.ts` | review-only | error-code: catalogue; reseal-surface: catalogue; reseal-surface: pattern; reseal-surface: surface-frontend-lock-operations; reseal-surface: surface-frontend-lock-paths; reseal-surface: surface-frontend-lock-schemas |
| `web/tests/unit/api/failure-surface.test.ts` | review-only | error-code: error-frontend-failure-enum-count; error-code: pattern |
| `web/tests/unit/screens/run-terminal-reason.test.ts` | changed | error-code: pattern |

## Ownership proof and limitations

Changed files are the `git show --name-only` set of the eventual lane commit;
all **51** sit inside the amended `W56A-SEAL-01` allowlist (0 outside). In particular,
`P02_LOCK.json`, `VERSION`, root dependency/lock files, old migrations,
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, global styles, the knowledge-base filter,
`origin/main` and deployment state were not changed. The task-file amendment
names the five otherwise ungranted direct pins/tests before their edits.
The generated contract has no gateway model name, and no v2 analysis or decision
fold is active. The local PostgreSQL container was stopped after the focused
migration tests.
