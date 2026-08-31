# ADR-0006: Private S3-compatible artifact storage

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Durable bytes and large artifacts live in private S3-compatible storage. Business code references opaque `blob_id`, role, size, SHA-256 and media type. Storage adapter alone owns object-key layout. Upload/publish is temporary→verify→publish; published manifest/object is immutable.

Presigned access is short-lived and scoped; internal keys are not UI/API identity.
