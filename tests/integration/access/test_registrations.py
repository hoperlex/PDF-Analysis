"""Registration requests: submit, approve, reject, status read, constant work -- no router.

`W49-ACCESS-01c`, `W49-PLAN.md` §3.3, `R-56`.
"""

from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access import passwords
from auditmanager.access.accounts import AccountRepository
from auditmanager.access.passwords import StoredPassword, verify_password
from auditmanager.access.registrations import (
    MAX_PENDING_REQUESTS,
    RegistrationRecord,
    RegistrationRepository,
)
from auditmanager.access.repository import FAILED_SIGN_IN_ALLOWANCE, UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "an-applicant-password"  # noqa: S105 - a test literal
WRONG = "not-the-applicant-password"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()
registrations = RegistrationRepository()


def _seed(session: Session) -> str:
    record = users.find_by_login(session, "admin")
    assert record is not None
    return str(record.user_uid)


def _submit(session: Session, email: str = "anna@example.com", **extra) -> RegistrationRecord:
    record = registrations.submit(
        session,
        login=extra.pop("login", email),
        password=extra.pop("password", PASSWORD),
        last_name=extra.pop("last_name", "Петрова"),
        first_name=extra.pop("first_name", "Анна"),
        middle_name=extra.pop("middle_name", None),
    )
    session.commit()
    return record


def _stored(session: Session, request_id: str):
    return session.execute(
        text(
            "SELECT password_algorithm, password_iterations, password_salt, password_hash, "
            "failed_sign_ins, sign_in_blocked_until FROM registration_request "
            "WHERE request_id = :r"
        ),
        {"r": request_id},
    ).one()


