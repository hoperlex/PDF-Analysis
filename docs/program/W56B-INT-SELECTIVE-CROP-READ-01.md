# W56B-INT-SELECTIVE-CROP-READ-01 — selected saved IMAGE crop result

**Status:** completed as an unserved, offline-tested source slice from dev64
`a09721a5895a0aff93d08f203fe1bedbbffffb8a`.

## Changed files

- `src/auditmanager/analysis/geometry/saved_crop_custody.py` — checks all
  saved IMAGE references and the complete portal/crop JSON cohort without
  requiring sibling PNG bytes; separately verifies the chosen PNG's digest,
  size, decoding and dimensions.
- `src/auditmanager/analysis/public.py` — narrow exports of the new pure
  metadata and selected-byte checks and their immutable result types.
- `src/auditmanager/runs/geometry_crop_item_input.py` — current-Attempt,
  caller-transaction-owned read of two metadata Blobs and one selected PNG.
- `src/auditmanager/runs/public.py` — public Runs facade export.
- `tests/integration/analysis/geometry/test_saved_crop_item_custody.py` —
  complete metadata, reused content-addressed PNG, missing/extra/changed
  saved refs, unknown block and corrupt selected bytes.
- `tests/integration/runs/test_geometry_crop_item_input.py` — one-PNG read,
  caps, source-digest check and final Attempt/Version/StageResult fences.
- `docs/program/tasks/W56B-INT-SELECTIVE-CROP-READ-01.md` — exact task grant.
- This result report.

## Checks

- New and predecessor crop suites: **46 passed**.
- ALR-05 context boundaries and programme task governance: **18 passed**.
  Pytest emitted five warnings while cleaning unrelated shared
  `/tmp/pytest-of-root/garbage-*` directories; neither suite failed.
- Owned Python compilation and `git diff --check`: passed.
- Frozen API, registry, crop schema, code-first plan, migration and source
  SHA-256 values matched the task. Exact eight-path and committed handoff
  proofs are recorded by the handoff output.
- No Docker, real PostgreSQL/S3, provider call or full `make gate` was run.
  R-135 defers the complete gate to the final beta code candidate.

## Integration contract and limits

`load_saved_image_crop_item` receives the caller's short transaction, current
Attempt, selected `portal_block_id`, BlobStore and separate positive caps for
the two metadata Blobs together and the selected PNG. It first checks the
Run and Version, including the one structured-companion source digest. The
pure metadata phase verifies exact canonical JSON, a complete IMAGE cohort,
all distinct saved crop references against that manifest and the selected
block's eligibility. The adapter then reads and checks only that PNG, and
rechecks Attempt, Run, Version and StageResult before returning. Two portal
blocks may share one content-addressed saved PNG reference.

The result certifies **only the selected PNG's bytes**. A sibling PNG may be
missing or corrupt and is not checked until separately selected. The
metadata scan and returned cohort still scale with the number of saved
blocks; the selected image is held in memory and Blob streaming can briefly
double its byte count. The caps come from a future caller, not an inferred
model budget. There is no served route, W56b provider/effect policy, citation
policy, finding or corpus claim. A later provider effect needs a fresh
authority check and journal.

## Integrator note

Review and integrate only the eight task paths. The existing complete-crop
reader retains its behavior and focused tests. Remove this unserved code and
tests before activation to roll back; there is no persisted-state migration,
feature flag or product-data rollback. No forbidden hotspot, remote ref,
checkpoint or tag changed.
