# ADR-0006: Private S3-compatible artifact storage

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principle P-13; fork note `R-156f`

## Context
Legacy import already shows checksum-verified assembly with staging, backup, journal and atomic replacement (`DW-04`). No legacy S3 parity exists and none is claimed (CP-00 review §5).

## Decision
Durable bytes and large artifacts live in private S3-compatible storage. Business code references opaque `blob_id`, role, size, SHA-256 and media type. Storage adapter alone owns object-key layout. Upload/publish is temporary→verify→publish; published manifest/object is immutable.

Presigned access is short-lived and scoped; internal keys are not UI/API identity.

**Fork (`R-156f`).** The fork starts with MinIO in the stack; after its bucket lane the objects live in a private Yandex Object Storage bucket. The application key is limited to that bucket and is not a root key; the bucket has no versioning (it would break erase, purge and forget); the move keeps the five object attributes; the object key is still derived from `blob_id` and the database stores no bucket or key. **Open:** region, bucket and account, decided by the owner when that lane starts.

## Consequences
- Positive: temporary → verify → publish maps directly onto the observed legacy import safety (CP-00 review §5).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-11-18 — fork note (`R-156f`): the fork's objects move to a private Yandex Object Storage bucket.
