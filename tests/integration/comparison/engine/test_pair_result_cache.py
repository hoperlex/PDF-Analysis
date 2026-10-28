"""The pair result against PostgreSQL, MinIO and the real children (`CMP-ENGINE-01`, ADR-0025 decisions 7, 8, 9, 15).

VS-1 `v1.pdf` and `v2.pdf` are seeded as published versions of one project and profiled by the real page children; the
pairs are the corpus' own: E01 is byte-identical, E02 has a moved label, E05 has an annotation only.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from sqlalchemy import text

FIXTURES = __import__('pathlib').Path(__file__).resolve().parents[4] / 'fixtures' / 'comparison'

from auditmanager.comparison.engine import PairResultRepository, compare_sheet_pair, decode_mask
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.db import session_scope


@pytest.fixture
def two_versions(lane):
    project = lane.project()
    return lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)


def compare(lane, a, b, pa: int | None, pb: int | None, **kw):
    return compare_sheet_pair(
        lane.sessions, lane.blob_store, project_uid=a.project_uid,
        page_a_profile_id=None if pa is None else a.pages[pa], page_b_profile_id=None if pb is None else b.pages[pb], **kw)


def test_a_pair_is_compared_written_with_its_mask_and_found_again_without_a_second_computation(lane, two_versions) -> None:
    v1, v2 = two_versions
    first = compare(lane, v1, v2, 2, 2)
    assert first.created is True and first.cached is False and first.status == "different" and first.result_id.startswith("csp_")
    rows = lane.results(v1.project_uid)
    assert len(rows) == 1
    row = rows[0]
    assert (row["status"], row["page_a_profile_id"], row["page_b_profile_id"]) == ("different", v1.pages[2], v2.pages[2])
    assert row["result"]["format"] == 1 and row["channels"]["text"]["state"] == "checked" and row["channels"]["text"]["diffs"] >= 1
    info = row["result"]["mask"]
    assert info["format"] == 1 and info["dpi"] == row["result"]["how_compared"]["dpi"]

    # The mask blob is a stored, available blob of format 1 over the declared grid.
    assert row["mask_blob_id"] == first.mask_blob_id and lane.blob_state(row["mask_blob_id"]) == "available"
    from auditmanager.storage.public import parse_blob_id

    decoded = decode_mask(lane.blob_store.read(parse_blob_id(row["mask_blob_id"]), verify=True))
    assert (decoded.width_px, decoded.height_px) == (info["width_px"], info["height_px"])
    assert decoded.plane("main").any() and decoded.plane("service_zones").any()

    again = compare(lane, v1, v2, 2, 2)
    assert (again.created, again.cached, again.result_id) == (False, True, first.result_id)
    assert len(lane.results(v1.project_uid)) == 1


def test_a_pair_of_the_same_content_is_same_and_holds_no_mask_and_no_blob(lane, two_versions) -> None:
    v1, v2 = two_versions
    outcome = compare(lane, v1, v2, 1, 1)
    assert outcome.status == "same" and outcome.created and outcome.mask_blob_id is None and outcome.child_end == "identical"
    row = lane.results(v1.project_uid)[0]
    assert row["mask_blob_id"] is None and row["result"]["mask"] is None and row["reasons"] == []
    assert all(c["state"] != "unchecked" for c in row["channels"].values())


def test_an_annotation_only_change_is_different_in_annotations_and_nowhere_else(lane, two_versions) -> None:
    v1, v2 = two_versions
    outcome = compare(lane, v1, v2, 5, 5)
    row = lane.results(v1.project_uid)[0]
    assert outcome.status == "different"
    assert row["channels"]["annotations"] == {"state": "checked", "diffs": 1}
    assert all(row["channels"][c].get("diffs", 0) == 0 for c in ("geometry", "color", "text", "zones"))
    assert [n["kind"] for n in row["result"]["service_notes"]] == ["annotation"]


def test_a_sheet_with_no_partner_needs_no_result_and_writes_nothing(lane, two_versions) -> None:
    v1, v2 = two_versions
    assert (compare(lane, v1, v2, None, 3).status, compare(lane, v1, v2, 3, None).status) == ("added", "removed")
    assert compare(lane, v1, v2, None, 3).result_id is None and lane.results(v1.project_uid) == []
    with pytest.raises(ValueError):
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=v1.project_uid, page_a_profile_id=None, page_b_profile_id=None)


def test_another_project_does_not_share_the_row_nor_the_pages(lane, two_versions) -> None:
    v1, v2 = two_versions
    first = compare(lane, v1, v2, 2, 2)
    other = lane.project()
    w1, w2 = lane.seed("vs1/v1.pdf", 6, project_uid=other), lane.seed("vs1/v2.pdf", 6, project_uid=other)
    second = compare(lane, w1, w2, 2, 2)
    assert second.created is True and second.result_id != first.result_id
    assert len(lane.results(v1.project_uid)) == 1 and len(lane.results(other)) == 1
    with pytest.raises(DomainError) as refusal:  # the pages of one project are not the pages of another
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=other, page_a_profile_id=v1.pages[2], page_b_profile_id=w2.pages[2])
    assert refusal.value.code is ErrorCode.NOT_FOUND


def test_a_medium_link_gives_needs_review_even_for_pages_of_the_same_content(lane, two_versions) -> None:
    v1, v2 = two_versions
    plain = compare(lane, v1, v2, 1, 1)
    medium = compare(lane, v1, v2, 1, 1, link_reasons=["MATCH_LOW_CONFIDENCE"])
    assert (plain.status, medium.status) == ("same", "needs_review") and plain.result_id != medium.result_id
    assert "MATCH_LOW_CONFIDENCE" in lane.results(v1.project_uid)[1]["reasons"]


def test_the_split_part_and_the_reasons_are_part_of_the_key(lane, two_versions) -> None:
    v1, v2 = two_versions
    ids = {compare(lane, v1, v2, 1, 1).result_id, compare(lane, v1, v2, 1, 1, part="split").result_id,
           compare(lane, v1, v2, 1, 1, link_reasons=["DUPLICATE_SHEET"]).result_id}
    assert len(ids) == 3 and len(lane.results(v1.project_uid)) == 3


def test_the_mask_blob_is_available_before_the_row_names_it(lane, two_versions, monkeypatch: pytest.MonkeyPatch) -> None:
    v1, v2 = two_versions
    seen: list[str | None] = []
    insert = PairResultRepository.insert

    def spy(self, session, **kw):
        seen.append(lane.blob_state(kw["mask_blob_id"]) if kw["mask_blob_id"] else None)
        return insert(self, session, **kw)

    monkeypatch.setattr(PairResultRepository, "insert", spy)
    compare(lane, v1, v2, 3, 3)
    assert seen == ["available"]


def test_a_blob_that_could_not_be_written_leaves_no_row(lane, two_versions, monkeypatch: pytest.MonkeyPatch) -> None:
    v1, v2 = two_versions

    def refuse(self, payload, *, role, media_type):
        raise RuntimeError("the object store is down")

    monkeypatch.setattr(ProfileBlobPublisher, "publish", refuse)
    with pytest.raises(RuntimeError):
        compare(lane, v1, v2, 2, 2)
    assert lane.results(v1.project_uid) == []
    monkeypatch.undo()
    assert compare(lane, v1, v2, 2, 2).created is True  # and the pair can be written once the store is back


def test_two_workers_computing_one_pair_write_one_row(lane, two_versions) -> None:
    v1, v2 = two_versions
    barrier = threading.Barrier(2)
    outcomes: list[Any] = []

    def work() -> None:
        barrier.wait()
        outcomes.append(compare(lane, v1, v2, 3, 3))

    threads = [threading.Thread(target=work) for _ in range(2)]
    [t.start() for t in threads]
    [t.join(timeout=120) for t in threads]
    assert len(outcomes) == 2 and outcomes[0].result_id == outcomes[1].result_id
    assert sorted(o.created for o in outcomes) in ([False, True], [False, False])  # the loser reads the winner's row
    assert len(lane.results(v1.project_uid)) == 1


def test_a_scan_with_one_replaced_image_byte_is_not_the_same_pair(lane, tmp_path) -> None:
    """ADR-0025 decision 15: a scan with a replaced image is not ``same``. The page's Merkle holds the image's bytes."""
    from auditmanager.comparison.engine.child.words import MM  # noqa: F401 - keeps the import graph honest

    original = (FIXTURES / "vs1/v4.pdf").read_bytes()
    at = original.index(b"\xff" * 64, original.index(b"/Subtype /Image")) + 32
    altered = bytearray(original)
    altered[at] = 0x00
    path = tmp_path / "v4_altered.pdf"
    path.write_bytes(bytes(altered))
    project = lane.project()
    base = lane.seed("vs1/v4.pdf", 6, project_uid=project)
    changed = lane.seed(path, 6, project_uid=project)
    same_file = compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=base.pages[4],
                                   page_b_profile_id=base.pages[4])
    replaced = compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=base.pages[4],
                                  page_b_profile_id=changed.pages[4])
    assert same_file.status == "same"
    assert replaced.status != "same" and replaced.result_id != same_file.result_id
    assert len({r["content_key"] for r in lane.results(project)}) == 2
