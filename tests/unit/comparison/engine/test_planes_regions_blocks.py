"""The plane store, the grouping of regions, the checks around a region and the moved blocks (`CMP-ENGINE-01`)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from auditmanager.comparison.engine.child import blocks, regions
from auditmanager.comparison.engine.child.geometry import Canvas
from auditmanager.comparison.engine.child.planes import PlaneStore
from auditmanager.comparison.engine.mask_codec import decode_mask, encode_packed_planes

CANVAS = Canvas(width_pt=288.0, height_pt=144.0, dpi=200)  # 800 x 400 px


def store(width: int = 800, height: int = 400, names=("a_only", "b_only", "light_a", "light_b", "color", "style",
                                                    "dark_a", "dark_b", "any_a", "any_b", "moved", "zones", "noise", "within_tol")):
    return PlaneStore(width, height, names)


def test_rows_and_windows_round_trip_for_widths_that_are_not_a_multiple_of_eight() -> None:
    rng = np.random.default_rng(1)
    for width in (1, 7, 8, 9, 37, 801):
        planes = PlaneStore(width, 20, ("p",))
        picture = (rng.random((20, width)) < 0.3).astype(np.uint8)
        planes.put_rows("p", 0, picture)
        assert np.array_equal(planes.rows("p", 0, 20), picture)
        x0, x1 = min(3, width - 1), width
        assert np.array_equal(planes.window("p", x0, 2, x1, 15), picture[2:15, x0:x1])
        assert planes.count("p") == int(picture.sum())


def test_a_window_written_back_changes_only_its_own_bits() -> None:
    planes = PlaneStore(50, 30, ("p",))
    base = np.zeros((30, 50), np.uint8)
    base[5, 7] = 1
    planes.put_rows("p", 0, base)
    planes.put_window("p", 10, 4, np.ones((3, 5), np.uint8))
    expected = base.copy()
    expected[4:7, 10:15] = 1
    assert np.array_equal(planes.rows("p", 0, 30), expected)
    planes.or_window("p", 12, 4, np.zeros((3, 20), np.uint8))
    assert np.array_equal(planes.rows("p", 0, 30), expected)


def test_a_window_outside_the_canvas_is_clipped() -> None:
    planes = PlaneStore(40, 20, ("p",))
    planes.put_window("p", 35, 15, np.ones((10, 10), np.uint8))
    assert planes.count("p") == 5 * 5
    assert planes.window("p", -5, -5, 3, 3).shape == (3, 3)


def test_the_stacked_planes_are_the_packed_array_of_the_mask_blob() -> None:
    rng = np.random.default_rng(2)
    names = [f"p{i}" for i in range(8)]
    planes = PlaneStore(203, 31, names)
    full = (rng.random((8, 31, 203)) < 0.2).astype(np.uint8)
    for i, name in enumerate(names):
        planes.put_rows(name, 0, full[i])
    decoded = decode_mask(encode_packed_planes(planes.packed(names), 203, 31))
    assert np.array_equal(decoded.planes(), full.astype(bool))


# -- grouping and counts ------------------------------------------------------------------------------------------

def _speck(planes: PlaneStore, name: str, x: int, y: int, size: int = 3) -> None:
    window = np.ones((size, size), np.uint8)
    planes.or_window(name, x, y, window)


def test_specks_within_one_and_a_half_millimetres_are_one_region_and_far_ones_are_not() -> None:
    planes = store()
    _speck(planes, "a_only", 100, 100)
    _speck(planes, "b_only", 106, 100)      # 3 px apart = 0.4 mm: the same region
    _speck(planes, "a_only", 400, 300)      # far away
    regions.close_union(planes, CANVAS, band_pixels=40_000)
    labels, stats, factor = regions.label_regions(planes, band_pixels=40_000)
    assert factor == 1 and int(stats.shape[0]) - 1 == 2
    counts = regions.layer_counts(planes, labels, stats.shape[0], factor, ("a_only", "b_only", "out"), band_pixels=40_000)
    near = int(labels[101, 101])
    assert counts["a_only"][near] == 9 and counts["b_only"][near] == 9 and counts["out"][near] == 18


def test_counts_leave_out_the_places_of_moved_inscriptions() -> None:
    planes = store()
    _speck(planes, "a_only", 100, 100)
    regions.close_union(planes, CANVAS, band_pixels=40_000)
    labels, stats, factor = regions.label_regions(planes, band_pixels=40_000)
    counts = regions.layer_counts(planes, labels, stats.shape[0], factor, ("out",), band_pixels=40_000,
                                  exclude=lambda y0, y1: regions.rect_arrays([[90, 90, 120, 120]], y1 - y0, 800, y0))
    assert counts["out"].sum() == 0


def test_a_large_canvas_is_labelled_on_the_reduced_grid_and_the_regions_still_cover_the_pixels() -> None:
    assert regions.reduction_factor(6623, 4678) == 3 and regions.reduction_factor(5000, 4000) == 2 and regions.reduction_factor(3308, 2339) == 1
    planes = PlaneStore(6000, 3000, ("a_only", "b_only", "light_a", "light_b", "color", "style"))
    _speck(planes, "a_only", 1001, 1001, 7)
    regions.close_union(planes, Canvas(2160.0, 1080.0, 200), band_pixels=1_000_000)
    labels, stats, factor = regions.label_regions(planes, band_pixels=1_000_000)
    assert factor == 2
    x, y, w, h = (int(v) * factor for v in stats[1][:4])
    assert x <= 1001 and y <= 1001 and x + w >= 1008 and y + h >= 1008


# -- glyph lines ----------------------------------------------------------------------------------------------------

def _glyph_row(count: int, stroke: bool) -> np.ndarray:
    mm = CANVAS.dpi / 25.4
    mask = np.zeros((60, 400), np.uint8)
    h = int(2.5 * mm)
    for i in range(count):
        x = 10 + i * int(3.5 * mm)
        if stroke:
            cv2.line(mask, (x, 10), (x, 10 + h), 1, 1)
        else:
            cv2.circle(mask, (x + h // 3, 10 + h // 2), h // 3, 1, 2)
            cv2.line(mask, (x + h // 3, 10 + h // 2), (x + h // 3 + 3, 10 + h), 1, 1)
    return mask


def test_three_glyphs_of_one_height_in_a_row_are_an_inscription() -> None:
    mm = CANVAS.dpi / 25.4
    assert regions.glyph_line(_glyph_row(4, stroke=False), mm) is True


def test_a_row_of_straight_strokes_is_a_hatch_not_an_inscription() -> None:
    mm = CANVAS.dpi / 25.4
    assert regions.glyph_line(_glyph_row(6, stroke=True), mm) is False


def test_two_glyphs_are_not_enough() -> None:
    mm = CANVAS.dpi / 25.4
    assert regions.glyph_line(_glyph_row(2, stroke=False), mm) is False


def _reference_glyph_line(mask, mm_px, common=None) -> bool:
    """The original's loop without the pruning (``engine.py:192-232``), to hold the pruning to the same answers."""
    from auditmanager.comparison.engine.child import settings

    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    glyphs = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[i])
        if not (1.0 * mm_px <= h <= 6 * mm_px and w <= 6 * mm_px):
            continue
        if w > settings.GLYPH_MAX_ASPECT * h or area > settings.GLYPH_MAX_FILL * w * h:
            continue
        glyphs.append((stats[i], cents[i], regions._is_stroke((lab[y : y + h, x : x + w] == i).astype(np.uint8))))
    glyphs.sort(key=lambda g: g[1][0])
    for i in range(len(glyphs)):
        chain = [glyphs[i]]
        for g in glyphs[i + 1 :]:
            last = chain[-1]
            same_row = abs(g[1][1] - last[1][1]) <= 1.0 * mm_px
            similar = 0.6 <= g[0][3] / max(1, last[0][3]) <= 1.6
            gap_x0, gap_x1 = last[0][0] + last[0][2], g[0][0]
            close = -0.25 * min(g[0][3], last[0][3]) <= gap_x1 - gap_x0 <= 3 * mm_px
            if close and common is not None and gap_x1 > gap_x0:
                gy0 = max(last[0][1], g[0][1])
                gy1 = min(last[0][1] + last[0][3], g[0][1] + g[0][3])
                if gy1 > gy0 and common[gy0:gy1, gap_x0:gap_x1].any():
                    close = False
            if same_row and similar and close:
                chain.append(g)
        if len(chain) >= 3 and not all(g[2] for g in chain):
            return True
    return False


