"""P01 baseline head: an empty schema with a working migration runner.

FF-01 §4 approves the foundation and explicitly does *not* approve product tables,
so this revision creates none. It exists so that:

* ``alembic_version`` is created and stamped on a clean database, which is what
  makes "migrate an empty database" and "re-running migrations is safe at head"
  distinguishable outcomes rather than the same no-op;
* the P02 schema has a named parent to extend, instead of being the base itself.
  Reverting the product schema then leaves a working, migrated, empty database
  rather than an unmigrated one.

Downgrade is a deliberate no-op: there is nothing below this point, and
``db/migrations/README.md`` is explicit that a down file is not a substitute for
data recovery.

Revision ID: 0001_baseline
Revises: None
Created: 2026-09-10
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema objects. The baseline is the empty database, recorded."""


def downgrade() -> None:
    """No-op: nothing was created."""
