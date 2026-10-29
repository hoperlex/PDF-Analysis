"""The pyramid grid and the transform convention (`CMP-VIEWER-01`)."""

from __future__ import annotations

import math

import pytest

from auditmanager.comparison.profile.child.geometry import pyramid_levels, raster_size, registration_dpi
from auditmanager.comparison.tiles.grid import Affine, PageGrid, TransformInvalid


def _summary(width_pt: float, height_pt: float) -> dict:
    dpi = registration_dpi(width_pt, height_pt, pixel_cap=40_000_000, max_dpi=200, min_dpi=72)
    width, height = raster_size(width_pt, height_pt, dpi)
    return {
        "width_pt": width_pt, "height_pt": height_pt,
        "raster": {"dpi": dpi, "width_px": width, "height_px": height},
        "tiles": {"tile_px": 512, "levels": [
            {"level": l.level, "width_px": l.width_px, "height_px": l.height_px, "columns": l.columns,
             "rows": l.rows, "stored": l.level >= 2} for l in pyramid_levels(width, height, 512)]},
    }


def test_the_grid_is_the_pyramid_of_the_page_profile() -> None:
    grid = PageGrid.from_summary(_summary(2383.94, 1683.78))  # A1
    assert grid is not None and grid.dpi == 200 and (grid.width_px, grid.height_px) == (6623, 4678)
    assert len(grid.levels) == 5 and grid.levels[4].columns == 1
    assert grid.tile_box(0, 12, 9) == (6144, 4608, 6623, 4678)  # the partial tile at the corner
    assert grid.tile_box(0, 13, 0) is None and grid.tile_box(5, 0, 0) is None and grid.tile_box(0, 0, -1) is None
    assert grid.points_per_pixel(0) == pytest.approx(0.36) and grid.points_per_pixel(3) == pytest.approx(2.88)


def test_a_page_without_a_pyramid_has_no_grid() -> None:
    assert PageGrid.from_summary({}) is None
    assert PageGrid.from_summary({"raster": {"dpi": 200, "width_px": 10, "height_px": 10}, "tiles": {"levels": []}}) is None
    broken = _summary(595.0, 842.0)
    broken["raster"]["dpi"] = 0
    assert PageGrid.from_summary(broken) is None
    skipped = _summary(2383.94, 1683.78)
    del skipped["tiles"]["levels"][1]
    assert PageGrid.from_summary(skipped) is None


def test_the_convention_of_the_six_numbers_is_the_pdf_matrix_order() -> None:
    """x' = a x + c y + e ; y' = b x + d y + f -- the order of fitz.Matrix(a, b, c, d, e, f) in the original."""
    t = Affine.from_sequence([2, 0, 0, 3, 10, 20])
    assert t.apply(1, 1) == (12, 23)
    shear = Affine.from_sequence([1, 0.5, 0.25, 1, 0, 0])
    assert shear.apply(4, 8) == (4 + 0.25 * 8, 0.5 * 4 + 8)


def test_the_inverse_undoes_the_map() -> None:
    t = Affine.from_sequence([0.98, 0.02, -0.03, 1.01, 12.5, -7.25])
    x, y = t.apply(123.4, 567.8)
    assert t.inverse().apply(x, y) == pytest.approx((123.4, 567.8))
    assert t.scale == pytest.approx(math.sqrt(0.98 * 1.01 + 0.02 * 0.03))


@pytest.mark.parametrize("value", [None, "abcdef", [1, 2, 3], [1, 0, 0, 1, 0], [1, 0, 0, 1, 0, 0, 0],
                                   [1, 0, 0, 1, 0, float("nan")], [1, 0, 0, 1, 0, float("inf")], [True, 0, 0, 1, 0, 0],
                                   [1, 0, 0, 1, 0, "0"], [0, 0, 0, 0, 5, 5], [1, 2, 2, 4, 0, 0]])
def test_a_transform_that_is_not_six_finite_numbers_of_an_invertible_map_is_refused(value) -> None:
    with pytest.raises(TransformInvalid):
        Affine.from_sequence(value)
