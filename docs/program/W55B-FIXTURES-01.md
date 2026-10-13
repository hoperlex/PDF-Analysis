# W55B-FIXTURES-01 — hand-back report

- Task: `dispatch/W55-PLAN.md` §B3.8 and §B4 `W55B-FIXTURES-01`; freeze `W55B-FREEZE-01.md`; sealed surface `W55B-SEAL-01.md`.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `85fd99f0` (the `W55B-SEAL-01` report commit).
  Commits: `a32be73d` (generator, writer, reader, validator), `4c027161` (the committed bundles), `0ad6d833`
  (archive negatives, positives, stand-ins, assemble tool), `df4bf7e5` (tests), `4aa3c535` (README), `37369ef5`
  and `2d1f91e2` (two more test cases); this report is the last commit.
- Checks follow `R-102` (container-free light checks). No container, database, object store or stand was used, and
  nothing was pushed, merged or tagged.

## 1. Changed files

`git diff --name-only 85fd99f0..HEAD` before this report: 29 paths, all inside the lane's grant (§6).

- **Generator package (new), `tools/fixtures/portal_bundle/`:**
  `zipwrite.py` (hand-rolled deterministic ZIP writer), `zipscan.py` (central-directory reader and the display-name
  decode), `portal_format.py` (constants, identifiers), `pdffacts.py`, `blocklist.py`, `results.py` (markdown and HTML),
  `stampaudit.py`, `bundle.py` (files, packing, `build_bundle`, the defect variant), `committed.py` (the seven committed
  bundles and their oracle), `validate.py` and `schemacheck.py` (the validator), `archive_negatives.py`, `positives.py`,
  `generated.py` (test-time stand-ins), `__init__.py`.
- **CLIs (new):** `tools/fixtures/build_portal_bundles.py` (writes, `--check`s), `tools/fixtures/assemble_portal_bundle.py`.
- **Edited:** `tools/fixtures/build_ar_corpus.py` (§4.1: 20 added lines, so its `--check` ignores the `bundles/` lines of
  `SHA256SUMS`); `fixtures/synthetic/ar/README.md`; `fixtures/synthetic/ar/SHA256SUMS` (eight lines appended, the eight
  existing lines and their order unchanged).
- **Committed outputs (new):** `fixtures/synthetic/ar/bundles/{ar_baseline, ar_baseline_minimal, ar_baseline_ocr_defects,
  image_only, image_only_with_block, encrypted, pages_31}.zip` (875 848 bytes together) and `bundle_manifest.json`.
- **Tests (new):** `tests/contract/fixtures_ar/test_portal_bundles.py` (70 tests). The three existing test files in that
  directory are unchanged.
- **Not touched:** `tools/fixtures/ar_corpus/**`, `fixtures/synthetic/ar/negative/**`, `ar_baseline.pdf`,
  `expected_issues.json` (their digests in `SHA256SUMS` are the same, and a test pins them), `fixtures/synthetic/README.md`.

## 2. Checks run, with commands and results

Run on the committed tree, from the worktree, each exit status captured directly (`rc=$?`), none behind a pipe.

| Command | Result |
| --- | --- |
| `git diff --check` | rc 0 (and `git diff --check 85fd99f0 HEAD` rc 0) |
| `.venv/bin/python -m compileall -q tools/fixtures tests/contract/fixtures_ar` | rc 0 |
| `.venv/bin/python tools/fixtures/build_portal_bundles.py --check` | rc 0; every artefact `OK`, the committed archives judged by the validator against the manifest |
| `.venv/bin/python tools/fixtures/build_ar_corpus.py --check` | rc 0 (unchanged result; see §4.1 for the edit that keeps it so) |
| `.venv/bin/python -m pytest -q tests/contract/fixtures_ar -p no:cacheprovider` | rc 0: **110 passed, 18 559 subtests passed** in 4.8 s (70 of them new) |
| `(cd fixtures/synthetic/ar && sha256sum -c SHA256SUMS)` | rc 0; 16 lines, all `OK` |
| `python3 tools/fixtures/build_portal_bundles.py --check` with the system interpreter (3.12.3, no venv) | rc 0 (pure standard library) |
| `.venv/bin/python -m pytest -q tests/contract/api_v1/test_surface_counts_in_prose.py -p no:cacheprovider` | rc 0, 33 passed (it reads tracked text under `tools/`, so it was run once to be sure the new files do not trip it) |
| the validator on the owner's real export's block list and markdown, read-only, `python -I`, only counts printed | 0 violations for 129 blocks; nothing of it was copied or written anywhere |

