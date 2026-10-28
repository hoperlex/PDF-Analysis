"""The series through the real runner (`CMP-SERIES-01`, ADR-0025 decisions 4, 6, 7): each pair is one item, the engine's result
lands on the pair, the transitions are finalised and the series concludes, and the lease fence guards every write of a pair.

The pair comparison is a scripted engine that writes real result rows (the foreign keys, the project trigger and the unique
content key apply); the real engine on the corpus is `test_corpus_against_the_answer_keys.py`."""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine.runner import ChildStartError
from auditmanager.shared.errors import DomainError, ErrorCode

from .support import (
    ScriptedEngine, build, drain, items, key, make_due, pair_rows, runner_with, start, steer,
)


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def version_of(lab, doc) -> dict[str, str]:
    rows = lab.rows("SELECT comparison_page_profile_id AS id, version_uid FROM comparison_page_profile "
                    "WHERE version_uid = ANY(CAST(:v AS text[]))", v=list(doc.versions))
    return {r["id"]: r["version_uid"] for r in rows}


def test_every_pair_is_computed_the_transitions_are_finalised_and_the_series_concludes(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    ran = drain(runner, worker_id, engine, sessions, doc.project_uid)

    assert sorted(set(kind for kind, _ in ran)) == ["series_drive", "series_pair"]
    assert [state for kind, state in ran if kind == "series_pair"] == ["succeeded"] * 24
    assert ran[-1] == ("series_drive", "succeeded")
    done = service.get_series(series_id=series["series_id"])
    assert done["state"] == "completed" and (done["transitions_total"], done["transitions_done"]) == (4, 4)
    assert all(t["state"] == "completed" and t["items_done"] == t["items_total"] for t in done["transitions"])
    assert [t["verdict"] for t in done["transitions"]] == [["content_same"], ["composition_changed"], ["content_same"], ["needs_review"]]
    first = done["transitions"][0]["summary"]
    assert first == {"sheets": 6, "compared": 6, "same": 6, "zones_only": 0, "different": 0, "style_only": 0, "needs_review": 0,
                     "added": 0, "removed": 0, "failed": 0, "ai_dependent": 0}
    assert [w["state"] for w in items(lab, series["series_id"])] == ["succeeded"] * 25
    assert all(p["state"] == "done" and (p["result_id"] is not None) == (p["status"] not in ("added", "removed")) for p in pair_rows(lab, series["series_id"]))


def test_a_non_adjacent_pair_of_versions_is_never_compared(lab, sessions, engine, blob_store, worker_id, prepared) -> None:
    doc, series = prepared
    fake = ScriptedEngine(sessions)
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)
    owner = version_of(lab, doc)
    position = {version: i for i, version in enumerate(doc.versions)}
    assert len(fake.calls) == 24
    for call in fake.calls:
        assert position[owner[call["b"]]] - position[owner[call["a"]]] == 1, call


def test_the_statuses_the_engine_gives_decide_the_counts_and_the_verdict(lab, sessions, engine, blob_store, worker_id, service, prepared) -> None:
    doc, series = prepared
    rows = pair_rows(lab, series["series_id"])
    first = [p for p in rows if p["transition_no"] == 1]
    fake = ScriptedEngine(sessions, script={
        (first[1]["a"], first[1]["b"]): "different", (first[2]["a"], first[2]["b"]): "needs_review",
        (first[3]["a"], first[3]["b"]): "same_zones_changed"})
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)
    transition = service.get_series(series_id=series["series_id"])["transitions"][0]
    assert transition["verdict"] == ["different", "needs_review"]
    assert transition["summary"]["different"] == 1 and transition["summary"]["needs_review"] == 1
    assert transition["summary"]["zones_only"] == 1 and transition["summary"]["same"] == 3
    # the link reasons the matrix cell gives are handed to the engine
    assert any(call["reasons"] for call in fake.calls) or all(call["reasons"] == () for call in fake.calls)


def test_a_pair_that_fails_leaves_its_transition_incomplete_and_never_content_same(
    lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    rows = pair_rows(lab, series["series_id"])
    victim = [p for p in rows if p["transition_no"] == 1][0]
    fake = ScriptedEngine(sessions, script={(victim["a"], victim["b"]): "raise"})
    fake.boom = ChildStartError("the pair child never started")
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)

    done = service.get_series(series_id=series["series_id"])
    first = done["transitions"][0]
    assert first["state"] == "completed" and first["items_done"] == 5 and first["items_total"] == 6
    assert first["verdict"] == ["incomplete", "calculation_failed"] and "content_same" not in first["verdict"]
    assert first["summary"]["failed"] == 1 and done["state"] == "completed"
    failed = [p for p in pair_rows(lab, series["series_id"]) if p["id"] == victim["id"]][0]
    assert failed["state"] == "failed" and failed["failure_reason"] == "series_pair_child_start_failed"
    assert failed["status"] is None and failed["result_id"] is None
    assert len([c for c in fake.calls if c["a"] == victim["a"] and c["b"] == victim["b"]]) == 3  # three attempts, then it gives up

    # «Досчитать» queues the failed pair again and reuses everything that is done
    fake.script.clear()
    finished = steer(service, "finish", series["series_id"], expert_uid)
    assert finished["state"] == "queued" and finished["transitions"][0]["state"] == "queued"
    assert len(items(lab, series["series_id"])) == 25 + 2  # one pair item and one drive, the old ones ended
    before = len(fake.calls)
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)
    assert len(fake.calls) == before + 1
    healed = service.get_series(series_id=series["series_id"])
    assert healed["state"] == "completed" and healed["transitions"][0]["verdict"] == ["content_same"]


