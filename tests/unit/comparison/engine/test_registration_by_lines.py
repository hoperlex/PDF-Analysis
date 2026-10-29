"""The shift of B onto A from the vector lines of the sheets, and the pieces that keep registration inside the ceiling
(`CMP-ENGINE-01`): the line vote, the numpy similarity RANSAC, the reduced phase correlation."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from auditmanager.comparison.engine.child import registration as reg
from auditmanager.comparison.engine.child import settings


def sheet(seed: int = 4, n: int = 600) -> np.ndarray:
    """``n`` lines, each ``[x0, top, x1, bottom]``, scattered over an A3 sheet."""
    rng = np.random.default_rng(seed)
    x, y = rng.uniform(30, 1100, n), rng.uniform(30, 780, n)
    length = rng.uniform(4, 120, n)
    horizontal = rng.random(n) < 0.5
    return np.stack([x, y, np.where(horizontal, x + length, x), np.where(horizontal, y, y + length)], axis=1).astype(np.float32)


def test_a_shift_of_two_and_a_half_points_is_recovered_to_a_tenth() -> None:
    a = sheet()
    b = a - np.float32([2.5, -1.3, 2.5, -1.3])  # B is A moved by (-2.5, +1.3): to bring B onto A add (2.5, -1.3)
    found = reg.refine_by_lines(a, b, reg.identity())
    assert found is not None and found["method"] == "lines"
    assert np.allclose(np.array(found["matrix"])[:, 2], [2.5, -1.3], atol=0.06)
    assert found["votes"] >= 0.8 * 2 * len(a)


def test_the_same_lines_are_a_zero_shift() -> None:
    a = sheet()
    found = reg.refine_by_lines(a, a.copy(), reg.identity())
    assert found is not None and np.allclose(np.array(found["matrix"])[:, 2], [0.0, 0.0], atol=0.06)


def test_lines_that_have_nothing_in_common_give_no_vote() -> None:
    assert reg.refine_by_lines(sheet(1), sheet(2), reg.identity()) is None


def test_a_few_common_lines_among_many_others_are_not_enough() -> None:
    a = sheet(1, 600)
    b = sheet(2, 600)
    b[:5] = a[:5] + np.float32([1.0, 1.0, 1.0, 1.0])
    assert reg.refine_by_lines(a, b, reg.identity()) is None


def test_only_a_pure_shift_is_refined() -> None:
    a = sheet()
    scaled = np.array([[1.01, 0.0, 0.0], [0.0, 1.01, 0.0]])
    assert reg.refine_by_lines(a, a, scaled) is None
    assert reg.refine_by_lines(None, a, reg.identity()) is None


def test_a_hatch_is_given_up_not_voted_on() -> None:
    """Every point of a fine hatch has hundreds of neighbours within the radius: the vote means nothing and the work is
    bounded (`total > 1 500 000`), and a periodic drawing agrees with itself at many shifts, so no peak stands out."""
    xs = np.arange(0, 600, 0.5, dtype=np.float32)
    hatch = np.stack([xs, np.full_like(xs, 10.0), xs + 3, np.full_like(xs, 10.0)], axis=1)
    many = np.concatenate([hatch + np.float32([0, 0.3 * k, 0, 0.3 * k]) for k in range(200)])
    assert reg.refine_by_lines(many, many, reg.identity()) is None


def test_the_phase_estimate_of_identical_masks_is_replaced_by_the_identity() -> None:
    rng = np.random.default_rng(5)
    mask = (rng.random((300, 220)) < 0.04).astype(np.uint8)
    result = reg.register([], [], [], [], mask, mask.copy(), 36)
    assert result["identity"] is True and result["method"] == "phase" and result["reliable"] is True


def test_with_lines_the_registration_of_a_shifted_sheet_is_exact() -> None:
    rng = np.random.default_rng(6)
    lines = sheet(8, 400)
    shift = np.float32([4.0, 2.0, 4.0, 2.0])
    shifted = lines - shift   # B
    mask_a = np.zeros((int(842 / 2), int(1190 / 2)), np.uint8)
    for x0, y0, x1, y1 in lines:
        cv2.line(mask_a, (int(x0 / 2), int(y0 / 2)), (int(x1 / 2), int(y1 / 2)), 1, 1)
    mask_b = np.zeros_like(mask_a)
    for x0, y0, x1, y1 in shifted:
        cv2.line(mask_b, (int(x0 / 2), int(y0 / 2)), (int(x1 / 2), int(y1 / 2)), 1, 1)
    result = reg.register([], [], [], [], mask_a, mask_b, 36, lines, shifted)
    assert result["method"] == "lines" and result["reliable"] is True
    assert np.allclose(np.array(result["matrix"])[:, 2], [4.0, 2.0], atol=0.06)


def test_a_mask_over_the_limit_is_reduced_before_the_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[int, int]] = []
    real = cv2.phaseCorrelate

    def spy(a, b, *args):
        seen.append(a.shape)
        return real(a, b, *args)

    monkeypatch.setattr(cv2, "phaseCorrelate", spy)
    big = np.zeros((1685, 2384), np.uint8)
    big[100:900, 200:260] = 1
    result = reg.by_phase(big, np.roll(big, 4, axis=1), 36)
    assert seen and seen[0][0] * seen[0][1] <= settings.PHASE_MAX_PIXELS
    assert result["accepted"] and abs(result["matrix"][0][2]) > 0  # a shift of 4 px = 8 pt, to within the reduction


def test_the_numpy_ransac_returns_the_similarity_of_the_inliers_and_ignores_outliers() -> None:
    rng = np.random.default_rng(9)
    src = rng.uniform(0, 500, (120, 2))
    theta, scale, t = 0.01, 1.003, np.array([5.0, -7.0])
    rotation = scale * np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    dst = src @ rotation.T + t
    dst[:20] += rng.uniform(40, 90, (20, 2))
    matrix, inliers = reg.similarity_ransac(src, dst, 2.0)
    assert matrix is not None and inliers.sum() >= 99
    assert np.allclose(matrix[:, :2], rotation, atol=1e-4) and np.allclose(matrix[:, 2], t, atol=0.05)


def test_the_numpy_ransac_refuses_what_it_cannot_fit() -> None:
    two = np.array([[0.0, 0.0], [1.0, 1.0]])
    assert reg.similarity_ransac(two, two, 1.0) == (None, None)  # two points are not enough to tell inliers from a fit
    same_point = np.zeros((5, 2))
    assert reg.similarity_ransac(same_point, same_point, 1.0) == (None, None)  # no pair of distinct points
