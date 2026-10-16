# Task W58-INT-TARGET-DIGEST-METADATA-01 — make sealed target bytes readable as Blobs

task_id: W58-INT-TARGET-DIGEST-METADATA-01

## Outcome

The unactivated W58 target copy attaches the locally verified sealed SHA-256
as the `content-sha256` S3 user metadata on each newly copied object. A
container-free test uses the real S3BlobStore read path and refuses a missing
or wrong digest. This closes the positive available-Blob readback gap without
claiming a PostgreSQL/S3 drill or general source metadata preservation.

## Depends on

- `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01` — completed target copy helper.
- `W58-INT-TARGET-BLOB-READBACK-PREP-01` — completed Blob readback contract.
- `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01` — completed coordinator.

## Frozen inputs

- base commit: `69b923156ea3988dbad3cc378644b9799a6bdd23`
- published development commit at dispatch: `69b923156ea3988dbad3cc378644b9799a6bdd23`;
- W58 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- W58 target copy and readback SHA-256: `c1e1a5f54f557bc6ea7e291d94467709fedbf52f1e99f86cdf97775c4d2bca8b`, `b85e85818fce4e0dcbe701c33b30fef7366b008a102b79c2c85a83d5611ee53b`;
- storage adapter SHA-256: `00bffb6f23b7270fff58c479da6275fe6d851ffacd257c94fddd1c9ee1c87d1a`;
- migration head: `0023_norm_citations`; API/domain/error/stage contracts remain frozen.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the target copy writes sealed bytes without the digest metadata the
  owned BlobStore requires before it streams any available Blob.

### P-01 — missing write metadata and required read metadata

- captured_at: 2026-10-16
- command: `rg -n 'client.put_object|recorded = _metadata_value|_META_SHA256|Metadata=' scripts/recovery/target_object_restore.py src/auditmanager/storage/s3.py`
- captured_output:
  ```text
  src/auditmanager/storage/s3.py:88:_META_SHA256: Final[str] = "content-sha256"
  src/auditmanager/storage/s3.py:161:                self._client.put_object(
  src/auditmanager/storage/s3.py:286:                    field=_META_SHA256,
  src/auditmanager/storage/s3.py:320:                Metadata=_metadata_for(verified),
  src/auditmanager/storage/s3.py:406:            recorded = _metadata_value(response, _META_SHA256)
  src/auditmanager/storage/s3.py:409:                    field=_META_SHA256,
  src/auditmanager/storage/s3.py:589:        recorded_sha = metadata.get(_META_SHA256)
  src/auditmanager/storage/s3.py:670:        _META_SHA256: verified.sha256,
  src/auditmanager/storage/s3.py:696:    recorded = _metadata_value(response, _META_SHA256)
  src/auditmanager/storage/s3.py:699:            field=_META_SHA256,
  scripts/recovery/target_object_restore.py:208:                        client.put_object(
  ```
- interpretation: production BlobStore requires a recorded content digest;
  the W58 target copy currently sends no user metadata. The W58 manifest has
  an SHA-256 for each local payload, checked by `verify_manifest` and a second
  file hash before target write. This does not prove source metadata, endpoint
  isolation or full recovery.

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
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `docs/program/tasks/W58-INT-TARGET-DIGEST-METADATA-01.md`
- `docs/program/W58-INT-TARGET-DIGEST-METADATA-01.md`

## Forbidden hotspots

- `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, other `scripts/recovery/**`;
- root dependency/lock files, composition root, global styles,
  `docs/program/CURRENT_STATE.md`, W56b/W57a lanes, published refs and tags.

## Non-goals

- No source metadata capture, source writer quiescence, real service drill,
  restoration of role/media-type/custom S3 metadata, RPO or B6 acceptance.
- No Docker, PostgreSQL, MinIO or paid provider while W55b gate owns resources.

## Deliverables

- One targeted helper correction, real-adapter fake-client regression, updated
  injected client compatibility, and result report.

## Required tests

- Focused regression first fails on published base, then passes after fix.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.local/worktrees/code-first-entry/.venv/bin/python -m pytest tests/integration/recovery/test_target_object_restore.py tests/integration/recovery/test_isolated_restore_drill.py -q -p no:cacheprovider` — pass.
- Python compile, task governance, `git diff --check` and exact five-path containment.
- Real DB/S3 and full `make gate` deferred to owner service lane and R-135.

## Integration contract

After validating the canonical seal and full local bytes, the W58 target copy
puts a missing object with `Metadata={"content-sha256": sealed_sha256}` and
`IfNoneMatch="*"`. Existing target objects are not rewritten; the full
readback still checks their bytes. The real `S3BlobStore.open_stream` accepts
a newly restored canonical Blob only when this metadata matches the DB fact.

## Failure/idempotency/security cases

- A missing or wrong digest on an existing object fails the later BlobStore
  readback, even when its bytes happen to match the seal.
- A failed conditional PutObject never overwrites a concurrent object.
- The sealed SHA-256 is rehashed from the private mirror before upload; no
  caller-supplied metadata string is trusted. Full source S3 metadata remains
  unavailable in the frozen W58 object seal.

## Rollback / feature flag

Unactivated offline helper; revert this task's changed paths to roll back.

## Handoff

- changed files: report on completion;
- commands/results: report on completion;
- known limits: source metadata and real service proof remain open;
- integration notes: run the positive Blob readback in the later isolated lane.
