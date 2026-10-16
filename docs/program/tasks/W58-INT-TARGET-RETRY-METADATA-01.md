# Task W58-INT-TARGET-RETRY-METADATA-01 — refuse unreadable target object metadata

task_id: W58-INT-TARGET-RETRY-METADATA-01

## Outcome

An unactivated W58 target restore accepts an existing exact-byte object only
when its `content-sha256` user metadata equals the sealed digest. Every final
GetObject readback checks the same value, including newly uploaded objects.
Container-free tests prove refusal before any new upload and refusal after a
metadata change during final readback.

## Depends on

- `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01` — completed conditional target copy and full byte readback.
- `W58-INT-TARGET-DIGEST-METADATA-01` — completed digest metadata write and real BlobStore read regression.

## Frozen inputs

- base commit: `7b56cb451946d250b1030f61150a4979dbcfc157`
- published development commit at dispatch: `7b56cb451946d250b1030f61150a4979dbcfc157` (dev62);
- W58 scope and code-first plan SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`, `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- target restore/test SHA-256: `bd0ab6f3ae14c69121d18b98f9c8ef1033d25bd61b2f68294e95207b3c0aaa2f`, `f65a16d6945b4ecd698cd4ab3c5dfea3a8bc4ad9ce351e043bc028ba28a91db7`;
- storage public/adapter SHA-256: `b8f1c8163827e9e86ae7e3a96a286e15e7fb41afc35813cadb7f705f9c54247c`, `00bffb6f23b7270fff58c479da6275fe6d851ffacd257c94fddd1c9ee1c87d1a`;
- API/domain/error/stage SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`, `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`, `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`, `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- migration head: `0023_norm_citations`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the target restore writes digest metadata for new objects, but its
  GetObject byte checks accept an exact-byte existing object without that
  metadata. The real BlobStore refuses such an object.

### P-01 — target readback omits required digest metadata

- captured_at: 2026-10-16
- command: `rg -n '^def _read_target|_read_target\\(|Metadata=|client.metadata\\[key\\].clear|BlobMetadataInvalidError' scripts/recovery/target_object_restore.py tests/integration/recovery/test_target_object_restore.py`
- captured_output:
  ```text
  scripts/recovery/target_object_restore.py:129:def _read_target(client: TargetObjectClient, bucket: str, key: str, size: int, sha256: str) -> None:
  scripts/recovery/target_object_restore.py:200:                _read_target(client, target_bucket, key, size, sha256)
  scripts/recovery/target_object_restore.py:211:                            Metadata={"content-sha256": sha256},
  scripts/recovery/target_object_restore.py:220:            _read_target(client, target_bucket, key, size, sha256)
  scripts/recovery/target_object_restore.py:228:        _read_target(client, target_bucket, key, size, sha256)
  tests/integration/recovery/test_target_object_restore.py:12:    BlobId, BlobMetadataInvalidError, BlobIntegrityError, S3BlobStore, S3StorageSettings,
  tests/integration/recovery/test_target_object_restore.py:163:    client.metadata[key].clear()
  tests/integration/recovery/test_target_object_restore.py:164:    with pytest.raises(BlobMetadataInvalidError):
  ```
- interpretation: the write path supplies a digest; all three target read
  paths reuse `_read_target`, whose current body validates length and bytes
  only. The BlobStore test proves why a missing digest cannot be treated as a
  usable restored object. This does not prove source metadata or service IO.

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
- `docs/program/tasks/W58-INT-TARGET-RETRY-METADATA-01.md`
- `docs/program/W58-INT-TARGET-RETRY-METADATA-01.md`

## Forbidden hotspots

- other `scripts/recovery/**`, `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`;
- root dependency/lock files, composition root, global styles,
  `docs/program/CURRENT_STATE.md`, corpus data, service state, remote refs and tags.

## Non-goals

- No source S3 role, media type or custom metadata preservation; the frozen
  W58 object seal does not contain those facts.
- No real PostgreSQL/S3 drill, production restore, source writer quiescence,
  RPO or W58/B6 acceptance.

## Deliverables

- One target GetObject metadata guard, fake-client refusal/regression tests,
  coordinator fixture propagation of the existing PutObject Metadata field,
  and a result report with exact changed paths and remaining limits.

## Required tests

- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/integration/recovery/test_target_object_restore.py -q -p no:cacheprovider` — pass.
- `PYTHONPATH=src:. /root/projects/PDF-Analysis/.venv/bin/python -m pytest tests/integration/recovery -q -p no:cacheprovider` — pass.
- Python compile, programme task governance, `git diff --check`, and exact
  five-path containment — pass. No heavy service or full gate under R-135.

## Integration contract

`restore_sealed_objects` requires `Metadata["content-sha256"]` to equal the
SHA-256 in the sealed object manifest on every target GetObject response.
An existing exact-byte object with missing or mismatched metadata refuses
before later missing objects are uploaded. New uploads keep the existing
conditional `IfNoneMatch="*"` and sealed digest metadata write. Final byte
readback refuses metadata drift. Existing objects are never overwritten.

## Failure/idempotency/security cases

- Missing/malformed/wrong digest metadata refuses even if bytes are intact.
- A retry with exact bytes and digest metadata succeeds without rewriting;
  wrong existing metadata refuses before any new upload.
- A concurrent metadata change between reads refuses on final readback.

## Rollback / feature flag

The helper is unactivated; revert the five owned paths to remove this guard.
No served behavior or feature flag changes.

## Handoff

- changed files: report on completion;
- commands/results: report on completion;
- known limits: source metadata and a real isolated service drill remain open;
- integration notes: cherry-pick the exact local source commit into the
  assigned `origin/dev` integration slot after focused checks.
