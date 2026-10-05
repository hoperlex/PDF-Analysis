"""`W49-DECISIONS-01`: every new decision event names the account that took it.

``expert_decision_event.author_user_uid`` (migration ``0015``) is the identity beside the
display label. These tests hold four claims:

* **written on every new event** -- each event type, through both write paths, stores the
  ``user_uid`` it was given. The stored value is read back with raw SQL, past the module,
  so a read path that invented the value could not make the write look right;
* **history is listed, never refused** -- a row written the way every pre-``0015`` event was
  (no account) appears in the history and in the journal with ``author_user_uid`` ``None``,
  beside a row that has one;
* **nothing is coerced** -- a malformed or unknown identity is a refused append, not a NULL;
* **the account is part of the idempotency payload** -- one key, one label, two accounts is
  a reused key; and with no account the fingerprint is the pre-``0015`` one.

Literals are written out. Nothing here builds its expectation from the module under test.
"""

from __future__ import annotations

import dataclasses
import inspect
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.decisions import (
    DecisionEvent,
    JournalEntry,
    append_decision_under_key,
    current_verdict,
    decision_history,
    decision_journal,
    record_decision,
)
from auditmanager.ingest.public import payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId

#: The one display name both accounts below carry. A label identifies nobody; that is the
#: premise of the column, so the suite makes two accounts indistinguishable by it.
SHARED_LABEL = "Петрова А. С."

#: A well-formed ``usr_<ULID>`` that no ``app_user`` row carries.
UNKNOWN_ACCOUNT = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _key() -> str:
    return f"w49dec-{uuid.uuid4().hex[:20]}"


def _account(session: Session) -> str:
    """A real ``app_user`` row, so the foreign key is satisfied by an account and not by
    a value that merely looks like one. Rolled back with the test's unit of work."""
    login = f"w49dec-{uuid.uuid4().hex[:12]}@example.com"
    record = UserRepository().create_user(
        session, login, f"w49dec-passphrase-{uuid.uuid4().hex}"
    )
    return str(record.user_uid)


def _stored_account(session: Session, decision_id: str) -> object:
    """The column as the database holds it -- not as any read path of the module says."""
    return session.execute(
        text("SELECT author_user_uid FROM expert_decision_event WHERE decision_id = :d"),
        {"d": decision_id},
    ).scalar_one()


def _event_count(session: Session, finding_uid: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"),
            {"f": finding_uid},
        ).scalar_one()
    )


def _comment_for(event_type: str) -> str | None:
    return "Проверено по разделу АР." if event_type == "comment" else None


# =======================================================================================
# Written on every new event.
# =======================================================================================


class TestEveryNewEventPersistsItsAuthorAccount:
    @pytest.mark.parametrize("event_type", ["accept", "reject", "comment"])
    def test_record_decision_writes_the_account(
        self, session: Session, published, event_type: str
    ) -> None:
        author = _account(session)
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type=event_type,
            comment=_comment_for(event_type),
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )

        assert _stored_account(session, event.decision_id) == author
        assert event.author_user_uid == author
        assert event.author_label == SHARED_LABEL

    @pytest.mark.parametrize("event_type", ["accept", "reject", "comment"])
    def test_the_keyed_append_writes_the_account(
        self, session: Session, published, event_type: str
    ) -> None:
        author = _account(session)
        event, replayed = append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type=event_type,
            idempotency_key=_key(),
            comment=_comment_for(event_type),
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )

        assert replayed is False
        assert _stored_account(session, event.decision_id) == author
        assert event.author_user_uid == author

    def test_both_read_paths_report_the_stored_account(
        self, session: Session, published
    ) -> None:
        """The history and the journal each read the column, not the write's echo."""
        author = _account(session)
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )

        (listed,) = decision_history(session, published.finding_uid)
        assert listed.decision_id == event.decision_id
        assert listed.author_user_uid == author

        journal = {e.decision_id: e for e in decision_journal(session)}
        assert journal[event.decision_id].author_user_uid == author

    def test_two_accounts_with_one_label_stay_two_authors(
        self, session: Session, published
    ) -> None:
        """The reason the column exists: the label cannot tell these two apart."""
        first, second = _account(session), _account(session)
        for author in (first, second):
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="comment",
                comment="Замечание.",
                author_label=SHARED_LABEL,
                author_user_uid=author,
            )

        history = decision_history(session, published.finding_uid)
        assert [e.author_label for e in history] == [SHARED_LABEL, SHARED_LABEL]
        assert [e.author_user_uid for e in history] == [first, second]


# =======================================================================================
# History is listed, never refused.
# =======================================================================================


