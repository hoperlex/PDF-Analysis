"""A page over the pixel cap is refused, never rendered (`CMP-PROFILE-01`, ADR-0025 decision 9).

Three layers hold the line and each is tested where it can fail on its own: the child refuses before it opens a
bitmap (so no file is written and no memory is spent), the page profile then runs **no other child** for that
page and stores a ``refused`` / ``PAGE_TOO_LARGE`` row, and the full-page renderer exported from
``analysis.public`` refuses at its own cap before PDFium allocates anything. A page just inside the cap is
rendered, at the dpi the rule gives, inside the 768 MiB ceiling.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pypdf import PdfWriter

from auditmanager.analysis.public import FULL_PAGE_MAX_PIXELS, PdfiumDocument, page_raster_size
from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.profiling import profile_page
from auditmanager.comparison.profile.runner import ChildResult, SubprocessChildRunner
from auditmanager.shared.errors import DomainError, ErrorCode


def _blank(tmp_path: Path, width: float, height: float, name: str = "blank.pdf") -> str:
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    path = tmp_path / name
    with open(path, "wb") as sink:
        writer.write(sink)
    return str(path)


class _Counting:
    """A runner that records which modes were started and delegates to the real one."""

    def __init__(self) -> None:
        self.modes: list[str] = []
        self._real = SubprocessChildRunner()

    def run(self, settings, child_limits) -> ChildResult:
        self.modes.append(settings["mode"])
        return self._real.run(settings, child_limits)


def test_the_child_refuses_a_page_over_the_cap_before_it_renders_anything(tmp_path: Path) -> None:
    pdf = _blank(tmp_path, 12000, 12000)
    out = tmp_path / "out"
    out.mkdir()
    result = SubprocessChildRunner().run(
        {"mode": "render", "pdf": pdf, "page": 0, "out_dir": str(out), **limits.render_settings()},
        limits.RENDER_LIMITS,
    )
    assert result.status == "refused" and result.answered and not result.ok
    assert result.facts["reason"] == limits.REASON_PAGE_TOO_LARGE
    assert (result.facts["width_pt"], result.facts["height_pt"]) == (12000.0, 12000.0)
    assert os.listdir(out) == [], "nothing was rendered, encoded or written"
    # ... and it never got near the ceiling: a 144 Mpx RGBX bitmap alone is 576 MB.
    assert result.facts["vm_peak_kib"] < 250 * 1024


def test_a_refused_page_starts_no_other_child_and_is_stored_refused(tmp_path: Path) -> None:
    runner = _Counting()
    outcome = profile_page(runner, pdf_path=_blank(tmp_path, 12000, 12000), page_index=0, version_sha256="4" * 64)
    assert runner.modes == ["render"], "the extraction child is not started for a refused page"
    assert (outcome.status, outcome.reason) == ("refused", limits.REASON_PAGE_TOO_LARGE)
    assert outcome.pack is None and outcome.preview is None and outcome.thumbnail is None
    assert outcome.summary["width_pt"] == 12000.0 and outcome.summary["refusal"] == {"pixel_cap": 40_000_000, "min_dpi": 72}
    assert len(outcome.content_key) == 64


def test_the_pixel_cap_is_the_one_the_ceilings_were_sized_for() -> None:
    assert limits.PIXEL_CAP == 40_000_000 == FULL_PAGE_MAX_PIXELS


def test_a_page_just_inside_the_cap_is_rendered_at_the_dpi_the_rule_gives(tmp_path: Path) -> None:
    # 6000 x 6000 pt: floor(sqrt(40e6 / 83.33^2)) = 75 dpi, 6250 x 6250 = 39.06 Mpx.
    outcome = profile_page(SubprocessChildRunner(), pdf_path=_blank(tmp_path, 6000, 6000), page_index=0, version_sha256="5" * 64)
    assert outcome.status == "ready", outcome.summary
    raster = outcome.summary["raster"]
    assert raster == {"dpi": 75, "width_px": 6250, "height_px": 6250}
    assert raster["width_px"] * raster["height_px"] <= limits.PIXEL_CAP
    assert outcome.timings["render"]["vm_peak_kib"] < 768 * 1024, "inside the render ceiling at the cap"
    assert outcome.summary["tiles"]["levels"][0]["columns"] == 13
    assert outcome.summary["ink"]["ratio"] == 0.0 and outcome.summary["scan"] is False


def test_the_exported_full_page_renderer_holds_its_own_cap(tmp_path: Path) -> None:
    pdf = _blank(tmp_path, 595, 842, "a4.pdf")
    with PdfiumDocument(pdf, stage_id="test") as document:
        with pytest.raises(DomainError) as raised:
            document.render_page(1, dpi=200, max_pixels=1_000_000)
        assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
        assert raised.value.detail_fields == {"stage_id": "test", "reason": "page_pixel_cap"}
        image = document.render_page(1, dpi=72)
        assert image.size == page_raster_size(595, 842, 72) == (595, 842) and image.mode == "RGB"
    huge = _blank(tmp_path, 12000, 12000, "huge.pdf")
    with PdfiumDocument(huge, stage_id="test") as document:
        with pytest.raises(DomainError) as raised:
            document.render_page(1, dpi=72)  # 144 Mpx at one pixel to the point
        assert raised.value.detail_fields["reason"] == "page_pixel_cap"
