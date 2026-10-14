"""The upload envelope's PDF work is bounded whatever the PDF holds (`W55B-FIX`, X-1).

`W55B-JUDGE-X` X-1: no archive rule sees the compression *inside* a PDF. A PDF of a few KiB
whose pages share one Flate content stream made PDFium, in the API process and under its
lock, spend 1.8 GB and 4.7 s on every page; with 500 pages that was about 40 minutes of the
lock and an upload slot, and a stream ten times larger would have OOM-killed the API.

Now the PDF is read by a child process (``auditmanager.ingest.pdf_reader``) under an
address-space and a CPU-time ceiling, with a wall clock in the API, and four ceilings give a
typed refusal before the work grows:

* a page's drawing elements (path segments and other objects, into form XObjects) or
  characters -- ``pdf_page_content``;
* the document's drawing elements or characters -- ``pdf_document_content``;
* the reader's memory or time -- ``pdf_reader_limits``.

Each bomb below is refused **by the rule named, within a few seconds, and without the API
process's own memory growing** -- measured as this process's peak resident set, which the
in-process envelope this replaced grew by hundreds of MiB for the smallest of them. A reader
that never starts is the server's fault (a ``RuntimeError``, answered ``500``), never a
refusal of the caller's document. Every expected figure is a literal.

The module needs no database. Every committed fixture and bundle is still admitted (the other
modules of this directory); the corpus and the owner's export were measured for the ceilings
(``docs/program/W55B-FIX.md`` section 4).
"""

from __future__ import annotations

import io
import resource
import sys
import time
import zlib
from pathlib import Path
from typing import Any

import pytest

from auditmanager.ingest import envelope
from auditmanager.ingest.envelope import inspect_pdf
from auditmanager.shared.errors import DomainError


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


MiB = 1024 * 1024


def _pdf(pages: int, content: bytes, *, form: bool = False) -> bytes:
    """``pages`` pages that all draw one shared Flate stream, directly or through one form."""
    packed = zlib.compress(content, 9)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % (6 + i) for i in range(pages))
        + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed) + packed + b"\nendstream",
    ]
    if form:
        page_stream = b"/Fm1 Do"
        objects[3] = (
            b"<< /Type /XObject /Subtype /Form /BBox [0 0 595 842] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Length %d /Filter /FlateDecode >>\nstream\n"
            % len(packed) + packed + b"\nendstream"
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(page_stream) + page_stream + b"\nendstream")
        resources = b"/Resources << /XObject << /Fm1 4 0 R >> >> /Contents 5 0 R"
    else:
        objects.append(b"<< >>")
        resources = b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R"
    for _ in range(pages):
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] " + resources + b" >>")
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


_TEXT = b"BT /F1 9 Tf 10 10 Td (a line of text for the layer, well over fifty characters) Tj ET\n"
#: The judge's text bomb: 500 000 strings of sixteen characters, about 8 M characters a page
#: (the judge's p5 at 8 M: 1.8 GB and 4.7 s a page in the API process).
TEXT_BOMB = b"BT /F1 1 Tf 0 0 Td " + b"(AAAAAAAAAAAAAAAA) Tj " * 500_000 + b"ET"
#: 15 000 strings of sixteen characters: few elements, 240 000 characters on the page.
DENSE_TEXT = b"BT /F1 1 Tf 0 0 Td " + b"(AAAAAAAAAAAAAAAA) Tj " * 15_000 + b"ET"
#: The judge's low-text page: a text line and 40 000 path operators.
PATHS = _TEXT + b"0 0 m 1 1 l S " * 40_000
#: 2 000 strings of PDFium's longest (32 767 characters), each on a line of its own: 65 M
#: characters on one page, whose text no address space the reader may use can hold.
LONG_STRINGS = b"BT /F1 1 Tf " + (b"0 1 Td (" + b"A" * 32_767 + b") Tj ") * 2_000 + b"ET"


def _peak_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _refused(pdf: bytes, *, within: float) -> tuple[str, float]:
    """(the constraint, the seconds it took), and this process's own peak barely moved."""
    before = _peak_mib()
    started = time.monotonic()
    with pytest.raises(DomainError) as refused:
        inspect_pdf(pdf, require_text=False)
    took = time.monotonic() - started
    grew = _peak_mib() - before
    details = dict(refused.value.detail_fields)
    assert details["field"] == "content", details
    assert took < within, f"{details['constraint']} took {took:.1f} s"
    assert grew < 64, f"the API process's own peak grew {grew:.0f} MiB reading the PDF"
    return str(details["constraint"]), took


