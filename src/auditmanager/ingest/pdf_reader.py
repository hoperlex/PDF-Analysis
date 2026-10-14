"""The PDF half of the upload envelope, run as a process of its own (`W55B-FIX`, X-1).

:func:`auditmanager.ingest.envelope.inspect_pdf` starts this file as a program --
``python -I -B pdf_reader.py <settings>`` -- hands it the PDF as an open file descriptor and
reads one answer from its standard output. It is a program and not a function because what it
does cannot be bounded from inside the process that asks: PDFium decompresses and parses a
page's content when the page is loaded, so a PDF of a few KiB whose pages share one
compressed content stream made the API process spend gigabytes and minutes per page
(`W55B-JUDGE-X` X-1: 27 KiB, 1.8 GB and 4.7 s per page; with 500 pages about 40 minutes
holding the PDFium lock and an upload slot). Here the work runs under limits the kernel
enforces -- an address-space ceiling and a CPU-time ceiling -- and the API waits for it with a
wall clock. Whatever the document does to this process, the API's memory is untouched and
nothing in the API holds PDFium's lock for it.

**Nothing from the product is imported**, so a crash of PDFium here is a crash of this
process only, and this file depends on the standard library and ``pypdfium2`` alone. It is
started with ``-I``: no environment variable, user site or script directory reaches its
import path. It writes no file (its core size limit is zero) and receives no secret (the API
starts it with a bare environment).

The protocol
------------
* argument 1: the settings, a JSON object written by the envelope (the descriptor, the file's
  size, the text rule and every ceiling);
* stdout, line 1: ``ready`` -- written once the limits are set and ``pypdfium2`` is imported,
  so a process that dies before it is a server fault and one that dies after it was killed by
  the document;
* stdout, line 2: the answer, one JSON object: ``{"pages": [[characters, has_layer], ...]}``,
  ``{"refused": "<rule>"}`` or ``{"unreadable_handle": true}``.

The rules are the envelope's, in its order (:mod:`auditmanager.ingest.envelope`): the
document loads, it is not encrypted, its page count is within bounds, and then per page --
its drawing objects, counted into form XObjects, within the page ceiling and the document's;
its characters within the page ceiling, read only after the count says so; the document's
characters within their ceiling; and, for a bare PDF, a text layer. ``refused`` names the
rule; the envelope owns every message.
"""

from __future__ import annotations

import json
import os
import resource
import sys
from typing import Any

READY = "ready"
#: The exit status for a ``MemoryError`` raised in Python code: the address-space ceiling was
#: met. A ceiling met inside PDFium ends the process by a signal instead; both are the same
#: answer to the envelope.
EXIT_RESOURCES = 3

#: PDFium's document-load error codes that mean "encrypted" (``FPDF_ERR_PASSWORD``,
#: ``FPDF_ERR_SECURITY``); every other code is a structure it could not parse.
_ENCRYPTED_LOAD_ERRORS = frozenset({4, 5})


