"""``startComparisonSeries`` (`CMP-SERIES-01`, ADR-0025 decisions 14, 16, 19, 21): what is written, what is refused, and
that a repeat of the key answers the first series."""

from __future__ import annotations

import pytest

from auditmanager.shared.errors import DomainError, ErrorCode

from .support import ADMIN, build, items, key, pair_rows, start, steer


def reason(failure: pytest.ExceptionInfo[DomainError]) -> str | None:
    return failure.value.detail_fields.get("conflict_reason")


def test_a_series_is_written_with_every_adjacent_transition_every_pair_and_its_work(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    matrix = build(matrix_service, doc)
    series = start(service, doc, expert_uid)

    assert series["state"] == "queued" and series["project_uid"] == doc.project_uid and series["document_uid"] == doc.document_uid
    assert series["matrix_revision"] == matrix["revision"] and "restarted_from" not in series and "stale_reasons" not in series
    assert (series["transitions_total"], series["transitions_done"]) == (4, 0)
    transitions = series["transitions"]
    assert [(t["source_version_uid"], t["target_version_uid"]) for t in transitions] == list(zip(doc.versions, doc.versions[1:]))
    assert all(t["state"] == "queued" and "verdict" not in t for t in transitions)
    assert [t["items_total"] for t in transitions] == [6, 7, 6, 7]  # the matrix's pairs: the split's second part is a pair of its own
    assert all(t["items_done"] == 0 or t["summary"]["added"] + t["summary"]["removed"] for t in transitions)

    pairs = pair_rows(lab, series["series_id"])
    assert len(pairs) == 26
    compared = [p for p in pairs if p["state"] == "queued"]
    immediate = [p for p in pairs if p["state"] == "done"]
    assert {p["status"] for p in immediate} == {"added", "removed"} and len(immediate) == 2 and len(compared) == 24
    assert all(p["a"] and p["b"] for p in compared) and all(p["result_id"] is None for p in pairs)

    work = items(lab, series["series_id"])
    assert sorted(w["kind"] for w in work) == ["series_drive"] + ["series_pair"] * 24
    assert all(w["state"] == "queued" and w["comparison_series_id"] == series["series_id"] for w in work)
    # earlier transitions run first
    by_pair = {w["payload"]["sheet_pair_id"]: w["priority"] for w in work if w["kind"] == "series_pair"}
    assert [by_pair[p["id"]] for p in compared if p["transition_no"] == 1][0] > [by_pair[p["id"]] for p in compared if p["transition_no"] == 4][0]


def test_the_series_binds_the_matrix_revision_and_the_input_digest(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    matrix = build(matrix_service, doc)
    series = start(service, doc, expert_uid)
    row = lab.rows("SELECT comparison_matrix_id, matrix_edit_no, input_sha256, order_id, actor_user_uid, actor_label "
                   "FROM comparison_series WHERE comparison_series_id = :s", s=series["series_id"])[0]
    assert (row["comparison_matrix_id"], row["matrix_edit_no"]) == (matrix["revision"]["matrix_id"], matrix["revision"]["edit_no"])
    assert len(row["input_sha256"]) == 64 and row["order_id"] is None
    assert (row["actor_user_uid"], row["actor_label"]) == (expert_uid, "Эксперт Т.")


def test_one_live_series_for_a_document_set(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    first = start(service, doc, expert_uid)
    with pytest.raises(DomainError) as refused:
        start(service, doc, expert_uid)
    assert refused.value.code is ErrorCode.CONFLICT and reason(refused) == "comparison_series_active"
    with pytest.raises(DomainError) as restart:
        start(service, doc, expert_uid, restart=True)
    assert reason(restart) == "comparison_series_active"
    assert lab.rows("SELECT count(*) AS n FROM comparison_series WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 1
    # a document set of its own is not held by another's series
    other = lab.clone()
    build(matrix_service, other)
    assert start(service, other, expert_uid)["series_id"] != first["series_id"]


def test_a_matrix_that_is_not_ready_is_refused(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    with pytest.raises(DomainError) as absent:
        start(service, doc, expert_uid)
    assert absent.value.code is ErrorCode.CONFLICT and reason(absent) == "comparison_matrix_stale"
    build(matrix_service, doc)
    version = lab.add_version(doc, profiles=True)  # a version published after the build: the build no longer matches
    assert matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)["state"] == "stale"
    with pytest.raises(DomainError) as stale:
        start(service, doc, expert_uid)
    assert reason(stale) == "comparison_matrix_stale"
    assert version not in doc.versions
    assert lab.rows("SELECT count(*) AS n FROM comparison_series WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 0


def test_a_document_set_of_one_version_has_nothing_to_compare(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone(versions=1)
    build(matrix_service, doc)
    with pytest.raises(DomainError) as refused:
        start(service, doc, expert_uid)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_the_order_revision_the_caller_saw_must_be_the_latest(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    with pytest.raises(DomainError) as stale:
        start(service, doc, expert_uid, base=7)
    assert stale.value.code is ErrorCode.CONFLICT and reason(stale) == "comparison_version_order_stale"
    assert start(service, doc, expert_uid, base=0)["state"] == "queued"  # no revision: 0


def test_a_repeat_of_the_key_answers_the_first_series_and_another_payload_is_refused(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    token = key()
    first = start(service, doc, expert_uid, idempotency_key=token)
    again = start(service, doc, expert_uid, idempotency_key=token)
    assert again["series_id"] == first["series_id"]
    assert lab.rows("SELECT count(*) AS n FROM comparison_series WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 1
    assert len(items(lab, first["series_id"])) == 25  # not queued twice
    with pytest.raises(DomainError) as other:
        start(service, doc, expert_uid, idempotency_key=token, restart=True)
    assert other.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_a_refused_start_leaves_nothing_and_its_key_is_free(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    token = key()
    with pytest.raises(DomainError):
        start(service, doc, expert_uid, idempotency_key=token)  # no matrix yet
    build(matrix_service, doc)
    assert start(service, doc, expert_uid, idempotency_key=token)["state"] == "queued"


def test_a_start_is_an_experts_act(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    with pytest.raises(DomainError) as refused:
        start(service, doc, expert_uid, roles=ADMIN)
    assert refused.value.code is ErrorCode.PERMISSION_DENIED
    assert lab.rows("SELECT count(*) AS n FROM comparison_series WHERE document_uid = :d", d=doc.document_uid)[0]["n"] == 0


def test_an_unknown_project_or_a_document_of_another_project_is_not_found(lab, service, matrix_service, expert_uid) -> None:
    doc, other = lab.clone(), lab.clone()
    build(matrix_service, doc)
    for project, document in (("prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", doc.document_uid), (other.project_uid, doc.document_uid)):
        with pytest.raises(DomainError) as missing:
            service.start_series(project_uid=project, document_uid=document, restart=False, base_order_revision_no=None,
                                 user_uid=expert_uid, actor_label="Э", actor_roles=frozenset({"expert"}), idempotency_key=key())
        assert missing.value.code is ErrorCode.NOT_FOUND


def test_a_restart_names_the_series_it_replaced(lab, service, matrix_service, expert_uid) -> None:
    doc = lab.clone()
    build(matrix_service, doc)
    first = start(service, doc, expert_uid)
    steer(service, "cancel", first["series_id"], expert_uid)
    second = start(service, doc, expert_uid, restart=True)
    assert second["restarted_from"] == first["series_id"] and second["series_id"] != first["series_id"]
    # a plain start after the replacement does not name anything
    steer(service, "cancel", second["series_id"], expert_uid)
    assert "restarted_from" not in start(service, doc, expert_uid)
