# W55B-INGEST-01 — part A (backend and the test suite): living report

- Task: `dispatch/W55-PLAN.md` §B3.1, §B3.2 (limits, database), §B3.4, §B3.5, §B4 Stage B 1 `W55B-INGEST-01`, §B5.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `588773e9` (STREAM report; below it FIXTURES `461411b6`, SEAL `85fd99f0`).
- **Part A is this file's author. Part B** (the browser upload form, the browser journey, the final switch that refuses a bare PDF)
  is written afterwards by another writer. A successor can continue from `git log` and this file alone.
- This report is rewritten in every commit. The final form follows the six-item layout of the other lane reports.

## Status

Updated in each commit. `[x]` done and committed, `[~]` in progress, `[ ]` not started.

- [x] 1. Bundle reader `src/auditmanager/ingest/bundle_archive.py`: central directory, names, every archive rule, members extracted to temporary files with the actual bytes counted. Tests: `tests/integration/ingest/test_bundle_archive.py` (one refusal test per rule, product vs the FIXTURES reference validator on all 67 small negatives, the size rules declared and counted, names, ZIP64/descriptors/real deflate, memory).
- [x] 2. Bundle envelope `bundle_envelope.py`: PDF member (the bare PDF's own refusals), `_blocks.json` against the pinned schema (hand-written, compared with the contract file and with the generic checker over a seeded fuzz), `_results.md` both ways, text-layer rule, the three counts. Tests: `test_bundle_envelope.py`.
- [x] 3. Counts on `document_version` (`documents/{models,public,repository}.py`; NULL for a bare PDF). Not on the API wire.
- [x] 4. `IngestService.upload_bundle`: four stored members, fingerprint over all five digests, all staged before any is recorded, one breadcrumb transaction, one publication transaction. Tests: `test_bundle_publication.py` (fingerprint, HTML not stored, partial member set, refused bundle leaves nothing, reconciliation).
- [x] 5. `DocumentAdapter` routes by magic bytes (`looks_like_zip`; the bare-PDF branch is marked `W55B-LEGACY-BARE-PDF`).
- [x] 6. Limits: `envelope.py` and `ingest/__init__.py` 500 / 250 MiB; headroom chain gains `pre-check <= MAX_BYTES < UPLOAD_MAX_BODY < nginx` (`test_upload_limit_headroom.py` + 3 prover mutations); `ar_corpus` `MAX_PAGES` 500.
- [x] 7. Negatives: `oversize.pdf`, `too_many_pages.pdf` deleted; generators replace them; `SHA256SUMS`, `expected_issues.json`, `bundle_manifest.json`, `tests/contract/fixtures_ar/**` follow; both generators' `--check` and `sha256sum -c` are green.
- [~] 8. The suite: moved so far: characterization journey and records, `tests/e2e/pc01/{driver,test_acceptance,test_live_text_analysis}.py`,
  `tests/integration/ingest/*`, `tests/integration/p02_journey/*`, `tests/integration/api/*` (the conftest double delegates to the shipped
  adapter; the tests that upload over HTTP send bundles). Still to do: the probe over every directory (item C of the successor's brief)
  and the report's list of files left for part B.
- [ ] 9. 250 MiB bundle: memory and time measured (`.local/w55b-tools/measure_bundle.py`, lane ports 57531/57532).
- [ ] 10. Mutation proofs, final checks, containment, hand-back.

### Successor writer: verification of the predecessor's tree (2026-10-13, lane stack 57430/61030)

The first writer died after twelve commits. The second writer re-ran, on the lane stack and one invocation at a time:
`tests/integration/ingest` 540 passed; `tests/integration/api` 568 passed; `tests/integration/p02_journey` 59 passed;
`tests/characterization` 61 passed. `git diff --check` and `compileall` of the changed modules are clean.

## The owner's real export as an acceptance test (counts only, F-7)

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

## Design decisions (made while writing; each is open to the integrator's veto)

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
