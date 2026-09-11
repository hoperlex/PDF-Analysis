"""The idempotency key an API caller supplies must reach the ledger.

``expert_decision_event.command_id`` is a foreign key into ``command_record``. Before this
existed, ``record_decision`` accepted a ``command_id`` that nothing ever claimed, so the
header the frozen contract requires on ``appendDecision`` had nowhere to go and a repeat
appended a **second event** to an append-only ledger. `B6` saw the gap from the edge and
`B4` from the ledger; neither could close it from inside its own tree.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from auditmanager.decisions import append_decision_under_key, decision_history
from auditmanager.shared.errors import DomainError, ErrorCode

from sqlalchemy.orm import Session


def _key() -> str:
    return f"k-{uuid.uuid4().hex[:20]}"


class TestTheKeyIsClaimedNotHashed:
    def test_a_repeat_under_one_key_appends_exactly_one_event(
        self, session: Session, published
    ) -> None:
        if True:
            finding_uid = published.finding_uid
            observation_id = published.finding_observation_id
            key = _key()
            first, replayed_first = append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=observation_id,
                event_type="accept",
                idempotency_key=key,
            )
            second, replayed_second = append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=observation_id,
                event_type="accept",
                idempotency_key=key,
            )
            assert replayed_first is False
            assert replayed_second is True
            assert first.decision_id == second.decision_id
            assert len(decision_history(session, finding_uid)) == 1

    def test_the_command_id_resolves_to_a_real_command_record(
        self, session: Session, published
    ) -> None:
        """The foreign key is satisfied by a claim, not by a value that looks like one."""
        if True:
            finding_uid = published.finding_uid
            observation_id = published.finding_observation_id
            event, _ = append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=observation_id,
                event_type="reject",
                idempotency_key=_key(),
            )
            assert event.command_id is not None
            row = session.execute(
                text(
                    "SELECT command_type, state FROM command_record WHERE command_id = :c"
                ),
                {"c": event.command_id},
            ).first()
            assert row is not None, "command_id points at no command_record row"
            assert row[0] == "append_decision"
            assert row[1] == "succeeded"

    def test_the_same_key_with_a_different_payload_is_refused(
        self, session: Session, published
    ) -> None:
        import pytest

        if True:
            finding_uid = published.finding_uid
            observation_id = published.finding_observation_id
            key = _key()
            append_decision_under_key(
                session,
                finding_uid=finding_uid,
                finding_observation_id=observation_id,
                event_type="accept",
                idempotency_key=key,
            )
            with pytest.raises(DomainError) as caught:
                append_decision_under_key(
                    session,
                    finding_uid=finding_uid,
                    finding_observation_id=observation_id,
                    event_type="reject",
                    idempotency_key=key,
                )
            assert caught.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
            assert len(decision_history(session, finding_uid)) == 1
