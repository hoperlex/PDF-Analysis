"""The pure geometry core (`W55B-GEOMETRY-01`): the page box, the page-box check, the crop plan.

No PDF, no renderer, no store: every branch of :mod:`auditmanager.analysis.geometry.maths` is
driven with numbers. The rotation cases are checked against the independent oracle in
``geometry_support`` (the four clockwise-``/Rotate`` formulas of the PDF reference); the
renderer's agreement with them is ``test_clip_render.py``'s.
"""

from __future__ import annotations

import math
import random

import pytest

from auditmanager.analysis.geometry import maths
from auditmanager.analysis.geometry.maths import (
    GEOMETRY_MISMATCH,
    GEOMETRY_OK,
    MAX_PIXELS,
    MIN_LONG_SIDE_PX,
    Box,
    DegenerateCrop,
    check_page,
    displayed_size,
    plan_crop,
)
from tests.integration.analysis.geometry.geometry_support import PageSpec
from tests.integration.analysis.geometry.geometry_support import displayed_size as oracle_size

A4 = (595.28, 841.89)


# -- the displayed page --------------------------------------------------------------------


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("size", [(600.0, 400.0), (400.0, 600.0), A4, (2384.0, 1684.0)])
def test_the_displayed_size_is_the_box_after_a_clockwise_rotate(rotation, size) -> None:
    width, height = size
    box = Box(0.0, 0.0, width, height)
    assert displayed_size(box, box, rotation) == oracle_size(PageSpec(width, height, rotation))


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_a_crop_box_inside_the_media_box_is_the_page(rotation) -> None:
    media = Box(0.0, 0.0, 600.0, 400.0)
    crop = Box(50.0, 20.0, 550.0, 320.0)
    expected = oracle_size(PageSpec(600.0, 400.0, rotation, cropbox=(50.0, 20.0, 550.0, 320.0)))
    assert displayed_size(crop, media, rotation) == expected


def test_a_crop_box_outside_the_media_box_is_clipped_to_it() -> None:
    media = Box(0.0, 0.0, 600.0, 400.0)
    assert displayed_size(Box(-100.0, -50.0, 700.0, 300.0), media, 0) == (600.0, 300.0)
    assert displayed_size(Box(-100.0, -50.0, 700.0, 300.0), media, 90) == (300.0, 600.0)
    # corners in either order are the same box
    assert displayed_size(Box(700.0, 300.0, -100.0, -50.0), media, 0) == (600.0, 300.0)


def test_rotations_normalise_and_anything_off_the_quarter_turns_is_refused() -> None:
    assert [maths.normalised_rotation(d) for d in (0, 90, 180, 270, 360, 450, -90, -180)] == [
        0, 90, 180, 270, 0, 90, 270, 180,
    ]
    for bad in (45, 1, True, 90.0):
        with pytest.raises(ValueError):
            maths.normalised_rotation(bad)  # type: ignore[arg-type]


# -- the page-box check: rotation --------------------------------------------------------


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_an_agreeing_rotation_and_aspect_is_ok(rotation) -> None:
    width, height = oracle_size(PageSpec(*A4, rotation))
    assert check_page(
        portal_width_px=round(width * 300 / 72), portal_height_px=round(height * 300 / 72),
        portal_rotation=rotation, page_width_pt=width, page_height_pt=height, page_rotation=rotation,
    ) == GEOMETRY_OK


@pytest.mark.parametrize("portal", [0, 90, 180, 270])
@pytest.mark.parametrize("pdf", [0, 90, 180, 270])
def test_a_portal_rotation_other_than_the_pdfs_is_a_mismatch_even_on_a_square_page(portal, pdf) -> None:
    verdict = check_page(
        portal_width_px=1000, portal_height_px=1000, portal_rotation=portal,
        page_width_pt=500.0, page_height_pt=500.0, page_rotation=pdf,
    )
    assert verdict == (GEOMETRY_OK if portal == pdf else GEOMETRY_MISMATCH)


# -- the page-box check: the tolerance, both sides of the boundary, both directions ------


def _verdict(ratio: float) -> str:
    """The portal's aspect at ``ratio`` times the page's (a 1000 x 2000 pt page)."""
    page_w, page_h = 1000.0, 2000.0
    height_px = 1_000_000
    width_px = round(height_px * (page_w / page_h) * ratio)
    return check_page(
        portal_width_px=width_px, portal_height_px=height_px, portal_rotation=0,
        page_width_pt=page_w, page_height_pt=page_h, page_rotation=0,
    )


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (1.0, GEOMETRY_OK),
        (1.0006, GEOMETRY_OK),            # the real АР pages, about 0.06 %
        (1.0049, GEOMETRY_OK),
        (1.00499, GEOMETRY_OK),
        (1.00501, GEOMETRY_MISMATCH),
        (1.0051, GEOMETRY_MISMATCH),
        (1.0100, GEOMETRY_MISMATCH),
        (1 / 1.00499, GEOMETRY_OK),       # the portal narrower than the page
        (1 / 1.00501, GEOMETRY_MISMATCH),
        (1 / 1.0100, GEOMETRY_MISMATCH),
    ],
)
def test_the_aspect_tolerance_holds_on_both_sides_of_half_a_percent(ratio, expected) -> None:
    assert _verdict(ratio) == expected


