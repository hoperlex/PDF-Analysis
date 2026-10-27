# CMP-SEAL-C0 — the seal of wave C0: contract 1.9.0, migration 0038, dependencies, module flag

Written 2026-10-27 by the Sonnet lane `CMP-SEAL-C0` (branch `agent/cmp-seal-c0`, base `03f73103` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-SEAL-C0.md`](tasks/CMP-SEAL-C0.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 3, 3.2 and 4.0.

No product logic is written: every operation is a stub answering `503 dependency_unavailable`, every table is empty, and no code reads or writes one.

## 1. Base facts, printed before any edit

`git show 03f73103:contracts/api/v1/openapi.json` read with `json`: contract `1.8.0`, 98 paths, 111 operations, 321 schemas, 27 error codes; `VERSION` `0.9.0`; migration head `0037_analysis_presets` (`revision: str = "0037_analysis_presets"`). They equal the task's premise, so the lane went on. After the seal: contract `1.9.0`, **115 paths / 130 operations / 351 schemas** (+17 / +19 / +30), 27 error codes (unchanged), head `0038_comparison_foundation` (26 characters), `VERSION` untouched.

## 2. The probe, and the grant list it gave

A disposable branch (`probe/cmp-seal-c0`, one commit, deleted afterwards) put one stub operation (`GET /probe/uploads`), one schema, one table (`comparison_upload`, migration `0038_probe`) and `info.version` `1.9.0` in the OpenAPI document and its mirror, and nothing else. It was measured three ways; every red below is a file that pins a fact this seal moves.

* `tests/contract` (minus the three `D-220` files): 20 failed, 1284 passed on the probe against 1 failed on the base (the base red is `test_wave_governance.py`: the task file's own premise block lacked a command, a date and an output; fixed here). New reds in seven files: `api_v1/test_contract_seal.py`, `api_v1/test_doc_prose_facts.py`, `api_v1/test_openapi_conformance.py`, `api_v1/test_openapi_conformance_live.py`, `api_v1/test_surface_counts_in_prose.py`, `domain_p02/test_openapi_document.py`, `domain_p02/test_seam_register.py`.
* web: `tests/contract/seam-operations.contract.test.ts`, `tests/guards/frontend-lock.guard.test.ts`, `tests/guards/query-key-shape.guard.test.ts` (it runs `tsc`), and `tsc` itself on 49 test files that type `ErrorEnvelope.contract_version`; `api:verify` drifted in four generated files.
* `tests/integration/db tests/integration/recovery tests/integration/composition tests/integration/p02_journey tests/integration/foundation` (42 minutes, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`): 249 failed, 86 errors, 2984 passed, in 35 files — `db/`: `test_accounts_migration`, `test_application_role_grants` (86), `test_application_role_plugin`, `test_ar_v3_cite_stage_id_migration`, `test_ar_v3_run_group`, `test_cite_partition_v3_migration` (5), `test_effect_state_guards_0033`, `test_execution_workers_migration`, `test_executor_connections_migration`, `test_executor_pull_migration`, `test_findings_v2_migration`, `test_fixture_template`, `test_migration_lifecycle`, `test_norm_citations_migration`, `test_norm_custody_migration`, `test_norms_search_migration`, `test_pass_scope_migration`, `test_portal_bundles_migration`, `test_release_notes_migration`, `test_schema_invariant_inventory`, `test_schema_shape`; `foundation/`: `test_cross_provider_publication`, `test_idempotency`; `recovery/`: `test_analysis_preset_classification`, `test_comparison_records_purge_and_erase` (3), `test_grant_classification` (2), `test_product_purge` (47), `test_product_purge_executor_events` (2), `test_product_purge_run_group` (3), `test_product_purge_script` (7), `test_project_erase` (117), `test_project_erase_shapes` (3), `test_schema_coverage` (26), `test_synthetic_drill_compare`, `test_synthetic_drill_seed`. (`composition/` and `p02_journey/` were green on the probe: the probe wired no code; they went red on the real change and are in the lists below.)

The grant list is therefore: the families of `pin_sweep.py contract-version`, `reseal-surface`, `migration` and `table`, plus the files above. Files outside the task's `allowed_paths` that were edited, each with its reason:

