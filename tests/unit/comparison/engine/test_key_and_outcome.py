"""The content key (ADR-0025 decision 15) and the shape of an outcome (wave brief section 4 item 3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditmanager.comparison.engine.child import result as res
from auditmanager.comparison.engine.child import settings
from auditmanager.comparison.engine.key import content_key, page_part
from auditmanager.comparison.engine.validate import ResultInvalid, validate_outcome
from auditmanager.comparison.profile.models import PageProfileRow

PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def row(merkle: str | None = "a" * 64, annotations: tuple[str, ...] = (), status: str = "ready", key: str = "k" * 64,
        algo: str = "cmp-profile/1") -> PageProfileRow:
    return PageProfileRow(
        page_profile_id="cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", page_number=1,
        content_key=key, algo_version=algo, status=status, reason=None if status == "ready" else "RENDER_FAILED",
        summary={"content_merkle": merkle, "annotation_hashes": list(annotations)}, profile_blob_id=None,
        preview_blob_id=None, thumbnail_blob_id=None, created_at=datetime.now(timezone.utc))


A, B = row("a" * 64), row("b" * 64)


def test_the_same_inputs_give_the_same_key() -> None:
    assert content_key(PROJECT, A, B) == content_key(PROJECT, A, B)
    assert len(content_key(PROJECT, A, B)) == 64


def test_a_changed_byte_of_either_page_changes_the_key() -> None:
    base = content_key(PROJECT, A, B)
    assert content_key(PROJECT, row("a" * 63 + "0"), B) != base
    assert content_key(PROJECT, A, row("b" * 63 + "0")) != base


def test_another_project_does_not_share_the_key() -> None:
    assert content_key("prj_01ARZ3NDEKTSV4RRFFQ69G5FAW", A, B) != content_key(PROJECT, A, B)


def test_the_pair_is_ordered_older_then_newer() -> None:
    assert content_key(PROJECT, A, B) != content_key(PROJECT, B, A)


def test_an_annotation_only_change_changes_the_key_and_their_order_does_not() -> None:
    base = content_key(PROJECT, A, B)
    assert content_key(PROJECT, row("a" * 64, ("h1",)), B) != base
    assert content_key(PROJECT, row("a" * 64, ("h1", "h2")), B) == content_key(PROJECT, row("a" * 64, ("h2", "h1")), B)


def test_the_link_reasons_and_the_split_part_are_in_the_key_and_the_order_of_reasons_is_not() -> None:
    base = content_key(PROJECT, A, B)
    assert content_key(PROJECT, A, B, reasons=["MATCH_LOW_CONFIDENCE"]) != base
    assert content_key(PROJECT, A, B, part="split") != base and content_key(PROJECT, A, B, part="floors") != content_key(PROJECT, A, B, part="split")
    assert content_key(PROJECT, A, B, reasons=["X", "Y"]) == content_key(PROJECT, A, B, reasons=["Y", "X", "X"])


def test_a_change_of_the_algorithm_version_changes_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.comparison.engine import key

    base = content_key(PROJECT, A, B)
    monkeypatch.setattr(key, "ALGO_VERSION", "cmp-engine/9")
    assert content_key(PROJECT, A, B) != base


def test_a_result_stored_under_the_first_version_of_the_engine_is_not_found_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """`CMP-C1-FIX-A` item 1: the first engine wrote ``UNCHECKED_CHANNEL:<channel>``. Its ``ALGO_VERSION`` is in the content
    key, so the key a result of ``cmp-engine/1`` was stored under is not the key of today and the pair is compared again."""
    from auditmanager.comparison.engine import key

    current = content_key(PROJECT, A, B)
    monkeypatch.setattr(key, "ALGO_VERSION", "cmp-engine/1")
    assert content_key(PROJECT, A, B) != current
    assert settings.ALGO_VERSION != "cmp-engine/1"


def test_a_result_stored_before_the_split_parts_were_registered_in_their_own_region_is_not_found_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """`CMP-C1-FIX-A` item 2: ``cmp-engine/2`` registered the second part of a split sheet onto the first part's region."""
    from auditmanager.comparison.engine import key

    current = content_key(PROJECT, A, B, part="split")
    monkeypatch.setattr(key, "ALGO_VERSION", "cmp-engine/2")
    assert content_key(PROJECT, A, B, part="split") != current
    assert settings.ALGO_VERSION not in ("cmp-engine/1", "cmp-engine/2")


def test_a_result_stored_before_the_specification_positions_were_read_is_not_found_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """`CMP-VC-SPEC-01`: ``cmp-engine/3`` left the channel ``spec_positions`` ``unchecked`` whenever the graphics of a specification
    sheet differed. Its ``ALGO_VERSION`` is in the content key, so a result stored under it is compared again."""
    from auditmanager.comparison.engine import key

    current = content_key(PROJECT, A, B)
    monkeypatch.setattr(key, "ALGO_VERSION", "cmp-engine/3")
    assert content_key(PROJECT, A, B) != current
    assert settings.ALGO_VERSION == "cmp-engine/4"


def test_a_change_of_a_threshold_is_a_change_of_the_parameters_in_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.comparison.engine import key

    base = content_key(PROJECT, A, B)
    monkeypatch.setattr(key, "PARAMS", {**settings.PARAMS, "dark": 190})
    assert content_key(PROJECT, A, B) != base


def test_a_page_with_no_merkle_is_keyed_by_the_content_key_of_its_profile() -> None:
    failed_1, failed_2 = row(None, status="needs_review", key="1" * 64), row(None, status="needs_review", key="2" * 64)
    assert page_part(failed_1)["merkle"] is None and page_part(failed_1)["profile"] == "1" * 64
    assert content_key(PROJECT, failed_1, B) != content_key(PROJECT, failed_2, B)


