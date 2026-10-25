# Task AR-V3-BETA-PACK-STATUS-API-01 — serve whether a reviewed pack is installed (contract 1.4.0 to 1.5.0)

task_id: AR-V3-BETA-PACK-STATUS-API-01
status: completed in development candidate

## Outcome
An authenticated user of any role can read, through one new operation `getArV3BetaPackStatus` (`GET /ar-v3-beta/pack`), whether a reviewed AR v3 beta pack is installed on this server and the reviewer attestation that came with its manifest, so the web screen can offer "start six checks" only when it is true. Not installed answers `{"state":"not_installed"}`; installed answers the profile and prompt-bundle IDs, the sealed pack digest, the six scope IDs in order and the five-field attestation. The answer says nothing about whether the attestation is true and exposes no map, set or snapshot identity, scope digest, path or environment value.

## Depends on
- `AR-V3-BETA-PACK-INSTALL-01` — completed manifest loader, `ParsedPackManifest`, `ReviewAttestation`, `load_manifest`.
- `AR-V3-BETA-GROUP-API-SEAL-01` — completed previous seal (contract `1.4.0`, 91 paths / 103 operations / 298 schemas).

## Frozen inputs
- shared domain/API/analysis/events contract: `1.4.0` → additive `1.5.0`; domain catalogue candidate revision 22 → 23
- AR v3 beta stage extension: `1.0.0`, unchanged
- API surface: 91 paths / 103 operations / 298 schemas → 92 / 104 / 300 (`ArV3BetaPackStatus`, `ArV3BetaPackReview`)
- error catalogue: 27 codes, unchanged; migration head: `0032_ar_v3_run_group`, unchanged; `VERSION` `0.8.0`, unchanged
- base commit: `0555a1209eff5db2134543c7b48d8d2423625944` (`integration/ar-close-1026`)

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `AR-V3-BETA-PACK-STATUS-API-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface contract-version`

## Captured premise evidence
- premise: no public operation reports the installed pack, and the composition root drops the attestation after the load

### P-01 — the attestation does not reach the API
- captured_at: 2026-10-26
- command: `git grep -n -E 'getArV3BetaPackStatus|_ar_v3_pack_registry|ReviewAttestation|load_trusted_pack_registry' 0555a1209eff5db2134543c7b48d8d2423625944 -- src/auditmanager/api src/auditmanager/bootstrap contracts/api`
- captured_output:
  ```text
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/adapters.py:849:        self._ar_v3_pack_registry = ar_v3_pack_registry
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/adapters.py:881:            pack=(None if self._ar_v3_pack_registry is None
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/adapters.py:882:                  else self._ar_v3_pack_registry.select_beta()),
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/adapters.py:1030:                ar_v3_pack_registry=self._ar_v3_pack_registry,
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/composition.py:67:    load_trusted_pack_registry,
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/composition.py:76:def _ar_v3_pack_registry(env: dict[str, str]) -> TrustedPackRegistry:
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/composition.py:84:        return load_trusted_pack_registry(env.get(PACK_MANIFEST_ENV))
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/composition.py:180:    ar_v3_pack_registry = _ar_v3_pack_registry(env)
  0555a1209eff5db2134543c7b48d8d2423625944:src/auditmanager/bootstrap/composition.py:317:    ar_v3_pack_registry = _ar_v3_pack_registry(env)
  ```
- interpretation: at the base, only the registry is built from the manifest (`load_trusted_pack_registry` returns a registry, never the `ReviewAttestation`), and no file under `src/auditmanager/api` or `contracts/api` mentions a pack-status operation. Nothing in the API can tell a screen whether a pack is installed.

### P-02 — the sealed 1.4.0 surface at the base
- captured_at: 2026-10-26
- command: `git show 0555a1209eff5db2134543c7b48d8d2423625944:tests/support/expected_facts.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['surface']['path_count'], len(d['surface']['operations']), len(d['surface']['schema_names']), d['contract_version'], d['migration_head'])"`
- captured_output:
  ```text
  91 103 298 1.4.0 0032_ar_v3_run_group
  ```
