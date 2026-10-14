# W56A-PREFREEZE-01 — freeze-input inventory on the W55b candidate

**Task:** `tasks/W56A-PREFREEZE-01.md`. **Base:** `8c5a109bd98302b64fb47b364d4c639ff63c0eda`.
**Scope:** read-only investigation, except this task file and report. W55b acceptance is still
open; this is not `W56A-FREEZE-01`.

## 1. Findings

| Input | Evidence on the base | Status for the freeze |
| --- | --- | --- |
| W55b close | `git rev-parse integration/w55b` → `8c5a109b`; `rg --files docs/program \| rg 'W55B-INT-CLOSE\|W56A-FREEZE-01'` → no match | **Pending.** Freeze and implementation wait for `W55B-INT-CLOSE`; rerun every state-dependent sweep on its SHA. |
| Frozen surface | `CURRENT_STATE.md` live section: 47 paths / 54 operations / 123 schemas, error catalog 24, domain revision 12, migration `0021_portal_bundles`; the three SHA-256 values are in the task file | Verified on `8c5a109b`; `0022_findings_v2` is the planned next migration, not yet granted. |
| Proxy routing | `git merge-base --is-ancestor 63cb3ca HEAD` → exit 0; `proxy.py` and `provider.env.example` carry the gateway prefix | `W48-PROXY-01` is in this candidate. |
| Model lock | `P02_LOCK.json:62-70`: `claude-opus-5` at $5/$25 and `claude-sonnet-5` at $2/$10 per million input/output tokens; no `gateway_name` key (`rg -n '"gateway'` finds none) | Gateway names and price tolerance must be pinned by the freeze's two-gateway, two-call identity probe. No live call was made here. |
| Proxy error debt | `DEBT_REGISTER.md` D-133 § row: 402/403/404 and unclassified 5xx mapping/logging repaired by `W52-DEBT-CODE-133`; typed `RunStatus` stage message and startup model policy remain open | `W56A-SEAL-01` and `W56A-PROVIDER-01` must carry the remaining class/message/startup work. Live QA remains D-139; full gate remains D-140. |
| Legacy АР inputs | The plan names `prompts/disciplines/AR/{finding_categories,checklist,role,drawing_types,project_params}.md` and `backend/app/data/discipline_checklists/AR.md`; `W56-RESEARCH.md` at planning SHA `2b45a11e` names `/root/projects/PDF-proverka/PDF-proverka` | **Missing on this host:** `ls -ld /root/projects/PDF-proverka /root/projects/PDF-proverka/PDF-proverka` exits 2. Do not invent or port content until the owner gives a source; ask for the path/archive and verify six file digests at freeze. |
| Research provenance | `git ls-tree -r --name-only 2b45a11e docs/program/reviews` contains `W56-RESEARCH.md` and `W56-PLAN-JUDGING.md`; the former's SHA-256 is `5c3050b8e14cf3db361c821cee15bef61ccf53488ca63a0da23ddca6f005aea8` | These two files are absent from the W55b candidate. The freeze cites the immutable planning SHA or imports reviewed copies through its own grant. The full research reports exist only in that planning session's transcript. |
| Release predecessor | `VERSION` is `0.6.0`. `git grep -n '0\.6\.0' -- tests web/tests` found only the release-note form test and the release loader test | The RELNOTES grant needs both paths, plus a fresh sweep after W55b close. Occurrences of `0.5.0` in worker-version fixtures are not automatically release pins. |

## 2. Checks and advisory pin inventory

On this base, `/root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py
reseal-surface migration table error-code` exited 0 and emitted **98 paths**; stdout SHA-256
`dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b`.
The output is an advisory inventory, including broad patterns and paths that may need only
review. `W56A-FREEZE-01` must grant every actual writer after the accepted-base rerun; this
report grants none. Complete output follows in §5.

`git diff --check` and the exact changed-path proof run after this report is committed.

## 3. Stops and limits

The accepted W55b SHA, legacy source files and their digests, and both gateway identity probes
are still absent. They are genuine freeze inputs, not values to fill by inference. The owner
has been asked for the legacy source location. No credential, private portal export, paid model
call, stand or service was used. The plan's `R-Z1`…`R-Z6` placeholders are replaced on the
separate `W56A-RULE-01` branch `227ac151`; its ruling numbers must be checked again before
integration because W55b may take intervening numbers.

## 4. Integration handoff, contracts and rollback

After `W55B-INT-CLOSE`, first integrate/rebase `W56A-RULE-01` and verify its ruling numbers.
Then rerun §2 on the accepted SHA, verify the six legacy file digests, perform the gateway
probes within the wave's spend ledger, fix any stop they reveal, and issue `W56A-FREEZE-01`
with the actual migration/head, port grants and remeasurement tolerance. No SEAL or Stage B
lane can use this report as its freeze.

