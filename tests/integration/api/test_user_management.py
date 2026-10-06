"""`W49-SEAL-01c` -- the account itself and account management, end to end (`R-55`, `R-59`, `R-61`).

``getMe`` and ``updateMyProfile`` for the account the credential names; the seven
administrator operations for the account the path names. The invariants are
``auditmanager.access``'s and are proven there without a router; what is asserted here is what
the **served** operations answer over real rows -- the codes, the closed detail values and
the revocation a change of rights carries -- through the shipped adapters and the shipped
credential port, inside the suite's rolled-back transaction.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.accounts import AccountInvariantViolation, LAST_ADMIN
from auditmanager.shared.errors import ErrorCode
from w13_api_driver import Surface

from .identity_surface import ADMIN_ROLES, credential_for, identity_surface, make_account


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return identity_surface(session_factory)


@pytest.fixture
def admin(session: Session) -> str:
    return make_account(
        session,
        login=f"um-admin-{secrets.token_hex(4)}@suite.invalid",
        names=("Админова", "Ольга", "Сергеевна"),
        roles=ADMIN_ROLES,
    )


@pytest.fixture
def expert(session: Session) -> str:
    return make_account(
        session,
        login=f"um-expert-{secrets.token_hex(4)}@suite.invalid",
        names=("Экспертов", "Иван", None),
        roles=("expert",),
    )


def _json(answer: Any) -> dict[str, Any]:
    return json.loads(answer.body)


def _send(surface: Surface, method: str, path: str, credential: str, body: Any = None) -> Any:
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    return surface.send(method, path, headers=headers, body=payload, credential=credential)


def _epoch(session: Session, user_uid: str) -> int:
    return int(
        session.execute(
            text("SELECT token_epoch FROM app_user WHERE user_uid = :u"), {"u": user_uid}
        ).scalar_one()
    )


class TestTheAccountItself:
    def test_get_me_reads_the_row_the_credential_names(
        self, surface: Surface, session: Session, expert: str
    ) -> None:
        answer = _send(surface, "GET", "/me", credential_for(session, expert))
        assert answer.status == 200, answer.body
        body = _json(answer)
        assert body["user_uid"] == expert
        assert body["display_label"] == "Экспертов И."
        assert body["roles"] == ["expert"]
        assert body["profile_complete"] is True
        assert body["archived_at"] is None

    def test_an_incomplete_legacy_account_completes_its_profile_in_one_write(
        self, surface: Surface, session: Session
    ) -> None:
        """`R-59`: the e-mail becomes the login, the names land, the profile is complete."""
        legacy = make_account(
            session, login=f"um-legacy-{secrets.token_hex(4)}", names=None, roles=("expert",)
        )
        credential = credential_for(session, legacy)
        before = _send(surface, "GET", "/me", credential)
        assert before.status == 200, before.body
        assert _json(before)["profile_complete"] is False
        # Refused everything else meanwhile, by the seam's incomplete-profile register.
        refused = _send(surface, "GET", "/users", credential)
        assert refused.status == 403, refused.body
        email = f"um-completed-{secrets.token_hex(4)}@suite.invalid"
        completed = _send(
            surface,
            "PATCH",
            "/me",
            credential,
            {"email": email, "last_name": "Наследова", "first_name": "Алла"},
        )
        assert completed.status == 200, completed.body
        body = _json(completed)
        assert body["login"] == email
        assert body["profile_complete"] is True
        assert body["display_label"] == "Наследова А."

    def test_a_legacy_account_without_an_email_is_refused_on_the_field(
        self, surface: Surface, session: Session
    ) -> None:
        legacy = make_account(session, login=f"um-legacy-{secrets.token_hex(4)}", names=None)
        answer = _send(
            surface,
            "PATCH",
            "/me",
            credential_for(session, legacy),
            {"last_name": "Наследова", "first_name": "Алла"},
        )
        assert answer.status == 422, answer.body
        assert _json(answer)["details"] == {"field": "email"}

    def test_a_complete_profile_changes_its_names_and_never_its_login(
        self, surface: Surface, session: Session, expert: str
    ) -> None:
        credential = credential_for(session, expert)
        renamed = _send(
            surface, "PATCH", "/me", credential, {"last_name": "Новиков", "first_name": "Иван"}
        )
        assert renamed.status == 200, renamed.body
        assert _json(renamed)["display_label"] == "Новиков И."
        moved = _send(
            surface,
            "PATCH",
            "/me",
            credential,
            {"last_name": "Новиков", "first_name": "Иван", "email": "other@suite.invalid"},
        )
        assert moved.status == 422, moved.body
        assert _json(moved)["details"] == {"field": "login"}

    def test_an_email_another_active_account_holds_is_login_taken(
        self, surface: Surface, session: Session, expert: str
    ) -> None:
        legacy = make_account(session, login=f"um-legacy-{secrets.token_hex(4)}", names=None)
        held = session.execute(
            text("SELECT login FROM app_user WHERE user_uid = :u"), {"u": expert}
        ).scalar_one()
        answer = _send(
            surface,
            "PATCH",
            "/me",
            credential_for(session, legacy),
            {"email": held, "last_name": "Дублёва", "first_name": "Ада"},
        )
        assert answer.status == 409, answer.body
        assert _json(answer)["details"] == {"conflict_reason": "login_taken"}


class TestAccountManagement:
    def test_listing_excludes_archived_accounts_unless_asked(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        assert _send(surface, "POST", f"/users/{expert}/archive", credential).status == 200
        default = _json(_send(surface, "GET", "/users?limit=200", credential))
        asked = _json(_send(surface, "GET", "/users?include_archived=true&limit=200", credential))
        assert expert not in {item["user_uid"] for item in default["items"]}
        assert expert in {item["user_uid"] for item in asked["items"]}

    def test_a_role_change_revokes_the_account_s_credentials(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        before = _epoch(session, expert)
        old_credential = credential_for(session, expert)
        answer = _send(
            surface,
            "PATCH",
            f"/users/{expert}",
            credential_for(session, admin),
            {"roles": ["expert", "admin"]},
        )
        assert answer.status == 200, answer.body
        assert _json(answer)["roles"] == ["admin", "expert"]
        assert _epoch(session, expert) == before + 1
        assert _send(surface, "GET", "/me", old_credential).status == 401

    def test_names_change_without_revoking(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        before = _epoch(session, expert)
        answer = _send(
            surface,
            "PATCH",
            f"/users/{expert}",
            credential_for(session, admin),
            {"names": {"last_name": "Переименов", "first_name": "Иван"}},
        )
        assert answer.status == 200, answer.body
        assert _json(answer)["display_label"] == "Переименов И."
        assert _epoch(session, expert) == before

    def test_an_administrator_cannot_demote_archive_reset_or_purge_themselves(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        credential = credential_for(session, admin)
        for method, path, body in (
            ("PATCH", f"/users/{admin}", {"roles": ["expert"]}),
            ("POST", f"/users/{admin}/archive", None),
            ("POST", f"/users/{admin}/password", {"temporary_password": "temporary-pass-91"}),
            ("DELETE", f"/users/{admin}", None),
        ):
            answer = _send(surface, method, path, credential, body)
            assert answer.status == 403, (path, answer.body)
            envelope = _json(answer)
            assert envelope["error_code"] == "permission_denied"
            assert "details" not in envelope, (path, envelope)

    def test_archive_restore_and_the_machine(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        archived = _send(surface, "POST", f"/users/{expert}/archive", credential)
        assert archived.status == 200, archived.body
        assert _json(archived)["archived_at"] is not None
        again = _send(surface, "POST", f"/users/{expert}/archive", credential)
        assert again.status == 409, again.body
        assert _json(again)["details"] == {
            "machine": "app_user",
            "current_state": "archived",
            "requested_state": "archived",
        }
        restored = _send(surface, "POST", f"/users/{expert}/restore", credential)
        assert restored.status == 200, restored.body
        assert _json(restored)["archived_at"] is None

    def test_an_archived_account_cannot_be_served(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, expert)
        assert _send(surface, "POST", f"/users/{expert}/archive", credential_for(session, admin)).status == 200
        assert _send(surface, "GET", "/me", credential).status == 401

    def test_purge_refuses_an_active_account_and_deletes_an_archived_unreferenced_one(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        active = _send(surface, "DELETE", f"/users/{expert}", credential)
        assert active.status == 409, active.body
        assert _json(active)["details"] == {
            "machine": "app_user",
            "current_state": "active",
            "requested_state": "purged",
        }
        assert _send(surface, "POST", f"/users/{expert}/archive", credential).status == 200
        purged = _send(surface, "DELETE", f"/users/{expert}", credential)
        assert purged.status == 204, purged.body
        assert purged.body == b""
        assert _send(surface, "GET", f"/users/{expert}", credential).status == 404

    def test_purge_refuses_an_account_that_archived_another(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        """`R-61`: an administrator who archived anything is referenced and stays."""
        other_admin = make_account(
            session,
            login=f"um-admin2-{secrets.token_hex(4)}@suite.invalid",
            names=("Второва", "Зоя", None),
            roles=ADMIN_ROLES,
        )
        assert _send(surface, "POST", f"/users/{expert}/archive", credential_for(session, other_admin)).status == 200
        credential = credential_for(session, admin)
        assert _send(surface, "POST", f"/users/{other_admin}/archive", credential).status == 200
        refused = _send(surface, "DELETE", f"/users/{other_admin}", credential)
        assert refused.status == 409, refused.body
        assert _json(refused)["details"] == {"conflict_reason": "account_referenced"}

    def test_a_reset_forces_the_change_and_revokes(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        before = _epoch(session, expert)
        answer = _send(
            surface,
            "POST",
            f"/users/{expert}/password",
            credential_for(session, admin),
            {"temporary_password": "temporary-pass-91"},
        )
        assert answer.status == 200, answer.body
        assert _json(answer)["is_default_credential"] is True
        assert _epoch(session, expert) == before + 1

    def test_an_unknown_account_is_not_found(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        answer = _send(
            surface, "GET", "/users/usr_01M2545JSD15ETSNNV904X99ZZ", credential_for(session, admin)
        )
        assert answer.status == 404, answer.body

    def test_a_malformed_identity_is_not_found_with_its_aggregate(
        self, surface: Surface, session: Session, admin: str
    ) -> None:
        answer = _send(surface, "GET", "/users/not-an-identity", credential_for(session, admin))
        assert answer.status == 404, answer.body
        assert _json(answer)["details"] == {"aggregate_type": "User"}


class TestARepeatWithoutAKey:
    """What each account write does when it is sent twice. None takes ``Idempotency-Key``.

    `docs/program/P02_SEAMS.md` §7 states these outcomes beside the writes that do take a
    key; this class is where they are measured, so the sentence cannot describe a surface
    that does something else.
    """

    def test_a_repeated_profile_completion_writes_the_same_state(
        self, surface: Surface, session: Session
    ) -> None:
        legacy = make_account(
            session, login=f"um-legacy-{secrets.token_hex(4)}", names=None, roles=("expert",)
        )
        credential = credential_for(session, legacy)
        body = {
            "email": f"um-repeat-{secrets.token_hex(4)}@suite.invalid",
            "last_name": "Повторова",
            "first_name": "Анна",
        }
        first = _send(surface, "PATCH", "/me", credential, body)
        assert first.status == 200, first.body
        epoch = _epoch(session, legacy)
        # The completion moved the login, not the epoch, so the same credential still works
        # -- and the repeat names the login the account now has, which is allowed.
        again = _send(surface, "PATCH", "/me", credential, body)
        assert again.status == 200, again.body
        assert _json(again) == _json(first)
        assert _epoch(session, legacy) == epoch

    def test_a_repeated_role_change_writes_the_same_set_and_revokes_once(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        before = _epoch(session, expert)
        first = _send(surface, "PATCH", f"/users/{expert}", credential, {"roles": ["expert", "admin"]})
        assert first.status == 200, first.body
        again = _send(surface, "PATCH", f"/users/{expert}", credential, {"roles": ["expert", "admin"]})
        assert again.status == 200, again.body
        assert _json(again) == _json(first)
        assert _epoch(session, expert) == before + 1

    def test_a_repeated_archive_or_restore_is_a_refused_transition(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        assert _send(surface, "POST", f"/users/{expert}/archive", credential).status == 200
        assert _send(surface, "POST", f"/users/{expert}/restore", credential).status == 200
        again = _send(surface, "POST", f"/users/{expert}/restore", credential)
        assert again.status == 409, again.body
        assert _json(again)["details"] == {
            "machine": "app_user",
            "current_state": "active",
            "requested_state": "active",
        }

    def test_a_repeated_purge_is_not_found(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        assert _send(surface, "POST", f"/users/{expert}/archive", credential).status == 200
        assert _send(surface, "DELETE", f"/users/{expert}", credential).status == 204
        again = _send(surface, "DELETE", f"/users/{expert}", credential)
        assert again.status == 404, again.body
        assert _json(again)["error_code"] == "not_found"

    def test_a_repeated_reset_repeats_its_effect(
        self, surface: Surface, session: Session, admin: str, expert: str
    ) -> None:
        credential = credential_for(session, admin)
        before = _epoch(session, expert)
        body = {"temporary_password": "temporary-pass-91"}
        assert _send(surface, "POST", f"/users/{expert}/password", credential, body).status == 200
        again = _send(surface, "POST", f"/users/{expert}/password", credential, body)
        assert again.status == 200, again.body
        assert _epoch(session, expert) == before + 2


def test_the_last_admin_refusal_carries_its_closed_reason() -> None:
    """`conflict_reason: last_admin` is a value the catalog admits on ``conflict``.

    Through the served surface the rule is unreachable by construction -- the actor of an
    administrator operation holds ``admin`` itself, so the target is never the last one --
    and the access suite proves it at the repository. What this module owns is the wire:
    the refusal the access boundary raises renders as the envelope the contract declares.
    """
    from auditmanager.shared.errors.envelope import screen_details

    refusal = AccountInvariantViolation(LAST_ADMIN, message="the last active administrator")
    assert refusal.code is ErrorCode.CONFLICT
    assert screen_details(refusal.code, refusal.detail_fields) == {
        "conflict_reason": "last_admin"
    }
    envelope = refusal.envelope("corr-last-admin").as_dict()
    assert envelope["details"] == {"conflict_reason": "last_admin"}
    assert envelope["retryable"] is False
