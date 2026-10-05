"""Complete an account's profile from the host::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.profile \\
        --login admin --email owner@example.com --last-name Петрова --first-name Анна \\
        [--middle-name Сергеевна]

`W49-PLAN.md` §3.1, `R-59`. Every account that existed when migration ``0015`` ran is a
**legacy account**: it reaches only its own profile and password until it gives its names
and an e-mail login. This command is the operator's path to that state, for two cases the
W51 screens do not cover:

* **between W49 and W51**, when the stand has no profile screen yet; and
* **recovery**, when nobody can sign in to complete a profile -- which, once the
  authorization registers refuse an incomplete profile, may include the only administrator.

It replaces ``python -m auditmanager.access.name`` as the way a person's name is set.

What it does
------------
One UPDATE writes the names, rewrites ``login`` to the e-mail and sets
``profile_completed_at`` -- the same statement ``updateMyProfile`` will use. The account
signs in with the e-mail from then on. Nothing else changes: not the password, not the
roles, not ``token_epoch``.

What it refuses
---------------
A name or an e-mail the rules of :mod:`auditmanager.access.models` refuse; an e-mail an
active account already holds; and a profile that is already complete, because a complete
profile's login is fixed.

Exit status
-----------
``0`` when the profile was completed, ``1`` when the command was well-formed and no active
account has that login, ``2`` when a value was refused or the database could not be read
or written -- the convention of :mod:`auditmanager.access.name`.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sqlalchemy.orm import Session

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError

__all__ = [
    "COMPLETED_PREFIX",
    "NO_SUCH_ACCOUNT_SENTINEL",
    "build_parser",
    "main",
    "run_complete_profile",
]

#: Printed when a profile was completed. Stable text for a checklist and a log scraper.
COMPLETED_PREFIX = "access-profile COMPLETED"

#: Printed when ``--login`` named no active account.
NO_SUCH_ACCOUNT_SENTINEL = "access-profile: no active account has that login"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.access.profile",
        description=(
            "Complete an account's profile: its names and its e-mail login, in one "
            "statement. The account signs in with the e-mail afterwards. The password, "
            "the roles and every credential it holds are unchanged."
        ),
    )
    parser.add_argument(
        "--login", required=True, help="the account, by the login it signs in with now"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="the e-mail address that becomes the login (ASCII, at most 254 characters)",
    )
    parser.add_argument("--last-name", required=True, help="at most 60 characters")
    parser.add_argument("--first-name", required=True, help="at most 60 characters")
    parser.add_argument("--middle-name", default=None, help="optional, at most 60 characters")
    return parser


def run_complete_profile(
    *,
    login: str,
    email: str,
    last_name: str,
    first_name: str,
    middle_name: str | None,
    settings: DatabaseSettings | None = None,
) -> int:
    """Complete the profile and report it. The session is committed here, the outermost caller."""
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            account = UserRepository().find_by_login(session, login)
            if account is None:
                print(NO_SUCH_ACCOUNT_SENTINEL, flush=True)
                return 1
            record = AccountRepository().complete_profile(
                session,
                user_uid=str(account.user_uid),
                email=email,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
            )
            session.commit()
    finally:
        engine.dispose()

    print(
        f"{COMPLETED_PREFIX}: login={record.login} user_uid={record.user_uid} "
        f"label={record.display_label!r} (was login={account.login})",
        flush=True,
    )
    print(
        f"access-profile: this account now signs in as {record.login}. Decisions already "
        "recorded keep the label they were written with.",
        flush=True,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 2)
    try:
        return run_complete_profile(
            login=arguments.login,
            email=arguments.email,
            last_name=arguments.last_name,
            first_name=arguments.first_name,
            middle_name=arguments.middle_name,
        )
    except DomainError as exc:
        print(f"access-profile FAILED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-profile FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
