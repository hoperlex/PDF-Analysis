# W33-CORPUS — the normative corpus, segmented and dated

**Task `W33-CORPUS`, the first measurable half of `R-16`, and `R-17`'s snapshot identifier
settled as data.** Worktree `/root/w33corpus`, branch `agent/w33-corpus`, based on `adc2bd6`.
Gate lane `gate-w33d`. Logs under `/root/w33-logs/corpus-*`.

Every figure below carries the command that produced it and the tree it ran on. The corpus is
read-only and nothing was written into `.local/`.

**Where the corpus is, which is not where the brief says.** `.local/norms/corpus/` does not
exist in `/root/w33corpus`. `.gitignore` excludes `.local/`, and `git worktree add` copies
tracked files only, so a linked worktree has no corpus at all — mine holds
`.local/{pip-cache,uv,uv-cache}` and nothing else. The corpus lives in the **primary
checkout**, `/root/projects/PDF-Analysis/.local/norms/corpus/`, and every command in this
document reads it there. A session that took the brief's path literally inside its own
worktree would have found nothing, which is `OPERATING_CONSTRAINTS.md` §12 applied to a path
again.

---

## 1. Every figure, re-measured

### 1.1 The corpus as it is

| Measured | Value | Command |
|---|---|---|
| documents | 674 | `ls -1d /root/projects/PDF-Analysis/.local/norms/corpus/*/ \| wc -l` |
| PDF pages | 28 251 | `MANIFEST.json` → `summary.totals.pdf_pages` |
| blocks | 28 249 | `MANIFEST.json` → `summary.totals.blocks`; independently re-counted from all 674 `blocks.json` |
| `## Page` headings in `results.md` | **28 249** | full parse, `/root/w33-logs/corpus-measure.log` |
| characters across all 674 `results.md` | **74 642 798** | sum of `len(bytes.decode('utf-8'))` over 674 files |
| `coords_norm == [0.0, 0.0, 1.0, 1.0]` | **28 249 of 28 249** | `/root/w33-logs/corpus-scratch/blocks-geometry.txt` |
| `polygon_points is null` | **28 249 of 28 249** | same |
| `shape_type` | `rectangle` ×28 249 | same |
| block status | `recognized` 28 246, `failed` 3 | same |

**74 642 798 is `R-16`'s figure to the character.** It is the total of the whole file
including scaffolding, not of the recognised text; the recognised text is 69 193 145
characters. The geometric premise `R-16` rests its page-anchoring ruling on holds exactly:
there is no geometry in this corpus to anchor to.

### 1.2 Segmentation, mine against `R-16`'s

Run: `.venv/bin/python /root/w33-logs/corpus-scratch/measure.py` at `283de7c`, output at
`/root/w33-logs/corpus-measure.log`, per-document rows at `/root/w33-logs/corpus-per-document.tsv`.
Reconciliation: `/root/w33-logs/corpus-scratch/reconcile.py` → `/root/w33-logs/corpus-reconcile.log`.

| | `R-16` | **W33, my method** | W33 under `R-16`'s implied method | difference to `R-16` |
|---|---:|---:|---:|---:|
| paragraph candidates | 455 907 | 483 058 | **453 575** | −0.51 % |
| discarded | 136 177 | 134 281 | **134 281** | −1.39 % |
| discard rate | 29 % | 27.80 % | **29.61 %** | +0.6 pp |
| substantive paragraphs | 319 730 | 348 777 | **319 294** | **−0.14 %** |
| average paragraph, characters | 192 | 173 | **185** | −3.6 % |
| numbered clauses | 71 934 | 88 099 | **72 697** | +1.06 % |
| chunks at ~1200 characters | 58 021 | 55 702 | **54 465** | −6.1 % |
| average chunk, characters | 1 072 | 1 096 | **1 094** | +2.1 % |
| vectors, `halfvec` 1024 | 0.11 GB | **0.114 GB** | 0.111 GB | +3 % |

**The one methodological difference, isolated.** `R-16`'s counts are reproducible to within
half a percent on the assumption that **markdown headings were not paragraph candidates at
all**. Removing the 29 483 headings from my candidate population moves candidates from
483 058 to 453 575 (`R-16`: 455 907) and substantive paragraphs from 348 777 to 319 294
(`R-16`: 319 730, a gap of **436 paragraphs in 674 documents**). No other single choice
accounts for the difference, and with it made every remaining figure lands within a few
percent. I take that as a reproduction rather than a discrepancy.

**I keep the headings, deliberately, and that is the right-hand column's whole content.** A
heading in this corpus is `##### 1. ОБЩИЕ ПОЛОЖЕНИЯ` — the clause title that names the body
underneath it. 15 402 of the 29 483 headings carry a clause number. Dropping them at
segmentation throws away the section title of every clause in the corpus, which is signal a
retrieval layer wants and cannot recover afterwards. They are kept and tagged
`ParagraphKind.HEADING`, so a consumer that disagrees can weight or drop them without
re-parsing 5.1 GB.

