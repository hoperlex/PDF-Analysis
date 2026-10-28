"""The PDF half of the stamp reader, run as a process of its own (ADR-0025 decisions 8 and 9).

:func:`auditmanager.ingest.comparison_pdf.reading.read_pdf` starts this file as a program --
``python -I -B stamp_reader.py <settings>`` -- hands it the PDF as an open file descriptor and reads one answer from
its standard output. It is the same discipline as :mod:`auditmanager.ingest.pdf_reader`, for the same reason: what
PDFium does with a hostile page cannot be bounded from inside the API process, so the work runs under limits the
kernel enforces (an address-space ceiling and a CPU-time ceiling) and the API waits for it with a wall clock.

**Nothing from the product is imported**: this file depends on the standard library and ``pypdfium2`` alone, so a
crash of PDFium here is a crash of this process only. It writes no file and receives no secret.

What it reads: for every page, the text that lies in the lower-right corner of the page **as it is displayed**
(``zone_width_pt`` x ``zone_height_pt``, the original's 205 x 70 mm), whatever the page's ``/Rotate`` and
``/CropBox`` say. A title block is there; the parsing of its text into facts is
:mod:`auditmanager.ingest.comparison_pdf.stamp`, which is plain Python and has no PDFium in it.

The protocol
------------
* argument 1: the settings, a JSON object (the descriptor, the file's size and the four bounds);
* stdout, line 1: ``ready`` once the limits are set and ``pypdfium2`` is imported, so a process that dies before it is a
  server fault and one that dies after it was stopped by the document;
* stdout, line 2: ``{"pages": [[zone_text, page_has_text], ...]}`` or ``{"refused": "<rule>"}``
  (``encrypted``, ``unparseable`` or ``text_unreadable``).
"""

from __future__ import annotations

import json
import os
import resource
import sys
from typing import Any

READY = "ready"
EXIT_RESOURCES = 3
_ENCRYPTED_LOAD_ERRORS = frozenset({4, 5})


def _limit(settings: dict[str, Any]) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    address_space = int(settings["address_space"])
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    cpu_seconds = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))


def _say(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _open(descriptor: int, size: int, raw: Any) -> tuple[Any, Any] | dict[str, Any]:
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


def displayed_box(page: Any) -> tuple[float, float, float, float, int]:
    """``(left, bottom, right, top, rotation)`` of the page's visible area, in the page's own (native) space.

    The CropBox clipped to the MediaBox, exactly as :func:`auditmanager.ingest.pdf_reader._displayed` reads it for
    the width and height; here the origin is kept because the zone is asked for in native coordinates.
    """
    crop = page.get_cropbox()
    media = page.get_mediabox()
    rotation = int(page.get_rotation())
    if rotation % 90 != 0:
        raise ValueError("a page rotation is a multiple of 90 degrees")
    rotation %= 360
    left = max(min(crop[0], crop[2]), min(media[0], media[2]))
    bottom = max(min(crop[1], crop[3]), min(media[1], media[3]))
    right = max(left, min(max(crop[0], crop[2]), max(media[0], media[2])))
    top = max(bottom, min(max(crop[1], crop[3]), max(media[1], media[3])))
    return left, bottom, right, top, rotation


def native_zone(
    box: tuple[float, float, float, float, int], zone_width: float, zone_height: float
) -> tuple[float, float, float, float]:
    """The lower-right ``zone_width`` x ``zone_height`` corner of the **displayed** page, as ``(l, b, r, t)`` in
    native space. A quarter-turn ``/Rotate`` moves that corner to another corner of the unrotated page:

    ======= =========================== ==============================================
    rotate  the displayed lower-right is  the native rectangle
    ======= =========================== ==============================================
    0       lower-right                  x in [R - w, R], y in [B, B + h]
    90      upper-right                  x in [R - h, R], y in [T - w, T]
    180     upper-left                   x in [L, L + w], y in [T - h, T]
    270     lower-left                   x in [L, L + h], y in [B, B + w]
    ======= =========================== ==============================================
    """
    left, bottom, right, top, rotation = box
    if rotation == 0:
        return max(left, right - zone_width), bottom, right, min(top, bottom + zone_height)
    if rotation == 90:
        return max(left, right - zone_height), max(bottom, top - zone_width), right, top
    if rotation == 180:
        return left, max(bottom, top - zone_height), min(right, left + zone_width), top
    return left, bottom, min(right, left + zone_height), min(top, bottom + zone_width)


def _pages(document: Any, page_count: int, settings: dict[str, Any]) -> dict[str, Any]:
    zone_width = float(settings["zone_width_pt"])
    zone_height = float(settings["zone_height_pt"])
    limit = int(settings["zone_characters"])
    answers: list[list[Any]] = []
    try:
        for index in range(page_count):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    has_text = text_page.count_chars() > 0
                    left, bottom, right, top = native_zone(displayed_box(page), zone_width, zone_height)
                    zone = text_page.get_text_bounded(left, bottom, right, top) if has_text else ""
                finally:
                    text_page.close()
            finally:
                page.close()
            answers.append([zone[:limit], has_text])
    except MemoryError:
        raise
    except Exception:  # noqa: BLE001 - a page PDFium cannot read is the document's fault
        return {"refused": "text_unreadable"}
    return {"pages": answers}


def read(settings: dict[str, Any]) -> dict[str, Any]:
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
        answer = _pages(document, page_count, settings)
        if keep_alive[1]:
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
        answer = read(settings)
    except MemoryError:
        return EXIT_RESOURCES
    _say(json.dumps(answer, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
