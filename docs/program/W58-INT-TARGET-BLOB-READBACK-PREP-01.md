# W58-INT-TARGET-BLOB-READBACK-PREP-01 — target Blob byte readback

**Frozen base:** `b01f9bdee80e5b05350bcba6f55f980364372517` (2026-10-16).
**Status:** isolated read-only preparation; no real DB/S3 restore or target readback executed.

## Result

`scripts/recovery/target_blob_readback.py` adds
`audit_target_blob_readback(evidence, target)`. It accepts the completed
offline restore evidence and a caller-owned target `BlobStore`. Before target
I/O it refuses duplicate, absent or inconsistent DB-to-mirror bindings and
checks canonical keys via the storage public boundary. It then opens each
target object by opaque Blob ID, reads the whole stream and independently
checks size and SHA-256. It returns count, bytes and a deterministic digest
of checked Blob facts only after every stream completes. The helper writes no
data and closes streams on local refusal.

The real storage port already checks the same declarations inside
`open_stream`; independent hashing ensures the recovery check itself cannot
pass on a metadata-only or broken fake adapter. Keys remain transport
locators in the offline evidence, never Blob identities in the target call.

## Checks

- Frozen W58 scope, code-first plan, coordinator, DB audit, binder, storage
  public/port and API/domain/error/stage hashes matched the task file;
  migration head is `0022_findings_v2`.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery/test_target_blob_readback.py -q -p no:cacheprovider` — **10 passed**. Cases include empty body, repeat, tamper, short/long body, missing target, forged or incomplete evidence and no partial result.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **76 passed**.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m py_compile scripts/recovery/target_blob_readback.py tests/integration/recovery/test_target_blob_readback.py` — passed.
- Direct task governance `governance_findings(...)` — `[]` for this new task.
  The whole governance test file is **15 passed / 1 failed** because ten
  existing W54/W56A/W59 task documents have findings; none is this task.
  Exact-path containment and `git diff --check` passed. Full gate remains
  deferred under R-135.

## Limits and integration

The caller must hold an isolated read-only restored DB transaction while
collecting the upstream evidence, freeze the private copy and target bucket,
and provide a target `BlobStore` bound to that isolated bucket. This helper
does not create a restore, authenticate the source bucket, enumerate extra
target objects, decide what to do with nonavailable Blob rows, prove source
quiescence or establish an RPO. A real isolated DB+S3 drill remains required
for W58 acceptance.

## Containment and handoff

Changed files are exactly:

- `scripts/recovery/target_blob_readback.py`
- `tests/integration/recovery/test_target_blob_readback.py`
- `docs/program/tasks/W58-INT-TARGET-BLOB-READBACK-PREP-01.md`
- `docs/program/W58-INT-TARGET-BLOB-READBACK-PREP-01.md`

No existing recovery/storage module, shared contract, migration, root
dependency/lock file, composition root, global style or remote ref changed.
Rollback is deletion of these four files. Integrate after the completed W58
offline evidence coordinator and keep unactivated until an isolated drill.