The last row is a measurement, not a committed test: it shows the validator's block-list schema and the
markdown-to-blocks match accept the format the fixtures mirror. The real files were not packaged, and the assemble tool
was exercised on synthetic directories only.

### How each new test was shown to fail

Each mutation was applied to the committed file (or committed data), the lane's tests run, and the file restored with
`git checkout` (`git status --porcelain` was empty after every one). "Rewritten" means `build_portal_bundles.py` was
run on the mutated code first, so that a test reading the committed archives sees the mutation. A test named
here was red; other tests were red as well in most rows and are not listed.

**Byte stability and determinism**

| Mutation | Red test |
| --- | --- |
| `BLOCK_CREATED_AT` `…07:36:38` → `…07:36:39` | `test_the_rebuild_equals_every_committed_file`, `test_check_mode_exits_zero_in_a_fresh_interpreter`, `test_every_timestamp_is_one_of_the_fixed_constants` |
| `block_id` mixes in a per-process counter | `test_building_twice_in_one_process_gives_identical_bytes`, `test_identifiers_are_digests_of_the_stem_the_kind_and_a_number` |
| `import random` added to `portal_format.py` | `test_the_package_imports_nothing_that_could_vary_between_runs` |
| `ROLE_ORDER = tuple(set(ROLE_ORDER))` (varies with `PYTHONHASHSEED`) | `test_interpreters_with_different_hash_seeds_agree` |
| each local header's DOS time advances by 2 per header written | `test_the_same_members_always_give_the_same_bytes`, `test_building_twice_in_one_process_gives_identical_bytes` |
| local header DOS time `+ 1`, bundles rewritten | `test_the_zip_timestamps_are_the_fixed_dos_constants` |
| `DISPLAY_PATH` an absolute path, bundles rewritten | `test_no_output_carries_a_path_a_clock_reading_or_a_host_name` |

**The committed set**

| Mutation | Red test |
| --- | --- |
| bundles rewritten around `pdf + b"\n"` (sums and manifest regenerated, so consistent) | `test_every_synthetic_pdf_has_a_bundle_carrying_its_exact_bytes` and the CLI `--check`; the existing `test_determinism.py` stays green, which is why this test exists |
| `SHA256SUMS` loses the `pages_31.zip` line | `test_sha256sums_covers_every_bundle_file_and_verifies`, the existing `test_sha256sums_covers_every_generated_artefact` |
| `bundle_manifest.json` says `image_only.zip` is `accepted` | `test_the_oracle_is_the_one_the_task_states`, `test_sha256sum_itself_accepts_the_file` |
| `pages_31.zip` deleted and a stray `stray.txt` added to `bundles/` | `test_the_bundle_directory_holds_the_seven_bundles_and_the_manifest_only`, `test_the_manifest_agrees_with_the_bytes`, `test_the_validator_agrees_with_the_oracle_on_the_committed_archives` |
| one character of `negative/not_a_pdf.txt` changed | `test_the_committed_negatives_and_baseline_are_untouched`, `test_the_committed_negatives_are_still_what_they_were`, the existing `test_every_recorded_digest_is_correct` |
| the minimal bundle also carries the HTML, bundles rewritten | `test_the_minimal_bundle_has_the_three_required_members_and_text_blocks_only` |
| the scanned pair's recognised text loses the word «распознанный», bundles rewritten | `test_the_scanned_bundle_pair_differs_only_by_the_blocks` |
| `MAX_PAGES` 500 → 30 (the committed 31-page bundle judged under the old bound) | `test_the_31_page_bundle_is_valid_under_the_new_limit`, `test_the_validator_agrees_with_the_oracle_on_the_committed_archives` |

