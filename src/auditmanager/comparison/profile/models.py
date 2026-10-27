"""The page profile as other lanes read it: typed, immutable, no database, no blob store.

`CMP-PROFILE-01`. :class:`PageProfileRow` is one row of ``comparison_page_profile`` with its small
summary; :class:`PageProfileData` is that row together with the stored archive opened: the words with
boxes, the vector lines, the annotations, the stamp, the ink mask. The matrix and the engine lanes
read :class:`PageProfileData` through ``auditmanager.comparison.public.read_page_profile`` and never
open the archive themselves.

Coordinates are those of the page as displayed, in points, origin at the top left, as ``pdfplumber``
reports them (the answer key of the synthetic corpus uses the PDF's own lower-left origin; the
conversion is ``y = height_pt - y_pdf``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final, NamedTuple

__all__ = [
    "Annotation",
    "InkMask",
    "PageProfileData",
    "PageProfileRow",
    "SUMMARY_SCHEMA",
    "StampFields",
    "VectorLine",
    "Word",
]

SUMMARY_SCHEMA: Final[str] = "cmp-page-profile/1"


class Word(NamedTuple):
    x0: float
    top: float
    x1: float
    bottom: float
    text: str


class VectorLine(NamedTuple):
    x0: float
    top: float
    x1: float
    bottom: float
    linewidth: float
    stroking_color: tuple[float, ...] | None


class Annotation(NamedTuple):
    subtype: str | None
    rect: tuple[float, ...] | None
    contents: str | None
    sha256: str


@dataclass(frozen=True, slots=True)
class StampFields:
    designation: str | None = None
    sheet_number: str | None = None
    sheet_title: str | None = None
    revision_number: str | None = None
    release_date: str | None = None


@dataclass(frozen=True, slots=True)
class InkMask:
    """A one-bit-a-pixel raster of where the page has ink, at ``dpi`` (36 by default).

    ``data`` holds ``height_px`` rows of ``row_bytes`` bytes, most significant bit first, 1 is ink.
    """

    dpi: int
    width_px: int
    height_px: int
    row_bytes: int
    data: bytes

    def as_array(self) -> Any:
        """A ``numpy`` boolean array of shape ``(height_px, width_px)``, True where there is ink."""
        import numpy

        rows = numpy.frombuffer(self.data, dtype=numpy.uint8).reshape(self.height_px, self.row_bytes)
        return numpy.unpackbits(rows, axis=1)[:, : self.width_px].astype(bool)

    @property
    def ink_ratio(self) -> float:
        import numpy

        total = self.width_px * self.height_px
        return float(self.as_array().sum()) / total if total else 0.0


@dataclass(frozen=True, slots=True)
class PageProfileRow:
    """One row of ``comparison_page_profile``."""

    page_profile_id: str
    version_uid: str
    page_number: int
    content_key: str
    algo_version: str
    status: str
    reason: str | None
    summary: dict[str, Any]
    profile_blob_id: str | None
    preview_blob_id: str | None
    thumbnail_blob_id: str | None
    created_at: datetime

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


@dataclass(frozen=True, slots=True)
class PageProfileData:
    """A stored page profile with its archive opened. Raw evidence: nothing here is an AI's word."""

    row: PageProfileRow
    width_pt: float
    height_pt: float
    rotation: int
    has_text_layer: bool
    scan: bool
    content_merkle: str | None
    words: tuple[Word, ...] = ()
    lines: tuple[VectorLine, ...] = ()
    image_boxes: tuple[tuple[float, float, float, float], ...] = ()
    annotations: tuple[Annotation, ...] = ()
    stamp: StampFields = field(default_factory=StampFields)
    ink_mask: InkMask | None = None
    #: ``(dpi, width_px, height_px)`` of the working raster the tiles are cut from.
    raster: tuple[int, int, int] | None = None