def test_the_deviation_is_symmetric_and_exactly_half_a_percent_passes() -> None:
    # r and 1/r deviate equally, so a portal wider and a portal narrower than the page by
    # the same factor get the same verdict.
    assert maths.aspect_deviation(1005, 1000, 1.0, 1.0) == pytest.approx(0.005)
    assert maths.aspect_deviation(1000, 1005, 1.0, 1.0) == pytest.approx(0.005)
    # exactly at the boundary passes ("within"): r = 1.005 exactly in binary is not
    # representable, so the boundary is probed with the comparison itself
    assert maths.PAGE_BOX_TOLERANCE == 0.005
    assert check_page(
        portal_width_px=200, portal_height_px=100, portal_rotation=0,
        page_width_pt=200.0, page_height_pt=100.0, page_rotation=0,
    ) == GEOMETRY_OK


@pytest.mark.parametrize("bad", [(0, 100, 10.0, 10.0), (100, 100, 0.0, 10.0), (100, 100, 10.0, 0.0)])
def test_a_degenerate_page_or_raster_is_a_mismatch_never_a_division(bad) -> None:
    portal_w, portal_h, page_w, page_h = bad
    assert check_page(
        portal_width_px=portal_w, portal_height_px=portal_h, portal_rotation=0,
        page_width_pt=page_w, page_height_pt=page_h, page_rotation=0,
    ) == GEOMETRY_MISMATCH


# -- the crop plan ---------------------------------------------------------------------------


def _covers(plan: maths.CropPlan, box: tuple[float, ...]) -> bool:
    """The clip on the canvas covers the box (outward rounding), by at most a pixel per side."""
    x0, y0, x1, y1 = (box[0] * plan.canvas_width, box[1] * plan.canvas_height,
                      box[2] * plan.canvas_width, box[3] * plan.canvas_height)
    right, bottom = plan.left + plan.width, plan.top + plan.height
    return (
        plan.left <= x0 + 1e-6 and x0 - plan.left < 1 + 1e-6
        and plan.top <= y0 + 1e-6 and y0 - plan.top < 1 + 1e-6
        and right >= x1 - 1e-6 and right - x1 < 1 + 1e-6
        and bottom >= y1 - 1e-6 and bottom - y1 < 1 + 1e-6
    )


def test_a_block_at_the_portal_density_keeps_it_when_both_bounds_allow() -> None:
    box = (0.12, 0.62, 0.88, 0.8)
    base = 2480 / A4[0]
    plan = plan_crop(box, *A4, base)
    assert plan.scale == round(base, maths.SCALE_DIGITS)
    assert plan.long_side >= MIN_LONG_SIDE_PX and plan.pixels <= MAX_PIXELS
    assert _covers(plan, box)


def test_a_small_block_is_raised_to_the_800_pixel_floor() -> None:
    box = (0.5, 0.5, 0.55, 0.52)                      # about 30 x 17 pt
    plan = plan_crop(box, *A4, 1.0)
    assert plan.long_side >= MIN_LONG_SIDE_PX
    assert plan.long_side <= MIN_LONG_SIDE_PX + 2, "raised to the floor, not past it"
    assert plan.scale > 1.0
    assert _covers(plan, box)


def test_a_large_block_at_a_dense_raster_is_lowered_to_the_pixel_cap() -> None:
    box = (0.01, 0.01, 0.99, 0.99)
    plan = plan_crop(box, 2384.0, 1684.0, 600 / 72)    # an A1 sheet at 600 dpi
    assert plan.pixels <= MAX_PIXELS
    assert plan.pixels >= MAX_PIXELS * 0.995, "lowered to the cap, not far below it"
    assert plan.long_side >= 2000 > MIN_LONG_SIDE_PX
    assert _covers(plan, box)


def test_the_recorded_scale_is_the_rendered_one_to_six_decimals() -> None:
    plan = plan_crop((0.1, 0.1, 0.9, 0.9), *A4, 1 / 3)
    assert plan.scale == round(plan.scale, 6)
    assert plan.canvas_width == math.floor(A4[0] * plan.scale + 0.5)
    assert plan.canvas_height == math.floor(A4[1] * plan.scale + 0.5)


def test_the_clip_is_the_crop_and_never_the_page() -> None:
    plan = plan_crop((0.25, 0.25, 0.5, 0.5), *A4, 4.0)
    assert (plan.width, plan.height) != (plan.canvas_width, plan.canvas_height)
    assert plan.width < plan.canvas_width / 3 and plan.height < plan.canvas_height / 3
    assert 0 <= plan.left and plan.left + plan.width <= plan.canvas_width
    assert 0 <= plan.top and plan.top + plan.height <= plan.canvas_height


