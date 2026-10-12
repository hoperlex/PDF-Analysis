# norms — the normative corpus

**Bounded context.** Owns the body of external normative documents the system reasons
against — ГОСТ, СП, СНиП, ВСН, приказы, постановления — as *drawn* on a date, segmented
into retrievable units, and attributed to a source.

It is not `documents`. `documents` owns what a customer uploads into a project and is bound
to a project's lifecycle; a norm is owned by nobody, arrives in bulk, is identical for every
customer, and is replaced wholesale when the corpus is refreshed. The two share the word
"document" and nothing else: no aggregate, no identity space, no lifecycle.

It is not `ingest` or `analysis` either. `ingest` publishes one uploaded blob under an
idempotency key; `analysis` runs an engine over one run's documents. Segmenting a normative
corpus is neither: it is a deterministic parse of an external drop, and its output is a
projection that can be rebuilt from the drop at any time.

## What lives here

| module | holds |
|---|---|
| `model.py` | `Paragraph` (with its `TextReliability`), `Chunk`, `SegmentationReport`, `SourceAttribution` — values, no behaviour beyond derivation |
| `running_heads.py` | what counts as publisher noise, and the repeated-offcut rule |
| `segmentation.py` | the `results.md` parse: pages, blocks, recognised text, paragraphs |
| `chunking.py` | joining paragraphs into ~1200-character retrieval chunks: `characters-v1` (every paragraph) and the reliability-aware `characters-v2`, with the coverage invariant |
| `snapshot.py` | deterministic effective-text `content_key` derivation (`R-17`), its `+seg-<profile>` term (`D-126`), and the canonical row digest over a stored snapshot's rows |
| `repair.py` | the immutable repair ledger and repaired-content key |
| `corpus_source.py` | the only module that reads the filesystem; strict manifest/projection boundary |
| `repository.py` | transaction-local PostgreSQL writes, content-key idempotency, rows read back with their ids, the streamed row digest, chunk builds from stored paragraphs |
| `loader.py` | the atomic loader and its operator CLI; `import_snapshot`, which inserts rows with the ids they carry |
| `embedding/` | the resumable, batch-bounded `bge-m3-dense-v1` embedder: the 512/64 windowing ported from the bake-off runner, the plan and per-batch checkpoint files, the encode phase, `embed-texts`, and the `norm-embedding-set/2` digest; standard library only at module level |
| `embedding_repository.py` | transaction-local embedding persistence: a build accepted only with every chunk's full window set and loaded in one transaction ending with its completion row (`D-127`); the filtered HNSW search with its scan settings (`D-124`) |

## Rules this context keeps

- **Deterministic.** Same bytes in, byte-identical chunks out. `test_determinism.py` proves it
  by running the pipeline twice over the same input and comparing the serialised output.
- **Page anchoring, not fragment anchoring.** `R-16`: `coords_norm` is `[0,0,1,1]` for
  28 249 of 28 249 corpus blocks and `polygon_points` is `null` for every one, so there is no
  geometry to anchor to. A chunk carries `page_first`/`page_last` and a character offset into
  the document's recognised text. Re-segmenting page images is explicitly out of scope.
- **No identity from a path.** The corpus slug is a directory name and a display attribute.
  Durable identity is an opaque id on a row (`ADR-0010`), never the slug.
- **Identity is not content.** Persisted `norms_snapshot_id` is an opaque `ns_<ULID>` from the
  frozen catalog. Each immutable document and canonical paragraph receives its own
  `ndoc_<ULID>` or `npar_<ULID>`; none is derived from content, names, ordinals or private
  numeric keys. The readable W33/W39 value is stored as unique `content_key`; it resolves an
  idempotent load but is never accepted as an entity identity. Retrieval chunks have no public
  identity.
- **Nothing is written back into the corpus.** `corpus_source.py` opens files for reading only.
- **A repair is a projection, never an in-place edit.** `segment_corpus` verifies the ledger's
  base snapshot and every source block before yielding anything, applies only rows whose outcome
  is `repaired`, and puts the repaired snapshot identifier on the chunks containing repaired
  text. A stale or partially applicable ledger is refused rather than silently ignored.
- **Paragraphs are canonical; chunks are rebuildable.** Stored paragraphs and their source
  anchors are immutable. A named chunking profile may be deleted and rebuilt from those
  paragraphs, never edited in place. A stored `bge-m3-dense-v1` build embeds the chunks of one
  profile (`characters-v2` for a repaired snapshot) and applies deterministic 512-total-token
  windows with 64-content-token overlap to any over-limit chunk; it never truncates or
  substitutes an AI summary.