**Clause counting.** 88 099 paragraphs open with a clause number under my rule
(`^\d+(\.\d+)*\.?\s+\S`), of which 72 697 are body and 15 402 are headings. The body figure
is 1.06 % above `R-16`'s 71 934, which is the closest agreement of any figure here and
suggests `R-16` used a near-identical rule over a near-identical population.

### 1.3 The embedding cost, and the part of it I could not verify

| | `R-16` | W33 | command |
|---|---:|---:|---|
| chunks | 58 021 | **55 702** | `/root/w33-logs/corpus-load-estimate.log` |
| chunk text, characters | ~62 M | **61 027 315** | same |
| chunk text, **UTF-8 bytes** | — | **103 036 052 (98.3 MiB)** | same |
| text "in the database" | ~62 MB | **~103 MB** | same |
| vectors, `halfvec` 1024 | 0.11 GB | **0.114 GB** | same |
| vectors, `float32` 1536 | 0.33 GB | **0.342 GB** | same |
| tokens to embed once | ~15.6 M | **unverified — see below** | — |

**`R-16`'s ~62 MB of text is a character count read as a byte count, and the corpus is
Cyrillic.** Russian characters are two bytes in UTF-8, so 61 027 315 characters of chunk text
is **103 036 052 bytes — 66 % more than the figure the ruling budgets for.** Both numbers are
in the table so the next reader can see which is which. The vector figures are unaffected and
match.

**The token figure is not measured and I will not present it as though it were.** `R-16`'s
~15.6 M tokens over ~62 M characters implies 3.99 characters per token. No tokenizer is
installed in this lane (`tiktoken`, `transformers`, `tokenizers`, `sentencepiece` — all
absent; `anthropic` is present but counting through it means a network call this stream is not
authorised to make), and installing one would touch `pyproject.toml`, which is forbidden. What
can be said without one: **BPE tokenizers are markedly less efficient on Cyrillic than on
Latin**, commonly 2.5–3.5 characters per token rather than 4, which over 61 027 315 characters
gives:

