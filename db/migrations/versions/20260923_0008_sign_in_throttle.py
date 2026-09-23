"""Failed sign-ins as columns: the count, when it last moved, and until when the door is shut.

Revision ID: 0008_sign_in_throttle
Revises: 0007_credential_epoch

``0007_credential_epoch`` made a credential retractable. This revision makes one harder to
guess. They are the two halves of `R-26` and they are **not** the same mechanism, which is
the first thing to say because the columns sit in the same table and invite being read as
one thing:

* ``token_epoch`` decides whether a credential **already minted** is still accepted. It is
  raised deliberately, by a password change or by an operator, and it never moves on its
  own.
* The three columns here decide whether a credential **may be minted at all right now**.
  They move by themselves, on every failed attempt, and they **unmove by themselves** when
  time passes. Nothing an attacker does to them reaches a credential somebody already holds.

A rate limit and a lockout are two different things
---------------------------------------------------
``failed_sign_ins`` and ``last_failed_sign_in_at`` are the **rate limit**: a count of
consecutive recent failures for one account. A rate limit slows a guesser and recovers on
its own -- the count restarts by itself once the failures stop being recent, and no
operator is ever involved.

``sign_in_blocked_until`` is the **lockout**: an instant before which this account's
password is not consulted at all, so that even the right password mints nothing. A lockout
stops a guesser rather than slowing one, and **a lockout needs a way back**, because a
lockout with no way back is a denial of service anybody can aim at a named account. There
are three ways back and all three are in the code rather than in a runbook:

1. **time** -- the instant passes and the next attempt starts a fresh allowance. This is
   the ordinary one and needs nobody;
2. **a password change** -- ``POST /auth/password`` clears these three columns in the same
   UPDATE that writes the new digest, because an account that has just proved its current
   password is not a guesser;
3. **an operator** -- ``python -m auditmanager.access.unlock --login <login>``, immediately,
   with no redeploy and no restart. It is the answer to *"the owner cannot sign in to their
   own pilot"* and it is why this revision exists as a column rather than as a counter in
   the API process's memory.

Why these are columns and not process memory
---------------------------------------------
``0007``'s docstring argues the same point for revocation and the argument is **not** the
same one here, so it is made again rather than borrowed.

For revocation, memory is fatal because a restart would **undo** the operator's decision. A
failed-attempt counter has the opposite failure mode: a restart would **forget** an
attacker's accumulated budget, which costs a bounded amount of protection and nothing an
operator decided.

The reason it is still a column is the lockout, not the counter. A lockout is a refusal
state somebody has to be able to **see** and **clear**: an operator whose owner cannot sign
in needs to know that the account is shut and needs to open it. In memory, the only way to
clear it is to restart the API -- and *"restart something and hope that was the process
holding it"* is exactly the reasoning `W39-REVOKE` refused for revocation. A second replica
makes it worse in both directions at once: N replicas mean N times the allowance, and an
unlock that reaches one of them.

And once the lockout is durable the count must be too, because the count is the only
evidence the lockout was ever earned.

Why the arithmetic is the database's
-------------------------------------
Every write below computes the next value **from the row**, never from a value this
process read a moment ago -- the same reason ``0007`` made revocation
``token_epoch = token_epoch + 1``. Two simultaneous failed attempts must produce two
increments; a read-modify-write in the application would let one overwrite the other with
the same number, which reads as a counted attempt and is not one. An attacker who can make
requests in parallel would get the difference for free.

For the same reason ``sign_in_blocked_until`` is compared against the database's ``now()``
and never against a clock this process read. Two clocks that must agree are two ways to be
wrong, and one of the two would be the attacker's side of the comparison.

Defaults, and what they mean for an existing installation
-----------------------------------------------------------
``failed_sign_ins`` starts at 0 with a ``CHECK (>= 0)``; the two instants start NULL.
**NULL means "nothing has failed recently" and never "blocked forever"** -- a nullable
column whose NULL had to be read as a refusal would be one restart away from locking an
installation out of itself. So every existing account is unblocked with a clean count the
moment this lands, and **deploying this revision locks nobody out**, which is the opposite
of what deploying ``0007`` does and is worth stating beside it.

Downgrade
---------
Dropping these columns removes a brake and loses a count. Nothing measured is destroyed --
the values record attempts that have already happened and whose effect is either spent or
about to expire on its own -- so unlike ``0004`` there is nothing here that exists nowhere
else. It is still **loud**: any account currently blocked is named before the columns go,
because an operator downgrading during an attack is un-blocking an account under attack and
should be told so rather than find out.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0008_sign_in_throttle"
down_revision: str | None = "0007_credential_epoch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Named ``alembic.*`` so it inherits the runner's configured handler and reaches the
#: deployment log, exactly as ``0006`` and ``0007`` do.
_log = logging.getLogger("alembic.migration.sign_in_throttle")


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app_user
            ADD COLUMN failed_sign_ins integer NOT NULL DEFAULT 0,
            ADD COLUMN last_failed_sign_in_at timestamptz,
            ADD COLUMN sign_in_blocked_until timestamptz;
        """
    )
    op.execute(
        """
        ALTER TABLE app_user
            ADD CONSTRAINT ck_app_user_failed_sign_ins CHECK (failed_sign_ins >= 0);
        """
    )
    op.execute(
        "COMMENT ON COLUMN app_user.failed_sign_ins IS "
        "'Consecutive recent failed sign-ins for this account. Raised by one on every "
        "refused attempt whose predecessor was recent, restarted at one when it was not, "
        "and set to zero by a successful sign-in, by a password change and by the operator "
        "unlock command. It is a rate limit and not a lockout: on its own it refuses "
        "nothing.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.last_failed_sign_in_at IS "
        "'When failed_sign_ins last moved. NULL means nothing has failed since this account "
        "was last clean. It is what makes the count mean CONSECUTIVE AND RECENT rather than "
        "EVER: failures further apart than the attempt window do not accumulate, so a "
        "reviewer who mistypes twice a week is not walked into a lockout.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.sign_in_blocked_until IS "
        "'The lockout. Until this instant the password is not consulted at all, so even the "
        "right one mints nothing; NULL means the account may be tried now, and NULL is NEVER "
        "read as a refusal. It is set when the allowance is spent and it clears itself by "
        "passing - and also by a password change, and by python -m auditmanager.access.unlock. "
        "A lockout with no way back is a denial of service anybody can aim at a named "
        "account, so the ways back are part of the mechanism rather than a runbook step. "
        "Credentials already minted are NOT touched: an unauthenticated caller must not be "
        "able to sign out a reviewer who is working.';"
    )
    _log.warning(
        "0008_sign_in_throttle: repeated failed sign-ins now slow an account down and "
        "then close it for a cooling-off period. Nobody is locked out by this upgrade - "
        "every existing account starts with a clean count and no block. If an account is "
        "ever shut and the owner needs it now, run "
        "`python -m auditmanager.access.unlock --login <login>`."
    )


def downgrade() -> None:
    """Drop the columns, after naming every account the drop lets back in.

    See the module docstring: removing these columns removes a brake. The accounts that
    are blocked at this instant are the ones an operator most needs to know about, because
    a block that is live is usually a block something is currently earning.
    """
    bind = op.get_bind()
    blocked = bind.execute(
        text(
            "SELECT login, sign_in_blocked_until FROM app_user "
            "WHERE sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until > now() "
            "ORDER BY login"
        )
    ).all()
    if blocked:
        _log.warning(
            "0008_sign_in_throttle downgrade: %d account(s) are blocked from signing in "
            "right now (%s). Dropping sign_in_blocked_until opens them immediately and "
            "removes the brake that closed them. If this is an attack, it is still going "
            "on after the downgrade and nothing is counting it.",
            len(blocked),
            ", ".join(f"{login} (until {until.isoformat()})" for login, until in blocked),
        )
    op.execute("ALTER TABLE app_user DROP CONSTRAINT ck_app_user_failed_sign_ins;")
    op.execute(
        "ALTER TABLE app_user "
        "DROP COLUMN sign_in_blocked_until, "
        "DROP COLUMN last_failed_sign_in_at, "
        "DROP COLUMN failed_sign_ins;"
    )
