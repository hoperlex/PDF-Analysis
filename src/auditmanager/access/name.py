"""Give a reviewer the name other reviewers read on their decisions::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.name \\
        --login admin --display-name 'Анна Петрова'
    PYTHONPATH=src .venv/bin/python -m auditmanager.access.name --login admin --clear

`R-37`. Wave 41 stopped attributing every verdict to one configured constant and started
writing the authenticated reviewer's **login** into ``expert_decision_event.author_label``
(`D-78`). The owner ruled that what other reviewers should read there is a **display
name**, and this is the only thing in the tree that writes one.

Why it is a command and not an operation
-----------------------------------------
The same reason :mod:`auditmanager.access.revoke` and :mod:`auditmanager.access.unlock` are
commands, and here the question it would force is the sharpest version of it: publishing a
rename means deciding **who may rename whom**, on a ledger every reviewer reads. A surface
on which one reviewer can change the name another reviewer's past decisions are attributed
to is an authorization model this system has not got, and ``T-6`` forbids inventing one at
that seam. So the surface this adds is zero -- and the contract does not move for it, which
is why `R-37` costs a migration and a reseal and not an operation.

What it does not do
--------------------
It does not touch the password, the default-credential flag, the sign-in brake or
``token_epoch``. **A rename is not a revocation**: signing every reviewer's browser out
because somebody corrected a spelling would punish tidiness. The consequence is stated
rather than hidden: the name travels inside the signed credential, so a reviewer holding
one minted before the rename goes on recording decisions under the old name until it
expires -- at most ``TOKEN_LIFETIME_SECONDS``, one hour. Signing out sooner is
``python -m auditmanager.access.revoke --login <login>``, which is a separate decision and
stays a separate command.

**And it changes nothing already recorded.** ``expert_decision_event`` is append-only,
enforced by a trigger, so every decision keeps the label it was written with. That is the
correct behaviour for a ledger and not a limitation of this command: the row records who
made the decision under the name they had at the time.

``--clear`` is a real operation
--------------------------------
It returns the account to the fallback -- ``display_label`` answers with the login -- and it
is not a way of breaking anything. A reviewer who leaves should be able to stop having
their name shown without their row being deleted and without their past decisions changing.

Exit status
-----------
``0`` when the account was found and written, ``1`` when the command was well-formed and
matched no account, and ``2`` when the value was refused or the database could not be read
or written. The middle one is a *successful reading* that found nothing, and it is its own
status for :mod:`auditmanager.access.unlock`'s reason: reporting it as success would make
``--login typo`` look exactly like a rename that happened.
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
    "CLEARED_PREFIX",
    "NAMED_PREFIX",
    "NO_SUCH_ACCOUNT_SENTINEL",
    "build_parser",
    "main",
    "run_set_display_name",
]

#: Printed when a name was written. Stable text, so a checklist and a log scraper can both
#: match it.
NAMED_PREFIX = "access-name NAMED"

#: Printed when a name was removed and the account returned to the login fallback. Its own
#: prefix and not a variant of the one above, because the two are different states and a
#: scraper must not be able to conflate them.
CLEARED_PREFIX = "access-name CLEARED"

#: Printed when ``--login`` named an account that does not exist.
NO_SUCH_ACCOUNT_SENTINEL = "access-name: no account has that login"


def build_parser() -> argparse.ArgumentParser:
    """``--login``, and exactly one of ``--display-name`` / ``--clear``.

    There is no bare form and no default name. A command that invents a name when somebody
    presses return is the one thing `R-37` rules out by name: *"inventing one is not"*
    defensible, because in an append-only ledger a fabricated name becomes, a year later,
    indistinguishable from one a person chose.
    """
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.access.name",
        description=(
            "Set or clear the name other reviewers read on this account's decisions. "
            "Nothing else changes - no password, no credential, no revocation - and "
            "decisions already recorded keep the label they were written with, because "
            "the ledger is append-only."
        ),
    )
    parser.add_argument(
        "--login", required=True, help="the account to name, by the login it signs in with"
    )
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument(
        "--display-name",
        help=(
            "the name to show, 1-128 characters, in any script. Stored as typed apart "
            "from surrounding whitespace: not folded, not transliterated, not shortened."
        ),
    )
    what.add_argument(
        "--clear",
        action="store_true",
        help=(
            "remove the name, returning this account to its login as its label. Past "
            "decisions are untouched."
        ),
    )
    return parser


def run_set_display_name(
    *,
    login: str,
    display_name: str | None,
    settings: DatabaseSettings | None = None,
) -> int:
    """Write the name and report it. ``display_name=None`` clears it.

    The session is committed here because this module is the outermost caller -- the same
    place ownership of the transaction stops for the API's adapters.
    """
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            record = UserRepository().set_display_name(
                session, login=login, display_name=display_name
            )
            session.commit()
    finally:
        engine.dispose()

    if record is None:
        print(NO_SUCH_ACCOUNT_SENTINEL, flush=True)
        return 1
    if record.display_name is None:
        print(
            f"{CLEARED_PREFIX}: login={record.login} user_uid={record.user_uid} "
            f"label={record.display_label!r} (the login, which is the fallback)",
            flush=True,
        )
    else:
        print(
            f"{NAMED_PREFIX}: login={record.login} user_uid={record.user_uid} "
            f"label={record.display_label!r}",
            flush=True,
        )
    print(
        "access-name: decisions already recorded keep the label they were written with. "
        "A credential minted before now carries the old name until it expires; "
        "`python -m auditmanager.access.revoke --login "
        f"{record.login}` ends that immediately.",
        flush=True,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exit_request:
        # As in `unlock.py`: argparse's usage exit is this module's "could not act" status
        # already, and it is re-reported here so every exit goes through one place.
        return int(exit_request.code or 2)
    try:
        return run_set_display_name(
            login=arguments.login,
            display_name=None if arguments.clear else arguments.display_name,
        )
    except DomainError as exc:
        # A refused name -- blank, too long, carrying a control character -- and a login
        # this boundary would never have stored both land here. Both are the operator's
        # own input being refused, which is a different mistake from naming an account
        # nobody holds, and it gets a different status.
        print(f"access-name FAILED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-name FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