This task changes no contract, migration, dependency, lockfile, composition root or global
style. Rollback is deletion/reversion of the two document paths only. The exact diff proof
after commit is the forbidden-hotspot check.

## 5. Complete advisory pin-sweep output

```text
contracts/api/v1/openapi.json	error-code: catalogue; reseal-surface: catalogue
contracts/domain/v1/error-codes.json	error-code: catalogue
db/migrations/versions/**	migration: catalogue; table: catalogue
docs/manual-tests/PC-01_prototype.md	migration: catalogue; migration: prose
docs/manual-tests/README.md	migration: prose
docs/program/ALPHA_ROADMAP.md	error-code: live claims; error-code: prose; migration: live claims; reseal-surface: live claims; reseal-surface: prose; table: live claims
docs/program/CONTRACT_PIN_REGISTRY.md	error-code: registry; migration: registry; reseal-surface: registry; table: registry
docs/program/CURRENT_STATE.md	error-code: live claims; error-code: prose; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims
docs/program/P02_SEAMS.md	error-code: live claims; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims
infra/deploy/README.md	reseal-surface: catalogue
infra/deploy/compose.server.yml	table: catalogue
infra/deploy/deploy.sh	table: catalogue
infra/deploy/proxy/nginx.conf	reseal-surface: catalogue; reseal-surface: prose
infra/deploy/reset.sh	table: catalogue
infra/deploy/serve.py	reseal-surface: catalogue; reseal-surface: pattern
src/auditmanager/api/README.md	reseal-surface: catalogue
src/auditmanager/api/app.py	reseal-surface: catalogue; reseal-surface: live claim; reseal-surface: pattern
src/auditmanager/api/health.py	reseal-surface: live claim
src/auditmanager/api/routers/__init__.py	reseal-surface: pattern
src/auditmanager/api/routers/blocks.py	reseal-surface: live claim
src/auditmanager/api/routers/errors.py	migration: live claim
src/auditmanager/documents/refusals.py	migration: live claim
src/auditmanager/ingest/pdf_reader.py	reseal-surface: pattern
src/auditmanager/norms/__main__.py	migration: live claim
src/auditmanager/norms/bundle/__init__.py	migration: pattern
src/auditmanager/norms/bundle/copy_record.py	migration: live claim; migration: pattern
src/auditmanager/norms/bundle/export.py	migration: pattern
src/auditmanager/norms/bundle/manifest.py	migration: pattern; reseal-surface: pattern
src/auditmanager/norms/bundle/stand.py	migration: live claim; migration: pattern
src/auditmanager/shared/db/__init__.py	migration: pattern
src/auditmanager/shared/db/check.py	migration: live claim
src/auditmanager/shared/db/errors.py	migration: live claim
src/auditmanager/shared/db/migrations.py	migration: live claim; migration: pattern
src/auditmanager/shared/db/schema.py	migration: live claim
src/auditmanager/shared/statemachine/topology.py	migration: live claim
src/auditmanager/storage/check.py	migration: live claim
tests/contract/api_v1/test_doc_prose_facts.py	error-code: pattern; migration: catalogue; migration: migration-application-head; migration: pattern; reseal-surface: pattern; reseal-surface: surface-doc-prose-triple
tests/contract/api_v1/test_openapi_conformance.py	reseal-surface: pattern; reseal-surface: surface-conformance-operation-count; reseal-surface: surface-conformance-operation-set; reseal-surface: surface-conformance-schema-count; reseal-surface: surface-conformance-schema-set
tests/contract/api_v1/test_surface_counts_in_prose.py	reseal-surface: pattern
tests/contract/domain_p02/test_contract_vocabulary.py	error-code: error-migration-domain-count; error-code: pattern; migration: pattern
tests/contract/domain_p02/test_openapi_document.py	error-code: error-openapi-enum-count; error-code: pattern; reseal-surface: pattern
tests/contract/domain_p02/test_seam_register.py	reseal-surface: pattern
tests/contract/test_cp00_candidate.py	error-code: pattern; migration: pattern
tests/contract/test_proxy_rate_limits.py	table: pattern
tests/contract/tools/test_pin_sweep.py	migration: pattern; reseal-surface: pattern
tests/e2e/pc01/journey/manifest.json	reseal-surface: catalogue
tests/e2e/pc01/test_acceptance.py	reseal-surface: pattern; reseal-surface: surface-e2e-composition
tests/integration/api/driver.py	reseal-surface: pattern
tests/integration/api/test_authorization.py	reseal-surface: pattern
tests/integration/api/test_envelope_screen_rules.py	error-code: error-screen-source-count; error-code: pattern
tests/integration/api/test_operation_surface.py	reseal-surface: pattern; reseal-surface: surface-path-and-operation-count; reseal-surface: surface-router-and-document-count; reseal-surface: surface-router-count
tests/integration/api/test_role_register.py	reseal-surface: pattern
tests/integration/api/test_router_and_body_rules.py	reseal-surface: pattern; reseal-surface: surface-router-operation-id-count; reseal-surface: surface-router-route-count-control
tests/integration/api/test_served_document_and_health_plane.py	reseal-surface: pattern; reseal-surface: surface-served-operation-count; reseal-surface: surface-served-path-count; reseal-surface: surface-served-schema-count
tests/integration/composition/test_api_token_channel.py	reseal-surface: pattern; reseal-surface: surface-composition-token-case
tests/integration/composition/test_bundle_transport_refusals.py	migration: pattern
tests/integration/composition/test_composition_root.py	reseal-surface: pattern; reseal-surface: surface-composition-proxy; reseal-surface: surface-composition-recorded
tests/integration/composition/test_deployed_stack_probe.py	table: pattern
tests/integration/composition/test_norms_worker_image_contract.py	error-code: pattern
tests/integration/composition/test_proxy_config_follows_checkout.py	table: pattern
tests/integration/composition/test_reset_rehearsal_counts_base_tables.py	table: catalogue; table: pattern
tests/integration/composition/test_reset_script_refusals.py	table: pattern
tests/integration/composition/test_session_register_volume.py	table: catalogue
tests/integration/composition/test_stand_copy_refusals.py	migration: pattern
tests/integration/db/test_accounts_migration.py	migration: pattern
tests/integration/db/test_durable_analysis_effects.py	migration: pattern
tests/integration/db/test_migration_lifecycle.py	migration: catalogue; migration: pattern; table: pattern
tests/integration/db/test_release_notes_migration.py	migration: pattern
tests/integration/db/test_schema_shape.py	table: catalogue; table: pattern
tests/integration/foundation/test_cross_provider_publication.py	migration: pattern
tests/integration/norms/bundle/conftest.py	migration: pattern
tests/integration/norms/bundle/support.py	migration: pattern
tests/integration/norms/bundle/test_bundle_postgres.py	migration: pattern
tests/integration/norms/bundle/test_contents.py	reseal-surface: pattern
tests/integration/norms/bundle/test_copy_record.py	migration: pattern
tests/integration/norms/bundle/test_manifest.py	migration: pattern
tests/integration/p02_journey/journey.py	table: catalogue; table: pattern
tests/integration/p02_journey/test_extractor_divergence.py	error-code: pattern
tests/support/expected_facts.json	error-code: expected facts (error_catalog.api_codes, error_catalog.stored_vocabulary); migration: expected facts (migration_head); reseal-surface: expected facts (surface.path_count, surface.operations, surface.schema_names); table: expected facts (no table field; review alongside schema)
tests/support/expected_facts.py	migration: pattern; reseal-surface: pattern
web/FRONTEND_LOCK.json	error-code: catalogue; reseal-surface: catalogue
web/openapi/openapi.json	error-code: catalogue; reseal-surface: catalogue
web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx	reseal-surface: live claim
web/src/app/bff/v1/[...path]/route.ts	reseal-surface: live claim
web/src/entities/audit-run/model/terminal-reason.ts	error-code: pattern
web/src/entities/execution/model/presentation.ts	error-code: pattern
web/src/shared/api/catalog-message.ts	error-code: pattern
web/src/shared/api/errors.ts	error-code: pattern
web/src/shared/api/generated/**	error-code: catalogue; reseal-surface: catalogue
web/src/shared/api/generated/operations.gen.ts	reseal-surface: pattern
web/src/shared/api/generated/types.gen.ts	error-code: pattern
web/tests/contract/catalog-message.contract.test.ts	error-code: pattern
web/tests/contract/pc01-error-codes.contract.test.ts	error-code: pattern
web/tests/contract/seam-operations.contract.test.ts	error-code: error-frontend-contract-enum-count; error-code: pattern; reseal-surface: pattern
web/tests/contract/terminal-reason-sentences.contract.test.ts	error-code: pattern
web/tests/guards/frontend-lock.guard.test.ts	error-code: catalogue; reseal-surface: catalogue; reseal-surface: pattern; reseal-surface: surface-frontend-lock-operations; reseal-surface: surface-frontend-lock-paths; reseal-surface: surface-frontend-lock-schemas
web/tests/unit/api/failure-surface.test.ts	error-code: error-frontend-failure-enum-count; error-code: pattern
web/tests/unit/screens/run-terminal-reason.test.ts	error-code: pattern
```
