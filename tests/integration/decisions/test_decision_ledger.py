"""The append-only ledger and the current-verdict projection.

The claim under test is not "the module appends" — it is that nothing anywhere can do
anything else. So the refusals are asserted against the database with raw SQL, past the
module entirely, and the projection is compared against a fold of the raw event stream
rather than against the module's own reading of it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.decisions import (
    DECLARED_EVENT_TYPES,
    PC01_EVENT_TYPES,
    current_verdict,
    decision_history,
    rebuild_current_verdict,
    record_decision,
)
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, FindingUid


class TestTheJourneyAppendsAndUpdatesNothing:
    def test_accept_then_comment_then_reject_appends_three_events(
        self, session: Session, published
    ) -> None:
        """The PC-01 journey. Three events, three identities, nothing overwritten."""
        accept = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        commented = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="comment",
            comment="Проверено по разделу АР.",
            author_label="reviewer-1",
        )
        reject = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label="reviewer-1",
        )

        identities = {accept.decision_id, commented.decision_id, reject.decision_id}
        assert len(identities) == 3, "every event carries a fresh decision_id"

        history = decision_history(session, published.finding_uid)
        assert [event.event_type for event in history] == ["accept", "comment", "reject"]
        assert [event.verdict for event in history] == ["accepted", None, "rejected"]

        # The superseded accept is still there, unchanged. History is the point.
        assert history[0].decision_id == accept.decision_id
        assert history[0].verdict == "accepted"

    def test_the_projection_equals_the_last_valid_event(
        self, session: Session, published
    ) -> None:
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        projection = current_verdict(session, published.finding_uid)
        assert projection is not None
        assert projection.current_verdict == "accepted"

        rejected = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label="reviewer-1",
        )
        projection = current_verdict(session, published.finding_uid)
        assert projection.current_verdict == "rejected"
        assert projection.latest_verdict_decision_id == rejected.decision_id
        assert projection.decision_event_count == 2

    def test_appending_a_comment_after_a_verdict_does_not_overwrite_history(
        self, session: Session, published
    ) -> None:
        """A comment moves the latest event and leaves the verdict where it was."""
        accept = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        before = current_verdict(session, published.finding_uid)
        assert before.current_verdict == "accepted"
        assert before.latest_decision_id == accept.decision_id

        commented = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="comment",
            comment="Согласовано с ГИП.",
            author_label="reviewer-1",
        )
        after = current_verdict(session, published.finding_uid)

        assert after.current_verdict == "accepted", "a comment is not a judgement"
        assert after.latest_verdict_decision_id == accept.decision_id
        assert after.latest_decision_id == commented.decision_id
        assert after.latest_comment == "Согласовано с ГИП."
        assert after.latest_comment_decision_id == commented.decision_id
        assert after.decision_event_count == 2
        assert after.decision_recorded_at >= before.decision_recorded_at, (
            "decision_recorded_at describes the most recent event of any type, so "
            "appending a comment moves it"
        )

        # The accept row itself is byte-for-byte what it was.
        history = decision_history(session, published.finding_uid)
        assert history[0].decision_id == accept.decision_id
        assert history[0].verdict == "accepted"
        assert history[0].comment is None

    def test_a_comment_on_an_untouched_finding_leaves_it_pending(
        self, session: Session, published
    ) -> None:
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="comment",
            comment="Нужна проверка.",
            author_label="reviewer-1",
        )
        projection = current_verdict(session, published.finding_uid)
        assert projection.current_verdict == "pending"
        assert projection.latest_verdict_decision_id is None
        assert projection.latest_comment == "Нужна проверка."

    def test_a_finding_with_no_events_is_explicitly_pending(
        self, session: Session, published
    ) -> None:
        """``pending`` is explicit, never inferred from a missing row."""
        projection = current_verdict(session, published.finding_uid)
        assert projection is not None
        assert projection.current_verdict == "pending"
        assert projection.decision_event_count == 0
        assert projection.latest_decision_id is None


class TestTheProjectionIsRebuildable:
    def test_the_rebuild_from_the_ledger_equals_the_stored_projection(
        self, session: Session, published
    ) -> None:
        """The view is computed by PostgreSQL; the rebuild is a fold over the raw
        events in Python. They cannot agree by comparing a cache with itself."""
        for event_type, comment in (
            ("accept", None),
            ("comment", "Уточнить у смежников."),
            ("reject", None),
            ("comment", "Отклонено окончательно."),
            ("accept", "Пересмотрено."),
        ):
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type=event_type,
                comment=comment,
                author_label="reviewer-1",
            )

        stored = current_verdict(session, published.finding_uid)
        rebuilt = rebuild_current_verdict(session, published.finding_uid)
        assert stored is not None and rebuilt is not None
        assert rebuilt.comparable() == stored.comparable()
        assert stored.current_verdict == "accepted"
        assert stored.latest_comment == "Пересмотрено."
        assert stored.decision_event_count == 5

    def test_the_projection_is_a_view_and_not_a_table(self, session: Session) -> None:
        """"Rebuildable projection" is true by construction only while this holds."""
        kind = session.execute(
            text(
                "SELECT c.relkind FROM pg_class c JOIN pg_namespace n "
                "ON n.oid = c.relnamespace "
                "WHERE c.relname = 'finding_current_verdict' AND n.nspname = 'public'"
            )
        ).scalar_one()
        assert kind == "v", "finding_current_verdict must be a view, not a cached table"

    def test_two_findings_keep_separate_verdicts(
        self, session: Session, published
    ) -> None:
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        record_decision(
            session,
            finding_uid=published.second_finding_uid,
            finding_observation_id=published.second_finding_observation_id,
            event_type="reject",
            author_label="reviewer-1",
        )
        assert current_verdict(session, published.finding_uid).current_verdict == "accepted"
        assert (
            current_verdict(session, published.second_finding_uid).current_verdict == "rejected"
        )


class TestRevocation:
    """PD-01, proved at the ledger even though PC-01 produces no revocation.

    ``record_decision`` refuses ``revoke`` — the enum carries it so PD-01 stays
    implementable without a schema change, and PC-01 has no producer. The event is
    therefore appended here with raw SQL, which is exactly what a future producer would
    do, so the projection's behaviour is established now rather than discovered later.
    """

    def _revoke(self, session: Session, published) -> str:
        decision_id = DecisionId.new().value
        session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, author_label) "
                "VALUES (:d, :f, :o, 'revoke', 'pending', :label)"
            ),
            {
                "d": decision_id,
                "f": published.finding_uid,
                "o": published.finding_observation_id,
                "label": "planted-by-the-test",
            },
        )
        return decision_id

    def test_pc01_refuses_to_produce_a_revocation(
        self, session: Session, published
    ) -> None:
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="revoke",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert "revoke" in DECLARED_EVENT_TYPES
        assert "revoke" not in PC01_EVENT_TYPES

    def test_a_revocation_moves_the_projection_to_pending(
        self, session: Session, published
    ) -> None:
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        assert current_verdict(session, published.finding_uid).current_verdict == "accepted"

        revoked = self._revoke(session, published)
        projection = current_verdict(session, published.finding_uid)
        assert projection.current_verdict == "pending"
        assert projection.latest_verdict_decision_id == revoked

    def test_a_revocation_restores_no_earlier_verdict(
        self, session: Session, published
    ) -> None:
        """The heart of PD-01. Two verdicts precede the revocation; neither comes back."""
        first = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        second = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label="reviewer-1",
        )
        self._revoke(session, published)

        projection = current_verdict(session, published.finding_uid)
        assert projection.current_verdict == "pending"
        assert projection.latest_verdict_decision_id not in {
            first.decision_id,
            second.decision_id,
        }
        assert projection.decision_event_count == 3

        # Both superseded verdicts are still in the history, unrestored and unremoved.
        history = decision_history(session, published.finding_uid)
        assert [event.verdict for event in history] == ["accepted", "rejected", "pending"]

        # And the rebuild agrees: the fold never walks back past a revocation.
        rebuilt = rebuild_current_verdict(session, published.finding_uid)
        assert rebuilt.comparable() == projection.comparable()

    def test_a_verdict_after_a_revocation_needs_a_new_event(
        self, session: Session, published
    ) -> None:
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        self._revoke(session, published)
        assert current_verdict(session, published.finding_uid).current_verdict == "pending"

        reinstated = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        projection = current_verdict(session, published.finding_uid)
        assert projection.current_verdict == "accepted"
        assert projection.latest_verdict_decision_id == reinstated.decision_id


class TestTheLedgerRefusesRewriting:
    def test_update_is_refused_with_am002(self, session: Session, published) -> None:
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        with pytest.raises(DBAPIError) as caught:
            with nested_transaction(session):
                proxy = session.execute(
                    text(
                        "UPDATE expert_decision_event SET verdict = 'rejected' "
                        "WHERE decision_id = :d"
                    ),
                    {"d": event.decision_id},
                )
                assert proxy.rowcount == 1, (
                    "the statement matched no row, so no trigger could have refused it"
                )
        assert caught.value.orig.sqlstate == "AM002"

        assert (
            session.execute(
                text("SELECT verdict FROM expert_decision_event WHERE decision_id = :d"),
                {"d": event.decision_id},
            ).scalar_one()
            == "accepted"
        )

    def test_delete_is_refused_with_am002(self, session: Session, published) -> None:
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label="reviewer-1",
        )
        with pytest.raises(DBAPIError) as caught:
            with nested_transaction(session):
                proxy = session.execute(
                    text("DELETE FROM expert_decision_event WHERE decision_id = :d"),
                    {"d": event.decision_id},
                )
                assert proxy.rowcount == 1
        assert caught.value.orig.sqlstate == "AM002"
        assert current_verdict(session, published.finding_uid).decision_event_count == 1

    def test_an_accept_event_may_not_carry_a_rejected_verdict(
        self, session: Session, published
    ) -> None:
        """The event type and the verdict agree, or the row does not exist."""
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                        "finding_observation_id, event_type, verdict, author_label) "
                        "VALUES (:d, :f, :o, 'accept', 'rejected', 'local-reviewer')"
                    ),
                    {
                        "d": DecisionId.new().value,
                        "f": published.finding_uid,
                        "o": published.finding_observation_id,
                    },
                )

    def test_an_accept_event_may_not_carry_a_null_verdict(
        self, session: Session, published
    ) -> None:
        """A CHECK that evaluates to NULL is *satisfied* in PostgreSQL, so this is the
        case a naively written constraint lets through."""
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                        "finding_observation_id, event_type, verdict, author_label) "
                        "VALUES (:d, :f, :o, 'accept', NULL, 'local-reviewer')"
                    ),
                    {
                        "d": DecisionId.new().value,
                        "f": published.finding_uid,
                        "o": published.finding_observation_id,
                    },
                )


class TestWhatMayBeJudged:
    def test_a_decision_on_an_unknown_finding_is_not_found(
        self, session: Session, published
    ) -> None:
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=FindingUid.new().value,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.NOT_FOUND

    def test_an_ungrounded_observation_cannot_be_judged(
        self, session: Session, published
    ) -> None:
        """An ungrounded observation carries no ``finding_uid``, so there is nothing to
        judge — it is not merely hidden from the finding list.

        The run really does hold one: the fixture publishes an observation whose
        quotation is not in the document. Every way of aiming a decision at it fails.
        """
        rejected = published.ungrounded_observation_id
        assert (
            session.execute(
                text(
                    "SELECT finding_uid FROM finding_observation "
                    "WHERE finding_observation_id = :id"
                ),
                {"id": rejected},
            ).scalar_one()
            is None
        )

        # Paired with a real finding identity, the observation is not that finding's.
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=rejected,
                event_type="accept",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.NOT_FOUND

        # And no finding identity of its own exists to name.
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=FindingUid.new().value,
                finding_observation_id=rejected,
                event_type="accept",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.NOT_FOUND

        # Scoped to the observation under test, not to the table. A global count is only
        # zero while this suite owns the database alone, and it does not: the suites share
        # one instance, so running the battery in sequence made this assertion read rows
        # written by earlier suites and fail on work that was never its own. Scoping keeps
        # the property - nothing was appended *here* - and makes it order-independent.
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM expert_decision_event "
                    "WHERE finding_observation_id = :o"
                ),
                {"o": rejected},
            ).scalar_one()
            == 0
        ), "an event was appended for an ungrounded observation"

    def test_an_observation_that_is_not_the_findings_own_is_refused(
        self, session: Session, published
    ) -> None:
        """A decision references the observation the expert actually reviewed, so a
        mismatched pair is a caller fault rather than a row to write."""
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.second_finding_observation_id,
                event_type="accept",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.NOT_FOUND

    def test_a_comment_event_must_carry_a_comment(
        self, session: Session, published
    ) -> None:
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="comment",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_an_event_type_outside_the_journey_is_refused(
        self, session: Session, published
    ) -> None:
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="needs_manual_review",
                author_label="reviewer-1",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


class TestIdempotency:
    def test_replaying_one_command_appends_exactly_one_event(
        self, session: Session, published, command
    ) -> None:
        command_id = command("expert-accept-001")
        first = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label="reviewer-1",
        )
        second = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label="reviewer-1",
        )
        assert second.decision_id == first.decision_id
        assert current_verdict(session, published.finding_uid).decision_event_count == 1

    def test_the_unique_index_is_the_enforcement(
        self, session: Session, published, command
    ) -> None:
        """Not the handler's memory: a second event under one command_id is refused by
        the database even when the module is bypassed entirely."""
        from sqlalchemy.exc import IntegrityError

        command_id = command("expert-accept-002")
        record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label="reviewer-1",
        )
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                        "finding_observation_id, event_type, verdict, author_label, "
                        "command_id) VALUES (:d, :f, :o, 'reject', 'rejected', "
                        "'local-reviewer', :c)"
                    ),
                    {
                        "d": DecisionId.new().value,
                        "f": published.finding_uid,
                        "o": published.finding_observation_id,
                        "c": command_id,
                    },
                )

    def test_a_lost_race_returns_the_other_writers_event(
        self, session: Session, published, command, monkeypatch
    ) -> None:
        """The recovery branch, made reachable.

        In production the pre-check misses only when another writer appended between
        the check and the insert. That window cannot be opened from inside one
        transaction, so the pre-check is suppressed for one call — which is precisely
        what losing the race looks like from in here. Everything else is real: the real
        INSERT, the real unique index, the real violation, the real re-read.
        """
        from auditmanager.decisions import ledger as ledger_module

        command_id = command("expert-accept-004")
        first = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label="reviewer-1",
        )

        real = ledger_module._existing_event
        calls = {"n": 0}

        def blind_once(session_arg, key):
            calls["n"] += 1
            if calls["n"] == 1:
                return None  # the pre-check misses, as it does in a race
            return real(session_arg, key)

        monkeypatch.setattr(ledger_module, "_existing_event", blind_once)

        second = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            command_id=command_id,
            author_label="reviewer-1",
        )
        assert calls["n"] == 2, "the insert must have been attempted and refused"
        assert second.decision_id == first.decision_id
        assert second.event_type == "accept", "the other writer's event is the answer"
        assert current_verdict(session, published.finding_uid).decision_event_count == 1

    def test_two_different_commands_append_two_events(
        self, session: Session, published, command
    ) -> None:
        one = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command("expert-accept-003"),
            author_label="reviewer-1",
        )
        two = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            command_id=command("expert-reject-003"),
            author_label="reviewer-1",
        )
        assert one.decision_id != two.decision_id
        assert current_verdict(session, published.finding_uid).decision_event_count == 2


class TestAuthorLabel:
    """`D-78`. The author the caller names is the author the ledger keeps.

    **This class used to be vacuous and `W12-DEC` said so at the time.** It imported
    ``CONFIGURED_AUTHOR_LABEL`` and compared both sides of the assertion to it, so mutation
    ``M21`` -- the constant changed from ``"local-reviewer"`` to ``"someone-else"`` --
    moved the expectation along with the subject and reddened nothing. `W12-DEC` recorded
    that as deliberate: pinning the literal would have frozen what the module called a
    composition-root knob.

    It is no longer a knob. The label is the login of the reviewer the seam verified, so
    there is a real question to ask here and it is asked with **literals this file owns**:
    two different labels go in, the same two come back out of the database, and neither of
    them is read from the module under test.
    """

    def test_the_label_the_caller_gives_is_the_label_the_row_keeps(
        self, session: Session, published
    ) -> None:
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="anna.petrova",
        )
        assert event.author_label == "anna.petrova"
        stored = session.execute(
            text("SELECT author_label FROM expert_decision_event WHERE decision_id = :d"),
            {"d": event.decision_id},
        ).scalar_one()
        assert stored == "anna.petrova"

    def test_a_second_author_is_a_second_label(self, session: Session, published) -> None:
        """The control, and the whole of `D-78` at this level.

        One event proves a string survives a round trip. Two events by two authors prove the
        column carries *whose* judgement it was -- which is what `P04` reads it for, and what
        a single configured constant could never answer.
        """
        first = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="anna.petrova",
        )
        second = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label="boris.smirnov",
        )
        rows = session.execute(
            text(
                "SELECT decision_id, author_label FROM expert_decision_event "
                "WHERE finding_uid = :f ORDER BY sequence_no"
            ),
            {"f": published.finding_uid},
        ).all()
        assert [(row[0], row[1]) for row in rows] == [
            (first.decision_id, "anna.petrova"),
            (second.decision_id, "boris.smirnov"),
        ]

    def test_the_ledger_offers_no_default_author(self) -> None:
        """`D-66`'s shape, kept out by construction.

        A default is what a caller with no authenticated subject falls into, and a row
        attributed to a configuration constant reads like a decision somebody took.
        """
        import inspect

        parameter = inspect.signature(record_decision).parameters["author_label"]
        assert parameter.default is inspect.Parameter.empty, (
            f"record_decision defaults `author_label` to {parameter.default!r}; a decision "
            "with no named author must be a refusal, not an anonymous row."
        )

    def test_an_empty_label_is_refused(self, session: Session, published) -> None:
        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                author_label="   ",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


class TestOrdering:
    def test_events_inside_one_transaction_are_distinguishable(
        self, session: Session, published
    ) -> None:
        """``recorded_at`` is ``clock_timestamp()``, not ``now()``: with ``now()`` every
        event in one transaction would share a timestamp and the client-visible order
        would be undefined."""
        events = [
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="comment",
                comment=f"Замечание {index}.",
                author_label="reviewer-1",
            )
            for index in range(3)
        ]
        recorded = [event.recorded_at for event in events]
        assert len(set(recorded)) == len(recorded), (
            "all three events share a timestamp; ordering inside one transaction is "
            "then undefined"
        )
        assert recorded == sorted(recorded)

    def test_the_server_sequence_is_never_returned(
        self, session: Session, published
    ) -> None:
        """The contract lists a database sequence value exposed to a client among the
        non-identities, so it is not on the event this module returns."""
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label="reviewer-1",
        )
        assert not hasattr(event, "sequence_no")
        projection = current_verdict(session, published.finding_uid)
        assert not hasattr(projection, "sequence_no")
