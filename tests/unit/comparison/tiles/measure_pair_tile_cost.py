"""What one pair-tile request costs on a 2A0-sized mask (`CMP-VIEWER-01`; the report quotes its output).

Not a test (the name does not start with ``test_``): a measurement a person runs, with the command in the report::

    PYTHONPATH=src .venv/bin/python tests/unit/comparison/tiles/measure_pair_tile_cost.py

A 2A0 sheet (1682 x 1189 mm) is 7483 x 5290 pixels at the 113 dpi the registration rule gives it (39.6 Mpx a plane), so
its mask is eight bit-packed planes of 39.6 MB in all. The mask is synthetic: rectangles of different sizes in every
layer, scattered lone pixels in ``within_tolerance`` and ``noise``, and the stamp zone in ``service_zones``. It prints
JSON: the blob size, the cold decode (time and the process' peak RSS before and after), and for every pyramid level
the time to reduce all eight layers to the busiest tile and to the whole-sheet tile, then the cost of the rest of a
request on a 512 x 512 tile (a warp of page B from four source tiles, the overlay, the paint and the PNG encode).
"""

from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import time
import zlib

import numpy

from auditmanager.comparison.tiles.compose import encode_png, min_composite, paint_layers
from auditmanager.comparison.tiles.grid import Affine, PageGrid
from auditmanager.comparison.tiles.mask import LAYER_NAMES, read_mask
from auditmanager.comparison.tiles.reduction import axis_starts, reduce_max
from auditmanager.comparison.tiles.warp import Region, SourceBudget, warp_region

DPI = 113
WIDTH_PT, HEIGHT_PT = 1682 / 25.4 * 72, 1189 / 25.4 * 72
WIDTH, HEIGHT = math.ceil(WIDTH_PT * DPI / 72), math.ceil(HEIGHT_PT * DPI / 72)


def _status(field: str) -> float:
    """``VmRSS`` (now) or ``VmHWM`` (the peak so far) of this process, in MiB."""
    with open("/proc/self/status", encoding="ascii") as handle:
        for line in handle:
            if line.startswith(field + ":"):
                return int(line.split()[1]) / 1024
    raise RuntimeError(field)