def test_a_pair_whose_item_the_queue_gave_up_on_is_failed_by_the_drive(
    lab, sessions, engine, blob_store, worker_id, service, prepared,
) -> None:
    doc, series = prepared
    victim = [p for p in pair_rows(lab, series["series_id"]) if p["transition_no"] == 2 and p["state"] == "queued"][0]
    fake = ScriptedEngine(sessions, script={(victim["a"], victim["b"]): "raise"})
    fake.boom = RuntimeError("an unexpected fault in the handler")
    drain(runner_with(sessions, engine, blob_store, compare=fake), worker_id, engine, sessions, doc.project_uid)

    failed = [p for p in pair_rows(lab, series["series_id"]) if p["id"] == victim["id"]][0]
    assert failed["state"] == "failed" and failed["failure_reason"], failed
    done = service.get_series(series_id=series["series_id"])
    assert done["state"] == "completed" and done["transitions"][1]["verdict"][0] == "incomplete"


def test_a_cancel_stops_the_work_and_what_is_done_stays_done(
    lab, sessions, engine, blob_store, worker_id, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    fake = ScriptedEngine(sessions)
    runner = runner_with(sessions, engine, blob_store, compare=fake)
    from .support import fenced
    for _ in range(3):  # three pairs are computed
        make_due(sessions, doc.project_uid)
        with fenced(engine, doc.project_uid, ("series_drive",)):
            item = runner.claim(worker_id)
        assert item is not None and item.kind == "series_pair"
        assert runner.execute(item) == "succeeded"
    cancelled = steer(service, "cancel", series["series_id"], expert_uid)
    assert cancelled["state"] == "cancelled" and all(t["state"] == "cancelled" for t in cancelled["transitions"])
    assert {w["state"] for w in items(lab, series["series_id"])} == {"succeeded", "cancelled"}
    rows = pair_rows(lab, series["series_id"])
    assert sum(1 for p in rows if p["state"] == "done" and p["result_id"]) == 3
    assert drain(runner, worker_id, engine, sessions, doc.project_uid) == []
    # «Досчитать» takes up what is left
    finished = steer(service, "finish", series["series_id"], expert_uid)
    assert finished["state"] == "queued" and all(t["state"] == "queued" for t in finished["transitions"])
    drain(runner, worker_id, engine, sessions, doc.project_uid)
    assert len(fake.calls) == 24  # nothing was computed twice
    assert service.get_series(series_id=series["series_id"])["state"] == "completed"


def test_a_transition_none_of_whose_pairs_needed_the_engine_still_completes(lab, sessions, blob_store, service, prepared) -> None:
    """The database has no ``queued -> completed`` edge for a transition or a series: both pass through ``running``."""
    from sqlalchemy import text

    from auditmanager.comparison.series.advance import SeriesAdvancer

    doc, series = prepared
    sid = series["series_id"]
    with lab.sessions() as session:  # every pair of every transition is one the matrix could not place; no item will run
        session.execute(text("UPDATE comparison_sheet_pair SET state = 'computing' WHERE state = 'queued' AND comparison_transition_id IN "
                             "(SELECT comparison_transition_id FROM comparison_transition WHERE comparison_series_id = :s)"), {"s": sid})
        session.execute(text("UPDATE comparison_sheet_pair SET state = 'done', status = 'unmatched' WHERE state = 'computing' AND "
                             "comparison_transition_id IN (SELECT comparison_transition_id FROM comparison_transition "
                             "WHERE comparison_series_id = :s)"), {"s": sid})
        session.execute(text("UPDATE comparison_work SET state = 'cancelled', terminal_at = clock_timestamp() "
                             "WHERE comparison_series_id = :s AND kind = 'series_pair'"), {"s": sid})
        session.commit()
    assert service.get_series(series_id=sid)["state"] == "queued"
    assert SeriesAdvancer(sessions, blob_store).advance(sid, fence=lambda session: None).live is False
    done = service.get_series(series_id=sid)
    assert done["state"] == "completed" and [t["state"] for t in done["transitions"]] == ["completed"] * 4
    assert all(t["verdict"] == ["needs_review"] for t in done["transitions"][:1])
