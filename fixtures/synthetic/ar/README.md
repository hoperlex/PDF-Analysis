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
| `bundles/` | One portal bundle (a ZIP) per synthetic PDF, and `bundle_manifest.json`, the oracle for them |

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
| `negative/not_a_pdf.txt` | `ENV-PDF` | A UTF-8 text file presented as the source document |
| `negative/companion_archive.zip` | `ENV-PDF` | A ZIP holding a PDF plus companion files |

**`ENV-SIZE` and `ENV-PAGES` have no committed fixture.** The limits are 250 MiB and 500 pages
(`W55B-INGEST-01`), and a file that size is never committed. `negative/oversize.pdf` (26 MiB) and
`negative/too_many_pages.pdf` (31 pages) were deleted: the over-size stand-in is a sparse file and
the over-page one a 501-page PDF, both made when a test runs by
`tools/fixtures/portal_bundle/generated.py` (`oversize_sparse_file`, `pdf_with_n_pages`).

## Portal bundles

An upload is now one ZIP, the *portal bundle* (`W55-PLAN.md` B3.1): the PDF, the portal's block
list (`<stem>_blocks.json`), the recognised text (`<stem>_results.md`) and, optionally, the
portal's HTML (`<stem>_results.html`, kept as a digest only) and a stamp audit
(`<stem>_stamp_audit.json`). `bundles/` holds one bundle for every synthetic PDF in this
directory; the PDF inside each is the committed PDF, byte for byte. **They are synthetic**: every
byte was written by `tools/fixtures/build_portal_bundles.py` from the corpus above. The formats
mirror what the portal writes (measured on one real export, which stays outside the repository),
but nothing in them comes from it, and the crop URLs sit under the reserved `.invalid` domain
and are never to be fetched.

| Bundle | Source PDF | Members | Expected |
| --- | --- | --- | --- |
| `bundles/ar_baseline.zip` | `ar_baseline.pdf` | all five: 8 TEXT blocks, 2 IMAGE blocks (one a polygon), 2 STAMP blocks, HTML, stamp audit | accepted |
| `bundles/ar_baseline_minimal.zip` | `ar_baseline.pdf` | the three required, TEXT blocks only | accepted |
| `bundles/ar_baseline_ocr_defects.zip` | `ar_baseline.pdf` | the three required; the recognised text of pages 2-6 carries seeded flaws (Latin homoglyphs, a CJK character, doubled list markers, a mixed-script word) and engineering designations (`1.A`, `B25`, `A500C`, `REI 150`) that must not be flagged | accepted |
| `bundles/image_only.zip` | `negative/image_only.pdf` | the three required; the block list holds no block | refused: `every_page_has_extractable_text` |
| `bundles/image_only_with_block.zip` | `negative/image_only.pdf` | the three required; one TEXT block on each scanned page | accepted |
| `bundles/encrypted.zip` | `negative/encrypted.pdf` | the three required | refused: `not_encrypted` |
| `bundles/pages_31.zip` | `ar_corpus/negatives.py:build_pages_31` | the three required, 31 TEXT blocks | accepted (over the old 30-page limit, inside the 500-page one) |

`bundles/bundle_manifest.json` (schema `ar-portal-bundles/1`) records, for every bundle, the file's
size and SHA-256, each member's name, role, size and SHA-256, the block counts by type, whether it
is `accepted` or `refused` and, for a refusal, the registered `constraint` and its `field`. It is
the oracle INGEST and the judges read. The scanned and encrypted bundles are *well-formed
archives*: they are refused for the PDF inside them. The 31-page PDF of `pages_31.zip` is built by
the corpus generator (`build_pages_31`) and its digest is pinned in `portal_bundle/committed.py`;
it is the deleted `too_many_pages.pdf`, byte for byte. The generated stand-ins (a sparse file past
250 MiB, 501 pages, a page with neither a text layer nor a block, and one archive per bundle rule,
`tools/fixtures/portal_bundle/`) are made when a test runs and are not committed.

`negative/not_a_pdf.txt` and `negative/companion_archive.zip` keep their meaning for the bare-PDF
path until the last step of `W55B-INGEST-01` refuses a bare PDF.

To package a real portal export for a local run (never to commit it), see
`tools/fixtures/assemble_portal_bundle.py <input_dir> <out.zip> [--stamp-audit FILE]`.

```
python3 tools/fixtures/build_portal_bundles.py            # rewrite bundles/ and its SHA256SUMS lines
python3 tools/fixtures/build_portal_bundles.py --check    # verify against what is committed
```

The bundle builder is byte-deterministic like the corpus builder: fixed timestamps, identifiers that
are digests of the stem, no clock and no PRNG. Members are stored or framed as deflate *stored
blocks*, written by hand, so the bytes do not depend on which zlib the machine has. Run
`build_ar_corpus.py` first if the PDFs change: a bundle is only built around the committed PDF.
`build_ar_corpus.py` leaves the `bundles/` lines of `SHA256SUMS` as they are, and
`build_portal_bundles.py` leaves the others.

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
