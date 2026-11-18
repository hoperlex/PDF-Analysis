# ADR-0020: Normative corpus alpha runtime uses PostgreSQL, pgvector and private S3 custody

- Status: accepted
- Date: 2026-10-01 (accepted for alpha by the repository owner, `NORM-ADR-01`); revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `NORM-ADR-01`; `R-76` (2026-10-09); `R-104` (2026-10-12, `OWNER_RULINGS_2026-09-17.md` section 3.30, `docs/program/dispatch/W54-PLAN.md` sections 3.1, 3.3 and 3.5, recorded by `W54-SEAL-01`); principles P-02, P-03, P-05, P-07, P-10, P-11, P-15, P-17
- Amends: settles the unresolved pgvector-versus-external-index choice in `ROADMAP.md`; no prior ADR is replaced

## Context

The roadmap left the retrieval store undecided between PostgreSQL/pgvector and an external vector
index. Later owned tasks created immutable normative snapshots, canonical paragraphs, rebuildable
chunks, a pinned BGE-M3 profile and a pgvector-capable PostgreSQL schema, but no production embedding
worker or search surface. Three readings had to be excluded:

- the 5.1 GB local corpus drop as an alpha runtime input would make one machine's ignored filesystem
  canonical, contrary to ADR-0005;
- vectors as the only corpus would make lossy derived retrieval rows the normative authority,
  contrary to P-11 and P-17;
- a distributed vector service would add a network service without the evidence ADR-0002 requires.

## Decision

For alpha, the normative runtime uses the already selected single PostgreSQL 17.11 derivative with
pgvector 0.8.6. There is no separate external or distributed vector database. Authority is layered:

1. `norms_snapshot`, `norm_document` and `norm_paragraph` in PostgreSQL are the canonical normative
   dataset. Published audit work pins the opaque `norms_snapshot_id`.
2. `norm_chunk`, tokenizer windows and `norm_embedding` are versioned rebuildable retrieval
   projections in the same PostgreSQL service. Search results resolve to canonical snapshot,
   document and paragraph identities/anchors; a vector row is never cited as authority.
3. Every source PDF and crop is a private S3-compatible Blob; PostgreSQL owns binding metadata and
   publication state, MinIO owns the bytes. A local path, filename, bucket or object key is never
   identity. A Blob is content-derived (`R-76`, superseding the earlier claim that each admission has
   its own `blob_id`): equal verified bytes in the corpus and in a project reuse one object. Each
   admission has its own immutable binding, with role `norm_source` and the drop's opaque `doc_…` /
   `blk_…` / `page_index` text anchors; the first publisher's storage role is metadata, not a
   restriction on later bindings. Reuse requires equal size, SHA-256 and media type; a missing
   recorded SHA-256 or a changed media type is a refusal, and a mismatch rejects the admission or
   Attempt, never the shared Blob row. Custody is two-phase (`R-104`): an *admission*
   (`norm_custody_admission`, `nad_<ULID>`) is the intent and its outbox row in one record, the
   dispatcher verifies the bytes and confirms it, and no binding is visible then; *binding
   publication* (`publish_bindings(role, target)`) runs in the transaction that holds the target rows
   and inserts one immutable `norm_custody_binding` (`nbd_<ULID>`) per confirmed admission, checking
   the target there. Roles map to target kinds through `ck_norm_custody_role_shape` (migration
   `0018_norm_custody`; W57a widens it for its own roles). Detail:
   `docs/program/NORM_CORPUS_CUSTODY.md`.
4. `.local/norms/corpus/**` is an offline/bootstrap source only. It is not baked into an image,
   copied to the alpha host as a serving dataset, mounted by a serving process or configured in alpha
   environment variables. Once a snapshot is published, runtime reads PostgreSQL/pgvector. The one
   exception (`R-104`): a verified bundle (`<content_key>+<bundle digest>/`) and the one-off database
   dump of the K-1 copy may sit transiently on the stand, in staging, read only by the one-shot
   importer or by `restore-db`; neither is a serving mount or an environment value, and the importer
   deletes the bundle's objects after `report` matches. Both forced-command keys (inbound bundle
   transport and the one-off copy) are owner-installed; their forced command is the boundary, because
   the key's account runs `docker`.
