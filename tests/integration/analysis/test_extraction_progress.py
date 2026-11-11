"""The extraction tells its caller the pages it has read (`RUN-STAGE-PROGRESS-01`).

The geometry stage re-reads the whole document, as long on a large drawing set as the preparation; its pages are
journalled as ``stage.progress`` so that the run's screen shows them. What the caller's callback raises -- a fenced
Attempt, a cancelled run -- leaves the extraction as itself, never as the document's ``source_unreadable``.
"""

from __future__ import annotations

import io

import pytest

from auditmanager.analysis.stages import extraction
from auditmanager.shared.errors import DomainError, ErrorCode

_TEXT = b"BT /F1 9 Tf 10 10 Td (a line of text for the layer, well over fifty characters) Tj ET\n"


def _pdf(pages: int) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % (5 + i) for i in range(pages)) + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(_TEXT) + _TEXT + b"\nendstream",
    ]
    objects += [b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"] * pages
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


def test_the_pages_are_told_in_order_from_none_to_all() -> None:
    told: list[tuple[int, int]] = []
    document = extraction.extract_document(_pdf(3), progress=lambda done, total: told.append((done, total)))
    assert document.page_count == 3
    assert told == [(0, 3), (1, 3), (2, 3), (3, 3)]


def test_without_a_callback_the_extraction_is_what_it_was() -> None:
    assert extraction.extract_document(_pdf(3)) == extraction.extract_document(_pdf(3), progress=lambda done, total: None)


@pytest.mark.parametrize(
    "raised",
    [ValueError("a fault of the caller"), KeyError("authority"),
     DomainError(ErrorCode.CONFLICT, message="the Attempt was superseded")],
    ids=["value-error", "key-error", "domain-error"],
)
def test_what_the_callback_raises_leaves_as_itself(raised: Exception) -> None:
    def fenced(done: int, total: int) -> None:
        if done == 2:
            raise raised

    with pytest.raises(type(raised)) as caught:
        extraction.extract_document(_pdf(3), progress=fenced)
    assert caught.value is raised
    if isinstance(raised, DomainError):
        assert dict(raised.detail_fields).get("reason") != "source_unreadable"
