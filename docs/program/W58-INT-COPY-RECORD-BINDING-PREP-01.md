# W58-INT-COPY-RECORD-BINDING-PREP-01 — bind the offline mirror to the W54 copy record

**Base:** `f88c3bef90f8180ac7ade683bff2b2359d1e9b20`, 2026-10-15.
**Status:** pure preparation complete; W58 recovery acceptance pending.

## Result and changed files

`verify_copy_record_binding(record_data, inventory_data, sealed_data)` accepts
the existing W54 canonical `record.json` layout, its sorted `inventory.tsv`,
and the existing W58 `offline-object-copy-v1` seal. It refuses duplicate JSON
keys, unknown or incomplete artifact shapes, a waiver or partial copy,
malformed record identity and fingerprint fields, mismatched inventory
SHA-256/count/bytes, reordered or changed seal rows, and invalid object SHA-256
values. It creates no file and performs no DB, S3 or network operation.

- `scripts/recovery/copy_record_binding.py`
- `tests/integration/recovery/test_copy_record_binding.py`
- `docs/program/tasks/W58-INT-COPY-RECORD-BINDING-PREP-01.md`
- `docs/program/W58-INT-COPY-RECORD-BINDING-PREP-01.md`

## Checks

- `python3.12 -m py_compile scripts/recovery/copy_record_binding.py tests/integration/recovery/test_copy_record_binding.py` — passed.
- `git diff --check` — passed for tracked changes; these four new files are
  untracked until integration, so their whitespace was also scanned directly.
- `.venv/bin/python -m pytest tests/integration/recovery/test_copy_record_binding.py -q -p no:cacheprovider` — **12 passed in 0.04s** in a later CPU/RAM window (disk 1,929,965,568 bytes, available RAM 6,012,940,288 bytes, load1 7.62). The disk remained below the W54 restore floor.
- Full gate, DB/S3 restore and stand drill — deferred under R-135 and the
  separate W58 freeze.

## Contract and integration

No API, domain, migration, runtime or artifact format changed. The verifier is
pure and unconnected. The caller passes the exact raw bytes from the W54 copy
and the W58 mirror seal. The order for a future W58 recovery owner is:

1. Keep writers stopped and transfer the object payloads into a private mirror.
2. Run existing `object_copy.verify_manifest` against the mirror and seal.
3. Run `verify_copy_record_binding` against record, inventory and seal bytes.
4. Independently verify DB dump/restore, S3 readback, DB-to-Blob references and
   safe retry on isolated data before a backup or recovery claim.

The function checks that seal metadata and every row belong to the record's
inventory; it does not rehash mirrored payloads, verify the DB dump bytes or
prove the live bucket remained quiescent. Object keys are transport locators,
not Blob identities. ETag is retained as listing provenance, never treated as
a content checksum.

## Scope and rollback

Only the four paths above were added. No `contracts/**`, migration, existing
runtime/deployment script, root dependency/lock file, composition root, global
style, corpus artifact, Docker resource, Git ref or remote was modified.
Rollback is deletion of this unused pure module, its focused tests and two
documentation files. Keep the module inactive until the separately frozen W58
recovery integration.
