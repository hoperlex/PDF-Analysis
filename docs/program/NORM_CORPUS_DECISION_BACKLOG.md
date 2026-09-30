# Normative corpus decision backlog

No implementation may silently choose an owner answer. Resolved rows are frozen inputs for the
named implementation task; the three open rows do not block persistence, embedding evaluation or
custody staging.

| ID | Status | Decision / conservative default | Owner of implementation |
|---|---|---|---|
| NORM-Q01 | resolved 2026-09-30 | No public `norm_chunk_id`. Search results will cite a snapshot and canonical paragraph identities/anchors; retrieval chunks remain rebuildable projection rows. | future search API contract |
| NORM-Q02 | resolved 2026-09-30 | Split first at canonical table rows, then use deterministic tokenizer windows of 512 tokens with 64-token overlap. No AI summary and no truncation. | `NORM-EMBED-EVAL-01` profile; later pgvector slot |
| NORM-Q03 | resolved 2026-09-30 | `bge-m3-dense-v1`: BAAI/bge-m3 at `5617a9f61b028005a4858fdac845db406aefb181`, plain text, CLS pooling, 1024 float32, L2 normalization, inner product, 512 total tokens and 64-token overlap. | later pgvector migration/rebuild slot |
| NORM-Q04 | **open** | Preserve attribution exactly and make no release-rights claim until publication/licensing treatment for ConsultantPlus-derived text and 17 unattributed documents is approved. | owner before corpus-backed release |
| NORM-Q05 | resolved 2026-09-30 | Every source PDF and every crop is an independent immutable Blob with its own `blob_id`; publish bindings only after transactional intent/outbox reconciliation and checksum confirmation. | parallel MinIO migration/reconciliation slot |
| NORM-Q06 | **open** | Retain every loaded snapshot and confirmed source/crop Blob until a cited-data retention/deletion rule is approved. | owner before deletion capability |
| NORM-Q07 | resolved 2026-09-30 | Norm documents and canonical paragraphs are public contracted entities with opaque `ndoc_<ULID>` and `npar_<ULID>`; source names, ordinals and content never form identity. | `NORM-ID-01` |
| NORM-Q08 | **open** | The pinned plain PostgreSQL 17.11 image has no `vector` extension. Choose a repository-owned derivative image with pinned pgvector or an independently pinned third-party pgvector image. | owner before pgvector migration slot |
