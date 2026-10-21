# W58-INT-TARGET-DIGEST-METADATA-01 — sealed digest on restored target objects

**Base:** published `origin/dev=69b923156ea3988dbad3cc378644b9799a6bdd23`.
**Status:** unactivated offline code correction; no real PostgreSQL, S3 or recovery drill.

## Result and proof

The W58 target helper now writes `Metadata={"content-sha256": sha256}` alongside
each missing sealed object. The digest is from the canonical W58 manifest,
which `verify_manifest` checks against full private mirror bytes before target
I/O. `_hash_file` rechecks those same bytes immediately before and after the
conditional `PutObject`. Existing objects remain untouched; the later target
BlobStore readback refuses absent or wrong digest metadata.

The regression uses the real `S3BlobStore.open_stream` with an injected fake
S3 client and a canonical content-addressed Blob key. On the published base it
failed with `BlobMetadataInvalidError` because the target `PutObject` sent no
user metadata. With this fix it reads the full payload, and removing or
changing `content-sha256` causes a typed refusal. The coordinator fake also
checks that each target write carries the SHA-256 of the bytes it received.

## Checks

- Before the fix: focused positive-Blob regression **failed** on missing
  `content-sha256` in the real BlobStore read path (expected red proof).
- After the fix: `test_target_object_restore.py` and
  `test_isolated_restore_drill.py`: **21 passed** in 0.35 s.
- `test_wave_governance.py`: **16 passed** in 0.10 s.
- Python compile, task-handoff parser and `git diff --check`: passed.
- No Docker, PostgreSQL, S3 request, paid provider, broad gate, remote ref or
  tag was used while W55b gate owned the resource lane.

## Limits and integration

This supplies the one user-metadata field required by `S3BlobStore.open_stream`
for full-body Blob verification. The frozen W58 seal stores payload bytes,
size, ETag and SHA-256, but not the source object's full S3 metadata. This
change does not preserve role, media type or arbitrary source metadata and
does not prove a fully functional source-bucket recovery. The later operator
must run an isolated positive-Blob DB/S3 drill, prove target endpoint and
bucket isolation, source quiescence and safe retry, and separately decide the
required policy for full metadata preservation before W58/B6 acceptance.

No API/domain/stage/storage public contract, migration, dependency or served
behavior changed. The injected `TargetObjectClient.put_object` call gains the
S3-compatible `Metadata` argument for W58 only. Revert this five-path task
commit to roll back the unactivated correction.

## Containment and handoff

Exactly these task-owned paths changed:

- `scripts/recovery/target_object_restore.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `docs/program/tasks/W58-INT-TARGET-DIGEST-METADATA-01.md`
- `docs/program/W58-INT-TARGET-DIGEST-METADATA-01.md`

No forbidden contract, migration, root lock/dependency, composition, global
style or other lane path was touched. The integrator can cherry-pick the
source commit, rerun the focused tests and retain the real drill as a separate
operator-owned service task.