| characters/token | tokens |
|---:|---:|
| 3.99 (`R-16`'s implied ratio) | 15.3 M |
| 3.5 | 17.4 M |
| 3.0 | 20.3 M |
| 2.5 | 24.4 M |

**So the embedding bill may be up to 1.6× `R-16`'s estimate, and this is unverified, not
conservative.** The first thing the embedding stream should do is count tokens with the actual
model's tokenizer over the actual chunk text; it is a minutes-long measurement and it moves a
real cost.

### 1.4 The chunk-length tail, which nobody has looked at

| threshold | chunks | share |
|---:|---:|---:|
| > 1 200 characters | 3 666 | 6.58 % |
| > 2 000 | 864 | 1.55 % |
| > 8 000 | 73 | 0.13 % |
| > 16 000 | 24 | 0.04 % |
| **longest chunk** | **62 359** | — |

The chunker never splits a paragraph, so a paragraph longer than the target becomes a chunk on
its own. 6.58 % of chunks exceed 1200 characters for that reason, and the longest is a 62 359
character table transcribed with no blank line inside it. **An embedding model with an input
ceiling will reject or silently truncate these.** It is a decision for the embedding stream —
split long tables on row boundaries, or embed a summary, or accept truncation and say so — and
it is recorded here rather than resolved silently. 33.4 % of chunks (18 599) span more than one
page, and 57.6 % (32 086) carry at least one numbered clause.

---

## 2. The bounded context, and the argument for it

**`src/auditmanager/norms/`.**

The sixteen contexts in the tree are `access analysis api bootstrap comparison decisions
documents export exports findings ingest jobs operations runs shared storage workers`. A
corpus of external regulations is none of them, and the argument is about ownership and
lifecycle rather than about subject matter.

- **Not `documents`.** `documents` owns what a customer uploads into a project, keyed to that
  project, created and deleted with it. A norm is owned by nobody, arrives in bulk, is
  byte-identical for every customer, and is replaced wholesale when the corpus is refreshed.
  They share the English word "document" and no aggregate, no identity space and no lifecycle.
  Putting norms in `documents` would put 674 rows nobody's project owns inside an aggregate
  whose every invariant is *"belongs to exactly one project"*.
- **Not `ingest`.** `ingest` publishes one uploaded blob under an idempotency key, with a
  temporary→verify→publish sequence and reconciliation against S3. Nothing in the corpus is
  uploaded, raced for, or reconciled; it is a drop that is read.
- **Not `analysis`.** `analysis` runs an engine over one run's documents and produces findings.
  Segmentation is a deterministic parse with no engine, no cost ceiling and no run.
- **Not `shared` and not a `corpus` utility module.** `AGENTS.md` §4 forbids *"generic
  repository/base service/global utils without proven semantics"*. `corpus` is a container
  word — a corpus of what? — and a module named for a container invites the next unrelated
  body of text to land in it. `norms` names the subject: ГОСТ, СП, СНиП, ВСН, приказы,
  постановления. The domain language the ruling itself uses is *"the normative corpus"*.

**Why it is a context rather than a package.** It owns an identity space no one else owns (a
corpus snapshot and the chunks under it), a lifecycle no one else has (drawn, dated,
attributed, refreshed wholesale), and it hands other contexts a read model — chunks with a
page anchor — rather than an aggregate they mutate. `ADR-0012` already says the similar-case
index is a rebuildable projection and never a source of truth; the chunk set is the same kind
of thing, and this context is where the rebuild lives.

**No deep imports, in either direction.** `norms` imports nothing from another context, and
nothing imports it yet. One module, `corpus_source.py`, touches the filesystem; everything else
takes text and returns values. **No new dependency** — the parse is `re`, `hashlib`, `json` and
`pathlib`, and if segmentation had seemed to want a markdown library the answer would have been
to stop and report rather than touch `pyproject.toml`.

| module | holds |
|---|---|
| `model.py` | `Paragraph`, `Chunk`, `SegmentationReport`, `CorpusTotals`, `ParagraphKind`, `SourceAttribution` |
| `running_heads.py` | the publisher-noise list and the repeated-offcut rule |
| `segmentation.py` | the `results.md` parse: pages, blocks, recognised text, paragraphs |
| `chunking.py` | joining paragraphs into ~1200-character chunks |
| `snapshot.py` | `R-17`'s identifier and its derivation |
| `corpus_source.py` | the only module that opens a file, and only for reading |

---

## 3. The snapshot identifier

### 3.1 What it is

```
<first-draw>..<last-draw>+<undated>d.<content-digest-12>
```

For the corpus as it stands:

```
2026-07-23..2026-08-20+17d.4b74348debf7
```

Full digest `4b74348debf7788d4eccb551fe4d9b2f58bde7bc1342f216561ef7e7ad6420d4`, from
`.venv/bin/python /root/w33-logs/corpus-scratch/measure.py`.

### 3.2 How it is derived

Three parts, each answering a question the others cannot.

1. **The window** — the earliest and latest `Дата сохранения` the corpus states about itself,
   read out of the documents rather than configured, so it cannot drift from what it describes.
2. **The undated count** — how many documents the window does *not* cover, in the identifier
   itself. A reader who sees `+17d` asks what those seventeen are; a reader who sees only a
   window does not know there is anything to ask about.
3. **The content digest** — SHA-256 over `(slug, source document id, sha256(results.md))` for
   every document, **sorted before a byte is hashed**, truncated to 12 hex characters in the
   identifier with the full 64 kept on the snapshot row.

**The dates are what the corpus says; the digest is what it is.** A refresh that reissues a
ГОСТ under an unchanged save date moves no date at all. If the identifier were the window
alone that refresh would be invisible, and verdicts taken against the old text would claim to
have been taken against the new — which is exactly the failure `R-17`'s recorded consequence
exists to prevent. `test_one_changed_byte_anywhere_changes_the_snapshot` holds both halves: the
identifier changes and the window does not.

The sort is not tidiness. A filesystem walk has no guaranteed order and the corpus is invisible
to git, so there is no commit name to identify a draw by. Structure, then compute, then write
the value.

### 3.3 Why it is not a single date

The distribution, verified independently of the ruling
(`/root/w33-logs/corpus-scratch/date-distribution.txt`, a full parse of all 674 `results.md`):

| stated `Дата сохранения` | documents |
|---|---:|
| 23.07.2026 | **395** |
| 24.07.2026 | **256** |
| 20.08.2026 | **6** |
| none stated | **17** |

`R-17`'s figures are exact. `grep -c "Дата сохранения" .local/norms/corpus/*/results.md` gives
657 non-zero of 674, which is the 17 exactly. **No document states two different dates** — a
fact the ruling does not claim and that is worth having, because it means the per-document date
is well-defined and the window is a genuine min/max rather than an envelope over ambiguity.

*"As at 20.08.2026"* is false for 668 of 674 documents. *"As at 23.07.2026"* is false for 279.
No single date is true of the 17 at all. **A single date is not a conservative approximation of
this corpus; it is a false statement about most of it.** `CorpusSnapshot.footnote_window`
returns the window and returns it as a window even when both ends fall on one day, so the
appendix phrase does not quietly collapse back into a date the first time a corpus is drawn in
one sitting.

### 3.4 What a chunk row carries

Every chunk carries the corpus-snapshot identifier as a field —
`Chunk.snapshot_id` — plus `document_slug`, `page_first`, `page_last`, `char_offset`,
`char_length`, `paragraph_count`, `clause_numbers` and `contains_clause`. The
per-document draw date and source attribution live on the document row the chunk joins to,
because they are per-document facts and duplicating them on 55 702 rows would invite the two
copies to disagree.

**One point where I read the ruling narrowly and the owner may want to read it differently.**
`R-17` says documents are *"not pinned to versions and their revisions are not qualified"*. I
propose recording the observed `Дата сохранения` per document, which is **not** a version pin
and **not** a revision qualification — it is transcribing what the file says about itself, and
it is the only thing that makes the corpus-level window auditable rather than asserted. It
costs four bytes a document. If the owner reads `R-17` as forbidding any per-document date,
drop `norm_document.drawn_on`: the snapshot-level window survives, and what is lost is the
ability to answer *"which of the three draws was this document in"* after the fact.

---

## 4. The proposed table shape

**No migration is proposed and `db/` was not touched.** This is a shape for the owner of the
migration slot to take or refuse. `ADR-0005` puts chunk text, metadata and vectors in
PostgreSQL; `ADR-0006` puts source PDFs and crops in private S3 by `blob_id`.

### `corpus_snapshot`

| column | type | why |
|---|---|---|
| `id` | `text` PK | the derived identifier, `2026-07-23..2026-08-20+17d.4b74348debf7`. Readable on sight and derived from content, so two people who draw the same corpus agree without coordinating |
| `drawn_from`, `drawn_to` | `date NULL` | the window. Two columns, not a `daterange`, because the footnote prints two dates and a range type would have to be unpacked to print them |
| `undated_documents` | `integer NOT NULL` | the count the window does not cover. In the table as well as in the id, so a query can find it without parsing a string |
| `document_count` | `integer NOT NULL` | what the digest was taken over |
| `content_digest` | `char(64) NOT NULL` | the full SHA-256. The id truncates; nothing depends on the truncation |
| `created_at` | `timestamptz NOT NULL` | when the snapshot was loaded, which is not when the corpus was drawn |

### `norm_document`

| column | type | why |
|---|---|---|
| `id` | `text` PK (ULID) | opaque identity. `AGENTS.md` §4 forbids a path or filename as identity, and the slug is a directory name |
| `corpus_snapshot_id` | `text NOT NULL REFERENCES corpus_snapshot` | a document belongs to the draw it came in |
| `slug` | `text NOT NULL` | the directory name, as a **display and join attribute**, never as identity. `UNIQUE (corpus_snapshot_id, slug)` |
| `source_document_id` | `text NOT NULL` | the pipeline's `doc_<32 hex>`, unique 674/674 per the manifest. Provenance into the drop, not our identity |
| `title` | `text NOT NULL` | from the `# Document:` line |
| `doc_type` | `text NOT NULL` | ГОСТ / СП / СНиП / …, 23 values in this drop |
| `page_count`, `block_count` | `integer NOT NULL` | and they are **different numbers** — see §7 |
| `drawn_on` | `date NULL` | the stated `Дата сохранения`. `NULL` for the 17, which is the honest value and not a default |
| `source_attribution` | `text NOT NULL CHECK (IN ('consultant_plus','unattributed'))` | `R-17`'s footnote names one source and it is wrong for 17 documents. An enum-shaped check rather than a boolean, because a third source will appear |
| `pdf_blob_id` | `text NULL` | `ADR-0006`. The 712 MB of source PDFs and 4.04 GB of crops stay in S3; the database holds the reference |

### `norm_chunk`

| column | type | why |
|---|---|---|
| `id` | `text` PK (ULID) | opaque, sortable, stable across a reload |
| `norm_document_id` | `text NOT NULL REFERENCES norm_document` | |
| `corpus_snapshot_id` | `text NOT NULL REFERENCES corpus_snapshot` | **`R-17`'s consequence, on the row.** Denormalised deliberately: a verdict cites a chunk, and the question *"which corpus was this decided against"* must be answerable without a join through a document that may since have been deleted |
| `ordinal` | `integer NOT NULL` | position in the document. `UNIQUE (norm_document_id, ordinal)` |
| `page_first`, `page_last` | `integer NOT NULL` | `R-16`'s page anchoring. Two columns because 33.4 % of chunks span more than one page, and the expert is shown one crop per page in the span |
| `char_offset`, `char_length` | `integer NOT NULL` | offset into the document's **recognised text** — the concatenation of block bodies in block order, defined once in `segmentation.recognised_text` |
| `contains_clause` | `boolean NOT NULL` | the flag the brief requires, on the row rather than derived, so it can be indexed |
| `clause_numbers` | `text[] NOT NULL DEFAULT '{}'` | which clauses. A GIN index makes *"find the chunk for СП 52.13330 clause 7.2.4"* a lookup rather than a scan |
| `text` | `text NOT NULL` | `ADR-0005` |
| `char_count` | `integer GENERATED ALWAYS AS (length(text)) STORED` | derived, so it cannot disagree |
| `content_sha256` | `char(64) NOT NULL` | the determinism check made queryable, and the key for *"is this chunk unchanged since the last snapshot"* on a refresh |
| `embedding` | `halfvec(1024) NULL` | `ADR-0005` puts vectors in PostgreSQL via pgvector. `NULL` until the embedding stream runs, which is not this stream |

**What it costs to load**, from `/root/w33-logs/corpus-load-estimate.log`:

| | |
|---|---:|
| `norm_chunk` rows | 55 702 |
| chunk text, UTF-8 | **103 036 052 bytes (98.3 MiB)** |
| `norm_document` rows | 674 |
| `corpus_snapshot` rows | 1 |
| vectors when filled, `halfvec(1024)` | 114 MB |
| **total PostgreSQL, text + vectors, before indexes and TOAST overhead** | **~220 MB** |
| S3, unchanged by this | 4.04 GB crops + 712 MB PDFs |
| wall time to parse all 674 and build every chunk | **3.4 s** (single process, `/root/w33-logs/corpus-measure.log`) |
| wall time to derive the snapshot identifier | **0.4 s** |

The segmentation is not the expensive part of `R-16` and never was. The embedding is.

---

## 5. Determinism, and every guard's mutation red

### 5.1 The determinism proof

Two tests, because one of them cannot see the failure the other can.

- `test_two_runs_over_one_input_are_byte_identical` — segments and chunks the same input twice
  in one process and compares the **serialised** output, field by field for reports,
  paragraphs and chunks. A serialisation comparison rather than a field list, so a field added
  later is covered without anyone remembering to extend the test.
- `test_the_run_does_not_depend_on_the_process_it_runs_in` — runs the pipeline in **three
  fresh interpreters under `PYTHONHASHSEED` 0, 1 and 4242** and asserts the three outputs are
  one string. This is what covers the `frozenset` in the offcut rule; the in-process test
  cannot, because both of its runs share one process and therefore one seed. The subprocess
  derives its `PYTHONPATH` from `auditmanager.norms.__file__` — the module the test actually
  imported — and **not** from its own file path, which is `OPERATING_CONSTRAINTS.md` §2: aimed
  at the worktree it would have been blind to every mutation in the copy.
- `test_the_snapshot_identifier_does_not_depend_on_directory_order` — 25 fingerprints shuffled
  five times under a seeded RNG, one identifier.

### 5.2 The anti-vacuity sweep

Copy built with `make mutation-copy MUT=/root/w33corpus-mut`
(`/root/w33-logs/corpus-mutation-copy.log`, exit 0). **Baselined unmutated first**:
`.venv/bin/pytest tests/integration/norms -o pythonpath=/root/w33corpus-mut/src -q` →
`29 passed`, and the copy proved to be the imported tree
(`IMPORTED /root/w33corpus-mut/src/auditmanager/norms/__init__.py`).

Sweep: `bash /root/w33-logs/corpus-scratch/mutate.sh` → `/root/w33-logs/corpus-mutations.log`.
**Nineteen mutations, nineteen reds, each naming the test that belongs to it.**

| | mutation | pytest | red, verbatim |
|---|---|---|---|
| G1 | `running_heads.py`: drop `"КонсультантПлюс"` from the noise list | 1 | `E AssertionError: 'КонсультантПлюс' survived segmentation` |
| G2 | `^Страница\s+\d+\s+из\s+\d+$` → `Страница` | 1 | `E assert False` on `assert any(text.startswith("Страница документа") ...)` |
| G3 | noise test `all(...)` → `any(...)` | 1 | `E AssertionError: dropping this would lose clause 1.9 with the stamp` |
| G4 | offcut rule `seen > 1` → `seen > 0` | 1 | `E AssertionError: an ellipsis-terminated paragraph occurring once is body text, not an offcut` |
| G5 | offcut rule stops stripping trailing closers | 1 | `E AssertionError: the truncated title is reprinted on both pages and is a running head` |
| G6 | clause pattern drops the separator requirement | 1 | `E AssertionError: assert (... clause_number='2000', text='2000')] and '2000' is None)` |
| G7 | `page_label = int(match.group(1))` → `pages + 1` | 1 | `E assert [2, 3] == [1, 3]` |
| G8 | paragraph offset searches from zero every time | 1 | `E AssertionError: assert 0 != 0` |
| G9 | attribution always returns `CONSULTANT_PLUS` | 1 | `E AssertionError: assert <SourceAttribution.CONSULTANT_PLUS: 'consultant_plus'> is <SourceAttribution.UNATTRIBUTED: 'unattributed'>` |
| G10 | digest hashes in directory order instead of sorted | 1 | `E AssertionError: assert '2026-07-23......64770ca309bb' == '2026-07-23......d94c43355260'` |
| G11 | identifier drops the content digest | 1 | `snapshot_id='2026-07-23..2026-07-23+17d'` — 5 failed |
| G12 | `footnote_window` returns `drawn_to` alone | 1 | `E AssertionError: assert '2026-08-20' == '2026-07-23..2026-08-20'` |
| G13 | undated documents counted as 0 | 1 | `'undated+0d.3403a7a42467'.startswith` — 3 failed |
| G14 | empty corpus given an identifier instead of refused | 1 | `E Failed: DID NOT RAISE ValueError` |
| G15 | chunker splits a paragraph at the target | 1 | `E AssertionError: assert 'яяяяяяяяяяяя...' == 'яяяяяяяяяяяя...'` |
| G16 | `page_last` = the first page of the span | 1 | `E assert (5, 5) == (5, 6)` |
| G17 | chunker drops the clause numbers | 1 | `E AssertionError: assert () == ('4.2',)` |
| G18 | chunker ignores the target | 1 | `E assert [5] == [2, 2, 1]` |
| G19 | chunker accepts a nonpositive target | 1 | `E Failed: DID NOT RAISE ValueError` |

### 5.3 The two mutations that first reddened nothing, and which was which

Rule 7 asks which of *weak guard* or *insufficient mutation* it was. It was one of each.

- **G8 — the guard was weak.** Rewriting the offset search to start from zero every time
  reddened nothing, because no fixture repeated a line inside one block. The corpus does — a
  table's units row, a repeated `Примечание`. Two chunks would have claimed one position and
  nothing downstream could have noticed.
  `test_two_identical_paragraphs_in_one_block_get_two_different_offsets` was added; G8 now
  reddens with `assert 0 != 0`.
- **G17 — the mutation was insufficient.** I wrote
  `clause_numbers=() or tuple(x for x in () if x) or tuple(` , and `()` is falsy, so the
  expression evaluated to the original tuple. A no-op mutation, and the guard was fine. The
  corrected mutation replaces the whole expression with `clause_numbers=(),` and reddens with
  `assert () == ('4.2',)`.

### 5.4 A third finding, about the sweep itself

**The first sweep was reading stale bytecode, and nineteen greens and reds were partly
attributable to the wrong mutation.** `__pycache__` validates a `.pyc` against the source's
mtime **in whole seconds** plus its size. Two same-size mutations to one file inside one second
leave the first one's bytecode live. G3 (`all(` → `any(`, same length) and G4 (`seen > 1` →
`seen > 0`, same length) ran 0.15 s apart, and **G4's run executed G3's mutation and reddened
G3's test** — which is what exposed it, because G4's red named a function G4 had not touched.

