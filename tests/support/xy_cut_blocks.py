"""A portal-style block layout for a PDF that does not come with one, found from the PAGE RASTER, never from the text layer.

A real portal draws its rectangles from what the page looks like. To hold the finding to block relation against a richer
document than the committed bundles (tables, the cells of a table row, justified paragraphs) a stand needs block lists that
are independent of the text layer's line boxes -- otherwise the lines and the blocks would agree by construction. This module
renders each page with PDFium, binarises it, and runs the classic recursive XY-cut on the ink: split a region where a band of
empty rows at least ``gap_y`` high crosses it, else where a band of empty columns at least ``gap_x`` wide does, and stop at a
region that neither splits. A leaf is the tight ink box plus a little padding (a person does not draw on the glyph edge).

The recognised text of a block is what the PDF's characters inside its box read as (``Page.within_bbox``, the same extraction
options as the text layer). It is the stand-in for the portal's OCR; it is *geometric*, so a comparison of a quote with it
tests where the block lies, which is the point.

Not product code. Deterministic: the same PDF and parameters give the same blocks.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import pdfplumber
import pypdfium2 as pdfium

from auditmanager.analysis.stages.extraction import TEXT_OPTIONS

#: Pixels per point of the raster the layout is found on.
SCALE = 2.0
#: A pixel is ink when its grey value is below this (a table header's light grey fill is not).
INK_BELOW = 200


@dataclass(frozen=True, slots=True)
class Layout:
    """How eagerly a page is cut. ``gap_*`` are in points of the page."""

    name: str
    gap_y_pt: float
    gap_x_pt: float
    pad_pt: float = 1.5


#: Paragraph-level blocks: a table stays whole unless its columns stand far apart.
PARAGRAPHS = Layout("paragraphs", gap_y_pt=7.0, gap_x_pt=30.0)
#: Cell-level blocks: the columns of a table row are blocks of their own.
CELLS = Layout("cells", gap_y_pt=7.0, gap_x_pt=11.0)


def _runs(empty: np.ndarray, minimum: int) -> list[tuple[int, int]]:
    """The ``(start, end)`` of every run of ``True`` in ``empty`` at least ``minimum`` long, interior only."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(empty):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            if index - start >= minimum:
                runs.append((start, index))
            start = None
    return runs


def _cut(ink: np.ndarray, x0: int, y0: int, x1: int, y1: int, gap_x: int, gap_y: int) -> list[tuple[int, int, int, int]]:
    region = ink[y0:y1, x0:x1]
    rows, cols = np.flatnonzero(region.any(axis=1)), np.flatnonzero(region.any(axis=0))
    if rows.size == 0:
        return []
    x0, x1, y0, y1 = x0 + int(cols[0]), x0 + int(cols[-1]) + 1, y0 + int(rows[0]), y0 + int(rows[-1]) + 1
    region = ink[y0:y1, x0:x1]
    for axis, gap in ((1, gap_y), (0, gap_x)):
        empty = ~region.any(axis=axis)
        gaps = _runs(empty, gap)
        if not gaps:
            continue
        edges = [0, *[edge for gap_run in gaps for edge in gap_run], empty.size]
        parts: list[tuple[int, int, int, int]] = []
        for start, end in zip(edges[0::2], edges[1::2]):
            if end <= start:
                continue
            if axis == 1:
                parts += _cut(ink, x0, y0 + start, x1, y0 + end, gap_x, gap_y)
            else:
                parts += _cut(ink, x0 + start, y0, x0 + end, y1, gap_x, gap_y)
        return parts
    return [(x0, y0, x1, y1)]


def page_blocks(pdf: bytes, layout: Layout) -> list[list[tuple[float, float, float, float]]]:
    """Per page, the blocks as normalised ``(x0, y0, x1, y1)`` boxes (top-left origin), in reading order."""
    document = pdfium.PdfDocument(pdf)
    pages: list[list[tuple[float, float, float, float]]] = []
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=SCALE).to_numpy()
            grey = bitmap[:, :, :3].mean(axis=2)
            ink = grey < INK_BELOW
            height, width = ink.shape
            boxes = _cut(ink, 0, 0, width, height, round(layout.gap_x_pt * SCALE), round(layout.gap_y_pt * SCALE))
            pad = layout.pad_pt * SCALE
            normalised = [
                (max(0.0, (x0 - pad) / width), max(0.0, (y0 - pad) / height),
                 min(1.0, (x1 + pad) / width), min(1.0, (y1 + pad) / height))
                for x0, y0, x1, y1 in boxes
            ]
            pages.append(sorted(normalised, key=lambda b: (round(b[1], 3), b[0])))
            page.close()
    finally:
        document.close()
    return pages


def block_text(pdf: bytes, layout_pages: list[list[tuple[float, float, float, float]]]) -> list[list[str]]:
    """What the PDF's characters inside each block read as; ``""`` for a block with no characters."""
    texts: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        for page, boxes in zip(document.pages, layout_pages):
            width, height = float(page.width), float(page.height)
            row: list[str] = []
            for x0, y0, x1, y1 in boxes:
                area = page.within_bbox((x0 * width, y0 * height, x1 * width, y1 * height), strict=False)
                row.append((area.extract_text(**TEXT_OPTIONS) or "").strip())
            texts.append(row)
    return texts
