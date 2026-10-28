"""PDF annotations of the two pages (port of ``engine._compare_annotations``, ``engine.py:348-379``).

`CMP-ENGINE-01`. An annotation of A is the same as one of B when they are of the same kind and their rectangles, B
carried onto A, overlap at least half (``iou >= 0.5``, ``engine.py:367``); the pair is *changed* when the text differs.
The page profile keeps the rectangle in the PDF's own frame (origin at the lower left, not turned); the engine moves it
into the frame of the displayed page only when the page is not turned, and compares annotations of a turned page by
kind and text alone (the profile does not carry the box offset a turned page would need). The original also keyed on the
subject and the author; the profile keeps neither, and compares the hash of the annotation's dictionary and appearance
instead, but only when the registration is the identity, where it is meaningful.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .words import rect_through

__all__ = ["compare_annotations", "display_rect"]


def display_rect(rect: Sequence[float] | None, page_h: float, rotation: int) -> list[float] | None:
    """The rectangle in the frame of the displayed page (origin at the top left), or ``None`` for a turned page."""
    if not rect or rotation % 360 != 0:
        return None
    x0, y0, x1, y1 = (float(v) for v in rect)
    return [min(x0, x1), page_h - max(y0, y1), max(x0, x1), page_h - min(y0, y1)]


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def compare_annotations(
    aa: Sequence[dict[str, Any]],
    bb: Sequence[dict[str, Any]],
    *,
    matrix: Any,
    a_height: float,
    a_rotation: int,
    b_height: float,
    b_rotation: int,
    identity: bool,
) -> dict[str, Any]:
    """``{"same": n, "added": [...], "removed": [...], "changed": [{"before", "after"}]}`` for two lists of
    ``{"subtype", "rect", "contents", "sha256"}``."""
    boxes_a = [display_rect(a.get("rect"), a_height, a_rotation) for a in aa]
    boxes_b = []
    for b in bb:
        rect = display_rect(b.get("rect"), b_height, b_rotation)
        boxes_b.append(rect_through(matrix, rect) if rect is not None else None)
    used: set[int] = set()
    same = 0
    removed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for i, a in enumerate(aa):
        match = None
        for j, b in enumerate(bb):
            if j in used or a.get("subtype") != b.get("subtype"):
                continue
            if boxes_a[i] is not None and boxes_b[j] is not None:
                if _iou(boxes_a[i], boxes_b[j]) >= 0.5:
                    match = j
                    break
            elif (a.get("contents") or "") == (b.get("contents") or ""):
                match = j
                break
        if match is None:
            removed.append(a)
            continue
        used.add(match)
        b = bb[match]
        text_differs = (a.get("contents") or "") != (b.get("contents") or "")
        appearance_differs = identity and a.get("sha256") != b.get("sha256")
        if text_differs or appearance_differs:
            changed.append({"before": a, "after": b})
        else:
            same += 1
    added = [b for j, b in enumerate(bb) if j not in used]
    return {"same": same, "added": added, "removed": removed, "changed": changed}


def diff_count(result: dict[str, Any]) -> int:
    return len(result["added"]) + len(result["removed"]) + len(result["changed"])


def notes(result: dict[str, Any]) -> list[dict[str, Any]]:
    """``ComparisonServiceNote`` dicts for the annotation changes."""
    out: list[dict[str, Any]] = []

    def text(annotation: dict[str, Any]) -> str:
        return " ".join(str(annotation.get("contents") or "").split())[:2000]

    for a in result["removed"]:
        out.append(_note("removed", a, before=text(a)))
    for b in result["added"]:
        out.append(_note("added", b, after=text(b)))
    for pair in result["changed"]:
        out.append(_note("changed", pair["after"], before=text(pair["before"]), after=text(pair["after"])))
    return out


def _note(change: str, annotation: dict[str, Any], *, before: str = "", after: str = "") -> dict[str, Any]:
    note: dict[str, Any] = {"kind": "annotation", "change": change, "zone": "annotations"}
    subtype = str(annotation.get("subtype") or "").strip("/")
    if subtype:
        note["field"] = subtype[:64]
    if before:
        note["before"] = before
    if after:
        note["after"] = after
    return note
