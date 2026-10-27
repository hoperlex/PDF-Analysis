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

**Since `R-37` it also reports which accounts have chosen no display name**, so their
decisions are attributed to their login. That is the declared fallback and not a defect --
see ``UNNAMED_PREFIX`` for why the exit status deliberately does not move for it -- but a
fallback nobody can see is the silent fallback ``AGENTS.md`` section 4 forbids, and this
line plus ``app_user.display_name IS NULL`` is what makes it visible.

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

**Since `PROD-02` it has a second, narrower mode, ``--gate``**::

    PYTHONPATH=src .venv/bin/python -m auditmanager.access.check --gate

The default mode above answers "which accounts are still on a temporary password", and
that is the wrong question for a deployment to be *refused* over: an administrator's
``resetUserPassword`` also marks the account must-change, so taken literally the default
mode would shut a published site over a reset that is waiting for its owner to sign in
(`R-146z`, ``ADR-0023`` section 3). The gate asks the question the deployment actually has
to be refused over -- **is the published pair, ``admin`` / ``password``, still valid?** --
and answers it by *verifying* the seeded ``admin`` account's stored credential against the
published password, not by reading a flag:

* a finding (status ``1``) only when an **active** account whose login is the seeded one
  accepts :data:`~auditmanager.access.policy.SHIPPED_DEFAULT_PASSWORD`. That is the one
  credential anyone who has read the deployment notes can use;
* every *other* account still on a temporary password is printed as a ``WARNING`` line and
  never moves the status (`R-46` keeps that visible without making it a refusal);
* status ``2`` when the database could not be read **or the stored credential could not be
  verified** (an algorithm this build does not implement, a corrupt digest): an answer
  nobody could give is not a clean one, and ``deploy.sh`` / ``verify-deployed.sh`` refuse
  on it rather than reading it as "no finding";
* the default mode, its sentinels and its exit statuses are unchanged, because
  ``readiness.sh`` reads them.

It prints logins and timestamps and never a digest, a salt or the password it tried. It
reads the four credential columns itself, with one read-only statement, because the only
other readers of them (``UserRepository.authenticate`` and ``change_password``) *write*: a
failed attempt through ``authenticate`` counts against the account and can shut the very
account whose state the gate is reporting, and a shut account answers "no" without
consulting the password at all -- so a deployment would read a locked seeded account as
clean. This statement is the third reader of those columns; ``repository.py`` (which is
not edited here) still describes two.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.models import UserRecord
from auditmanager.access.passwords import StoredPassword, verify_password
from auditmanager.access.policy import SHIPPED_DEFAULT_PASSWORD
from auditmanager.access.repository import UserRepository
from auditmanager.shared.db.config import DatabaseSettings, load_settings
from auditmanager.shared.db.engine import create_database_engine

__all__ = [
    "BLOCKED_PREFIX",
    "CLEAN_SENTINEL",
    "FINDING_PREFIX",
    "GATE_CLEAN_SENTINEL",
    "GATE_FINDING_PREFIX",
    "GATE_WARNING_PREFIX",
    "SEEDED_ADMIN_LOGIN",
    "SeededAccount",
    "UNNAMED_PREFIX",
    "gate_report",
    "main",
    "read_seeded_account",
    "run_check",
    "run_gate",
    "seeded_account_accepts_the_published_password",
]

#: Printed when nothing is on a default credential. Stable text, so a checklist can grep.
CLEAN_SENTINEL = "access-check OK no default credentials"

#: Printed, once per account, when something is. Also stable.
FINDING_PREFIX = "access-check DEFAULT CREDENTIAL"

#: Printed, once per account, for every account inside a cooling-off period at the moment
#: of the reading. Stable, and deliberately a different prefix from the one above so a
#: scraper cannot conflate two states with different remedies.
BLOCKED_PREFIX = "access-check SIGN-IN BLOCKED"