| file | reason |
| --- | --- |
| `contracts/analysis/**` (18), `contracts/events/v1/**` (3) | the shared `contract_version` literal; `test_contract_seal.py` requires one value in all four families and the registry's contract-version event names them (as `CONTRACT-1-8-0-01` did) |
| `docs/program/P02_SEAMS.md` | probe red: `test_seam_register.py` and `test_surface_counts_in_prose.py` read its operation table, keyed-write sentence and the count |
| `docs/manual-tests/PC-01_prototype.md` | probe red: `test_doc_prose_facts.py::test_the_scanned_docs_state_the_migration_head_this_tree_has` |

Everything else is in the task's `allowed_paths`.

## 3. Contract 1.9.0

Nineteen operations, all sealed stubs (`503 dependency_unavailable`, `details.dependency` one of `comparison_uploads`, `comparison_version_orders`, `version_pages`), tag `comparison` (new). Reads are any one role; every write is an expert's act (`_EXPERT`: an administrator without `expert` is refused, ADR decision 16) and carries a required `Idempotency-Key`.

| operationId | method, path | role | keyed | implements |
| --- | --- | --- | --- | --- |
| `createComparisonUpload` | `POST /projects/{project_uid}/comparison-uploads` | expert | yes | INGEST-01 |
| `listComparisonUploads` | `GET /projects/{project_uid}/comparison-uploads` | any role | no | INGEST-02 |
| `getComparisonUpload` | `GET /comparison-uploads/{comparison_upload_id}` | any role | no | INGEST-01 |
| `getComparisonUploadProposal` | `GET /comparison-uploads/{comparison_upload_id}/proposal` | any role | no | INGEST-01 |
| `uploadComparisonUploadPart` | `PUT /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/parts?part_number=n` (raw `application/octet-stream`, `format: binary`, at most 16 MiB) | expert | yes | INGEST-01 over STORAGE-PARTS-01 |
| `completeComparisonUploadFile` | `POST /comparison-uploads/{comparison_upload_id}/files/{comparison_upload_file_id}/completion` | expert | yes | INGEST-01 |
| `confirmComparisonUploadSet` | `POST /comparison-uploads/{comparison_upload_id}/sets/{comparison_upload_set_id}/confirmation` | expert | yes | INGEST-01 |
| `excludeComparisonUploadSet` | `POST .../sets/{comparison_upload_set_id}/exclusion` | expert | yes | INGEST-02 |
| `retryComparisonUploadSet` | `POST .../sets/{comparison_upload_set_id}/retry` | expert | yes | INGEST-02 |
| `pauseComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/pause` | expert | yes | INGEST-02 |
| `resumeComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/resume` | expert | yes | INGEST-02 |
| `cancelComparisonUpload` | `POST /comparison-uploads/{comparison_upload_id}/cancellation` | expert | yes | INGEST-02 |
| `listComparisonVersionOrders` | `GET /projects/{project_uid}/documents/{document_uid}/comparison-version-orders` | any role | no | INGEST-01 |
| `appendComparisonVersionOrder` | `POST` the same path | expert | yes | INGEST-01 |
| `listVersionPageProfiles` | `GET /versions/{version_uid}/page-profiles` | any role | no | PROFILE-01 |
| `getVersionPageProfile` | `GET /page-profiles/{comparison_page_profile_id}` | any role | no | PROFILE-01 |
| `streamVersionPagePreview` | `GET /page-profiles/{comparison_page_profile_id}/preview` (`image/png`) | any role | no | PROFILE-01 |
| `streamVersionPageThumbnail` | `GET /page-profiles/{comparison_page_profile_id}/thumbnail` (`image/png`) | any role | no | PROFILE-01 |
| `streamVersionPageTile` | `GET /page-profiles/{comparison_page_profile_id}/tile?level&column&row` (`image/png`) | any role | no | PROFILE-01 |

Ten keyed writes, nine reads. Why the addresses are shaped this way: the contract forbids addressing anything by an ordinal (`test_no_endpoint_addresses_a_resource_by_a_non_identity`), so a page is addressed by the identity of its profile (`cpr_`) and `listVersionPageProfiles` hands out those identities with their `page_number`; the part number and the tile coordinates are query parameters (bounds `1..10000` and `0..12`, `0..4095`).

