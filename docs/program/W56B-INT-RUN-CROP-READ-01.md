# W56B-INT-RUN-CROP-READ-01 — current Attempt crop read

Base: published `origin/dev` candidate 32,
`5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`.

The unserved `load_saved_image_crops` service receives an existing database
transaction and current Attempt authority. It fences the Attempt through the
Jobs repository; loads the exact Run and its saved geometry StageResult through
the Runs repository; checks a caller-supplied aggregate byte ceiling; streams
only the referenced portal, crop manifest and PNG Blobs under the StageResult's
SHA-256 and size declarations; runs the existing complete crop-byte verifier;
and rechecks the Attempt, Run and saved stage row before returning checked PNG
bytes. The block-index reference is required but not read for this IMAGE
input. The service uses only public Analysis, Jobs and BlobStore ports.

## Checks

- Focused container-free test command in the task: **21 passed**. The new
  tests prove exact run-scoped repository calls, current Attempt checks before
  and after Blob reads, four expected BlobStore stream reads, full cohort
  return, stale Attempt, changed Run/stage, foreign VersionUid, non-running
  Run, byte ceiling, corrupt Blob and missing/duplicate stage refusal.
- Python compilation, task-handoff governance, frozen SHA-256 readback,
  whitespace check and exact five-path diff: recorded after commit.
- No Docker, PostgreSQL, S3, provider, network or full beta gate was used.

## Contracts and limitations

No contract, migration, stage registry, geometry producer, storage adapter,
served route, composition or API/UI behavior changed. `analysis/public.py`
exports only the pre-existing pure W56b verifier types/function needed by the
Runs adapter. This is a real code path through RunRepository, JobRepository and
BlobStore interfaces, but its focused tests use offline fakes. A separate
isolated PostgreSQL/S3 acceptance is still required before serving it. The
Run/Job/Attempt/Lease row locks taken by `require_current` remain held while
Blob reads run in the caller's transaction; callers must keep that transaction
short. Returned bytes do not reserve authority for a subsequent provider
call. The future stage must recheck/journal the provider effect and enforce a
model/budget policy before dispatch. The explicit aggregate byte ceiling
limits retained input, but bytearray-to-bytes conversion can briefly double
one Blob's memory use.

Changed paths are exactly the five in the task's `Allowed paths`: one public
facade, one additive Runs adapter, one offline test, task and this report.
Rollback is deletion of the additive adapter/test and removal of the four
facade exports before runtime wiring; there is no data migration.
