"""The three owner-ruled corrections of migration ``0003_open_items``.

Each closes an item a session reported and could not fix from inside its own tree, and each
is asserted against the live schema rather than against the migration source - a migration
that was written is not a migration that ran.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy import Engine
from sqlalchemy.orm import Session


def _constraint(session: Session, name: str) -> str | None:
    return session.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    ).scalar()


class TestTheBlobIndexSaysWhatItDoes:
    """The correction here is to a comment, not to an invariant.

    B1 was right that the old comment could not be true: blob_id is derived from
    (sha256, size) and is the primary key, so a rejected blob bans those bytes whatever the
    index is scoped to. The integrator's first attempt therefore dropped the index - and two
    existing tests caught it, because the **database** does not know blob_id is derived. The
    storage adapter guarantees that; the schema does not. Without the partial index, two
    available rows with different blob_ids and identical content insert cleanly.

    So the index is the only content-uniqueness guarantee the database itself holds, and
    removing it would have deleted a real invariant to fix a false sentence.
    """

    def test_the_index_is_still_there(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session:
            present = session.execute(
                text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE indexname = 'uq_blob_available_content'"
                )
            ).scalar_one()
        assert present == 1, "the database's only content-uniqueness guarantee is gone"

    def test_its_comment_no_longer_promises_a_rejected_blob_can_return(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            comment = session.execute(
                text("SELECT obj_description('uq_blob_available_content'::regclass, 'pg_class')")
            ).scalar()
        assert comment is not None, "the index carries no comment at all"
        assert "does NOT let a rejected blob be re-uploaded" in comment
        assert "must not block a later good upload" not in comment


class TestTheProvenanceVocabularyFits:
    def test_truncated_is_admitted(self, migrated_engine: Engine) -> None:
        """`analysis.text.provenance` emits it; the CHECK used to refuse it.

        B5 mapped `truncated` to `succeeded` and kept the stop reason elsewhere, because the
        row would not otherwise insert. That is a lossy map made under duress.
        """
        with Session(migrated_engine) as session:
            definition = _constraint(session, "ck_model_call_status")
        assert definition is not None
        assert "truncated" in definition


class TestTheUngroundedVocabularyIsEnforced:
    def test_the_five_declared_reasons_are_the_only_ones(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            definition = _constraint(session, "ck_finding_observation_ungrounded_reason")
        assert definition is not None
        for reason in (
            "quotation_absent",
            "quotation_on_different_page",
            "span_outside_page",
            "span_outside_block",
            "span_length_mismatch",
        ):
            assert reason in definition, f"{reason} is not enforced by the constraint"

    def test_an_invented_reason_is_refused(self, migrated_engine: Engine) -> None:
        """The column was plain nullable text, so the database accepted anything.

        Nothing writes it today - the analysis stage drops unresolvable anchors before the
        gate can see one, and the owner accepted that. The constraint is here so the
        declared vocabulary cannot drift the moment a producer appears.
        """
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO finding_observation "
                    "(finding_observation_id, run_id, grounded, ungrounded_reason) "
                    "VALUES (:o, :r, false, 'looked_wrong')"
                ),
                {
                    "o": f"fobs_{uuid.uuid4().hex[:26].upper()}",
                    "r": f"run_{uuid.uuid4().hex[:26].upper()}",
                },
            )
            session.flush()


class TestTheCostBasisIsRecordedRatherThanDerived:
    """`model_call.cost_micros` held a measurement or a derivation with nothing saying which.

    Tolerable while a rate table was the only source; not tolerable once `OD-02` was revised
    to a proxy that reports what a call actually cost, because the same column now carries a
    measurement for a proxied run and a derivation for a replay. A report presenting the two
    identically is one nobody can cite - which `P4-OPS-01` hit directly, having to derive the
    basis rather than read it.
    """

    def test_the_column_exists_and_is_constrained_to_the_two_values(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as session:
            definition = _constraint(session, "ck_model_call_cost_basis")
        assert definition is not None, "cost_basis carries no constraint"
        assert "measured" in definition and "estimated" in definition

    def test_an_invented_basis_is_refused(self, migrated_engine: Engine) -> None:
        with Session(migrated_engine) as session, pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO model_call "
                    "(model_call_id, run_id, stage_id, provider, model_identity, "
                    " provider_mode, cost_basis, status) "
                    "VALUES (:m, :r, 'text_analysis', 'p', 'm', 'recorded', 'guessed', "
                    " 'succeeded')"
                ),
                {
                    "m": f"mc_{uuid.uuid4().hex[:26].upper()}",
                    "r": f"run_{uuid.uuid4().hex[:26].upper()}",
                },
            )
            session.flush()
        session.rollback()

    def test_the_default_is_the_honest_one(self, migrated_engine: Engine) -> None:
        """Every row written before the column existed was derived.

        Defaulting to `measured` would have invented provenance for calls nobody measured,
        which is worse than the gap it closed.
        """
        with Session(migrated_engine) as session:
            default = session.execute(
                text(
                    "SELECT column_default FROM information_schema.columns "
                    "WHERE table_name = 'model_call' AND column_name = 'cost_basis'"
                )
            ).scalar_one()
        assert "estimated" in str(default)