New schemas (30): `AppendComparisonVersionOrderRequest`, `ComparisonModules`, `ComparisonPageProfileId`, `ComparisonProposalFile`, `ComparisonProposalSet`, `ComparisonProposalWarning`, `ComparisonUpload`, `ComparisonUploadFile`, `ComparisonUploadFileDeclaration`, `ComparisonUploadFileId`, `ComparisonUploadFileState`, `ComparisonUploadId`, `ComparisonUploadPage`, `ComparisonUploadPartReceipt`, `ComparisonUploadProposal`, `ComparisonUploadSetId`, `ComparisonUploadSetState`, `ComparisonUploadState`, `ComparisonVersionOrder`, `ComparisonVersionOrderId`, `ComparisonVersionOrderList`, `ComparisonVersionOrderSource`, `ConfirmComparisonUploadSetRequest`, `ConfirmedComparisonFile`, `CreateComparisonUploadRequest`, `PageProfileStatus`, `PageStamp`, `VersionPageProfile`, `VersionPageProfilePage`, `VersionUploadKind`. Changed (additive): `DocumentVersion.upload_kind` (`portal_bundle` | `comparison_pdf`, optional, always sent), `ProductVersion.comparison_modules` (optional, always sent), `RunnerImage` (`portal_block_id` no longer required, optional opaque `crop_id`), `ClaimedExecutorTask.images` (`maxItems` 1 to 8), `ClaimExecutorTaskRequest.max_images` (optional, 1..8; absent means 1).

**The module flag (decision 23): carrier `ProductVersion.comparison_modules`, not the session subject.** The module set is a fact about the deployment, not about an account: `Account` is returned by eight operations (the user administration among them) and a deployment-wide field on every one would be a lie about each account, while `ProductVersion` is the one object that already says what the running product is, is read by any complete account, and is already loaded by the shell frame. The value is `none` (default), `versions` or `versions,stages`, parsed in `src/auditmanager/comparison/modules.py` from `AUDITMANAGER_COMPARISON_MODULES` (unset or empty means `none`; any other value is a `ConfigurationError` while wiring, never a quiet `none`). The composition root reads the environment (`bootstrap/composition.py`) because `bootstrap/settings.py` is outside the grant; moving the read there is a one-line change for its owner. No compose file is touched (the default needs none).

No new error code: registered reasons were added to the notes of `validation_failed` (limits of decision 9 and the part and set refusals), `conflict` (`comparison_upload_active`, `comparison_upload_state`, `comparison_set_state`, `comparison_version_order_stale`), `storage_integrity_error` (declared digest or size at completion), `analysis_input_invalid` (`comparison_only_version`) and `dependency_unavailable` (the three stub class names and `comparison_modules`), and the Russian sentence of `comparison_only_version` is in the catalogue (`web/src/shared/api/catalog-message.ts`).

