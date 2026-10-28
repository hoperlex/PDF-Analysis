"""`CMP-INGEST-02`: what a confirmed set causes -- its versions' page profiles on the comparison queue, one set at a time --
and the drive that watches a batch (completes it, releases the next set, notices an abandoned upload).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.comparison.public import Failed, WorkItem
from auditmanager.shared.db import session_scope
from tests.integration.ingest.comparison_batch.support import Harness, Queue


def _versions_of(h: Harness, set_id: str) -> list[str]:
    [(proposal,)] = h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=set_id)
    return [f["version_uid"] for f in sorted(proposal["confirmed"]["files"], key=lambda f: f["position"])]


def _profile_items(h: Harness, upload_id: str) -> list[tuple[str, str]]:
    return [(w["payload"]["version_uid"], w["state"]) for w in h.work(upload_id, kind="page_profile")]


class TestAConfirmedSetPutsItsPagesOnTheQueue:
    def test_one_item_per_version_in_the_confirmed_order_attached_to_the_batch_and_the_project(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 3, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        versions = _versions_of(h, alpha.set_id)
        assert len(versions) == 3
        rows = h.work(upload_id, kind="page_profile")
        assert [w["payload"]["version_uid"] for w in rows] == versions
        assert {w["upload"] for w in rows} == {upload_id}
        assert [w["dedupe_key"] for w in rows] == [f"page_profile:{v}" for v in versions]
        assert h.rows("SELECT DISTINCT project_uid, module FROM comparison_work WHERE kind = 'page_profile'") == [
            (h.project_uid, "versions")]
        assert h.state(upload_id) == "processing"

    def test_the_set_is_marked_released_with_the_items_that_carry_its_versions(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        [(proposal,)] = h.rows("SELECT proposal FROM comparison_upload_set WHERE comparison_upload_set_id = :s", s=alpha.set_id)
        marked = proposal["processing"]["work"]
        assert sorted(marked) == sorted(_versions_of(h, alpha.set_id))
        assert sorted(marked.values()) == sorted(w["id"] for w in h.work(upload_id, kind="page_profile"))

    def test_asking_again_enqueues_nothing_more(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, key="confirm-1")
        before = h.work(upload_id)
        h.batches.after_confirmation(upload_id=upload_id, set_id=alpha.set_id)
        h.confirm(upload_id, alpha, key="confirm-1")  # a replay of the confirmation, and the hook with it
        assert h.work(upload_id) == before
        assert len(h.work(kind="comparison_batch_drive")) == 1
        # Once its items have ended the set is still not released again: the mark on the set is what says so.
        queue.run_all()
        ended = h.work(upload_id)
        assert [w["state"] for w in ended] == ["succeeded", "succeeded"]
        h.batches.after_confirmation(upload_id=upload_id, set_id=alpha.set_id)
        h.confirm(upload_id, alpha, key="confirm-1")
        assert h.work(upload_id) == ended

    def test_a_hook_that_failed_is_repaired_by_the_clients_replay(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, hook=False, key="confirm-1")  # the process died after the commit, before the hook
        assert h.state(upload_id) == "proposed" and h.work(upload_id, kind="page_profile") == []
        h.confirm(upload_id, alpha, key="confirm-1")
        assert h.state(upload_id) == "processing" and len(h.work(upload_id, kind="page_profile")) == 1

    def test_without_the_hook_the_drive_repairs_it(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, hook=False)
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert h.state(upload_id) == "processing"
        assert [state for _v, state in _profile_items(h, upload_id)] == ["succeeded"]

    def test_the_last_set_of_a_batch_completed_at_its_confirmation_is_released_by_the_hook(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 2})
        alpha = h.sets(upload_id)[0]
        h.confirm(upload_id, alpha)
        assert h.state(upload_id) == "completed", "CMP-INGEST-01 completes a batch whose last set is decided"
        assert len(h.work(upload_id, kind="page_profile")) == 2

    def test_without_the_hook_the_drive_releases_the_sets_of_a_completed_batch(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 2})
        h.confirm(upload_id, h.sets(upload_id)[0], hook=False)
        assert h.state(upload_id) == "completed" and h.work(upload_id, kind="page_profile") == []
        h.make_due("comparison_batch_drive")
        steps = queue.run_all()
        assert ("comparison_batch_drive", "succeeded") in steps
        assert len(h.work(upload_id, kind="page_profile")) == 2

    def test_a_cancelled_batch_releases_nothing(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.confirm(upload_id, alpha, hook=False)
        h.cancel(upload_id)
        h.batches.after_confirmation(upload_id=upload_id, set_id=alpha.set_id)
        assert h.work(upload_id, kind="page_profile") == []
        assert h.state(upload_id) == "cancelled"

    def test_a_set_that_is_not_done_releases_nothing(self, h: Harness) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, _beta = h.sets(upload_id)
        h.batches.after_confirmation(upload_id=upload_id, set_id=alpha.set_id)
        assert h.work(upload_id) == []
        assert h.state(upload_id) == "proposed"


class TestOneSetAtATime:
    def test_the_next_set_is_released_only_when_nothing_of_the_batch_is_live(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 2, "Beta": 1, "Gamma": 1})
        alpha, beta, gamma = h.sets(upload_id)
        for one in (alpha, beta, gamma):
            h.confirm(upload_id, one)
        assert [v for v, _s in _profile_items(h, upload_id)] == _versions_of(h, alpha.set_id)

        # The drive comes while a version of Alpha is in flight: nothing is released.
        first = queue.claim()
        assert first is not None and first.kind == "page_profile"
        h.make_due("comparison_batch_drive")
        # The other version of Alpha runs, and the drive finds Alpha's first version still in flight.
        assert sorted(queue.run_all()) == [("comparison_batch_drive", "queued"), ("page_profile", "succeeded")]
        assert len(h.work(upload_id, kind="page_profile")) == 2, "Beta is not on the queue"
        queue.runner.execute(first)

        # Alpha has ended: the drive releases Beta -- not Gamma, whose turn is after it.
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "queued"), ("page_profile", "succeeded")]
        assert [v for v, _s in _profile_items(h, upload_id)] == _versions_of(h, alpha.set_id) + _versions_of(h, beta.set_id)
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert [v for v, _s in _profile_items(h, upload_id)][-1] == _versions_of(h, gamma.set_id)[0]

    def test_sets_are_released_in_the_order_they_were_confirmed_not_the_order_they_were_proposed(
        self, h: Harness, queue: Queue
    ) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1, "Gamma": 1})
        alpha, beta, gamma = h.sets(upload_id)
        h.confirm(upload_id, gamma)
        h.confirm(upload_id, alpha)
        h.confirm(upload_id, beta)
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()
        released = [v for v, _s in _profile_items(h, upload_id)]
        assert released == [_versions_of(h, one.set_id)[0] for one in (gamma, alpha, beta)]


class TestTheBatchCompletes:
    def test_when_every_set_is_decided_every_done_set_released_and_nothing_is_live(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        h.confirm(upload_id, beta)
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()  # releases Beta, runs it
        assert h.state(upload_id) == "processing"
        h.make_due("comparison_batch_drive")
        assert ("comparison_batch_drive", "succeeded") in queue.run_all()
        assert h.state(upload_id) == "completed"
        assert [w["state"] for w in h.work(kind="comparison_batch_drive")] == ["succeeded"]

    def test_a_live_item_keeps_it_processing(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        h.confirm(upload_id, beta)
        queue.run_all()                           # Alpha ends
        h.make_due("comparison_batch_drive")
        item = None
        # The drive releases Beta; take Beta's item and keep it in flight.
        for _ in range(2):
            item = queue.claim()
            if item is not None and item.kind == "page_profile":
                break
            if item is not None:
                queue.runner.execute(item)
        assert item is not None and item.kind == "page_profile"
        assert item.payload["version_uid"] == _versions_of(h, beta.set_id)[0]
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "queued")]
        assert h.state(upload_id) == "processing", "an item of the last set is still in flight"
        queue.runner.execute(item)
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "succeeded")]
        assert h.state(upload_id) == "completed"

    def test_an_item_that_failed_does_not_hold_the_batch_open(self, h: Harness, queue: Queue) -> None:
        queue.profiles.outcome = Failed("page_profile_source_unreadable")
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        h.confirm(upload_id, alpha)
        h.confirm(upload_id, beta)
        assert queue.run_all() == [("page_profile", "failed")]
        h.make_due("comparison_batch_drive")
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert h.state(upload_id) == "completed"

    def test_a_failed_set_keeps_the_batch_open_until_it_is_left_out(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        alpha, beta = h.sets(upload_id)
        with session_scope(h.sessions) as session:
            session.execute(text(
                "UPDATE comparison_upload_set SET state = 'failed', failure_reason = 'comparison_sets_limit' "
                "WHERE comparison_upload_set_id = :s"), {"s": beta.set_id})
        h.confirm(upload_id, alpha)
        assert h.state(upload_id) == "processing"
        queue.run_all()
        h.make_due("comparison_batch_drive")
        queue.run_all()
        assert h.state(upload_id) == "processing", "a failed set is not decided"
        h.exclude(upload_id, beta.set_id)
        assert h.state(upload_id) == "completed"


class TestTheDriveItself:
    def test_every_declared_batch_has_exactly_one_drive_and_it_is_not_attached_to_the_batch(self, h: Harness) -> None:
        view = h.declare(["Alpha (1).pdf"])
        h.batches.after_declaration(upload_id=view.upload_id)  # a client's retry of the declaration
        [drive] = h.work(kind="comparison_batch_drive")
        assert drive["payload"] == {"upload_id": view.upload_id} and drive["upload"] is None
        assert drive["dedupe_key"] == f"batch_drive:{view.upload_id}"
        with h.sessions() as session:
            from auditmanager.comparison.public import ComparisonWorkRepository

            assert ComparisonWorkRepository().counts(session, upload_id=view.upload_id) == {}, "never counted as the batch's"

    def test_a_cancelled_batch_ends_its_drive_at_the_next_poll(self, h: Harness, queue: Queue) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        h.cancel(upload_id)
        h.make_due("comparison_batch_drive")
        assert ("comparison_batch_drive", "succeeded") in queue.run_all()

    @pytest.mark.parametrize("reach", ["proposed", "paused"])
    def test_a_batch_waiting_for_a_person_is_polled_again_later(self, h: Harness, queue: Queue, reach: str) -> None:
        upload_id = h.proposed({"Alpha": 1, "Beta": 1})
        if reach == "paused":
            h.confirm(upload_id, h.sets(upload_id)[0])
            h.pause(upload_id)
        queue.run_all()  # the profile items of a confirmed set, if any
        h.make_due("comparison_batch_drive")
        assert queue.run_all() == [("comparison_batch_drive", "queued")]
        assert h.state(upload_id) == reach

    def test_a_payload_that_is_not_a_batch_is_a_failure_that_starts_nothing(self, h: Harness, queue: Queue) -> None:
        from auditmanager.comparison.public import ComparisonWorkRepository

        for payload in ({}, {"upload_id": "nope"}, {"upload_id": "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV", "extra": 1}):
            with session_scope(h.sessions) as session:
                ComparisonWorkRepository().enqueue(
                    session, project_uid=h.project_uid, module="versions", kind="comparison_batch_drive", payload=payload,
                    dedupe_key=f"bad-{len(payload)}-{payload.get('upload_id')}",
                )
        steps = queue.run_all()
        assert steps == [("comparison_batch_drive", "failed")] * 3
        assert {w["failure_reason"] for w in h.work(kind="comparison_batch_drive")} == {"batch_payload_invalid"}

    def test_a_drive_that_lost_its_lease_changes_nothing(self, h: Harness, queue: Queue) -> None:
        """The handler publishes only inside a transaction that first proves its attempt still holds the item."""
        upload_id = h.declare(["Alpha (1).pdf"]).upload_id
        h.make_idle(upload_id, seconds=25 * 3600)  # an abandoned batch: this poll would cancel it
        h.make_due("comparison_batch_drive")
        item = queue.claim()
        assert isinstance(item, WorkItem) and item.kind == "comparison_batch_drive"
        with session_scope(h.sessions) as session:
            session.execute(text(
                "UPDATE comparison_work_attempt SET lease_expires_at = clock_timestamp() - interval '1 minute' "
                "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
        assert queue.runner.execute(item) is None, "the outcome of an attempt that lost its lease is dropped"
        assert h.state(upload_id) == "uploading", "and so is what it would have written"
