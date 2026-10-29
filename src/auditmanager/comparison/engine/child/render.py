"""Rendering a band of a page through an affine matrix, with PDFium, and a store of compressed bands.

`CMP-ENGINE-01`, ADR-0025 decision 8 ("the engine tiles its full-resolution work to fit"). The original renders both
pages whole onto a canvas (``engine.py:94-103``); a 40 Mpx page rendered whole twice is two 120 MB arrays before any
filter has run, so here a band of rows is rendered at a time with ``FPDF_RenderPageBitmapWithMatrix``: the matrix
carries the page of B onto the canvas of A (vector rendering at the final place, as the original's
``fitz.Matrix`` did) and the band's offset, and the bitmap is the band alone. Annotations are not drawn (the original
passed ``annots=False``, ``pdfio.py:258``): they are compared on their own.

A and B are rendered the same way, band for band, so identical content under the identity registration gives identical
pixels, whatever PDFium does at the edge of a clip (a tiling pattern's phase comes from the clip box; the same bands
for both pages cancel it). A's bands are kept zlib-compressed (:class:`BandStore`) while B's document is open, so only one document's
objects are in memory at a time.
"""

from __future__ import annotations

import zlib
from collections.abc import Sequence
from typing import Any

import numpy

__all__ = ["BandStore", "open_page", "render_rows"]


def open_page(pdf_path: str, page_index: int) -> tuple[Any, Any]:
    """``(document, page)``; the caller closes the page and then the document."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf_path)
    try:
        return document, document[page_index]
    except BaseException:
        document.close()
        raise


def render_rows(page: Any, matrix: Sequence[float], width_px: int, y0: int, y1: int, x0: int = 0) -> Any:
    """Rows ``[y0, y1)`` of the canvas as a ``uint8`` array ``(y1 - y0, width_px, 3)`` in B, G, R order.

    ``matrix`` is ``[a, b, c, d, e, f]`` taking points of the displayed page onto pixels of the *whole* canvas
    (``x' = a x + c y + e``, ``y' = b x + d y + f``); the band's offset (``y0``, and ``x0`` for a window that does
    not start at the left edge) is applied here."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    rows = y1 - y0
    bitmap = pdfium.PdfBitmap.new_native(width_px, rows, raw.FPDFBitmap_BGR)
    try:
        bitmap.fill_rect((255, 255, 255, 255), 0, 0, width_px, rows)
        a, b, c, d, e, f = (float(v) for v in matrix)
        raw.FPDF_RenderPageBitmapWithMatrix(
            bitmap.raw, page.raw, raw.FS_MATRIX(a, b, c, d, e - x0, f - y0), raw.FS_RECTF(0.0, 0.0, float(width_px), float(rows)), 0
        )
        return numpy.ascontiguousarray(bitmap.to_numpy())
    finally:
        bitmap.close()


class BandStore:
    """Renders kept compressed, one per key: ``put`` an array, ``get`` the same array back."""

    def __init__(self) -> None:
        self._bands: dict[int, tuple[tuple[int, ...], bytes]] = {}
        self.bytes = 0

    def put(self, key: int, array: Any) -> None:
        blob = zlib.compress(array.tobytes(), 1)
        self._bands[key] = (tuple(array.shape), blob)
        self.bytes += len(blob)

    def get(self, key: int) -> Any:
        shape, blob = self._bands[key]
        return numpy.frombuffer(zlib.decompress(blob), dtype=numpy.uint8).reshape(shape)
