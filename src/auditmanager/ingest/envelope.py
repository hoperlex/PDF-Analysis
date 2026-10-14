"""The PDF rules of the admission envelope, answered before anything is stored.

``P2-META-01``: "an admission probe rejecting, **before any publication**, non-PDF magic
bytes, an encrypted PDF, an oversize file, an over-page-count file and any page without
extractable embedded text, each with ``validation_failed`` and a constraint detail."

The envelope of a PDF is: unencrypted, at most 250 MiB, between one and five hundred
pages (`W55B-INGEST-01`, owner ruling R-116; it was 25 MiB and thirty pages). Anything
outside it is a typed :class:`~auditmanager.shared.errors.DomainError`, and the caller never
reaches the store or the database, so "nothing was published" is true because nothing was
attempted.

Since the last step of `W55B-INGEST-01` the upload is a portal bundle and a bare PDF is
refused before it reaches these rules (``portal_bundle_required``). They judge the PDF
*member* of a bundle (:func:`inspect_pdf`), and a refusal of the member keeps the ``field``,
``constraint`` and message it had when the upload was a bare PDF.

**OCR is always marked, and never substituted.** A page with no embedded text layer is a
rejection with a named constraint, not an input to a different extraction path -- *unless*
the page has at least one portal block (:mod:`auditmanager.ingest.bundle_envelope`), in
which case the recognised text is kept as its own marked artifact and nothing here merges it
into a text layer. Where there is no block for a page, the page must still carry a layer.
There is no OCR dependency in the root lock and this module must never acquire one: the
point of the rule is that a reader can trust that published text came off the page.

A file handle, not a byte string (`W55B-STREAM-01`)
---------------------------------------------------
:func:`inspect_pdf` takes the upload as a **seekable binary handle** -- in the served
application, the temporary file the multipart parser already spooled the part to -- and
never reads it whole. The size is the handle's length, the magic bytes are its first
five, and the structure is read by
``pypdfium2`` **from the handle**, which asks the file for the blocks it needs. A byte
string is still accepted, for the callers that have one; it is wrapped, not copied.

The structure, the encryption flag, the page count and the per-page text presence all come
from ``pypdfium2`` (``pypdf`` and ``pdfplumber`` were used before; the plan measured 18.2 s
for 30 pages against 0.53 s). **Every refusal keeps the ``field``, ``constraint`` and
message it had** -- ``tests/integration/ingest/test_envelope_differential.py`` runs the
committed negatives and generated variants through the previous implementation, kept
there as the oracle, and requires identical payloads.

PDFium runs in a process of its own (`W55B-FIX`, X-1)
-----------------------------------------------------
The structure, the encryption flag, the page count and the per-page text are read by
:mod:`auditmanager.ingest.pdf_reader`, a program this module starts for every PDF and hands
the file as an open descriptor. A PDF is free to make PDFium's work as large as it likes --
a few KiB whose pages share one compressed content stream cost the API gigabytes and minutes
a page (`W55B-JUDGE-X` X-1) -- and nothing inside the API process could bound that. The
reader runs under an address-space ceiling and a CPU-time ceiling the kernel enforces
(:data:`READER_ADDRESS_SPACE`, :data:`READER_SECONDS`), and this module waits for it with a
wall clock of the same length and kills it when that runs out. Four ceilings give a typed
refusal for the documents that stay inside those limits but are no real document's shape
(:data:`PAGE_ELEMENTS_MAX`, :data:`PAGE_CHARACTERS_MAX`, :data:`DOCUMENT_ELEMENTS_MAX`,
:data:`DOCUMENT_CHARACTERS_MAX`), and they bound what the run stages meet in a version the
envelope accepted: the same pages, read by pdfplumber and rendered by PDFium.

**This process never calls PDFium for the envelope, so it never holds** :data:`PDFIUM_LOCK`
**for a document.** The lock is still the process's one PDFium lock: the geometry stage's
renderer takes it per page (``analysis/geometry/render.py``), and with the envelope out of the
process no upload can hold a render up.

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
7. per page, in page order: its drawing elements within :data:`PAGE_ELEMENTS_MAX` and the
   document's within :data:`DOCUMENT_ELEMENTS_MAX`, then its characters within
   :data:`PAGE_CHARACTERS_MAX` and the document's within :data:`DOCUMENT_CHARACTERS_MAX`
   (`W55B-FIX`, X-1); reading the document within the reader's limits
   (``pdf_reader_limits``);
8. every page yields extractable text (``require_text``), or the pages are counted for the bundle
   envelope, which decides the text rule with the portal's blocks in hand.

A file extension is deliberately **not** a rule. It is a presentation value and a caller
controls it; the magic bytes and the parser decide what the content is, which is the
strictly stronger check. ``not_a_pdf.txt`` and ``companion_archive.zip`` are both refused
on their content at rule 3.

The same rules judge the PDF member of a portal bundle (:func:`inspect_pdf`), so a refusal
of the member keeps the ``field``, ``constraint`` and message of a refusal of a bare PDF.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Final

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ACCEPTED_MEDIA_TYPE",
    "DOCUMENT_CHARACTERS_MAX",
    "DOCUMENT_ELEMENTS_MAX",
    "MAX_BYTES",
    "MAX_PAGES",
    "MAX_SOURCE_FILENAME",
    "MIN_PAGES",
    "PAGE_CHARACTERS_MAX",
    "PAGE_ELEMENTS_MAX",
    "PDFIUM_LOCK",
    "PDF_MAGIC",
    "READER_ADDRESS_SPACE",
    "READER_SECONDS",
    "TEXTLESS_PAGE_CHARACTERS",
    "PdfFacts",
    "as_handle",
    "inspect_pdf",
    "page_text_refusal",
    "validate_source_filename",
]

#: One unencrypted PDF, at most 250 MiB (R-116). The whole upload is held to the same figure:
#: the PDF is almost all of a bundle, and the browser pre-check, the API's body cap and the
#: proxy's are set around it (``tests/e2e/test_upload_limit_headroom.py``).
MAX_BYTES: Final[int] = 250 * 1024 * 1024
#: The schema agrees: ``ck_document_version_page_count CHECK (page_count BETWEEN 1 AND 500)``.
MIN_PAGES: Final[int] = 1
MAX_PAGES: Final[int] = 500
#: A page with fewer pypdfium2 characters than this is counted as text-less (the
#: ``textless_pages`` of a version; ``W55B-FREEZE-01``). It is a count of what pypdfium2
#: reads, line breaks included -- not a statement that the page has no text layer.
TEXTLESS_PAGE_CHARACTERS: Final[int] = 50
ACCEPTED_MEDIA_TYPE: Final[str] = "application/pdf"
PDF_MAGIC: Final[bytes] = b"%PDF-"
MAX_SOURCE_FILENAME: Final[int] = 255

#: A plain base name: no directory separator, no traversal, no control character, no NUL.
_PLAIN_BASENAME: Final[re.Pattern[str]] = re.compile(r"^[^\x00-\x1f/\\]+$")

#: PDFium is not thread-safe (pypdfium2's own documentation). Every call into PDFium made in
#: this process is under this lock -- the geometry stage's renderer takes it per page. The
#: envelope makes none: it reads a PDF in a child process (see the module docstring).
PDFIUM_LOCK: Final[threading.Lock] = threading.Lock()

# -- the reader's bounds (`W55B-FIX`, X-1) -----------------------------------------------
#
# A drawing element is a segment of a path or any other page object, counted into form
# XObjects (``pdf_reader._elements``): what pdfplumber pays for when a run reads the page --
# about 1.6 to 2 KiB and 31 to 41 us an element, measured on the owner's export (24 MiB and
# 0.51 s a page) and on `W55B-REHEARSAL-01`'s vector drawing set (23 MiB and 0.46 s a page).
#
# Measured with PDFium, counted as the reader counts, on the 674 PDFs of the norms corpus
# (28 251 pages) and on the owner's portal export (30 pages): at most 75 486 drawing
# elements on a page (the export) and 1 300 705 in a document (the corpus), at most 19 132
# characters on a page (the export) and 1 892 768 in a document (the corpus), at most 0.05 s
# for a page and 2.9 s for a document; every one of those documents is read inside 64 MiB of
# address space. Each ceiling below keeps a margin of at least five over the largest of those
# figures.

#: A page's drawing elements: five times the real maximum (75 486). pdfplumber holds one page
#: at a time (``analysis.stages.extraction``), so this bounds a run's page at about 800 MiB.
PAGE_ELEMENTS_MAX: Final[int] = 400_000
#: A page's characters: ten times the real maximum (19 132). PDFium's text page holds about
#: 220 bytes a character (`W55B-JUDGE-X` p5).
PAGE_CHARACTERS_MAX: Final[int] = 200_000
#: A document's drawing elements: six times the real maximum (1 300 705), above the owner's
#: export carried to 500 pages (about 6.2 M) and `W55B-REHEARSAL-01`'s 500-sheet vector set
#: (7.5 M), so a page of the most complex drawing a ceiling admits cannot be repeated on
#: every one of five hundred pages (one shared content stream did exactly that in
#: `W55B-JUDGE-X` p9). Two pdfplumber passes over it take about 500 to 660 s.
DOCUMENT_ELEMENTS_MAX: Final[int] = 8_000_000
#: A document's characters: ten times the real maximum (1 892 768), and a hundred times under
#: the ``integer`` ``text_character_count`` is stored in (2**31 - 1).
DOCUMENT_CHARACTERS_MAX: Final[int] = 20_000_000
#: The reader's address space: eight times what every real document needs (each of them is
#: read inside 64 MiB, and none inside 48 MiB). Two uploads at once can make the API's host
#: hold at most twice this for their readers, whatever their PDFs do.
READER_ADDRESS_SPACE: Final[int] = 512 * 1024 * 1024
#: The reader's CPU time and the envelope's wall clock for it, in seconds: twenty times the
#: slowest real document (2.9 s). Inside the BFF's 290 s and nginx's 300 s.
READER_SECONDS: Final[int] = 60

#: The program :func:`inspect_pdf` starts, beside this module.
_READER: Final[Path] = Path(__file__).with_name("pdf_reader.py")
#: The reader's environment: nothing of the API's, which holds the deployment's secrets.
_READER_ENVIRONMENT: Final[dict[str, str]] = {"PATH": os.defpath}
#: How much of a handle without a file descriptor is copied at a time.
_COPY_PIECE: Final[int] = 1024 * 1024
#: The reader's first line once its limits are set and PDFium is loaded.
_READY: Final[str] = "ready"


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


@dataclass(frozen=True, slots=True)
class PdfFacts:
    """What reading a PDF established: its size, its page count and what each page holds.

    ``page_characters[i]`` is the number of characters pypdfium2 reads on page ``i + 1``
    (``get_text_range()``, generated line breaks included); ``page_has_layer[i]`` is whether
    that text, stripped, is not empty -- the existing definition of an embedded text layer.
    """

    byte_size: int
    page_count: int
    page_characters: tuple[int, ...]
    page_has_layer: tuple[bool, ...]


def inspect_pdf(content: bytes | bytearray | BinaryIO, *, require_text: bool) -> PdfFacts:
    """The PDF rules, in the order above, for a bare PDF or for the PDF member of a bundle.

    ``require_text=True`` is the bare-PDF rule: the first page without an embedded text
    layer is refused (``every_page_has_extractable_text``) and no page after it is read.
    ``require_text=False`` reads every page and hands the counts back; the bundle envelope
    then decides the text rule with the portal's blocks, which a page may rest on instead of
    a layer. The handle is left positioned at its start.
    """
    handle = as_handle(content)
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
    page_characters, page_has_layer = _inspect_pages(handle, require_text=require_text)
    handle.seek(0)
    return PdfFacts(
        byte_size=size,
        page_count=len(page_characters),
        page_characters=page_characters,
        page_has_layer=page_has_layer,
    )


def as_handle(content: Any) -> BinaryIO:
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


def _inspect_pages(
    handle: BinaryIO, *, require_text: bool
) -> tuple[tuple[int, ...], tuple[bool, ...]]:
    """Encryption, page count and per-page text, in that order, read by the reader process.

    The encryption flag is read as soon as the document opens: a document PDFium cannot
    open without a password is encrypted by that very refusal, and one it opens with an
    empty password still names a security handler. The page count is bounded before any
    page is loaded, so a document over the bound costs one open and no page.
    """
    size = handle.seek(0, os.SEEK_END)
    with _descriptor_of(handle) as descriptor:
        answer = _read_in_a_child(descriptor, size, require_text=require_text)
    handle.seek(0)
    if "pages" in answer:
        pages = answer["pages"]
        return tuple(int(c) for c, _ in pages), tuple(bool(layer) for _, layer in pages)
    if answer.get("unreadable_handle"):
        # The handle itself failed -- the server's fault and not the caller's document.
        raise OSError("the upload handle could not be read")
    raise _refusal_for(str(answer.get("refused")))


@contextlib.contextmanager
def _descriptor_of(handle: BinaryIO) -> Iterator[int]:
    """A descriptor on a regular file holding the handle's bytes, for the reader to inherit.

    A handle on a regular file -- every bundle member, which the archive reader wrote to its
    temporary directory -- is passed as it is. Anything else (a byte string's ``BytesIO``) is
    copied into an anonymous temporary file a piece at a time, with ``readinto`` as PDFium
    read it before, so a handle that fails fails here as itself.
    """
    descriptor = _regular_file_descriptor(handle)
    if descriptor is not None:
        yield descriptor
        return
    with tempfile.TemporaryFile() as spool:
        buffer = bytearray(_COPY_PIECE)
        view = memoryview(buffer)
        handle.seek(0)
        while True:
            count = handle.readinto(view)
            if not count:
                break
            spool.write(view[:count])
        spool.flush()
        yield spool.fileno()


def _regular_file_descriptor(handle: BinaryIO) -> int | None:
    fileno = getattr(handle, "fileno", None)
    if not callable(fileno):
        return None
    try:
        descriptor = int(fileno())
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
    except (OSError, ValueError, io.UnsupportedOperation):
        return None
    flush = getattr(handle, "flush", None)
    if callable(flush):
        flush()
    return descriptor


def _read_in_a_child(descriptor: int, size: int, *, require_text: bool) -> dict[str, Any]:
    """Run :mod:`auditmanager.ingest.pdf_reader` over ``descriptor`` and return its answer.

    A reader that does not say ``ready`` is a server fault (:class:`RuntimeError`): it never
    reached the document. One that said it and then ran out of time, ran out of memory or
    was killed by a signal was stopped by the document: ``pdf_reader_limits``.
    """
    settings = {
        "descriptor": descriptor,
        "size": size,
        "require_text": require_text,
        "min_pages": MIN_PAGES,
        "max_pages": MAX_PAGES,
        "page_elements": PAGE_ELEMENTS_MAX,
        "page_characters": PAGE_CHARACTERS_MAX,
        "document_elements": DOCUMENT_ELEMENTS_MAX,
        "document_characters": DOCUMENT_CHARACTERS_MAX,
        "address_space": READER_ADDRESS_SPACE,
        "cpu_seconds": READER_SECONDS,
    }
    reader = subprocess.Popen(
        [sys.executable, "-I", "-B", str(_READER), json.dumps(settings)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        pass_fds=(descriptor,),
        cwd="/",
        env=_READER_ENVIRONMENT,
    )
    timed_out = False
    try:
        output, _ = reader.communicate(timeout=READER_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        reader.kill()
        output, _ = reader.communicate()
    except BaseException:
        reader.kill()
        reader.wait()
        raise
    lines = output.decode("ascii", errors="replace").splitlines()
    if not lines or lines[0] != _READY:
        raise RuntimeError(
            "the PDF reader process did not start"
            + (" within its time" if timed_out else f" (exit status {reader.returncode})")
        )
    if timed_out or reader.returncode != 0 or len(lines) < 2:
        raise _reader_limits_refusal()
    try:
        answer = json.loads(lines[1])
    except ValueError:
        raise RuntimeError("the PDF reader process answered something else") from None
    if not isinstance(answer, dict):
        raise RuntimeError("the PDF reader process answered something else")
    return answer


def _refusal_for(rule: str) -> DomainError:
    """The envelope's refusal for a rule the reader named. Unknown names are a server fault."""
    if rule == "encrypted":
        return _encrypted()
    if rule == "unparseable":
        # The parser refused the structure. Nothing PDFium said is repeated: it can quote
        # bytes of the payload.
        return _refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be parsed as a PDF document.",
        )
    if rule == "text_unreadable":
        return _refuse(
            "content",
            "parseable_pdf",
            "The upload payload could not be read for its text layer.",
        )
    if rule == "page_count":
        return _page_count_refusal()
    if rule == "page_text":
        return page_text_refusal()
    if rule == "page_content":
        return _refuse(
            "content",
            "pdf_page_content",
            "A page of the document holds more drawing objects or text characters than the "
            "accepted envelope reads.",
        )
    if rule == "document_content":
        return _refuse(
            "content",
            "pdf_document_content",
            "The document holds more drawing objects or text characters in all than the "
            "accepted envelope reads.",
        )
    raise RuntimeError("the PDF reader process named no rule this envelope knows")


def _reader_limits_refusal() -> DomainError:
    return _refuse(
        "content",
        "pdf_reader_limits",
        "Reading the document needed more memory or time than the accepted envelope allows.",
    )


def _encrypted() -> DomainError:
    return _refuse(
        "content",
        "not_encrypted",
        "The document is encrypted. This prototype accepts unencrypted PDFs only.",
    )


def page_text_refusal() -> DomainError:
    """A page the rule refuses: ``every_page_has_extractable_text``, field ``page_text``.

    One sentence for both entries. The bundle's rule is wider -- a page is also fine when it
    has a portal block -- but a page it refuses has no embedded text layer all the same, and
    the sentence says exactly that; it is also what characterization record 21 pinned before
    the bundle existed, and the record stays byte for byte what it was.
    """
    return _refuse(
        "page_text",
        "every_page_has_extractable_text",
        "At least one page carries no extractable embedded text. "
        "This prototype never substitutes OCR for a text layer.",
    )


def _page_count_refusal() -> DomainError:
    return _refuse(
        "page_count",
        f"{MIN_PAGES} <= page_count <= {MAX_PAGES}",
        "The document carries more pages than the accepted envelope allows, or carries "
        "none at all.",
    )
