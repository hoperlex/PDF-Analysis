# Task P1-INF-01 — start local PostgreSQL and private S3-compatible services

> **Status: specified; dispatch after accepted `P1-INT-00`.** Authoring may run in
> parallel with `P1-DB-01` and `P1-STO-01`; acceptance uses the integrated INF provider.

## Outcome

`make up` starts pinned PostgreSQL and MinIO services with health checks, persistent
volumes and an idempotently initialized private bucket.

## Depends on

- `P1-INT-00` — completed and integrated

## Frozen inputs

- FF-01 decisions and `FOUNDATION_LOCK.json`
- environment names and literal commands from `P1-INT-00`
- migration head: `none`, read only
- base commit: accepted `P1-INT-00` integration commit

## Allowed paths

- `infra/local/**`
- foundation sections of `infra/README.md`
- lane-owned tests under `tests/integration/infra/**`
- `docs/program/tasks/P1-INF-01.md` status/handoff

## Forbidden hotspots

- root manifests/locks, `.env.example`, migrations, Python storage/DB providers
- contracts, composition root, web, CP-00 artifacts and global styles

## Non-goals

- No cloud deployment, production credentials, public bucket, lifecycle or backup.
- No database schema or application runtime.

## Deliverables

- pinned Compose-compatible PostgreSQL and MinIO services
- health checks and persistent network/volume names derived from `FOUNDATION_INSTANCE`
- idempotent private-bucket initializer using the frozen `S3_BUCKET`
- `infra/local/check_services.py`, proving service health and bucket initialization but
  making no claim about application migrations or the BlobStore adapter
- start/stop/troubleshooting documentation and lane tests

## Required tests

- Command: `make up`
  Expected: exit `0`; both services become healthy without manual action on this lane's
  unique instance and ports.
- Command: `make check-services`
  Expected: exit `0`; PostgreSQL/MinIO are healthy, the bucket exists, authenticated
  service access works and no migration-head claim is made.
- Command: `make down && make up && make check-services`
  Expected: exit `0`; this instance's service volumes persist without touching another
  lane's state.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

DB/storage lanes receive healthy services through frozen environment names. Internal
ports are exposed only to the local host/network required by development.
Compose project, network and volume names are derived from `FOUNDATION_INSTANCE`.

## Failure/idempotency/security cases

- Repeated `make up` and bucket initialization are safe.
- Anonymous bucket list/read/write is denied.
- Missing credentials or unhealthy service produces an explicit non-zero check.

## Rollback / feature flag

`make down` is non-destructive. Data removal is never a default rollback action.

## Handoff

- changed files and image digests
- commands/results, privacy check and persistence result
- local prerequisites and known platform limitations