#: `R-37`. Printed, once per account, for every account that has chosen no display name,
#: so its decisions are attributed to its login. Stable, and a third prefix rather than a
#: variant of either above, for the reason ``BLOCKED_PREFIX`` is its own: three states with
#: three different remedies must not be conflatable by a scraper.
#:
#: **The status does not move for these either, and here the reason is stronger.** A
#: default credential is a temporary state that becomes permanent unseen, so it is worth a
#: number a checklist fails on. A lockout is temporary by construction. An unset display
#: name is neither -- it is the **declared fallback working as designed**, and an
#: installation may legitimately never set one. Failing a checklist over it would be this
#: command asserting that every reviewer must be named, which is a policy nobody has ruled.
#: What it is worth is being *visible*: the fallback is the one thing about `R-37` that a
#: reader could otherwise mistake for a reviewer having chosen their login as their name.
UNNAMED_PREFIX = "access-check NO DISPLAY NAME"


#: `PROD-02`. Printed by ``--gate`` when the seeded account still accepts the published
#: password. A different prefix from :data:`FINDING_PREFIX` on purpose: the two modes answer
#: two questions and a scraper must not be able to read one as the other.
GATE_FINDING_PREFIX = "access-check GATE DEFAULT CREDENTIAL"

#: Printed by ``--gate`` as its last line when (and only when) there is no finding.
GATE_CLEAN_SENTINEL = "access-check GATE OK no published credential"

#: Printed by ``--gate``, once per account, for a must-change account that is **not** the
#: published pair -- an administrator's temporary password. Information beside a status
#: about something else (`R-146z`).
GATE_WARNING_PREFIX = "access-check GATE WARNING temporary password"

#: The login ``0006_app_user`` seeds. A second copy, like
#: :data:`~auditmanager.access.policy.SHIPPED_DEFAULT_PASSWORD`, and guarded as one:
#: ``tests/unit/access/test_access_check_gate.py`` reads the migration's literal and
#: compares, so a seed that moved would fail a test and not quietly stop the gate looking.
SEEDED_ADMIN_LOGIN: Final[str] = "admin"

#: One read-only statement, addressed by login to the **active** holder of it (a login is
#: unique only among accounts that are not archived, `R-61`). It projects the four
#: credential columns and the two public facts the finding line prints, in one statement for
#: the reason ``repository._SELECT_CREDENTIAL`` gives: two reads of one row can disagree.
#: Unlike ``authenticate`` it writes nothing and it does not consult the lockout -- the
#: published pair is valid whether or not the account is shut at this instant.
_SELECT_SEEDED_ACCOUNT = text(
    "SELECT user_uid, password_updated_at, password_algorithm, password_iterations, "
    "password_salt, password_hash FROM app_user "
    "WHERE login = :login AND archived_at IS NULL"
)


@dataclass(frozen=True, slots=True)
class SeededAccount:
    """The seeded account as the gate needs it. ``stored`` is credential material: it is
    consumed by :func:`seeded_account_accepts_the_published_password` and never printed
    (``StoredPassword``'s own ``repr`` redacts the salt and the digest)."""

    user_uid: str
    password_updated_at: datetime
    stored: StoredPassword


def read_seeded_account(session: Session) -> SeededAccount | None:
    """The active account with the seeded login, or ``None`` when there is none."""
    row = session.execute(_SELECT_SEEDED_ACCOUNT, {"login": SEEDED_ADMIN_LOGIN}).first()
    if row is None:
        return None
    user_uid, password_updated_at, algorithm, iterations, salt, digest = row
    return SeededAccount(
        user_uid=str(user_uid),
        password_updated_at=password_updated_at,
        stored=StoredPassword(
            algorithm=algorithm, iterations=int(iterations), salt=salt, digest=digest
        ),
    )