Reproduced in isolation:

```
first import : aaa
pyc header source-mtime: 1790068372 (seconds since epoch, 1-second granularity)
second import: aaa  <- source says bbb
```

The sweep now purges `__pycache__` and runs under `PYTHONDONTWRITEBYTECODE=1`, and was re-run
from scratch. **This generalises beyond this lane**: any fast mutation sweep over same-size
edits to one file on this host has the same trap, and its symptom is a red that names a test
belonging to the previous case — which is easy to read as a broad guard rather than as
contamination. It belongs in `OPERATING_CONSTRAINTS.md` §10 if the integrator agrees.

---

## 6. The seventeen documents with no ConsultantPlus marker

`R-17`'s footnote names one source. These seventeen do not come from it.

```
ГОСТ_13463-77            ГОСТ_2822-78             ГОСТ_32498-2020
ГОСТ_33367-2015          ГОСТ_33542-2015          ГОСТ_379-2025
ГОСТ_4907-81             ГОСТ_6133-2026           ГОСТ_8732-2025
ГОСТ_8909-75             ГОСТ_IEC_61347-2-13-2021 ГОСТ_Р_21.101-2026
ГОСТ_Р_57058-2016        ГОСТ_Р_72509-2026        ПЭУ_7_Изд
СП_112.13330.2011        Постановление_ФАС_Поволжского_округа_от_20.06.2013_…
```

