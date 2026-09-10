"""The admission probe: the accepted input envelope, answered before anything is stored.

``P2-META-01``: "an admission probe rejecting, **before any publication**, non-PDF magic
bytes, an encrypted PDF, an oversize file, an over-page-count file and any page without
extractable embedded text, each with ``validation_failed`` and a constraint detail."

The envelope is exactly one unencrypted PDF, at most 25 MiB, between one and thirty
pages, every page carrying extractable embedded text. Anything outside it is a typed
:class:`~auditmanager.shared.errors.DomainError`, and the caller never reaches the
store or the database, so "nothing was published" is true because nothing was attempted.

**OCR is never silently substituted.** A page with no embedded text is a rejection with
a named constraint, not an input to a different extraction path. There is no OCR
dependency in the root lock and this module must never acquire one: the point of the
rule is that a reader can trust that published text came off the page.

Order of the rules
------------------
Cheapest first, and each fixture in ``fixtures/synthetic/ar/negative`` trips exactly one,
so a rejection is attributable to a rule rather than to a coincidence of two:

1. the file name is a plain base name -- no separator, no traversal, no control character;
2. the content is non-empty;
3. the content begins with a PDF header;
4. the content is within the size bound -- checked before any parse, so an oversize file
   is refused without being handed to a parser;
5. the document is not encrypted -- ``pypdf`` answers this before page access, which
   matters because reading pages of an encrypted document raises instead;
6. the page count is within bounds;
7. every page yields extractable text.

A file extension is deliberately **not** a rule. It is a presentation value and a caller
controls it; the magic bytes and the parser decide what the content is, which is the
strictly stronger check. ``not_a_pdf.txt`` and ``companion_archive.zip`` are both refused
on their content at rule 3.
"""

from __future__ import annotations

import hashlib
import io
import re
import warnings
from dataclasses import dataclass
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ACCEPTED_MEDIA_TYPE",
    "MAX_BYTES",
    "MAX_PAGES",
    "MAX_SOURCE_FILENAME",
    "MIN_PAGES",
    "PDF_MAGIC",
    "AdmissionReport",
    "probe",
    "validate_source_filename",
]

#: One unencrypted PDF, at most 25 MiB.
MAX_BYTES: Final[int] = 25 * 1024 * 1024
#: The schema agrees: ``ck_document_version_page_count CHECK (page_count BETWEEN 1 AND 30)``.
MIN_PAGES: Final[int] = 1
MAX_PAGES: Final[int] = 30
ACCEPTED_MEDIA_TYPE: Final[str] = "application/pdf"
PDF_MAGIC: Final[bytes] = b"%PDF-"
MAX_SOURCE_FILENAME: Final[int] = 255

#: A plain base name: no directory separator, no traversal, no control character, no NUL.
_PLAIN_BASENAME: Final[re.Pattern[str]] = re.compile(r"^[^\x00-\x1f/\\]+$")


@dataclass(frozen=True, slots=True)
class AdmissionReport:
    """What the probe established. Facts about content, never about a location."""

    byte_size: int
    sha256: str
    page_count: int
    media_type: str = ACCEPTED_MEDIA_TYPE


def _refuse(field: str, constraint: str, message: str) -> DomainError:
    """Build the one refusal shape this module raises.

    ``message`` is a fixed sentence chosen at the call site below; no caller-supplied
    value is ever interpolated into one, so nothing a client sent can travel back out.
    The envelope screens it anyway -- that screen is the guard, and its passing is
    asserted by this slice's tests rather than assumed.
    """
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message=message, field=field, constraint=constraint
    )


