# W55B-INGEST-01 — part A (backend and the test suite): living report

- Task: `dispatch/W55-PLAN.md` §B3.1, §B3.2 (limits, database), §B3.4, §B3.5, §B4 Stage B 1 `W55B-INGEST-01`, §B5.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `588773e9` (STREAM report; below it FIXTURES `461411b6`, SEAL `85fd99f0`).
- **Part A is this file's author. Part B** (the browser upload form, the browser journey, the final switch that refuses a bare PDF)
  is written afterwards by another writer. A successor can continue from `git log` and this file alone.
- This report is rewritten in every commit. The final form follows the six-item layout of the other lane reports.

## Status

Updated in each commit. `[x]` done and committed, `[~]` in progress, `[ ]` not started.

- [x] 1. Bundle reader (`src/auditmanager/ingest/bundle_archive.py`): central directory, names, every archive rule, extraction to temporary files. Agrees with the FIXTURES validator on all 67 small archive negatives, 11 positives and the 7 committed bundles (scratch differential; the committed test is still to write, see 10).
- [x] 2. Bundle envelope (`bundle_envelope.py`): PDF member, `_blocks.json`, `_results.md` both ways, text-layer rule, counts.
- [x] 3. Counts on `document_version`, `documents/{models,public,repository}.py` (NULL for a bare PDF).
- [x] 4. `IngestService.upload_bundle`: stored inputs, fingerprint, one publication transaction (code written; tests still to write, see 10).
- [x] 5. `DocumentAdapter` routes by magic bytes (`looks_like_zip`; the bare-PDF branch is marked `W55B-LEGACY-BARE-PDF`).
- [~] 6. Limits: `envelope.py` and `ingest/__init__.py` done (500 / 250 MiB). Still: headroom chain (`tests/e2e/test_upload_limit_headroom.py`, `prove_the_headroom_guard_can_fail.py`), `ar_corpus` `MAX_PAGES`.
- [ ] 7. Negatives: `oversize.pdf`, `too_many_pages.pdf` consumers moved to the generators, files deleted, `SHA256SUMS`, `pages_31.zip`.
- [ ] 8. The suite: every Python/JSON SUITE file moved to a bundle; the probe.
- [ ] 9. 250 MiB bundle: memory and time measured.
- [ ] 10. New tests for 1-5 (archive rules one by one, envelope, counts, publication, fingerprint, partial member set, reconciliation, adapter), mutation proofs, checks, containment, hand-back. **Not written yet at the time of the commit that added this line.**

Existing tests moved to the new limits in the same commit as the source: `tests/integration/ingest/*` (differential oracle at the new numbers, size window, negatives from generators), characterization records 02, 13, 17-21, 26, 32, 33 (re-captured; only the request side, the manifest and the two numbers moved), `test_portal_block_routes.py` (one line, the service entry). `tests/integration/ingest` + `tests/characterization`: 249 passed on the lane stack.

## Design decisions (made while writing; each is open to the integrator's veto)

Filled in as they are made. See the end of the file for the readings where the plan was silent.
