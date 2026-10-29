"""Part A of the specification, over PostgreSQL and the object store (`CMP-VC-SPEC-01`): the positions of a page and of a sheet pair.

The oracle is the answer key of the synthetic corpus (V4 to V5, sheet E07: position 7 added, position 6 removed, the quantity of
position 3 from 2 to 3). Page profiles are built by the real children; a series over the clone of the template gives the sheet
pairs the reads are addressed by. No worker runs, no engine child runs, no model is called.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.comparison.public import SpecificationReader
from auditmanager.comparison.specification import reader as reader_module
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import SPEC_PAGE


@pytest.fixture
def reader(sessions, blob_store) -> SpecificationReader:
    return SpecificationReader(sessions, blob_store)


def _spec_pair(lab: Any, series_id: str, transition_no: int, a_page: int, b_page: int) -> str:
    found = lab.rows(
        "SELECT p.comparison_sheet_pair_id AS id FROM comparison_sheet_pair p "
        "JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
        "JOIN comparison_page_profile pa ON pa.comparison_page_profile_id = p.page_a_profile_id "
        "JOIN comparison_page_profile pb ON pb.comparison_page_profile_id = p.page_b_profile_id "
        "WHERE t.comparison_series_id = :s AND t.transition_no = :t AND pa.page_number = :a AND pb.page_number = :b",
        s=series_id, t=transition_no, a=a_page, b=b_page)
    assert len(found) == 1, found
    return str(found[0]["id"])


def test_the_positions_of_a_specification_page_are_those_of_the_key(lab, reader, vs1_key) -> None:
    doc = lab.clone()
    view = reader.page_view(lab.profile_id(doc, 2, SPEC_PAGE["vs1/v5.pdf"]))
    transition = next(t for t in vs1_key["transitions"] if (t.get("transition") or t.get("id")) == "V4->V5")
    expected = next(s for s in transition["sheets"] if s["sheet_id"] == "E07")["spec_positions"]["positions_after"]
    assert view["is_specification"] is True and view["spec_version"] == "cmp-spec/1" and view["ambiguous_rows"] == 0
    assert [(p["pos"], p["mark"], p["name"], p["quantity"], p["mass"]) for p in view["positions"]] == [
        (e["position"], e["designation"], e["name"], e["quantity"], e["mass"]) for e in expected]
    assert all(p["page"]["page_number"] == 7 and p["page"]["version_uid"] == doc.versions[2] for p in view["positions"])
    assert all(p["page"]["page_profile_id"] == lab.profile_id(doc, 2, 7) for p in view["positions"])


def test_a_page_that_is_not_a_specification_has_no_positions(lab, reader) -> None:
    doc = lab.clone()
    for page in (1, 2, 3):
        view = reader.page_view(lab.profile_id(doc, 2, page))
        assert view["is_specification"] is False and view["positions"] == [] and view["ambiguous_rows"] == 0


def test_an_unknown_page_profile_is_not_found(reader) -> None:
    with pytest.raises(DomainError) as failure:
        reader.page_view("cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert failure.value.code is ErrorCode.NOT_FOUND


def test_the_sheet_pair_of_the_key_reports_the_three_position_changes(lab, reader, started, vs1_key) -> None:
    doc, series = started()
    pair = _spec_pair(lab, series["series_id"], 2, SPEC_PAGE["vs1/v4.pdf"], SPEC_PAGE["vs1/v5.pdf"])
    view = reader.pair_view(pair)
    assert view["sheet_pair_id"] == pair and view["is_specification"] is True
    assert view["totals"] == {"changed": 1, "added": 1, "removed": 1, "unclear": 0, "renumbered": 0, "moved": 0}
    kinds = {c["kind"]: c for c in view["changes"]}
    assert [c["kind"] for c in view["changes"]] == ["changed", "removed", "added"]
    assert kinds["changed"]["fields"] == [{"field": "quantity", "was": "2", "now": "3"}]
    assert kinds["changed"]["old"]["pos"] == "3" and kinds["changed"]["new"]["pos"] == "3"
    assert kinds["removed"]["old"]["pos"] == "6" and "new" not in kinds["removed"]
    assert kinds["added"]["new"]["pos"] == "7" and "old" not in kinds["added"]
    assert kinds["changed"]["old"]["page"]["version_uid"] == doc.versions[1] and kinds["changed"]["new"]["page"]["version_uid"] == doc.versions[2]
    assert all(1 <= len(c["text"]) <= 600 and c["change_id"].startswith("s") for c in view["changes"])


def test_an_unchanged_specification_sheet_pair_has_no_change(lab, reader, started) -> None:
    _, series = started()
    pair = _spec_pair(lab, series["series_id"], 1, SPEC_PAGE["vs1/v3.pdf"], SPEC_PAGE["vs1/v4.pdf"])
    view = reader.pair_view(pair)
    assert view["is_specification"] is True and view["changes"] == []
    assert set(view["totals"].values()) == {0}


def test_a_sheet_pair_that_is_not_a_specification_says_so(lab, reader, started) -> None:
    _, series = started()
    pair = _spec_pair(lab, series["series_id"], 2, 2, 2)
    view = reader.pair_view(pair)
    assert view["is_specification"] is False and view["changes"] == [] and set(view["totals"].values()) == {0}


def test_an_unknown_sheet_pair_is_not_found(reader) -> None:
    with pytest.raises(DomainError) as failure:
        reader.pair_view("ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert failure.value.code is ErrorCode.NOT_FOUND


def test_nothing_is_claimed_over_a_stream_with_a_hole(lab, reader, started, monkeypatch) -> None:
    """The mutation proof of the rule: if a specification page whose table could not be read were left out of the stream, the
    positions on it would read as removed (or added). The read says «specification» and lists no change."""
    _, series = started()
    pair = _spec_pair(lab, series["series_id"], 2, SPEC_PAGE["vs1/v4.pdf"], SPEC_PAGE["vs1/v5.pdf"])
    real = reader_module.parse_data
    seen: list[int] = []

    def parse(data):
        parsed = real(data)
        if data.row.page_number == SPEC_PAGE["vs1/v5.pdf"] and parsed is not None:
            seen.append(data.row.page_number)
            return {"parsed": False, "reason": "колонки таблицы не найдены"}
        return parsed

    monkeypatch.setattr(reader_module, "parse_data", parse)
    view = reader.pair_view(pair)
    assert seen and view["is_specification"] is True and view["changes"] == [] and set(view["totals"].values()) == {0}


def test_a_page_move_is_not_a_change_across_a_stream(lab, reader, started) -> None:
    """V3 and V4 have the specification on page 6 and V5 on page 7; V3 to V4 (page 6 to page 6) and V4 to V5 (page 6 to page 7)
    differ only by the three changes of the key: the move of the sheet from page 6 to page 7 is none of them."""
    _, series = started()
    pair = _spec_pair(lab, series["series_id"], 2, SPEC_PAGE["vs1/v4.pdf"], SPEC_PAGE["vs1/v5.pdf"])
    view = reader.pair_view(pair)
    assert sum(view["totals"].values()) == 3
