"""The rate limit and the lockout, end to end, over real rows: the columns, the exchange,
the ways back, and the two properties that keep a lockout from being a weapon.

`R-26`'s second half, `W40-LIMIT`. Until this wave a caller could offer the exchange as
many passwords as it could ask for. A derivation costs about 0.113 s
(:data:`auditmanager.access.passwords.ITERATIONS`), so an unbraked attacker had roughly
nine guesses a second against an account whose login is published in a migration.

**This suite is where the halves meet and the only place all of them are real at once**:
migration ``0008_sign_in_throttle``'s columns, the repository's writes, the served exchange
through the application's own seam, the two operator commands as subprocesses, and the
interaction with `W39-REVOKE`'s epoch. Everything else about the brake is asserted against
something fake somewhere, and a fake can agree with another fake for ever.

**It does not skip.** The claim is that a guesser is slowed and then stopped, and a suite
that skipped would report success for a tree in which neither happens.

**Every account here is randomised and removed afterwards.** ``OPERATING_CONSTRAINTS.md``
§6 and §9: this database is long-lived and shared, so a suite that shut the seeded ``admin``
account -- or any account it did not create -- would lock whatever else is running against
the same lane out of its own exchange for five minutes. Nothing below touches a row it did
not write.

Two conventions, both of them about §12
----------------------------------------
**The allowance is measured and never imported.** Nothing here computes an expectation out
of :data:`~auditmanager.access.repository.FAILED_SIGN_IN_ALLOWANCE`; the test that cares
drives real refusals until the door shuts, bounded by a literal ceiling, and asserts the
number it took is exactly five. A test that looped ``range(ALLOWANCE)`` and then asserted a
block would pass against every value of the constant, which is wave 9's shape exactly.

**Time is moved by ageing the row, never by sleeping and never by patching a clock.** The
decision is the database's ``now()`` -- deliberately, so that the instant a block is
compared against and the instant it was written with come from one clock -- so the honest
way to ask "what happens when this is old" is to make the row old.
"""

from __future__ import annotations

import logging
import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access import passwords
from auditmanager.access.check import BLOCKED_PREFIX, FINDING_PREFIX
from auditmanager.access.models import UserRecord
from auditmanager.access.repository import SIGN_IN_BLOCKED, UserRepository
from auditmanager.access.unlock import (
    NO_SUCH_ACCOUNT_SENTINEL,
    NOTHING_SHUT_SENTINEL,
    UNLOCKED_PREFIX,
)
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter


def _tree_under_test() -> Path:
    """The root of the tree pytest actually imported, derived from the module under test.

    **Not** ``Path(__file__).parents[3]``, and `W39-REVOKE` paid for the difference: the
    operator commands below are driven as *subprocesses*, so they get their own interpreter
    and their own ``PYTHONPATH``. A path derived from **this file** points at whichever
    checkout the test module was read from, which in a ``make mutation-copy`` run is the
    pristine one -- so the subprocess would execute unmutated code and report green, and a
    green from a mutation that never reached the code is indistinguishable from a guard
    that cannot fail. Two of wave 39's cases died exactly that way before it was noticed.
    """
    import auditmanager

    return Path(auditmanager.__file__).resolve().parents[2]


#: This suite's deployment secret. Not a credential: it is what the signing key is derived
#: from, and presenting it is a refusal like any other string.
DEPLOYMENT_SECRET = "w40-limit-suite-deployment-secret"

#: The password the created account holds, and the one it is changed to.
PASSWORD = "correct-horse-battery-staple-4471"
NEW_PASSWORD = "a-different-horse-entirely-9920"

#: What a guesser offers. Distinctive so that finding it anywhere means something.
WRONG_PASSWORD = "not-this-accounts-password-00000"

#: A ceiling on how many refusals a measuring loop will drive before giving up. A literal,
#: and deliberately not derived from the allowance: this is the number that makes the loop
#: terminate, not the number under test.
REFUSAL_CEILING = 12