def validate_source_filename(source_filename: str) -> str:
    """Refuse anything that is not a plain base name, without echoing it.

    The uploaded file name is retained for display and is never an identity, never a
    key and never a path this system opens. It is still validated, because a value that
    looks like a path invites a later reader to treat it as one -- ``GJ-01-FC-03``.
    """
    if not isinstance(source_filename, str) or not source_filename.strip():
        raise _refuse(
            "source_filename",
            "non_empty",
            "A source file name is required and must not be blank.",
        )
    candidate = source_filename.strip()
    if len(candidate) > MAX_SOURCE_FILENAME:
        raise _refuse(
            "source_filename",
            f"char_length <= {MAX_SOURCE_FILENAME}",
            "The source file name is longer than the accepted limit.",
        )
    if candidate in (".", "..") or not _PLAIN_BASENAME.match(candidate):
        raise _refuse(
            "source_filename",
            "plain_base_name",
            "The source file name must be a plain base name with no separator, "
            "no traversal segment and no control character.",
        )
    return candidate


def probe(content: bytes, *, source_filename: str) -> AdmissionReport:
    """Answer whether these bytes are inside the accepted envelope.

    Returns the facts a published version records. Raises ``validation_failed`` with a
    ``field`` and a ``constraint`` for anything outside it, having stored nothing,
    contacted no service and opened no transaction.
    """
    validate_source_filename(source_filename)

    if not isinstance(content, (bytes, bytearray)):
        raise _refuse(
            "content", "bytes", "The upload payload must be raw bytes."
        )
    data = bytes(content)

    if not data:
        raise _refuse("content", "non_empty", "The upload payload is empty.")

    if not data.startswith(PDF_MAGIC):
        raise _refuse(
            "content",
            "pdf_magic_bytes",
            "The upload payload does not begin with a PDF header, so it is not a PDF "
            "whatever its name says.",
        )

    if len(data) > MAX_BYTES:
        raise _refuse(
            "content",
            f"byte_size <= {MAX_BYTES}",
            "The upload payload is larger than the accepted envelope allows.",
        )

    page_count = _page_count(data)

    if page_count < MIN_PAGES or page_count > MAX_PAGES:
        raise _refuse(
            "page_count",
            f"{MIN_PAGES} <= page_count <= {MAX_PAGES}",
            "The document carries more pages than the accepted envelope allows, or "
            "carries none at all.",
        )

    _require_text_on_every_page(data)

    return AdmissionReport(
        byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
    )


def _page_count(data: bytes) -> int:
    """Encryption and page count, in that order, from the cheap structural probe.

    ``is_encrypted`` is consulted **before** ``pages``: reading the pages of an encrypted
    document raises ``FileNotDecryptedError``, which would turn an attributable
    "encrypted" refusal into a vague "unparseable" one.
    """
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = PdfReader(io.BytesIO(data), strict=False)
            if reader.is_encrypted:
                raise _refuse(
                    "content",
                    "not_encrypted",
                    "The document is encrypted. This prototype accepts unencrypted "
                    "PDFs only.",
                )
            return len(reader.pages)
    except DomainError:
        raise
    except (PdfReadError, ValueError, OSError, KeyError, TypeError, RecursionError):
        # The parser refused the structure. The exception text can quote raw bytes of
        # the payload, so it is dropped rather than wrapped: `from None`.
        raise _refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be parsed as a PDF document.",
        ) from None


def _require_text_on_every_page(data: bytes) -> None:
    """Every page must yield extractable embedded text. No page is ever sent to OCR."""
    import pdfplumber

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pdfplumber.open(io.BytesIO(data)) as document:
                pages = document.pages
                if not pages:
                    raise _refuse(
                        "page_count",
                        f"{MIN_PAGES} <= page_count <= {MAX_PAGES}",
                        "The document carries no pages.",
                    )
                for page in pages:
                    if not (page.extract_text() or "").strip():
                        raise _refuse(
                            "page_text",
                            "every_page_has_extractable_text",
                            "At least one page carries no extractable embedded text. "
                            "This prototype never substitutes OCR for a text layer.",
                        )
    except DomainError:
        raise
    except Exception:
        raise _refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be read for its text layer.",
        ) from None
