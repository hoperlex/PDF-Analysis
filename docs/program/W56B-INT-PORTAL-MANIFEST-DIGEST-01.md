# W56B-INT-PORTAL-MANIFEST-DIGEST-01 — saved OCR source digests

Base: published development candidate
`3a7c558a862d975f5305f6c54b15c6dfa5e9dca6`.

The unserved saved OCR region reader now requires exactly one markdown and one
structured-companion entry in the Run Version's immutable portal manifest.
It checks their media types, positive sizes, SHA-256 values and Blob ID shapes
before opening saved artifact Blobs. It then requires the recognised artifact's
`results_sha256` to equal the markdown source SHA-256 and the portal geometry
artifact's `blocks_sha256` to equal the structured-companion source SHA-256.
The existing bounded two-Blob read and the second Attempt, Run, Version and
StageResult fence remain in force. A changed manifest refuses at the second
Version check. No original portal source Blob is opened.

## Checks

- Saved OCR region and pure OCR candidate suites: **47 passed**. Cases include
  missing, duplicate and malformed manifest entries; wrong media or Blob ID;
  independently mismatched recognised and geometry inner source digests; and
  a manifest change during the read.
- Python compilation, task governance, frozen SHA-256 readback, whitespace and
  exact four-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or full gate was run.

## Contracts and limits

No contract, migration, registry, W54/W57/W58 path, provider, API/UI,
composition, dependency or served runtime change. This is read-only source
lineage checking; it sets no model, vision, citation, region or cost policy.
The tests use fake Run, Version, Job and Blob ports rather than persisted DB/S3
acceptance. Matching digests establish content identity with the Version
manifest, not current availability of the original member Blobs.

Rollback is reverting the reader/test change before wiring. No data rollback
or runtime flag is needed. Only these four paths change:

- `src/auditmanager/runs/recognised_region_input.py`;
- `tests/integration/runs/test_recognised_region_input.py`;
- `docs/program/tasks/W56B-INT-PORTAL-MANIFEST-DIGEST-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after direct handoff.
The reader remains unserved until W56b policy and persisted acceptance are
ready.
