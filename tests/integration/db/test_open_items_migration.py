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


class TestTheBlobIndexNoLongerClaimsWhatItCannotDo:
    def test_the_partial_index_is_gone(self, migrated_engine: Engine) -> None:
        """Its comment promised a rejected blob would not block a later upload.

        It could not: blob_id is derived from (sha256, size) and is the PRIMARY KEY, so
        content uniqueness already holds in every state. Scoping a second index to
        `available` bought nothing and described behaviour nobody had.
        """
        with Session(migrated_engine) as session:
            present = session.execute(
                text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE indexname = 'uq_blob_available_content'"
                )
            ).scalar_one()
        assert present == 0

    def test_content_uniqueness_still_holds_through_the_primary_key(
        self, migrated_engine: Engine
    ) -> None:
        """Dropping the index must not weaken the invariant it was shadowing."""
        blob_id = f"blob_{uuid.uuid4().hex[:26].upper()}"
        with Session(migrated_engine) as session:
            session.execute(
                text(
                    "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
                    "VALUES (:b, 'temporary', :s, 1, 'application/pdf')"
                ),
                {"b": blob_id, "s": "a" * 64},
            )
            session.flush()
            with pytest.raises(DBAPIError):
                session.execute(
                    text(
                        "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
                        "VALUES (:b, 'temporary', :s, 1, 'application/pdf')"
                    ),
                    {"b": blob_id, "s": "a" * 64},
                )
                session.flush()
            session.rollback()


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
