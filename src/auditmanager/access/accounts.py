"""Accounts as an administrator and the account itself manage them (`W49-PLAN.md` §3.1-§3.2).

:mod:`auditmanager.access.repository` is the sign-in half of ``app_user``: find, prove a
password, change it, revoke, brake. This module is the management half that `W49` adds --
the profile, the role set, archive, restore, purge and the administrator's password reset
-- and it is a separate class for the reason the sign-in half keeps its operator views off
its port: the API's credential adapter reaches the sign-in half on every request and must
not be able to reach these.

Shaped like the rest of the tree: explicit statements, the caller's
:class:`~sqlalchemy.orm.Session`, no generic CRUD. **Every invariant of §3.2 is enforced
here, not in a router**, and is proven by tests that never build an application:

* an account cannot archive, purge, demote or reset itself;
* the last active account holding ``admin`` cannot be archived or lose ``admin``;
* approval grants at least one role (:mod:`auditmanager.access.registrations`).

**Every change to who an account is raises its ``token_epoch`` in the same transaction** --
a role change, an archive, a restore, an administrator's reset -- so each credential that
account holds answers ``authentication_required`` on its next request and the account meets
its new rights only after signing in again. A purge needs no bump: the row is gone, and a
credential for a row that is gone has no standing.

**Concurrency.** The last-administrator rule is a statement about a set, so it is decided
under a lock on that set: every operation that can remove an administrator first locks the
rows of all active administrators, in ``user_uid`` order, and only then the target. Two
administrators archiving each other at the same instant therefore serialise, and the second
sees the first's result -- the count is never read from a snapshot the other transaction is
about to make false. The fixed order is what keeps two such transactions from deadlocking.
"""

from __future__ import annotations

import logging
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.models import (
    UserRecord,
    is_email_login,
    normalize_email,
    normalize_person_name,
    parse_role,
)
from auditmanager.access.repository import _PUBLIC_COLUMNS, _record
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "PROFILE_COMPLETED",
    "ROLES_CHANGED",
    "AccountRepository",
]

_log = logging.getLogger(__name__)

#: PostgreSQL's unique-violation SQLSTATE, matched on the code and never on the message.
_UNIQUE_VIOLATION: Final[str] = "23505"

#: Stable prefixes for the deployment log, as :mod:`auditmanager.access.repository` names its own.
PROFILE_COMPLETED: Final[str] = "profile completed"
ROLES_CHANGED: Final[str] = "roles changed"

_SELECT_BY_UID_FOR_UPDATE = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user WHERE user_uid = :user_uid FOR UPDATE"
)

_SELECT_ROLES = text(
    "SELECT role FROM app_user_role WHERE user_uid = :user_uid ORDER BY role"
)

