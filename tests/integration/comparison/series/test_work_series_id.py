"""The series id on a work item (`CMP-SERIES-01` in `comparison/work/**` and `engine/enqueue.py`): a series pauses, resumes and
cancels its items the way an upload does, and counts them; the id is not part of an item's identity."""

from __future__ import annotations

import pytest

from auditmanager.comparison.public import (
    CANCEL_REQUESTED, ComparisonWorkRepository, enqueue_pair_result, pair_result_dedupe_key,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError

from .support import ScriptedEngine, build, drain, fenced, key, runner_with, start


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def test_an_item_carries_its_series_and_the_counts_can_be_asked_for_one_series(lab, sessions, expert_uid, matrix_service, service, prepared) -> None:
    doc, series = prepared
    other = lab.clone()
    build(matrix_service, other)
    elsewhere = start(service, other, expert_uid)
    work = ComparisonWorkRepository()
    with sessions() as session:
        assert work.counts(session, series_id=series["series_id"]) == {"queued": 25}
        assert work.counts(session, series_id=elsewhere["series_id"]) == {"queued": 25}
        assert work.counts(session, project_uid=doc.project_uid) == {"queued": 25}
        assert work.counts(session, series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV") == {}


def test_the_controls_reach_exactly_the_items_of_the_series(lab, sessions, expert_uid, matrix_service, service, prepared) -> None:
    doc, series = prepared
    other = lab.clone()
    build(matrix_service, other)
    elsewhere = start(service, other, expert_uid)
    work = ComparisonWorkRepository()
    with session_scope(sessions) as session:
        assert work.pause_for_series(session, series["series_id"]) == 25
    with sessions() as session:
        assert work.counts(session, series_id=series["series_id"]) == {"paused": 25}
        assert work.counts(session, series_id=elsewhere["series_id"]) == {"queued": 25}
    with session_scope(sessions) as session:
        assert work.resume_for_series(session, series["series_id"]) == 25
        assert work.resume_for_series(session, series["series_id"]) == 0
    with session_scope(sessions) as session:
        result = work.cancel_for_series(session, series["series_id"])
        assert (result.cancelled, result.requested) == (25, 0)
    with sessions() as session:
        assert work.counts(session, series_id=series["series_id"]) == {"cancelled": 25}
        assert work.counts(session, series_id=elsewhere["series_id"]) == {"queued": 25}


def test_an_item_in_flight_is_asked_to_stop_not_ended(lab, sessions, engine, blob_store, worker_id, prepared) -> None:
    doc, series = prepared
    runner = runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions))
    with fenced(engine, doc.project_uid, ("series_drive",)):
        item = runner.claim(worker_id)
    assert item is not None and item.comparison_series_id == series["series_id"]
    work = ComparisonWorkRepository()
    with session_scope(sessions) as session:
        result = work.cancel_for_series(session, series["series_id"])
        assert (result.cancelled, result.requested) == (24, 1)
        assert work.get(session, item.work_id).cancel_requested is True  # type: ignore[union-attr]
        assert work.get(session, item.work_id).comparison_series_id == series["series_id"]  # type: ignore[union-attr]


def test_the_pair_result_item_can_be_attached_to_a_series_without_changing_its_identity(lab, sessions, expert_uid, prepared) -> None:
    doc, series = prepared
    pair = lab.rows(
        "SELECT p.page_a_profile_id AS a, p.page_b_profile_id AS b FROM comparison_sheet_pair p "
        "JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
        "WHERE t.comparison_series_id = :s AND p.state = 'queued' ORDER BY t.transition_no, p.pair_no LIMIT 1", s=series["series_id"])[0]
    with session_scope(sessions) as session:
        attached = enqueue_pair_result(
            session, project_uid=doc.project_uid, page_a_profile_id=pair["a"], page_b_profile_id=pair["b"],
            created_by_user_uid=expert_uid, comparison_series_id=series["series_id"])
        assert attached.created is True
        again = enqueue_pair_result(
            session, project_uid=doc.project_uid, page_a_profile_id=pair["a"], page_b_profile_id=pair["b"],
            created_by_user_uid=expert_uid)
        assert (again.created, again.work_id) == (False, attached.work_id)  # the dedupe key ignores the series
    row = lab.rows("SELECT comparison_series_id AS s, dedupe_key AS k FROM comparison_work WHERE comparison_work_id = :w", w=attached.work_id)[0]
    assert row == {"s": series["series_id"], "k": pair_result_dedupe_key(pair["a"], pair["b"])}


def test_a_series_id_that_names_no_series_is_refused_by_the_database(lab, sessions, expert_uid, prepared) -> None:
    doc, _series = prepared
    work = ComparisonWorkRepository()
    with pytest.raises(Exception) as refused:
        with session_scope(sessions) as session:
            work.enqueue(session, project_uid=doc.project_uid, module="versions", kind="series_drive", payload={},
                         dedupe_key=key(), comparison_series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert "fk_comparison_work_series" in str(refused.value) or isinstance(refused.value, DomainError)
    assert CANCEL_REQUESTED == "cancel_requested"