@pytest.mark.parametrize(
    ("label", "build", "constraint"),
    [
        ("30 pages of the judge's text bomb", lambda: _pdf(30, TEXT_BOMB), "pdf_page_content"),
        ("the text bomb inside a form XObject", lambda: _pdf(30, TEXT_BOMB, form=True), "pdf_page_content"),
        ("a page of 240 000 characters", lambda: _pdf(30, DENSE_TEXT), "pdf_page_content"),
        ("500 pages of the judge's low-text page", lambda: _pdf(500, PATHS), "pdf_document_content"),
        ("a page no address space can hold", lambda: _pdf(1, LONG_STRINGS), "pdf_reader_limits"),
    ],
    ids=["text-bomb", "text-bomb-in-a-form", "dense-text", "paths-on-500-pages", "long-strings"],
)
def test_a_small_pdf_that_would_cost_gigabytes_is_refused_by_its_rule_in_seconds(
    label: str, build: Any, constraint: str
) -> None:
    pdf = build()
    assert len(pdf) < 128 * 1024, f"{label}: {len(pdf)} bytes is not the small PDF it should be"
    found, _took = _refused(pdf, within=20)
    assert found == constraint, label


def test_the_reader_is_stopped_by_its_wall_clock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A reader that is still working when the clock runs out is killed, and the document is
    refused ``pdf_reader_limits``. Shown with a stand-in reader that says ``ready`` and then
    never answers, and a clock of two seconds."""
    stalled = tmp_path / "stalled_reader.py"
    stalled.write_text('import sys, time\nprint("ready", flush=True)\ntime.sleep(600)\n')
    monkeypatch.setattr(envelope, "_READER", stalled)
    monkeypatch.setattr(envelope, "READER_SECONDS", 2)
    started = time.monotonic()
    with pytest.raises(DomainError) as refused:
        inspect_pdf(_pdf(1, _TEXT), require_text=False)
    assert time.monotonic() - started < 10
    assert dict(refused.value.detail_fields)["constraint"] == "pdf_reader_limits"


def test_a_short_clock_stops_a_slow_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """With one second of CPU time and of wall clock, the low-text page on 500 pages -- refused
    by the document ceiling after about two seconds otherwise -- is stopped by the limits."""
    monkeypatch.setattr(envelope, "READER_SECONDS", 1)
    constraint, _took = _refused(_pdf(500, PATHS), within=10)
    assert constraint == "pdf_reader_limits"


def test_a_reader_that_never_starts_is_the_servers_fault_not_the_documents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(envelope, "_READER", tmp_path / "there_is_no_reader.py")
    with pytest.raises(RuntimeError, match="did not start"):
        inspect_pdf(_pdf(1, _TEXT), require_text=False)


def test_the_reader_gets_no_secret_of_the_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The API's environment holds the deployment's secrets; the reader parses hostile bytes."""
    monkeypatch.setenv("AUDITMANAGER_API_TOKEN", "a-secret-the-reader-must-not-see")
    spy = tmp_path / "spy_reader.py"
    spy.write_text(
        "import json, os\n"
        'print("ready", flush=True)\n'
        'leaked = set(os.environ) - {"PATH", "LC_CTYPE"}\n'
        'print(json.dumps({"refused": "page_content" if leaked else "page_count"}), flush=True)\n'
    )
    monkeypatch.setattr(envelope, "_READER", spy)
    with pytest.raises(DomainError) as refused:
        inspect_pdf(_pdf(1, _TEXT), require_text=False)
    assert dict(refused.value.detail_fields)["constraint"] == "1 <= page_count <= 500"


def test_a_real_page_is_read_as_before() -> None:
    """The counts the reader returns are pypdfium2's, read here directly and not by the product."""
    import pypdfium2 as pdfium

    pdf = _pdf(3, _TEXT)
    document = pdfium.PdfDocument(pdf)
    try:
        expected = []
        for index in range(len(document)):
            page = document[index]
            text_page = page.get_textpage()
            expected.append(len(text_page.get_text_range()))
            text_page.close()
            page.close()
    finally:
        document.close()
    facts = inspect_pdf(pdf, require_text=True)
    assert facts.page_count == 3
    assert facts.page_has_layer == (True, True, True)
    assert list(facts.page_characters) == expected and expected[0] > 50


def test_the_ceilings_are_the_recorded_figures() -> None:
    """Written out: the real maxima they were sized from are in the report, not in the code."""
    assert envelope.PAGE_ELEMENTS_MAX == 400_000          # 5 x 75 486, the export's page
    assert envelope.PAGE_CHARACTERS_MAX == 200_000        # 10 x 19 132, the export's page
    assert envelope.DOCUMENT_ELEMENTS_MAX == 8_000_000    # 6 x 1 300 705, a corpus document
    assert envelope.DOCUMENT_CHARACTERS_MAX == 20_000_000  # 10 x 1 892 768, a corpus document
    assert envelope.DOCUMENT_CHARACTERS_MAX * 100 < 2**31  # text_character_count is an integer
    assert envelope.READER_ADDRESS_SPACE == 512 * MiB     # 8 x the 64 MiB every real PDF needs
    assert envelope.READER_SECONDS == 60                  # 20 x the slowest real document
    assert sys.executable, "the reader is started with this interpreter"
