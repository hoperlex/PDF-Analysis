"""Does anything notice a value leaving the five-reason vocabulary?

``UNGROUNDED_REASONS`` is pinned to five literals by
``TestTheUngroundedVocabularyIsClosed.test_the_enum_is_exactly_the_five_declared_reasons``,
and mutating the enum reddens that. What nothing checked is the **other** half:

1. that the gate's vocabulary and the database's own CHECK still say the same five things,
   so a constant drifting away from the constraint is a red test rather than a quiet
   disagreement between a module and a migration;
2. that the constraint is actually installed and actually refuses a sixth value.

The second matters because the docstring on ``TestTheUngroundedVocabularyIsClosed`` is
**stale**. It says that "at the P02 migration head, ``finding_observation.ungrounded_reason``
carries no CHECK constraint ... the database accepts any string, including
``'looked_wrong'``". That was true at `0002_pc01_schema`. Migration
`0003_open_items` added ``ck_finding_observation_ungrounded_reason`` and the database now
refuses exactly that string. The claim is left in place in the file that makes it — this
session does not own the correction of another test's prose any more than it owns the
migration — and is asserted false here instead.

The migration is the independent authority. The five values below are read out of
`db/migrations/versions/20260911_0003_open_items.py` and also written as literals, so a
migration edited to widen the vocabulary reddens rather than dragging the expectation with
it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditmanager.findings import UNGROUNDED_REASONS
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.identity import FindingObservationId

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "db"
    / "migrations"
    / "versions"
    / "20260911_0003_open_items.py"
)

#: The five values, written out. P02 §5.1, and the CHECK added by `0003_open_items`.
DECLARED = frozenset(
    {
        "quotation_absent",
        "quotation_on_different_page",
        "span_outside_page",
        "span_outside_block",
        "span_length_mismatch",
    }
)

#: A value that is not one of them, and is exactly the one the stale docstring says the
#: database accepts.
OUTSIDE_THE_VOCABULARY = "looked_wrong"


def _vocabulary_in_the_migration() -> frozenset[str]:
    """The ``IN (...)`` list of ``ck_finding_observation_ungrounded_reason``."""
    source = _MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"ck_finding_observation_ungrounded_reason.*?ungrounded_reason IN \((.*?)\)",
        source,
        re.S,
    )
    assert match is not None, "the migration no longer adds a CHECK on ungrounded_reason"
    return frozenset(re.findall(r"'([a-z_]+)'", match.group(1)))


class TestTheGateAndTheMigrationAgree:
    def test_the_migration_declares_exactly_the_five_values(self) -> None:
        assert _vocabulary_in_the_migration() == DECLARED

    def test_the_gates_vocabulary_is_the_migrations_vocabulary(self) -> None:
        """Neither side is derived from the other: both are compared with ``DECLARED``
        first, so a change to either is attributable."""
        assert UNGROUNDED_REASONS == DECLARED
        assert set(UNGROUNDED_REASONS) == set(_vocabulary_in_the_migration())


class TestTheDatabaseRefusesAValueOutsideTheVocabulary:
    """The constraint is installed, and it bites.

    Each attempt runs in a savepoint so a refusal discards only the attempt, leaving the
    fixture's rows for the next one — the pattern ``TestTheDatabaseEnforcesThePairing``
    established, and for the reason it gives: a statement that matches nothing cannot be
    refused.
    """

    _INSERT = text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, "
        "finding_uid, stage_id, category, finding_text, recommendation_text, "
        "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
        "provider_mode) VALUES (:id, :run, NULL, 'text_analysis', "
        "'internal_contradiction', 'т', 'т', false, :reason, :ap, :pb, 'recorded')"
    )

    def _parameters(self, seeded, reason: str) -> dict:
        return {
            "id": FindingObservationId.new().value,
            "run": seeded.run_id,
            "reason": reason,
            "ap": seeded.analysis_profile_id,
            "pb": seeded.prompt_bundle_id,
        }

    def test_a_sixth_reason_is_refused(self, session: Session, seeded) -> None:
        with pytest.raises(IntegrityError) as caught:
            with nested_transaction(session):
                session.execute(
                    self._INSERT, self._parameters(seeded, OUTSIDE_THE_VOCABULARY)
                )
        # Name the constraint that refused, not merely that something did: the row also
        # violates nothing else, and a test that accepted any IntegrityError here would
        # pass if a foreign key had fired instead.
        assert "ck_finding_observation_ungrounded_reason" in str(caught.value.orig)

    @pytest.mark.parametrize("reason", sorted(DECLARED))
    def test_each_declared_reason_is_accepted(
        self, session: Session, seeded, reason: str
    ) -> None:
        """The control. The constraint refuses the sixth value because it is outside the
        vocabulary, not because it refuses every ungrounded row."""
        with nested_transaction(session):
            session.execute(self._INSERT, self._parameters(seeded, reason))
