"""The post-phases after the sheet loop (`CMP-SERIES-01`; the original's ``_parts_phase`` and ``_permit_phase``): the parts
coverage of a split sheet, the reconciliation of the permit's declared changes with the found ones, and the rule that
neither touches the engine's result row."""

from __future__ import annotations

import json
from typing import Any

import pytest

from .support import ScriptedEngine, build, drain, pair_rows, runner_with, start


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def sheet_of(lab, profile_id: str) -> tuple[int, str | None]:
    row = lab.rows("SELECT page_number, profile->'stamp'->>'sheet_number' AS sheet FROM comparison_page_profile "
                   "WHERE comparison_page_profile_id = :i", i=profile_id)[0]
    return int(row["page_number"]), row["sheet"]


def run(lab, sessions, engine, blob_store, worker_id, doc, fake) -> None:
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)


def split_pairs(lab, series_id: str) -> list[dict[str, Any]]:
    return [p for p in pair_rows(lab, series_id) if p["transition_no"] == 4 and p["parts"]]


def test_the_two_parts_of_a_split_sheet_cover_the_sheet_and_each_is_a_review(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    parts = split_pairs(lab, series["series_id"])
    assert len(parts) == 2 and {p["a"] for p in parts} == {parts[0]["a"]}  # both name the older sheet as page A
    fake = ScriptedEngine(sessions, part_script={
        (parts[0]["a"], parts[0]["b"]): {"area_a_pt": [0, 0, 1190, 841], "coverage_a": 0.5, "reliable": True},
        (parts[1]["a"], parts[1]["b"]): {"area_a_pt": [1193, 0, 2384, 841], "coverage_a": 0.49, "reliable": True},
    })
    run(lab, sessions, engine, blob_store, worker_id, doc, fake)
    fourth = service.get_series(series_id=series["series_id"])["transitions"][3]
    assert fourth["state"] == "completed" and fourth["verdict"] == ["needs_review"]
    for part in split_pairs(lab, series["series_id"]):
        shown = service.get_sheet_pair(sheet_pair_id=part["id"])
        assert shown["status"] == "needs_review" and "SPLIT_SHEET" in shown["reasons"]
        assert shown["parts"]["role"] == "part" and shown["parts"]["covered_percent"] == 99.0
        assert len(shown["parts"]["parts"]) == 1 and shown["parts"]["parts"][0]["version_uid"] == doc.versions[4]
        # the engine's own row is untouched: its status is the engine's, the review is the series' verdict (the first
        # part was linked with medium confidence, a forcing reason of the engine's; the second was not)
        row = lab.rows("SELECT status, reasons FROM comparison_sheet_pair_result WHERE comparison_sheet_pair_result_id = :r",
                       r=shown["result_id"])[0]
        assert "SPLIT_SHEET" not in row["reasons"]
        assert row["status"] == ("needs_review" if part["confidence"] == "medium" else "same")
    assert [p["parts"]["coverage_reliable"] for p in split_pairs(lab, series["series_id"])] == [True, True]


def test_a_part_whose_registration_is_not_reliable_leaves_the_text_coverage_marked_unreliable(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    parts = split_pairs(lab, series["series_id"])
    fake = ScriptedEngine(sessions, part_script={
        (parts[0]["a"], parts[0]["b"]): {"area_a_pt": [0, 0, 1190, 841], "coverage_a": 0.5, "reliable": False},
        (parts[1]["a"], parts[1]["b"]): {"area_a_pt": [1193, 0, 2384, 841], "coverage_a": 0.49, "reliable": True},
    })
    run(lab, sessions, engine, blob_store, worker_id, doc, fake)
    for part in split_pairs(lab, series["series_id"]):
        assert part["parts"]["coverage_reliable"] is False
        assert part["parts"]["covered_percent"] == part["parts"]["text_percent"]
        assert service.get_sheet_pair(sheet_pair_id=part["id"])["status"] == "needs_review"


def test_the_permit_of_the_fourth_version_is_reconciled_with_the_found_changes_as_the_key_says(
    lab, sessions, engine, blob_store, worker_id, service, vs1_key, prepared,
) -> None:
    doc, series = prepared
    third = [p for p in pair_rows(lab, series["series_id"]) if p["transition_no"] == 3]
    statuses = {1: "different", 2: "same", 3: "different", 4: "needs_review", 5: "different", 6: "same"}  # the key's V3 -> V4
    script = {(p["a"], p["b"]): statuses[sheet_of(lab, p["b"])[0]] for p in third}
    run(lab, sessions, engine, blob_store, worker_id, doc, ScriptedEngine(sessions, script=script))

    key = vs1_key["transitions"][2]["permit"]
    # the scan of the fourth sheet has no text, so no stamp: the pair says the older sheet is the same sheet
    by_sheet = {sheet_of(lab, p["b"])[1] or sheet_of(lab, p["a"])[1]: service.get_sheet_pair(sheet_pair_id=p["id"])
                for p in pair_rows(lab, series["series_id"]) if p["transition_no"] == 3}
    expected = {"5": "declared_and_found", "7": "declared_no_diff", "4": "needs_review", "3": "diff_not_declared"}
    assert {sheet: shown["permit"]["state"] for sheet, shown in by_sheet.items() if "permit" in shown} == expected
    for entry in key["declared"]:
        assert [i["text"] for i in by_sheet[entry["sheet_no"]]["permit"]["items"]] == [entry["text"]]
    assert by_sheet["3"]["permit"]["items"] == []  # found, not declared: nothing was declared
    assert "permit" not in by_sheet["1"] and "permit" not in by_sheet["2"]  # the sheet that carries the permit; an unchanged sheet
    # and the classes agree with the key's own names
    assert {k: sorted(v) for k, v in key["classes"].items()} == {
        "declared_and_found": ["E05"], "declared_not_found": ["E07"], "declared_unverifiable_scan": ["E04"],
        "found_not_declared": ["E03"]}


def test_a_transition_whose_newer_version_has_no_permit_gets_no_permit_record(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    run(lab, sessions, engine, blob_store, worker_id, doc, ScriptedEngine(sessions))
    first = [p for p in pair_rows(lab, series["series_id"]) if p["transition_no"] == 1]
    assert all(p["permit"] is None for p in first)


def test_the_result_jsonb_is_copied_verbatim_into_the_pair_and_nothing_else_is(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    evidence = {
        "canvas": {"width_pt": 1190.55, "height_pt": 841.89},
        "differences": [{"region_class": "text", "layer": "main", "box": {"x0": 0.1, "y0": 0.30000000000000004, "x1": 5.5, "y1": 6.0},
                         "before_text": "3,0", "after_text": "3,6"}],
        "text_changes": [{"kind": "changed", "before": "3,0", "after": "3,6", "numbers": [{"before": "3,0", "after": "3,6"}]}],
        "service_notes": [{"kind": "stamp", "change": "changed", "zone": "stamp", "field": "date", "before": "15.01", "after": "12.02"}],
        "how_compared": {"algo_version": "scripted", "dpi": 113, "tolerance_pt": 0.5, "transform": [1.0, 0.0, 0.0, 1.0, 0.25, -0.5]},
    }
    first = [p for p in pair_rows(lab, series["series_id"]) if p["transition_no"] == 1 and p["state"] == "queued"]
    run(lab, sessions, engine, blob_store, worker_id, doc,
        ScriptedEngine(sessions, script={(first[0]["a"], first[0]["b"]): "different"}, evidence=evidence))
    shown = service.get_sheet_pair(sheet_pair_id=first[0]["id"])
    stored = lab.rows("SELECT result, channels, reasons FROM comparison_sheet_pair_result WHERE comparison_sheet_pair_result_id = :r",
                      r=shown["result_id"])[0]
    for member in ("canvas", "differences", "text_changes", "service_notes", "how_compared"):
        assert json.dumps(shown[member], sort_keys=True) == json.dumps(stored["result"][member], sort_keys=True), member
    assert shown["channels"] == stored["channels"] and shown["reasons"] == stored["reasons"]
    assert not {"format", "aligned_blocks", "mask", "part"} & set(shown)
