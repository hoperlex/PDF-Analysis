"""Take credentials away, from one account or from all of them::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.revoke --login admin
    PYTHONPATH=src .venv/bin/python -m auditmanager.access.revoke --everyone

Why this is a command and not an operation
------------------------------------------
The question this answers is *"the pilot has ended -- stop the credentials we handed out"*.
That is an **operator's** action, taken by somebody with a shell on the deployment, and it
is not a reviewer's. Publishing it as an HTTP operation would require deciding who may call
it, and this system has no roles: ``permission_denied`` is in the catalog precisely because
nothing raises it yet, and :mod:`auditmanager.api.security` says in as many words that it
decides *who* the subject is and not *what* they may do. An operation every authenticated
reviewer could call to revoke another account is not a smaller decision than adding roles,
it is the same decision taken by accident.

So the surface this adds is zero. A reviewer who wants to invalidate their own credentials
changes their password, which revokes them as part of the same statement; an operator who
wants to end the pilot runs this.

Exit status
-----------
``0`` when something was revoked, ``1`` when the command was well-formed and matched no
account, and ``2`` when the database could not be read or written. The middle one is a
*successful reading* that found nothing, and it is its own status so a checklist can tell
"there was nobody to revoke" from "revocation failed" -- reporting the first as success
would let ``--login typo`` look exactly like a revocation that happened.

There is no bare form
---------------------
Running this with no argument does **nothing** and exits ``2``. Neither available default
is defensible: revoking everybody by default is a command that ends the pilot when somebody
presses up-arrow, and revoking nobody by default is a command that reports success having
done nothing. ``--login`` and ``--everyone`` are mutually exclusive and one is required.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sqlalchemy.orm import Session

from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine

__all__ = ["REVOKED_PREFIX", "NOTHING_SENTINEL", "build_parser", "main", "run_revocation"]

#: Printed once per account whose credentials were taken away. Stable text, so a checklist
#: and a log scraper can both match it.
REVOKED_PREFIX = "access-revoke REVOKED"

#: Printed when the command was well-formed and matched nothing. Also stable.
NOTHING_SENTINEL = "access-revoke: nothing matched, so nothing was revoked"


def build_parser() -> argparse.ArgumentParser:
    """The two mutually exclusive, jointly required ways to say what to revoke."""
    parser = argparse.ArgumentParser(
        prog="python -m auditmanager.access.revoke",
        description=(
            "Revoke issued credentials by raising an account's credential epoch. Every "
            "credential minted for that account before this moment stops being accepted "
            "immediately, everywhere, without a redeploy and without a restart."
        ),
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--login",
        help="revoke every credential held by this one account",
    )
    target.add_argument(
        "--everyone",
        action="store_true",
        help=(
            "revoke every credential held by every account. This is the pilot-has-ended "
            "command: everybody signs in again, including you."
        ),
    )
    return parser


def run_revocation(
    *, login: str | None, settings: DatabaseSettings | None = None
) -> int:
    """Do the revocation and report it. ``login=None`` means every account.

    The session is committed here because this module is the outermost caller -- the same
    place ownership of the transaction stops for the API's adapters.
    """
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            revoked = UserRepository().revoke_credentials(session, login=login)
            session.commit()
    finally:
        engine.dispose()

    if not revoked:
        print(NOTHING_SENTINEL, flush=True)
        return 1
    for user in revoked:
        print(
            f"{REVOKED_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"token_epoch={user.token_epoch} "
            f"revoked_at={user.token_epoch_updated_at.isoformat()}",
            flush=True,
        )
    print(
        f"access-revoke: {len(revoked)} account(s) revoked. Every credential minted for "
        "them before now is refused; anyone holding one signs in again.",
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
        return run_revocation(login=None if arguments.everyone else arguments.login)
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-revoke FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
