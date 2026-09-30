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
| `model.py` | `Paragraph`, `Chunk`, `SegmentationReport`, `SourceAttribution` — values, no behaviour beyond derivation |
| `running_heads.py` | what counts as publisher noise, and the repeated-offcut rule |
| `segmentation.py` | the `results.md` parse: pages, blocks, recognised text, paragraphs |
| `chunking.py` | joining paragraphs into ~1200-character retrieval chunks |
| `snapshot.py` | deterministic effective-text `content_key` derivation (`R-17`) |
| `repair.py` | the immutable repair ledger and repaired-content key |
| `corpus_source.py` | the only module that reads the filesystem; strict manifest/projection boundary |
| `repository.py` | transaction-local PostgreSQL writes and content-key idempotency |
| `loader.py` | atomic loader and its operator CLI |

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
  paragraphs, never edited in place. The measured `bge-m3-dense-v1` profile starts from
  table-row paragraphs and applies deterministic 512-total-token windows with 64-content-token
  overlap to any over-limit paragraph; it never truncates or substitutes an AI summary.

After migration `0012_norms_corpus`, load with:

`PYTHONPATH=src .venv/bin/python -m auditmanager.norms.loader --corpus <root> [--ledger <repairs.json>]`
The command commits one database transaction and performs no S3/provider side effect.
