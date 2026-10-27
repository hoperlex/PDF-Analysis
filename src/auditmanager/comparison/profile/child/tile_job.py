"""The tile job of the page-profile child: one tile of level 0 or 1, rendered on request.

`CMP-PROFILE-01`, ADR-0025 addendum of 2026-10-27: levels 0 and 1 of the pyramid are **not stored**;
they are rendered again, one tile at a time, in a child under the 768 MiB ceiling, never inside the
API process. A tile is a **clip render**, which is what makes it cheap (a 512 px tile is 0.1 s and under
200 MiB of address space; rendering the page's whole raster to cut one tile out of it is seconds and the
better part of the ceiling):

* **level 0** draws the page on the same canvas as ``render_job`` (the registration dpi) into a bitmap the
  size of the tile, PDFium drawing only what falls inside it;
* **level 1** is the clip render of the 2 x 2 tiles of level 0 that it covers, reduced by two with
  ``PIL.Image.reduce(2)`` -- the operation that makes level 1 of the stored pyramid.

A tile rendered here is the tile the whole raster would give **to within PDFium's own clip-box effects**:
the partial tiles at the page's far edges are identical, 0.13 % of all pixels of the A1 plan of the corpus
differ (nearly all by one or two grey levels of anti-aliasing, a few thousandths of a percent by more where
a tiling pattern's phase is taken from the clip box). That is a viewer's tile, not evidence: the engine
compares rasters it renders whole in its own child.

Asking for a tile that is not in the pyramid, or for a level above 1, is :class:`geometry.TileOutOfRange`.
"""

from __future__ import annotations

import os
import time
from typing import Any

try:  # the product (a package) and the child program (top-level modules) both load this file
    from . import geometry
except ImportError:  # pragma: no cover - the child program's import path
    import geometry  # type: ignore[no-redef]

__all__ = ["MAX_ON_REQUEST_LEVEL", "run"]

#: Levels rendered on request; the worker stores the others.
MAX_ON_REQUEST_LEVEL = 1
_WHITE = (255, 255, 255, 255)


def run(settings: dict[str, Any]) -> dict[str, Any]:
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    clock = time.perf_counter
    started = clock()
    tile_px = int(settings["tile_px"])
    level_no, column, row = int(settings["level"]), int(settings["column"]), int(settings["row"])
    if not 0 <= level_no <= MAX_ON_REQUEST_LEVEL:
        raise geometry.TileOutOfRange("level")

    document = pdfium.PdfDocument(str(settings["pdf"]))
    try:
        page = document[int(settings["page"])]
        try:
            width_pt, height_pt = page.get_size()
            dpi = geometry.registration_dpi(
                width_pt,
                height_pt,
                pixel_cap=int(settings["pixel_cap"]),
                max_dpi=int(settings["max_dpi"]),
                min_dpi=int(settings["min_dpi"]),
            )
            if dpi is None:
                raise geometry.PageRefused("PAGE_TOO_LARGE", width_pt, height_pt)
            raster_w, raster_h = geometry.raster_size(width_pt, height_pt, dpi)
            levels = geometry.pyramid_levels(raster_w, raster_h, tile_px)
            if level_no >= len(levels):
                raise geometry.TileOutOfRange("level")
            if geometry.tile_box(levels[level_no], column, row, tile_px) is None:
                raise geometry.TileOutOfRange("tile")

            span = 1 << level_no
            left, top = column * tile_px * span, row * tile_px * span
            region_w = min(tile_px * span, raster_w - left)
            region_h = min(tile_px * span, raster_h - top)
            bitmap = pdfium.PdfBitmap.new_native(region_w, region_h, raw.FPDFBitmap_BGR)
            try:
                bitmap.fill_rect(_WHITE, 0, 0, region_w, region_h)
                raw.FPDF_RenderPageBitmap(
                    bitmap, page, -left, -top, raster_w, raster_h, 0, raw.FPDF_ANNOT
                )
                image = bitmap.to_pil().copy()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()

    if level_no == 1:
        image = image.reduce(2)
    out_dir = str(settings["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "tile.png")
    image.save(target, format="PNG")
    return {
        "dpi": dpi,
        "level": level_no,
        "column": column,
        "row": row,
        "width_px": image.size[0],
        "height_px": image.size[1],
        "bytes": os.path.getsize(target),
        "t_child_s": round(clock() - started, 4),
    }
