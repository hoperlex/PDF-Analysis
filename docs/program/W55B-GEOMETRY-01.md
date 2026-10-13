# W55B-GEOMETRY-01 — report (portal blocks and crops)

Living report: updated with every commit of the lane, so a restart resumes from `git log` and this file.

## 0. Status

- Task: `dispatch/W55-PLAN.md` §B3.7, §B3.3 (the PDF opened from a temporary file), §B4 Stage B 4 `W55B-GEOMETRY-01`, §B5;
  `P02_SEAMS.md` §4.5, §4.8, §4.9, §4.10 (sealed, read only); `W55B-FREEZE-01.md` (crop budget, page-box tolerance).
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `887a8254` (the RECOGNISED report).
- Written by one writer (a Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- Lane stack (when up): `FOUNDATION_INSTANCE=auditmanager-w55b-geometry`, PostgreSQL `57460`, S3 `61060/61061`.
- **State: implementation committed (`2f83e608`); tests next.** Then the existing tests the change forces, the README, the
  real-export count run, light acceptance and the mutation table.

## 1. Decisions (each names the alternative rejected; open to the integrator's veto)

Recorded as they are made; the final form moves them to an appendix.

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
