# PC-02 field-validation corpus

**Everything in this directory is synthetic.** It was written by a generator, not
extracted from any document. There are no customer, production or real project bytes, and
no real organisation, address, person or project is named. Owner decision **OD-17** rules
this corpus synthetic-only, so every manifest record's `provenance` is `synthetic` and
none is `anonymized`.

This is the input to the P04 learning gate. PC-01 established that the machinery works and
that the model can do the task, on **one** document. Whether the findings are
professionally useful is what P04 asks, and this corpus is what makes that question
answerable. A corpus that is too easy produces a flattering number nobody can act on; one
whose ground truth is wrong measures the ground truth rather than the model.

## Contents

| Path | What it is |
| --- | --- |
| `corpus_manifest.json` | The ground-truth oracle: per document its label, SHA-256, page count, byte size, provenance and every seeded issue and control with exact quotations and offsets |
| `documents/` | 14 measurable AR documents, 94 pages, all inside the PC-01 envelope |
| `negative/` | 4 negative-envelope documents, counted separately and excluded from every finding denominator |
| `session_record.schema.json` | JSON Schema for a validation session record (`pc02-session-record/1`) |
| `build_pc02_corpus.py` | The deterministic generator |
| `pc02_corpus/` | Corpus text, layout and negative builders |
| `SHA256SUMS` | Digest of every artefact, verifiable with `sha256sum -c` from this directory |

The session protocol is `docs/program/validation/PC-02_PROTOCOL.md`.

## Composition

14 measurable documents: **5 seeded** and **9 controls**. The seeded count is fixed by task
`P4-QA-01`; the control count carries the whole 12–16 range.

| Label | Role | Pages | Seeded | Controls | Theme |
| --- | --- | --- | --- | --- | --- |
| `PC02-S01` | seeded | 7 | 2 | 4 | Structural fire-hazard class; a `TBD` marque |
| `PC02-S02` | seeded | 6 | 1 | 6 | Total floor area, with a notation-variant decoy |
| `PC02-S03` | seeded | 7 | 2 | 4 | Roof type; a blank insulation thickness |
| `PC02-S04` | seeded | 9 | 2 | 5 | Datum elevation; passenger-lift count |
| `PC02-S05` | seeded | 10 | 2 | 6 | Storey count; an undetermined room purpose |
| `PC02-C01` | control | 5 | 0 | 3 | Three fire-resistance degrees, three objects |
| `PC02-C02` | control | 6 | 0 | 5 | Five heights, five scopes |
| `PC02-C03` | control | 6 | 0 | 5 | Dense `уточн` stems, nothing unfilled |
| `PC02-C04` | control | 7 | 0 | 6 | Six figures, one repeated in two notations |
| `PC02-C05` | control | 6 | 0 | 4 | Exit counts separated by scope |
| `PC02-C06` | control | 5 | 0 | 4 | A thickness the document itself withdraws |
| `PC02-C07` | control | 5 | 0 | 4 | Absence by scope, not incompleteness |
| `PC02-C08` | control | 8 | 0 | 2 | The longest document, and the quietest |
| `PC02-C09` | control | 7 | 0 | 6 | Three classification systems, easy to conflate |

**9 seeded issues** — 6 `internal_contradiction`, 3 `explicit_placeholder`. **64 control
statements** across **12 declared near-miss archetypes**. 86 ground-truth quotations in
all, every one resolved at its declared page and character offset.

### None of the seeded issues repeats a PC-01 attribute

PC-01's three — fire-resistance *degree*, evacuation-exit count, the literal `уточнить` —
were found by a live model run on 2026-09-14. Reusing them would make PC-02 a
re-measurement of a result already in hand, and the task's non-goals forbid a corpus
reverse-engineered from findings the current prompt already produces. Each seeded issue's
`why_seeded` field in the manifest records why it was chosen instead.

### The controls are near misses, not trivial negatives

Precision is measurable against a control a reasonable analyzer could trip on, and
meaningless against one it could not. The 12 archetypes are defined in the manifest under
`control_archetypes`; the sharpest are:

- **`other_object`** — a third fire-resistance degree that belongs to a boiler house.
- **`scope_dependent`** — `этажность корпуса 5 — 12` beside `количество этажей, включая
  подземные, — 13`, which differ by the basement *on purpose*, one line from the seeded
  storey-count contradiction.
- **`notation_variant`** — one total area written `4 812,5 м²` and `4812,5 кв. м`:
  identical to a reader, different to a string comparator, in the same document as a real
  area contradiction.
- **`superseded`** — a datum value the document explicitly withdraws, sitting between two
  that genuinely conflict.
