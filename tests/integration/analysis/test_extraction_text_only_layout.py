"""The run lays a page out without its paths, and reads the same text (`PDF-TEXT-LAYOUT-01`).

`PDF-PAGE-CONTENT-01` (owner, 2026-11-11) admits a page of up to 2 000 000 drawing elements.
pdfplumber built a layout object for every path, about 1.5 KiB a segment, so such a page was
about 3 GiB in the worker's geometry stage and more than the PDF precheck child's 1.5 GiB.
Nothing in the run reads a path from pdfplumber, so
:func:`auditmanager.analysis.stages.extraction.lay_out_text_only` lays the page out with
pdfplumber's own device painting every path to nothing.

Three things are asserted. Every committed PDF extracts to exactly what the full layout gives,
refusals included. A page laid out this way holds its characters and no line, rectangle or
curve. A CAD-like page just under the envelope's ceiling (1 950 001 elements) passes the run's
own PDF precheck under its real limits, and the in-process extraction reads it in a process
capped far under what the full layout needed.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

import pytest

import auditmanager
from auditmanager.analysis.stages import extraction, pdf_precheck

SOURCE_ROOT = Path(auditmanager.__file__).resolve().parents[1]
ROOT = SOURCE_ROOT.parent
COMMITTED_PDFS = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("fixtures", "tests", "docs")
    for path in (ROOT / folder).rglob("*.pdf")
)

_TEXT = b"BT /F1 9 Tf 10 10 Td (a line of text for the layer, well over fifty characters) Tj ET\n"


def _pdf(content: bytes) -> bytes:
    packed = zlib.compress(content, 6)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [5 0 R] /Count 1 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed) + packed + b"\nendstream",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 2384 1684] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>",
    ]
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


def _drawing(paths: int) -> bytes:
    """One text line and ``paths`` short strokes of two segments each, as a CAD sheet draws."""
    return _pdf(_TEXT + b"0.25 w\n" + b"".join(
        b"%d %d m %d %d l S\n" % ((i * 7) % 2300, (i * 13) % 1600, (i * 7) % 2300 + 3, (i * 13) % 1600 + 2)
        for i in range(paths)
    ))


def _outcome(path: str) -> tuple[Any, ...]:
    try:
        return ("extracted", extraction.extract_document(ROOT / path))
    except Exception as exc:  # noqa: BLE001 - the refusal is compared, whatever it is
        return ("raised", type(exc).__name__, dict(getattr(exc, "detail_fields", {})))


def test_the_committed_pdfs_were_found() -> None:
    assert len(COMMITTED_PDFS) >= 40, COMMITTED_PDFS


@pytest.mark.parametrize("path", COMMITTED_PDFS)
def test_a_committed_pdf_extracts_as_the_full_layout_did(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    text_only = _outcome(path)
    monkeypatch.setattr(extraction, "lay_out_text_only", lambda page: None)
    assert _outcome(path) == text_only


def test_a_page_laid_out_text_only_holds_its_characters_and_no_path() -> None:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(_drawing(1_000))) as pdf:
        page = pdf.pages[0]
        assert {"line", "rect", "curve"} & set(page.objects), "the full layout builds the paths"
        page.close()
        extraction.lay_out_text_only(page)
        kinds = set(page.objects)
        assert "char" in kinds and not {"line", "rect", "curve"} & kinds, kinds
        laid_out = page.layout
        extraction.lay_out_text_only(page)
        assert page.layout is laid_out, "a page already laid out is left as it is"


def test_a_page_at_the_envelope_ceiling_passes_the_runs_own_precheck(tmp_path: Path) -> None:
    """1 950 001 elements, under the real `PdfPrecheckLimits` (1.5 GiB): refused
    ``pdf_precheck_limits`` before `PDF-TEXT-LAYOUT-01`; about 20 s on the development host."""
    source = tmp_path / "drawing.pdf"
    source.write_bytes(_drawing(975_000))
    document = pdf_precheck.extract_document(source)
    assert document.page_count == 1
    assert document.pages[0].text.startswith("a line of text for the layer")


_CHILD = r"""
import json, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (int(sys.argv[1]), int(sys.argv[1])))
sys.path.insert(0, sys.argv[2])
from auditmanager.analysis.stages.extraction import extract_document
document = extract_document(sys.argv[3])
peak = next(l for l in open("/proc/self/status") if l.startswith("VmHWM")).split()[1]
print(json.dumps({"pages": document.page_count, "vmhwm_kib": int(peak)}))
"""


def test_the_geometry_stages_extraction_reads_that_page_in_a_small_process(tmp_path: Path) -> None:
    """The geometry stage calls :func:`extraction.extract_document` in the worker itself, with no
    ceiling of its own. Under a 1 GiB address space -- a third of what the full layout needed
    for this page -- it reads the page, and its peak stays under 512 MiB."""
    source = tmp_path / "drawing.pdf"
    source.write_bytes(_drawing(975_000))
    completed = subprocess.run(
        [sys.executable, "-I", "-c", _CHILD, str(1 << 30), str(SOURCE_ROOT), str(source)],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    answer = json.loads(completed.stdout.strip().splitlines()[-1])
    assert answer["pages"] == 1
    assert answer["vmhwm_kib"] < 512 * 1024, answer
