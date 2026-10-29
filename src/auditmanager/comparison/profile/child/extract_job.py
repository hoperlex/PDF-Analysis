"""The extraction job of the page-profile child: words with boxes and vector lines, per page.

`CMP-PROFILE-01`, ADR-0025 decision 8 and the addendum of 2026-10-27: ``pdfplumber`` reads the
words with boxes and the vector lines, ``pypdf`` the annotations and the content Merkle, and the
child that runs them gets 1024 MiB (the heaviest real extraction needs 704 MiB; VmPeak 658 to
674 MiB). One job is **one page** of one document; the page is addressed by its 0-based index
and the document by a path in a directory only this worker can read.

The job writes the big arrays to ``extract.json`` in its output directory (words, lines, image
boxes, annotations) and returns the small facts on its answer line. Coordinates are those of the
displayed page, origin at the top left, as ``pdfplumber`` reports them, rounded to two decimals.
"""

from __future__ import annotations

import gc
import json
import os
import time
from typing import Any

try:  # the product (a package) and the child program (top-level modules) both load this file
    from . import page_merkle, segments
except ImportError:  # pragma: no cover - the child program's import path
    import page_merkle  # type: ignore[no-redef]
    import segments  # type: ignore[no-redef]

__all__ = ["run"]

EXTRACT_FILE = "extract.json"


def _round(value: Any, places: int = 2) -> float:
    return round(float(value), places)


def _color(value: Any) -> list[float] | None:
    if value is None or isinstance(value, (str, bytes)):
        return None
    try:
        return [_round(component, 3) for component in value]
    except (TypeError, ValueError):
        return None


def _pypdf_facts(path: str, index: int) -> dict[str, Any]:
    from pypdf import PdfReader

    with open(path, "rb") as handle:
        reader = PdfReader(handle, strict=False)
        page = reader.pages[index]
        facts = {
            "displayed": list(page_merkle.page_frame(page)),
            "merkle": page_merkle.page_digest(page),
            "annotations": page_merkle.annotation_records(page),
        }
    return facts


def run(settings: dict[str, Any]) -> dict[str, Any]:
    import pdfplumber

    clock = time.perf_counter
    started = clock()
    path, index = str(settings["pdf"]), int(settings["page"])

    pypdf_facts = _pypdf_facts(path, index)
    gc.collect()
    t_pypdf = clock() - started

    began = clock()
    pdf = pdfplumber.open(path)
    try:
        page = pdf.pages[index]
        words = page.extract_words()
        t_words = clock() - began
        began = clock()
        raw_lines, raw_rects, raw_curves = page.lines, page.rects, page.curves
        drawn_lines, rect_count, curve_count, char_count = len(raw_lines), len(raw_rects), len(raw_curves), len(page.chars)
        raw_images = list(page.images)
        t_lines = clock() - began
        width, height, rotation, offset_x, offset_y = pypdf_facts["displayed"]

        def box(x0: float, top: float, x1: float, bottom: float) -> list[float]:
            return [_round(x0 - offset_x), _round(top - offset_y), _round(x1 - offset_x), _round(bottom - offset_y)]

        words = [box(w["x0"], w["top"], w["x1"], w["bottom"]) + [w["text"]] for w in words]
        images = [box(i["x0"], i["top"], i["x1"], i["bottom"]) for i in raw_images]
        # `CMP-C1-FIX-A` item 8: the lines, then the edges of rectangles and the straight segments of curves.
        lines = segments.collect(raw_lines, raw_rects, raw_curves, box, _color)
        del raw_lines, raw_rects, raw_curves
        body = {
            "page": {
                "width_pt": _round(width),
                "height_pt": _round(height),
                "rotation": int(rotation),
                "offset": [_round(offset_x), _round(offset_y)],
                "frame_width_pt": _round(page.width),
                "frame_height_pt": _round(page.height),
            },
            "words": words,
            "lines": lines,
            "images": images,
            "annotations": pypdf_facts["annotations"],
        }
        facts = {
            "width_pt": _round(width),
            "height_pt": _round(height),
            "rotation": int(rotation),
            "offset": [_round(offset_x), _round(offset_y)],
            "words": len(words),
            "lines": len(lines),
            "drawn_lines": drawn_lines,
            "rects": rect_count,
            "curves": curve_count,
            "chars": char_count,
            "images": len(images),
            "annotations": len(pypdf_facts["annotations"]),
            "annotation_hashes": [record["sha256"] for record in pypdf_facts["annotations"]],
            "merkle": pypdf_facts["merkle"],
            "t_pypdf_s": round(t_pypdf, 4),
            "t_words_s": round(t_words, 4),
            "t_lines_s": round(t_lines, 4),
        }
        page.flush_cache()
    finally:
        pdf.close()
    out_dir = str(settings["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, EXTRACT_FILE), "w", encoding="utf-8") as sink:
        json.dump(body, sink, ensure_ascii=False, separators=(",", ":"))
    facts["extract_bytes"] = os.path.getsize(os.path.join(out_dir, EXTRACT_FILE))
    facts["t_child_s"] = round(clock() - started, 4)
    return facts
