# W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01 — offline restore-input preflight

**Base:** `62a9e23dd44cdd7d9373e69413ce6ad27e508d3d`, 2026-10-15.
**Status:** code preparation complete; no recovery or backup qualification.

## Result

`verify_offline_restore_inputs(copy_dir, objects_root)` reads only local
inputs. It requires an owned private copy directory named for the W54 record
stamp and an owned private object-mirror root. It opens canonical
`record.json`, `db.dump`, `inventory.tsv` and `objects.json` as regular files
without following their leaf symlinks. Existing W58 code checks exact
record/inventory/seal binding and rehashes every mirrored payload. The new
check streams `db.dump`, matching its byte count and SHA-256 to the W54 record,
then checks the copy files and both directory identities and metadata again.
The CLI prints only a local-input result and writes no acceptance marker.

Changed files:

- `scripts/recovery/offline_restore_preflight.py`
- `tests/integration/recovery/test_offline_restore_preflight.py`
- `docs/program/tasks/W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01.md`
- `docs/program/W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01.md`

## Checks

- Frozen SHA-256 values for API, domain identifiers, error catalog, analysis
  registry, W54 copy/pull scripts and W58 helper modules matched the task.
- `python3.12 -m py_compile scripts/recovery/offline_restore_preflight.py tests/integration/recovery/test_offline_restore_preflight.py` — passed.
- `.venv/bin/python -m pytest tests/integration/recovery/test_offline_restore_preflight.py -q -p no:cacheprovider` — **11 passed in 0.21s**. Pytest also warned that it could not remove five stale `/tmp/pytest-of-root/garbage-*` directories from unrelated prior tests; these did not affect the result.
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **36 passed in 0.17s**; the same stale `/tmp` cleanup warnings appeared.
- `git diff --check` and direct trailing-whitespace scan of the new files — passed.
- Full gate, live S3 readback, PostgreSQL restore and reference check — deferred
  under R-135 and the later W58 recovery freeze.

## Integration and limits

Call the new preflight immediately before an **isolated** restore, while the
copy and mirror are frozen. A successful call proves local bytes agree at the
time of this check. It does not prove source-bucket quiescence, backup
freshness, S3 readback, a successful DB restore, Blob references in the
restored DB, safe retry or RPO. No actual database or S3 operation was run.
Large inventory and seal inputs are bounded at 256 MiB and 512 MiB, and the
record at 1 MiB; larger copies need a separately reviewed streaming format.
The mirror rehash is implemented by the existing `object_copy` scanner.

No contract, migration, API, existing recovery/deploy script, composition root,
root dependency/lock file, global style, corpus artifact or Git ref changed.
The four added files are isolated and uncommitted for the integrator. Rollback
is deletion of those four files; no feature flag is needed because nothing
calls this preflight in runtime.
