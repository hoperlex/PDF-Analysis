"""``prepareComparisonMatrix`` and the ``matrix_build`` work kind through the real runner (`CMP-MATRIX-01`, ADR-0025
decisions 4, 6, 7): the missing page profiles are enqueued through the profile queue's function, then a build item that
waits for them by yielding, fails with a typed reason when nothing builds them, and writes the matrix once.

The runner is the one the worker builds from the shipped handler tuple (``build_comparison_work``); the database is
shared with other integration directories, so its Run-priority gate reads nothing and every claim is fenced to the
lane's own projects (the technique of ``comparison/profile_queue/conftest.py``)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from unittest import mock

import pytest
from sqlalchemy import text

from auditmanager.bootstrap.composition import build_comparison_work
from auditmanager.comparison.public import (
    ClaimGates,
    ComparisonWorkRepository,
    default_gates,
    matrix_build_dedupe_key,
)

from .support import EXPERT, get, key


@pytest.fixture
def worker(sessions, engine, blob_store):
    """``(runner, claim)`` over the shipped tuple; ``claim(project, kinds=None)`` leases an item of the project."""
    from auditmanager.workers.public import WorkerRegistry

    gates = lambda: ClaimGates(paused=default_gates().paused, run_claimable=lambda session: False)  # noqa: E731
    with mock.patch("auditmanager.comparison.work.runner.default_gates", gates):
        runner = build_comparison_work(
            sessions=sessions, engine=engine, blob_store=blob_store,
            environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"},
        )
    with sessions() as session:
        worker_id = WorkerRegistry().register(session, version="cmp-matrix-01-test", slots=1)
        session.commit()

    @contextmanager
    def fenced(project: str, hold_kinds: tuple[str, ...]) -> Iterator[None]:
        with engine.connect() as fence:
            fence.execute(text(
                "SELECT comparison_work_id FROM comparison_work WHERE state = 'queued' AND (project_uid <> :p "
                "OR kind = ANY (CAST(:k AS text[]))) ORDER BY comparison_work_id FOR UPDATE SKIP LOCKED"),
                {"p": project, "k": list(hold_kinds)})
            try:
                yield
            finally:
                fence.rollback()

    def claim(project: str, hold_kinds: tuple[str, ...] = ()):
        with fenced(project, hold_kinds):
            item = runner.claim(worker_id)
        assert item is not None, "nothing of the lane's project was claimable"
        assert item.project_uid == project
        return item

    return runner, claim


def _items(lab, project: str) -> list[dict]:
    return lab.rows(
        "SELECT comparison_work_id AS id, kind, state, dedupe_key, attempt_count, failure_reason, payload, not_before "
        "FROM comparison_work WHERE project_uid = :p ORDER BY created_at, comparison_work_id", p=project)


def _make_due(lab, work_id: str) -> None:
    with lab.sessions() as session:
        session.execute(text("UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                             "WHERE comparison_work_id = :w"), {"w": work_id})
        session.commit()


def _prepare(service, doc, user, token=None):
    return service.prepare_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid, user_uid=user,
                                  actor_roles=EXPERT, idempotency_key=token or key())


def test_the_build_kind_is_registered_through_the_shipped_tuple(worker) -> None:
    runner, _claim = worker
    assert "matrix_build" in runner.kinds and "page_profile" in runner.kinds
    runner.verify()


def test_prepare_enqueues_the_profiles_then_one_build_and_the_runner_builds_the_matrix(service, lab, worker, expert_uid) -> None:
    runner, claim = worker
    doc = lab.seed_sources(["v1.pdf", "v2.pdf"])
    before = get(service, doc)
    assert (before["state"], before["progress"]) == ("absent", {"total": 12, "ready": 0, "failed": 0}) and "rows" not in before

    token = key()
    preparation = _prepare(service, doc, expert_uid, token)
    assert preparation["state"] == "building" and preparation["progress"]["total"] == 12
    kinds = [(i["kind"], i["state"]) for i in _items(lab, doc.project_uid)]
    assert kinds == [("page_profile", "queued"), ("page_profile", "queued"), ("matrix_build", "queued")]
    build_item = _items(lab, doc.project_uid)[2]
    assert build_item["dedupe_key"] == matrix_build_dedupe_key(doc.document_uid) and build_item["payload"] == {"document_uid": doc.document_uid}
    assert get(service, doc)["state"] == "building"

    # a replay and a second request (another key) put nothing more on the queue: a live item of the key is returned
    _prepare(service, doc, expert_uid, token)
    _prepare(service, doc, expert_uid)
    assert [i["kind"] for i in _items(lab, doc.project_uid)] == ["page_profile", "page_profile", "matrix_build"]

    # the build is claimed first (the profile items are held back): it waits, spends no attempt and writes nothing
    item = claim(doc.project_uid, hold_kinds=("page_profile",))
    assert item.kind == "matrix_build"
    assert runner.execute(item) == "queued"
    waiting = [i for i in _items(lab, doc.project_uid) if i["kind"] == "matrix_build"][0]
    assert (waiting["state"], waiting["attempt_count"]) == ("queued", 0)
    assert lab.rows("SELECT count(*) AS n FROM comparison_matrix WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 0

    # the profiles are built by the same runner, then the build is due again and writes the matrix once
    for _ in range(2):
        profile = claim(doc.project_uid, hold_kinds=("matrix_build",))
        assert profile.kind == "page_profile" and runner.execute(profile) == "succeeded"
    assert get(service, doc)["progress"] == {"total": 12, "ready": 12, "failed": 0}
    _make_due(lab, waiting["id"])
    item = claim(doc.project_uid)
    assert item.kind == "matrix_build" and runner.execute(item) == "succeeded"

    matrix = get(service, doc)
    assert matrix["state"] == "ready" and matrix["counts"]["rows"] == 6 and matrix["revision"]["edit_no"] == 0
    assert all(i["state"] == "succeeded" for i in _items(lab, doc.project_uid))
    # nothing is queued for a build that is current
    again = _prepare(service, doc, expert_uid)
    assert again["state"] == "ready" and [i["kind"] for i in _items(lab, doc.project_uid)].count("matrix_build") == 1


def test_a_build_that_nothing_is_building_profiles_for_fails_with_its_reason_and_no_retry(service, lab, worker) -> None:
    runner, claim = worker
    doc = lab.seed_sources(["v1.pdf", "v2.pdf"])
    with lab.sessions() as session:
        ComparisonWorkRepository().enqueue(
            session, project_uid=doc.project_uid, module="versions", kind="matrix_build",
            payload={"document_uid": doc.document_uid}, dedupe_key=matrix_build_dedupe_key(doc.document_uid))
        session.commit()
    item = claim(doc.project_uid)
    assert runner.execute(item) == "failed"
    [only] = _items(lab, doc.project_uid)
    assert (only["state"], only["failure_reason"], only["attempt_count"]) == ("failed", "matrix_build_profiles_missing", 1)
    state = get(service, doc)
    assert state["state"] == "failed" and state["failure_reason"] == "matrix_build_profiles_missing" and "rows" not in state


def test_a_payload_of_another_shape_and_an_unknown_document_fail_without_a_retry(lab, worker) -> None:
    runner, claim = worker
    project = lab.clone(versions=1).project_uid
    with lab.sessions() as session:
        repository = ComparisonWorkRepository()
        repository.enqueue(session, project_uid=project, module="versions", kind="matrix_build",
                           payload={"document_uid": "not-a-document"}, dedupe_key="matrix_build:a")
        repository.enqueue(session, project_uid=project, module="versions", kind="matrix_build",
                           payload={"document_uid": "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, dedupe_key="matrix_build:b")
        session.commit()
    for _ in range(2):
        assert runner.execute(claim(project)) == "failed"
    assert sorted(i["failure_reason"] for i in _items(lab, project)) == [
        "matrix_build_document_not_found", "matrix_build_payload_invalid"]