#: Profile completion, `R-59`: the names, the login and the timestamp in **one UPDATE**,
#: so there is no instant at which an account has an e-mail login and no names, or names
#: and the legacy login, and the CHECKs of ``0015`` see the finished row.
_COMPLETE_PROFILE = text(
    f"""
    UPDATE app_user SET
        login = :login,
        last_name = :last_name,
        first_name = :first_name,
        middle_name = :middle_name,
        profile_completed_at = now()
    WHERE user_uid = :user_uid AND archived_at IS NULL AND profile_completed_at IS NULL
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_INSERT_ROLE = text(
    "INSERT INTO app_user_role (user_uid, role, granted_by) "
    "VALUES (:user_uid, :role, :granted_by) "
    "ON CONFLICT (user_uid, role) DO NOTHING RETURNING role"
)

#: The epoch bump every change of rights carries. Computed by the database, so two
#: concurrent changes produce two increments (see ``_REVOKE_ONE`` in the sign-in half).
_BUMP_EPOCH = text(
    "UPDATE app_user SET token_epoch = token_epoch + 1, token_epoch_updated_at = now() "
    "WHERE user_uid = :user_uid"
)


def _unique_violation(exc: DBAPIError) -> bool:
    return str(getattr(exc.orig, "sqlstate", "") or "") == _UNIQUE_VIOLATION


def login_taken() -> DomainError:
    """`conflict` with ``conflict_reason: login_taken`` (`W49-PLAN.md` §3.3)."""
    return DomainError(
        ErrorCode.CONFLICT,
        message="an active account already holds this login",
        conflict_reason="login_taken",
    )


class AccountRepository:
    """Profile, roles, archive, restore, purge and reset for ``app_user``."""

    __slots__ = ()

    # -- reads -------------------------------------------------------------------------

    def roles_of(self, session: Session, user_uid: str) -> frozenset[str]:
        """The role set this account holds. Empty is a valid answer, never a refusal."""
        rows = session.execute(_SELECT_ROLES, {"user_uid": user_uid}).scalars().all()
        return frozenset(parse_role(role) for role in rows)

    def _lock(self, session: Session, user_uid: str) -> UserRecord | None:
        row = session.execute(_SELECT_BY_UID_FOR_UPDATE, {"user_uid": user_uid}).first()
        return None if row is None else _record(row)

    # -- the profile ---------------------------------------------------------------------

    def complete_profile(
        self,
        session: Session,
        *,
        user_uid: str,
        email: str | None,
        last_name: str,
        first_name: str,
        middle_name: str | None = None,
    ) -> UserRecord:
        """Complete a legacy profile in one UPDATE (`R-59`) and return the record.

        ``email`` becomes the login. It may be omitted only when the login already is an
        e-mail. Refusals: ``validation_failed`` for a name or an e-mail the rules refuse, or
        a missing e-mail on a legacy login; ``not_found`` for no such active account;
        ``state_transition_not_allowed`` when the profile is already complete (the login is
        writable only while it is not); ``conflict`` with ``conflict_reason: login_taken``
        when another active account holds that e-mail.
        """
        last = normalize_person_name(last_name, field="last_name", required=True)
        first = normalize_person_name(first_name, field="first_name", required=True)
        middle = normalize_person_name(middle_name, field="middle_name", required=False)

        current = self._lock(session, user_uid)
        if current is None or current.archived:
            raise DomainError(ErrorCode.NOT_FOUND, message="no such active account")
        if current.profile_complete:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="this profile is already complete; its login is fixed",
                field="login",
            )
        if email is None:
            if not is_email_login(current.login):
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED,
                    message="a legacy login is completed with an e-mail address",
                    field="email",
                )
            login = current.login
        else:
            login = normalize_email(email)

        try:
            with session.begin_nested():
                row = session.execute(
                    _COMPLETE_PROFILE,
                    {
                        "user_uid": user_uid,
                        "login": login,
                        "last_name": last,
                        "first_name": first,
                        "middle_name": middle,
                    },
                ).one()
        except DBAPIError as exc:
            if _unique_violation(exc):
                raise login_taken() from exc
            raise
        record = _record(row)
        _log.warning(
            "%s: %s (was %r) is now %r, shown as %r.",
            PROFILE_COMPLETED,
            record.user_uid,
            current.login,
            record.login,
            record.display_label,
        )
        return record

    # -- roles ---------------------------------------------------------------------------

    def grant_role(
        self,
        session: Session,
        *,
        user_uid: str,
        role: str,
        granted_by: str | None,
    ) -> bool:
        """Add ``role`` to the account's set; ``True`` when the set changed.

        ``granted_by`` is the administrator's identity, or ``None`` for the operator's
        command (:mod:`auditmanager.access.grant`). A change raises ``token_epoch`` in the
        same transaction; a grant of a role already held changes nothing and bumps nothing.
        """
        role = parse_role(role)
        current = self._lock(session, user_uid)
        if current is None or current.archived:
            raise DomainError(ErrorCode.NOT_FOUND, message="no such active account")
        inserted = session.execute(
            _INSERT_ROLE,
            {"user_uid": user_uid, "role": role, "granted_by": granted_by},
        ).first()
        if inserted is None:
            return False
        session.execute(_BUMP_EPOCH, {"user_uid": user_uid})
        _log.warning(
            "%s: %s (%r) now holds %r; every credential it held is refused from now on.",
            ROLES_CHANGED,
            user_uid,
            current.login,
            role,
        )
        return True
