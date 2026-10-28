# Synthetic comparison corpus (CMP-FIXTURES-01)

Test data for the comparison modules «Сравнение версий» and «Сравнение стадий»: PDFs and, beside
each set, an **answer key** that states what a correct comparison must find. The key is authored
next to the content that creates the difference; it is not the output of a comparison engine, and
it is not re-captured from one. Everything is invented: no customer, production or real project
bytes, no real organisation, address or person (owner decision OD-17).

## Regenerate and check (one command each)

```
python3 tools/fixtures/comparison/build.py            # write everything under fixtures/comparison/
python3 tools/fixtures/comparison/build.py --check    # rebuild in memory, compare byte for byte, write nothing
```

Pure standard library; the font is the committed `tools/fixtures/assets/ARCorpusSans.ttf`. The
build is byte-deterministic (no clock, no PRNG, no compression, fixed document ids and dates) and
refuses to write when an authored expectation contradicts the sheets it describes. `README.md` and
`.gitattributes` are hand-written; every other file is generator output and is digested in
`SHA256SUMS`.

The tests are `tests/contract/fixtures_comparison`; they re-read every claim of the keys from the
PDF bytes with pypdf, pdfplumber and pypdfium2. Total size of the committed PDFs: about 1.0 MB
(limit 2 MB).

## Layout

| Path | What it is |
| --- | --- |
| `vs1/v1.pdf` … `vs1/v5.pdf` | VS-1: five versions of one drawing set, designation `СИНТ-01-ЭМ` |
| `vs1/answer_key.json` | schema `cmp-vs1-answer-key/1` |
| `sp1/old_p.pdf`, `sp1/new_r1.pdf`, `sp1/new_r2.pdf`, `sp1/new_r3.pdf` | SP-1: one П document and an assembly of three Р documents |
| `sp1/answer_key.json` | schema `cmp-sp1-answer-key/1` |
| `SHA256SUMS` | digest of every generated file |

The «realistic A1» sheet is **not** here. `tools/fixtures/comparison/realistic_a1.py OUT.pdf
[--second OUT_B.pdf]` writes it to a path the caller gives (about 4.5 MB and 3 MB), refuses a path
inside the repository and refuses to write on a nearly full disk.

## VS-1

Every sheet has a 185 x 55 mm title block (designation, sheet title, stage, sheet number, «Изм.N»,
date), a frame, Cyrillic text from an embedded font, and a text layer. A sheet keeps the «Изм.» of
its last change, so the version label (`Изм.N`, the highest on the sheets) and its date are facts a
reader has to derive. Formats: A4 and A3 sheets and one A1 plan (V1–V4); V5 holds the two A2 parts
the A1 plan was split into.

| Version | Label, date | Pages | Transition into it (what is in the key) |
| --- | --- | --- | --- |
| V1 | Изм.0, 15.01.2026 | 6 | the base: general data, lighting plan (dashed axes on an optional-content layer, a tiling-pattern hatch), one-line diagram with a table, ВРУ diagram, A1 power plan, earthing plan |
| V2 | Изм.1, 12.02.2026 | 6 | a label moved (`ЩО-1` on sheet 2); a number in a table cell changed (`3,0` to `3,6`, sheet 3); a stamp-only revision (sheet 4: `same_zones_changed`); a PDF text annotation added to the A1 plan (annotation-only change) |
| V3 | Изм.2, 10.03.2026 | 6 | a sheet added (7, specification) and one removed (6); a line added (sheet 2); the cable-tray colour changed red to blue (A1 plan); a bus line weight changed 0.5 to 1.5 (sheet 4); a square annotation on the new sheet |
| V4 | Изм.3, 07.04.2026 | 6 | a permit table «Разрешение на внесение изменений» on sheet 1 with three declared changes: one declared and found (a tray branch on sheet 5), one declared and not found (cable in the specification, sheet 7 unchanged), one declared on a sheet that became a scan (sheet 4); one change nobody declared (a cable in the table of sheet 3, stamp revision not raised); sheet 4 replaced by a scan (one image, no text layer); sheet 2 byte-identical |
| V5 | Изм.4, 05.05.2026 | 8 | the A1 plan split into two A2 portrait sheets (5.1, 5.2), cut at x = 1190.55 / 1193.39 pt and translated, never scaled; sheet 3 duplicated at the end (page 8); the specification table (ГОСТ 21.110 layout) with position 7 added, position 6 removed and position 3 changed (`Кол.` 2 to 3); sheets 2 and 4 byte-identical to V4 |

