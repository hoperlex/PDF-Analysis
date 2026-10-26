"""`PROD-06`: the six ``access.*`` audit events (ADR-0023 section 4, ``R-146n`` item 6, ``AD-10``).

Real PostgreSQL, a private migrated clone per test. What is asserted is read back from
``audit_event`` over a **separate connection**, so a row counts only if it is committed.

* every event type has a test per code path that writes it -- the repository (sign-in, blocked,
  password change, reset, role grant and revoke, registration approval), the host command run
  as an operator runs it, and the served API (``issueToken``, ``changePassword``,
  ``approveRegistration``, ``updateUser``, ``resetUserPassword``);
* an attempt that starts no cooling-off period, an unknown login and a refused change write
  nothing (ADR-0023 section 4: the table cannot be grown by guessing);
* the event and the change commit or roll back **together**; a failing event aborts the change;
* no secret and no IP in any stored row: the API test sends distinctive passwords, an
  ``X-Forwarded-For`` address, a client address and a user agent, then scans every stored row of
  every ``access.*`` type for each value, and checks every key against the writer's allow-list;
* the correlation seam carries the request's id when bound and ``NULL`` otherwise.

Every guard here was shown failing under a mutation; the table is in
``docs/program/PROD-06-ACCESS-AUDIT-01.md``.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access import audit
from auditmanager.access.accounts import (
    LAST_ADMIN,
    SELF_ACTION,
    AccountInvariantViolation,
    AccountRepository,
)
from auditmanager.access.grant import run_grant
from auditmanager.access.registrations import RegistrationRepository
from auditmanager.access.repository import (
    COOLING_OFF_SECONDS,
    FAILED_SIGN_IN_ALLOWANCE,
    UserRepository,
)
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import (
    AccountAdapter,
    CredentialAdapter,
    RegistrationAdapter,
)
from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.errors import DomainError
from tests.integration.db.conftest import run_foundation_command  # type: ignore[import-not-found]

PASSWORD = "a-long-enough-password-7731"  # noqa: S105 - a test literal
SEED_PASSWORD = "password"  # noqa: S105 - the published 0006 default
GRANT = [".venv/bin/python", "-m", "auditmanager.access.grant"]

users = UserRepository()
accounts = AccountRepository()
registrations = RegistrationRepository()


# --- helpers -------------------------------------------------------------------------------------


def _events(engine: Engine, event_type: str | None = None) -> list[dict[str, Any]]:
    """The committed ``access.*`` rows, oldest first, as plain dictionaries."""
    sql = (
        "SELECT event_type, aggregate_type, aggregate_id, correlation_id, payload "
        "FROM audit_event WHERE starts_with(event_type, 'access.') "
        + ("AND event_type = :t " if event_type else "")
        + "ORDER BY sequence_no"
    )
    with engine.connect() as connection:
        rows = connection.execute(text(sql), {"t": event_type} if event_type else {}).mappings().all()
    return [dict(row) for row in rows]


def _count(engine: Engine) -> int:
    return len(_events(engine))


def _seed_uid(session: Session) -> str:
    record = users.find_by_login(session, "admin")
    assert record is not None
    return str(record.user_uid)


def _create(session: Session, email: str, *, roles: tuple[str, ...] = ("expert",)) -> str:
    uid = str(users.create_user(session, email, PASSWORD).user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    session.commit()
    return uid


def _role_set(engine: Engine, uid: str) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(
            text("SELECT role FROM app_user_role WHERE user_uid = :u"), {"u": uid}).scalars())


# --- sign-in -------------------------------------------------------------------------------------


class TestSignIn:
    def test_an_accepted_password_appends_one_event_in_the_same_commit(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _seed_uid(session)
        assert _count(migrated_engine) == 0
        assert users.authenticate(session, "admin", SEED_PASSWORD) is not None
        # not visible to another connection before the commit: it rides the caller's transaction
        assert _count(migrated_engine) == 0
        session.commit()
        (event,) = _events(migrated_engine)
        assert event["event_type"] == "access.sign_in_succeeded"
        assert event["aggregate_type"] == "Account" and event["aggregate_id"] == uid
        assert event["payload"] == {"subject_uid": uid, "source": "api", "default_credential": True}

    def test_the_default_credential_flag_is_the_rows_own_answer(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "anna@example.com")
        assert users.authenticate(session, "anna@example.com", PASSWORD) is not None
        session.commit()
        (event,) = _events(migrated_engine, "access.sign_in_succeeded")
        assert event["payload"] == {"subject_uid": uid, "source": "api", "default_credential": False}

    def test_a_refusal_that_starts_no_cooling_off_writes_nothing(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        _create(session, "anna@example.com")
        baseline = _count(migrated_engine)
        for _ in range(FAILED_SIGN_IN_ALLOWANCE - 1):
            assert users.authenticate(session, "anna@example.com", "wrong-password-0000") is None
            session.commit()
        # an unknown login, and a login that could not have been stored, write nothing either
        assert users.authenticate(session, "nobody@example.com", PASSWORD) is None
        assert users.authenticate(session, "not a login!", PASSWORD) is None
        session.commit()
        assert _count(migrated_engine) == baseline

    def test_the_attempt_that_starts_a_cooling_off_is_journalled_once_per_period(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "anna@example.com")
        for _ in range(FAILED_SIGN_IN_ALLOWANCE):
            assert users.authenticate(session, "anna@example.com", "wrong-password-0000") is None
            session.commit()
        (blocked,) = _events(migrated_engine, "access.sign_in_blocked")
        assert blocked["aggregate_type"] == "Account" and blocked["aggregate_id"] == uid
        assert blocked["payload"] == {
            "subject_uid": uid, "source": "api", "failures": FAILED_SIGN_IN_ALLOWANCE}
        # knocking on a shut door -- wrong password or the right one -- adds nothing
        for password in ("wrong-password-0000", PASSWORD, "wrong-password-1111"):
            assert users.authenticate(session, "anna@example.com", password) is None
            session.commit()
        assert len(_events(migrated_engine, "access.sign_in_blocked")) == 1
        assert _events(migrated_engine, "access.sign_in_succeeded") == []
        assert COOLING_OFF_SECONDS == 300  # the period the "once per period" bound is stated in

    def test_the_password_proof_of_a_change_moves_the_same_brake_and_is_journalled_once(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "anna@example.com")
        for _ in range(FAILED_SIGN_IN_ALLOWANCE):
            assert users.change_password(
                session, user_uid=uid, current_password="wrong-password-0000",
                new_password="another-long-password-3") is None
            session.commit()
        (blocked,) = _events(migrated_engine, "access.sign_in_blocked")
        assert blocked["payload"]["subject_uid"] == uid
        assert _events(migrated_engine, "access.password_changed") == []


# --- passwords -----------------------------------------------------------------------------------


class TestPasswords:
    def test_a_password_change_appends_one_event_whose_actor_is_the_account(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "anna@example.com")
        record = users.change_password(
            session, user_uid=uid, current_password=PASSWORD, new_password="another-long-password-3")
        assert record is not None
        session.commit()
        (event,) = _events(migrated_engine, "access.password_changed")
        assert event["aggregate_type"] == "Account" and event["aggregate_id"] == uid
        assert event["payload"] == {"subject_uid": uid, "actor_uid": uid, "source": "api"}

    def test_a_refused_change_writes_nothing(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "anna@example.com")
        # wrong current password; the same password; a password below the policy floor
        assert users.change_password(
            session, user_uid=uid, current_password="wrong-password-0000",
            new_password="another-long-password-3") is None
        session.commit()
        for new in (PASSWORD, "short"):
            with pytest.raises(DomainError):
                users.change_password(
                    session, user_uid=uid, current_password=PASSWORD, new_password=new)
            session.rollback()
        assert _events(migrated_engine, "access.password_changed") == []

    def test_an_administrators_reset_appends_one_event_naming_both(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        uid = _create(session, "anna@example.com")
        accounts.reset_password(
            session, actor_uid=admin, user_uid=uid, temporary_password="temporary-password-55")
        session.commit()
        (event,) = _events(migrated_engine, "access.password_reset")
        assert event["aggregate_id"] == uid
        assert event["payload"] == {"subject_uid": uid, "actor_uid": admin, "source": "api"}

    def test_a_refused_reset_writes_nothing(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.reset_password(
                session, actor_uid=admin, user_uid=admin, temporary_password="temporary-password-55")
        assert caught.value.invariant == SELF_ACTION
        session.rollback()
        assert _events(migrated_engine, "access.password_reset") == []


# --- roles ---------------------------------------------------------------------------------------


class TestRoles:
    def test_an_administrators_set_names_what_moved_and_nothing_else(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        uid = _create(session, "anna@example.com", roles=("expert",))
        baseline = _count(migrated_engine)
        accounts.set_roles(session, actor_uid=admin, user_uid=uid, roles={"admin"})
        session.commit()
        granted, revoked = (
            _events(migrated_engine, "access.role_granted")[-1],
            _events(migrated_engine, "access.role_revoked")[-1],
        )
        assert _count(migrated_engine) == baseline + 2
        assert granted["aggregate_id"] == uid and revoked["aggregate_id"] == uid
        assert granted["payload"] == {
            "subject_uid": uid, "actor_uid": admin, "role": "admin", "source": "api"}
        assert revoked["payload"] == {
            "subject_uid": uid, "actor_uid": admin, "role": "expert", "source": "api"}
        # the same set again changes nothing and journals nothing
        accounts.set_roles(session, actor_uid=admin, user_uid=uid, roles={"admin"})
        session.commit()
        assert _count(migrated_engine) == baseline + 2

    def test_a_refused_removal_writes_nothing(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        expert = _create(session, "expert@example.com", roles=("expert",))
        baseline = _count(migrated_engine)
        # oneself: refused before any write
        with pytest.raises(AccountInvariantViolation) as own:
            accounts.set_roles(session, actor_uid=admin, user_uid=admin, roles={"expert"})
        assert own.value.invariant == SELF_ACTION
        session.rollback()
        # the last active administrator (the actor here is not one, so only this rule can refuse)
        with pytest.raises(AccountInvariantViolation) as last:
            accounts.set_roles(session, actor_uid=expert, user_uid=admin, roles={"expert"})
        assert last.value.invariant == LAST_ADMIN
        session.rollback()
        assert _count(migrated_engine) == baseline
        assert "admin" in _role_set(migrated_engine, admin)

    def test_the_host_style_grant_has_no_actor_and_the_administrators_has_one(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        uid = _create(session, "anna@example.com", roles=())
        baseline = _count(migrated_engine)
        assert accounts.grant_role(session, user_uid=uid, role="expert", granted_by=None)
        assert accounts.grant_role(session, user_uid=uid, role="admin", granted_by=admin)
        # a role already held changes nothing and journals nothing
        assert not accounts.grant_role(session, user_uid=uid, role="admin", granted_by=admin)
        session.commit()
        first, second = _events(migrated_engine, "access.role_granted")[-2:]
        assert _count(migrated_engine) == baseline + 2
        assert first["payload"] == {"subject_uid": uid, "role": "expert", "source": "host_cli"}
        assert second["payload"] == {
            "subject_uid": uid, "actor_uid": admin, "role": "admin", "source": "api"}

    def test_a_registration_approval_journals_each_role_it_grants_to_the_new_account(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        submitted = registrations.submit(
            session, login="applicant@example.com", password=PASSWORD,
            last_name="Заявкина", first_name="Мария")
        session.commit()
        decided, account = registrations.approve(
            session, actor_uid=admin, request_id=submitted.request_id, roles={"expert", "admin"})
        session.commit()
        events = _events(migrated_engine, "access.role_granted")
        assert [e["payload"]["role"] for e in events] == ["admin", "expert"]
        for event in events:
            assert event["aggregate_id"] == str(account.user_uid) == event["payload"]["subject_uid"]
            assert event["payload"]["actor_uid"] == admin and event["payload"]["source"] == "api"
        assert _role_set(migrated_engine, str(account.user_uid)) == {"expert", "admin"}
        assert decided.status == "approved"

    def test_a_rejection_and_a_refused_approval_write_nothing(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        submitted = registrations.submit(
            session, login="applicant@example.com", password=PASSWORD,
            last_name="Заявкина", first_name="Мария")
        session.commit()
        with pytest.raises(DomainError):  # no role chosen
            registrations.approve(
                session, actor_uid=admin, request_id=submitted.request_id, roles=set())
        session.rollback()
        registrations.reject(
            session, actor_uid=admin, request_id=submitted.request_id, reason="no vacancy")
        session.commit()
        assert _events(migrated_engine, "access.role_granted") == []


class TestTheHostCommand:
    """``python -m auditmanager.access.grant`` run as the operator runs it: a subprocess."""

    def test_the_command_journals_one_grant_with_no_actor_and_a_repeat_none(
        self, session: Session, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "clara@example.com", roles=())
        baseline = _count(migrated_engine)
        url = migrated_database.url.render_as_string(hide_password=False)

        first = run_foundation_command([*GRANT, "--login", "clara@example.com", "--role", "admin"], url)
        assert first.returncode == 0, first.describe()
        assert "access-grant GRANTED" in first.stdout
        (event,) = _events(migrated_engine, "access.role_granted")
        assert _count(migrated_engine) == baseline + 1
        assert event["aggregate_type"] == "Account" and event["aggregate_id"] == uid
        assert event["payload"] == {"subject_uid": uid, "role": "admin", "source": "host_cli"}
        assert "actor_uid" not in event["payload"]

        again = run_foundation_command([*GRANT, "--login", "clara@example.com", "--role", "admin"], url)
        assert again.returncode == 0 and "access-grant UNCHANGED" in again.stdout, again.describe()
        assert _count(migrated_engine) == baseline + 1

    def test_a_refused_command_journals_nothing(
        self, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        url = migrated_database.url.render_as_string(hide_password=False)
        missing = run_foundation_command([*GRANT, "--login", "nobody", "--role", "expert"], url)
        assert missing.returncode == 1, missing.describe()
        assert _count(migrated_engine) == 0

    def test_the_function_the_command_runs_commits_the_event_with_the_grant(
        self, session: Session, migrated_database: DatabaseSettings, migrated_engine: Engine
    ) -> None:
        uid = _create(session, "clara@example.com", roles=())
        assert run_grant(login="clara@example.com", role="expert", settings=migrated_database) == 0
        assert _role_set(migrated_engine, uid) == {"expert"}
        (event,) = _events(migrated_engine, "access.role_granted")
        assert event["payload"]["subject_uid"] == uid


# --- the transaction -----------------------------------------------------------------------------


class TestTheEventRidesTheChange:
    def test_a_rolled_back_change_leaves_neither_the_change_nor_its_event(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        admin = _seed_uid(session)
        uid = _create(session, "anna@example.com", roles=())
        baseline = _count(migrated_engine)
        accounts.grant_role(session, user_uid=uid, role="admin", granted_by=admin)
        accounts.set_roles(session, actor_uid=admin, user_uid=uid, roles={"expert"})
        accounts.reset_password(
            session, actor_uid=admin, user_uid=uid, temporary_password="temporary-password-55")
        users.authenticate(session, "admin", SEED_PASSWORD)
        session.rollback()
        assert _count(migrated_engine) == baseline
        assert _role_set(migrated_engine, uid) == set()

    def test_a_change_cannot_commit_when_its_event_cannot_be_written(
        self, session: Session, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The writer neither swallows its failure nor commits on its own: the grant aborts."""
        uid = _create(session, "anna@example.com", roles=())
        monkeypatch.setattr(audit, "AGGREGATE_TYPE", "x")  # the table's CHECK refuses it
        with pytest.raises(DBAPIError):
            accounts.grant_role(session, user_uid=uid, role="expert", granted_by=None)
        session.rollback()
        assert _role_set(migrated_engine, uid) == set()
        assert _events(migrated_engine) == []

    def test_a_failed_event_in_the_middle_of_an_approval_takes_the_account_with_it(
        self, session: Session, migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        admin = _seed_uid(session)
        submitted = registrations.submit(
            session, login="applicant@example.com", password=PASSWORD,
            last_name="Заявкина", first_name="Мария")
        session.commit()
        monkeypatch.setattr(audit, "AGGREGATE_TYPE", "x")
        with pytest.raises(DBAPIError):
            registrations.approve(
                session, actor_uid=admin, request_id=submitted.request_id, roles={"expert"})
        session.rollback()
        with migrated_engine.connect() as connection:
            assert connection.execute(text(
                "SELECT count(*) FROM app_user WHERE login = 'applicant@example.com'")).scalar_one() == 0
            assert connection.execute(text(
                "SELECT status FROM registration_request WHERE login = 'applicant@example.com'"
            )).scalar_one() == "pending"


class TestTheCorrelationSeam:
    def test_a_bound_id_lands_in_the_column_and_an_unbound_one_is_null(
        self, session: Session, migrated_engine: Engine
    ) -> None:
        uid = _seed_uid(session)
        audit.record_password_changed(session, subject_uid=uid)
        with audit.correlation_scope("cid-0123456789abcdef"):
            audit.record_password_changed(session, subject_uid=uid)
        audit.record_password_changed(session, subject_uid=uid)
        session.commit()
        assert [e["correlation_id"] for e in _events(migrated_engine)] == [
            None, "cid-0123456789abcdef", None]


# --- the served API, end to end, and the secrets scan ---------------------------------------------

DEPLOYMENT_SECRET = "prod-06-suite-deployment-secret"  # noqa: S105 - what the signing key derives from
CLIENT_ADDRESS = "198.51.100.9"
FORWARDED_ADDRESS = "203.0.113.77"
USER_AGENT = "prod06-scan-agent/9.9.9"
ADMIN_LOGIN = "admin.prod06@suite.invalid"
APPLICANT = "applicant.prod06@suite.invalid"
APPLICANT_PASSWORD = "applicant-secret-phrase-8841"  # noqa: S105
ADMIN_NEW_PASSWORD = "admin-brand-new-phrase-5520"  # noqa: S105
TEMPORARY_PASSWORD = "temporary-phrase-from-admin-31"  # noqa: S105
WRONG_PASSWORD = "wrong-guess-phrase-0042"  # noqa: S105


@pytest.fixture
def client(migrated_engine: Engine) -> Iterator[TestClient]:
    """The served surface over the shipped adapters and a private migrated database."""
    factory = sessionmaker(migrated_engine)
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None
    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            factory, users=UserRepository(), accounts=AccountRepository(), signer=signer),
        accounts=AccountAdapter(factory, accounts=AccountRepository()),
        registrations=RegistrationAdapter(factory, registrations=RegistrationRepository()),
    )

    class _Built:
        def __init__(self) -> None:
            from auditmanager.runs import InlineCarrier

            self.router = router
            self.carrier = InlineCarrier()

    app = create_asgi_app(environ={API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}, application=_Built())
    # not entered as a context manager: that would run the application's startup reconcile,
    # which needs a product session factory this suite does not build
    yield TestClient(
        app, raise_server_exceptions=False, client=(CLIENT_ADDRESS, 54321),
        headers={"X-Forwarded-For": FORWARDED_ADDRESS, "User-Agent": USER_AGENT},
    )


