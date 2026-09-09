# Task P1-STO-01 — implement the checksum-verified S3 BlobStore foundation

> **Status: specified; dispatch after accepted `P1-INT-00`.** Authoring may run in
> parallel; final acceptance runs after `P1-INF-01` is integrated.

## Outcome

A narrow BlobStore port writes temporary bytes, verifies size/SHA-256, publishes them
under an adapter-owned key and reads published bytes from real MinIO/S3-compatible
storage without exposing bucket/key as business identity.

## Depends on

- `P1-INT-00` — completed and integrated

## Frozen inputs

- FF-01 blob publication and privacy invariants
- locked S3 dependency, environment names and lane-isolation variables
- domain identifiers: read only; migration head: read only
- base commit: accepted `P1-INT-00` integration commit

## Allowed paths

- `src/auditmanager/storage/**`
- lane-owned tests under `tests/integration/storage/**`
- `docs/program/tasks/P1-STO-01.md` status/handoff

## Forbidden hotspots

- root locks/commands, `infra/local/**`, migrations, routers, product contexts and web
- contracts, CP-00 artifacts and global styles

## Non-goals

- No database metadata table, presigned browser route, multipart/resumable upload,
  lifecycle, retention or cross-region replication.
- No filesystem canonical adapter and no generic storage repository.

## Deliverables

- typed BlobStore port and explicit storage errors
- MinIO/S3 adapter implementing temporary upload, metadata/hash verification,
  publication, inspection and read
- `src/auditmanager/storage/check.py`, proving adapter-level private-bucket access through
  the reserved `make check-storage` target
- opaque `blob_id`; internal object-key layout confined to the adapter
- real-service tests for success, wrong checksum, unavailable service and idempotent
  repeated publication

## Required tests

- Command: `make up && make check-storage`
  Expected: exit `0` against the storage lane's unique private local bucket.
- Command: `.venv/bin/pytest tests/integration/storage`
  Expected: exit `0` against MinIO/S3, including negative paths.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Consumers receive opaque blob identity, role, media type, size and checksum. They can
publish only verified temporary content and cannot choose or observe canonical keys.

## Failure/idempotency/security cases

- Wrong checksum or size leaves no canonical publication.
- Repeating publication of identical verified content is controlled and documented.
- Missing credentials/unavailable storage is explicit; no filesystem fallback.
- Bucket/key never appears in public return models or error text.

## Rollback / feature flag

No product data exists in P01. Revert provider code; remove test objects only through
the scoped test cleanup, never by a broad bucket deletion.

## Handoff

- public port and error list
- object-key privacy proof
- commands/results and cleanup behavior
- known limits deferred to P02+
