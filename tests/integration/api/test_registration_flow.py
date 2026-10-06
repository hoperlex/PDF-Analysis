"""`W49-SEAL-01c` -- the registration operations, end to end over real rows (`R-56`).

An applicant with no account submits, reads that the application is pending, and is told
nothing else: a rejected application's pair is answered exactly like an unknown pair. An
administrator lists, approves (one transaction, keyed) and rejects. Every rule is
``auditmanager.access``'s; this module asserts what the **served** operations answer, through
the shipped adapters and the shipped credential port, inside the suite's rolled-back
transaction.
"""

from __future__ import annotations

import json
import secrets
import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access import passwords
from auditmanager.access.repository import FAILED_SIGN_IN_ALLOWANCE
from w13_api_driver import Surface

from .identity_surface import ADMIN_ROLES, credential_for, identity_surface, make_account

PASSWORD = "applicant-password-4471"


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return identity_surface(session_factory)


@pytest.fixture
def admin(session: Session) -> str:
    return make_account(
        session,
        login=f"reg-admin-{secrets.token_hex(4)}@suite.invalid",
        names=("Админова", "Ольга", None),
        roles=ADMIN_ROLES,
    )


def _email() -> str:
    return f"applicant-{secrets.token_hex(5)}@suite.invalid"


def _submit(surface: Surface, login: str, password: str = PASSWORD) -> Any:
    return surface.send(
        "POST",
        "/registrations",
        headers={"Content-Type": "application/json"},
        body=json.dumps(
            {
                "login": login,
                "password": password,
                "last_name": "Заявкина",
                "first_name": "Мария",
                "middle_name": "Петровна",
            }
        ).encode("utf-8"),
        credential=None,
    )


def _status(surface: Surface, login: str, password: str = PASSWORD) -> Any:
    return surface.send(
        "POST",
        "/registrations/status",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"login": login, "password": password}).encode("utf-8"),
        credential=None,
    )


def _exchange(surface: Surface, login: str, password: str = PASSWORD) -> Any:
    """``issueToken``, unauthenticated -- the first half of a BFF sign-in."""
    return surface.send(
        "POST",
        "/auth/token",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"login": login, "password": password}).encode("utf-8"),
        credential=None,
    )


def _brake(session: Session, login: str) -> tuple[int, bool]:
    """The request's counter, and whether it is shut."""
    failed, blocked_until = session.execute(
        text(
            "SELECT failed_sign_ins, sign_in_blocked_until FROM registration_request "
            "WHERE login = :l"
        ),
        {"l": login},
    ).one()
    return int(failed), blocked_until is not None


def _request_id(session: Session, login: str) -> str:
    return session.execute(
        text(
            "SELECT request_id FROM registration_request WHERE login = :l "
            "ORDER BY submitted_at DESC LIMIT 1"
        ),
        {"l": login},
    ).scalar_one()


def _approve(
    surface: Surface, credential: str, request_id: str, roles: list[str], key: str
) -> Any:
    return surface.send(
        "POST",
        f"/registrations/{request_id}/approve",
        headers={"Content-Type": "application/json", "Idempotency-Key": key},
        body=json.dumps({"roles": roles}).encode("utf-8"),
        credential=credential,
    )


def _without_correlation(answer: Any) -> dict[str, Any]:
    body = answer.json()
    body.pop("correlation_id", None)
    return body


class TestTheApplicant:
    def test_a_submission_is_pending_and_names_nothing_else(self, surface: Surface) -> None:
        answer = _submit(surface, _email())
        assert answer.status == 201, answer.body
        assert answer.json() == {"status": "pending"}

    def test_the_pair_proves_a_pending_application(self, surface: Surface) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        answer = _status(surface, login)
        assert answer.status == 200, answer.body
        assert answer.json() == {"status": "pending"}

    def test_a_wrong_password_and_an_unknown_login_are_one_refusal(
        self, surface: Surface
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        wrong = _status(surface, login, "not-the-password-1")
        unknown = _status(surface, _email())
        assert wrong.status == unknown.status == 401
        assert _without_correlation(wrong) == _without_correlation(unknown)
        assert wrong.json()["error_code"] == "authentication_required"

    def test_a_refused_pair_is_counted_on_the_request(
        self, surface: Surface, session: Session
    ) -> None:
        """The status read writes: a refused attempt is counted on the request (the brake).

        The access boundary counts and leaves the commit to its caller, so this is the
        adapter's half -- a read that never committed would answer the same ``401`` and
        lose the count, and the brake would never engage.
        """
        login = _email()
        assert _submit(surface, login).status == 201
        assert _status(surface, login, "not-the-password-1").status == 401
        counted = session.execute(
            text("SELECT failed_sign_ins FROM registration_request WHERE login = :l"),
            {"l": login},
        ).scalar_one()
        assert counted == 1

    def test_a_second_pending_application_for_one_login_is_request_pending(
        self, surface: Surface
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        again = _submit(surface, login)
        assert again.status == 409, again.body
        assert again.json()["details"] == {"conflict_reason": "request_pending"}

    def test_a_login_an_active_account_holds_is_login_taken(
        self, surface: Surface, session: Session
    ) -> None:
        login = _email()
        make_account(session, login=login, names=("Занятова", "Анна", None))
        answer = _submit(surface, login)
        assert answer.status == 409, answer.body
        assert answer.json()["details"] == {"conflict_reason": "login_taken"}

    def test_the_password_policy_refuses_at_submission(self, surface: Surface) -> None:
        answer = _submit(surface, _email(), password="short")
        assert answer.status == 422, answer.body
        assert answer.json()["error_code"] == "validation_failed"

    def test_a_submission_without_a_name_is_refused_by_the_schema(
        self, surface: Surface
    ) -> None:
        answer = surface.send(
            "POST",
            "/registrations",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"login": _email(), "password": PASSWORD}).encode("utf-8"),
            credential=None,
        )
        assert answer.status == 422, answer.body
        assert answer.json()["details"]["constraint"] == "required"