**They carry no ConsultantPlus marker in any form.** Measured across the five markers
(`/root/w33-logs/corpus-scratch/cp-markers.txt`): `КонсультантПлюс` 0, `consultant.ru` 0,
`надежная правовая поддержка` 0, `Дата сохранения` 0, in all seventeen. `R-17`'s claim is
exact.

**And there is independent corroboration the ruling does not have, from the PDF producer
field.** Of the 657 ConsultantPlus documents, **655 were produced by `Microsoft® Word 2021`
and 2 by a producer literally named `КонсультантПлюс`** — one homogeneous export pipeline. The
seventeen are spread across **eight different producers**: 9 × `Adobe Acrobat 11.0.11`,
2 × `PyPDF2`, and one each of `Microsoft® Word 2021`, `iLovePDF`, `TCPDF 6.10.0`,
`Iceni Technology`, `wkhtmltopdf`, and one with no producer at all. The split is not a gap in
one export; **it is a different acquisition.** And one of them says so on every page:
`ГОСТ_Р_72509-2026` prints `Страница документа - https://GostExpert.ru/gost/gost-72509-2026`
**49 times** — a second publisher's watermark, in a corpus whose footnote will name only the
first.

**What that does to attribution, and what I did about it.**

1. **A blanket footnote is inaccurate for 2.5 % of the corpus**, and prose in an appendix
   cannot be interrogated. So `SourceAttribution` is a **field** — `consultant_plus` or
   `unattributed` — on every document row, and the guard `G9` proves the classifier can fail.
   With it, whoever writes the appendix can produce the exact list, and a verdict citing a
   clause of one of the seventeen can be told apart from one citing ConsultantPlus.
