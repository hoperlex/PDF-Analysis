# Task W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01 — restore a sealed mirror to an isolated target

task_id: W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01

## Outcome

An unactivated W58 helper copies every object in a verified private mirror to
an operator-owned isolated S3 bucket, refuses foreign or mismatched existing
objects, supports retry after a partial transfer, and fully reads target bytes
and exact key sets before returning facts. Focused fake-client tests prove this.

## Depends on

- `W58-INT-OBJECT-COPY-PREP-01` — completed canonical inventory and local byte seal.
- `W58-INT-SOURCE-OBJECT-MIRROR-PREP-01` — completed source GetObject-to-private-mirror helper.
- `W58-INT-OFFLINE-RESTORE-PREFLIGHT-PREP-01` — completed dump/record/mirror preflight for the later operator.

## Frozen inputs

- base commit: `c157ee0d4601f2bf81c68708ebf556b95b87acd5`
- publication readback at dispatch: `origin/dev` matched this base;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W58 object-copy SHA-256: `2e66ca7b30672d7118c037a35ab2ac71251082d6a8ed0602327e9e1f44195884`;
- W58 source mirror SHA-256: `da1098696b2833afc91cf200172a4bb6d522bbd75e3d35e722d9c52a239db7d8`;
- W58 offline preflight SHA-256: `91d40a5dbb4d9108ff3ed5aa81d86e861dc57f0fca3d37fc3250270f975a7b76`;
- storage public SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`;
- API/domain/error/analysis registry SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the existing W58 helpers verify a local mirror and read target Blobs,
  but no helper uploads all sealed mirror objects to a target bucket.

### P-01 — existing source and target boundaries

- captured_at: 2026-10-16
- command: `rg -n '^def (verify_manifest|mirror_source_objects|audit_target_blob_readback)\(' scripts/recovery/object_copy.py scripts/recovery/source_object_mirror.py scripts/recovery/target_blob_readback.py`
- captured_output:
  ```text
  scripts/recovery/target_blob_readback.py:66:def audit_target_blob_readback(
  scripts/recovery/source_object_mirror.py:193:def mirror_source_objects(
  scripts/recovery/object_copy.py:150:def verify_manifest(inventory_data: bytes, objects_root: Path, sealed_bytes: bytes) -> None:
  ```
- interpretation: local verification and target Blob readback exist; this
  output does not prove an isolated target upload or a complete recovery drill.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/target_object_restore.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `docs/program/tasks/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`
- `docs/program/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`

## Forbidden hotspots

- existing `scripts/recovery/**`, `src/**`, `contracts/**`, `db/migrations/**`;
- `infra/**`, root dependency/lock files, composition root, global styles;
- `docs/program/CURRENT_STATE.md`, production stand and configuration, Git refs and tags.

## Non-goals

- No PostgreSQL restore, source writer quiescence, live stand copy, bucket
  creation, production endpoint authentication, DB-to-Blob audit, RPO or
  recovery-acceptance claim.
- No real S3 request or heavy service start in this task. The caller must
  establish that the target bucket is disposable and isolated.

## Deliverables

- A target copy/readback helper with an injected S3-shaped client, fake-client
  refusal and retry tests, and this task's result report.

## Required tests

- `PYTHONPATH=src:. ../../../.venv/bin/python -m pytest tests/integration/recovery/test_target_object_restore.py -q -p no:cacheprovider` — focused tests pass.
- `PYTHONPATH=src:. ../../../.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — recovery suite passes.
- Python compile, task governance, `git diff --check` and four-path containment pass.
- Real PostgreSQL/S3 drill and full gate deferred under R-135 and host lane ownership.

## Integration contract

The future operator first verifies the W54 record, dump and sealed mirror with
`verify_offline_restore_inputs`. While holding a private frozen mirror and an
isolated disposable target bucket, it calls
`restore_sealed_objects(inventory_data, sealed_data, objects_root,
target_bucket, client)`. The helper rehashes the whole mirror, lists the target
with pagination, refuses any foreign or mismatched existing key, uploads only
missing keys with conditional `IfNoneMatch="*"`, and reads complete target
payloads. Two exact final listings bracket final byte readback. It rehashes
the mirror again and returns count, bytes and seal digest only on agreement.
The later W58 drill must restore PostgreSQL separately, audit restored Blob
references and use `audit_target_blob_readback` against the same isolated
target; no DB/S3 dual write occurs in this helper.

## Failure/idempotency/security cases

- Invalid seal, changed mirror, public/symlink local path, foreign target key,
  wrong existing bytes or size, malformed or cyclic listing, failed conditional
  upload, short/long/non-byte target stream and changed target inventory refuse.
- A failed run may leave a verified target prefix. Retry reads that prefix
  before uploading missing keys; it never overwrites an existing object.
- ETag is only source inventory metadata, never the payload checksum. The
  caller owns endpoint isolation and absence of concurrent target writers;
  two listings cannot make an atomic S3 snapshot.

## Rollback / feature flag

No application behavior change or feature flag. Remove the four added files.

## Handoff

- changed files: the four allowed paths;
- commands/results: `docs/program/W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`;
- known limits: no real target or DB restore yet;
- integration notes: keep unconnected until an isolated W58 drill owner runs it.