- **Unreliable text is marked, and only the reliability-aware profile is built over it**
  (`F-4`). A block the repair ledger holds that did not end `repaired` keeps its corpus text;
  each of its paragraphs is stored with `text_reliability = 'unreliable'`, and the snapshot
  stores the block count as `unreliable_count`. `characters-v2` skips those paragraphs and
  ends a chunk at each one — every reliable paragraph covered exactly once, exactly the
  unreliable set skipped. `characters-v1` joins every paragraph and is refused, in the
  projection and again by the repository on the stored count, over a snapshot with
  `unreliable_count > 0`. Over a snapshot with nothing unreliable the two profiles agree chunk
  for chunk. The loader builds `characters-v2` unless told otherwise.
- **The key names the segmentation profile** (`D-126`). Any `SEGMENTATION_PROFILE_VERSION`
  other than the literal `markdown-v1` appends `+seg-<profile>` after the digest of both the
  content key and the base key, so a raised profile loads as a new snapshot beside the old one.
  `markdown-v1` adds nothing; every existing key stays byte-identical.
- **Identity travels with the rows.** The promotion database mints every `ns_`, `ndoc_` and
  `npar_` id once, by the loader. `import_snapshot` inserts rows with the ids they carry
  (private keys minted and remapped), builds the named chunk profiles from those paragraphs and
  re-reads the row digest: an exact replay is a no-op; the same key under another id, the same
  id under another key, equal ids with other rows, or a child id held by another snapshot is
  refused with nothing written.

After migration `0018_norm_custody` (which adds `text_reliability` and `unreliable_count`;
the current database head is `0019_execution_workers`), load with:

`PYTHONPATH=src .venv/bin/python -m auditmanager.norms.loader --corpus <root> [--ledger <repairs.json>] [--target-characters 1200] [--chunking-version characters-v2]`

The command commits one database transaction, performs no S3/provider side effect, and prints
the snapshot id, content key, chunk profile, `unreliable_count`, the row digest and the counts.
A replay that names a chunk profile the stored snapshot lacks builds it from the stored
paragraphs.

## The embedding build (`W54-EMBED-01`)

- **Three restartable phases.** `prepare` (host, `DATABASE_URL`) streams the profile's chunks
  in canonical `(source_document_ref, ordinal)` order into `plan.json` and one input file per
  batch. `build` runs inside the norms-worker image with `--network none` and no database
  (`infra/norms-worker/run-build.sh`): it windows and embeds every batch that has no verified
  checkpoint, writes each checkpoint fsynced and renamed before its SHA-256 sidecar, and skips
  verified batches on a restart, so a kill costs at most the batch in flight and the ≈ 14 h
  corpus build spans night windows. `load` (host) verifies every checkpoint and streams them
  into one transaction that ends with the completion row. Memory is bounded by one batch in
  every phase.
- **Complete means the full window set (`D-127`).** Each chunk's windows start at its first
  character, end at its last, overlap pairwise, carry the SHA-256 of exactly their slice and the
  paragraph span that slice touches, and every chunk of the profile is present once. The
  repository applies this against the stored chunk text before it inserts anything.
- **The digest names content, not rows (`D-127`).** `embedding_set_sha256` is
  `norm-embedding-set/2` over `content_key ‖ source_document_ref ‖ chunking_profile ‖ ordinal`
  and each window's fields; no private key enters it. After a load the database recomputes it
  from the stored rows, and it must equal the checkpoints'.
- **Invisible until complete.** Windows and their completion row commit together; another
  transaction sees all of a build or none of it, and `nearest` refuses a build with no
  completion row.
- **Filtered search (`D-124`).** The one HNSW index spans every snapshot. `nearest` sets
  `hnsw.iterative_scan = strict_order`, `hnsw.ef_search` and `hnsw.max_scan_tuples` for its
  transaction and refuses a scan that returns fewer rows than the build holds.

```
PYTHONPATH=src .venv/bin/python -m auditmanager.norms.embedding prepare --snapshot <ns_id> --chunking-profile characters-v2:1200 --checkpoint .local/norms/builds/<content_key>
infra/norms-worker/run-build.sh auditmanager-norms-worker:bge-m3-dense-v1-5617a9f .local/norms/builds/<content_key> <ns_id> characters-v2:1200 [<max batches>]
PYTHONPATH=src .venv/bin/python -m auditmanager.norms.embedding load --snapshot <ns_id> --chunking-profile characters-v2:1200 --checkpoint .local/norms/builds/<content_key>
```

`build` exits 0 when every batch is verified, 75 when `--max-batches` left work for the next
window, and 2 on a refusal. `embed-texts --in <request.json> --out <response.json>` answers a
`auditmanager-embed-texts-request/1` file with base64 big-endian float32 vectors, the profile,
the model revision and each vector's SHA-256; a text over 512 tokens is refused, never cut.
