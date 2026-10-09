# Task W53-REHEARSAL-REPAIR-01 — restore from upgraded S3 source

## Outcome

Correct the disposable MinIO rehearsal so its `--full` rollback restores objects exported through the *new-image S3 API*, with version order, bytes and metadata verified on the old image. A PASS must not be obtainable merely by replaying the script's original fixture list.

## Depends on

- W53-REHEARSAL-01 (partial handback integrated; full MinIO scenario blocked by capacity)

## Frozen inputs

- domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- analysis/comparison/event: frozen W53 SEAL set; migration head `0017_execution_queue`.
- MinIO pin `RELEASE.2025-10-15T17-29-55Z`, commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`.
- base code before this dispatch amendment: `07c6d0f525348bb28793d6ec12a0c245ec26f14b`, after independent QA/X reports and the proxy repair. Integrator assigns exact post-amendment SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — restored bytes bypass upgraded source

- captured_at: 2026-10-09
- command: `nl -ba scripts/rehearsal/w53/minio_upgrade.py | sed -n '173,190p'`
- captured_output:
  ```text
     173        start(NEW, COPY_VOLUME, user, password)
     174        running = True
     175        new_manifest = manifest(ready(user, password), payloads)
     176        assert new_manifest == old_manifest, "version IDs/keys/bytes changed on volume copy"
     177        print("old-volume-copy/new-image-read: PASS, exact version IDs and bytes")
     178        stop()
     179        running = False
     180        start(OLD, RESTORE_VOLUME, user, password)
     181        running = True
     182        restored = ready(user, password)
     183        restored.create_bucket(Bucket=BUCKET)
     184        restored.put_bucket_versioning(
     185            Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"}
     186        )
     187        for key, body, metadata in payloads:
     188            restored.put_object(Bucket=BUCKET, Key=key, Body=body, Metadata=metadata)
     189        rollback_manifest = manifest(restored, payloads)
     190        assert logical_manifest(rollback_manifest) == logical_manifest(old_manifest)
  ```
- interpretation: Y independently found that the restore uses in-memory original fixtures; no export from upgraded S3 source is restored. This is a defect in the unrun full procedure, not a claim that the runtime rollback already failed.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W53-REHEARSAL-01.md`
- addendum_path: `docs/program/W53-REHEARSAL-REPAIR-01.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/rehearsal/w53/minio_upgrade.py`
- `docs/program/W53-REHEARSAL-REPAIR-01.md`

## Forbidden hotspots

- Historical `docs/program/W53-REHEARSAL-01.md`, other scripts, `contracts/**`, runtime/routers, migration, root dependency/lock, composition root, global styles, new-image pin, backup/deploy paths, working stand, refs/tags.

## Non-goals

- Actually claiming new-image compatibility or rollback without the image and safe disk capacity. No working-stand or beta backup.
- Changing original Stage-C evidence; the addendum explains the discovered limitation.

## Deliverables

- Script that enumerates versioned objects from new-image S3 after the volume-copy read, exports each version's bytes and metadata in exact per-key order, then imports that export into a fresh old-image S3 volume and compares logical manifest. Do not consult original `payloads` to supply restored bytes; they may be used only for expected comparison.
- Addendum report with a pure fake-source/fake-target regression or other direct test that proves restore consumes exported changed source data, six AGENTS.md §5 handback items, clean SHA and path audit.

## Required tests

- `python -m py_compile scripts/rehearsal/w53/minio_upgrade.py`; run a focused test with a fake new-source object differing from the original fixture and prove the old target receives the exported bytes. Run `--old-only` if private ports/services can be used safely and disk preflight permits. Do not run `--full` until the real new image exists and AGENTS.md §8 preflight has a credible build/peak margin. `git diff --check`, frozen SHA and exact path audit.

## Integration contract

The corrected full procedure will, when it can run, prove S3-level recovery from the upgraded server. Until then MinIO new-image read and rollback stay blocked under D-119/D-123. Integrator reviews the fake-source test and performs the actual disposable runtime later.

## Failure/idempotency/security cases

- Preserve all versions and metadata; fail on missing/extra versions, not merely equal counts. New VersionIds after S3 restore are expected; compare ordered logical content. No credentials in tracked files or logs.

## Rollback / feature flag

No product behavior changes. The rehearsal script is revertible; clean only its own disposable resources.

## Handoff

- changed files; commands/results; contracts; risks; integration instructions; forbidden-hotspot proof — six AGENTS.md §5 items.