@pytest.fixture
def user(
    app_user_table: object, session_factory: sessionmaker[Session]
) -> Iterator[UserRecord]:
    """One real account, created through the repository and removed afterwards."""
    login = f"w40lim-{secrets.token_hex(6)}"
    repository = UserRepository()
    with session_factory() as session:
        record = repository.create_user(session, login, PASSWORD)
        session.commit()
    try:
        yield record
    finally:
        with session_factory() as session:
            session.execute(
                text("DELETE FROM app_user WHERE login = :login"), {"login": login}
            )
            session.commit()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    """The served surface, wired exactly as the composition root wires it."""
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=None,  # type: ignore[arg-type]
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            session_factory, users=UserRepository(), signer=signer
        ),
    )

    class _Built:
        def __init__(self) -> None:
            from auditmanager.runs import InlineCarrier

            self.router = router
            self.carrier = InlineCarrier()

    app = create_asgi_app(
        environ={API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}, application=_Built()
    )
    return TestClient(app, raise_server_exceptions=False)


# =======================================================================================
# Helpers. None of them reads a constant from the module under test.
# =======================================================================================


def _row(session_factory: sessionmaker[Session], login: str) -> UserRecord:
    with session_factory() as session:
        found = UserRepository().find_by_login(session, login)
    assert found is not None, login
    return found


def _refuse_once(session_factory: sessionmaker[Session], login: str) -> UserRecord:
    """One refused attempt through the real path, committed as the adapter commits it."""
    repository = UserRepository()
    with session_factory() as session:
        assert repository.authenticate(session, login, WRONG_PASSWORD) is None
        session.commit()
    return _row(session_factory, login)


def _shut_it(session_factory: sessionmaker[Session], login: str) -> int:
    """Drive real refusals until the door shuts. Returns how many it took.

    Bounded by a literal ceiling so a tree in which nothing ever shuts fails here rather
    than running for ever.
    """
    for attempt in range(1, REFUSAL_CEILING + 1):
        record = _refuse_once(session_factory, login)
        if record.sign_in_blocked_until is not None:
            return attempt
    raise AssertionError(
        f"{REFUSAL_CEILING} consecutive refusals did not shut {login!r}: "
        "the lockout never engages"
    )


def _age_the_row(
    session_factory: sessionmaker[Session], login: str, *, sql_interval: str
) -> None:
    """Move this account's two instants back by ``sql_interval``.

    The clock is the database's, so this is how the suite asks "what happens when this is
    old" without sleeping and without patching anything.
    """
    with session_factory() as session:
        session.execute(
            text(
                "UPDATE app_user SET "
                f"last_failed_sign_in_at = last_failed_sign_in_at - interval '{sql_interval}', "
                f"sign_in_blocked_until = sign_in_blocked_until - interval '{sql_interval}' "
                "WHERE login = :login"
            ),
            {"login": login},
        )
        session.commit()


def _exchange(client: TestClient, login: str, password: str) -> object:
    return client.post("/auth/token", json={"login": login, "password": password})


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


# =======================================================================================
# The rate limit: a count that means CONSECUTIVE AND RECENT.
# =======================================================================================


def test_a_new_account_carries_no_failures_and_no_block(user: UserRecord) -> None:
    """And the two instants are NULL rather than an epoch-like sentinel.

    A nullable instant whose NULL had to be read as a refusal would be one restart away
    from locking an installation out of itself, which is why the column is documented as
    "NULL means this account may be tried now" in as many words.
    """
    assert user.failed_sign_ins == 0
    assert user.last_failed_sign_in_at is None
    assert user.sign_in_blocked_until is None


