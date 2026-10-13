"""The one module of this stage that calls PDFium (``pypdfium2``), and always under its lock.

`W55B-GEOMETRY-01`. PDFium is not thread-safe, and this process may run ingest's envelope
(``pypdfium2``, in API request threads) while a run executes beside it -- with
``EXECUTION_ROLE=all`` the run carrier is a thread of the serving process
(:mod:`auditmanager.runs.carrier`). So every call made here holds the process's one lock,
``PDFIUM_LOCK``, which ingest owns and exports through :mod:`auditmanager.ingest.public`
(the one cross-context name this package imports, as ALR-05 allows).

**Short critical sections.** The lock is taken per operation -- opening the document, reading
one page's boxes, rendering one crop, closing the document -- and released between them, so
a document of five hundred pages never holds up an upload for the length of the stage. Every
PDFium object created inside a section is closed inside it, except the document, which is
closed in its own section on the way out; nothing is left for a finaliser to close on another
thread.

**A clip render.** :meth:`PdfiumDocument.render` allocates a bitmap of the crop's size --
``plan.width`` x ``plan.height``, never the page's -- and asks PDFium to draw the page as
displayed (``/Rotate`` applied), scaled to ``plan.canvas_width`` x ``plan.canvas_height`` and
shifted so the clip's top-left corner is the bitmap's origin. PDFium rasterises only what
falls inside the bitmap. This is the call ``pypdfium2``'s own ``PdfPage.render(crop=...)``
makes, made directly so that the bitmap is exactly the integer rectangle
:func:`~auditmanager.analysis.geometry.maths.plan_crop` computed rather than ``pypdfium2``'s
own per-side rounding of a crop given in points.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Final

from auditmanager.analysis.geometry.maths import Box, CropPlan, displayed_size, normalised_rotation
from auditmanager.shared.errors import DomainError, ErrorCode

#: The fill of the bitmap before the page is drawn on it: opaque white, as a page prints.
_WHITE: Final[tuple[int, int, int, int]] = (255, 255, 255, 255)


def pdfium_lock() -> threading.Lock:
    """The process's one PDFium lock (ingest's ``PDFIUM_LOCK``)."""
    from auditmanager.ingest.public import PDFIUM_LOCK

    return PDFIUM_LOCK


def renderer_name() -> str:
    """``pypdfium2 <version>``, read from the installed module (``render_profile.renderer``)."""
    import pypdfium2.version

    return f"pypdfium2 {pypdfium2.version.PYPDFIUM_INFO.version}"


@dataclass(frozen=True, slots=True)
class PageGeometry:
    """One page as PDFium displays it: the CropBox clipped to the MediaBox, after ``/Rotate``."""

    page_number: int
    width_pt: float
    height_pt: float
    rotation_deg: int


class PdfiumDocument:
    """A PDF opened by PDFium from a file path, for the length of a ``with`` block."""

    def __init__(self, path: str, *, stage_id: str) -> None:
        self._path = path
        self._stage_id = stage_id
        self._document: Any = None
        self._page_count = 0

    def __enter__(self) -> PdfiumDocument:
        import pypdfium2 as pdfium

        with pdfium_lock():
            try:
                self._document = pdfium.PdfDocument(self._path)
                self._page_count = len(self._document)
            except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
                if self._document is not None:
                    self._document.close()
                    self._document = None
                raise DomainError(
                    ErrorCode.ANALYSIS_INPUT_INVALID,
                    message="the source document could not be opened by the page renderer",
                    stage_id=self._stage_id,
                    reason="source_unreadable",
                ) from exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._document is not None:
            with pdfium_lock():
                self._document.close()
            self._document = None

    @property
    def page_count(self) -> int:
        return self._page_count

    def page_geometry(self, page_number: int) -> PageGeometry:
        """The displayed size and ``/Rotate`` of one 1-based page."""
        with pdfium_lock():
            page = self._document[page_number - 1]
            try:
                cropbox = Box(*page.get_cropbox())
                mediabox = Box(*page.get_mediabox())
                rotation = normalised_rotation(int(page.get_rotation()))
            finally:
                page.close()
        width, height = displayed_size(cropbox, mediabox, rotation)
        return PageGeometry(page_number, width, height, rotation)

    def render(self, page_number: int, plan: CropPlan) -> Any:
        """The clip ``plan`` of one 1-based page, as an RGB :class:`PIL.Image.Image`."""
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_raw

        with pdfium_lock():
            page = self._document[page_number - 1]
            try:
                # PDFium writes BGR; ``to_pil`` reads it as such and gives an RGB image.
                bitmap = pdfium.PdfBitmap.new_native(
                    plan.width, plan.height, pdfium_raw.FPDFBitmap_BGR
                )
                try:
                    bitmap.fill_rect(_WHITE, 0, 0, plan.width, plan.height)
                    pdfium_raw.FPDF_RenderPageBitmap(
                        bitmap,
                        page,
                        -plan.left,
                        -plan.top,
                        plan.canvas_width,
                        plan.canvas_height,
                        0,
                        pdfium_raw.FPDF_ANNOT,
                    )
                    # A copy that owns its pixels, so nothing outlives the bitmap's buffer.
                    image = bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
        return image


__all__ = ["PageGeometry", "PdfiumDocument", "pdfium_lock", "renderer_name"]
