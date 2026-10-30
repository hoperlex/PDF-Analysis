"""Registration refusal, native B boxes and deterministic raw-region identities."""

from types import SimpleNamespace

import pytest

from auditmanager.comparison.stage_graphic.evidence import inverse_box, project_result
from auditmanager.comparison.stage_graphic.service import StageGraphicService


def _stored(*, reasons=(), transform=(1, 0, 0, 1, 10, 20), region_class="graphic_changed"):
    return SimpleNamespace(result_id="result", algo_version="engine", content_key="content",
        page_a_profile_id="left", page_b_profile_id="right", reasons=list(reasons),
        channels={"geometry": {"state": "checked", "diffs": 1}, "color": {"state": "checked", "diffs": 0}},
        result={"how_compared": {"transform": list(transform), "dpi": 200}, "differences": [{
            "region_class": region_class, "layer": "main", "box": {"x": 50, "y": 60, "width": 20, "height": 30}}]})


def test_right_crop_uses_inverse_transform_and_preserves_engine_proof():
    result = _stored()
    status, reason, regions = project_result(result, left_size=(200, 200), right_size=(200, 200))
    assert (status, reason) == ("reliable", "graphics_compared")
    assert regions[0]["left_box"] == [50, 60, 70, 90]
    assert regions[0]["right_box"] == [40, 40, 60, 70]
    assert regions[0]["registration"]["transform_direction"] == "right_to_left"
    assert regions[0]["registration"]["result_id"] == "result"
    assert project_result(result, left_size=(200, 200), right_size=(200, 200))[2] == regions


@pytest.mark.parametrize("reason,expected", [("ALIGNMENT_UNRELIABLE", "unreliable"),
    ("ALIGNMENT_PARTIAL", "unreliable"), ("PARTIAL_COVERAGE", "unreliable"),
    ("RENDER_FAILED", "not_checked"), ("PAGE_TOO_LARGE", "not_checked")])
def test_no_graphic_claim_survives_registration_or_render_refusal(reason, expected):
    status, _, regions = project_result(_stored(reasons=[reason]), left_size=(200, 200), right_size=(200, 200))
    assert status == expected and regions == []


def test_text_only_difference_is_not_relabelled_as_graphics_and_empty_is_checked():
    status, reason, regions = project_result(_stored(region_class="text"), left_size=(200, 200), right_size=(200, 200))
    assert (status, reason, regions) == ("reliable", "graphics_compared_no_regions", [])


def test_singular_transform_cannot_give_reliable_evidence():
    status, _, regions = project_result(_stored(transform=(0, 0, 0, 0, 0, 0)), left_size=(200, 200), right_size=(200, 200))
    assert status == "unreliable" and not regions
    assert inverse_box((0, 1, -1, 0, 100, 0), (60, 10, 80, 30)) == (10, 20, 30, 40)


@pytest.mark.parametrize("changes,reason", [({"relation": "only_left"}, "graphics_not_checked_unpaired_link"),
    ({"left_degree": 2}, "graphics_not_checked_many_to_many"),
    ({"confidence": "review"}, "graphics_not_checked_source_link_uncertain"),
    ({"right_status": "refused"}, "graphics_not_checked_profile_unavailable")])
def test_only_degree_one_ready_unambiguous_links_reach_engine(changes, reason):
    link = {"relation": "paired", "left_profile_id": "left", "right_profile_id": "right",
            "left_degree": 1, "right_degree": 1, "confidence": "manual", "left_status": "ready", "right_status": "ready"}
    assert StageGraphicService._refusal(link | changes) == reason
