# ADR-0020: Normative corpus alpha runtime uses PostgreSQL, pgvector and private S3 custody

- Status: accepted
- Date: 2026-10-01 (accepted for alpha by the repository owner, `NORM-ADR-01`); revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `NORM-ADR-01`; `R-76` (2026-10-09); `R-104` (2026-10-12, `OWNER_RULINGS_2026-09-17.md` section 3.30, `docs/program/dispatch/W54-PLAN.md`, recorded by `W54-SEAL-01`); fork decision 7: `R-156b`…`R-156k`
- Amends: settles the unresolved pgvector-versus-external-index choice in `ROADMAP.md`; no prior ADR is replaced

## Context

The roadmap left the retrieval store undecided between PostgreSQL/pgvector and an external vector index.
Excluded readings: the 5.1 GB local corpus drop as an alpha runtime input (an ignored local filesystem
would be canonical, contrary to ADR-0005); vectors as the only corpus (lossy derived rows would be the
authority, contrary to P-11 and P-17); a distributed vector service (a network service without the
evidence ADR-0002 requires).

## Decision

For alpha, the normative runtime uses the already selected single PostgreSQL 17.11 derivative with
pgvector 0.8.6. There is no separate external or distributed vector database. Authority is layered:

1. `norms_snapshot`, `norm_document` and `norm_paragraph` in PostgreSQL are the canonical normative
   dataset. Published audit work pins the opaque `norms_snapshot_id`.
2. `norm_chunk`, tokenizer windows and `norm_embedding` are versioned rebuildable retrieval projections
   in the same PostgreSQL service. Search results resolve to canonical snapshot, document and paragraph
   identities and anchors; a vector row is never cited as authority.
3. Every source PDF and crop is a private S3-compatible Blob; PostgreSQL owns binding metadata and
   publication state, MinIO owns the bytes. A local path, filename, bucket or object key is never
   identity. A Blob is content-derived (`R-76`): equal verified bytes in the corpus and in a project
   reuse one object, and a mismatch rejects the admission or Attempt, never the shared Blob row. Each
   admission has its own immutable binding, with role `norm_source` and the drop's opaque `doc_…` /
   `blk_…` / `page_index` anchors; the first publisher's role restricts no later binding. Custody is
   two-phase (`R-104`): an admission (`nad_<ULID>`) is the intent and its outbox row in one record,
   confirmed once the dispatcher has verified the bytes, with no binding visible then; binding
   publication (`nbd_<ULID>`) runs in the transaction that holds the target rows and checks the target
   there. Detail: `docs/program/NORM_CORPUS_CUSTODY.md`.
4. `.local/norms/corpus/**` is an offline/bootstrap source only: not baked into an image, copied to the
   alpha host as a serving dataset, mounted by a serving process or set in alpha environment variables.
   Once a snapshot is published, runtime reads PostgreSQL/pgvector. The one exception (`R-104`): a
   verified bundle and the one-off database dump of the K-1 copy may sit transiently on the stand, in
   staging, read only by the one-shot importer or by `restore-db`, never as a serving mount or an
   environment value; the importer deletes the bundle's objects after `report` matches. Both
   forced-command keys (bundle transport, one-off copy) are owner-installed; their forced command is the
   boundary, because the key's account runs `docker`.
5. Re-recognition emits an immutable repair ledger and produces a new snapshot rather than mutating
   canonical paragraphs. Since `R-104` it runs on the development machine, before any custody exists,
   against a local promotion database, reading crops from the drop, each checked against the operator's
   `SHA256SUMS` taken before the run; it never reads confirmed crop custody, and the drop is never
   admitted to custody or read by a serving process. Embedding rebuilds read canonical PostgreSQL text.
6. Corpus data is not seeded by Alembic. A separately owned promotion task must preserve opaque
   identities, content/build digests and all-or-nothing visibility while moving a verified canonical
   snapshot and complete embedding build into alpha PostgreSQL.
