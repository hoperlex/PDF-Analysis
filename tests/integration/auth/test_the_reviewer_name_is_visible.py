"""`R-37` and `R-55`: the name a reviewer is shown under, and where the fallback says so.

`R-37` asked what an account with no display name writes, and the answer -- its login -- had
to be *visible*, because ``AGENTS.md`` §4 forbids a silent fallback. `R-55` then gave every
account a full name and made the name form "Фамилия И. О." outrank both the display name and
the login, and `W49-SEAL-01` removed ``python -m auditmanager.access.name``: a person's name is
now set by **completing the profile** -- the account itself through ``updateMyProfile``, or the
operator from the host through ``python -m auditmanager.access.profile`` (`R-59`). A decision
event is written only by a complete profile, so the label it records is the name form, at most
66 characters, inside ``author_label``'s 1..128 by construction.

This module drives what a person can reach:

1. ``python -m auditmanager.access.profile``, the operator's way out of the fallback;
2. ``python -m auditmanager.access.check``, one line per account still on it, naming the way out.

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
from auditmanager.access.models import MAX_NAME_LABEL_LENGTH, UserRecord
from auditmanager.access.profile import COMPLETED_PREFIX, NO_SUCH_ACCOUNT_SENTINEL
from auditmanager.access.repository import UserRepository

PASSWORD = "correct-horse-battery-staple-4471"


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
    """One real legacy account -- no names, no display name -- removed afterwards."""
    login = f"w49name-{secrets.token_hex(6)}"
    with session_factory() as session:
        record = UserRepository().create_user(session, login, PASSWORD)
        session.commit()
    try:
        yield record
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE user_uid = :uid"),
                {"uid": str(record.user_uid)},
            )
            session.commit()


def _by_uid(session_factory: sessionmaker[Session], user: UserRecord) -> UserRecord:
    from auditmanager.access.accounts import AccountRepository

    with session_factory() as session:
        found = AccountRepository().get_account(session, str(user.user_uid))
    assert found is not None, user.user_uid
    return found.record


def _complete(user: UserRecord, *names: str) -> subprocess.CompletedProcess[str]:
    arguments = [
        "--login",
        user.login,
        "--email",
        f"{user.login}@suite.invalid",
        "--last-name",
        names[0],
        "--first-name",
        names[1],
    ]
    if len(names) > 2:
        arguments += ["--middle-name", names[2]]
    return _run("auditmanager.access.profile", *arguments)


# =======================================================================================
# The fallback, and the command that ends it.
# =======================================================================================


def test_a_new_legacy_account_starts_on_the_login_fallback(user: UserRecord) -> None:
    """The ordinary state of an account no person has named yet -- an incomplete profile.

    Such an account reaches no product change since `W49-SEAL-01`, so its login never
    reaches the ledger; the fallback is still a real, non-empty label for every place the
    account is shown.
    """
    assert user.display_name is None
    assert user.profile_complete is False
    assert user.display_label == user.login


def test_completing_the_profile_gives_the_name_form_and_says_what_it_wrote(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    result = _complete(user, "Петрова", "Анна", "Сергеевна")
    assert result.returncode == 0, result.stderr
    assert COMPLETED_PREFIX in result.stdout
    assert "Петрова А. С." in result.stdout

    completed = _by_uid(session_factory, user)
    assert completed.profile_complete is True
    assert completed.login == f"{user.login}@suite.invalid"
    assert completed.display_label == "Петрова А. С."


def test_the_name_form_is_bounded_at_66_characters(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The longest names the rules accept give the longest label, inside 1..128."""
    longest = "Ф" * 60
    result = _complete(user, longest, "Анна", "Сергеевна")
    assert result.returncode == 0, result.stderr
    label = _by_uid(session_factory, user).display_label
    assert len(label) == MAX_NAME_LABEL_LENGTH == 66
    assert 1 <= len(label) <= 128


