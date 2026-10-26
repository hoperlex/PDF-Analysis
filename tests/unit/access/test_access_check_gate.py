"""`PROD-02`: the narrower mode of ``python -m auditmanager.access.check`` -- ``--gate`` -- with no database.

``ADR-0023`` section 3 and ``R-146z``: a deployment is refused, and the application port
stays shut, while the **published pair** (``admin`` / ``password``) is valid. A temporary
password an administrator issued (``resetUserPassword`` also sets ``is_default_credential``)
is a warning line and never the refusal. The default mode keeps its sentinels because
``readiness.sh`` greps them.

Every row of that table is a case here, because the report is a function of facts already
read (:func:`gate_report`); the one fact that is *computed* -- does the stored credential
verify against the published password -- is :func:`seeded_account_accepts_the_published_password`
and has its own cases, including the one that matters most: a credential this build cannot
verify must not read as "no".

The statement that reads the credential and the wiring of :func:`run_gate` are driven with
fakes for ``Session``, the engine and the repository, so the suite proves what the gate does
*not* touch (``authenticate`` writes: it counts a failed attempt against the very account the
gate is reporting on, and a shut account answers "no" without consulting the password).
``tests/integration/composition/test_default_credential_gate.py`` drives the shell side.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from auditmanager.access import check
from auditmanager.access.models import UserRecord, UserUid
from auditmanager.access.passwords import StoredPassword, hash_password
from auditmanager.access.policy import SHIPPED_DEFAULT_PASSWORD
from auditmanager.shared.errors import DomainError

ROOT = Path(__file__).resolve().parents[3]
WHEN = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
SEEDED_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAA"
OTHER_UID = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAB"

#: One iteration: the cases are about *which* password verifies, not about the cost.
CHEAP = 1


def _stored(password: str) -> StoredPassword:
    return hash_password(password, iterations=CHEAP)


def _seeded(password: str = SHIPPED_DEFAULT_PASSWORD) -> check.SeededAccount:
    return check.SeededAccount(
        user_uid=SEEDED_UID, password_updated_at=WHEN, stored=_stored(password)
    )


def _record(login: str, uid: str = OTHER_UID) -> UserRecord:
    return UserRecord(
        user_uid=UserUid.parse(uid),
        login=login,
        is_default_credential=True,
        created_at=WHEN,
        password_updated_at=WHEN,
        token_epoch=0,
        token_epoch_updated_at=WHEN,
        failed_sign_ins=0,
        last_failed_sign_in_at=None,
        sign_in_blocked_until=None,
        display_name=None,
        last_name=None,
        first_name=None,
        middle_name=None,
        profile_completed_at=None,
        archived_at=None,
        archived_by=None,
    )


class TestWhatTheGateRefusesOver:
    """The table of ``ADR-0023`` commitment 9, one row per case."""

    def test_the_published_pair_is_the_finding_and_only_it(self) -> None:
        seeded = _seeded()
        lines, status = check.gate_report(seeded, True, [_record("admin", SEEDED_UID)])
        assert status == 1
        assert [line for line in lines if line.startswith(check.GATE_FINDING_PREFIX)] == [
            f"{check.GATE_FINDING_PREFIX}: login=admin user_uid={SEEDED_UID} "
            f"password_unchanged_since={WHEN.isoformat()}"
        ]
        assert check.GATE_CLEAN_SENTINEL not in lines
        # The seeded account is the finding; it is not also listed as a mere warning.
        assert not [line for line in lines if line.startswith(check.GATE_WARNING_PREFIX)]

    def test_a_temporary_password_an_administrator_issued_only_warns(self) -> None:
        temporary = _record("someone@example.invalid")
        lines, status = check.gate_report(_seeded("a-password-that-was-chosen"), False, [temporary])
        assert status == 0
        assert lines == [
            f"{check.GATE_WARNING_PREFIX}: login=someone@example.invalid "
            f"user_uid={OTHER_UID} password_unchanged_since={WHEN.isoformat()}",
            check.GATE_CLEAN_SENTINEL,
        ]

    def test_the_pair_valid_and_a_temporary_password_is_the_finding_with_the_warning(self) -> None:
        lines, status = check.gate_report(
            _seeded(), True, [_record("admin", SEEDED_UID), _record("someone@example.invalid")]
        )
        assert status == 1
        assert sum(line.startswith(check.GATE_FINDING_PREFIX) for line in lines) == 1
        warnings = [line for line in lines if line.startswith(check.GATE_WARNING_PREFIX)]
        assert len(warnings) == 1 and "login=someone@example.invalid" in warnings[0]

    @pytest.mark.parametrize("seeded", [None, "changed"])
    def test_nothing_on_the_published_pair_is_clean(self, seeded: str | None) -> None:
        account = None if seeded is None else _seeded("a-password-that-was-chosen")
        lines, status = check.gate_report(account, False, [])
        assert (lines, status) == ([check.GATE_CLEAN_SENTINEL], 0)

    def test_the_sentinel_is_the_last_line_when_there_is_no_finding(self) -> None:
        lines, _ = check.gate_report(None, False, [_record("a@example.invalid"), _record("b@example.invalid")])
        assert lines[-1] == check.GATE_CLEAN_SENTINEL
        assert len(lines) == 3


class TestWhatDecidesThatThePairIsValid:
    """The one computed fact. The flag ``is_default_credential`` is not consulted: the
    stored credential is."""

    def test_the_seeded_credential_verifies(self) -> None:
        assert check.seeded_account_accepts_the_published_password(_seeded()) is True

    def test_a_changed_password_does_not(self) -> None:
        assert check.seeded_account_accepts_the_published_password(_seeded("changed-since")) is False

    def test_the_published_password_in_another_case_is_not_the_published_password(self) -> None:
        assert check.seeded_account_accepts_the_published_password(_seeded("PASSWORD")) is False

    def test_no_such_account_is_not_a_finding(self) -> None:
        assert check.seeded_account_accepts_the_published_password(None) is False

    def test_a_credential_this_build_cannot_verify_is_an_error_and_not_a_no(self) -> None:
        """``verify_password`` raises on an unsupported algorithm; the gate lets that
        reach ``main`` (status 2) instead of turning it into ``False``, which a deploy
        would read as clean."""
        account = check.SeededAccount(
            user_uid=SEEDED_UID,
            password_updated_at=WHEN,
            stored=StoredPassword(algorithm="argon2", iterations=1, salt="00", digest="00"),
        )
        with pytest.raises(DomainError):
            check.seeded_account_accepts_the_published_password(account)

    def test_a_corrupt_digest_is_an_error_and_not_a_no(self) -> None:
        good = _stored(SHIPPED_DEFAULT_PASSWORD)
        account = check.SeededAccount(
            user_uid=SEEDED_UID,
            password_updated_at=WHEN,
            stored=StoredPassword(
                algorithm=good.algorithm, iterations=good.iterations, salt=good.salt, digest="not-hex"
            ),
        )
        with pytest.raises(DomainError):
            check.seeded_account_accepts_the_published_password(account)


class TestNothingSecretIsPrinted:
    def test_no_digest_salt_or_password_reaches_the_output(self) -> None:
        seeded = _seeded()
        lines, _ = check.gate_report(seeded, True, [_record("admin", SEEDED_UID)])
        text = "\n".join(lines)
        assert seeded.stored.salt not in text
        assert seeded.stored.digest not in text
        # The published password is public, but the gate has no business echoing the
        # attempt: the only place the word appears is the sentence about it.
        assert f"password={SHIPPED_DEFAULT_PASSWORD}" not in text
        assert re.search(r"[0-9a-f]{32,}", text) is None
        assert seeded.stored.salt not in repr(seeded)
        assert seeded.stored.digest not in repr(seeded)


class _Row:
    """What ``Session.execute(...).first()`` hands back."""

    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def first(self) -> tuple[Any, ...] | None:
        return self._row


class _FakeSession:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self.row = row
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any]) -> _Row:
        self.calls.append((str(statement), params))
        return _Row(self.row)


class TestTheStatementThatReadsTheCredential:
    def test_it_is_one_read_only_statement_addressed_to_the_active_seeded_login(self) -> None:
        stored = _stored(SHIPPED_DEFAULT_PASSWORD)
        session = _FakeSession(
            (SEEDED_UID, WHEN, stored.algorithm, stored.iterations, stored.salt, stored.digest)
        )
        account = check.read_seeded_account(session)  # type: ignore[arg-type]
        assert account == check.SeededAccount(SEEDED_UID, WHEN, stored)
        assert len(session.calls) == 1
        sql, params = session.calls[0]
        assert params == {"login": "admin"}
        assert sql.lstrip().upper().startswith("SELECT ")
        assert not re.search(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP)\b", sql, re.I)
        # An archived account holds its login without being able to sign in (`R-61`), so
        # it is not the published pair; the active holder is.
        assert "archived_at IS NULL" in sql and "login = :login" in sql
        # The lockout is deliberately NOT consulted: the pair is valid while the account is
        # shut for a minute, and a gate that read "shut" as "clean" would be wrong.
        assert "sign_in_blocked_until" not in sql
        for column in ("password_algorithm", "password_iterations", "password_salt", "password_hash"):
            assert column in sql

    def test_no_row_is_none(self) -> None:
        assert check.read_seeded_account(_FakeSession(None)) is None  # type: ignore[arg-type]


class _FakeEngine:
    disposed = False

    def dispose(self) -> None:
        self.disposed = True


class _ForbiddenRepository:
    """Has exactly the one method the gate may call. ``authenticate`` would write."""

    def __init__(self, must_change: tuple[UserRecord, ...]) -> None:
        self._must_change = must_change
        self.calls: list[str] = []

    def users_on_default_credentials(self, session: Any) -> tuple[UserRecord, ...]:
        self.calls.append("users_on_default_credentials")
        return self._must_change


@pytest.fixture()
def wired(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"row": None, "must_change": (), "engine": _FakeEngine()}

    class _SessionContext:
        def __init__(self, engine: Any) -> None:
            assert engine is state["engine"]

        def __enter__(self) -> _FakeSession:
            state["session"] = _FakeSession(state["row"])
            return state["session"]

        def __exit__(self, *exc: object) -> None:
            return None

    def _repository() -> _ForbiddenRepository:
        state["repository"] = _ForbiddenRepository(state["must_change"])
        return state["repository"]

    monkeypatch.setattr(check, "load_settings", lambda: object())
    monkeypatch.setattr(check, "create_database_engine", lambda _settings: state["engine"])
    monkeypatch.setattr(check, "Session", _SessionContext)
    monkeypatch.setattr(check, "UserRepository", _repository)
    return state


def _row(password: str) -> tuple[Any, ...]:
    stored = _stored(password)
    return (SEEDED_UID, WHEN, stored.algorithm, stored.iterations, stored.salt, stored.digest)


class TestRunGate:
    def test_the_pair_valid_exits_1_names_the_login_and_touches_nothing_else(
        self, wired: dict[str, Any], capsys: pytest.CaptureFixture[str]
    ) -> None:
        wired["row"] = _row(SHIPPED_DEFAULT_PASSWORD)
        wired["must_change"] = (_record("admin", SEEDED_UID),)
        assert check.run_gate() == 1
        out = capsys.readouterr().out
        assert f"{check.GATE_FINDING_PREFIX}: login=admin" in out
        assert check.GATE_CLEAN_SENTINEL not in out
        assert wired["repository"].calls == ["users_on_default_credentials"]
        assert len(wired["session"].calls) == 1
        assert wired["engine"].disposed is True

    def test_a_temporary_password_exits_0_with_a_warning(
        self, wired: dict[str, Any], capsys: pytest.CaptureFixture[str]
    ) -> None:
        wired["row"] = _row("chosen-after-the-seed")
        wired["must_change"] = (_record("reset@example.invalid"),)
        assert check.run_gate() == 0
        out = capsys.readouterr().out.splitlines()
        assert out[0].startswith(check.GATE_WARNING_PREFIX)
        assert out[-1] == check.GATE_CLEAN_SENTINEL

    def test_a_locked_seeded_account_is_still_a_finding(
        self, wired: dict[str, Any], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The row carries no lockout column at all, so a shut account cannot read as clean."""
        wired["row"] = _row(SHIPPED_DEFAULT_PASSWORD)
        assert check.run_gate() == 1
        assert check.GATE_FINDING_PREFIX in capsys.readouterr().out

    def test_the_engine_is_disposed_when_the_read_fails(self, wired: dict[str, Any]) -> None:
        wired["row"] = (SEEDED_UID, WHEN, "argon2", 1, "00", "00")
        with pytest.raises(DomainError):
            check.run_gate()
        assert wired["engine"].disposed is True


