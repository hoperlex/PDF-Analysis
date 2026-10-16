# W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01 — isolated DB and Blob drill code

**Base:** published `origin/dev=e70c91ef7064c8e36f377bd3995960a0e93acf35`.
**Status:** unactivated offline coordination; no real PostgreSQL/S3 drill or
recovery acceptance.

## Result

The restored-DB Blob audit now pins `0023_norm_citations` and enumerates both
`norm_retrieval_set.set_blob_id` and `catalogue_blob_id`. Each verified set
must name two available Blobs whose SHA-256 and size match its observed
facts; a rejected set must hold neither reference. The closed catalog still
refuses any unknown or missing schema-declared Blob source.

`run_isolated_restore_drill` sequences the completed W58 components. It
rehashes the private W54/W58 copy before invoking an injected PostgreSQL
restore callback. The callback must restore `db.dump` into an empty isolated
target, calculate the existing `stand-fingerprint-v1` digest, and yield a
stable read-only Session. The coordinator compares that digest to the copy
record, audits the restored DB and binds available Blobs to the sealed mirror
before any target object write. It then copies the entire mirror with
conditional writes and full S3 readback, reads every available DB Blob through
the target storage port, rechecks the local copy and returns counts/digests.
It does not run `pg_restore` or configure PostgreSQL/S3 by itself.

## Checks

- Frozen W58 scope/plan, migration 0023 and W58 helper hashes matched the
  formal task; `origin/dev` was exactly the base commit at dispatch.
- Focused Blob audit and coordinator tests: **33 passed**. They include both
  new Blob columns, wrong/missing/unavailable facts for either role, rejected
  set behavior, ordered restore/audit/write/readback, fingerprint refusal,
  no target write after DB failure, exact existing-object retry and refusal
  when either target Blob read is missing.
- Whole recovery suite plus programme governance: **140 passed**.
- Python compile, task parser/governance (`set()` findings) and
  `git diff --check`: passed. The exact changed-path list is below.
- No Docker, PostgreSQL, S3, paid provider, full `make gate` or remote ref
  operation was run. A full gate is deferred under R-135.

## Limits and integration

The operator must supply a restore callback that proves an empty isolated
PostgreSQL target, uses atomic `pg_restore`, computes the pinned fingerprint
from that restored database and yields a repeatable-read, read-only Session.
The operator must also prove that the object client and BlobStore use the same
isolated disposable bucket and keep the private copy and targets frozen.
Injected fakes prove control flow and refusal behavior, not those external
conditions. The coordinator reuses W58's bounded no-follow metadata reader;
that same-package helper is currently private and is a coupling to watch if
the recovery package is refactored. No source quiescence, elapsed restore
time, RPO or real DB/S3 readback has been measured. A separately owned
service lane is required before any W58 recovery or B6 claim.

No API, domain, stage or storage contract changed. Migration 0023 is read,
not edited. The audit's closed schema-source registry was updated for its
two new Blob columns; no recovery policy for other Blob states changed.

## Containment and rollback

Changed files are exactly:

- `scripts/recovery/blob_reference_audit.py`
- `scripts/recovery/isolated_restore_drill.py`
- `tests/integration/recovery/test_blob_reference_audit.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `docs/program/tasks/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`
- `docs/program/W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`

No forbidden `contracts/**`, migration, dependency, composition, global style,
stand or other recovery path was changed. The helper is not wired into served
behavior. Revert these six paths to roll back the code preparation. The
integrator may cherry-pick the exact task commit after checking its base,
run the addressed suite, and keep the service drill separately scheduled.