2. **`unattributed` is the honest value and I did not guess further.** GostExpert.ru is
   visible in one document; the other sixteen state nothing. Inventing
   `SourceAttribution.GOST_EXPERT` from one watermark would be an unverified claim dressed as
   data, and the enum is shaped so a third value costs one migration when someone establishes
   where they came from.
3. **The rights question is untouched and is not mine.** `R-17` settles attribution and says
   explicitly that the right to use a particular edition is a separate question. Seventeen
   documents of unknown provenance make that question sharper, not different.
4. **The noise filter had to learn about them before it could be trusted.** `Страница ` is a
   ConsultantPlus footer in 657 documents and body text in one of the seventeen. The rule is
   anchored — `^Страница\s+\d+\s+из\s+\d+$` — and `G2` proves the anchor is load-bearing: the
   unanchored form deletes all 49 GostExpert lines. **This is the first concrete cost of the
   seventeen not being ConsultantPlus, and it would have been a silent one.**

---

## 7. Every premise I measured and found false

**1. The corpus is not in this worktree.** The brief points at `.local/norms/corpus/` as though
it were a path in the tree. `git worktree add` copies tracked files only and `.local/` is
ignored, so `/root/w33corpus/.local/` holds package caches and nothing else. The corpus exists
once on this host, in the primary checkout. Every brief that sends a worktree session at the
corpus should give the absolute path.

