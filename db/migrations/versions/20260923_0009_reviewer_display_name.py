"""The name other reviewers read: ``app_user.display_name``, nullable on purpose.

Revision ID: 0009_reviewer_display_name
Revises: 0008_sign_in_throttle

`R-37`. Wave 41 stopped attributing every verdict by every reviewer to one configured
constant and started writing the **login** of the authenticated reviewer into
``expert_decision_event.author_label`` (`D-78`). That label reaches every other reviewer
through ``listDecisionHistory``, ``listDecisions`` and two screens, and the owner ruled
that what it should carry is a **display name**.

This revision is the column that name lives in. What reads it is
``auditmanager.access.models.UserRecord.display_label``; what writes it is
``python -m auditmanager.access.name``.

Why it is nullable, which is the decision the ruling left open
---------------------------------------------------------------
The obvious alternative is ``NOT NULL`` backfilled from ``login``. It is simpler, it makes
every read unconditional, and it is **wrong here**, because it destroys -- in data, on the
first upgrade, irreversibly -- the difference between

* an account whose reviewer has **not chosen** a name, and
* an account whose reviewer **chose** their own login as their name.

Those are different facts and only the first one is a state somebody should act on. With a
backfill, nobody can ever tell them apart again; the fallback becomes invisible the moment
it is applied, which is the **silent fallback** ``AGENTS.md`` §4 forbids, frozen into rows.

Keeping the NULL makes it a query instead::

    SELECT login FROM app_user WHERE display_name IS NULL

which is exactly what ``0006`` did for the seeded password with ``is_default_credential``:
*"the condition is a query rather than a piece of folklore"*. The same three visibility
mechanisms are used here for the same reason -- the column, the warning this revision logs
while it runs, and ``python -m auditmanager.access.check``.

**An account with no display name is not broken.** ``display_label`` answers with the
login, which is a real string the reviewer typed, is unique, and is 1..100 characters by
``ck_app_user_login_format`` -- inside ``author_label``'s 1..128 by construction. So every
account can record a decision from the moment this lands, and nothing here is a
prerequisite for anything.

Why 128, and why the CHECK
---------------------------
128 is ``DecisionEvent.author_label``'s ``maxLength`` in the frozen
``contracts/api/v1/openapi.json``. A column that admitted a longer name would let an
account be given one that cannot be recorded against a decision -- and the failure would
appear at the moment an expert records a verdict, which is the worst available moment.
``auditmanager.access.models.MAX_DISPLAY_NAME_LENGTH`` carries the same number with the
same reason; the CHECK is here as well because raw SQL must not be able to write what the
boundary would refuse, which is the rule ``0006`` already applies to the login.

The CHECK also refuses a blank and an untrimmed value. A blank would be a stored value that
``author_label``'s ``minLength: 1`` refuses, i.e. a row that cannot be written at the one
moment it is needed, and ``' Анна '`` beside ``'Анна'`` would be two names that render
identically and compare unequal.

**No UNIQUE.** Two reviewers may genuinely share a display name; identity is ``user_uid``
and the addressable name is ``login``, both of which are already unique. A UNIQUE here
would be this table claiming that two people cannot be called the same thing.

Downgrade
---------
Dropping the column loses names somebody typed and that exist nowhere else, which is the
shape ``0004``'s and ``0006``'s downgrades refuse outright. It is **not** refused here, and
the difference is worth stating: a display name is a label, not credential material and not
measured evidence -- losing it costs the typing, and every account keeps working, because
``display_label`` falls back to the login. So the downgrade proceeds and is **loud**: it
names every account whose name it is about to destroy, so an operator who is downgrading
during an incident is told what it costs rather than finding out afterwards.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0009_reviewer_display_name"
down_revision: str | None = "0008_sign_in_throttle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Named ``alembic.*`` so it inherits the runner's configured handler and reaches the
#: deployment log, exactly as ``0006``, ``0007`` and ``0008`` do.
_log = logging.getLogger("alembic.migration.reviewer_display_name")

#: ``DecisionEvent.author_label``'s ``maxLength``. See the module docstring.
MAX_DISPLAY_NAME_LENGTH = 128


def upgrade() -> None:
    op.execute("ALTER TABLE app_user ADD COLUMN display_name text;")
    op.execute(
        f"""
        ALTER TABLE app_user
            ADD CONSTRAINT ck_app_user_display_name CHECK (
                display_name IS NULL
                OR (
                    btrim(display_name) = display_name
                    AND length(display_name) BETWEEN 1 AND {MAX_DISPLAY_NAME_LENGTH}
                )
            );
        """
    )
    op.execute(
        "COMMENT ON COLUMN app_user.display_name IS "
        "'The name other reviewers read on a decision this account recorded. NULL means "
        "this reviewer has not chosen one, and NULL is NEVER an error: the label falls "
        "back to the login, which is unique and is 1-100 characters, so it always fits "
        "author_label. The NULL is kept rather than backfilled so that -has not chosen- "
        "and -chose their own login- stay different facts: SELECT login FROM app_user "
        "WHERE display_name IS NULL is the whole of how an operator sees the fallback. "
        "Not unique: two reviewers may share a name. Not an identity: user_uid is. "
        "Set with python -m auditmanager.access.name --login <login> --display-name <name>.';"
    )
    unnamed = (
        op.get_bind()
        .execute(
            text("SELECT login FROM app_user WHERE display_name IS NULL ORDER BY login")
        )
        .scalars()
        .all()
    )
    if unnamed:
        _log.warning(
            "0009_reviewer_display_name: %d account(s) have no display name (%s), so a "
            "decision they record is attributed to their login. That is the intended "
            "fallback and not a failure -- nothing is locked out and nothing needs doing "
            "before the next run. Give a reviewer the name other reviewers should read "
            "with `python -m auditmanager.access.name --login <login> --display-name "
            "'<name>'`, and see the whole list at any time with `python -m "
            "auditmanager.access.check`.",
            len(unnamed),
            ", ".join(unnamed),
        )


def downgrade() -> None:
    """Drop the column, after naming every account whose name the drop destroys.

    See the module docstring: unlike ``0004`` and ``0006`` this downgrade proceeds, because
    what it loses is a label rather than credential material or measured evidence, and
    every account goes on working with its login as its label. It is loud because the names
    exist nowhere else and nobody can be asked to retype what they were not told was gone.
    """
    named = (
        op.get_bind()
        .execute(
            text(
                "SELECT login, display_name FROM app_user "
                "WHERE display_name IS NOT NULL ORDER BY login"
            )
        )
        .all()
    )
    if named:
        _log.warning(
            "0009_reviewer_display_name downgrade: %d account(s) have a display name "
            "somebody typed and it exists nowhere else (%s). Dropping the column destroys "
            "it. Every account keeps working -- a decision recorded after this is "
            "attributed to the login, as it was before this revision -- so nothing is lost "
            "but the typing, and the typing is not recoverable.",
            len(named),
            ", ".join(f"{login} ({name})" for login, name in named),
        )
    op.execute("ALTER TABLE app_user DROP CONSTRAINT ck_app_user_display_name;")
    op.execute("ALTER TABLE app_user DROP COLUMN display_name;")
