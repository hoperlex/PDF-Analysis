# ADR-0020: Normative corpus alpha runtime uses PostgreSQL, pgvector and private S3 custody

- Status: accepted for alpha by repository owner
- Date: 2026-10-01
- Owners: repository owner / `NORM-ADR-01`
- Supersedes: the unresolved pgvector-versus-external-index choice in `ROADMAP.md`; no prior ADR
- Related principles: P-02, P-03, P-05, P-07, P-10, P-11, P-15, P-17

## Context

The original roadmap placed normative compliance in P05+ and deliberately left the retrieval
store undecided between PostgreSQL/pgvector and an external vector index. Subsequent owned tasks
created immutable normative snapshots, canonical paragraphs, rebuildable chunks, a pinned BGE-M3
profile and a pgvector-capable PostgreSQL schema. They did not create a production embedding
worker or search surface.

The remaining ambiguity is operationally material. Treating the 5.1 GB local corpus drop as an
alpha runtime input would make one machine's ignored filesystem canonical, contrary to ADR-0005.
Treating vectors as the only corpus would make lossy derived retrieval rows the normative
authority, contrary to P-11 and P-17. Adding a distributed vector service would also add a network
service without the evidence ADR-0002 requires.

## Decision

For alpha, the normative runtime uses the already selected single PostgreSQL 17.11 derivative
with pgvector 0.8.6. There is no separate external or distributed vector database.

Authority is layered as follows:

1. `norms_snapshot`, `norm_document` and `norm_paragraph` in PostgreSQL are the canonical
   normative dataset. Published audit work pins the opaque `norms_snapshot_id`.
2. `norm_chunk`, tokenizer windows and `norm_embedding` are versioned rebuildable retrieval
   projections in the same PostgreSQL service. Search results resolve to canonical snapshot,
   document and paragraph identities/anchors; a vector row is never cited as authority.
3. Every source PDF and crop is an immutable private S3-compatible Blob with its own opaque
   `blob_id`. PostgreSQL owns binding metadata and publication state; MinIO owns the bytes. A
   local path, filename, bucket or object key is never identity.
4. `.local/norms/corpus/**` is an offline/bootstrap source only. It is not baked into an image,
   copied to the alpha host as a serving dataset, mounted by a serving process or configured in
   alpha environment variables. Once a snapshot is published, runtime reads PostgreSQL/pgvector.
5. Re-recognition reads only confirmed crop custody, emits an immutable repair ledger, and
   produces a new snapshot rather than mutating canonical paragraphs. Embedding rebuilds read
   canonical PostgreSQL text and need no filesystem drop.
6. Corpus data is not seeded by Alembic. A separately owned promotion task must preserve opaque
   identities, content/build digests and all-or-nothing visibility while moving a verified
   canonical snapshot and complete embedding build into alpha PostgreSQL.

The embedding producer may run as a separate execution process because it has a different
resource profile, but it is not a new network service and publishes only through the existing
transactional PostgreSQL boundary.

## Consequences

### Positive

- Alpha has one database backup/restore and consistency boundary for canonical text and search.
- The application has no runtime dependency on an ignored local directory or a second vector
  service.
- Vector profiles can be rebuilt without changing cited normative evidence.
- Raw source provenance remains available without placing large PDF/crop bytes in PostgreSQL.

### Negative / cost

- Embedding generation and HNSW maintenance share PostgreSQL CPU, memory, I/O and operational
  capacity with the control plane.
- Source custody needs its own outbox/reconciler before re-recognition can rely on MinIO.
- A verified snapshot promotion mechanism is still required; schema migration alone deliberately
  leaves the corpus tables empty.
- Alpha is not horizontally distributed and has no independent vector-store availability.

## Alternatives considered

1. **Ship the filesystem drop to the VPS.** Rejected as a runtime design: paths are not identity,
   the drop is not deployment configuration, and filesystem/JSON is not canonical durable state.
2. **Use an external/distributed vector database.** Rejected for alpha: no measured scale,
   latency or availability evidence justifies a second service, and its consistency/backup
   boundary would be wider.
3. **Store only vectors.** Rejected: embeddings are model/profile-dependent derived data and
   cannot reproduce exact normative wording or source anchors.
4. **Put PDFs/crops in PostgreSQL.** Rejected: ADR-0006 assigns durable large bytes to private
   S3-compatible storage and PostgreSQL stores opaque bindings and metadata.

## Verification

- automated check/test: migrations require exact pgvector 0.8.6 and constrain canonical versus
  replace-only tables; composition uses the repository-owned PostgreSQL derivative and contains
  no external vector service
- manual/operational evidence: a promoted snapshot must report its opaque ID, content key,
  document/paragraph/chunk/window counts and embedding-set digest; alpha restore must recover the
  PostgreSQL snapshot and private S3 bindings without a filesystem corpus mount

## Revisit trigger

Replace this ADR only when production-like measurement shows that pgvector materially violates an
agreed search-latency/SLO, embedding/HNSW work causes unacceptable control-plane contention,
corpus/index scale exceeds the proven PostgreSQL envelope, or availability/region requirements
cannot share the alpha PostgreSQL failure domain. A replacement must define dual-system
publication, reconciliation, backup/restore and canonical citation behavior before adding a
network service.

## W53 addendum — R-76, 2026-10-09

Decision item 3's “every source PDF and crop ... with its own `blob_id`” described
separate admissions as separate bytes. R-76 supersedes that identity claim: a Blob
is content-derived and equal verified bytes in the corpus and a project reuse the same
object. Each admission has its own immutable binding; the binding carries role
`norm_source` and the drop's opaque `doc_…` / `blk_…` / `page_index` text anchors.
The first publisher's storage role remains metadata, not a restriction on later
bindings. Reuse requires size, SHA-256 and media type equality; a missing recorded
SHA-256 or a changed media type is a refusal. A mismatch rejects the admission or
Attempt, never the shared Blob row. W54 implements this after reconciling storage and
ingest public seams; this addendum changes no runtime behavior.
