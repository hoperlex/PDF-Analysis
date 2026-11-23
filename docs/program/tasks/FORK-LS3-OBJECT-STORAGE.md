# Task FORK-LS3-OBJECT-STORAGE — move the fork's objects from MinIO to Yandex Object Storage

## Outcome
The stack runs with an external S3 bucket (`ALPHA_S3_MODE=external`). The MinIO service and its volume are removed after a verified move.
There are no client data yet, so no window, retention period or rehearsal is needed (`R-156f`).

## Owner and paths
The fork's storage lane: `src/auditmanager/storage/**`, `infra/deploy/**`, `infra/deploy/compose.server.yml`, the S3 tests and this card.

## Depends on
- `FORK-L0-MEASURE`.

## Work
1. **Code.**
   - Add `ALPHA_S3_MODE=local|external` through `COMPOSE_PROFILES`; external drops the `s3` and `s3-init` services.
   - In external mode the application key is its own, not the MinIO root pair: remove the guard `S3_ACCESS_KEY_ID == MINIO_ROOT_USER`.
   - TLS to the bucket; checksum `when_required`.
   - Copy objects with a tool that keeps their five attributes, replacing `mc`.
   - `deploy.sh` and `verify-deployed.sh` work without the `s3` service.
2. **Provider checks before the switch:** TLS; a 25 MiB upload; a range read; latency, since every document view goes through the bucket;
   a lifecycle rule for abandoned multipart uploads.
3. **The move.** Copy the 28,920 norm objects with their attributes, then verify `blob_id` (sha256 and size) and the move fingerprint.
   Switch the env, run `verify-deployed.sh`, do a practice read, and only then remove the MinIO volume.
   - Alternative: when this lane lands before an import, import the norms bundle straight into the bucket.

## Owner decisions at the start (poll)
The region and the place client data are stored (ru-central1 or kz1), the bucket name, and who owns the cloud account.
The bucket is private, its key is scoped to that bucket only, and versioning is off, because versioning breaks erasure (`ADR-0006` fork note).

## Checks
- The storage tests.
- `docker compose config` in both modes.
- The provider checks.
- The move fingerprint compared before and after.

## Integration and rollback
`ALPHA_S3_MODE=local` together with the MinIO volume kept until the verified move.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
