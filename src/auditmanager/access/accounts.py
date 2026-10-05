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
    ROLE_ADMIN,
    Account,
    AccountStanding,
    UserRecord,
    is_email_login,
    normalize_email,
    normalize_person_name,
    parse_role,
)
from auditmanager.access.passwords import hash_password
from auditmanager.access.policy import enforce_password_policy
from auditmanager.access.references import restricting_references
from auditmanager.access.repository import _PUBLIC_COLUMNS, _record
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ACCOUNT_ARCHIVED",
    "ACCOUNT_PURGED",
    "ACCOUNT_RESTORED",
    "LAST_ADMIN",
    "PASSWORD_RESET",
    "PROFILE_COMPLETED",
    "ROLES_CHANGED",
    "SELF_ACTION",
    "AccountInvariantViolation",
    "AccountRepository",
    "account_referenced",
    "login_taken",
]

_log = logging.getLogger(__name__)

#: PostgreSQL's unique-violation SQLSTATE, matched on the code and never on the message.
_UNIQUE_VIOLATION: Final[str] = "23505"

#: PostgreSQL's foreign-key-violation SQLSTATE: a RESTRICT reference refused a DELETE.
_FOREIGN_KEY_VIOLATION: Final[str] = "23503"

#: Stable prefixes for the deployment log, as :mod:`auditmanager.access.repository` names its own.
PROFILE_COMPLETED: Final[str] = "profile completed"
ROLES_CHANGED: Final[str] = "roles changed"
ACCOUNT_ARCHIVED: Final[str] = "account archived"
ACCOUNT_RESTORED: Final[str] = "account restored"
ACCOUNT_PURGED: Final[str] = "account purged"
PASSWORD_RESET: Final[str] = "password reset by an administrator"

#: The two invariants of `W49-PLAN.md` §3.2 that are not a state machine's transition.
SELF_ACTION: Final[str] = "self_action"
LAST_ADMIN: Final[str] = "last_admin"


class AccountInvariantViolation(DomainError):
    """A §3.2 invariant refused the change; ``invariant`` says which.

    * :data:`SELF_ACTION` -- an account may not archive, purge, demote or reset itself:
      ``permission_denied``. The subject is authenticated and may hold ``admin``; it is
      refused *this operation on this resource*, which is that code's definition.
    * :data:`LAST_ADMIN` -- the last active account holding ``admin`` may not be archived
      or lose ``admin``: ``conflict`` (an invariant would be violated).

    Neither carries a detail key: the catalog's closed ``conflict_reason`` set of
    `W49-PLAN.md` §3.3 has no member for either, and inventing one is the seal's decision,
    not this boundary's. ``invariant`` is for the seal and the tests, never the wire.
    """

    __slots__ = ("invariant",)

    def __init__(self, invariant: str, *, message: str) -> None:
        code = ErrorCode.PERMISSION_DENIED if invariant == SELF_ACTION else ErrorCode.CONFLICT
        super().__init__(code, message=message)
        self.invariant = invariant

_SELECT_BY_UID_FOR_UPDATE = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user WHERE user_uid = :user_uid FOR UPDATE"
)

_SELECT_ROLES = text(
    "SELECT role FROM app_user_role WHERE user_uid = :user_uid ORDER BY role"
)

#: The account with its role set, in one statement. ``array_agg`` over a LEFT JOIN, so an
#: account with no role answers an empty set and not a missing row.
_ACCOUNTS = (
    f"SELECT {', '.join('u.' + c.strip() for c in _PUBLIC_COLUMNS.split(','))}, "
    "COALESCE(array_agg(r.role ORDER BY r.role) FILTER (WHERE r.role IS NOT NULL), "
    "ARRAY[]::text[]) "
    "FROM app_user u LEFT JOIN app_user_role r ON r.user_uid = u.user_uid "
)
_SELECT_ACCOUNT = text(_ACCOUNTS + "WHERE u.user_uid = :user_uid GROUP BY u.user_uid")
_LIST_ACCOUNTS = text(
    _ACCOUNTS
    + "WHERE (:include_archived OR u.archived_at IS NULL) "
    "GROUP BY u.user_uid ORDER BY u.login, u.user_uid"
)

#: The standing read (`W49-PLAN.md` §3.2): one primary-key lookup with its roles, run on
#: every credentialed request exactly as ``credential_standing`` is today, and never cached
#: -- a role change that took effect a little while later would be a revocation with a
#: delay. It answers for an archived account too, with ``archived`` true, so that the seam
#: and not this read decides the refusal; the refusal is ``authentication_required``.
_SELECT_STANDING = text(
    "SELECT u.token_epoch, u.is_default_credential, u.archived_at IS NOT NULL, "
    "u.profile_completed_at IS NOT NULL, "
    "COALESCE(array_agg(r.role ORDER BY r.role) FILTER (WHERE r.role IS NOT NULL), "
    "ARRAY[]::text[]) "
    "FROM app_user u LEFT JOIN app_user_role r ON r.user_uid = u.user_uid "
    "WHERE u.user_uid = :user_uid GROUP BY u.user_uid"
)

