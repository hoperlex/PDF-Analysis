# W58-INT-STORAGE-KEY-RESOLVER-01 — storage-owned recovery key resolver

**Frozen base:** `8dac96f7c36fad3e3855ab6abeb180a2a503fd9a` (2026-10-15).
**Status:** offline W58 integration seam ready; no real restore or S3 readback.

## Result

`auditmanager.storage.public.canonical_object_key_for_recovery` now accepts
an opaque Blob ID, validates it with the existing storage parser and delegates
to the same `_object_layout.canonical_key` function used by `S3BlobStore`.
It provides the required storage-owned callback for the W58 pure
`bind_available_blob_objects` bridge. No key algorithm was duplicated and no
private layout or S3 adapter implementation was changed.

The focused test passes this public resolver into the bridge and compares its
result for two content-derived Blob IDs with independently constructed sealed
inventory keys. It also checks that a malformed ID refuses. Product code
continues to use opaque Blob IDs; this resolver is explicitly for isolated
recovery verification and must not be used in a router or business response.

## Checks

- Frozen W58 scope, code-first plan, storage public/layout, W58 bridge and
  API/domain/error/stage contract SHA-256 values matched the task file.
- `.venv/bin/python -m py_compile src/auditmanager/storage/public.py tests/integration/recovery/test_blob_object_binding.py` — passed.
- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_object_binding.py -q -p no:cacheprovider` — **9 passed in 0.32s**.
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **61 passed in 0.44s**.
- `.venv/bin/python -m pytest tests/contract/architecture/test_alr05_boundaries.py -q -p no:cacheprovider` — **2 passed in 0.68s**.
- All pytest runs emitted five stale `/tmp/pytest-of-root/garbage-*` cleanup
  warnings from unrelated earlier test directories; results were unaffected.
- Task governance, `git diff --check`, direct trailing-whitespace scan and
  exact-path containment — passed. Full gate is deferred under R-135.

## Limits and integration

The resolver only maps a validated ID to the adapter's key. It does not prove
the object exists, hash bytes, read S3 or restore a DB. Use it only after the
W58 local dump/mirror preflight and restored-DB Blob reference audit, then
perform the real isolated DB+S3 recovery drill and source-quiescence proof.

Two older storage docstrings say no public key accessor exists and that only
`s3.py` imports `_object_layout`. This narrowly scoped recovery function is an
intentional exception. Those docstrings are outside this task's allowlist and
need an owned documentation correction before broad recovery activation.

## Containment and handoff

Changed files are exactly:

- `src/auditmanager/storage/public.py`
- `tests/integration/recovery/test_blob_object_binding.py`
- `docs/program/tasks/W58-INT-STORAGE-KEY-RESOLVER-01.md`
- `docs/program/W58-INT-STORAGE-KEY-RESOLVER-01.md`

No contract, migration, private layout, S3 implementation, existing recovery
script, root dependency/lock file, composition root, global style or Git ref
was changed. Concurrent tasks may appear in the shared worktree; stage only
these four owned paths. No commit or push was made here. Rollback is removal
of the new function/export, test and the two task documents.