def test_the_profile_algorithm_is_in_the_key() -> None:
    assert content_key(PROJECT, row(algo="cmp-profile/2"), B) != content_key(PROJECT, A, B)


# -- the outcome -----------------------------------------------------------------------------------------------

def test_a_failed_outcome_validates_and_is_not_same() -> None:
    outcome = res.failure_outcome("RENDER_FAILED", "не удалось")
    validate_outcome(outcome["channels"], outcome["result"])
    assert outcome["status"] == "needs_review" and outcome["result"]["format"] == 1 and outcome["result"]["mask"] is None


def test_an_identical_outcome_is_same_without_a_mask_and_with_the_channels_of_the_original() -> None:
    outcome = res.identical_outcome(width_pt=595.0, height_pt=842.0, dpi=200, reasons=[], annotation_diffs=0,
                                    has_annotations=False, service_notes=[], is_spec=False)
    validate_outcome(outcome["channels"], outcome["result"])
    assert outcome["status"] == "same" and outcome["result"]["mask"] is None
    assert outcome["channels"]["annotations"]["state"] == "not_applicable" and outcome["channels"]["geometry"] == {"state": "checked", "diffs": 0}


def test_an_identical_outcome_with_a_medium_link_is_needs_review_and_with_an_annotation_change_is_different() -> None:
    low = res.identical_outcome(width_pt=1.0, height_pt=1.0, dpi=72, reasons=["MATCH_LOW_CONFIDENCE"], annotation_diffs=0,
                                has_annotations=False, service_notes=[], is_spec=False)
    assert low["status"] == "needs_review"
    annotated = res.identical_outcome(width_pt=1.0, height_pt=1.0, dpi=72, reasons=[], annotation_diffs=2, has_annotations=True,
                                      service_notes=[], is_spec=False)
    assert annotated["status"] == "different" and annotated["channels"]["annotations"]["diffs"] == 2


def test_the_validator_refuses_a_member_the_contract_does_not_allow() -> None:
    outcome = res.failure_outcome("RENDER_FAILED", "x")
    bad = {**outcome["result"], "differences": [{"region_class": "Bad Class", "layer": "main", "box": {"x": 0, "y": 0, "width": 1, "height": 1}}]}
    with pytest.raises(ResultInvalid):
        validate_outcome(outcome["channels"], bad)
    too_many = {**outcome["result"], "service_notes": [{"kind": "field", "change": "changed"}] * 501}
    with pytest.raises(ResultInvalid):
        validate_outcome(outcome["channels"], too_many)
    with pytest.raises(ResultInvalid):
        validate_outcome({**outcome["channels"], "geometry": {"state": "checked", "diffs": -1}}, outcome["result"])
    with pytest.raises(ResultInvalid):
        validate_outcome(outcome["channels"], {**outcome["result"], "format": 2})


def test_a_result_is_capped_at_the_limits_of_its_schemas() -> None:
    many = [{"region_class": "text", "layer": "main", "box": {"x": 0, "y": 0, "width": 1, "height": 1}}] * 2500
    built = res.build_result(width_pt=1, height_pt=1, dpi=72, matrix_pdf=[1, 0, 0, 1, 0, 0], differences=many,
                             text_changes=[{"kind": "added"}] * 2500, service_notes=[{"kind": "field", "change": "added"}] * 700,
                             aligned_blocks=[])
    assert (len(built["differences"]), len(built["text_changes"]), len(built["service_notes"])) == (2000, 2000, 500)


def test_every_region_class_maps_to_a_class_and_a_layer_of_the_contract() -> None:
    from auditmanager.api.schemas.models import ComparisonLayer

    layers = {m.value for m in ComparisonLayer}
    for name, (region_class, layer) in res.REGION_CLASSES.items():
        assert layer in layers and region_class.replace("_", "").isalpha()
    assert {c for c, _ in res.REGION_CLASSES.values()} == {
        "text", "text_moved", "graphic_added", "graphic_removed", "graphic_changed", "color_change", "light_fill",
        "line_style", "block_moved", "shifted"}


def test_a_difference_and_a_text_change_are_built_for_the_contract() -> None:
    region = {"class": "changed", "bbox_a_pt": [10.0, 20.0, 40.0, 30.0], "text_before": ["а", "б"], "text_after": [], "moved_text": []}
    d = res.difference(region)
    assert d == {"region_class": "graphic_changed", "layer": "main", "box": {"x": 10.0, "y": 20.0, "width": 30.0, "height": 10.0}, "before_text": "а б"}
    c = res.text_change({"kind": "changed", "norm": "spaces", "before": "a b", "after": "ab", "numbers": [{"before": "1", "after": "2"}, {"before": "3", "after": ""}],
                         "a_bbox": [1, 2, 3, 4], "b_in_a_bbox": None})
    assert c["kind"] == "changed_spaces" and c["numbers"] == [{"before": "1", "after": "2"}] and c["box"]["width"] == 2.0


def test_the_validator_refuses_a_reason_the_contract_cannot_carry_and_accepts_the_engines() -> None:
    """`CMP-C1-FIX-A` item 1: ``UNCHECKED_CHANNEL:text`` (a colon, lower case) never reaches a stored row."""
    outcome = res.failure_outcome("RENDER_FAILED", "x")
    validate_outcome(outcome["channels"], outcome["result"], outcome["reasons"])
    for bad in ("UNCHECKED_CHANNEL:text", "lower", "AB", "A" * 65, "1ABC", "ABC\n", ""):
        with pytest.raises(ResultInvalid):
            validate_outcome(outcome["channels"], outcome["result"], [*outcome["reasons"], bad])
    with pytest.raises(ResultInvalid):
        validate_outcome(outcome["channels"], outcome["result"], [f"REASON_{n}" for n in range(33)])
