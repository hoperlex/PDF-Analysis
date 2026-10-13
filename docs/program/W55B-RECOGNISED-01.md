# W55B-RECOGNISED-01 — report (the portal's recognised text)

- Task: `dispatch/W55-PLAN.md` §B3.5 (the text-layer-or-block rule), §B3.6, §B3.3 (the PDF opened from a temporary file), §B4 Stage B 3
  `W55B-RECOGNISED-01`, §B5; `P02_SEAMS.md` §4.1, §4.2, §4.8 (sealed, read only); owner rulings R-116, R-117.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `19ea1525` (BUDGET report; below it INGEST, STREAM, FIXTURES, SEAL).
- Written by one writer (Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- **The lane is complete.** A version uploaded as a portal bundle now gets `prepared.recognised_text` from `source_preparation`: per TEXT
  block the portal's OCR text marked `quote_source: recognised` with quality flags, per IMAGE block the portal's description, nothing for a
  STAMP block, never merged into `prepared.text_layer` and never an input of analysis. A page with no text layer is admitted when the
  version's block list holds a block on it ("OCR is always marked") and refused otherwise; a version without a bundle keeps today's rule.
  The PDF is streamed to a temporary file and opened by its path. The executor hands a bundle version's two members to the stage.
- Lane stack: `FOUNDATION_INSTANCE=auditmanager-w55b-recognised`, PostgreSQL `57450`, S3 `61050/61051`; torn down at the end (section 5).

## 1. Changed files

`git diff --name-status 19ea1525..HEAD`:

```text
A docs/program/W55B-RECOGNISED-01.md                                  this report
A src/auditmanager/analysis/recognised/__init__.py                    the package's surface
A src/auditmanager/analysis/recognised/markdown.py                    the _results.md reader (one body per block header)
A src/auditmanager/analysis/recognised/portal.py                      the block list, and the two members held equal both ways
A src/auditmanager/analysis/recognised/flags.py                       the quality flags and the pinned designation pattern
A src/auditmanager/analysis/recognised/artifact.py                    the prepared.recognised_text builder
M src/auditmanager/analysis/ports/artifacts.py                        three role constants (and their __all__ names)
M src/auditmanager/analysis/public.py                                 export lines (three roles; one line for the kinds and the marker)
M src/auditmanager/analysis/stages/source_preparation.py              temporary file, text-layer-or-block rule, the artifact, metrics
M src/auditmanager/analysis/stages/extraction.py                      extract_document / probe_envelope take bytes or a path
M src/auditmanager/norms/public.py                                    one import line (DegeneracySignal, inspect_degeneracy) and two __all__ names
M src/auditmanager/runs/executor.py                                   OUTSIDE THE GRANT, pre-authorised: the bundle members reach source_preparation
A tests/integration/analysis/recognised/recognised_support.py        helpers (not a test module): committed bundles, the S3 fixture, the shape validator
A tests/integration/analysis/recognised/test_markdown_reader.py       16 tests
A tests/integration/analysis/recognised/test_portal_agreement.py      21 tests
A tests/integration/analysis/recognised/test_quality_flags.py         87 tests
A tests/integration/analysis/recognised/test_recognised_artifact.py   15 tests
A tests/integration/analysis/recognised/test_source_preparation_bundle.py          20 tests (S3)
A tests/integration/analysis/recognised/test_recognised_never_reaches_analysis.py   3 tests
A tests/integration/analysis/recognised/test_run_hands_the_bundle_to_preparation.py 2 tests (PostgreSQL and S3)
M tests/integration/analysis_engine/test_fail_closed.py               the image-only case's docstring states the rule as it now is
M tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py    OUTSIDE THE GRANT, forced: the substitution also covers the streamed read
```

No `conftest.py` was added or changed: the S3 fixture lives in `recognised_support.py` and is bound into each module that uses it; the
run-wiring module loads the runs harness by path, as `tests/integration/exports` does.

## 2. Checks, and how each new test was shown to fail

Light acceptance (`R-102`), on the lane stack, one invocation at a time, `set -a; . ./.env; set +a` before
`.venv/bin/python -m pytest -p no:cacheprovider -q <target>`; exit codes read directly (`> log 2>&1; rc=$?`), never behind a pipe. Host:
9.6 to 10.0 GiB available and 17 GiB free on `/` when the stack came up.

| Check | Exit | Result |
| --- | --- | --- |
| `git diff --check 19ea1525..HEAD` | 0 | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/analysis src/auditmanager/runs src/auditmanager/norms tests/integration/analysis tests/integration/analysis_engine` | 0 | |
| `tests/contract` without `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py` (clean committed tree, `296804e4`) | 0 | 752 passed, 18 927 subtests |
| `tests/integration/analysis` (with the new `recognised/`) | 0 | 411 passed (247 before the lane and 164 new) |
| `tests/integration/analysis_engine` | 0 | 47 passed |
| `tests/integration/analysis_text` | 0 | 223 passed |
| `tests/integration/p02_journey` | 0 | 59 passed |
| `tests/integration/runs`, first run | 1 | 198 passed, 2 failed: `test_a_halted_chain_reaches_a_terminal.py` (both cases), see 2.2 |
| `tests/integration/runs` after the forced test edit (`ff6c7920`), reused database | 1 | 199 passed, 1 failed: `test_durable_effect_boundaries.py::test_provider_effect_settlement_is_bounded_and_resumable` (it passed in the first run; state-dependent on a reused database, as BUDGET recorded) |
| the database and object store recreated (`make down`, the lane's two volumes removed, `make up`, `make migrate`) | 0 | head `0021_portal_bundles` |
| `tests/integration/runs`, fresh database | 0 | 200 passed |
| `tests/integration/{analysis,analysis_engine,analysis_text,p02_journey}` again, fresh database, one invocation | 0 | 740 passed |
| `tests/characterization` | 0 | 61 passed |
| `tests/e2e` (no browser) | 0 | 163 passed, 5 skipped (the opt-in live-model cases) |
| `tests/unit` | 0 | 1 passed |
| beyond the brief, the suites that execute runs: `tests/integration/{exports,workers,jobs,execution,qa_w52,qa_w53}`, one invocation | 0 | 106 passed |
| beyond the brief: `tests/integration/api` | 0 | 569 passed |
| `tests/integration/composition` (last) | 0 | 750 passed, 2 skipped (the opt-in proxy stand and the stand-copy window, off by design) |
| a full `make gate` | -- | **not run** (light acceptance, `R-102`; one full gate runs on the final W55b candidate) |
| web lint, typecheck, Vitest | -- | not run: the brief's list does not name them and this lane changes no file under `web/` |

The 19 temporary files the "temporary file: removed" mutation (section 2.1) left in the temporary directory were that mutation working: it
disables the removal. All were created inside one three-second window of the mutation run and were removed by name afterwards; a normal run
of the stage tests leaves the count of `am-source-*` files unchanged (19 before, 19 after, then 0 once removed).

### 2.1 Mutation proofs

Method: a scratch driver (session scratchpad, not committed) makes a one-line textual replacement in the **committed** file (the old text must
occur exactly once), runs the named test file with `pytest -x -q --tb=no -rf` on the lane stack (one invocation at a time), writes the
original bytes back and compares the file's SHA-256 before and after. **31 mutations, 31 red, every file restored** (`restored=yes` in each
row). Test paths are relative to `tests/integration/analysis/recognised/`.

| Behaviour | Mutation | First failing test |
| --- | --- | --- |
| `mixed_script` | `mixed.append(word)` becomes `pass` | `test_quality_flags.py::test_each_seeded_flaw_raises_its_flag_on_the_recognised_word[page5-mixed_script_word-...]` |
| `homoglyph`, within a word | `if _within_word_homoglyph(word):` becomes `if False:` | `test_quality_flags.py::test_each_seeded_flaw_raises_its_flag_on_the_recognised_word[page2-latin_homoglyph-...]` |
| `homoglyph`, a whole Latin word | the neighbour condition becomes `if False:` | `test_quality_flags.py::test_the_designations_block_would_be_flagged_without_the_exemption` |
| `cjk` | `if _CJK.search(normalised) is not None:` becomes `if False:` | `test_quality_flags.py::test_each_seeded_flaw_raises_its_flag_on_the_recognised_word[page3-cjk_character-...]` |
| `doubled_list_marker` | `if marker is not None:` becomes `if False:` | `test_quality_flags.py::test_each_seeded_flaw_raises_its_flag_on_the_recognised_word[page4-doubled_list_marker-...]` |
| a thematic break is not doubled | `if _THEMATIC_BREAK.match(line):` becomes `if False:` | `test_quality_flags.py::test_a_single_marker_a_thematic_break_or_a_marker_inside_a_line_is_not[- - -]` |
| the degeneracy flags | the loop over the verdict iterates `zip((), ())` | `test_quality_flags.py::test_flags_are_deduplicated_and_in_the_pinned_order` |
| `empty_text` | `if not normalised.strip():` becomes `if False:` | `test_quality_flags.py::test_an_empty_body_is_empty_text[]` |
| the designation exemption | `if is_exempt:` becomes `if False:` | `test_quality_flags.py::test_each_seeded_designation_raises_nothing[B25]` |
| the exemption's narrowing (one capital needs two digits) | `\d{{2,}}` becomes `\d{{1,}}` | `test_quality_flags.py::test_a_look_alike_letter_where_the_other_script_belongs_is_a_homoglyph[класс C0 здания-C0]` |
| the `quote_source: recognised` marker | the line is deleted | `test_recognised_artifact.py::test_every_accepted_bundle_builds_the_sealed_shape[ar_baseline.zip]` |
| an IMAGE entry carries no flags | `"flags": []` added to the description entry | `test_recognised_artifact.py::test_every_accepted_bundle_builds_the_sealed_shape[ar_baseline.zip]` |
| the entry order | `ranked.sort(...)` becomes `pass` | `test_recognised_artifact.py::test_entries_are_ordered_by_page_then_by_place_in_the_markdown` |
| `results_sha256` | the digest of `b""` | `test_recognised_artifact.py::test_every_accepted_bundle_builds_the_sealed_shape[ar_baseline.zip]` |
| the reader skips the quote lines | the skipping loop becomes `while False:` | `test_markdown_reader.py::test_the_reader_counts_every_body_as_ingest_does[ar_baseline.zip]` |
| the reader drops a trailing CR | `line.rstrip("\r")` becomes `line` | `test_markdown_reader.py::test_a_crlf_file_reads_to_the_same_bodies_as_its_lf_twin` |
| agreement, list to markdown | the per-block check becomes `if False:` | `test_portal_agreement.py::test_a_header_of_the_other_type_is_refused` |
| agreement, markdown to list | the extra-header check becomes `if False:` | `test_portal_agreement.py::test_a_header_for_a_stamp_is_refused` |
| a block on a page the PDF lacks | `if page_index >= page_count:` becomes `if False:` | `test_portal_agreement.py::test_a_block_on_a_page_the_pdf_does_not_have_is_refused` |
| textless rule, admitted with a block | the block condition is dropped (`if page.char_count == 0:`) | `test_source_preparation_bundle.py::test_a_textless_page_that_holds_a_portal_block_is_admitted_and_marked` |
| textless rule, refused without one | the condition becomes `... and False` | `test_source_preparation_bundle.py::test_a_textless_page_with_no_portal_block_is_refused` |
| `has_text_layer: false` on such a page | the value becomes `True` | `test_source_preparation_bundle.py::test_a_textless_page_that_holds_a_portal_block_is_admitted_and_marked` |
| both members or neither | `if markdown_blob is None or blocks_blob is None:` becomes `if False:` | `test_source_preparation_bundle.py::test_one_member_without_the_other_is_refused[markdown]` |
| never in the text layer | the text layer of a bundle gains a `recognised` member holding the bodies | `test_source_preparation_bundle.py::test_the_text_layer_of_a_bundle_is_byte_for_byte_the_text_layer_of_its_bare_pdf` |
| the extractor gets a path | `extract_document(path)` becomes `extract_document(Path(path).read_bytes())` | `test_source_preparation_bundle.py::test_the_pdf_is_opened_from_a_temporary_file_that_is_gone_afterwards` |
| the PDF is streamed, never read whole | the stream becomes `[store.read(blob_id, verify=True)]` | `test_source_preparation_bundle.py::test_a_stream_that_breaks_is_source_unreadable_and_leaves_no_file` |
| the temporary file is removed | `Path(name).unlink(missing_ok=True)` becomes `pass` | `test_source_preparation_bundle.py::test_the_pdf_is_opened_from_a_temporary_file_that_is_gone_afterwards` |
| the metrics | `recognised_entry_count` becomes `0` | `test_source_preparation_bundle.py::test_a_bundle_publishes_the_recognised_text_beside_the_two_prepared_artifacts` |
| executor, the role tuple | back to `(ROLE_SOURCE_DOCUMENT,)` (the stage gets no markdown) | `test_run_hands_the_bundle_to_preparation.py::test_a_run_over_a_bundle_version_publishes_the_recognised_text` |
| executor, the seeding | the manifest loop's condition becomes `if False:` | `test_run_hands_the_bundle_to_preparation.py::test_a_run_over_a_bundle_version_publishes_the_recognised_text` |
| the isolation guard | `import auditmanager.analysis.recognised` planted in `analysis/text/prompt.py` | `test_recognised_never_reaches_analysis.py::test_the_prompt_path_imports_nothing_from_the_recognised_package` |

The first run of the set left one row unrun, not alive: the narrowing row's old text did not match because the pattern held a literal
no-break space instead of its escape. That was a defect of the source (an invisible character in a pinned pattern), fixed in `803c89c9`
with a test for the spelling; the row then ran red.

### 2.2 The two edits forced outside the grant, and their evidence

- **`runs/executor.py`** (pre-authorised): without it the stage never receives the markdown or the block list, so no real run can publish
  the artifact. Two mutations in 2.1 (the role tuple, the seeding) turn the DB-backed wiring test red.
- **`tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py`** (forced, not pre-authorised): the test halts a run by substituting
  non-PDF bytes at the store's `read()` of the source blob. `source_preparation` no longer calls `read()` for the PDF (it streams it with
  `open_stream`, §B3.3), so the substitution reached only `page_geometry_extraction`'s whole read, the chain halted one stage later, and
  both cases went red (the first `runs` run above). The edit adds the same substitution to `open_stream` and says so in the docstring;
  nothing else changed and both cases are green. GEOMETRY, which must also stop reading the PDF whole, is already covered by it.

### 2.3 What the new tests assert

- `test_markdown_reader.py`: the reader and INGEST's `recognised_characters` give the same character count for every TEXT and IMAGE body of
  all seven committed bundles (six with bodies); CRLF reads to the LF bodies and counts as INGEST counts it; an empty body; a header
  directly followed by the next; only the leading quote lines are metadata; a page heading ends a body; the type label is case-insensitive;
  a 500-page markdown of 15.4 MiB is read whole (well under a second here; the bound asserted is 30 s).
- `test_portal_agreement.py`: each way the stored pair can disagree is refused with `analysis_input_invalid` and its own `reason`; a stamp
  alone puts its page among the pages with a block; a lower-case label still agrees.
- `test_quality_flags.py`: each seeded flaw of `ar_baseline_ocr_defects.zip` raises its flag on the recognised word; its four designations
  raise nothing, and three of them are flagged when the pattern is disabled; the clean `ar_baseline.zip`, `ar_baseline_minimal.zip` and
  `pages_31.zip` raise nothing on any block; per flag, positive and negative unit cases (clean Russian text raises nothing; a Latin-only
  English word is not `mixed_script`; a Cyrillic word among Latin ones is not a `homoglyph`; CJK punctuation alone is not `cjk`; a single
  marker, a thematic break or a marker inside a line is not doubled); each exempted designation is flagged by the rules alone and exempt with
  the pattern (`REI 150` through its mixed spelling with a Cyrillic `Е`, because `R` has no Cyrillic twin); four near misses still flagged
  (`Bход`, `1.Aрхитектура`, `A500Cталь`, `C0`); the vocabulary and its order pinned as literals; NFC.
- `test_recognised_artifact.py`: the section 4.8 shape by a strict validator (which refuses six damaged copies); TEXT is `recognised_text`
  with `quote_source: recognised` and flags, IMAGE is `portal_description` with neither; a STAMP block has no entry; the text is the body
  verbatim; the order by page, then markdown position; an empty body kept with `empty_text`; `results_sha256`; same input, same bytes.
- `test_source_preparation_bundle.py` (S3): the artifact beside the two prepared ones, with the new metrics; none without a bundle; the text
  layer and the page inventory of a bundle are byte for byte those of its bare PDF, and no seeded flaw is in the layer;
  `image_only_with_block.zip` admitted (`has_text_layer: false`, `char_count: 0`, `char_start == char_end`, and `analysis.text`'s
  `load_text_layer` accepts the layer); `image_only.zip` (no block), a block on another page only, and two bare PDFs refused with
  `validation_failed`, `page_number` and the unchanged constraint; one member without the other; a disagreeing pair; CRLF; two runs publish
  the same three blobs; the extractor is handed a path to a file in the temporary directory holding the PDF's exact bytes, gone afterwards on
  success, on an extraction failure, on a refused document, on a truncated PDF and on a stream that breaks (`source_unreadable`); the source
  blob is never `read()` whole; no PDFium document is opened.
- `test_recognised_never_reaches_analysis.py`: no module of `analysis/text` imports `analysis.recognised` (direct, relative or literal
  dynamic import; the scan is shown to catch all three on planted modules); in the frozen registry only `source_preparation` reads
  `source.markdown` and no stage reads `prepared.recognised_text`.
- `test_run_hands_the_bundle_to_preparation.py` (PostgreSQL and S3): `start_audit_run` and `execute_run` (recorded, offline) over a version
  whose manifest holds the bundle's three members persist `prepared.recognised_text` among `source_preparation`'s artifacts (10 entries) and
  the run still reaches `published`; over a version without a bundle, none.

## 3. Contracts

- **Unchanged:** `contracts/**` (the stage registry already declared both optional inputs and the optional output; stage and artifact
  versions stay `1.0.0`), the OpenAPI document and its surface counts, the error catalog, the migration head `0021_portal_bundles` (no
  migration), `pyproject.toml`, `uv.lock`, the composition root, `P02_SEAMS.md`.
- **Error codes used, none added:** `analysis_input_invalid` with `stage_id` and a `reason` of `portal_inputs_incomplete`,
  `portal_input_unreadable`, `portal_blocks_invalid`, `portal_blocks_page_mismatch`, `recognised_markdown_invalid` or
  `recognised_markdown_mismatch` (new reasons), and `source_unreadable` (unchanged, now also for a stream that breaks or does not match its
  recorded digest); `validation_failed` with `field: page_number` and `constraint: every page must carry extractable embedded text`, as
  before (the message adds "and no portal block").
- **Locks:** `PDFIUM_LOCK` is **not** used, because nothing on this path calls PDFium: `pypdf` probes, `pdfplumber` extracts, and
  pdfplumber imports `pypdfium2` only for `to_image()`, which is never called. A test replaces `pypdfium2.PdfDocument` with a refusal and the
  stage still succeeds. Had it been needed: `ingest.public` does not export the lock today.
- **The artifact `prepared.recognised_text`** (`P02_SEAMS` section 4.8, exactly): root `artifact_role`, `artifact_version` `1.0.0`,
  `version_uid`, `results_sha256` (SHA-256 of the stored `_results.md` bytes), `entries` ordered by page number, then the block's position
  in the markdown, then `portal_block_id`. A TEXT entry: `portal_block_id`, `page_number` (`page_index + 1` from the block list),
  `kind: recognised_text`, `quote_source: recognised`, `text` (the body, markdown, verbatim), `flags`. An IMAGE entry: `portal_block_id`,
  `page_number`, `kind: portal_description`, `text`. No STAMP entry; no offsets. Canonical serialization through `publish_artifact`, so
  equal input gives an equal blob.
- **The flag vocabulary** (lowercase snake_case, each at most once, in this order): `mixed_script`, `homoglyph`, `cjk`,
  `doubled_list_marker`, `degenerate_instruction_echo`, `degenerate_first_person_plan`, `degenerate_page_narration`,
  `degenerate_serialised_payload`, `empty_text`. Definitions: `analysis/recognised/flags.py`'s docstring; the exemption:
  `flags.DESIGNATION`'s comment.
- **Stage metrics added** (bundle versions only; none renamed): `recognised_entry_count`, `recognised_flagged_entry_count`,
  `pages_without_text_layer`.
- **New Python surface:** `auditmanager.analysis.recognised` (`read_blocks`, `read_block_list`, `read_portal`, `flags_for`,
  `inspect_recognised`, `build_recognised_text`, `recognised_entries`, `DESIGNATION`, `FLAG_ORDER`, the kind and marker constants);
  `analysis.public`: `ROLE_RECOGNISED_TEXT`, `ROLE_SOURCE_MARKDOWN`, `ROLE_SOURCE_STRUCTURED_COMPANION`, `KIND_RECOGNISED_TEXT`,
  `KIND_PORTAL_DESCRIPTION`, `QUOTE_SOURCE_RECOGNISED`; `analysis.stages.extraction.PdfSource`, with `extract_document` and
  `probe_envelope` taking bytes or a path; `norms.public`: `DegeneracySignal`, `inspect_degeneracy`.

## 4. Risks and limitations

### 4.1 The measured precision (F-7: counts only)

**Method.** A scratch script in the session scratchpad (never committed), run as `.venv/bin/python -I <scratchpad>/measure/precision.py
<worktree> .local/portal-exports/<the owner's export>.zip`, which puts the worktree's `src` on `sys.path` itself. It reads the archive in
memory (nothing extracted to disk, nothing copied), takes the PDF's text layer per page with the product's own `extract_document`, reads the
markdown and the block list with `read_portal`, and runs `inspect_recognised` on every TEXT body. For each flag's evidence: a flagged word is
a **false positive** if the same page's text layer (NFC, split into words by the flags module's own word pattern) holds it verbatim, and a
**true positive** otherwise; a doubled marker is false if a line of that page's text layer starts with the same markers; a degeneracy
phrase is false if the page's text holds it (case-folded). The view used to tune the rules printed letters as `L`, `l`, `C`, `c` and digits
as `d`, never a word. **Read-only:** the export's SHA-256 prefix and modification time were identical before the first read and after the
last; nothing derived from it is in the repository.

| The heuristics | flagged TEXT blocks of 56 | `mixed_script` TP / FP | `homoglyph` TP / FP | `doubled_list_marker` TP / FP | overall precision |
| --- | --- | --- | --- | --- | --- |
| as first written | 21 | 11 / 0 | 11 / 7 | 137 / 0 | 159 / 166 = 0.958 |
| the mirror whole-word rule removed (decision 7) | 20 | 11 / 0 | 11 / 0 | 137 / 0 | 159 / 159 = 1.000 |
| the exemption narrowed (decision 8): **final** | 22 | 11 / 0 | 27 / 0 | 137 / 0 | **175 / 175 = 1.000** |

- The export: 30 pages, 56 TEXT and 47 IMAGE bodies (IMAGE bodies are not flagged, by design), no empty body. Final blocks per flag:
  `mixed_script` 9, `homoglyph` 12, `doubled_list_marker` 11. `cjk`, the four degeneracy flags and `empty_text`: **0** on the export.
- The exemption on the export: with the final pattern it suppresses nothing (a run with the pattern disabled gives the same counts). The
  first pattern suppressed 16 words in 2 blocks, all of the shape one Latin capital and one digit, none of them in the text layer; that is
  why it was narrowed. The 7 false flags of the first version were all two-letter Cyrillic capitals between Latin words.
- **Recall on the synthetic set** (`ar_baseline_ocr_defects.zip`, its manifest's `seeded_text_defects`): **6 of 6** flaggable flaws flagged
  on the recognised word (2 homoglyphs, 1 CJK character, 2 doubled markers, 1 mixed-script word); **4 of 4** designations (`B25`, `A500C`,
  `1.A`, `REI 150`) unflagged.

**What it does not cover:** (1) "true" means *not verbatim in the PDF's text layer*, not *wrong*: a Latin `x` standing for a `×` or a
Cyrillic `х` counts as true though a reader might call it typography; (2) there is no recall figure on the real export (no ground truth of
its OCR errors); (3) `cjk`, the degeneracy flags and `empty_text` never fired on real text, so they rest on synthetic and unit cases alone
(no committed portal text carries a degenerate or empty body, and fixtures are FIXTURES'); (4) one document, one portal, one recognition
model; (5) **the final precision is in-sample**: two rules (decisions 7 and 8) were changed because of what the same export showed, so
1.000 is the figure after tuning on the document it is measured on, not an estimate for an unseen one. The wave executor re-ran the
suites and six spot mutations independently (section 7).

### 4.2 Other risks

1. **`doubled_list_marker` fires on a portal habit.** On the export it marks 137 lines in 11 of 56 blocks: the portal writes nested list
   markers (`- - ...`, `1. 1. ...`) the PDF does not have. True by the criterion, and the plan names the flag, but it will be the flag a
   reviewer sees most; how «Блоки» shows it is WEB-BLOCKS'.
2. **Two readings of "has a text layer".** INGEST admits a page by pypdfium2's per-page text presence; the stage refuses by pdfplumber's
   extracted characters. A page where pypdfium2 sees characters and pdfplumber extracts none, with no portal block on it, is admitted at
   upload and refused when the run starts (`validation_failed`, as before this lane). No such page exists in the fixtures or the export.
3. **The exemption is a trade.** `B25`, `A500C`, `REI 150`, `СП 7-АР` written with Latin look-alikes are not flagged even where the PDF has
   Cyrillic. A code of one capital and one digit (`C0`) is flagged, which will be a false flag on a document whose own PDF writes it in Latin.
4. **The temporary file** is up to 250 MiB in the process's temporary directory (the worker image's `/tmp`, its writable layer) for the
   length of the extraction; one run per worker at a time. Memory of the extraction itself is unchanged (pdfplumber keeps per-page objects
   until the document closes); REHEARSAL measures the 500-page low-text run.
5. **An empty body** is an entry with `text: ""` (and `empty_text` on a TEXT one), while the wire's `PortalRecognisedText.text` and
   `portal_description` are `minLength: 1`: the joiner must leave the member out (section 5).
6. **Stale prose outside the grant:** `src/auditmanager/analysis/README.md` lines 112-115 still say `has_text_layer` is `true` for every
   page; the README is GEOMETRY's file (plan §B4, item 4).
7. **`P02_SEAMS` section 4.2** places the refusal "at ingest" with the constraint `every_page_has_extractable_text`; the stage's own refusal
   (a second line behind ingest, for versions published another way and for the reading in risk 2) keeps its existing field and constraint
   string. Recorded, not redesigned, as the plan asks for contradictions with §B3.5 to §B3.7.

## 5. Integrator instructions

1. Merge `agent/w55b` through this report's commit. No contract, migration, lock file or composition root is touched.
2. **Heavy steps owed: none of this lane's.** Light acceptance only (`R-102`); the one full `make gate` runs on the final W55b candidate.
3. **`src/auditmanager/runs/executor.py` is outside the plan's grant** (a plan gap, pre-authorised by the wave executor; you may veto). It is
   the minimal change: the manifest entries for `source.markdown` and `source.structured_companion` are seeded into the stage outputs and
   both roles join `source_preparation`'s tuple; `page_geometry_extraction` is not wired. Without it no real run publishes the artifact.
4. **`tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py` is outside the grant, forced** (section 2.2).
5. **`src/auditmanager/analysis/stages/extraction.py`** is not in the plan's path list; the brief directed the path form there. The bytes
   form is unchanged for `page_geometry_extraction` and four tests.
6. For **GEOMETRY**: add its export lines to `analysis/public.py` after this lane's; `page_geometry_extraction` still reads the PDF whole
   (`read(verify=True)`, then bytes) and can switch to `extract_document(path)` with the same temporary-file pattern
   (`source_preparation._source_file`); the joiner of `listVersionPortalBlocks` reads `prepared.recognised_text` by `portal_block_id`,
   puts a `recognised_text` entry under `PortalRecognisedText` (`quote_source`, `text`, `flags`) and a `portal_description` entry's `text`
   under `portal_description`, and **omits either when its text is empty** (`minLength: 1`); and corrects the README lines of risk 6.
7. The lane stack is down: `make down`, `docker volume rm auditmanager-w55b-recognised-postgres-data
   auditmanager-w55b-recognised-s3-data`, `.env` removed.

## 6. Containment

`git diff --name-only 19ea1525..HEAD` is the list of section 1 (22 paths). Against the grant:

- **inside:** `src/auditmanager/analysis/stages/source_preparation.py`; `src/auditmanager/analysis/recognised/**` (5 files);
  `src/auditmanager/analysis/ports/artifacts.py` and `src/auditmanager/analysis/public.py` (role constants and export lines only);
  `src/auditmanager/norms/public.py` (one import line, and its two `__all__` names); `tests/integration/analysis/recognised/**` (8 files);
  `tests/integration/analysis_engine/test_fail_closed.py` (a source-preparation case the rule moved: its docstring only);
  `docs/program/W55B-RECOGNISED-01.md`;
- **outside, each with its reason:** `src/auditmanager/runs/executor.py` (pre-authorised, section 5 item 3);
  `src/auditmanager/analysis/stages/extraction.py` (the path form the brief directed, item 5);
  `tests/integration/runs/test_a_halted_chain_reaches_a_terminal.py` (forced, section 2.2).
- **Forbidden hotspots untouched:** `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `src/auditmanager/bootstrap/**`, any
  `conftest.py`, `tests/support/**`, `fixtures/**`, `tools/**`, `web/**`, `P02_SEAMS.md`.
- `git status --porcelain -uall` is empty at the tip.

## Appendix: design decisions (made while writing; each is open to the integrator's veto)

Each decision names the alternative rejected.

1. **Manifest roles are the dotted contract roles.** The brief says the manifest spells the two bundle roles with an underscore; the tree says
   otherwise: `documents.models.MANIFEST_ROLE_MARKDOWN` and `MANIFEST_ROLE_STRUCTURED_COMPANION` are read from the stage registry and are
   `source.markdown` and `source.structured_companion`. The underscore spelling (`source_markdown`, `source_structured_companion`) is the
   **blob** role on the object. The executor therefore looks the entries up by the contract role, exactly as it already does for
   `source.document`.

2. **An own markdown reader, held equal to INGEST's by a test.** `analysis/recognised/markdown.py` restates the grammar INGEST counts
   `recognised_character_count` by (the block header, the `## Page N` heading, the `> **Key:**` quote lines, the trimming of blank lines, a
   trailing carriage return dropped per line). Rejected: importing `ingest.bundle_envelope` (a deep import across bounded contexts, ALR-05) and
   exporting INGEST's private parser through `ingest.public` (outside the grant, and it would bind analysis to ingest's internals). A test
   runs both over every committed bundle and requires the same character count per block.
3. **The stage re-checks the two members cheaply, and only what it reads.** The block list: strict UTF-8 JSON, a `pages` list as long as the
   PDF's page count, and per block a `blk_<32hex>` id (unique), a type of the three and a page index on a page of the PDF. The markdown: UTF-8,
   and the both-way agreement INGEST enforces at upload. Each refusal is `analysis_input_invalid` with its own `reason`
   (`portal_blocks_invalid`, `portal_blocks_page_mismatch`, `recognised_markdown_invalid`, `recognised_markdown_mismatch`). Rejected:
   re-running the whole pinned block-list schema (INGEST's at upload; the boxes and polygons are GEOMETRY's to normalise).
4. **Both members or neither.** A markdown without a block list, or the reverse, is refused (`portal_inputs_incomplete`); a member the store
   cannot hand back is `portal_input_unreadable`. Rejected: applying the text-layer-or-block rule from the block list alone and skipping the
   artifact (a silent half-bundle).
5. **The flag vocabulary** (open, lowercase snake_case, in this order): `mixed_script`, `homoglyph`, `cjk`, `doubled_list_marker`,
   `degenerate_instruction_echo`, `degenerate_first_person_plan`, `degenerate_page_narration`, `degenerate_serialised_payload`, `empty_text`.
   Definitions are in `flags.py`'s docstring. Flags are computed on an NFC copy; the stored text is not normalised.
6. **One flag per degeneracy signal**, `degenerate_<signal value>`, derived from `norms.public.DegeneracySignal` so a signal the norms context
   adds becomes a flag instead of a crash (a test pins today's four). Rejected: a single `degenerate` flag (it loses which of four different
   failures it was). `norms.public` gained one import line (`DegeneracySignal`, `inspect as inspect_degeneracy`) and its two `__all__` names.
7. **`homoglyph` reads within a word both ways, and a whole word one way.** Within a word: the minority script's letters are all look-alikes
   of the other script (`Уровeнь`; the reverse, `Systеm`). A whole word: a Latin word whose letters are all look-alikes, between Cyrillic words
   on its line (`c` for `с`, `600x600`). The mirror whole-word rule (a Cyrillic look-alike word between Latin words) was written, measured on
   the owner's export, raised 7 flags that were all false (the PDF's own text layer held each word) and nothing true, and was removed.
8. **The designation exemption is one pinned pattern (`flags.DESIGNATION`), narrowed by measurement.** It matches `1.A`, `B25`, `A500C`,
   `REI 150`, `СП 7-АР` and their kind (its docstring lists what it matches and deliberately does not). The first version also matched one
   capital and one digit (`C0`, `B1`); on the owner's export that hid 16 words, none of which the PDF's text layer holds (hazard classes written
   with a Latin look-alike: real substitutions), and suppressed no false flag. A single capital now needs a number of two digits or more.
   Rejected: dropping the exemption (the brief requires it) and widening it to every capital-and-digit code.
9. **An empty body is an entry with `text: ""`**; a TEXT one carries `empty_text`. Section 4.8 says one entry per TEXT or IMAGE block the
   markdown holds, so the block is not dropped. The wire's `PortalRecognisedText.text` and `portal_description` are `minLength: 1`, so the
   joiner (GEOMETRY / the blocks adapter) must leave the member out for an empty entry: recorded for the integrator (section 5).
10. **The PDF goes to a temporary file through `open_stream`.** `inspect()` gives the recorded SHA-256 and size; `open_stream(...)` (a whole
    read) hashes while it streams and withholds the last chunk unless the digest is the recorded one -- the comparison `read(verify=True)`
    made. The file is `tempfile.mkstemp` in the process's temporary directory, removed in `finally` (success or failure). Rejected: `read()`
    then write (the bytes would still be whole in memory) and `NamedTemporaryFile(delete=True)` (the extractor reopens the file by its path).
11. **`extract_document` takes bytes or a path (`PdfSource`).** For a path, `pypdf` gets an open file object (given a path, `PdfReader` would
    read the whole file into memory) and `pdfplumber` opens the path itself. Neither is `pypdfium2` (pdfplumber imports it only for
    `to_image()`, which nothing here calls), so `PDFIUM_LOCK` is not taken; a test proves no PDFium document is opened during the stage.
    The bytes form is unchanged for its callers (`page_geometry_extraction` and four tests).
12. **Metrics.** Three new names, emitted only for a bundle: `recognised_entry_count`, `recognised_flagged_entry_count`,
    `pages_without_text_layer`. No existing metric is renamed. Rejected: emitting zeros for a version without a bundle (zero entries and no
    bundle would read the same).
13. **The refusal keeps its field and constraint** (`page_number`, `every page must carry extractable embedded text`); the message gains
    "and no portal block". `has_text_layer` is `char_count > 0`.
14. **The executor** seeds `outputs.refs` with every manifest entry whose role is `source.markdown` or `source.structured_companion` and adds
    both roles to `source_preparation`'s tuple (absent roles are simply not supplied). `page_geometry_extraction` is not wired (GEOMETRY's).
15. **`analysis.public`** exports `ROLE_RECOGNISED_TEXT`, `ROLE_SOURCE_MARKDOWN`, `ROLE_SOURCE_STRUCTURED_COMPANION` (in the existing
    `ports.artifacts` import) and `KIND_RECOGNISED_TEXT`, `KIND_PORTAL_DESCRIPTION`, `QUOTE_SOURCE_RECOGNISED` (one line after BUDGET's); nothing
    reordered.
16. **The mutation driver and the measurement scripts stay in the session scratchpad**, never committed, as the brief requires for the
    measurement; the mutation method and its results are in section 2.1. Rejected: a committed mutation tool (outside the grant).
17. **The two bundle members are read whole** (`read(verify=True)`): INGEST bounds each at 16 MiB, and the reader needs the whole markdown
    to agree it with the list. Only the PDF, up to 250 MiB, is streamed. Rejected: streaming the markdown too (no gain at that bound).

## 7. Verification by the wave executor (after the writer's hand-back)

Run by the wave executor on its own lane stack (same ports), a freshly migrated database, tip `79b88974`, one invocation at a time; exit codes read directly.

| Check | Result |
| --- | --- |
| `git diff --check 19ea1525..HEAD`; `git status --porcelain -uall` | exit 0; empty |
| `tests/contract` (the three files excluded) on the committed tip | 752 passed, 18 927 subtests |
| `tests/integration/analysis`, `analysis_engine`, `runs`, `p02_journey` | 411, 47, 200, 59 passed (the writer's counts) |
| spot mutations (restored byte for byte, SHA-256 compared): the executor's role tuple; `has_text_layer` always true; the temporary file kept; the exemption widened to one capital and one digit; a wrong `source_sha256` in the inventory; a wrong digest held to the stream | all six red |

The sixth and fifth are not rows of section 2.1: the existing `test_page_inventory_shape` and the S3 stage cases catch them. The temporary-file mutation
left 19 `am-source-*` files in the temporary directory, as section 2 says it does; they were removed by name.

Two corrections to the writer's hand-back message (not to this report): the lane is 12 commits above `19ea1525`, not 14, and the report's
containment count was 23 paths where the list holds 22 (fixed above).
