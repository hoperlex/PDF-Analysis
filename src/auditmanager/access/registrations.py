"""Registration requests: submit, decide, read the status (`W49-PLAN.md` §3.3, `R-56`).

`W49-ACCESS-01c`. The only reader and writer of ``registration_request``. Shaped like
:mod:`auditmanager.access.repository`: explicit statements, the caller's session, and the
credential columns read in exactly two named places -- :data:`_LOCK_FOR_DECISION` (approval
moves the digest to the new account) and :data:`_SELECT_STATUS_CANDIDATE` (the status read
proves the pair) -- both consumed here and never returned.

The lifecycle
-------------
* **Submit** is unauthenticated. The e-mail, the names and the password are validated
  first -- the password by `R-48`'s policy with the applicant's names and e-mail local part
  added to the contextual blocklist -- then, under one advisory lock so the queue cap cannot
  be raced past: an active account holding the login answers ``conflict``
  (``login_taken``), a pending request for it ``conflict`` (``request_pending``), and 100
  pending requests ``conflict`` (``queue_full``). The password is stored hashed until the
  decision. That ``login_taken`` and ``request_pending`` tell a submitter that a login is
  known is an accepted limitation the plan registers.
* **Approve** runs in the caller's one transaction: the request is locked ``FOR UPDATE``,
  the account is created with the request's digest, its names and ``profile_completed_at =
  now()``, the chosen roles (at least one) are granted by the administrator, and the
  request is decided -- which nulls its password columns. Two concurrent approvals: the
  second waits on the lock, then finds the request decided and answers
  ``state_transition_not_allowed``.
* **Reject** decides the request with a reason of 1-256 characters (a free text, so it
  travels in the status read and never as an error detail) and nulls the password.

The status read, and the work it does
-------------------------------------
:meth:`RegistrationRepository.read_status` answers a pair (login, password) that matches a
request, and ``None`` -- the same generic refusal as a failed exchange -- otherwise. **It
performs exactly one PBKDF2 derivation on every path**, request or no request, blocked or
not, so its timing says nothing; and :meth:`auditmanager.access.repository.UserRepository.
authenticate` likewise spends exactly one on a login no account holds, whether or not a
request exists. Only a failed status read is counted on the request's own throttle
columns, with the account brake's rules (`W40-LIMIT`); a failed exchange spends its
derivation and writes nothing on the request (`R-63`), so a pending applicant's sign-in --
a refused exchange followed by this read, as the BFF sends them -- costs one attempt.

**A decided request cannot be matched by a password**, because the decision nulls the
password columns (§3.3, and the guard trigger refuses any later write). So this read
answers ``pending`` for a proven pair, and answers ``None`` for a pair whose request is
already decided -- including a rejected one. The `R-56` addendum rules that sign-in
shows the generic refusal for a rejected request; only administrators see the reason
until a later mail notification exists.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.accounts import login_taken
from auditmanager.access.models import (
    RegistrationId,
    UserRecord,
    UserUid,
    name_label,
    normalize_email,
    normalize_person_name,
    parse_role,
)
from auditmanager.access.passwords import (
    StoredPassword,
    hash_password,
    spend_a_verification,
    verify_password,
)
from auditmanager.access.policy import enforce_password_policy
from auditmanager.access.repository import (
    _NEXT_FAILED_SIGN_INS,
    _PUBLIC_COLUMNS,
    ATTEMPT_WINDOW_SECONDS,
    COOLING_OFF_SECONDS,
    FAILED_SIGN_IN_ALLOWANCE,
    _record,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "MAX_PENDING_REQUESTS",
    "MAX_REJECTION_REASON_LENGTH",
    "REGISTRATION_DECIDED",
    "REGISTRATION_SUBMITTED",
    "RegistrationRecord",
    "RegistrationRepository",
    "RegistrationStatus",
]

_log = logging.getLogger(__name__)

#: `W49-PLAN.md` §3.3: more than this many pending requests answers ``queue_full``.
MAX_PENDING_REQUESTS: Final[int] = 100

#: The catalog's per-value limit, and the reason the reason is not an error detail.
MAX_REJECTION_REASON_LENGTH: Final[int] = 256

REGISTRATION_SUBMITTED: Final[str] = "registration submitted"
REGISTRATION_DECIDED: Final[str] = "registration decided"

_UNIQUE_VIOLATION: Final[str] = "23505"

#: One key for the whole queue: submissions serialise on it for the length of their
#: transaction, so "count, then insert" cannot be interleaved past the cap. Arbitrary, fixed,
#: and spelled once ("REGQ").
_QUEUE_LOCK_KEY: Final[int] = 0x52454751

#: Control characters a reason may not carry. A line feed is allowed -- an administrator may
#: write two sentences on two lines -- and nothing else below 0x20, nor DEL, nor C1.
_REASON_CONTROL: Final[re.Pattern[str]] = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")

_STATUSES: Final[frozenset[str]] = frozenset({"pending", "approved", "rejected"})

_REQUEST_COLUMNS: Final[str] = (
    "request_id, login, last_name, first_name, middle_name, status, submitted_at, "
    "decided_at, decided_by, rejection_reason, created_user_uid"
)


@dataclass(frozen=True, slots=True)
class RegistrationRecord:
    """One request, as anything outside this module may see it. No credential material."""

    request_id: str
    login: str
    last_name: str
    first_name: str
    middle_name: str | None
    status: str
    submitted_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    rejection_reason: str | None
    created_user_uid: str | None

    @property
    def display_label(self) -> str:
        return name_label(self.last_name, self.first_name, self.middle_name)


@dataclass(frozen=True, slots=True)
class RegistrationStatus:
    """What the status read answers to a proven pair (``readRegistrationStatus``)."""

    status: str
    decided_at: datetime | None
    rejection_reason: str | None


def _registration(row) -> RegistrationRecord:
    values = tuple(row)
    if values[5] not in _STATUSES:  # pragma: no cover - the CHECK forbids it
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="unknown request status")
    return RegistrationRecord(*values)


_INSERT_REQUEST = text(
    f"""
    INSERT INTO registration_request (
        request_id, login, last_name, first_name, middle_name,
        password_algorithm, password_iterations, password_salt, password_hash
    ) VALUES (
        :request_id, :login, :last_name, :first_name, :middle_name,
        :algorithm, :iterations, :salt, :digest
    )
    RETURNING {_REQUEST_COLUMNS}
    """
)

_LOGIN_HELD_BY_AN_ACTIVE_ACCOUNT = text(
    "SELECT EXISTS (SELECT 1 FROM app_user WHERE login = :login AND archived_at IS NULL)"
)
_PENDING_FOR_LOGIN = text(
    "SELECT EXISTS (SELECT 1 FROM registration_request "
    "WHERE login = :login AND status = 'pending')"
)
_COUNT_PENDING = text("SELECT count(*) FROM registration_request WHERE status = 'pending'")

_SELECT_REQUEST = text(
    f"SELECT {_REQUEST_COLUMNS} FROM registration_request WHERE request_id = :request_id"
)
_LIST_REQUESTS = text(
    f"SELECT {_REQUEST_COLUMNS} FROM registration_request "
    "WHERE (CAST(:status AS text) IS NULL OR status = :status) "
    "ORDER BY submitted_at, request_id"
)

#: One of the two statements that read a request's credential columns: the approval's lock.
_LOCK_FOR_DECISION = text(
    f"SELECT {_REQUEST_COLUMNS}, password_algorithm, password_iterations, password_salt, "
    "password_hash FROM registration_request WHERE request_id = :request_id FOR UPDATE"
)

#: The other: the status read's candidate -- the pending request for this login, else the
#: latest one -- with whether it is braked right now, computed by the database's clock.
_SELECT_STATUS_CANDIDATE = text(
    "SELECT request_id, status, decided_at, rejection_reason, password_algorithm, "
    "password_iterations, password_salt, password_hash, "
    "COALESCE(sign_in_blocked_until > now(), false) "
    "FROM registration_request WHERE login = :login "
    "ORDER BY (status = 'pending') DESC, submitted_at DESC, request_id DESC LIMIT 1"
)

_INSERT_ACCOUNT_FROM_REQUEST = text(
    f"""
    INSERT INTO app_user (
        user_uid, login, password_algorithm, password_iterations, password_salt,
        password_hash, is_default_credential, last_name, first_name, middle_name,
        profile_completed_at
    ) VALUES (
        :user_uid, :login, :algorithm, :iterations, :salt, :digest, false,
        :last_name, :first_name, :middle_name, now()
    )
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_GRANT_ON_APPROVAL = text(
    "INSERT INTO app_user_role (user_uid, role, granted_by) VALUES (:user_uid, :role, :by)"
)

