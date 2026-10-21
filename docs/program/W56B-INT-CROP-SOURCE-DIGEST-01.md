# W56B-INT-CROP-SOURCE-DIGEST-01 — saved IMAGE crop source binding

Base: published development candidate
`417123c729599cfa075d3461038c8dd15b86d4a3`.

The unserved crop reader now requires exactly one structured-companion entry
in the Run Version's immutable manifest. Before opening saved artifact Blobs,
it checks Version and project identity plus the entry's role, media type,
positive byte size, SHA-256 and Blob ID shape. After the existing full crop
cohort byte check, the reader compares its portal `blocks_sha256` to that
entry. The final fence rereads Version along with Attempt, Run and StageResult.

The discriminating regression first failed: a changed canonical portal
artifact, recomputed StageResult reference and matching Blob bytes returned a
cohort with a source digest absent from the Version. The fixed reader refuses
that combination with `analysis_input_invalid`.

## Checks

- Saved crop reader/custody and saved OCR reader suites: **57 passed**.
  Cases include the self-consistent changed Blob, missing/duplicate/wrong-role
  source entry, wrong media/SHA/size/Blob ID, a changed Version at the final
  fence and the normal successful read.
- Program governance suite: **16 passed**.
- Python compilation, frozen contract and migration SHA-256 readback,
  `git diff --check` and exact four-path proof: passed.
- No Docker, PostgreSQL, S3, proxy, paid call or full beta gate was run.

## Contracts and limits

No contract, migration, registry, producer, pure verifier, API/UI,
composition, dependency or served runtime change. The comparison proves that
the derived portal artifact names the Version's source content digest; it
does not prove that the original source Blob remains available. Tests use
fake ports, not a new real DB/S3 acceptance. The reader remains unserved and
selects no model, citation status, provider effect or cost policy.

Rollback is reverting this unserved reader/test change before wiring. No
data rollback or runtime flag is needed. Only these four paths change:

- `src/auditmanager/runs/geometry_crop_input.py`;
- `tests/integration/runs/test_geometry_crop_input.py`;
- `docs/program/tasks/W56B-INT-CROP-SOURCE-DIGEST-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after technical
handoff. Activation remains a separate W56b policy/effect task.