class TestAHistoryRowReadsAsAuthorAccountUnknown:
    def _history_row(self, session: Session, published) -> str:
        """An event inserted the way every pre-``0015`` writer inserted one: the
        statement does not name ``author_user_uid`` at all."""
        decision_id = DecisionId.new().value
        session.execute(
            text(
                "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                "finding_observation_id, event_type, verdict, comment, author_label) "
                "VALUES (:d, :f, :o, 'accept', 'accepted', NULL, 'local-reviewer')"
            ),
            {
                "d": decision_id,
                "f": published.finding_uid,
                "o": published.finding_observation_id,
            },
        )
        return decision_id

    def test_the_history_lists_it_beside_a_row_that_has_an_account(
        self, session: Session, published
    ) -> None:
        historical = self._history_row(session, published)
        author = _account(session)
        recent = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )

        assert _stored_account(session, historical) is None
        history = decision_history(session, published.finding_uid)
        assert [(e.decision_id, e.author_user_uid) for e in history] == [
            (historical, None),
            (recent.decision_id, author),
        ]
        assert history[0].author_label == "local-reviewer"

        # The projection folds the history row like any other event.
        projection = current_verdict(session, published.finding_uid)
        assert projection is not None
        assert projection.current_verdict == "rejected"
        assert projection.decision_event_count == 2

    def test_the_journal_lists_it(self, session: Session, published) -> None:
        historical = self._history_row(session, published)

        listed = [e for e in decision_journal(session) if e.decision_id == historical]
        assert len(listed) == 1, "the journal dropped an event whose account is unknown"
        assert listed[0].author_user_uid is None
        assert listed[0].author_label == "local-reviewer"

        # And under the filters, which join the projection -- still listed.
        narrowed = decision_journal(
            session, category="internal_contradiction", verdict="accepted"
        )
        assert historical in {e.decision_id for e in narrowed}

    def test_the_command_replay_lists_it(
        self, session: Session, published, command
    ) -> None:
        """The third read of the event, ``record_decision``'s replay by ``command_id``."""
        command_id = command(_key())
        first = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label=SHARED_LABEL,
            author_user_uid=None,
        )
        replayed = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
            author_label=SHARED_LABEL,
            author_user_uid=None,
        )
        assert replayed.decision_id == first.decision_id
        assert replayed.author_user_uid is None

    def test_no_account_given_writes_null_and_invents_nothing(
        self, session: Session, published
    ) -> None:
        """The transitional path (`W49-SEAL-01` has not wired the subject yet) stores the
        same NULL a history row holds -- not a configured account, not the label."""
        event = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            author_label=SHARED_LABEL,
            author_user_uid=None,
        )
        assert _stored_account(session, event.decision_id) is None
        assert event.author_user_uid is None


# =======================================================================================
# Nothing is coerced.
# =======================================================================================


class TestAnIdentityIsWrittenAsGivenOrRefused:
    @pytest.mark.parametrize(
        "author",
        ["", " ", "Admin", "usr_not-a-ulid", "Петрова А. С."],
        ids=["empty", "blank", "a-login", "malformed", "a-label"],
    )
    def test_a_malformed_identity_is_refused_not_nulled(
        self, session: Session, published, author: str
    ) -> None:
        with pytest.raises(DomainError):
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                author_label=SHARED_LABEL,
                author_user_uid=author,
            )
        assert _event_count(session, published.finding_uid) == 0

    def test_an_unknown_account_is_refused(self, session: Session, published) -> None:
        with pytest.raises(DomainError):
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                author_label=SHARED_LABEL,
                author_user_uid=UNKNOWN_ACCOUNT,
            )
        assert _event_count(session, published.finding_uid) == 0


# =======================================================================================
# The account is part of the idempotency payload.
# =======================================================================================


class TestTheAccountIsPartOfTheKeyedPayload:
    def test_one_key_two_accounts_one_label_is_a_reused_key(
        self, session: Session, published
    ) -> None:
        first, second = _account(session), _account(session)
        key = _key()
        append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            idempotency_key=key,
            author_label=SHARED_LABEL,
            author_user_uid=first,
        )
        with pytest.raises(DomainError) as caught:
            append_decision_under_key(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                idempotency_key=key,
                author_label=SHARED_LABEL,
                author_user_uid=second,
            )
        assert caught.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
        (only,) = decision_history(session, published.finding_uid)
        assert only.author_user_uid == first

    def test_one_key_one_account_replays_with_its_account(
        self, session: Session, published
    ) -> None:
        author = _account(session)
        key = _key()
        first, _ = append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            idempotency_key=key,
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )
        again, replayed = append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            idempotency_key=key,
            author_label=SHARED_LABEL,
            author_user_uid=author,
        )
        assert replayed is True
        assert again.decision_id == first.decision_id
        assert again.author_user_uid == author
        assert _event_count(session, published.finding_uid) == 1

    def test_without_an_account_the_fingerprint_is_the_pre_0015_one(
        self, session: Session, published
    ) -> None:
        """A key claimed before the column existed must still replay, so with no account
        the payload is exactly the six keys it always was. Written out, not imported."""
        key = _key()
        event, _ = append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            idempotency_key=key,
            author_label=SHARED_LABEL,
            author_user_uid=None,
        )
        stored = session.execute(
            text("SELECT payload_fingerprint FROM command_record WHERE command_id = :c"),
            {"c": event.command_id},
        ).scalar_one()
        pre_0015 = payload_fingerprint(
            {
                "command": "append_decision.v1",
                "finding_uid": published.finding_uid,
                "finding_observation_id": published.finding_observation_id,
                "event_type": "accept",
                "comment": None,
                "author_label": SHARED_LABEL,
            }
        )
        assert stored == str(pre_0015)


# =======================================================================================
# The shape the integration contract names.
# =======================================================================================


class TestTheSignatureTakesTheAccount:
    @pytest.mark.parametrize("function", [record_decision, append_decision_under_key])
    def test_the_account_is_keyword_only_and_defaults_to_no_constant(
        self, function
    ) -> None:
        """`W49-SEAL-01` passes ``Subject.user_uid`` by name. Until it does, the only
        admissible default is ``None`` -- "author account unknown". A configured account
        would be `D-66`'s shape again: a row attributed to whatever the default said."""
        parameter = inspect.signature(function).parameters["author_user_uid"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is None or parameter.default is inspect.Parameter.empty, (
            f"{function.__name__} defaults `author_user_uid` to {parameter.default!r}"
        )

    @pytest.mark.parametrize("shape", [DecisionEvent, JournalEntry])
    def test_the_read_models_carry_the_account_without_a_default(self, shape) -> None:
        """Every construction states what it read; a default would let one forget."""
        (field,) = [f for f in dataclasses.fields(shape) if f.name == "author_user_uid"]
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
