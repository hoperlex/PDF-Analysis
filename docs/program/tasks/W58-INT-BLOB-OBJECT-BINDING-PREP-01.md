# Task W58-INT-BLOB-OBJECT-BINDING-PREP-01 — bind restored available Blobs to the offline object seal

task_id: W58-INT-BLOB-OBJECT-BINDING-PREP-01

## Outcome

A pure recovery helper refuses an available Blob from the restored DB unless
the W54 copy record, inventory and W58 seal agree and a storage-owned canonical
key resolves to exactly one sealed object with matching SHA-256 and size.

## Depends on

- `W58-INT-BLOB-REFERENCE-AUDIT-PREP-01` — completed SELECT-only DB fact audit.
- `W58-INT-COPY-RECORD-BINDING-PREP-01` — completed record/inventory/seal validation.
- `W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01` — completed local mirror-byte preflight.

## Frozen inputs

- base commit: `6b2e9ade4967b0c225e7e4be63b19a74e8cd2b3e`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- DB audit SHA-256: `6807a99488498699be48f76c0f80f1c487695c9d924ba833bada0e9830a20960`;
- object seal SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`;
- record binding SHA-256: `080a82775b469d09321cbc79d2d65d284f2aebb5e577e997572531e905e21bb6`;
- private storage layout SHA-256: `33cc2c9693d319088a14bcd913af26eec7ef89dd024352212ca0c7f359e907df`;
- migration head: `0022_findings_v2`; API/domain/error/analysis contracts unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the DB audit provides all available Blob facts; storage owns the
  canonical object layout privately, so recovery has no public key resolver.

### P-01 — DB facts and private key rule

- captured_at: 2026-10-15
- command: `rg -n '^class BlobReferenceAudit:|^    available_blobs:|^def canonical_key\(|^def bind_available_blob_objects\(' scripts/recovery/blob_reference_audit.py src/auditmanager/storage/_object_layout.py`
- captured_output:
  ```text
  scripts/recovery/blob_reference_audit.py:91:class BlobReferenceAudit:
  scripts/recovery/blob_reference_audit.py:93:    available_blobs: tuple[BlobFact, ...]
  src/auditmanager/storage/_object_layout.py:39:def canonical_key(blob_id: BlobId) -> str:
  ```
- interpretation: the rule exists, but the `_object_layout` module states it
  is adapter-only. A caller must inject a storage-owned resolver; this task
  cannot establish that trust by importing a private module or copying its
  fan-out algorithm.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/blob_object_binding.py`
- `tests/integration/recovery/test_blob_object_binding.py`
- `docs/program/tasks/W58-INT-BLOB-OBJECT-BINDING-PREP-01.md`
- `docs/program/W58-INT-BLOB-OBJECT-BINDING-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files;
- existing `scripts/recovery/**`, `src/**`, `infra/deploy/**`;
- composition root, global styles, Docker/S3/production DB, Git refs;
- `docs/program/CURRENT_STATE.md`.

## Non-goals

- No DB restore, S3 read, mirror-file rehash, actual storage resolver wiring,
  source quiescence proof or recovery acceptance.
- Extra mirrored objects outside the available DB set are not classified by
  this check; nonavailable Blob states need a separately frozen policy.

## Deliverables

- One pure binding function, focused tests and a limitation report.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_blob_object_binding.py -q -p no:cacheprovider`
- `.venv/bin/python -m py_compile scripts/recovery/blob_object_binding.py tests/integration/recovery/test_blob_object_binding.py`
- `git diff --check` and exact-path containment proof.
- Full gate and real DB/S3 drill deferred under R-135.

## Integration contract

After `verify_offline_restore_inputs` rehashes a frozen private mirror and
`audit_blob_references` reads an isolated restored DB in a stable read-only
transaction, call `bind_available_blob_objects(audit, record_data,
inventory_data, sealed_data, canonical_key_for=storage_owned_resolver)`.
The resolver must implement the same canonical rule as `S3BlobStore` and be
provided through a separately owned storage adapter slot. The helper accepts
only exact record/inventory/seal agreement and one unique key with matching
hash and size per available Blob. Returned keys are transport locators, never
Blob identity. Do not activate this helper as a recovery verdict without the
storage resolver and a real isolated DB+S3 drill.

## Failure/idempotency/security cases

- Missing object, changed seal, mismatched SHA-256 or size, duplicate Blob ID,
  repeated key, malformed fact or resolver refusal fail closed. Calls write
  nothing. The resolver is trusted input; arbitrary callbacks cannot be
  authenticated by this pure module.

## Rollback / feature flag

No application behavior change or feature flag. Delete the four added files.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-BLOB-OBJECT-BINDING-PREP-01.md`;
- known limits: no storage adapter resolver or real restore;
- integration notes: keep unconnected until a storage slot exposes a trusted resolver.
