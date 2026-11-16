"""`R-151a`, `R-151e` and `UIP-G-10` (migrations 0052, 0053, 0070): a document archived, restored, renamed, tagged and grouped, on a real database.

Archive is a reversible flag, never a deletion; a rename keeps the identity; tags are replaced as a whole set, trimmed and
deduplicated without regard to case, at most ten; a group is one optional value of the document, 1 to 40 characters after trimming;
the same state again records nothing; each change is on the trail.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.ingest.lifecycle import (
    clean_group, group_of, rename_document, set_document_archived, set_document_group, set_document_tags, tags_of,
)
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


def test_a_group_is_one_optional_value_set_changed_and_cleared_on_the_trail(session: Session, published) -> None:
    """`UIP-G-10`: the group is the document's own column; a blank value is NULL; the same group again records nothing."""
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    assert group_of(session, published.document_uid) is None
    set_document_group(session, group="  Конструкции   КР ", idempotency_key=_key(), **document)
    assert group_of(session, published.document_uid) == "Конструкции КР"
    set_document_group(session, group="Конструкции КР", idempotency_key=_key(), **document)  # the same group: nothing
    set_document_group(session, group="Инженерные сети", idempotency_key=_key(), **document)
    set_document_group(session, group="   ", idempotency_key=_key(), **document)  # blank clears
    assert group_of(session, published.document_uid) is None
    set_document_group(session, group=None, idempotency_key=_key(), **document)  # already none: nothing
    assert _trail(session, published.document_uid) == ["document.group_set"] * 3
    payloads = [
        dict(row) for row in session.execute(text(
            "SELECT payload FROM audit_event WHERE aggregate_type = 'Document' AND aggregate_id = :d "
            "AND event_type = 'document.group_set' ORDER BY occurred_at, sequence_no"),
            {"d": published.document_uid}).scalars()
    ]
    assert [(p["from"], p["to"]) for p in payloads] == [
        (None, "Конструкции КР"), ("Конструкции КР", "Инженерные сети"), ("Инженерные сети", None),
    ]
    assert all(p["actor_uid"] == actor for p in payloads)


def test_a_group_is_bounded_and_the_database_holds_the_same_bound(session: Session, published) -> None:
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    set_document_group(session, group="Ж" * 40, idempotency_key=_key(), **document)
    assert group_of(session, published.document_uid) == "Ж" * 40
    with pytest.raises(DomainError) as refused:
        set_document_group(session, group="Ж" * 41, idempotency_key=_key(), **document)
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(refused.value.detail_fields)["constraint"] == "length"
    assert clean_group(None) is None and clean_group("") is None and clean_group(" \t ") is None
    # The check of migration 0070 holds what the command stores even for a writer that does not go through it.
    for bad in ("", " x", "x ", "Ж" * 41):
        with pytest.raises(Exception) as rejected:
            with session.begin_nested():
                session.execute(text("UPDATE document SET group_label = :g WHERE document_uid = :d"),
                                {"g": bad, "d": published.document_uid})
        assert "ck_document_group_label_length" in str(rejected.value)


def test_a_group_of_another_project_or_an_unknown_document_is_not_found(session: Session, published) -> None:
    actor = _account(session)
    with pytest.raises(DomainError) as other_project:
        set_document_group(session, project_uid="prj_01M2545JSD15ETSNNV904X991F", document_uid=published.document_uid,
                           group="Конструкции", actor_uid=actor, idempotency_key=_key())
    assert other_project.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as unknown:
        set_document_group(session, project_uid=published.project_uid, document_uid="doc_01M2545JSD15ETSNNV904X991H",
                           group="Конструкции", actor_uid=actor, idempotency_key=_key())
    assert unknown.value.code is ErrorCode.NOT_FOUND
    assert group_of(session, published.document_uid) is None


def test_a_group_replays_under_its_key_and_refuses_the_key_for_another_group(session: Session, published) -> None:
    actor = _account(session)
    document = {"project_uid": published.project_uid, "document_uid": published.document_uid, "actor_uid": actor}
    key = _key()
    set_document_group(session, group="Конструкции", idempotency_key=key, **document)
    set_document_group(session, group="Конструкции", idempotency_key=key, **document)  # replay
    assert _trail(session, published.document_uid) == ["document.group_set"]
    with pytest.raises(DomainError) as reused:
        set_document_group(session, group="Инженерные сети", idempotency_key=key, **document)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert group_of(session, published.document_uid) == "Конструкции"
