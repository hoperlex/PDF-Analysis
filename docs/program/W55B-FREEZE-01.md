# W55B-FREEZE-01 — the W55b development freeze

**Integrator:** `pdf-analysis-29`, 2026-10-13.
**Base:** `origin/dev` after `v0.5.0` (W54 + W55a released; `origin/main` `23fd729`), plus `W55B-RULE-01`.
**Plan:** `dispatch/W55-PLAN.md` Part B, as adopted (`R-100`).
**Rulings:** `R-116` … `R-119` (§3.32), plus `R-102` (light acceptance per lane and one full gate before main) and `R-110` (no stand copy while the stand holds test data).

## Fixed at the freeze (§B4)

| Item | Value | Note |
| --- | --- | --- |
| migration | `0021_portal_bundles` | owned by `W55B-SEAL-01` |
| archive compression-ratio bound | 100 : 1 per member, and for the archive as a whole | §B3.1 |
| crop pixel budget | long side ≥ 800 px, ≤ 4 000 000 pixels per crop | §B3.7 |
| page-box tolerance | 0.5 % per side | §B3.7; the real pages differ by ≈ 0.06 % |
| `textless_pages` threshold | a page with fewer than 50 pypdfium2 characters | §B3.2 |
| upload timeouts | nginx upload location: `client_body_timeout 120s`, `proxy_read_timeout 300s`; BFF `AbortSignal.timeout(290 s)`; the API answers an accepted 250 MiB upload within ≈ 240 s, measured | §B3.2 |
| API worker count | one uvicorn process per stand; the upload concurrency gate admits 2 uploads, the third is refused before its body is read (`Retry-After`) | §B3.2 |
| analysis input budget | derived at start-up by `analysis.public.input_budget_characters(model_id, ceiling_usd)` (§B3.3); BUDGET records the calibrated ratio and the resulting figure for the configured model | not a literal |
| `contract_version` | unchanged (`1.0.0-draft.1`); its next value is decided at the beta freeze (`R-71`) | no event added |

## Inputs not present at the freeze

- **The owner's portal export** is absent: `.local/portal-exports/` does not exist. Implementation and FIXTURES use bundles assembled from the АР set's files (§B3.8). `W55B-REHEARSAL-01`'s real-export step is a stop until the owner supplies the export.
- **The W54 OCR and vision probe reports were not run**: they need that export, and the vision probe also needs the proxy key. §B3.5–§B3.7 stand as written. RECOGNISED and GEOMETRY record any contradiction they meet instead of redesigning.
- **W55a's 0.6.0 notes are not authored**: they come with P4. So `W55B-RELNOTES-01` waits for `v0.6.0`.

## Checks (`R-102`)

Every lane uses container-free light checks. Its DB, S3 and stack cases run on its private ports, one heavy step at a time, with at least 3 GiB available, and the lane cleans up afterwards. The plan's "(full gate)" lane labels are replaced. One full `make gate` runs on the final W55b candidate before `origin/main`. The BFF/nginx changes in STREAM still need `nginx -t` for both configs, run inside a disposable `nginx` container.

## Lanes, order and ports

The order follows plan §B4 and §B5:

