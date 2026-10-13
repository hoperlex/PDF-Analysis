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

A file handle, not a byte string (`W55B-STREAM-01`)
---------------------------------------------------
:func:`probe` takes the upload as a **seekable binary handle** -- in the served
application, the temporary file the multipart parser already spooled the part to -- and
never reads it whole. The size is the handle's length, the magic bytes are its first
five, the digest is computed over fixed-size chunks, and the structure is read by
``pypdfium2`` **from the handle**, which asks the file for the blocks it needs. A byte
string is still accepted, for the callers that have one; it is wrapped, not copied.

The structure, the encryption flag, the page count and the per-page text presence all come
from ``pypdfium2`` (``pypdf`` and ``pdfplumber`` were used before; the plan measured 18.2 s
for 30 pages against 0.53 s). **Every refusal keeps the ``field``, ``constraint`` and
message it had** -- ``tests/integration/ingest/test_envelope_differential.py`` runs the
committed negatives and generated variants through the previous implementation, kept
there as the oracle, and requires identical payloads.

PDFium is not thread-safe, and the served route runs in a thread pool, so every use of it
here is under :data:`PDFIUM_LOCK`. Anything else in this process that calls ``pypdfium2``
must take the same lock.

Order of the rules
------------------
Cheapest first, and each fixture in ``fixtures/synthetic/ar/negative`` trips exactly one,
so a rejection is attributable to a rule rather than to a coincidence of two:

1. the file name is a plain base name -- no separator, no traversal, no control character;
2. the content is non-empty;
3. the content begins with a PDF header;
4. the content is within the size bound -- checked before any parse, so an oversize file
   is refused without being handed to a parser or hashed;
5. the document is not encrypted -- the security handler is read straight after the
   document opens, before any page is touched;
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
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO, Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ACCEPTED_MEDIA_TYPE",
    "MAX_BYTES",
    "MAX_PAGES",
    "MAX_SOURCE_FILENAME",
    "MIN_PAGES",
    "PDFIUM_LOCK",
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

#: How much of the upload the digest reads at a time. The whole upload is never held.
_DIGEST_CHUNK: Final[int] = 1024 * 1024

#: PDFium is not thread-safe (pypdfium2's own documentation), and the upload route runs in a
#: thread pool where two uploads may be admitted at once. Every call into PDFium made here
#: is under this lock; any other caller of ``pypdfium2`` in the same process must take it.
PDFIUM_LOCK: Final[threading.Lock] = threading.Lock()

#: PDFium's document-load error codes (``FPDF_ERR_*``) that mean "encrypted": ``PASSWORD``
#: (4), a document it cannot open without one, and ``SECURITY`` (5), a security scheme it
#: does not support. Every other code is a structure it could not parse.
_PDFIUM_ENCRYPTED: Final[frozenset[int]] = frozenset({4, 5})


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


def probe(content: bytes | bytearray | BinaryIO, *, source_filename: str) -> AdmissionReport:
    """Answer whether this upload is inside the accepted envelope.

    ``content`` is a seekable binary handle (or a byte string). Returns the facts a
    published version records and leaves a handle positioned at its start, ready to be
    staged. Raises ``validation_failed`` with a ``field`` and a ``constraint`` for anything
    outside the envelope, having stored nothing, contacted no service and opened no
    transaction.
    """
    validate_source_filename(source_filename)

    handle = _handle_of(content)
    size = handle.seek(0, os.SEEK_END)
    handle.seek(0)

    if not size:
        raise _refuse("content", "non_empty", "The upload payload is empty.")

    if handle.read(len(PDF_MAGIC)) != PDF_MAGIC:
        raise _refuse(
            "content",
            "pdf_magic_bytes",
            "The upload payload does not begin with a PDF header, so it is not a PDF "
            "whatever its name says.",
        )

    if size > MAX_BYTES:
        raise _refuse(
            "content",
            f"byte_size <= {MAX_BYTES}",
            "The upload payload is larger than the accepted envelope allows.",
        )

    handle.seek(0)
    page_count = _inspect_pages(handle)

    handle.seek(0)
    digest = hashlib.sha256()
    while chunk := handle.read(_DIGEST_CHUNK):
        digest.update(chunk)
    handle.seek(0)

    return AdmissionReport(
        byte_size=size,
        sha256=digest.hexdigest(),
        page_count=page_count,
    )