def test_a_refused_attempt_is_counted_and_dated(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    after = _refuse_once(session_factory, user.login)
    assert after.failed_sign_ins == 1
    assert after.last_failed_sign_in_at is not None
    assert after.sign_in_blocked_until is None, "one refusal is not a lockout"


def test_two_refusals_in_a_row_accumulate(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    _refuse_once(session_factory, user.login)
    assert _refuse_once(session_factory, user.login).failed_sign_ins == 2


def test_a_refusal_that_is_not_recent_does_not_accumulate(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The window is what makes the count mean *consecutive and recent*.

    Without it, a reviewer who mistypes twice in March and three times in June is locked
    out in June -- a brake that fires on a pattern every human produces and no attacker
    does.
    """
    _refuse_once(session_factory, user.login)
    _refuse_once(session_factory, user.login)
    _age_the_row(session_factory, user.login, sql_interval="1 day")
    assert _refuse_once(session_factory, user.login).failed_sign_ins == 1


def test_an_empty_or_over_long_candidate_is_counted_like_any_other_refusal(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """A candidate the mechanical bounds refuse could not have matched any stored digest,
    which is what it has in common with every other refused attempt. An uncounted refusal
    is an attempt shape a guesser would find and use."""
    repository = UserRepository()
    with session_factory() as session:
        assert repository.authenticate(session, user.login, "") is None
        assert repository.authenticate(session, user.login, "x" * 4000) is None
        session.commit()
    assert _row(session_factory, user.login).failed_sign_ins == 2


def test_an_unknown_login_records_nothing_and_still_costs_a_derivation(
    app_user_table: object,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """There is no row to count against, and inventing one would be a table an
    unauthenticated caller can grow. What keeps the two paths indistinguishable is the
    derivation, which is asserted here as a call rather than as a duration -- a wall-clock
    assertion on a shared lane is a flake, and what the code decides is *to spend the
    work*."""
    spent: list[str] = []
    monkeypatch.setattr(
        "auditmanager.access.repository.spend_a_verification",
        lambda password, **_: spent.append(password),
    )
    with session_factory() as session:
        assert UserRepository().authenticate(session, "nobody-here-at-all", "x") is None
        session.commit()
    assert spent == ["x"]


# =======================================================================================
# The lockout: what it takes, what it refuses, and that it ends.
# =======================================================================================


def test_the_allowance_is_five_consecutive_refusals(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """Measured by driving real refusals until the door shuts, never by reading the
    constant. A loop over ``range(ALLOWANCE)`` would pass against every value of it."""
    assert _shut_it(session_factory, user.login) == 5
    shut = _row(session_factory, user.login)
    assert shut.sign_in_blocked_until is not None
    assert shut.failed_sign_ins == 5


def test_a_shut_account_refuses_the_right_password(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """**This is what a lockout is**, and it is worth stating as its own assertion.

    A lockout a correct password defeats does not stop guessing, because a guess that
    succeeds *is* a correct password. The availability that costs is the price of the
    confidentiality it buys; what bounds it is that it ends, and the three ways it ends are
    each asserted below.
    """
    _shut_it(session_factory, user.login)
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is None
        session.commit()


def test_an_attempt_while_shut_spends_the_same_derivation_every_refusal_spends(
    user: UserRecord,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cheap refusal here would answer a *better* question than the enumeration oracle
    the exchange already closes: not only "does this account exist" but "is it under attack
    right now"."""
    _shut_it(session_factory, user.login)
    spent: list[str] = []
    monkeypatch.setattr(
        "auditmanager.access.repository.spend_a_verification",
        lambda password, **_: spent.append(password),
    )
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is None
        session.commit()
    assert spent == [PASSWORD]


def test_an_attempt_while_shut_does_not_extend_the_block(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """Counting attempts made against a shut door would let an attacker who keeps knocking
    hold an account closed indefinitely, which is a permanent lockout wearing a temporary
    one's clothes."""
    _shut_it(session_factory, user.login)
    shut = _row(session_factory, user.login)
    with session_factory() as session:
        repository = UserRepository()
        for _ in range(3):
            assert repository.authenticate(session, user.login, WRONG_PASSWORD) is None
        session.commit()
    after = _row(session_factory, user.login)
    assert after.sign_in_blocked_until == shut.sign_in_blocked_until
    assert after.failed_sign_ins == shut.failed_sign_ins


def test_a_block_that_has_passed_lets_the_right_password_through(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The first way back, and the one that needs nobody."""
    _shut_it(session_factory, user.login)
    _age_the_row(session_factory, user.login, sql_interval="1 hour")
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is not None
        session.commit()


def test_a_served_block_is_spent_and_the_next_failure_starts_a_fresh_allowance(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """Without this clause one attempt per cooling-off period re-trips the block for ever,
    and the temporary lockout is a permanent one an unauthenticated caller can aim."""
    _shut_it(session_factory, user.login)
    _age_the_row(session_factory, user.login, sql_interval="1 hour")
    after = _refuse_once(session_factory, user.login)
    assert after.failed_sign_ins == 1
    assert after.sign_in_blocked_until is None


def test_a_successful_sign_in_clears_what_earlier_refusals_recorded(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    _refuse_once(session_factory, user.login)
    _refuse_once(session_factory, user.login)
    with session_factory() as session:
        signed_in = UserRepository().authenticate(session, user.login, PASSWORD)
        session.commit()
    assert signed_in is not None
    assert signed_in.failed_sign_ins == 0, "the record handed out carries the cleared count"
    assert signed_in.last_failed_sign_in_at is None
    cleared = _row(session_factory, user.login)
    assert cleared.failed_sign_ins == 0
    assert cleared.last_failed_sign_in_at is None
    assert cleared.sign_in_blocked_until is None


def test_the_moment_a_block_is_set_is_logged_once_with_a_stable_prefix(
    user: UserRecord,
    session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The operator's only live view of a state nothing else announces -- and exactly one
    line per cooling-off period, because an attempt made while shut writes nothing."""
    with caplog.at_level(logging.WARNING, logger="auditmanager.access.repository"):
        _shut_it(session_factory, user.login)
        with session_factory() as session:
            for _ in range(3):
                UserRepository().authenticate(session, user.login, WRONG_PASSWORD)
            session.commit()
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING and SIGN_IN_BLOCKED in record.getMessage()
    ]
    assert len(warnings) == 1, warnings
    assert user.login in warnings[0]
    assert "unlock" in warnings[0], "the warning names the way back"


# =======================================================================================
# The exchange, over the application's own seam.
# =======================================================================================


def test_the_exchange_shuts_an_account_and_then_refuses_its_real_password(
    user: UserRecord, client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """The whole wave in one assertion, driven the way a caller drives it.

    The adapter opens a **write** session for this, which it did not before: a read session
    would discard the count on the way out and the brake would be applied only in the log.
    """
    for _ in range(REFUSAL_CEILING):
        refused = _exchange(client, user.login, WRONG_PASSWORD)
        assert refused.status_code == 401  # type: ignore[attr-defined]
        if _row(session_factory, user.login).sign_in_blocked_until is not None:
            break
    else:  # pragma: no cover - the loop above shuts the door long before the ceiling
        raise AssertionError("the exchange never shut the account")
    answer = _exchange(client, user.login, PASSWORD)
    assert answer.status_code == 401  # type: ignore[attr-defined]


def test_a_shut_account_and_a_wrong_password_are_byte_identical_apart_from_correlation(
    user: UserRecord, client: TestClient
) -> None:
    """One answer, as everywhere on this path. A caller able to tell them apart would learn
    that the account exists *and* that somebody is attacking it -- the enumeration oracle
    with a progress bar."""
    first = _exchange(client, user.login, WRONG_PASSWORD)
    body_while_open = first.json()  # type: ignore[attr-defined]
    for _ in range(REFUSAL_CEILING):
        _exchange(client, user.login, WRONG_PASSWORD)
    shut = _exchange(client, user.login, PASSWORD)
    body_while_shut = shut.json()  # type: ignore[attr-defined]
    assert shut.status_code == first.status_code  # type: ignore[attr-defined]
    assert body_while_shut["error_code"] == body_while_open["error_code"]
    assert body_while_shut["error_code"] == "authentication_required"
    assert body_while_shut["retryable"] == body_while_open["retryable"]
    assert body_while_shut["message"] == body_while_open["message"]
    for forbidden in ("blocked", "locked", "until", "attempt", "retry_after"):
        assert forbidden not in shut.text.lower(), forbidden  # type: ignore[attr-defined]


def test_no_response_header_tells_a_caller_when_to_come_back(
    user: UserRecord, client: TestClient
) -> None:
    """``Retry-After`` would be the same disclosure one layer out, and the catalog has no
    ``429`` to carry it anyway: ``retryable`` is authoritative and the code is
    ``authentication_required``, whose ``retryable`` is false because retrying the same
    request never succeeds."""
    for _ in range(REFUSAL_CEILING):
        _exchange(client, user.login, WRONG_PASSWORD)
    shut = _exchange(client, user.login, PASSWORD)
    assert "retry-after" not in {k.lower() for k in shut.headers}  # type: ignore[attr-defined]


# =======================================================================================
# The lockout and the epoch are different states, and that is the property that keeps a
# lockout from being a weapon.
# =======================================================================================


def test_a_lockout_does_not_touch_a_credential_anybody_already_holds(
    user: UserRecord, client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """**The `R-29` property.** A lockout refuses *minting*; revocation refuses
    *presenting*. If the first reached the second, an unauthenticated caller could sign out
    a reviewer who is working by typing wrong passwords at their login -- a caller who never
    had access taking it away from one who did.

    The probe sends the account's real current password to ``changePassword``: the seam runs
    before the handler, so a credential the seam refuses answers 401 without the port being
    reached, and 200 means the seam accepted it.
    """
    minted = _exchange(client, user.login, PASSWORD).json()["token"]  # type: ignore[attr-defined]
    _shut_it(session_factory, user.login)
    assert _row(session_factory, user.login).sign_in_blocked_until is not None
    probe = client.post(
        "/auth/password",
        headers={"Authorization": f"Bearer {minted}"},
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert probe.status_code == 200, probe.text


def test_the_lockout_leaves_the_epoch_alone(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """Asserted on the column as well as on the behaviour above: the two are separate
    states with separate remedies and nothing here may collapse them."""
    _shut_it(session_factory, user.login)
    assert _row(session_factory, user.login).token_epoch == user.token_epoch


def test_a_revoked_account_is_not_thereby_shut(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """And the other direction. An operator ending the pilot takes credentials away; they
    do not also bar the account from signing in, which would make ``revoke`` an unlockable
    lockout."""
    with session_factory() as session:
        UserRepository().revoke_credentials(session, login=user.login)
        session.commit()
    revoked = _row(session_factory, user.login)
    assert revoked.token_epoch == user.token_epoch + 1
    assert revoked.sign_in_blocked_until is None
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is not None
        session.commit()


# =======================================================================================
# The second way back: a password change.
# =======================================================================================


def test_a_password_change_clears_the_brake(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """An account that has just proved its current password is not what the brake exists to
    slow -- and this is the way back for a reviewer who is shut out of the exchange but
    still holding a live credential."""
    _shut_it(session_factory, user.login)
    with session_factory() as session:
        changed = UserRepository().change_password(
            session,
            user_uid=str(user.user_uid),
            current_password=PASSWORD,
            new_password=NEW_PASSWORD,
        )
        session.commit()
    assert changed is not None
    assert changed.failed_sign_ins == 0
    assert changed.sign_in_blocked_until is None
    with session_factory() as session:
        assert (
            UserRepository().authenticate(session, user.login, NEW_PASSWORD) is not None
        )
        session.commit()


def test_a_wrong_current_password_does_not_move_the_sign_in_brake(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """The two counters are deliberately not one. ``changePassword`` is reached only by a
    caller who already holds a credential for this account, so guessing there is guessing
    as the account -- and a shared counter would let a stolen credential, or a reviewer
    mistyping, shut the account's own front door."""
    with session_factory() as session:
        for _ in range(REFUSAL_CEILING):
            assert (
                UserRepository().change_password(
                    session,
                    user_uid=str(user.user_uid),
                    current_password=WRONG_PASSWORD,
                    new_password=NEW_PASSWORD,
                )
                is None
            )
        session.commit()
    untouched = _row(session_factory, user.login)
    assert untouched.failed_sign_ins == 0
    assert untouched.sign_in_blocked_until is None


# =======================================================================================
# The third way back: the operator's command.
# =======================================================================================


def test_the_command_releases_one_account_and_says_which(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    _shut_it(session_factory, user.login)
    result = _run("auditmanager.access.unlock", "--login", user.login)
    assert result.returncode == 0, result.stderr
    assert UNLOCKED_PREFIX in result.stdout
    assert user.login in result.stdout
    released = _row(session_factory, user.login)
    assert released.failed_sign_ins == 0
    assert released.sign_in_blocked_until is None
    with session_factory() as session:
        assert UserRepository().authenticate(session, user.login, PASSWORD) is not None
        session.commit()


def test_releasing_an_account_that_was_not_shut_is_a_fact_and_not_a_success(
    user: UserRecord
) -> None:
    """Exit ``1``, and the sentence says it was a no-op rather than a typo."""
    result = _run("auditmanager.access.unlock", "--login", user.login)
    assert result.returncode == 1, result.stdout
    assert NOTHING_SHUT_SENTINEL in result.stdout


def test_releasing_a_login_nobody_holds_says_so_and_is_still_not_a_success(
    app_user_table: object
) -> None:
    """The same status and a **different sentence**. An operator unlocking an account in a
    hurry is exactly the person who has just mistyped a login, and "nothing was shut" would
    read as reassurance."""
    result = _run("auditmanager.access.unlock", "--login", f"ghost-{secrets.token_hex(4)}")
    assert result.returncode == 1, result.stdout
    assert NO_SUCH_ACCOUNT_SENTINEL in result.stdout


def test_the_command_refuses_to_run_bare(app_user_table: object) -> None:
    """Neither available default is defensible: releasing every brake by default is a
    command that undoes the guard when somebody presses up-arrow, and releasing none is a
    command that reports success having done nothing."""
    result = _run("auditmanager.access.unlock")
    assert result.returncode == 2
    assert UNLOCKED_PREFIX not in result.stdout


def test_the_command_refuses_both_targets_at_once(app_user_table: object) -> None:
    result = _run("auditmanager.access.unlock", "--login", "admin", "--everyone")
    assert result.returncode == 2
    assert UNLOCKED_PREFIX not in result.stdout


def test_releasing_does_not_undo_a_revocation(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """``unlock`` and ``revoke`` look like opposites and are not. An operator's slip must
    not hand back credentials somebody took away on purpose."""
    with session_factory() as session:
        UserRepository().revoke_credentials(session, login=user.login)
        session.commit()
    epoch_after_revocation = _row(session_factory, user.login).token_epoch
    _shut_it(session_factory, user.login)
    assert _run("auditmanager.access.unlock", "--login", user.login).returncode == 0
    assert _row(session_factory, user.login).token_epoch == epoch_after_revocation


# =======================================================================================
# The operator's read-only view.
# =======================================================================================


def test_the_repository_names_who_is_shut_right_now(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    _shut_it(session_factory, user.login)
    with session_factory() as session:
        blocked = UserRepository().accounts_blocked_from_signing_in(session)
    assert user.login in [record.login for record in blocked]
    _age_the_row(session_factory, user.login, sql_interval="1 hour")
    with session_factory() as session:
        after = UserRepository().accounts_blocked_from_signing_in(session)
    assert user.login not in [record.login for record in after], (
        "a block that has passed is not a block, and the query asks the database's clock"
    )


def test_the_check_command_reports_a_shut_account_without_changing_its_status(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """A lockout expires on its own, so a checklist that failed over one would fail over
    somebody mistyping a password five minutes ago. A default credential does not expire,
    which is why that one *is* the status."""
    before = _run("auditmanager.access.check")
    _shut_it(session_factory, user.login)
    after = _run("auditmanager.access.check")
    assert BLOCKED_PREFIX in after.stdout
    assert user.login in after.stdout
    assert "unlock" in after.stdout, "the report names the way back"
    assert after.returncode == before.returncode, (
        "reporting a lockout must not move a status that is about default credentials"
    )
    # And the two states are reported under different prefixes, so a scraper cannot read
    # one as the other. They have different remedies.
    assert BLOCKED_PREFIX != FINDING_PREFIX
    assert not BLOCKED_PREFIX.startswith(FINDING_PREFIX)


def test_the_check_command_says_nothing_about_an_account_that_is_not_shut(
    user: UserRecord
) -> None:
    result = _run("auditmanager.access.check")
    assert f"{BLOCKED_PREFIX}: login={user.login}" not in result.stdout


# =======================================================================================
# One property of the module the brake could have broken, asserted so that it cannot.
# =======================================================================================


def test_no_statement_in_this_path_returns_credential_material(
    user: UserRecord, session_factory: sessionmaker[Session]
) -> None:
    """`W39-REVOKE`'s load-bearing sentence, re-asserted because `W40-LIMIT` widened the
    statement that reads the digest. The extra column it projects is a boolean about a
    cooling-off period; nothing about the digest may travel with it."""
    _shut_it(session_factory, user.login)
    with session_factory() as session:
        blocked = UserRepository().accounts_blocked_from_signing_in(session)
    for record in [_row(session_factory, user.login), *blocked]:
        fields = set(type(record).__dataclass_fields__)
        for forbidden in (
            "password_algorithm",
            "password_iterations",
            "password_salt",
            "password_hash",
        ):
            assert forbidden not in fields, forbidden
        assert passwords.ALGORITHM not in repr(record)
