"""A PDF the run's readers cannot read is refused at the upload (`RUN-ROBUSTNESS-01`, D-160).

The envelope reads a PDF with ``pypdfium2``; the run stages read the same stored bytes with
``pypdf`` and ``pdfplumber``, and ``page_geometry_extraction`` then needs PDFium's page count to
equal theirs. PDFium repairs what the others refuse, so a version could be accepted, immutable,
and fail every run (``W55B-JUDGE-Y`` Y-1 (c), ``D-160``; ``test_envelope_differential.py`` had
recorded the leniency as accepted by design). Now a second program
(:mod:`auditmanager.ingest.stage_reader`) asks the stages' questions of every document PDFium
accepts, and a document they cannot answer gets the refusal an unreadable document always had:
``parseable_pdf``.

The fixtures are PDFs written here, byte by byte, from the failure descriptions: each one is
shown, **by the libraries themselves and not by the product under test**, to be a document that
PDFium opens and counts and that the stage's own reader (``extract_document``) fails on or
disagrees about. A fixture that stopped being one -- a library that learned to repair it --
fails its premise test before anything else, so the refusal tests cannot pass vacuously.

The module needs no database and no container.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import pytest

from auditmanager.analysis.stages.extraction import extract_document
from auditmanager.ingest import envelope
from auditmanager.ingest.envelope import inspect_pdf
from auditmanager.shared.errors import DomainError
from tests.integration.ingest.bundle_support import bundle_around, judge

_UNPARSEABLE = "The upload payload could not be parsed as a PDF document."
_TEXT_LAYER = "The upload payload could not be read for its text layer."


@pytest.fixture(scope="session", autouse=True)
def lane_environment() -> None:  # type: ignore[override]
    """Overrides ``conftest.lane_environment``: this module reaches no service."""


@pytest.fixture(autouse=True)
def clean_tables() -> None:  # type: ignore[override]
    """Overrides ``conftest.clean_tables``: there is no database to empty."""


def pdf(
    pages: int = 1,
    *,
    count: int | None = None,
    kids: str | None = None,
    content_filter: bytes = b"",
    stream: bytes | None = None,
) -> bytes:
    """A PDF written by hand with a correct cross-reference table; each argument breaks one thing."""
    kid_list = kids if kids is not None else " ".join(f"{4 + 2 * i} 0 R" for i in range(pages))
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kid_list}] /Count {pages if count is None else count} >>".encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index in range(pages):
        page_id, content_id = 4 + 2 * index, 5 + 2 * index
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % content_id
        )
        body = stream if stream is not None else b"BT /F1 12 Tf 72 700 Td (Hello, run readers) Tj ET"
        objects[content_id] = (
            b"<< /Length %d " % len(body) + content_filter + b">>\nstream\n" + body + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.7\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref)
    return bytes(out)


#: name -> (the document, what the stage's reader does with it, the sentence of the refusal).
#: ``"raises"``: ``extract_document`` fails. ``"counts"``: it succeeds with another page count
#: than PDFium's, which ``page_geometry_extraction`` refuses.
CASES: dict[str, tuple[Callable[[], bytes], str, str]] = {
    "a page tree that lists itself as a kid": (
        lambda: pdf(1, kids="2 0 R 4 0 R"), "raises", _UNPARSEABLE),
    "a page listed twice": (
        lambda: pdf(1, kids="4 0 R 4 0 R"), "raises", _TEXT_LAYER),
    "a content stream with an unknown filter": (
        lambda: pdf(1, content_filter=b"/Filter /NoSuchFilter "), "raises", _TEXT_LAYER),
    "an LZW stream that does not decode": (
        lambda: pdf(1, content_filter=b"/Filter /LZWDecode ", stream=b"\xff\xff\xff"), "raises", _TEXT_LAYER),
    "a page count the page tree does not bear out": (
        lambda: pdf(2, count=1), "counts", _UNPARSEABLE),
}


def _pdfium_pages(data: bytes) -> int:
    """PDFium's page count, read here and not by the product."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        return len(document)
    finally:
        document.close()


def _stage_reads(data: bytes, tmp_path: Path) -> object:
    path = tmp_path / "stored.pdf"
    path.write_bytes(data)
    try:
        return extract_document(path)
    except Exception as failure:  # noqa: BLE001 - the stage's own failure, whatever its type
        return failure


