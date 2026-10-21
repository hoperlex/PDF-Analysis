# W58-INT-BLOB-REFERENCE-AUDIT-PREP-01 — restored DB Blob references

**Frozen base:** `6a1d915c76e9de3d14c6c81967ddb38d91f90242` (2026-10-15).
**Status:** SELECT-only code preparation; no restored DB or S3 was used.

## Result

`scripts/recovery/blob_reference_audit.py` exposes
`audit_blob_references(session)`. Inside the caller's stable, read-only
transaction it first requires migration head `0022_findings_v2`, then reads
the non-system SQL catalog for Blob-ID columns and foreign keys to `blob`.
Its exact source registry is:

| Source | Row meaning | Required availability |
| --- | --- | --- |
| `input_manifest_entry.blob_id` | Published version input | `available`, exact SHA-256/size/media type |
| `analysis_artifact_publication.blob_id` | Durable analysis intent or bound artifact | `bound` requires `available`; `prepared`/`abandoned` require a Blob row |
| `norm_custody_admission.blob_id` | Normative custody outbox intent | `confirmed` requires `available` with exact declared facts; pending/poisoned/rejected may lack a Blob row |
| `norm_custody_binding.blob_id` | Published normative binding | `available` plus matching confirmed admission |

`blob.blob_id` is the metadata identity, not a reference. For every Blob row,
the audit checks the ID shape, valid metadata and content-derived identity
whenever SHA-256 and size exist. All `available` rows must have full metadata.
The result returns every available Blob's ID, SHA-256, size and media type,
including rows without a current reference, for a later mirror comparison.
An unknown or missing declared source refuses before row reads. The query
also catches an unfamiliar Blob FK whose column is not named `blob_id`.

The current CSV and XLSX exports are generated from finding/version reads;
there is no persisted export Blob table in migration head `0022`. Exported
files, audit-event JSON and other free-form JSON/text can carry strings that
look like Blob IDs, but the schema does not declare them as Blob references.
This audit makes no claim about those embedded strings.

## Checks

- Frozen scope, plan, migrations and storage-layout SHA-256 values matched the
  task file. Exact base `6a1d915c` was recorded before implementation.
- `.venv/bin/python -m py_compile scripts/recovery/blob_reference_audit.py tests/integration/recovery/test_blob_reference_audit.py` — passed.
- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_reference_audit.py -q -p no:cacheprovider` — **16 passed in 0.51s**. Cases cover good data, exact schema, unknown/missing source, wrong head, missing/mismatched published references, allowed unsettled intents, identity and unknown state.
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — **52 passed in 0.59s**. Pytest emitted five stale `/tmp/pytest-of-root/garbage-*` cleanup warnings from unrelated previous test directories; test results were unaffected.
- `git diff --check` and a direct whitespace scan of the added files — passed. Untracked files are invisible to plain `git diff`, so the direct scan was needed.
- A real PostgreSQL query, SQL parser check and DB+S3 recovery drill were not run. `pglast` is absent in this worktree's venv, and the task is bounded to fake sessions. Full gate remains deferred under R-135.

## Limits and integration

This is a **DB-side** check. It does not map `blob_id` to an object key or prove
that a mirrored payload exists. The canonical layout is private to
`auditmanager.storage._object_layout`; the public BlobStore accepts a Blob ID,
not a mirror key. W58 still needs a separately owned adapter/contract to bind
each returned Blob fact to its exact canonical object key, then a real isolated
restore, mirror readback, repeatability and writer-quiescence proof. Matching
objects by digest alone would not prove that they occupy the canonical keys.

The caller must supply an isolated restored DB at the pinned head and hold a
stable read-only transaction for the whole audit. The tool issues only SELECT
queries and writes no marker. Unknown schema, broken row or SQL failure gives
no acceptance result. It materializes Blob and source rows in memory, so a
production-size recovery drill must measure that footprint before activation.
It is intentionally unconnected to production/runtime.

## Containment and handoff

Changed files are exactly:

- `scripts/recovery/blob_reference_audit.py`
- `tests/integration/recovery/test_blob_reference_audit.py`
- `docs/program/tasks/W58-INT-BLOB-REFERENCE-AUDIT-PREP-01.md`
- `docs/program/W58-INT-BLOB-REFERENCE-AUDIT-PREP-01.md`

No contract, migration, existing recovery/deploy script, source module,
composition root, root dependency/lock file, global style or Git ref was
changed by this task. The base-to-current `git diff` includes an independent
W57a commit `ecf5f56f` by the integrator; use the exact four owned paths above
for containment, rather than attributing that unrelated commit to this task.
No commit or push was made here. Rollback is deletion of the four files.
