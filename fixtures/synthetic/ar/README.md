# Synthetic AR corpus — the PC-01 acceptance input

**Everything in this directory is synthetic.** It was written by a generator, not
extracted from any document. There are no customer, production or real project bytes, and
no real organisation, address, person or project is named. Owner decision **OD-17** rules
the PC-01 corpus synthetic-only. Nothing that is not produced by
`tools/fixtures/build_ar_corpus.py` belongs here.

This is the **only** AR fixture for PC-01. Ingest, analysis, findings and QA consume these
paths read-only and never add a second one (task `P2-BHV-01`, integration contract).

## Contents

| Path | What it is |
| --- | --- |
| `ar_baseline.pdf` | The baseline: 8-page Russian AR document, embedded text layer, inside the envelope |
| `expected_issues.json` | The expected-issues manifest — the acceptance oracle |
| `SHA256SUMS` | Digest of every file here, verifiable with `sha256sum -c` from this directory |
| `negative/` | One fixture per envelope rule, each violating that rule and no other |

## The oracle

`expected_issues.json` records, for every seeded issue, its category, the pages it spans
and the **exact quotation** on each page, plus the character offset and line index of that
quotation inside the extracted page text.

Three issues are seeded:

| Id | Category | Pages | What is wrong |
| --- | --- | --- | --- |
| `SI-01` | `internal_contradiction` | 2, 6 | Fire-resistance class of the same building given as `II` and as `III` |
| `SI-02` | `internal_contradiction` | 3, 7 | Evacuation exits from the above-ground part given as two and as three |
| `SI-03` | `explicit_placeholder` | 8 | Window infill type left as the literal `уточнить` |

Six **controls** are recorded alongside them. A control is a statement a correct analyzer
must *not* report, and PC-01 precision is measured against them. They are deliberate near
misses, not obvious non-issues:

| Id | Pages | Why a naive analyzer trips on it |
| --- | --- | --- |
| `CTL-01` | 5 | A *third* fire-resistance class — but for the separate gatehouse, not the house |
| `CTL-02` | 4 | Contains the stem `уточн` while describing a decision already made |
| `CTL-03` | 3 | Storey height `3,3 м` — for the ground floor |
| `CTL-04` | 4 | Storey height `3,0 м` — for the typical floors, so CTL-03 is not contradicted |
| `CTL-05` | 2, 6 | The same fire-safety class repeated identically on two pages; a different attribute from `SI-01` |
| `CTL-06` | 7 | An exit count that differs because it is the basement, excluded by the next line |

### Why the quotations can be trusted

In Gate B a grounding gate rejects any model finding whose quotation does not resolve at
its declared anchor, so a quotation that is not really in the text layer would contaminate
every downstream measurement without anyone noticing. The corpus is therefore built so
that this is *asserted*, not assumed:

* every quotation lies wholly within one rendered line, and each line is drawn with a
  single text-showing operator at a single absolute position, so no extractor has to guess
  where a soft wrap or an inter-word gap was;
* the generator refuses to write if any line would overflow the text box;
* after generating the PDF the generator extracts the text back out of the **file bytes**
  with an independent parser and asserts every quotation is present character-for-
  character, on exactly the pages it declares and on no others;
* `tests/contract/fixtures_ar` repeats that assertion against the *committed* file, and
  additionally cross-checks with `pdftotext` when poppler is installed.

## The envelope

`PROTOTYPE_PROFILE.md` §7.1: one unencrypted PDF, at most 25 MiB and 30 pages, every page
carrying extractable embedded text. Scanned, password-protected, mixed-file and companion
inputs fail explicitly; OCR is never silently substituted.

`tools/fixtures/ar_corpus/envelope.py` turns that into rules with stable ids:

| Rule | Meaning |
| --- | --- |
| `ENV-PDF` | the input is a PDF file |
| `ENV-ENCRYPTED` | the PDF is not encrypted or password-protected |
| `ENV-SIZE` | at most 26 214 400 bytes (25 MiB) |
| `ENV-PAGES` | at most 30 pages |
| `ENV-TEXT` | every page carries extractable embedded text |

A rule that could not be evaluated reports `not_evaluated`, never `pass`. An encrypted
file's page count is unknown, not acceptable.

### Negative fixtures

Each violates **exactly one** rule, so a rejection is attributable to the rule that fired.

| File | Violates | Notes |
| --- | --- | --- |
| `negative/encrypted.pdf` | `ENV-ENCRYPTED` | User password `synthetic-user-pw`, owner password `synthetic-owner-pw` (standard security handler, revision 2). Two pages, well inside every other limit |
| `negative/image_only.pdf` | `ENV-TEXT` | Two pages, each one 1-bit image XObject; no text operator anywhere |
| `negative/oversize.pdf` | `ENV-SIZE` | Valid two-page text PDF carried past 25 MiB by one unreferenced padding stream |
| `negative/too_many_pages.pdf` | `ENV-PAGES` | 31 pages, one over the limit, every page with real text |
| `negative/not_a_pdf.txt` | `ENV-PDF` | A UTF-8 text file presented as the source document |
| `negative/companion_archive.zip` | `ENV-PDF` | A ZIP holding a PDF plus companion files |

`oversize.pdf` is 26 MiB in the working tree but roughly 128 KiB as a Git object: the
padding is a repeating uncompressed ASCII line, which Git's own zlib crushes. It really is
over the limit on disk, which is what the fixture has to prove, without permanently
costing the repository 26 MiB.

## Regenerating

```
python3 tools/fixtures/build_ar_corpus.py            # rewrite every artefact
python3 tools/fixtures/build_ar_corpus.py --check    # verify against what is committed
sha256sum -c SHA256SUMS                              # from this directory
```

The generator is byte-deterministic: fixed creation date, fixed document id, a committed
font subset, no filters and no PRNG seeded from the environment. Running it twice produces
identical bytes.

The embedded font is `tools/fixtures/assets/ARCorpusSans.ttf`, a committed 31 KiB glyph
subset. The generator never reads a font from the build machine, so regeneration does not
depend on which fonts happen to be installed. `tools/fixtures/build_font_subset.py`
rebuilds that subset from DejaVu Sans, and is only needed if the document text starts
using a character outside the declared repertoire — in which case the corpus build fails
loudly rather than dropping a glyph.

## Known limits of this corpus

* One document, one discipline (AR), one language. There is no second AR fixture and no
  second discipline by design.
* The seeded issues are unambiguous by construction. Real documents contain borderline
  cases that this corpus does not represent, so a perfect score here is not evidence of
  real-world accuracy.
* The controls cover the near misses that were anticipated. They bound precision against
  *those*; they cannot bound it against a failure mode nobody thought of.
* Layout is plain single-column text. There are no tables, stamps, drawings, rotated
  pages, multi-column text or scanned-then-OCR'd pages, so it exercises text extraction
  but not layout reconstruction.
* `page_geometry_extraction` has nothing interesting to find here: every line is one text
  run, so block structure is trivial.
* The oracle names issues, not sentences. No test asserts model wording (`P2-BHV-01`
  non-goals).