**The portal formats (bundles rewritten)**

| Mutation | Red test |
| --- | --- |
| stamps receive ordinals | `test_ordinals_run_over_text_and_image_blocks_in_reading_order_and_stamps_have_none` |
| `RENDER_DPI` 300 → 150 | `test_page_sizes_are_the_300_dpi_render_and_match_the_pdf_aspect` |
| the markdown writes a section for stamps | `test_stamps_appear_in_the_block_list_and_never_in_the_markdown` |
| IMAGE bodies lose `**Summary:**` | `test_image_blocks_carry_the_portals_description_fields` |
| no blank line between a block header and its quote lines | `test_markdown_headers_follow_the_portals_layout`, `test_recognised_text_of_the_clean_bundles_is_the_text_layer` |
| recognised text of the clean bundles lower-cased | `test_recognised_text_of_the_clean_bundles_is_the_text_layer` |
| the defect variant forgets the CJK edit | `test_the_defect_variant_seeds_each_kind_and_keeps_designations_unflagged` |
| the stamp audit lists no stamps | `test_the_complete_bundle_has_everything_the_task_asks_for` |
| `status` and `export_status` swapped in a block | `test_the_block_list_has_the_portals_keys_in_the_portals_order` |
| `enabled` and `stamps` swapped in the audit | `test_the_stamp_audit_has_the_owners_corpus_shape` |
| the HTML links to the crop URL | `test_the_html_is_a_small_deterministic_document_without_links` |
| `A500C` dropped from the seeded designations | `test_the_defect_variant_seeds_each_kind_and_keeps_designations_unflagged` |

**The validator**

| Mutation | Red test |
| --- | --- |
| symlink check removed | `test_each_small_negative_is_refused_for_exactly_its_own_rule` (the `symlink` case) |
| markdown check loses the "header the list does not hold" half | the same test (`extra_header`, `header_for_a_stamp`) |
| `blocks_page_count` switched off | the same test (`fewer_pages`, `more_pages`) |
| stems compared after UTF-8 decode and NFC | the same test (`stem_mismatch_normalisation`) |
| stems compared by display name, not raw bytes | `test_names_are_compared_on_raw_bytes_across_encodings` |
| entry-count rule at 12 instead of 8 | `test_the_entry_count_gate_sits_between_eight_and_nine`, the same test |
| ratio rule never fires | `test_a_ratio_above_the_bound_is_refused_and_one_below_it_is_not` |
| member bound `>` → `>=` | `test_a_member_exactly_at_the_bound_passes_the_size_rules` |
| total-size rule never fires | `test_two_members_inside_the_member_bound_that_pass_the_total_are_refused` |
| actual bytes not counted against the member bound | `test_a_header_that_declares_less_than_the_member_holds_is_caught_by_counting` |
| declared sizes not checked | `test_one_byte_over_the_member_bound_is_refused_stored_or_deflated`, `test_a_header_that_declares_more_than_the_member_holds_is_refused_on_its_word` |
| upload bound `>` → `>=` | `test_exactly_at_the_bound_the_size_rule_does_not_fire` |
| text-layer rule ignores portal blocks | `test_a_page_without_a_layer_or_a_block_is_refused_and_a_block_satisfies_the_rule`, `test_the_validator_agrees_with_the_oracle_on_the_committed_archives` |
| `IMPLEMENTED_ENVELOPE_RULES` 5 → 4 (what a rule added to the contract would do) | `test_the_block_list_schema_is_read_from_the_contract_and_guarded` and most of the file |
| `schemacheck` ignores `minimum` | `test_each_small_negative_is_refused_for_exactly_its_own_rule` (`zero_width`) |
| `schemacheck` accepts `oneOf` as supported | `test_the_block_list_schema_is_read_from_the_contract_and_guarded` |
| `not_encrypted` answered under field `file` | `test_the_pdf_member_keeps_its_existing_constraints_and_fields`, `test_the_oracle_is_the_one_the_task_states` |
| the CRC-32 of an unpacked member no longer checked | `test_a_bundle_is_judged_on_what_it_unpacks_to_not_on_what_it_says` |
| the ZIP magic not checked | `test_the_committed_negatives_judged_as_uploads_under_the_bundle_rules` |
| freeze ratio 100 → 10 | `test_the_freeze_values_are_the_validators_defaults` |
| the `symlink` group dropped from the negatives registry | `test_every_registered_bundle_constraint_has_a_negative_and_a_field` |
| Info-ZIP Unicode Path field never consulted; flag 11 consulted after it | `test_display_names_decode_in_the_ruled_order` (each) |
| `infozip_unicode` writes a UTF-8 header name | `test_the_four_name_encodings_decode_to_the_same_display_name` |