class TestMain:
    def test_no_argument_is_the_report_it_always_was(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(check, "run_check", lambda: 7)
        monkeypatch.setattr(check, "run_gate", lambda: 9)
        assert check.main() == 7
        assert check.main([]) == 7

    def test_gate_is_the_narrow_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(check, "run_check", lambda: 7)
        monkeypatch.setattr(check, "run_gate", lambda: 9)
        assert check.main(["--gate"]) == 9

    @pytest.mark.parametrize("argument", ["--gtae", "gate", "--gate=yes", "-g"])
    def test_an_argument_it_does_not_know_is_status_2_and_runs_neither(
        self, argument: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def _boom() -> int:
            raise AssertionError("must not run")

        monkeypatch.setattr(check, "run_check", _boom)
        monkeypatch.setattr(check, "run_gate", _boom)
        assert check.main([argument]) == 2
        assert "unrecognised argument" in capsys.readouterr().err

    def test_a_failure_to_read_or_to_verify_is_status_2_on_stderr(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def _fail() -> int:
            raise RuntimeError("no database")

        monkeypatch.setattr(check, "run_gate", _fail)
        assert check.main(["--gate"]) == 2
        captured = capsys.readouterr()
        assert "access-check FAILED: no database" in captured.err
        assert captured.out == ""


class TestTheTwoCopiesAndTheScriptsThatReadTheOutput:
    def test_the_seed_login_and_password_are_the_migrations(self) -> None:
        text = next((ROOT / "db/migrations/versions").glob("*_0006_*.py")).read_text(encoding="utf-8")
        login = re.search(r'^SEED_LOGIN = "([^"]+)"', text, re.M)
        password = re.search(r'^SEED_PASSWORD = "([^"]+)"', text, re.M)
        assert login is not None and password is not None
        assert check.SEEDED_ADMIN_LOGIN == login.group(1)
        assert SHIPPED_DEFAULT_PASSWORD == password.group(1)

    def test_the_default_mode_keeps_the_sentinels_readiness_reads(self) -> None:
        readiness = (ROOT / "infra/deploy/readiness.sh").read_text(encoding="utf-8")
        assert f"'^{check.CLEAN_SENTINEL}$'" in readiness
        assert f"'^{check.FINDING_PREFIX}" in readiness
        assert check.CLEAN_SENTINEL == "access-check OK no default credentials"
        assert check.FINDING_PREFIX == "access-check DEFAULT CREDENTIAL"

    def test_the_gate_prefixes_cannot_be_read_as_the_default_modes(self) -> None:
        assert not check.GATE_FINDING_PREFIX.startswith(check.FINDING_PREFIX)
        assert check.GATE_CLEAN_SENTINEL != check.CLEAN_SENTINEL
        assert check.GATE_WARNING_PREFIX != check.GATE_FINDING_PREFIX
