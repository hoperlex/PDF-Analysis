"""Grant a role to an account from the host::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.grant --login admin --role admin

`W49-PLAN.md` §3.2. Migration ``0015`` gives every existing account ``expert`` and the
``0006`` seed -- the account whose login is ``admin`` -- also ``admin``. When no such
account exists the migration still succeeds and says that nobody holds ``admin``; this
command is then the way in. It is also the recovery path when the last administrator's
credentials are lost: the database refuses to let the last active administrator lose the
role through the application, so an operator with the host is the only other way.

It **grants only**. Taking a role away is an administrator's decision made through the
application, where the invariants of §3.2 (not oneself, never the last administrator) are
enforced; an operator's shell that could demote anybody would be a second, unguarded path.

A grant that changes the set raises the account's ``token_epoch`` in the same transaction:
every credential it holds is refused on its next request, and it meets the new role after
signing in again. A role already held changes nothing and revokes nothing.

Exit status
-----------
``0`` when the account holds the role afterwards (``GRANTED`` or ``UNCHANGED``), ``1`` when
no active account has that login, ``2`` when the role was refused or the database could not
be read or written.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sqlalchemy.orm import Session

from auditmanager.access.accounts import AccountRepository
from auditmanager.access.models import ROLES
from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.errors import DomainError

__all__ = [
    "GRANTED_PREFIX",
    "NO_SUCH_ACCOUNT_SENTINEL",
    "UNCHANGED_PREFIX",
    "build_parser",
    "main",
    "run_grant",
]

GRANTED_PREFIX = "access-grant GRANTED"
UNCHANGED_PREFIX = "access-grant UNCHANGED"
NO_SUCH_ACCOUNT_SENTINEL = "access-grant: no active account has that login"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.access.grant",
        description=(
            "Grant a role to an account. Its credentials are revoked when the role set "
            "changes, so it signs in again to use the role."
        ),
    )
    parser.add_argument("--login", required=True, help="the account, by its login")
    parser.add_argument("--role", required=True, choices=sorted(ROLES), help="the role")
    return parser


def run_grant(*, login: str, role: str, settings: DatabaseSettings | None = None) -> int:
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            account = UserRepository().find_by_login(session, login)
            if account is None:
                print(NO_SUCH_ACCOUNT_SENTINEL, flush=True)
                return 1
            accounts = AccountRepository()
            changed = accounts.grant_role(
                session, user_uid=str(account.user_uid), role=role, granted_by=None
            )
            roles = accounts.roles_of(session, str(account.user_uid))
            session.commit()
    finally:
        engine.dispose()

    prefix = GRANTED_PREFIX if changed else UNCHANGED_PREFIX
    print(
        f"{prefix}: login={account.login} user_uid={account.user_uid} role={role} "
        f"roles={','.join(sorted(roles))}",
        flush=True,
    )
    if changed:
        print(
            "access-grant: every credential this account held is refused from now on; "
            "it signs in again to use the role.",
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
        return run_grant(login=arguments.login, role=arguments.role)
    except DomainError as exc:
        print(f"access-grant FAILED: {exc}", file=sys.stderr, flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-grant FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