7. **The fork server: embeddings on the fly, in local PostgreSQL (`R-156b`…`R-156d`, `R-156g`, `R-156h`,
   `R-156j`, `R-156k`).** On the fork's own server (32 GB RAM, 12 CPU cores, no GPU) texts are embedded when
   they arrive, by a model larger than today's BGE-M3 int8 profile; there is no night window. Vectors stay
   in the local PostgreSQL with pgvector 0.8.6 on the repository's own image, one failure domain: no managed
   or external vector service, because the managed offers are cut down and too slow for on-the-fly
   embedding. Only the norms corpus arrives there (`R-156g`). The code is written in the fork (`R-156k`).
   - The active embedding profile is a setting, not a literal. A profile names the exact weights, runtime
     and precision; vectors of different profiles are never mixed; the profile is part of each vector key
     and each profile has its own partial HNSW index.
   - One resident embedder service on the stack network is permitted: no database access, no published
     port, a hard memory limit (8 GB planned) and at most 8 of the 12 cores. The worker calls it and writes
     the vectors in its own transaction. For the fork this replaces "not a new network service" below.
   - **Open:** the model — the owner chooses after his own study, Giga-Embeddings is the leading candidate
     (`R-156j`), and a switch is preceded by the corpus retrieval fixture (BGE-M3 baseline MRR 0.849), a
     lower score going to the owner; the dimension — 1024 if the model gives it without material loss,
     otherwise `halfvec(N)`, N ≤ 4000, and a migration of the three vector columns.
   - The current production VPS keeps the BGE-M3 profile and the windows of `ADR-0029`.

The embedding producer may run as a separate execution process (a different resource profile), but it is
not a new network service and publishes only through the transactional PostgreSQL boundary.

## Consequences

- Positive: one backup/restore and consistency boundary for canonical text and search; vector profiles
  rebuild without changing evidence.
- Cost: embedding and HNSW maintenance share PostgreSQL capacity with the control plane; alpha has no
  independent vector-store availability.
- Cost: source custody needs its own outbox/reconciler, and a promotion mechanism is needed (decision
  6): a migration alone leaves the corpus tables empty.

## Alternatives considered

1. **Ship the filesystem drop to the VPS** — rejected: paths are not identity and the drop is not
   deployment configuration.
2. **Use an external/distributed vector database** — rejected for alpha: no measured evidence justifies
   a second service and a wider consistency/backup boundary.
3. **Store only vectors** — rejected: embeddings are derived data and cannot reproduce exact wording or
   source anchors.
4. **Put PDFs/crops in PostgreSQL** — rejected: ADR-0006 assigns durable large bytes to private S3.

## Verification

Migrations require exact pgvector 0.8.6 and constrain canonical versus replace-only tables; composition
has no external vector service. A promoted snapshot reports its opaque ID, content key,
document/paragraph/chunk/window counts and embedding-set digest; alpha restore recovers the PostgreSQL
snapshot and private S3 bindings without a filesystem corpus mount.

## Revisit trigger

Replace this ADR only when production-like measurement shows that pgvector materially violates an agreed
search-latency/SLO, embedding/HNSW work causes unacceptable control-plane contention, corpus/index scale
exceeds the proven PostgreSQL envelope, or availability/region requirements cannot share the alpha
PostgreSQL failure domain. A replacement defines dual-system publication, reconciliation, backup/restore
and canonical citation before adding a network service.

## History

- 2026-10-01 — accepted for alpha by the repository owner (`NORM-ADR-01`).
- 2026-10-09 — W53 addendum (`R-76`): a Blob is content-derived and bindings carry the role; folded into
  decision 3.
- 2026-10-12 — W54 addendum (`R-104`, `W54-SEAL-01`): two-phase custody, stand staging exception,
  re-recognition from the drop; folded into decisions 3, 4 and 5.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0020-normative-corpus-alpha-runtime.md
- 2026-11-18 — decision 7 added: the fork server, embeddings on the fly in local PostgreSQL (`R-156b`…`R-156k`).