def _limit(settings: dict[str, Any]) -> None:
    """The kernel's ceilings on this process, set before anything else is loaded."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    address_space = int(settings["address_space"])
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    cpu_seconds = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))


def _say(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _open(descriptor: int, size: int, raw: Any) -> tuple[Any, Any] | dict[str, Any]:
    """Load the document with PDFium's own call, reading the descriptor block by block.

    A failed load returns no handle, and the error code read straight after it is that load's
    own: a fresh process has no earlier load whose error could be borrowed.
    """
    import ctypes

    failures: list[BaseException] = []

    def read_block(_param: Any, position: int, buffer: Any, count: int) -> int:
        try:
            data = os.pread(descriptor, count, position)
            if len(data) != count:
                return 0
            ctypes.memmove(buffer, data, count)
            return 1
        except BaseException as failure:  # noqa: BLE001 - a ctypes callback cannot raise
            failures.append(failure)
            return 0

    reader = raw.FPDF_FILEACCESS()
    reader.m_FileLen = size
    reader.m_GetBlock = type(reader.m_GetBlock)(read_block)
    reader.m_Param = None
    document = raw.FPDF_LoadCustomDocument(reader, None)
    if document:
        return document, (reader, failures)
    if failures:
        return {"unreadable_handle": True}
    if raw.FPDF_GetLastError() in _ENCRYPTED_LOAD_ERRORS:
        return {"refused": "encrypted"}
    return {"refused": "unparseable"}


def _objects(raw: Any, page: Any, ceiling: int) -> int:
    """The page's drawing objects, those inside form XObjects included, up to ``ceiling`` + 1.

    PDFium counts a form XObject as one object of the page, but parses everything inside it,
    and so does every later reader of the page; a page that wraps a million paths in one form
    is a page of a million objects.
    """
    total = 0
    pending: list[tuple[Any, bool]] = [(page, False)]
    while pending:
        container, is_form = pending.pop()
        count = (raw.FPDFFormObj_CountObjects if is_form else raw.FPDFPage_CountObjects)(container)
        total += max(count, 0)
        if total > ceiling:
            return total
        get = raw.FPDFFormObj_GetObject if is_form else raw.FPDFPage_GetObject
        for index in range(max(count, 0)):
            child = get(container, index)
            if child and raw.FPDFPageObj_GetType(child) == raw.FPDF_PAGEOBJ_FORM:
                pending.append((child, True))
    return total


def _pages(document: Any, raw: Any, page_count: int, settings: dict[str, Any]) -> dict[str, Any]:
    """Every page's characters and layer, or the first rule a page breaks."""
    require_text = bool(settings["require_text"])
    page_objects = int(settings["page_objects"])
    page_characters = int(settings["page_characters"])
    document_objects = int(settings["document_objects"])
    document_characters = int(settings["document_characters"])
    pages: list[list[Any]] = []
    objects_in_all = 0
    characters_in_all = 0
    try:
        for index in range(page_count):
            page = document[index]
            try:
                objects = _objects(raw, page.raw, page_objects)
                if objects > page_objects:
                    return {"refused": "page_content"}
                objects_in_all += objects
                if objects_in_all > document_objects:
                    return {"refused": "document_content"}
                text_page = page.get_textpage()
                try:
                    if text_page.count_chars() > page_characters:
                        return {"refused": "page_content"}
                    text = text_page.get_text_range()
                finally:
                    text_page.close()
            finally:
                page.close()
            characters_in_all += len(text)
            if characters_in_all > document_characters:
                return {"refused": "document_content"}
            has_layer = bool(text.strip())
            if require_text and not has_layer:
                return {"refused": "page_text"}
            pages.append([len(text), has_layer])
    except MemoryError:
        raise
    except Exception:  # noqa: BLE001 - a page PDFium cannot read is the document's fault
        return {"refused": "text_unreadable"}
    return {"pages": pages}


def inspect(settings: dict[str, Any]) -> dict[str, Any]:
    """The envelope's PDF rules over the descriptor ``settings`` names."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    opened = _open(int(settings["descriptor"]), int(settings["size"]), raw)
    if isinstance(opened, dict):
        return opened
    loaded, keep_alive = opened
    document = pdfium.PdfDocument(loaded)
    try:
        if raw.FPDF_GetSecurityHandlerRevision(document.raw) != -1:
            return {"refused": "encrypted"}
        page_count = len(document)
        if not int(settings["min_pages"]) <= page_count <= int(settings["max_pages"]):
            return {"refused": "page_count"}
        answer = _pages(document, raw, page_count, settings)
        if keep_alive[1]:
            # The descriptor failed under PDFium mid-read: the server's file, not the caller's
            # document, whatever PDFium made of the short block.
            return {"unreadable_handle": True}
        return answer
    finally:
        document.close()
        del keep_alive


def main(argv: list[str]) -> int:
    settings = json.loads(argv[1])
    _limit(settings)
    import pypdfium2  # noqa: F401 - loaded before "ready", so a failure here is the server's

    _say(READY)
    try:
        answer = inspect(settings)
    except MemoryError:
        return EXIT_RESOURCES
    _say(json.dumps(answer, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
