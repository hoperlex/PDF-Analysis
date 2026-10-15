# W58-INT-OFFLINE-RESTORE-AUDIT-01 — offline recovery evidence coordinator

**Frozen base:** `248179be684395170311c8c2fea604ddea165bb5` (2026-10-15).
**Status:** read-only local evidence preparation; no real DB restore or S3 readback.

## Result

`scripts/recovery/offline_restore_audit.py` exposes
`collect_offline_restore_evidence(session, copy_dir, objects_root)`. It runs
the existing dump and mirrored-object preflight **before** any restored-DB
SELECT, then reopens `record.json`, `inventory.tsv` and `objects.json` through
an owned private directory with no-follow regular-file reads and size limits.
It calls the existing DB Blob-reference audit, binds all `available` rows to
sealed canonical objects with the storage public resolver, repeats the local
preflight and reads the metadata files again. A changed file, dump or mirror
prevents a result. The return value contains only the DB audit and bound
object facts; lower-level refusal types propagate.

The preflight API returns `None` and closes its descriptors. The coordinator
cannot hold an atomic view across the database and filesystem. It compares
the exact metadata bytes before and after the DB audit and rehashes dump and
mirror twice, but the caller must keep both private directories frozen during
the whole call. This is evidence collection, not a recovery verdict.

## Checks

- Frozen W58 scope, plan, preflight, DB audit, binding, storage public and
  API/domain/error/stage contract SHA-256 values matched the task file.
- `.venv/bin/python -m py_compile scripts/recovery/offline_restore_audit.py tests/integration/recovery/test_offline_restore_audit.py` — passed.
- `.venv/bin/python -m pytest tests/integration/recovery/test_offline_restore_audit.py -q -p no:cacheprovider` — **5 passed in 0.27s** on the final files. Cases cover order, stable facts, a failed first preflight blocking DB reads, symlink substitution, and post-audit mirror/metadata drift.
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **66 passed in 0.38s**. Pytest emitted five stale `/tmp/pytest-of-root/garbage-*` cleanup warnings from unrelated previous directories; results were unaffected.
- Task governance, direct trailing-whitespace scan, `git diff --check` and
  exact-path containment — passed. Full gate remains deferred under R-135.

## Limits and integration

The caller must provide an already restored, isolated database `Session`
inside a stable read-only transaction and keep the copy and mirror frozen.
This module opens no database connection or transaction, issues no SQL itself,
and makes no S3/network call or filesystem write. Its tests use a fake audit
response; the underlying SELECT-only DB audit has its own focused tests. A
real isolated PostgreSQL restore with actual reference rows, S3 readback,
source quiescence, safe retry and RPO remain to be demonstrated before W58
acceptance. A second full rehash increases work roughly with the dump and
mirror byte count; a production drill must measure that cost.

## Containment and handoff

Changed files are exactly:

- `scripts/recovery/offline_restore_audit.py`
- `tests/integration/recovery/test_offline_restore_audit.py`
- `docs/program/tasks/W58-INT-OFFLINE-RESTORE-AUDIT-01.md`
- `docs/program/W58-INT-OFFLINE-RESTORE-AUDIT-01.md`

No existing recovery/storage code, contract, migration, root dependency/lock
file, composition root, global style or Git ref was changed. Other tasks may
appear concurrently in the shared worktree; stage only these four paths. No
commit or push was made here. Rollback is deletion of these files.
