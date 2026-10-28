"""The overview only reads, and only its own project (`CMP-VC-OVERVIEW-01`; seal section 3: any role reads, an absent
project is ``404``; the brief: no write, no enqueue, a project never leaks into another's rows)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import InternalError, OperationalError, ProgrammingError

from auditmanager.comparison.overview import repository as overview_repository
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import Doc, Lab
from .test_bounded import populate


def _without_time(overview: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in overview.items() if k != "generated_at"}


# -- an absent project ---------------------------------------------------------------------------------------------------


def test_an_absent_project_is_not_found_and_never_an_empty_overview(service) -> None:
    with pytest.raises(DomainError) as refusal:
        service.get_overview(project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert refusal.value.code is ErrorCode.NOT_FOUND
    assert dict(refusal.value.detail_fields)["aggregate_type"] == "Project"


# -- no write, no enqueue --------------------------------------------------------------------------------------------------


def test_neither_read_changes_a_row_of_any_table(lab: Lab, service) -> None:
    project = populate(lab, 6)
    before = lab.counts()
    first = service.get_overview(project_uid=project)
    service.get_queue_summary(modules="versions")
    service.get_overview(project_uid=project)
    assert lab.counts() == before, {t: (before[t], n) for t, n in lab.counts().items() if before[t] != n}
    assert _without_time(first) == _without_time(service.get_overview(project_uid=project))


def test_neither_read_enqueues_work_even_for_a_set_that_needs_preparation(lab: Lab, service) -> None:
    doc = lab.document(lab.project(), profiles="none")
    before = lab.rows("SELECT count(*) AS n FROM comparison_work")[0]["n"]
    overview = service.get_overview(project_uid=doc.project_uid)
    assert overview["sets"][0]["next_step"] == "profile"  # it proposes the preparation and starts nothing
    assert lab.rows("SELECT count(*) AS n FROM comparison_work")[0]["n"] == before


def test_the_reads_run_in_a_transaction_the_database_refuses_to_write_in(lab: Lab, service, monkeypatch) -> None:
    """The structural guard: a write attempted inside either read is refused by PostgreSQL itself."""
    project = lab.project()
    refused: list[str] = []
    original = overview_repository.OverviewRepository.documents

    def writes_then_reads(self: Any, session: Any, project_uid: str) -> Any:
        try:
            session.execute(text("INSERT INTO project (project_uid, name) VALUES ('prj_01ARZ3NDEKTSV4RRFFQ69G5FAZ', 'x')"))
        except (InternalError, OperationalError, ProgrammingError) as failure:
            refused.append(str(failure.orig))
            session.rollback()
            session.connection(execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True})
        return original(self, session, project_uid)

    monkeypatch.setattr(overview_repository.OverviewRepository, "documents", writes_then_reads)
    service.get_overview(project_uid=project)
    assert refused and "read-only" in refused[0].lower(), refused
    assert lab.rows("SELECT count(*) AS n FROM project WHERE project_uid = 'prj_01ARZ3NDEKTSV4RRFFQ69G5FAZ'")[0]["n"] == 0


# -- one project's rows only -----------------------------------------------------------------------------------------------


def _busy(lab: Lab, project: str) -> list[Doc]:
    """Facts of every kind in a project: profiles, a build, a series, queue items of all three kinds, a pending batch."""
    docs = []
    for index in range(3):
        doc = lab.document(project, title=f"Чужой {index}", profiles="all" if index else "none")
        docs.append(doc)
        lab.work(project, "page_profile", "running", key=f"page_profile:{doc.versions[0]}", payload={"version_uid": doc.versions[0]})
        lab.work(project, "matrix_build", "failed", key=f"matrix_build:{doc.document_uid}", payload={"document_uid": doc.document_uid})
        lab.work(project, "series_after_preparation", "queued", key=f"series_after_preparation:cus_{doc.document_uid[-20:]}",
                 payload={"document_uid": doc.document_uid, "set_id": "cus_x", "actor_label": "Э"})
        if index:
            build = lab.build(doc, lab.aligned_rows(doc, unmatched=1))
            lab.series(doc, build, "completed")
    lab.upload(project, "processing", sets=("needs_confirmation",))
    return docs


def test_another_projects_documents_work_and_batches_never_reach_a_row(lab: Lab, service) -> None:
    mine = lab.project()
    own = [lab.document(mine, title="Мой 1"), lab.document(mine, title="Мой 2", profiles="none")]
    alone = _without_time(service.get_overview(project_uid=mine))
    other = lab.project()
    foreign = _busy(lab, other)
    after = service.get_overview(project_uid=mine)
    assert _without_time(after) == alone, "another project's activity changed this project's overview"
    assert {s["document_uid"] for s in after["sets"]} == {d.document_uid for d in own}
    assert after["pending_uploads"] == []
    elsewhere = service.get_overview(project_uid=other)
    assert {s["document_uid"] for s in elsewhere["sets"]} == {d.document_uid for d in foreign}
    assert len(elsewhere["pending_uploads"]) == 1
    assert elsewhere["totals"] == {"versions": 9, "transitions": 6}


def test_a_work_item_names_the_document_of_its_own_project_only(lab: Lab, service) -> None:
    """A follow-up whose payload names a document of another project does not queue this project's series."""
    mine = lab.project()
    doc = lab.document(mine)
    lab.build(doc, lab.aligned_rows(doc))
    other = lab.project()
    lab.work(other, "series_after_preparation", "queued", key="series_after_preparation:cus_foreign",
             payload={"document_uid": doc.document_uid, "set_id": "cus_x", "actor_label": "Э"})
    lab.work(other, "matrix_build", "failed", key=f"matrix_build:{doc.document_uid}", payload={"document_uid": doc.document_uid})
    lab.work(other, "page_profile", "queued", key=f"page_profile:{doc.versions[0]}", payload={"version_uid": doc.versions[0]})
    (row,) = service.get_overview(project_uid=mine)["sets"]
    states = {s["step"]: s["state"] for s in row["steps"]}
    assert states["series"] == "not_started" and states["matrix"] == "done" and states["profile"] == "done"


