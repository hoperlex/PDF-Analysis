# W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01 — isolated target object restore

**Base:** published `origin/dev=c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
**Status:** unactivated code preparation, no real PostgreSQL/S3 drill.

## Result

`restore_sealed_objects` verifies the canonical W58 seal against every byte of
the private local mirror before touching the target. It paginates an isolated
target bucket listing, refuses extra keys and wrong existing sizes, then reads
and hashes each already present object. Missing objects are read from the
private mirror and sent with `PutObject` and `IfNoneMatch="*"`; each is then
read back through `GetObject`. A second exact listing, complete final byte
readback, third listing and fresh local mirror verification precede the
returned count, byte total and seal digest. ETag is not used as a checksum.

A partial upload can leave correct objects in the isolated bucket. A retry
checks those bytes and uploads only missing keys. It cannot silently overwrite
an existing object; wrong bytes or a concurrently created key refuse.

## Checks

- Frozen W58 scope/plan, prior object-copy/source-mirror/offline-preflight,
  storage public and API/domain/error/stage hashes matched the task file.
- `PYTHONPATH=src:. ../../../.venv/bin/python -m pytest tests/integration/recovery/test_target_object_restore.py -q -p no:cacheprovider` — **13 passed**.
- `PYTHONPATH=src:. ../../../.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **107 passed**.
- Python compile, task governance, `git diff --check` and exact-path containment
  are recorded in the final commit handoff.
- No Docker, PostgreSQL, MinIO, network, W54 paid call or full `make gate` was run.

## Limits and next integration

The operator must prove the bucket is disposable and isolated, keep it and the
private copy frozen, and run W54 record/dump/mirror preflight before this helper.
The helper cannot prove source-writer quiescence, endpoint identity or an
atomic S3 snapshot. Its injected S3-shaped client has fake-client evidence
only; actual MinIO/S3 `IfNoneMatch` behavior and pagination need a separately
owned service test. The real W58 drill must restore PostgreSQL from the same
copy into an isolated database, audit its Blob references, then call
`audit_target_blob_readback` against this target. Safe repeat, full reference
integrity, copy/restore time and RPO remain unproved until that drill.

## Containment and rollback

Changed files are exactly this report, its formal task,
`scripts/recovery/target_object_restore.py` and
`tests/integration/recovery/test_target_object_restore.py`. No contract,
migration, root dependency/lock file, composition root, global style, existing
recovery code, production stand or remote ref was changed. The module is not
wired into application behavior. Rollback removes these four files.