def test_the_pruned_glyph_search_gives_the_answers_of_the_original_loop() -> None:
    mm = CANVAS.dpi / 25.4
    rng = np.random.default_rng(7)
    for trial in range(60):
        mask = np.zeros((90, 500), np.uint8)
        for _ in range(int(rng.integers(3, 25))):
            x, y = int(rng.integers(5, 470)), int(rng.integers(5, 60))
            w, h = int(rng.integers(3, int(3 * mm))), int(rng.integers(int(1.2 * mm), int(3.5 * mm)))
            if rng.random() < 0.5:
                cv2.rectangle(mask, (x, y), (x + w, y + h), 1, 1)
            else:
                cv2.ellipse(mask, (x, y), (w, h // 2 + 1), int(rng.integers(0, 90)), 0, 360, 1, 1)
        common = (rng.random((90, 500)) < 0.01).astype(np.uint8) if trial % 3 == 0 else None
        assert regions.glyph_line(mask, mm, common) == _reference_glyph_line(mask, mm, common), trial


# -- shift explained, moved blocks -------------------------------------------------------------------------------------

def _figure(planes: PlaneStore, name_pairs, x: int, y: int) -> None:
    window = np.zeros((20, 40), np.uint8)
    cv2.rectangle(window, (2, 2), (36, 16), 1, 1)
    cv2.line(window, (6, 8), (30, 8), 1, 1)
    for name in name_pairs:
        planes.or_window(name, x, y, window)


def test_a_figure_that_moved_with_its_caption_is_explained_by_the_shift() -> None:
    planes = store()
    _figure(planes, ("dark_a", "any_a", "a_only"), 100, 100)
    _figure(planes, ("dark_b", "any_b", "b_only"), 130, 110)  # moved by (30, 10) px
    mm_vector = (30 / CANVAS.s, 10 / CANVAS.s)
    assert regions.shift_explains(planes, [mm_vector], [90, 90, 190, 140], CANVAS, deadline=1e18)


def test_a_new_figure_that_nothing_moved_to_is_not_explained_by_a_shift() -> None:
    planes = store()
    _figure(planes, ("dark_b", "any_b", "b_only"), 130, 110)
    assert not regions.shift_explains(planes, [(30 / CANVAS.s, 10 / CANVAS.s)], [120, 100, 190, 140], CANVAS, deadline=1e18)


def test_blocks_are_found_from_five_words_that_share_a_vector_and_not_from_four() -> None:
    def make(n: int):
        a = [{"text": f"слово{i}", "pt": [10.0, 10.0 + 12 * i, 40.0, 18.0 + 12 * i], "dir": None} for i in range(n)]
        b = [{"text": w["text"], "pt": [w["pt"][0] + 50, w["pt"][1] + 20, w["pt"][2] + 50, w["pt"][3] + 20], "dir": None} for w in a]
        return {"only_a": a, "only_b": b, "moved": []}

    found = blocks.find(make(6))
    assert len(found) == 1 and len(found[0]["a_words"]) == 6
    assert found[0]["vector"] == pytest.approx([50.0, 20.0], abs=0.01)
    assert blocks.find(make(4)) == []


def test_a_block_whose_pixels_the_shift_explains_leaves_the_difference_layers_for_the_moved_layer() -> None:
    planes = store()
    vx, vy = 36, 14
    block = np.zeros((60, 120), np.uint8)
    cv2.rectangle(block, (2, 2), (110, 50), 1, 1)
    cv2.line(block, (2, 26), (110, 26), 1, 1)
    for name in ("dark_a", "any_a", "a_only"):
        planes.or_window(name, 100, 100, block)
    for name in ("dark_b", "any_b", "b_only"):
        planes.or_window(name, 100 + vx, 100 + vy, block)
    words_a = [{"text": f"w{i}", "pt": [104 / CANVAS.s, (104 + 8 * i) / CANVAS.s, 140 / CANVAS.s, (110 + 8 * i) / CANVAS.s], "dir": None} for i in range(6)]
    words_b = [{"text": w["text"], "pt": [w["pt"][0] + vx / CANVAS.s, w["pt"][1] + vy / CANVAS.s, w["pt"][2] + vx / CANVAS.s, w["pt"][3] + vy / CANVAS.s], "dir": None} for w in words_a]
    candidates = blocks.find({"only_a": words_a, "only_b": words_b, "moved": []})
    assert len(candidates) == 1
    before = planes.count("a_only"), planes.count("b_only")
    confirmed = blocks.confirm(candidates, planes, CANVAS)
    assert len(confirmed) == 1 and confirmed[0]["share"] >= 0.9
    assert planes.count("a_only") < before[0] * 0.1 and planes.count("b_only") < before[1] * 0.1
    assert planes.count("moved") > 0.8 * (before[0] + before[1])


def test_a_candidate_whose_pixels_do_not_agree_is_not_confirmed() -> None:
    planes = store()
    block = np.zeros((60, 120), np.uint8)
    cv2.rectangle(block, (2, 2), (110, 50), 1, 1)
    for name in ("dark_a", "any_a", "a_only"):
        planes.or_window(name, 100, 100, block)
    other = np.zeros((60, 120), np.uint8)
    cv2.circle(other, (60, 30), 25, 1, 1)
    for name in ("dark_b", "any_b", "b_only"):
        planes.or_window(name, 136, 114, other)
    words_a = [{"text": f"w{i}", "pt": [104 / CANVAS.s, (104 + 8 * i) / CANVAS.s, 140 / CANVAS.s, (110 + 8 * i) / CANVAS.s], "dir": None} for i in range(6)]
    words_b = [{"text": w["text"], "pt": [w["pt"][0] + 36 / CANVAS.s, w["pt"][1] + 14 / CANVAS.s, w["pt"][2] + 36 / CANVAS.s, w["pt"][3] + 14 / CANVAS.s], "dir": None} for w in words_a]
    assert blocks.confirm(blocks.find({"only_a": words_a, "only_b": words_b, "moved": []}), planes, CANVAS) == []
    assert planes.count("moved") == 0
