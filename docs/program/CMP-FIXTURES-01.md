# CMP-FIXTURES-01 — hand-back report

- Task: `tasks/CMP-FIXTURES-01.md`; plan `dispatch/COMPARE-MODULES-PLAN.md` §1.1, §3.2 `R3-14`/`R3-19`, §6.
- Branch `agent/cmp-fixtures-01`, worktree `.local/worktrees/cmp-fixtures-01`, base `5867d704` (task files of the first CMP
  lanes, on `integration/compare-modules`). Commits, oldest first: `2af62130` (writer extensions), `608fdd3e` (generator),
  `dd1e29fc` (committed corpus), `b82383e2` (realistic A1), `9ecf141a` (tests); this report and the task file's Handoff
  are the last commit. Nothing was pushed, merged or tagged.
- Checks follow `R-70`/`R-135`: the task's own required command and the AR-corpus builders' `--check`; no container, no
  database, no full gate.

## 1. Changed files

`git diff --name-only 5867d704..HEAD` before this report: 29 paths, all inside the task's `allowed_paths`.

| Path | What |
| --- | --- |
| `tools/fixtures/ar_corpus/pdfwrite.py` | **additive**: 334 lines added, 0 deleted (`git diff --numstat`); see §3 |
| `tools/fixtures/comparison/__init__.py`, `outlines.py`, `scene.py`, `vs1.py`, `sp1.py`, `build.py` | the generator: TrueType glyph outlines, the scene model and PDF document builder, VS-1, SP-1, the one-command CLI |
| `tools/fixtures/comparison/realistic_a1.py` | the realistic A1 generator (writes where the caller says) |
| `fixtures/comparison/vs1/v1.pdf` … `v5.pdf`, `vs1/answer_key.json` | VS-1 and its key |
| `fixtures/comparison/sp1/old_p.pdf`, `new_r1.pdf`, `new_r2.pdf`, `new_r3.pdf`, `sp1/answer_key.json` | SP-1 and its key |
| `fixtures/comparison/README.md`, `.gitattributes`, `SHA256SUMS` | the corpus description and the one regeneration command; PDFs marked binary; digests of every generated file |
| `tests/contract/fixtures_comparison/` (6 test modules, 1 support module) | 116 tests |
| `docs/program/CMP-FIXTURES-01.md`, `docs/program/tasks/CMP-FIXTURES-01.md` | this report; the Handoff section |

## 2. What is in the corpus

### 2.1 VS-1 — five versions of `СИНТ-01-ЭМ`

Seven sheets over the set's life; each version is one PDF; every vector sheet has a frame and a 185 x 55 mm title
block (designation, sheet title, stage `Р`, sheet number, `Изм.N`, date) written as text with the embedded
`ARCorpusSans` font. As in real sets a sheet keeps the `Изм.` of its **last change**: the version label is the highest
`Изм.` on its sheets (a fact for the profile reader to derive), and a sheet whose stamp changed alone is a
`same_zones_changed` case.

| Sheet | Format | Title | Life |
| --- | --- | --- | --- |
| E01 (1) | A4 | Общие данные | V1–V5; carries the sheet list and, from V4, the permit table |
| E02 (2) | A3 | План освещения. Корпус 1, этаж 1 | V1–V5; dashed axes on an optional-content layer, a tiling-pattern hatch |
| E03 (3) | A3 | Схема электрическая принципиальная ЩО-1 | V1–V5; a table of group lines |
| E04 (4) | A3 | Схема электрическая вводного устройства ВРУ-1 | V1–V5; a scan in V4 and V5 |
| E05 (5) | A1 | План силовых сетей. Корпус 1, этаж 1 | V1–V4; in V5 two A2 portrait parts, 5.1 and 5.2 |
| E06 (6) | A3 | План заземления. Корпус 1 | V1–V2, removed in V3 |
| E07 (7) | A4 | Спецификация оборудования, изделий и материалов | added in V3 (ГОСТ 21.110 layout) |

Pages: V1–V4 six each, V5 eight (two parts of E05 and the duplicate of E03).

