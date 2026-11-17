"""`UIP-G-05` (contract 1.56.0, owner ruling Г7-B) -- the object an account chose last, kept on the server.

``setMyLastProject`` (``PUT /me/last-project``) writes the signed-in account's choice; ``getMe`` and
``updateMyProfile`` read it back as ``last_project_uid``. What is asserted here is what the **served**
operations answer over real rows, through the shipped adapters and the shipped credential port, inside the
suite's rolled-back transaction: a write, a read, an exact replay, a reused key, an unknown object, the row going
with the account, and an object that is gone reading as no choice.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.identity.ids import ProjectUid
from w13_api_driver import Surface

from .identity_surface import ADMIN_ROLES, credential_for, identity_surface, make_account


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return identity_surface(session_factory)


@pytest.fixture
def person(session: Session) -> str:
    return make_account(
        session,
        login=f"lp-person-{secrets.token_hex(4)}@suite.invalid",
        names=("Выбиров", "Олег", None),
        roles=("expert",),
    )


@pytest.fixture
def admin(session: Session) -> str:
    return make_account(
        session,
        login=f"lp-admin-{secrets.token_hex(4)}@suite.invalid",
        names=("Админова", "Ольга", "Сергеевна"),
        roles=ADMIN_ROLES,
    )


def _project(session: Session) -> str:
    uid = str(ProjectUid.new())
    session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:uid, :name)"),
        {"uid": uid, "name": f"Объект {uid[-6:]}"},
    )
    return uid


def _key() -> str:
    return f"lp-{secrets.token_hex(8)}"


def _json(answer: Any) -> dict[str, Any]:
    return json.loads(answer.body)


def _choose(
    surface: Surface, credential: str, project_uid: str, *, key: str | None = None, body: Any = None
) -> Any:
    payload = {"project_uid": project_uid} if body is None else body
    headers = {"Content-Type": "application/json"}
    if key is not False:
        headers["Idempotency-Key"] = key or _key()
    return surface.send(
        "PUT", "/me/last-project", headers=headers, body=json.dumps(payload).encode("utf-8"), credential=credential
    )


def _me(surface: Surface, credential: str) -> dict[str, Any]:
    answer = surface.send("GET", "/me", credential=credential)
    assert answer.status == 200, answer.body
    return _json(answer)


def _row(session: Session, user_uid: str) -> tuple[str, Any] | None:
    found = session.execute(
        text("SELECT project_uid, selected_at FROM account_last_project WHERE user_uid = :u"), {"u": user_uid}
    ).one_or_none()
    return None if found is None else (found[0], found[1])


def _receipts(session: Session, key: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM command_record WHERE command_type = 'set_last_project' AND idempotency_key = :k"),
            {"k": key},
        ).scalar_one()
    )


class TestChoosingAnObject:
    def test_an_account_that_has_chosen_nothing_reads_null(self, surface: Surface, session: Session, person: str) -> None:
        body = _me(surface, credential_for(session, person))
        assert body["last_project_uid"] is None

    def test_the_choice_is_written_and_read_back(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        project = _project(session)
        answer = _choose(surface, credential, project)
        assert answer.status == 204, answer.body
        assert answer.body == b""
        assert _me(surface, credential)["last_project_uid"] == project
        assert _row(session, person) is not None and _row(session, person)[0] == project

    def test_choosing_another_object_replaces_the_choice(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        first, second = _project(session), _project(session)
        assert _choose(surface, credential, first).status == 204
        assert _choose(surface, credential, second).status == 204
        assert _me(surface, credential)["last_project_uid"] == second
        count = session.execute(
            text("SELECT count(*) FROM account_last_project WHERE user_uid = :u"), {"u": person}
        ).scalar_one()
        assert count == 1, "one row per account"

    def test_choosing_the_object_already_chosen_under_a_new_key_changes_nothing(
        self, surface: Surface, session: Session, person: str
    ) -> None:
        credential = credential_for(session, person)
        project = _project(session)
        assert _choose(surface, credential, project).status == 204
        before = _row(session, person)
        assert _choose(surface, credential, project).status == 204
        assert _row(session, person) == before, "selected_at is the instant of the latest change"

    def test_update_my_profile_carries_the_choice_too(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        project = _project(session)
        assert _choose(surface, credential, project).status == 204
        answer = surface.send(
            "PATCH",
            "/me",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"last_name": "Выбиров", "first_name": "Олег"}).encode("utf-8"),
            credential=credential,
        )
        assert answer.status == 200, answer.body
        assert _json(answer)["last_project_uid"] == project

    def test_an_administrators_read_of_another_account_does_not_carry_it(
        self, surface: Surface, session: Session, person: str, admin: str
    ) -> None:
        assert _choose(surface, credential_for(session, person), _project(session)).status == 204
        answer = surface.send("GET", f"/users/{person}", credential=credential_for(session, admin))
        assert answer.status == 200, answer.body
        assert "last_project_uid" not in _json(answer)

    def test_the_choice_belongs_to_the_credentials_account_only(
        self, surface: Surface, session: Session, person: str, admin: str
    ) -> None:
        project = _project(session)
        assert _choose(surface, credential_for(session, person), project).status == 204
        assert _me(surface, credential_for(session, admin))["last_project_uid"] is None
        # A body naming an account is refused: the shape has no such property.
        refused = _choose(
            surface, credential_for(session, admin), project, body={"project_uid": project, "user_uid": person}
        )
        assert refused.status == 422, refused.body
        assert _row(session, admin) is None

    def test_an_account_without_roles_may_choose(self, surface: Surface, session: Session) -> None:
        roleless = make_account(
            session, login=f"lp-roleless-{secrets.token_hex(4)}@suite.invalid", names=("Безролев", "Роман", None)
        )
        credential = credential_for(session, roleless)
        project = _project(session)
        assert _choose(surface, credential, project).status == 204
        assert _me(surface, credential)["last_project_uid"] == project

    def test_an_incomplete_profile_is_refused_like_every_other_operation_but_the_three(
        self, surface: Surface, session: Session
    ) -> None:
        legacy = make_account(
            session, login=f"lp-legacy-{secrets.token_hex(4)}", names=None, roles=("expert",)
        )
        answer = _choose(surface, credential_for(session, legacy), _project(session))
        assert answer.status == 403, answer.body
        assert _json(answer)["error_code"] == "permission_denied"
        assert _row(session, legacy) is None


class TestTheKey:
    def test_an_exact_repeat_changes_nothing_and_records_one_receipt(
        self, surface: Surface, session: Session, person: str
    ) -> None:
        credential = credential_for(session, person)
        project = _project(session)
        key = _key()
        first = _choose(surface, credential, project, key=key)
        assert first.status == 204, first.body
        row = _row(session, person)
        again = _choose(surface, credential, project, key=key)
        assert again.status == 204, again.body
        assert _row(session, person) == row
        assert _receipts(session, key) == 1

    def test_a_replay_does_not_undo_a_later_choice(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        first, second = _project(session), _project(session)
        key = _key()
        assert _choose(surface, credential, first, key=key).status == 204
        assert _choose(surface, credential, second).status == 204
        assert _choose(surface, credential, first, key=key).status == 204, "the recorded outcome is replayed"
        assert _me(surface, credential)["last_project_uid"] == second, "the replay wrote nothing"

    def test_the_same_key_for_another_object_is_refused(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        first, second = _project(session), _project(session)
        key = _key()
        assert _choose(surface, credential, first, key=key).status == 204
        reused = _choose(surface, credential, second, key=key)
        assert reused.status == 409, reused.body
        assert _json(reused)["error_code"] == "idempotency_key_reuse"
        assert _me(surface, credential)["last_project_uid"] == first

    def test_the_key_is_required(self, surface: Surface, session: Session, person: str) -> None:
        answer = _choose(surface, credential_for(session, person), _project(session), key=False)  # type: ignore[arg-type]
        assert answer.status == 422, answer.body
        assert _json(answer)["details"] == {"field": "Idempotency-Key"} or "Idempotency-Key" in answer.body.decode()


class TestAnObjectThatIsNotThere:
    def test_an_unknown_object_is_not_found_and_writes_nothing(
        self, surface: Surface, session: Session, person: str
    ) -> None:
        credential = credential_for(session, person)
        kept = _project(session)
        assert _choose(surface, credential, kept).status == 204
        missing = str(ProjectUid.new())
        answer = _choose(surface, credential, missing)
        assert answer.status == 404, answer.body
        assert _json(answer)["error_code"] == "not_found"
        assert _me(surface, credential)["last_project_uid"] == kept, "a refused choice leaves the earlier one"

    def test_a_refusal_does_not_consume_the_key(self, surface: Surface, session: Session, person: str) -> None:
        credential = credential_for(session, person)
        key = _key()
        assert _choose(surface, credential, str(ProjectUid.new()), key=key).status == 404
        assert _receipts(session, key) == 0
        real = _project(session)
        assert _choose(surface, credential, real, key=key).status == 204
        assert _me(surface, credential)["last_project_uid"] == real

    @pytest.mark.parametrize("value", ["", "not-a-project", "doc_01M2545JSD15ETSNNV904X991H", None, 7])
    def test_a_malformed_identity_is_a_validation_failure(
        self, surface: Surface, session: Session, person: str, value: Any
    ) -> None:
        answer = _choose(surface, credential_for(session, person), "ignored", body={"project_uid": value})
        assert answer.status == 422, answer.body
        assert _json(answer)["error_code"] == "validation_failed"
        assert _row(session, person) is None

    def test_the_all_objects_view_is_not_stored(self, surface: Surface, session: Session, person: str) -> None:
        refused = _choose(surface, credential_for(session, person), "ignored", body={})
        assert refused.status == 422, refused.body


class TestTheRowAndWhatItNames:
    def test_it_goes_with_the_account(self, session: Session, surface: Surface) -> None:
        doomed = make_account(
            session, login=f"lp-doomed-{secrets.token_hex(4)}@suite.invalid", names=("Удалёнов", "Иван", None)
        )
        assert _choose(surface, credential_for(session, doomed), _project(session)).status == 204
        assert _row(session, doomed) is not None
        session.execute(text("DELETE FROM app_user WHERE user_uid = :u"), {"u": doomed})
        assert _row(session, doomed) is None

    def test_an_object_that_is_gone_reads_as_no_choice_and_the_next_choice_replaces_the_row(
        self, surface: Surface, session: Session, person: str
    ) -> None:
        """No key to ``project`` (migration 0069): deleting an object is never refused for this table, and ``getMe`` never
        answers an identity that names nothing."""
        credential = credential_for(session, person)
        project = _project(session)
        assert _choose(surface, credential, project).status == 204
        session.execute(text("DELETE FROM project WHERE project_uid = :p"), {"p": project})
        assert _me(surface, credential)["last_project_uid"] is None
        assert _row(session, person) is not None, "the stale row is left for the next choice to replace"
        again = _project(session)
        assert _choose(surface, credential, again).status == 204
        assert _me(surface, credential)["last_project_uid"] == again
        assert _row(session, person)[0] == again

    def test_the_register_names_the_table_with_the_cascade(self) -> None:
        from auditmanager.access.public import ACCOUNT_REFERENCES

        entries = [entry for entry in ACCOUNT_REFERENCES if entry.table == "account_last_project"]
        assert [(entry.column, entry.on_delete) for entry in entries] == [("user_uid", "CASCADE")]
