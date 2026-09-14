"""Record whether a model call's cost was measured or estimated.

Revision ID: 0004_cost_basis
Revises: 0003_open_items

``model_call.cost_micros`` held both and nothing recorded which. That was tolerable while a
rate table was the only source; it stopped being tolerable when `OD-02` was revised to a
proxy that reports what a call actually cost, because the same column now carries a
measurement for a proxied run and a derivation for a recorded one - and a report that
presents the two identically is a report nobody can cite.

`P4-OPS-01` found it while building the PC-02 tooling: it had to derive the basis rather than
read it, and derivation is exactly what a measurement study should not have to do about its
own figures.
"""

from __future__ import annotations

from alembic import op

revision = "0004_cost_basis"
down_revision = "0003_open_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE model_call
            ADD COLUMN cost_basis text NOT NULL DEFAULT 'estimated';
        """
    )
    op.execute(
        """
        ALTER TABLE model_call ADD CONSTRAINT ck_model_call_cost_basis
            CHECK (cost_basis IN ('measured', 'estimated'));
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN model_call.cost_basis IS
            'Whether cost_micros was reported by the transport or derived from a rate '
            'table. The default is estimated because every row written before this column '
            'existed was derived: a backfill claiming otherwise would invent provenance '
            'for calls nobody measured.';
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE model_call DROP CONSTRAINT IF EXISTS ck_model_call_cost_basis;")
    op.execute("ALTER TABLE model_call DROP COLUMN IF EXISTS cost_basis;")