| Transition | Sheet → status (channels that must report a difference) | What was done |
| --- | --- | --- |
| V1→V2 | E01 `same`; E02 `different` (text, zones); E03 `different` (text, zones); E04 `same_zones_changed` (zones); E05 `different` (annotations); E06 `same` | label `ЩО-1` moved (+120, +30 pt); table cell `3,0` → `3,6`; stamp `Изм.0` → `Изм.1` and date on E04 with content untouched; a `/Text` annotation added to the A1 plan |
| V2→V3 | E01 `different`; E02 `different` (geometry, zones); E03 `same`; E04 `different` (color, zones); E05 `different` (color, zones); E06 `removed`; E07 `added` | a line added to the lighting plan; six tray lines red → blue (A1); the `PE` bus weight 0.5 → 1.5; sheet list changed on E01; a `/Square` annotation on the new sheet |
| V3→V4 | E01 `different` (geometry, text, zones); E02 `same` (byte-identical); E03 `different` (text); E04 `needs_review` (text_coverage); E05 `different` (geometry, zones); E07 `same` | the permit table «Разрешение на внесение изменений» with three entries; a cable cell on E03 changed with no entry and no stamp change; E04 replaced by a scan (one 1-bit image, no text layer); a tray branch added to E05 |
| V4→V5 | E01 `different`; E02 `same` (byte-identical); E03 `needs_review` (warnings); E04 `same` (identical scan); E05 `needs_review` (split); E07 `different` (text, zones, spec_positions) | the A1 plan split in two A2 parts; E03 present twice (pages 3 and 8); specification: position 7 added, position 6 removed, position 3 quantity 2 → 3 |

Permit reconciliation (V3→V4), derived by the build and re-read by the tests: entry 1 (sheet 5, tray branch)
`declared_and_found`; entry 2 (sheet 7, cable in the specification) `declared_not_found`; entry 3 (sheet 4, QF2 100 А → 125 А)
`declared_unverifiable_scan`; sheet 3 `found_not_declared`.

### 2.2 SP-1 — a stage pair

`old_p.pdf` is the П document `СИНТ-02-АР` (6 sheets); `new_r1.pdf`, `new_r2.pdf`, `new_r3.pdf` are the Р documents
`СИНТ-02-АР.1` (3 sheets), `.2` (1), `.3` (2). Titles carry type, building and level; five sheets link 1:1 (P1→R1 … P5→R5).
Changed text: `101  Холл  24,5 м²` → `25,1 м²`, `Уклон кровли 2 %` → `3 %`. Added: a room, a note, and the whole sheet R6.
Removed: a room, the parapet note, the schedule header and the built-up-area line. Moved to another sheet: the three
schedule rows of P6 are blocks on R4. Without a pair: P6 (OLD only) and R6 (NEW only). Sixteen `unchanged` fragments are in
the key as text a comparison must not report.

### 2.3 Answer-key design

Per transition and per sheet: the expected status (one of the six), the channels that **must** report a difference, the
channels that **must not** (a channel in neither list is unconstrained, so a correct engine is not asserted against a
detail the corpus cannot know), reasons, page mapping, the text changes with before/after and bounding boxes, the graphic
changes, the annotation changes, `byte_identical_page`; for the scan pair the changes that exist only in pixels; for the
split the part regions and an empty `content_changes_in_region`; for the specification the added/removed/changed
positions and both tables; for V3→V4 the permit block. The schema is in `fixtures/comparison/README.md`.

How the key is kept honest: each sheet is a list of operations with authored ids; two versions are compared by id and the
key's change lists are that difference. The authored statuses, the permit outcome and (SP-1) the text classes are
second entries: `build()` refuses to write when an authored value contradicts the computed difference.

## 3. `pdfwrite.py` extensions

Added below the old code, each off unless asked for: `page_dictionary` (`/CropBox`, `/Rotate`, `/Annots`),
`add_text_annotation`, `add_square_annotation` (both with appearance streams), `add_ocg`, `ocg_properties`,
`layer_begin`/`layer_end`, `stroke_line_op`/`stroke_rect_op`/`stroke_circle_op` (dashes), `add_hatch_pattern` +
`pattern_fill_op` (tiling hatch), `hatch_segments`/`hatch_lines` (parallel-stroke hatch), `clip_rect_op`, `stroke_text_op`
(glyph outlines stroked; no text-showing operator). Proof that no AR output moved: 0 lines deleted; no AR builder or
module calls any new name (a test greps for it); the default page dictionary serialises to the bytes the AR builders
write (a test); the AR builders' own `--check` runs and the AR/seeded tests pass unchanged (§4).

## 4. Commands and results

Run on the committed tree at `9ecf141a`, from the worktree root, `PYTHONPATH=$PWD/src:$PWD`, interpreter
`/root/projects/PDF-Analysis/.venv/bin/python`, exit status read directly.

