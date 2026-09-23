"""`R-37`: naming a reviewer, and the four places the login fallback says it is happening.

The ruling left one thing to be decided: **what an account with no display name writes.**
The answer is its login, and the load-bearing half of that answer is not the value -- it is
that the fallback is *not silent*. ``AGENTS.md`` §4 forbids a silent fallback, and a
fallback that lives inside one ``or`` expression is one.

So it is said in four places, and this module drives the three that a person can reach:

1. the nullable column, so the state is a query -- driven in
   ``tests/integration/db/test_reviewer_display_name.py``;
2. ``python -m auditmanager.access.check``, one line per account, its own stable prefix;
3. ``python -m auditmanager.access.name``, which is the only thing in the tree that writes
   a display name and therefore the only way out of the fallback;
4. the warning ``0009_reviewer_display_name`` writes into the deployment log, driven in the
   migration suite beside (1).

**The commands are driven as subprocesses**, the way an operator runs them, and the tree
they run against is derived from ``auditmanager.__file__`` rather than from this file --
`W39-REVOKE` paid for that difference and ``test_sign_in_throttle.py`` writes out why.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.check import CLEAN_SENTINEL, UNNAMED_PREFIX
from auditmanager.access.models import MAX_DISPLAY_NAME_LENGTH, UserRecord
from auditmanager.access.name import (
    CLEARED_PREFIX,
    NAMED_PREFIX,
    NO_SUCH_ACCOUNT_SENTINEL,
)
from auditmanager.access.repository import UserRepository

PASSWORD = "correct-horse-battery-staple-4471"

#: A name in the script the interface is actually written in. `R-37` exists because
#: ``author_label`` is read by people, and an ASCII-only test would not notice a boundary
#: that had quietly kept the login rule's alphabet.
DISPLAY_NAME = "Анна Петрова"


def _tree_under_test() -> Path:
    import auditmanager

    return Path(auditmanager.__file__).resolve().parents[2]


def _run(module: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an operator command as an operator runs it: a subprocess reading its own env."""
    tree = _tree_under_test()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(tree / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=tree,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def user(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> Iterator[UserRecord]:
    """One real account with no display name, removed afterwards."""
    login = f"w42seal-{secrets.token_hex(6)}"
    with session_factory() as session:
        record = UserRepository().create_user(session, login, PASSWORD)
        session.commit()
    try:
        yield record
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE login = :login"), {"login": login}
            )
            session.commit()


def _row(session_factory: sessionmaker[Session], login: str) -> UserRecord:
    with session_factory() as session:
        found = UserRepository().find_by_login(session, login)
    assert found is not None, login
    return found


# =======================================================================================
# The command that writes a name.
# =======================================================================================


def test_a_new_account_starts_on_the_fallback_and_that_is_not_a_failure(
    user: UserRecord,
) -> None:
    """`R-37`'s empty case is the **ordinary** state of a fresh installation.

    ``0006`` seeds one account and names nobody, and nothing in this wave invents a name,
    because inventing one is what the ruling forbids. So an account records decisions under
    its login until somebody says otherwise, and everything works meanwhile.
    """
    assert user.display_name is None
    assert user.display_label == user.login
    assert 1 <= len(user.display_label) <= MAX_DISPLAY_NAME_LENGTH, (
        "the fallback must fit author_label's 1..128 by construction, which it does "
        "because ck_app_user_login_format bounds a login at 1..100"
    )


def test_the_command_names_an_account_and_says_what_it_wrote(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    result = _run(
        "auditmanager.access.name", "--login", user.login, "--display-name", DISPLAY_NAME
    )
    assert result.returncode == 0, result.stderr
    assert NAMED_PREFIX in result.stdout
    assert DISPLAY_NAME in result.stdout

    named = _row(session_factory, user.login)
    assert named.display_name == DISPLAY_NAME
    assert named.display_label == DISPLAY_NAME


def test_naming_does_not_revoke_anything(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """A rename is not a revocation, and this is the assertion that keeps it that way.

    Raising ``token_epoch`` here would sign every reviewer's browser out because somebody
    corrected a spelling. The price of not raising it is stated rather than hidden: the
    name travels in the signed credential, so a reviewer holding one goes on recording
    under the old name until it expires.
    """
    before = _row(session_factory, user.login)
    result = _run(
        "auditmanager.access.name", "--login", user.login, "--display-name", DISPLAY_NAME
    )
    assert result.returncode == 0, result.stderr
    after = _row(session_factory, user.login)
    assert after.token_epoch == before.token_epoch
    assert after.password_updated_at == before.password_updated_at
    assert after.is_default_credential == before.is_default_credential
    assert after.failed_sign_ins == before.failed_sign_ins
    assert after.sign_in_blocked_until == before.sign_in_blocked_until
    # And the password still works, which is the property an operator actually cares about.
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is not None
        session.commit()


def test_clearing_returns_the_account_to_the_fallback(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    _run("auditmanager.access.name", "--login", user.login, "--display-name", DISPLAY_NAME)
    result = _run("auditmanager.access.name", "--login", user.login, "--clear")
    assert result.returncode == 0, result.stderr
    assert CLEARED_PREFIX in result.stdout
    cleared = _row(session_factory, user.login)
    assert cleared.display_name is None
    assert cleared.display_label == user.login


def test_naming_a_login_nobody_holds_is_a_fact_and_not_a_success(
    app_user_table: object,
) -> None:
    result = _run(
        "auditmanager.access.name",
        "--login",
        f"ghost-{secrets.token_hex(4)}",
        "--display-name",
        "X",
    )
    assert result.returncode == 1, result.stdout
    assert NO_SUCH_ACCOUNT_SENTINEL in result.stdout


@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("blank", "   "),
        ("too long", "x" * (MAX_DISPLAY_NAME_LENGTH + 1)),
        ("a newline", "Анна\nПетрова"),
    ],
)
def test_a_refused_name_is_exit_two_and_writes_nothing(
    user: UserRecord, session_factory: sessionmaker[Session], label: str, value: str
) -> None:
    """A refusal is the operator's own input being refused, which is not "no such account".

    Each of the three would become a defect at the moment an expert records a verdict: a
    blank fails ``author_label``'s ``minLength: 1``, an over-long one fails its
    ``maxLength: 128``, and a newline reaches a CSV export and a screen.
    """
    result = _run("auditmanager.access.name", "--login", user.login, "--display-name", value)
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert NAMED_PREFIX not in result.stdout
    assert _row(session_factory, user.login).display_name is None


def test_the_command_refuses_to_run_bare(app_user_table: object) -> None:
    """There is no default name, and the reason is the ruling's own words.

    *"Inventing one is not"* defensible: in an append-only ledger a fabricated name is, a
    year later, indistinguishable from one a person chose.
    """
    result = _run("auditmanager.access.name")
    assert result.returncode == 2
    assert NAMED_PREFIX not in result.stdout


def test_the_command_refuses_a_name_and_a_clear_at_once(user: UserRecord) -> None:
    result = _run(
        "auditmanager.access.name",
        "--login",
        user.login,
        "--display-name",
        DISPLAY_NAME,
        "--clear",
    )
    assert result.returncode == 2
    assert NAMED_PREFIX not in result.stdout


# =======================================================================================
# The report that makes the fallback visible.
# =======================================================================================


def test_access_check_names_every_account_on_the_fallback(user: UserRecord) -> None:
    result = _run("auditmanager.access.check")
    assert result.returncode in (0, 1), result.stderr
    assert UNNAMED_PREFIX in result.stdout
    assert user.login in result.stdout
    assert f"--login {user.login}" in result.stdout, (
        "the report names the state but not the way out of it; an operator reading it "
        "still has to go and find the command"
    )


def test_a_named_account_drops_out_of_the_report(user: UserRecord) -> None:
    """The half that makes the line above mean something.

    A report that printed every account would satisfy the assertion above for ever and
    would be telling nobody anything.
    """
    _run("auditmanager.access.name", "--login", user.login, "--display-name", DISPLAY_NAME)
    result = _run("auditmanager.access.check")
    assert result.returncode in (0, 1), result.stderr
    named_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(UNNAMED_PREFIX) and user.login in line
    ]
    assert named_lines == [], named_lines


def test_an_unnamed_account_does_not_move_the_exit_status(user: UserRecord) -> None:
    """Information beside a status about something else, which is ``check.py``'s own shape.

    A default credential is a temporary state that becomes permanent unseen, so it earns a
    status a checklist fails on. An unset display name is the **declared fallback working
    as designed**; failing a checklist over it would be this command asserting a policy --
    "every reviewer must be named" -- that nobody has ruled.
    """
    result = _run("auditmanager.access.check")
    assert UNNAMED_PREFIX in result.stdout, "this case needs an unnamed account to exist"
    if CLEAN_SENTINEL in result.stdout:
        assert result.returncode == 0, (
            "an account with no display name moved the exit status. It is information, "
            "not a finding: see UNNAMED_PREFIX."
        )
    else:
        # Some other account in this shared lane is on a default credential, which is what
        # the status is actually about. The assertion above still holds: this one is not.
        assert result.returncode == 1
