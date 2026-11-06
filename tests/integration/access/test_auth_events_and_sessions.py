"""Contract 1.36.0 (`UI-A-92`, `UI-A-93`, `UI-A-94`): the last sign-in, ending an account's sessions, the access journal.

Real PostgreSQL, a private migrated clone per test, the shipped adapters behind the served surface. What is asserted
is read back over a **separate connection**, so a row counts only if it is committed.

* ``Account.last_sign_in_at`` is the journal's latest ``sign_in_succeeded`` of that account, ``null`` before one;
* ``endUserSessions`` raises the credential epoch (the account's next request is ``401``), journals
  ``sessions_ended`` in the same commit, is keyed (an exact repeat ends nothing more, another account under the key is
  ``idempotency_key_reuse``), and is refused for oneself, an archived account and a non-administrator -- with no event
  and no consumed key;
* ``listAuthEvents`` is administrator-only, newest first, cursor-paged without a gap or a repeat, names the people by
  label (``null`` once an account is deleted), and its rows hold nothing but the writer's allow-listed facts.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterator
from datetime import timezone
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access import audit
from auditmanager.access.accounts import AccountRepository
from auditmanager.access.journal import last_sign_in_times, read_access_events
from auditmanager.access.registrations import RegistrationRepository
from auditmanager.access.repository import UserRepository
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import AccountAdapter, CredentialAdapter, RegistrationAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "journal-suite-password-7731"  # noqa: S105 - a test literal
DEPLOYMENT_SECRET = "c2-suite-deployment-secret"  # noqa: S105

users = UserRepository()
accounts = AccountRepository()


def _create(session: Session, email: str, *, roles: tuple[str, ...]) -> str:
    uid = str(users.create_user(session, email, PASSWORD).user_uid)
    accounts.complete_profile(
        session, user_uid=uid, email=None, last_name="Петрова", first_name="Анна"
    )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    session.commit()
    return uid


@pytest.fixture
def client(migrated_engine: Engine) -> Iterator[TestClient]:
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
    yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def cast(migrated_engine: Engine) -> dict[str, str]:
    with Session(migrated_engine) as session:
        return {
            "admin": _create(session, "c2.admin@suite.invalid", roles=("expert", "admin")),
            "expert": _create(session, "c2.expert@suite.invalid", roles=("expert",)),
            "other": _create(session, "c2.other@suite.invalid", roles=("expert",)),
        }


def _sign_in(client: TestClient, login: str) -> str:
    answer = client.post("/auth/token", json={"login": login, "password": PASSWORD})
    assert answer.status_code == 200, answer.text
    return str(answer.json()["token"])


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _keyed(token: str, key: str | None = None) -> dict[str, str]:
    return {**_bearer(token), "Idempotency-Key": key or f"c2-{secrets.token_hex(8)}"}


def _events(engine: Engine, event_type: str) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT aggregate_id, payload FROM audit_event WHERE event_type = :t ORDER BY sequence_no"
            ),
            {"t": event_type},
        ).mappings().all()
    return [dict(row) for row in rows]


def _epoch(engine: Engine, uid: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(
            text("SELECT token_epoch FROM app_user WHERE user_uid = :u"), {"u": uid}).scalar_one())


def _receipts(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(
            "SELECT count(*) FROM command_record WHERE command_type = 'end_user_sessions'")).scalar_one())


# --- the last sign-in -----------------------------------------------------------------------------------


class TestLastSignIn:
    def test_it_is_null_until_a_sign_in_and_is_the_latest_one_after(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        before = client.get(f"/users/{cast['expert']}", headers=_bearer(admin))
        assert before.status_code == 200, before.text
        assert before.json()["last_sign_in_at"] is None

        _sign_in(client, "c2.expert@suite.invalid")
        _sign_in(client, "c2.expert@suite.invalid")
        with migrated_engine.connect() as connection:
            latest = connection.execute(text(
                "SELECT max(occurred_at) FROM audit_event WHERE event_type = 'access.sign_in_succeeded' "
                "AND aggregate_id = :u"), {"u": cast["expert"]}).scalar_one()
        after = client.get(f"/users/{cast['expert']}", headers=_bearer(admin)).json()
        assert after["last_sign_in_at"] is not None
        assert after["last_sign_in_at"] == latest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def test_the_list_and_the_account_itself_carry_it(
        self, client: TestClient, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        _sign_in(client, "c2.other@suite.invalid")
        listed = client.get("/users?limit=200", headers=_bearer(admin)).json()["items"]
        by_uid = {item["user_uid"]: item for item in listed}
        assert by_uid[cast["admin"]]["last_sign_in_at"] is not None
        assert by_uid[cast["other"]]["last_sign_in_at"] is not None
        assert by_uid[cast["expert"]]["last_sign_in_at"] is None
        me = client.get("/me", headers=_bearer(admin)).json()
        assert me["last_sign_in_at"] == by_uid[cast["admin"]]["last_sign_in_at"]

    def test_a_refused_sign_in_is_not_a_sign_in(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        refused = client.post("/auth/token", json={"login": "c2.expert@suite.invalid", "password": "not-the-password-1"})
        assert refused.status_code == 401
        with Session(migrated_engine) as session:
            assert last_sign_in_times(session, [cast["expert"]]) == {}

    def test_the_read_is_one_statement_for_the_set_and_empty_for_none(
        self, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        with Session(migrated_engine) as session:
            assert last_sign_in_times(session, []) == {}
            audit.record_sign_in_succeeded(session, subject_uid=cast["expert"], default_credential=False)
            audit.record_sign_in_succeeded(session, subject_uid=cast["expert"], default_credential=False)
            audit.record_sign_in_succeeded(session, subject_uid=cast["other"], default_credential=False)
            session.commit()
            found = last_sign_in_times(session, [cast["expert"], cast["other"], cast["admin"]])
            assert set(found) == {cast["expert"], cast["other"]}  # the account that never signed in is absent
            latest = session.execute(text(
                "SELECT max(occurred_at) FROM audit_event WHERE event_type = 'access.sign_in_succeeded' "
                "AND aggregate_id = :u"), {"u": cast["expert"]}).scalar_one()
            assert found[cast["expert"]] == latest  # the later of the two events, not the first


# --- ending the sessions --------------------------------------------------------------------------------


class TestEndUserSessions:
    def test_the_next_request_of_the_account_is_unauthenticated_and_the_event_is_journalled(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        first = _sign_in(client, "c2.expert@suite.invalid")
        second = _sign_in(client, "c2.expert@suite.invalid")  # a second browser
        assert client.get("/me", headers=_bearer(first)).status_code == 200
        epoch = _epoch(migrated_engine, cast["expert"])

        ended = client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin))
        assert ended.status_code == 200, ended.text
        body = ended.json()
        assert body["user_uid"] == cast["expert"] and body["archived_at"] is None
        assert _epoch(migrated_engine, cast["expert"]) == epoch + 1
        for credential in (first, second):
            assert client.get("/me", headers=_bearer(credential)).status_code == 401
        assert _events(migrated_engine, "access.sessions_ended") == [
            {"aggregate_id": cast["expert"],
             "payload": {"subject_uid": cast["expert"], "actor_uid": cast["admin"], "source": "api"}}]
        # nothing else changed: the same password signs in again, the roles stand
        again = _sign_in(client, "c2.expert@suite.invalid")
        assert client.get("/me", headers=_bearer(again)).json()["roles"] == ["expert"]

    def test_an_exact_repeat_of_the_key_ends_nothing_more(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        key = f"c2-{secrets.token_hex(8)}"
        first = client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin, key))
        assert first.status_code == 200, first.text
        epoch = _epoch(migrated_engine, cast["expert"])
        signed_in_after = _sign_in(client, "c2.expert@suite.invalid")
        repeat = client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin, key))
        assert repeat.status_code == 200, repeat.text
        assert _epoch(migrated_engine, cast["expert"]) == epoch
        assert len(_events(migrated_engine, "access.sessions_ended")) == 1
        # the replay did not end the session opened between the two calls
        assert client.get("/me", headers=_bearer(signed_in_after)).status_code == 200

    def test_the_key_under_another_account_is_a_reuse(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        key = f"c2-{secrets.token_hex(8)}"
        assert client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin, key)).status_code == 200
        reused = client.post(f"/users/{cast['other']}/sessions/end", headers=_keyed(admin, key))
        assert reused.status_code == 409, reused.text
        assert reused.json()["error_code"] == "idempotency_key_reuse"
        assert len(_events(migrated_engine, "access.sessions_ended")) == 1

    def test_a_new_key_ends_the_sessions_again(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        for _ in range(2):
            assert client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin)).status_code == 200
        assert len(_events(migrated_engine, "access.sessions_ended")) == 2

    def test_a_refusal_writes_no_event_and_consumes_no_key(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        epoch = _epoch(migrated_engine, cast["admin"])
        key = f"c2-{secrets.token_hex(8)}"
        own = client.post(f"/users/{cast['admin']}/sessions/end", headers=_keyed(admin, key))
        assert own.status_code == 403, own.text
        assert own.json()["error_code"] == "permission_denied"
        assert "details" not in own.json()
        assert _epoch(migrated_engine, cast["admin"]) == epoch
        assert client.get("/me", headers=_bearer(admin)).status_code == 200

        assert client.post(f"/users/{cast['other']}/archive", headers=_bearer(admin)).status_code == 200
        archived = client.post(f"/users/{cast['other']}/sessions/end", headers=_keyed(admin))
        assert archived.status_code == 404, archived.text
        missing = client.post(
            "/users/usr_01M2545JSD15ETSNNV904X99ZZ/sessions/end", headers=_keyed(admin))
        assert missing.status_code == 404, missing.text

        assert _events(migrated_engine, "access.sessions_ended") == []
        assert _receipts(migrated_engine) == 0  # the claims rolled back with the refusals
        # the key a refusal did not consume is still free for the account it was meant for
        ok = client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin, key))
        assert ok.status_code == 200, ok.text

    def test_the_key_is_required_and_the_role_is_the_administrators(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        keyless = client.post(f"/users/{cast['expert']}/sessions/end", headers=_bearer(admin))
        assert keyless.status_code == 422, keyless.text
        expert = _sign_in(client, "c2.expert@suite.invalid")
        denied = client.post(f"/users/{cast['other']}/sessions/end", headers=_keyed(expert))
        assert denied.status_code == 403, denied.text
        anonymous = client.post(f"/users/{cast['other']}/sessions/end", headers={"Idempotency-Key": "c2-anonymous-1"})
        assert anonymous.status_code == 401, anonymous.text
        assert _events(migrated_engine, "access.sessions_ended") == []

    def test_the_event_and_the_epoch_commit_together(
        self, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        with Session(migrated_engine) as session:
            accounts.end_sessions(session, actor_uid=cast["admin"], user_uid=cast["expert"])
            session.rollback()
        assert _events(migrated_engine, "access.sessions_ended") == []
        before = _epoch(migrated_engine, cast["expert"])  # the rolled-back raise left the epoch where it was
        with Session(migrated_engine) as session:
            accounts.end_sessions(session, actor_uid=cast["admin"], user_uid=cast["expert"])
            session.commit()
        assert _epoch(migrated_engine, cast["expert"]) == before + 1
        assert len(_events(migrated_engine, "access.sessions_ended")) == 1

    def test_the_rule_is_the_access_boundarys(
        self, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        with Session(migrated_engine) as session:
            with pytest.raises(DomainError) as own:
                accounts.end_sessions(session, actor_uid=cast["admin"], user_uid=cast["admin"])
            assert own.value.code is ErrorCode.PERMISSION_DENIED
            session.rollback()
            with pytest.raises(DomainError) as missing:
                accounts.end_sessions(session, actor_uid=cast["admin"], user_uid="usr_01M2545JSD15ETSNNV904X99ZZ")
            assert missing.value.code is ErrorCode.NOT_FOUND


# --- the journal ----------------------------------------------------------------------------------------


def _walk(client: TestClient, cast: dict[str, str]) -> str:
    """A sign-in of each kind of actor, a password reset, a role change and an end of sessions; returns the admin token."""
    admin = _sign_in(client, "c2.admin@suite.invalid")
    _sign_in(client, "c2.expert@suite.invalid")
    assert client.patch(
        f"/users/{cast['other']}", headers=_bearer(admin), json={"roles": ["admin"]}).status_code == 200
    assert client.post(
        f"/users/{cast['other']}/password", headers=_bearer(admin),
        json={"temporary_password": "temporary-phrase-from-c2-17"}).status_code == 200
    assert client.post(f"/users/{cast['expert']}/sessions/end", headers=_keyed(admin)).status_code == 200
    return admin


class TestListAuthEvents:
    def test_only_an_administrator_reads_it(self, client: TestClient, cast: dict[str, str]) -> None:
        expert = _sign_in(client, "c2.expert@suite.invalid")
        assert client.get("/auth-events", headers=_bearer(expert)).status_code == 403
        assert client.get("/auth-events").status_code == 401

    def test_newest_first_with_both_people_named(self, client: TestClient, cast: dict[str, str]) -> None:
        admin = _walk(client, cast)
        answer = client.get("/auth-events?limit=200", headers=_bearer(admin))
        assert answer.status_code == 200, answer.text
        items = answer.json()["items"]
        kinds = [item["event_type"] for item in items]
        assert kinds[0] == "sessions_ended"
        assert {"sign_in_succeeded", "role_granted", "role_revoked", "password_reset", "sessions_ended"} <= set(kinds)
        times = [item["occurred_at"] for item in items]
        assert times == sorted(times, reverse=True)
        top = items[0]
        assert top["subject_user_uid"] == cast["expert"] and top["subject_label"] == "Петрова А."
        assert top["actor_user_uid"] == cast["admin"] and top["actor_label"] == "Петрова А."
        assert top["source"] == "api"
        assert (top["role"], top["failures"], top["default_credential"]) == (None, None, None)
        sign_in = next(item for item in items if item["event_type"] == "sign_in_succeeded")
        assert sign_in["actor_user_uid"] is None and sign_in["actor_label"] is None
        assert sign_in["default_credential"] is False
        granted = next(item for item in items if item["event_type"] == "role_granted"
                       and item["subject_user_uid"] == cast["other"] and item["actor_user_uid"] == cast["admin"])
        assert granted["role"] == "admin"
        # a closed shape: exactly the contract's eleven keys, whatever the type
        for item in items:
            assert set(item) == {
                "event_id", "event_type", "occurred_at", "subject_user_uid", "subject_label", "actor_user_uid",
                "actor_label", "source", "role", "failures", "default_credential"}

    def test_the_cursor_walks_every_event_once(self, client: TestClient, cast: dict[str, str]) -> None:
        admin = _walk(client, cast)
        everything = client.get("/auth-events?limit=200", headers=_bearer(admin)).json()
        assert everything["page"]["next_cursor"] is None
        wanted = [item["event_id"] for item in everything["items"]]
        assert len(wanted) >= 6
        walked: list[str] = []
        cursor: str | None = None
        pages = 0
        while True:
            query = "limit=2" + ("" if cursor is None else f"&cursor={cursor}")
            page = client.get(f"/auth-events?{query}", headers=_bearer(admin)).json()
            assert len(page["items"]) <= 2
            walked.extend(item["event_id"] for item in page["items"])
            pages += 1
            cursor = page["page"]["next_cursor"]
            if cursor is None:
                break
        assert walked == wanted and len(set(walked)) == len(walked)
        assert pages == (len(wanted) + 1) // 2

    def test_a_cursor_that_is_not_ours_is_refused_and_an_unknown_event_is_an_empty_page(
        self, client: TestClient, cast: dict[str, str]
    ) -> None:
        import base64

        admin = _walk(client, cast)

        def token(parts: list[str]) -> str:
            return base64.urlsafe_b64encode(json.dumps(parts).encode()).decode().rstrip("=")

        for bad in ("not-a-cursor", token(["a", "b"]), token(["admin"]), token(["evt_lowercase0000000000000000"])):
            refused = client.get(f"/auth-events?cursor={bad}", headers=_bearer(admin))
            assert refused.status_code == 422, (bad, refused.text)
        unknown = client.get(
            f"/auth-events?cursor={token(['evt_01M2545JSD15ETSNNV904X99ZZ'])}", headers=_bearer(admin))
        assert unknown.status_code == 200 and unknown.json()["items"] == []
        assert client.get("/auth-events?limit=0", headers=_bearer(admin)).status_code == 422

    def test_a_deleted_account_keeps_its_events_with_no_label(
        self, client: TestClient, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        admin = _sign_in(client, "c2.admin@suite.invalid")
        _sign_in(client, "c2.other@suite.invalid")
        assert client.post(f"/users/{cast['other']}/archive", headers=_bearer(admin)).status_code == 200
        assert client.delete(f"/users/{cast['other']}", headers=_bearer(admin)).status_code == 204
        items = client.get("/auth-events?limit=200", headers=_bearer(admin)).json()["items"]
        gone = [item for item in items if item["subject_user_uid"] == cast["other"]]
        assert gone, "the journal outlives the account"
        assert {item["subject_label"] for item in gone} == {None}

    def test_nothing_secret_and_no_login_reaches_the_answer(self, client: TestClient, cast: dict[str, str]) -> None:
        admin = _walk(client, cast)
        refused = client.post("/auth/token", json={"login": "someone.unknown@suite.invalid", "password": "wrong-guess-phrase-0042"})
        assert refused.status_code == 401
        raw = client.get("/auth-events?limit=200", headers=_bearer(admin)).text
        for forbidden in (PASSWORD, "temporary-phrase-from-c2-17", "wrong-guess-phrase-0042", "someone.unknown",
                          "c2.admin@suite.invalid", "c2.expert@suite.invalid", DEPLOYMENT_SECRET, admin):
            assert forbidden not in raw, forbidden

    def test_the_read_orders_by_time_and_the_writers_types_only(
        self, migrated_engine: Engine, cast: dict[str, str]
    ) -> None:
        with Session(migrated_engine) as session:
            audit.record_sign_in_succeeded(session, subject_uid=cast["expert"], default_credential=True)
            audit.record_sessions_ended(session, subject_uid=cast["expert"], actor_uid=cast["admin"])
            # a row of another family on the same aggregate type is not an access event
            session.execute(text(
                "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                "VALUES ('evt_01M2545JSD15ETSNNV904X99ZA', 'account.other_family', 'Account', :u, CAST('{}' AS jsonb))"),
                {"u": cast["expert"]})
            session.commit()
            rows = read_access_events(session, after_event_id=None, limit=10)
        assert [row.event_type for row in rows[:2]] == ["access.sessions_ended", "access.sign_in_succeeded"]
        assert rows[0].actor_uid == cast["admin"] and rows[1].default_credential is True
        assert "account.other_family" not in {row.event_type for row in rows}
