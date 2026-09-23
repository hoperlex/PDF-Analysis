"""Revocation as a column: the credential epoch, and when it last moved.

Revision ID: 0007_credential_epoch
Revises: 0006_app_user

A credential minted by ``auditmanager.api.security`` is a signed statement, not a row.
That is what makes it cheap -- the API verifies it with one HMAC and reaches for nothing
-- and it is also what made it **irrevocable**. Between the moment one was issued and the
moment its ``exp`` passed, the only thing that could stop it was rotating the deployment
secret, which stops *every* credential including the operator's own and needs a redeploy.
``0006_app_user``'s own docstring says why a credential in the environment is the wrong
place: it "cannot be created, changed or revoked without a redeploy". The row fixed
creation and change. This revision fixes revocation.

What is revoked, and why a counter rather than a list
-----------------------------------------------------
**An account's credentials, all of them at once -- never one token.** The alternative is a
denylist keyed by a token identity, and it is worse here in three separate ways: it needs
a second table that grows with traffic and must be swept; it cannot express "everything
this account holds", which is the only question anybody actually asks ("the pilot has
ended", "change my password"); and it cannot revoke a credential minted *before* the
denylist existed, because such a credential carries no identity to list.

``token_epoch`` is a counter. Every credential carries the epoch it was minted under, and
a request is accepted only when the two agree. Raising the column by one invalidates every
credential ever minted for that account, in one statement, with no list to keep and
nothing to sweep. It is `O(1)` to revoke and `O(1)` to check.

Why it starts at 1 and not at 0
-------------------------------
So that "this account has an epoch" and "this account's epoch is falsy" are never the same
test. The CHECK enforces it. Nothing in this system is allowed to read a missing epoch as
a permissive one, and a column that cannot hold 0 is one fewer place that could.

**Every credential issued before this revision is refused from the moment it lands.**
Those credentials carry no epoch at all, and a credential whose epoch cannot be read is
not a credential -- the same rule the seam already applies to an unknown format version.
So deploying this change is itself a global revocation, and the honest way to describe it
to an operator is: everyone signs in again once. That is stated here rather than
discovered, and it is the correct direction for a change whose entire purpose is that a
credential can be taken away.

``token_epoch_updated_at``
--------------------------
The epoch is a number nobody can date. An operator asking "when did we end the pilot?" or
"has this account been revoked since the incident?" needs an instant, and the same
reasoning that gave ``password_updated_at`` its column gives this one its own: a fact an
operator needs is a column, not an inference from a log that may have rotated.

It is *not* merged with ``password_updated_at``. A password change bumps both; a
revocation bumps only this one. Collapsing them would make "the password was changed" and
"the credentials were revoked" the same record, and they are different events with
different remedies.

Downgrade
---------
Dropping these columns is reversible in the schema and **not** reversible in effect: the
application that ran before them accepts any credential whose signature and ``exp`` hold,
so a downgrade restores every credential revoked within the last
``TOKEN_LIFETIME_SECONDS`` -- one hour at the time of writing -- and no later one, because
anything older has expired on its own.

That window is bounded, an operator takes it deliberately, and refusing the downgrade
outright would make the first password change in an installation's life permanently
un-downgradable. So it proceeds, and it is **loud**: the accounts whose epoch is above 1
are named in a warning before the columns go, which is the same bargain ``0006`` makes
with its seeded password. Nothing measured is lost -- unlike ``0004``, the value here
records an intent that has already taken effect, not an observation that exists nowhere
else.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0007_credential_epoch"
down_revision: str | None = "0006_app_user"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Named ``alembic.*`` so it inherits the runner's configured handler and reaches the
#: deployment log, exactly as ``0006`` does.
_log = logging.getLogger("alembic.migration.credential_epoch")

#: What every existing account is set to, and what a new one starts at. Never 0: see the
#: docstring.
INITIAL_EPOCH = 1


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app_user
            ADD COLUMN token_epoch integer NOT NULL DEFAULT 1,
            ADD COLUMN token_epoch_updated_at timestamptz NOT NULL DEFAULT now();
        """
    )
    op.execute(
        """
        ALTER TABLE app_user
            ADD CONSTRAINT ck_app_user_token_epoch CHECK (token_epoch >= 1);
        """
    )
    op.execute(
        "COMMENT ON COLUMN app_user.token_epoch IS "
        "'The generation of credentials this account currently accepts. Every minted "
        "credential carries the epoch it was minted under, and the API refuses one whose "
        "epoch is not this value. Raising it by one revokes every credential this account "
        "holds, everywhere, immediately - that is the whole mechanism, and there is no "
        "list of tokens anywhere because there does not need to be. It is never 0 and "
        "never decreases; a CHECK enforces the floor.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.token_epoch_updated_at IS "
        "'When token_epoch last moved - that is, when this account was last revoked, by a "
        "password change or by an operator. Equal to the moment the column was added until "
        "something revokes. It is separate from password_updated_at on purpose: a password "
        "change moves both, a revocation moves only this one, and reading one for the other "
        "would answer a question nobody asked.';"
    )
    _log.warning(
        "0007_credential_epoch: every credential issued before this revision is now "
        "refused, because it carries no epoch and a credential whose epoch cannot be read "
        "is not a credential. Everyone signs in again once. This is the intended effect of "
        "a change whose purpose is that a credential can be taken away."
    )


def downgrade() -> None:
    """Drop the columns, after naming every account the drop un-revokes.

    See the module docstring: this restores credentials that were deliberately revoked
    within the last token lifetime, and nothing else. It proceeds because the window is
    bounded and the operator chose it, and it says out loud what it is doing because a
    revocation silently undone is worse than one that never happened.
    """
    bind = op.get_bind()
    revoked = bind.execute(
        text(
            "SELECT login, token_epoch FROM app_user "
            "WHERE token_epoch > :initial ORDER BY login"
        ),
        {"initial": INITIAL_EPOCH},
    ).all()
    if revoked:
        _log.warning(
            "0007_credential_epoch downgrade: %d account(s) have been revoked at least "
            "once (%s). Dropping token_epoch restores any credential of theirs that was "
            "revoked within the last token lifetime and has not expired on its own. "
            "Revoke again after downgrading if that window matters.",
            len(revoked),
            ", ".join(f"{login} (epoch {epoch})" for login, epoch in revoked),
        )
    op.execute("ALTER TABLE app_user DROP CONSTRAINT ck_app_user_token_epoch;")
    op.execute(
        "ALTER TABLE app_user "
        "DROP COLUMN token_epoch_updated_at, "
        "DROP COLUMN token_epoch;"
    )