def _sign_in(client: TestClient, login: str, password: str) -> str | None:
    answer = client.post("/auth/token", json={"login": login, "password": password})
    return str(answer.json()["token"]) if answer.status_code == 200 else None


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _walk_through_every_event_type(client: TestClient, engine: Engine) -> list[str]:
    """Drive all six types through the served API; returns every token it was handed."""
    tokens: list[str] = []

    # The seeded administrator has no names yet, and the seam refuses an incomplete profile
    # every operation but its own profile and password; complete it the way its owner would,
    # leaving it on the seeded password.
    with Session(engine) as setup:
        seed = users.find_by_login(setup, "admin")
        assert seed is not None
        accounts.complete_profile(
            setup, user_uid=str(seed.user_uid), email=ADMIN_LOGIN,
            last_name="Админова", first_name="Ольга")
        setup.commit()

    first = _sign_in(client, ADMIN_LOGIN, SEED_PASSWORD)                    # sign_in_succeeded
    assert first is not None
    tokens.append(first)
    changed = client.post(                                                  # password_changed
        "/auth/password", headers=_bearer(first),
        json={"current_password": SEED_PASSWORD, "new_password": ADMIN_NEW_PASSWORD})
    assert changed.status_code == 200, changed.text
    tokens.append(str(changed.json()["token"]))

    admin = _sign_in(client, ADMIN_LOGIN, ADMIN_NEW_PASSWORD)                  # sign_in_succeeded (default: false)
    assert admin is not None
    tokens.append(admin)

    submitted = client.post("/registrations", json={
        "login": APPLICANT, "password": APPLICANT_PASSWORD,
        "last_name": "Заявкина", "first_name": "Мария", "middle_name": "Петровна"})
    assert submitted.status_code == 201, submitted.text
    with engine.connect() as connection:
        request_id = connection.execute(text(
            "SELECT request_id FROM registration_request WHERE login = :l"), {"l": APPLICANT}).scalar_one()
    approved = client.post(                                                 # role_granted x2
        f"/registrations/{request_id}/approve",
        headers={**_bearer(admin), "Idempotency-Key": f"prod06-{secrets.token_hex(6)}"},
        json={"roles": ["expert", "admin"]})
    assert approved.status_code == 200, approved.text
    with engine.connect() as connection:
        applicant_uid = connection.execute(text(
            "SELECT user_uid FROM app_user WHERE login = :l"), {"l": APPLICANT}).scalar_one()

    narrowed = client.patch(                                                # role_revoked
        f"/users/{applicant_uid}", headers=_bearer(admin), json={"roles": ["expert"]})
    assert narrowed.status_code == 200, narrowed.text
    reset = client.post(                                                    # password_reset
        f"/users/{applicant_uid}/password", headers=_bearer(admin),
        json={"temporary_password": TEMPORARY_PASSWORD})
    assert reset.status_code == 200, reset.text

    for _ in range(FAILED_SIGN_IN_ALLOWANCE):                               # sign_in_blocked (once)
        assert _sign_in(client, APPLICANT, WRONG_PASSWORD) is None
    return tokens


