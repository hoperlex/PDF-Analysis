"""The canvas, affine helpers and the bands of the raster (``numpy`` only).

`CMP-ENGINE-01`. The canvas is the page of A at ``dpi``: pixel ``(x, y)`` is the square of the canvas from
``(x, y) * 72 / dpi`` points, the origin at the top left (the wave brief, section 4 item 1). The original's canvas was
the union of A and the carried B (``engine.py:66-91``); a canvas of A alone is what the viewer and the mask share, and
what B puts outside it is reported as ``PARTIAL_COVERAGE`` by the job and not compared.

A 2 x 3 matrix ``m`` maps points of B onto points of A: ``x' = m[0][0] x + m[0][1] y + m[0][2]``,
``y' = m[1][0] x + m[1][1] y + m[1][2]``. The contract's ``transform`` lists it as ``[a, b, c, d, e, f]`` in the order
of the PDF and of PDFium's ``FS_MATRIX`` (``x' = a x + c y + e``, ``y' = b x + d y + f``).
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import numpy

__all__ = [
    "Band",
    "Canvas",
    "bands",
    "identity",
    "invert",
    "matrix_from_pdf",
    "matrix_to_pdf",
]


@dataclass(frozen=True, slots=True)
class Canvas:
    width_pt: float
    height_pt: float
    dpi: int

    @property
    def s(self) -> float:
        return self.dpi / 72.0

    @property
    def width_px(self) -> int:
        return int(math.ceil(self.width_pt * self.s))

    @property
    def height_px(self) -> int:
        return int(math.ceil(self.height_pt * self.s))

    def px(self, r: Sequence[float]) -> list[int]:
        """A rectangle in points as a rectangle of pixels (floor, ceil), ``engine.py:79``."""
        s = self.s
        return [int(math.floor(r[0] * s)), int(math.floor(r[1] * s)), int(math.ceil(r[2] * s)), int(math.ceil(r[3] * s))]

    def pt(self, r: Sequence[int]) -> list[float]:
        s = self.s
        return [r[0] / s, r[1] / s, r[2] / s, r[3] / s]


def identity() -> Any:
    return numpy.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def invert(m: Any) -> Any:
    """The inverse of an affine matrix (``cv2.invertAffineTransform``, written out)."""
    a = numpy.array(m, dtype=numpy.float64)
    det = a[0, 0] * a[1, 1] - a[0, 1] * a[1, 0]
    if abs(det) < 1e-12:
        raise ValueError("the matrix is not invertible")
    inv = numpy.array([[a[1, 1], -a[0, 1]], [-a[1, 0], a[0, 0]]], dtype=numpy.float64) / det
    shift = -inv @ numpy.array([a[0, 2], a[1, 2]])
    return numpy.array([[inv[0, 0], inv[0, 1], shift[0]], [inv[1, 0], inv[1, 1], shift[1]]])


def matrix_to_pdf(m: Any) -> list[float]:
    """``[a, b, c, d, e, f]`` of a 2 x 3 matrix."""
    return [float(m[0][0]), float(m[1][0]), float(m[0][1]), float(m[1][1]), float(m[0][2]), float(m[1][2])]


def matrix_from_pdf(values: Sequence[float]) -> Any:
    a, b, c, d, e, f = (float(v) for v in values)
    return numpy.array([[a, c, e], [b, d, f]])


@dataclass(frozen=True, slots=True)
class Band:
    """Rows ``[core0, core1)`` are the band's; ``[ext0, ext1)`` adds the margin the filters need around them."""

    core0: int
    core1: int
    ext0: int
    ext1: int


def bands(width_px: int, height_px: int, *, pixels: int, margin: int) -> Iterator[Band]:
    rows = max(64, pixels // max(1, width_px))
    for core0 in range(0, height_px, rows):
        core1 = min(height_px, core0 + rows)
        yield Band(core0, core1, max(0, core0 - margin), min(height_px, core1 + margin))