**The writer and the stand-ins**

| Mutation | Red test |
| --- | --- |
| central-directory offsets `+ 1` | `test_standard_library_reads_every_header_combination`, `test_the_standard_library_reads_every_valid_output`, `test_the_directory_reader_agrees_with_the_standard_library` |
| stored-block deflate writes a wrong `NLEN` | `test_stored_block_deflate_is_a_valid_deflate_stream_whatever_the_length` |
| the ZIP64 field lists the compressed size first | `test_standard_library_reads_every_header_combination` |
| a `Fill` payload produced as one block | `test_a_large_member_streams_without_being_held_in_memory` (64 MiB member, traced peak under 8 MiB) |
| the oversize stand-in fully allocated (`posix_fallocate`) instead of `truncate` | `test_the_oversize_stand_in_is_sparse_and_past_the_upload_bound` |
| `pdf_with_n_pages` drops its last page | `test_501_pages_are_501_pages_to_the_independent_reader_and_small`, `test_a_501_page_bundle_breaks_the_page_rule_and_a_500_page_one_does_not` |
| `SYMLINK` attribute is a regular file's | `test_the_fields_a_negative_needs_land_where_the_standard_library_sees_them` |
| the textless page gets text after all | `test_a_page_without_a_layer_or_a_block_is_refused_and_a_block_satisfies_the_rule` |

**The tools and the generator's guards**

| Mutation | Red test |
| --- | --- |
| `build_bundle` ignores the validator's verdict | `test_the_generator_refuses_a_bundle_its_own_validator_rejects` |
| the assemble tool skips its validation | `test_it_refuses_and_leaves_nothing_when_the_validator_rejects` |
| the assemble tool accepts a directory with no PDF | `test_it_stops_on_a_directory_that_is_not_one_export` |
| the assemble tool ignores `--stamp-audit` | `test_it_packages_a_synthetic_export_deterministically` |
| `keep_appended_lines` drops the `bundles/` lines | `test_the_corpus_script_keeps_the_lines_another_generator_appended` and the existing `test_generator_check_mode_exits_zero` |
| `build_portal_bundles.checksum_bytes` drops the corpus generator's lines | `test_the_bundle_script_leaves_the_corpus_scripts_lines_alone` |

## 3. Contracts

**None changed.** `contracts/**` was read, never written: the validator reads `contracts/analysis/v1/portal-blocks.schema.json`
at run time (so it cannot drift from the pinned schema) and refuses to run if that file gains an envelope rule or a
keyword it does not implement. The registered classifier values are read from the `validation_failed` notes of
`contracts/domain/v1/error-codes.json` by a test, which fails if one lacks a negative.

