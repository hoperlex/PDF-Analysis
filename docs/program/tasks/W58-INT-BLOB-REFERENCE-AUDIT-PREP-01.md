# Task W58-INT-BLOB-REFERENCE-AUDIT-PREP-01 — audit restored DB Blob references

task_id: W58-INT-BLOB-REFERENCE-AUDIT-PREP-01

## Outcome

A SELECT-only, caller-transaction audit refuses a restored `0022_findings_v2`
database when a published/confirmed Blob reference is broken, a durable
artifact intent lacks its required Blob row, or a new Blob-reference column
appears outside its explicit source registry. Pending/poisoned/rejected
custody admissions are outbox intents and may precede or lack a Blob row.
The audit returns available Blob facts for a later object-mirror comparison.
It does not qualify the DB+S3 recovery by itself.

## Depends on

- `W54-STAND-COPY-01` — completed one-off DB dump and object inventory format.
- `W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01` — completed local input preflight.

## Frozen inputs

- base commit: `6a1d915c76e9de3d14c6c81967ddb38d91f90242`
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migrations `0002`, `0014`, `0018` SHA-256: `4229cfb7b3cea01c9f211275a656cc9a2c4a71711b55dec1cf2bbd71c44b069c`, `8d2a912407f418ca8843671a22cc0d2881229e23dd1c2c02acb5929f48bc7983`, `7b9ac6798011639c666e53d908a7c5f13199b6993b4b812388b270153498e4c5`;
- storage object layout SHA-256: `33cc2c9693d319088a14bcd913af26eec7ef89dd024352212ca0c7f359e907df`;
- migration head: `0022_findings_v2`; API/domain/error catalogs unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the restored schema has four DB-side Blob-reference columns and no
  persisted export Blob table. The latter is read-time CSV/XLSX projection.

### P-01 — migration-defined Blob-reference columns

- captured_at: 2026-10-15
- command: `rg -n 'blob_id[[:space:]]+text' db/migrations/versions`
- captured_output:
  ```text
  db/migrations/versions/20261012_0018_norm_custody.py:210:            blob_id             text NOT NULL,
  db/migrations/versions/20261012_0018_norm_custody.py:275:            blob_id     text NOT NULL REFERENCES blob (blob_id),
  db/migrations/versions/20260910_0002_pc01_schema.py:536:            blob_id     text PRIMARY KEY,
  db/migrations/versions/20260910_0002_pc01_schema.py:582:            blob_id     text NOT NULL REFERENCES blob (blob_id),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:340:            blob_id       text NOT NULL REFERENCES blob (blob_id),
  ```
- interpretation: `blob` is metadata identity; the other four rows are
  `input_manifest_entry`, `analysis_artifact_publication`,
  `norm_custody_admission` and `norm_custody_binding`. This text search
  finds columns by declaration form; it cannot rule out references embedded
  in JSON or text. Runtime catalog enumeration must still refuse a newer or
  changed set of declared reference columns.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/blob_reference_audit.py`
- `tests/integration/recovery/test_blob_reference_audit.py`
- `docs/program/tasks/W58-INT-BLOB-REFERENCE-AUDIT-PREP-01.md`
- `docs/program/W58-INT-BLOB-REFERENCE-AUDIT-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files;
- existing `scripts/recovery/**`, `src/**`, `infra/deploy/**`;
- composition root, global styles, Docker/S3/production DB, Git refs;
- W57a task/code paths and `docs/program/CURRENT_STATE.md`.

## Non-goals

- No DB restore, S3 access, mirrored-object key mapping, object-byte validation,
  source quiescence or production recovery acceptance.
- No claim about Blob IDs embedded inside free-form JSON, audit-event payloads
  or exported files; this audits schema-declared Blob reference columns.

## Deliverables

- One SELECT-only DB audit, focused fake-session tests and limitation report.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_reference_audit.py -q -p no:cacheprovider`
- `.venv/bin/python -m py_compile scripts/recovery/blob_reference_audit.py tests/integration/recovery/test_blob_reference_audit.py`
- `git diff --check` and exact-path containment proof.
- Full gate and real DB/S3 drill deferred under R-135.

## Integration contract

After isolated restore, call `audit_blob_references(session)` inside the
caller's pinned, read-only transaction at migration head `0022_findings_v2`.
The audit executes only SELECT statements, enumerates every table/column
named as a Blob reference or constrained by a Blob FK, compares that set to
four pinned sources, checks all rows and returns available Blob facts. Any
unknown source or broken reference raises `BlobReferenceAuditRefused`.
The W58 integration owner must still join returned Blob IDs to canonical
object keys using an owned storage adapter contract and verify mirrored bytes.

## Failure/idempotency/security cases

- Unknown/missing source, wrong migration, missing required Blob row, active
  reference to nonavailable Blob, mismatched manifest/custody facts, unknown
  state and malformed available Blob metadata refuse. Repeated audits write
  nothing. `prepared`/`abandoned` analysis intents need a Blob metadata row;
  only `bound` artifacts need its `available` state.
- Catalog scope is non-system schemas; an unrecognized Blob FK or `*_blob_id`
  column refuses even when empty. SQL names are fixed constants, never data.

## Rollback / feature flag

No application behavior changes. Delete the four added files to roll back.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-BLOB-REFERENCE-AUDIT-PREP-01.md`;
- known limits: no object-key mapping or actual restore;
- integration notes: keep unconnected until the W58 recovery integration.
