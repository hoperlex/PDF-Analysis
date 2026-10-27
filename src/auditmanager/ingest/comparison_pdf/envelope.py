"""The comparison envelope: the admission rules for a plain PDF that is read for comparison only.

`CMP-INGEST-01`, ADR-0025 decision 11 and the addendum of 2026-10-27 item 3. The portal-bundle envelope
(:mod:`auditmanager.ingest.envelope`) refuses a page of more than 400 000 drawing elements, which is five times
the largest page it was measured on (75 486, the owner's portal export). The real set that `CMP-MEASURE-01A`
measured has a page of **536 426** (``v1.pdf`` p. 7, 2102 x 594 mm; 13 of its 59 pages are above 75 486), so the
portal rule would refuse the very sets this module is for. A comparison upload is read, rendered and extracted
only in ceilinged child processes (decisions 8 and 9), where an overrun is a typed ``RENDER_FAILED`` on that page
and never a crash of the API; so the per-page element limit is the comparison path's own, **set from the
measurement**, and the portal envelope is not touched (it is a different module and a different caller).

========================== ============ ============ ==========================================================
limit                      portal       comparison   basis
========================== ============ ============ ==========================================================
file bytes                 250 MiB      250 MiB      one bound for every PDF the product stores (R-116)
pages                      1 to 500     1 to 500     ``ck_document_version_page_count``
page elements              400 000      **1 000 000** 1.86 times the measured maximum (536 426); the portal figure
                                                      is 5.3 times *its* maximum
page characters            200 000      200 000      unchanged: the real set's text pages are far below it
document elements          8 000 000    8 000 000    unchanged: the real set's heaviest file is about 2.4 M
document characters        20 000 000   20 000 000   unchanged
reader address space       512 MiB      **768 MiB**  decision 8: the scan child of the measurement ran at 768 MiB
reader CPU and wall clock  60 s         **120 s**    a 26-page real file is read in seconds; 500 heavy pages are not
========================== ============ ============ ==========================================================

Every other rule is the portal envelope's, unchanged and in its order: a plain base name for the declared name
(validated where the name is given), a PDF header, the size bound before any parse, no encryption, the page
count, then per page the element and character ceilings. The **text rule is not applied**: a page with no text
layer (a scan, a drawing whose letters are outlines) is admitted and read as an image only, and the proposal says
so (``scan_without_text``); that is the point of «Сравнение версий». The second program the portal path starts
(``stage_reader``, which asks ``pypdf`` and ``pdfplumber`` to open the document the way a *run* will) is not
started: no run reads a comparison-only version, and the comparison's own readers run page by page in the
profile children (`CMP-PROFILE-01`), where a page they cannot read is ``RENDER_FAILED`` on that page.

The program that does the work is the **same** :mod:`auditmanager.ingest.pdf_reader` the portal path starts, run
with these figures; a refusal keeps the field, constraint and message of the portal's own (``_refusal_for``), so
a reviewer reads one wording for one fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, BinaryIO, Final

from auditmanager.ingest import envelope as _portal
from auditmanager.ingest.envelope import PdfFacts
from auditmanager.shared.errors import DomainError

from .child import descriptor_of, run_child

__all__ = [
    "COMPARISON_POLICY",
    "ComparisonEnvelopePolicy",
    "inspect_comparison_pdf",
]


@dataclass(frozen=True, slots=True)
class ComparisonEnvelopePolicy:
    """The figures a comparison admission applies. One instance is the served policy; tests build others."""

    max_bytes: int
    min_pages: int
    max_pages: int
    page_elements: int
    page_characters: int
    document_elements: int
    document_characters: int
    address_space: int
    seconds: int


#: The served policy (see the module docstring for the basis of each figure).
COMPARISON_POLICY: Final[ComparisonEnvelopePolicy] = ComparisonEnvelopePolicy(
    max_bytes=_portal.MAX_BYTES,
    min_pages=_portal.MIN_PAGES,
    max_pages=_portal.MAX_PAGES,
    page_elements=1_000_000,
    page_characters=_portal.PAGE_CHARACTERS_MAX,
    document_elements=_portal.DOCUMENT_ELEMENTS_MAX,
    document_characters=_portal.DOCUMENT_CHARACTERS_MAX,
    address_space=768 * 1024 * 1024,
    seconds=120,
)


def inspect_comparison_pdf(
    content: bytes | bytearray | BinaryIO, *, policy: ComparisonEnvelopePolicy = COMPARISON_POLICY
) -> PdfFacts:
    """The comparison envelope's rules over one PDF; its facts, or the portal's own typed refusal.

    ``content`` is a seekable binary handle (or a byte string). The handle is left positioned at its start, as
    :func:`auditmanager.ingest.envelope.inspect_pdf` leaves it.
    """
    handle = _portal.as_handle(content)
    size = handle.seek(0, 2)
    handle.seek(0)
    if not size:
        raise _portal._refuse("content", "non_empty", "The upload payload is empty.")  # noqa: SLF001
    if handle.read(len(_portal.PDF_MAGIC)) != _portal.PDF_MAGIC:
        raise _portal._refuse(  # noqa: SLF001
            "content",
            "pdf_magic_bytes",
            "The upload payload does not begin with a PDF header, so it is not a PDF whatever its name says.",
        )
    if size > policy.max_bytes:
        raise _portal._refuse(  # noqa: SLF001
            "content",
            f"byte_size <= {policy.max_bytes}",
            "The upload payload is larger than the accepted envelope allows.",
        )
    handle.seek(0)
    with descriptor_of(handle) as descriptor:
        answer = run_child(
            _portal._READER,  # noqa: SLF001
            descriptor,
            {
                "descriptor": descriptor,
                "size": size,
                # No text rule: a page without a layer is read as an image only.
                "require_text": False,
                "min_pages": policy.min_pages,
                "max_pages": policy.max_pages,
                "page_elements": policy.page_elements,
                "page_characters": policy.page_characters,
                "document_elements": policy.document_elements,
                "document_characters": policy.document_characters,
                "address_space": policy.address_space,
                "cpu_seconds": policy.seconds,
            },
            wall_seconds=policy.seconds,
        )
    handle.seek(0)
    return _facts_of(answer, size)


def _facts_of(answer: dict[str, Any], size: int) -> PdfFacts:
    if "pages" in answer:
        pages = answer["pages"]
        return PdfFacts(
            byte_size=size,
            page_count=len(pages),
            page_characters=tuple(int(page[0]) for page in pages),
            page_has_layer=tuple(bool(page[1]) for page in pages),
            page_geometry=tuple((float(page[2]), float(page[3]), int(page[4])) for page in pages),
        )
    if answer.get("unreadable_handle"):
        # The handle itself failed -- the server's fault and not the caller's document.
        raise OSError("the upload handle could not be read")
    raise _refusal(str(answer.get("refused")))


def _refusal(rule: str) -> DomainError:
    return _portal._refusal_for(rule)  # noqa: SLF001