_APPROVE = text(
    f"""
    UPDATE registration_request SET
        status = 'approved', decided_at = now(), decided_by = :actor_uid,
        created_user_uid = :created_user_uid,
        password_algorithm = NULL, password_iterations = NULL,
        password_salt = NULL, password_hash = NULL
    WHERE request_id = :request_id AND status = 'pending'
    RETURNING {_REQUEST_COLUMNS}
    """
)

_REJECT = text(
    f"""
    UPDATE registration_request SET
        status = 'rejected', decided_at = now(), decided_by = :actor_uid,
        rejection_reason = :reason,
        password_algorithm = NULL, password_iterations = NULL,
        password_salt = NULL, password_hash = NULL
    WHERE request_id = :request_id AND status = 'pending'
    RETURNING {_REQUEST_COLUMNS}
    """
)

#: A refused status read, recorded on the candidate request. The same expression as the
#: account brake; never reached for a request that is braked right now.
_NOTE_A_FAILED_STATUS_READ = text(
    f"""
    UPDATE registration_request SET
        failed_sign_ins = {_NEXT_FAILED_SIGN_INS},
        last_failed_sign_in_at = now(),
        sign_in_blocked_until = CASE
            WHEN ({_NEXT_FAILED_SIGN_INS}) >= :allowance
                THEN now() + (:cooling * interval '1 second')
            WHEN sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until <= now()
                THEN NULL
            ELSE sign_in_blocked_until
        END
    WHERE request_id = :request_id
    """
)

