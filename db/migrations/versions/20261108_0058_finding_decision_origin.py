"""0058 -- a finding decision may be carried over from an earlier version (`UI-A-73`, the original's «↩ Перенесено из V1»).

An expert may carry the decision in force of a finding of an earlier version over to the matching finding of a later
version (`W59-DECISION-CARRYOVER-01`). A carried decision is **an ordinary decision event** of the target finding, authored
by the expert who confirmed the carryover (the append-only ledger and its triggers are unchanged); until this migration the
only trace of where it came from was the event's rendered comment. ``carried_from_decision_id`` names the source decision --
by its opaque identity, never by a display number, a name or a position -- and is ``NULL`` for every event an expert made
directly, which is every row written before this migration. The comment of an event carried before the migration still
says where it came from, and nothing parses it back (the ledger cannot be rewritten to add the link to those rows).

Four constraints keep the column honest:

* ``fk_expert_decision_event_carried_from`` -- the named decision exists, and (with the append-only trigger) can never be
  deleted from under the decision that cites it; the project erase tool, which deletes a whole project's ledger in one
  statement, is the one deliberate exception (`R-146o`);
* ``ck_expert_decision_event_carried_from_format`` -- the usual ``dec_<ULID>`` shape;
* ``ck_expert_decision_event_carried_from_not_self`` -- an event is not its own source;
* ``ck_expert_decision_event_carried_from_verdict`` -- only an ``accept`` or a ``reject`` is carried (a comment or a
  withdrawal is not a decision in force, and nothing is carried for a finding nobody decided).

That the source belongs to an *earlier* version of the *same* document set, and that the target finding had no event, cannot
be seen by a CHECK (it needs other rows); the command checks both under the row locks of both findings
(`auditmanager.decisions.carryover`).

The downgrade refuses while any carried event exists: dropping the column would turn «carried from V1» into «decided
directly», a false statement about an expert's act (AGENTS section 4, no silent fallback). An operator decides what to do
with that history first.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0058_finding_decision_origin"
down_revision: str | None = "0057_decision_carryover"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_TABLE = "expert_decision_event"
_FK = "fk_expert_decision_event_carried_from"
_FORMAT = "ck_expert_decision_event_carried_from_format"
_NOT_SELF = "ck_expert_decision_event_carried_from_not_self"
_VERDICT = "ck_expert_decision_event_carried_from_verdict"
_INDEX = "ix_expert_decision_event_carried_from"

_COMMENT_BEFORE = (
    "The append-only expert decision ledger. UPDATE and DELETE are refused by the "
    "database itself, not by a repository somebody could bypass: there is no row to "
    "overwrite, so a verdict is a projection over this stream and history cannot be "
    "lost. PD-01: correction and revocation append a new decision_id. PC-01 emits "
    "accept, reject and comment; revoke is in the enum so PD-01 stays implementable "
    "without a schema change."
)
_COMMENT_AFTER = (
    _COMMENT_BEFORE
    + " carried_from_decision_id (`UI-A-73`) names the decision of an earlier version''s finding that an expert "
    "carried over; NULL for an event made directly."
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} ADD COLUMN carried_from_decision_id text NULL")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FK} "
        "FOREIGN KEY (carried_from_decision_id) "
        f"REFERENCES {_TABLE} (decision_id) ON DELETE RESTRICT"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FORMAT} "
        f"CHECK (carried_from_decision_id IS NULL OR carried_from_decision_id ~ '^dec_{ULID}$')"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_NOT_SELF} "
        "CHECK (carried_from_decision_id IS NULL OR carried_from_decision_id <> decision_id)"
    )
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_VERDICT} "
        "CHECK (carried_from_decision_id IS NULL OR event_type IN ('accept', 'reject'))"
    )
    # Partial: almost every row is a direct decision, and the only question asked of the column is "which events were
    # carried from this one" (the foreign key's own check, and a reader of an event's descendants).
    op.execute(
        f"CREATE INDEX {_INDEX} ON {_TABLE} (carried_from_decision_id) WHERE carried_from_decision_id IS NOT NULL"
    )
    op.execute(f"COMMENT ON TABLE {_TABLE} IS '{_COMMENT_AFTER}';")


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM expert_decision_event WHERE carried_from_decision_id IS NOT NULL) THEN
                RAISE EXCEPTION
                    'expert decision events include carried-over ones (carried_from_decision_id); decide '
                    'what to do with that history before downgrading 0058';
            END IF;
        END
        $$;
        """
    )
    op.execute(f"DROP INDEX {_INDEX}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_VERDICT}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_NOT_SELF}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_FORMAT}")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT {_FK}")
    op.execute(f"ALTER TABLE {_TABLE} DROP COLUMN carried_from_decision_id")
    op.execute(f"COMMENT ON TABLE {_TABLE} IS '{_COMMENT_BEFORE}';")