def _handle_of(content: Any) -> BinaryIO:
    """The upload as a seekable binary handle, or the one refusal for anything else.

    A byte string is wrapped in :class:`io.BytesIO`, which shares the buffer until it is
    written to, so no second copy exists. A handle must offer what both the digest and
    PDFium ask of it -- ``seek``, ``tell``, ``read`` and ``readinto``.
    """
    if isinstance(content, (bytes, bytearray)):
        return io.BytesIO(bytes(content))
    if all(
        callable(getattr(content, name, None)) for name in ("seek", "tell", "read", "readinto")
    ):
        seekable = getattr(content, "seekable", None)
        if callable(seekable) and not seekable():
            # A programming error in the caller, not a refusal of the caller's upload: the
            # served route always hands over the parser's temporary file.
            raise TypeError("the upload handle must be seekable")
        return content  # type: ignore[no-any-return]
    raise _refuse("content", "bytes", "The upload payload must be raw bytes.")


def _inspect_pages(handle: BinaryIO) -> int:
    """Encryption, page count and per-page text, in that order, read from the handle.

    The encryption flag is read as soon as the document opens: a document PDFium cannot
    open without a password is encrypted by that very refusal, and one it opens with an
    empty password still names a security handler. The page count is bounded before any
    page is loaded, so a document over the bound costs one open and no page.
    """
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_raw

    with PDFIUM_LOCK:
        opened = _open(handle, pdfium_raw)
        if isinstance(opened, DomainError):
            raise opened from None
        document = pdfium.PdfDocument(opened.raw)
        try:
            if pdfium_raw.FPDF_GetSecurityHandlerRevision(document.raw) != -1:
                raise _encrypted()
            page_count = len(document)
            if page_count < MIN_PAGES or page_count > MAX_PAGES:
                raise _page_count_refusal()
            _require_text_on_every_page(document, page_count)
            return page_count
        finally:
            document.close()
            opened.release()


class _Opened:
    """A document PDFium loaded from a handle, and what must outlive it.

    PDFium calls back into Python for each block it reads, so the callback object has to
    stay alive until the document is closed -- it is held here and dropped by
    :meth:`release`.
    """

    __slots__ = ("raw", "_reader", "_failures")

    def __init__(self, raw: Any, reader: Any, failures: list[BaseException]) -> None:
        self.raw = raw
        self._reader = reader
        self._failures = failures

    def release(self) -> None:
        self._reader = None


def _open(handle: BinaryIO, pdfium_raw: Any) -> _Opened | DomainError:
    """Load the document with PDFium's own call, so the failure is read where it happened.

    ``pypdfium2.PdfDocument(handle)`` was not used for the load, for one reason: it reports
    a document that loaded **with no page** as a failure and reads PDFium's *last error*
    for the code, and PDFium sets that error only when a load fails. After an earlier
    upload was refused as encrypted the stale code says "password" for a document that has
    simply no pages. Here a failed load returns no handle and the code read straight after
    it is that load's own; a load that succeeded is never asked for one.
    """
    import ctypes

    size = handle.seek(0, os.SEEK_END)
    handle.seek(0)
    failures: list[BaseException] = []

    def read_block(_param: Any, position: int, buffer: Any, count: int) -> int:
        try:
            view = (ctypes.c_ubyte * count).from_address(ctypes.addressof(buffer.contents))
            handle.seek(position)
            return 1 if handle.readinto(view) == count else 0
        except BaseException as failure:  # noqa: BLE001 - a ctypes callback cannot raise
            failures.append(failure)
            return 0

    reader = pdfium_raw.FPDF_FILEACCESS()
    reader.m_FileLen = size
    reader.m_GetBlock = type(reader.m_GetBlock)(read_block)
    reader.m_Param = None

    raw = pdfium_raw.FPDF_LoadCustomDocument(reader, None)
    if raw:
        return _Opened(raw, reader, failures)

    if failures:
        # The handle itself failed -- the server's fault and not the caller's document.
        raise OSError("the upload handle could not be read") from failures[0]
    code = pdfium_raw.FPDF_GetLastError()
    if code in _PDFIUM_ENCRYPTED:
        return _encrypted()
    # The parser refused the structure. Nothing PDFium said is repeated: it can quote bytes
    # of the payload.
    return _refuse(
        "content",
        "parseable_pdf",
        "The upload payload could not be parsed as a PDF document.",
    )


def _encrypted() -> DomainError:
    return _refuse(
        "content",
        "not_encrypted",
        "The document is encrypted. This prototype accepts unencrypted PDFs only.",
    )


def _page_count_refusal() -> DomainError:
    return _refuse(
        "page_count",
        f"{MIN_PAGES} <= page_count <= {MAX_PAGES}",
        "The document carries more pages than the accepted envelope allows, or carries "
        "none at all.",
    )


def _require_text_on_every_page(document: Any, page_count: int) -> None:
    """Every page must yield extractable embedded text. No page is ever sent to OCR."""
    try:
        for index in range(page_count):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range()
                finally:
                    text_page.close()
            finally:
                page.close()
            if not text.strip():
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
