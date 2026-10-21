# SPEC-TABLE-RECORDING-01 — the Form-7 extractor reads more of the saved text, and a synthetic AR set reaches optimisation proposals

**Base:** `origin/dev` `ff58bdd1`; branch `agent/spec-table-recording-01`, isolated worktree
`spec-table-recording`, lane PostgreSQL 57740 / MinIO 61360–61361. **Status:** both parts complete.
Development candidate under `R-135`: no full gate, no live journey, no push, no merge, no tag. No
migration, no contract change, no dependency, no LLM call, nothing persisted by the extractor.

Debt `D-184` (the extractor half) and the live reach of optimisation proposals for beta
criterion B12. Not touched: the documents-side section query, the price-list upload invalidation
(`web/**`), and the `п.м`/`м` rule (see Known limitations).

## Part 1 — what the saved text can say (`optimisation/specification.py`, `matching.py`)

The saved text layer has no column geometry: a line is a row's cells joined by single spaces.
Three additive rules, each only as far as plain text supports it. `EXTRACTION_ALGORITHM` stays
`specification-text-v1` (the API constant is frozen); public names are unchanged, `SpecificationRow`
gains `manufacturer` and `DetectedTable` gains `continued_on`, both defaulted and neither served
(the adapter maps fields by name, the contract is untouched).

| Rule | Evidence required | When there is none |
| --- | --- | --- |
| **Cells wrapped above their anchor line** | the row's fragment (text before its unit) does not begin with a capitalised word (a lower-case word, a mark, an abbreviation, a size), and a line that opens a name (a capitalised word) is among the at most 3 unanchored lines that touch the anchor line from above | nothing moves: the lines stay with the row above (or are reported `text_before_first_row`), exactly as before. A skipped line (`continuation_limit`, `position_missing`), a group heading or column numbering between breaks the adjacency |
| **A table continued onto the next page without a repeated header** | the table ran to the end of its page (its last row, then only the stamp; with a position or unit column nothing after the stamp reads as one of its rows), the next page is the next page number, before its first row there are only column numbers, a group heading and a «Продолжение» line (at most 3), that row parses under the same header, and the numbering goes on (next integer) or the page says «Продолжение» (always for a table without a position column or with dotted positions) | the table ends with its page, as before (a note, a header of its own, an unreadable stamp layout, a gap in the numbering) |
| **Manufacturer** | the header names a manufacturer column and the row's own fragment holds a legal form (`ООО`, `АО`, `ЗАО`, `ПАО`, `ИП`…) after at least one word and before something | `manufacturer` is `None`; `name` is the description either way |

Rows of a continued table keep the table's ordinal; `DetectedTable.row_count` includes them and
`continued_on` lists the pages. The matcher gains one tier-2 fallback (exact tier first and
unchanged): a vendor's legal form is optional on **one** side — the row's `manufacturer` without
its legal form is compared against positions whose vendor has none, a row without a legal form
against positions whose vendor has one dropped; `ООО` and `ЗАО` are never equal.

**Not done, deliberately.** The type/mark and the code are not split from the name: nothing in plain
text separates them from the name or from each other (a size, a standard reference or an
abbreviation all look like a mark), and a guessed split would move money. Fully geometry-aware
extraction from the portal blocks remains `D-184`'s remaining half. A name wrapped above an anchor
whose own fragment opens with a capitalised word, an anchor line with no description text at all
(`name_missing`), and a table whose next page opens with other text stay as they were.

**Residual risk of the wrapped-above rule.** A row whose fragment begins with an abbreviation or a
mark, after a row whose wrapped line begins with a capitalised word, has that line moved to it. The
tests pin the boundary (`test_a_fragment_that_can_open_a_name_takes_nothing_from_the_lines_above`,
`test_without_a_line_that_opens_a_name_above_nothing_moves`); the matcher is exact on the whole
description, so a wrong attribution leaves a row unmatched rather than priced against a wrong
position, but it can also free the row above to match a shorter name.

## Part 2 — the synthetic AR set with a specification, its recorded answer and its price list

Why: the only recorded model response was for `fixtures/synthetic/ar/ar_baseline.pdf`, which has no
specification table, so an optimisation pass held 0 proposals. Everything is synthetic and says so;
no model produced the recorded reply and no money was spent.

| Name | What |
| --- | --- |
| `fixtures/synthetic/ar_specification/ar_specification.zip` | portal bundle (five members, stem `ar_specification`) to upload |
| `fixtures/synthetic/ar_specification/ar_specification.pdf` | the PDF in it, 4 pages, specification over sheets 3 and 4 |
| `fixtures/synthetic/ar_specification/ar_specification_prices.csv` | price list, 10 positions, RUB |
| `fixtures/synthetic/ar_specification/expected_specification.json` | oracle (rows, matches, totals, proposals), computed in the generator from the authored numbers |
| `fixtures/synthetic/ar_specification/{SHA256SUMS,README.md}` | digests; the step-by-step journey and the oracle table |
| `fixtures/recorded/sections/ar_specification/19fa19530edb2f0a6f0139a2e156ea1128662e52b668ea6a701bb6e946f9e584.json` | synthetic AR reply (one `explicit_placeholder`, page 2), found by `RecordedAdapter()` |
| `tools/fixtures/build_ar_specification.py`, `fixtures/recorded/sections/ar_specification/build_fixtures.py` | the builders, each with `--check` |

