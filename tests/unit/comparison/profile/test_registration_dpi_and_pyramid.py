"""The registration dpi rule and the tile pyramid (`CMP-PROFILE-01`, ADR-0025 decision 9 and its addendum).

The rule is ``min(200, floor(sqrt(40e6 / (w_in * h_in))))`` lowered while the raster PDFium really allocates
is over the cap, and a page under 72 dpi is refused. The worked cases are the ones the measurement reported
(``MEASURE-RENDER-01`` finding 7): 1682 x 1189 mm at 113 dpi, 2102 x 594 mm at 143 dpi, an A1 sheet at 200.
"""

from __future__ import annotations

import math

import pytest

from auditmanager.comparison.profile import limits
from auditmanager.comparison.profile.child import geometry

MM = 72.0 / 25.4


def _dpi(width_mm: float, height_mm: float) -> int | None:
    return limits.registration_dpi(
        width_mm * MM,
        height_mm * MM,
        pixel_cap=limits.PIXEL_CAP,
        max_dpi=limits.MAX_REGISTRATION_DPI,
        min_dpi=limits.MIN_REGISTRATION_DPI,
    )


@pytest.mark.parametrize(
    ("width_mm", "height_mm", "expected"),
    [
        (210, 297, 200),  # A4
        (297, 420, 200),  # A3
        (594, 841, 200),  # A1: 30.98 Mpx at 200 dpi, under the cap
        (1682, 1189, 113),  # 2A0, the measurement's worst page: 39.6 Mpx
        (2102, 594, 143),  # the real set's long page
    ],
)
def test_the_rule_gives_the_measured_dpi(width_mm: float, height_mm: float, expected: int) -> None:
    assert _dpi(width_mm, height_mm) == expected


@pytest.mark.parametrize("width_mm", [250, 700, 1500, 1682, 2102, 2200])
@pytest.mark.parametrize("height_mm", [297, 594, 1189, 2000])
def test_the_raster_is_under_the_cap_and_one_dpi_more_is_not(width_mm: float, height_mm: float) -> None:
    width_pt, height_pt = width_mm * MM, height_mm * MM
    dpi = _dpi(width_mm, height_mm)
    if dpi is None:
        # Refused: even the minimum dpi is over the cap.
        w, h = geometry.raster_size(width_pt, height_pt, limits.MIN_REGISTRATION_DPI)
        assert w * h > limits.PIXEL_CAP
        return
    w, h = geometry.raster_size(width_pt, height_pt, dpi)
    assert w * h <= limits.PIXEL_CAP
    assert limits.MIN_REGISTRATION_DPI <= dpi <= limits.MAX_REGISTRATION_DPI
    if dpi < limits.MAX_REGISTRATION_DPI:
        w2, h2 = geometry.raster_size(width_pt, height_pt, dpi + 1)
        assert w2 * h2 > limits.PIXEL_CAP, "a higher dpi would still fit: the rule is not the largest"


def test_a_page_that_cannot_be_kept_under_the_cap_is_refused_not_lowered() -> None:
    # 12000 x 12000 pt (the PDF's own limit is 14400): 144 Mpt^2, 5.2 times the cap at 72 dpi.
    assert limits.registration_dpi(12000, 12000, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72) is None
    # Just inside: 6300 x 6300 pt at 72 dpi is 39.69 Mpx.
    assert limits.registration_dpi(6300, 6300, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72) == 72
    # One pt more on a side and the 72 dpi raster is over the cap.
    assert limits.registration_dpi(6330, 6330, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72) is None


@pytest.mark.parametrize("bad", [0, -5, math.nan, math.inf, None, "10"])
def test_a_page_without_a_usable_size_has_no_dpi(bad: object) -> None:
    assert limits.registration_dpi(bad, 100, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72) is None  # type: ignore[arg-type]
    assert limits.registration_dpi(100, bad, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72) is None  # type: ignore[arg-type]


def test_the_ceil_of_the_raster_is_inside_the_cap_check() -> None:
    """3004.2 x 2253.52 pt: floor(sqrt(cap / area)) is 175 dpi, but PDFium rounds each side of the raster up
    and 175 dpi is then 40 000 356 pixels, over the cap; the rule goes down one step."""
    width_pt, height_pt = 3004.2, 2253.52
    plain = min(200, math.floor(math.sqrt(limits.PIXEL_CAP / ((width_pt / 72) * (height_pt / 72)))))
    assert plain == 175
    w, h = geometry.raster_size(width_pt, height_pt, plain)
    assert (w, h, w * h) == (7302, 5478, 40_000_356)
    got = limits.registration_dpi(width_pt, height_pt, pixel_cap=limits.PIXEL_CAP, max_dpi=200, min_dpi=72)
    assert got == 174
    w, h = geometry.raster_size(width_pt, height_pt, got)
    assert w * h <= limits.PIXEL_CAP


def test_the_a1_pyramid_matches_what_the_child_cuts() -> None:
    levels = geometry.pyramid_levels(6623, 4678, limits.TILE_PX)
    assert [(lv.level, lv.width_px, lv.height_px, lv.columns, lv.rows) for lv in levels] == [
        (0, 6623, 4678, 13, 10),
        (1, 3312, 2339, 7, 5),
        (2, 1656, 1170, 4, 3),
        (3, 828, 585, 2, 2),
        (4, 414, 293, 1, 1),
    ]
    assert geometry.tile_box(levels[2], 3, 2, limits.TILE_PX) == (1536, 1024, 1656, 1170)
    assert geometry.tile_box(levels[2], 4, 0, limits.TILE_PX) is None
    assert geometry.tile_box(levels[2], 0, -1, limits.TILE_PX) is None


def test_a_page_smaller_than_one_tile_has_one_level_and_nothing_to_store() -> None:
    levels = geometry.pyramid_levels(400, 300, limits.TILE_PX)
    assert len(levels) == 1 and (levels[0].columns, levels[0].rows) == (1, 1)
    assert [lv for lv in levels if lv.level >= limits.FIRST_STORED_TILE_LEVEL] == []


def test_the_on_request_levels_are_exactly_those_below_the_first_stored_level() -> None:
    assert limits.FIRST_STORED_TILE_LEVEL == 2 and limits.MAX_ON_REQUEST_TILE_LEVEL == 1


def test_the_ceilings_are_the_ones_of_the_addendum() -> None:
    mib = 1024 * 1024
    assert limits.RENDER_LIMITS.address_space == 768 * mib
    assert limits.EXTRACT_LIMITS.address_space == 1024 * mib
    assert (limits.RENDER_LIMITS.cpu_seconds, limits.RENDER_LIMITS.wall_seconds) == (300, 600.0)
    assert (limits.EXTRACT_LIMITS.cpu_seconds, limits.EXTRACT_LIMITS.wall_seconds) == (300, 600.0)
    assert limits.TILE_LIMITS.address_space == 768 * mib
    assert limits.PIXEL_CAP == 40_000_000
    assert len(limits.ALGO_VERSION) <= 64