## 4. Risks, known limitations, and readings where the plan was silent

### 4.1 An edit to `build_ar_corpus.py`, outside `ar_corpus/`

`build_ar_corpus.py --check` rebuilds `SHA256SUMS` and compares it byte for byte, so appending the `bundles/` lines made
it red. The task says it must still pass, and the new lines must be in the same file (the existing
`test_sha256sums_covers_every_generated_artefact` requires every file under the corpus to be listed). The smallest change
is in `tools/fixtures/build_ar_corpus.py` (20 added lines, no existing line altered): it keeps the lines starting
`bundles/` as they are, in both modes. `build_portal_bundles.py` does the converse. `ar_corpus/**` is untouched.

### 4.2 Readings where the plan or the brief was silent or differs

1. **An ordinary non-bundle ZIP is refused as `bundle_member_set`, not `portal_bundle_required`.** The brief lists it under
   the second; SEAL registered `portal_bundle_required` for "the part is not a ZIP, a bare PDF included". The fixtures follow
   the registered text (a bare PDF, plain text, gzip, a 7z header and an empty body are `portal_bundle_required`). If the
   owner wants a ZIP-wrapped PDF to get the "how to obtain the bundle" sentence, that is a contract change, not a fixture
   change. The committed `negative/companion_archive.zip`, judged as an upload, is `bundle_member_set`.
2. **Fields of the PDF member's refusals.** The brief says every manifest refusal has `field: "file"`. The existing envelope
   answers `not_encrypted` under `content` and `every_page_has_extractable_text` under `page_text` (characterization
   records 19 and 21, which STREAM keeps byte-identical), and SEAL registered the bundle constraints under `file` only. The
   manifest therefore records `content` and `page_text` for the two PDF-level refusals and `file` for archive-level rules.
   The manifest carries a `refusal_fields` note saying so. If INGEST moves those fields, the manifest moves with them.
3. **`negative/oversize.pdf` has no bundle.** "Every synthetic PDF gets a bundle" is followed for the four others. A 26 MiB PDF
   is over no limit under the bundle rules, and the brief's own list of seven bundles omits it; its replacement is the sparse
   file generated at test time. The test names this one exception (`UNBUNDLED_PDFS`) and asserts it is the only one.
4. **`image_only_with_block.zip` carries one TEXT block on each of the PDF's two pages**, not one block in all: both pages are
   scanned, and the rule is per page, so one block would leave the other page refused.