def seeded_account_accepts_the_published_password(account: SeededAccount | None) -> bool:
    """True when ``account`` exists and its stored credential verifies against the
    published password.

    A credential this build cannot verify raises (``verify_password`` raises on an
    unsupported algorithm or a corrupt column) and the exception reaches :func:`main`,
    which reports status ``2``: "could not tell" is not "no".
    """
    if account is None:
        return False
    return verify_password(account.stored, SHIPPED_DEFAULT_PASSWORD)


def gate_report(
    seeded: SeededAccount | None,
    seeded_accepts: bool,
    must_change: Sequence[UserRecord],
) -> tuple[list[str], int]:
    """The lines the gate prints and the status it exits with, from facts already read.

    Separate from the database so every row of the table (the pair valid; a temporary
    password only; both; neither) is a unit case with no database.
    """
    lines: list[str] = []
    # An administrator's temporary password, or a must-change flag on any account that is
    # not the published pair: visible, never a refusal.
    for user in must_change:
        if seeded_accepts and seeded is not None and str(user.user_uid) == seeded.user_uid:
            continue
        lines.append(
            f"{GATE_WARNING_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"password_unchanged_since={user.password_updated_at.isoformat()}"
        )
    if seeded_accepts and seeded is not None:
        lines.append(
            f"{GATE_FINDING_PREFIX}: login={SEEDED_ADMIN_LOGIN} user_uid={seeded.user_uid} "
            f"password_unchanged_since={seeded.password_updated_at.isoformat()}"
        )
        lines.append(
            f"access-check GATE: the account {SEEDED_ADMIN_LOGIN!r} still accepts the "
            "published password. Anyone who has read the deployment notes can sign in as it."
        )
        return lines, 1
    lines.append(GATE_CLEAN_SENTINEL)
    return lines, 0


def run_gate(settings: DatabaseSettings | None = None) -> int:
    """``--gate``: status ``1`` only while the published pair is valid. See the module
    docstring."""
    resolved = settings if settings is not None else load_settings()
    engine = create_database_engine(resolved)
    try:
        with Session(engine) as session:
            seeded = read_seeded_account(session)
            must_change = UserRepository().users_on_default_credentials(session)
    finally:
        engine.dispose()
    accepts = seeded_account_accepts_the_published_password(seeded)
    lines, status = gate_report(seeded, accepts, must_change)
    for line in lines:
        print(line, flush=True)
    return status


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
            # Third question about the same table, in the same session, for the reason the
            # second one is here: a reader who had to reconcile three readings would be
            # doing the work this command exists to save.
            unnamed = repository.accounts_without_a_display_name(session)
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

    for user in unnamed:
        # `R-37`. Information, never a finding: the status below does not move for it. See
        # `UNNAMED_PREFIX`.
        print(
            f"{UNNAMED_PREFIX}: login={user.login} user_uid={user.user_uid} "
            f"label={user.display_label!r} "
            # `W49-SEAL-01` removed `access.name`; a person's name is set by completing the
            # profile, which `access.profile` does from the host (`R-59`).
            f"set_name='python -m auditmanager.access.profile --login {user.login} "
            "--email <email> --last-name <last> --first-name <first>'",
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


def main(argv: Sequence[str] = ()) -> int:
    """``argv`` is the arguments after the module name; the module's own entry point passes
    ``sys.argv[1:]``. Called with none (the default, and every caller before `PROD-02`) it
    is the report it always was. The only option is ``--gate``; anything else is status
    ``2`` rather than silently ignored, because a deploy that typed ``--gtae`` and got the
    default report back would read a flag it never asked about as a clean gate."""
    gate = False
    for argument in argv:
        if argument == "--gate":
            gate = True
        else:
            print(
                f"access-check FAILED: unrecognised argument {argument!r}; "
                "the only option is --gate",
                file=sys.stderr,
                flush=True,
            )
            return 2
    try:
        return run_gate() if gate else run_check()
    except Exception as exc:  # noqa: BLE001 - a CLI boundary reports rather than raises
        print(f"access-check FAILED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main(sys.argv[1:]))
