# Normative corpus decision backlog

No implementation may silently choose an owner answer. Resolved rows are frozen inputs for the
named implementation task. All normative-corpus rows now carry an owner disposition; the global
retention/legal-hold authority in `U-04` remains separate and open.

| ID | Status | Decision / conservative default | Owner of implementation |
|---|---|---|---|
| NORM-Q01 | resolved 2026-09-30 | No public `norm_chunk_id`. Search results will cite a snapshot and canonical paragraph identities/anchors; retrieval chunks remain rebuildable projection rows. | future search API contract |
| NORM-Q02 | resolved 2026-09-30 | Split first at canonical table rows, then use deterministic tokenizer windows of 512 tokens with 64-token overlap. No AI summary and no truncation. | `NORM-EMBED-EVAL-01` profile; later pgvector slot |
| NORM-Q03 | resolved 2026-09-30 | `bge-m3-dense-v1`: BAAI/bge-m3 at `5617a9f61b028005a4858fdac845db406aefb181`, plain text, CLS pooling, 1024 float32, L2 normalization, inner product, 512 total tokens and 64-token overlap. | later pgvector migration/rebuild slot |
| NORM-Q04 | resolved 2026-10-01 | Internal-use only. Preserve attribution exactly and make no publication/release-rights claim for ConsultantPlus-derived text or the 17 unattributed documents. Revisit licensing before any external corpus-backed release. | corpus-backed release gate; owner review remains scheduled soon |
| NORM-Q05 | superseded by R-76 on 2026-10-09 | A source PDF and crop have separate immutable bindings; equal verified bytes reuse one content-derived `blob_id` across corpus and project. The binding carries `norm_source`; publish it only after transactional intent/outbox reconciliation and checksum/media confirmation. | W54-CUSTODY-01 |
| NORM-Q06 | resolved 2026-10-01 | Full retention: retain every loaded snapshot, source PDF Blob, crop Blob and immutable repair ledger with no automatic deletion or TTL. Any later deletion capability is a new owner/legal/security ruling and forward-only implementation task. | every corpus persistence/custody task |
| NORM-Q07 | resolved 2026-09-30 | Norm documents and canonical paragraphs are public contracted entities with opaque `ndoc_<ULID>` and `npar_<ULID>`; source names, ordinals and content never form identity. | `NORM-ID-01` |
| NORM-Q08 | resolved 2026-10-01 | Build a repository-owned derivative of the pinned PostgreSQL 17.11 base. Compile official pgvector v0.8.6 commit `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c` from archive SHA-256 `d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299`; never consume a floating pgvector image/tag. | `NORM-VECTOR-01` image/migration slot |
| NORM-Q09 | resolved 2026-10-01 | Alpha uses the existing single PostgreSQL service plus pgvector, with no external/distributed vector database. Canonical documents and paragraphs live in PostgreSQL; chunks/windows/embeddings are rebuildable projections. Source PDFs and crops live only as private MinIO/S3 Blobs. `.local/norms/corpus/**` is an offline/bootstrap input and never an alpha serving mount or environment dependency. | `NORM-ADR-01`; later corpus-promotion and search slots |
