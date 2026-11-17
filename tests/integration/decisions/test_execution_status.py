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
from auditmanager.decisions import decision_journal, record_decision
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


# ----------------------------------------------------------------------------- the journal (`UIP-S12-01`)


def _journal(session: Session, published, **filters):
    """The journal of the fixture's own project: absolute, whatever else the database holds."""
    return decision_journal(session, project_uid=published.project_uid, **filters)


def _entries(session: Session, published, **filters) -> set[tuple[str, str]]:
    return {(entry.finding_uid, entry.event_type) for entry in _journal(session, published, **filters)}


def _two_findings(session: Session, published) -> tuple[str, str]:
    """The first finding accepted after a comment (two events), the second only accepted (one)."""
    first, second = published.finding_uid, published.second_finding_uid
    record_decision(
        session, finding_uid=first, finding_observation_id=published.finding_observation_id, event_type="comment",
        comment="к принятому", author_label="Эксперт", author_user_uid=None,
    )
    _accept(session, published, first, published.finding_observation_id)
    _accept(session, published, second, published.second_finding_observation_id)
    return first, second


def test_an_entry_carries_the_status_of_its_finding_and_a_finding_without_one_carries_none(
    session: Session, published
) -> None:
    first, second = _two_findings(session, published)
    assert {entry.execution_status for entry in _journal(session, published)} == {None}, "no status was set yet"
    set_execution_status(session, finding_uid=first, status="amended", actor_uid=_account(session), idempotency_key=_key())
    at = execution_statuses(session, [first])[first][1]

    for entry in _journal(session, published):
        if entry.finding_uid == first:
            # Both events of the finding -- the comment, which carries no verdict, and the accept -- read the finding's status.
            assert (entry.execution_status, entry.execution_status_at) == ("amended", at), entry.event_type
        else:
            assert (entry.execution_status, entry.execution_status_at) == (None, None)
    assert len([e for e in _journal(session, published) if e.finding_uid == first]) == 2, "one status, not one row per join"


def test_the_filter_keeps_the_findings_with_any_of_the_statuses_and_none_of_the_others(
    session: Session, published
) -> None:
    first, second = _two_findings(session, published)
    actor = _account(session)
    both = {(first, "comment"), (first, "accept"), (second, "accept")}
    assert _entries(session, published) == both

    set_execution_status(session, finding_uid=first, status="amended", actor_uid=actor, idempotency_key=_key())
    # The second finding is accepted and has no status: it is in none of the groups.
    assert _entries(session, published, execution_statuses=["amended"]) == {(first, "comment"), (first, "accept")}
    assert _entries(session, published, execution_statuses=["agreed"]) == set()
    assert _entries(session, published, execution_statuses=["agreed", "declined", "taken_into_account"]) == set()

    set_execution_status(session, finding_uid=second, status="agreed", actor_uid=actor, idempotency_key=_key())
    assert _entries(session, published, execution_statuses=["agreed"]) == {(second, "accept")}
    assert _entries(session, published, execution_statuses=["amended", "agreed"]) == both
    assert _entries(session, published, execution_statuses=("agreed", "amended", "agreed")) == both, "a repeated value is one value"
    assert _entries(session, published, execution_statuses=["declined"]) == set()
    # The same filter in another order is the same answer, and the order of the journal is the journal's own.
    assert [e.decision_id for e in _journal(session, published, execution_statuses=["agreed", "amended"])] == [
        e.decision_id for e in _journal(session, published, execution_statuses=["amended", "agreed"])
    ] == [e.decision_id for e in _journal(session, published)]

    # Clearing the status takes the finding out of its group at once.
    set_execution_status(session, finding_uid=first, status=None, actor_uid=actor, idempotency_key=_key())
    assert _entries(session, published, execution_statuses=["amended"]) == set()
    assert _entries(session, published, execution_statuses=["agreed"]) == {(second, "accept")}


def test_the_filter_composes_with_the_verdict_and_the_category(session: Session, published) -> None:
    first, second = _two_findings(session, published)
    actor = _account(session)
    set_execution_status(session, finding_uid=first, status="declined", actor_uid=actor, idempotency_key=_key())
    set_execution_status(session, finding_uid=second, status="declined", actor_uid=actor, idempotency_key=_key())
    everything = _entries(session, published, execution_statuses=["declined"])
    assert {finding for finding, _ in everything} == {first, second}
    assert _entries(session, published, execution_statuses=["declined"], verdict="accepted") == everything
    assert _entries(session, published, execution_statuses=["declined"], verdict="rejected") == set()
    assert _entries(session, published, execution_statuses=["declined"], category="explicit_placeholder") == {
        (second, "accept")
    }, "the second finding is the placeholder, the first the contradiction"
    assert _entries(session, published, execution_statuses=["declined"], category="internal_contradiction") == {
        (first, "comment"), (first, "accept")
    }


def test_a_status_is_not_a_decision_the_journal_and_its_counts_are_the_same_with_and_without_it(
    session: Session, published
) -> None:
    """`R-151g`: setting, changing and clearing a status adds no entry and moves no verdict or count of the journal."""
    first, second = _two_findings(session, published)
    actor = _account(session)

    def shape() -> list[tuple[str, str, str | None, str, int]]:
        return [
            (e.decision_id, e.finding_uid, e.verdict, e.current_verdict, e.decision_event_count)
            for e in _journal(session, published)
        ]

    before = shape()
    assert len(before) == 3
    for status in ("agreed", "declined", None):
        set_execution_status(session, finding_uid=first, status=status, actor_uid=actor, idempotency_key=_key())
        assert shape() == before, f"setting {status!r} moved the journal"
    set_execution_status(session, finding_uid=second, status="taken_into_account", actor_uid=actor, idempotency_key=_key())
    assert shape() == before
    assert session.execute(text(
        "SELECT count(*) FROM expert_decision_event WHERE finding_uid IN (:a, :b)"), {"a": first, "b": second}
    ).scalar_one() == 3


def test_an_empty_set_of_statuses_is_refused_and_is_neither_no_filter_nor_nothing(session: Session, published) -> None:
    _two_findings(session, published)
    with pytest.raises(ValueError):
        decision_journal(session, project_uid=published.project_uid, execution_statuses=[])