_CLEAR_REQUEST_BRAKE = text(
    "UPDATE registration_request SET failed_sign_ins = 0, last_failed_sign_in_at = NULL, "
    "sign_in_blocked_until = NULL WHERE request_id = :request_id "
    "AND (failed_sign_ins <> 0 OR last_failed_sign_in_at IS NOT NULL "
    "OR sign_in_blocked_until IS NOT NULL)"
)


def _conflict(reason: str, message: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message=message, conflict_reason=reason)


def _transition(current: str, requested: str) -> DomainError:
    """Against the ``registration_request`` machine of §3.4: ``pending -> approved |
    rejected``, nothing after."""
    return DomainError(
        ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
        message=f"a request that is {current} cannot become {requested}",
        machine="registration_request",
        current_state=current,
        requested_state=requested,
    )


def _no_such_request() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, message="no such registration request")


def normalize_rejection_reason(raw: str) -> str:
    """Strip; 1..256 characters; no control character but a line feed. Never repaired."""
    if not isinstance(raw, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the reason must be text", field="reason"
        )
    candidate = raw.strip()
    if not 1 <= len(candidate) <= MAX_REJECTION_REASON_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"the reason must be 1-{MAX_REJECTION_REASON_LENGTH} characters",
            field="reason",
        )
    if _REASON_CONTROL.search(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the reason must not contain control characters",
            field="reason",
        )
    return candidate


