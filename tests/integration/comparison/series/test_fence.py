"""The lease fence on every write of a pair (`CMP-SERIES-01`, ADR-0025 decision 7): an attempt that lost its lease writes
no pair -- not when it starts, not when it finishes, not when the series advances."""

from __future__ import annotations

import pytest

from auditmanager.comparison.series.advance import SeriesAdvancer
from auditmanager.shared.errors import DomainError, ErrorCode

from .support import (
    ScriptedEngine, build, drain, expire_lease, fenced, items, make_due, pair_rows, runner_with, start,
)


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def claim_pair(runner, worker_id, engine, sessions, project):
    make_due(sessions, project)
    with fenced(engine, project, ("series_drive",)):
        item = runner.claim(worker_id)
    assert item is not None and item.kind == "series_pair"
    return item


def test_an_attempt_that_lost_its_lease_before_it_starts_writes_no_pair(lab, sessions, engine, blob_store, worker_id, prepared) -> None:
    doc, series = prepared
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    item = claim_pair(runner, worker_id, engine, sessions, doc.project_uid)
    expire_lease(sessions, item.work_id)
    assert runner.execute(item) is None  # its outcome is dropped
    assert fake.calls == []
    assert [p["state"] for p in pair_rows(lab, series["series_id"])].count("computing") == 0


def test_an_attempt_that_loses_its_lease_after_the_comparison_leaves_the_pair_unfinished(
    lab, sessions, engine, blob_store, worker_id, prepared,
) -> None:
    doc, series = prepared
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    item = claim_pair(runner, worker_id, engine, sessions, doc.project_uid)
    fake.after_call = lambda *_a: expire_lease(sessions, item.work_id)  # the result is written, then the lease is gone
    assert runner.execute(item) is None
    victim = [p for p in pair_rows(lab, series["series_id"]) if p["id"] == item.payload["sheet_pair_id"]][0]
    assert victim["state"] == "computing" and victim["status"] is None and victim["result_id"] is None
    assert [p["state"] for p in pair_rows(lab, series["series_id"])].count("done") == 2  # the immediate pairs only
    # the reclaim gives the item to the next attempt, which finds the result and writes the pair
    fake.after_call = None
    with sessions() as session:
        assert runner._repository.reclaim_expired(session) >= 1  # the database is shared: other tests' leases too
        session.commit()
    drain(runner, worker_id, engine, sessions, doc.project_uid)
    victim = [p for p in pair_rows(lab, series["series_id"]) if p["id"] == item.payload["sheet_pair_id"]][0]
    assert victim["state"] == "done" and victim["status"] == "same" and victim["result_id"]
    attempts = [w for w in items(lab, series["series_id"]) if w["id"] == item.work_id]
    assert attempts[0]["state"] == "succeeded"
    # the first attempt wrote its result row (the engine's own fence held then); the second found it, so one row per pair
    assert len(fake.calls) == 25  # 24 pairs, the victim twice
    assert lab.rows("SELECT count(*) AS n FROM comparison_sheet_pair_result WHERE project_uid = :p", p=doc.project_uid)[0]["n"] == 24


def test_the_series_advances_only_under_a_fence_that_holds(lab, sessions, blob_store, engine, worker_id, service, prepared) -> None:
    doc, series = prepared
    sid = series["series_id"]
    with lab.sessions() as session:  # every item of the series ends without a result: its pairs wait for nothing
        from sqlalchemy import text
        session.execute(text("UPDATE comparison_work SET state = 'cancelled', terminal_at = clock_timestamp() "
                             "WHERE comparison_series_id = :s AND kind = 'series_pair'"), {"s": sid})
        session.commit()
    advancer = SeriesAdvancer(sessions, blob_store)

    def refuse(session) -> None:
        raise DomainError(ErrorCode.STALE_ATTEMPT)

    with pytest.raises(DomainError) as lost:
        advancer.advance(sid, fence=refuse)
    assert lost.value.code is ErrorCode.STALE_ATTEMPT
    rows = pair_rows(lab, sid)
    assert [p["state"] for p in rows].count("failed") == 0 and [p["state"] for p in rows].count("queued") == 24
    assert service.get_series(series_id=sid)["state"] == "queued"

    advanced = advancer.advance(sid, fence=lambda session: None)
    assert advanced.live is False
    rows = pair_rows(lab, sid)
    assert [p["state"] for p in rows].count("failed") == 24 and {p["failure_reason"] for p in rows if p["state"] == "failed"} == {"series_item_cancelled"}
    done = service.get_series(series_id=sid)
    assert done["state"] == "completed"
    assert all("content_same" not in t["verdict"] and "incomplete" in t["verdict"] for t in done["transitions"])
    assert items(lab, sid)[0]["state"] in ("cancelled", "queued")