def test_both_bounds_hold_over_ten_thousand_random_blocks_and_pages() -> None:
    """The floor and the cap never conflict for a positive box (the module's proof), so every
    plan meets both; and every plan covers its box."""
    rng = random.Random(55)
    for _ in range(10_000):
        page = (rng.uniform(50.0, 3500.0), rng.uniform(50.0, 3500.0))
        x0, x1 = sorted(rng.uniform(0, 1) for _ in range(2))
        y0, y1 = sorted(rng.uniform(0, 1) for _ in range(2))
        if x1 - x0 < 1e-3 or y1 - y0 < 1e-3:
            continue                     # a box at least a few pixels of a portal raster
        box = (x0, y0, x1, y1)
        plan = plan_crop(box, *page, rng.choice([0.5, 1.0, 2.0, 300 / 72, 600 / 72, 50.0]))
        assert plan.long_side >= MIN_LONG_SIDE_PX, (box, page, plan)
        assert plan.pixels <= MAX_PIXELS, (box, page, plan)
        assert _covers(plan, box), (box, page, plan)


def test_the_corner_rule_lets_the_cap_win(monkeypatch) -> None:
    """Were the floor ever to need more pixels than the cap allows, the cap wins.

    It cannot happen for a real box, so it is reached by lowering the cap inside the module:
    a 1 000-pixel cap with an 800-pixel floor leaves no box room for both.
    """
    monkeypatch.setattr(maths, "MAX_PIXELS", 1_000)
    plan = plan_crop((0.1, 0.1, 0.9, 0.8), 1000.0, 1000.0, 1.0)
    assert plan.pixels <= 1_000
    assert plan.long_side < MIN_LONG_SIDE_PX


@pytest.mark.parametrize(
    "box",
    [
        (0.5, 0.5, 0.5, 0.6),           # no width
        (0.5, 0.6, 0.6, 0.6),           # no height
        (0.6, 0.5, 0.5, 0.6),           # reversed
        (-0.1, 0.5, 0.5, 0.6),          # outside [0, 1]
        (0.5, 0.5, 1.1, 0.6),
        (0.5, 0.5, 0.5 + 1e-9, 0.5 + 1e-9),  # smaller than any canvas can position
        (0.1, 0.2, 0.3),                # three coordinates
        (0.1, float("nan"), 0.3, 0.4),
    ],
)
def test_a_degenerate_box_is_refused(box) -> None:
    with pytest.raises(DegenerateCrop):
        plan_crop(box, *A4, 4.0)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "box",
    [
        (0.0, 0.0, 5e-324, 5e-324),     # subnormal sides: the floor's ceil(inf) overflowed
        (0.0, 0.0, 5e-324, 0.5),        # one subnormal side
        (0.0, 0.0, 1e-300, 1e-300),     # the cap's quadratic divided by zero
        (0.0, 0.0, 1e-160, 1e-160),     # the clip's area underflows to zero
    ],
)
def test_a_box_ingest_admits_whose_arithmetic_fails_is_degenerate_never_an_untyped_error(box) -> None:
    """`W55B-JUDGE-X` X-8. Each box is what ingest admits -- four numbers in [0, 1] with
    ``x0 < x1`` and ``y0 < y1``, unchanged by a JSON round trip -- and each made
    ``plan_crop`` raise ``OverflowError`` or ``ZeroDivisionError``, which the stage did not
    catch and the run ended ``crashed``. It is a box too small to position on a canvas: the
    typed refusal, and nothing else."""
    import json

    admitted = tuple(json.loads(json.dumps(list(box))))
    assert admitted == box and box[0] < box[2] and box[1] < box[3]
    with pytest.raises(DegenerateCrop) as refused:
        plan_crop(admitted, *A4, 4.0)
    assert type(refused.value) is DegenerateCrop


def test_a_block_of_one_portal_pixel_is_still_cut_and_the_degenerate_bound_is_far_below_it() -> None:
    """Degenerate means a long side under ``800 / 2**24`` of the page's longer side: about a
    sixth of a pixel of a 300 dpi A4 raster. One pixel of that raster is still cut."""
    pixel = 1 / 3508
    plan = plan_crop((0.5, 0.5, 0.5 + pixel, 0.5 + pixel), *A4, 2480 / A4[0])
    assert plan.long_side >= MIN_LONG_SIDE_PX
    assert max(plan.canvas_width, plan.canvas_height) <= maths.MAX_CANVAS_SIDE
    bound = MIN_LONG_SIDE_PX / maths.MAX_CANVAS_SIDE           # of the longer page side
    plan_crop((0.5, 0.5, 0.5 + bound * 1.01, 0.5 + bound * 1.01), *A4, 1.0)
    with pytest.raises(DegenerateCrop):
        plan_crop((0.5, 0.5, 0.5 + bound * 0.99, 0.5 + bound * 0.99), *A4, 1.0)


def test_the_base_scale_is_the_portal_rasters_density() -> None:
    assert maths.base_scale(2480, 595.28) == pytest.approx(4.1661, abs=1e-4)
