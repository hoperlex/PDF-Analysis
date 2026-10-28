"""A series that no longer matches its inputs says so (`CMP-SERIES-01`, ADR-0025 decision 21, plan `R3-32`): a reorder, a
manual matrix edit, a version published after it, other page profiles -- each by the digest of the stored inputs."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from auditmanager.ingest.comparison_pdf.public import ComparisonVersionOrderService

from .support import EXPERT, ScriptedEngine, build, drain, key, runner_with, start


@pytest.fixture
def prepared(lab, matrix_service, service, expert_uid):
    doc = lab.clone()
    build(matrix_service, doc)
    return doc, start(service, doc, expert_uid)


def stale(service, series_id: str) -> list[str]:
    return service.get_series(series_id=series_id).get("stale_reasons", [])


def test_a_fresh_series_is_not_stale(service, prepared) -> None:
    doc, series = prepared
    assert stale(service, series["series_id"]) == []
    page = service.list_series(project_uid=doc.project_uid, document_uid=doc.document_uid, after=None, limit=10)
    assert [item.get("stale_reasons") for item in page.items] == [None]


def test_a_manual_edit_of_the_matrix_makes_the_series_matrix_changed(lab, matrix_service, service, expert_uid, prepared) -> None:
    doc, series = prepared
    matrix = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    page = {"version_uid": doc.versions[4], "page_number": 8}
    from auditmanager.comparison.public import MatrixEditInput, MatrixPageRef

    matrix_service.apply_edits(
        project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=matrix["revision"]["matrix_id"],
        base_edit_no=matrix["revision"]["edit_no"], user_uid=expert_uid, actor_label="Э", actor_roles=EXPERT,
        idempotency_key=key(), edits=[MatrixEditInput(kind="unlink", page=MatrixPageRef(**page))])
    assert stale(service, series["series_id"]) == ["matrix_changed"]
    # the series itself is untouched: it keeps the revision it was started on
    assert service.get_series(series_id=series["series_id"])["matrix_revision"] == series["matrix_revision"]


def test_an_undone_edit_is_still_a_change_of_the_revision(lab, matrix_service, service, expert_uid, prepared) -> None:
    doc, series = prepared
    matrix = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    from auditmanager.comparison.public import MatrixEditInput, MatrixPageRef

    applied = matrix_service.apply_edits(
        project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=matrix["revision"]["matrix_id"],
        base_edit_no=0, user_uid=expert_uid, actor_label="Э", actor_roles=EXPERT, idempotency_key=key(),
        edits=[MatrixEditInput(kind="unlink", page=MatrixPageRef(version_uid=doc.versions[4], page_number=8))])
    matrix_service.undo_edit(
        project_uid=doc.project_uid, document_uid=doc.document_uid, base_matrix_id=applied["revision"]["matrix_id"],
        base_edit_no=applied["revision"]["edit_no"], user_uid=expert_uid, actor_label="Э", actor_roles=EXPERT,
        idempotency_key=key())
    assert stale(service, series["series_id"]) == ["matrix_changed"]  # edit events 0 -> 2: the cells may differ in between


def test_a_reorder_makes_the_series_order_changed_and_a_new_matrix_adds_matrix_changed(
    lab, sessions, matrix_service, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    orders = ComparisonVersionOrderService(session_factory=sessions)
    swapped = list(doc.versions)
    swapped[1], swapped[2] = swapped[2], swapped[1]
    orders.append_order(
        project_uid=doc.project_uid, document_uid=doc.document_uid, version_uids=swapped, base_revision_no=0,
        user_uid=expert_uid, actor_label="Э", actor_roles=EXPERT, idempotency_key=key())
    assert stale(service, series["series_id"]) == ["order_changed"]
    # the matrix is rebuilt for the new order (a new build): the series is stale for both reasons
    matrix_service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert stale(service, series["series_id"]) == ["order_changed", "matrix_changed"]


def test_an_order_revision_with_the_same_order_changes_nothing_for_the_series_until_the_matrix_is_rebuilt(
    lab, sessions, matrix_service, service, expert_uid, prepared,
) -> None:
    doc, series = prepared
    ComparisonVersionOrderService(session_factory=sessions).append_order(
        project_uid=doc.project_uid, document_uid=doc.document_uid, version_uids=list(doc.versions), base_revision_no=0,
        user_uid=expert_uid, actor_label="Э", actor_roles=EXPERT, idempotency_key=key())
    assert stale(service, series["series_id"]) == []


def test_a_version_published_after_the_series_makes_it_order_changed(lab, service, prepared) -> None:
    doc, series = prepared
    lab.add_version(doc, profiles=True)
    assert stale(service, series["series_id"]) == ["order_changed"]


def test_a_page_profiled_again_makes_the_series_profiles_changed(lab, service, prepared) -> None:
    """A profile row is frozen; a page is profiled again by deleting its row (only a page no pair names can be) and
    building it anew. The copy of a duplicated sheet (the fifth version's page 8) is such a page."""
    doc, series = prepared
    with lab.sessions() as session:
        deleted = session.execute(text(
            "DELETE FROM comparison_page_profile WHERE version_uid = :v AND page_number = 8"), {"v": doc.versions[4]}).rowcount
        session.commit()
    assert deleted == 1
    assert stale(service, series["series_id"]) == ["profiles_changed"]


def test_another_algorithm_of_the_pair_comparison_is_profiles_changed(service, prepared, monkeypatch) -> None:
    """The contract has no reason of its own for a new ``ALGO_VERSION``; the digest says it, the catch-all names it."""
    from auditmanager.comparison.series import service as service_module

    doc, series = prepared
    monkeypatch.setattr(service_module, "ENGINE_ALGO_VERSION", "vc-next")
    assert stale(service, series["series_id"]) == ["profiles_changed"]


def test_staleness_does_not_depend_on_the_state_of_the_series(lab, sessions, engine, blob_store, worker_id, service, matrix_service,
                                                              expert_uid, prepared) -> None:
    doc, series = prepared
    drain(runner_with(sessions, engine, blob_store, compare=ScriptedEngine(sessions)), worker_id, engine, sessions, doc.project_uid)
    assert service.get_series(series_id=series["series_id"])["state"] == "completed" and stale(service, series["series_id"]) == []
    lab.add_version(doc, profiles=True)
    done = service.get_series(series_id=series["series_id"])
    assert done["state"] == "completed" and done["stale_reasons"] == ["order_changed"]
