"""What the child is told about a pair: the two page profiles, as a JSON file and two packed masks.

`CMP-ENGINE-01`. The child reads no database and no object store; the worker writes its inputs into a private
temporary directory (mode 0700) and removes it afterwards. A page is its source PDF (a path the child opens by
itself), its page index and its profile: the words with boxes, the long lines (only those a frame can be made of), the
annotations, the title block, the image boxes, and the 36 dpi ink mask.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy

from auditmanager.comparison.engine.child.settings import TOLERANCE_PT
from auditmanager.comparison.profile.models import PageProfileData

__all__ = ["page_inputs", "write_inputs"]


def _frame_segments(data: PageProfileData) -> list[list[float]]:
    """Lines long enough to be part of a sheet's frame (``stamp.detect_frame`` asks for 0.4 of a side)."""
    out = []
    for line in data.lines:
        dx, dy = abs(line.x1 - line.x0), abs(line.bottom - line.top)
        if (dx < 0.8 and dy >= 0.4 * data.height_pt) or (dy < 0.8 and dx >= 0.4 * data.width_pt):
            out.append([line.x0, line.top, line.x1, line.bottom])
    return out


def page_inputs(data: PageProfileData, *, pdf_path: str, page_index: int, work_dir: str, name: str) -> dict[str, Any]:
    mask_info = None
    if data.ink_mask is not None:
        mask_path = os.path.join(work_dir, f"mask36_{name}.bin")
        with open(mask_path, "wb") as sink:
            sink.write(data.ink_mask.data)
        mask_info = {
            "file": mask_path, "width_px": data.ink_mask.width_px, "height_px": data.ink_mask.height_px,
            "row_bytes": data.ink_mask.row_bytes,
        }
    lines_info = None
    if data.lines:
        lines_path = os.path.join(work_dir, f"lines_{name}.f32")
        numpy.array([[ln.x0, ln.top, ln.x1, ln.bottom] for ln in data.lines], dtype=numpy.float32).tofile(lines_path)
        lines_info = {"file": lines_path, "count": len(data.lines)}
    stamp = data.stamp
    return {
        "pdf": pdf_path,
        "index": page_index,
        "width_pt": data.width_pt,
        "height_pt": data.height_pt,
        "rotation": data.rotation,
        "scan": data.scan,
        "words": [[w.x0, w.top, w.x1, w.bottom, w.text] for w in data.words],
        "frame_segments": _frame_segments(data),
        "image_boxes": [list(b) for b in data.image_boxes],
        "annotations": [
            {"subtype": a.subtype, "rect": None if a.rect is None else list(a.rect), "contents": a.contents, "sha256": a.sha256}
            for a in data.annotations
        ],
        "stamp": {
            key: value
            for key, value in (
                ("designation", stamp.designation), ("sheet_number", stamp.sheet_number),
                ("sheet_title", stamp.sheet_title), ("revision_number", stamp.revision_number),
                ("release_date", stamp.release_date),
            )
            if value
        },
        "stamp_zone": data.row.summary.get("stamp_zone"),
        "mask36": mask_info,
        "lines": lines_info,
    }


def write_inputs(
    path: str, a: dict[str, Any], b: dict[str, Any], *, dpi: int, reasons: list[str], part: str | None
) -> None:
    document = {"a": a, "b": b, "dpi": int(dpi), "tolerance_pt": TOLERANCE_PT, "reasons": list(reasons), "part": part}
    with open(path, "w", encoding="utf-8") as sink:
        json.dump(document, sink, ensure_ascii=False, separators=(",", ":"))