@pytest.mark.parametrize("name", sorted(CASES))
def test_premise_pdfium_reads_the_document_and_the_stages_reader_does_not(
    name: str, tmp_path: Path
) -> None:
    """The fixture is what it claims to be, by the libraries and not by the envelope."""
    build, behaviour, _sentence = CASES[name]
    data = build()
    pdfium_pages = _pdfium_pages(data)
    assert pdfium_pages >= 1, "PDFium must open and count the document"
    stage = _stage_reads(data, tmp_path)
    if behaviour == "raises":
        assert isinstance(stage, Exception), f"the stage's reader read it: {stage!r}"
    else:
        assert not isinstance(stage, Exception), stage
        assert stage.page_count != pdfium_pages, "the stage must count other pages than PDFium"  # type: ignore[attr-defined]


def test_the_control_is_read_by_everyone(tmp_path: Path) -> None:
    data = pdf(3)
    assert _pdfium_pages(data) == 3
    stage = _stage_reads(data, tmp_path)
    assert not isinstance(stage, Exception) and stage.page_count == 3  # type: ignore[attr-defined]
    assert inspect_pdf(data, require_text=True).page_count == 3


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_envelope_refuses_what_the_run_could_not_read(name: str) -> None:
    build, _behaviour, sentence = CASES[name]
    with pytest.raises(DomainError) as refused:
        inspect_pdf(build(), require_text=False)
    assert dict(refused.value.detail_fields) == {"field": "content", "constraint": "parseable_pdf"}
    assert str(refused.value) == sentence


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_bundle_around_such_a_pdf_is_refused_as_its_pdf_member(name: str) -> None:
    """The member is judged first, by the same rules as a bare PDF (the upload's only door)."""
    build, _behaviour, _sentence = CASES[name]
    assert judge(bundle_around(build()))[:2] == ("content", "parseable_pdf")


def test_the_second_reader_is_asked_only_of_a_document_the_first_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A document PDFium refuses never starts the stages' reader: its refusal is PDFium's."""
    monkeypatch.setattr(envelope, "_STAGE_READER", tmp_path / "there_is_no_stage_reader.py")
    with pytest.raises(DomainError) as refused:
        inspect_pdf(b"%PDF-1.7\nnot a document", require_text=False)
    assert dict(refused.value.detail_fields)["constraint"] == "parseable_pdf"


def test_a_stage_reader_that_never_starts_is_the_servers_fault_not_the_documents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(envelope, "_STAGE_READER", tmp_path / "there_is_no_stage_reader.py")
    with pytest.raises(RuntimeError, match="did not start"):
        inspect_pdf(pdf(1), require_text=False)


def test_the_stage_reader_is_stopped_by_its_wall_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A stage reader still working when the clock runs out is killed and the document is
    refused ``pdf_reader_limits`` -- the same answer the first reader gives."""
    stalled = tmp_path / "stalled_stage_reader.py"
    stalled.write_text('import time\nprint("ready", flush=True)\ntime.sleep(600)\n')
    monkeypatch.setattr(envelope, "_STAGE_READER", stalled)
    monkeypatch.setattr(envelope, "READER_SECONDS", 2)
    started = time.monotonic()
    with pytest.raises(DomainError) as refused:
        inspect_pdf(pdf(1), require_text=False)
    assert time.monotonic() - started < 10
    assert dict(refused.value.detail_fields)["constraint"] == "pdf_reader_limits"


def test_the_stage_reader_gets_no_secret_of_the_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AUDITMANAGER_API_TOKEN", "a-secret-the-stage-reader-must-not-see")
    spy = tmp_path / "spy_stage_reader.py"
    spy.write_text(
        "import json, os\n"
        'print("ready", flush=True)\n'
        'leaked = set(os.environ) - {"PATH", "LC_CTYPE"}\n'
        'print(json.dumps({"refused": "encrypted" if leaked else "unparseable"}), flush=True)\n'
    )
    monkeypatch.setattr(envelope, "_STAGE_READER", spy)
    with pytest.raises(DomainError) as refused:
        inspect_pdf(pdf(1), require_text=False)
    assert dict(refused.value.detail_fields)["constraint"] == "parseable_pdf"  # not not_encrypted


def test_a_stage_reader_that_names_no_rule_the_envelope_knows_is_a_server_fault(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    odd = tmp_path / "odd_stage_reader.py"
    odd.write_text('print("ready", flush=True)\nprint(\'{"refused": "something_new"}\', flush=True)\n')
    monkeypatch.setattr(envelope, "_STAGE_READER", odd)
    with pytest.raises(RuntimeError, match="named no rule"):
        inspect_pdf(pdf(1), require_text=False)
