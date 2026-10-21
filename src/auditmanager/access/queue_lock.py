"""The registration queue's lock, shared by every writer that can give an account a login.

`D-147`. One invariant is meant to hold: a **pending registration request and an active
account never hold the same login**. Three statements enforce its halves one at a time and
none of them can enforce it alone:

* ``uq_registration_request_pending_login`` keeps one pending request per login;
* ``uq_app_user_login`` (partial, ``WHERE archived_at IS NULL``) keeps one active account per
  login;
* neither index relates a request to an account.

So the relation is kept by a lock and a read. Every writer that can *make an account active
under a login* -- :meth:`RegistrationRepository.submit` (which makes a request), approval,
profile completion and restoring an archived account -- takes the **same transaction
advisory lock** first, then asks the question it needs answered, so the answer cannot change
before the transaction ends:

* submit: "does an active account hold this login? does a request?";
* approval, profile completion, restore: "does a pending request hold this login?"
  (approval is the request it is deciding, and the check there is the account's).

Before this module approval and profile completion took neither the lock nor a check. A
submit that interleaved with an approval read "no account yet" and then "no pending request"
(the approved one had just stopped being pending) and inserted a request for a login the
approval had just given to an account: a request nobody could ever approve
(``login_taken``). Profile completion could make the same pair with no race at all.

**Lock order.** The queue lock is always taken **first** in a transaction, before any row
lock this context takes (a request ``FOR UPDATE``, an account ``FOR UPDATE``, the
administrators). With one order there is no cycle, and no code path takes the queue lock
after a row lock. :func:`take_queue_lock` is reentrant within a transaction, so a caller that
takes it twice does not wait for itself.

This module reads ``registration_request`` once, in :func:`login_has_pending_request`,
because the account writers in :mod:`auditmanager.access.accounts` need that one answer and
cannot import :mod:`auditmanager.access.registrations` (which imports them).
"""

from __future__ import annotations

from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

__all__ = ["QUEUE_LOCK_KEY", "login_has_pending_request", "take_queue_lock"]

#: One key for the whole queue: writers serialise on it for the length of their transaction,
#: so "count, then insert" cannot be interleaved past the cap and "check, then give the login
#: to an account" cannot be interleaved with a submit. Arbitrary, fixed, and spelled once
#: ("REGQ"); ``tests/integration/api/qa_w49/test_qa_w49_queue_cap.py`` holds it by value.
QUEUE_LOCK_KEY: Final[int] = 0x52454751

_TAKE = text("SELECT pg_advisory_xact_lock(:key)")
_PENDING_FOR_LOGIN = text(
    "SELECT EXISTS (SELECT 1 FROM registration_request "
    "WHERE login = :login AND status = 'pending')"
)


def take_queue_lock(session: Session) -> None:
    """Hold the queue lock until the caller's transaction ends. Reentrant; never released early."""
    session.execute(_TAKE, {"key": QUEUE_LOCK_KEY})


def login_has_pending_request(session: Session, login: str) -> bool:
    """True when a pending registration request holds ``login``.

    Only meaningful after :func:`take_queue_lock` in the same transaction: without it the
    answer can be out of date before the caller acts on it, which is the defect this module
    exists to close.
    """
    return bool(session.execute(_PENDING_FOR_LOGIN, {"login": login}).scalar_one())