def build_mask() -> bytes:
    rng = numpy.random.default_rng(2026)
    packed = numpy.zeros((8, HEIGHT, (WIDTH + 7) // 8), dtype=numpy.uint8)
    for index, name in enumerate(LAYER_NAMES):
        plane = numpy.zeros((HEIGHT, WIDTH), dtype=bool)
        rectangles = {"main": 300, "light_elements": 100, "color_change": 50, "line_style": 200, "moved": 20,
                      "within_tolerance": 0, "noise": 0, "service_zones": 0}[name]
        for _ in range(rectangles):
            w, h = int(rng.integers(2, 400)), int(rng.integers(2, 120))
            x, y = int(rng.integers(0, WIDTH - w)), int(rng.integers(0, HEIGHT - h))
            plane[y : y + h, x : x + w] = True
        if name in ("within_tolerance", "noise"):
            count = 5000 if name == "within_tolerance" else 20000
            plane[rng.integers(0, HEIGHT, count), rng.integers(0, WIDTH, count)] = True
        if name == "service_zones":
            plane[HEIGHT - round(70 / 25.4 * DPI) :, WIDTH - round(205 / 25.4 * DPI) :] = True
        packed[index] = numpy.packbits(plane, axis=-1)
        del plane
    header = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, WIDTH, HEIGHT)
    return header + zlib.compress(packed.tobytes(), 6)


def main() -> None:
    """Build the blob in one process and measure in a fresh one, so that the peak RSS is the decode's and not the build's."""
    began = time.perf_counter()
    blob = build_mask()
    built = round(time.perf_counter() - began, 2)
    with tempfile.NamedTemporaryFile(prefix="cmp-2a0-mask-", suffix=".bin") as handle:
        handle.write(blob)
        handle.flush()
        done = subprocess.run([sys.executable, __file__, "--measure", handle.name, str(built)], capture_output=True, text=True, check=True)
    print(done.stdout)


def measure(path: str, built: float) -> None:
    blob = open(path, "rb").read()
    out: dict[str, object] = {"host_load_1min": os.getloadavg()[0], "python": sys.version.split()[0],
                              "numpy": numpy.__version__, "grid_px": [WIDTH, HEIGHT], "plane_mpx": round(WIDTH * HEIGHT / 1e6, 2)}
    out["blob_bytes"] = len(blob)
    out["blob_built_s"] = built
    out["rss_mib_before_decode"], out["peak_rss_mib_before_decode"] = round(_status("VmRSS"), 1), round(_status("VmHWM"), 1)
    began = time.perf_counter()
    mask = read_mask(blob)
    out["decode_cold_s"] = round(time.perf_counter() - began, 3)
    out["inflated_bytes"] = mask.nbytes
    out["rss_mib_after_decode"], out["peak_rss_mib_after_decode"] = round(_status("VmRSS"), 1), round(_status("VmHWM"), 1)

    levels = []
    level_w, level_h = WIDTH, HEIGHT
    level = 0
    while True:
        columns, rows = math.ceil(level_w / 512), math.ceil(level_h / 512)
        timings = []
        for column, row in ((0, 0), (columns // 2, rows // 2), (columns - 1, rows - 1)):
            tw, th = min(512, level_w - column * 512), min(512, level_h - row * 512)
            began = time.perf_counter()
            xs, x_end = axis_starts(column * 512, tw, 1 << level, 1, WIDTH)
            ys, y_end = axis_starts(row * 512, th, 1 << level, 1, HEIGHT)
            for name in LAYER_NAMES:
                reduce_max(mask.plane(name), xs, x_end, ys, y_end)
            timings.append(round((time.perf_counter() - began) * 1000, 1))
        levels.append({"level": level, "tiles": f"{columns}x{rows}", "ms_all_8_layers_worst_of_3_tiles": max(timings)})
        if max(level_w, level_h) <= 512:
            break
        level_w, level_h, level = math.ceil(level_w / 2), math.ceil(level_h / 2), level + 1
    out["reduce_all_layers"] = levels

    # The rest of a request on a 512 x 512 tile: page B from four source tiles, overlay, paint, encode.
    rng = numpy.random.default_rng(1)
    page = numpy.full((1100, 1100, 3), 255, dtype=numpy.uint8)
    page[rng.integers(0, 1100, 4000), rng.integers(0, 1100, 4000)] = 0
    summary = {"width_pt": 1100 * 72 / DPI, "height_pt": 1100 * 72 / DPI, "raster": {"dpi": DPI, "width_px": 1100, "height_px": 1100},
               "tiles": {"tile_px": 512, "levels": [{"level": 0, "width_px": 1100, "height_px": 1100, "columns": 3, "rows": 3, "stored": False}]}}
    grid = PageGrid.from_summary(summary)
    assert grid is not None

    def fetch(level: int, column: int, row: int):
        box = grid.tile_box(level, column, row)
        return None if box is None else page[box[1] : box[3], box[0] : box[2]].copy()

    transform = Affine.from_sequence([1, 0, 0, 1, -3.7, -2.9])
    samples = []
    for _ in range(20):
        began = time.perf_counter()
        budget = SourceBudget()
        image = warp_region(fetch, budget, grid_a=grid, level_a=0, origin=(512, 512), region=Region(0, 0, 512, 512), grid_b=grid, to_a=transform)
        warped = time.perf_counter()
        overlay = min_composite(fetch(0, 1, 1), image)
        masks = {name: numpy.zeros((512, 512), dtype=bool) for name in LAYER_NAMES[:7]}
        for plane in masks.values():
            plane[100:140, 100:300] = True
        masks["service_zones"] = numpy.ones((512, 512), dtype=bool)
        paint_layers(overlay, masks, (512, 512))
        painted = time.perf_counter()
        data = encode_png(overlay)
        done = time.perf_counter()
        samples.append((warped - began, painted - warped, done - painted))
    out["tile_512_ms"] = {
        "source_tiles_read": budget.count,
        "warp": round(1000 * sorted(s[0] for s in samples)[len(samples) // 2], 1),
        "overlay_and_paint": round(1000 * sorted(s[1] for s in samples)[len(samples) // 2], 1),
        "png_encode": round(1000 * sorted(s[2] for s in samples)[len(samples) // 2], 1),
        "png_bytes": len(data),
    }
    out["rss_mib_end"], out["peak_rss_mib_end"] = round(_status("VmRSS"), 1), round(_status("VmHWM"), 1)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--measure":
        measure(sys.argv[2], float(sys.argv[3]))
    else:
        main()
