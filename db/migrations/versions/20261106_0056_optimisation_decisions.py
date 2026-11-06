"""0056 -- an expert may withdraw a decision on an optimisation proposal (`UI-B-12`, «Снять решение»).

``0027`` closed ``optimisation_proposal_decision.verdict`` to ``accept``, ``reject`` and ``revise``. A withdrawal is one
more kind of event on the same append-only table: the decision of a proposal stays what its latest event says, and when
that event is a ``revoke`` the proposal is ``pending`` again. Nothing is updated or deleted -- ``am_immutable_row`` still
guards the table -- so the history keeps the decision that was withdrawn, the withdrawal and who made it.

The constraint keeps its name: tests and operators address it by name. That a ``revoke`` has something to withdraw (a
latest event that is not itself a ``revoke``) is checked by the command under the proposal's advisory lock, because a CHECK
cannot see the proposal's other rows.

The downgrade refuses while any ``revoke`` event exists. Dropping them would erase an expert's act and re-adding the old
CHECK would fail over them (AGENTS §4, no silent fallback); an operator decides what to do with that history first.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0056_optimisation_decisions"
down_revision: str | None = "0055_work_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Restated rather than imported (a migration is history); ``tests/unit/optimisation/proposals`` holds it equal to
#: ``auditmanager.optimisation.proposals.policy.STORED_VERDICTS``.
STORED_VERDICTS: tuple[str, ...] = ("accept", "reject", "revise", "revoke")
PREVIOUS_VERDICTS: tuple[str, ...] = ("accept", "reject", "revise")

_CONSTRAINT = "ck_optimisation_proposal_decision_verdict"
_COMMENT_HEAD = (
    "W60-OPT-PROPOSALS-01. Append-only expert decisions on one proposal: accept, reject or revise (with its comment)"
)
_COMMENT_TAIL = (
    ", the acting account, the claimed command and the time. seq orders one proposal''s decisions and is never an "
    "identity; the current decision is the latest. Never updated or deleted (am_immutable_row)."
)


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _set_verdicts(values: Sequence[str]) -> None:
    op.execute(f"ALTER TABLE optimisation_proposal_decision DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE optimisation_proposal_decision ADD CONSTRAINT {_CONSTRAINT} "
        f"CHECK (verdict IN ({_sql_list(values)}))"
    )


def upgrade() -> None:
    _set_verdicts(STORED_VERDICTS)
    op.execute(
        "COMMENT ON TABLE optimisation_proposal_decision IS "
        f"'{_COMMENT_HEAD}, or revoke (`UI-B-12`: the withdrawal of the standing decision, which takes the proposal back "
        f"to pending){_COMMENT_TAIL}';"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM optimisation_proposal_decision WHERE verdict = 'revoke') THEN
                RAISE EXCEPTION
                    'optimisation proposal decisions include withdrawals (revoke); decide what to do with that '
                    'history before downgrading 0056';
            END IF;
        END
        $$;
        """
    )
    _set_verdicts(PREVIOUS_VERDICTS)
    op.execute(
        "COMMENT ON TABLE optimisation_proposal_decision IS "
        f"'{_COMMENT_HEAD}{_COMMENT_TAIL}';"
    )
