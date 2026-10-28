"""The contract-shaped dictionaries of the series (`CMP-SERIES-01`): raw evidence is copied, never rebuilt."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any

from auditmanager.comparison.series import views
from auditmanager.comparison.series.repository import SeriesRow, TransitionRow

EVIDENCE = {
    "format": 1,
    "canvas": {"width_pt": 1190.55, "height_pt": 841.89},
    "differences": [
        {"region_class": "text", "layer": "main", "box": {"x0": 1.5, "y0": 2.25, "x1": 3.0, "y1": 4.0}, "before_text": "3,0", "after_text": "3,6"},
        {"region_class": "line_style", "layer": "line_style", "box": {"x0": 0.1, "y0": 0.2, "x1": 0.30000000000000004, "y1": 0.4}},
    ],
    "text_changes": [{"kind": "changed", "before": "3,0", "after": "3,6", "numbers": [{"before": "3,0", "after": "3,6"}]}],
    "service_notes": [{"kind": "stamp", "change": "changed", "zone": "stamp", "field": "date", "before": "15.01.2026", "after": "12.02.2026"}],
    "how_compared": {"algo_version": "vc1.13", "dpi": 113, "tolerance_pt": 0.5, "transform": [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]},
    "aligned_blocks": [{"box_a": [0, 0, 1, 1], "dx_pt": 1.0, "dy_pt": 2.0}],
    "mask": {"format": 1, "dpi": 113, "width_px": 10, "height_px": 10},
    "part": {"kind": "split", "area_a_pt": [0, 0, 1, 1], "coverage_a": 0.5, "reliable": True},
}


def row(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "comparison_sheet_pair_id": "ctp_1", "comparison_transition_id": "ctn_1", "pair_no": 1, "state": "done",
        "status": "different", "page_a_profile_id": "cpr_a", "page_b_profile_id": "cpr_b", "confidence": "high",
        "flags": ["duplicate"], "result_id": "csp_1", "ai_dependent": False, "permit": None, "parts": None,
        "failure_reason": None,
        "a_version": "ver_a", "a_number": 3, "a_sheet": "3", "a_title": "Схема", "a_scan": False,
        "b_version": "ver_b", "b_number": 3, "b_sheet": "3", "b_title": "Схема", "b_scan": True,
        "r_channels": {"text": {"state": "checked", "diffs": 1}}, "r_reasons": ["DUPLICATE_SHEET"],
        "r_result": copy.deepcopy(EVIDENCE),
    }
    return base | changes


def test_the_evidence_members_are_copied_verbatim_and_the_engines_own_are_not_exposed() -> None:
    out = views.pair_dict(row(), with_evidence=True)
    for member in views.EVIDENCE_MEMBERS:
        assert out[member] == EVIDENCE[member]
        # the same bytes, not a rebuilt value: a float like 0.30000000000000004 survives a JSON round trip unchanged
        assert json.dumps(out[member], sort_keys=True) == json.dumps(EVIDENCE[member], sort_keys=True)
    assert not {"format", "aligned_blocks", "mask", "part"} & set(out)
    assert out["channels"] == {"text": {"state": "checked", "diffs": 1}} and out["reasons"] == ["DUPLICATE_SHEET"]


def test_the_list_form_carries_no_evidence() -> None:
    out = views.pair_dict(row(), with_evidence=False)
    assert not set(views.EVIDENCE_MEMBERS) & set(out)
    assert out["page_a"] == {"page": {"version_uid": "ver_a", "page_number": 3, "page_profile_id": "cpr_a"},
                             "sheet_number": "3", "title": "Схема", "scan": False}
    assert out["page_b"]["scan"] is True


def test_a_one_sided_pair_has_one_page_and_no_result() -> None:
    out = views.pair_dict(
        row(status="added", page_a_profile_id=None, result_id=None, confidence=None, flags=[], r_channels=None,
            r_reasons=None, r_result=None, a_version=None, a_number=None, a_sheet=None, a_title=None, a_scan=None),
        with_evidence=True,
    )
    assert "page_a" not in out and out["page_b"]["page"]["page_profile_id"] == "cpr_b"
    assert not {"result_id", "channels", "reasons", "confidence", "flags", "canvas"} & set(out)
    assert out["status"] == "added" and out["ai_dependent"] is False


def test_the_series_reasons_follow_the_raw_ones_and_the_working_members_of_parts_stay_inside() -> None:
    parts = {"kind": "split", "role": "part", "source_profile_id": "cpr_a", "text_percent": 90.0, "covered_percent": 99.5,
             "coverage_reliable": True, "parts": [{"version_uid": "ver_b", "page_number": 6}], "series_reasons": ["SPLIT_SHEET"]}
    out = views.pair_dict(row(parts=parts, r_reasons=["DUPLICATE_SHEET", "SPLIT_SHEET"]), with_evidence=False)
    assert out["reasons"] == ["DUPLICATE_SHEET", "SPLIT_SHEET"]  # not twice
    out = views.pair_dict(row(parts=parts, r_reasons=["DUPLICATE_SHEET"]), with_evidence=False)
    assert out["reasons"] == ["DUPLICATE_SHEET", "SPLIT_SHEET"]
    assert out["parts"] == {"role": "part", "covered_percent": 99.5, "parts": [{"version_uid": "ver_b", "page_number": 6}]}


def test_a_failed_pair_says_why() -> None:
    out = views.pair_dict(row(state="failed", status=None, result_id=None, failure_reason="series_item_failed", r_channels=None,
                              r_reasons=None, r_result=None), with_evidence=True)
    assert out["state"] == "failed" and out["failure_reason"] == "series_item_failed" and "status" not in out


def test_the_series_and_the_transition() -> None:
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    series = SeriesRow("cser_1", "prj_1", "doc_1", "running", "cvo_1", "cmx_1", 3, "0" * 64, "cser_0", None, "usr_1", now, now)
    transition = TransitionRow("ctn_1", "cser_1", 1, "ver_a", "ver_b", "completed", {"sheets": 1}, ["different"], None)
    t = views.transition_dict(transition, items_total=2, items_done=2, summary={"sheets": 1})
    assert t["verdict"] == ["different"] and t["summary"] == {"sheets": 1} and "failure_reason" not in t
    s = views.series_dict(series, transitions_total=1, transitions_done=1, stale_reasons=["order_changed"], transitions=[t])
    assert s["matrix_revision"] == {"matrix_id": "cmx_1", "edit_no": 3} and s["order_id"] == "cvo_1"
    assert s["restarted_from"] == "cser_0" and s["stale_reasons"] == ["order_changed"] and s["transitions"] == [t]
    bare = views.series_dict(series, transitions_total=0,
                             transitions_done=0, stale_reasons=[], transitions=None)
    assert "transitions" not in bare and "stale_reasons" not in bare
    running = views.transition_dict(
        TransitionRow("ctn_2", "cser_1", 2, "ver_b", "ver_c", "running", None, None, None), items_total=3, items_done=1,
        summary={"sheets": 3})
    assert "verdict" not in running  # absent until the transition has run
