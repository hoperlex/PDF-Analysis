"""Let an account sign in again, now::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.unlock --login admin
    PYTHONPATH=src .venv/bin/python -m auditmanager.access.unlock --everyone

**This command is the way back from a lockout, and the lockout is not allowed to exist
without it.**

`R-26` rules a rate limit and a lockout into the alpha. A rate limit needs no way back: it
counts consecutive recent failures and the count restarts by itself once the failures stop
being recent. A lockout is the other thing -- a state in which an account's password is not
consulted at all -- and **a lockout with no way back is a denial of service anybody can aim
at a named account.** This installation is seeded with one account, ``admin``, whose login
is written in a migration and in the deployment runbook, so the account an unauthenticated
caller can shut is the owner's own.

There are three ways back and two of them need nobody:

1. **time.** ``COOLING_OFF_SECONDS`` passes and the next attempt starts a fresh allowance;
2. **a password change.** ``POST /auth/password`` clears the brake in the same UPDATE that
   writes the new digest, so a reviewer who is shut out of the exchange but still holding a
   live credential can open their own door;
3. **this command**, for the case the first two do not cover: the owner cannot sign in,
   cannot wait, and holds no credential to change a password with.

Why it is a command and not an operation
-----------------------------------------
The same reason :mod:`auditmanager.access.revoke` is, and the reason is stronger here.
Publishing an unlock would mean deciding **who may unlock whom**, which is the role
vocabulary this system has not got -- ``permission_denied`` sits unraised in the catalog
for exactly that reason. And an unlock reachable over the network by an *unauthenticated*
caller would delete the brake this wave exists to add, while one reachable only by an
authenticated caller would be useless to the person it is for: being unable to sign in is
the problem.

So the surface this adds is zero. It is an operator's action taken by somebody with a shell
on the deployment, exactly like ending the pilot.

What it does **not** do
------------------------
It does not change a password, does not touch ``token_epoch``, and does not issue anything.
An account that was revoked stays revoked and an account on a default credential stays on
it: this command releases a brake and nothing else. The two states are deliberately
separate -- a lockout refuses *minting* a credential, a revocation refuses *presenting*
one -- and a command that collapsed them would be an operator's slip away from handing back
credentials somebody had taken away on purpose.

Exit status
-----------
``0`` when something was released, ``1`` when the command was well-formed and released
nothing, and ``2`` when the database could not be read or written. The middle one is a
*successful reading* that found nothing to do, and it is its own status for the reason
:mod:`auditmanager.access.revoke` gives: reporting it as success would make ``--login
typo`` look exactly like an unlock that happened.

**And it distinguishes the two ways of releasing nothing in its output**, though not in its
status. "There is no such account" and "that account was not shut" are different facts for
the person typing, and an operator who is unlocking an account in a hurry is exactly the
person who has just mistyped a login.

There is no bare form
---------------------
Running this with no argument does **nothing** and exits ``2``. ``--login`` and
``--everyone`` are mutually exclusive and one is required, for the same reason revocation
has no default: a command that acts on everybody when somebody presses up-arrow is the
wrong shape for a lever, in either direction.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sqlalchemy.orm import Session

from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError

__all__ = [
    "NOTHING_SHUT_SENTINEL",
    "NO_SUCH_ACCOUNT_SENTINEL",
    "UNLOCKED_PREFIX",
    "build_parser",
    "main",
    "run_unlock",
]

#: Printed once per account whose brake was released. Stable text, so a checklist and a log
#: scraper can both match it.
UNLOCKED_PREFIX = "access-unlock RELEASED"

#: Printed when the command matched an account -- or every account -- and none of them had
#: anything to release. Stable.
NOTHING_SHUT_SENTINEL = "access-unlock: nothing was shut, so nothing was released"

#: Printed when ``--login`` named an account that does not exist. Also stable, and separate
#: from the sentinel above because a typo and a no-op are different things to the person
#: who typed one of them.
NO_SUCH_ACCOUNT_SENTINEL = "access-unlock: no account has that login"


def build_parser() -> argparse.ArgumentParser:
    """The two mutually exclusive, jointly required ways to say whose door to open."""
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.access.unlock",
        description=(
            "Release the sign-in brake: clear an account's consecutive-failure count and "
            "any cooling-off period it has earned, so it can sign in again immediately. "
            "Nothing else changes - no password, no credential, and no revocation is "
            "undone."
        ),
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--login",
        help="release the brake on this one account",
    )
    target.add_argument(
        "--everyone",
        action="store_true",
        help=(
            "release the brake on every account. For the case where something is shut "
            "and you do not yet know what: it opens every door and counts no guess "
            "against anybody."
        ),
    )
    return parser


def run_unlock(*, login: str | None, settings: DatabaseSettings | None = None) -> int:
    """Release the brake and report it. ``login=None`` means every account.

    The session is committed here because this module is the outermost caller -- the same
    place ownership of the transaction stops for the API's adapters.
    """
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            repository = UserRepository()
            released = repository.clear_failed_sign_ins(session, login=login)
            # Read before committing and only when nothing moved: the answer decides
            # which sentence is printed, and asking afterwards would be asking about a
            # tree the statement may have changed.
            existed = True
            if not released and login is not None:
                existed = repository.find_by_login(session, login) is not None
            session.commit()
    finally:
        engine.dispose()

    if not released:
        print(
            NOTHING_SHUT_SENTINEL if existed else NO_SUCH_ACCOUNT_SENTINEL,
            flush=True,
        )
        return 1
    for user in released:
        print(
            f"{UNLOCKED_PREFIX}: login={user.login} user_uid={user.user_uid} "
            "failed_sign_ins=0 sign_in_blocked_until=none",
            flush=True,
        )
    print(
        f"access-unlock: {len(released)} account(s) can sign in again immediately. "
        "Nothing else changed: no password, no credential, no revocation.",
        flush=True,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exit_request:
        # `argparse` exits 2 for a usage error, which is this module's "could not act"
        # status already. It is caught and re-reported rather than allowed to propagate so
        # that every exit from this module goes through one place and means one thing.
        return int(exit_request.code or 2)
    try:
        return run_unlock(login=None if arguments.everyone else arguments.login)
    except DomainError as exc:
        # A login the boundary would never have stored raises rather than answering "no
        # such account", and that distinction is worth keeping at a command line: an
        # operator who typed `--login "Admin!"` has made a different mistake from one who
        # typed a login nobody holds.
        print(f"access-unlock FAILED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-unlock FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
