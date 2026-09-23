"""The only reader and writer of ``app_user``.

Shaped like the rest of the tree: explicit statements, no base repository, no generic
CRUD, and the :class:`~sqlalchemy.orm.Session` passed in by the caller rather than owned
here (``docs/program/P02_SEAMS.md`` section 3.5, and
:mod:`auditmanager.documents.repository` for the same decision written out).

Three properties are specific to this table.

**The credential columns are read in exactly two places, and both are named.**
``_SELECT_CREDENTIAL`` and ``_SELECT_CREDENTIAL_BY_UID`` are the only statements that
project ``password_algorithm``, ``password_iterations``, ``password_salt`` and
``password_hash``. The first serves :meth:`UserRepository.authenticate`, which is addressed
by login because that is what a sign-in form types; the second serves
:meth:`UserRepository.change_password`, which is addressed by ``user_uid`` because the
caller there has already been authenticated and holds an identity rather than a name. In
both, the value built (:class:`~auditmanager.access.passwords.StoredPassword`) is consumed
inside this module and never returned. Everything else projects ``_PUBLIC_COLUMNS``, which
does not contain them.

*This paragraph said "exactly one place" until wave 39, and the sentence was load-bearing:
it is the whole of the argument that a digest never leaves here.* Adding the second reader
without moving it would have left a true-sounding claim that no longer covered the code --
``OPERATING_CONSTRAINTS.md`` §4.7 inside the module that holds the credential, which is
exactly where the last one was found.

**Revocation is a column, and a password change is one statement.** ``token_epoch`` is the
generation of credentials the account accepts; the seam stamps it into every credential it
mints and refuses one that disagrees. :meth:`UserRepository.change_password` writes the new
digest, clears ``is_default_credential`` and raises ``token_epoch`` **in a single UPDATE**,
so there is no interleaving in which the password changed and the old credentials survived.
That is not an optimisation: a password change that leaves credentials minted under the old
password working is a password change in name only, and two statements are two chances for
only the first to land.

**Failing to find a user still costs a hash.** See
:func:`~auditmanager.access.passwords.spend_a_verification`. Without it the response
time answers "does this account exist?" for anybody with a stopwatch.

**A default credential is loud.** Every successful authentication of a user whose
``is_default_credential`` is still true logs a warning naming the login. That is the
runtime half of the visibility the seeded ``admin`` account needs; the database half is
the column itself, and ``python -m auditmanager.access.check`` reports it without
anybody having to log in. The warning is not rate-limited and not suppressible: an
operator who is tired of reading it changes the password, which is the point.
"""

from __future__ import annotations