class TestTheServedApi:
    def test_all_six_types_are_written_by_the_served_operations_in_their_commit(
        self, client: TestClient, migrated_engine: Engine
    ) -> None:
        _walk_through_every_event_type(client, migrated_engine)
        by_type: dict[str, list[dict[str, Any]]] = {}
        for event in _events(migrated_engine):
            by_type.setdefault(event["event_type"], []).append(event)
        assert set(by_type) == set(audit.ACCESS_EVENT_TYPES)
        assert {t: len(v) for t, v in by_type.items()} == {
            "access.sign_in_succeeded": 2, "access.sign_in_blocked": 1, "access.role_granted": 2,
            "access.role_revoked": 1, "access.password_changed": 1, "access.password_reset": 1}
        flags = [e["payload"]["default_credential"] for e in by_type["access.sign_in_succeeded"]]
        assert flags == [True, False]  # the seeded password, then the one the administrator chose
        assert all(e["aggregate_type"] == "Account" for e in _events(migrated_engine))

    def test_a_refused_operation_writes_no_event(
        self, client: TestClient, migrated_engine: Engine
    ) -> None:
        assert _sign_in(client, "admin", WRONG_PASSWORD) is None
        assert _sign_in(client, "nobody@suite.invalid", WRONG_PASSWORD) is None
        token = _sign_in(client, "admin", SEED_PASSWORD)
        assert token is not None
        baseline = _count(migrated_engine)
        wrong = client.post(
            "/auth/password", headers=_bearer(token),
            json={"current_password": WRONG_PASSWORD, "new_password": ADMIN_NEW_PASSWORD})
        assert wrong.status_code == 401
        assert _count(migrated_engine) == baseline