def test_the_pair_is_marked_computing_only_under_the_fence(lab, sessions, engine, blob_store, worker_id, prepared) -> None:
    from auditmanager.comparison.public import ComparisonWorkRepository, SeriesPairHandler, WorkDependencies

    doc, series = prepared
    runner = runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions))
    item = claim_pair(runner, worker_id, engine, sessions, doc.project_uid)
    expire_lease(sessions, item.work_id)
    handler = SeriesPairHandler(WorkDependencies(engine=engine, session_factory=sessions, blob_store=blob_store,
                                                 work=ComparisonWorkRepository()))
    with pytest.raises(DomainError) as lost:
        handler._begin(item, item.payload["sheet_pair_id"])
    assert lost.value.code is ErrorCode.STALE_ATTEMPT
    assert [p["state"] for p in pair_rows(lab, series["series_id"])].count("computing") == 0


class FailAfter:
    """A fence that holds for ``holds`` transactions and then refuses: the attempt lost its lease in between."""

    def __init__(self, holds: int) -> None:
        self.holds, self.calls = holds, 0

    def __call__(self, session) -> None:
        self.calls += 1
        if self.calls > self.holds:
            raise DomainError(ErrorCode.STALE_ATTEMPT)


def orphaned(lab, sessions, sid: str) -> None:
    from sqlalchemy import text

    with lab.sessions() as session:
        session.execute(text("UPDATE comparison_work SET state = 'cancelled', terminal_at = clock_timestamp() "
                             "WHERE comparison_series_id = :s AND kind = 'series_pair'"), {"s": sid})
        session.commit()


def test_a_fence_that_refuses_after_the_reconcile_stops_the_finalisation_of_every_transition(
    lab, sessions, blob_store, service, prepared,
) -> None:
    doc, series = prepared
    sid = series["series_id"]
    orphaned(lab, sessions, sid)
    fence = FailAfter(1)  # the reconcile may write, the first finalisation may not
    with pytest.raises(DomainError):
        SeriesAdvancer(sessions, blob_store).advance(sid, fence=fence)
    assert fence.calls == 2
    seen = service.get_series(series_id=sid)
    assert [t["state"] for t in seen["transitions"]] == ["running"] * 4 and "verdict" not in seen["transitions"][0]
    assert [p["state"] for p in pair_rows(lab, sid)].count("failed") == 24  # what the reconcile wrote stands


def test_a_fence_that_refuses_at_the_end_leaves_the_series_unconcluded(lab, sessions, blob_store, service, prepared) -> None:
    doc, series = prepared
    sid = series["series_id"]
    orphaned(lab, sessions, sid)
    fence = FailAfter(1 + 4)  # the reconcile and the four finalisations may write, the conclusion may not
    with pytest.raises(DomainError):
        SeriesAdvancer(sessions, blob_store).advance(sid, fence=fence)
    seen = service.get_series(series_id=sid)
    assert [t["state"] for t in seen["transitions"]] == ["completed"] * 4 and seen["state"] in ("queued", "running")
    # a second look under a fence that holds concludes it
    assert SeriesAdvancer(sessions, blob_store).advance(sid, fence=lambda session: None).live is False
    assert service.get_series(series_id=sid)["state"] == "completed"