class TestAPendingApplicantSigningIn:
    """`R-63` (`W49-QA-01` Q-1), through the served operations in the BFF's shape: a refused
    ``issueToken`` followed by ``readRegistrationStatus`` with the same pair. Only the status
    read counts against the request; the exchange spends its derivation and writes nothing."""

    def test_correct_sign_ins_beyond_the_allowance_are_never_throttled(
        self, surface: Surface, session: Session
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        for attempt in range(FAILED_SIGN_IN_ALLOWANCE + 2):
            assert _exchange(surface, login).status == 401
            assert _brake(session, login) == (0, False), f"exchange {attempt} was counted"
            answer = _status(surface, login)
            assert answer.status == 200, (attempt, answer.body)
            assert answer.json() == {"status": "pending"}

    def test_a_wrong_sign_in_costs_one_attempt_and_the_allowance_still_brakes(
        self, surface: Surface, session: Session
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        for attempt in range(FAILED_SIGN_IN_ALLOWANCE - 1):
            assert _exchange(surface, login, f"wrong-{attempt}").status == 401
            assert _status(surface, login, f"wrong-{attempt}").status == 401
        assert _brake(session, login) == (FAILED_SIGN_IN_ALLOWANCE - 1, False)
        # Q-1's sign-in: the right password after wrong ones, short of the allowance.
        assert _exchange(surface, login).status == 401
        assert _status(surface, login).status == 200, "a correct sign-in was refused"
        assert _brake(session, login) == (0, False)
        # The brake itself is unchanged: the allowance in wrong status reads shuts it.
        for attempt in range(FAILED_SIGN_IN_ALLOWANCE):
            assert _exchange(surface, login, f"again-{attempt}").status == 401
            assert _status(surface, login, f"again-{attempt}").status == 401
        assert _brake(session, login) == (FAILED_SIGN_IN_ALLOWANCE, True)
        assert _exchange(surface, login).status == 401
        assert _status(surface, login).status == 401

    def test_a_sign_in_costs_the_same_derivations_with_or_without_a_request(
        self, surface: Surface, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Constant work, unchanged by `R-63`: each half of a sign-in spends one PBKDF2
        derivation whether or not a request exists, and whichever password is offered."""
        calls: list[int] = []
        original = passwords._derive

        def counting(*args: Any, **kwargs: Any) -> Any:
            result = original(*args, **kwargs)
            calls.append(1)
            return result

        login = _email()
        assert _submit(surface, login).status == 201
        monkeypatch.setattr(passwords, "_derive", counting)
        cost: dict[str, tuple[int, int]] = {}
        for name, (who, password) in {
            "pending-right": (login, PASSWORD),
            "pending-wrong": (login, "not-the-password-2"),
            "no-request": (_email(), PASSWORD),
        }.items():
            calls.clear()
            assert _exchange(surface, who, password).status == 401
            exchanged = len(calls)
            calls.clear()
            _status(surface, who, password)
            cost[name] = (exchanged, len(calls))
        assert cost == {name: (1, 1) for name in cost}, cost


class TestTheAdministrator:
    def test_the_listing_carries_the_pending_total(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        answer = surface.send(
            "GET", "/registrations?status=pending&limit=200", credential=credential_for(session, admin)
        )
        assert answer.status == 200, answer.body
        body = answer.json()
        assert body["pending_total"] >= 1
        assert login in {item["login"] for item in body["items"]}
        assert {item["status"] for item in body["items"]} == {"pending"}

    def test_an_expert_without_admin_is_refused_by_the_seam(
        self, surface: Surface, session: Session
    ) -> None:
        expert = make_account(
            session,
            login=f"reg-expert-{secrets.token_hex(4)}@suite.invalid",
            names=("Экспертова", "Ия", None),
            roles=("expert",),
        )
        answer = surface.send("GET", "/registrations", credential=credential_for(session, expert))
        assert answer.status == 403, answer.body
        assert answer.json()["details"] == {"required_capability": "role:admin"}

    def test_approval_creates_a_complete_account_with_the_chosen_roles(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        request_id = _request_id(session, login)
        answer = _approve(
            surface, credential_for(session, admin), request_id, ["expert"], f"a-{uuid.uuid4()}"
        )
        assert answer.status == 200, answer.body
        body = answer.json()
        assert body["status"] == "approved"
        assert body["decided_by"] == admin
        assert body["created_user_uid"]
        account = surface.send(
            "GET", f"/users/{body['created_user_uid']}", credential=credential_for(session, admin)
        )
        assert account.status == 200, account.body
        created = account.json()
        assert created["login"] == login
        assert created["profile_complete"] is True
        assert created["roles"] == ["expert"]
        assert created["display_label"] == "Заявкина М. П."
        # The applicant signs in with the password they applied with: the account took the
        # request's digest, and the request no longer holds it.
        assert _status(surface, login).status == 401

    def test_an_identical_approval_replays_and_another_payload_is_a_reused_key(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        request_id = _request_id(session, login)
        credential = credential_for(session, admin)
        key = f"a-{uuid.uuid4()}"
        first = _approve(surface, credential, request_id, ["expert"], key)
        assert first.status == 200, first.body
        replay = _approve(surface, credential, request_id, ["expert"], key)
        assert replay.status == 200, replay.body
        assert replay.json() == first.json()
        reused = _approve(surface, credential, request_id, ["admin"], key)
        assert reused.status == 409, reused.body
        assert reused.json()["error_code"] == "idempotency_key_reuse"

    def test_a_decided_request_is_a_transition_the_machine_refuses(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        request_id = _request_id(session, login)
        credential = credential_for(session, admin)
        assert _approve(surface, credential, request_id, ["expert"], f"a-{uuid.uuid4()}").status == 200
        again = _approve(surface, credential, request_id, ["expert"], f"a-{uuid.uuid4()}")
        assert again.status == 409, again.body
        envelope = again.json()
        assert envelope["error_code"] == "state_transition_not_allowed"
        assert envelope["details"] == {
            "machine": "registration_request",
            "current_state": "approved",
            "requested_state": "approved",
        }

    def test_an_approval_needs_a_role(self, surface: Surface, session: Session, admin: str) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        answer = _approve(
            surface,
            credential_for(session, admin),
            _request_id(session, login),
            [],
            f"a-{uuid.uuid4()}",
        )
        assert answer.status == 422, answer.body
        assert answer.json()["details"] == {"field": "roles", "constraint": "length"}

    def test_a_role_named_twice_is_refused(self, surface: Surface, session: Session, admin: str) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        answer = _approve(
            surface,
            credential_for(session, admin),
            _request_id(session, login),
            ["expert", "expert"],
            f"a-{uuid.uuid4()}",
        )
        assert answer.status == 422, answer.body
        assert answer.json()["details"] == {"field": "roles", "constraint": "uniqueItems"}

    def test_a_rejection_keeps_its_reason_for_administrators_only(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        request_id = _request_id(session, login)
        answer = surface.send(
            "POST",
            f"/registrations/{request_id}/reject",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"reason": "Нет в списке экспертов."}).encode("utf-8"),
            credential=credential_for(session, admin),
        )
        assert answer.status == 200, answer.body
        body = answer.json()
        assert body["status"] == "rejected"
        assert body["rejection_reason"] == "Нет в списке экспертов."
        assert body["created_user_uid"] is None
        # `R-56` addendum: the applicant learns nothing -- the pair is answered exactly like
        # an unknown one, byte for byte apart from the correlation id.
        rejected = _status(surface, login)
        unknown = _status(surface, _email())
        assert rejected.status == unknown.status == 401
        assert _without_correlation(rejected) == _without_correlation(unknown)

    def test_a_repeated_rejection_is_a_refused_transition(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        """Rejection takes no ``Idempotency-Key`` (`P02_SEAMS.md` §7): a repeat is the
        machine's refusal, never a second decision."""
        login = _email()
        assert _submit(surface, login).status == 201
        request_id = _request_id(session, login)
        credential = credential_for(session, admin)

        def reject() -> Any:
            return surface.send(
                "POST",
                f"/registrations/{request_id}/reject",
                headers={"Content-Type": "application/json"},
                body=json.dumps({"reason": "Повтор."}).encode("utf-8"),
                credential=credential,
            )

        assert reject().status == 200
        again = reject()
        assert again.status == 409, again.body
        assert again.json()["details"] == {
            "machine": "registration_request",
            "current_state": "rejected",
            "requested_state": "rejected",
        }

    def test_a_reason_over_256_characters_is_refused(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        login = _email()
        assert _submit(surface, login).status == 201
        answer = surface.send(
            "POST",
            f"/registrations/{_request_id(session, login)}/reject",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"reason": "x" * 257}).encode("utf-8"),
            credential=credential_for(session, admin),
        )
        assert answer.status == 422, answer.body

    def test_an_unknown_request_is_not_found(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        answer = _approve(
            surface,
            credential_for(session, admin),
            "reg_01M2545JSD15ETSNNV904X99ZZ",
            ["expert"],
            f"a-{uuid.uuid4()}",
        )
        assert answer.status == 404, answer.body