1. SEAL.
2. FIXTURES (after SEAL).
3. STREAM (from SEAL's merge).
4. INGEST.
5. BUDGET.
6. RECOGNISED.
7. GEOMETRY.
8. WEB-BLOCKS.
9. REHEARSAL, RELNOTES, QA, JUDGE-X and JUDGE-Y, FIX.

Lanes run one at a time on this host. Shared files pass between owners in §B5's order.

| Lane | Private ports |
| --- | --- |
| `W55B-SEAL-01` | PostgreSQL `57410`, S3 `61010/61011` |
| `W55B-FIXTURES-01` | none |
| `W55B-STREAM-01` | `57420`, `61020/61021` |
| `W55B-INGEST-01` | `57430`, `61030/61031`; API `57530`, Next `31630` for the journey |
| `W55B-BUDGET-01` | `57440`, `61040/61041` |
| `W55B-RECOGNISED-01` | `57450`, `61050/61051` |
| `W55B-GEOMETRY-01` | `57460`, `61060/61061` |
| `W55B-WEB-BLOCKS` | API `57570`, Next `31670` for the journey |
| integrator | `57400`, `61000/61001` |

## SUITE file list

The suite was measured on this base with
`git grep -l -E 'upload_single_pdf\(|files=|"file": \(|upload_document\(|uploadDocument' -- tests web/tests scripts`,
which matched 62 files. The plan also adds `tests/e2e/pc01/journey/{journey,cdp}.mjs`,
`tests/e2e/pc01/test_live_text_analysis.py`, `tests/e2e/p02/test_journey.py`,
`scripts/manual-alpha-check.sh` and `tests/contract/test_alpha_acceptance_command.py`. Every
file below is granted to `W55B-INGEST-01`; INGEST states in its report why each one moved.

```text
scripts/light_acceptance.py
scripts/validate_bootstrap.py
tests/characterization/w13_baseline/journey.py
tests/characterization/w13_baseline/records/02-uploadDocument.success.json
tests/characterization/w13_baseline/records/17-uploadDocument.refusal.pdf_magic_bytes.json
tests/characterization/w13_baseline/records/18-uploadDocument.refusal.byte_size.json
tests/characterization/w13_baseline/records/19-uploadDocument.refusal.not_encrypted.json
tests/characterization/w13_baseline/records/20-uploadDocument.refusal.page_count.json
tests/characterization/w13_baseline/records/21-uploadDocument.refusal.every_page_has_extractable_text.json
tests/characterization/w13_baseline/records/22-uploadDocument.refusal.max_bytes.json
tests/characterization/w13_baseline/records/26-uploadDocument.refusal.additionalProperties.json
tests/characterization/w13_baseline/records/33-listVersions.success.json
tests/characterization/w13_baseline/test_response_baseline.py
tests/contract/domain_p02/test_openapi_document.py
tests/contract/test_cp00_candidate.py
tests/contract/test_deploy_auto_workflow.py
tests/contract/test_validate_bootstrap.py
tests/e2e/pc01/driver.py
tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json
tests/e2e/pc01/journey/fixtures/redden-write.manifest.json
tests/e2e/pc01/journey/fixtures/w28-live/w28-measure.manifest.json
tests/e2e/pc01/journey/fixtures/w28-live/w28-proxy.manifest.json
tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded.manifest.json
tests/e2e/pc01/journey/fixtures/w28-live/w28-recorded-redden.manifest.json
tests/e2e/pc01/journey/manifest.json
tests/e2e/pc01/journey/prove_the_guard_can_fail.py
tests/e2e/pc01/journey/refusals.mjs
tests/e2e/pc01/test_acceptance.py
tests/e2e/pc01/test_live_text_analysis.py
tests/e2e/test_pc01_journey_conformance.py
tests/integration/api/conftest.py
tests/integration/api/test_authorization.py
tests/integration/api/test_document_content_window.py
tests/integration/api/test_listing_surface.py
tests/integration/api/test_multipart_rules.py
tests/integration/api/test_no_internal_identifiers.py
tests/integration/api/test_role_register.py
tests/integration/api/test_served_document_and_health_plane.py
tests/integration/composition/test_deploy_script_refusals.py
tests/integration/db/test_norms_corpus_migration.py
tests/integration/ingest/test_envelope_rules_with_no_negative_fixture.py
tests/integration/ingest/test_idempotency.py
tests/integration/ingest/test_immutability.py
tests/integration/ingest/test_negative_envelope.py
tests/integration/ingest/test_project_document_count.py
tests/integration/ingest/test_publication.py
tests/integration/ingest/test_reconciliation.py
tests/integration/ingest/test_reconciliation_reads_the_bytes.py
tests/integration/ingest/test_reconciliation_rules_with_no_guard.py
tests/integration/ingest/test_service_refusals_with_no_guard.py
tests/integration/ingest/test_the_read_path_answers_the_manifest.py
tests/integration/norms/bundle/test_manifest.py
tests/integration/norms/test_snapshot_rows.py
tests/integration/p02_journey/journey.py
tests/integration/p02_journey/test_explicit_failures.py
tests/integration/p02_journey/test_manifest_role_seam.py
tests/support/expected_facts.json
web/tests/contract/seam-operations.contract.test.ts
web/tests/guards/dashboard-invalidation.guard.test.ts
web/tests/guards/rendered-language.guard.test.ts
web/tests/unit/projects/upload-failure.test.ts
web/tests/unit/screens/cold-load.test.ts
```

## Amendment 1 — the owner's portal export checked against §B3.1 and §B3.5 (2026-10-13)

The owner supplied `.local/portal-exports/13АВ-РД-АР-ТП1-ТП2_V1.zip` (9 035 796 bytes, never
committed, F-7). It is a fresh export of the same АР document the plan measured. The check was
read-only, run with `python -I` over the archive in memory.

**Holds as planned:**

- **Archive:** 4 entries, deflate only, UTF-8 name flag (bit 11) set, no data descriptors, no ZIP64, compression ratio ≤ 6.2, total uncompressed 9.9 MB.
- **Members:** one stem; one `.pdf`, `_blocks.json`, `_results.md` and `_results.html` each.
- **Pages:** PDF 30 pages = `pages[]` 30, `page_index` 0…29, every `rotation` 0. The page-box aspect differs by 0.012 %, inside the 0.5 % tolerance.
- **Blocks:** 129 (56 text, 47 image, 26 stamp), `blk_<32hex>` ids unique, every `coords_norm` inside [0,1] and ordered.
- **Agreement:** `_results.md` and `_blocks.json` agree both ways for text and image blocks (103 ids, 103 crop links). Stamps appear only in `_blocks.json`.
- **Text layer:** every page has one (≥ 50 characters).

**Differs from the plan's wording; the implementation follows the export:**

| Item | Plan text | Real export | Rule adopted |
| --- | --- | --- | --- |
| stamp audit | every corpus ZIP holds `_stamp_audit.json` | **absent** in this client export | stays **optional** (§B3.1 already says so); its absence is not a refusal |
| id field | "unique ids" | `block_id` | read `block_id` |
| type field | TEXT / IMAGE | `block_type` ∈ {`text`, `image`, `stamp`}, lower case | case-sensitive enum of these three; `_results.md` headers carry `[TEXT]`/`[IMAGE]` |
| extra block fields | — | `shape_type` ∈ {`rectangle`, `polygon`}, `export_status` | accepted; `shape_type` stored, `export_status` tolerated like `status` |
| `polygon_points` | "optional (12)" | a list of `[x, y]` pairs of variable length (6–11) on `polygon` blocks; empty on rectangles | a list of 3…64 normalised points, required non-empty only when `shape_type` is `polygon` |
| `ordinal` | non-unique | non-unique, **`null` on every stamp** | nullable |
| `crop_url` | capability URL | `https://…/api/crops/…`, **`null` on stamps** | nullable; never fetched (§B3.1) |
| top-level keys | `pages`, `blocks`, `document_id` | also `schema_version` (1), `coordinate_space` (`normalized_page_top_left`), `document_name`, `document_path`, `generated_at` | `schema_version` must be 1 and `coordinate_space` that literal, otherwise refuse; the rest are ignored (`document_path` is never identity or displayed) |
| `status` values | the portal's set, `failed` tolerated | only `recognized` in this export | keep the planned set |

**Not exercised by this export:** low-text or raster pages, rotations other than 0, failed
blocks, a stamp audit. Those stay covered by `W55B-FIXTURES-01`'s synthetic bundles.

**Unblocked:** the real-export step of `W55B-REHEARSAL-01`, and the report-only `W54-OCR-PROBE`,
which needs no network. `W54-VISION-PROBE` still waits for the proxy key on this host.
