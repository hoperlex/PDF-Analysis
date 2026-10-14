"""The extraction stage holds one page at a time, not the whole document (`W55B-FIX`, X-2).

`W55B-JUDGE-X` X-2: ``extract_document`` kept every pdfplumber page alive until the document
closed. A two-KiB PDF whose pages share one stream of 40 000 path operators cost about
120 MiB *per page* in the worker (215 MiB at one page, 574 MiB at four), so a 500-page
version of it was tens of GiB. A second path to the same growth: pdfminer resolves every
page's content streams when the page list is built and decodes each in place when the page
is read, so a document of large per-page streams kept every decoded stream.

Each case runs ``extract_document`` -- the stage's own path form, over a temporary file -- in
a child process under a hard address-space limit, and reads the child's own peak resident
set (``VmHWM``) after one page and after five. The peak must not grow with the page count.
The figures are the kernel's, of a process that did nothing else; the bound on the growth
(24 MiB) is far under one heavy page and far over the measured noise (0-2 MiB).

Measured with these cases (one page against five) on the code before the repair: +239 MiB for
the paths, +78 MiB for the padded streams. After it: within 2 MiB. Leaving out any one
of the three steps of ``extraction._release`` -- the page's own flush, emptying its content
list, the per-page collection -- or turning pdfminer's document cache back on, keeps the
padded case growing (+64 MiB each).
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

import auditmanager

SOURCE_ROOT = Path(auditmanager.__file__).resolve().parents[1]

#: The address space each child may use: generous for one heavy page, and a hard stop for a
#: regression on a shared host.
CHILD_ADDRESS_SPACE = 2 << 30
#: How much the peak may grow from one page to five. One heavy page below costs ~60 MiB.
MAX_GROWTH_MIB = 24

_CHILD = r"""
import json, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (int(sys.argv[1]), int(sys.argv[1])))
sys.path.insert(0, sys.argv[2])
from auditmanager.analysis.stages.extraction import extract_document
document = extract_document(sys.argv[3])
peak = next(l for l in open("/proc/self/status") if l.startswith("VmHWM")).split()[1]
print(json.dumps({"pages": document.page_count, "vmhwm_kib": int(peak)}))
"""


def _pdf(pages: int, content: bytes, *, shared: bool) -> bytes:
    """A PDF whose pages draw ``content``: one stream for every page, or one stream each."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % (4 + i) for i in range(pages))
        + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    first_stream = 4 + pages
    for index in range(pages):
        stream = first_stream if shared else first_stream + index
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % stream
        )
    for index in range(1 if shared else pages):
        packed = zlib.compress(content + b"\n%% page %d" % index, 9)
        objects.append(
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed)
            + packed
            + b"\nendstream"
        )
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
    out.write(
        b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    )
    return out.getvalue()


_TEXT = b"BT /F1 9 Tf 10 10 Td (a line of text for the layer, well over fifty characters) Tj ET\n"

#: The judge's page: a text line and 20 000 path operators, one stream shared by every page.
PATHS = _TEXT + b"0 0 m 1 1 l S " * 20_000
#: A text line and 16 MiB of whitespace after it, in a stream of each page's own.
PADDED = _TEXT + b" " * (16 << 20)
#: A drawing sheet, as `W55B-REHEARSAL-01`'s vector set draws one (each stroke its own path
#: object), in a stream of each page's own: about 23 MiB a page kept before the repair, the
#: owner's export's mean (24 MiB).
DRAWING = _TEXT + b"".join(
    b"%d %d m %d %d l S\n" % (10 + i % 500, 10 + i // 500 * 50, 40 + i % 500, 10 + i // 500 * 50)
    for i in range(7_500)
)


def _peak_kib(tmp_path: Path, pages: int, content: bytes, *, shared: bool) -> int:
    source = tmp_path / f"document-{pages}.pdf"
    source.write_bytes(_pdf(pages, content, shared=shared))
    completed = subprocess.run(
        [sys.executable, "-I", "-c", _CHILD, str(CHILD_ADDRESS_SPACE), str(SOURCE_ROOT), str(source)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    answer = json.loads(completed.stdout)
    assert answer["pages"] == pages
    return int(answer["vmhwm_kib"])


@pytest.mark.parametrize(
    ("label", "content", "shared"),
    [
        ("paths on one shared stream", PATHS, True),
        ("large streams of their own", PADDED, False),
        ("drawing sheets of their own", DRAWING, False),
    ],
    ids=["shared-paths", "padded-streams", "drawing-sheets"],
)
def test_the_peak_over_five_heavy_pages_is_the_peak_over_one(tmp_path, label, content, shared) -> None:
    one = _peak_kib(tmp_path, 1, content, shared=shared)
    five = _peak_kib(tmp_path, 5, content, shared=shared)
    growth_mib = (five - one) / 1024
    assert growth_mib <= MAX_GROWTH_MIB, (
        f"{label}: the stage's peak grew {growth_mib:.0f} MiB from one page to five "
        f"({one // 1024} MiB to {five // 1024} MiB): it holds pages it has finished reading"
    )


def test_releasing_a_page_keeps_the_text_and_lines_it_read() -> None:
    """The release happens after a page is read, so the result is the one an unreleased read
    gives -- checked on the AR baseline, page by page, against pdfplumber read directly."""
    import pdfplumber

    from auditmanager.analysis.stages.extraction import extract_document

    baseline = (SOURCE_ROOT.parent / "fixtures" / "synthetic" / "ar" / "ar_baseline.pdf").read_bytes()
    document = extract_document(baseline)
    with pdfplumber.open(io.BytesIO(baseline)) as pdf:
        expected = [page.extract_text() or "" for page in pdf.pages]
    assert [page.text for page in document.pages] == expected
    assert all(page.lines for page in document.pages if page.text)
