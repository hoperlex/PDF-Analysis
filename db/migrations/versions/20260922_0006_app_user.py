"""Users as data: the ``app_user`` table, and one seeded account that says so out loud.

Revision ID: 0006_app_user
Revises: 0005_truncated_call_status

Until now a user was an environment variable. The legacy portal read
``PORTAL_AUTH_USERS='login:hash'`` -- a single string, with a commented-out example and
no account in it -- which means there is no user data to migrate and nothing to import.
What survives from the legacy system is one decision, and it is a good one: the hashes
were ``pbkdf2_sha256``. This revision keeps the algorithm and drops the transport.

Why a table rather than a variable
----------------------------------
A credential in the environment cannot be created, changed or revoked without a
redeploy, cannot record when it was last changed, and is readable by every process in
the container and by anything that dumps the environment into a crash report. A row can
be written by the application, carries its own timestamps, and is covered by whatever
backup policy the database has.

The credential columns, and why there are four of them
------------------------------------------------------
``password_algorithm``, ``password_iterations``, ``password_salt`` and ``password_hash``
are separate columns rather than one encoded ``algorithm$iterations$salt$hash`` string.
The parameters are then *queryable*: "which accounts were hashed below the iteration
count we use today" is one SELECT, and the answer is what a rehash campaign works from.
An encoded string would need a parser, and a parser is a thing that can disagree with
the writer.

No column here is named ``password``, ``secret`` or ``credential``, which
``tests/integration/db/test_schema_shape.py`` bans outright. That ban is about storing a
secret; a salted PBKDF2 digest at 600_000 iterations is not one, and the test's own list
is matched on exact names. A user's plaintext password is never written anywhere: it
exists inside one derivation call and is carried into no column, no log line and no error
message. The one string that *is* printed is the seeded default below, which is a
published constant of this revision rather than anybody's secret, and printing it is the
whole point of printing it.

The seeded account
------------------
``admin`` / ``password``, by an explicit owner decision, for a short window: registration
and password change are the next piece of work. There is no feature flag and no
environment marker around it -- the owner removed those -- but the state is made
**visible** in three ways that do not depend on anybody remembering it:

1. ``app_user.is_default_credential`` is ``true`` on that row, so the condition is a
   query rather than a piece of folklore: ``SELECT login FROM app_user WHERE
   is_default_credential``.
2. This migration logs a warning while it runs, so the deployment log of every
   installation contains the sentence.
3. At runtime, every sign-in with such an account logs a warning, and
   ``python -m auditmanager.access.check`` reports the accounts without logging in.

Whoever changes that password clears the flag in the same statement; the column is the
record of "still the seeded password", not of "was seeded once".

**The hash is computed here rather than imported.** The iteration count and the
derivation below are written out, so this revision reproduces from an empty database
without ``auditmanager.access`` existing at all, and re-reading it tells you exactly what
was written. It cannot drift from the verifier either: verification reads the algorithm,
the iteration count and the salt *from the row*, so a later change to the application's
default cost leaves this row verifiable.
``tests/integration/db/test_app_user_migration.py`` asserts that the seeded row verifies
against :func:`auditmanager.access.passwords.verify_password` with the literal password,
which is the claim that matters and the one that would catch a divergence.

Downgrade
---------
Dropping this table destroys password data that cannot be recovered from anywhere else,
which is exactly the shape ``0004``'s downgrade refuses. So the downgrade is conditional:
it drops the table when it holds nothing but the untouched seeded account, and refuses
when it holds a real one. The information genuinely cannot survive the drop, so the
honest behaviour is to stop and make an operator decide.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

from auditmanager.shared.identity.ulid import new_ulid

revision: str = "0006_app_user"
down_revision: str | None = "0005_truncated_call_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Named ``alembic.*`` so it inherits the runner's configured handler and reaches the
#: deployment log rather than a logger nobody attached anything to.
_log = logging.getLogger("alembic.migration.app_user")

#: The seeded account. Both halves are literals here because both are facts about what
#: this revision writes, and a reader of the migration should not have to look anywhere
#: else to learn that the password is `password`.
SEED_LOGIN = "admin"
SEED_PASSWORD = "password"  # noqa: S105 - the owner's deliberate default; see the docstring

#: What a hash written by this revision costs. OWASP's 2023 figure for
#: PBKDF2-HMAC-SHA256. It is written into the row, so verification never assumes it.
SEED_ITERATIONS = 600_000

_SALT_BYTES = 16
_DERIVED_KEY_BYTES = 32


def _seed_credential() -> dict[str, str | int]:
    """Derive the seeded account's stored credential, with a fresh random salt.

    Random rather than fixed: two installations that both run this revision must not end
    up with the same digest, or one dumped database would publish the digest of every
    other installation's admin account. The password is public knowledge already; the
    salt is what keeps that from being a single precomputed value.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        SEED_PASSWORD.encode("utf-8"),
        salt,
        SEED_ITERATIONS,
        dklen=_DERIVED_KEY_BYTES,
    )
    return {
        "user_uid": f"usr_{new_ulid()}",
        "login": SEED_LOGIN,
        "algorithm": "pbkdf2_sha256",
        "iterations": SEED_ITERATIONS,
        "salt": salt.hex(),
        "digest": digest.hex(),
    }


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app_user (
            user_uid              text PRIMARY KEY,
            login                 text NOT NULL,
            password_algorithm    text NOT NULL,
            password_iterations   integer NOT NULL,
            password_salt         text NOT NULL,
            password_hash         text NOT NULL,
            is_default_credential boolean NOT NULL DEFAULT false,
            created_at            timestamptz NOT NULL DEFAULT now(),
            password_updated_at   timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_app_user_login UNIQUE (login),
            CONSTRAINT ck_app_user_user_uid_format
                CHECK (user_uid ~ '^usr_[0-9A-HJKMNP-TV-Z]{26}$'),
            -- The login is stored already folded. Enforced here as well as in the
            -- boundary so raw SQL cannot create `Admin` beside `admin` and make the
            -- UNIQUE constraint meaningless.
            CONSTRAINT ck_app_user_login_format
                CHECK (login ~ '^[a-z0-9][a-z0-9._-]{0,99}$'),
            CONSTRAINT ck_app_user_password_algorithm
                CHECK (password_algorithm = 'pbkdf2_sha256'),
            -- A cost that is not a cost is the failure mode this catches: a row written
            -- with 1 iteration verifies perfectly and protects nothing.
            CONSTRAINT ck_app_user_password_iterations
                CHECK (password_iterations >= 100000),
            CONSTRAINT ck_app_user_password_salt_format
                CHECK (password_salt ~ '^[0-9a-f]{32}$'),
            CONSTRAINT ck_app_user_password_hash_format
                CHECK (password_hash ~ '^[0-9a-f]{64}$')
        );
        """
    )
    op.execute(
        "COMMENT ON TABLE app_user IS "
        "'One account that can sign in. Identity only: this table carries no role, no "
        "permission and no session - those arrive with the work on users and rights "
        "that follows the alpha. The password is stored as a salted PBKDF2-HMAC-SHA256 "
        "digest with its parameters in their own columns; no plaintext password is "
        "written here or anywhere else.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.login IS "
        "'The name typed at the sign-in form, stored already lower-cased and stripped. "
        "It is UNIQUE and it is a natural key for lookup, but it is NOT the identity: "
        "user_uid is, and a login that is renamed later must not take the identity with "
        "it.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.password_iterations IS "
        "'The PBKDF2 iteration count THIS row was written with. Verification uses this "
        "value, never the application constant, so raising the constant later does not "
        "lock anybody out - it only means rows below it want rehashing on next sign-in.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.password_hash IS "
        "'A salted PBKDF2-HMAC-SHA256 derived key, hex. Not reversible and not a "
        "password-equivalent token: it is useless against this system without the "
        "plaintext, because the server always derives from what was typed. Compared "
        "with a constant-time comparison; never with =.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.is_default_credential IS "
        "'TRUE while this account still holds the password the system seeded it with, "
        "which anyone reading the deployment notes knows. It is a WARNING FLAG, not a "
        "role: the account is fully privileged in every other respect. Whoever changes "
        "the password sets this to false in the same statement. SELECT login FROM "
        "app_user WHERE is_default_credential is the query that answers whether this "
        "installation is still shipping with a known password.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.password_updated_at IS "
        "'When the stored digest was last written. Equal to created_at until somebody "
        "changes the password; that is how long a default credential has been live.';"
    )

    _insert_seed()

    _log.warning(
        "0006_app_user seeded the account %r with the DEFAULT PASSWORD %r. "
        "Anyone who can reach this installation and has read the deployment notes can "
        "sign in as it. The row is flagged: SELECT login FROM app_user WHERE "
        "is_default_credential. Change the password, or run "
        "`PYTHONPATH=src python -m auditmanager.access.check` to see it is still there.",
        SEED_LOGIN,
        SEED_PASSWORD,
    )


def _insert_seed() -> None:
    """Insert the seeded account, with its parameters bound rather than interpolated."""
    op.get_bind().execute(
        text(
            "INSERT INTO app_user ("
            "  user_uid, login, password_algorithm, password_iterations,"
            "  password_salt, password_hash, is_default_credential"
            ") VALUES ("
            "  :user_uid, :login, :algorithm, :iterations, :salt, :digest, true"
            ")"
        ),
        _seed_credential(),
    )


def downgrade() -> None:
    """Drop the table only when nothing but the untouched seed would be lost.

    A real account's digest exists in this table and nowhere else. Dropping it is not a
    reversible schema change, it is deletion of the only copy, and a downgrade that did
    it quietly would be the same silent loss ``0004`` refuses.
    """
    bind = op.get_bind()
    survivors = bind.execute(
        text(
            "SELECT count(*) FROM app_user "
            "WHERE is_default_credential IS NOT TRUE OR login <> :seed"
        ),
        {"seed": SEED_LOGIN},
    ).scalar_one()
    if survivors:
        raise RuntimeError(
            f"refusing to downgrade 0006_app_user: app_user holds {survivors} account(s) "
            "that are not the untouched seeded one. Their password digests exist in this "
            "table and nowhere else, so dropping it deletes the only copy. Remove or "
            "export them deliberately first, then re-run this downgrade."
        )
    op.execute("DROP TABLE app_user;")
