"""0057 -- a decision may be carried over from an earlier version's pass (`UI-B-14`, «Перенести решения из V#»).

An expert may carry the decisions in force of one optimisation pass over to the pass of a later version of the same
document set. A carried decision is **an ordinary decision event** of the target proposal, authored by the expert who
confirmed the carryover (the append-only history of ``optimisation_proposal_decision`` and ``am_immutable_row`` are
unchanged); the one thing it adds is where it came from. ``carried_from_decision_id`` names the source decision --
by its opaque identity, never by a display number, a name or a position -- and is ``NULL`` for every decision an expert
made directly, which is every row written before this migration.

Four constraints keep the column honest:

* ``fk_optimisation_proposal_decision_carried_from`` -- the named decision exists, and (with ``am_immutable_row``) can
  never be deleted from under the decision that cites it;
* ``ck_optimisation_proposal_decision_carried_from_format`` -- the usual ``opd_<ULID>`` shape;
* ``ck_optimisation_proposal_decision_carried_from_not_self`` -- a decision is not its own source;
* ``ck_optimisation_proposal_decision_carried_from_not_revoke`` -- a withdrawal is not carried. A carryover moves a
  decision in force (``accept``, ``reject`` or ``revise``); nothing is carried for a proposal nobody decided.

That the source belongs to a pass of an *earlier* version of the *same* document set, and that the target proposal had no
event, cannot be seen by a CHECK (it needs other rows); the command checks both under the target proposal's advisory
lock (`auditmanager.optimisation.proposals.carryover`).

The downgrade refuses while any carried decision exists: dropping the column would turn «carried from V1» into «decided
directly», a false statement about an expert's act (AGENTS section 4, no silent fallback). An operator decides what to
do with that history first.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0057_decision_carryover"
down_revision: str | None = "0056_optimisation_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_TABLE = "optimisation_proposal_decision"
_FK = "fk_optimisation_proposal_decision_carried_from"
_FORMAT = "ck_optimisation_proposal_decision_carried_from_format"
_NOT_SELF = "ck_optimisation_proposal_decision_carried_from_not_self"
_NOT_REVOKE = "ck_optimisation_proposal_decision_carried_from_not_revoke"
_INDEX = "ix_optimisation_proposal_decision_carried_from"

_COMMENT_BEFORE = (
    "W60-OPT-PROPOSALS-01. Append-only expert decisions on one proposal: accept, reject or revise (with its comment), "
    "or revoke (`UI-B-12`: the withdrawal of the standing decision, which takes the proposal back to pending), the "
    "acting account, the claimed command and the time. seq orders one proposal''s decisions and is never an identity; "
    "the current decision is the latest. Never updated or deleted (am_immutable_row)."
)
_COMMENT_AFTER = (
    _COMMENT_BEFORE
    + " carried_from_decision_id (`UI-B-14`) names the decision of an earlier version''s pass that an expert carried "
    "over; NULL for a decision made directly."
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} ADD COLUMN carried_from_decision_id text NULL")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FK} "
        "FOREIGN KEY (carried_from_decision_id) "
        f"REFERENCES {_TABLE} (proposal_decision_id) ON DELETE RESTRICT"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FORMAT} "
        f"CHECK (carried_from_decision_id IS NULL OR carried_from_decision_id ~ '^opd_{ULID}$')"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_NOT_SELF} "
        "CHECK (carried_from_decision_id IS NULL OR carried_from_decision_id <> proposal_decision_id)"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_NOT_REVOKE} "
        "CHECK (carried_from_decision_id IS NULL OR verdict <> 'revoke')"
    )
    # Partial: almost every row is a direct decision, and the only question asked of the column is "which decisions
    # were carried from this one" (the foreign key's own check, and a reader of a decision's descendants).
    op.execute(
        f"CREATE INDEX {_INDEX} ON {_TABLE} (carried_from_decision_id) WHERE carried_from_decision_id IS NOT NULL"
    )
    op.execute(f"COMMENT ON TABLE {_TABLE} IS '{_COMMENT_AFTER}';")


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM optimisation_proposal_decision WHERE carried_from_decision_id IS NOT NULL) THEN
                RAISE EXCEPTION
                    'optimisation proposal decisions include carried-over ones (carried_from_decision_id); decide '
                    'what to do with that history before downgrading 0057';
            END IF;
        END
        $$;
        """
    )
    op.execute(f"DROP INDEX {_INDEX}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_NOT_REVOKE}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_NOT_SELF}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_FORMAT}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_FK}")
    op.execute(f"ALTER TABLE {_TABLE} DROP COLUMN carried_from_decision_id")
    op.execute(f"COMMENT ON TABLE {_TABLE} IS '{_COMMENT_BEFORE}';")