#: The serialisation point of every change that can remove an administrator: the rows of
#: all active administrators, locked in ``user_uid`` order (see the module docstring).
_LOCK_ACTIVE_ADMINS = text(
    "SELECT u.user_uid FROM app_user u "
    "JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'admin' "
    "WHERE u.archived_at IS NULL ORDER BY u.user_uid FOR UPDATE OF u"
)

#: Counted by a **fresh statement after** the lock is held, so the count sees whatever the
#: transaction that held the lock before committed -- a count taken inside the locking
#: statement could re-check the locked rows but not the role rows joined to them.
_COUNT_OTHER_ACTIVE_ADMINS = text(
    "SELECT count(*) FROM app_user u "
    "JOIN app_user_role r ON r.user_uid = u.user_uid AND r.role = 'admin' "
    "WHERE u.archived_at IS NULL AND u.user_uid <> :user_uid"
)

_UPDATE_NAMES = text(
    f"""
    UPDATE app_user SET last_name = :last_name, first_name = :first_name,
        middle_name = :middle_name
    WHERE user_uid = :user_uid
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Archive (`R-61`): the state, the administrator, and the epoch, in one UPDATE.
_ARCHIVE = text(
    f"""
    UPDATE app_user SET archived_at = now(), archived_by = :actor_uid,
        token_epoch = token_epoch + 1, token_epoch_updated_at = now()
    WHERE user_uid = :user_uid AND archived_at IS NULL
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_RESTORE = text(
    f"""
    UPDATE app_user SET archived_at = NULL, archived_by = NULL,
        token_epoch = token_epoch + 1, token_epoch_updated_at = now()
    WHERE user_uid = :user_uid AND archived_at IS NOT NULL
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_LOGIN_HELD_BY_ANOTHER_ACTIVE = text(
    "SELECT EXISTS (SELECT 1 FROM app_user WHERE login = :login "
    "AND archived_at IS NULL AND user_uid <> :user_uid)"
)

_PURGE = text("DELETE FROM app_user WHERE user_uid = :user_uid AND archived_at IS NOT NULL")

#: The administrator's reset: a temporary password, the must-change flag
#: (``is_default_credential``, `W49-PLAN.md` §3.1), a cleared brake and a raised epoch -- one
#: statement, for the reason ``change_password`` is one statement.
_RESET_PASSWORD = text(
    f"""
    UPDATE app_user SET
        password_algorithm = :algorithm, password_iterations = :iterations,
        password_salt = :salt, password_hash = :digest, password_updated_at = now(),
        is_default_credential = true,
        token_epoch = token_epoch + 1, token_epoch_updated_at = now(),
        failed_sign_ins = 0, last_failed_sign_in_at = NULL, sign_in_blocked_until = NULL
    WHERE user_uid = :user_uid AND archived_at IS NULL
    RETURNING {_PUBLIC_COLUMNS}
    """
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


def _account(row) -> Account:
    record = _record(tuple(row)[:-1])
    return Account(record=record, roles=frozenset(parse_role(role) for role in row[-1]))


def _no_such_account() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, message="no such account")


def _transition(current: str, requested: str) -> DomainError:
    """``state_transition_not_allowed`` against the ``app_user`` machine of §3.4
    (``active -> archived -> active | purged``), with its honest details."""
    return DomainError(
        ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
        message=f"an account that is {current} cannot become {requested}",
        machine="app_user",
        current_state=current,
        requested_state=requested,
    )


def account_referenced() -> DomainError:
    """`conflict` with ``conflict_reason: account_referenced`` (`R-61`)."""
    return DomainError(
        ErrorCode.CONFLICT,
        message="this account is referenced and cannot be purged; it stays archived",
        conflict_reason="account_referenced",
    )


def _refuse_self(actor_uid: str, user_uid: str, action: str) -> None:
    if actor_uid == user_uid:
        raise AccountInvariantViolation(
            SELF_ACTION, message=f"an account cannot {action} itself"
        )


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

    def get_account(self, session: Session, user_uid: str) -> Account | None:
        """The account and its roles, archived or not; ``None`` for no such account."""
        row = session.execute(_SELECT_ACCOUNT, {"user_uid": user_uid}).first()
        return None if row is None else _account(row)

    def list_accounts(
        self, session: Session, *, include_archived: bool = False
    ) -> tuple[Account, ...]:
        """Every active account, or every account, ordered by login."""
        rows = session.execute(_LIST_ACCOUNTS, {"include_archived": include_archived}).all()
        return tuple(_account(row) for row in rows)

    def account_standing(self, session: Session, user_uid: str) -> AccountStanding | None:
        """The standing the seam re-reads on every credentialed request, or ``None``.

        ``None`` means no such row -- a purged account. An archived account answers with
        ``archived=True``; the seam turns both into ``authentication_required``. A role the
        vocabulary does not know is a raise, never a dropped member (:func:`parse_role`).
        """
        row = session.execute(_SELECT_STANDING, {"user_uid": user_uid}).first()
        if row is None:
            return None
        epoch, is_default, archived, complete, roles = row
        return AccountStanding(
            token_epoch=int(epoch),
            is_default_credential=bool(is_default),
            archived=bool(archived),
            profile_complete=bool(complete),
            roles=frozenset(parse_role(role) for role in roles),
        )

    def _lock_admins_then(self, session: Session, user_uid: str) -> UserRecord | None:
        """Lock every active administrator, then the target -- always in that order."""
        session.execute(_LOCK_ACTIVE_ADMINS).all()
        return self._lock(session, user_uid)

    def _refuse_last_admin(self, session: Session, user_uid: str, action: str) -> None:
        """Refuse when ``user_uid`` holds ``admin`` and no other active account does.

        Must run after :meth:`_lock_admins_then` in the same transaction.
        """
        if ROLE_ADMIN not in self.roles_of(session, user_uid):
            return
        others = session.execute(_COUNT_OTHER_ACTIVE_ADMINS, {"user_uid": user_uid}).scalar_one()
        if int(others) == 0:
            raise AccountInvariantViolation(
                LAST_ADMIN,
                message=f"the last active administrator cannot {action}",
            )

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

    def update_my_profile(
        self,
        session: Session,
        *,
        user_uid: str,
        last_name: str,
        first_name: str,
        middle_name: str | None = None,
        email: str | None = None,
    ) -> UserRecord:
        """The account's own profile change (``updateMyProfile``, `W49-PLAN.md` §3.4).

        An **incomplete** profile is completed by :meth:`complete_profile` -- one UPDATE of
        names, login and timestamp. A **complete** one changes its names only: ``email`` may
        be omitted or repeat the current login, and anything else is ``validation_failed``
        on ``login``, because a complete profile's login is fixed (§3.1).
        """
        current = self.get_account(session, user_uid)
        if current is None or current.record.archived:
            raise _no_such_account()
        if not current.record.profile_complete:
            return self.complete_profile(
                session,
                user_uid=user_uid,
                email=email,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            )
        if email is not None and normalize_email(email) != current.record.login:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="a complete profile's login is fixed",
                field="login",
            )
        return self.update_names(
            session,
            user_uid=user_uid,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
        )

    def update_names(
        self,
        session: Session,
        *,
        user_uid: str,
        last_name: str,
        first_name: str,
        middle_name: str | None = None,
    ) -> UserRecord:
        """Change an account's names, and nothing else (``updateUser``'s names).

        Never completes a profile and never touches the login: an administrator naming a
        legacy account leaves it a legacy account until it gives its own e-mail. Not a
        revocation either -- a name is not a right.
        """
        last = normalize_person_name(last_name, field="last_name", required=True)
        first = normalize_person_name(first_name, field="first_name", required=True)
        middle = normalize_person_name(middle_name, field="middle_name", required=False)
        if self._lock(session, user_uid) is None:
            raise _no_such_account()
        row = session.execute(
            _UPDATE_NAMES,
            {"user_uid": user_uid, "last_name": last, "first_name": first, "middle_name": middle},
        ).one()
        return _record(row)

    # -- archive, restore, purge, reset ----------------------------------------------------

    def archive_account(self, session: Session, *, actor_uid: str, user_uid: str) -> UserRecord:
        """Archive ``user_uid`` on ``actor_uid``'s authority (`R-61`).

        Refusals, in order: oneself (``permission_denied``); no such account
        (``not_found``); already archived (``state_transition_not_allowed``, ``app_user``
        ``archived -> archived``); the last active administrator (``conflict``). The UPDATE
        sets the state, names the administrator and raises ``token_epoch``.
        """
        _refuse_self(actor_uid, user_uid, "archive")
        current = self._lock_admins_then(session, user_uid)
        if current is None:
            raise _no_such_account()
        if current.archived:
            raise _transition("archived", "archived")
        self._refuse_last_admin(session, user_uid, "be archived")
        record = _record(
            session.execute(_ARCHIVE, {"user_uid": user_uid, "actor_uid": actor_uid}).one()
        )
        _log.warning(
            "%s: %s (%r) by %s; it cannot sign in and every credential it held is refused.",
            ACCOUNT_ARCHIVED,
            user_uid,
            record.login,
            actor_uid,
        )
        return record

    def restore_account(self, session: Session, *, actor_uid: str, user_uid: str) -> UserRecord:
        """Return an archived account to active. ``conflict`` (``login_taken``) when an
        active account took its login meanwhile; ``state_transition_not_allowed``
        (``active -> active``) when it is not archived. Raises ``token_epoch``."""
        current = self._lock(session, user_uid)
        if current is None:
            raise _no_such_account()
        if not current.archived:
            raise _transition("active", "active")
        taken = session.execute(
            _LOGIN_HELD_BY_ANOTHER_ACTIVE, {"login": current.login, "user_uid": user_uid}
        ).scalar_one()
        if taken:
            raise login_taken()
        try:
            with session.begin_nested():
                row = session.execute(_RESTORE, {"user_uid": user_uid}).one()
        except DBAPIError as exc:
            if _unique_violation(exc):
                raise login_taken() from exc
            raise
        record = _record(row)
        _log.warning("%s: %s (%r) by %s.", ACCOUNT_RESTORED, user_uid, record.login, actor_uid)
        return record

    def references_to(self, session: Session, user_uid: str) -> tuple[str, ...]:
        """The register's RESTRICT entries that name this account, as ``table.column``."""
        found: list[str] = []
        for entry in restricting_references():
            # Table and column come from the register, a constant of this package -- never
            # from input -- so formatting them into the statement is safe.
            exists = session.execute(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {entry.table} "  # noqa: S608
                    f"WHERE {entry.column} = :user_uid)"
                ),
                {"user_uid": user_uid},
            ).scalar_one()
            if exists:
                found.append(f"{entry.table}.{entry.column}")
        return tuple(found)

    def purge_account(self, session: Session, *, actor_uid: str, user_uid: str) -> None:
        """Delete an archived, unreferenced account irreversibly (`R-61`, P-12).

        Refusals, in order: oneself (``permission_denied``); no such account
        (``not_found``); not archived (``state_transition_not_allowed``, ``app_user``
        ``active -> purged``); referenced by any RESTRICT entry of the register
        (``conflict``, ``conflict_reason: account_referenced``). The database's own
        RESTRICT keys are the backstop: a reference the register check missed still
        refuses the DELETE, and is reported the same way. The account's roles go with it
        (CASCADE); the request that created it keeps its row with ``created_user_uid``
        NULL (SET NULL).
        """
        _refuse_self(actor_uid, user_uid, "purge")
        current = self._lock(session, user_uid)
        if current is None:
            raise _no_such_account()
        if not current.archived:
            raise _transition("active", "purged")
        references = self.references_to(session, user_uid)
        if references:
            _log.info(
                "%s refused for %s: referenced by %s", ACCOUNT_PURGED, user_uid, references
            )
            raise account_referenced()
        try:
            with session.begin_nested():
                session.execute(_PURGE, {"user_uid": user_uid})
        except DBAPIError as exc:
            if str(getattr(exc.orig, "sqlstate", "") or "") == _FOREIGN_KEY_VIOLATION:
                raise account_referenced() from exc
            raise
        _log.warning(
            "%s: %s (%r) by %s. Irreversible; its login is free.",
            ACCOUNT_PURGED,
            user_uid,
            current.login,
            actor_uid,
        )

    def reset_password(
        self,
        session: Session,
        *,
        actor_uid: str,
        user_uid: str,
        temporary_password: str,
    ) -> UserRecord:
        """An administrator sets a temporary password (``resetUserPassword``, §3.4).

        Not oneself (``permission_denied`` -- an administrator changes their own password
        with ``changePassword``, proving the current one). The temporary password passes
        `R-48`'s policy against the target's login; the row is marked must-change
        (``is_default_credential``), the brake is cleared and ``token_epoch`` raised in one
        statement. That the administrator knows the temporary password is a registered
        limitation of this operation, not a property of it.
        """
        _refuse_self(actor_uid, user_uid, "reset its own password")
        current = self._lock(session, user_uid)
        if current is None or current.archived:
            raise _no_such_account()
        enforce_password_policy(temporary_password, login=current.login)
        stored = hash_password(temporary_password)
        record = _record(
            session.execute(
                _RESET_PASSWORD,
                {
                    "user_uid": user_uid,
                    "algorithm": stored.algorithm,
                    "iterations": stored.iterations,
                    "salt": stored.salt,
                    "digest": stored.digest,
                },
            ).one()
        )
        _log.warning(
            "%s: %s (%r) by %s; it must change the temporary password at its next sign-in "
            "and every credential it held is refused.",
            PASSWORD_RESET,
            user_uid,
            record.login,
            actor_uid,
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