### Answer key, `vs1/answer_key.json`

- `versions[]`: file, sha256, bytes, `label` and `date` (as derived from the stamps), `page_count`, and
  per page: `sheet_id`, `sheet_no`, `title`, `format`, `width_pt`/`height_pt`, `text_layer`, `scan`, the stamp
  fields and `stamp_bbox`, annotations (kind, contents, rect), `content_sha256`. For the scan page the stamp
  fields are what the image shows; the PDF carries no text for them (`text_layer: false`).
- `sheet_identity[]`: which page of which version is which sheet (`E01`…`E07`; the split and the
  duplicate list two pages).
- `transitions[]`: `V1->V2` … `V4->V5`, each with `status_counts` and one entry per sheet:
  - `expected_status`: one of `same`, `same_zones_changed`, `different`, `needs_review`, `added`, `removed`;
  - `channels_with_differences`: channels (`geometry`, `color`, `text`, `text_coverage`, `zones`,
    `annotations`, `warnings`, `spec_positions`) that **must** report a difference;
  - `channels_without_differences`: channels that **must** report none; a channel in neither list is
    unconstrained (for instance `geometry` for a changed number, because its glyph pixels differ);
  - `reasons` (`NO_TEXT_LAYER`, `DUPLICATE_SHEET`, `SPLIT_SHEET`), `relation` (`one_to_one`, `added`,
    `removed`, `duplicate`, `split`), `from_page`/`to_page` (or `to_pages`);
  - `text_changes[]` and `graphic_changes[]`: each with the operation `id`, `kind`
    (`text_changed`, `text_moved`, `text_added`, `text_removed`, `graphic_added`, `graphic_color`,
    `graphic_width`, …), `zone` (`content` or `stamp`), `before`/`after` and the bounding boxes
    (PDF points, origin at the lower left of the page);
  - `annotation_changes`, `byte_identical_page`;
  - for the scan pair `changes_in_pixels` (what changed in the image, not readable from the PDF);
  - for the split, `parts[]` with the region of the old sheet, the translation and an empty
    `content_changes_in_region`;
  - for the specification sheet, `spec_positions` (`added`, `removed`, `changed`, and both tables);
- `transitions[V3->V4].permit`: the table, the declared entries with their class
  (`declared_and_found`, `declared_not_found`, `declared_unverifiable_scan`) and `found_not_declared`.

## SP-1

`old_p.pdf` is the П document `СИНТ-02-АР` (6 sheets); `new_r1.pdf`, `new_r2.pdf`, `new_r3.pdf` are the Р
documents `СИНТ-02-АР.1`, `.2`, `.3` (3 + 1 + 2 sheets). Sheet titles carry type, building and level
(«План. Корпус 1. Этаж 1», «План. Корпус 1. Кровля», «Разрез 1-1. Корпус 1. Уровень +0,000»), so a
sheet passport matches five sheets 1:1. The pair holds text changed (a room area, a roof slope),
added (a note, a room, a section sheet) and removed (a parapet note, a room), the room schedule of
building 2 moved from its own sheet (P6) onto a plan (R4), and one sheet without a pair on each side
(P6 only in OLD, R6 only in NEW).

`sp1/answer_key.json`: `documents[]`, `sheets[]` (passport, stamp, fragments with bounding boxes),
`sheet_links[]` (old, new, basis, passport, `stamp_differences`), `sheets_without_pair`, and
`text_fragments` with the classes `changed`, `added`, `removed`, `moved_between_sheets` and
`unchanged` (text a comparison must **not** report). A fragment is a text operation whose id is
`<sheet>.f.<key>`; the key is its identity across the two stages. Title-block fields are service
zones, not fragments.

## Adding a case

Add an operation (with a stable id) to the sheet builder, change the authored expectation next to it
(`EXPECTED_STATUS`, `SPECIAL`, `EXPECTED_PERMIT` in `vs1.py`; `EXPECTED_TEXT` in `sp1.py`), run the
build, then the tests. The build fails when the expectation and the sheets disagree, and the tests
fail when a PDF reader sees something other than the key says.
