"""0069 -- the project an account chose last: ``account_last_project`` (`UIP-G-05`, programme `UI-PARITY-R3`).

Revision ID: 0069_account_last_project
Revises: 0068_reviewable_findings

Owner ruling Г7-B: the screens that show «Все объекты» or one object remember the object an account chose, on the server and not in
the browser, and a link with ``?project=`` overrides it. This revision stores only that choice: one row per account that has chosen
an object. «Все объекты» is not stored; an account that has not chosen one has no row.

What this revision adds
-----------------------
``account_last_project`` (KEEP, account side, like ``account_release_mark``)
    ``user_uid`` -- the account, the primary key (one row per account) with ``ON DELETE CASCADE``: the row is the account's own and
    goes with it; it is an entry of ``auditmanager.access.references.ACCOUNT_REFERENCES``. ``project_uid`` -- the object chosen, as a bare
    identity with its format check. ``selected_at`` -- the instant of the latest change of the choice.

    **There is no foreign key to ``project``, on purpose.** A table that references ``project`` joins the foreign-key closure of
    ``scripts/recovery/project_erase.py`` and must then be a PRODUCT table, truncated by a purge of product data and listed with its own
    scope slice in the erase's test; the choice is the account's preference, not product data, and must survive a purge with its
    account. The two consequences are written down where they are handled: ``setMyLastProject`` refuses an object that does not exist
    (``not_found``) by reading ``project`` in the same transaction, and ``getMe`` reads the choice only while its object exists, so an
    object that was erased or purged leaves ``null`` behind and never a dangling identity. A stale row is overwritten by the next choice.
    Deleting an object is never refused for this table.

The application role may ``SELECT``, ``INSERT``, ``UPDATE`` and ``DELETE`` it (``scripts/recovery/grant_classification.py``,
read-write: the choice is an upsert).

Downgrade
---------
Drops the table. The only fact lost is which object each account chose last; nothing else reads it.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0069_account_last_project"
down_revision: str | None = "0068_reviewable_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE account_last_project (
            user_uid text NOT NULL
                CONSTRAINT ck_account_last_project_user_format CHECK (user_uid ~ '^usr_{ULID}$')
                CONSTRAINT fk_account_last_project_user REFERENCES app_user (user_uid) ON DELETE CASCADE,
            project_uid text NOT NULL
                CONSTRAINT ck_account_last_project_project_format CHECK (project_uid ~ '^prj_{ULID}$'),
            selected_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT pk_account_last_project PRIMARY KEY (user_uid)
        )
    """)
    op.execute(
        "COMMENT ON TABLE account_last_project IS "
        "'UIP-G-05 (owner ruling G7-B): the object an account chose last, one row per account, kept on the server. The all-objects view is not "
        "stored. Goes with the account (ON DELETE CASCADE). No foreign key to project: the choice survives a purge of product data and is read "
        "only while its object exists.';"
    )


def downgrade() -> None:
    op.execute("DROP TABLE account_last_project")