| Command | Result |
| --- | --- |
| `pytest -q tests/contract/fixtures_comparison tests/contract/fixtures_ar tests/contract/fixtures_seeded -p no:cacheprovider` (the task's command) | rc 0: **296 passed, 19 249 subtests passed** in 43 s: 116 in `fixtures_comparison` (new), 114 in `fixtures_ar`, 66 in `fixtures_seeded`; the two existing directories gave the same 180 passed and 19 249 subtests before this task's first commit (run on the base tree) |
| the new directory alone, per module | determinism 15, guards 53, readers 19, realistic A1 9, SP-1 5, VS-1 15 (116) |
| `python3 tools/fixtures/comparison/build.py --check` | rc 0; 12 artefacts `OK` (digests in `fixtures/comparison/SHA256SUMS`) |
| `python3 tools/fixtures/build_ar_corpus.py --check` | rc 0 (unchanged) |
| `python3 tools/fixtures/build_portal_bundles.py --check` | rc 0 (unchanged) |
| `python3 tools/fixtures/build_ar_specification.py --check` | rc 0 (unchanged) |
| `git diff --check 5867d704..HEAD` | rc 0 |
| `git diff --numstat 5867d704..HEAD -- tools/fixtures/ar_corpus` | `334 0 tools/fixtures/ar_corpus/pdfwrite.py` |

Sizes (`du -b`): VS-1 `v1` 71 108, `v2` 71 767, `v3` 75 741, `v4` 316 215, `v5` 324 278; SP-1 `old_p` 53 711, `new_r1`
46 107, `new_r2` 41 512, `new_r3` 43 306. **PDFs together 1 043 745 bytes (limit 2 000 000)**; the keys are 114 569 and
41 002 bytes; the whole directory is 1 208 676 bytes. The scan page (A3 at 100 dpi, 1 bit, 241 kB of image data, in `v4` and `v5`) is why those two files are about 320 kB; the rest is uncompressed vector content and one 32 kB font per file.

Realistic A1, written to a scratch directory outside the repository (free space measured first: 4.5 GiB):

| Command | Result |
| --- | --- |
| `realistic_a1.py OUT/a.pdf --second OUT/b.pdf` | 0.77 s, peak RSS 67 MiB; A 4 470 378 bytes, B 3 076 406 bytes; 76 000 painted paths, **185 983 elements by the product reader's count** (PDFium, `ingest/pdf_reader._elements`) |
| `realistic_a1.py OUT/light.pdf --paint-ops 0` | 0.29 s; 1 635 388 bytes; 20 509 painted paths, **75 001 elements** (the largest real page measured had 75 486) |

Both pages: `/Rotate 90`, MediaBox `[0 0 1683.78 2383.94]`, CropBox `[8.5 8.5 1675.28 2375.44]` (PDFium shows 2366.94 x 1666.78),
one optional-content group `Строительная сетка` that is `OFF` by default and holds 1 500 dashed lines, no text layer
(0 characters in PDFium, no `Tj`), dashes, a tiling hatch and 45-degree stroke hatches. The two producers' renderings
differ by 4.1 grey levels on average at 0.3 scale (the test allows 8) and are not pixel-identical.

## 5. Guards, each shown failing

Key mutations (in memory, `test_cmp_fixtures_guards.py`, 53 tests): every tag the readers' checks can report
(`[stamp]`, `[pages]`, `[size]`, `[annots]`, `[scan]`, `[title]`, `[identical]`, `[text_change]`, `[style]`, `[spec]`,
`[permit]`, `[status]`, `[identity]`, `[version]`, `[split]`, `[duplicate]`, `[sha]`, `[files]`, and SP-1's `[links]`,
`[fragments]`) is made to appear by changing one fact of the key; a swapped PDF, a missing PDF and a PDF whose glyph
strings were destroyed are reported. Generator refusals: a status the sheets contradict (three variants), a permit
outcome that is wrong, a text class that is wrong, operations that cross the split line, a text layer that does not carry
the key, the 2 MB budget, `--check` on an altered committed file.

Code mutations (applied to the generator, corpus rebuilt where the build allowed it, the lane's tests run, tree restored
with `git checkout`; `git status` clean after each):

| Mutation | Result |
| --- | --- |
| annotations not written (`for note in []`) | 3 red: the key-vs-PDF check, the pypdf annotation test, the split-annotation test |
| stamp text drawn 30 pt too high | the build itself refuses (`FAIL: the text layer does not carry the keys' claims`, rc 1, one line per wrong stamp field) and writes nothing |
| the scan page drawn as vector text (`SCANS = set()`) | 2 red: the key-vs-PDF check and the scan test |
| a nanosecond clock value in the info dictionary | 4 red: in-process twice, committed-vs-fresh, hash-seed agreement, `--check` |
| layer names taken from an unsorted set | 3 red: committed-vs-fresh, hash-seed agreement, `--check` |
| realistic A1 without `/Rotate` | 1 red (rotate / CropBox / OCG test) |
| realistic A1 padded to half the element count | 1 red + the fixture's own assertion (6 errors) |
| realistic A1 with the OCG not hidden | 1 red (same test) |

## 6. Known limits

- **V5 has no A1 sheet.** The task asks for "one A1 sheet split into two sheets" and "sheets of A4, A3 and one A1". An A1
  landscape sheet cut in two at the same scale is two A2 portrait sheets (1190.55 x 1683.78 pt), so V1–V4 have the A1 and V5
  has its two A2 parts. This is the harder case for a comparison (a size change with a pure translation). The realistic A1
  generator supplies an A1 page for measurements.
- **The scan is ours.** A pure-Python scan-line rasteriser draws the sheet at 100 dpi, 1 bit, no noise, no skew, glyph
  outlines filled. It proves "no text layer, one image"; it does not prove anything about OCR on a real scan.
- **Stroked text is glyph outlines**, not a centre-line (SHX-like) stroke font: each character is one path of 25–50
  segments, heavier per character than a real plotter export. The realistic sheet's element count is padded to the
  requested minimum anyway.
- **The default realistic A1 is heavier than the real maximum by the reader's count** (185 983 against 75 486), because it
  also reaches 76 000 painted paths so that no reading of "75 000 elements" fails. A ceiling gate met on it is conservative;
  `--paint-ops 0` gives 75 001 elements.
- **The hidden layer holds lines only.** The "pdfplumber reads hidden text that PDFium does not draw" trap needs a text
  object in a hidden layer; with strokes-only text there is none, so it is not reproduced.
- **The second producer differs in order, grouping, precision, `/Producer` and document id**, not in line joins, caps or
  anti-aliasing, which a different CAD would also change.
- **Channel rules are this corpus's reading** of the original's channels (`ORIGINAL-VERSION-COMPARISON-INVENTORY.md` §4.1):
  stamp text belongs to `zones`, not `text`; a style-only change is `color`, not `geometry`; a changed number may also show
  in `geometry` (unconstrained). `CMP-ORIGINAL-READ-01` may refine them; a lane that disagrees stops to the wave's FIX slot
  and does not edit a key it does not own.
- **Split and duplicate statuses are `needs_review` with weak channel claims.** What is certain is stated as a fact (the
  parts equal their regions; the duplicate pages are identical); the status of a pair the matrix may or may not present
  as one pair is not over-specified.
- **Plain PDF 1.7**: uncompressed streams, classic xref, no encryption, no compressed object streams. A reader's handling
  of `FlateDecode` content or xref streams, which real exports use, is not exercised.
- **The table checks use pdfplumber's line-strategy extractor**; a pdfplumber upgrade that changes it would be a test
  finding, not a corpus change.

## 7. Integration notes

- `CMP-PROFILE-01`: per page `stamp` (designation, title, stage, sheet number, revision, date), `text_layer`/`scan`,
  `format`; the version `label` is the highest `Изм.` (V2 `Изм.1`, 12.02.2026 …); on the scan page the stamp is pixels only
  (no text to read), and the realistic A1 has no text layer at all.
- `CMP-MATRIX-01`: `sheet_identity` (page numbers shift: E06 leaves in V3, E07 arrives; sheet numbers are stable); the
  split (`E05` pages 5–6, parts with regions) and the duplicate (`E03` pages 3 and 8) with `reasons`.
- `CMP-ENGINE-01`: per-sheet status and the required/forbidden channels, `text_changes`/`graphic_changes` with bounding boxes
  (assert that a reported difference region overlaps the expected box), `byte_identical_page`, `changes_in_pixels` for the
  scan; `realistic_a1.py` for the A1 time/RSS/bytes gate (see §4 for sizes and counts).
- `CMP-SERIES-01`: `status_counts` per transition. `CMP-VC-SPEC-01`: `spec_positions` on E07 for V4→V5 (and
  `spec_positions_on_page` for the added sheet in V2→V3). Stage slices: `sp1/answer_key.json`.
- Changing the corpus: edit the sheet builder, the authored expectation beside it, run
  `python3 tools/fixtures/comparison/build.py`, then the tests (README, "Adding a case"). The digests and the keys are
  generator output; do not edit them by hand.
- The new key schemas (`cmp-vs1-answer-key/1`, `cmp-sp1-answer-key/1`) are test-data schemas, not entries of `contracts/**`.

## 8. Forbidden hotspots

Untouched: `git diff --name-only 5867d704..HEAD` lists only paths under `tools/fixtures/comparison/`,
`tools/fixtures/ar_corpus/pdfwrite.py`, `fixtures/comparison/`, `tests/contract/fixtures_comparison/`,
`docs/program/CMP-FIXTURES-01.md` and `docs/program/tasks/CMP-FIXTURES-01.md`. No `contracts/**`, migration, `src/**`,
root lock, composition root, `web/**`, `conftest.py` or global style. Every existing AR-corpus output is byte-identical
(§3, §4); no dependency was added (the tests use `pypdf`, `pdfplumber`, `pypdfium2` and `Pillow`, already in the venv).
