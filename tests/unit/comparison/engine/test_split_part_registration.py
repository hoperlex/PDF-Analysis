"""A part of a split sheet registers onto its own region of the older sheet (`CMP-C1-FIX-A` item 2).

`CMP-SERIES-01` section 9 item 2 and `CMP-ENGINE-01` section 5: in the corpus (V4 to V5, sheet E05) the second part was
registered onto the left region of the older sheet (`area_a_pt` `[78.89, 3.5, 1221.89, 1680.5]` against the first part's
`[45.5, 3.5, 1188.5, 1680.5]`), so the areas overlapped and the series refused the ink coverage. The sheet repeats itself:
its right half is its left half with other labels, so a registration that compares the whole masks cannot tell the
halves apart; the place of a part is where its whole ink (frame included) fits **inside** the older sheet.

The corpus tests run the real page children and the real engine child; the others build masks.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from auditmanager.comparison.engine.child import registration as reg
from auditmanager.comparison.engine.child import settings

DPI = settings.MASK_DPI


def mirrored_sheet(width: int = 1192, height: int = 842, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """A 36 dpi mask of a sheet whose right half repeats its left half but for two small labels, and a part: the right half
    cut out, with a frame of its own. Returns ``(sheet, part)``."""
    rng = np.random.default_rng(seed)
    half = width // 2
    left = np.zeros((height, half), np.uint8)
    for _ in range(90):  # a drawing: bars
        x, y = int(rng.integers(30, half - 60)), int(rng.integers(30, height - 60))
        if rng.random() < 0.5:
            left[y : y + 2, x : x + int(rng.integers(8, 60))] = 1
        else:
            left[y : y + int(rng.integers(8, 60)), x : x + 2] = 1
    right = left.copy()
    left[100:108, 100:140] = 1  # the labels that differ: "(L)" and "(R)"
    right[100:108, 160:200] = 1
    sheet = np.concatenate([left, right], axis=1)
    sheet[:3, :] = 1  # the frame of the whole sheet
    sheet[-3:, :] = 1
    sheet[:, :3] = 1
    sheet[:, -3:] = 1
    part = sheet[:, half:].copy()
    part[:, :3] = 1  # the part has a frame of its own at its left edge too
    return sheet, part


def test_the_part_is_found_in_the_right_half_not_the_left() -> None:
    sheet, part = mirrored_sheet()
    half = sheet.shape[1] // 2
    found = reg.by_template(sheet, part, DPI, [], [])
    assert found is not None and found["method"] == "template" and found["accepted"], found
    dx = found["matrix"][0][2] * DPI / 72
    assert abs(dx - half) <= 1.0 and abs(found["matrix"][1][2]) <= 1.0, found


def test_the_left_part_is_found_at_the_origin() -> None:
    sheet, _ = mirrored_sheet()
    left = sheet[:, : sheet.shape[1] // 2].copy()
    left[:, -3:] = 1
    found = reg.by_template(sheet, left, DPI, [], [])
    assert found is not None and found["accepted"] and found["identity"], found


def test_a_part_larger_than_the_sheet_is_not_a_crop() -> None:
    sheet, _ = mirrored_sheet()
    assert reg.by_template(sheet[:, :600], sheet, DPI, [], []) is None
    assert reg.by_template(sheet, np.zeros((10, 10), np.uint8), DPI, [], []) is None  # no ink: nothing to place


def test_a_page_that_is_not_in_the_sheet_is_not_placed() -> None:
    sheet, _ = mirrored_sheet()
    stranger = np.zeros((700, 500), np.uint8)
    rng = np.random.default_rng(99)
    ys, xs = rng.integers(0, 700, 4000), rng.integers(0, 500, 4000)
    stranger[ys, xs] = 1
    found = reg.by_template(sheet, stranger, DPI, [], [])
    assert found is not None and found["accepted"] is False and found["score"] < settings.TEMPLATE_MIN_SCORE, found
    # and the registration does not pretend: nothing was placed, so it is not reliable
    result = reg.register([], [], [], [], sheet, stranger, DPI, crop=True)
    assert result["reliable"] is False and result["method"] == "identity", result


def test_the_service_zones_of_the_two_sheets_do_not_decide_the_place() -> None:
    """The stamp is redrawn on every part (and differs between versions): it is cleared in both masks before they are compared."""
    sheet, part = mirrored_sheet()
    half = sheet.shape[1] // 2
    k = DPI / 72
    sheet[760:830, 1050:1180] = 1  # a heavy stamp at the lower right of the sheet
    part[760:830, 20:150] = 1  # the part's own stamp, at its lower left
    zone_a = [[1050 / k, 760 / k, 1180 / k, 830 / k]]
    zone_b = [[20 / k, 760 / k, 150 / k, 830 / k]]
    found = reg.by_template(sheet, part, DPI, zone_a, zone_b)
    assert found is not None and found["accepted"] and abs(found["matrix"][0][2] * k - half) <= 1.0, found


def test_a_mask_over_the_phase_budget_is_reduced_and_the_place_is_known_to_the_reduction() -> None:
    sheet, part = mirrored_sheet(width=2400, height=1700, seed=5)  # 4.1 Mpx: a 2A0 sheet
    assert sheet.size > settings.PHASE_MAX_PIXELS
    found = reg.by_template(sheet, part, DPI, [], [])
    assert found is not None and found["accepted"] and found["uncertainty_pt"] > 72 / DPI, found  # more than one pixel of the mask
    assert abs(found["matrix"][0][2] * DPI / 72 - 1200) <= 2 * found["uncertainty_pt"] * DPI / 72, found


def test_the_agreement_of_a_part_is_judged_over_the_area_it_covers() -> None:
    """A quarter of a sheet placed exactly is a good registration. Over the whole sheet it would agree with a quarter of the
    ink at best (a Dice of 0.4, under ``ALIGN_MIN_DICE``), and the pair would be called unreliable."""
    sheet, _ = mirrored_sheet()
    quarter = sheet[:, : sheet.shape[1] // 4].copy()
    identity = np.eye(3)[:2]
    assert reg.dice(sheet, quarter, identity, DPI, [], crop=True) > 0.95
    assert reg.dice(sheet, quarter, identity, DPI, [], crop=False) < settings.ALIGN_MIN_DICE
    result = reg.register([], [], [], [], sheet, quarter, DPI, crop=True)
    assert result["reliable"] is True and result["method"] == "template", result


def test_without_the_part_flag_the_registration_is_the_old_one() -> None:
    """Only a ``split`` part is looked for inside the sheet; every other pair is registered as before."""
    sheet, part = mirrored_sheet()
    result = reg.register([], [], [], [], sheet, part, DPI, crop=False)
    assert all(attempt["method"] != "template" for attempt in result["attempts"]), result["attempts"]


# -- the corpus ----------------------------------------------------------------------------------------------------

def _overlap(a: list[float], b: list[float]) -> float:
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


@pytest.fixture(scope="module")
def parts(compare):
    """The two parts of the split sheet E05 (V5 pages 5 and 6) compared with the older sheet (V4 page 5) as a split."""
    return [compare("vs1/v4.pdf", 5, "vs1/v5.pdf", page, part="split") for page in (5, 6)]


def test_each_part_of_the_split_sheet_sits_in_its_own_region_of_the_older_sheet(parts, vs1_key) -> None:
    transition = next(t for t in vs1_key["transitions"] if (t.get("transition") or t.get("id")) == "V4->V5")
    sheet = next(s for s in transition["sheets"] if s["sheet_id"] == "E05")
    for computed, key_part in zip(parts, sheet["parts"]):
        outcome = computed.outcome["result"]
        # the key's translation is of the old sheet onto the new part: the part's place in A is its negative
        assert outcome["how_compared"]["transform"][4] == pytest.approx(-key_part["translation_x"], abs=0.1)
        assert outcome["how_compared"]["transform"][5] == pytest.approx(0.0, abs=0.1)
        region = key_part["region_in_old_sheet_x"]
        x0, _y0, x1, _y1 = outcome["part"]["area_a_pt"]
        assert region[0] - 1 <= x0 and x1 <= region[1] + 1, (key_part["to_page"], outcome["part"], region)
        assert outcome["part"]["reliable"] is True


def test_the_two_areas_do_not_overlap_and_the_ink_coverage_of_the_split_is_computed(parts) -> None:
    first, second = (p.outcome["result"]["part"] for p in parts)
    assert _overlap(first["area_a_pt"], second["area_a_pt"]) == 0.0, (first, second)
    covered = first["coverage_a"] + second["coverage_a"]
    assert 0.97 <= covered <= 1.0, covered


def test_the_series_accepts_the_two_areas_as_one_reliable_coverage(parts) -> None:
    """What `CMP-SERIES-01` does with them (`series/parts.py`): the sum of the ink shares, reliable, where it used to refuse."""
    from auditmanager.comparison.series.parts import PartFact, group_coverage

    facts = [PartFact(p.outcome["result"]["part"]["area_a_pt"], p.outcome["result"]["part"]["coverage_a"],
                      p.outcome["result"]["part"]["reliable"]) for p in parts]
    percent, reliable = group_coverage(60.71, facts)
    assert reliable is True and 97.0 <= percent <= 100.0, (percent, reliable)


def test_a_part_registered_in_its_own_region_has_the_differences_of_the_part_not_of_the_wrong_half(parts) -> None:
    """On the wrong half the second part showed 29 differences; in its own region it differs where the key says the
    parts differ, in the cut and the labels of the stamp."""
    assert len(parts[1].outcome["result"]["differences"]) <= 5
    assert "ALIGNMENT_UNRELIABLE" not in parts[1].outcome["reasons"]