class RegistrationRepository:
    """Submit, approve, reject, list and read the status of registration requests."""

    __slots__ = ()

    # -- submit ------------------------------------------------------------------------

    def submit(
        self,
        session: Session,
        *,
        login: str,
        password: str,
        last_name: str,
        first_name: str,
        middle_name: str | None = None,
    ) -> RegistrationRecord:
        """Record a request. Validation first, then the three conflicts under the queue lock,
        then the derivation, then the INSERT -- see the module docstring."""
        email = normalize_email(login)
        last = normalize_person_name(last_name, field="last_name", required=True)
        first = normalize_person_name(first_name, field="first_name", required=True)
        middle = normalize_person_name(middle_name, field="middle_name", required=False)
        enforce_password_policy(
            password,
            login=email,
            context=(email.split("@", 1)[0], last, first, middle),
        )

        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _QUEUE_LOCK_KEY})
        if session.execute(_LOGIN_HELD_BY_AN_ACTIVE_ACCOUNT, {"login": email}).scalar_one():
            raise _conflict("login_taken", "an active account already holds this login")
        if session.execute(_PENDING_FOR_LOGIN, {"login": email}).scalar_one():
            raise _conflict("request_pending", "a request for this login is already pending")
        if int(session.execute(_COUNT_PENDING).scalar_one()) >= MAX_PENDING_REQUESTS:
            raise _conflict("queue_full", "too many registration requests are pending")

        stored = hash_password(password)
        try:
            with session.begin_nested():
                row = session.execute(
                    _INSERT_REQUEST,
                    {
                        "request_id": str(RegistrationId.new()),
                        "login": email,
                        "last_name": last,
                        "first_name": first,
                        "middle_name": middle,
                        "algorithm": stored.algorithm,
                        "iterations": stored.iterations,
                        "salt": stored.salt,
                        "digest": stored.digest,
                    },
                ).one()
        except DBAPIError as exc:
            if str(getattr(exc.orig, "sqlstate", "") or "") == _UNIQUE_VIOLATION:
                raise _conflict(
                    "request_pending", "a request for this login is already pending"
                ) from exc
            raise
        record = _registration(row)
        _log.info("%s: %s for %r", REGISTRATION_SUBMITTED, record.request_id, record.login)
        return record

    # -- decide ------------------------------------------------------------------------

    def approve(
        self,
        session: Session,
        *,
        actor_uid: str,
        request_id: str,
        roles: frozenset[str] | set[str] | tuple[str, ...] | list[str],
    ) -> tuple[RegistrationRecord, UserRecord]:
        """Create the account and decide the request, in the caller's one transaction.

        Refusals: no role (``validation_failed`` on ``roles`` -- approval grants at least
        one, §3.2); no such request (``not_found``); not pending
        (``state_transition_not_allowed``, ``registration_request``); an active account
        holds the login by now (``conflict``, ``login_taken``; the request stays pending).
        """
        chosen = frozenset(parse_role(role) for role in roles)
        if not chosen:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="an approval grants at least one role",
                field="roles",
            )
        RegistrationId.parse(request_id)
        row = session.execute(_LOCK_FOR_DECISION, {"request_id": request_id}).first()
        if row is None:
            raise _no_such_request()
        request = _registration(tuple(row)[:11])
        if request.status != "pending":
            raise _transition(request.status, "approved")
        algorithm, iterations, salt, digest = tuple(row)[11:]
        if session.execute(
            _LOGIN_HELD_BY_AN_ACTIVE_ACCOUNT, {"login": request.login}
        ).scalar_one():
            raise login_taken()

        user_uid = str(UserUid.new())
        try:
            with session.begin_nested():
                account = _record(
                    session.execute(
                        _INSERT_ACCOUNT_FROM_REQUEST,
                        {
                            "user_uid": user_uid,
                            "login": request.login,
                            "algorithm": algorithm,
                            "iterations": iterations,
                            "salt": salt,
                            "digest": digest,
                            "last_name": request.last_name,
                            "first_name": request.first_name,
                            "middle_name": request.middle_name,
                        },
                    ).one()
                )
        except DBAPIError as exc:
            if str(getattr(exc.orig, "sqlstate", "") or "") == _UNIQUE_VIOLATION:
                raise login_taken() from exc
            raise
        for role in sorted(chosen):
            session.execute(_GRANT_ON_APPROVAL, {"user_uid": user_uid, "role": role, "by": actor_uid})
        decided = _registration(
            session.execute(
                _APPROVE,
                {"request_id": request_id, "actor_uid": actor_uid, "created_user_uid": user_uid},
            ).one()
        )
        _log.warning(
            "%s: %s approved by %s; account %s (%r) holds %s.",
            REGISTRATION_DECIDED,
            request_id,
            actor_uid,
            user_uid,
            account.login,
            sorted(chosen),
        )
        return decided, account

    def reject(
        self, session: Session, *, actor_uid: str, request_id: str, reason: str
    ) -> RegistrationRecord:
        """Decide the request as rejected, with a reason of 1-256 characters."""
        text_reason = normalize_rejection_reason(reason)
        RegistrationId.parse(request_id)
        row = session.execute(_LOCK_FOR_DECISION, {"request_id": request_id}).first()
        if row is None:
            raise _no_such_request()
        request = _registration(tuple(row)[:11])
        if request.status != "pending":
            raise _transition(request.status, "rejected")
        decided = _registration(
            session.execute(
                _REJECT,
                {"request_id": request_id, "actor_uid": actor_uid, "reason": text_reason},
            ).one()
        )
        _log.warning("%s: %s rejected by %s.", REGISTRATION_DECIDED, request_id, actor_uid)
        return decided

    # -- read --------------------------------------------------------------------------

    def get(self, session: Session, request_id: str) -> RegistrationRecord | None:
        row = session.execute(_SELECT_REQUEST, {"request_id": request_id}).first()
        return None if row is None else _registration(row)

    def list_requests(
        self, session: Session, *, status: str | None = None
    ) -> tuple[RegistrationRecord, ...]:
        """``listRegistrations``: every request, or those in one status, oldest first."""
        if status is not None and status not in _STATUSES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, message="unknown request status", field="status"
            )
        rows = session.execute(_LIST_REQUESTS, {"status": status}).all()
        return tuple(_registration(row) for row in rows)

    def pending_total(self, session: Session) -> int:
        """The administrator's badge (``pending_total``)."""
        return int(session.execute(_COUNT_PENDING).scalar_one())

    def read_status(
        self, session: Session, *, login: str, password: str
    ) -> RegistrationStatus | None:
        """The status of the request this pair proves, or ``None`` -- exactly one derivation.

        Every path below spends one PBKDF2 derivation and only one: an unusable login, no
        request, a braked request, a decided request (no password left to compare), a wrong
        password and the right one. A refused attempt on a request that is not braked is
        counted on it; a proven pair clears its brake. The caller commits.
        """
        try:
            email = normalize_email(login)
        except DomainError:
            spend_a_verification(password)
            return None
        row = session.execute(_SELECT_STATUS_CANDIDATE, {"login": email}).first()
        if row is None:
            spend_a_verification(password)
            return None
        (
            request_id,
            status,
            decided_at,
            rejection_reason,
            algorithm,
            iterations,
            salt,
            digest,
            blocked_now,
        ) = row
        if blocked_now:
            spend_a_verification(password)
            return None
        if digest is None:
            # Decided: the password columns were nulled by the decision, so this pair can
            # no longer be proven. See the module docstring -- the conservative answer.
            spend_a_verification(password)
            self._note_a_failed_read(session, request_id)
            return None
        stored = StoredPassword(
            algorithm=algorithm, iterations=int(iterations), salt=salt, digest=digest
        )
        try:
            matched = verify_password(stored, password)
        except DomainError as exc:
            if exc.code is ErrorCode.VALIDATION_FAILED:
                self._note_a_failed_read(session, request_id)
                return None
            raise
        if not matched:
            self._note_a_failed_read(session, request_id)
            return None
        session.execute(_CLEAR_REQUEST_BRAKE, {"request_id": request_id})
        return RegistrationStatus(
            status=status, decided_at=decided_at, rejection_reason=rejection_reason
        )

    def _note_a_failed_read(self, session: Session, request_id: str) -> None:
        session.execute(
            _NOTE_A_FAILED_STATUS_READ,
            {
                "request_id": request_id,
                "window": ATTEMPT_WINDOW_SECONDS,
                "allowance": FAILED_SIGN_IN_ALLOWANCE,
                "cooling": COOLING_OFF_SECONDS,
            },
        )
