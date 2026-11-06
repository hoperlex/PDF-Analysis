"""`R-151a` and `R-151e` (migrations 0052, 0053): a document archived, restored, renamed and tagged, on a real database.

Archive is a reversible flag, never a deletion; a rename keeps the identity; tags are replaced as a whole set, trimmed and
deduplicated without regard to case, at most ten; the same state again records nothing; each change is on the trail.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.ingest.lifecycle import rename_document, set_document_archived, set_document_tags, tags_of
from auditmanager.shared.errors import DomainError, ErrorCode


def _account(session: Session) -> str:
    login = f"r151a-{uuid.uuid4().hex[:12]}@example.com"
    return str(UserRepository().create_user(session, login, f"r151a-passphrase-{uuid.uuid4().hex}").user_uid)


def _key() -> str:
    return f"r151a-{uuid.uuid4().hex[:24]}"


def _trail(session: Session, document_uid: str) -> list[str]:
    return list(session.execute(text(
        "SELECT event_type FROM audit_event WHERE aggregate_type = 'Document' AND aggregate_id = :d "
        "ORDER BY occurred_at, sequence_no"
    ), {"d": document_uid}).scalars())


def test_archive_is_a_reversible_flag_and_each_change_is_on_the_trail(session: Session, published) -> None:
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    set_document_archived(session, archived=True, idempotency_key=_key(), **document)
    set_document_archived(session, archived=True, idempotency_key=_key(), **document)  # already archived: nothing
    row = session.execute(text(
        "SELECT archived_at IS NOT NULL, archived_by_user_uid FROM document WHERE document_uid = :d"),
        {"d": published.document_uid}).one()
    assert tuple(row) == (True, actor)
    set_document_archived(session, archived=False, idempotency_key=_key(), **document)
    assert session.execute(text(
        "SELECT archived_at, archived_by_user_uid FROM document WHERE document_uid = :d"),
        {"d": published.document_uid}).one() == (None, None)
    assert _trail(session, published.document_uid) == ["document.archived", "document.restored"]
    # Nothing was deleted: the version and its run are where they were.
    assert session.execute(text("SELECT count(*) FROM document_version WHERE version_uid = :v"),
                           {"v": published.version_uid}).scalar_one() == 1


def test_a_rename_keeps_the_identity_and_refuses_a_blank_title(session: Session, published) -> None:
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    rename_document(session, display_title="  Пояснительная записка  ", idempotency_key=_key(), **document)
    rename_document(session, display_title="Пояснительная записка", idempotency_key=_key(), **document)
    assert session.execute(text("SELECT display_title FROM document WHERE document_uid = :d"),
                           {"d": published.document_uid}).scalar_one() == "Пояснительная записка"
    assert _trail(session, published.document_uid) == ["document.renamed"]
    with pytest.raises(DomainError) as refused:
        rename_document(session, display_title="   ", idempotency_key=_key(), **document)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED


def test_tags_are_one_set_without_case_duplicates_and_at_most_ten(session: Session, published) -> None:
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    set_document_tags(session, tags=[" Корпус  1 ", "корпус 1", "Секция А"], idempotency_key=_key(), **document)
    assert tags_of(session, published.document_uid) == ["Корпус 1", "Секция А"]
    set_document_tags(session, tags=["Секция А", "Корпус 1"], idempotency_key=_key(), **document)  # the same set
    set_document_tags(session, tags=[], idempotency_key=_key(), **document)
    assert tags_of(session, published.document_uid) == []
    with pytest.raises(DomainError) as refused:
        set_document_tags(session, tags=[f"метка {n}" for n in range(11)], idempotency_key=_key(), **document)
    assert dict(refused.value.detail_fields)["constraint"] == "max_items"
