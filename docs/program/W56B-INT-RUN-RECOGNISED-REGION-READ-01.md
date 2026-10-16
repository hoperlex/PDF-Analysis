# W56B-INT-RUN-RECOGNISED-REGION-READ-01 — saved OCR region read

Base: published development candidate
`95de4f6b4e10a8b60f57ae84ab66156917c7b96c`.

The unserved `load_saved_recognised_region` service binds a supplied OCR
block/page/quote to one current Run and Attempt. It reads the Run's frozen
Version and exactly one successful source and geometry StageResult, validates
their complete saved artifact-reference roles, and refuses a total Blob size
above the caller's explicit byte ceiling before opening storage. It reads
only the two required JSON Blobs, verifies the saved SHA-256 and size, exact
role/version and canonical bytes, then uses the existing pure W56b binder to
return a marked OCR quote with its checked portal region.

Before returning, it checks Attempt authority again and rereads Run, Version
and both StageResults. A changed value refuses. The caller owns the
transaction and holds its repository locks during the Blob reads; a later
effect needs a fresh authority check and journal.

## Checks

- New service plus existing OCR-region, saved TEXT and saved crop suites:
  **60 passed**. Covered cases include both Attempt fences, changed Run,
  Version and either stage, absent/duplicate/failed stages, invalid refs,
  foreign/nonportal/nonrunning Run, corrupt or overlong Blob, invalid byte
  ceiling, noncanonical JSON, mismatched page count and unbound quote.
- Analysis public boundary and architecture checks: **5 passed**.
- Python compilation, frozen SHA-256 readback, task parser, whitespace and
  exact five-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or full gate was run.

## Contracts and limits

No contract, migration, registry, W54/W57/W58 path, provider, API/UI,
composition, dependency or served runtime change. `analysis/public.py` adds
only the existing pure binder and its two types. The byte ceiling is an
explicit caller input; this task sets no model, vision, citation status,
region policy or spend. The service makes no DB or S3 write.

The focused tests use fake Run, Version, Job and Blob ports and establish
call order and fail-closed behaviour; they are not persisted DB/S3 acceptance.
The pure candidate's `results_sha256` and `blocks_sha256` remain the saved
artifact fields. This service verifies the outer saved Blob references and
canonical documents; it does not independently re-read the original portal
markdown or block-list members behind those inner digest fields.

Rollback is removal of the additive service/test and public exports before
wiring; no data migration or runtime flag is needed. Only these five paths
change:

- `src/auditmanager/analysis/public.py`;
- `src/auditmanager/runs/recognised_region_input.py`;
- `tests/integration/runs/test_recognised_region_input.py`;
- `docs/program/tasks/W56B-INT-RUN-RECOGNISED-REGION-READ-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after the direct
handoff. The service remains unserved until W56b citation/effect policy and
real DB/S3 acceptance are ready.