- interpretation: the independent facts file at the base states the 1.4.0 surface this task moves to 92 / 104 / 300 at `1.5.0`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
The first group is the lane brief's list. The second group is the sweep-driven additions: each is a live pin of the shared contract version or the surface counts that a guard in the first group reads, found by `grep -rIn 1.4.0` and `tools/plan/pin_sweep.py`, added as exact paths. Four of them are under `infra/`, which the lane brief lists as forbidden; they are text-only and sit alone in one commit so the integrator can refuse them (see Integration contract).

- `contracts/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/runs/public.py`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `web/openapi/**`
- `tests/contract/**`
- `tests/integration/composition/test_v3_pack_install.py`
- `tests/integration/api/**`
- `tests/support/**`
- `docs/program/tasks/AR-V3-BETA-PACK-STATUS-API-01.md`
- `docs/program/AR-V3-BETA-PACK-STATUS-API-01.md`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/runs/v3_cite_stage_contract.py`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/app/bff/v1/[...path]/route.ts`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/P02_SEAMS.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `web/tests/guards/gender-agreement.guard.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/analysis-settings/analysis-settings.test.ts`
- `web/tests/unit/api/authorization-state.test.ts`
- `web/tests/unit/api/credentialed-forward.test.ts`
- `web/tests/unit/api/failure-message.test.ts`
- `web/tests/unit/api/failure-surface.test.ts`
- `web/tests/unit/api/server-credential.test.ts`
- `web/tests/unit/blocks/portal-states.test.ts`
- `web/tests/unit/comparison/decision-carryover.test.ts`
- `web/tests/unit/dispatcher/dispatcher.test.ts`
- `web/tests/unit/execution/execution-screens.test.ts`
- `web/tests/unit/export/export-panel-xlsx.test.ts`
- `web/tests/unit/norm-references/norm-references.test.ts`
- `web/tests/unit/norms/catalogue.test.ts`
- `web/tests/unit/norms/document-view.test.ts`
- `web/tests/unit/norms/norms-screen.test.ts`
- `web/tests/unit/norms/presentation.test.ts`
- `web/tests/unit/optimisation/fixtures.ts`
- `web/tests/unit/projects/create-and-list-failure.test.ts`
- `web/tests/unit/projects/upload-failure.test.ts`
- `web/tests/unit/qa_w49/epoch-401-closes-the-session.test.ts`
- `web/tests/unit/qa_w49/sign-in-status-and-throttle.test.ts`
- `web/tests/unit/run/input-budget.test.ts`
- `web/tests/unit/run/polling.test.ts`
- `web/tests/unit/run/run-failure.test.ts`
- `web/tests/unit/screens/cold-load.test.ts`
- `web/tests/unit/screens/home.test.ts`
- `web/tests/unit/screens/stage-comparison.test.ts`
- `web/tests/unit/screens/widgets.test.ts`
- `web/tests/unit/section-specification/section-specification.test.ts`
- `web/tests/unit/sections/fixtures.ts`
- `web/tests/unit/session/account-fixture.ts`
- `web/tests/unit/specification-prices/specification-prices.test.ts`
- `web/tests/unit/styles/screens.ts`
- `web/tests/unit/upload/price-list-upload-failure.test.ts`
- `web/tests/unit/widgets/registration-queue.test.ts`
- `web/tests/unit/widgets/user-management.test.ts`
- `web/tests/unit/workers/executor-connections.test.ts`
- `web/tests/unit/workers/workers.test.ts`

Reasons for the second group: `analysis/engine/result.py` holds `CONTRACT_VERSION` that `test_contract_seal` equates with the sealed version; `runs/v3_cite_stage_contract.py` states the family version in its docstring; `credentialed-forward.ts` and the two `infra/deploy/proxy/*.conf` 401/429 bodies carry the version literal that `test_contract_seal` reads; `authorization.ts`, `route.ts`, `infra/deploy/README.md`, `serve.py` and the `nginx.conf` comments state operation or path counts the prose guard `test_surface_counts_in_prose` scans; `ALPHA_ROADMAP.md` and `P02_SEAMS.md` state the current surface and are live-document scanned; the 40 `web/tests` files each contain one frozen error-envelope fixture with `contract_version: '1.4.0'` (or an assertion on it) that must equal the served version.

