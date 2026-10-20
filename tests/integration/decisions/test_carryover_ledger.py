"""The ledger half of a confirmed carryover (`W59-DECISION-CARRYOVER-01`).

``tests/integration/comparison/test_decision_carryover_db.py`` drives the command through a
recomputed comparison. This suite holds the decisions context's own guards against a
caller that did not: a provenance that names the wrong version, a malformed provenance, and
the two batch projections the candidate list reads, which must agree with the single reads.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.decisions.public import (
    CarryoverProvenance,
    append_decision_under_key,
    carry_over_decision,
    carryover_comment,
    current_verdict,
    current_verdicts,
    decision_events_by_id,
    decision_history,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, FindingUid, VersionUid


def _key() -> str:
    return f"w59carryledger-{uuid.uuid4().hex[:16]}"


def _accept(session: Session, published) -> str:  # noqa: ANN001
    event, _ = append_decision_under_key(
        session, finding_uid=published.finding_uid,
        finding_observation_id=published.finding_observation_id, event_type="accept",
        idempotency_key=_key(), author_label="Эксперт", author_user_uid=None,
    )
    return event.decision_id


def _provenance(published, decision_id: str, **changes) -> CarryoverProvenance:  # noqa: ANN001, ANN003
    values = {
        "source_finding_uid": published.finding_uid,
        "source_decision_id": decision_id,
        "source_version_uid": published.version_uid,
        "source_version_ordinal": 1,
        "target_version_uid": VersionUid.new().value,
        "mode": "version",
    } | changes
    return CarryoverProvenance(**values)


def _account(session: Session) -> str:
    login = f"w59carryledger-{uuid.uuid4().hex[:12]}@example.com"
    return str(UserRepository().create_user(
        session, login, f"w59carryledger-passphrase-{uuid.uuid4().hex}",
    ).user_uid)


def _carry(session: Session, published, provenance: CarryoverProvenance,  # noqa: ANN001, ANN202
           author: str | None = None):
    return carry_over_decision(
        session, provenance=provenance, target_finding_uid=published.second_finding_uid,
        target_finding_observation_id=published.second_finding_observation_id,
        idempotency_key=_key(), author_label="Эксперт",
        author_user_uid=author or _account(session),  # type: ignore[arg-type]
    )


def test_an_unattributed_carryover_is_refused(session, published) -> None:
    provenance = _provenance(published, _accept(session, published))
    with pytest.raises(DomainError) as caught:
        _carry(session, published, provenance, author="local-reviewer")
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.detail_fields["field"] == "author_user_uid"


def test_a_target_of_another_version_than_named_is_refused(session, published) -> None:
    decision = _accept(session, published)
    with pytest.raises(DomainError) as caught:
        _carry(session, published, _provenance(published, decision))
    assert caught.value.code is ErrorCode.CONFLICT
    assert caught.value.detail_fields["conflict_reason"] == "carryover_pair_not_proposed"
    assert decision_history(session, published.second_finding_uid) == ()


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"source_version_ordinal": 0}, "source_version_ordinal"),
        ({"source_version_ordinal": True}, "source_version_ordinal"),
        ({"mode": "object"}, "mode"),
        ({"source_decision_id": "dec_x"}, "source_decision_id"),
        ({"target_version_uid": "ver_x"}, "target_version_uid"),
    ],
)
def test_a_malformed_provenance_is_refused_before_any_read(session, published, changes, field) -> None:
    with pytest.raises(DomainError) as caught:
        carryover_comment(_provenance(published, DecisionId.new().value, **changes))
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert caught.value.detail_fields["field"] == field


def test_the_same_version_on_both_sides_is_not_a_pair(session, published) -> None:
    provenance = _provenance(
        published, DecisionId.new().value, target_version_uid=published.version_uid,
    )
    with pytest.raises(DomainError) as caught:
        _carry(session, published, provenance)
    assert caught.value.detail_fields["conflict_reason"] == "carryover_pair_not_proposed"


def test_the_comment_is_a_fixed_rendering_of_the_provenance(published) -> None:
    provenance = _provenance(published, DecisionId.new().value)
    assert carryover_comment(provenance) == carryover_comment(provenance)
    assert carryover_comment(provenance).startswith("Решение перенесено из версии 1 ")
    other = _provenance(published, provenance.source_decision_id,
                        target_version_uid=provenance.target_version_uid, mode="stage")
    assert carryover_comment(other) != carryover_comment(provenance)


def test_the_batch_projections_agree_with_the_single_reads(session, published) -> None:
    decision = _accept(session, published)
    unknown = FindingUid.new().value
    batch = current_verdicts(
        session, [published.finding_uid, published.second_finding_uid, unknown],
    )
    assert set(batch) == {published.finding_uid, published.second_finding_uid}
    for uid in batch:
        assert batch[uid] == current_verdict(session, uid)
    assert batch[published.second_finding_uid].current_verdict == "pending"
    events = decision_events_by_id(session, [decision, DecisionId.new().value])
    assert list(events) == [decision]
    assert events[decision] == decision_history(session, published.finding_uid)[0]
    assert current_verdicts(session, []) == {} and decision_events_by_id(session, []) == {}
