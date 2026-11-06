"""`R-151g` (migration 0054): the designer's execution status of an accepted finding, on a real database.

Set only on a finding the expert accepted, cleared on any; the same status again records nothing; every change appends
``finding.execution_status_set``; one key is one command (a replay changes nothing); the verdict, the ledger and the
counters are untouched.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.decisions import record_decision
from auditmanager.decisions.execution_status import execution_statuses, set_execution_status
from auditmanager.shared.errors import DomainError, ErrorCode


def _account(session: Session) -> str:
    login = f"r151g-{uuid.uuid4().hex[:12]}@example.com"
    return str(UserRepository().create_user(session, login, f"r151g-passphrase-{uuid.uuid4().hex}").user_uid)


def _key() -> str:
    return f"r151g-{uuid.uuid4().hex[:24]}"


def _events(session: Session, finding_uid: str) -> list[dict]:
    rows = session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'finding.execution_status_set' AND aggregate_id = :f "
        "ORDER BY occurred_at, sequence_no"
    ), {"f": finding_uid}).scalars().all()
    return [dict(row) for row in rows]


def _accept(session: Session, published, finding_uid: str, observation_id: str) -> None:
    record_decision(
        session, finding_uid=finding_uid, finding_observation_id=observation_id, event_type="accept",
        author_label="Эксперт", author_user_uid=None,
    )


def test_an_accepted_finding_takes_a_status_and_every_change_is_on_the_trail(session: Session, published) -> None:
    actor = _account(session)
    _accept(session, published, published.finding_uid, published.finding_observation_id)
    ledger_before = session.execute(text(
        "SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"), {"f": published.finding_uid}).scalar_one()

    set_execution_status(session, finding_uid=published.finding_uid, status="amended", actor_uid=actor,
                         idempotency_key=_key())
    assert execution_statuses(session, [published.finding_uid])[published.finding_uid][0] == "amended"

    # The same status again (a new command) records nothing.
    set_execution_status(session, finding_uid=published.finding_uid, status="amended", actor_uid=actor,
                         idempotency_key=_key())
    set_execution_status(session, finding_uid=published.finding_uid, status=None, actor_uid=actor,
                         idempotency_key=_key())
    assert execution_statuses(session, [published.finding_uid]) == {}
    assert [(event["from"], event["to"]) for event in _events(session, published.finding_uid)] == [
        (None, "amended"), ("amended", None),
    ]
    # Not a decision: the ledger and the verdict are as the accept left them.
    assert session.execute(text(
        "SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"), {"f": published.finding_uid}
    ).scalar_one() == ledger_before
    assert session.execute(text(
        "SELECT current_verdict FROM finding_current_verdict WHERE finding_uid = :f"), {"f": published.finding_uid}
    ).scalar_one() == "accepted"


def test_a_finding_not_accepted_is_refused_a_status_and_may_be_cleared(session: Session, published) -> None:
    actor = _account(session)
    with pytest.raises(DomainError) as refused:
        set_execution_status(session, finding_uid=published.second_finding_uid, status="agreed", actor_uid=actor,
                             idempotency_key=_key())
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
    assert dict(refused.value.detail_fields)["constraint"] == "finding_not_accepted"
    set_execution_status(session, finding_uid=published.second_finding_uid, status=None, actor_uid=actor,
                         idempotency_key=_key())
    assert _events(session, published.second_finding_uid) == []


def test_one_key_is_one_command(session: Session, published) -> None:
    actor = _account(session)
    _accept(session, published, published.finding_uid, published.finding_observation_id)
    key = _key()
    for _ in range(2):
        set_execution_status(session, finding_uid=published.finding_uid, status="declined", actor_uid=actor,
                             idempotency_key=key)
    assert len(_events(session, published.finding_uid)) == 1
    with pytest.raises(DomainError) as reused:
        set_execution_status(session, finding_uid=published.finding_uid, status="agreed", actor_uid=actor,
                             idempotency_key=key)
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_an_unknown_finding_is_not_found(session: Session) -> None:
    with pytest.raises(DomainError) as missing:
        set_execution_status(session, finding_uid="fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z", status=None,
                             actor_uid=_account(session), idempotency_key=_key())
    assert missing.value.code is ErrorCode.NOT_FOUND