Journey and figures are in `fixtures/synthetic/ar_specification/README.md`. In short: classify
`{"project_stage":"P","section_code":"AR"}`; the project vendor list `Завод Север`; 7 rows, 5
matched, totals RUB 464278 over 4 rows; four `cheaper_analog` proposals with savings 16000, 15600,
650 and absent (a dash quantity); unit mismatch (`п.м` against `м`), `no_position`, and
`quantity_not_numeric` counted, none of them proposed.

**Placement of the recording.** `RecordedAdapter()` searches `fixtures/recorded/text_analysis/` and
each directory under `fixtures/recorded/sections/`. The canonical directory is closed to new
recordings (`tests/integration/analysis_text/test_provider_modes.py` counts its four files and takes
"the first" one), so the reply is in its own directory under `sections/`; it is the AR profile's
reply, not a section recording.

**Hand-off to the live-journey lane** (`agent/beta-live-journey-01`): upload
`ar_specification.zip`; classify `P`/`AR`; start the run (recorded mode on the stand); upload
`ar_specification_prices.csv` with `default_currency=RUB`; `PUT /projects/{p}/vendor-lists/AR`
`{"mode":"list","entries":[{"vendor":"Завод Север"}]}` (an expert may); start the pass; then decide
(`POST /optimisation-proposals/{id}/decisions`) and download (`.../export.csv`). The stand's image
copies `fixtures/recorded/` whole (`infra/deploy/Dockerfile.api`), so the new file ships with it.
The proof of steps 1-7 is `tests/integration/optimisation/test_ar_specification_journey.py`.

## Checks

Interpreter: the shared `w55b-main-candidate` venv through `.venv`; lane containers up and migrated
to `0028_classification_corrections`; `.env` exported (`set -a; . ./.env; set +a`);
`python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`. Host load 12-19
during the runs (neighbour lanes), one pytest process at a time.

| Command (paths) | Result |
| --- | --- |
| `tests/unit/optimisation` | 314 passed (272 before; +42 in the two new files, no existing test edited) |
| `tests/unit/optimisation tests/unit/ingest tests/unit/analysis tests/unit/sections` | 462 passed |
| `tests/integration/optimisation` (lane PostgreSQL + MinIO) | 102 passed (11 new in `test_ar_specification_journey.py`) |
| `tests/integration/ingest` | 649 passed |
| `tests/integration/composition` specification/optimisation/section-specification over HTTP + `tests/integration/releases` | 85 passed |
| `tests/integration/analysis_text tests/integration/sections tests/integration/runs/test_w59_section_profile_recorded.py` | 370 passed, **1 failed**: see Risks |
| `python3 tools/fixtures/build_ar_specification.py --check`, `fixtures/recorded/sections/ar_specification/build_fixtures.py --check` | exit 0 |

Mutation probes (applied, run, restored, digests compared): 18 on part 1 (`mutate.py`: every
condition of every rule — the can-open-a-name gate, taking all lines when none opens a name, the 3-line
bound, adjacency across a skipped line, any line opening a name, numbering that need not go on, no
look at what follows the stamp, a page that need not be the next, other text before the first row,
a table cut by a note staying open, the stamp look for every header, the continuation line ignored, a
stamp before the first row, no manufacturer-column gate, a legal form opening the fragment or ending
it, the loose tier beside the exact one, different legal forms equal) each turned the named test red; the
first run of two survived (the stamp look and the stamp before the first row) and the tests were
sharpened until they died. Four on the journey: no above-wrap rule, no continuation, no optional legal
form, the recorded answer removed — each turned the journey red.

## Risks, known limitations, instructions for the integrator

- **One guard trips, and is not patched here** (outside the allowed paths):
  `tests/integration/sections/test_section_recordings.py::test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory`
  asserts `RecordedAdapter().recording_dirs == (CANONICAL, ai, pos, ps, tx)`. The new directory makes
  the served adapter search `(CANONICAL, ai, ar_specification, pos, ps, tx)`. The owner of that file
  adds `SECTIONS / "ar_specification"` to the expected tuple (sorted position: after `ai`). Nothing
  else moved: the canonical directory is untouched, `test_provider_modes` still counts four files.
- `fixtures/recorded` is part of `build_id`: the new directory changes it, as the brief expected.
- `D-184` is not closed: type/mark and code are still inside the description, the geometry-aware
  extraction from the portal blocks is still open, and `п.м` against `м` stays `unit_mismatch` (a
  price per metre is not silently a price per running metre; changing it is a money decision for the
  owner and `matching.py`'s `unit_key`). The debt register is the integrator's: suggested wording is
  "rules 1-3 of `SPEC-TABLE-RECORDING-01` done; remaining: geometry, type/mark/code split, `п.м`".
- The wrapped-above rule can mis-attribute a line in the case under "Residual risk"; it is bounded
  and pinned, not eliminated.
- The recorded answer's key depends on the PDF, the AR prompt bundle and the extractor; a change to
  any of them orphans it. `build_fixtures.py --check` (also run by the journey test) says so.
- Merge: real merge of `agent/spec-table-recording-01`; no other lane's path is touched. Generated
  files are re-derived with the two builders, never hand-merged.