def test_completing_does_not_revoke_anything(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """A name is not a right: no epoch moves, and the password still works.

    The seam publishes the label the row holds now (`W49-SEAL-01`), so a credential the
    account already holds needs no replacement to be shown under the new name.
    """
    before = _by_uid(session_factory, user)
    assert _complete(user, "Петрова", "Анна").returncode == 0
    after = _by_uid(session_factory, user)
    assert after.token_epoch == before.token_epoch
    assert after.password_updated_at == before.password_updated_at
    with session_factory() as session:
        assert UserRepository().authenticate(session, after.login, PASSWORD) is not None
        session.commit()


def test_completing_a_login_nobody_holds_is_a_fact_and_not_a_success(
    app_user_table: object,
) -> None:
    result = _run(
        "auditmanager.access.profile",
        "--login",
        f"ghost-{secrets.token_hex(4)}",
        "--email",
        "ghost@suite.invalid",
        "--last-name",
        "Призракова",
        "--first-name",
        "Ия",
    )
    assert result.returncode == 1, result.stdout
    assert NO_SUCH_ACCOUNT_SENTINEL in result.stdout


@pytest.mark.parametrize(
    ("label", "last_name"),
    [
        ("too long", "Ф" * 61),
        ("a word that mixes Cyrillic and Latin", "Иванoв"),
        ("a digit", "Иванов2"),
    ],
)
def test_a_refused_name_is_exit_two_and_writes_nothing(
    user: UserRecord, session_factory: sessionmaker[Session], label: str, last_name: str
) -> None:
    result = _complete(user, last_name, "Анна")
    assert result.returncode == 2, (label, result.returncode, result.stdout, result.stderr)
    assert COMPLETED_PREFIX not in result.stdout
    assert _by_uid(session_factory, user).profile_complete is False


def test_the_command_refuses_to_run_bare(app_user_table: object) -> None:
    """There is no default name: a fabricated one is, a year later, indistinguishable from
    one a person chose."""
    result = _run("auditmanager.access.profile")
    assert result.returncode == 2
    assert COMPLETED_PREFIX not in result.stdout


def test_the_retired_naming_command_is_gone() -> None:
    """`W49-SEAL-01`: ``access.name`` is removed; ``access.profile`` replaces it."""
    result = _run("auditmanager.access.name", "--login", "anyone", "--clear")
    assert result.returncode != 0
    assert "No module named auditmanager.access.name" in result.stderr


# =======================================================================================
# The report that makes the fallback visible.
# =======================================================================================


def test_access_check_names_every_account_on_the_fallback(user: UserRecord) -> None:
    result = _run("auditmanager.access.check")
    assert result.returncode in (0, 1), result.stderr
    assert UNNAMED_PREFIX in result.stdout
    assert user.login in result.stdout
    line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith(UNNAMED_PREFIX) and user.login in line
    )
    assert f"auditmanager.access.profile --login {user.login}" in line, (
        "the report names the state but not the way out of it -- or names a command that "
        "no longer exists; an operator reading it still has to go and find the command"
    )


def test_a_named_account_drops_out_of_the_report(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The half that makes the line above mean something.

    A report that printed every account would satisfy the assertion above for ever and
    would be telling nobody anything.
    """
    # The display name `R-37` introduced, set through the repository: its command is
    # retired, and the column is what the report reads.
    with session_factory() as session:
        UserRepository().set_display_name(
            session, login=user.login, display_name="Анна Петрова"
        )
        session.commit()
    result = _run("auditmanager.access.check")
    assert result.returncode in (0, 1), result.stderr
    named_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(UNNAMED_PREFIX) and user.login in line
    ]
    assert named_lines == [], named_lines


def test_a_completed_profile_drops_out_of_the_report(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """`W49-SEAL-01`: a complete profile is named, by its names, with no display name.

    Until the seal the report's query read ``display_name IS NULL`` alone, so every account
    that completed its profile -- which shows the name form "Фамилия И." everywhere and
    can never fall back to its login -- was still listed as being on the fallback.
    """
    from auditmanager.access.accounts import AccountRepository

    email = f"w49named-{secrets.token_hex(5)}@suite.invalid"
    repository = UserRepository()
    with session_factory() as session:
        before = {str(u.user_uid) for u in repository.accounts_without_a_display_name(session)}
        assert str(user.user_uid) in before, "the legacy account starts on the fallback"
        AccountRepository().complete_profile(
            session,
            user_uid=str(user.user_uid),
            email=email,
            last_name="Названова",
            first_name="Ирина",
        )
        session.commit()
    with session_factory() as session:
        after = {str(u.user_uid) for u in repository.accounts_without_a_display_name(session)}
    assert str(user.user_uid) not in after
    result = _run("auditmanager.access.check")
    assert result.returncode in (0, 1), result.stderr
    listed = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(UNNAMED_PREFIX) and str(user.user_uid) in line
    ]
    assert listed == [], listed


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
