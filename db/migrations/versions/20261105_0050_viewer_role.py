"""The account role vocabulary gains «Наблюдатель» (``viewer``): `R-150e`, `R-150x`.

``0015`` closed ``app_user_role.role`` to ``expert`` and ``admin`` with
``ck_app_user_role_role``. The viewer reads and downloads product data and changes nothing; it
is the only role of an account that holds it, a rule the ``access`` boundary enforces where
roles are written (``require_exclusive_viewer``) because a column CHECK cannot see the other
rows of the same account.

The constraint keeps its name: tests and operators address it by name.

The downgrade refuses while any account holds the viewer role. Deleting those rows would
silently change who may read product data (AGENTS §4, no silent fallback); an operator
removes or changes those roles first, deliberately.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050_viewer_role"
down_revision: str | None = "0049_stage_identity_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE app_user_role DROP CONSTRAINT ck_app_user_role_role")
    op.execute(
        "ALTER TABLE app_user_role ADD CONSTRAINT ck_app_user_role_role "
        "CHECK (role IN ('expert', 'admin', 'viewer'))"
    )
    op.execute(
        "COMMENT ON TABLE app_user_role IS "
        "'The roles an account holds, as a set: expert, admin, both, viewer alone, or none. "
        "Enforced on the server by the operation register in api/security.py; no role travels "
        "in a credential. The viewer is never combined with another role (access boundary). "
        "Every change raises app_user.token_epoch in the same transaction.';"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM app_user_role WHERE role = 'viewer') THEN
                RAISE EXCEPTION
                    'accounts hold the viewer role; change those roles before downgrading 0050';
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE app_user_role DROP CONSTRAINT ck_app_user_role_role")
    op.execute(
        "ALTER TABLE app_user_role ADD CONSTRAINT ck_app_user_role_role "
        "CHECK (role IN ('expert', 'admin'))"
    )
    op.execute(
        "COMMENT ON TABLE app_user_role IS "
        "'The roles an account holds, as a set: expert, admin, both or none. Enforced on "
        "the server by the operation register in api/security.py; no role travels in a "
        "credential. Every change raises app_user.token_epoch in the same transaction.';"
    )
