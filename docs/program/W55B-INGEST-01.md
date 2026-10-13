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
- [~] 8. The suite: moved so far: characterization journey and records, `tests/e2e/pc01/{driver,test_acceptance,test_live_text_analysis}.py`, `tests/integration/ingest/*`, `tests/integration/p02_journey/*`, `tests/integration/api/conftest.py` (now delegates to the shipped adapter). Still to do: the probe over every directory, `tests/integration/api/*` tests that upload over HTTP, and the report's list of files left for part B.
- [ ] 9. 250 MiB bundle: memory and time measured (`.local/w55b-tools/measure_upload.py`, lane ports 57531/57532).
- [ ] 10. Mutation proofs, final checks, containment, hand-back.

## Design decisions (made while writing; each is open to the integrator's veto)

Filled in as they are made. See the end of the file for the readings where the plan was silent.