**2. `R-16`'s "~62 MB of text in the database" is a character count, and the corpus is
Cyrillic.** 61 027 315 characters of chunk text is **103 036 052 UTF-8 bytes**, 66 % more.
Measured; the vector figures in the same sentence are correct and unaffected.

**3. `R-16`'s ~15.6 M tokens rests on 3.99 characters per token, which is a Latin-text ratio.**
I could not verify it — no tokenizer in the lane and adding one is forbidden — and I am
stating that in the conclusion rather than in a footnote. At 2.5–3.5 characters per token the
figure is 17.4–24.4 M, so the one real cost in `R-16` may be understated by up to 1.6×.

**4. "One block per page" is not merely off by two — `results.md` cannot see the two pages at
all.** The brief and the ruling both reconcile 28 249 blocks with 28 251 pages by noting two
uncovered pages. What neither says is that **`results.md` prints no `## Page` heading for a
page with no block**: my parse finds 28 249 headings, not 28 251. The surviving labels are the
true PDF page numbers and do not renumber over the gap — `ГОСТ_Р_50030_2-2010` runs 1..225 with
22 and 210 absent — so the page anchor still fetches the right crop, but **any page-level
coverage figure derived from `results.md` is blind to those two pages, and would be blind to
two thousand if a future drop were worse.** The field in the code is named `page_headings` for
this reason.

**5. The five ConsultantPlus phrases are not the whole noise vocabulary.** A sixth running-head
family exists — `Страница документа - https://GostExpert.ru/…`, 49 occurrences — in a document
outside the ConsultantPlus set. It is *kept* by my filter, deliberately, because discarding it
would need a rule that also eats the 49; the point is that the brief's list is the vocabulary
of one publisher and the corpus has at least two.

**6. The truncated-title running head is not always terminated by the ellipsis.** The export
quotes the title and truncates it **inside** the quotes as readily as after them: **838 lines
in 102 documents end `..."` rather than `...`**. My first rule tested the last character, and
those 838 running heads survived segmentation. It was my own fixture that reddened it, not
review. The rule now strips trailing closers first, and `G5` proves it can fail.

**7. The recognised text is not only the norm's text. 34 documents carry leaked LLM reasoning
in English, as body content.** 79 occurrences of `The user wants me to …` and 66 of
`transcription engine`, at the head of transcribed tables:
*"The user wants me to act as a strict transcription engine for Russian construction
documents…"*. The recognition pipeline's prompt or chain-of-thought is inside `results.md`
where the document's text should be, and it is what makes the longest paragraph in the corpus
62 359 characters. **Vectorising the corpus as it stands would embed that as normative text.**
Separately and independently measured by script rather than by phrase: 706 paragraphs of
≥200 characters across 201 documents are predominantly Latin — much of that is legitimate
(LaTeX formulas, ISO citations in reference lists) and some is LLM *descriptions of figures*
(*"A side view of a screw with a semi-circular head. Dimensions include: D (head diameter)…"*),
which is also not the norm's text. **This is the largest open quality question in `R-16` and
nothing in the ruling or the brief mentions it.** I did not filter it: deciding what is a
transcription artefact and what is a legitimately Latin clause is a judgement, not a markdown
parse, and it needs the owner or a dedicated pass.