class TestNoSecretAndNoAddressIsEverStored:
    def test_every_stored_row_of_every_access_type_is_clean(
        self, client: TestClient, migrated_engine: Engine
    ) -> None:
        tokens = _walk_through_every_event_type(client, migrated_engine)
        with migrated_engine.connect() as connection:
            credentials = connection.execute(text(
                "SELECT login, last_name, first_name, middle_name, password_salt, password_hash "
                "FROM app_user")).all()
            requests = connection.execute(text(
                "SELECT login, last_name, first_name, middle_name FROM registration_request")).all()
            # every stored column that carries a value the writer chose: the event type is a fixed
            # word of the ADR ("access.password_changed" contains the seeded password, innocently)
            whole_rows = [r[0] for r in connection.execute(text(
                "SELECT concat_ws('|', aggregate_type, aggregate_id, correlation_id, payload::text) "
                "FROM audit_event WHERE starts_with(event_type, 'access.')"))]
        assert len(whole_rows) == 8

        forbidden: dict[str, str] = {
            "seeded password": SEED_PASSWORD, "new admin password": ADMIN_NEW_PASSWORD,
            "applicant password": APPLICANT_PASSWORD, "temporary password": TEMPORARY_PASSWORD,
            "wrong guess": WRONG_PASSWORD, "client address": CLIENT_ADDRESS,
            "forwarded address": FORWARDED_ADDRESS, "user agent": USER_AGENT,
            "deployment secret": DEPLOYMENT_SECRET, "applicant e-mail": APPLICANT,
            "administrator e-mail": ADMIN_LOGIN,
        }
        forbidden.update({f"token {i}": token for i, token in enumerate(tokens)})
        for row in (*credentials, *requests):
            for position, value in enumerate(row):
                if value:
                    forbidden[f"stored value {position} of {row[0]}"] = str(value)
        # a stored value shorter than 5 characters ("admin", "password" are named above) would
        # match innocent text; the long ones -- digests, salts, tokens, names -- are what this is for
        scanned = {name: value for name, value in forbidden.items() if len(value) >= 5}
        assert len(scanned) >= 20
        for raw in whole_rows:
            for name, value in scanned.items():
                assert value not in raw, f"{name} appears in a stored access.* row: {raw}"

        # and structurally: only allow-listed keys, only scalars, only what the type permits
        allowed = set().union(*(required | optional for required, optional in audit.PAYLOAD_KEYS.values()))
        for event in _events(migrated_engine):
            required, optional = audit.PAYLOAD_KEYS[event["event_type"]]
            payload = event["payload"]
            assert required <= set(payload) <= required | optional, event
            assert set(payload) <= allowed
            assert all(isinstance(v, (str, int, bool)) and not isinstance(v, float) for v in payload.values())
            assert json.loads(json.dumps(payload)) == payload
