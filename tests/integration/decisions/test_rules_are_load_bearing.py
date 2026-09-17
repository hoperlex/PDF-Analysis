"""Rules in the decision ledger that the existing suite does not hold down.

Every test here was written because a mutation of the rule it names left
`tests/integration/decisions` entirely green. The mutations are recorded in
`docs/program/reviews/W12-DEC.md`; each test below says which one it reddens.

Two shapes recur and are worth naming, because both are how a deleted check survives a
sweep:

* **Two rules, one error code.** ``record_decision`` raises ``VALIDATION_FAILED`` from
  four places and ``NOT_FOUND`` from two. A test that asserts only the code passes
  whichever of them fired, so deleting the first of a pair is invisible: the second
  refuses the same input with the same code. The tests here remove the second rule's
  reach — by widening the vocabulary it consults, or by aiming past it — so that only
  the rule under test can produce the refusal.
* **One comparison, one shared accessor.** The projection is proved rebuildable by
  ``rebuilt.comparable() == stored.comparable()``. Both sides call the same method, so
  narrowing it narrows the claim on both sides at once and the assertion stays true.

Nothing here imports the value it pins. The literals below are written out.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.decisions import (
    DECLARED_EVENT_TYPES,
    PC01_EVENT_TYPES,
    CurrentVerdict,
    append_decision_under_key,
    current_verdict,
    rebuild_current_verdict,
    record_decision,
)
from auditmanager.decisions import ledger as ledger_module
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DecisionId, FindingUid


def _key() -> str:
    return f"w12dec-{uuid.uuid4().hex[:20]}"


# ---------------------------------------------------------------------------
# The vocabulary, pinned as literals rather than imported into its own expectation
# ---------------------------------------------------------------------------


class TestTheVocabularyIsWhatItSays:
    def test_the_two_event_vocabularies_are_exactly_these_values(self) -> None:
        """Written out, not derived. A test that builds its expectation from the
        constant moves with it and pins nothing."""
        assert set(PC01_EVENT_TYPES) == {"accept", "reject", "comment"}
        assert set(DECLARED_EVENT_TYPES) == {"accept", "reject", "comment", "revoke"}
        # The one event type the schema declares and PC-01 does not produce.
        assert set(DECLARED_EVENT_TYPES) - set(PC01_EVENT_TYPES) == {"revoke"}


class TestRevokeIsRefusedByItsOwnRule:
    """`record_decision` refuses ``revoke`` twice over.

    The first refusal is the deliberate one the module docstring argues for: "PC-01
    emits no revocation event and the UI offers none, so accepting one here would create
    a producer the programme has not decided to have. The refusal names that, rather
    than failing on a constraint the caller cannot read."

    The second is incidental: ``revoke`` is simply not in ``PC01_EVENT_TYPES``.

    Both raise ``VALIDATION_FAILED``, so
    ``test_pc01_refuses_to_produce_a_revocation`` — which asserts only the code — passes
    with the deliberate rule deleted. Measured: deleting it leaves all 32 tests of this
    suite and all 1492 of the canonical battery green.

    This test takes the incidental refusal away, so only the deliberate one is left to
    fire.
    """

    def test_revoke_is_refused_even_when_the_vocabulary_would_admit_it(
        self, session: Session, published, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Widening the vocabulary is what removes the *second* rule's reach. It is not
        # a claim that the vocabulary should contain `revoke`; the test above pins that
        # it does not.
        monkeypatch.setattr(
            ledger_module,
            "PC01_EVENT_TYPES",
            frozenset({"accept", "reject", "comment", "revoke"}),
        )
        # The patch must actually widen it, or this test proves nothing.
        assert "revoke" in ledger_module.PC01_EVENT_TYPES

        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="revoke",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

        # And nothing was appended. Scoped to this finding, because the suites share one
        # database instance and a table-wide count would read other suites' rows.
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM expert_decision_event "
                    "WHERE finding_uid = :f AND event_type = 'revoke'"
                ),
                {"f": published.finding_uid},
            ).scalar_one()
            == 0
        ), "a revocation was appended by a producer PC-01 has not decided to have"


class TestAnUnknownFindingIsRefusedByTheFindingRule:
    """``record_decision`` checks two things and refuses both with ``NOT_FOUND``:
    that the finding exists, and that the observation carries that finding's identity.

    The second subsumes the first for every input a test can supply, because an
    observation cannot belong to a finding that does not exist. So deleting the
    ``finding_exists`` check is invisible: measured, all 32 tests of this suite stay
    green without it.

    Aiming past the second check is the only way to leave the first one alone in the
    field, so the collaborator the second check calls is suppressed for one call. The
    insert that follows is real, and so is the foreign key it would violate.
    """

    def test_a_missing_finding_is_refused_before_any_row_is_attempted(
        self, session: Session, published, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ledger_module, "observation_belongs_to_finding", lambda *a, **k: True
        )
        absent = FindingUid.new().value
        assert (
            session.execute(
                text("SELECT count(*) FROM finding WHERE finding_uid = :f"),
                {"f": absent},
            ).scalar_one()
            == 0
        ), "the suite's own fixture handed out a finding_uid that exists"

        with pytest.raises(DomainError) as caught:
            record_decision(
                session,
                finding_uid=absent,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
            )
        # NOT_FOUND, and specifically not CONFLICT: with the rule gone the INSERT is
        # attempted and the foreign key refuses it, which this module reports as
        # CONFLICT. The distinction is the whole content of this test.
        assert caught.value.code is ErrorCode.NOT_FOUND


# ---------------------------------------------------------------------------
# The projection: what "the rebuild equals the view" actually compares
# ---------------------------------------------------------------------------


class TestTheRebuildComparisonIsWideEnoughToMeanSomething:
    #: Every field ``comparable()`` must carry, written out. ``decision_recorded_at`` is
    #: deliberately excluded — only the database can produce it — and that exclusion is
    #: asserted below rather than left implied.
    COMPARED_FIELDS = (
        "finding_uid",
        "current_verdict",
        "latest_verdict_decision_id",
        "latest_comment",
        "latest_comment_decision_id",
        "latest_decision_id",
        "decision_event_count",
    )
    EXCLUDED_FIELDS = ("decision_recorded_at",)

    def test_comparable_carries_every_field_the_projection_declares(self) -> None:
        """Both sides of ``rebuilt.comparable() == stored.comparable()`` call this one
        method, so a field it stops carrying stops being compared on both sides at once
        and the assertion goes on holding. Measured: narrowing ``comparable()`` to
        ``(self.finding_uid,)`` leaves all 32 tests of this suite green.

        The sentinels are distinct per field, so a tuple that carried the same field
        twice, or carried them out of order, is a different tuple.
        """
        probe = CurrentVerdict(
            finding_uid="fnd_00000000000000000000000001",
            current_verdict="accepted",
            latest_verdict_decision_id="dec_00000000000000000000000002",
            latest_comment="the comment",
            latest_comment_decision_id="dec_00000000000000000000000003",
            latest_decision_id="dec_00000000000000000000000004",
            decision_recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            decision_event_count=7,
        )
        assert probe.comparable() == (
            "fnd_00000000000000000000000001",
            "accepted",
            "dec_00000000000000000000000002",
            "the comment",
            "dec_00000000000000000000000003",
            "dec_00000000000000000000000004",
            7,
        )
        # And the exclusion is intentional, not an omission: the timestamp is absent.
        assert probe.decision_recorded_at not in probe.comparable()

    def test_the_projection_declares_exactly_the_fields_the_comparison_covers(
        self,
    ) -> None:
        """A field added to the projection and not to ``comparable()`` would be
        unchecked by the rebuild for ever, silently. This is the drift guard the
        literal tuple above cannot give on its own."""
        declared = tuple(f.name for f in dataclasses.fields(CurrentVerdict))
        assert set(declared) == set(self.COMPARED_FIELDS) | set(self.EXCLUDED_FIELDS), (
            "CurrentVerdict gained or lost a field. Decide whether the rebuild should "
            "compare it, then update COMPARED_FIELDS or EXCLUDED_FIELDS here."
        )


class TestCriterionSixOrdering:
    """Criterion 6: one finding accepted, one rejected, and a comment appended *later*
    and visible.

    Both existing rebuild-versus-view comparisons run a stream that **ends on a
    verdict-bearing event** — `accept, comment, reject, comment, accept` in one, and
    `accept, reject, revoke` in the other. So "``latest_decision_id`` and
    ``decision_recorded_at`` describe the most recent event of *any* type" is never put
    to the fold: measured, restricting the fold to move them only on verdict-bearing
    events leaves all 32 tests of this suite green.

    This is the stream criterion 6 actually describes, and it ends on the comment.
    """

    def test_a_comment_appended_last_is_visible_in_both_the_view_and_the_rebuild(
        self, session: Session, published
    ) -> None:
        accepted = record_decision(
            session,
            finding_uid=published.second_finding_uid,
            finding_observation_id=published.second_finding_observation_id,
            event_type="accept",
        )
        rejected = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="reject",
        )
        commented = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="comment",
            comment="Замечание после отклонения.",
        )

        stored = current_verdict(session, published.finding_uid)
        rebuilt = rebuild_current_verdict(session, published.finding_uid)
        assert stored is not None and rebuilt is not None

        # The view, pinned to literals rather than to the other side of the comparison.
        assert stored.current_verdict == "rejected", "a comment is not a judgement"
        assert stored.latest_verdict_decision_id == rejected.decision_id
        assert stored.latest_decision_id == commented.decision_id
        assert stored.latest_comment == "Замечание после отклонения."
        assert stored.latest_comment_decision_id == commented.decision_id
        assert stored.decision_event_count == 2

        # The fold agrees on all of it, with the stream ending on a non-verdict event.
        assert rebuilt.comparable() == stored.comparable()
        assert rebuilt.latest_decision_id == commented.decision_id, (
            "the fold stopped at the last verdict-bearing event; latest_decision_id "
            "describes the most recent event of any type"
        )

        # The other finding is untouched and accepted: criterion 6 wants both.
        other = current_verdict(session, published.second_finding_uid)
        assert other is not None
        assert other.current_verdict == "accepted"
        assert other.latest_decision_id == accepted.decision_id
        assert other.decision_event_count == 1


# ---------------------------------------------------------------------------
# The keyed append: the two stale arms
# ---------------------------------------------------------------------------


class TestAStaleCommandRecordIsRefused:
    """``append_decision_under_key`` has two arms that both raise
    ``IDEMPOTENCY_KEY_STALE``, and neither was reached by any test: measured, deleting
    either one leaves all 32 tests of this suite green.

    Both describe the same situation from two sides — a ``command_record`` that reached
    ``succeeded`` but whose outcome does not lead to an event. That is not reachable by
    running this code, which is the point: it is what a database written by an earlier
    version, or by a command that was recorded and then lost its event, looks like now.
    ``IDEMPOTENCY_KEY_STALE`` is the code the catalog has for exactly that.

    The two scenarios are built so that each reddens under its own rule only:

    * an outcome with no ``decision_id``, **and an event that does exist** — with the
      first arm gone the second finds the event and returns it, so nothing raises;
    * an outcome naming a ``decision_id``, **and no event at all** — the first arm is
      satisfied by the string and only the second can fire.

    Neither the fingerprint nor the payload shape is written out here. The fingerprint
    is read back off a real claim the module itself made, so this suite does not carry a
    second copy of what ``append_decision_under_key`` hashes.
    """

    COMMAND_TYPE = "append_decision"

    def _real_claim_fingerprint(self, session: Session, published) -> str:
        """Make one honest keyed append and read back the fingerprint it computed."""
        event, replayed = append_decision_under_key(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            idempotency_key=_key(),
        )
        assert replayed is False
        fingerprint = session.execute(
            text("SELECT payload_fingerprint FROM command_record WHERE command_id = :c"),
            {"c": event.command_id},
        ).scalar_one()
        return str(fingerprint)

    def _plant_claimed_command(self, session: Session, *, key: str, fingerprint: str):
        """A ``command_record`` claimed under ``key``, still ``in_progress``.

        Inserted at the machine's initial state and moved to ``succeeded`` by the
        product's own repository, so the state guard and the frozen-column guard both
        see what they would in production. Returns ``(command_id, repository, typed_id)``.
        """
        from auditmanager.ingest import CommandRepository
        from auditmanager.shared.identity import CommandId

        command_id = CommandId.new()
        session.execute(
            text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, "
                "payload_fingerprint, state) VALUES (:c, :t, :k, :f, 'in_progress')"
            ),
            {
                "c": str(command_id),
                "t": self.COMMAND_TYPE,
                "k": key,
                "f": fingerprint,
            },
        )
        return str(command_id), CommandRepository, command_id

    def test_an_outcome_with_no_decision_id_is_stale_even_when_the_event_exists(
        self, session: Session, published
    ) -> None:
        fingerprint = self._real_claim_fingerprint(session, published)
        key = _key()
        command_id, repository, typed_id = self._plant_claimed_command(
            session, key=key, fingerprint=fingerprint
        )

        # The event really is there under this command_id, so the *other* arm cannot
        # fire. This is what makes the refusal below attributable to one rule.
        planted = record_decision(
            session,
            finding_uid=published.finding_uid,
            finding_observation_id=published.finding_observation_id,
            event_type="accept",
            command_id=command_id,
        )
        repository().succeed(
            session, command_id=typed_id, outcome={"appended": True}
        )
        assert (
            session.execute(
                text("SELECT count(*) FROM expert_decision_event WHERE command_id = :c"),
                {"c": command_id},
            ).scalar_one()
            == 1
        ), "the setup did not plant the event the other arm would have found"

        with pytest.raises(DomainError) as caught:
            append_decision_under_key(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                idempotency_key=key,
            )
        assert caught.value.code is ErrorCode.IDEMPOTENCY_KEY_STALE
        # Not IDEMPOTENCY_KEY_REUSE: the payload really is the same one, so the refusal
        # is about the recorded outcome and not about the fingerprint.
        assert planted.decision_id is not None

    def test_an_outcome_naming_a_decision_the_ledger_does_not_hold_is_stale(
        self, session: Session, published
    ) -> None:
        fingerprint = self._real_claim_fingerprint(session, published)
        key = _key()
        command_id, repository, typed_id = self._plant_claimed_command(
            session, key=key, fingerprint=fingerprint
        )

        orphan = DecisionId.new().value
        repository().succeed(session, command_id=typed_id, outcome={"decision_id": orphan})
        assert (
            session.execute(
                text("SELECT count(*) FROM expert_decision_event WHERE decision_id = :d"),
                {"d": orphan},
            ).scalar_one()
            == 0
        ), "the setup accidentally created the event it meant to leave missing"

        with pytest.raises(DomainError) as caught:
            append_decision_under_key(
                session,
                finding_uid=published.finding_uid,
                finding_observation_id=published.finding_observation_id,
                event_type="accept",
                idempotency_key=key,
            )
        assert caught.value.code is ErrorCode.IDEMPOTENCY_KEY_STALE


class TestTheVerdictMapAgreesWithTheSchema:
    """``VERDICT_FOR_EVENT`` declares the verdict each event type carries, and the
    database declares the same thing in ``ck_expert_decision_event_type_verdict_agree``.
    Two declarations that must agree, with nothing making them.

    The ``revoke`` entry is the one nothing reads: ``record_decision`` refuses ``revoke``
    before it ever indexes the map, so measured, changing that entry from ``pending`` to
    ``rejected`` leaves all 32 tests of the original suite green — and it is exactly the
    entry a future PD-01 producer would rely on.

    The inputs here are taken from the map on purpose: the claim *is* that what the map
    says is what the table accepts. The expectation comes from PostgreSQL, not from the
    map, so the two cannot move together. The map itself is pinned as a literal below.
    """

    #: Written out, not imported into its own expectation.
    EXPECTED_MAP = {
        "accept": "accepted",
        "reject": "rejected",
        "comment": None,
        "revoke": "pending",
    }

    def test_the_map_is_exactly_this(self) -> None:
        from auditmanager.decisions import VERDICT_FOR_EVENT

        assert dict(VERDICT_FOR_EVENT) == self.EXPECTED_MAP

    def test_every_declared_event_type_is_storable_with_the_verdict_the_map_gives_it(
        self, session: Session, published, subtests
    ) -> None:
        from auditmanager.decisions import VERDICT_FOR_EVENT
        from auditmanager.shared.db import nested_transaction

        assert set(VERDICT_FOR_EVENT) == set(DECLARED_EVENT_TYPES), (
            "the map and the declared vocabulary have drifted apart"
        )

        for event_type in sorted(DECLARED_EVENT_TYPES):
            with subtests.test(event_type=event_type):
                verdict = VERDICT_FOR_EVENT[event_type]
                decision_id = DecisionId.new().value
                # A comment column is required for `comment` and harmless elsewhere;
                # the constraint under test is the type/verdict agreement.
                with nested_transaction(session):
                    session.execute(
                        text(
                            "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                            "finding_observation_id, event_type, verdict, comment, "
                            "author_label) VALUES (:d, :f, :o, :t, :v, :c, 'local-reviewer')"
                        ),
                        {
                            "d": decision_id,
                            "f": published.finding_uid,
                            "o": published.finding_observation_id,
                            "t": event_type,
                            "v": verdict,
                            "c": "Замечание." if event_type == "comment" else None,
                        },
                    )
                stored = session.execute(
                    text(
                        "SELECT verdict FROM expert_decision_event WHERE decision_id = :d"
                    ),
                    {"d": decision_id},
                ).scalar_one()
                assert stored == verdict, (
                    f"the table stored a different verdict for {event_type!r} than the "
                    f"map declares"
                )