5. Re-recognition emits an immutable repair ledger and produces a new snapshot rather than mutating
   canonical paragraphs. Since `R-104` it no longer reads confirmed crop custody: the repair run
   happens on the development machine, before any custody exists, against a local promotion database,
   and reads crops from the drop, each checked against the operator's `SHA256SUMS` taken before the
   run. The drop stays an offline input; it is never admitted to custody and never read by a serving
   process. Embedding rebuilds read canonical PostgreSQL text and need no filesystem drop.
6. Corpus data is not seeded by Alembic. A separately owned promotion task must preserve opaque
   identities, content/build digests and all-or-nothing visibility while moving a verified canonical
   snapshot and complete embedding build into alpha PostgreSQL.

The embedding producer may run as a separate execution process because it has a different resource
profile, but it is not a new network service and publishes only through the existing transactional
PostgreSQL boundary.

## Consequences

- Positive: one database backup/restore and consistency boundary for canonical text and search.
- Positive: no runtime dependency on an ignored local directory or a second vector service.
- Positive: vector profiles can be rebuilt without changing cited normative evidence; raw source
  provenance stays available without placing large PDF/crop bytes in PostgreSQL.
- Cost: embedding generation and HNSW maintenance share PostgreSQL CPU, memory, I/O and operational
  capacity with the control plane.
- Cost: source custody needs its own outbox/reconciler before re-recognition can rely on MinIO.
- Cost: a verified snapshot promotion mechanism is still required; schema migration alone
  deliberately leaves the corpus tables empty.
- Cost: alpha is not horizontally distributed and has no independent vector-store availability.

## Alternatives considered

1. **Ship the filesystem drop to the VPS.** Rejected as a runtime design: paths are not identity,
   the drop is not deployment configuration, and filesystem/JSON is not canonical durable state.
2. **Use an external/distributed vector database.** Rejected for alpha: no measured scale, latency or
   availability evidence justifies a second service, and its consistency/backup boundary would be
   wider.
3. **Store only vectors.** Rejected: embeddings are model/profile-dependent derived data and cannot
   reproduce exact normative wording or source anchors.
4. **Put PDFs/crops in PostgreSQL.** Rejected: ADR-0006 assigns durable large bytes to private
   S3-compatible storage and PostgreSQL stores opaque bindings and metadata.

## Verification

- Automated: migrations require exact pgvector 0.8.6 and constrain canonical versus replace-only
  tables; composition uses the repository-owned PostgreSQL derivative and contains no external vector
  service.
- Operational: a promoted snapshot reports its opaque ID, content key, document/paragraph/chunk/window
  counts and embedding-set digest; alpha restore recovers the PostgreSQL snapshot and private S3
  bindings without a filesystem corpus mount.

## Revisit trigger

Replace this ADR only when production-like measurement shows that pgvector materially violates an
agreed search-latency/SLO, embedding/HNSW work causes unacceptable control-plane contention,
corpus/index scale exceeds the proven PostgreSQL envelope, or availability/region requirements cannot
share the alpha PostgreSQL failure domain. A replacement must define dual-system publication,
reconciliation, backup/restore and canonical citation behavior before adding a network service.

## History

- 2026-10-01 — accepted for alpha by the repository owner (`NORM-ADR-01`).
- 2026-10-09 — W53 addendum (`R-76`): a Blob is content-derived and bindings carry the role; folded
  into decision 3. It changed no runtime behavior; W54 implements it.
- 2026-10-12 — W54 addendum (`R-104`, `W54-SEAL-01`): custody two-phase, stand staging exception,
  re-recognition from the drop; folded into decisions 3, 4 and 5. Migration `0018_norm_custody` carries
  the schema; the addendum changed no runtime behavior.
- 2026-11-18 — compressed and unified (ADR-OPTIMISE-01); no decision changed.