@pytest.fixture
def derivations(monkeypatch) -> list[int]:
    """Every PBKDF2 derivation that completes, counted."""
    calls: list[int] = []
    original = passwords._derive

    def counting(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(1)
        return result

    monkeypatch.setattr(passwords, "_derive", counting)
    return calls


# =======================================================================================
# Submit.
# =======================================================================================


class TestSubmit:
    def test_a_request_is_pending_with_its_password_hashed(self, session: Session) -> None:
        record = _submit(
            session, login=" Anna@Example.COM ", last_name=" Петрова ", middle_name="Сергеевна"
        )
        assert record.status == "pending"
        assert record.login == "anna@example.com"
        assert (record.last_name, record.middle_name) == ("Петрова", "Сергеевна")
        assert record.request_id.startswith("reg_")
        assert record.display_label == "Петрова А. С."
        assert not {"password_hash", "password_salt"} & set(RegistrationRecord.__dataclass_fields__)
        algorithm, iterations, salt, digest, *_ = _stored(session, record.request_id)
        assert verify_password(StoredPassword(algorithm, int(iterations), salt, digest), PASSWORD)
        plaintext = session.execute(
            text("SELECT count(*) FROM registration_request WHERE password_hash = :p"),
            {"p": PASSWORD},
        ).scalar_one()
        assert plaintext == 0

    def test_a_login_an_active_account_holds_is_login_taken(self, session: Session) -> None:
        with pytest.raises(DomainError) as caught:
            _submit(session, login="admin")
        assert caught.value.code is ErrorCode.VALIDATION_FAILED, "a new login is an e-mail"
        users.create_user(session, "anna@example.com", PASSWORD)
        session.commit()
        with pytest.raises(DomainError) as caught:
            _submit(session)
        assert caught.value.code is ErrorCode.CONFLICT
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}

    def test_an_archived_accounts_login_may_be_requested(self, session: Session) -> None:
        uid = str(users.create_user(session, "anna@example.com", PASSWORD).user_uid)
        accounts.archive_account(session, actor_uid=_seed(session), user_uid=uid)
        session.commit()
        assert _submit(session).status == "pending"

    def test_a_second_pending_request_is_request_pending(self, session: Session) -> None:
        _submit(session)
        with pytest.raises(DomainError) as caught:
            _submit(session, login="ANNA@example.com")
        assert caught.value.detail_fields == {"conflict_reason": "request_pending"}

    def test_the_queue_holds_100_and_refuses_the_101st(self, session: Session) -> None:
        """99 rows written directly (each submit costs a derivation), then the 100th and
        101st through the repository."""
        for index in range(MAX_PENDING_REQUESTS - 1):
            session.execute(
                text(
                    "INSERT INTO registration_request (request_id, login, last_name, "
                    "first_name, password_algorithm, password_iterations, password_salt, "
                    "password_hash) VALUES (:rid, :login, 'Петрова', 'Анна', "
                    "'pbkdf2_sha256', 600000, :s, :d)"
                ),
                {
                    "rid": f"reg_01ARZ3NDEKTSV4RRFFQ69G{index:04d}",
                    "login": f"applicant{index}@example.com",
                    "s": "0" * 32,
                    "d": "0" * 64,
                },
            )
        session.commit()
        assert _submit(session, "hundredth@example.com").status == "pending"
        assert registrations.pending_total(session) == MAX_PENDING_REQUESTS
        with pytest.raises(DomainError) as caught:
            _submit(session, "overflow@example.com")
        assert caught.value.detail_fields == {"conflict_reason": "queue_full"}

    @pytest.mark.parametrize(
        ("password", "fragment"),
        [
            ("short", "at least 8"),
            ("AuditManager", "product's name"),
            ("Password", "ships with"),
            ("Anastasia.Petrova@Example.com", "own login"),
            ("ANASTASIA.PETROVA", "own name or e-mail"),
            ("константинова", "own name or e-mail"),
            ("АЛЕКСАНДРА", "own name or e-mail"),
            ("Сергеевна", "own name or e-mail"),
        ],
        ids=["length", "product", "default", "login", "local-part", "last-name",
             "first-name", "middle-name"],
    )
    def test_the_password_policy_includes_the_applicants_own_facts(
        self, session: Session, password: str, fragment: str
    ) -> None:
        """Every fact here is at least 8 characters, so the length floor cannot be what
        refuses it (measured: mutation M01c-15 survived a version with shorter facts)."""
        with pytest.raises(DomainError) as caught:
            _submit(
                session,
                login="anastasia.petrova@example.com",
                password=password,
                last_name="Константинова",
                first_name="Александра",
                middle_name="Сергеевна",
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert fragment in str(caught.value)

    def test_a_refused_name_writes_nothing(self, session: Session) -> None:
        with pytest.raises(DomainError):
            _submit(session, last_name="Петрoва")
        session.rollback()
        assert registrations.pending_total(session) == 0


# =======================================================================================
# Approve and reject.
# =======================================================================================


class TestApprove:
    def test_approval_creates_the_account_from_the_request_in_one_transaction(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        request = _submit(session, middle_name="Сергеевна")
        decided, account = registrations.approve(
            session, actor_uid=seed, request_id=request.request_id, roles=["expert"]
        )
        session.commit()
        assert decided.status == "approved"
        assert decided.decided_by == seed and decided.created_user_uid == str(account.user_uid)
        assert account.login == "anna@example.com"
        assert account.profile_complete and account.is_default_credential is False
        assert account.display_label == "Петрова А. С."
        assert accounts.roles_of(session, str(account.user_uid)) == frozenset({"expert"})
        granted_by = session.execute(
            text("SELECT granted_by FROM app_user_role WHERE user_uid = :u"),
            {"u": str(account.user_uid)},
        ).scalar_one()
        assert granted_by == seed
        assert tuple(_stored(session, request.request_id))[:4] == (None, None, None, None)
        assert users.authenticate(session, "anna@example.com", PASSWORD) is not None

    @pytest.mark.parametrize("roles", [[], ["root"]], ids=["none", "unknown"])
    def test_approval_grants_at_least_one_known_role(self, session: Session, roles) -> None:
        request = _submit(session)
        with pytest.raises(DomainError) as caught:
            registrations.approve(
                session, actor_uid=_seed(session), request_id=request.request_id, roles=roles
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert caught.value.detail_fields == {"field": "roles"}

    def test_a_decided_request_cannot_be_decided_again(self, session: Session) -> None:
        seed = _seed(session)
        request = _submit(session)
        registrations.reject(
            session, actor_uid=seed, request_id=request.request_id, reason="Не сейчас"
        )
        session.commit()
        with pytest.raises(DomainError) as caught:
            registrations.approve(
                session, actor_uid=seed, request_id=request.request_id, roles=["expert"]
            )
        assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
        assert caught.value.detail_fields == {
            "machine": "registration_request",
            "current_state": "rejected",
            "requested_state": "approved",
        }

    def test_a_login_taken_meanwhile_leaves_the_request_pending(self, session: Session) -> None:
        request = _submit(session)
        users.create_user(session, "anna@example.com", PASSWORD)
        session.commit()
        with pytest.raises(DomainError) as caught:
            registrations.approve(
                session, actor_uid=_seed(session), request_id=request.request_id, roles=["expert"]
            )
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}
        session.rollback()
        assert registrations.get(session, request.request_id).status == "pending"

    def test_an_unknown_request_is_not_found(self, session: Session) -> None:
        with pytest.raises(DomainError) as caught:
            registrations.approve(
                session,
                actor_uid=_seed(session),
                request_id="reg_01ARZ3NDEKTSV4RRFFQ69G5FAA",
                roles=["expert"],
            )
        assert caught.value.code is ErrorCode.NOT_FOUND

    def test_two_concurrent_approvals_one_wins_the_other_is_a_transition(
        self, migrated_engine: Engine
    ) -> None:
        with Session(migrated_engine) as setup:
            seed = _seed(setup)
            request_id = _submit(setup).request_id
        outcome: dict[str, object] = {}
        first = Session(migrated_engine)
        registrations.approve(first, actor_uid=seed, request_id=request_id, roles=["expert"])

        def second() -> None:
            with Session(migrated_engine) as other:
                other.execute(text("SET lock_timeout = '20s'"))
                try:
                    registrations.approve(
                        other, actor_uid=seed, request_id=request_id, roles=["admin"]
                    )
                    other.commit()
                    outcome["second"] = "approved"
                except DomainError as exc:
                    outcome["second"] = exc.code

        worker = threading.Thread(target=second)
        worker.start()
        waiting = 0
        deadline = time.monotonic() + 5
        # A fresh connection per probe: pg_stat_activity is a per-transaction snapshot
        # (stats_fetch_consistency = cache), so one connection polling inside one transaction
        # would read the first answer for ever.
        while time.monotonic() < deadline and not outcome:
            with migrated_engine.connect() as probe:
                waiting = probe.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    )
                ).scalar_one()
            if waiting:
                break
            time.sleep(0.05)
        first.commit()
        first.close()
        worker.join(30)
        assert outcome == {"second": ErrorCode.STATE_TRANSITION_NOT_ALLOWED}
        assert waiting, "the second approval never waited on the request's lock"
        with Session(migrated_engine) as check:
            created = check.execute(
                text("SELECT count(*) FROM app_user WHERE login = 'anna@example.com'")
            ).scalar_one()
        assert created == 1


