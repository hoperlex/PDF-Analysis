"""The pixel layers of a band (`CMP-ENGINE-01`, port of ``engine.py:575-684``): what only A draws, what only B draws,
style, light elements, colour, the tolerance and noise, on synthetic pictures whose every pixel is known."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from auditmanager.comparison.engine.child.geometry import bands
from auditmanager.comparison.engine.child.layers import compute_band

H, W = 160, 240
RADIUS = 1  # 0.5 pt at 200 dpi is 1.4 px: the tolerance of one pixel


def page() -> np.ndarray:
    return np.full((H, W, 3), 255, np.uint8)


def band(a: np.ndarray, b: np.ndarray, zone: np.ndarray | None = None, **kw):
    main = np.ones((H, W), np.uint8) if zone is None else (1 - zone)
    zones = {} if zone is None else {"stamp": zone}
    return compute_band(a, b, main, None, radius=RADIUS, core=(0, a.shape[0]), zone_masks=zones, **kw)


def count(layers, name: str) -> int:
    return int(layers[name].sum())


def test_identical_pages_differ_nowhere() -> None:
    a = page()
    cv2.line(a, (10, 10), (200, 90), (0, 0, 0), 2)
    layers = band(a, a.copy())
    assert all(count(layers, n) == 0 for n in ("a_only", "b_only", "style", "light_a", "light_b", "color", "within_tol"))


def test_a_line_shifted_by_one_pixel_is_within_the_tolerance_and_no_difference() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 50), (200, 50), (0, 0, 0), 3)
    cv2.line(b, (10, 51), (200, 51), (0, 0, 0), 3)
    layers = band(a, b)
    assert count(layers, "a_only") == 0 and count(layers, "b_only") == 0
    assert count(layers, "within_tol") > 0 and layers["within_components"] >= 1


def test_a_line_shifted_by_six_pixels_is_removed_from_a_and_added_in_b() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 50), (200, 50), (0, 0, 0), 3)
    cv2.line(b, (10, 56), (200, 56), (0, 0, 0), 3)
    layers = band(a, b)
    assert count(layers, "a_only") > 100 and count(layers, "b_only") > 100
    assert layers["a_only"][:, :].nonzero()[0].max() <= 52 and layers["b_only"].nonzero()[0].min() >= 54


def test_a_new_figure_is_only_in_b() -> None:
    a, b = page(), page()
    cv2.circle(b, (120, 80), 20, (0, 0, 0), 2)
    layers = band(a, b)
    assert count(layers, "b_only") > 50 and count(layers, "a_only") == 0


def test_a_common_line_that_changes_colour_is_a_colour_difference_and_not_a_geometry_one() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 50), (200, 50), (0, 0, 0), 5)
    cv2.line(b, (10, 50), (200, 50), (0, 0, 200), 5)  # BGR: red
    layers = band(a, b)
    assert count(layers, "color") > 100
    assert count(layers, "a_only") == 0 and count(layers, "b_only") == 0


def test_one_isolated_pixel_of_colour_is_the_blending_of_smoothing_and_goes_to_noise() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 50), (200, 50), (0, 0, 0), 5)
    cv2.line(b, (10, 50), (200, 50), (0, 0, 0), 5)
    b[50, 100] = (0, 0, 255)
    layers = band(a, b)
    assert count(layers, "color") == 0 and count(layers, "noise") >= 1


def test_a_dot_at_the_corner_of_a_common_line_is_noise_but_a_dot_on_an_empty_place_is_a_difference() -> None:
    """The dot is diagonal to the end of a common line: outside the tolerance disk (a cross of radius one) and inside
    the 3 x 3 neighbourhood of the common line, which is what anti-aliasing at the end of a line leaves."""
    a, b = page(), page()
    for picture in (a, b):
        cv2.rectangle(picture, (10, 49), (200, 51), (0, 0, 0), -1)
    b[48, 201] = (0, 0, 0)    # diagonal to the corner (49, 200)
    b[120, 100] = (0, 0, 0)   # alone in white space
    layers = band(a, b)
    assert layers["b_only"][48, 201] == 0 and layers["noise"][48, 201] == 1
    assert layers["b_only"][120, 100] == 1 and layers["noise"][120, 100] == 0


def test_a_thickened_pen_is_the_same_line_drawn_otherwise() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 50), (200, 50), (0, 0, 0), 2)
    cv2.line(b, (10, 50), (200, 50), (0, 0, 0), 6)
    layers = band(a, b)
    assert count(layers, "style") + count(layers, "b_only") + count(layers, "light_b") > 0
    assert count(layers, "a_only") == 0


def test_a_light_fill_only_in_b_is_a_light_element() -> None:
    a, b = page(), page()
    cv2.rectangle(b, (60, 40), (160, 100), (225, 225, 225), -1)  # grey 225: lighter than 250? no: darker, so ink
    layers = band(a, b)
    assert count(layers, "light_b") > 1000 and count(layers, "light_a") == 0


def test_pixels_in_a_service_zone_are_not_compared_as_main_and_are_counted_for_the_zone() -> None:
    a, b = page(), page()
    cv2.circle(b, (30, 30), 15, (0, 0, 0), 2)
    zone = np.zeros((H, W), np.uint8)
    zone[0:70, 0:70] = 1
    layers = band(a, b, zone)
    assert count(layers, "b_only") == 0
    differs, strict = layers["zone_stats"]["stamp"]
    assert differs > 50 and strict >= differs


def test_the_part_mask_limits_the_main_area_and_the_ink_of_a_is_counted_inside_and_outside_it() -> None:
    a, b = page(), page()
    cv2.line(a, (10, 20), (230, 20), (0, 0, 0), 3)
    cv2.line(b, (10, 26), (230, 26), (0, 0, 0), 3)
    part = np.zeros((H, W), np.uint8)
    part[:, :120] = 1
    layers = compute_band(a, b, np.ones((H, W), np.uint8), part, radius=RADIUS, core=(0, H), zone_masks={})
    assert layers["a_only"][:, 120:].sum() == 0 and layers["a_only"][:, :120].sum() > 0
    assert 0 < layers["ink_a_in_part"] < layers["ink_a_main"]


@pytest.mark.parametrize("rows", [41, 64, 160])
def test_a_band_with_its_margin_gives_the_core_rows_of_the_whole_canvas(rows: int) -> None:
    """The margin is enough for every filter: the core rows of a band equal the same rows of one band of the page."""
    a, b = page(), page()
    cv2.line(a, (10, 30), (200, 100), (0, 0, 0), 3)
    cv2.line(b, (10, 33), (200, 104), (0, 0, 0), 3)
    cv2.line(a, (5, 130), (230, 130), (0, 0, 0), 2)
    cv2.line(b, (5, 130), (230, 130), (0, 0, 200), 2)
    cv2.circle(b, (120, 80), 12, (0, 0, 0), 2)
    b[60, 60] = (0, 0, 0)
    whole = band(a, b)
    margin = 2 * RADIUS + 10
    for part in bands(W, H, pixels=rows * W, margin=margin):
        got = compute_band(a[part.ext0 : part.ext1], b[part.ext0 : part.ext1], np.ones((part.ext1 - part.ext0, W), np.uint8),
                           None, radius=RADIUS, core=(part.core0 - part.ext0, part.core1 - part.ext0), zone_masks={})
        lo, hi = part.core0 - part.ext0, part.core1 - part.ext0
        for name in ("a_only", "b_only", "style", "light_a", "light_b", "color", "noise", "within_tol", "dark_a", "any_b"):
            assert np.array_equal(got[name][lo:hi], whole[name][part.core0 : part.core1]), (name, part)