5. **"At least one portal block" means a block of any type**, a STAMP included (SEAL's wording: "neither a text layer nor a
   portal block"). Whether a stamp-only page should pass is INGEST's call; the validator's rule is one line to change.
6. **Crop URLs are `https://portal.invalid/api/crops/<20 characters>`**, not the portal's own host: the path shape is the
   real one, and no fixture may point at a host that could answer if something fetched it by mistake.
7. **Declared and actual sizes.** Declared sizes are judged first (member bound, then total), then declared ratios, then each
   member is unpacked and its real bytes counted. A header that disagrees with the unpacked bytes *within* every bound is
   `bundle_unreadable`; one that disagrees *across* a bound is the size rule. The ratio is judged only on members that passed the
   size rules, and the archive-level ratio cannot fire alone (a total ratio above 100 : 1 needs a member above it).
8. **The 8-entry bound is reachable only with extra entries.** A valid bundle has at most five members, so entries 6 to 8 are
   refused as `bundle_member_set`, and 9 as `bundle_entry_count` (the count is read from the end record before the directory
   is parsed). A test pins both sides.
9. **A bundle with an unreadable markdown (not UTF-8) is `results_blocks_mismatch`**; a stamp audit need only be JSON (not
   an object) and within `stamp_audit_bytes`. Neither has a registered constraint of its own.
10. **Names with a directory part (`dir/a.pdf`) are not refused** by the validator: the registered name rules are absolute,
    drive-letter, backslash and `..`. A member named `a.pdf` inside `dir/` has the stem `dir/a`, which every member shares.
11. **The text of the `ar_baseline_ocr_defects.zip` flaws** is an authored guess at what OCR does; the manifest records every
    seeded flaw (page, block id, kind, original, recognised, `flaggable`). The four engineering designations are in the
    recognised text of page 6 as separate Latin tokens, `flaggable: false`. RECOGNISED measures real precision on the real set.
12. **The encrypted bundle's recognised text is authored**, because the PDF's own text layer cannot be read without its
    password. The encrypted PDF's page count (2) is a constant of the fixture, not read from the file.

### 4.3 Risks and limits

- **zlib.** Committed archives do not depend on the zlib build: members are stored (the PDFs) or framed as hand-written
  deflate stored blocks, CRC-32 aside. Real deflate (`deflate="zlib"`) is used only by builders that run at test time and are
  never hashed (`real_deflate`, the size-driven archives, the assemble tool). A reader that only ever saw stored-block deflate
  is covered by the `real_deflate` positive, not by a committed file.
- **Memory.** The validator keeps the PDF, the block list, the markdown and the stamp audit of one bundle in memory, bounded by
  `member_bytes`; at 250 MiB that is INGEST's design problem, not a fixture's. The size-driven builders and the writer
  stream (a test traces a 64 MiB member at under 8 MiB). The host was loaded when sampled at the start (load average 65, 41, 29; about 1 GiB available), and every run above took under 6 s.
- **The validator is a reference, not the envelope.** INGEST's own envelope may order its checks differently; the oracle
  holds for what each fixture breaks, and the order of the validator's stages is documented in its docstring.
- **`ar_baseline.zip` and the other committed archives do not exercise a dynamic-Huffman deflate stream**, ZIP64 or a data
  descriptor; the test-time positives do.
- **Block geometry is synthetic**: a TEXT block covers the text area of the page, the IMAGE blocks sit over it. GEOMETRY's
  tests of the portal-to-PDF aspect check and of crops will want their own rotated pages (the plan says as much); the
  writer reads `/Rotate` and swaps the pixel size, but no committed fixture has a rotated page.
- **Not done:** nothing in the brief was left undone. `fixtures/synthetic/README.md` was not changed.

## 5. Instructions for the integrator (and for INGEST)

1. Read the diff and this report; merge `agent/w55b` at the tip named in the hand-back message by fast-forward. Nothing here
   needs a contract, migration or lockfile change, and the `fixtures/synthetic/ar/` digests other lanes pin are unchanged
   except `SHA256SUMS` itself (eight lines added).
2. **Which builder replaces which committed negative** (INGEST switches the consumers; the committed files stay until then):

   | Committed negative | Replacement |
   | --- | --- |
   | `negative/oversize.pdf` (over 25 MiB) | `generated.oversize_sparse_file(path, size)`, `size` named by the caller, past 250 MiB (`max_bytes`) |
   | `negative/too_many_pages.pdf` (31 pages) | `generated.pdf_with_n_pages(501)` and `generated.bundle_with_pages(501)` (`page_count`); the 31-page PDF is now valid, as `bundles/pages_31.zip` |
   | `negative/image_only.pdf` | `bundles/image_only.zip` (refused: `every_page_has_extractable_text`) and `bundles/image_only_with_block.zip` (accepted); `generated.bundle_without_block_on_textless_page()` and `generated.bundle_with_block_on_textless_page()` for a single textless page |
   | `negative/encrypted.pdf` | `bundles/encrypted.zip` (refused: `not_encrypted`) |
   | `negative/not_a_pdf.txt`, a bare PDF | `archive_negatives.plain_text()`, `bare_pdf()` (`portal_bundle_required`) |
   | `negative/companion_archive.zip` | `archive_negatives.ordinary_zip()` (`bundle_member_set`) |

3. **The oracle** is `fixtures/synthetic/ar/bundles/bundle_manifest.json` (`ar-portal-bundles/1`): per bundle `expected`
   (`accepted` or `refused`), `refusal.constraint` and `refusal.field`, the members with sizes and digests, block counts, and
   for `ar_baseline_ocr_defects.zip` the seeded flaws. `build_portal_bundles.py --check` re-judges the committed archives
   against it.
4. **One archive per registered constraint**: `archive_negatives.by_constraint()` maps each constraint to its small builders
   (67 in all, each returning `bytes`); `archive_negatives.SIZE_DRIVEN` maps `bundle_member_size`, `bundle_total_size` and
   `bundle_compression_ratio` to the builders that write to a path. `validate.validate(bytes_or_path, limits)` returns the
   constraint names a fixture breaks; a test of an envelope can compare against it.
5. **Bounds the caller must supply.** The freeze fixes the ratio (100 : 1, per member and for the archive), the total (300 MiB),
   the entry count (8) and the upload (250 MiB); they are the defaults of `validate.Limits`. **The per-member bound
   (`member_bytes`) and the stamp-audit cap (`stamp_audit_bytes`) have no default**; INGEST names them. Every size-driven
   builder takes the sizes it needs as arguments (`member_size(path, member_bytes=…)`, `total_size(path, member_bytes=…,
   total_bytes=…)`, `compression_ratio(path, size=…)`, `size_lie_declared_small(path, actual_bytes=…, declared_bytes=…)`,
   `size_lie_declared_large(path, actual_bytes=…, declared_bytes=…)`), each with `compress="stored"` or `"deflate"` (deflated
   zeros are a few hundred KiB for hundreds of MiB). With the committed bundles, any `member_bytes` of 250 000 or more and
   `stamp_audit_bytes` of 4 000 or more keep the oracle true (the largest member is `image_only.pdf`, 246 242 bytes).
6. **Imports.** Tests add `tools/fixtures` to `sys.path` and import `portal_bundle`, as the existing fixture tests do for
   `ar_corpus`; nothing here is importable from `src/`.
7. **Local runs with a real export.** `python3 tools/fixtures/assemble_portal_bundle.py <input_dir> <out.zip>
   [--stamp-audit FILE]` packages a directory holding `<stem>.pdf`, `<stem>_blocks.json`, `<stem>_results.md` (and, if present,
   `<stem>_results.html`, `<stem>_stamp_audit.json`); other files are listed and left out; a bundle the validator refuses is
   deleted. Keep the output under `.local/`, never in the repository.
8. **Regenerating.** `python3 tools/fixtures/build_ar_corpus.py` first (if the PDFs change), then
   `python3 tools/fixtures/build_portal_bundles.py`; each `--check` judges its own lines of `SHA256SUMS`.

## 6. Containment

- `git diff --name-only 85fd99f0..HEAD` before this report (29 paths): `fixtures/synthetic/ar/{README.md, SHA256SUMS,
  bundles/*}` (10), `tests/contract/fixtures_ar/test_portal_bundles.py` (1), and `tools/fixtures/{assemble_portal_bundle.py,
  build_ar_corpus.py, build_portal_bundles.py, portal_bundle/*}` (18). With this report the list gains
  `docs/program/W55B-FIXTURES-01.md`. Every path is inside `tools/fixtures/**`, `fixtures/synthetic/**`,
  `tests/contract/fixtures_ar/**` or this file.
- Not touched: `contracts/**`, `src/**`, `db/**`, `pyproject.toml`, `uv.lock`, `tests/integration/**`,
  `tests/characterization/**`, `docs/program/{DEBT_REGISTER, CURRENT_STATE}.md`, `.local/**`, `tools/fixtures/ar_corpus/**`,
  `fixtures/synthetic/ar/negative/**`, `ar_baseline.pdf`, `expected_issues.json`; no ref, tag, stand or other worktree.
- `git status --porcelain -uall` is empty after the report commit.
