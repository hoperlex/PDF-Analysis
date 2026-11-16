"""`UIP-G-10` (contract 1.55.0, owner ruling Г11) -- the one optional group of a document.

``setDocumentGroup`` (``PUT /projects/{project_uid}/documents/{document_uid}/group``) sets, changes or clears the group a
document carries; ``listDocuments`` and ``getDocumentVersion`` read it back as ``group`` (absent is «Без группы»). What is asserted
here is what the **served** operations answer over real rows, through the shipped ``DocumentAdapter``, ``ProjectAdapter`` and
``CredentialAdapter`` (so the role is the account row's, not a stand-in's), inside the suite's rolled-back transaction:

* a group is set, changed and cleared (``null``, and a blank text), and the document it names is the only one that moves;
* the text is trimmed and its inner runs of spaces collapse; 40 characters are allowed and 41 are ``422 validation_failed``;
* an exact replay under the same key answers the same body and records one event; the same key with another group is ``409``;
* the same group again under a new key changes nothing and records nothing;
* a document addressed under another project, an unknown document and an unknown project are ``404 not_found`` and change nothing;
* the free tags are untouched by a group and the group by the tags;
* ``expert`` and ``admin`` may, ``viewer`` is refused (``403``), no credential is ``401``;
* every change is on the document's audit trail as ``document.group_set``, with the group before and after.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import (
    AccountRepository,
    RegistrationRepository,
    UserRepository,
)
from auditmanager.api.routers import build_router
from auditmanager.bootstrap.adapters import (
    AccountAdapter,
    CredentialAdapter,
    DocumentAdapter,
    ProjectAdapter,
    RegistrationAdapter,
)
from auditmanager.ingest import IngestService
from w13_api_driver import Surface

from .identity_surface import ADMIN_ROLES, SIGNER, credential_for, make_account

BOUNDARY = "----uipg10group"


@pytest.fixture
def surface(ingest: IngestService, session_factory: sessionmaker[Session]) -> Surface:
    """The served application over the shipped project, document, account and credential adapters."""
    return Surface(
        build_router(
            projects=ProjectAdapter(ingest, session_factory),
            documents=DocumentAdapter(ingest, session_factory),
            runs=None,  # type: ignore[arg-type]
            findings=None,  # type: ignore[arg-type]
            decisions=None,  # type: ignore[arg-type]
            exports=None,  # type: ignore[arg-type]
            credentials=CredentialAdapter(
                session_factory, users=UserRepository(), accounts=AccountRepository(), signer=SIGNER,
            ),
            accounts=AccountAdapter(session_factory, accounts=AccountRepository()),
            registrations=RegistrationAdapter(session_factory, registrations=RegistrationRepository()),
        )
    )


def _account(session: Session, roles: tuple[str, ...]) -> str:
    return make_account(
        session, login=f"grp-{secrets.token_hex(4)}@suite.invalid", names=("Группов", "Глеб", None), roles=roles,
    )


@pytest.fixture
def expert_uid(session: Session) -> str:
    return _account(session, ("expert",))


@pytest.fixture
def expert(session: Session, expert_uid: str) -> str:
    return credential_for(session, expert_uid)


@pytest.fixture
def admin(session: Session) -> str:
    return credential_for(session, _account(session, ADMIN_ROLES))


@pytest.fixture
def viewer(session: Session) -> str:
    return credential_for(session, _account(session, ("viewer",)))


def _key() -> str:
    return f"grp-{secrets.token_hex(8)}"


def _json(answer: Any) -> dict[str, Any]:
    return json.loads(answer.body)


def _ok(answer: Any) -> dict[str, Any]:
    assert answer.status < 300, (answer.status, answer.body)
    return _json(answer)


def _multipart(content: bytes, *, filename: str, title: str) -> bytes:
    return b"".join(
        [
            (
                f"--{BOUNDARY}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                "Content-Type: application/zip\r\n\r\n"
            ).encode("utf-8"),
            content,
            (
                f"\r\n--{BOUNDARY}\r\n"
                f'Content-Disposition: form-data; name="display_title"\r\n\r\n{title}'
            ).encode("utf-8"),
            f"\r\n--{BOUNDARY}--\r\n".encode("utf-8"),
        ]
    )


class World:
    """A project with two documents, so that a change to one can be seen not to move the other."""

    def __init__(self, surface: Surface, credential: str, actor_uid: str, bundle_around: Any, corpus_pdf: bytes) -> None:
        self.surface = surface
        self.credential = credential
        self.actor_uid = actor_uid
        project = _ok(
            surface.send(
                "POST", "/projects",
                headers={"Idempotency-Key": _key(), "Content-Type": "application/json"},
                body=json.dumps({"name": f"Объект {secrets.token_hex(3)}"}).encode("utf-8"),
                credential=credential,
            )
        )
        self.project_uid: str = project["project_uid"]
        self.first = self._upload(bundle_around, corpus_pdf, "a", "Пояснительная записка")
        self.second = self._upload(bundle_around, corpus_pdf, "b", "Архитектурные решения")

    def _upload(self, bundle_around: Any, corpus_pdf: bytes, label: str, title: str) -> dict[str, Any]:
        content = bundle_around(corpus_pdf + f"\n% {label} {secrets.token_hex(4)}\n".encode(), stem=f"doc_{label}")
        return _ok(
            self.surface.send(
                "POST", f"/projects/{self.project_uid}/documents",
                headers={"Idempotency-Key": _key(), "Content-Type": f"multipart/form-data; boundary={BOUNDARY}"},
                body=_multipart(content, filename=f"doc_{label}.zip", title=title),
                credential=self.credential,
            )
        )

    def put_group(
        self, document: dict[str, Any], group: Any, *, key: str | None = None, credential: str | None = None,
        project_uid: str | None = None, body: Any = None, document_uid: str | None = None,
    ) -> Any:
        payload = {"group": group} if body is None else body
        return self.surface.send(
            "PUT",
            f"/projects/{project_uid or self.project_uid}/documents/{document_uid or document['document_uid']}/group",
            headers={"Idempotency-Key": key or _key(), "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
            credential=self.credential if credential is None else credential,
        )

    def listed(self, *, credential: str | None = None) -> dict[str, dict[str, Any]]:
        answer = self.surface.send(
            "GET", f"/projects/{self.project_uid}/documents",
            credential=self.credential if credential is None else credential,
        )
        return {item["document_uid"]: item for item in _ok(answer)["items"]}

    def read(self, document: dict[str, Any]) -> dict[str, Any]:
        return _ok(self.surface.send("GET", f"/versions/{document['version_uid']}", credential=self.credential))


@pytest.fixture
def world(surface: Surface, expert: str, expert_uid: str, bundle_around: Any, corpus_pdf: bytes) -> World:
    return World(surface, expert, expert_uid, bundle_around, corpus_pdf)


def _trail(session: Session, document_uid: str) -> list[tuple[str, dict[str, Any]]]:
    rows = session.execute(
        text(
            "SELECT event_type, payload FROM audit_event WHERE aggregate_type = 'Document' AND aggregate_id = :d "
            "ORDER BY occurred_at, sequence_no"
        ),
        {"d": document_uid},
    ).all()
    return [(str(kind), dict(payload)) for kind, payload in rows]


def _group_events(session: Session, document_uid: str) -> list[dict[str, Any]]:
    return [payload for kind, payload in _trail(session, document_uid) if kind == "document.group_set"]


def _stored(session: Session, document_uid: str) -> str | None:
    return session.execute(
        text("SELECT group_label FROM document WHERE document_uid = :d"), {"d": document_uid}
    ).scalar_one()


def _receipts(session: Session, key: str) -> int:
    return int(
        session.execute(
            text("SELECT count(*) FROM command_record WHERE command_type = 'set_document_group' AND idempotency_key = :k"),
            {"k": key},
        ).scalar_one()
    )


class TestSettingChangingAndClearingAGroup:
    def test_a_document_carries_no_group_until_one_is_set(self, world: World) -> None:
        listed = world.listed()
        assert set(listed) == {world.first["document_uid"], world.second["document_uid"]}
        assert all("group" not in item for item in listed.values()), "absent is «Без группы», never an empty text"
        assert "group" not in world.read(world.first)

    def test_a_group_is_set_and_read_back_by_the_listing_and_the_version(self, world: World, session: Session) -> None:
        answer = world.put_group(world.first, "Архитектурные решения")
        body = _ok(answer)
        assert answer.status == 200
        assert body["group"] == "Архитектурные решения"
        assert body["document_uid"] == world.first["document_uid"] and body["version_uid"] == world.first["version_uid"]
        listed = world.listed()
        assert listed[world.first["document_uid"]]["group"] == "Архитектурные решения"
        assert "group" not in listed[world.second["document_uid"]], "only the named document moves"
        assert world.read(world.first)["group"] == "Архитектурные решения"
        assert "group" not in world.read(world.second)
        assert _stored(session, world.first["document_uid"]) == "Архитектурные решения"
        assert _stored(session, world.second["document_uid"]) is None

    def test_a_group_is_changed(self, world: World, session: Session) -> None:
        document = world.first
        _ok(world.put_group(document, "Конструкции"))
        body = _ok(world.put_group(document, "Инженерные сети"))
        assert body["group"] == "Инженерные сети"
        assert world.listed()[document["document_uid"]]["group"] == "Инженерные сети"
        assert _group_events(session, document["document_uid"]) == [
            {"actor_uid": world.actor_uid, "from": None, "to": "Конструкции"},
            {"actor_uid": world.actor_uid, "from": "Конструкции", "to": "Инженерные сети"},
        ]

    def test_a_group_is_cleared_by_null(self, world: World, session: Session) -> None:
        document = world.first
        _ok(world.put_group(document, "Конструкции"))
        answer = world.put_group(document, None)
        body = _ok(answer)
        assert answer.status == 200
        assert "group" not in body, "no group is no property"
        assert "group" not in world.listed()[document["document_uid"]]
        assert "group" not in world.read(document)
        assert _stored(session, document["document_uid"]) is None
        assert _group_events(session, document["document_uid"])[-1] == {
            "actor_uid": world.actor_uid, "from": "Конструкции", "to": None,
        }

    @pytest.mark.parametrize("blank", ["", "   ", "\t \n"])
    def test_a_blank_text_clears_it_too_and_is_never_stored(self, world: World, session: Session, blank: str) -> None:
        document = world.first
        _ok(world.put_group(document, "Конструкции"))
        body = _ok(world.put_group(document, blank))
        assert "group" not in body
        assert _stored(session, document["document_uid"]) is None, "NULL is the only way to say none, never an empty text"

    def test_clearing_a_document_that_has_none_records_nothing(self, world: World, session: Session) -> None:
        document = world.first
        assert "group" not in _ok(world.put_group(document, None))
        assert "group" not in _ok(world.put_group(document, "  "))
        assert _group_events(session, document["document_uid"]) == []

    def test_the_text_is_trimmed_and_its_inner_spaces_collapse(self, world: World, session: Session) -> None:
        document = world.first
        body = _ok(world.put_group(document, "  Раздел   КР \t 1  "))
        assert body["group"] == "Раздел КР 1"
        assert _stored(session, document["document_uid"]) == "Раздел КР 1"
        # The same group as the stored one, spelt with other spaces, is the same group: nothing is recorded.
        _ok(world.put_group(document, "Раздел КР 1 "))
        assert len(_group_events(session, document["document_uid"])) == 1

    def test_two_documents_may_share_a_group_and_case_is_kept(self, world: World) -> None:
        _ok(world.put_group(world.first, "Конструкции"))
        _ok(world.put_group(world.second, "конструкции"))
        listed = world.listed()
        assert listed[world.first["document_uid"]]["group"] == "Конструкции"
        assert listed[world.second["document_uid"]]["group"] == "конструкции", "a group is the value the document carries"

    def test_the_group_is_independent_of_the_free_tags(self, world: World, session: Session) -> None:
        document = world.first
        path = f"/projects/{world.project_uid}/documents/{document['document_uid']}/tags"
        tagged = world.surface.send(
            "PUT", path, headers={"Idempotency-Key": _key(), "Content-Type": "application/json"},
            body=json.dumps({"tags": ["Корпус 1"]}).encode("utf-8"), credential=world.credential,
        )
        assert _ok(tagged)["tags"] == ["Корпус 1"]
        _ok(world.put_group(document, "Конструкции"))
        item = world.listed()[document["document_uid"]]
        assert item["tags"] == ["Корпус 1"] and item["group"] == "Конструкции"
        _ok(world.put_group(document, None))
        item = world.listed()[document["document_uid"]]
        assert item["tags"] == ["Корпус 1"] and "group" not in item, "clearing the group leaves the tags"
        _ok(world.put_group(document, "Конструкции"))
        cleared = world.surface.send(
            "PUT", path, headers={"Idempotency-Key": _key(), "Content-Type": "application/json"},
            body=json.dumps({"tags": []}).encode("utf-8"), credential=world.credential,
        )
        assert _ok(cleared)["tags"] == []
        assert world.listed()[document["document_uid"]]["group"] == "Конструкции", "clearing the tags leaves the group"


class TestTheBoundsOfAGroup:
    def test_forty_characters_are_allowed_and_forty_one_are_refused(self, world: World, session: Session) -> None:
        forty = "Ж" * 40
        assert _ok(world.put_group(world.first, forty))["group"] == forty
        answer = world.put_group(world.second, "Ж" * 41)
        assert answer.status == 422, answer.body
        assert _json(answer)["error_code"] == "validation_failed"
        assert _stored(session, world.second["document_uid"]) is None, "a refused group is not stored"

    def test_the_bound_is_read_on_the_cleaned_text_by_the_command(self) -> None:
        """The wire bound refuses 41 characters as sent; the command refuses what is still 41 after it is cleaned."""
        from auditmanager.ingest.lifecycle import clean_group
        from auditmanager.shared.errors import DomainError, ErrorCode

        assert clean_group("  " + "Ж" * 40 + "  ") == "Ж" * 40
        assert clean_group(("Ж" * 19 + "   ") + ("Ж" * 20)) == ("Ж" * 19) + " " + ("Ж" * 20)
        with pytest.raises(DomainError) as collapsed:
            clean_group(("Ж" * 20 + "   ") + ("Ж" * 20))  # 43 as sent, 41 once the spaces collapse
        assert collapsed.value.code is ErrorCode.VALIDATION_FAILED
        with pytest.raises(DomainError) as refused:
            clean_group("Ж" * 41)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    @pytest.mark.parametrize("body", [{}, {"group": 5}, {"group": ["Конструкции"]}, {"group": "Конструкции", "extra": 1}])
    def test_a_malformed_body_is_refused(self, world: World, session: Session, body: Any) -> None:
        answer = world.put_group(world.first, None, body=body)
        assert answer.status == 422, answer.body
        assert _json(answer)["error_code"] == "validation_failed"
        assert _stored(session, world.first["document_uid"]) is None

    def test_the_key_is_required(self, world: World) -> None:
        answer = world.surface.send(
            "PUT", f"/projects/{world.project_uid}/documents/{world.first['document_uid']}/group",
            headers={"Content-Type": "application/json"}, body=json.dumps({"group": "Конструкции"}).encode("utf-8"),
            credential=world.credential,
        )
        assert answer.status == 422, answer.body
        assert _json(answer)["error_code"] == "validation_failed"


class TestIdempotency:
    def test_an_exact_replay_answers_the_same_body_and_records_one_event(self, world: World, session: Session) -> None:
        key = _key()
        first = world.put_group(world.first, "Конструкции", key=key)
        again = world.put_group(world.first, "Конструкции", key=key)
        assert first.status == again.status == 200
        assert _json(first) == _json(again)
        assert _receipts(session, key) == 1
        assert len(_group_events(session, world.first["document_uid"])) == 1

    def test_a_replay_does_not_undo_a_later_change(self, world: World, session: Session) -> None:
        key = _key()
        _ok(world.put_group(world.first, "Конструкции", key=key))
        _ok(world.put_group(world.first, "Инженерные сети"))
        replay = world.put_group(world.first, "Конструкции", key=key)
        assert replay.status == 200
        assert _stored(session, world.first["document_uid"]) == "Инженерные сети", "a replay writes nothing"
        assert len(_group_events(session, world.first["document_uid"])) == 2

    def test_the_same_key_with_another_group_is_a_conflict(self, world: World, session: Session) -> None:
        key = _key()
        _ok(world.put_group(world.first, "Конструкции", key=key))
        reused = world.put_group(world.first, "Инженерные сети", key=key)
        assert reused.status == 409, reused.body
        assert _json(reused)["error_code"] == "idempotency_key_reuse"
        assert _stored(session, world.first["document_uid"]) == "Конструкции"

    def test_the_same_group_under_a_new_key_changes_nothing(self, world: World, session: Session) -> None:
        _ok(world.put_group(world.first, "Конструкции"))
        updated = session.execute(
            text("SELECT updated_at FROM document WHERE document_uid = :d"), {"d": world.first["document_uid"]}
        ).scalar_one()
        answer = world.put_group(world.first, "Конструкции")
        assert answer.status == 200 and _json(answer)["group"] == "Конструкции"
        assert len(_group_events(session, world.first["document_uid"])) == 1, "nothing changed, so nothing is recorded"
        assert session.execute(
            text("SELECT updated_at FROM document WHERE document_uid = :d"), {"d": world.first["document_uid"]}
        ).scalar_one() == updated


class TestAnotherProjectAndAnUnknownDocument:
    def test_a_document_of_another_project_is_not_found_and_stays_as_it_was(
        self, world: World, session: Session, surface: Surface, bundle_around: Any, corpus_pdf: bytes, expert: str
    ) -> None:
        other = World(surface, expert, world.actor_uid, bundle_around, corpus_pdf)
        _ok(world.put_group(world.first, "Конструкции"))
        # the document of this project, addressed under the other project
        answer = world.put_group(world.first, "Чужая группа", project_uid=other.project_uid)
        assert answer.status == 404, answer.body
        assert _json(answer)["error_code"] == "not_found"
        # and the other project's document under this one
        crossed = world.put_group(other.first, "Чужая группа")
        assert crossed.status == 404 and _json(crossed)["error_code"] == "not_found"
        assert _stored(session, world.first["document_uid"]) == "Конструкции"
        assert _stored(session, other.first["document_uid"]) is None
        assert _group_events(session, other.first["document_uid"]) == []

    def test_an_unknown_document_and_an_unknown_project_are_not_found(self, world: World) -> None:
        ghost_document = "doc_01M2545JSD15ETSNNV904X991H"
        ghost_project = "prj_01M2545JSD15ETSNNV904X991F"
        unknown_document = world.put_group(world.first, "Конструкции", document_uid=ghost_document)
        assert unknown_document.status == 404 and _json(unknown_document)["error_code"] == "not_found"
        unknown_project = world.put_group(world.first, "Конструкции", project_uid=ghost_project)
        assert unknown_project.status == 404 and _json(unknown_project)["error_code"] == "not_found"

    def test_a_listing_of_one_project_carries_only_its_own_groups(
        self, world: World, surface: Surface, bundle_around: Any, corpus_pdf: bytes, expert: str
    ) -> None:
        other = World(surface, expert, world.actor_uid, bundle_around, corpus_pdf)
        _ok(world.put_group(world.first, "Конструкции"))
        _ok(other.put_group(other.first, "Инженерные сети"))
        assert {item["group"] for item in world.listed().values() if "group" in item} == {"Конструкции"}
        assert {item["group"] for item in other.listed().values() if "group" in item} == {"Инженерные сети"}


class TestWhoMayGroup:
    def test_expert_and_admin_may_and_viewer_may_only_read(
        self, world: World, session: Session, admin: str, viewer: str
    ) -> None:
        assert _ok(world.put_group(world.first, "Конструкции", credential=admin))["group"] == "Конструкции"
        assert _ok(world.put_group(world.second, "Инженерные сети"))["group"] == "Инженерные сети"
        refused = world.put_group(world.first, "Чужая группа", credential=viewer)
        assert refused.status == 403, refused.body
        assert _json(refused)["error_code"] == "permission_denied"
        assert _stored(session, world.first["document_uid"]) == "Конструкции", "a refused write changes nothing"
        # a viewer reads the group, both on the listing and on the version
        assert world.listed(credential=viewer)[world.first["document_uid"]]["group"] == "Конструкции"
        read = world.surface.send("GET", f"/versions/{world.first['version_uid']}", credential=viewer)
        assert _ok(read)["group"] == "Конструкции"

    def test_no_credential_is_refused_before_anything_is_read(self, world: World, session: Session) -> None:
        answer = world.surface.send(
            "PUT", f"/projects/{world.project_uid}/documents/{world.first['document_uid']}/group",
            headers={"Idempotency-Key": _key(), "Content-Type": "application/json"},
            body=json.dumps({"group": "Конструкции"}).encode("utf-8"), credential=None,
        )
        assert answer.status == 401, answer.body
        assert _stored(session, world.first["document_uid"]) is None


class TestTheTrail:
    def test_each_change_is_one_event_with_the_group_before_and_after(self, world: World, session: Session) -> None:
        document = world.first
        _ok(world.put_group(document, "Конструкции"))
        _ok(world.put_group(document, "Конструкции"))  # nothing changed: nothing recorded
        _ok(world.put_group(document, "Инженерные сети"))
        _ok(world.put_group(document, None))
        trail = _trail(session, document["document_uid"])
        group = [(kind, payload["from"], payload["to"]) for kind, payload in trail if kind == "document.group_set"]
        assert group == [
            ("document.group_set", None, "Конструкции"),
            ("document.group_set", "Конструкции", "Инженерные сети"),
            ("document.group_set", "Инженерные сети", None),
        ]
        assert all(payload["actor_uid"].startswith("usr_") for kind, payload in trail if kind == "document.group_set")
        # the tags' own event type is not borrowed
        assert "document.tags_set" not in [kind for kind, _ in trail]
