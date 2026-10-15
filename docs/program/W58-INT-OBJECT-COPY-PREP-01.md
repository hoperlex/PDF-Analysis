# W58-INT-OBJECT-COPY-PREP-01 — offline object-copy seal

**Base:** `5a51721a745a7bfc5c85cc4594625fa53cbce523`, 2026-10-15.
**Status:** bounded preparation complete; W58 recovery code and backup acceptance remain open.

## Result and changed files

The existing W54 one-off copy fetches `record.json`, `db.dump` and
`inventory.tsv`; it does not fetch S3 payload bytes. `scripts/recovery/object_copy.py`
checks a separately mirrored, objects-only directory against every sorted
`key<TAB>size<TAB>etag` inventory row. It refuses missing and extra files,
incorrect sizes, symlinks, unsafe keys and ambiguous rows. It streams a
SHA-256 for each local payload into a canonical `offline-object-copy-v1`
manifest. `verify` rehashes the mirror and compares the entire seal. Sealing
the same bytes again is a no-op; a different or concurrently created manifest
is never overwritten. Both copy directory and object root must be owned by
the invoking user and private; the manifest is mode 0600 beside the inventory.

- `scripts/recovery/object_copy.py`
- `tests/integration/recovery/test_object_copy.py`
- `docs/program/tasks/W58-INT-OBJECT-COPY-PREP-01.md`
- `docs/program/W58-INT-OBJECT-COPY-PREP-01.md`

## Checks

- `../../../.venv/bin/python -m pytest tests/integration/recovery/test_object_copy.py -q -p no:cacheprovider` — **13 passed**. Pytest emitted five unrelated cleanup warnings for stale `/tmp/pytest-of-root/garbage-*` directories.
- `../../../.venv/bin/python -m py_compile scripts/recovery/object_copy.py` — **passed**.
- `git diff --check` and direct trailing-whitespace/newline scan over the four
  owned new files — **passed**.
- `governed_task_findings()` for this task — **empty**. The complete
  `test_wave_governance.py` file had 15 passes and one failure from eight
  other task documents in the shared tree; this task is not among them.
- Mutation probe: replacing the one `if set(actual) != expected_keys:`
  guard with `if False:` made a mirror containing an extra object pass;
  the original refused it. The extra-object test is load-bearing.
- Full gate and live DB/S3 drill — **deferred** by R-135 and the absent W58 production freeze.

## Contract and integration

No API, domain, event, migration or runtime contract changed. The new offline
artifact is canonical JSON with `format`, `inventory_sha256`, `count`, `bytes`
and sorted `objects` entries (`key`, `size_bytes`, `etag`, `sha256`). ETag is
retained as inventory provenance; SHA-256 is computed from the local bytes.

After the W54 copy sequence and local DB restore test, a future W58 transport
must mirror every S3 object to a private objects-only directory, with the
writers stopped. It may run:

```text
python scripts/recovery/object_copy.py seal <copy>/inventory.tsv <objects-root> <copy>/objects.json
python scripts/recovery/object_copy.py verify <copy>/inventory.tsv <objects-root> <copy>/objects.json
```

The mirror and inventory must remain frozen together from sealing through the
restore. Before a recovery claim, W58 still needs authenticated object transfer,
S3 readback verification, binding of this seal to the W54 copy record, a
DB-to-Blob reference check, full isolated restore and safe retry evidence.
This tool performs none of those operations and makes no production claim.

## Risks and containment

Object keys are used only as transport locators. The tool never treats a path
as a Blob identity. It does not touch a real DB, bucket or working stand.
Its scanner uses no-follow opens and regular-file checks; the source mirror
must not be mutated concurrently. The CLI does not make that external state
immutable.

The four changed paths above are the task's complete allowlist. `git status`
also shows other agents' concurrent corpus, section and comparison edits;
this task did not modify those paths. No `contracts/**`, migrations, storage,
deployment, composition, root dependencies, refs or `origin/main` were touched.
