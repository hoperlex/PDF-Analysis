"""The service zones of a page: the title block, the release mark with its QR code, the margins outside the frame.

`CMP-ENGINE-01`. Port of the zones of ``profile.py:112-125`` of the original, built from the page profile (words, long
lines, the 36 dpi ink mask) instead of from ``PyMuPDF`` objects, and of ``service.py`` (the QR code). A zone is
``{"type", "bbox"}`` with ``bbox`` in points in the frame of the displayed page. The main area of the comparison is the
page without them; they are compared on their own, field by field (:mod:`.job`).

**Not built: the separation of overlay objects** (``separation.py`` of the original). The original removes the last
content stream of a page (how PDF editors append a release mark, a warning or a QR code) from an in-memory copy and
compares the drawing under it. That needs a PDF editor (``PyMuPDF``, excluded by ADR-0025 ``OD-01``), and a copy of an A1
page through ``pypdf`` costs more than the child's ceiling. Here a release mark is a *zone* the main comparison leaves
out (the original does the same with a mark it could not separate, ``engine.py:452-458``), and a warning set into the
page content is reported as such: the ``warnings`` channel is ``unchecked`` and the pair is ``PARTIAL_COVERAGE``
(``engine.py:978-981``, the original's own answer to a warning it did not separate).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

import cv2
import numpy

from . import words as words_module
from .words import MM

__all__ = ["page_zones", "qr_like_components", "read_qr", "release_text", "zone_bbox"]

#: ``service.py:98``: how far around a release mark a QR code is looked for (x, y), points.
QR_SEARCH_PT = (250.0, 100.0)
QR_DPI = 200


def qr_like_components(mask: Any, dpi: int, near: Sequence[float]) -> list[list[float]]:
    """Square patches of graphics 8-40 mm across next to a release mark: a QR code (``profile.py:64-85``)."""
    k = dpi / 72.0
    mm = dpi / 25.4
    dilated = cv2.dilate(mask, numpy.ones((3, 3), numpy.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(dilated, connectivity=8)
    x0, y0, x1, y1 = near
    out: list[list[float]] = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        if not (8 * mm <= w <= 40 * mm and 8 * mm <= h <= 40 * mm and 0.7 <= w / max(h, 1) <= 1.4):
            continue
        if area < 0.25 * w * h:
            continue
        bx0, by0, bx1, by1 = x / k, y / k, (x + w) / k, (y + h) / k
        v_overlap = min(by1, y1) - max(by0, y0)
        h_gap = max(bx0 - x1, x0 - bx1)
        if v_overlap > 0.3 * (by1 - by0) and h_gap <= 30 * 72 / 25.4:
            out.append([bx0, by0, bx1, by1])
    return out


def page_zones(
    words: list[dict[str, Any]],
    width_pt: float,
    height_pt: float,
    frame_segments: Sequence[Sequence[float]],
    profile_stamp_zone: Sequence[float] | None,
    has_stamp_fields: bool,
    mask36: Any,
) -> list[dict[str, Any]]:
    """The service zones of one page: title block, release marks (with a QR code next to them), margins."""
    frame = words_module.detect_frame(width_pt, height_pt, frame_segments)
    zones: list[dict[str, Any]] = []
    stamp = words_module.stamp_zone(words, width_pt, height_pt, frame)
    if stamp is None and has_stamp_fields and profile_stamp_zone:
        stamp = [float(v) for v in profile_stamp_zone]
    if stamp is not None:
        zones.append({"type": "stamp", "bbox": stamp})
    for release in words_module.release_blocks(words):
        bbox = release["bbox"]
        qr = qr_like_components(mask36, 36, bbox) if mask36 is not None else []
        union = [min([bbox[0]] + [q[0] for q in qr]), min([bbox[1]] + [q[1] for q in qr]),
                 max([bbox[2]] + [q[2] for q in qr]), max([bbox[3]] + [q[3] for q in qr])]
        zones.append({"type": "release_stamp", "bbox": union, "text": release["text"][:200], "date": release["date"]})
    if frame:
        fx0, fy0, fx1, fy1 = frame
        for rect in ([0, 0, fx0, height_pt], [fx1, 0, width_pt, height_pt], [fx0, 0, fx1, fy0], [fx0, fy1, fx1, height_pt]):
            if rect[2] - rect[0] > 0.5 and rect[3] - rect[1] > 0.5:
                zones.append({"type": "margin", "bbox": [float(v) for v in rect]})
    return zones


def zone_bbox(zones: Sequence[dict[str, Any]], kind: str) -> list[float] | None:
    boxes = [z["bbox"] for z in zones if z["type"] == kind]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def release_text(zones: Sequence[dict[str, Any]], zone_words: Sequence[str]) -> str:
    """The text of the release mark: from the zone, else the words that stand in it (``service.py:120``)."""
    texts = [" ".join(str(z.get("text") or "").split()) for z in zones if z["type"] == "release_stamp"]
    return " | ".join(t for t in texts if t) or " ".join(" ".join(zone_words).split())


def _qr_crops(gray: Any) -> list[Any]:
    ink = (gray < 128).astype(numpy.uint8)
    closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, numpy.ones((9, 9), numpy.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(closed)
    out = []
    for i in range(1, n):
        x, y, w, h, _a = (int(v) for v in st[i])
        if 40 <= w <= 800 and 0.8 <= w / max(1, h) <= 1.25 and ink[y : y + h, x : x + w].mean() >= 0.3:
            out.append(cv2.copyMakeBorder(gray[y : y + h, x : x + w], 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255))
    return out


def read_qr(gray: Any) -> dict[str, Any] | None:
    """A QR code in a grey area (``service.py:51-84``): its content if it reads, else a fingerprint of its modules;
    ``None`` when the area holds no code."""
    detector = cv2.QRCodeDetector()
    try:
        ok, texts, _points, _ = detector.detectAndDecodeMulti(gray)
    except cv2.error:
        ok, texts = False, ()
    found = sorted(t for t in (texts or ()) if t) if ok else []
    crops = _qr_crops(gray)
    if not found:
        detectors = [detector] + ([cv2.QRCodeDetectorAruco()] if hasattr(cv2, "QRCodeDetectorAruco") else [])
        for crop in crops:
            for d in detectors:
                try:
                    text = d.detectAndDecode(crop)[0]
                except cv2.error:
                    text = ""
                if text:
                    found.append(text)
                    break
    if found:
        return {"decoded": True, "content": sorted(set(found))}
    if not crops:
        return None
    small = cv2.resize(crops[0], (41, 41), interpolation=cv2.INTER_AREA) < 128
    return {"decoded": False, "content": [], "fingerprint": hashlib.sha256(bytes(numpy.packbits(small))).hexdigest()[:16]}


def qr_search_box(zones: Sequence[dict[str, Any]], width_pt: float, height_pt: float) -> list[float] | None:
    """The area around the release mark (else the title block) in which to look for a QR code (``service.py:101``)."""
    box = zone_bbox(zones, "release_stamp") or zone_bbox(zones, "stamp")
    if not box:
        return None
    dx, dy = QR_SEARCH_PT
    return [max(0.0, box[0] - dx), max(0.0, box[1] - dy), min(width_pt, box[2] + dx), min(height_pt, box[3] + dy)]
