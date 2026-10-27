# CMP-PROFILE-01 — page profiles of a version: words, vector lines, stamp, ink mask, scan flag, stored previews and tiles

Written 2026-10-28 by the Sonnet lane `CMP-PROFILE-01` (branch `agent/cmp-profile-01`, base `cc3dd36b` on `integration/compare-modules`; nothing pushed, nothing merged). Task file: [`tasks/CMP-PROFILE-01.md`](tasks/CMP-PROFILE-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (decisions 8 and 9 and the addendum of 2026-10-27); the measured technique reused is [`compare/MEASURE-RENDER-01.md`](compare/MEASURE-RENDER-01.md); the seal is [`CMP-SEAL-C0.md`](CMP-SEAL-C0.md); the oracle is the synthetic corpus `fixtures/comparison` with its answer keys.

## 1. Result

For a published version, `build_version_page_profiles` writes one `comparison_page_profile` row per page (a ULID `cpr_` id and a unique content key) with the page's **words with boxes, vector lines, annotations and their hashes, stamp (designation, sheet number, sheet title, «Изм.», date), 36 dpi ink mask, scan flag and content Merkle**, and publishes a **preview PNG, a thumbnail PNG and the tile levels 2 and up** as blobs. Every render and extraction runs in a **child process under a kernel ceiling** (768 MiB for render and tile children, 1024 MiB for the child that runs pdfplumber, 300 s CPU, 600 s wall), one page per child; **any end without a result is a `needs_review` page with reason `RENDER_FAILED` for that page only**. A page that cannot be kept under **40 Mpx** at the registration dpi is **refused (`PAGE_TOO_LARGE`) and never rendered**. Tile levels 0 and 1 are **rendered on request in a ceilinged child; the API process never loads PDFium** (a fresh interpreter that imports the composition root and serves a real tile has no `pypdfium2`, `pdfplumber` or `pypdf` in `sys.modules`). The five sealed reads are served by `VersionPageAdapter`.

Measured on the synthetic corpus and, numbers only, on the real set of four versions (§6): every one of 59 + 48 pages ends `ready`; the worst page (a 1680 x 1190 mm sheet with 186 861 vector lines) needs 15.5 s and 727 MiB of address space to extract (ceiling 1024 MiB) and the worst render 481 MiB (ceiling 768 MiB); stored bytes are 0.16 MB a page on the synthetic corpus and 1.12 MB a page (at most 3.7 MB) on the real set.

## 2. Base facts, printed before any edit

`contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes`, `VERSION` `0.9.0`, head `0038_comparison_foundation`, base `cc3dd36b5b05b28ed0232107c8d0a437e304f07b` (`P-01` of the task file). They equal the premise of the wave brief, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file.

## 3. What was built

Own paths: `src/auditmanager/comparison/profile/**`; the full-page renderer in `analysis/geometry/render.py`, exported from `analysis/public.py`; the wiring hunks of wave brief §1 rule 4 (below).

| File | What it holds |
| --- | --- |
| `profile/limits.py` | the numbers with the decision that sets each: `ALGO_VERSION` `cmp-profile/1`, ceilings (`RENDER_LIMITS`, `EXTRACT_LIMITS`, `TILE_LIMITS`), `PIXEL_CAP` 40 Mpx, dpi bounds 200 / 72, preview 1400 px, thumbnail 220 px, tile 512 px, first stored level 2, mask 36 dpi, statuses and reasons |
| `profile/child/program.py` | the child: `python -I -B program.py '<json>'`; sets `RLIMIT_CORE`, `RLIMIT_AS`, `RLIMIT_CPU` and `RLIMIT_FSIZE` **before it loads anything**, imports nothing from the product (the precedent of `ingest/pdf_reader.py`), writes JSON lines (`limits_set`, then one `status`) and files into its output directory |
| `profile/child/render_job.py`, `extract_job.py`, `tile_job.py` | the three jobs (render: dpi rule, preview, thumbnail, mask, pyramid; extract: pdfplumber words, lines, images, pypdf annotations and Merkle; tile: one clip-rendered tile of level 0 or 1) |
| `profile/child/geometry.py` | the registration dpi rule, raster size, pyramid and tile boxes, shared by the child and the worker (pure, standard library) |
| `profile/child/page_merkle.py` | the content Merkle and the annotation hashes (pypdf) |
| `profile/runner.py` | `SubprocessChildRunner`: starts the child with a bare environment and `cwd=/`, waits with a wall clock, signals **only its own child by PID**, reaps with `wait4`, classifies the end (`ok`, `refused`, `range`, `overrun`, `cpu`, `wall`, `signal:NAME`, `error:TYPE`, `exit:N`; a child that dies before `limits_set` is `ChildStartError`, the server's fault) |
| `profile/stamp.py` | the stamp reader (§4.4) |
| `profile/profiling.py` | `profile_page`: render child, then extraction child, assemble the summary, the archive, the content key; a failure is a typed page |
| `profile/pack.py` | the stored archive (a deterministic ZIP: `profile.json`, `mask.bin`, `tiles/<level>/<col>_<row>.png`) |
| `profile/builder.py`, `publish.py`, `repository.py`, `source.py` | `build_version_page_profiles` (idempotent, one page at a time, one transaction per page), the blob journal (declared, verifying, available) through `DurablePublicationStore`, the SQL of the table, the source PDF streamed digest-checked into a private temporary file |
| `profile/reader.py`, `tiles.py`, `models.py` | the five reads and the typed `PageProfileData` for other lanes; `TileRenderer` (bounded children, bounded source cache) |
| `analysis/geometry/render.py`, `analysis/public.py` | `PdfiumDocument.render_page(page, dpi=, max_pixels=)`: the whole page under `PDFIUM_LOCK`, refused at its own cap before PDFium allocates; exported as `PdfiumDocument`, `FULL_PAGE_MAX_PIXELS`, `page_raster_size`. **The lane's own children do not call it**: a child that imports the product pays 0.7 s and about 50 MiB of address space to import `analysis` (a tile that takes 0.09 s would take 0.8 s), so the children are standalone programs like `ingest/pdf_reader.py`; the exported renderer is the in-process oracle (`test_tiles_and_the_exported_renderer.py` shows the child's preview, thumbnail and stored tiles equal to its pixels) and the renderer for callers that have measured the page |
| `bootstrap/adapters.py` | `VersionPageAdapter(session_factory, *, blob_store, tiles=None)` replaces the stub; `_page_profile_view` maps a row to the frozen `VersionPageProfile` |
| `comparison/public.py` | appends of this lane's names only (§5) |
| `api/routers/version_pages.py` | docstring only (the router already called the port) |
| `scripts/recovery/grant_classification.py` | `comparison_page_profile` leaves `SEALED_NOT_YET_WRITTEN` (the code now writes it) |
| the two enumerators | the five stub rows removed (`SEALED_STUB_GETS`, `SEALED_STUB_ADDRESSED`); the sweeps now read `404` for an absent `cpr_` |
| `bootstrap/composition.py` | **one line**: `version_pages=VersionPageAdapter(sessions, blob_store=store)` (§9, item 1) |

### 3.1 The registration dpi rule and the cap

`dpi = min(200, floor(sqrt(40e6 / (w_in x h_in))))`, then lowered one step at a time while the raster PDFium really allocates (`ceil` of each side) is over the cap (`3004.2 x 2253.52 pt` gives 175 by the plain rule and 40 000 356 pixels; the rule gives 174), and a page whose dpi would fall under **72** is refused: it cannot be kept under the cap at a resolution that is any use for registration (the largest page admitted is about 6300 x 6300 pt, 2.2 m a side). The worked cases are the measurement's: A1 200 dpi (30.98 Mpx), 1682 x 1189 mm 113 dpi (39.6 Mpx), 2102 x 594 mm 143 dpi. The child checks the cap twice (the rule, then the raster it is about to allocate), so a wrong caller cannot make it allocate more.

### 3.2 What is stored, and where (decision 9, "bytes it keeps count in the page budget")

`comparison_page_profile` has three blob columns, all audited by `scripts/recovery/blob_reference_audit.py` and write-once. **The tile levels 2 and up live inside the archive of `profile_blob_id`**, so that every byte the lane stores is reachable from an audited reference and none is an orphan a reconciliation report would have to explain; the preview and thumbnail are the other two columns, served as they are. A row is inserted **once, complete** (its blobs already `available`), `ON CONFLICT DO NOTHING`; nothing is ever updated or evicted; no code of the package calls the object store to remove anything (held by a static test). The one SQL `DELETE` removes the row of a page that ended without a result, on request (`retry_failed=True`); a `ready` or `refused` row is never deleted.

### 3.3 Coordinates

Words, lines and image boxes are in points in the frame of **the page as displayed** (CropBox applied, `/Rotate` applied), origin at the top left, so `pixel = point x dpi / 72` for the raster, the mask (`x 36/72`) and the tiles. pdfplumber reports the **rotated MediaBox** frame and ignores the CropBox; the extraction child subtracts the displayed page's offset in that frame (computed per rotation from the boxes). Checked on a page cropped asymmetrically and turned by each quarter: every word inside the displayed page has ink under its box in the mask, and a frame shifted by 30 pt would not (`test_words_sit_on_ink_...`). If PDFium and the extraction disagree about the displayed size by more than half a point, the page is `needs_review` with reason `FRAME_MISMATCH` (it was never seen on any page measured). Annotation rectangles are the PDF's own (origin lower left, unrotated); they are kept for identity, not for placing.

### 3.4 The stamp reader (`profile/stamp.py`)

The zone is 205 x 70 mm at the lower-right corner of the displayed page (the original's rule). A title block of the GOST 21.101 family prints the name of a cell above its value; a label is a word that is exactly «Обозначение», «Наименование», «Стадия», «Лист», «Изм.», «Дата» or «Организация»; a cell runs from the label's left edge to the next label of its row and down to the next label below it; the value is read under the label (three lines at most, stopping at a gap of 1.5 line heights). A field whose label is absent, whose cell is empty or whose text has the wrong shape (a sheet number is a short number, optionally `5.1`; a date is `dd.mm.yyyy` and a real date; «Изм.» holds a number) **is absent, never guessed**. A page with no text layer, such as a scan, has no stamp here (no OCR).

### 3.5 Scan flag, content Merkle, content key

* **Scan**: images cover at least 60 % of the page and the page draws at most 20 vector objects (lines, rects, curves), with or without an OCR text layer. A plan on a raster background has vector content on top and is not a scan.
* **Content Merkle** (decision 15): the decoded `/Contents` stream(s) (never interpreted: pypdf's `ContentStream` parses every operator into Python objects), the `/Resources` tree (dictionaries and arrays by value, streams by dictionary and decoded bytes, an image by its **encoded** bytes, references by the digest of their target so object numbers never reach the digest, loops marked, a node budget and a depth ceiling), and the page boxes and `/Rotate`. Annotations are hashed beside it (dictionary and appearance streams, back references left out), so an annotation-only change moves the hash and not the Merkle.
* **Content key** = `sha256{algo, page number, Merkle, annotation hashes}`. The page number is in it because `UNIQUE (version, content_key)` would refuse the second of two identical pages of one version (the VS-1 duplicate sheet); the Merkle itself, in the summary, is equal for them and is what the engine keys its sheet-pair cache on. A refused or failed page has a key over its page number and the version's digest.

### 3.6 Tiles (decision 9, addendum item 2)

The pyramid is 512 px tiles over the working raster; level `n + 1` is level `n` reduced by two (`PIL.Image.reduce(2)`); it stops at the first level whose long side is one tile. **Levels 2 and up are stored** (A1: 17 tiles, 207 KB; levels 0 and 1 would be 84 to 94 % of the bytes). **Levels 0 and 1 are a clip render** in a `tile` child: a bitmap the size of the tile (level 1: the 2 x 2 tiles it covers, reduced by two); a tile takes 0.09 s and **45 MiB (level 0) or 53 MiB (level 1) of address space** (the ceiling is 768). A tile rendered on request equals the whole raster's cut **to within PDFium's clip-box effects**: partial tiles at the page's edge are identical, and 0.13 % of the pixels of the A1 plan differ (nearly all by one or two grey levels; 1 086 pixels in 31 million by more, where a tiling pattern's phase comes from the clip box). It is a viewer's tile, not evidence: the engine renders whole rasters in its own child.

The API-side `TileRenderer` runs at most **2 children at once**, waits 30 s for a slot, and answers `dependency_unavailable` (`dependency: page_tile_render`) for no slot or a child that ended without a result; a tile outside the pyramid is `404`. The source PDF comes from a bounded cache of private temporary files (3 files, 512 MiB, never evicting a file in use).

## 4. The public API for the matrix and engine lanes

From `auditmanager.comparison.public` (appends of this lane's names only):

| Name | What it is |
| --- | --- |
| `build_version_page_profiles(session_factory, blob_store, version_uid, *, runner=None, pages=None, retry_failed=False, on_page=None, render_limits=, extract_limits=, work_dir=None) -> VersionBuildReport` | the function the queue calls as a work kind: stores every missing profile of the current algorithm, idempotent, resumable; `on_page(report)` is called after each page and whatever it raises ends the build there (heartbeat, cancel); a `ChildStartError` is the server's fault and ends it |
| `PAGE_PROFILE_WORK_KIND = "page_profile"` | a suggested kind name; the payload is `{"version_uid": "ver_..."}`; the registry belongs to `CMP-WORK-01` |
| `VersionBuildReport`, `PageBuildReport` | per page: number, `cpr_` id, status, reason, `created`, timings (wall, CPU, peak RSS, `VmPeak` of each child) |
| `PageProfileReader(session_factory, blob_store, *, tiles=None)` | `read_page_profile(id)`, `read_version_profiles(version_uid)` (the typed profiles of a whole version), `list_profiles`, `get_profile`, `read_preview`, `read_thumbnail`, `read_tile` |
| `PageProfileData`, `PageProfileRow`, `PageWord`, `VectorLine`, `PageAnnotation`, `StampFields`, `InkMask` | the typed raw profile; `InkMask.as_array()` is a numpy boolean array (True is ink), `ink_ratio` |
| `PROFILE_READY`, `PROFILE_NEEDS_REVIEW`, `PROFILE_REFUSED`, `REASON_RENDER_FAILED`, `REASON_PAGE_TOO_LARGE` | statuses and reasons (also `FRAME_MISMATCH` in `profile.limits`) |
| `registration_dpi(w_pt, h_pt, *, pixel_cap, max_dpi, min_dpi)`, `PAGE_PIXEL_CAP`, `PAGE_PROFILE_ALGO_VERSION` | the one dpi rule for the engine's registration (`CMP-ENGINE-01`) to reuse |
| `SubprocessChildRunner`, `ChildRunner`, `ChildResult`, `ChildLimits`, `ChildStartError`, `TileRenderer` | the ceilinged child technique, for the engine's own children |
| `analysis.public.PdfiumDocument.render_page(page_number, *, dpi, max_pixels=FULL_PAGE_MAX_PIXELS)`, `page_raster_size` | the in-process full-page renderer under `PDFIUM_LOCK` (for pages already measured; a worker that must bound a hostile page uses a child) |

`listVersionPageProfiles` lists, and the builder builds, the profiles of the **current** `ALGO_VERSION` only; a profile is read by its id whatever its algorithm.

## 5. The five operations

`listVersionPageProfiles` (by page number, opaque cursor, unknown version `404`), `getVersionPageProfile`, `streamVersionPagePreview`, `streamVersionPageThumbnail`, `streamVersionPageTile` (`level 0..12`, `column`, `row` bounded by the router, a tile outside the pyramid `404`). `VersionPageAdapter` is thin: it calls `PageProfileReader` and maps `PageProfileRow` to `VersionPageProfile` (only what the profile holds is set; a failed page has `reason` and no stamp, size or images). Driven through the composed application in `test_page_reads_over_http.py` (listing and cursor, profile equals its list item, preview 187 156 B and thumbnail 11 933 B for the A1 plan of VS-1 v1, a stored tile, tiles of levels 0 and 1 rendered on request with the edge tile's size, every refusal, a failed page).

## 6. Measurements

**Method.** A 40-line loop over `profile_page` with the real runner, one record per page (kept outside git; its core is `outcome = profile_page(SubprocessChildRunner(), pdf_path=..., page_index=i, version_sha256=...)` and the fields of `outcome.timings` and the sizes of `outcome.pack`, `.preview`, `.thumbnail`), run from the lane worktree at commit `86253517` (clean), interpreter `.venv/bin/python` (Python 3.12, `pypdfium2` 5.13.0, `pdfplumber` 0.11.10, Pillow 12.3.0), on 2026-10-28 between 02:15 and 02:30 (+05:00). Per child: wall = the parent's clock; CPU and RSS = the kernel's (`wait4`); `VmPeak` = read by the child itself (the quantity `RLIMIT_AS` limits). **The host was not quiet:** the one-minute load average was 16 to 20 on 8 vCPU while the figures were taken (other projects' runs), so wall times are upper bounds; memory is not load-sensitive. The real set `.local/comparison-measure/13AV-RD-EM2-PA/` was read and measured **by numbers only** (sizes, counts, times, bytes; nothing of a page was printed, copied or stored; `v4.pdf` is byte-identical to `v3.pdf` and was not run again).

**Synthetic corpus** (VS-1 five versions, SP-1 four documents, 44 pages; and the four realistic A1 sheets of `tools/fixtures/comparison/realistic_a1.py`: producer A, producer B, `--paint-ops 0`, `--elements 400001`). All 48 pages `ready`.

| Page class | pages | dpi / Mpx | render wall | render RSS / VmPeak | extract wall | extract RSS / VmPeak | archive + preview + thumbnail |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| A4 (297 x 210) | 9 | 200 / 3.9 | <= 0.27 s | 52 / 71 MiB | <= 0.29 s | 45 / 70 MiB | <= 0.27 MB |
| A3 (420 x 297) | 29 | 200 / 7.7 | <= 0.40 s | 70 / 90 MiB | <= 0.32 s | 44 / 70 MiB | <= 0.19 MB |
| A2 (594 x 420) | 2 | 200 / 15.5 | <= 0.45 s | 106 / 125 MiB | <= 0.28 s | 44 / 70 MiB | <= 0.31 MB |
| **A1 plan (841 x 594), VS-1** | 4 | 200 / 31.0 | **0.74 s** | **178 / 196 MiB** | 0.26 s | 45 / 70 MiB | **0.42 MB** (archive 222 KB, preview 187 KB, thumbnail 12 KB; of the archive 207 KB are tiles) |
| realistic A1, 74 773 lines (A) | 1 | 200 / 30.4 | 1.14 s | 196 / 216 MiB | 8.99 s | 342 / 372 MiB | 1.53 MB (archive 1.11 MB) |
| realistic A1, producer B | 1 | 200 / 30.4 | 1.25 s | 191 / 211 MiB | 6.84 s | 327 / 356 MiB | 1.51 MB |
| realistic A1, light (19 282 lines) | 1 | 200 / 30.4 | 1.15 s | 183 / 202 MiB | 2.86 s | 135 / 162 MiB | 0.91 MB |
| realistic A1, 400 001 elements (181 782 lines) | 1 | 200 / 30.4 | 1.75 s | 240 / 259 MiB | **23.7 s** | **742 / 778 MiB** | 2.56 MB (archive 2.09 MB) |

The preview and thumbnail bytes of the realistic A1 (396 665 and 18 006 for producer A; 403 695 and 18 098 for B) are the figures `MEASURE-RENDER-01` reported for the same sheets **to the byte**: the render child is the measured pipeline. The 44 synthetic pages cost 14.2 s of render and 10.7 s of extraction in all (0.56 s a page) and 7.15 MB (0.16 MB a page).

**Real set** (59 pages of three versions, numbers only; all `ready`; dpi 200 for the small sheets, 143 for 2102 x 594 mm, 113 for 1682 x 1189 mm and 1680 x 1190 mm; the large pages are 39.6 Mpx):

| Figure | Value | Page |
| --- | --- | --- |
| worst render wall | 3.5 s | v2 p13, 1682 x 1189 mm, 39.6 Mpx |
| worst render `VmPeak` (ceiling 768 MiB) | **481 MiB** (RSS 462) | v3 p13, 1680 x 1190 mm, 113 dpi |
| worst extraction wall | 17.3 s | v1 p8, 1682 x 1189 mm |
| worst extraction `VmPeak` (ceiling 1024 MiB) | **727 MiB** (RSS 694) | v3 p12, 1680 x 1190 mm, 186 861 lines, 15.5 s |
| the 59 pages together | render 48.8 s, extraction 145.4 s | |
| stored bytes (archive + preview + thumbnail) | 66.3 MB in all, **1.12 MB a page**, at most 3.74 MB | |

**Bytes per A1 page** (decision 9 asks for it): 0.42 MB for a vector A1 sheet of the corpus, 0.9 to 2.6 MB for the realistic ones, 0.60 to 3.74 MB for the real set's 1680 x 1190 mm pages (the archive carries words, lines, mask and the tile levels 2 and up). For 12 versions of 100 sheets (1 200 pages) at the real set's mean that is **1.3 GB**, at its worst page 4.5 GB; both inside the 8 GiB project cap, and the preview + thumbnail share is 0.4 to 1.3 GB as the addendum estimated. The per-project figure of the ADR (`1.9 to 6.2 GB` in all) therefore needs the engine's masks added, not these.

## 7. Tests

Commands run from the lane worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src`; integration on the lane's own PostgreSQL (`57750`) and MinIO (`61750`) after `make migrate` (head `0038`). Code commit measured: `a8d9d2bc`.

| Run | Result |
| --- | --- |
| `git diff --check` | clean |
| `pytest -q tests/unit/comparison/profile` | **159 passed** in 48 s in 11 files (the five VS-1 versions go through the real children once per session) |
| `pytest -q tests/integration/comparison tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py tests/integration/recovery/test_grant_classification.py tests/integration/api/test_role_register.py` | **281 passed, 1 skipped** (the skip is not this lane's) in 82 s. A first attempt that also took the whole `tests/integration/composition` directory was ended by its own 25-minute `timeout` before it printed a summary and is **not counted**; the two composition files this lane changed (`test_router_answers.py`, `test_an_absent_parent_is_not_an_empty_page.py`) are in this selection and the lane's own 28 integration tests (`tests/integration/comparison/profile`, 16 + 7 + the unit-free ones) are inside it |
| `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract --ignore=<the three D-220 files>` | {{CONTRACT}} |

What the new tests prove, and against what:

* **Against the answer keys** (`test_profiles_against_the_answer_key.py`, 14 tests, the real children): every page of the five VS-1 versions (32 pages) is `ready` and gives the key's designation, **sheet number**, **sheet title**, revision and date, text layer, **scan flag** (exactly V4 page 4 and V5 page 4), size and annotation count; the SP-1 pair's 12 sheets give the key's designation, number and title; the archive holds the words, lines, mask and exactly the stored tile levels; the previews and thumbnails are PNGs of the measured sizes; **every word's box has ink in the mask** (and the same boxes shifted 30 pt do not); the rotated and asymmetrically cropped page of each quarter keeps that property.
* **Merkle** (`test_content_merkle.py`): the Merkle classes of the 32 pages equal the key's classes of `content_sha256` and `image_sha256` exactly; an annotation-only change moves the annotation hash and the content key and not the Merkle; the duplicated sheet has one Merkle and two content keys; a changed stream byte, resource, image byte or page box moves the digest; a reference loop terminates; the budget refuses.
* **Ceilings** (`test_child_runner_and_ceilings.py`, real children): an A1 plan under a 144 MiB render ceiling ends without a result and **only that page** is `needs_review` / `RENDER_FAILED` (the five others are `ready`, the failed page has a distinct content key and no extraction was started for it); a 40 MiB extraction ceiling keeps the pictures and names the stage; an unreadable file and a page index beyond the document are typed pages; **the CPU ceiling ends a child as `cpu`, the wall clock kills only its child and reaps it (no zombie)**; every end is classified from the kernel's wait status; a child that never says `limits_set` is the server's fault; the realistic A1 passes under the addendum's ceilings.
* **Pixel cap** (`test_pixel_cap.py`): the child refuses 12 000 x 12 000 pt before rendering (the output directory is empty, `VmPeak` under 250 MiB), the page profile starts no extraction child for it and stores `refused` / `PAGE_TOO_LARGE`, a 6000 x 6000 pt page is rendered at 75 dpi (39.06 Mpx) inside the ceiling, the exported `render_page` refuses at its own cap.
* **Tiles** (`test_tiles_and_the_exported_renderer.py`): the stored preview and thumbnail are the resize of the in-process raster from the exported renderer; every stored tile (17 on the A1 plan) is the cut of the reduced raster, byte for pixel; tiles of levels 0 and 1 rendered on request are the cut to within the tolerance of §3.6 and the partial tiles at the edge are identical; a tile outside the pyramid or of a stored level is `range`; the on-request child of a page over the cap is refused.
* **The API process** (`test_api_never_loads_pdfium.py`): a static scan of the package outside `child/` and a fresh interpreter that serves a real tile through the composition root's imports.
* **Integration** (database and object store): the build writes the rows and the three blobs of each page, all `available`; a second build writes nothing and two at once write one row a page; a failed page is a typed row without blobs and the version goes on, and `retry_failed` builds only it and deletes nothing that is evidence; a refused page; a version that is unknown, has no source document or whose recorded digest is not its blob's (no child started); a listing by page number; frozen rows and write-once blob references; the starved tile child is `dependency_unavailable` and a stored level is served without any child; the five operations through the composed application.

### 7.1 Mutation proofs (ADR-0025 acceptance criteria; each guard shown red, restored, green)

`<scratch>/mut.sh ID FILE 'OLD=>NEW' TESTS` edits the file, runs the tests, restores the file from git (`git checkout -- FILE`) and runs them again; every "red" below is the quoted failure and every "green" the rerun on the restored file.

| Id | Guard | Mutation | Red | Green |
| --- | --- | --- | --- | --- |
| M1 | the dpi rule refuses a page it cannot keep under the cap | `registration_dpi` ends with `return int(min_dpi)` | `test_a_page_that_cannot_be_kept_under_the_cap_is_refused_not_lowered` (the child's second check still refuses: the test of the child passes alone) | 2 passed |
| M1b | the child never renders a page over the cap | both the rule and the child's second check removed | `test_the_child_refuses_a_page_over_the_cap_before_it_renders_anything` (`'overrun' == 'refused'`) and `test_a_refused_page_starts_no_other_child_and_is_stored_refused` | 5 passed |
| M2 | a refused page is not extracted | `if render.status == "refused"` made `if False` | `test_a_refused_page_starts_no_other_child_and_is_stored_refused` | 1 passed |
| M3 | an end without a result is never `ready` | `_failed` returns `STATUS_READY` | `test_an_unreadable_file_is_a_typed_page_not_an_exception` | 2 passed |
| M4 | the address-space ceiling | `RLIMIT_AS` set to 64 times the ceiling | `test_a_render_that_needs_more_than_its_ceiling_ends_without_a_result_and_the_next_page_is_built` | 2 passed |
| M5 | the CPU ceiling | `RLIMIT_CPU` line removed | `test_the_cpu_ceiling_ends_a_child_and_is_reported_as_cpu` | 1 passed |
| M6 | the wall clock | the remaining time made unbounded | `test_the_wall_clock_kills_only_its_child_and_reaps_it` | 1 passed |
| M7, M7b | the API process never imports PDFium | `import pypdfium2` added to `tiles.py` | `test_no_module_of_the_api_side_imports_a_pdf_library`; and alone `test_a_tile_served_by_the_api_side_code_loads_no_pdf_library_into_the_process` | 2 passed |
| M8 | two identical pages of a version have two keys | `"page"` removed from the content key | `test_a_duplicated_sheet_has_one_merkle_and_two_content_keys` | 1 passed |
| M9 | the Merkle covers every resource | the resources digest made constant | `test_a_changed_resource_changes_the_digest`, `test_a_replaced_image_changes_the_digest_of_a_scan` | 2 passed |
| M10 | levels 0 and 1 are not stored | `FIRST_STORED_TILE_LEVEL = 0` | `test_the_a1_plan_is_the_one_page_with_several_stored_levels` | 1 passed |
| M11 | the frame of the words is the raster's | the crop offset set to zero | `test_words_sit_on_ink_in_the_displayed_frame_..._[0]` | 4 passed |
| M12 | the scan rule | `SCAN_IMAGE_COVERAGE = 2.0` | `test_the_two_scanned_pages_are_flagged_and_have_no_text_nor_stamp` | 1 passed |
| M13 | nothing is guessed (the shape of a sheet number) | any token accepted | `test_nothing_is_guessed_without_a_label_or_with_the_wrong_shape` | 1 passed |
| M14 | the stamp zone | the zone filter dropped | `test_words_outside_the_zone_are_not_the_stamp` | 1 passed |
| M15 | every blob a row names is `available` | `mark_available` removed from the publisher | `test_every_blob_a_row_names_is_available_and_none_is_left_in_flight` (on pages the store has never seen: the first version of this test passed under the mutation because an earlier run had published the same bytes, and was rewritten) | 1 passed |
| M16 | two builders do not fail each other | `ON CONFLICT DO NOTHING` removed | `test_a_second_build_writes_nothing_and_two_builds_at_once_write_one_row_a_page` | 1 passed |
| M17 | an unknown version is `404`, not an empty page | the existence check removed | `test_a_listing_pages_by_page_number_and_an_unknown_version_is_not_found` | 1 passed |
| M18 | the stub rows are gone because the port is served | `get_profile` answers the sealed `503` again | the sweep `test_every_declared_get_answers_without_an_internal_error` | 13 passed |
| M19 | only a failed page's row can be deleted | the `DELETE` scope widened | `test_the_only_delete_statement_removes_rows_that_ended_without_a_result` | 2 passed |
| M20 | no blob is removed | `discard_temporary` called by the publisher | `test_no_module_asks_the_object_store_to_remove_anything` | 2 passed |

Not shown red, with the reason: the child's second pixel-cap check alone (it is unreachable while the rule is right; M1 shows it holding when the rule is wrong); `FRAME_MISMATCH` (no page measured produces it; its branch is three lines and is exercised only by reading); the 503 of a tile child with no slot is a unit test of `TileRenderer` (`test_at_most_the_configured_children_run_at_once_...`) with a fake runner.

## 8. Contracts and hotspots

* **New or changed contracts: none.** `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json` untouched (`git diff --name-only cc3dd36b..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web` prints nothing). Nothing under `src/auditmanager/comparison/work/`, `storage/`, `ingest/`, `jobs/` or `executors/` changed.
* **Files outside the lane's own paths, by wave brief §1 rule 4:** `bootstrap/adapters.py` (`VersionPageAdapter` and two helpers, at the end of the file), `api/routers/version_pages.py` (docstring), `comparison/public.py` (appends), `scripts/recovery/grant_classification.py` (one name), the two composition enumerators (five stub rows), `bootstrap/composition.py` (**one line**, §9 item 1).

## 9. Instructions for the integrator

1. **`bootstrap/composition.py` is `CMP-WORK-01`'s file in this wave, and one line of it is this lane's.** `VersionPageAdapter` cannot reach the database without it: `version_pages=VersionPageAdapter(sessions, blob_store=store),` (it was `VersionPageAdapter(),`). It is the only hunk in that file; if `CMP-WORK-01` merges first, take its file and re-apply this line. Without it the two composition sweeps read `503` for an absent profile now that their stub rows are gone.
2. **Merge order** (§3 of the brief): the lane's hunks in `adapters.py`, `comparison/public.py` and the two enumerators overlap with those of `CMP-INGEST-01` and `-02` (they remove their own rows from the same sets); they are line-local. `adapters.py` ends with `VersionPageAdapter`; its two helpers (`_page_cursor`, `_page_profile_view`) are above it.
3. **The queue.** Register `build_version_page_profiles(session_factory, blob_store, version_uid, on_page=...)` as a work kind (`PAGE_PROFILE_WORK_KIND` is a suggestion) with payload `{"version_uid": ...}`; pass the lease heartbeat and the cancel check as `on_page`. A `ChildStartError` is the server's fault: let the attempt fail and retry. A page that ended without a result is stored `needs_review`; building it again is `retry_failed=True` (it deletes only such rows).
4. **A blob the lane publishes and no row names** (a crash between the three blobs and the insert) is `available` and unreferenced; the content addressing makes a re-run publish the same ids and reference them. `CMP-STORAGE-PARTS-01`'s unreferenced-blob report will list them until then.
5. **`ALGO_VERSION`.** Any change to a rule above is a new value; the old rows stay, and the listing shows the current algorithm's only.
6. The disk of the stand: the lane's measured bytes are in §6; a build writes its working files into the process's temporary directory (one page at a time, at most the page's raster-derived PNGs: 2 to 4 MB) and one source PDF (at most 250 MiB) per version; both are removed on the way out.

## 10. Risks and known limits

1. **The stamp reader is tuned to the label-above-value layout** (the synthetic corpus and the GOST 21.101 form it imitates). The original's own stamp parser was not read (`ORIGINAL-UNREAD-SOURCES.md`), and no real stamp was read by this lane (the real set was measured by numbers only), so what it does on real stamps is **unmeasured**: a layout it does not understand yields an absent field, never a wrong one, but the rate of absent fields on real sheets is unknown. A word «Лист» or «Дата» inside a title shortens the cell to its left.
2. **The scan rule** (60 % image coverage, at most 20 vector objects) is a rule of this lane. It flags the two scans of the synthetic corpus and, on the real set (numbers only), exactly the seven A4 raster pages of `v3.pdf` (pages 20 to 26: no words, three images each) and none of the other 52 pages, among them pages with 302 images; no other evidence exists, and a scan with a drawn overlay would not be flagged.
3. **Tiles of levels 0 and 1 differ from the whole raster's cut in 0.13 % of the pixels** (§3.6). Seams between adjacent on-request tiles can show a one-pixel pattern phase. The engine must not use them.
4. **A tile read of a stored level reads the whole archive** (the object store port has no range read for the archive's directory; `open_stream(window=)` exists and is not used): at most 1 to 3 MB for the pages measured. A page of 500 000 elements has an archive of several MB.
5. **A page that failed is not retried by itself**: the row is frozen and `UNIQUE (version, page, algo_version)` holds it; `retry_failed=True` or a new `ALGO_VERSION` builds it again. A transient overrun under host memory pressure therefore needs an operator's or the queue's decision.
6. **`profile_blob_id` holds more than the profile** (the tile levels): a reader of the profile alone downloads them too. The alternative (a fourth blob column) is a migration.
7. **pdfplumber ignores the CropBox and a viewer does not**; the lane corrects for it, and `FRAME_MISMATCH` exists for the case where it cannot (never seen). Annotation rectangles are in PDF user space.
8. **Memory on the heaviest extraction is 727 to 778 MiB of the 1024 MiB** ceiling (the pypdf Merkle pass runs first and is released before pdfplumber starts; the extraction keeps the words and lines twice for a moment while it moves them into the displayed frame). A page with several times the real set's 186 861 lines would end as `RENDER_FAILED`, as designed.
9. Host load made every wall time an upper bound (§6).
10. **No OCR** is substituted for a missing text layer (P-guard of the product); a scan has no words and no stamp in its profile.
11. The tile child answers `dependency_unavailable`, not a typed `RENDER_FAILED` (an interactive read has no row to hold it); the status line and the reason are logged (`comparison_tile_render_failed end=... stage=...`).

## 11. Resources

Lane containers `auditmanager-cmp-profile-01-{postgres,s3}` on ports 57750 / 61750 / 61751, brought up with `make up` and migrated with `make migrate` from the lane worktree; `df -h /` was read before every container start and every long run (2.6 to 3.1 GiB free, above the 1.5 GiB stop); `make down` was run at the end ({{DOWN}}). AGENTS §8 names a change of the composition root or of a `conftest.py` as one that asks for a complete `make gate` once on the lane; **none was run** (wave brief §1 rule 7: light acceptance, and `R-135`: no full gate in the code series): it is the integrator's window. No process was killed by a pattern; the only signals sent are the runner's `SIGKILL` of its own child by PID at the wall clock.