### Live pins moved (sorted by the sweep)
- Shared version `1.4.0` → `1.5.0`: the 30 non-README, non-OpenAPI files under `contracts/analysis`, `contracts/domain`, `contracts/events` (schemas, catalogues, examples, `ar_v3_beta/v1/stage.json`); `contracts/api/v1/openapi.json` (`info.version`, `ErrorEnvelope.contract_version` const) and its `web/openapi/openapi.json` mirror; `analysis/engine/result.py`, `api/routers/__init__.py` (`CONTRACT_VERSION`), `api/schemas/models.py` (`ErrorEnvelope.contract_version`), `runs/v3_cite_stage_contract.py` (docstring); `credentialed-forward.ts`; the two proxy configs; generated client (`CONTRACT_VERSION`, headers); `tests/support/expected_facts.json`; `test_contract_seal.py` (`SEALED`, `PREVIOUS`, candidate revision 23); the 40 web test files.
- Surface 91/103/298 → 92/104/300 and spelled forms: `expected_facts.json` (path count, the operation triple, two schema names); `app.py` ("ninety-two paths", "104", "299 models", "300 schema names"), `health.py`, `routers/__init__.py`, `routers/declarations.py` ("twenty-seven of the 104 operations declare no 422", measured from the document: 27 of 104, where the old text said twenty-five of 103 and the document had 26), `routers/errors.py`, `api/README.md`; `infra/deploy/README.md`, `serve.py`, `nginx.conf`; `authorization.ts`, `route.ts`; `ALPHA_ROADMAP.md`, `P02_SEAMS.md` (count and one register row); the OpenAPI `info.description`; `test_surface_counts_in_prose.py` (two mutation needles); `test_openapi_document.py` (`REQUIRED_OPERATIONS`, `INPUT_LESS_OPERATIONS`); `tests/integration/api` (`conftest.py` fake port, `test_authorization.py`, `test_role_register.py`).
- Frozen-client lock: `web/FRONTEND_LOCK.json` (openapi sha256 and snapshot, content commit `b02f680e`, counts, four generated-file digests, `info_version`).

