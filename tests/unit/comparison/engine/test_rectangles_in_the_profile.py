"""What the engine gains from rectangles in the profile's vector lines (`CMP-C1-FIX-A` item 8).

`CMP-ENGINE-01` section 9 item 2 and section 11 item 4: a frame drawn as a rectangle was not found (so the margin zones were
absent), and the registration by vector lines had no lines to vote on for a form drawn with rectangles. Real children, pages
drawn with reportlab in ``tmp_path``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from auditmanager.comparison.engine.child.words import detect_frame
from auditmanager.comparison.engine.inputs import _frame_segments

MM = 72 / 25.4
WIDTH, HEIGHT = 842.0, 595.0  # A4 landscape, in points


def sheet(path: Path, *, dx: float = 0.0, dy: float = 0.0, framed: bool = True) -> Path:
    """A form: a grid of cells drawn as stroked rectangles, an inner frame of the sheet, and nothing else (no text, no line)."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(WIDTH, HEIGHT))
    c.translate(dx, dy)
    c.setLineWidth(0.7)
    if framed:
        c.rect(20 * MM, 5 * MM, WIDTH - 25 * MM, HEIGHT - 10 * MM, stroke=1, fill=0)
    for row in range(7):
        for column in range(9):
            if (row * 5 + column * 3) % 4:  # an uneven form, so that no shift of a whole cell agrees with another
                c.rect(90 + column * 70 + (row % 3) * 4, 90 + row * 58, 62, 50, stroke=1, fill=0)
    c.showPage()
    c.save()
    path.write_bytes(buffer.getvalue())
    return path


def test_a_frame_drawn_as_a_rectangle_is_found(tmp_path: Path, corpus_page) -> None:
    page = corpus_page(str(sheet(tmp_path / "framed.pdf")), 1)
    assert len(page.data.lines) >= 4, "the rectangle's edges are in the profile's lines"
    frame = detect_frame(page.data.width_pt, page.data.height_pt, _frame_segments(page.data))
    assert frame is not None
    assert frame == pytest.approx([20 * MM, 5 * MM, WIDTH - 5 * MM, HEIGHT - 5 * MM], abs=0.1), frame


def test_a_page_without_a_frame_has_none(tmp_path: Path, corpus_page) -> None:
    page = corpus_page(str(sheet(tmp_path / "bare.pdf", framed=False)), 1)
    assert detect_frame(page.data.width_pt, page.data.height_pt, _frame_segments(page.data)) is None


def test_a_form_drawn_with_rectangles_is_registered_exactly_by_its_lines(tmp_path: Path, compare) -> None:
    """B is A moved by (3.37, -1.83) pt. The phase correlation of the 36 dpi masks is good to a point or two (a pixel is two
    points); the vote of the rectangle edges is exact to a tenth, which only a page whose rectangles are lines can have."""
    a = sheet(tmp_path / "a.pdf")
    b = sheet(tmp_path / "b.pdf", dx=3.37, dy=-1.83)
    computed = compare(str(a), 1, str(b), 1)
    transform = computed.outcome["result"]["how_compared"]["transform"]
    # B onto A is the opposite shift: B is 3.37 to the right of A and, its y axis pointing up in the PDF, 1.83 lower
    # (the profile's y axis points down, so the lower B is carried up, which is -1.83 there as well)
    assert transform[4] == pytest.approx(-3.37, abs=0.06) and transform[5] == pytest.approx(-1.83, abs=0.06), transform
    assert computed.outcome["status"] in ("same", "same_zones_changed") or computed.outcome["channels"]["geometry"]["diffs"] <= 2