# -- the counters, the totals, the metadata ----------------------------------------------------------------------------------


def _group(row: dict[str, Any]) -> str:
    """The derivation a client makes from a row, written out here (the report gives it to the screen)."""
    proposed = row.get("next_step")
    if proposed is None:
        return "ready"
    state = {s["step"]: s["state"] for s in row["steps"]}[proposed]
    if state in ("queued", "running", "pausing"):
        return "running"
    if state == "failed" and proposed in ("upload", "profile", "matrix"):
        return "failed"
    return "waiting"


def test_the_counters_equal_the_rows_and_the_totals_equal_the_versions(lab: Lab, service) -> None:
    project = populate(lab, 12)
    _busy(lab, project)
    overview = service.get_overview(project_uid=project)
    rows = overview["sets"]
    groups = [_group(r) for r in rows]
    c = overview["counters"]
    assert c == {"all": len(rows), "waiting": groups.count("waiting"), "running": groups.count("running"),
                 "failed": groups.count("failed"), "ready": groups.count("ready")}
    assert c["waiting"] + c["running"] + c["failed"] + c["ready"] == c["all"] == 15
    assert overview["totals"] == {"versions": sum(r["version_count"] for r in rows),
                                  "transitions": sum(max(0, r["version_count"] - 1) for r in rows)}
    assert {"waiting", "running", "ready"} <= {g for g in groups}, groups  # the fixture reaches several groups


def test_the_metadata_of_the_admitting_set_is_the_rows_and_a_set_without_one_has_none(lab: Lab, service) -> None:
    project = lab.project()
    stamped = lab.document(project, title="Пояснительная записка")
    lab.stamp(stamped, designation="133/23-ГК-ПЗ", stage="P", section="PS")
    plain = lab.document(project, title="Без шифра")
    rows = {r["document_uid"]: r for r in service.get_overview(project_uid=project)["sets"]}
    assert rows[stamped.document_uid]["designation"] == "133/23-ГК-ПЗ"
    assert rows[stamped.document_uid]["project_stage"] == "P" and rows[stamped.document_uid]["section_code"] == "PS"
    assert rows[stamped.document_uid]["title"] == "Пояснительная записка"
    for key in ("designation", "project_stage", "section_code"):
        assert key not in rows[plain.document_uid]
    assert rows[plain.document_uid]["title"] == "Без шифра"


def test_the_rows_are_in_a_stable_order_by_designation_then_title(lab: Lab, service) -> None:
    project = lab.project()
    b = lab.document(project, title="Б"); lab.stamp(b, designation="ЭМ-2")
    a = lab.document(project, title="Я"); lab.stamp(a, designation="ЭМ-1")
    n = lab.document(project, title="А")
    first = [r["document_uid"] for r in service.get_overview(project_uid=project)["sets"]]
    assert first == [a.document_uid, b.document_uid, n.document_uid]
    assert first == [r["document_uid"] for r in service.get_overview(project_uid=project)["sets"]]


def test_the_date_of_a_row_is_its_last_upload(lab: Lab, service) -> None:
    from datetime import UTC, datetime

    project = lab.project()
    doc = lab.document(project, published_at=datetime(2026, 3, 1, tzinfo=UTC))
    (row,) = service.get_overview(project_uid=project)["sets"]
    assert row["updated_at"] == datetime(2026, 3, 1, tzinfo=UTC) and row["document_uid"] == doc.document_uid


# -- the batches still being uploaded ----------------------------------------------------------------------------------------


def test_pending_uploads_are_the_batches_that_are_not_finished(lab: Lab, service) -> None:
    project = lab.project()
    uploading = lab.upload(project, "uploading", sets=("uploading", "uploading"))
    proposed = lab.upload(project, "proposed", sets=("needs_confirmation", "failed", "excluded"))
    processing = lab.upload(project, "processing")
    paused = lab.upload(project, "paused")
    lab.upload(project, "completed")
    lab.upload(project, "cancelled")
    done = lab.document(project)
    lab.stamp(done, designation="ЭМ-1")  # a completed batch with a done set: not pending
    pending = {u["upload_id"]: u for u in service.get_overview(project_uid=project)["pending_uploads"]}
    assert set(pending) == {uploading, proposed, processing, paused}
    assert pending[uploading] == {"upload_id": uploading, "state": "uploading", "declared_files": 2, "sets_total": 2, "sets_done": 0}
    assert pending[proposed]["sets_total"] == 2, "an excluded set is decided and is not counted"
    assert pending[processing]["sets_total"] == 0 and pending[paused]["state"] == "paused"
