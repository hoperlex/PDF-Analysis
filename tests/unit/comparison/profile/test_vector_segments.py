"""Rectangles and curves are vector lines of the profile (`CMP-C1-FIX-A` item 8).

`CMP-ENGINE-01` section 11 item 4 and `CMP-SERIES-01` section 9 item 7: the profile kept ``pdfplumber`` lines only, so a frame,
a stamp or a table drawn as rectangles was not in it. The first tests read dictionaries shaped like ``pdfplumber``'s; the
others run the real extraction child on pages drawn with reportlab.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import pytest

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.child import segments
from auditmanager.comparison.profile.profiling import profile_page


def rect(x0: float, top: float, x1: float, bottom: float, *, stroke: bool = False, fill: bool = False, lw: float = 1.0) -> dict[str, Any]:
    return {"x0": x0, "x1": x1, "top": top, "bottom": bottom, "stroke": stroke, "fill": fill, "linewidth": lw,
            "stroking_color": (1.0, 0.0, 0.0), "non_stroking_color": (0.0, 0.0, 1.0)}


def curve(path: list[tuple], *, stroke: bool = True, lw: float = 0.5) -> dict[str, Any]:
    return {"path": path, "stroke": stroke, "fill": not stroke, "linewidth": lw, "stroking_color": (0.0, 0.0, 0.0), "non_stroking_color": 0}


# -- what becomes a segment -------------------------------------------------------------------------------------------------

def test_a_stroked_rectangle_gives_its_four_edges() -> None:
    edges = segments.rectangle_boxes(rect(20, 30, 120, 80, stroke=True))
    assert sorted(edges) == sorted([(20, 30, 120, 30), (20, 80, 120, 80), (20, 30, 20, 80), (120, 30, 120, 80)])


def test_a_stroked_and_filled_rectangle_is_still_a_frame() -> None:
    assert len(segments.rectangle_boxes(rect(0, 0, 50, 50, stroke=True, fill=True))) == 4


def test_a_filled_area_is_not_a_drawn_line() -> None:
    """A page-sized white background would become a frame at the page edge (and so a wrong title-block zone)."""
    assert segments.rectangle_boxes(rect(0, 0, 595, 842, fill=True)) == []
    assert segments.rectangle_boxes(rect(10, 10, 60, 40, fill=True)) == []
    assert segments.rectangle_boxes(rect(10, 10, 60, 40)) == []  # neither stroked nor filled: a clip, nothing drawn


def test_a_rule_drawn_as_a_thin_filled_rectangle_is_one_segment_along_its_long_side() -> None:
    assert segments.rectangle_boxes(rect(50, 100, 250, 100.4, fill=True)) == [(50, 100.2, 250, 100.2)]
    assert segments.rectangle_boxes(rect(150, 80, 150.4, 280, fill=True)) == [(150.2, 80, 150.2, 280)]
    assert segments.rectangle_boxes(rect(50, 100, 51, 101, fill=True)) == []  # a dot


def test_the_straight_steps_of_a_stroked_path_are_segments_and_the_close_is_one() -> None:
    triangle = curve([("m", (20.0, 100.0)), ("l", (80.0, 50.0)), ("l", (120.0, 100.0)), ("h",)])
    assert segments.curve_boxes(triangle) == [(20, 50, 80, 100), (80, 50, 120, 100), (20, 100, 120, 100)]


def test_a_bezier_step_is_not_a_segment_but_the_path_goes_on_from_its_end() -> None:
    arc_then_line = curve([("m", (20.0, 180.0)), ("c", (40.0, 140.0), (80.0, 140.0), (100.0, 180.0)), ("l", (150.0, 180.0))])
    assert segments.curve_boxes(arc_then_line) == [(100, 180, 150, 180)]
    assert segments.curve_boxes(curve([("m", (0.0, 0.0)), ("c", (1.0, 1.0), (2.0, 1.0), (3.0, 0.0))])) == []


def test_a_filled_path_and_a_long_path_are_left_out() -> None:
    area = curve([("m", (0.0, 0.0)), ("l", (50.0, 0.0)), ("l", (50.0, 50.0)), ("h",)], stroke=False)
    assert segments.curve_boxes(area) == []
    figure = curve([("m", (0.0, 0.0))] + [("l", (float(i), float(i % 7))) for i in range(1, 201)])  # a figure of 201 steps
    assert segments.MAX_PATH_STEPS < 200 and segments.curve_boxes(figure) == []
    rule = curve([("m", (0.0, 0.0))] + [("l", (float(i), float(i % 7))) for i in range(1, segments.MAX_PATH_STEPS)])
    assert len(segments.curve_boxes(rule)) == segments.MAX_PATH_STEPS - 1  # the longest path that is still a rule


def test_the_lines_come_first_and_unchanged_then_the_rectangles_then_the_curves() -> None:
    line = {"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 2.0, "linewidth": 0.25, "stroking_color": (0.0, 0.0, 0.0)}
    rows = segments.collect(
        [line], [rect(10, 10, 20, 20, stroke=True, lw=2.0)], [curve([("m", (0.0, 0.0)), ("l", (5.0, 0.0))])],
        lambda x0, top, x1, bottom: [x0, top, x1, bottom], lambda color: color,
    )
    assert rows[0] == [1.0, 2.0, 3.0, 2.0, 0.25, (0.0, 0.0, 0.0)]
    assert [r[:4] for r in rows[1:5]] == [[10, 10, 20, 10], [10, 20, 20, 20], [10, 10, 10, 20], [20, 10, 20, 20]]
    assert rows[1][4:] == [2.0, (1.0, 0.0, 0.0)]  # a stroked rectangle: its line width and stroking colour
    assert rows[5] == [0.0, 0.0, 5.0, 0.0, 0.5, (0.0, 0.0, 0.0)]
    assert len(rows) == 6


def test_a_thin_filled_rule_has_its_thin_side_for_a_width_and_its_fill_colour() -> None:
    rows = segments.collect([], [rect(0, 10, 100, 10.5, fill=True)], [], lambda *b: list(b), lambda color: color)
    assert rows == [[0.0, 10.25, 100.0, 10.25, 0.5, (0.0, 0.0, 1.0)]]


# -- the real extraction child ----------------------------------------------------------------------------------------------

def _page(draw) -> bytes:
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595, 842))
    draw(c)
    c.showPage()
    c.save()
    return buffer.getvalue()


def _profile(tmp_path: Path, runner, data: bytes, name: str = "page.pdf"):
    path = tmp_path / name
    path.write_bytes(data)
    outcome = profile_page(runner, pdf_path=str(path), page_index=0, version_sha256=hashlib.sha256(data).hexdigest())
    assert outcome.status == "ready", outcome.reason
    return outcome


def _lines(outcome) -> list[list[Any]]:
    from auditmanager.comparison.profile.pack import PackReader

    return PackReader(outcome.pack).document()["lines"]


def test_a_frame_a_rule_a_polyline_and_a_line_drawn_on_a_page_are_all_vector_lines(tmp_path: Path, runner) -> None:
    def draw(c) -> None:
        c.setLineWidth(1.5)
        c.rect(56.7, 14.2, 523.0, 813.0, stroke=1, fill=0)  # the frame of a sheet: 20 mm at the left, 5 mm elsewhere
        c.setFillColorRGB(0, 0, 1)
        c.rect(150, 300, 0.4, 200, stroke=0, fill=1)  # a rule of a table drawn as an area
        c.rect(200, 100, 150, 100, stroke=0, fill=1)  # an area: not a line
        path = c.beginPath()
        path.moveTo(100, 600)
        path.lineTo(160, 650)
        path.lineTo(220, 600)
        c.drawPath(path, stroke=1, fill=0)
        c.line(300, 700, 380, 700)

    outcome = _profile(tmp_path, runner, _page(draw))
    lines = _lines(outcome)
    counts = outcome.summary["counts"]
    assert counts["drawn_lines"] == 1 and counts["rects"] == 3
    assert counts["lines"] == len(lines) == 1 + 4 + 1 + 2  # the line, the frame, the rule, the two steps of the polyline
    frame_edges = [l for l in lines if l[4] == 1.5 and l[2] - l[0] > 400 or l[4] == 1.5 and l[3] - l[1] > 600]
    assert len(frame_edges) == 4
    assert lines[0][:4] == [300.0, 142.0, 380.0, 142.0], "the line the profile always kept is the first row, unchanged"
    assert not any(l[2] - l[0] > 500 and l[3] - l[1] > 800 for l in lines), "no edge of a page-sized area"


def test_the_scan_flag_still_counts_what_the_page_draws_not_the_segments_kept(tmp_path: Path, runner) -> None:
    """A scan: images cover the page and it draws at most 20 vector objects. Eight stroked rectangles are eight objects but
    thirty-two segments; they must not turn a scan into a drawing."""
    from reportlab.lib.utils import ImageReader
    from PIL import Image

    def draw(c) -> None:
        image = Image.new("L", (60, 84), 200)
        c.drawImage(ImageReader(image), 0, 0, width=595, height=842)
        for i in range(8):
            c.rect(30 + i * 60, 40, 40, 40, stroke=1, fill=0)

    outcome = _profile(tmp_path, runner, _page(draw))
    counts = outcome.summary["counts"]
    assert counts["rects"] == 8 and counts["lines"] == 32 and counts["drawn_lines"] == 0
    assert outcome.summary["scan"] is True


def test_the_algorithm_version_is_not_the_one_that_kept_lines_only() -> None:
    assert limits.ALGO_VERSION not in ("cmp-profile/1", "cmp-profile/2")


def test_the_corpus_profiles_keep_every_line_they_kept_and_the_counts_agree(vs1_profiles: dict) -> None:
    from auditmanager.comparison.profile.pack import PackReader

    for version, outcomes in vs1_profiles.items():
        for index, outcome in enumerate(outcomes):
            stored = PackReader(outcome.pack).document()["lines"]
            counts = outcome.summary["counts"]
            assert len(stored) == counts["lines"] >= counts["drawn_lines"], (version, index)
