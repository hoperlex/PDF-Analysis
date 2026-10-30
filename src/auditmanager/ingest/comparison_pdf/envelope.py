"""Validate a plain comparison PDF before any version is published.

The temporary statistics intake raises numeric size, page, text, drawing,
reader-memory and reader-time ceilings to representation limits. PDF magic,
encryption, parseability and immutable facts are still checked. The original
ADR-0025 policy values are preserved in its decision record for rollback.
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
    page_elements=2**63 - 1,
    page_characters=_portal.PAGE_CHARACTERS_MAX,
    document_elements=_portal.DOCUMENT_ELEMENTS_MAX,
    document_characters=_portal.DOCUMENT_CHARACTERS_MAX,
    address_space=2**63 - 1,
    seconds=2**31 - 1,
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
