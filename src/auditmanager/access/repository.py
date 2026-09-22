"""The only reader and writer of ``app_user``.

Shaped like the rest of the tree: explicit statements, no base repository, no generic
CRUD, and the :class:`~sqlalchemy.orm.Session` passed in by the caller rather than owned
here (``docs/program/P02_SEAMS.md`` section 3.5, and
:mod:`auditmanager.documents.repository` for the same decision written out).

Three properties are specific to this table.

**The credential columns are read in exactly one place.** ``_SELECT_CREDENTIAL`` is the
only statement that projects ``password_algorithm``, ``password_iterations``,
``password_salt`` and ``password_hash``, and the value it builds
(:class:`~auditmanager.access.passwords.StoredPassword`) is consumed inside
:meth:`UserRepository.authenticate` and never returned. Everything else in this module
projects ``_PUBLIC_COLUMNS``, which does not contain them. So "a digest never leaves the
repository" is checkable by reading the four statements below.

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
    spend_a_verification,
    verify_password,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEFAULT_CREDENTIAL_WARNING", "UserRepository"]

_log = logging.getLogger(__name__)

#: PostgreSQL's unique-violation SQLSTATE. Matched on the code, never on the message
#: text: a message is a diagnostic string a server upgrade or a locale may reword.
_UNIQUE_VIOLATION: Final[str] = "23505"

#: The prefix of the warning emitted when a default credential is used. Named here so a
#: test and a log-scraping operator can both match on something stable.
DEFAULT_CREDENTIAL_WARNING: Final[str] = "default credential in use"

#: Everything a caller may see. The four credential columns are absent by construction.
_PUBLIC_COLUMNS: Final[str] = (
    "user_uid, login, is_default_credential, created_at, password_updated_at"
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

#: The one statement in this package that reads credential material.
_SELECT_CREDENTIAL = text(
    "SELECT password_algorithm, password_iterations, password_salt, password_hash "
    "FROM app_user WHERE login = :login"
)

_SELECT_DEFAULT_CREDENTIALS = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user "
    "WHERE is_default_credential IS TRUE ORDER BY login"
)


def _record(row: object) -> UserRecord:
    user_uid, login, is_default_credential, created_at, password_updated_at = row  # type: ignore[misc]
    return UserRecord(
        user_uid=UserUid.parse(user_uid),
        login=login,
        is_default_credential=bool(is_default_credential),
        created_at=created_at,
        password_updated_at=password_updated_at,
    )


class UserRepository:
    """Find a user, prove a password, create a user.

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

    def users_on_default_credentials(self, session: Session) -> tuple[UserRecord, ...]:
        """Every user whose password is still the one the system seeded them with.

        The state this reports is meant to be temporary. It is a query rather than a
        boolean so the answer names the accounts, and reading it costs no login.
        """
        rows = session.execute(_SELECT_DEFAULT_CREDENTIALS).all()
        return tuple(_record(row) for row in rows)
