# W53 custody correction to NORM-CUSTODY-01

The completed `NORM-CUSTODY-01` task and its handoff are historical evidence and remain
bytewise unchanged. R-76 (2026-10-09) supersedes their one-Blob-per-admission rule.

The implementation grant belongs to `W54-CUSTODY-01`. W53 records the current design in
`NORM_CORPUS_CUSTODY.md`, NORM-Q05 and ADR-0020's addendum. `blob_id` is derived from
verified SHA-256 and size; equal bytes reuse one Blob even when a corpus and project bind
them for different purposes. Bindings carry the `norm_source` role and opaque source
anchors. Reuse verifies size, SHA-256 and media type and refuses missing SHA-256 or a
media mismatch. A failed admission or Attempt does not reject a shared Blob. Publication
serializes per blob through the storage metadata repository's advisory lock, shared
with ingest. `reject_unpublished` must respect non-terminal custody admissions and
Attempts. Erasure must see no live binding in any context's public module.

The custody outbox, dispatcher, reconciler, binding IDs, five-try schedule and operator
commands remain W54 work. No custody code, migration, data movement or live MinIO change
is performed by W53-SEAL-01.
