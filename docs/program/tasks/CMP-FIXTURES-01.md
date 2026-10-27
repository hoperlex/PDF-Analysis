# Task CMP-FIXTURES-01 — a synthetic comparison corpus with answer keys

## Outcome
`tools/fixtures/comparison/` generates, byte for byte reproducibly, (1) a version set VS-1 of five versions and
(2) a stage pair SP-1 (one П document, an assembly of three Р documents), each with a JSON answer key that states
what a correct comparison must find, plus (3) an on-demand «realistic A1» generator for measurements. Tests prove
the generator is deterministic and that the answer keys agree with the generated files.

## Depends on
- `COMPARE-MODULES-PLAN` revision 3 merged on `integration/compare-modules` (`cccdb6b8`)

## Frozen inputs
- domain contract: not changed
- API contract: not changed
- analysis/comparison/event contract: not changed
- migration head: not changed
- base commit: `cccdb6b8` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `tools/fixtures/comparison/**`
- `tools/fixtures/ar_corpus/pdfwrite.py`
- `fixtures/comparison/**`
- `tests/contract/fixtures_comparison/**`
- `docs/program/CMP-FIXTURES-01.md`
- `docs/program/tasks/CMP-FIXTURES-01.md`

## Forbidden hotspots
- contracts, migrations, `src/**`, root locks, composition root, global styles, `web/**`
- any byte change of an existing AR-corpus output: the existing tests that read `tools/fixtures/ar_corpus` must stay
  green with unchanged outputs

## Non-goals
- no comparison engine, no product code; the corpus states expected results, it does not compute them
- the realistic A1 file is not committed (it is generated on demand into a path the caller gives)

## Deliverables
- `pdfwrite.py` extensions needed by the corpus, additive and off by default: `/Annots` (a text annotation and a
  square annotation), `/Rotate`, a CropBox different from the MediaBox, one optional-content group (OCG), dashed lines,
  hatch fills, text drawn as strokes (paths) instead of glyphs
- VS-1, five versions, Cyrillic text through the existing font machinery, each version a PDF with a title block
  (stamp) carrying designation «СИНТ-01-ЭМ», «Изм.N» and a date, sheets of A4, A3 and one A1; the transitions
  carry, at least: V1→V2 a moved label, a changed number in a table cell, a stamp «Изм.» change, an added PDF
  annotation; V2→V3 an added sheet, a removed sheet, an added line, a colour change, a line-thickness change;
  V3→V4 a change-permit table «Разрешение на внесение изменений» with one change declared and found, one declared and
  not found, one found and not declared, and one image-only (scan) page; V4→V5 one A1 sheet split into two sheets, one
  duplicate sheet, one specification table in the ГОСТ 21.110 layout (позиция, обозначение, наименование, кол.) with
  an added, a removed and a changed position, and one sheet byte-identical to its predecessor
- SP-1: a П document and three Р documents whose sheet titles carry type, корпус, этаж/кровля/уровень so that sheet
  passports can match them; text changes, a fragment moved to another sheet, a sheet without a pair
- answer keys `fixtures/comparison/vs1/answer_key.json` and `fixtures/comparison/sp1/answer_key.json`: the sheet
  identity across versions (which page of which version is which sheet), the expected status per sheet per
  transition (`same`, `same_zones_changed`, `different`, `needs_review`, `added`, `removed`), the channels expected to
  report a difference (`geometry`, `color`, `text`, `text_coverage`, `zones`, `annotations`, `warnings`,
  `spec_positions`), the expected text changes (before/after), the permit reconciliation classes, the spec position
  changes, and for SP-1 the expected sheet links and the expected changed/removed/added text fragments
- the committed corpus PDFs under `fixtures/comparison/` (keep the total under 2 MB) and a `README.md` there
- `tools/fixtures/comparison/realistic_a1.py`: an A1 sheet with strokes-only text, `/Rotate`, a CropBox offset, one
  OCG layer, hatches and dashes and at least 75 000 drawing elements, plus a second rendering of the same sheet by a
  different operator order (a «second producer»), written to a caller-given path
- the report `docs/program/CMP-FIXTURES-01.md`

## Required tests
- command: `PYTHONPATH=$PWD/src:$PWD /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/fixtures_comparison tests/contract/fixtures_ar tests/contract/fixtures_seeded -p no:cacheprovider`
- expected: all pass; the AR-corpus and seeded tests pass with unchanged outputs
- the new tests at least: regenerating twice gives identical bytes; every PDF opens in `pypdf`, `pdfplumber` and
  `pypdfium2`; page counts, page sizes, stamps and titles agree with the answer keys; `/Annots` present where the key
  says; the scan page has no text layer; the realistic A1 generator writes a file with ≥ 75 000 elements, `/Rotate`,
  a CropBox offset and an OCG (generate into a temporary directory, never into the repository)

## Integration contract
CMP-PROFILE-01, CMP-MATRIX-01, CMP-ENGINE-01, CMP-SERIES-01, CMP-VC-SPEC-01 and the stage slices assert against these
answer keys; CMP-MEASURE-01 uses `realistic_a1.py`.

## Failure/idempotency/security cases
- no timestamps, no random seeds that are not fixed, no environment-dependent bytes

## Rollback / feature flag
Not applicable (test data and a tool).

## Handoff
- changed files:
- commands/results:
- known limits:
- integration notes:
