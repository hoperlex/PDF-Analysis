"""Registration of B onto A on the downsampled raster (port of ``registration.py``)."""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from auditmanager.comparison.engine.child import registration as reg


def anchors(n: int = 40, seed: int = 3):
    rng = np.random.default_rng(seed)
    return [[float(x), float(y), float(x) + 30, float(y) + 8, f"марка{i}"] for i, (x, y) in
            enumerate(zip(rng.uniform(40, 540, n), rng.uniform(40, 780, n)))]


def moved(words, m):
    out = []
    for x0, y0, x1, y1, t in words:
        a, b = m[0][0] * x0 + m[0][1] * y0 + m[0][2], m[1][0] * x0 + m[1][1] * y0 + m[1][2]
        c, d = m[0][0] * x1 + m[0][1] * y1 + m[0][2], m[1][0] * x1 + m[1][1] * y1 + m[1][2]
        out.append([a, b, c, d, t])
    return out


def inverse_of(angle_deg: float, scale: float, dx: float, dy: float):
    """B -> A is the inverse of A -> B; build A = f(B) so that the registration recovers f."""
    t = math.radians(angle_deg)
    return np.array([[scale * math.cos(t), -scale * math.sin(t), dx], [scale * math.sin(t), scale * math.cos(t), dy]])


def test_anchors_recover_a_known_similarity() -> None:
    a_words = anchors()
    f = inverse_of(0.4, 1.01, 7.5, -3.25)  # B -> A
    # B holds the points that f carries onto A: b = f^-1 (a)
    inv = cv2.invertAffineTransform(f)
    b_words = moved(a_words, inv)
    result = reg.by_anchors(a_words, b_words, [], [])
    assert result["accepted"] and result["inliers"] == 40
    got = np.array(result["matrix"])
    assert np.allclose(got, f, atol=0.02)


def test_a_few_wrong_anchors_do_not_move_the_registration() -> None:
    a_words = anchors()
    f = inverse_of(0.0, 1.0, 12.0, 4.0)
    b_words = moved(a_words, cv2.invertAffineTransform(f))
    for i in range(0, 8):
        b_words[i][0] += 150
        b_words[i][2] += 150
    result = reg.by_anchors(a_words, b_words, [], [])
    assert result["accepted"] and np.allclose(np.array(result["matrix"]), f, atol=0.05)


def test_fewer_than_three_common_unique_words_is_not_a_registration() -> None:
    result = reg.by_anchors(anchors(2), anchors(2), [], [])
    assert result["accepted"] is False and result["anchors"] == 2


def test_words_in_a_service_zone_and_repeated_words_are_no_anchors() -> None:
    words = [[10, 10, 40, 18, "дубль"], [100, 10, 130, 18, "дубль"], [10, 100, 40, 108, "ab"], [200, 200, 240, 208, "уникально"]]
    assert list(reg._anchors(words, [])) == ["уникально"]
    assert list(reg._anchors(words, [[190, 190, 260, 220]])) == []


def test_a_shift_within_half_a_point_is_snapped_to_the_identity() -> None:
    m, is_identity = reg._snap(np.array([[1.0, 0.0, 0.3], [0.0, 1.0, -0.2]]))
    assert is_identity and np.array_equal(m, reg.identity())
    m, is_identity = reg._snap(np.array([[1.0, 0.0, 3.0], [0.0, 1.0, -0.2]]))
    assert not is_identity and m[0][2] == 3.0


def blob_mask(shift_x: int = 0, shift_y: int = 0) -> np.ndarray:
    mask = np.zeros((300, 220), np.uint8)
    rng = np.random.default_rng(5)
    for _ in range(40):
        x, y = int(rng.integers(20, 180)), int(rng.integers(20, 260))
        cv2.rectangle(mask, (x + shift_x, y + shift_y), (x + shift_x + 12, y + shift_y + 5), 1, -1)
    return mask


def test_phase_correlation_finds_a_shift_of_the_masks_in_points() -> None:
    a = blob_mask()
    b = blob_mask(-6, 4)  # B is A moved by (-6, +4) px: to bring B onto A shift by (+6, -4) px = (+12, -8) pt at 36 dpi
    result = reg.by_phase(a, b, 36)
    assert result["accepted"]
    assert np.allclose(np.array(result["matrix"])[:, 2], [12.0, -8.0], atol=1.1)  # the estimate is good to half a pixel


def test_the_dice_of_masks_that_agree_is_high_and_of_masks_that_do_not_is_low() -> None:
    a = blob_mask()
    assert reg.dice(a, a.copy(), reg.identity(), 36, []) > 0.99
    assert reg.dice(a, blob_mask(40, 40), reg.identity(), 36, []) < 0.5


def test_register_takes_the_identity_for_pages_that_agree_and_marks_it_reliable() -> None:
    a = blob_mask()
    result = reg.register([], [], [], [], a, a.copy(), 36)
    assert result["identity"] is True and result["reliable"] is True and result["dice36"] > 0.99


def test_register_with_nothing_to_go_by_is_the_identity_and_not_reliable() -> None:
    result = reg.register([], [], [], [], None, None, 36)
    assert result["identity"] is True and result["reliable"] is False
