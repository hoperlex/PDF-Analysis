# W55B-GEOMETRY-01 — report (portal blocks and crops)

- Task: `dispatch/W55-PLAN.md` §B3.7, §B3.3 (the PDF opened from a temporary file), §B4 Stage B 4 `W55B-GEOMETRY-01`, §B5;
  `P02_SEAMS.md` §4.5, §4.8, §4.9, §4.10 (sealed, read only); `W55B-FREEZE-01.md` (crop budget, page-box tolerance).
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `887a8254` (the RECOGNISED report; below it BUDGET, INGEST,
  STREAM, FIXTURES, SEAL).
- Written by one writer (a Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- **The lane is complete.** A portal-bundle version now gets «Блоки»: `page_geometry_extraction` normalises the bundle's
  `_blocks.json` into `geometry.portal_blocks`, checks every page's box against the PDF, clip-renders a crop for each IMAGE
  block on a page that passed, publishes the PNGs as `geometry.crop_image` blobs and the manifest `geometry.page_crops` under
  `crop_policy: portal_image_blocks`; `BlockAdapter` serves `listVersionPortalBlocks` and `streamVersionPortalBlockCrop`. A
  version without a bundle publishes exactly what it did before (`crop_policy: none`, `crops: []`, no new artifact).
- Lane stack: `FOUNDATION_INSTANCE=auditmanager-w55b-geometry`, PostgreSQL `57460`, S3 `61060/61061`; torn down at the end
  (section 5).

## 1. Changed files

`git diff --name-status 887a8254..HEAD`:

```text
A docs/program/W55B-GEOMETRY-01.md                                   this report
M src/auditmanager/analysis/README.md                                OD-04 flipped; has_text_layer lines corrected; the portal artifacts
A src/auditmanager/analysis/geometry/__init__.py                     the package's surface
A src/auditmanager/analysis/geometry/maths.py                        pure: the page box, the page-box check, the crop plan
A src/auditmanager/analysis/geometry/portal.py                       pure: the block list normalised and ordered
A src/auditmanager/analysis/geometry/render.py                       the only PDFium caller, under PDFIUM_LOCK
A src/auditmanager/analysis/geometry/crops.py                        PNG encoding, content-addressed publication, manifest records
A src/auditmanager/analysis/geometry/source_file.py                  the source PDF in a temporary file
M src/auditmanager/analysis/ports/artifacts.py                       two role constants (and their __all__ names)
M src/auditmanager/analysis/public.py                                one export line (the two roles) and two __all__ names
M src/auditmanager/analysis/stages/page_geometry_extraction.py       temporary file; the bundle path; metrics
M src/auditmanager/bootstrap/adapters.py                             BlockAdapter only: the two portal reads
M src/auditmanager/ingest/public.py                                  OUTSIDE THE GRANT, pre-authorised: one line re-exporting PDFIUM_LOCK
M src/auditmanager/runs/executor.py                                  OUTSIDE THE GRANT, pre-authorised: the block list reaches the geometry stage
A tests/integration/analysis/geometry/geometry_support.py           helpers (not a test module): PDF writer, oracle, bundles, validators
A tests/integration/analysis/geometry/reads_support.py              helpers (not a test module): the runs harness, a bundle version, a run
A tests/integration/analysis/geometry/test_geometry_maths.py        73 tests
A tests/integration/analysis/geometry/test_portal_layout.py         37 tests
A tests/integration/analysis/geometry/test_clip_render.py           20 tests
A tests/integration/analysis/geometry/test_geometry_stage.py        18 tests (S3)
A tests/integration/analysis/geometry/test_portal_block_reads.py    12 tests (PostgreSQL and S3)
A tests/integration/analysis/geometry/test_portal_block_integrity.py 5 tests (PostgreSQL and S3)
M tests/integration/api/test_portal_block_routes.py                  OUTSIDE THE GRANT, forced: the stub assertion became "serves"
M tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py   SEALED_STUB_ADDRESSED emptied
M tests/integration/composition/test_router_answers.py              SEALED_STUB_GETS emptied
M tests/integration/composition/test_version_blocks_wire_shape.py   the portal reads at the wire (5 tests, 2 new)
```

No `conftest.py`, fixture, tool, contract, migration or lock file was added or changed. `api/routers/blocks.py` was not touched:
its bodies were already real (only the adapter was stubbed). `tests/integration/runs/test_w45_blocks_version_block_index.py`
needed no change: `getVersionBlocks` is unchanged.

## 2. Checks, and how each new test was shown to fail

Light acceptance (`R-102`), on the lane stack, one invocation at a time, `set -a; . ./.env; set +a` before
`.venv/bin/python -m pytest -p no:cacheprovider -q <target>`; exit codes read directly (`> log 2>&1; rc=$?`), never behind a pipe.
Host when the stack came up: 9.5 GiB available, 17 GiB free on `/`. Code tip of the acceptance run: `e1d309ac` (later commits
change this report only).

| Check | Exit | Result |
| --- | --- | --- |
| `make up`, `make migrate`, `make check-db` | 0, 0, 0 | head `0021_portal_bundles` |
| `git diff --check 887a8254..HEAD` | 0 | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/{analysis,bootstrap,ingest,runs} tests/integration/{analysis,api,composition}` | 0 | |
| `tests/contract` without `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py` (clean committed tree) | 0 | 752 passed, 18 927 subtests (`dc967c61`; repeated on the final tip, section 6) |
| `tests/integration/analysis` (with the new `geometry/`) | 0 | 576 passed (411 before the lane, 165 new) |
| `tests/integration/analysis_engine` | 0 | 47 passed |
| `tests/integration/analysis_text` | 0 | 223 passed |
| `tests/integration/p02_journey` | 0 | 59 passed |
| `tests/integration/runs` (database reused across the lane, no state-dependent failure) | 0 | 200 passed |
| `tests/integration/api` | 0 | 569 passed |
| `tests/characterization` | 0 | 61 passed |
| `tests/e2e` (no browser) | 0 | 163 passed, 5 skipped (the opt-in live-model cases) |
| `tests/integration/{exports,workers,jobs,execution,qa_w52,qa_w53}`, one invocation | 0 | 106 passed |
| beyond the brief, `ingest/public.py` changed: `tests/integration/ingest` | 0 | 593 passed |
| `tests/unit` | 0 | 1 passed |
| `tests/integration/composition` (last) | 0 | 752 passed, 2 skipped (the opt-in proxy stand and the stand-copy window, off by design) |
| the produced manifests (baseline bundle, four rotations, a bare version) against `crop-manifest.schema.json` with `jsonschema` 4.26 `Draft202012Validator` in the governance interpreter `.venv/bootstrap/bin/python` (scratch, not committed) | 0 | 0 errors each; two damaged copies each 1 error |
| a full `make gate` | -- | **not run** (light acceptance, `R-102`; one full gate runs on the final W55b candidate) |
| web lint, typecheck, Vitest | -- | not run: this lane changes no file under `web/` |

`am-geometry-*` and `am-source-*` in the temporary directory: 0 before the lane, 0 after; the 7 files the "temporary file
removed" mutation left (that mutation disables the removal) were deleted by name.

### 2.1 Mutation proofs

Method: a scratch driver (session scratchpad, not committed) makes one textual replacement in the **committed** file (the old
text must occur exactly once; every replacement changes one line, except the lock-release row, which inserts one), runs the named
test files with `pytest -x -q --tb=no -rf` on the lane stack (one invocation at a time), writes the original bytes back and
compares the file's SHA-256. **40 mutations, 40 red, every file restored.** A second pass ran 16 of them against the specific test
written for that behaviour (when the first failing test was a broader one): **16 red** ("also" below). In that pass the looser
tolerance first stayed green at the stage level (its mismatch page was 1 % off, so a doubled tolerance still refused it): the
stage case was moved to 0.6 % (`e1d309ac`) and the row then ran red. Test paths are relative to
`tests/integration/analysis/geometry/`.

| Behaviour (mutation) | File | First failing test |
| --- | --- | --- |
| rotation 90 swaps the sides | `geometry/maths.py` | `test_clip_render.py::test_the_displayed_page_is_the_oracles_and_pdfiums_own[rotate-90]`; also `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-90]` |
| rotation 270 swaps the sides | `geometry/maths.py` | `test_clip_render.py::test_the_displayed_page_is_the_oracles_and_pdfiums_own[rotate-270]`; also `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-270]` |
| rotation 180 keeps the sides | `geometry/maths.py` | `test_clip_render.py::test_the_displayed_page_is_the_oracles_and_pdfiums_own[rotate-180]`; also `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-180]` |
| rotation 0 keeps the sides | `geometry/maths.py` | `test_clip_render.py::test_the_displayed_page_is_the_oracles_and_pdfiums_own[rotate-0]`; also `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-0]` |
| the CropBox, clipped to the MediaBox | `geometry/maths.py` | `test_clip_render.py::test_the_displayed_page_is_the_oracles_and_pdfiums_own[rotate-90-cropbox]` |
| the tolerance, looser | `geometry/maths.py` | `test_geometry_maths.py::test_the_aspect_tolerance_holds_on_both_sides_of_half_a_percent[1.00501-geometry_mismatch]`; also `test_geometry_stage.py::test_a_page_whose_box_disagrees_cuts_no_crop_and_the_stage_still_succeeds` |
| the tolerance, stricter | `geometry/maths.py` | `test_geometry_maths.py::test_the_aspect_tolerance_holds_on_both_sides_of_half_a_percent[1.0049-ok]`; also `test_geometry_stage.py::test_a_page_whose_box_disagrees_cuts_no_crop_and_the_stage_still_succeeds` |
| the deviation in both directions | `geometry/maths.py` | `test_geometry_maths.py::test_the_aspect_tolerance_holds_on_both_sides_of_half_a_percent[0.9950149749753734-geometry_mismatch]` |
| the portal's rotation must be the PDF's | `geometry/maths.py` | `test_geometry_maths.py::test_a_portal_rotation_other_than_the_pdfs_is_a_mismatch_even_on_a_square_page[0-90]`; also `test_geometry_stage.py::test_a_page_whose_box_disagrees_cuts_no_crop_and_the_stage_still_succeeds` |
| the 800 px floor | `geometry/maths.py` | `test_clip_render.py::test_the_decoded_png_meets_the_budget[box0-1.0-floor]` |
| the 4 000 000 pixel cap | `geometry/maths.py` | `test_geometry_maths.py::test_a_large_block_at_a_dense_raster_is_lowered_to_the_pixel_cap`; also `test_clip_render.py::test_the_decoded_png_meets_the_budget[box1-8.333333333333334-cap]` |
| a degenerate box is refused | `geometry/maths.py` | `test_geometry_maths.py::test_a_degenerate_box_is_refused[box5]` |
| no crop on a mismatch page | `geometry/portal.py` | `test_geometry_stage.py::test_a_page_whose_box_disagrees_cuts_no_crop_and_the_stage_still_succeeds` |
| a block repeats its page's verdict | `geometry/portal.py` | `test_portal_layout.py::test_every_block_repeats_its_pages_verdict_and_only_ok_image_blocks_are_cut` |
| page_number = page_index + 1 | `geometry/portal.py` | `test_portal_layout.py::test_the_strict_validator_refuses_damaged_copies`; also `test_portal_layout.py::test_the_baseline_normalises_to_section_4_9` |
| blocks_sha256 of the stored bytes | `geometry/portal.py` | `test_portal_layout.py::test_the_baseline_normalises_to_section_4_9` |
| crop_url never copied | `geometry/portal.py` | `test_portal_layout.py::test_the_strict_validator_refuses_damaged_copies`; also `test_portal_layout.py::test_crop_url_and_the_portals_document_fields_reach_no_artifact` |
| polygon_points omitted for a rectangle | `geometry/portal.py` | `test_portal_layout.py::test_the_strict_validator_refuses_damaged_copies`; also `test_portal_layout.py::test_a_rectangles_null_or_empty_polygon_never_reaches_the_artifact[None]` |
| the order: page, ordinal, id | `geometry/portal.py` | `test_portal_layout.py::test_blocks_are_ordered_by_page_then_ordinal_with_null_last_then_id` |
| the order: a null ordinal last | `geometry/portal.py` | `test_portal_layout.py::test_the_strict_validator_refuses_damaged_copies`; also `test_portal_layout.py::test_blocks_are_ordered_by_page_then_ordinal_with_null_last_then_id` |
| the clip: a bitmap of the crop's size | `geometry/render.py` | `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-0]`; also `test_clip_render.py::test_the_bitmap_is_the_clip_and_never_the_page` |
| the clip: positioned at its origin | `geometry/render.py` | `test_clip_render.py::test_each_rotation_cuts_the_rectangle_the_oracle_displays[rotate-0]`; also `test_clip_render.py::test_the_clip_equals_the_same_region_of_a_whole_page_render` |
| the lock held while rendering | `geometry/render.py` | `test_clip_render.py::test_the_lock_is_held_during_every_render_and_another_thread_takes_it_between_crops` |
| the lock released between crops | `geometry/render.py` | `test_clip_render.py::test_the_lock_is_held_during_every_render_and_another_thread_takes_it_between_crops` |
| equal crops published once | `geometry/crops.py` | `test_geometry_stage.py::test_equal_crops_are_one_blob_published_once` |
| the policy value | `stages/page_geometry_extraction.py` | `test_geometry_stage.py::test_a_bundle_publishes_portal_blocks_the_manifest_and_one_blob_per_crop` |
| a version without a bundle unchanged | `stages/page_geometry_extraction.py` | `test_geometry_stage.py::test_a_version_without_a_bundle_publishes_exactly_what_it_did_before` |
| the extractor gets a path | `stages/page_geometry_extraction.py` | `test_geometry_stage.py::test_the_pdf_is_opened_from_one_temporary_file_that_is_gone_afterwards` |
| the temporary file removed | `geometry/source_file.py` | `test_geometry_stage.py::test_the_pdf_is_opened_from_one_temporary_file_that_is_gone_afterwards` |
| the PDF streamed, never read whole | `geometry/source_file.py` | `test_geometry_stage.py::test_the_source_document_is_never_read_whole` |
| crop blobs in the stage result (bound) | `stages/page_geometry_extraction.py` | `test_portal_block_reads.py::test_the_executor_hands_the_block_list_to_the_geometry_stage_and_binds_every_crop` |
| executor: the block list to geometry | `runs/executor.py` | `test_portal_block_reads.py::test_not_produced_before_a_run_and_produced_by_that_run_after`; also `test_portal_block_reads.py::test_the_executor_hands_the_block_list_to_the_geometry_stage_and_binds_every_crop` |
| adapter: the join | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_the_join_puts_each_artifact_on_its_block` |
| adapter: an empty recognised text left out | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_an_empty_body_is_left_out_never_sent_empty` |
| adapter: an empty description left out | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_an_empty_body_is_left_out_never_sent_empty` |
| adapter: an unknown version is 404 | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_an_unknown_version_is_not_found_for_both_reads` |
| adapter: a block without a crop is 404 | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_a_block_without_a_crop_is_not_found[blk_285e293c6614ba032cb547f00c83b5f6]` |
| adapter: not_produced before a run | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_not_produced_before_a_run_and_produced_by_that_run_after` |
| adapter: only a run with portal_blocks | `bootstrap/adapters.py` | `test_portal_block_reads.py::test_a_version_without_a_bundle_produces_no_portal_geometry` |
| adapter: the digest is the record's | `bootstrap/adapters.py` | `test_portal_block_integrity.py::test_a_crop_blob_that_is_missing_or_not_the_recorded_one_is_an_integrity_error[missing]`; also `test_portal_block_integrity.py::test_a_crop_blob_that_is_missing_or_not_the_recorded_one_is_an_integrity_error[other bytes]` |

Mutations, one line each: the rotation set `frozenset({90, 270})` became `{270}`, `{90}`, `{90, 180, 270}`, `{0, 90, 270}`;
`box = effective_box(...)` became `box = mediabox`; the tolerance comparison `> PAGE_BOX_TOLERANCE` became `* 2` and `/ 2`;
`max(ratio, 1/ratio) - 1` became `ratio - 1`; the rotation comparison became `if False:`; the floor became `max(scale, 0.0)`;
the cap became `min(scale, 1e9)`; the degenerate `raise` became `pass`; the mismatch filter lost `and verdict == ok`; the block
verdict became `GEOMETRY_OK`; `page_index + 1` became `page_index`; the digest of `b""`; a `"crop_url": None` member; the
polygon `del` became `pass`; the sort dropped; `ordinal is None` became `False`; the bitmap allocated at the canvas size; the
clip origin `-plan.left` became `0`; `with pdfium_lock()` became `with threading.Lock()`; a `pdfium_lock().acquire()` before
the render section (the worker thread deadlocks, the probe test fails at its 60 s join); `if known is not None` became
`if False`; the portal policy became `"none"`; the bare manifest's policy became the portal one; `extract_document(path)`
became the file's bytes; the unlink became `pass`; the stream became a whole `read`; the crop images left out of the stage
result; the executor tuple reverted; `entry = None`; each `if entry["text"]:` became `if True:`; the version check became
`pass`; `if record is None` became `if False`; `not_produced` became `produced`; `if portal_blocks is None` became `if False`;
the declared digest became the object's own (`inspect`).

### 2.2 The edits outside the grant, and their evidence

- **`runs/executor.py`** (pre-authorised): `ROLE_SOURCE_STRUCTURED_COMPANION` added to `page_geometry_extraction`'s role tuple
  (RECOGNISED already seeds the manifest's member into `outputs.refs`). Without it no real run publishes portal geometry; the
  mutation row "executor: the block list to geometry" turns the DB-backed tests red.
- **`ingest/public.py`** (pre-authorised): one line, `from auditmanager.ingest.envelope import PDFIUM_LOCK as PDFIUM_LOCK`.
  The redundant alias is the re-export idiom; the line is not added to `__all__` (the grant was one line). ALR-05
  (`tests/contract/architecture/test_alr05_boundaries.py`) allows `analysis -> ingest.public`; it passes.
- **`tests/integration/api/test_portal_block_routes.py`** (pre-authorised, forced): its last case asserted the sealed
  `503 dependency_unavailable`, the behaviour this lane removes. It now asserts the shipped adapter reaches for the version
  (a session factory that records the call) and that the stub method is gone; the unused error imports went with it.

### 2.3 What the new tests assert

- `test_geometry_maths.py`: the displayed size for 0/90/180/270 on four page shapes against the oracle; a CropBox inside and
  outside the MediaBox; rotation normalisation; agreeing rotation and aspect is `ok`; every portal/PDF rotation pair on a square
  page; the tolerance at 1.0, 1.0006, 1.0049, 1.00499 (ok) and 1.00501, 1.0051, 1.01 (mismatch), both directions; degenerate
  pages and rasters; the base kept, the floor reached and not passed, the cap reached to within 0.5 %; the recorded scale is the
  rendered one; the clip is not the page; both bounds and coverage over 10 000 random blocks and pages; the corner rule (cap
  wins) under a lowered cap; eight degenerate boxes refused; the degenerate bound on both sides; one portal pixel still cut.
- `test_portal_layout.py`: the strict validator refuses twelve damaged copies; the baseline normalises to section 4.9
  (`page_number`, label, ordinal, type, status, box, id verbatim, `blocks_sha256` of the stored bytes); no `crop_url`,
  `document_*`, `shape_type`, `export_status`, `coords_norm`, `page_index` or URL in the artifact; `polygon_points` kept (3 and
  64 vertices) or absent (`null`, `[]`, missing), never `null` or `[]`; seven bad polygons refused; the order (page, ordinal,
  null last, id) on a reversed, extended list; per-block verdicts and the crop selection; eighteen refusals as
  `portal_blocks_invalid`; RECOGNISED's reader runs first (`portal_blocks_page_mismatch` passes through).
- `test_clip_render.py`: the lock is ingest's; the renderer name is the installed version; PDFium's page size equals the
  oracle's for the five pages; for each rotation (and a CropBox) the red rectangle lands where the oracle displays it, to a pixel,
  with a white border; an unrotated reading of a rotated page holds no red; one bitmap of the clip's size and the canvas
  offset passed to PDFium; the clip equals the same region of a whole-page render, pixel for pixel; the decoded PNG at the floor
  and at the cap; two renders give the same bytes and no metadata chunk; the lock is held in every render and another thread
  takes it between two crops; PDFium opens the path it is given.
- `test_geometry_stage.py` (S3): the baseline bundle's artifacts (roles, order, one blob per crop), exact metrics, section 4.9 by
  the validator; the manifest by the contract schema, each record against its blob (digest, size, decoded pixels, profile,
  scale `round(2480 / 595.28, 6)`); no `crop_url` or URL in any JSON artifact; same input, same JSON bytes and same crops; the
  manifest validator refuses eleven damaged manifests; a bare version publishes exactly the two old artifacts, the old four
  metric names, the canonical `none` manifest and the same block index bytes as the bundle; four rotations cut red-centred,
  white-cornered crops; a page 0.6 % off and a page whose portal rotation disagrees are `geometry_mismatch` with no crop while
  a page 0.4 % off passes and the stage succeeds; three equal crops are one blob published once; the extractor and PDFium get the
  same `am-geometry-*` file holding the PDF's exact bytes, gone after success and after a failure in the extraction or the
  render; the source blob is never read whole; every stage render holds the lock; an unreadable block list
  (`portal_input_unreadable`), a broken stream (`source_unreadable`), an unusable block list (`portal_blocks_invalid`) and a
  degenerate IMAGE block (`portal_block_degenerate`) are refused, with no file left.
- `test_portal_block_reads.py` (PostgreSQL and S3; `execute_run`, recorded, offline): `not_produced` before a run, `produced`
  by that run after; the join (TEXT: recognised text and flags; IMAGE: description and the manifest's crop; stamp: neither;
  polygon kept, rectangle without); the port's order; an empty TEXT and an empty IMAGE body left out (the crop stays); an
  unknown version `not_found` for both reads; the crop's bytes hash to the listed digest; a text block, a stamp, an unknown id and
  a version before any run `not_found`; the run's geometry stage carries the portal artifact and two crop blobs, and every blob
  it published is `bound`; a bare version publishes no portal geometry and answers `not_produced` while `getVersionBlocks`
  answers `produced`.
- `test_portal_block_integrity.py`: a crop blob missing or replaced, and each of the three joined artifacts missing or replaced,
  is `storage_integrity_error`. A module of its own because the store's refusal closes its connection and the runs harness's
  socket guard forbids the reconnect (its docstring says so); nothing in it can reach a model.
- `test_version_blocks_wire_shape.py`: over HTTP, an uploaded bundle answers `not_produced` and a crop `404` before a run, an
  unknown version `404` for both reads, and after a published run 12 items with the recognised text marked `recognised`, the
  descriptions, one polygon, two crops, no URL, and a crop whose bytes hash to the listed digest with the wire headers.

## 3. Contracts

- **Unchanged:** `contracts/**` (the stage registry already declared the optional input and both optional outputs; stage and
  artifact versions stay `1.0.0`), the OpenAPI document and the generated client (47 paths / 54 operations / 123 schemas), the
  error catalog (24 codes), the migration head `0021_portal_bundles`, `pyproject.toml`, `uv.lock`, `P02_SEAMS.md`.
- **Error codes used, none added:** `analysis_input_invalid` with `stage_id` and `reason` `portal_input_unreadable`,
  `portal_blocks_invalid`, `portal_blocks_page_mismatch` (RECOGNISED's reader), `portal_block_degenerate` (new reason),
  `page_count_disagreement` or `source_unreadable`; `not_found` (`aggregate_type: PortalBlock` for a crop that does not exist;
  `DocumentVersion` for an unknown version, as before); `storage_integrity_error` (`role`, and `blob_id`, `expected_sha256` for
  a missing blob); `unsupported_contract_version` for an unknown artifact version; other storage failures through
  `ingest.domain_error_from_storage`, as the content reads do.
- **Locks:** `PDFIUM_LOCK` (ingest's `threading.Lock`, the one PDFium lock of the process) is shared through
  `auditmanager.ingest.public` and taken per PDFium operation (open, one page's boxes, one crop, close). Where stages run: with
  `EXECUTION_ROLE=all` the run carrier is a thread of the serving process (`runs/carrier.py`), beside the upload route's
  `inspect_pdf`; on the stand the worker process runs stages and the API runs ingest, so there the lock guards the worker's own
  threads. The lock is process-local by nature.
- **Artifacts** (`P02_SEAMS` sections 4.5, 4.9, 4.10): `geometry.portal_blocks` -- root `artifact_role`, `artifact_version`,
  `version_uid`, `blocks_sha256` (SHA-256 of the stored `_blocks.json`), `pages[]` (`page_number`, `width_px`, `height_px`,
  `rotation_deg`, `geometry`) and `blocks[]` (`portal_block_id`, `page_number`, `page_label`, `ordinal`, `block_type`,
  `status`, `bbox_norm`, `polygon_points` only when non-empty, and `geometry`, its page's verdict -- the brief's addition, which
  section 4.9's example does not show; the wire carries it per block). `geometry.page_crops` -- `crop_policy`
  `portal_image_blocks` and one record per crop (`portal_block_id`, `page_number`, `bbox_norm`, `render_profile`, `blob_id`,
  `sha256`, `size_bytes`, `width_px`, `height_px`). `geometry.crop_image` -- `image/png` blobs, each distinct PNG once in the
  stage result.
- **Roles on the Python surface:** `ROLE_PORTAL_BLOCKS` (`geometry.portal_blocks`) and `ROLE_CROP_IMAGE`
  (`geometry.crop_image`) in `analysis.ports.artifacts` and `analysis.public`; the package `auditmanager.analysis.geometry`;
  `page_geometry_extraction.CROP_POLICY_PORTAL`, `REASON_PORTAL_UNREADABLE`, `REASON_BLOCK_DEGENERATE`.
- **Metrics** (a bundle only; none renamed; `crop_policy`, `crop_count`, `block_count`, `page_count` kept, `crop_count` = crops
  cut): `crop_blob_count`, `crop_skipped_for_mismatch_count`, `portal_block_count`, `portal_image_block_count`,
  `geometry_mismatch_page_count`.
- **The render profile and rules:** `renderer` `pypdfium2 <installed version>` (`pypdfium2 5.13.0`), `scale` (pixels per point,
  six decimals), `min_long_side_px` 800, `max_pixels` 4 000 000, `format` `png`. **Scale:** base = `width_px / width_pt` (the
  portal raster's density), raised to the 800 px floor, lowered to the 4 000 000 pixel cap, both bounds computed with the integer
  clip's worst rounding included (half a pixel of canvas rounding, a pixel at each outward edge). **Corner:** the bounds cannot
  conflict for a positive box; the cap wins if they ever did. **Rotation:** the box is the CropBox clipped to the MediaBox, after
  `/Rotate`; PDFium renders the displayed page, so 90 and 270 only exchange width and height; the PDF's `/Rotate` is trusted and
  the portal's `rotation` must equal it, else `geometry_mismatch`. **Tolerance:** `r = (width_px / height_px) / (width_pt /
  height_pt)`, pass iff `max(r, 1/r) - 1 <= 0.005`. **Degenerate:** a canvas side above 2**24 px is refused. Details and
  rejected alternatives: the appendix.

## 4. Risks and limitations

### 4.1 The owner's export (F-7: counts only)

**Method.** A scratch script in the session scratchpad (never committed), run once as `.venv/bin/python -I <scratchpad>/measure.py
<worktree> .local/portal-exports/<the owner's export>.zip <private temporary directory>`: the archive read in memory; the three
members published to an **in-memory** store (nothing in S3, nothing on disk); `source_preparation` then
`page_geometry_extraction` run through `run_stage`; the stage's temporary PDF placed in a private directory removed afterwards;
peak RSS reset with `/proc/self/clear_refs` (5) just before the geometry stage and read from `VmHWM` after. No crop was saved;
only the counts below left the process. **Read-only:** the export's SHA-256 prefix (`a56f0868...`) and modification time were
identical before the first read and after the last; nothing derived from it is in the repository.

| Measure | Value |
| --- | --- |
| pages; rotations | 30; all 0 |
| blocks | 129: 56 text, 47 image, 26 stamp; 12 polygons |
| crops cut; distinct blobs; mismatch pages | 47; 47; **0** |
| page aspect deviation (portal raster against the PDF page) | max 0.0124 %, median 0.0 % (tolerance 0.5 %) |
| crop width min / median / max | 1 177 / 2 307 / 4 206 px |
| crop height min / median / max | 593 / 1 426 / 2 642 px |
| crops at the 800 px floor; at the 4 000 000 pixel cap | 0; **23** (largest 3 995 776 pixels) |
| scale min / max | 2.215091 / 4.166667 px per point |
| PNG bytes, all crops | 25 004 608 |
| `page_geometry_extraction` wall time | 20.7 s (includes the stage's pdfplumber re-extraction; not split) |
| peak RSS growth during the stage | 189 916 kB over an RSS of 824 896 kB before it |

Nothing contradicted §B3.5 to §B3.7: no page needed the tolerance, no IMAGE block was degenerate. **What it does not cover:**
one document, one portal, one raster density (300 dpi A4-like pages and larger sheets); no rotated page, no failed block, no
low-text page; the time is one run on a quiet host; the split between the existing text re-extraction and the new crops was not
measured on this export.

### 4.2 Other risks

1. **The 500-page case is REHEARSAL's to measure.** The stage renders one crop at a time (one bitmap of at most 4 000 000
   pixels, about 12 MB, plus its PIL copy and PNG), publishes it and lets it go; but on the export half the crops hit the cap
   and the stage took 20.7 s for 30 pages. A 500-page low-text bundle with an IMAGE block per page could spend minutes and
   hundreds of megabytes of PNG per run (content-addressed, so a rerun in the same image stores nothing new). The page-box
   check also loads every page in PDFium once (`FPDF_LoadPage` parses the page's content), and each crop loads its page again.
2. **Crop bytes depend on the image** (PDFium build, Pillow, zlib). A rerun after an image change publishes new crop blobs; the
   reads use the latest run's manifest, so they stay consistent, and older runs keep their own bound blobs.
3. **A degenerate IMAGE block fails the run** (`portal_block_degenerate`): rare by construction (a long side under about a
   sixth of a 300 dpi pixel), but one such block refuses the whole bundle rather than leave it without the crop section 4.5
   promises.
4. **Rotated pages are untested on real data.** The portal's `rotation` field is assumed to be the PDF's `/Rotate` and its
   raster the displayed page; a portal that reports rotations differently would mark every rotated page `geometry_mismatch`
   (no crops, visible), not cut wrong ones.
5. **`listVersionPortalBlocks` for a version without a bundle stays `not_produced` after its runs** (decision 11): true by the
   sealed description ("no run of which has produced portal geometry"), but «Блоки» must not read it as "after the first run"
   for such a version. Only versions published before W55b are affected (ingest now refuses a bare PDF). See section 5.
6. **Stale prose outside the grant:** the module docstring of `src/auditmanager/api/schemas/blocks.py` (sealed by SEAL) still
   says `geometry.page_crops` is "unconditionally `crops: []`". It describes `getVersionBlocks`' view and is now wrong about the
   manifest; a one-sentence fix for the integrator or WEB-BLOCKS.
7. **The `PDFIUM_LOCK` re-export is not in `ingest.public.__all__`** (the grant was one line); an explicit import works, a star
   import would not carry it.
8. **`P02_SEAMS` section 4.9's example shows no per-block `geometry`**; the artifact carries it (the brief and the wire both
   want it per block). Additive; the seam is not edited.

## 5. Integrator instructions

1. Merge `agent/w55b` through this report's commit. No contract, migration, lock file or fixture is touched.
2. **Heavy steps owed: none of this lane's.** Light acceptance only (`R-102`); `bootstrap/adapters.py` is under the composition
   root, which `AGENTS.md` §8 lists for a full gate: the one full `make gate` of the final W55b candidate covers it.
3. **Outside the grant (all three pre-authorised by the wave executor; you may veto):** `src/auditmanager/runs/executor.py`
   (one role in the geometry stage's tuple), `src/auditmanager/ingest/public.py` (one re-export line),
   `tests/integration/api/test_portal_block_routes.py` (the stub assertion, forced). Evidence in section 2.2.
4. **For WEB-BLOCKS:** a version published before W55b (no bundle) answers `listVersionPortalBlocks` with `not_produced` even
   after a run; read the version's manifest roles (no `source.structured_companion`) or `getVersionBlocks` to tell it from
   "no run yet". The crop endpoint answers `404 not_found` for every block without a crop, including blocks on a
   `geometry_mismatch` page; `PortalBlock.geometry` says which.
5. **For REHEARSAL:** measure the geometry stage's time and peak memory on the 500-page low-text bundle with an IMAGE block per
   page (risk 1); `crop_count`, `crop_blob_count`, `geometry_mismatch_page_count` and `duration_ms` are in the stage result.
6. Prose follow-up outside the grant: risk 6 (`api/schemas/blocks.py` docstring).
7. The lane stack is down: `make down`, `docker volume rm auditmanager-w55b-geometry-postgres-data
   auditmanager-w55b-geometry-s3-data`, `.env` removed.

## 6. Containment

`git diff --name-only 887a8254..HEAD` is the list of section 1 (26 paths). Against the grant:

- **inside:** `src/auditmanager/analysis/stages/page_geometry_extraction.py`; `src/auditmanager/analysis/geometry/**` (6 files);
  `src/auditmanager/analysis/ports/artifacts.py` and `src/auditmanager/analysis/public.py` (role constants and export lines
  only, after RECOGNISED's, nothing reordered); `src/auditmanager/bootstrap/adapters.py` (`BlockAdapter` only: every hunk is
  inside the class); `src/auditmanager/analysis/README.md`; `tests/integration/analysis/geometry/**` (8 files);
  `tests/integration/composition/{test_version_blocks_wire_shape,test_router_answers,test_an_absent_parent_is_not_an_empty_page}.py`;
  `docs/program/W55B-GEOMETRY-01.md`;
- **outside, each with its reason:** `src/auditmanager/runs/executor.py`, `src/auditmanager/ingest/public.py`,
  `tests/integration/api/test_portal_block_routes.py` (section 2.2).
- **Forbidden hotspots untouched:** `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, any `conftest.py`,
  `tests/support/**`, `fixtures/**`, `tools/**`, `web/**`, `P02_SEAMS.md`, `source_preparation.py`, `api/routers/blocks.py`,
  `api/schemas/**`; in `bootstrap/` only `BlockAdapter`.
- `git status --porcelain -uall` is empty at the tip.

## Appendix: design decisions (made while writing; each is open to the integrator's veto)

Each decision names the alternative rejected.

1. **Page box = CropBox clipped to the MediaBox, after `/Rotate`, read from PDFium** (`maths.displayed_size` over
   `PdfPage.get_cropbox()`, `get_mediabox()`, `get_rotation()`). Rejected: `pypdf`'s boxes (a second library whose box could
   differ from the one PDFium draws) and the page inventory's `width_pt`/`height_pt` (pdfplumber's, not the CropBox).
2. **Rotation: the PDF's `/Rotate` is trusted; the portal's `rotation` is only compared.** PDFium renders the page as
   displayed (its `/Rotate` applied clockwise), and `bbox_norm` is in that displayed top-left space, so a box maps the same way
   for every rotation; 90 and 270 exchange the displayed width and height. A portal `rotation` other than the PDF's is
   `geometry_mismatch` (no crop), never a guess. Rejected: re-rotating the render to the portal's `rotation`.
3. **Tolerance "0.5 % per side":** `r = (width_px/height_px) / (width_pt/height_pt)`; pass iff `max(r, 1/r) - 1 <= 0.005`
   (scaling the portal page so one side equals the PDF's, the other side differs by at most 0.5 % of its length, whichever
   side is fitted); equality passes. Rejected: `|r - 1|` alone (asymmetric by direction).
4. **Scale rule:** base = the portal raster's density `width_px / width_pt` (the crop has the resolution of the image the
   portal recognised the block on); raised to a long side of 800 px; lowered to 4 000 000 pixels; kept to 6 decimals so
   `render_profile.scale` is the rendered scale; the integer clip (outward: floor of the near edge, ceil of the far edge) is
   then nudged until both bounds hold. **Corner:** the two bounds cannot conflict for a positive box (the floor gives at most
   640 000 pixels; the cap gives a long side of at least 2 000 px); if rounding ever made them, the cap wins (memory over
   resolution). Rejected: a fixed DPI (ignores the portal's own resolution) and a long side of exactly 800 px (the cap would
   never bind and large drawings would be cut at about 70 dpi).
5. **Degenerate box:** a block needing a page canvas wider than 2**24 px (PDFium positions clips in float32) is refused with
   `analysis_input_invalid`, `reason: portal_block_degenerate`: a long side under `800 / 2**24` of the page's longer side,
   about a sixth of a pixel of a 300 dpi A4 raster. Rejected: leaving such an IMAGE block without a crop (section 4.5 promises one per IMAGE block on a page
   that passed).
6. **Clip render by `FPDF_RenderPageBitmap` with a bitmap of the clip's size** and the page canvas shifted by the clip's
   origin (the call `PdfPage.render(crop=...)` makes), so the bitmap is exactly `maths.plan_crop`'s integer rectangle.
   Rejected: `PdfPage.render(scale, crop=...)` (its per-side `ceil` of a crop given in points can lose a pixel of the floor)
   and rendering the page then cutting (the brief forbids it; memory of the whole page).
7. **`PDFIUM_LOCK` per operation** (open, one page's boxes, one crop, close), every PDFium object closed inside its
   section. Shared through **one line in `ingest/public.py`** (`from auditmanager.ingest.envelope import PDFIUM_LOCK as
   PDFIUM_LOCK`); ALR-05 permits `analysis -> ingest.public`; imported lazily in `geometry.render.pdfium_lock()`. Rejected:
   a lock of analysis's own (two locks do not exclude each other), and moving the lock to `shared` (edits ingest's envelope).
8. **Temporary file:** `geometry.source_file` restates `source_preparation._source_file` with the caller's `stage_id`
   (prefix `am-geometry-`). Rejected: importing the private helper (its refusal names `source_preparation`).
9. **Block list read:** `recognised.portal.read_block_list` first (its strict checks), then `geometry.portal.read_layout`
   for the fields only this stage reads, refusing `portal_blocks_invalid`; `schema_version` 1 and `coordinate_space`
   `normalized_page_top_left` are required (the coordinates mean nothing otherwise). The artifact is built from named fields
   only (no `crop_url`, `document_*`, `shape_type`, `export_status`); `polygon_points` only when non-empty.
10. **Crop blobs are stage artifacts.** Each distinct PNG is published once (`CropPublisher`, by SHA-256) and listed once
    in the stage result as role `geometry.crop_image`: the executor binds each published blob's intent through the stage
    result, and the stage-result schema requires unique items. Rejected: leaving them out of the stage result (their
    publication intents would never be bound).
11. **`listVersionPortalBlocks` reads the latest run whose geometry stage succeeded and published
    `geometry.portal_blocks`.** A version without a bundle therefore answers `not_produced` after its runs too (no run
    produced portal geometry); `getVersionBlocks` is unchanged. See section 4 (an open question for WEB-BLOCKS).
12. **Joined reads are verified against the stage result's recorded digest and size** (`open_stream` with the reference as
    the declaration), and a crop against its manifest record; a missing blob or a disagreement between the run's artifacts
    is `storage_integrity_error` with the `role`; an unknown artifact version is `unsupported_contract_version`. The crop
    404 is `not_found` with `aggregate_type: PortalBlock`.
