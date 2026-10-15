# Task W58-INT-OFFLINE-RESTORE-AUDIT-01 — coordinate offline recovery evidence

task_id: W58-INT-OFFLINE-RESTORE-AUDIT-01

## Outcome

One read-only function combines the existing W54/W58 local-byte preflight,
restored-DB Blob-reference audit and canonical object binding in a fixed
order. It returns facts only after a repeated local preflight and an exact
comparison of the copy metadata bytes; no recovery verdict is issued.

## Depends on

- `W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01` — completed dump and mirror rehash.
- `W58-INT-BLOB-REFERENCE-AUDIT-PREP-01` — completed restored-DB SELECT audit.
- `W58-INT-BLOB-OBJECT-BINDING-PREP-01` — completed exact sealed-object binding.
- `W58-INT-STORAGE-KEY-RESOLVER-01` — completed storage-owned key resolver.

## Frozen inputs

- base commit: `248179be684395170311c8c2fea604ddea165bb5`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- preflight SHA-256: `91d40a5dbb4d9108ff3ed5aa81d86e861dc57f0fca3d37fc3250270f975a7b76`;
- DB audit SHA-256: `6807a99488498699be48f76c0f80f1c487695c9d924ba833bada0e9830a20960`;
- object binding SHA-256: `37e705e36877ede907a7e362c601f4cfa3286830b6f9ff86c8cf8ff3c5e4c169`;
- storage public SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`;
- API/domain/error/analysis registry SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the four existing W58 entry points have the required facts, but
  preflight returns no open descriptors or metadata bytes to bind atomically.

### P-01 — existing entry points

- captured_at: 2026-10-15
- command: `rg -n '^def (verify_offline_restore_inputs|audit_blob_references|bind_available_blob_objects|canonical_object_key_for_recovery)\(' scripts/recovery/offline_restore_preflight.py scripts/recovery/blob_reference_audit.py scripts/recovery/blob_object_binding.py src/auditmanager/storage/public.py`
- captured_output:
  ```text
  src/auditmanager/storage/public.py:34:def canonical_object_key_for_recovery(blob_id: BlobId) -> str:
  scripts/recovery/blob_reference_audit.py:138:def audit_blob_references(session: Session) -> BlobReferenceAudit:
  scripts/recovery/offline_restore_preflight.py:81:def verify_offline_restore_inputs(copy_dir: Path, objects_root: Path) -> None:
  scripts/recovery/blob_object_binding.py:49:def bind_available_blob_objects(
  ```
- interpretation: the preflight returns `None`; a coordinator must reread
  record/inventory/seal under no-follow checks, repeat preflight after DB
  reads, compare the metadata bytes, and still rely on caller-owned freezing.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/offline_restore_audit.py`
- `tests/integration/recovery/test_offline_restore_audit.py`
- `docs/program/tasks/W58-INT-OFFLINE-RESTORE-AUDIT-01.md`
- `docs/program/W58-INT-OFFLINE-RESTORE-AUDIT-01.md`

## Forbidden hotspots

- existing `scripts/recovery/**`, `src/**`, `contracts/**`, `db/migrations/**`;
- root dependency/lock files, composition root, global styles;
- `docs/program/CURRENT_STATE.md`, Docker/S3/DB restore and Git refs.

## Non-goals

- No DB restore, S3/network access, transaction creation, filesystem write,
  recovery acceptance, source-bucket quiescence or RPO claim.
- This is a bounded evidence coordinator, not an atomic filesystem snapshot.

## Deliverables

- One read-only coordinator, focused order/refusal tests and a limitation report.

## Required tests

- `.venv/bin/python -m pytest tests/integration/recovery/test_offline_restore_audit.py -q -p no:cacheprovider`
- `.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider`
- `.venv/bin/python -m py_compile scripts/recovery/offline_restore_audit.py tests/integration/recovery/test_offline_restore_audit.py`
- task governance, `git diff --check` and exact-path containment.
- Full gate deferred under R-135.

## Integration contract

Caller supplies an isolated restored database `Session` already pinned to a
stable read-only transaction and owned private, frozen `copy_dir` and
`objects_root`. `collect_offline_restore_evidence` runs preflight before the
first DB SELECT, reads the three copy metadata files without following
symlinks, audits DB references and binds every available Blob through the
storage public resolver. It repeats the preflight and metadata read, refusing
if any metadata bytes changed, then returns only DB and object-binding facts.
All lower-level refusal types propagate. A later W58 owner must still prove
the real isolated restore, source quiescence and S3 readback.

## Failure/idempotency/security cases

- First preflight failure prevents DB reads. Missing, symlinked, public or
  changing metadata files refuse; post-audit drift prevents return. A DB or
  binding failure prevents return. Repeated calls write nothing. Caller must
  keep both directories frozen for the whole call; two scans cannot make an
  atomic snapshot of concurrently mutable storage.

## Rollback / feature flag

No application behavior changes or feature flag. Delete the four new files.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-OFFLINE-RESTORE-AUDIT-01.md`;
- known limits: no atomic snapshot or real recovery verdict;
- integration notes: keep unconnected until an isolated W58 drill.
