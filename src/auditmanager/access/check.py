"""Report which accounts are still on the password this system seeded them with::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.check

Why this exists as a command rather than only as a column: the state it reports is
supposed to be temporary, and a temporary state nobody can see from outside becomes
permanent. An operator can answer "is the default ``admin`` password still live?"
without opening a SQL client, without logging in as that user, and without reading any
credential material -- the query projects the login and the timestamps and nothing else.

It is **not** wired into ``make check-db`` or any gate. That target belongs to
``P1-INT-00`` and this stream does not own the Makefile; a stream adding a private
target or editing a frozen one is working around the ownership rule rather than
extending it. Whoever owns the deployment checklist can add the invocation above.

Exit status: ``0`` when no account is on a default credential, ``1`` when at least one
is, and ``2`` when the database could not be read. The first two are both *successful
readings*; the distinction is there so a checklist can assert on it.

**Since `W40-LIMIT` it also reports which accounts are shut out of signing in**, and the
status deliberately does **not** move for it. The reasons are the same sentence read twice:
a default credential is a state that is supposed to be temporary and becomes permanent when
nobody can see it, so it is worth a status a checklist fails on; a lockout is temporary *by
construction* -- it expires on its own -- so failing a checklist over one would fail it for
somebody mistyping a password five minutes ago. Folding both into the same number would
make ``1`` mean two things and an operator would have to read the output anyway to find out
which.

So the lockout lines are **information beside a status about something else**, stated here
rather than left to be inferred from the code. The question they answer is the only one a
lockout ever produces -- *"why can the owner not sign in?"* -- and it is asked by somebody
who cannot sign in to find out. The answer, when there is one, is
``python -m auditmanager.access.unlock --login <login>``.
"""

from __future__ import annotations

import sys

from sqlalchemy.orm import Session

from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine

__all__ = ["BLOCKED_PREFIX", "CLEAN_SENTINEL", "FINDING_PREFIX", "main", "run_check"]

#: Printed when nothing is on a default credential. Stable text, so a checklist can grep.
CLEAN_SENTINEL = "access-check OK no default credentials"

#: Printed, once per account, when something is. Also stable.
FINDING_PREFIX = "access-check DEFAULT CREDENTIAL"

#: Printed, once per account, for every account inside a cooling-off period at the moment
#: of the reading. Stable, and deliberately a different prefix from the one above so a
#: scraper cannot conflate two states with different remedies.
BLOCKED_PREFIX = "access-check SIGN-IN BLOCKED"


def run_check(settings: DatabaseSettings | None = None) -> int:
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            repository = UserRepository()
            users = repository.users_on_default_credentials(session)
            # Read in the same session as the line above, so the two halves of the report
            # describe one moment. They are two questions about one table and a reader who
            # had to reconcile two readings would be doing the work this command exists to
            # save.
            blocked = repository.accounts_blocked_from_signing_in(session)
    finally:
        engine.dispose()

    for user in blocked:
        # The status does not move for these; see the module docstring. A lockout expires
        # on its own, and a checklist that failed over one would fail over a reviewer
        # mistyping a password five minutes ago.
        until = user.sign_in_blocked_until
        if until is None:  # pragma: no cover - the query's own predicate excludes it
            # Not an `assert`, for the reason `api/security.py` gives about its own
            # unreachable refusal: an assertion disappears under `-O`, and this branch
            # means the statement's WHERE clause and this reader disagree about what
            # "blocked" is. Printing a placeholder would be the silent fallback
            # `AGENTS.md` section 4 forbids, in the one line an operator acts on.
            raise RuntimeError(
                f"accounts_blocked_from_signing_in returned {user.login!r} with no "
                "block instant; _SELECT_BLOCKED and this reader disagree"
            )
        print(
            f"{BLOCKED_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"failed_sign_ins={user.failed_sign_ins} "
            f"blocked_until={until.isoformat()} "
            f"release_now='python -m auditmanager.access.unlock --login {user.login}'",
            flush=True,
        )

    if not users:
        print(CLEAN_SENTINEL, flush=True)
        return 0
    for user in users:
        print(
            f"{FINDING_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"created_at={user.created_at.isoformat()} "
            f"password_unchanged_since={user.password_updated_at.isoformat()}",
            flush=True,
        )
    print(
        f"access-check: {len(users)} account(s) still hold the seeded password. "
        "Anyone who has read the deployment notes can sign in as them.",
        flush=True,
    )
    return 1


def main() -> int:
    try:
        return run_check()
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-check FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
