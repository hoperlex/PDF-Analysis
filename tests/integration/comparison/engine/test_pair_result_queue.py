"""The ``pair_result`` kind on the comparison queue, end to end (`CMP-ENGINE-01`, ADR-0025 decisions 4, 6, 7).

The runner is the real :class:`ComparisonWorkRunner` with the real handler; the claim, the lease and the attempt are the
queue's own. A cancel, a lease that is gone and a child that never started are the three ways a long step is stopped.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.comparison.engine import PairResultHandler, enqueue_pair_result, pair_result_dedupe_key
from auditmanager.comparison.profile.runner import ChildStartError
from auditmanager.comparison.work.gates import ClaimGates
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.comparison.work.registry import HandlerRegistry
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.comparison.work.runner import ComparisonWorkRunner
from auditmanager.shared.errors import DomainError, ErrorCode

USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


class Queue:
    def __init__(self, lane, child_runner=None) -> None:
        from auditmanager.workers.public import WorkerRegistry

        self.lane = lane
        self.repository = ComparisonWorkRepository()
        deps = WorkDependencies(engine=lane.engine, session_factory=lane.sessions, blob_store=lane.blob_store, work=self.repository)
        handler = PairResultHandler(deps, runner=child_runner)
        self.runner = ComparisonWorkRunner(
            lane.sessions, registry=HandlerRegistry({handler.kind: handler}), modules=frozenset({"versions"}),
            repository=self.repository, gates=ClaimGates(paused=lambda s: False, run_claimable=lambda s: False),
            heartbeat_seconds=3600.0)
        with lane.sessions() as session:
            self.worker = WorkerRegistry().register(session, version="cmp-engine-01-test", slots=1)
            session.commit()
        lane.workers.append(self.worker)

    def enqueue(self, a, b, pa, pb, **kw):
        with self.lane.sessions() as session:
            enqueued = enqueue_pair_result(session, project_uid=a.project_uid, page_a_profile_id=a.pages[pa],
                                           page_b_profile_id=b.pages[pb], created_by_user_uid=USER, **kw)
            session.commit()
        return enqueued

    def work(self, work_id):
        with self.lane.sessions() as session:
            return dict(session.execute(text(
                "SELECT state, failure_reason, attempt_count, payload, dedupe_key, kind, module FROM comparison_work "
                "WHERE comparison_work_id = :w"), {"w": work_id}).mappings().one())


@pytest.fixture
def versions(lane):
    project = lane.project()
    return lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)


@pytest.fixture
def queue(lane):
    return Queue(lane)


def test_a_pair_enqueued_is_compared_by_the_runner_and_the_item_succeeds(lane, queue, versions) -> None:
    v1, v2 = versions
    enqueued = queue.enqueue(v1, v2, 2, 2, reasons=["MATCH_LOW_CONFIDENCE"])
    work = queue.work(enqueued.work_id)
    assert enqueued.created and (work["kind"], work["module"], work["state"]) == ("pair_result", "versions", "queued")
    assert work["dedupe_key"] == pair_result_dedupe_key(v1.pages[2], v2.pages[2])
    assert work["payload"] == {"page_a": v1.pages[2], "page_b": v2.pages[2], "reasons": ["MATCH_LOW_CONFIDENCE"], "part": None}
    item = queue.runner.claim(queue.worker)
    assert item is not None and item.work_id == enqueued.work_id
    assert queue.runner.execute(item) == "succeeded"
    rows = lane.results(v1.project_uid)
    assert len(rows) == 1 and rows[0]["status"] == "needs_review" and "MATCH_LOW_CONFIDENCE" in rows[0]["reasons"]
    assert rows[0]["mask_blob_id"] is not None and lane.blob_state(rows[0]["mask_blob_id"]) == "available"


def test_a_pair_enqueued_twice_while_live_is_one_item_and_a_second_run_finds_the_row(lane, queue, versions) -> None:
    v1, v2 = versions
    first, second = queue.enqueue(v1, v2, 3, 3), queue.enqueue(v1, v2, 3, 3)
    assert first.created and not second.created and first.work_id == second.work_id
    assert queue.runner.execute(queue.runner.claim(queue.worker)) == "succeeded"
    third = queue.enqueue(v1, v2, 3, 3)
    assert third.created and third.work_id != first.work_id  # the key is free once the item has ended
    assert queue.runner.execute(queue.runner.claim(queue.worker)) == "succeeded"
    assert len(lane.results(v1.project_uid)) == 1  # the second item found the first's row


def test_pages_of_another_project_or_unknown_are_refused_at_enqueue_and_nothing_is_queued(lane, queue, versions) -> None:
    v1, v2 = versions
    other = lane.project()
    w2 = lane.seed("vs1/v2.pdf", 6, project_uid=other)
    with lane.sessions() as session, pytest.raises(DomainError) as refusal:
        enqueue_pair_result(session, project_uid=v1.project_uid, page_a_profile_id=v1.pages[2], page_b_profile_id=w2.pages[2], created_by_user_uid=USER)
    assert refusal.value.code is ErrorCode.NOT_FOUND
    with lane.sessions() as session, pytest.raises(DomainError) as refusal:
        enqueue_pair_result(session, project_uid=v1.project_uid, page_a_profile_id="cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            page_b_profile_id=v2.pages[2], created_by_user_uid=USER)
    assert refusal.value.code is ErrorCode.NOT_FOUND
    with lane.sessions() as session, pytest.raises(DomainError) as refusal:
        enqueue_pair_result(session, project_uid=v1.project_uid, page_a_profile_id="not-an-id", page_b_profile_id=v2.pages[2], created_by_user_uid=USER)
    assert refusal.value.code is ErrorCode.VALIDATION_FAILED
    assert queue.runner.claim(queue.worker) is None


def test_a_child_that_never_started_fails_the_attempt_and_the_item_waits_for_a_retry(lane, versions) -> None:
    class Broken:
        def run(self, settings, limits):
            raise ChildStartError("gone")

    queue = Queue(lane, child_runner=Broken())
    v1, v2 = versions
    enqueued = queue.enqueue(v1, v2, 2, 2)
    assert queue.runner.execute(queue.runner.claim(queue.worker)) in ("retry_wait", "queued", "failed")
    work = queue.work(enqueued.work_id)
    assert work["state"] in ("retry_wait", "queued") and work["attempt_count"] == 1
    assert lane.results(v1.project_uid) == []


def test_a_cancel_requested_before_the_blob_stops_the_item_and_writes_no_row(lane, queue, versions) -> None:
    v1, v2 = versions
    enqueued = queue.enqueue(v1, v2, 2, 2)
    item = queue.runner.claim(queue.worker)
    with lane.sessions() as session:
        ComparisonWorkRepository().cancel(session, enqueued.work_id)
        session.commit()
    assert queue.runner.execute(item) == "cancelled"
    assert lane.results(v1.project_uid) == []


def test_an_attempt_that_lost_its_lease_writes_nothing(lane, queue, versions) -> None:
    v1, v2 = versions
    queue.enqueue(v1, v2, 2, 2)
    item = queue.runner.claim(queue.worker)
    with lane.sessions() as session:
        session.execute(text("UPDATE comparison_work_attempt SET lease_expires_at = statement_timestamp() - interval '1 second' "
                             "WHERE comparison_work_attempt_id = :a"), {"a": item.attempt_id})
        session.commit()
    queue.runner.reclaim()
    handler = queue.runner._registry.handler("pair_result")
    outcome = handler.run(item)
    from auditmanager.comparison.work.model import Yielded

    assert isinstance(outcome, Yielded) and lane.results(v1.project_uid) == []


def test_the_shipped_tuple_builds_a_runner_that_holds_the_kind(lane) -> None:
    from auditmanager.bootstrap.composition import build_comparison_work

    runner = build_comparison_work(sessions=lane.sessions, engine=lane.engine, blob_store=lane.blob_store,
                                   environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"})
    assert {"pair_result", "page_profile"} <= runner.kinds
    runner.verify()
