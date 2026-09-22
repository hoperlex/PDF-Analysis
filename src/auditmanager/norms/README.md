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
| `snapshot.py` | the corpus-snapshot identifier (`R-17`) and its derivation |
| `corpus_source.py` | the only module that touches a filesystem; everything else takes text |

## Rules this context keeps

- **Deterministic.** Same bytes in, byte-identical chunks out. `test_determinism.py` proves it
  by running the pipeline twice over the same input and comparing the serialised output.
- **Page anchoring, not fragment anchoring.** `R-16`: `coords_norm` is `[0,0,1,1]` for
  28 249 of 28 249 corpus blocks and `polygon_points` is `null` for every one, so there is no
  geometry to anchor to. A chunk carries `page_first`/`page_last` and a character offset into
  the document's recognised text. Re-segmenting page images is explicitly out of scope.
- **No identity from a path.** The corpus slug is a directory name and a display attribute.
  Durable identity is an opaque id on a row (`ADR-0010`), never the slug.
- **Nothing is written back into the corpus.** `corpus_source.py` opens files for reading only.
