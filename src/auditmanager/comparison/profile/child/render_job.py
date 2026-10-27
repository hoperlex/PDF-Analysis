"""The render job of the page-profile child: preview, thumbnail, ink mask and the tile pyramid.

`CMP-PROFILE-01`, ADR-0025 decisions 8 and 9 and the addendum of 2026-10-27. One job is one page.
``pypdfium2`` renders the page at the **registration dpi** (``geometry.registration_dpi``: at most
40 Mpx), then from that one raster:

* the **preview** PNG (long side 1400 px, never enlarged) and the **thumbnail** PNG (220 px),
  Pillow's Lanczos with ``reducing_gap=3.0`` as measured in ``MEASURE-RENDER-01``;
* the **tile pyramid**, 512 px tiles; only levels ``first_stored_level`` and up are written (the
  worker stores those; levels 0 and 1 are 84 to 94 % of the bytes and are rendered again on
  request by ``tile_job``);
* the **ink mask**, a separate 36 dpi grey render thresholded to one bit a pixel (1 is ink), rows
  padded to whole bytes, most significant bit first.

A page over the pixel cap at the minimum dpi is **refused** before any bitmap is allocated
(:class:`geometry.PageRefused`); the raster that PDFium would allocate is checked against the
cap once more before it is, so a rule that is wrong in the caller cannot make this job allocate
more than the cap. The raster is made the way the measured pipeline made it (``lean``: PDFium
writes ``BGRx``, four bytes a pixel, Pillow shares that buffer), because that is the pipeline
whose peak memory the ceilings were sized from.

Nothing from the product is imported; the output goes to files in ``out_dir``.
"""

from __future__ import annotations

import os
import time
from typing import Any

try:  # the product (a package) and the child program (top-level modules) both load this file
    from . import geometry
except ImportError:  # pragma: no cover - the child program's import path
    import geometry  # type: ignore[no-redef]

__all__ = ["run"]


def _fit(width: int, height: int, long_side: int) -> tuple[int, int]:
    """The size with the long side at ``long_side``; never enlarged."""
    longest = max(width, height)
    if longest <= long_side:
        return width, height
    factor = long_side / longest
    return max(1, round(width * factor)), max(1, round(height * factor))


def _save_png(image: Any, path: str) -> int:
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(path, format="PNG")
    return os.path.getsize(path)


def _ink_mask(page: Any, settings: dict[str, Any], out_dir: str) -> dict[str, Any]:
    from PIL import Image

    mask_dpi = int(settings["mask_dpi"])
    below = int(settings["mask_ink_below"])
    gray = page.render(scale=mask_dpi / geometry.PT_PER_INCH, grayscale=True).to_pil()
    if gray.mode != "L":
        gray = gray.convert("L")
    table = [255 if value < below else 0 for value in range(256)]
    ink = gray.point(table, mode="L")
    ink_pixels = ink.histogram()[255]
    packed = ink.convert("1", dither=Image.Dither.NONE)
    data = packed.tobytes()
    with open(os.path.join(out_dir, "mask.bin"), "wb") as sink:
        sink.write(data)
    return {
        "dpi": mask_dpi,
        "width_px": gray.size[0],
        "height_px": gray.size[1],
        "row_bytes": (gray.size[0] + 7) // 8,
        "bytes": len(data),
        "ink_pixels": ink_pixels,
        "ink_below": below,
    }


def run(settings: dict[str, Any]) -> dict[str, Any]:
    import pypdfium2 as pdfium
    from PIL import Image

    clock = time.perf_counter
    started = clock()
    out_dir = str(settings["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    tile_px = int(settings["tile_px"])
    first_stored = int(settings["first_stored_level"])
    pixel_cap = int(settings["pixel_cap"])

    document = pdfium.PdfDocument(str(settings["pdf"]))
    try:
        page = document[int(settings["page"])]
        try:
            width_pt, height_pt = page.get_size()
            rotation = int(page.get_rotation())
            dpi = geometry.registration_dpi(
                width_pt,
                height_pt,
                pixel_cap=pixel_cap,
                max_dpi=int(settings["max_dpi"]),
                min_dpi=int(settings["min_dpi"]),
            )
            if dpi is None:
                raise geometry.PageRefused("PAGE_TOO_LARGE", width_pt, height_pt)
            raster_w, raster_h = geometry.raster_size(width_pt, height_pt, dpi)
            if raster_w * raster_h > pixel_cap:
                raise geometry.PageRefused("PAGE_TOO_LARGE", width_pt, height_pt)

            facts: dict[str, Any] = {
                "dpi": dpi,
                "width_pt": round(width_pt, 2),
                "height_pt": round(height_pt, 2),
                "rotation": rotation,
                "raster_width_px": raster_w,
                "raster_height_px": raster_h,
            }
            facts["mask"] = _ink_mask(page, settings, out_dir)

            began = clock()
            bitmap = page.render(scale=dpi / geometry.PT_PER_INCH, prefer_bgrx=True, rev_byteorder=True)
            image = bitmap.to_pil()
            facts["t_render_s"] = round(clock() - began, 4)
        finally:
            page.close()
        if image.size != (raster_w, raster_h):
            raise RuntimeError("the raster is not the size the rule computed")

        began = clock()
        size = _fit(raster_w, raster_h, int(settings["preview_px"]))
        preview = image if size == image.size else image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
        facts["preview"] = {
            "width_px": size[0],
            "height_px": size[1],
            "bytes": _save_png(preview, os.path.join(out_dir, "preview.png")),
        }
        del preview
        size = _fit(raster_w, raster_h, int(settings["thumbnail_px"]))
        thumbnail = image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0) if size != image.size else image
        facts["thumbnail"] = {
            "width_px": size[0],
            "height_px": size[1],
            "bytes": _save_png(thumbnail, os.path.join(out_dir, "thumbnail.png")),
        }
        del thumbnail
        facts["t_images_s"] = round(clock() - began, 4)

        began = clock()
        levels = geometry.pyramid_levels(raster_w, raster_h, tile_px)
        stored_tiles, stored_bytes = 0, 0
        # The working raster is released as soon as level 1 exists: the names that hold it are
        # dropped here, and each ``reduce`` below lets go of the level it was made from.
        current, image, bitmap = image, None, None
        for level in levels:
            if level.level >= first_stored:
                level_dir = os.path.join(out_dir, "tiles", str(level.level))
                os.makedirs(level_dir, exist_ok=True)
                for row in range(level.rows):
                    for column in range(level.columns):
                        box = geometry.tile_box(level, column, row, tile_px)
                        assert box is not None
                        stored_bytes += _save_png(
                            current.crop(box), os.path.join(level_dir, f"{column}_{row}.png")
                        )
                        stored_tiles += 1
            if level.level + 1 < len(levels):
                current = current.reduce(2)
        facts["levels"] = [
            {
                "level": level.level,
                "width_px": level.width_px,
                "height_px": level.height_px,
                "columns": level.columns,
                "rows": level.rows,
                "stored": level.level >= first_stored,
            }
            for level in levels
        ]
        facts["tile_px"] = tile_px
        facts["tiles_stored"] = stored_tiles
        facts["tiles_stored_bytes"] = stored_bytes
        facts["t_tiles_s"] = round(clock() - began, 4)
    finally:
        document.close()
    facts["t_child_s"] = round(clock() - started, 4)
    return facts
