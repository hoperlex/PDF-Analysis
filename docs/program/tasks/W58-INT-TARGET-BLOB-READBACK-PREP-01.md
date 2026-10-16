# Task W58-INT-TARGET-BLOB-READBACK-PREP-01 — verify restored target Blob bytes

task_id: W58-INT-TARGET-BLOB-READBACK-PREP-01

## Outcome

A read-only recovery helper refuses the restored target unless every available
DB Blob in the W58 offline evidence can be fully streamed from the target
BlobStore with matching SHA-256 and size. It returns deterministic aggregate
facts only after all streams finish.

## Depends on

- `W58-INT-OFFLINE-RESTORE-AUDIT-01` — completed DB and sealed-mirror evidence coordinator.
- `W58-INT-STORAGE-KEY-RESOLVER-01` — completed public canonical recovery key resolver.

## Frozen inputs

- base commit: `b01f9bdee80e5b05350bcba6f55f980364372517`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- offline evidence coordinator SHA-256: `91595bcde9460ef019179fe1e8cf72318d3eeef8c1b5eee8bae4ebfdc63bf8b1`;
- DB audit SHA-256: `6807a99488498699be48f76c0f80f1c487695c9d924ba833bada0e9830a20960`;
- object binding SHA-256: `37e705e36877ede907a7e362c601f4cfa3286830b6f9ff86c8cf8ff3c5e4c169`;
- storage public and port SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`, `82a2063384fbc683aafdadf144152cddb3bd3f2aabf7cb7f089846be9764ff44`;
- API/domain/error/analysis registry SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed coordinator proves DB-to-offline-mirror bindings,
  while the public storage port can stream a complete target Blob by opaque ID.

### P-01 — completed evidence and public streaming boundary

- captured_at: 2026-10-16
- command: `rg -n '^def (collect_offline_restore_evidence|canonical_object_key_for_recovery)\(|^    def open_stream\(' scripts/recovery/offline_restore_audit.py src/auditmanager/storage/public.py src/auditmanager/storage/port.py`
- captured_output:
  ```text
  src/auditmanager/storage/port.py:124:    def open_stream(
  src/auditmanager/storage/public.py:34:def canonical_object_key_for_recovery(blob_id: BlobId) -> str:
  scripts/recovery/offline_restore_audit.py:88:def collect_offline_restore_evidence(
  ```
- interpretation: these entry points exist and no target-bucket byte readback
  is part of the completed offline coordinator. This says nothing about a
  running target bucket or a completed restore.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/target_blob_readback.py`
- `tests/integration/recovery/test_target_blob_readback.py`
- `docs/program/tasks/W58-INT-TARGET-BLOB-READBACK-PREP-01.md`
- `docs/program/W58-INT-TARGET-BLOB-READBACK-PREP-01.md`

## Forbidden hotspots

- existing `scripts/recovery/**`, `src/**`, `contracts/**`, `db/migrations/**`;
- root dependency/lock files, composition root, global styles;
- `docs/program/CURRENT_STATE.md`, Docker, real DB/S3, deployment and Git refs.

## Non-goals

- No real restore, source-bucket quiescence, target bucket creation, Blob write,
  DB transaction, full S3 inventory, RPO claim or recovery acceptance.
- Target extra objects and nonavailable DB Blob states need separate policies.

## Deliverables

- One stream-and-hash target readback function, refusal tests and report.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery/test_target_blob_readback.py -q -p no:cacheprovider`
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider`
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m py_compile scripts/recovery/target_blob_readback.py tests/integration/recovery/test_target_blob_readback.py`
- task governance, `git diff --check` and exact-path containment. Full gate deferred under R-135.

## Integration contract

After `collect_offline_restore_evidence` completes against an isolated,
read-only restored DB and a frozen private copy, the caller supplies a
read-only target `BlobStore` bound to an isolated restored bucket.
`audit_target_blob_readback(evidence, target)` validates the entire available
DB-to-mirror binding before target I/O, then fully streams every available
Blob by opaque ID. It hashes delivered bytes itself and returns count, total
bytes and a deterministic digest of checked `(blob_id,size,sha256)` facts only
after all streams finish. Typed storage failures propagate; local mismatches
raise `TargetBlobReadbackRefused`. The target and copy must remain frozen
throughout the call.

## Failure/idempotency/security cases

- Missing/duplicate/forged bindings refuse before target I/O. Missing target
  Blob, changed bytes, short/long body or invalid chunks prevent a result.
- Streams close on local refusal. Repeat calls are read-only and deterministic
  for unchanged inputs; the helper cannot prevent concurrent target mutation.

## Rollback / feature flag

No application behavior changes or feature flag. Delete the four new files.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-TARGET-BLOB-READBACK-PREP-01.md`;
- known limits: no real restore or source/target atomicity;
- integration notes: keep unconnected until an isolated W58 drill.