- **`placeholder_stem`** — prose carrying `уточн` while recording a decision already made.

### Filler prose is inert by construction

Every line that is not declared ground truth contains **no digit and no placeholder
token**, and the build refuses to run if that stops being true. An unnoticed number in
boilerplate would be a project attribute nobody declared, and a model that noticed it
would be scored wrong for being right.

## The negative-envelope documents

Counted **separately**. Excluded from every finding denominator and from every gate that
counts measurable documents, G4 included. Each violates **exactly one** rule, so a
rejection is attributable to the rule that fired.

| File | Violates | Notes |
| --- | --- | --- |
| `negative/PC02-N01-encrypted.pdf` | `ENV-ENCRYPTED` | Two pages, user password `synthetic-user-pw`, owner password `synthetic-owner-pw` |
| `negative/PC02-N02-image-only.pdf` | `ENV-TEXT` | Two pages, each a 1-bit image XObject; no text operator anywhere |
| `negative/PC02-N03-oversize.pdf` | `ENV-SIZE` | A valid two-page text PDF carried past 25 MiB by one unreferenced padding stream |
| `negative/PC02-N04-too-many-pages.pdf` | `ENV-PAGES` | 31 pages, one over the limit, every page with real text |

`ENV-PDF` is already covered by the PC-01 negative corpus and is not duplicated here.

`PC02-N03-oversize.pdf` is 26 MiB in the working tree but roughly 128 KiB as a Git object:
the padding is a repeating uncompressed ASCII line, which Git's own zlib crushes. It
really is over the limit on disk, which is what the fixture has to prove.

## Why the quotations can be trusted

A grounding gate downstream rejects any model finding whose quotation does not resolve at
its declared anchor, so a quotation that is not really in the text layer would contaminate
every measurement without anyone noticing. The corpus is therefore built so that this is
*asserted*, not assumed:

- every quotation lies wholly within one rendered line, and each line is drawn with a
  single text-showing operator at a single absolute position, so no extractor has to guess
  where a soft wrap or an inter-word gap was;
- the generator refuses to write if any line would overflow the text box or be drawn into
  the footer band;
- after generating each PDF the generator extracts the text back out of **the file bytes**
  and asserts every quotation is present character-for-character, on exactly the pages it
  declares and on no others — **twice**, once with `ar_corpus.pdfextract` and once with
  `pdfplumber`, which shares no code with the writer;
- `tools/validation/corpus_check.py` repeats all of that against the **committed** files.

## Verifying and regenerating

```
.venv/bin/python tools/validation/corpus_check.py corpus_manifest.json  # from repo root
.venv/bin/python tools/validation/corpus_check.py --self-test
python3 fixtures/validation/PC-02/build_pc02_corpus.py --check          # rebuild + compare
python3 fixtures/validation/PC-02/build_pc02_corpus.py                  # rewrite
sha256sum -c SHA256SUMS                                                 # from here
```

`--self-test` breaks the corpus one way per assertion and requires *that named assertion*
to fire. 23 of the 24 checks are shown both red and green by it; the 24th,
`CHK-INDEPENDENT-AVAILABLE`, is an environment assertion no corpus mutation can arrange
and is proved by running the checker with `pdfplumber` unimportable.

The generator is byte-deterministic: fixed creation date, per-document ids derived from
the document label, a committed font subset, no filters, no PRNG and no clock. Running it
twice produces identical bytes.

## No dependency was added

`docs/program/P02_LOCK.json` pins `pdfplumber` and `pypdf`, and the root lock is a
single-writer hotspot. The PDF writer, the TrueType subsetter and the reference extractor
are session A4's, in `tools/fixtures/ar_corpus/`, imported **read-only**; the embedded
font is A4's committed subset in `tools/fixtures/assets/`. This corpus adds layout,
content and its own negative builders and reuses everything else.

## Known limits

- One document family, one discipline (AR), one language, one country's drafting
  conventions.
- The seeded issues are unambiguous by construction. Real documents contain borderline
  cases this corpus does not represent, so a perfect score here is not evidence of
  real-world accuracy.
- The controls cover 12 anticipated near-miss archetypes. They bound precision against
  *those*; they cannot bound it against a failure mode nobody thought of. The protocol
  therefore reports findings matching neither a seeded issue nor a declared control as
  their own group.
- Layout is plain single-column text: no tables, stamps, drawings, rotated pages,
  multi-column text or scanned-then-OCR'd pages. Text extraction is exercised; layout
  reconstruction is not.
- `session_record.schema.json` is checked structurally, not meta-validated against the
  JSON Schema 2020-12 metaschema: `jsonschema` is not in the lock and this task does not
  take the root lock to add it.
