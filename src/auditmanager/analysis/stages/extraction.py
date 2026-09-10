"""The pinned text and geometry extraction, and the one place normalization happens.

Read ``P02_SEAMS`` section 4.1 before changing anything here.

The offset rule
---------------
``prepared.text_layer`` defines **one document-global character sequence**: every
page's text concatenated in ascending page order, with **no separator between pages**.
Every offset in this system - evidence anchors, block spans, the grounding gate -
indexes that one sequence.

Offsets are Unicode **code points** after the declared normalization. Not bytes, not
UTF-16 code units. ``text[char_start:char_end]`` on the concatenated sequence is the
definition. There is no ``.encode()`` in this module, and there must never be one: the
corpus is Russian, so every Cyrillic character is two bytes in UTF-8 and a byte offset
would misplace every anchor by a growing amount while still looking entirely plausible
in a test written in English. ``len()`` on a ``str`` counts code points; that is the
only length this module takes.

Normalization is applied **once**, here, and declared in
``text_layer.normalization.id``. No later stage normalizes again, and ``B4``'s
grounding gate compares exactly after this one normalization and nothing else.

Why lines are the block unit
----------------------------
``pdfplumber.Page.extract_text_lines()`` returns the same lines, in the same order,
that ``extract_text()`` joins with ``"\\n"``. Building the page text *from* those lines
therefore yields a text layer and a block index derived from one traversal, so a block
span cannot drift from the text it indexes. :func:`extract_document` asserts the two
agree and refuses the document if they ever do not, rather than publishing a block
index whose spans quietly point at the wrong characters.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Final

from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.shared.errors import DomainError, ErrorCode

#: The declared normalization. Changing this identifier is a new ``artifact_version``.
NORMALIZATION_ID: Final[str] = "nfc_v1"
NORMALIZATION_DESCRIPTION: Final[str] = (
    "Unicode NFC. No case folding, no whitespace collapsing, no punctuation "
    "substitution and no line-ending rewriting beyond the extractor's own output."
)

#: The pinned extractor, per ``docs/program/P02_LOCK.json`` and ``OD-01``.
EXTRACTOR_NAME: Final[str] = "pdfplumber"

#: Extraction options, recorded so ``extractor.options_sha256`` fixes reproducibility.
#: Same bytes plus same extractor plus same options gives the same offsets; a change to
#: any of the three is a new ``artifact_version``.
EXTRACTION_OPTIONS: Final[dict[str, Any]] = {
    "line_source": "extract_text_lines",
    "page_separator": "",
    "line_separator": "\n",
    "normalization": NORMALIZATION_ID,
}


def normalize(text: str) -> str:
    """Apply the one declared normalization. Called exactly once per document."""
    return unicodedata.normalize("NFC", text)


def options_sha256() -> str:
    """Checksum of the canonically serialized extraction options."""
    return sha256_hex(canonical_bytes(EXTRACTION_OPTIONS))


def extractor_version() -> str:
    """The installed pdfplumber version, read rather than restated."""
    from importlib.metadata import version

    return version("pdfplumber")


@dataclass(frozen=True, slots=True)
class ExtractedLine:
    """One extracted line: its text and its geometry, already top-left and rotated."""

    text: str
    x0: float
    top: float
    x1: float
    bottom: float

    #: Dominant font size over the line's characters, used by the context build to
    #: tell a heading from body text. Not published in any artifact.
    size: float


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """One page: its geometry, its normalized text and its lines."""

    page_number: int
    width_pt: float
    height_pt: float
    rotation_deg: int
    text: str
    lines: tuple[ExtractedLine, ...]

    @property
    def char_count(self) -> int:
        """Code points, not bytes. See the module docstring."""
        return len(self.text)


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Every page of one source document, in ascending page order."""

    pages: tuple[ExtractedPage, ...]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def probe_envelope(payload: bytes) -> int:
    """Page count and encryption, answered by ``pypdf`` without parsing content.

    ``OD-01`` requires this probe to be a separate library from the extractor, so an
    extractor that silently returns empty text for an encrypted file cannot be
    mistaken for one that read an empty document.
    """
    import io

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(payload))
    except (PdfReadError, ValueError, OSError) as exc:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the source blob is not a readable PDF document",
            reason="source_unreadable",
        ) from exc

    if reader.is_encrypted:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the source document is encrypted; its content cannot be read and "
                "the stage refuses rather than publishing an empty text layer"
            ),
            reason="source_encrypted",
        )
    try:
        return len(reader.pages)
    except (PdfReadError, ValueError) as exc:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the source document's page tree could not be read",
            reason="source_unreadable",
        ) from exc