import logging
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.models import UserRecord, UserUid, normalize_login
from auditmanager.access.passwords import (
    StoredPassword,
    hash_password,
    is_the_same_password,
    spend_a_verification,
    verify_password,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["CREDENTIALS_REVOKED", "DEFAULT_CREDENTIAL_WARNING", "UserRepository"]

_log = logging.getLogger(__name__)

#: PostgreSQL's unique-violation SQLSTATE. Matched on the code, never on the message
#: text: a message is a diagnostic string a server upgrade or a locale may reword.
_UNIQUE_VIOLATION: Final[str] = "23505"

#: The prefix of the warning emitted when a default credential is used. Named here so a
#: test and a log-scraping operator can both match on something stable.
DEFAULT_CREDENTIAL_WARNING: Final[str] = "default credential in use"

#: The prefix of the warning emitted whenever an account's credentials are revoked, by a
#: password change or by an operator. Stable text, for the same two readers.
#:
#: It is a warning and not an info line on purpose. Revocation is rare, it is irreversible
#: for everyone holding a credential at that moment, and the one question an operator asks
#: afterwards -- "when did this happen, and to whom?" -- must be answerable from the
#: deployment log as well as from ``token_epoch_updated_at``.
CREDENTIALS_REVOKED: Final[str] = "credentials revoked"

#: Everything a caller may see. The four credential columns are absent by construction.
#:
#: ``token_epoch`` is here and not beside the digest: it is not credential material. It is
#: a counter the seam stamps into every credential it mints, so it travels on purpose, and
#: putting it behind the credential statement would mean the one value every request must
#: check could only be read by the one query that also reads the hash.
_PUBLIC_COLUMNS: Final[str] = (
    "user_uid, login, is_default_credential, created_at, password_updated_at, "
    "token_epoch, token_epoch_updated_at"
)

_INSERT_USER = text(
    f"""
    INSERT INTO app_user (
        user_uid, login, password_algorithm, password_iterations,
        password_salt, password_hash, is_default_credential
    ) VALUES (
        :user_uid, :login, :algorithm, :iterations,
        :salt, :digest, :is_default_credential
    )
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_SELECT_BY_LOGIN = text(f"SELECT {_PUBLIC_COLUMNS} FROM app_user WHERE login = :login")

#: One of the two statements in this package that read credential material. Addressed by
#: login, because a sign-in form types a name and not an identity.
_SELECT_CREDENTIAL = text(
    "SELECT password_algorithm, password_iterations, password_salt, password_hash "
    "FROM app_user WHERE login = :login"
)

#: The other. Addressed by ``user_uid``, because its caller has already been authenticated
#: and holds the identity the seam published -- and because a login can be renamed while an
#: identity cannot, so a password change addressed by name could in principle be applied to
#: a different account than the one that proved itself.
_SELECT_CREDENTIAL_BY_UID = text(
    "SELECT password_algorithm, password_iterations, password_salt, password_hash "
    "FROM app_user WHERE user_uid = :user_uid"
)

#: The new digest, the cleared default flag and the raised epoch, in one statement. See the
#: module docstring for why it is one and not three.
_CHANGE_PASSWORD = text(
    f"""
    UPDATE app_user SET
        password_algorithm = :algorithm,
        password_iterations = :iterations,
        password_salt = :salt,
        password_hash = :digest,
        password_updated_at = now(),
        is_default_credential = false,
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now()
    WHERE user_uid = :user_uid
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Revocation, for one account. ``token_epoch + 1`` is computed by the database rather than
#: read and written back: two operators revoking at once must produce two increments, and a
#: read-modify-write in this process would let one overwrite the other with the same value
#: -- which reads as a successful revocation and is not one.
_REVOKE_ONE = text(
    f"""
    UPDATE app_user SET
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now()
    WHERE login = :login
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Revocation, for every account. "The pilot has ended" is one statement.
_REVOKE_EVERY = text(
    f"""
    UPDATE app_user SET
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now()
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: The epoch check the seam runs on every authorized request. A primary-key lookup
#: projecting one integer, and deliberately nothing else: this runs on every request on the
#: surface, and a statement that also returned a login would invite a caller to read
#: identity out of the credential check.
_SELECT_TOKEN_EPOCH = text("SELECT token_epoch FROM app_user WHERE user_uid = :user_uid")

_SELECT_DEFAULT_CREDENTIALS = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user "
    "WHERE is_default_credential IS TRUE ORDER BY login"
)


def _record(row: object) -> UserRecord:
    (
        user_uid,
        login,
        is_default_credential,
        created_at,
        password_updated_at,
        token_epoch,
        token_epoch_updated_at,
    ) = row  # type: ignore[misc]
    return UserRecord(
        user_uid=UserUid.parse(user_uid),
        login=login,
        is_default_credential=bool(is_default_credential),
        created_at=created_at,
        password_updated_at=password_updated_at,
        token_epoch=int(token_epoch),
        token_epoch_updated_at=token_epoch_updated_at,
    )


class UserRepository:
    """Find a user, prove a password, create a user, change a password, revoke credentials.

    Conforms to :class:`auditmanager.access.ports.UserRepository`.
    """

    __slots__ = ()

    def find_by_login(self, session: Session, login: str) -> UserRecord | None:
        """The user with this login, or ``None``.

        A malformed login raises rather than returning ``None``: "this is not a login"
        and "no such user" are different facts, and collapsing them would make a typo in
        a caller look like a missing account.
        """
        row = session.execute(_SELECT_BY_LOGIN, {"login": normalize_login(login)}).first()
        return None if row is None else _record(row)

    def authenticate(self, session: Session, login: str, password: str) -> UserRecord | None:
        """The user when the password is theirs, ``None`` in every other case.

        ``None`` covers an unknown login, a wrong password and a login this boundary
        would never have stored. The three are deliberately indistinguishable to the
        caller and cost comparable time.
        """
        try:
            normalized = normalize_login(login)
        except DomainError:
            # A login that could not have been stored still costs a derivation: a cheap
            # refusal here would tell a prober which shapes exist in the table.
            spend_a_verification(password)
            return None

        credential = session.execute(_SELECT_CREDENTIAL, {"login": normalized}).first()
        if credential is None:
            spend_a_verification(password)
            return None

        algorithm, iterations, salt, digest = credential
        stored = StoredPassword(
            algorithm=algorithm,
            iterations=int(iterations),
            salt=salt,
            digest=digest,
        )
        try:
            matched = verify_password(stored, password)
        except DomainError as exc:
            if exc.code is ErrorCode.VALIDATION_FAILED:
                # An empty or over-long candidate is a failed attempt, not a server
                # fault. An unsupported algorithm or a corrupt column is neither, and
                # propagates: reporting it as a wrong password would hide a real defect
                # behind a plausible one.
                return None
            raise
        if not matched:
            return None

        row = session.execute(_SELECT_BY_LOGIN, {"login": normalized}).first()
        if row is None:  # pragma: no cover - the row was read microseconds ago
            return None
        record = _record(row)
        if record.is_default_credential:
            _log.warning(
                "%s: user %r signed in with the password this system was seeded with. "
                "Change it; until then anyone who has read the deployment notes can "
                "sign in as this user.",
                DEFAULT_CREDENTIAL_WARNING,
                record.login,
            )
        return record

    def create_user(
        self,
        session: Session,
        login: str,
        password: str,
        *,
        is_default_credential: bool = False,
    ) -> UserRecord:
        """Create a user and return them. The digest is written and forgotten.

        ``is_default_credential`` exists so the one account that *is* seeded with a
        known password can say so in its own row. It defaults to false, so an ordinary
        creation cannot set the flag by omission.
        """
        normalized = normalize_login(login)
        stored = hash_password(password)
        try:
            row = session.execute(
                _INSERT_USER,
                {
                    "user_uid": str(UserUid.new()),
                    "login": normalized,
                    "algorithm": stored.algorithm,
                    "iterations": stored.iterations,
                    "salt": stored.salt,
                    "digest": stored.digest,
                    "is_default_credential": is_default_credential,
                },
            ).one()
        except DBAPIError as exc:
            sqlstate = str(getattr(exc.orig, "sqlstate", "") or "")
            if sqlstate == _UNIQUE_VIOLATION:
                raise DomainError(
                    ErrorCode.CONFLICT,
                    message="a user with this login already exists",
                ) from exc
            raise
        return _record(row)

    def change_password(
        self,
        session: Session,
        *,
        user_uid: str,
        current_password: str,
        new_password: str,
    ) -> UserRecord | None:
        """Replace this account's password, and revoke every credential minted under the old one.

        ``None`` when the current password is not this account's, and when there is no such
        account. One answer for both, for the same reason :meth:`authenticate` gives one:
        the caller holding a credential for a deleted account learns nothing from being told
        which it was.

        **The order of the four steps is the security property, not house style.**

        1. the current password is proved first, so nothing about the *new* one -- not even
           that it was malformed -- is reported to somebody who has not shown they may
           change it;
        2. the new password is refused when it is the current one, because an operation
           called "change password" that changes nothing would tell a reviewer their
           password had changed when it had not;
        3. the new digest is derived, which is where the mechanical bounds in
           :mod:`~auditmanager.access.passwords` apply and raise;
        4. one UPDATE writes the digest, clears ``is_default_credential`` and raises
           ``token_epoch``.

        The returned record carries the **new** epoch, so the caller can mint a credential
        that the very next request will accept. A caller that minted before reading it would
        mint under the old epoch and hand out a credential already dead on arrival.
        """
        credential = session.execute(
            _SELECT_CREDENTIAL_BY_UID, {"user_uid": user_uid}
        ).first()
        if credential is None:
            # The same derivation an unknown login costs in `authenticate`. The caller here
            # already holds a credential, so this is not an enumeration oracle in the same
            # sense -- but the two paths through this method should still cost the same,
            # and a cheap refusal would say "that account is gone" in the timing.
            spend_a_verification(current_password)
            return None

        algorithm, iterations, salt, digest = credential
        stored = StoredPassword(
            algorithm=algorithm,
            iterations=int(iterations),
            salt=salt,
            digest=digest,
        )
        try:
            matched = verify_password(stored, current_password)
        except DomainError as exc:
            if exc.code is ErrorCode.VALIDATION_FAILED:
                # An empty or over-long *current* password is a failed attempt, exactly as
                # in `authenticate`. Anything else -- an unreadable stored credential -- is
                # a real fault and propagates rather than being reported as a wrong password.
                return None
            raise
        if not matched:
            return None

        if is_the_same_password(current_password, new_password):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "the new password must differ from the current one; a password change "
                    "that changes nothing is not a password change"
                ),
            )

        # Raises `VALIDATION_FAILED` for an empty or over-long new password, before any
        # write. Nothing has been changed at this point, so a refusal here leaves the
        # account exactly as it was.
        replacement = hash_password(new_password)

        row = session.execute(
            _CHANGE_PASSWORD,
            {
                "user_uid": user_uid,
                "algorithm": replacement.algorithm,
                "iterations": replacement.iterations,
                "salt": replacement.salt,
                "digest": replacement.digest,
            },
        ).first()
        if row is None:  # pragma: no cover - the row was read microseconds ago
            return None
        record = _record(row)
        _log.warning(
            "%s: user %r changed their password; every credential minted for them before "
            "this moment is refused from now on (token_epoch is now %d).",
            CREDENTIALS_REVOKED,
            record.login,
            record.token_epoch,
        )
        return record

    def revoke_credentials(
        self, session: Session, *, login: str | None = None
    ) -> tuple[UserRecord, ...]:
        """Raise the credential epoch, for one account or for every account.

        ``login=None`` means **every** account, and it is spelled as an explicit default
        rather than as an overload, because the two are one statement apart and the caller
        must say which it meant. The operator entry point
        (:mod:`auditmanager.access.revoke`) refuses to run without one of the two, so
        "revoke" typed with no argument does nothing rather than revoking the installation.

        The returned records carry the **new** epochs. An empty tuple means nothing matched
        -- an unknown login, or an empty table -- and is not an error: the caller decides
        whether "nothing to revoke" is a problem, and the CLI reports it as one.
        """
        if login is None:
            rows = session.execute(_REVOKE_EVERY).all()
        else:
            rows = session.execute(_REVOKE_ONE, {"login": normalize_login(login)}).all()
        records = tuple(sorted((_record(row) for row in rows), key=lambda r: r.login))
        for record in records:
            _log.warning(
                "%s: every credential held by %r is refused from now on "
                "(token_epoch is now %d).",
                CREDENTIALS_REVOKED,
                record.login,
                record.token_epoch,
            )
        return records

    def token_epoch(self, session: Session, user_uid: str) -> int | None:
        """The generation of credentials this account currently accepts, or ``None``.

        ``None`` means there is no such account, and the seam treats it as a refusal -- so
        deleting a row revokes that account's credentials for free, which is the answer to
        "what happens to the credential of an account that no longer exists". Before this
        column it kept working until it expired.

        This is the statement that runs on **every** authorized request. It is a primary-key
        lookup returning one integer, and it is deliberately not cached: a cache would give
        revocation a delay, and a revocation that takes effect in a little while is the
        thing this whole mechanism exists to replace.
        """
        row = session.execute(_SELECT_TOKEN_EPOCH, {"user_uid": user_uid}).first()
        return None if row is None else int(row[0])

    def users_on_default_credentials(self, session: Session) -> tuple[UserRecord, ...]:
        """Every user whose password is still the one the system seeded them with.

        The state this reports is meant to be temporary. It is a query rather than a
        boolean so the answer names the accounts, and reading it costs no login.
        """
        rows = session.execute(_SELECT_DEFAULT_CREDENTIALS).all()
        return tuple(_record(row) for row in rows)
