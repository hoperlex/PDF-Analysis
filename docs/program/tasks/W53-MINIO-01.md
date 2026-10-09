# Task W53-MINIO-01 — build and test the pinned security image on disposable data

task_id: W53-MINIO-01

## Outcome

The repository-owned MinIO server image builds from the official 2025-10-15 security release with verified source/toolchain inputs, and reads objects written by the prior image on a disposable copy. The working stand is unchanged.

## Depends on

- `W53-FREEZE-01`, completed at `3c527d363ee5a196fbd44bf2f5b187d544615dd6`.

## Frozen inputs

- Base `3c527d363ee5a196fbd44bf2f5b187d544615dd6`; `dispatch/W53-PLAN.md` §3.4/Stage A as amended 2026-10-09.
- R-75: source-pinned release and a recoverable-copy/inventory prerequisite before any working-stand upgrade. Backup implementation is deferred to a separate beta wave under R-77.
- Contract set remains domain revision 9, API 30/37/83, 23 error codes and head `0016_release_notes`; this lane owns none of it.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `docs/program/FOUNDATION_LOCK.json`
- enumerator_owner: `W53-MINIO-01`
- totality_query: the image build labels/version output and the lock's `minio_build_inputs` must name the same release/source digests; `tests/integration/composition/test_minio_image_contract.py` verifies it.

## Captured premise evidence

- premise: the image and composition inputs exist on the exact development base.

### P-01 — current image path

- captured_at: 2026-10-09
- command: `find infra/minio -maxdepth 1 -type f`
- captured_output:
  ```text
  infra/minio/Dockerfile
  ```
- interpretation: this identifies the current repository-owned image source; it does not prove the proposed release builds.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `infra/minio/**` — server source pin/build only; keep the `mc` client unless an exact build requirement proves otherwise.
- `infra/deploy/compose.server.yml`, `infra/local/docker-compose.yml` — MinIO image tags and directly attached comments only; no other service or volume edits.
- `docs/program/FOUNDATION_LOCK.json` — MinIO server entry and `minio_build_inputs` only.
- `tests/integration/composition/test_minio_image_contract.py` — exact image pin/build and old-write/new-read disposable-copy check only.
- `docs/program/W53-MINIO-01.md` — six-item hand-back.

## Forbidden hotspots

Every other path: contracts, migrations, root dependency/lock files, composition root, global styles, SEAL's surface/prose paths, backup/deploy scripts, `VERSION`, release notes, refs, tags and the working stand. Do not stop other lanes' containers, volumes or networks.

## Non-goals

No working-stand upgrade or inventory claim, no `D-119`/`D-123` closure, no backup implementation, no storage identity or persisted-data migration.

## Deliverables and required tests

Pinned Dockerfile/lock/tags, a build from verified official inputs, old-image writes → new-image reads using a disposable S3 copy, a disposable rollback read after S3-level restore, exact image contract test, `git diff --check`. The complete gate is deferred to the integrator's exact candidate; report focused checks actually run and any host-capacity refusal.

## Integration contract

Use branch `agent/w53-minio-01` in a separate worktree from the integrator's exact dispatch SHA. Only `gate-w53minio` ports 56840/60440/60441 may be used after a listener recheck. No publication, tag or stand access. The integrator merges after SEAL; this lane's paths do not overlap SEAL's editable paths.

## Failure/idempotency/security cases

Abort on source checksum, toolchain digest, version-label or old-object read mismatch. A green new-container startup alone is insufficient. Keep existing named S3 data volume semantics in compose; use disposable copies for tests and remove only lane-owned resources.

## Rollback / feature flag

The image tag can be reverted on the development branch. A working-stand rollback would require an S3-level recoverable copy and belongs to the later authorized deployment task; no feature flag.

## Handoff

Provide branch and exact SHA; changed files; commands/results; contract delta (expected none); risks; integrator instructions; allowed-path and forbidden-hotspot proof. No checkpoint/tag/push.
