"""Reading one plain PDF for comparison: the envelope, then the stamps, each in a ceilinged child.

This is the function a work handler or a request calls with a PDF in hand (:func:`read_pdf`): it applies the
comparison envelope (:mod:`.envelope`) and, for a document the envelope admitted, starts the stamp reader
(:mod:`.stamp_reader`, a second program of the same kind) and turns its zone text into the file's facts
(:mod:`.stamp`). Two children, one after the other, never in parallel: the host has one slot (ADR-0025
decision 8), and the second starts only for a document the first accepted.

Both children are started **by this process, with a descriptor**, never with a path, in a bare environment, under
an address-space ceiling and a CPU ceiling the kernel enforces and a wall clock this side enforces. An end
without an answer (memory, CPU, a signal from PDFium) is the portal envelope's own ``pdf_reader_limits`` refusal.
Nothing here holds :data:`~auditmanager.ingest.envelope.PDFIUM_LOCK`: the lock guards PDFium inside *this*
process, and no PDFium runs in it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Final

from auditmanager.ingest import envelope as _portal
from auditmanager.ingest.envelope import PdfFacts

from .child import descriptor_of, run_child
from .envelope import COMPARISON_POLICY, ComparisonEnvelopePolicy, inspect_comparison_pdf
from .stamp import FileStamp, PageStamp, parse_page_stamp, read_file_stamp

__all__ = ["PdfReading", "ZONE_HEIGHT_MM", "ZONE_WIDTH_MM", "read_pdf"]

#: The lower-right corner read for a title block: the original's 205 x 70 mm (GOST 21.101: 185 x 55 mm and a margin).
ZONE_WIDTH_MM: Final[float] = 205.0
ZONE_HEIGHT_MM: Final[float] = 70.0
_POINTS_PER_MM: Final[float] = 72.0 / 25.4
#: Text kept per page; a title block is a few hundred characters, and a hostile zone cannot grow the answer.
_ZONE_CHARACTERS: Final[int] = 4000
_STAMP_READER: Final[Path] = Path(__file__).with_name("stamp_reader.py")


@dataclass(frozen=True, slots=True)
class PdfReading:
    """What reading one PDF established: the envelope's facts and the stamp facts of the file."""

    facts: PdfFacts
    stamp: FileStamp


def read_pdf(
    content: bytes | bytearray | BinaryIO, *, policy: ComparisonEnvelopePolicy = COMPARISON_POLICY
) -> PdfReading:
    """Admit one PDF under ``policy`` and read its stamps; the portal's typed refusal when it is outside.

    The handle is left positioned at its start. A page with no text layer (a scan) is admitted and listed in
    the stamp's ``textless_pages``; it contributes no designation, no revision and no date.
    """
    handle = _portal.as_handle(content)
    facts = inspect_comparison_pdf(handle, policy=policy)
    size = handle.seek(0, 2)
    handle.seek(0)
    with descriptor_of(handle) as descriptor:
        answer = run_child(
            _STAMP_READER,
            descriptor,
            {
                "descriptor": descriptor,
                "size": size,
                "min_pages": policy.min_pages,
                "max_pages": policy.max_pages,
                "zone_width_pt": ZONE_WIDTH_MM * _POINTS_PER_MM,
                "zone_height_pt": ZONE_HEIGHT_MM * _POINTS_PER_MM,
                "zone_characters": _ZONE_CHARACTERS,
                "address_space": policy.address_space,
                "cpu_seconds": policy.seconds,
            },
            wall_seconds=policy.seconds,
        )
    handle.seek(0)
    pages = _pages_of(answer, expected=facts.page_count)
    return PdfReading(facts=facts, stamp=read_file_stamp(pages, has_layer=list(facts.page_has_layer)))


def _pages_of(answer: dict[str, Any], *, expected: int) -> list[PageStamp]:
    if "pages" in answer:
        pages = answer["pages"]
        if len(pages) != expected:
            # The two programs disagree about the document: a fault, not a fact to read through.
            raise RuntimeError("the stamp reader counted other pages than the envelope reader")
        return [parse_page_stamp(str(zone)) for zone, _has_text in pages]
    if answer.get("unreadable_handle"):
        raise OSError("the upload handle could not be read")
    raise _portal._refusal_for(str(answer.get("refused")))  # noqa: SLF001
