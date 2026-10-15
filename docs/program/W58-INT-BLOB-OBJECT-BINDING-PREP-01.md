# W58-INT-BLOB-OBJECT-BINDING-PREP-01 — available Blob to sealed object binding

**Frozen base:** `6b2e9ade4967b0c225e7e4be63b19a74e8cd2b3e` (2026-10-15).
**Status:** pure recovery preparation; no storage resolver or actual restore was activated.

## Result

`scripts/recovery/blob_object_binding.py` exposes
`bind_available_blob_objects(audit, record_data, inventory_data, sealed_data,
canonical_key_for=...)`. It first applies the existing W54 record/inventory/W58
seal verifier. It then requires every available DB Blob fact to have a valid
content-derived ID and one unique canonical key supplied by a storage-owned
resolver. The sealed object at that key must have the exact SHA-256 and byte
count recorded in the restored DB. Missing, repeated or mismatched bindings
refuse; the returned key is only a transport locator.

The storage layout in `src/auditmanager/storage/_object_layout.py` is private
and says it is imported only by the S3 adapter. `storage.public` exposes Blob
IDs and facts but no canonical-key resolver. This slice does not import that
private module or copy its fan-out algorithm. A later storage integration slot
must provide and own the resolver before the bridge can be activated. The pure
helper cannot authenticate an arbitrary caller-supplied callback, so its
success alone is not a DB+S3 recovery verdict.

## Checks

- Frozen scope, code-first plan, DB audit, object-seal, record-binding and
  private layout SHA-256 values matched the task file.
- `.venv/bin/python -m py_compile scripts/recovery/blob_object_binding.py tests/integration/recovery/test_blob_object_binding.py` — passed.
- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_object_binding.py -q -p no:cacheprovider` — **8 passed**. Tests cover two complete bindings, empty available set, missing object, SHA-256 and size mismatch, duplicate identity/key, malformed facts and noncanonical seal.
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **60 passed in 0.46s**. Pytest emitted five stale `/tmp/pytest-of-root/garbage-*` cleanup warnings from unrelated previous directories; results were unaffected.
- `git diff --check`, direct trailing-whitespace scan of the four new paths,
  task governance and exact-path containment — passed.
- Full gate and real DB/S3 recovery drill remain deferred under R-135.

## Limits and integration

Call `verify_offline_restore_inputs` immediately before the isolated restore
to rehash local dump and mirror bytes. Run `audit_blob_references` inside the
restored DB's stable read-only transaction. Then pass its result and the same
W54/W58 record, inventory and seal to this binding helper with a trusted
storage-owned canonical-key resolver. Keep the local inputs frozen across all
steps; any change needs a fresh preflight. This helper itself reads no DB,
filesystem or S3 and writes no marker.

The comparison covers every `available` Blob row, including rows without a
current published reference. It does not classify extra mirrored objects or
nonavailable Blob states. The existing DB audit covers declared Blob-reference
columns but not identifiers embedded in free-form JSON. A real isolated
restore, source-bucket quiescence, S3 readback, repeatability and recovery
acceptance remain open.

## Containment and handoff

Changed files are exactly:

- `scripts/recovery/blob_object_binding.py`
- `tests/integration/recovery/test_blob_object_binding.py`
- `docs/program/tasks/W58-INT-BLOB-OBJECT-BINDING-PREP-01.md`
- `docs/program/W58-INT-BLOB-OBJECT-BINDING-PREP-01.md`

No contract, migration, existing recovery script, source module, composition
root, root dependency/lock file, global style or Git ref was changed by this
task. Concurrent tasks may appear in the shared worktree; stage only the four
paths above. No commit or push was made here. Rollback is deletion of these
four files.
