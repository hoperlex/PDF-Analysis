"""Pause, resume and cancel of items and of an upload's items (`CMP-WORK-01`, ADR-0025 decisions 4 and 6).

A waiting item is paused and resumed; an item in flight is not paused (the holder finishes it, one
page or one pair) and a cancel asks it to stop; the upload-scoped forms are the ones the batch
operations of `CMP-INGEST-02` use over the ``comparison_upload_id`` column.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import CANCEL_REQUESTED, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid


@pytest.fixture
def upload(sessions, project) -> Iterator[str]:  # type: ignore[no-untyped-def]
    """A committed ``comparison_upload`` (and the command record it names), removed with its work."""
    upload_id, command_id = f"cbt_{new_ulid()}", f"cmd_{new_ulid()}"
    with sessions() as session:
        session.execute(text(
            "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
            "VALUES (:c, 'create_comparison_upload', :k, :f)"
        ), {"c": command_id, "k": f"cmp-work-{new_ulid()}", "f": "0" * 64})
        session.execute(text(
            "INSERT INTO comparison_upload (comparison_upload_id, project_uid, declared_files, declared_bytes, "
            "actor_user_uid, actor_label, command_id) VALUES (:u, :p, 1, 1, :a, 'cmp-work-01 test', :c)"
        ), {"u": upload_id, "p": project, "a": f"usr_{new_ulid()}", "c": command_id})
        session.commit()
    yield upload_id
    with sessions() as session:
        session.execute(text(
            "DELETE FROM comparison_work_attempt WHERE comparison_work_id IN "
            "(SELECT comparison_work_id FROM comparison_work WHERE comparison_upload_id = :u)"), {"u": upload_id})
        session.execute(text("DELETE FROM comparison_work WHERE comparison_upload_id = :u"), {"u": upload_id})
        session.execute(text("DELETE FROM comparison_upload WHERE comparison_upload_id = :u"), {"u": upload_id})
        session.execute(text("DELETE FROM command_record WHERE command_id = :c"), {"c": command_id})
        session.commit()


def test_a_paused_item_is_not_claimed_until_it_is_resumed(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    with sessions() as session:
        assert queue.repository.pause(session, work_id) == "paused"
        assert queue.repository.pause(session, work_id) == "paused", "pausing is idempotent"
        session.commit()
    assert queue.claim(worker_id) is None
    with sessions() as session:
        assert queue.repository.resume(session, work_id) == "queued"
        assert queue.repository.resume(session, work_id) == "queued", "resuming is idempotent"
        session.commit()
    assert queue.claim(worker_id).work_id == work_id


def test_an_item_in_flight_is_not_paused_and_a_resume_of_an_item_that_was_not_paused_is_refused(
    queue, sessions, worker_id
) -> None:
    work_id = queue.enqueue()
    queue.claim(worker_id)
    with sessions() as session, pytest.raises(DomainError) as refused:
        queue.repository.pause(session, work_id)
    assert refused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    with sessions() as session, pytest.raises(DomainError) as not_paused:
        queue.repository.resume(session, work_id)
    assert not_paused.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
    assert queue.work(work_id)["state"] == "running"


def test_a_cancel_ends_an_item_at_rest_and_asks_an_item_in_flight_to_stop(queue, sessions, worker_id) -> None:
    waiting, paused, running = queue.enqueue(), queue.enqueue(), queue.enqueue()
    with sessions() as session:
        queue.repository.pause(session, paused)
        session.commit()
    with sessions() as session:
        assert queue.repository.cancel(session, waiting) == "cancelled"
        assert queue.repository.cancel(session, paused) == "cancelled"
        session.commit()
    item = queue.claim(worker_id)
    assert item.work_id == running
    with sessions() as session:
        assert queue.repository.cancel(session, running) == CANCEL_REQUESTED
        assert queue.repository.cancel(session, running) == CANCEL_REQUESTED, "asking twice asks once"
        session.commit()
    assert queue.work(running)["cancel_requested"] is True
    assert queue.work(running)["state"] == "running", "the holder ends it"
    assert (queue.work(waiting)["state"], queue.work(waiting)["terminal"]) == ("cancelled", True)
    assert queue.work(paused)["state"] == "cancelled"
    with sessions() as session:
        assert queue.repository.cancel(session, waiting) == "cancelled", "a terminal item is left as it is"
        session.commit()


def test_a_cancel_requested_item_is_never_claimed_again(queue, sessions, worker_id) -> None:
    work_id = queue.enqueue()
    first = queue.claim(worker_id)
    with sessions() as session:
        queue.repository.cancel(session, work_id)
        queue.repository.finish(session, first.authority, Yielded())
        session.commit()
    assert queue.work(work_id)["state"] == "cancelled"
    assert queue.claim(worker_id) is None


def test_the_cancel_of_an_unknown_item_is_not_found(queue, sessions) -> None:
    with sessions() as session, pytest.raises(DomainError) as refused:
        queue.repository.cancel(session, f"cq_{new_ulid()}")
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_the_upload_scoped_forms_touch_only_that_uploads_waiting_items(queue, sessions, upload, worker_id) -> None:
    in_flight = queue.enqueue(comparison_upload_id=upload, priority=50)
    waiting = [queue.enqueue(comparison_upload_id=upload), queue.enqueue(comparison_upload_id=upload)]
    elsewhere = queue.enqueue()
    assert queue.claim(worker_id).work_id == in_flight
    with sessions() as session:
        assert queue.repository.pause_for_upload(session, upload) == 2, "the item in flight finishes"
        session.commit()
    with sessions() as session:
        assert queue.repository.counts(session, upload_id=upload) == {"running": 1, "paused": 2}
    assert queue.work(elsewhere)["state"] == "queued", "another upload's (or no upload's) item is untouched"
    assert queue.claim(worker_id).work_id == elsewhere, "the paused ones are not claimed"
    assert queue.claim(worker_id) is None
    with sessions() as session:
        assert queue.repository.resume_for_upload(session, upload) == 2
        session.commit()
    assert {queue.work(w)["state"] for w in waiting} == {"queued"}
    with sessions() as session:
        result = queue.repository.cancel_for_upload(session, upload)
        session.commit()
    assert (result.cancelled, result.requested) == (2, 1)
    with sessions() as session:
        assert queue.repository.counts(session, upload_id=upload) == {"running": 1, "cancelled": 2}
        assert queue.repository.counts(session, project_uid=queue.project_uid)["cancelled"] == 2
    assert queue.work(in_flight)["cancel_requested"] is True
