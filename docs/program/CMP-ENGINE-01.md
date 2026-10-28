# CMP-ENGINE-01 — the per-sheet comparison engine: a ceilinged child, the eight channels, the content-keyed result and its mask

Written 2026-10-28 by the Sonnet lane `CMP-ENGINE-01` (size XL, branch `agent/cmp-engine-01`, base `d11c13fd` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-ENGINE-01.md`](tasks/CMP-ENGINE-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (5, 7, 8, 9, 10, 15, 16, 18, 20, 23 and both addenda); the wave brief is [`dispatch/CMP-WAVE-C1.md`](dispatch/CMP-WAVE-C1.md) (section 4 is the pair evidence interface this lane writes); the oracle is the synthetic corpus `fixtures/comparison` with its answer keys; the original is PDF-proverka at `23f379fd`.

## 1. Result

For a project and two page profiles the engine answers the result identity of the pair: from the cache when the content key exists in the project, else computed in **one child process** under the ceilings of decision 8 (768 MiB of address space, 300 s of CPU, 600 s of wall) and written, **the mask blob first and then the row**. The child registers B onto A on the downsampled 36 dpi masks, renders both pages through PDFium **a band of rows at a time** (so a 40 Mpx canvas fits), computes the layers of the original (only in A, only in B, line style, light elements, colour, tolerance, noise), the text changes with their numbers, the moved blocks, the regions and their classes, the eight channels, the status and the forcing reasons, and the eight planes of the mask. An end without a result, whatever its cause, is a stored `needs_review` result with reason `RENDER_FAILED` for that pair only. Two entry points are exported for `CMP-SERIES-01`: `compare_sheet_pair(...)` and the work kind `pair_result` with `enqueue_pair_result(...)`; the mask codec (`engine/mask_codec.py`, the second commit) is ready for the viewer.

Measured on the real set (numbers only, section 6): **59 pairs of the three adjacent transitions (33 compared by a child, 26 of byte-identical files that need none) pairs of the three adjacent transitions, none ended without a result; the worst address space of a child was 568.6 MiB (ceiling 768), the worst peak resident set 300.2 MiB, the worst time 10.7 s, the masks together 6 233 092 bytes.**

## 2. Base facts, printed before any edit

`contract 1.10.0 131 paths 148 operations 432 schemas`, `VERSION` `0.9.0`, head `0039_comparison_core`, base `d11c13fd01f431bb081ad9f984fc6a3dc615b39e` (`P-01` of the task file). They equal the premise of the brief, so the lane went on. No contract, migration, dependency or lock file was changed. **The original's clone `/root/projects/PDF-proverka` does not exist on this host** (`D-252`, the owner is re-cloning it): the lane read the original's files at the pinned commit from the public repository's raw files (`backend/app/services/version_comparison/{settings,status,engine,registration,textdiff,service,separation,blocks,block_alignment,pdfio,stamp,profile,jobs,parts}.py`) into a scratch directory outside the repository (`P-02`). Every rule ported below cites the file and line of that source; no file of it was copied.

## 3. What was built

| Path | What it holds |
| --- | --- |
| `engine/mask_codec.py` | the second commit (`b1b3948a`): `MASK_FORMAT = 1`, `LAYERS`, `encode_mask`, `encode_packed_planes` (a band at a time; accepts a sequence of eight planes), `decode_mask` with a **bounded decompression**, `DecodedMask` (`packed`, `plane(name)`, `planes()`); stdlib and `numpy` only |
| `engine/child/program.py` | the child: `python -I -B program.py '<json>'`; sets `RLIMIT_CORE`, `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE` **before it loads anything**, shuts the thread pools before `numpy` is imported (the default pools reserve 1.5 GiB of address space), loads its own directory as a package under a private name and the codec beside it, imports nothing from the product, writes JSON lines (`limits_set`, then one `status`) |
| `engine/child/job.py` | the job (port of `engine.compute_sheet_pair`): zones and registration from the profile, A's bands (compressed), B's bands through the registration matrix, the plane store, words, blocks, text changes, regions, windows (overdraw, QR), channels, status, the mask, `outcome.json` |
| `engine/child/{settings,status,textdiff,words,annotations,result}.py` | pure Python (also imported by the worker's side): the thresholds with the original's line, the channels and `decide`, the text diff, words/warnings/release marks/frame/title block/kind of a sheet, annotations, the outcome and the `result` of the brief |
| `engine/child/{geometry,planes,render,layers,blocks,regions,zones,registration}.py` | `numpy`/`cv2`/`pypdfium2`: canvas and bands; the one-bit plane store; `FPDF_RenderPageBitmapWithMatrix` a band at a time and the compressed band store; the pixel layers of a band; moved blocks on windows; regions on a reduced canvas and the checks around them; zones and QR; registration |
| `engine/{service,key,repository,validate,inputs,limits,runner}.py` | the worker's side: `compare_sheet_pair`, `compute_pair` (no database), the content key, the SQL of `comparison_sheet_pair_result`, the validation by the generated models, the child's inputs, the numbers, the runner of the page-profile child with the engine's program |
| `engine/{handler,enqueue}.py` | the `pair_result` handler and `enqueue_pair_result` |
| `comparison/public.py` | appends only: the imports of the engine, `pair_result_handler` in `HANDLER_FACTORIES`, the new names in `__all__` |
| `scripts/recovery/grant_classification.py` | `comparison_sheet_pair_result` leaves `SEALED_NOT_YET_WRITTEN` (the code now writes it) |
| `tools/measure/comparison_engine.py` | the measurement (numbers only) |
| `tests/unit/comparison/engine/**`, `tests/integration/comparison/engine/**` | section 8 |

## 4. The original's rules, what was ported, and where this product differs

### 4.1 Ported (line numbers are those of the original at `23f379fd`)

| Rule | Original | Here |
| --- | --- | --- |
| thresholds: tolerance 0.5 pt; dark 200, light 250; colour 25, luma 60; noise 2 px; light delta 10; style fill 7 px; overdraw 25 / 0.6; blocks 5 words, 1.0 pt, 3.0 pt, 0.6; glyph 2.0 / 0.85 / 0.25; shift 0.9, 5 mm, 6 pt; region closing 1.5 mm; word move 20 pt; anchors 8 / 0.15 / 0.6 pt / 2.0 pt; align Dice 0.5, switch 0.1 | `settings.py:37-38, 46-47, 50-51, 53, 56, 60, 63-64, 68-71, 77-79, 81, 83, 85, 87, 90, 196-203` | `engine/child/settings.py`, each constant with its line; `PARAMS` is part of the content key |
| channels, main/service sets, forcing reasons, `decide` | `status.py:11-20, 45-66` | `child/status.py` |
| fast path for pages of the same content | `engine.py:505-527` | `child/result.identical_outcome`, `service._same_content` |
| the pixel layers: unique-to-A/B, style, noise, light elements, within tolerance, colour | `engine.py:575-684` | `child/layers.py` (band by band; the margin is `2 r + 10` rows, proved by `test_a_band_with_its_margin_gives_the_core_rows_of_the_whole_canvas`) |
| word comparison (same / moved ≤ 20 pt / only in A / only in B, greedy nearest) | `engine.py:142-178` | `child/words.compare_words` |
| text changes, numbers, normalisation classes | `textdiff.py:22-227` | `child/textdiff.py` |
| moved blocks: vote of word vectors, raster confirmation, explained pixels to the layer «moved» | `blocks.py:33-83, 112-184` | `child/blocks.py` (on windows of the plane store) |
| aligned blocks (`share ≥ 0.9`, no competing translation) | `block_alignment.py:16-24` | `job._aligned_blocks` |
| region grouping (closing 1.5 mm, one text change one region), classes in the original's order, shift explained, glyph lines, overdraw | `engine.py:759-898, 234-275, 192-232, 278-307` | `child/regions.py` and `job._classify_regions`, `_shift_and_glyph` |
| annotations (kind, IoU ≥ 0.5, changed by text) | `engine.py:348-379` | `child/annotations.py` |
| warnings baked into the content | `engine.py:310-333`, `separation.py:38-45` | `child/words.warning_lines` |
| registration: anchors, phase correlation of the 36 dpi masks, Dice, snap to identity, identity check | `registration.py:62-157` | `child/registration.py` |
| zones: title block, release mark with QR patch, margins outside the frame; QR read | `profile.py:64-125`, `stamp.py:68-111, 157-190`, `service.py:51-84` | `child/zones.py`, `child/words.py` |
| service fields «было → стало» (title block, release mark date and text, QR, signature images) | `service.py:125-183` | `job._service_fields` |
| spec sheets: positions not compared (`unchecked` unless the main channels are clean) | `engine.py:996-1000` | `job.run` |
| status names, 40 Mpx canvas | — | `ComparisonSheetStatus` (the four with a result), ADR-0025 decision 9 |

### 4.2 Where this product differs, and why

1. **`annotations` is a main channel** (original: a service channel, `status.py:13`). ADR-0025 decision 15 and plan R3-09 say an annotation-only change gives `different` in `annotations`; so does the answer key (V1→V2, sheet E05). `test_an_annotation_only_change_is_different_not_a_service_change`, mutation M4.
2. **The canvas is the page of A** (original: the union of A and the carried B, `engine.py:66-91`), because the wave brief fixes the mask grid to A's canvas. What B puts outside it is not compared; ink of B outside the canvas by more than 3 pt (three pixels of the 36 dpi mask) makes the pair `PARTIAL_COVERAGE`, which forces `needs_review`.
3. **No stream-level separation of overlay objects** (`separation.py`). It edits the page's content streams in memory with `PyMuPDF` (excluded, `OD-01`); the same through `pypdf` copies an A1 page into more than the ceiling. A release mark is therefore a *zone* the main comparison leaves out (what the original does with a mark it could not separate, `engine.py:452-458`), and a warning set into the page content gives `warnings` `unchecked` and `PARTIAL_COVERAGE` (`engine.py:978-981`, the original's own answer to a warning it did not separate). `how_compared.separated_objects` counts the release marks set aside.
4. **Two forcing reasons of its own**: `PAGE_TOO_LARGE` (a page the profile refused at the 40 Mpx cap) and `FRAME_MISMATCH` (the profile's own reason). The original's twelve are unchanged.
5. **`NO_TEXT_LAYER` is also given when only one of the pages has no text layer** (original: only when neither has, `engine.py:925-927`; when one page is a scan the original reports every word of the other as removed). ADR-0025 decision 11 says a scan is compared as an image only; the key says the same (V3→V4, sheet E04). The `text` channel is then `unchecked`.
6. **Registration** keeps the original's anchors and phase correlation, with four changes that the 768 MiB ceiling or the precision asked for: (a) the similarity RANSAC is written in `numpy` (`cv2.estimateAffinePartial2D` reserves **136 MiB** of address space the first time it runs); (b) a 36 dpi mask over 1 Mpx is reduced by an integer factor before the transform (a 2A0 mask needs **180 MiB** at full size); (c) the shift is **refined from the vector lines** of the profile (`refine_by_lines`: the corners of A's lines minus those of B's agree on one vector to a tenth of a point; accepted only with 8 votes, 5 % of the points, and a peak at least twice the next, so a hatch is not voted on): a drawing re-issued with unchanged coordinates is registered exactly, which the phase correlation (good to half a pixel of the mask, 1 pt) cannot do (the split sheet of the corpus went from 171 false differences to 1); (d) the identity is kept when it agrees with the drawing as well as the phase estimate does.
7. **Budgets.** Every check that looks at pixels around a region has a window cap (4 Mpx) and the analysis of regions has a CPU budget (120 s): when one is spent the region keeps the class the cheap rules gave it (never a shift, which would hide a difference) and the pair gets `PARTIAL_COVERAGE`.
8. **Text-change kinds** are `changed`, `added`, `removed`, `moved`, with the normalisation class appended (`changed_spaces`, `changed_symbol`, `changed_number_format`): the contract's `kind` is an open pattern.
9. **`result` carries one member the brief does not list**: `part` (`{"kind": "split"|"floors", "area_a_pt", "coverage_a", "reliable"}`), only for a split sheet or a sheet of floors, because the parts coverage of `CMP-SERIES-01` (`jobs.py:875-950`) needs the area of the part and whether the registration is reliable. It is additive and not an API field; section 11 asks the FIX slot to confirm it.

## 5. The corpus' answer keys against the engine

`test_against_the_answer_keys.py` runs the real page children and the real engine child on **every pair of the keys that has two pages** (23 pairs of VS-1 over the four transitions; the added and removed sheets E06 and E07 have no result by design) and compares, per sheet: the status, the reasons the key names (`NO_TEXT_LAYER`, `DUPLICATE_SHEET`), every channel in `channels_without_differences` (must be `checked` with no difference), every channel in `channels_with_differences` (must report a difference; for `text_coverage` an `unchecked` with its reason counts), the mask (a `same` result has none; any other decodes to the grid its `result.mask` declares), and the contract validation of the whole outcome. A time and a position check: the label «ЩО-1» of V1→V2 is found in both places (the removal at the key's `bbox_before`, the addition at `bbox_after`, the key's lower-left origin converted), and the changed table number is listed with its numbers.

**Status: 22 of 23 agree.**

| Transition | E01 | E02 | E03 | E04 | E05 | E06 | E07 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V1→V2 | `same` ✓ (identical) | `different` ✓ | `different` ✓ | `same_zones_changed` ✓ | `different` ✓ (annotation only) | `same` ✓ (identical) | — |
| V2→V3 | `different` ✓ | `different` ✓ | `same` ✓ (identical) | `different` ✓ | `different` ✓ | removed (no result) | added (no result) |
| V3→V4 | `different` ✓ | `same` ✓ (identical) | `different` ✓ | `needs_review` ✓ (`NO_TEXT_LAYER`) | `different` ✓ | — | `same` ✓ (identical) |
| V4→V5 | `different` ✓ | `same` ✓ (identical) | `needs_review` ✓ (`DUPLICATE_SHEET`, identical) | `same` ✓ (identical scan) | **`different`** ✗ (key: `needs_review`, split) | — | `different` ✓ |

**Every disagreement, named and tested** (the test fails if one appears that the list does not name, or one it names goes away). They are differences between the key's reading and the original's rules, which the engine follows; none is a status the engine got from a guess.

1. **V4→V5, E05 (the split A1 → A2 part): `different`, key `needs_review` with `SPLIT_SHEET`.** The registration is exact (method `lines`, identity), the part's area is found, and one region of 14 pt at the cut remains (before the line-based registration it was 171 false differences). `SPLIT_SHEET` is not a reason of the engine and not forcing in the original: `needs_review` for a split is the series' verdict from the coverage of **all** the parts (`jobs.py:875-950`), which one pair cannot know. The result carries `part.area_a_pt`, `part.coverage_a`, `part.reliable` for that verdict.
2. **V2→V3, E04 (the bus line weight 0.5 → 1.5 pt): `geometry` reports 1, `color` reports 0; the key wants `color` and no `geometry`.** The extra pixels of the thicker pen are light elements only in B (class `light`, layer `light_elements`); the original counts `light` in `geometry` (`engine.py:913-919`); `style` regions (a thicker pen whose extra pixels fall inside the dilated ink of the thin one) count in `color`.
3. **V4→V5, E03 (the duplicated sheet): `warnings` reports no difference; the key wants it to.** The pages are byte-identical, so the fast path (`engine.py:505-527`) gives every channel `checked` with 0; `DUPLICATE_SHEET` forces the status. The key's `warnings` requirement has no source in the original.
4. **V4→V5, E07 (the specification): `spec_positions` is `unchecked`, not a difference.** The original does not compare positions in its engine (`engine.py:996-1000`: `unchecked` when the main channels differ); `CMP-VC-SPEC-01` owns them. The status (`different`, from `text`) agrees.
5. **V1→V2, E02: the label moved by (+120, +30) pt is a removal and an addition, the key calls it `text_moved`.** `WORD_MOVE_PT` is 20 pt (`settings.py:90`); beyond it the original reports the text as removed from one place and added at another (`text` reports 2 differences, as the key requires).

The disagreements are **reported, not adjusted away**: the keys are the fixtures lane's, and the engine's rules are the original's.

## 6. The real set: time, memory and bytes (numbers only)

The set is `.local/comparison-measure/13AV-RD-EM2-PA/` (four versions of one project: 15, 18, 26 and 26 pages from A4 to 2A0, 1682 x 1189 mm). It was read **by code only**: no page, word, text or raster was opened, printed, shown or committed; the records hold numbers and state words.

* **Command** (from the lane worktree, the lane's interpreter, no other run on the lane, the host loaded at 12 to 34):
  `PYTHONPATH=$PWD/src AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent .venv/bin/python tools/measure/comparison_engine.py --out <records>.jsonl --work-dir <scratch>` (the scratch directory is deleted by the program; the set is the script's default `/root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA`).
* **Tree**: commit `986f813e7f6ee87b618bdb281f9c11e3315a4c49`, clean (`git status --short` empty), 2026-10-28 15:40 (+05:00); Python 3.12, `numpy` 2.5.4, `opencv-python-headless` 4.14.0, `pypdfium2` 5.13.0; the page profiles were built by the real children of `CMP-PROFILE-01` in the same run (`cmp-profile/1`).
* **Pairing**: the transitions are `v1→v2`, `v2→v3`, `v3→v4`. A page is paired **by the sheet number the profile reader gives from the stamp** when that number is read on exactly one page of each version (8 pairs of the 59), and **otherwise by index** (51 pairs). The reader reads few stamps on this set (strokes-only text), so most pairs are by index and, where a sheet was added or removed between versions, pair two different sheets; the numbers below are a load and a memory measurement, not a verdict on the pairs. `v3→v4`: the files are byte-identical, so all 26 pairs have the same Merkle and take the fast path (no child), status `same`.

| | pairs | by child | `same` | `different` | `needs_review` | mask bytes | child time (sum / worst) | worst address space | worst peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `v1→v2` | 15 | 15 | 4 | 0 | 11 | 2 605 927 | 43.2 s / 9.0 s | 462 MiB | 232 MiB |
| `v2→v3` | 18 | 18 | 7 | 5 | 6 | 3 627 165 | 63.6 s / 10.7 s | 569 MiB | 300 MiB |
| `v3→v4` | 26 | 0 | 26 | 0 | 0 | 0 | — | — | — |
| **all** | **59** | **33** | **37** | **5** | **17** | **6 233 092** | **106.8 s** | **568.6 MiB** | **300.2 MiB** |

* **Every child ended with a result** (33 of 33 `ok`; none overran, none was killed). **The worst address space of a child is 568.6 MiB against the ceiling of 768 MiB** (the quantity `RLIMIT_AS` limits, read by the child from `/proc/self/status` `VmPeak`); the worst **peak resident set** (`VmHWM`) is **300.2 MiB**. Both are of the same pair (`v2→v3`, page 13, 4767.8 x 3370.3 pt = 1682 x 1189 mm, 2A0, 113 dpi, 39.6 Mpx). The gate of the brief (the worst A1 pair's peak RSS under the ceiling) is met by **268 MiB** of resident set and **199 MiB** of address space.
* **Time**: the worst pair takes 10.7 s of wall and 10.7 s of CPU (the ceiling is 300 s of CPU, 600 s of wall); the eight pairs over 30 Mpx take 7.3 to 10.7 s each. The 33 child pairs together take 106.8 s.
* **Bytes**: the masks of the 33 pairs total **6 233 092 bytes** (189 KB a pair on average, 1 088 523 bytes at most, the 2A0 pair that differs most); the eight pairs over 30 Mpx hold 4 220 415 of them. The 37 pairs that are `same` have no mask and no blob. For 12 sheets of 100 pairs the ADR's estimate of 0.5 to 3 GB for masks is, on this set, 20 MB.
* **Statuses** (a load test; the pairs are partly by index): `needs_review` 17 (reasons `NO_TEXT_LAYER` 11, `PARTIAL_COVERAGE` 6, `TEXT_UNREADABLE_IN_DIFF_AREA` 4, `ALIGNMENT_PARTIAL` 3, `ALIGNMENT_UNRELIABLE` 2), `different` 5, `same` 37. Every large page of this set has no text layer, so the original's `NO_TEXT_LAYER` rule makes its pairs `needs_review`; `CMP-MEASURE-01` compares these with the original's statuses.
* **What the figures cost to reach.** The first run of this tree-to-be measured **727 MiB** of address space on the worst pair (5 % under the ceiling). Three causes, found by reading `VmPeak` at the stages of the job (`facts.peaks_mib`), were removed: the phase correlation of the 36 dpi masks (180 MiB at 2A0 size, now reduced by an integer factor), `cv2.estimateAffinePartial2D` (136 MiB reserved at its first call, now `numpy`), and the windows of the block check (12 Mpx, now 4 Mpx); the bands are 1 Mpx and the mask planes are compressed one after the other. `ru_maxrss` from `wait4` is **not** reported as the child's peak: it includes the resident set of the measuring parent at the `fork` (410 MB for the child of an A4 pair whose own peak is 158 MiB), which `CMP-PROFILE-01` noted too; the program reads the child's own `VmHWM`.

## 7. Safety rules as acceptance criteria, each with a mutation proof

Tool: `mut.py ID FILE 'OLD=>NEW' TESTS...` (kept outside git) edits the file, runs the tests, restores the file with `git checkout`, runs them again, and prints `git status` of the file. Every row: the mutation, the test that turns red, then green on the restored file, tree clean. All mutations were made on the committed tree.

| Id | Rule | Mutation | Red | Green |
| --- | --- | --- | --- | --- |
| M1 | ADR 8: the child holds its address space; an overrun gives `RENDER_FAILED`, never `same` | `engine/child/program.py`: the `RLIMIT_AS` line replaced by `pass` | `test_a_child_that_passes_its_address_space_ends_without_a_result_and_the_pair_is_render_failed` (the 120 MiB child completes) | 1 passed |
| I7 | ADR 8: an end without a result is stored, for that pair | `service.py`: `if not result.ok:` → `if False:` | `test_a_pair_whose_child_passes_the_address_space_is_stored_render_failed_and_is_not_computed_again` | 1 passed |
| M2 | the same-needs-every-channel rule | `child/status.py`: the unchecked-channel branch of `decide` → `if False:` | `test_a_channel_that_is_unchecked_is_never_same[geometry]` (and the rest of the eight) | 48 passed |
| M4 | ADR 15: an annotation-only change is `different` | `MAIN_CHANNELS` without `annotations` | `test_an_annotation_only_change_is_different_not_a_service_change` | 65 passed |
| M5 | the forcing reasons are the original's | `DUPLICATE_SHEET` removed from the set | `test_the_forcing_reasons_are_the_originals_and_two_of_this_product` | 48 passed |
| M6 | a medium link (`MATCH_LOW_CONFIDENCE`) gives `needs_review` even for pages of the same content | `identical_outcome`: `decide(channels, [])` | `test_an_identical_outcome_with_a_medium_link_is_needs_review_and_with_an_annotation_change_is_different` | 17 passed |
| M3a–f | ADR 15: the content key | `key.py`: page B dropped (a), the project (b), `ALGO_VERSION` (c), the link reasons (d), the annotation hashes (e), the Merkle (f) | `test_a_changed_byte_of_either_page_changes_the_key`, `test_another_project_does_not_share_the_key`, `test_a_change_of_the_algorithm_version_changes_the_key`, `test_the_link_reasons_and_the_split_part_are_in_the_key_...`, `test_an_annotation_only_change_changes_the_key_...`, `test_a_changed_byte_of_either_page_changes_the_key` | 17 passed each |
| I6 | a pair found by its key is not computed again | `service.py`: the lookup `if existing is not None:` → `if False:` | `test_a_pair_is_compared_written_with_its_mask_and_found_again_without_a_second_computation` (the spy child is started) | 1 passed |
| I1 | blob before row: a blob that could not be written leaves no row | `service.py`: the failure of the publication swallowed (`mask_blob_id = None`) | `test_a_blob_that_could_not_be_written_leaves_no_row` (a row without its blob is written) | 1 passed |
| I3 | the lease is proved before the blob is published | `before_publish` not called | `test_a_stop_before_the_blob_is_published_publishes_nothing` | 1 passed |
| I2 | the row is written under the queue's fence (ADR 7) | `fence(session)` not called | `test_an_attempt_the_fence_refuses_writes_no_row` | 1 passed |
| I4 | two workers write one row | `repository.py`: `ON CONFLICT (project_uid, content_key) DO NOTHING` removed | `test_two_workers_computing_one_pair_write_one_row` | 1 passed |
| I5 | a result is reused within one project only; foreign pages are `not_found` | `service.py`: `if owned != set(present):` → `if False:` | `test_pages_that_are_not_the_projects_are_refused_before_any_work` | 1 passed |
| M7 | ADR 9: a canvas over 40 Mpx is refused, not rendered | `job.py`: the cap `40_000_000` → `4_000_000_000` | `test_a_page_whose_canvas_passes_the_cap_is_refused_by_the_child_before_it_renders_anything` | 4 passed |
| M8 | ADR 9: a `same` pair has no mask | `job._write_mask`: the `same` return removed | `test_a_same_pair_gets_no_mask_even_when_a_plane_has_pixels` | 4 passed |
| M9 | the order of the planes is `ComparisonLayer` | `noise` and `service_zones` swapped | `test_the_planes_of_the_blob_are_the_layers_of_the_contract_in_order` | 4 passed |
| C1–C4 | ADR 9: the decoder's bounded decompression and refusals | `mask_codec.py`: (C1) the bound `expected + 1` removed from `decompress` → red on the zlib bomb; (C2) the 40 Mpx cap check → `if False`; (C3) the magic check; (C4) the `unused_data` check | `test_a_blob_that_claims_a_small_grid_and_expands_to_hundreds_of_megabytes_is_not_inflated` (300 MiB of zeros in 300 KiB, allocation under 4 MiB), `..._over_forty_megapixels...`, `test_a_wrong_magic_is_refused`, `test_bytes_after_the_end_of_the_stream_are_refused` | 39 passed each |
| M10 | the glyph search keeps the answers of the original's loop after its pruning | the pruning window `9 mm` → `1 mm` | `test_three_glyphs_of_one_height_in_a_row_are_an_inscription` (and the 60 random pictures against the original loop) | 16 passed |
| M11 | the shift from the vector lines needs a peak that stands out | `LINES_PEAK_RATIO` 2.0 → 0.0 | `test_a_hatch_is_given_up_not_voted_on` | 11 passed |
| M12 | the identity is kept when it agrees as well as the phase estimate | the preference removed | `test_the_phase_estimate_of_identical_masks_is_replaced_by_the_identity` | 11 passed |
| M13 | `WORD_MOVE_PT` = 20 pt | 20.0 → 200.0 | `test_a_word_more_than_twenty_points_away_is_removed_and_added` | 21 passed |
| M14 | the dedupe key is a function of the two pages | page B dropped from the key | `test_the_dedupe_key_is_a_function_of_the_two_pages_only` | 15 passed |
| M15 | a band's margin is enough for every filter | the margin of `bands()` → 0 | `test_a_band_with_its_margin_gives_the_core_rows_of_the_whole_canvas[41]` | 14 passed |

**Not shown red, with the reason.** (a) *A word moves at most once* (`blocks.confirm`, `claimed_a`): removing the guard changes nothing the tests can see, because the pixels a first block explained are gone from `a_only` when a second candidate that shares its words is tried (its share is then 0); the guard matters only for a second candidate that shares words and still has unexplained pixels, which no test builds. (b) *The lease fence against a lease lost between the last checkpoint and the insert* is shown by `fence` (I2) with a fence that refuses; the race itself is not run. (c) *ADR 10, 16, 18, 20*: the engine has no upload, no expert act, no image and no model; decisions 5 and 20 (spend, hidden change) do not touch a deterministic engine that writes immutable rows: the result is write-once (the table's frozen guard) and no AI layer exists here.

## 8. Commands and results

All from the lane worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src` and the lane's `.env` (PostgreSQL on 57850, MinIO on 61850) loaded for the container suites; `df -h /` before every container start and every long run.

| What | Command | Result |
| --- | --- | --- |
| whitespace | `git diff --check d11c13fd..HEAD` | exit 0, no output |
| engine unit tests | `pytest -q tests/unit/comparison/engine` | **255 passed** (the page and engine children are real; no container) |
| engine integration tests | `pytest -q tests/integration/comparison/engine` (own PostgreSQL 57850 and MinIO 61850, head `0039`) | **23 passed** |
| grant classification | `pytest -q tests/integration/recovery/test_grant_classification.py` | **35 passed** (`comparison_sheet_pair_result` is out of `SEALED_NOT_YET_WRITTEN`; the test is red until it is) |
| the three together, final code | one pytest run of the three paths above | **313 passed** in 367 s |
| the whole unit battery | `pytest -q tests/unit` | **4582 passed, 76 skipped**, 1 warning, 270 s (on the tree of the report draft `c9004e1a`; the 76 skips and the warning are not this lane's) |
| the contract battery | `pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py` | **1310 passed**, 19283 subtests passed, 144 s (same tree; it holds the boundary guard and the governance test of the task file) |
| the architecture boundary guard | `pytest -q tests/contract/architecture/test_alr05_boundaries.py` | red once on the first full run (`engine/validate.py` imported `api.schemas.models`, not a public module); fixed in `1a1224c9` by restating the models with a parity test; in the contract run above |
| mutation proofs | section 7 | every row red then green, tree clean |
| the real set | section 6 | 59 pairs, 33 children, none without a result |

Not run, by the brief and `R-135`: `make gate`, the web battery (no web change), the live journey. The three `D-220` files were left out of the contract run as the brief says.

## 9. Limits, risks, what the engine does not do

1. **No stream-level separation of overlays** (section 4.2 item 3). A release mark is compared as a zone; a warning set into the page content makes the pair `PARTIAL_COVERAGE` and `needs_review` even if nothing else differs; the drawing under a release mark is not compared. A release mark stamped as the last content stream of both versions is compared as a zone in both, so the common case costs nothing; a warning is the case that costs a review.
2. **The profile is the engine's only view of text and lines.** The profile keeps `pdfplumber` words (no direction of a line: a turned inscription is recognised by the shape of its box), `lines` (not rectangles and curves, so a frame drawn as a rectangle is not found and the margin zones are then absent), the annotation's kind, rectangle, text and hash (not its subject and author, nor the `AutoCAD SHX Text` role of the original: hidden SHX text is not read), the stamp's five fields and a 205 x 70 mm zone. The title-block zone is rebuilt as the original does from the row of signature labels, else from the frame, else (only if the profile read a field) the profile's own zone, which is wider than a real stamp.
3. **Annotations of a turned page** are compared by kind and text only (the profile keeps the PDF's own rectangle, not the page's offset and rotation).
4. **The content Merkle of the profile does not cover the catalogue's optional-content configuration** (`/OCProperties`, the original's `pdfio.content_hash` does, `pdfio.py:211-236`). Two pages with the same content stream and resources but different default layer visibility have the same Merkle and take the fast path to `same`. The engine does not look at it; the profile lane owns the Merkle (section 11).
5. **The text channel reads the text layer only** (no OCR): a page with no text layer, or one of the pair with none, is `NO_TEXT_LAYER`/`needs_review`, and the real set's large pages are of that kind.
6. **Time and memory are for the pages measured.** A page with several times the real set's 186 861 lines extracts to `RENDER_FAILED` in the profile, not here; the engine's own cost is the raster (bands) and the regions (a CPU budget of 120 s, after which the cheap classes stand and the pair is `PARTIAL_COVERAGE`). Pages with very many regions (a drawing that differs everywhere) hold the list of differences at 2000 (the true count is in the channels' `diffs`); shifts are listed after real differences.
7. **Registration is a similarity** (anchors) or a shift (lines, phase); a sheet re-composed or re-scaled in parts is `ALIGNMENT_PARTIAL`/`ALIGNMENT_UNRELIABLE`, as in the original.
8. **`spec_positions`** is `checked` only when the main channels are clean and `unchecked` otherwise, as the original's stage 1 (`engine.py:996-1000`); the real comparison of positions is `CMP-VC-SPEC-01`.
9. **The quality of the line-based shift on real sheets** is shown on the corpus' split sheet (171 false differences to 1) and not on the real set, whose pairs are partly by index; `CMP-MEASURE-01` compares the engine's statuses with the original's on that set.
10. **The lane's 120 MiB test** ends with `ImportError` or `MemoryError` depending on where the loader fails; both are ends without a result.
11. **Host load.** The tests and the measurement ran at load averages of 12 to 34 on 8 cores, so every wall time is an upper bound; the memory figures are not load-sensitive.

## 10. Notes for the next lanes

### CMP-SERIES-01
* **Entry points** (`auditmanager.comparison.public`): `compare_sheet_pair(session_factory, blob_store, *, project_uid, page_a_profile_id | None, page_b_profile_id | None, link_reasons=(), part=None, runner=None, child_limits=, work_dir=, before_publish=, fence=) -> PairOutcome(status, result_id, created, cached, reasons, mask_blob_id, child_end)`; a missing side gives `added`/`removed` and **no row** (the table holds only `same`, `same_zones_changed`, `different`, `needs_review`, and its `ck_..._result_when_compared` agrees). `enqueue_pair_result(session, *, project_uid, page_a_profile_id, page_b_profile_id, created_by_user_uid, reasons=(), part=None, comparison_upload_id=None)` and the handler of kind `pair_result` (payload `{"page_a", "page_b", "reasons", "part"}`). The dedupe key `pair_result:<page_a>:<page_b>` ignores the reasons and the part (the brief fixes it to the two identities): do not enqueue one pair twice with different reasons while the first is live. A series id on the item is one keyword for `enqueue.py` (this lane's file) and the column `comparison_work.comparison_series_id` that `comparison/work/**` does not use yet.
* **`link_reasons`** are the original's: `MATCH_LOW_CONFIDENCE` (medium or bridged links), `DUPLICATE_SHEET`, `TABLE_GROUP`, `AI_MATCH`, `CHAIN_ONLY`; the first two (and the originals' other forcing reasons) force `needs_review`, the rest are recorded. `part` is `"split"` (the sheet of A was cut into parts; only the area B occupies is compared) or `"floors"`. `SPLIT_SHEET` is not a reason of the engine: the sheets' `needs_review` for a split sheet is the series' verdict from the coverage of all the parts (`jobs.py:875-950`); the result of a split pair carries `part.area_a_pt`, `part.coverage_a` (the share of A's ink in the area) and `part.reliable`.
* **What a result holds**: the columns `status`, `reasons` (including `UNCHECKED_CHANNEL:<name>`), `channels` (state, diffs, reason: the contract's `ComparisonChannel`), and `result` (`format` 1, `canvas`, `differences`, `text_changes`, `service_notes`, `how_compared`, `aligned_blocks`, `mask`, and `part` when asked). `how_compared.transform` is `[a, b, c, d, e, f]` in the order of the PDF (`x' = a x + c y + e`, `y' = b x + d y + f`), B onto A, in points of the displayed page.
* **A pair is one item**; the series asks for each pair of the matrix and decides `added`/`removed`/`unmatched` itself. The permit reconciliation reads `service_notes`/`differences` and the sheet's stamp fields; the engine does not read the permit table.

### CMP-VIEWER-01
* Replace the reader by `decode_mask` (`DecodedMask.packed` is `(8, height, ceil(width / 8))`, `plane("main")` etc. unpack one plane; `encode_packed_planes` takes a sequence of eight planes). The decoder refuses the cases of the brief; its tests build blobs from the brief's own recipe.
* **Plane semantics**: `main` is the pixels only in A or only in B (the engine does not keep which; draw A and B tiles under it); `light_elements` the light fills and hatches that differ; `color_change` where a common line changed colour; `line_style` the same line drawn otherwise; `moved` the pixels a moved block or a moved inscription explains (not a change); `within_tolerance` and `noise` what was set aside; `service_zones` the rectangles of the title block, release mark and margins of A and of B carried onto A. The grid is the canvas of A at `how_compared.dpi` (A's registration dpi, at most 200), pixel `(x, y)` = points `(x, y) * 72 / dpi`.
* A `same` pair has no mask. A pair that differs only in annotations or in service fields can have `mask: null` (no pixel differs and no zone exists): the viewer lists the notes.
* `aligned_blocks[i]` = `{"box_a": [x0, y0, x1, y1], "dx_pt", "dy_pt"}`: `box_a` is the block's place **after the transform** (where B draws it on A's canvas); the block in A is `box_a` moved by `(-dx_pt, -dy_pt)`; draw B's part inside `box_a` moved by `(-dx_pt, -dy_pt)`.
* The region class of a difference and its layer: `text`, `graphic_added`, `graphic_removed`, `graphic_changed` on `main`; `light_fill` on `light_elements`; `color_change`; `line_style`; `text_moved`, `block_moved`, `shifted` on `moved` (hidden by default: «сдвиги (не изменение)»). Text-change kinds: `changed`, `added`, `removed`, `moved`, with `_spaces`, `_symbol`, `_number_format` appended when the change is a normalisation.

### CMP-MEASURE-01
* `tools/measure/comparison_engine.py` is the tool; the records of this run (numbers and states only) are in the lane's scratch and not committed. The statuses of section 6 are those of a load run with pairs by index; compare per sheet against the original's `result_status` with the matrix's pairs. The tool reports the child's own `VmHWM` and `VmPeak`; `ru_maxrss` is not the child's peak (section 6).
* The first measurement of this lane (727 MiB of address space on the worst pair) is the reason the three removals of section 6 exist; a change of the engine that adds a large array should read `facts.peaks_mib` (the child writes `VmPeak` after each stage).

## 11. Items for the FIX slot of the wave

1. **`result.part`** (section 4.2 item 9) is not in the brief's section 4 item 3. Confirm it (the series needs it) or tell the lane to drop it.
2. **The Merkle of the profile lacks `/OCProperties`** (section 9 item 4): `CMP-PROFILE-01` owns `page_merkle.py`; a change is a new `ALGO_VERSION` of the profile.
3. **Disagreements between the answer keys and the original's rules** (section 5): V2→V3 E04 (`color` against `geometry`), V4→V5 E03 (`warnings`), V4→V5 E05 (the split's status), V4→V5 E07 (`spec_positions`), V1→V2 E02 (`text_moved` against removed + added). The keys belong to `CMP-FIXTURES-01`; the engine follows the original.
4. **The profile's `lines`** are `pdfplumber` lines only (no rectangles, no curves): frames drawn as rectangles are not found, and the line-based registration has fewer lines to vote on. Adding `rects` to the profile (a new `ALGO_VERSION`) would improve both.
5. **Stream-level overlay separation** needs a decision on a PDF editor (`OD-01` excludes `PyMuPDF`); until then a warning in the content is `PARTIAL_COVERAGE`.
6. **`comparison_series_id` on the `pair_result` item** (section 10).
7. **The shared `.venv` and the baseline**: with the default thread pools `import numpy, cv2` reserves 1.5 GiB of address space, more than the ceiling; the child shuts them in `program.py`. Any other child that imports `cv2` under `RLIMIT_AS` must do the same.

## 12. Resources and hotspots

Containers `auditmanager-cmp-engine-01-{postgres,s3,s3-init}-1` on ports 57850 / 61850 / 61851, `make up` and `make migrate` from the lane worktree (head `0039`); `df -h /` was read before every container start and every long run (1.8 to 2.5 GiB free; the stop line is 1.5 GiB). At the end: `make down` removed the three containers and the network; the two volumes `auditmanager-cmp-engine-01-postgres-data` and `auditmanager-cmp-engine-01-s3-data` were removed **by those exact names**; `docker ps -a`, `docker volume ls` and `docker network ls` list nothing of the lane; the lane's git-ignored `.env` and the measurement's scratch directories (profiles, the realistic A1 PDFs) were deleted. Nothing of the real set was written anywhere but the numbers of section 6.
`git diff --name-only d11c13fd..HEAD` lists the files of section 3 and no other: nothing under `contracts/`, `db/`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `src/auditmanager/bootstrap/`, `src/auditmanager/api/`, `src/auditmanager/comparison/{work,profile,profile_queue}/`, `workers/`, `jobs/`, `storage/`, `ingest/`, `executors/`, `web/`, `infra/`. No process was killed by a pattern; the only signals sent are the runner's `SIGKILL` of its own child by PID at the wall clock (the tests of the ceilings).
