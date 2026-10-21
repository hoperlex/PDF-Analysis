"""The run stages' half of the upload envelope, run as a process of its own.

`RUN-ROBUSTNESS-01`, D-160.

:func:`auditmanager.ingest.envelope.inspect_pdf` reads a PDF with ``pypdfium2``
(:mod:`auditmanager.ingest.pdf_reader`). The run does not: ``source_preparation`` opens the
same stored bytes with ``pypdf`` (the encryption flag and the page count) and then with
``pdfplumber``, and ``page_geometry_extraction`` requires ``pypdfium2``'s page count to equal
the extractor's. The libraries disagree about damaged documents -- PDFium repairs a page tree
or a content stream that ``pypdf`` or ``pdfminer`` refuses -- so a PDF the envelope accepted,
and therefore stored for good, could fail every run that was ever started on it
(`W55B-JUDGE-Y` Y-1 (c), `D-160`).

This program asks the stages' own questions of the upload, in the order the stages ask them,
and nothing more:

1. ``pypdf`` opens the document (:func:`auditmanager.analysis.stages.extraction.probe_envelope`)
   and reports whether it is encrypted and how many pages it has -- ``unparseable`` or
   ``encrypted`` when it cannot;
2. ``pdfplumber`` opens it as ``extract_document`` does, builds its pages and **decodes every
   content stream of every page** (the filter chain, not the page description: what the stage
   cannot read without interpreting the page) -- ``text_unreadable`` when it cannot, or when it
   counts a different number of pages than ``pypdf`` did;
3. the count they agree on equals PDFium's -- ``unparseable`` otherwise.

What it does **not** do is interpret a page: the operators are not run, no text is laid out and
no character is extracted, which is the cost the envelope left ``pdfplumber`` for (18 s for 30
pages against 0.5 s). A failure that only the interpreter meets -- an operator or a font the
layout cannot place -- still reaches a run; ``docs/program/RUN-ROBUSTNESS-01.md`` says so.

It is a program and not a function for the reason :mod:`auditmanager.ingest.pdf_reader` is:
what these libraries do with a hostile file cannot be bounded from inside the API process.
It runs under the same kernel ceilings (an address space and a CPU time), is waited for with
the same wall clock, receives the same open descriptor and a bare environment, imports nothing
of the product, and writes no file. The protocol is the reader's: ``ready``, then one JSON
object -- ``{"readable": true}`` or ``{"refused": "<rule>"}`` -- and the envelope owns every
message.
"""

from __future__ import annotations

import json
import os
import resource
import sys
from typing import Any

READY = "ready"
#: The exit status for a ``MemoryError`` raised in Python code (see ``pdf_reader.EXIT_RESOURCES``).
EXIT_RESOURCES = 3


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


def _stream(descriptor: int) -> Any:
    """The inherited descriptor as a fresh binary stream at its start; it never closes it."""
    stream = os.fdopen(descriptor, "rb", closefd=False)
    stream.seek(0)
    return stream


def _pypdf_pages(descriptor: int) -> int | str:
    """``pypdf``'s page count, or the rule the document breaks (``probe_envelope``'s)."""
    from pypdf import PdfReader

    try:
        with _stream(descriptor) as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted:
                return "encrypted"
            return len(reader.pages)
    except MemoryError:
        raise
    except Exception:  # noqa: BLE001 - whatever pypdf cannot read, the stage cannot
        return "unparseable"


def _pdfplumber_pages(descriptor: int) -> int | None:
    """``pdfplumber``'s page count after every page's content streams decode, or ``None``.

    Opened as ``extract_document`` opens it (pdfminer's object cache off), page by page, each
    page released before the next is read. The decoded bytes are dropped at once.
    """
    import pdfplumber
    from pdfminer.pdftypes import stream_value

    try:
        with _stream(descriptor) as stream, pdfplumber.open(stream) as pdf:
            pdf.doc.caching = False
            pages = pdf.pages
            count = len(pages)
            for page in pages:
                try:
                    for content in page.page_obj.contents:
                        stream_value(content).get_data()
                finally:
                    page.close()
                    page.page_obj.contents = []
            return count
    except MemoryError:
        raise
    except Exception:  # noqa: BLE001 - whatever pdfplumber cannot read, the stage cannot
        return None


def inspect(settings: dict[str, Any]) -> dict[str, Any]:
    """The stages' reads over the descriptor ``settings`` names, in the stages' order."""
    descriptor = int(settings["descriptor"])
    declared = _pypdf_pages(descriptor)
    if isinstance(declared, str):
        return {"refused": declared}
    extracted = _pdfplumber_pages(descriptor)
    if extracted is None:
        return {"refused": "text_unreadable"}
    if extracted != declared:
        # `extract_document`'s own refusal: the extractor and the envelope probe disagree.
        return {"refused": "text_unreadable"}
    if declared != int(settings["page_count"]):
        # `page_geometry_extraction`'s: the renderer and the extractor disagree.
        return {"refused": "unparseable"}
    return {"readable": True}


def main(argv: list[str]) -> int:
    settings = json.loads(argv[1])
    _limit(settings)
    import pdfplumber  # noqa: F401 - loaded before "ready", so a failure here is the server's
    import pypdf  # noqa: F401

    _say(READY)
    try:
        answer = inspect(settings)
    except MemoryError:
        return EXIT_RESOURCES
    _say(json.dumps(answer, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
