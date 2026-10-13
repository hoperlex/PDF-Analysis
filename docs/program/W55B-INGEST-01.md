# W55B-INGEST-01 — report (the whole lane: backend, suite, browser upload, journey, final switch)

- Task: `dispatch/W55-PLAN.md` §B3.1, §B3.2 (limits, database), §B3.4, §B3.5, §B3.9 (the upload form), §B4 Stage B 1 `W55B-INGEST-01`, §B5, §C6.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `588773e9` (STREAM report; below it FIXTURES `461411b6`, SEAL `85fd99f0`).
- Written by three writers: the first died after twelve commits (`d4d4e483` to `5179fe75`), the second continued from `git log` and wrote part A
  (`3287aa23` to `1f9daab4`), the third wrote part B from `1f9daab4` (the browser upload, the journey, the final switch, this rewrite).
- **The lane is complete.** A portal bundle is accepted; a bare PDF is refused with `portal_bundle_required` and the Russian sentence by every route into the
  service (the final switch, `7d8535bd`, the lane's last implementation commit apart from the follow-ups listed in section 2.9, which change tests, the preflight and one drive line). The browser sends, pre-checks and
  explains a bundle. Nothing was pushed, merged or tagged. The one contract edit is the schema follow-up of section 4.1; no migration, lock file or composition root was touched.
- Left for the integrator (section 5): the full gate, the stand-side checks, and one stale document outside the grant.

## 1. Changed files

Part A (the list `git diff --name-status 588773e9..HEAD` gave when part A was handed back, `11f56050`; files added since are listed in the part B block below):

Product code: `src/auditmanager/ingest/{bundle_archive,bundle_envelope,bundle_members}.py` (new), `ingest/{__init__,commands,envelope,service}.py`,
`documents/{__init__,models,public,repository}.py`, `bootstrap/adapters.py` (`DocumentAdapter` only). Tests: `tests/integration/ingest/`
(three new modules `test_bundle_archive`, `test_bundle_envelope`, `test_bundle_publication`, the helper `bundle_support.py`, and the existing
modules moved to bundles), `tests/integration/api/`, `p02_journey/`, `tests/characterization/` (the journey and ten records), `tests/e2e/`
(driver, acceptance, live text analysis, journey conformance, the two headroom files), `tests/contract/fixtures_ar/`. Generators and fixtures:
`tools/fixtures/` (the negatives as generators, `MAX_PAGES`), `fixtures/synthetic/ar/` (`oversize.pdf` and `too_many_pages.pdf` deleted).

```text
A docs/program/W55B-INGEST-01.md
M fixtures/synthetic/ar/README.md
M fixtures/synthetic/ar/SHA256SUMS
M fixtures/synthetic/ar/bundles/bundle_manifest.json
M fixtures/synthetic/ar/expected_issues.json
D fixtures/synthetic/ar/negative/oversize.pdf
D fixtures/synthetic/ar/negative/too_many_pages.pdf
M scripts/manual-alpha-check.sh
M src/auditmanager/bootstrap/adapters.py
M src/auditmanager/documents/__init__.py
M src/auditmanager/documents/models.py
M src/auditmanager/documents/public.py
M src/auditmanager/documents/repository.py
M src/auditmanager/ingest/__init__.py
A src/auditmanager/ingest/bundle_archive.py
A src/auditmanager/ingest/bundle_envelope.py
A src/auditmanager/ingest/bundle_members.py
M src/auditmanager/ingest/commands.py
M src/auditmanager/ingest/envelope.py
M src/auditmanager/ingest/service.py
M tests/characterization/w13_baseline/journey.py
M tests/characterization/w13_baseline/records/02-uploadDocument.success.json
M tests/characterization/w13_baseline/records/13-getDocumentVersion.success.json
M tests/characterization/w13_baseline/records/17-uploadDocument.refusal.pdf_magic_bytes.json
M tests/characterization/w13_baseline/records/18-uploadDocument.refusal.byte_size.json
M tests/characterization/w13_baseline/records/19-uploadDocument.refusal.not_encrypted.json
M tests/characterization/w13_baseline/records/20-uploadDocument.refusal.page_count.json
M tests/characterization/w13_baseline/records/21-uploadDocument.refusal.every_page_has_extractable_text.json
M tests/characterization/w13_baseline/records/26-uploadDocument.refusal.additionalProperties.json
M tests/characterization/w13_baseline/records/32-listDocuments.success.json
M tests/characterization/w13_baseline/records/33-listVersions.success.json
M tests/contract/fixtures_ar/test_negative_fixtures.py
M tests/contract/fixtures_ar/test_portal_bundles.py
M tests/e2e/pc01/driver.py
M tests/e2e/pc01/test_acceptance.py
M tests/e2e/pc01/test_live_text_analysis.py
M tests/e2e/prove_the_headroom_guard_can_fail.py
M tests/e2e/test_pc01_journey_conformance.py
M tests/e2e/test_upload_limit_headroom.py
M tests/integration/analysis_engine/test_fail_closed.py
M tests/integration/api/conftest.py
M tests/integration/api/test_document_content_window.py
M tests/integration/api/test_journey.py
M tests/integration/api/test_multipart_rules.py
M tests/integration/api/test_no_internal_identifiers.py
M tests/integration/api/test_portal_block_routes.py
M tests/integration/api/test_schema_conformance.py
M tests/integration/composition/test_a_published_run_reports_itself.py
M tests/integration/composition/test_version_blocks_wire_shape.py
A tests/integration/ingest/bundle_support.py
M tests/integration/ingest/conftest.py
A tests/integration/ingest/test_bundle_archive.py
A tests/integration/ingest/test_bundle_envelope.py
A tests/integration/ingest/test_bundle_publication.py
M tests/integration/ingest/test_envelope_differential.py
M tests/integration/ingest/test_envelope_handle_adapter.py
M tests/integration/ingest/test_envelope_rules_with_no_negative_fixture.py
M tests/integration/ingest/test_envelope_through_the_service.py
M tests/integration/ingest/test_idempotency.py
M tests/integration/ingest/test_immutability.py
M tests/integration/ingest/test_negative_envelope.py
M tests/integration/ingest/test_project_document_count.py
M tests/integration/ingest/test_publication.py
M tests/integration/ingest/test_reconciliation.py
M tests/integration/ingest/test_reconciliation_reads_the_bytes.py
M tests/integration/ingest/test_reconciliation_rules_with_no_guard.py
M tests/integration/ingest/test_service_refusals_with_no_guard.py
M tests/integration/ingest/test_size_guard_boundary.py
M tests/integration/ingest/test_the_read_path_answers_the_manifest.py
M tests/integration/p02_journey/journey.py
M tests/integration/p02_journey/test_explicit_failures.py
M tests/integration/p02_journey/test_manifest_role_seam.py
M tools/fixtures/ar_corpus/document.py
M tools/fixtures/ar_corpus/envelope.py
M tools/fixtures/ar_corpus/negatives.py
M tools/fixtures/build_portal_bundles.py
M tools/fixtures/portal_bundle/committed.py
```

Part B, `git diff --name-status 1f9daab4..HEAD` (the commits after part A and the Amendment-1 follow-up):

```text
M docs/manual-tests/PC-01_prototype.md                 the refusal table (bundles, 501 pages, 250 MiB)
M docs/program/W55B-INGEST-01.md                       this file
M scripts/manual-alpha-check.sh                        the preflight checks the bundles, the bare PDF, the text file and the generated inputs
M src/auditmanager/bootstrap/adapters.py               the final switch: every upload goes to upload_bundle
M src/auditmanager/ingest/__init__.py                  exports (probe, AdmissionReport gone)
M src/auditmanager/ingest/envelope.py                  probe() and AdmissionReport deleted; inspect_pdf stays
M src/auditmanager/ingest/service.py                   upload_single_pdf and _commit_publication deleted
M tests/contract/test_alpha_acceptance_command.py      the preflight's upload files, with tests that can fail
M tests/e2e/pc01/journey/README.md                     the write half and the six refusals, as now
M tests/e2e/pc01/journey/fixtures/redden-refusals.json, redden-write.manifest.json, redden-write-bound.manifest.json
M tests/e2e/pc01/journey/fixtures/w28-live/{make_document.py, w28-*.manifest.json (4)}
A tests/e2e/pc01/journey/fixtures/w28-live/w28_own_document.zip     the same document as a bundle (make_document.py builds it)
M tests/e2e/pc01/journey/{journey.mjs (a comment), manifest.json, prove_the_guard_can_fail.py, refusals.mjs}
M tests/e2e/test_pc01_journey_conformance.py
M tests/integration/api/{conftest.py (a comment), test_multipart_rules.py}
M tests/integration/ingest/{test_bundle_envelope,test_bundle_publication,test_envelope_differential,test_envelope_handle_adapter,
                            test_negative_envelope,test_service_refusals_with_no_guard}.py
A tools/fixtures/build_journey_inputs.py               the generated journey inputs (never committed)
M web/src/entities/document-version/{index.ts, model/upload-envelope.ts, model/upload-failure.ts}
M web/src/features/upload-document/ui/upload-document-form.tsx
M web/src/shared/ui/states.tsx                         a comment
M web/src/widgets/upload-panel/ui/upload-panel.tsx
M web/tests/guards/rendered-language.guard.test.ts
M web/tests/unit/projects/{envelope-encoding-and-delivery,upload-envelope,upload-failure}.test.ts
M web/tests/unit/screens/{forms-and-pages,widgets}.test.ts
```

`web/tests/unit/screens/cold-load.test.ts`, `web/tests/guards/{upload-precheck-wiring,dashboard-invalidation}.guard.test.ts` and
`web/tests/contract/seam-operations.contract.test.ts` are in the plan's list and needed no change: they pass unedited against the new
envelope (they name the operation, the pre-check wiring and the invalidation, none of which moved). `cdp.mjs` and `write.mjs` needed no change either.

## 2. Checks, and how each new test was shown to fail

Part A's table, run on this branch at `11f56050` with the lane stack up (PostgreSQL 57430, S3 61030/61031), one invocation at a time, the host shared and loaded. Part B's checks follow in 2.6 to 2.9, on the final tree.

| Check | Result |
| --- | --- |
| `git diff --check` | clean |
| `python -m compileall -q` of the changed source, tools and test directories | exit 0 |
| `tests/contract` without `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`, `test_alpha_acceptance_command.py` | 717 passed |
| `tests/contract/test_alpha_acceptance_command.py` (clean committed tree) | 25 passed |
| `tools/fixtures/build_ar_corpus.py --check`, `tools/fixtures/build_portal_bundles.py --check` | exit 0 both |
| `sha256sum -c SHA256SUMS` in `fixtures/synthetic/ar` | exit 0, no line that is not `OK` |
| lane stack: `tests/integration/ingest` | 542 passed |
| lane stack: `tests/integration/api` | 568 passed |
| lane stack: `tests/integration/p02_journey` | 59 passed |
| lane stack: `tests/characterization` | 61 passed |
| lane stack: `tests/e2e` (no browser) | 159 passed, 5 skipped (the opt-in live-model tests of `test_live_text_analysis.py`) |
| lane stack: the two composition files and `analysis_engine/test_fail_closed.py` the first writer touched, and `tests/unit` | 29 passed |
| a full `make gate` | **not run** (not this lane's: light acceptance, `R-102`; the integrator owes it, section 5) |

Every new behaviour was shown to fail without its code (sections 2.4 for part A, 2.7 to 2.9 for part B). The sections below hold the real export, the 250 MiB
measurement, the migration probe and part B's own measurements.

### 2.1 The owner's real export as an acceptance test (counts only, F-7)

Run read-only over `.local/portal-exports/<the owner's export>.zip` (9 035 796 bytes; never copied, extracted into the repository,
committed, or quoted; the file's SHA-256 prefix and mtime were identical before and after). Method: `python -I` with `src/` on
`sys.path`; `extract_bundle` then `admit_bundle` (the product's reader and envelope), no parameter changed.

| Measure | Result |
| --- | --- |
| accepted | **yes** (no rule weakened) |
| archive members | 4 (`pdf`, `blocks`, `results_md`, `results_html`; no stamp audit) |
| pages / blocks | 30 / 129 (56 text, 47 image, 26 stamp) |
| `text_character_count` | 93 690 |
| `textless_pages` | none (empty) |
| `recognised_character_count` | 0 (no page is text-less) |
| reader + envelope time | 0.02 s extraction, 0.43 s admission, 0.45 s together |
| through the API on the lane stack (`measure_bundle.py file:<path>`, `serve.py` child on 57531/57532) | `201` in 0.7 s; the child's VmHWM grew 32.2 MiB over the idle process (165 648 KiB to 198 644 KiB) |

Structural facts of its `_blocks.json` (types and null counts only): every block carries the same eleven keys (`block_id`, `block_type`,
`coords_norm`, `crop_url`, `export_status`, `ordinal`, `page_index`, `page_label`, `polygon_points`, `shape_type`, `status`); `ordinal` and
`crop_url` are `null` on the 26 stamps and set on every other block; `polygon_points` is `null` on all 117 rectangles and a list of three
or more points on the 12 polygons; `status` and `export_status` are `recognized` on all 129.

### 2.2 The 250 MiB measurement (second writer)

**Method.** `.local/w55b-tools/measure_bundle.py VARIANT` (untracked; under `.local/`): builds a valid bundle with the `portal_bundle`
builders, starts `infra/deploy/serve.py` as a child it owns (lane `.env`, `AUDITMANAGER_API_PORT=57531`, health `57532`, loopback),
mints a credential through `tests/support/accounts.py`, creates a project, streams one multipart upload with a `Content-Length`
(1 MiB writes, `Content-Type: application/zip`) and reads the child's `VmHWM` (the kernel's peak resident set,
`/proc/<pid>/status`) before and after. **One API process per variant**, so every row is the growth of a fresh process over its own
idle peak. Tree: this branch at `27729ae8` (the `bundle_archive` fix below included); host load 1-3, 2.4-3.4 GiB free before each run.
No `nginx`/BFF in the path (loopback API only), so the time is the API's own, not the stand's.

| Bundle (archive size) | Answer | Time | `VmHWM` growth over the idle process (idle = 157-165 MiB) |
| --- | --- | --- | --- |
| the committed `ar_baseline.zip` (0.09 MiB), control | `201` | 0.5 s | +5.7 MiB |
| PDF = baseline + 30 MiB of comment lines after `%%EOF`, stored (30.07 MiB) | `201` | 1.0 s | +45.7 MiB |
| the same, 120 MiB (120.07 MiB) | `201` | 2.6 s | +127.6 MiB |
| the same, 244 MiB (244.07 MiB) | `201` | 3.4 s | +147.2 MiB |
| valid text PDF carrying one 244 MiB unreferenced stream before a correct xref, **stored** (244.04 MiB) | `201` | 1.9 s | +146.5 MiB |
| the same document, PDF member **deflated** (incompressible noise; 244.10 MiB) | `201` | 2.1 s | +146.0 MiB |
| baseline PDF + a 244 MiB `_results.html` of noise, stored (244.07 MiB): nothing near the PDF's size reaches PDFium | `201` | 2.9 s | +22.4 MiB |
| a generated 500-page bundle (`generated.bundle_with_pages(500)`, 0.80 MiB): the page ceiling, end to end | `201` | 0.8 s | +15.8 MiB |

**Reading.** The archive path alone (the HTML row) costs +22 MiB for a 244 MiB body: the members are counted and hashed in 64 KiB
pieces and written to temporary files. A large PDF member costs about +147 MiB on top of an idle process and **does not grow with
size past that**: 120 MiB gave +127.6 MiB, 244 MiB gave +147.2 MiB (+20 MiB for +124 MiB), and the document with its padding inside a
stream, with a correct xref and nothing to rebuild, gives the same figure (so it is not PDFium's xref rebuild). The plateau is what
the object store's multipart upload buffers and PDFium's page cache hold; it was not decomposed further. The plan's bound is that the
API answers an accepted 250 MiB upload within about 240 s: it answered in 1.9-3.4 s on loopback. **Memory is bounded and not
proportional to the bundle** (an idle API process of 165 MiB reached 308-315 MiB for a 244 MiB upload); the stand's own figures
belong to REHEARSAL. The generated archives were deleted after each run.

### 2.3 The migration probe (second writer)

**Method.** In a scratch edit (reverted; `git diff` empty afterwards) `DocumentAdapter.upload_document` and
`IngestService.upload_single_pdf` were made to raise `portal_bundle_required` for anything that is not a ZIP. Then, on the lane stack
(PostgreSQL 57430, S3 61030/61031), one invocation at a time with `--tb=no -rf`:

| Directory | Result with the bare-PDF paths refused |
| --- | --- |
| `tests/integration/ingest` | 533 passed, **7 failed** (all deliberate, below) |
| `tests/integration/api` | 568 passed |
| `tests/integration/p02_journey` | 59 passed |
| `tests/characterization` | 61 passed |
| `tests/integration/composition` | 725 passed, 2 skipped |
| `tests/integration/db` | 360 passed |
| `tests/integration/norms` | 753 passed |
| `tests/e2e` (no browser) | 159 passed, 5 skipped (`test_live_text_analysis.py`, opt-in `C2_PC01_LIVE=1`, spends money) |
| every other `tests/integration/*` directory (`access`, `analysis`, `analysis_engine`, `analysis_text`, `auth`, `decisions`, `execution`, `exports`, `findings`, `foundation`, `jobs`, `qa_w52`, `qa_w53`, `releases`, `runs`, `shared_kernel`, `storage`, `workers`) and `tests/unit`, `tests/replay` | all passed |

**The 7 tests that still send a bare PDF** (they test the legacy branch itself, so they are the final switch's to change):

- `tests/integration/ingest/test_bundle_publication.py`: `test_a_bare_pdf_still_publishes_with_no_counts_until_the_last_step`,
  `test_a_bundle_key_and_a_bare_pdf_key_never_replay_each_other`;
- `tests/integration/ingest/test_envelope_handle_adapter.py`: `test_a_zip_is_a_bundle_and_anything_else_is_still_the_single_pdf_entry`
  (three parameters: a bare PDF, `hello`, empty), `test_nothing_else_about_the_call_changed`, `test_a_missing_title_and_name_still_fall_back_as_they_did`.

No other Python test sends a bare PDF to the upload path; the five skipped tests of `test_live_text_analysis.py` upload through
`tests/e2e/pc01/driver.py`, which builds a bundle.

### 2.4 Mutation proofs (second writer, and the first writer's)

Method (`.local`-side driver, not committed): the mutation is a textual replacement in the **committed** source file, the named
tests run with `-x` on the lane stack, the file is restored from memory and its SHA-256 compared before and after (restored in every
row). Every mutation below made its test fail; the first failing test is named. The first run of the set left two mutations alive: one led to a test
fix (the refused-archive row), the other had been run against the wrong test file (the last row).

| Enforcement | The mutation | First failing test (in `tests/integration/ingest/`) |
| --- | --- | --- |
| symlink | `is_symlink` returns `False` | `test_bundle_archive::test_each_small_negative_is_refused_for_exactly_the_rule_it_was_built_to_break[symlink]` |
| ratio, declared | `_ratio_exceeded` returns `False` | `test_bundle_archive::test_a_ratio_above_the_bound_is_refused` |
| ratio, the bound itself passes | `>` becomes `>=` | `test_bundle_archive::test_the_ratio_rule_is_above_the_bound_and_not_at_it` |
| ratio, on what the stream used (new) | the check in `_unpack` is `if False` | `test_bundle_archive::test_a_header_that_claims_more_compressed_bytes_than_the_stream_holds_cannot_hide_the_ratio` |
| the stream ends at its end (new) | the `inflater.eof` break is `if False` | `test_bundle_archive::test_a_stream_that_ends_exactly_at_the_output_piece_with_bytes_behind_it_still_ends` (5 s alarm) |
| declared-size lie | the declared member bound is `if False` | `test_bundle_archive::test_a_member_one_byte_over_the_bound_is_refused_whether_stored_or_deflated[deflate]` |
| actual-size lie | the counted member bound is `if False` | `test_bundle_archive::test_a_header_that_declares_less_than_the_member_holds_is_caught_by_counting` |
| duplicate after NFC and case folding | the key is `shown.casefold()` | `test_bundle_archive::...built_to_break[duplicate_nfc_cyrillic]` |
| stem mismatch | the stem check is `if False` | `test_bundle_archive::...built_to_break[stem_mismatch_name]` |
| `0x7075` display name | the field is always skipped | `test_bundle_archive::test_the_display_name_is_decoded_in_the_ruled_order` |
| cp866 display name | cp866 decodes as latin-1 | `test_bundle_archive::test_the_four_name_encodings_decode_to_one_display_name[cp866]` |
| markdown to block list (a block with no single header) | the check is `if False` | `test_bundle_envelope::test_each_way_the_markdown_and_the_block_list_can_disagree_is_a_mismatch[duplicate_header]` |
| block list to markdown (a header for a block not held) | the check is `if False` | `test_bundle_envelope::...can_disagree_is_a_mismatch[extra_header]` |
| text-less pages computed | the admission returns `()` | `test_bundle_envelope::test_a_page_is_textless_below_fifty_characters_and_not_at_fifty` |
| text-less pages stored | the version gets `()` | `test_bundle_publication::test_the_three_counts_are_stored_together_and_exposed_on_the_version_record` |
| the HTML is hashed and dropped | the reader keeps it on disk | `test_bundle_archive::test_the_html_is_hashed_and_dropped_and_the_directory_holds_the_other_four` |
| the HTML is never stored | the reader keeps it and `STORED_MEMBERS` gets a row for it | `test_bundle_publication::test_the_html_is_hashed_and_never_stored` |
| the fingerprint covers the HTML | the HTML's digest is left out | `test_bundle_publication::test_a_bundle_that_differs_in_any_one_member_under_the_same_key_is_a_conflict[the HTML rendering-<lambda>]` |
| every member verified before any is recorded | a breadcrumb is written after each member | `test_bundle_publication::test_a_failure_while_staging_or_verifying_leaves_no_version_no_row_and_no_residue[2-stage_temporary]` |
| no version after a publication failure | a `publish` failure is swallowed | `test_bundle_publication::test_a_failure_while_publishing_leaves_no_version_and_the_reconciler_names_the_blobs[1]` |
| the version binds the complete member set | the version is bound to two members | `test_bundle_publication::test_a_complete_bundle_publishes_one_version_with_one_manifest_entry_per_stored_member` |
| a refused archive keeps nothing | the reader's clean-up on refusal is removed | `test_bundle_archive::test_a_refused_archive_leaves_no_temporary_directory` (**fixed**: it passed before, because the directory's finalizer removed it once the caught exception was freed; the test now holds the exceptions) |
| a refused bundle leaves nothing at the service | the same removal | `test_bundle_publication::test_a_refused_bundle_leaves_no_object_no_row_and_no_command_record[a size rule]` |
| 500 pages | `MAX_PAGES` is 30 | `test_bundle_envelope::test_the_page_ceiling_is_five_hundred_pages_inclusive` |
| 250 MiB | `MAX_BYTES` is 25 MiB | `test_bundle_archive::test_the_production_bounds_are_the_ruled_ones` |
| `looks_like_zip` (reader) | always `False` | `test_bundle_archive::test_the_magic_is_a_zip_local_header_an_empty_archive_or_a_spanning_marker` |
| `looks_like_zip` routing in the adapter | the ZIP branch is `if False` | `test_envelope_handle_adapter::test_a_zip_is_a_bundle_and_anything_else_is_still_the_single_pdf_entry[PK\x03\x04 a local header-upload_bundle]` |
| a non-ZIP is a non-ZIP before anything else (service) | the service's own check is `if False` | `test_envelope_through_the_service::test_a_non_zip_is_a_non_zip_before_it_is_anything_else_whatever_its_size` (**selected wrongly in the first run**, where the reader's second check made the mutant look equivalent) |

### 2.5 The 62 files of the freeze's SUITE list: which moved, which were left, and why

The list came from `git grep -l -E 'upload_single_pdf\(|files=|"file": \(|upload_document\(|uploadDocument' -- tests web/tests scripts`;
on this tree the same command matches 53 files (the 4 it matches outside the list are this lane's own legacy-path tests). The pattern is
broad: many matches are the word `files=` of another API or the operation's name in a table.

- **Moved to bundles (31 files, each now uploads a portal bundle or asserts what a bundle does):** the characterization `journey.py`
  and records 02, 17, 18, 19, 20, 21, 26, 33 (records 13 and 32 moved as well; the plan grants them beyond the list); `tests/e2e/pc01/{driver,test_acceptance,
  test_live_text_analysis}.py` and `tests/e2e/test_pc01_journey_conformance.py`; `tests/integration/api/{conftest,test_document_content_window,
  test_multipart_rules,test_no_internal_identifiers}.py`; the eleven `tests/integration/ingest/` modules of the list; and
  `tests/integration/p02_journey/{journey,test_explicit_failures,test_manifest_role_seam}.py`.
- **Left, because they send no PDF (16 files; the match is a word, and the probe of 2.3 confirms none fails with the bare-PDF paths
  refused):** `scripts/light_acceptance.py`, `scripts/validate_bootstrap.py`, `tests/contract/{test_cp00_candidate,test_deploy_auto_workflow,
  test_validate_bootstrap}.py` (the words `--untracked-files=all` and `json_files=`); `tests/characterization/.../test_response_baseline.py`
  and `tests/contract/domain_p02/test_openapi_document.py` (the operation's name in a list); `tests/integration/api/{test_authorization,
  test_listing_surface,test_role_register,test_served_document_and_health_plane}.py` (the operation in a table or in prose; no body);
  `tests/integration/composition/test_deploy_script_refusals.py`, `tests/integration/db/test_norms_corpus_migration.py`,
  `tests/integration/norms/test_snapshot_rows.py`, `tests/integration/norms/bundle/test_manifest.py` (keyword arguments named `files=`
  or `...profiles=`); `tests/characterization/.../22-uploadDocument.refusal.max_bytes.json` (a request with no body at all, refused by
  the transport cap STREAM set).
- **Left for part B (14 files, browser or journey, not to be edited here):** `web/tests/contract/seam-operations.contract.test.ts`,
  `web/tests/guards/{dashboard-invalidation,rendered-language}.guard.test.ts`, `web/tests/unit/projects/upload-failure.test.ts`,
  `web/tests/unit/screens/cold-load.test.ts`; `tests/e2e/pc01/journey/{manifest.json,refusals.mjs,prove_the_guard_can_fail.py}` and the six
  `tests/e2e/pc01/journey/fixtures/**/*.manifest.json`. (`prove_the_guard_can_fail.py` matches only operation names.)
- **Not this lane's:** `tests/support/expected_facts.json` (`tests/support/**`).

### 2.6 Part B: the checks on the final tree (`d809c91e`, the tree clean when each runs; the two live runs after the switch were made on `6b45bb63`, one drive line earlier)

Lane stack `auditmanager-w55b-ingest` (PostgreSQL 57430, S3 61030/61031, API 57530/57531, Next 31630); host load 5 to 15, 2.7 to 5.8 GiB available before each heavy step;
one invocation at a time. Exit codes were captured with `cmd > file 2>&1; rc=$?`.

| Command | Exit | Result |
| --- | --- | --- |
| `git diff --check` | 0 | clean |
| `python3 -m compileall -q src/auditmanager/ingest src/auditmanager/bootstrap/adapters.py tools/fixtures tests/integration/ingest tests/integration/api tests/e2e tests/contract/test_alpha_acceptance_command.py` | 0 | |
| `npm --prefix web run lint` | 0 | |
| `npm --prefix web run typecheck` | 0 | |
| `cd web && npx vitest run --exclude 'tests/guards/query-key-shape.guard.test.ts'` | 0 | 130 files, 1963 tests passed |
| `cd web && npx vitest run tests/guards/query-key-shape.guard.test.ts` | 0 | 14 passed |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract` minus `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py` (the alpha command test needs a clean committed tree, which it had) | 0 | 752 passed, 18 927 subtests |
| `tools/fixtures/build_ar_corpus.py --check`; `tools/fixtures/build_portal_bundles.py --check`; `tools/fixtures/build_journey_inputs.py --check` | 0, 0, 0 | |
| `sha256sum -c SHA256SUMS` in `fixtures/synthetic/ar` | 0 | every line `OK` |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/e2e/test_pc01_journey_conformance.py` | 0 | 87 passed |
| `.venv/bin/python tests/e2e/pc01/journey/prove_the_guard_can_fail.py` | 0 | 39 mutations of the real `manifest.json`, 39 reds, 0 vacuous; the manifest restored |
| `npm --prefix web run e2e:pc01 -- --origin http://127.0.0.1:31630 --phase all --out .local/w55b-journey-out2` (after the switch) | 0 | `write steps checked: 3/3`, `routes checked: 28/28`, sentinel `e2e:pc01 OK` |
| `node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31630 --out .local/w55b-refusals-out2` (after the switch) | 0 | `6 fixture(s) driven, 0 finding(s)` |

### 2.7 Part B: the live journey, before and after the switch

Environment (no secret in a tracked file): API `infra/deploy/serve.py` (`AUDITMANAGER_PROVIDER_MODE=recorded`, the lane's `.env`, a generated `AUDITMANAGER_API_TOKEN`), web
`NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=w55b-ingest npm --prefix web run build` then `npx next start -p 31630 -H 127.0.0.1` with `AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:57530`
and the same token; an account provisioned through the API (`POST /auth/token` with the seeded `admin`, `POST /auth/password`, `PATCH /me` with names and an e-mail that becomes the login;
`R-50` would otherwise stop the sign-in at `/account/password`); `E2E_PC01_LOGIN`, `E2E_PC01_PASSWORD` and `E2E_PC01_CHROME` (Chrome for Testing 154, installed on the host) at run time.
The recipe is the earlier reports' (`W47-PASS.md` section 5, `W51-ROUTES-01.md`); it worked as written.

| Run | Command | Exit | Result | Envelope (git-ignored) |
| --- | --- | --- | --- | --- |
| before the switch | `e2e:pc01 -- --phase all`, API started before the switch edits | 0 | 3/3 write steps, 28/28 routes, `e2e:pc01 OK` | `.local/w55b-journey-out/journey.json` |
| before the switch | `refusals.mjs` | 0 | 6 fixtures, 0 findings | `.local/w55b-refusals-out/refusals.json` |
| after the switch (a fresh stack, API from the committed final tree) | `e2e:pc01 -- --phase all` | 0 | 3/3, 28/28, `e2e:pc01 OK` | `.local/w55b-journey-out2/journey.json` |
| after the switch | `refusals.mjs` | 0 | 6 fixtures, 0 findings | `.local/w55b-refusals-out2/refusals.json` |

What the write half did: a project was created; the app's own file control attached `ar_baseline.zip` (92 161 bytes, declared `application/zip` by the browser); `POST /bff/v1/projects/{uid}/documents`
answered 201 and the screen navigated to the version's own address; `POST /bff/v1/runs` answered 202 and the run reached `published` (1 005 ms before the switch, 1 509 ms after).
The six refusals: a bare PDF (`ar_baseline.pdf`), a text file and the generated sparse 251 MiB file were refused by the browser with no upload request; `encrypted.zip`, `image_only.zip` and the
generated 501-page bundle were refused by the server (422, each with its own constraint and Russian rule sentence). **The bare-PDF case stays a browser refusal after the switch**: no screen can send
a bare PDF, so the server's own refusal of one is covered by a server-side test through the HTTP route
(`tests/integration/api/test_multipart_rules.py::TestEachRefusalNamesItsOwnRule::test_a_bare_pdf_is_refused_as_portal_bundle_required_and_publishes_nothing`). Every route logs one console line,
`NEXT_PUBLIC_WEB_BUILD_ID is missing from this build`: the lane's build did not set the variable; it is not a defect of the change. The reddening fixtures still go red:
`refusals.mjs --cases fixtures/redden-refusals.json` exit 1 (7 findings); `--phase write --manifest fixtures/redden-write.manifest.json` exit 1 (6 findings, 1 of 3 steps);
`... redden-write-bound.manifest.json` exit 1 (4 findings, 3 of 3 steps).

### 2.8 Part B: the migration probe in reverse (the final switch)

With the legacy branch, `upload_single_pdf`, `probe()` and `AdmissionReport` deleted (`7d8535bd`), every other directory was run on the lane stack, one invocation at a time
(`set -a; . ./.env; set +a; .venv/bin/python -m pytest -q -p no:cacheprovider --tb=short -rf <dir>`), each exit 0:

| Directory | Result |
| --- | --- |
| `tests/integration/ingest` | 593 passed |
| `tests/integration/api` | 569 passed |
| `tests/integration/p02_journey` | 59 passed |
| `tests/characterization` | 61 passed |
| `tests/e2e` (no browser) | 163 passed, 5 skipped (the opt-in live-model tests) |
| `tests/integration/composition` | 725 passed, 2 skipped |
| `tests/integration/db` | 360 passed |
| `tests/integration/norms` | 753 passed |
| `access` 239, `analysis` 247, `analysis_engine` 47, `analysis_text` 187, `auth` 122, `decisions` 69, `execution` 7, `exports` 43, `findings` 75, `foundation` 35, `jobs` 8, `qa_w52` 2, `qa_w53` 6, `releases` 59, `runs` 167, `shared_kernel` 10, `storage` 96, `workers` 40 (all `tests/integration/<name>`) | all passed |
| `tests/unit`, `tests/replay` | 1 passed, 7 passed |

**No test outside the seven failed**, and the seven are rewritten: the tests that sent a bare PDF on purpose now assert the refusal. Which they are and what each became:
`test_bundle_publication.py::test_a_bare_pdf_still_publishes_with_no_counts_until_the_last_step` is `test_a_bare_pdf_is_refused_with_portal_bundle_required_through_the_adapter`
(the adapter, a real service, a real database and bucket: `validation_failed`, `field: file`, `portal_bundle_required`, the Russian sentence, no object, no row, no command record);
`::test_a_bundle_key_and_a_bare_pdf_key_never_replay_each_other` is `test_a_refused_bare_pdf_does_not_burn_the_key_a_bundle_then_uses`;
`test_envelope_handle_adapter.py::test_a_zip_is_a_bundle_and_anything_else_is_still_the_single_pdf_entry` (three parameters) is
`test_every_upload_goes_to_the_bundle_entry_whatever_it_holds` (six parameters; the stand-in service no longer has a single-PDF entry, so an adapter that reached for it fails);
`::test_nothing_else_about_the_call_changed` and `::test_a_missing_title_and_name_still_fall_back_as_they_did` (now `test_a_missing_name_falls_back_to_a_zip_name_and_a_missing_title_stays_missing`)
assert the one entry; the adapter test that read four bytes now asserts it reads none (`..._reads_none_of_it`). `test_a_non_zip_is_a_non_zip_before_it_is_anything_else_whatever_its_size` is
unchanged and green. Added: `test_the_service_has_no_single_pdf_entry_left` and the HTTP route test.
`probe()` was imported by `test_envelope_differential.py` and `test_bundle_envelope.py`; both now build the same probe from the product's public pieces (`validate_source_filename`,
`as_handle`, `inspect_pdf(require_text=True)` and a digest) inside the test, so the 70 differential tests still hold the PDF rules to the previous implementation byte for byte.

### 2.9 Part B: how each new test was shown to fail

Method: as in 2.4. The mutation is a textual replacement in the **committed** file, the named tests run with `-x`, the file is restored byte for byte and its SHA-256 compared before and
after (**restored in every row**). Drivers were under the scratchpad and are not committed.

**B1, the browser upload** (`cd web && npx vitest run --bail=1 <files>`), 18 mutations, 18 killed. First failing test in each (all in `web/tests/`):

| Mutation | First failing test |
| --- | --- |
| the media-type check never refuses a non-ZIP | `unit/projects/upload-envelope` > refuses a bare PDF before it is sent, whatever its name says |
| `maxBytes` back to 25 MiB | > states 250 MiB in bytes, not megabytes |
| `maxPages` back to 30 | > states 500 pages and one ZIP archive |
| `endsWith('.zip')` becomes `includes('.zip')` | `envelope-encoding-and-delivery` > refuses a double extension when the browser declares nothing |
| the declared type is not lower-cased | > accepts an upper-case declaration |
| `application/x-zip-compressed` not accepted | `upload-envelope` > states 500 pages and one ZIP archive (the media types are asserted there) |
| a sentence for `bundle_member_set` missing | > has a sentence for each of them and for the PDF member constraints it keeps |
| the bare-PDF sentence dropped from the rules; a rule line dropped; the text-layer rule forgets the portal block | > names every refusal reason before a file is chosen (three mutations) |
| the page-count sentence matches a stale `1 <= page_count <= 30` | > states the page and size rules in the envelope numbers |
| the classifier prints no constraint sentence | `upload-failure` > adds the constraint sentence to the generic one and keeps the constraint name |
| the classifier invents a sentence for an unregistered constraint | > adds no sentence for a constraint nobody registered, and still shows its name |
| the file control accepts only `application/pdf` | `screens/forms-and-pages` > accepts one ZIP archive and says so to the file picker itself |
| the panel does not say where a bundle comes from; the panel prints the old limit | `screens/widgets` > says where a bundle comes from; > prints the two limits of the bundle and none of the old ones |
| the guard does not know `ZIP`; `.md` is no longer a filename | `guards/rendered-language` > does not redden a run state, a verdict, an identifier or a digest (two mutations) |

**B2, the journey inputs and the runbook**: 39 reds of 39 from `prove_the_guard_can_fail.py` (it gained three: a generated file the tool does not write, a committed file called
generated, a removed file name that came back). The tool and the script, by pytest `-x`: the tool no longer refuses an allocated stand-in (`test_the_journey_inputs_tool_refuses_to_allocate_the_oversize_file`);
the stand-in is not past the limit and the tool builds 500 pages instead of 501 (`test_the_journey_inputs_tool_writes_a_sparse_oversize_and_a_501_page_bundle`, the second after the
test was made to read the page count); the tool forgets one of its files (`test_every_refusal_fixture_the_journey_declares_is_on_disk_or_generated`); the preflight pins a wrong digest, a wrong size or
a wrong magic (`test_files_only_fails_when_an_upload_file_is_not_the_file_it_pins`); the preflight skips the generated inputs (`test_files_only_fails_when_the_generated_inputs_cannot_be_built`).
(One preflight mutation survived the first time: it appended an argument the function ignores, which is no mutation; the three real ones above are killed.) On the live stand the drive was mutated twice
and went red both times with a finding naming the file: a generated case looked for among the committed files, and a case's own `fixture_dir` ignored. The first run of those two showed
a crash (`Cannot read properties of undefined (reading 'total')`) instead of a finding, a defect of the drive's missing-fixture path older than this lane; `refusals.mjs` now returns its timings
there (`d809c91e`) and the finding prints.

**B4, the final switch**: with `adapters.py`, `service.py`, `envelope.py` and `ingest/__init__.py` restored byte for byte to the commit before the switch (the legacy branch back), all eight new
or rewritten tests fail (`pytest -x` on each, lane stack): the six adapter and publication tests, the HTTP route test (the bare PDF is published, 201) and `test_the_service_has_no_single_pdf_entry_left`.
The first run left one alive, `test_a_refused_bare_pdf_does_not_burn_the_key...`, because it called the service and not the adapter, so the legacy adapter could not touch it; it now goes
through the adapter and is killed. The four follow-up commits after `7d8535bd` change tests, the preflight tests and one drive line only (`266777a8`, `2aeae620`, `6b45bb63` and the missing-fixture fix);
none changes product code.

## 3. Contracts

**One edit, after the report was first written** (`f5057e1d`, section 4.1): `contracts/analysis/v1/portal-blocks.schema.json` now follows
Amendment 1. Otherwise **none changed.** `contracts/**` was not touched (the sealed schemas, the stage registry and the OpenAPI document are SEAL's), no migration
was added or edited (the counts columns and the 1-500 page check are SEAL's migration, which this lane only reads and writes), and
`pyproject.toml`, `uv.lock` and `bootstrap/composition.py` are untouched. New or changed Python interfaces, all behind
`auditmanager.ingest` and `auditmanager.documents`: `IngestService.upload_bundle`; `looks_like_zip` and `ZIP_MAGICS` (exported from
`auditmanager.ingest`); `inspect_pdf`, `PdfFacts`, `as_handle`, `page_text_refusal`, `TEXTLESS_PAGE_CHARACTERS` in `ingest/envelope.py`;
the three counts on the version record (`documents.models`, `documents.public`) and the manifest-role and blob-role constants for the
markdown, the structured companion and the stamp audit on `documents.public`. The wire is unchanged: the counts are on the
`document_version` row and its record, not on the API.

Part B changed **no contract**: no `contracts/**` file, no migration, no lock file, no composition root. It changed, in `auditmanager.ingest`, by deletion: `IngestService.upload_single_pdf`,
`envelope.probe` and `envelope.AdmissionReport` are gone (and with them their exports from `auditmanager.ingest`); `inspect_pdf`, `PdfFacts`, `as_handle`, `page_text_refusal` and
`validate_source_filename` stay. `DocumentPort.upload_document` and the `uploadDocument` operation are unchanged; a part that is not a ZIP now answers `validation_failed` /
`portal_bundle_required` (a value `W55B-SEAL-01` registered) on every path, not only for a ZIP-shaped one. New web public API (`entities/document-version`): `UPLOAD_CONSTRAINTS_STATED`,
`uploadConstraintSentence`, `PC01_UPLOAD_ENVELOPE.{mediaTypes, accept}`; the pre-check problem `not_pdf` is now `not_zip`.

## 4. Risks, known limits and readings where the plan was silent

Readings are decisions 1-14 at the end of this file. In addition:

- **Memory is bounded, not small.** An accepted 244 MiB bundle took an idle 165 MiB API process to 308-315 MiB (section 2.2). The
  figure is the API process alone on loopback, with no nginx or BFF in the path and a local object store; the stand's own numbers
  belong to REHEARSAL (the A13 decision).
- **The first writer's reader had a hang** (decision 13) and **hid a padded stream's ratio** (decision 14). Both are fixed and covered;
  the FIXTURES reference validator (`tools/fixtures/portal_bundle/validate.py`) shares neither defect-fix, so its differential
  agreement with the product holds for every fixture there is, not for those two adversarial shapes.
- **The sealed block-list schema differed from Amendment 1 in three places** (section 4.1): resolved by `f5057e1d`.
- **Text-less pages and the recognised count rest on a reading** (decision 8) of "the characters recognised on those pages".
- **PC-02's corpus check is red, as the plan registers it.** `.venv/bin/python tools/validation/corpus_check.py
  fixtures/validation/PC-02/corpus_manifest.json --quiet` exits 1 with `CHK-NEGATIVE-RULE` for `PC02-N03` (a 26 MiB file declared to break
  `ENV-SIZE`) and `PC02-N04` (31 pages declared to break `ENV-PAGES`): both are now inside the limits `tools/fixtures/ar_corpus/envelope.py`
  carries since `7b713b32`. Nothing in the gate or the test suites runs it. Debt, not changed here (`tools/validation/**` is not in this
  lane's grant).
- **The live journey was red until part B and is green now** (section 2.7): the manifest uploads `bundles/ar_baseline.zip`, its six refusals are bundle-based, and the browser says 250 MiB and 500 pages.
- **`scripts/manual-alpha-check.sh`** (part A stopped its preflight asking for the two deleted fixtures, `5179fe75`) now checks the files the journey uploads and the generated inputs, and needs `python3`
  in every mode (it needed it outside `--files-only` only).

Part B, in addition:

- **Resolved by the executor after part B (`4369245f`, outside the grant):** `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` and the human-tester pack under `artifacts/manual-alpha/` still named the two deleted fixtures (the pack's `SHA256SUMS` check failed, the runbook told a tester to upload bare PDFs). The runbook's file table, A03 and A10 now follow the bundle upload (six rejected files), and the pack is `alpha-test-files.tar.gz` (a deterministic tar of the three committed bundles, the bare PDF and text file the browser refuses, and the generated 501-page bundle; the 251 MiB stand-in is a `truncate -s 251M` sparse file). `sha256sum -c artifacts/manual-alpha/SHA256SUMS` passes.
- **The browser pre-check is a closed list**: `application/zip`, `application/x-zip-compressed`, or an empty type with a `.zip` name. A browser that labels a ZIP `application/octet-stream` or anything else
  would have it refused before it is sent (`not_zip`); the server would have accepted it (it decides by the first bytes). Not seen on Chrome or Firefox; the list is the brief's. Widening it is one array.
- **The server's own sentences are English except one**, and the web client cannot tell a catalog message from a call site's (`catalog-message.ts`), so the client states each constraint's rule itself
  (`uploadConstraintSentence`, 18 bundle values and the PDF member's five). A constraint the client has no sentence for is shown by name only. If SEAL registers a value, the contract test reading the
  note in `error-codes.json` reddens until a sentence is added.
- **`manual-alpha-check.sh --automated` cannot run on a host without `python3`** for the generated-input check (the journey itself, `refusals.mjs`, needs it too: `E2E_PC01_PYTHON` names another interpreter).
- **The upload panel and the failure screens print `constraint: <name>`** beside the Russian sentence, as the journey's `expects_rendered_from_envelope` requires; that machine token is English by the existing classifier,
  not new. The language guard judges the prose without it.

### 4.1 The sealed `_blocks.json` schema against Amendment 1 of the freeze

Resolved by `f5057e1d`. The schema (`contracts/analysis/v1/portal-blocks.schema.json`, SEAL's file), `bundle_envelope.py` and the FIXTURES
reference validator now state the same three rules, and `W55B-SEAL-01.md` ("Amendment 1 follow-up") records the contract edit:
`shape_type`, when present, is `rectangle` or `polygon`; `polygon_points` is `null` or empty on a rectangle and 3..64 normalised points
otherwise; a `polygon` block must carry a non-empty list. `status` is unchanged: the schema takes any lower-case token (`failed`
tolerated) and the plan never enumerated a set. `test_bundle_envelope.py` compares the three readings (product, reference, and a third
reading of the amendment) over every `shape_type` against every `polygon_points` case.

The rest of Amendment 1 holds in both and is covered by tests: `schema_version` 1 and `coordinate_space` the literal, otherwise refused;
`ordinal` and `crop_url` nullable; `export_status` tolerated; unknown top-level and block keys ignored; the stamp audit optional;
`block_id` / `block_type` (lower case, three values) read as named. "`shape_type` stored" has no ingest-side effect: the block list is
stored whole as `source.structured_companion` and `page_geometry_extraction` (GEOMETRY) normalises it. Since a rectangle's
`polygon_points` may now be `[]`, GEOMETRY must read an empty list as no polygon: the API's block view takes none or 3..64 points.

## 5. Instructions

### For the integrator

1. Merge `agent/w55b` through the commit that carries this file. Nothing here needs a migration or a lock change; the one contract edit is the schema follow-up of section 4.1 (`f5057e1d`).
   The branch already contains dev's `0.5.1`.
2. **Heavy steps still owed, none of them this lane's** (R-102 gave this lane light acceptance; the plan's C6 makes INGEST a full-gate lane): a full `make gate` with the literal `GATE OK` on the merged tree
   in the window; `npm --prefix web run e2e:pc01 -- --phase all` and `refusals.mjs` on the stand's own origin (they ran here on the lane stand, section 2.7, with a loopback API and no nginx or BFF
   proxy in the path); the stand's nginx upload locations with the 250 MiB body (STREAM's, `nginx -t` and the body test) and the 250 MiB memory figures on the stand (REHEARSAL, section 2.2);
   `make alpha-acceptance` / `manual-alpha-check.sh --automated` against a deployed candidate.
3. Register the PC-02 corpus-check debt (section 4) with the command and result given there.
4. `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` and `artifacts/manual-alpha/**` were rewritten by the executor (section 4); review that diff.
5. GEOMETRY must read an empty `polygon_points` list as no polygon (section 4.1).
6. The journey needs a Python 3 interpreter for the two generated inputs (`E2E_PC01_PYTHON`, default `python3`) and Chrome for Testing (`E2E_PC01_CHROME`); the lane's host has both.

## 6. Containment: `git diff --name-only 588773e9..HEAD` against the grant

The range includes the merge of `origin/dev` (`8e1a3043`: `VERSION`, `release-notes/0.5.1.json`, `web/src/app/globals.css`, the sign-in, user-list and version-history files, a few `docs/` files), which is
dev's and not this lane's; the lane's own files are `git log --first-parent --no-merges --format= --name-only 588773e9..HEAD` (111 files).

Inside the grant: everything under `src/auditmanager/ingest/**`, `src/auditmanager/documents/**`, `tests/integration/ingest/**`, `tools/fixtures/**`, `fixtures/synthetic/**`,
`src/auditmanager/bootstrap/adapters.py` (`DocumentAdapter` only), the SUITE files of `W55B-FREEZE-01.md`
(`tests/integration/api/{conftest,test_document_content_window,test_multipart_rules,test_no_internal_identifiers}.py`, `tests/e2e/pc01/{driver,test_acceptance,test_live_text_analysis}.py`,
`tests/e2e/test_pc01_journey_conformance.py`, the characterization `journey.py` and records 02, 13, 17-21, 26, 32, 33, `p02_journey/{journey,test_manifest_role_seam,test_explicit_failures}.py`,
`tests/contract/fixtures_ar/**`), `tests/e2e/{test_upload_limit_headroom,prove_the_headroom_guard_can_fail}.py`, `tests/integration/api/test_portal_block_routes.py`, and, for part B,
`tests/e2e/pc01/journey/{journey,refusals}.mjs`, `manifest.json`, `fixtures/**`, `prove_the_guard_can_fail.py`, `scripts/manual-alpha-check.sh`, `tests/contract/test_alpha_acceptance_command.py`,
`web/src/entities/document-version/model/upload-envelope.ts`, `web/src/features/upload-document/**`, `web/src/widgets/upload-panel/**`, `web/src/shared/ui/states.tsx` (a comment),
`web/tests/unit/projects/**`, `web/tests/unit/screens/{widgets,forms-and-pages}.test.ts`, `web/tests/guards/rendered-language.guard.test.ts`, `docs/manual-tests/PC-01_prototype.md` and this file.

**Outside the grant, each with its reason (10 files):**

| File | Why |
| --- | --- |
| `web/src/entities/document-version/model/upload-failure.ts` | the work order names "the upload-failure classifier"; the grant lists only `upload-envelope.ts`. It prints the constraint sentence (one call, `uploadConstraintSentence`) |
| `web/src/entities/document-version/index.ts` | the entity's public API exports the new helpers (the classifier and the tests may not import from `model/`) |
| `tests/e2e/pc01/journey/README.md` | stale after the move to bundles; it describes the write half and the refusals |
| `contracts/analysis/v1/portal-blocks.schema.json`, `docs/program/W55B-SEAL-01.md` | the Amendment-1 follow-up of section 4.1 (SEAL's files; recorded there) |
| `tests/integration/analysis_engine/test_fail_closed.py` | read `negative/too_many_pages.pdf`; now reads the same bytes from `bundles/pages_31.zip` |
| `tests/integration/api/test_journey.py`, `test_schema_conformance.py` | uploaded a bare PDF over HTTP (found by the migration probe, `9bc3d6d5`, separable) |
| `tests/integration/composition/test_a_published_run_reports_itself.py`, `test_version_blocks_wire_shape.py` | the same |

The brief also lists `web/tests/unit/screens/cold-load.test.ts`, `web/tests/guards/{upload-precheck-wiring,dashboard-invalidation}.guard.test.ts` and
`web/tests/contract/seam-operations.contract.test.ts`: not touched (they pass unedited, section 1).

Forbidden hotspots: `contracts/**` (except the one follow-up above), migrations, root dependency and lock files, `bootstrap/composition.py` and global styles are not in the lane's own file list
(`web/src/app/globals.css` is in the range only through dev's merge). `tests/support/**` and `tests/conftest.py` are untouched. The only `conftest.py` edit is a comment in
`tests/integration/api/conftest.py` (granted).

## 7. Appendix

### Design decisions (made while writing; each is open to the integrator's veto)

1. **The reader is hand-written, `zipfile` is the second opinion.** `bundle_archive.py` reads the end record, the ZIP64
   records and the central directory itself (raw name bytes, flags, external attributes, the `0x7075` field are what the
   rules are about), inflates with `zlib` in 64 KiB pieces and never trusts a declared size. The standard library reads
   the same archives in the tests and must agree. A differential test runs every one of the FIXTURES' 67 small archive
   negatives, 11 positives and 7 committed bundles through the product and through FIXTURES' reference validator and
   requires the same first constraint.
2. **Bounds** (named constants with their reason in `bundle_archive.py`): any member 250 MiB (`MEMBER_BYTES`, the PDF's
   own bound); the two members read into memory, `_blocks.json` and `_results.md`, 16 MiB (`TEXT_MEMBER_BYTES`: the
   norms corpus' worst case is 7.6 KB per page, 3.8 MB for 500 pages, and 1.1 KB per page for the block list; a 19.6 MB
   block list parses in 0.7 s and peaks at 80 MiB of Python objects); the stamp audit 4 MiB (`STAMP_AUDIT_BYTES`: worst
   62 KB, 547 bytes per page); total 300 MiB; ratio 100 : 1; 8 entries. FIXTURES' oracle needs `member_bytes >= 250 000` and
   `stamp_audit_bytes >= 4 000`: both hold. A text member over its bound answers `bundle_member_size`; a stamp audit over
   its cap answers `stamp_audit_invalid` (as the validator does).
3. **Order of refusal** is the validator's: archive (count, per-entry rules in directory order, duplicates, member set,
   stem, declared sizes, declared ratios, counted bytes), then the PDF, the block list, the markdown, the page count, the
   text-layer rule, the stamp audit. The first violation is raised. Ratio is judged on declared sizes only: once the
   counted bytes equal the declared size, the declared ratio is the real one, and a second check could not fire.
4. **What is stored.** `source.document`, `source.structured_companion`, `source.markdown`, `source.stamp_audit` (blob roles
   `source_document`, `source_structured_companion`, `source_markdown`, `source_stamp_audit`); `_results.html` is hashed
   while it is unpacked and dropped. Manifest roles are looked up in the stage registry at import, as the existing role is.
5. **Publication order** (service docstring): every member is staged and verified before any is recorded; the `verifying`
   rows of all members are committed in one transaction; objects are published one by one; one transaction marks every
   blob available, creates the document, the version with its manifest and counts, and the command's outcome. A failure
   discards every staged temporary. The reconciliation never assumed one temporary per attempt (it works from `blob` rows),
   so it needed no change; the tests show it naming several unattributed blobs of one attempt.
6. **Fingerprint** = project, target document, the digest of every member (`None` for an absent optional one), the PDF media
   type and the upload's own file name. Not the archive's bytes, compression, member order or name encoding.
7. **Display name.** `document_version.source_filename` is the PDF member's decoded name reduced to a plain base name (last
   path component, control characters to `_`, at most 255 characters); a missing title defaults to it. The upload's own file
   name is validated as before and used in the fingerprint, not stored.
8. **Counts** (precise definitions in `bundle_envelope.py`'s docstring). `text_character_count` is the sum of the lengths of
   pypdfium2's `get_text_range()` per page; `textless_pages` the 1-based pages below 50 such characters; `recognised_character_count`
   the length of the bodies in `_results.md` of the TEXT blocks of the block list that sit on a textless page. A body starts
   after the block's header and its `> **Key:** value` quote lines and ends at the next block header or page heading, trimmed
   of blank lines; line breaks inside it count one each. IMAGE bodies (the portal's descriptions) and stamps are not recognised
   text and do not count. All three are NULL together for a bare PDF.
9. **The bare-PDF path stayed, marked `W55B-LEGACY-BARE-PDF`, until the last step and is gone** (`7d8535bd`). `DocumentAdapter.upload_document` read the first four bytes, sent a ZIP to
   `upload_bundle` and anything else to `upload_single_pdf`; `upload_bundle` itself already refused a non-ZIP with `portal_bundle_required` and the Russian sentence, so the switch was one deleted
   branch, plus the method it called, its helper `_commit_publication`, `probe()` and `AdmissionReport`.
10. **A bundle's text-layer message is the bare PDF's** (`page_text_refusal()`): characterization record 21 must stay byte for
    byte, and a page the rule refuses has no embedded text layer in either entry.
11. **The envelope rule is "a text layer or a block of any type"** (FIXTURES' reading, kept). A STAMP-only or IMAGE-only page
    passes the rule and counts as textless.
12. **Stricter than the reference in one place**: a `block_id` with a trailing newline is refused (JSON Schema's `$` does not
    match before a final newline, Python's `re.search` does; the product uses `fullmatch`). A CRLF markdown is accepted
    (the reference would refuse its headers).
13. **A defect in the first writer's reader, found and fixed by the second** (`bundle_archive.read_chunks`). When a deflate stream
    ended exactly where one of the 64 KiB output pieces ended and the member's declared compressed length ran past the stream
    (padding behind it, which a header may claim), zlib reported the end of the stream but kept the bytes behind it as unconsumed
    input as well; the reader fed that tail back, got nothing, never stopped, and grew `unused_data` by the tail on every turn --
    a hang with unbounded memory, reachable by a crafted archive whose member unpacks to a multiple of 64 KiB. The reader now
    stops as soon as the stream ends. Test: `test_a_stream_that_ends_exactly_at_the_output_piece_with_bytes_behind_it_still_ends`
    (runs under a 5 s alarm so a regression fails instead of hanging; shown to fail with the check removed).
14. **The ratio is also judged on what the stream really used.** The declared ratio (`_judge_declared`) reads a header; a header can
    claim more compressed bytes than the stream holds, with padding behind it (the next member's header carries it), and so lower
    both the member's and the archive's declared ratio under 100 : 1 for a stream that is 1000 : 1. `_unpack` now also refuses
    `actual > ratio * consumed` (`consumed` is what the inflater took from the file before the stream ended; a stored member
    uses all it declares). Test: `test_a_header_that_claims_more_compressed_bytes_than_the_stream_holds_cannot_hide_the_ratio`
    (shown to fail with the check removed; it also proves the declared stage alone accepts the archive).

### Part B readings (where the plan or the brief was silent; each open to the integrator's veto)

15. **The browser pre-check is the brief's closed list**: `application/zip`, `application/x-zip-compressed`, or an empty type with a `.zip` name; the declared type is trimmed and lower-cased. The server decides
    by the first bytes. The refusal is named `not_zip` (it was `not_pdf`), the marker value the journey asserts, so a ZIP-checking branch no longer reports "not a PDF".
16. **Each constraint has a client-side sentence** (`uploadConstraintSentence`), restating the contract's own wording and adding no cause: 18 bundle values, the PDF member's `pdf_magic_bytes`, `parseable_pdf`,
    `not_encrypted`, `every_page_has_extractable_text` and `max_bytes`, and the two formulas the server writes (`1 <= page_count <= 500`, `byte_size <= 262144000`) matched against the envelope's current numbers, so
    a stale spelling prints no limit. The sentence is added after the catalog's generic one and before the `constraint:` / `field:` classifiers, which the journey asserts. A test reads the registered values out of the
    contract note and requires equality with the 18 it lists.
17. **The rendered-language guard learned `ZIP` and the `.md` / `.html` filename suffixes** (the bundle's `_results.md` and `_results.html` are named on screen so a reviewer can tell the files apart); a bare `HTML` or
    `Markdown` still reddens, and a new case judges every upload rule, pre-check message and refusal sentence as the form prints them (a refusal sits in a mutation's state, which no seed reaches).
18. **The six refusals** are a bare PDF, a text file and a sparse file past 250 MiB (the browser), and an encrypted bundle, an image-only bundle and a 501-page bundle (the server). `companion_archive.zip`
    (`bundle_member_set`) is no longer driven in the browser: the verifier and the acceptance suite expect exactly six records, and the Python suites still refuse it. A bare PDF is a browser refusal in the drive;
    the server-side refusal of one is the HTTP route test (section 2.7).
19. **Two inputs are generated, by a Python CLI, into a temporary directory the drive deletes** (`tools/fixtures/build_journey_inputs.py`; `E2E_PC01_PYTHON`). The oversize file is sparse (`truncate`), 251 MiB with a ZIP's
    first bytes; the CLI removes it and fails if the file system allocates it. The manifest declares the set twice and the conformance guard holds it equal to `--list`.
20. **`fixtures/w28-live/*.manifest.json` upload a committed bundle of their own document** (`w28_own_document.zip`, built by `make_document.py`, deterministic). They still carry no `session` section and drive nothing today
    (the README says so); they were moved so that whoever revives them uploads something the server accepts.
21. **The adapter's default file name is `upload.zip`** (it was `upload.pdf`; the route never sends an empty name), and a missing title is left to the service, which takes the PDF member's name.
22. **`probe()` and `AdmissionReport` were deleted although two test files imported them**: the tests now build the same probe from `validate_source_filename`, `as_handle`, `inspect_pdf(require_text=True)` and a digest.
    The alternative, keeping a production function for tests only, was rejected.
23. **`manual-alpha-check.sh` pins the five upload files by digest and size** (copied from `SHA256SUMS`) and runs the generator's `--check`; the previous per-PDF checks for the deleted negatives are gone.
24. **Light acceptance (R-102) was the level**: no `make gate`. The live journey and the six refusals ran twice on the lane stand (before and after the switch).
