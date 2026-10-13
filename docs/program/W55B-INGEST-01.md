# W55B-INGEST-01 — part A (backend and the test suite): report

- Task: `dispatch/W55-PLAN.md` §B3.1, §B3.2 (limits, database), §B3.4, §B3.5, §B4 Stage B 1 `W55B-INGEST-01`, §B5.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `588773e9` (STREAM report; below it FIXTURES `461411b6`, SEAL `85fd99f0`).
- Written by two writers: the first died after twelve commits (`d4d4e483` to `5179fe75`), the second continued from `git log` and the
  first version of this file (`3287aa23` onward) and wrote the sections marked "second writer".
- **Part A is complete; part B is not started.** Part B (the browser upload form, the browser journey, the final switch that refuses a
  bare PDF) is written afterwards by another writer; section 5 says exactly what it changes.
- **State left behind:** a portal bundle is accepted, and a bare PDF is **still accepted** (the branch marked `W55B-LEGACY-BARE-PDF`).
  Nothing was pushed, merged or tagged; no contract, migration, lock file or composition root was touched.

## 1. Changed files (`git diff --name-status 588773e9..HEAD`, before this file's last rewrite)

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

## 2. Checks, and how each new test was shown to fail

Run on this branch with the lane stack up (PostgreSQL 57430, S3 61030/61031), one invocation at a time, the host shared and loaded.

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
| a full `make gate`, the live browser journey, `npm` suites | **not run** (not this lane's: light acceptance, `R-102`; no web file was touched) |

Every new behaviour was shown to fail without its code (section 2.4). The same sections below hold the real export, the 250 MiB
measurement and the migration probe.

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

## 3. Contracts

**None changed.** `contracts/**` was not touched (the sealed schemas, the stage registry and the OpenAPI document are SEAL's), no migration
was added or edited (the counts columns and the 1-500 page check are SEAL's migration, which this lane only reads and writes), and
`pyproject.toml`, `uv.lock` and `bootstrap/composition.py` are untouched. New or changed Python interfaces, all behind
`auditmanager.ingest` and `auditmanager.documents`: `IngestService.upload_bundle`; `looks_like_zip` and `ZIP_MAGICS` (exported from
`auditmanager.ingest`); `inspect_pdf`, `PdfFacts`, `as_handle`, `page_text_refusal`, `TEXTLESS_PAGE_CHARACTERS` in `ingest/envelope.py`;
the three counts on the version record (`documents.models`, `documents.public`) and the manifest-role and blob-role constants for the
markdown, the structured companion and the stamp audit on `documents.public`. The wire is unchanged: the counts are on the
`document_version` row and its record, not on the API.

## 4. Risks, known limits and readings where the plan was silent

Readings are decisions 1-14 at the end of this file. In addition:

- **Memory is bounded, not small.** An accepted 244 MiB bundle took an idle 165 MiB API process to 308-315 MiB (section 2.2). The
  figure is the API process alone on loopback, with no nginx or BFF in the path and a local object store; the stand's own numbers
  belong to REHEARSAL (the A13 decision).
- **The first writer's reader had a hang** (decision 13) and **hid a padded stream's ratio** (decision 14). Both are fixed and covered;
  the FIXTURES reference validator (`tools/fixtures/portal_bundle/validate.py`) shares neither defect-fix, so its differential
  agreement with the product holds for every fixture there is, not for those two adversarial shapes.
- **The sealed block-list schema differs from Amendment 1 in three places** (section 4.1). The product follows the sealed schema, as a test
  requires, so the owner's real export passes; whether the contract or the amendment is right is the integrator's.
- **Text-less pages and the recognised count rest on a reading** (decision 8) of "the characters recognised on those pages".
- **PC-02's corpus check is red, as the plan registers it.** `.venv/bin/python tools/validation/corpus_check.py
  fixtures/validation/PC-02/corpus_manifest.json --quiet` exits 1 with `CHK-NEGATIVE-RULE` for `PC02-N03` (a 26 MiB file declared to break
  `ENV-SIZE`) and `PC02-N04` (31 pages declared to break `ENV-PAGES`): both are now inside the limits `tools/fixtures/ar_corpus/envelope.py`
  carries since `7b713b32`. Nothing in the gate or the test suites runs it. Debt, not changed here (`tools/validation/**` is not in this
  lane's grant).
- **The live browser journey is red until part B**, by construction: `tests/e2e/pc01/journey/manifest.json` still names the deleted
  `oversize.pdf` and `too_many_pages.pdf` and a 30-page constraint, and the browser pre-check still says 25 MiB and 30 pages. The
  container-free conformance test was changed to accept the generated cases; the live drive was not run (no browser, no web file touched).
- **One file part B owns was touched** (`scripts/manual-alpha-check.sh`): its preflight asked for the two deleted fixtures, so it
  stopped asking for them (commit `5179fe75`).

### 4.1 The sealed `_blocks.json` schema against Amendment 1 of the freeze (the schema is not edited here)

`contracts/analysis/v1/portal-blocks.schema.json` (SEAL) and `bundle_envelope.py` agree with each other (a test compares them keyword by
keyword). Against `W55B-FREEZE-01` Amendment 1 they differ in these places:

1. **`polygon_points` on a rectangle.** Amendment 1 writes "empty on rectangles" and adopts "a list of 3..64 normalised points, required
   non-empty only when `shape_type` is `polygon`". The schema allows `null` or a list of 3..64 points: **`[]` is refused**. The owner's real
   export has `null` on every rectangle, so it passes; a portal build that wrote `[]` would be refused by the schema and by the product.
2. **No conditional rule.** Amendment 1 requires a non-empty `polygon_points` when `shape_type` is `polygon`. The schema has no such rule
   (a `polygon` block with `null` or no `polygon_points` is accepted), and neither has the product.
3. **`shape_type` is any string** in the schema and in the product; Amendment 1 names the set {`rectangle`, `polygon`}.
4. `status`: the schema takes any lower-case token (`^[a-z][a-z0-9_]{0,39}$`, `failed` tolerated); Amendment 1 "keeps the planned set".
   Not a conflict in effect (every value of the real export is `recognized`), recorded for completeness.

The rest of Amendment 1 holds in both: `schema_version` 1 and `coordinate_space` the literal, otherwise refused; `ordinal` and `crop_url`
nullable; `export_status` tolerated; unknown top-level and block keys ignored; the stamp audit optional; `block_id` / `block_type`
(lower case, three values) read as named. "`shape_type` stored" has no ingest-side effect: the block list is stored whole as
`source.structured_companion` and `page_geometry_extraction` (GEOMETRY) normalises it.

## 5. Instructions

### For the integrator

1. Merge `agent/w55b` through the commit that carries this file; nothing here needs a migration, a lock change or a contract edit.
2. Register the PC-02 corpus-check debt (section 4) with the command and result given there.
3. Decide the three disagreements between the sealed block-list schema and Amendment 1 (section 4.1); until then the schema rules.
4. Run the lane's tests again after merging dev's `0.5.1`: the checks above were run on this branch's own base.
5. The 250 MiB figures are loopback figures (section 2.2); the stand's belong to REHEARSAL.

### For part B (the browser upload, the journey, the final switch)

*Browser constants still at the old envelope* (do not change them in this lane; part B owns them):

- `web/src/entities/document-version/model/upload-envelope.ts`: `mediaType: 'application/pdf'`, `maxBytes: 25 * 1024 * 1024`,
  `maxBytesLabel: '25 MiB'`, `maxPages: 30`, the `.pdf` name test, the sentences built from them; `web/src/features/upload-document/ui/upload-document-form.tsx`
  (`accept={PC01_UPLOAD_ENVELOPE.mediaType}`), `web/src/widgets/upload-panel/ui/upload-panel.tsx` (prints the limits), the comment in
  `web/src/shared/ui/states.tsx`.
- The plan's web tests: `web/tests/unit/projects/**` (including `upload-failure.test.ts`), `web/tests/unit/screens/{widgets,forms-and-pages,cold-load}.test.ts`,
  `web/tests/guards/{upload-precheck-wiring,dashboard-invalidation,rendered-language}.guard.test.ts`,
  `web/tests/contract/seam-operations.contract.test.ts`. The browser must send a ZIP (`application/zip` or no type), refuse a
  non-ZIP before sending, state 250 MiB / 500 pages, and the 250 MiB pre-check must stay strictly below nginx's `client_max_body_size`
  (`tests/e2e/test_upload_limit_headroom.py` holds that).
- The journey: `tests/e2e/pc01/journey/{journey,cdp,refusals}.mjs`, `manifest.json` (line 788 uploads `ar_baseline.pdf`; the refusals
  section names `oversize.pdf` and `too_many_pages.pdf`, the constraint `1 <= page_count <= 30`, and `fixture_dir` `fixtures/synthetic/ar/negative`),
  `fixtures/{redden-write,redden-write-bound}.manifest.json`, `fixtures/w28-live/*.manifest.json`, `prove_the_guard_can_fail.py`,
  `scripts/manual-alpha-check.sh` (the fixture preflight and the runbook steps that name PDFs), `tests/contract/test_alpha_acceptance_command.py`
  (reads that script), `tests/support/expected_facts.json` (not in this lane's grant either). The generated cases (a sparse over-bound
  file, a 501-page PDF) come from `tools/fixtures/portal_bundle/generated.py` (`oversize_sparse_file`, `pdf_with_n_pages`).

*The final switch* (the lane's last commit, after the suite moved; the browser and the journey must send bundles first):

1. `src/auditmanager/bootstrap/adapters.py`: delete the `else` branch marked `W55B-LEGACY-BARE-PDF` in `DocumentAdapter.upload_document`
   and the `looks_like_zip` routing that guards it; every upload goes to `IngestService.upload_bundle`, which already refuses a non-ZIP
   with `portal_bundle_required` and the Russian sentence.
2. `src/auditmanager/ingest/service.py`: delete `upload_single_pdf` and its docstring part; `ingest/envelope.py`: `probe()` and
   `AdmissionReport` serve only that path (`inspect_pdf` stays: the bundle's PDF member uses it), so remove them if nothing else imports them,
   and the module docstring's "until the last step" sentences (here and in `ingest/__init__.py`).
3. The seven tests that send a bare PDF on purpose (section 2.3): `test_bundle_publication.py::test_a_bare_pdf_still_publishes_with_no_counts_until_the_last_step`
   and `::test_a_bundle_key_and_a_bare_pdf_key_never_replay_each_other`; `test_envelope_handle_adapter.py::test_a_zip_is_a_bundle_and_anything_else_is_still_the_single_pdf_entry`
   (three parameters), `::test_nothing_else_about_the_call_changed`, `::test_a_missing_title_and_name_still_fall_back_as_they_did`. They must assert
   the refusal instead (the first of them becomes "a bare PDF is refused with `portal_bundle_required`").
   `test_envelope_through_the_service.py::test_a_non_zip_is_a_non_zip_before_it_is_anything_else_whatever_its_size` already asserts that
   refusal for a PDF-headed file, and it is the order the switch must keep (a non-ZIP is told it is not a bundle before its size is judged).
4. Characterization: records 17 and 26 and the rest of 02, 13, 17-21, 26, 32, 33 are bundle-based already and need no change; record 22 is the
   transport cap and is not this lane's. The columns' NULL for a bare PDF stay in the schema for the 30-page documents that exist.
5. Re-run the probe of section 2.3 in reverse: with the branch deleted, no test outside those seven may fail.

## 6. Containment: `git diff --name-only 588773e9..HEAD` against the grant

Inside the grant: everything under `src/auditmanager/ingest/**`, `src/auditmanager/documents/**`, `tests/integration/ingest/**`,
`tools/fixtures/**`, `tests/contract/fixtures_ar/**`, `fixtures/synthetic/ar/{negative/**,SHA256SUMS,expected_issues.json,bundles/**}`,
`src/auditmanager/bootstrap/adapters.py` (`DocumentAdapter` only: one routing branch), the SUITE files of `W55B-FREEZE-01.md`
(`tests/integration/api/{conftest,test_document_content_window,test_multipart_rules,test_no_internal_identifiers}.py`,
`tests/e2e/pc01/{driver,test_acceptance,test_live_text_analysis}.py`, `tests/e2e/test_pc01_journey_conformance.py`, the characterization
`journey.py` and records 02, 13, 17-21, 26, 32, 33, `p02_journey/{journey,test_manifest_role_seam,test_explicit_failures}.py`),
`tests/e2e/{test_upload_limit_headroom,prove_the_headroom_guard_can_fail}.py`, `tests/integration/api/test_portal_block_routes.py` (the plan's
one-line follow-up) and this file.

**Outside the grant, each with its reason (7 files):**

| File | Why |
| --- | --- |
| `scripts/manual-alpha-check.sh` | its preflight asked for the two deleted fixtures (part B's file; minimal change, `5179fe75`) |
| `fixtures/synthetic/ar/README.md` | its table described the two deleted fixtures and the old limits |
| `tests/integration/analysis_engine/test_fail_closed.py` | read `negative/too_many_pages.pdf`; now reads the same bytes from `bundles/pages_31.zip` |
| `tests/integration/api/test_journey.py`, `test_schema_conformance.py` | uploaded a bare PDF over HTTP (found by the migration probe, `9bc3d6d5`, separable) |
| `tests/integration/composition/test_a_published_run_reports_itself.py`, `test_version_blocks_wire_shape.py` | the same |

Forbidden hotspots: `contracts/**`, migrations, root dependency and lock files, `bootstrap/composition.py` and global styles are not in
`git diff --name-only 588773e9..HEAD`; no `web/**` file is either.

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
9. **The bare-PDF path stays, marked `W55B-LEGACY-BARE-PDF`.** `DocumentAdapter.upload_document` reads the first four bytes
   (`looks_like_zip`), sends a ZIP to `upload_bundle`, anything else to `upload_single_pdf` under the new limits. `upload_bundle`
   itself already refuses a non-ZIP with `portal_bundle_required` and the Russian sentence, so the final switch is one deleted
   branch (see the instructions for part B).
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
