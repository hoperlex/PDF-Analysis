"""An enqueued version is built end to end by the comparison runner (`CMP-PROFILE-QUEUE-01`), against PostgreSQL, MinIO
and the real page children.

The runner here is the one the worker builds: ``build_comparison_work`` applies the shipped
``HANDLER_FACTORIES`` to the dependency bundle, so the kind is proved to be registered the way the worker registers
it. The version is VS-1 ``v1.pdf`` (six sheets, one of them the A1 plan), seeded as a published ``document_version``
whose source PDF is a blob; the synthetic corpus' answer key is the oracle for what the stored profiles must say.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from auditmanager.bootstrap.composition import build_comparison_work
from auditmanager.comparison.public import (
    PAGE_PROFILE_WORK_KIND,
    PROFILE_READY,
    PageProfileReader,
)

def test_a_version_enqueued_after_a_set_is_confirmed_is_profiled_by_the_worker_runner_and_the_item_succeeds(
    lane, vs1_v1, vs1_key, blob_store, engine
) -> None:
    key = next(v for v in vs1_key["versions"] if v["id"] == "V1")
    seeded = lane.seed(vs1_v1, key["page_count"])
    enqueued = lane.enqueue(seeded)
    assert enqueued.created is True

    # The runner the worker builds, from the shipped tuple: the kind is registered through HANDLER_FACTORIES.
    runner = build_comparison_work(
        sessions=lane.sessions, engine=engine, blob_store=blob_store,
        environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
    )
    assert PAGE_PROFILE_WORK_KIND in runner.kinds
    runner.verify()

    item = lane.claim(runner)
    assert (item.work_id, item.kind, item.module, item.project_uid) == (
        enqueued.work_id, "page_profile", "versions", seeded.project_uid,
    )
    assert runner.execute(item) == "succeeded"

    work = lane.work(enqueued.work_id)
    assert (work["state"], work["terminal"], work["failure_reason"], work["attempt_count"]) == ("succeeded", True, None, 1)
    assert [(a["attempt_no"], a["state"]) for a in lane.attempts(enqueued.work_id)] == [(1, "succeeded")]

    # Every page of the version has a row; each is ready and carries its three blobs.
    rows = lane.rows(seeded.version_uid)
    assert [row.page_number for row in rows] == [1, 2, 3, 4, 5, 6]
    assert [row.status for row in rows] == [PROFILE_READY] * 6
    assert all(row.profile_blob_id and row.preview_blob_id and row.thumbnail_blob_id for row in rows)

    # What the rows say is what the answer key says (the sheet number, the title, the designation of each sheet).
    profiles = PageProfileReader(lane.sessions, blob_store).read_version_profiles(seeded.version_uid)
    assert len(profiles) == 6
    for profile, page_key in zip(profiles, key["pages"], strict=True):
        assert profile.scan is page_key["scan"]
        if page_key["text_layer"]:
            assert profile.stamp.sheet_number == page_key["sheet_no"]
            assert profile.stamp.sheet_title == page_key["title"]
            assert profile.stamp.designation == page_key["stamp"]["designation"]

    # The queue holds nothing live for the project: the item is the only one and it has ended.
    assert [w["state"] for w in lane.work_of(seeded.project_uid)] == ["succeeded"]


def test_the_same_version_enqueued_again_after_the_item_ended_is_a_new_item_that_costs_time_and_writes_no_row(
    lane, small_pdf, blob_store, engine
) -> None:
    seeded = lane.seed(small_pdf(3), 3)
    runner = build_comparison_work(
        sessions=lane.sessions, engine=engine, blob_store=blob_store,
        environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
    )
    first = lane.enqueue(seeded)
    assert runner.execute(lane.claim(runner)) == "succeeded"
    before = [(row.id, row.content_key) for row in lane.rows(seeded.version_uid)]
    assert len(before) == 3

    second = lane.enqueue(seeded)
    assert second.created is True and second.work_id != first.work_id, "the key is free once the item has ended"
    assert runner.execute(lane.claim(runner)) == "succeeded"
    assert [(row.id, row.content_key) for row in lane.rows(seeded.version_uid)] == before

    with lane.sessions() as session:
        written = session.execute(
            text("SELECT count(*) FROM comparison_page_profile WHERE version_uid = :v"), {"v": seeded.version_uid}
        ).scalar_one()
    assert written == 3