**8. `R-16`'s 29 % discard rate is right and its candidate population is not the obvious one.**
The figures reproduce to within 0.14 % only if markdown headings were never candidates. That is
a defensible choice and I made the opposite one, with the reason in §1.2. The number to carry
forward is that the two methods agree — this is a reproduction, not a discrepancy.

**9. The gate baseline in the brief is not the baseline at `adc2bd6`. The base commit is red.**
See §8. This is the finding with the shortest fuse, because three other wave-33 sessions are
standing on the same commit.

**10. And one about the sweep, not the corpus** — the `__pycache__` second-granularity trap in
§5.4, which made a mutation sweep attribute one case's red to another.

---

## 8. Verification

`git status --porcelain` clean before the gate. `make gate` from a committed-clean tree at
`283de7c`:

```
make gate > /root/w33-logs/corpus-gate.log 2>&1; echo "EXIT=$?" >> /root/w33-logs/corpus-gate.log
```

| component | baseline in the brief | this run | |
|---|---|---|---|
| foundation | 35 | **35 passed in 31.29s** | ✅ |
| battery | 2016 / 5 / 169 | **2044 passed, 2 failed, 5 skipped, 169 subtests** | ❌ — see below |
| frontend | 811 passed + 1 skipped in 58 files | **811 passed, 1 skipped, 58 files** | ✅ |
| `git diff --check` | clean | exit 0 | ✅ |

`2044 + 2 = 2046 = 2016 + 30`, the thirty tests this branch adds. Every one of the thirty
passes.

**The two failures are `adc2bd6`'s, not mine, and `adc2bd6` is where they started.**

```
FAILED tests/integration/composition/test_proxy_tls_path.py::test_the_overlay_introduces_no_name_that_could_hold_a_secret
FAILED tests/integration/composition/test_proxy_tls_path.py::test_the_base_deployment_is_unchanged_by_any_of_this
```

Driven rather than inferred, in a throwaway detached worktree at each commit:

| commit | `pytest tests/integration/composition/test_proxy_tls_path.py -q` |
|---|---|
| `235ff3a` | 9 passed |
| `eae032c` | 9 passed |
| `e584ce3` | 9 passed |
| **`adc2bd6`** | **2 failed, 7 passed** |

The cause is in `adc2bd6` itself, `fix(deploy): the stand binds to loopback`:

- it adds one **comment line** to `infra/deploy/compose.server.yml` reading
  `# should publish — one behind a real firewall, serving TLS on \`ALPHA_HTTPS_PORT\` under`,
  and `test_the_base_deployment_is_unchanged_by_any_of_this` asserts
  `assert "tls" not in base.lower()`;
- it adds `${ALPHA_BIND_ADDRESS:-127.0.0.1}` to `infra/deploy/proxy/compose.tls.yml`, and
  `test_the_overlay_introduces_no_name_that_could_hold_a_secret` asserts the overlay's
  substituted names are exactly `{"ALPHA_HTTPS_PORT"}`.

Whether the test or the commit is wrong is the infra owner's call, and `infra/**` is a
forbidden hotspot for this lane so I did not touch either. My reading, offered and not acted
on: the first assertion is over-broad — it forbids the *word* `tls` in a comment, and a
comment cannot enable a listener — while the second is doing its job and has found a genuinely
new substituted name, which happens to be a bind address rather than a secret.

**This is urgent for the integrator rather than for me.** Three other wave-33 sessions are
based on `adc2bd6` and every one of them will meet these two reds at its own gate, with no way
to tell from the red alone that it is not theirs.

---

## 9. Rollback

Additive: four commits, thirteen new files, one new package and one new test directory. Nothing
imports `auditmanager.norms` yet, no composition root, no contract, no migration.

| drop | to lose |
|---|---|
| `283de7c` | a corrected figure in a comment |
| `017a145` | the offset guard and the hardened sweep |
| `90f37e5` | the tests |
| `df162a8` .. `283de7c` (all four) | the whole context; the tree returns to `adc2bd6` exactly |

If the segmenter proves wrong, `git revert` is unnecessary — `git rm -r src/auditmanager/norms
tests/integration/norms` removes every trace, because nothing else references it.

## 10. What is deliberately not here

- **No migration, no schema change.** `db/` untouched. §4 is a proposal.
- **No embeddings, no pgvector call, no model call.** The ~15.6 M–24.4 M tokens are not this
  stream's to spend, and §1.3 says why that range is a range.
- **No contract change.** `contracts/**` untouched.
- **Nothing written into `.local/`.** It was opened read-only; all output is under
  `/root/w33-logs/corpus-*`.
- **No re-segmentation of page images.** `R-16` forbids it and §1.1 confirms the reason
  holds: 28 249 of 28 249 blocks have `coords_norm == [0,0,1,1]`.
