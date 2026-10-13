# W55B-INGEST-01 — part A (backend and the test suite): living report

- Task: `dispatch/W55-PLAN.md` §B3.1, §B3.2 (limits, database), §B3.4, §B3.5, §B4 Stage B 1 `W55B-INGEST-01`, §B5.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `588773e9` (STREAM report; below it FIXTURES `461411b6`, SEAL `85fd99f0`).
- **Part A is this file's author. Part B** (the browser upload form, the browser journey, the final switch that refuses a bare PDF)
  is written afterwards by another writer. A successor can continue from `git log` and this file alone.
- This report is rewritten in every commit. The final form follows the six-item layout of the other lane reports.

## Status

Updated in each commit. `[x]` done and committed, `[~]` in progress, `[ ]` not started.

- [ ] 1. Bundle reader (`src/auditmanager/ingest/bundle_archive.py`): central directory, names, every archive rule, extraction to temporary files.
- [ ] 2. Bundle envelope (`bundle_envelope.py`): PDF member, `_blocks.json`, `_results.md` both ways, text-layer rule, counts.
- [ ] 3. Counts on `document_version`, `documents/public.py`, repository.
- [ ] 4. `IngestService.upload_bundle`: stored inputs, fingerprint, one publication transaction, reconciliation.
- [ ] 5. `DocumentAdapter` routes by magic bytes.
- [ ] 6. Limits: 500 pages / 250 MiB (`envelope.py`, `ingest/__init__.py`, headroom chain, `ar_corpus` `MAX_PAGES`).
- [ ] 7. Negatives: `oversize.pdf`, `too_many_pages.pdf` consumers moved to the generators, files deleted, `SHA256SUMS`, `pages_31.zip`.
- [ ] 8. The suite: every Python/JSON SUITE file moved to a bundle; the probe.
- [ ] 9. 250 MiB bundle: memory and time measured.
- [ ] 10. Checks, mutation proofs, containment, hand-back.

## Design decisions (made while writing; each is open to the integrator's veto)

Filled in as they are made. See the end of the file for the readings where the plan was silent.
