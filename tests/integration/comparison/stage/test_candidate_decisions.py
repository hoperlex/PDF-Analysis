"""An expert, not a file name or a suggestion, confirms stage candidates."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
import pytest

from auditmanager.comparison.stage.admission import StageCandidateAdmissionService
from auditmanager.comparison.stage.candidates import StageCandidateDecisionService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid

from tests.integration.comparison.stage.test_upload_admission import PDF, RawStreamStore, ready_raw


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def candidate(database: Session):
    sessions, upload_id, file_id = ready_raw(database, kind="pdf", content=PDF)
    proposed = StageCandidateAdmissionService(sessions, RawStreamStore(PDF)).admit(
        upload_id=upload_id, file_id=file_id,
    )[0]
    return sessions, proposed


def test_confirm_is_keyed_expert_choice_with_one_audit_event(comparison_session: Session) -> None:
    sessions, proposed = candidate(comparison_session)
    service = StageCandidateDecisionService(sessions)
    request = {
        "candidate_id": proposed.candidate_id, "stage": "P", "section_code": "AR",
        "designation": "АР-01", "existing_document_uid": None,
        "user_uid": uid("usr"), "actor_roles": frozenset({"expert"}),
        "idempotency_key": f"stage-confirm-{new_ulid()}",
    }
    confirmed = service.confirm(**request)
    assert confirmed.state == "confirmed"
    assert (confirmed.confirmed_stage, confirmed.confirmed_section, confirmed.designation) == (
        "P", "AR", "АР-01",
    )
    assert confirmed.document_uid is None
    assert service.confirm(**request) == confirmed
    assert comparison_session.execute(
        text(
            "SELECT count(*) FROM audit_event WHERE aggregate_id = :candidate "
            "AND event_type = 'stage.upload_candidate_confirmed'"
        ), {"candidate": proposed.candidate_id},
    ).scalar_one() == 1

    with pytest.raises(DomainError) as second:
        service.confirm(**(request | {"idempotency_key": f"another-{new_ulid()}"}))
    assert second.value.code is ErrorCode.CONFLICT
    with pytest.raises(DomainError) as reused:
        service.confirm(**(request | {"designation": "АР-02"}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_reject_is_a_keyed_decision_and_nonexpert_cannot_act(comparison_session: Session) -> None:
    sessions, proposed = candidate(comparison_session)
    service = StageCandidateDecisionService(sessions)
    request = {
        "candidate_id": proposed.candidate_id, "user_uid": uid("usr"),
        "actor_roles": frozenset({"admin"}),
        "idempotency_key": f"stage-reject-{new_ulid()}",
    }
    with pytest.raises(DomainError) as denied:
        service.reject(**request)
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    request["actor_roles"] = frozenset({"expert"})
    rejected = service.reject(**request)
    assert rejected.state == "rejected"
    assert service.reject(**request) == rejected
    assert comparison_session.execute(
        text(
            "SELECT count(*) FROM audit_event WHERE aggregate_id = :candidate "
            "AND event_type = 'stage.upload_candidate_rejected'"
        ), {"candidate": proposed.candidate_id},
    ).scalar_one() == 1


def test_existing_document_must_belong_to_candidate_project(comparison_session: Session) -> None:
    sessions, proposed = candidate(comparison_session)
    foreign_project, foreign_document = uid("prj"), uid("doc")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Other project')"),
        {"project": foreign_project},
    )
    comparison_session.execute(
        text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:document, :project, 'Foreign')"
        ), {"document": foreign_document, "project": foreign_project},
    )
    with pytest.raises(DomainError) as refused:
        StageCandidateDecisionService(sessions).confirm(
            candidate_id=proposed.candidate_id, stage="P", section_code="AR",
            designation="АР-01", existing_document_uid=foreign_document,
            user_uid=uid("usr"), actor_roles=frozenset({"expert"}),
            idempotency_key=f"stage-foreign-{new_ulid()}",
        )
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert comparison_session.execute(
        text("SELECT state FROM stage_upload_candidate WHERE stage_upload_candidate_id = :candidate"),
        {"candidate": proposed.candidate_id},
    ).scalar_one() == "proposed"