class TestReject:
    def test_a_rejection_records_the_reason_and_nulls_the_password(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        request = _submit(session)
        decided = registrations.reject(
            session,
            actor_uid=seed,
            request_id=request.request_id,
            reason="  Нет подтверждения\nот руководителя  ",
        )
        session.commit()
        assert decided.status == "rejected"
        assert decided.rejection_reason == "Нет подтверждения\nот руководителя"
        assert decided.created_user_uid is None
        assert tuple(_stored(session, request.request_id))[:4] == (None, None, None, None)

    @pytest.mark.parametrize(
        "reason", ["", "   ", "x" * 257, "tab\there", "null\x00byte"],
        ids=["empty", "blank", "257", "tab", "nul"],
    )
    def test_a_reason_outside_1_to_256_or_with_control_characters_is_refused(
        self, session: Session, reason: str
    ) -> None:
        request = _submit(session)
        with pytest.raises(DomainError) as caught:
            registrations.reject(
                session, actor_uid=_seed(session), request_id=request.request_id, reason=reason
            )
        assert caught.value.detail_fields == {"field": "reason"}

    def test_256_characters_is_the_bound(self, session: Session) -> None:
        request = _submit(session)
        decided = registrations.reject(
            session, actor_uid=_seed(session), request_id=request.request_id, reason="я" * 256
        )
        assert len(decided.rejection_reason) == 256


def test_listing_and_the_badge(session: Session) -> None:
    seed = _seed(session)
    first = _submit(session, "anna@example.com")
    second = _submit(session, "boris@example.com")
    registrations.reject(session, actor_uid=seed, request_id=first.request_id, reason="Нет")
    session.commit()
    assert registrations.pending_total(session) == 1
    assert [r.request_id for r in registrations.list_requests(session, status="pending")] == [
        second.request_id
    ]
    assert len(registrations.list_requests(session)) == 2
    with pytest.raises(DomainError):
        registrations.list_requests(session, status="archived")


def test_the_account_approval_created_can_be_purged_and_the_request_survives(
    session: Session,
) -> None:
    seed = _seed(session)
    request = _submit(session)
    _, account = registrations.approve(
        session, actor_uid=seed, request_id=request.request_id, roles=["expert"]
    )
    uid = str(account.user_uid)
    accounts.archive_account(session, actor_uid=seed, user_uid=uid)
    accounts.purge_account(session, actor_uid=seed, user_uid=uid)
    session.commit()
    survivor = registrations.get(session, request.request_id)
    assert survivor.status == "approved" and survivor.created_user_uid is None
    assert survivor.decided_by == seed


# =======================================================================================
# The status read, its brake and its cost.
# =======================================================================================


class TestTheStatusRead:
    def test_a_proven_pair_reads_pending(self, session: Session) -> None:
        _submit(session)
        status = registrations.read_status(session, login="Anna@Example.com", password=PASSWORD)
        assert status is not None and status.status == "pending"
        assert status.decided_at is None and status.rejection_reason is None

    @pytest.mark.parametrize(
        ("login", "password"),
        [
            ("anna@example.com", WRONG),
            ("nobody@example.com", PASSWORD),
            ("admin", PASSWORD),
            ("not an address", PASSWORD),
        ],
        ids=["wrong-password", "no-request", "legacy-login", "malformed"],
    )
    def test_anything_else_is_the_generic_none(self, session: Session, login, password) -> None:
        _submit(session)
        assert registrations.read_status(session, login=login, password=password) is None

    def test_a_decided_request_is_not_disclosed_without_a_password_to_prove(
        self, session: Session
    ) -> None:
        """The conservative reading of §3.3 (open question in the 01c report): the
        decision nulled the password, so nothing can prove the pair any more."""
        seed = _seed(session)
        request = _submit(session)
        registrations.reject(
            session, actor_uid=seed, request_id=request.request_id, reason="Нет"
        )
        session.commit()
        assert registrations.read_status(
            session, login="anna@example.com", password=PASSWORD
        ) is None

    def test_failed_reads_are_braked_and_the_brake_ignores_the_right_password(
        self, session: Session
    ) -> None:
        request = _submit(session)
        for _ in range(FAILED_SIGN_IN_ALLOWANCE):
            assert registrations.read_status(
                session, login="anna@example.com", password=WRONG
            ) is None
        session.commit()
        *_, failed, blocked_until = _stored(session, request.request_id)
        assert failed == FAILED_SIGN_IN_ALLOWANCE and blocked_until is not None
        assert registrations.read_status(
            session, login="anna@example.com", password=PASSWORD
        ) is None

    def test_a_proven_read_clears_the_brake(self, session: Session) -> None:
        request = _submit(session)
        registrations.read_status(session, login="anna@example.com", password=WRONG)
        registrations.read_status(session, login="anna@example.com", password=PASSWORD)
        session.commit()
        assert tuple(_stored(session, request.request_id))[4] == 0

    def test_a_failed_exchange_counts_against_the_request(self, session: Session) -> None:
        request = _submit(session)
        assert users.authenticate(session, "anna@example.com", PASSWORD) is None
        session.commit()
        assert tuple(_stored(session, request.request_id))[4] == 1


class TestConstantWork:
    """`W49-PLAN.md` §3.3: the same number of derivations whether or not a request exists."""

    def test_every_status_read_path_costs_exactly_one_derivation(
        self, session: Session, derivations: list[int]
    ) -> None:
        seed = _seed(session)
        _submit(session, "pending@example.com")
        decided = _submit(session, "rejected@example.com")
        registrations.reject(session, actor_uid=seed, request_id=decided.request_id, reason="Нет")
        braked = _submit(session, "braked@example.com")
        session.execute(
            text(
                "UPDATE registration_request SET failed_sign_ins = 5, sign_in_blocked_until = "
                "now() + interval '5 minutes' WHERE request_id = :r"
            ),
            {"r": braked.request_id},
        )
        session.commit()
        paths = {
            "proven": ("pending@example.com", PASSWORD),
            "wrong-password": ("pending@example.com", WRONG),
            "no-request": ("nobody@example.com", PASSWORD),
            "decided": ("rejected@example.com", PASSWORD),
            "braked": ("braked@example.com", PASSWORD),
            "malformed": ("not an address", PASSWORD),
        }
        cost = {}
        for name, (login, password) in paths.items():
            derivations.clear()
            registrations.read_status(session, login=login, password=password)
            cost[name] = len(derivations)
        assert cost == {name: 1 for name in paths}

    def test_a_failed_exchange_costs_one_derivation_with_or_without_a_request(
        self, session: Session, derivations: list[int]
    ) -> None:
        _submit(session, "pending@example.com")
        derivations.clear()
        assert users.authenticate(session, "pending@example.com", PASSWORD) is None
        with_request = len(derivations)
        derivations.clear()
        assert users.authenticate(session, "nobody@example.com", PASSWORD) is None
        assert with_request == len(derivations) == 1
