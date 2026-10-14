#!/usr/bin/env python3
"""Do the crops depict the regions their blocks mark? Numbers, and sheets for the eye.

    python scripts/rehearsal/w55b/crop_fidelity.py DIR [--sheets] [--phase NAME]

``DIR`` is what ``drive.py fetch`` wrote under ``.local/rehearsal-w55b/``: the version's PDF, the
IMAGE blocks (page, ``bbox_norm``) and every crop the product cut. For each crop this script
renders the WHOLE page with pypdfium2 at the crop's own scale -- estimated from the crop's pixel
size and the block's box (three estimates: by width, by height, by both), never read from the
product -- takes the region the block marks, and compares it with the crop:

* the mean absolute difference per channel (0..255) at the best alignment within +-2 pixels
  (the product's clip is rounded outward to whole pixels), and the offset that gave it;
* the same measure against a deliberately wrong region of the same page and size (the control:
  a measure that cannot tell the right region from a wrong one would prove nothing);
* the share of non-white pixels in the crop (below 250 of 255 in grey) and of dark ones (below
  128) -- a blank crop has neither; the second is the one that means something on a grainy scan;
* whether the crop's size is the region's size to within 2 pixels.

``--sheets`` also writes contact sheets: each row the page, scaled down, with the block's box
drawn on it, beside the crop, labelled by a running number only. The figures file holds counts and
quantiles only (F-7): no name, no text, no identifier from inside the document.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402

from PIL import Image, ImageChops, ImageDraw, ImageStat  # noqa: E402

WHITE_BELOW = 250
SEARCH = 2


def _mad(a: Image.Image, b: Image.Image) -> float:
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    return sum(stat.mean) / len(stat.mean)


def _ink_share(image: Image.Image, below: int = WHITE_BELOW) -> float:
    grey = image.convert("L")
    histogram = grey.histogram()
    total = sum(histogram)
    return sum(histogram[:below]) / total if total else 0.0


def _quantiles(values: list[float], digits: int = 3) -> dict:
    if not values:
        return {}
    ordered = sorted(values)

    def at(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], digits)

    return {"n": len(ordered), "min": round(ordered[0], digits), "p10": at(0.10), "p50": at(0.50),
            "p90": at(0.90), "max": round(ordered[-1], digits)}


def measure(directory: Path, sheets: bool) -> dict:
    import pypdfium2 as pdfium

    records = json.loads((directory / "image_blocks.json").read_text(encoding="utf-8"))
    document = pdfium.PdfDocument(str(directory / "document.pdf"))
    rows = []
    sheet_rows = []
    try:
        for record in records:
            crop_path = directory / f"crop-{record['n']:03d}.png"
            if not crop_path.is_file():
                rows.append({"n": record["n"], "crop": False, "geometry": record["geometry"]})
                continue
            crop = Image.open(crop_path).convert("RGB")
            width, height = crop.size
            page = document[record["page_number"] - 1]
            try:
                page_w, page_h = page.get_size()
                x0, y0, x1, y1 = record["bbox_norm"]
                scale_x = width / ((x1 - x0) * page_w)
                scale_y = height / ((y1 - y0) * page_h)
                combined = (width + height) / ((x1 - x0) * page_w + (y1 - y0) * page_h)
                # Three estimates of the crop's scale, each rendered; the best alignment wins.
                best = (float("inf"), 0, 0)
                rendered = None
                for candidate in sorted({round(combined, 6), round(scale_x, 6), round(scale_y, 6)}):
                    image = page.render(scale=candidate).to_pil().convert("RGB")
                    w_c, h_c = image.size
                    l_c, t_c = math.floor(x0 * w_c), math.floor(y0 * h_c)
                    for dy in range(-SEARCH, SEARCH + 1):
                        for dx in range(-SEARCH, SEARCH + 1):
                            box = (l_c + dx, t_c + dy, l_c + dx + width, t_c + dy + height)
                            if box[0] < 0 or box[1] < 0 or box[2] > w_c or box[3] > h_c:
                                continue
                            value = _mad(crop, image.crop(box))
                            if value < best[0]:
                                best = (value, dx, dy)
                                rendered, scale = image, candidate
                    if rendered is not image:
                        del image
            finally:
                page.close()
            if rendered is None:
                rows.append({"n": record["n"], "crop": True, "geometry": record["geometry"], "unaligned": True})
                continue
            canvas_w, canvas_h = rendered.size
            left, top = math.floor(x0 * canvas_w), math.floor(y0 * canvas_h)
            region_w = math.ceil(x1 * canvas_w) - left
            region_h = math.ceil(y1 * canvas_h) - top
            # The control: the same size, displaced by half the crop (or as far as the page
            # allows), so it overlaps the right region by at most half.
            shift_x = width // 2 if left + width // 2 + width <= canvas_w else -min(left, width // 2)
            shift_y = 0 if shift_x else (height // 2 if top + height // 2 + height <= canvas_h else -min(top, height // 2))
            control_box = (left + shift_x, top + shift_y, left + shift_x + width, top + shift_y + height)
            control = None
            if (shift_x or shift_y) and control_box[0] >= 0 and control_box[1] >= 0 \
                    and control_box[2] <= canvas_w and control_box[3] <= canvas_h:
                control = _mad(crop, rendered.crop(control_box))
            region_ink = _ink_share(rendered.crop((left, top, left + width, top + height)))
            rows.append({
                "n": record["n"], "crop": True, "geometry": record["geometry"],
                "width": width, "height": height, "scale": round(scale, 6),
                "scale_xy_ratio": round(scale_x / scale_y, 5),
                "size_matches_region": abs(region_w - width) <= 2 and abs(region_h - height) <= 2,
                "best_mad": round(best[0], 4), "best_offset": [best[1], best[2]],
                "control_mad": None if control is None else round(control, 4),
                "crop_ink_share": round(_ink_share(crop), 5), "region_ink_share": round(region_ink, 5),
                "crop_dark_share": round(_ink_share(crop, 128), 5),
            })
            if sheets:
                thumb = rendered.copy()
                thumb.thumbnail((700, 700))
                factor = thumb.size[0] / canvas_w
                draw = ImageDraw.Draw(thumb)
                draw.rectangle((left * factor, top * factor, (left + width) * factor, (top + height) * factor),
                               outline=(255, 0, 0), width=4)
                small = crop.copy()
                small.thumbnail((700, 700))
                sheet_rows.append((record["n"], thumb, small))
            del rendered
    finally:
        document.close()
    if sheets:
        _write_sheets(directory / "sheets", sheet_rows)
    return {"rows": rows}


def _write_sheets(target: Path, rows: list, per_sheet: int = 4) -> None:
    target.mkdir(exist_ok=True)
    for start in range(0, len(rows), per_sheet):
        chunk = rows[start:start + per_sheet]
        sheet = Image.new("RGB", (1460, 720 * len(chunk)), (200, 200, 200))
        draw = ImageDraw.Draw(sheet)
        for index, (number, page, crop) in enumerate(chunk):
            y = index * 720 + 10
            sheet.paste(page, (10, y))
            sheet.paste(crop, (740, y))
            draw.rectangle((0, y - 10, 60, y + 20), fill=(0, 0, 0))
            draw.text((6, y - 6), f"#{number}", fill=(255, 255, 0))
        sheet.save(target / f"sheet-{start // per_sheet + 1:02d}.png")


def summarise(rows: list[dict]) -> dict:
    unaligned = sum(1 for r in rows if r.get("unaligned"))
    cut = [r for r in rows if r["crop"] and not r.get("unaligned")]
    controls = [r["control_mad"] for r in cut if r["control_mad"] is not None]
    return {
        "image_blocks": len(rows),
        "with_crop": len(cut) + unaligned,
        "without_crop": len(rows) - len(cut) - unaligned,
        "could_not_align": unaligned,
        "best_mad_quantiles": _quantiles([r["best_mad"] for r in cut]),
        "control_mad_quantiles": _quantiles(controls),
        "best_offset_zero": sum(1 for r in cut if r["best_offset"] == [0, 0]),
        "best_offset_within_1px": sum(1 for r in cut if max(map(abs, r["best_offset"])) <= 1),
        "size_matches_region": sum(1 for r in cut if r["size_matches_region"]),
        "scale_quantiles": _quantiles([r["scale"] for r in cut], 4),
        "scale_xy_ratio_quantiles": _quantiles([r["scale_xy_ratio"] for r in cut], 5),
        "crop_ink_share_quantiles": _quantiles([r["crop_ink_share"] for r in cut], 5),
        "crop_dark_share_quantiles": _quantiles([r["crop_dark_share"] for r in cut], 5),
        "blank_crops_ink_below_0_1_percent": sum(1 for r in cut if r["crop_ink_share"] < 0.001),
        "blank_crops_dark_below_0_1_percent": sum(1 for r in cut if r["crop_dark_share"] < 0.001),
        "controls_measured": len(controls),
        "controls_above_best": sum(1 for r in cut if r["control_mad"] is not None and r["control_mad"] > r["best_mad"]),
        "min_control_over_max_best": (round(min(controls) / max(r["best_mad"] for r in cut), 2)
                                      if controls and max(r["best_mad"] for r in cut) > 0 else None),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--sheets", action="store_true")
    parser.add_argument("--phase", default="c-crop-fidelity")
    args = parser.parse_args(argv)
    directory = args.directory.resolve()
    if common.OUT not in directory.parents:
        raise SystemExit(f"refusing to read or write outside {common.OUT}")
    result = measure(directory, args.sheets)
    (directory / "fidelity_rows.json").write_text(json.dumps(result["rows"], indent=1))
    summary = summarise(result["rows"])
    common.write_figures(args.phase, {"what": "each crop against the same region of a whole-page render", **summary})
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
