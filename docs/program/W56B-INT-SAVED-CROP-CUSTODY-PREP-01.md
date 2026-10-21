# W56B-INT-SAVED-CROP-CUSTODY-PREP-01 — supplied saved crop bytes

Base: published `origin/dev` at
`f6f19220fa5ae019daae07a3771846e2523ce55a`.

The additive, unserved `check_saved_crop_bytes` checks one supplied
run-scoped `page_geometry_extraction` stage snapshot against its supplied
artifact bytes. It requires the expected successful stage version, unique
and correctly typed saved references, exact portal/manifest/PNG byte sets,
matching SHA-256 and size, canonical artifact JSON, a complete same-version
IMAGE crop cohort, exact saved-to-manifest crop refs, and decodable PNGs with
the recorded dimensions. Any disagreement refuses the whole input.

## Checks

- Focused container-free suite: **13 passed**. It exercises a W55b producer
  shaped snapshot; foreign run/stage/version/status; duplicate and unexpected
  references; missing/extra/corrupt bytes; a checksum-valid foreign VersionUid
  or noncanonical/invalid JSON; a changed saved crop ref; and
  corrupt/wrong-size PNGs.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace check and exact four-path inspection: passed at commit.
- No Docker, PostgreSQL, S3, provider, network or full gate was used while
  W55b's gate owned the host. R-135 defers the complete beta gate.

## Contracts and limitations

No contract, migration, stage registry, producer, serving path, API/UI,
composition, dependency or runtime behavior changed. The verifier checks
supplied values only. Its `run_id` is attached by a caller and does **not**
prove that a `StageResultRow` came from the corresponding repository query.
The tests use in-memory bytes, so this is **not** a DB/S3 Blob readback test.
The block-index reference is required as stage metadata but its bytes are
outside this IMAGE-input check. The current interface holds supplied PNGs
in memory; a served adapter must bound memory use for large runs.

Only these four paths changed:

- `src/auditmanager/analysis/geometry/saved_crop_custody.py`;
- `tests/integration/analysis/geometry/test_saved_crop_custody.py`;
- `docs/program/tasks/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md`;
- this report.

Remove the additive module and test before wiring to roll back. No data
rollback or feature flag is needed.

The future W56b runs/storage owner must get the row through
`RunRepository.stage_results(session, run_id)`, read the exact referenced
bytes from BlobStore, prove the Run's immutable VersionUid and current
Attempt authority, and fence or recheck mutable state before a model call.
Provider, budget, failure/resume and served-stage decisions remain open.