### Not moved (historical or unrelated, left untouched)
- Earlier task files and reports under `docs/program` that quote `1.4.0` or 91/103/298 (`AR-V3-BETA-GROUP-API-SEAL-01`, `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`, `AR-V3-BETA-SCREEN-GATE-REPAIR-01`, `DEV-CONTRACT-REDS-01` and the task files that cite the contract of their day): the record of what was true then.
- `contracts/api/v1/README.md` section `1.4.0` (now marked historical) and the earlier sections; the OpenAPI `info.description` keeps the previous seal's paragraph without a surface total.
- `docs/program/WAVE_EXECUTION_GUIDE.md` `api: 1.4.0` / `analysis: 1.4.0`: a template example, not a pin; no test reads it.
- `1.4.0` that is not the contract: `anthropic==1.4.0` (`pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `docs/program/LIVE_RUN_INSTRUCTIONS.md`, `tests/integration/analysis_text/test_live_adapter_shape.py`), `natural-compare` and `expect-type` in `web/package-lock.json`.
- Sweep inventory entries (`pin_sweep.py reseal-surface contract-version --check`) with no literal to move, because each reads the count or version from `tests/support/expected_facts.json` or the served constants, or matches only on a familiar word: `VERSION`, `docs/program/CONTRACT_PIN_REGISTRY.md`, `src/auditmanager/ingest/pdf_reader.py`, `src/auditmanager/norms/bundle/manifest.py`, `tests/characterization/w13_baseline/test_response_baseline.py`, `tests/e2e/pc01/journey/manifest.json`, `tests/e2e/pc01/test_acceptance.py`, `tests/integration/analysis/test_status_policy_and_result_shape.py`, `tests/integration/auth/test_the_exchange_over_real_users.py`, `tests/integration/composition/test_api_token_channel.py`, `tests/integration/composition/test_composition_root.py`, `tests/integration/composition/test_router_answers.py`, `tests/integration/norms/bundle/test_contents.py`, `tests/integration/qa_w52/test_release_access_matrix.py`, `tests/unit/analysis/text_profiles/test_text_profile_packages.py`, `tests/unit/executor_runner/_support.py`, `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, `web/tests/contract/seam-operations.contract.test.ts`, `web/tests/guards/frontend-lock.guard.test.ts`.
- Not mine, numbers reported to the orchestrator: `docs/program/CURRENT_STATE.md` (line 8: the surface triple and "shared contract is `1.4.0`") and `docs/program/DEBT_REGISTER.md`.

## Forbidden hotspots
- `db/migrations/**`, `Makefile`, root dependency and lock files other than `web/FRONTEND_LOCK.json`, `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, `docs/program/RELEASES.md`, UI components under `web/src/**` other than the generated client, global styles.
- `infra/**` is forbidden except the four text-only paths named above.
- `origin/main`, tags and deployment host.

## Non-goals
- A web screen or any UI that consumes the operation (lane L8B).
- Deciding whether the attestation is true, approving a pack, installing one, or starting a group.
- Any new error code, migration, database read or provider call.
- Changing the worker composition root's behaviour: it still receives only the registry.

## Deliverables
- `GET /ar-v3-beta/pack` / `getArV3BetaPackStatus`, `ArV3BetaPackStatus` and `ArV3BetaPackReview`, role register entry (any role, as `getArV3BetaGroup`), port method, thin adapter read.
- Composition root keeps the `ParsedPackManifest` of the one load that builds the registry and hands it to the API adapter; the worker root is unchanged.
- Sealed contract `1.5.0`: OpenAPI content commit `b02f680e`, regenerated client and mirror, `web/FRONTEND_LOCK.json`, shared version stamp in every contract family, domain catalogue revision 23, every pin above.
- Tests: route and adapter unit tests, composition tests for both roots, 200-schema contract test.
- This task file and the result note.

## Verification
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/api/test_ar_v3_pack_status_route.py tests/integration/composition/test_v3_pack_install.py`
- Gate-equivalent contract run (the runtime venv lacks jsonschema; the bootstrap site-packages are appended last): `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py`
- `node web/scripts/generate-api-client.mjs --check`
- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface contract-version`
- Each new guard shown red under a quoted mutation (see the result note). DB- and S3-backed tests (`tests/integration/api` served-application cases, `test_role_register.py`, `test_authorization.py`) are collected but cannot run on this host.

## Integration contract
`GET /ar-v3-beta/pack` requires a bearer credential and any role. 200 `ArV3BetaPackStatus`: `state` is `installed` or `not_installed`; every other property is present only when installed (absent, never null). 401, 403, 500, 503 use the shared envelope responses; there is no 404 and no 422 (no input). The L8B screen consumes the generated `getArV3BetaPackStatus` and `ArV3BetaPackStatus`. Merge order: this lane before L8B. `docs/program/CURRENT_STATE.md` must move to 92 paths / 104 operations / 300 schemas and shared contract `1.5.0`; until it does, `test_the_scanned_docs_state_the_contract_surface_this_tree_has` is red. The infra commit (`5f4d3c31`) may be refused only together with moving the same four paths by the integrator, because `test_contract_seal` and the prose guard read them.

## Failure/idempotency/security cases
- Variable unset or blank: `not_installed`. Variable naming a refused manifest: the process still refuses to start with `ConfigurationError` (unchanged); the status is never an empty fallback for a pack that was meant to install.
- Pure read of in-memory state: no database, no provider call, repeatable.
- Exposed set is exactly six keys plus five attestation keys; the configured path, map, set, snapshot, content-key, builder, scope-digest values never appear.

## Rollback / feature flag
Forward-revert the lane's commits; the contract version returns to `1.4.0`. No data, migration or flag.

## Handoff
- changed files: see the result note
- commands/results: see the result note
- known limits: DB- and S3-backed integration cases not run on this host; no UI
- integration notes: update `CURRENT_STATE.md`; merge before L8B