Identity prefixes (the catalogue goes 48 to 56; each fits `^[a-z][a-z0-9]{1,7}$`, none collides): `cbt` upload batch, `cus` upload set (the original's batch item), `cuf` upload file, `cvo` version-order revision, `cpr` page profile, `cq` queue item, `cqa` queue attempt, `cmc` spend-journal row. The two the ADR left to this seal are `cqa` and `cmc`; `cus` and `cuf` are this seal's too (decision 10 names "the item id"). `python3 -I -c "..."` of decision 2 for the eighteen prefixes still prints `[]` for the other ten.

## 4. Migration `0038_comparison_foundation`

Up and down were run on an isolated database (`cmp_seal_c0_mig`, created and dropped on the lane's own PostgreSQL): `upgrade head` (0038), `downgrade -1` (0037), `upgrade head` again, and by `tests/integration/db/test_comparison_foundation_migration.py` (29 tests; the downgrade is refused while any row exists, and only then).

**Nine tables, not eight.** The task lists eight; the ninth is `comparison_upload_set`. A batch groups its files into proposed document sets that the user confirms, excludes or retries one by one (the original's batch *item*), and decision 10 names "the item id" as a resume and grouping identity: that needs an opaque identity and a state of its own, which a column of the files cannot hold. It is one more table in the per-table family and nothing else.

| table (identity) | what it holds | guards |
| --- | --- | --- |
| `comparison_upload` (`cbt_`) | a batch: project, state (`uploading`, `proposed`, `processing`, `paused`, `completed`, `cancelled`), declared files, bytes and pages, the 16 MiB part size, pause flag, actor, command receipt | state edges, frozen columns |
| `comparison_upload_set` (`cus_`) | a proposed set: state (`uploading`, `reading`, `needs_confirmation`, `ready`, `admitting`, `done`, `failed`, `excluded`), designation (metadata, never identity), existing and admitted document, stage and section, proposal `jsonb`, confirmer | state edges, frozen columns, a failed set holds its reason, a confirmed one its confirmer |
| `comparison_upload_file` (`cuf_`) | a declared file: name (hint), declared size and SHA-256, page count, state, the multipart token, the published blob | state edges, token and blob write-once, `verified` needs its blob |
| `comparison_upload_part` (file, part number) | one chunk, declared before its bytes are staged | state edges, a part is refused for a file with no token (trigger), staged facts required |
| `comparison_version_order` (`cvo_`) | an order revision of a document set's versions (`jsonb` array), source, actor, receipt | append-only (`am_immutable_row`), chain trigger: no gap, only the document's versions, each once |
| `comparison_page_profile` (`cpr_`) | the raw profile of one page of one version, a content-keyed row: ULID id plus `UNIQUE (version, content_key)` and `UNIQUE (version, page, algorithm)`; summary `jsonb`; profile, preview and thumbnail blobs | page must exist in the version (trigger), frozen apart from write-once blob references |
| `comparison_work` (`cq_`) | a queue item: module, kind, state (`queued`, `leased`, `running`, `retry_wait`, `paused`, `spend_unknown`, `succeeded`, `failed`, `cancelled`), payload, dedupe key (unique while live), priority, `not_before`, attempts, `current_work_attempt_id`, cancel request, reason | state edges, frozen identity columns, terminal time write-once |
| `comparison_work_attempt` (`cqa_`) | one leased execution: number, state, secret-class `execution_token`, worker, `lease_expires_at`, `heartbeat_at` | state edges (the `attempt` topology), a live attempt needs its lease |
| `comparison_model_call` (`cmc_`) | the spend journal: work kind, state (`prepared`, `sent`, `completed`, `failed`, `unknown`), provider mode, model, connection revision, request digest, estimate, executor task, response digest, tokens, cost basis and micros, error code | inserted `prepared` only (trigger), edges `prepared` to `sent`/`failed`/`unknown`, `sent` to `completed`/`failed`/`unknown`, terminal rows never move, shape per state, prepared facts frozen |

Other changes: `document_version.upload_kind` (`NOT NULL DEFAULT 'portal_bundle'`, CHECK, and a `comparison_pdf` version holds no portal bundle counts); `executor_task` gains the origin `comparison_call` and the nullable `comparison_attempt_id` (FK to `comparison_work_attempt`, shape CHECK rebuilt, frozen guard recreated with the column). `comparison_work`, `comparison_work_attempt` and `comparison_model_call` have no foreign key to `job`, `attempt` or `audit_run` (ADR verification 2, shown failing on a database in which one is added); every table reaches `project` by foreign keys (shown failing on an orphan table). Counts: columns +126, constraints +156, indexes +38, triggers +25, functions +5 (measured, in `test_schema_invariant_inventory.py`).

**Per-table family** (rule 3 of plan section 4.0): `scripts/recovery/schema_coverage.py` (head, nine tables, 25 triggers, constraint and index counts), `grant_classification.py` and `infra/deploy/apply-grants.sh` (eight tables read-write, `comparison_version_order` append-only; the generated block rewritten by the module's own `--write-script`), `product_purge.py` (nine PRODUCT tables and ten product command types), `project_erase.py` (`NON_TERMINAL_STATES` for `comparison_work`: queued, leased, running, retry wait, paused, `spend_unknown`; for `comparison_work_attempt`: created, leased, running, with its derivation test and an erase-refusal test), `blob_reference_audit.py` (the four blob columns: `comparison_upload_file.blob_id`, three of `comparison_page_profile`), the table-count and inventory pins of the db and recovery suites, `P02_TABLES` of `tests/integration/p02_journey/journey.py`. **`src/auditmanager/access/references.py` is untouched on purpose**: it registers foreign keys to `app_user`, and the actor columns here are, like `comparison_sheet_link.actor_user_uid`, deliberately not foreign keys. `executors/model.py` needed no edit (it holds no origin vocabulary).

## 5. Dependencies (decision 24)

`pyproject.toml`: `numpy==2.5.4`, `opencv-python-headless==4.14.0.94`, `reportlab==5.1.0`; `uv.lock` regenerated with `uv lock` (network; three packages added, nothing else moved); `docs/program/P02_LOCK.json` and the `DIRECT` tuple of `tests/contract/test_w55b_direct_pins.py` hold the three equal. The 4.x line of OpenCV is pinned (5.0.0.93 also resolved) because the original's algorithms were written against it and the API is the one the lanes will port to. A mutation of each pin is red (section 9).

| package | licence (and what the wheel bundles) | wheel (linux x86-64, cp312) | installed |
| --- | --- | --- | --- |
| numpy 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; the wheel bundles OpenBLAS and LAPACK (BSD-3-Clause), libgfortran (**GPL-3.0-or-later WITH GCC-exception-3.1**) and libquadmath (**LGPL-2.1-or-later**) | 16.7 MB (`manylinux_2_27`/`2_28`) | 33 MB + 27 MB libs |
| opencv-python-headless 4.14.0.94 | Apache-2.0 for `cv2`; `LICENSE-3RD-PARTY.txt` adds FFmpeg libraries (**LGPL-2.1**, dynamically linked), OpenSSL 1.1.1k, libpng (PNG Reference Library License 2), libjpeg-turbo (IJG, BSD, Zlib), libwebp, OpenJPEG, libtiff, zlib, libvpx, dav1d, libavif, protobuf and an **MPL-2.0** component | 62.0 MB (`manylinux_2_28`; 57.5 MB for `manylinux2014`) | 78 MB + 84 MB libs |
| reportlab 5.1.0 | BSD-3-Clause (pure Python; pulls Pillow, already pinned, and `charset-normalizer`, already locked) | 2.0 MB (`py3-none-any`) | 5 MB |

Image size: about **+230 MB** of site-packages in the API and worker images. Two things for the owner and the `PROD` owners to read, not decide here: the bundled LGPL and MPL libraries are shared objects in a wheel, not linked Python code (OD-01 blocked PyMuPDF, AGPL, as a Python library; `Q-CMP-9` named these three packages), and the OpenCV wheel carries OpenSSL 1.1.1k, which is end of life — the product opens no stream with `cv2`, so no network path reaches it, but it will show in an image scan.

## 6. Pins moved

* **contract-version family** (1.8.0 to 1.9.0, the `CONTRACT-1-8-0-01` classes): `contracts/api/v1/openapi.json` and `web/openapi/openapi.json` (`info.version`, the `ErrorEnvelope` const, a new paragraph and the surface sentence of `info.description`), `contracts/analysis/**` (18 files), `contracts/events/v1/**` (3), `contracts/domain/v1/**` (catalogs `supersedes` 1.8.0 and `candidate_revision` 27 with a revision note, their schemas' consts, the envelope schema and two examples, README), the three served constants (`analysis/engine/result.py`, `api/routers/__init__.py`, `api/schemas/models.py`), the four edge error bodies (`infra/deploy/proxy/nginx.conf`, `tls-server.conf`), `web/src/shared/api/credentialed-forward.ts`, `tests/support/expected_facts.json`, `tests/contract/api_v1/test_contract_seal.py` (`SEALED`, `PREVIOUS`, the retired-version tuple, revision 27), 50 web test files that type or quote the served version (a mechanical `1.8.0` to `1.9.0`), `contracts/api/v1/README.md`, `contracts/domain/v1/README.md`.
* **reseal surface family** (98/111/321 to 115/130/351): `docs/program/CURRENT_STATE.md`, `ALPHA_ROADMAP.md`, `P02_SEAMS.md` (operation table, keyed-write sentence, "130 operations, sealed."), `infra/deploy/README.md`, `nginx.conf`, `infra/deploy/serve.py`, `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`, `src/auditmanager/api/{app.py,health.py,README.md}`, `routers/{__init__,declarations,errors}.py` (the 422 count "Ninety-two of the 130" re-measured, not substituted), and `test_surface_counts_in_prose.py` (its locator read only spelled numbers up to ninety-nine; 115 needed the scan's own number pattern).
* **migration head**: `scripts/recovery/schema_coverage.py` (`HEAD`), `tests/support/expected_facts.json`, `docs/manual-tests/PC-01_prototype.md`, `CURRENT_STATE.md`.
* **per-table family**: section 4.
* **identifiers**: `contracts/domain/v1/identifiers.json` (+ a `distinct_identities` entry), `identifiers.schema.json`, `src/auditmanager/shared/identity/{ids,__init__}.py`, `test_w55b_portal_bundle_seal.py` (48 to 56), `test_schema_shape.py`.
* **stub enumerators**: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, nine paths, and `SEALED_STUB_QUERY` for the tile) and `test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, nine operations, `EXPECTED_ADDRESSED` 35 to 44; `SEALED_STUB_COLLECTIONS` stays empty because every comparison GET names a parent). All nine are addressed because the two listings hang off a project.
* other registers: `tests/contract/domain_p02/test_openapi_document.py` (required operations, keyed writes), `test_openapi_conformance.py` (the `NotFound` reference count 79 to 98), `tests/integration/api/{test_role_register,test_authorization,test_operation_surface,test_query_surface,test_served_document_and_health_plane}.py`, `web/tests/contract/seam-operations.contract.test.ts`.
* generated client and `web/FRONTEND_LOCK.json`: `npm --prefix web run api:generate` then `api:verify` (`OK - 130 operations`, contract sha256 `5daf6416...a1765`); the lock names the content commit `21058a2f` (the commit that holds the final contract bytes) and the three counts. Do not squash: the lock names that SHA.

## 7. Decisions of this seal that the ADR did not make

1. The ninth table (section 4). 2. The carrier of the flag (section 3). 3. `cus_`, `cuf_`, `cqa_`, `cmc_` (section 3). 4. Pages, parts and tiles are addressed by identity or query, never by an ordinal in a path. 5. The set state that needs the user is `needs_confirmation`: the rendered-language guard learns Latin words from contract values and refuses a bare `review` (the owner ruled it translated), so the contract value is a compound. 6. `SEALED_NOT_YET_WRITTEN` in `grant_classification.py`: the scan of the code's SQL says every table the code never writes is read-only; the nine tables are named as sealed-and-unwritten, and a guard goes red when a lane writes one without removing it (shown failing). 7. The command types of the ten keyed writes are registered as product receipts in `product_purge.PRODUCT_COMMAND_TYPES` under the snake case of the operationId; a lane that names one differently registers it. 8. `ProductVersion` is dumped with `exclude_unset` so a stand-in that does not set the optional field omits it instead of sending `null`.

## 8. Commands and results

Provisioning: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `npm --prefix web ci`, `.env` with the six lane values on both sides (`FOUNDATION_INSTANCE=auditmanager-cmp-seal-c0`, ports `57710`/`61710`/`61711`, `auditmanager_cmp_seal_c0`, `auditmanager-cmp-seal-c0`), the corpus symlink; `df -h /` before bootstrap (4.3 G), `npm ci` (4.0 G), the first test run (3.3 G); never below 2.2 G. `make up` and `make down` only for the lane's own containers.

RESULTS_PLACEHOLDER

## 9. Mutation proofs (each: the file changed, the guard run red, the file restored from git, the guard run green)

| # | mutation | guard | red | restored |
| --- | --- | --- | --- | --- |
| M1 | `pyproject.toml` `numpy==2.5.4` to `2.5.3` | `tests/contract/test_w55b_direct_pins.py` | 1 failed, 5 passed | 6 passed |
| M2 | `P02_LOCK.json` numpy `2.5.4` to `2.5.3` | the same | 1 failed, 5 passed | 6 passed |
| M3 | `contracts/events/v1/examples/event-envelope.example.json` back to `1.8.0` | `test_contract_seal.py` | 1 failed, 20 passed | 21 passed |
| M4 | `identifiers.json`: `cuf` set to `cus` (a duplicate prefix) | `test_identifier_catalog.py` | 3 failed | 32 passed |
| M5 | `getComparisonUpload` dropped from `SEALED_STUB_ADDRESSED` | `test_an_absent_parent_is_not_an_empty_page.py` | 1 failed, 11 passed | 12 passed |
| M6 | `ComparisonUploadFileDeclaration.size_bytes` `ge=1` to `ge=2` in the model only | `test_openapi_conformance_live.py` | 1 failed | 1 passed |
| M7 | `comparison_work` dropped from `schema_coverage.TABLES` | `test_schema_coverage.py` | 20 failed | 30 passed |
| M8 | `appendComparisonVersionOrder` opened to any role in `security.py` | `test_openapi_document.py` and `test_role_register.py::test_the_registers_are_the_ruled_ones` | 1 failed, 52 passed | 53 passed |
| M9a | the prepared-first trigger made a no-op | `test_comparison_foundation_migration.py -k inserted_prepared` | 4 failed | 4 passed |
| M9b | the token-first check made a no-op | `-k multipart_token` | 1 failed | 1 passed |
| M9c | an edge `cancelled` to `queued` added | `-k declared_edges` | 1 failed | 1 passed |
| M9d | the order chain check made a no-op | `-k order_revisions` | 1 failed | 1 passed |
| M10 | `parse_modules` falls back to `none` on an unknown value | `tests/unit/comparison/test_comparison_modules.py` | 7 failed, 15 passed | 22 passed |
| M11 | `api/routers/__init__.py` constant back to `1.8.0` | `test_contract_seal.py` | 1 failed, 20 passed | 21 passed |
| M12 | `FRONTEND_LOCK.json` `component_schemas` 351 to 350 | `web/tests/guards/frontend-lock.guard.test.ts` | 1 failed, 7 passed | 8 passed |
| M13 | `comparison_` tables out of `NON_TERMINAL_STATES` | `test_comparison_foundation_erase.py` (in the file) | a leased item no longer stops the erase | n/a (monkeypatch) |
| M14 | `comparison_work` dropped from `SEALED_NOT_YET_WRITTEN` | `test_grant_classification.py` | 2 failed, 33 passed | 35 passed |
| M15 | `paused` dropped from the `comparison_work` non-terminal list | `test_project_erase.py::test_the_non_terminal_states_are_the_complement_...` | 1 failed | 1 passed |
| M16 | a foreign key from the journal to `job`; an orphan table | the two mutation tests in the migration file | red in the file | n/a (own database) |
| M17 | a write is made an administrator's; a malformed part, tile or body | `test_comparison_stub_operations.py` (the role map is a literal written there) | in the file | n/a |

## 10. Limits, risks, what the seal does not do

* Every stub answers `503` for any request that passes authentication, the role and the request's own shape; the module flag does not yet gate anything (a stub answers `dependency_unavailable` whatever the flag says). The worker loop and the pause of queued work when a module is turned off are `CMP-WORK-01`'s (ADR verification 15); this seal delivers the flag's carrier and its parser.
* `ClaimExecutorTaskRequest.max_images` is accepted and ignored: nothing yet builds a task with more than one image (`executors/pull.py:194` still caps it), so no deployed runner can be handed one. The server-side gating is `CMP-EXEC-IMAGES-01`'s.
* `documents/models.py` carries `upload_kind` with the default `portal_bundle`; the repository read of the column is `CMP-INGEST-01`'s (it owns `documents/repository.py`). Until it lands every served version says `portal_bundle`, which is true of every row that can exist.
* The limits of ADR decision 9 are not in the schema (no `maxItems` or byte maxima on the declaration): they are refused as registered `constraint` reasons by the lane, because the owner may revise them (decision 27); only structural bounds are in the contract and the migration.
* `uploadComparisonUploadPart` reads the body (at most 16 MiB) before the port is called; `CMP-INGEST-01` owns the streaming and replaces that router file's body handling.
* No eviction, no blob delete, no worker: nothing runs. `comparison-disk` readiness (decision 9) is not built.
* The web test fixtures were rewritten mechanically (50 files, a literal each); the assertions on what a screen shows are untouched.
* `bootstrap/settings.py` still has no entry for the new environment variable (outside the grant, see section 3).
* The complete `make gate` was not run (`R-135`: moved to debt; the task's required tests are the list below). The seal touches `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `web/FRONTEND_LOCK.json` and the composition root, so `AGENTS.md` §8 case 3 asks one full gate on this lane, which `R-135` defers to the gate before the beta.

## 11. Per C0 lane: what it implements, on which tables

| lane | operations | tables and other objects | removes from the stub registers |
| --- | --- | --- | --- |
| `CMP-WORK-01` | none | `comparison_work`, `comparison_work_attempt`; the handler registry; the worker hook; reads `comparison/modules.py`; pauses queued work of a module that is off | `comparison_work`, `comparison_work_attempt` from `SEALED_NOT_YET_WRITTEN` |
| `CMP-SPEND-01` | none | `comparison_model_call`; the `comparison_call` origin and `comparison_attempt_id` of `executor_task`; `_SPEND` union | `comparison_model_call` from `SEALED_NOT_YET_WRITTEN` |
| `CMP-STORAGE-PARTS-01` | none | multipart staging behind `comparison_upload_file.multipart_token` and `comparison_upload_part`; the abort sweep as comparison work; unreferenced-blob report in `blob_reference_audit.py` (the four blob columns are already audited) | — |
| `CMP-EXEC-IMAGES-01` | `claimExecutorTask` (the `max_images` gating), `getExecutorTaskImage` for crops | `RunnerImage.crop_id`, up to eight images per task on every channel | — |
| `CMP-INGEST-ZIP-01` | none | the `bundle_archive` set policy | — |
| `CMP-INGEST-01` | `createComparisonUpload`, `getComparisonUpload`, `getComparisonUploadProposal`, `uploadComparisonUploadPart`, `completeComparisonUploadFile`, `confirmComparisonUploadSet`, `listComparisonVersionOrders`, `appendComparisonVersionOrder` | `comparison_upload`, `comparison_upload_set`, `comparison_upload_file`, `comparison_upload_part`, `comparison_version_order`; `document_version.upload_kind` (write and repository read); the `comparison_only_version` refusal in `runs/commands.py`; `ComparisonUploadAdapter` and `ComparisonVersionOrderAdapter` | its rows from the two enumerators; its tables from `SEALED_NOT_YET_WRITTEN` |
| `CMP-INGEST-02` | `listComparisonUploads`, `excludeComparisonUploadSet`, `retryComparisonUploadSet`, `pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload` | the state machines of `comparison_upload` and `comparison_upload_set` over `comparison_work` (kind per set) | the same |
| `CMP-PROFILE-01` | `listVersionPageProfiles`, `getVersionPageProfile`, `streamVersionPagePreview`, `streamVersionPageThumbnail`, `streamVersionPageTile` | `comparison_page_profile` and its three blobs; `VersionPageAdapter` | its five rows |
| `CMP-VERSION-MARK-01` | none (web) | reads `DocumentVersion.upload_kind` from the generated client | — |

A lane that finds a field missing STOPs to the wave's FIX slot; it does not edit the contract.

## 12. Instructions for the integrator

1. Merge `agent/cmp-seal-c0` as it is (do not squash: `web/FRONTEND_LOCK.json` names `21058a2f`), then re-run `npm --prefix web run api:verify` after any rebase. The contract and the migration head are held by this seal until its merge (plan section 5).
2. `uv sync --frozen` pulls about 230 MB more into every image; check the disk of the build host and note the image size.
3. Tell the `PROD` owners: no compose file changed; the first time the flag is turned on, `infra/deploy/compose.server.yml` (PROD-05b) needs `AUDITMANAGER_COMPARISON_MODULES: ${AUDITMANAGER_COMPARISON_MODULES:-none}` on the `api` and `worker` services, and `bootstrap/settings.py` (composition-root owner) should take over the read.
4. Rows and docs this seal does not edit: `DEBT_REGISTER.md`, the rulings, `docs/program/dispatch/COMPARE-MODULES-PLAN.md` (it still names the plan's eight tables and the page reads by number).
5. Forbidden hotspots untouched: `git diff --name-only 03f73103..HEAD -- web/src ':!web/src/shared/api' ':!web/src/app/bff'` prints nothing; no file under `src/auditmanager/jobs/`, `infra/deploy/compose.server.yml`, global styles or screens changed.