def extract_document(payload: bytes) -> ExtractedDocument:
    """Extract every page's normalized text and line geometry, in page order."""
    import io

    import pdfplumber
    from pdfminer.pdfparser import PDFSyntaxError

    declared_pages = probe_envelope(payload)

    pages: list[ExtractedPage] = []
    try:
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            if len(pdf.pages) != declared_pages:
                raise DomainError(
                    ErrorCode.ANALYSIS_INPUT_INVALID,
                    message=(
                        "the extractor and the envelope probe disagree on the page "
                        "count; the stage refuses rather than choosing one"
                    ),
                    reason="page_count_disagreement",
                )
            for ordinal, page in enumerate(pdf.pages, start=1):
                pages.append(_extract_page(page, ordinal))
    except DomainError:
        raise
    except (PDFSyntaxError, ValueError, OSError, KeyError, TypeError) as exc:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the source document's text layer could not be extracted",
            reason="source_unreadable",
        ) from exc

    return ExtractedDocument(pages=tuple(pages))


def _extract_page(page: Any, page_number: int) -> ExtractedPage:
    """Extract one page, cross-checking the line traversal against the page text."""
    raw_lines = page.extract_text_lines()
    joined = "\n".join(line["text"] for line in raw_lines)

    # The cross-check. If pdfplumber's line traversal ever stops agreeing with its
    # own page text, every block span would silently index the wrong characters, so
    # the document is refused instead.
    whole = page.extract_text() or ""
    if joined != whole:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the extractor's line traversal does not reproduce its own page "
                "text; block spans would not index the published text layer"
            ),
            reason="line_traversal_disagreement",
        )

    # Normalization is applied once, to the whole page text, and the lines are
    # normalized by the same call so the two cannot diverge.
    text = normalize(joined)
    lines = tuple(
        ExtractedLine(
            text=normalize(line["text"]),
            x0=float(line["x0"]),
            top=float(line["top"]),
            x1=float(line["x1"]),
            bottom=float(line["bottom"]),
            size=_dominant_size(line.get("chars", ())),
        )
        for line in raw_lines
    )

    # NFC is not guaranteed to preserve the join, so prove it did rather than assume.
    if "\n".join(line.text for line in lines) != text:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "normalization changed the page text and its lines differently; "
                "the stage refuses rather than publishing inconsistent spans"
            ),
            reason="normalization_disagreement",
        )

    return ExtractedPage(
        page_number=page_number,
        width_pt=round(float(page.width), 2),
        height_pt=round(float(page.height), 2),
        rotation_deg=int(page.rotation or 0) % 360,
        text=text,
        lines=lines,
    )


def _dominant_size(chars: Any) -> float:
    """The most common rounded font size on a line; the largest breaks a tie."""
    counts: dict[float, int] = {}
    for char in chars:
        size = round(float(char.get("size", 0.0)), 2)
        counts[size] = counts.get(size, 0) + 1
    if not counts:
        return 0.0
    return max(counts, key=lambda size: (counts[size], size))


__all__ = [
    "EXTRACTION_OPTIONS",
    "EXTRACTOR_NAME",
    "NORMALIZATION_DESCRIPTION",
    "NORMALIZATION_ID",
    "ExtractedDocument",
    "ExtractedLine",
    "ExtractedPage",
    "extract_document",
    "extractor_version",
    "normalize",
    "options_sha256",
    "probe_envelope",
]
