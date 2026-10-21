"""`CLASSIFICATION-CORRECTION-01`, over HTTP: an expert corrects a version's stage and section.

The shipped ``SectionAdapter`` and ``RunAdapter`` behind the shipped ``build_router`` and the real
ASGI app, driven through ``starlette``'s test client with real bearer credentials for real
accounts, against the lane's own PostgreSQL and MinIO. The section table is the real text-profile
registry.

* ``correctVersionClassification`` is expert-only (``admin`` alone is ``403 role:expert``); a new
  correction is ``201`` with the next ``revision``; an exact repeat answers the same body and
  writes one row; a stale ``expected_revision`` is ``409 classification_revision_stale``; an
  unclassified version is ``409 version_not_classified``; an ``expected_revision`` ahead, a pair
  equal to the current one and a blank reason are ``422``; a foreign chain is ``404``;
* every read of the version (``getDocumentVersion``, ``listVersions``, ``listDocuments``) and
  ``getVersionSectionReview`` shows the corrected classification with its revision, and the review
  lists the history oldest first, each correction with its expert and reason;
* a run started before a correction keeps the profile it pinned, and the replay of its key answers
  it; a run started after it, and a re-audit, route from the corrected section.

**This module commits**, like its sibling, and binds no ``_no_network`` guard: the model adapter is
``None`` and the carrier only records.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.accounts import AccountRepository as AccountAccessRepository
from auditmanager.access.repository import UserRepository as UserAccessRepository
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from auditmanager.bootstrap.adapters import (
    CredentialAdapter,
    ExecutionAdapter,
    RunAdapter,
    SectionAdapter,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, RunId, VersionUid

SECRET = "classification-correction-http-token"
REGISTRY = load_text_profile_registry()


@pytest.fixture(autouse=True)
def _no_network() -> None:
    """Replaces the run suite's guard for this module; see the module docstring."""


class _Carrier:
    def __init__(self) -> None:
        self.submitted: list[object] = []

    def submit(self, job: object) -> None:
        self.submitted.append(job)

    def shutdown(self) -> None:
        return None


class _Built:
    __slots__ = ("router", "carrier", "session_factory")

    def __init__(self, router: Any, carrier: Any, sessions: Any) -> None:
        self.router = router
        self.carrier = carrier
        self.session_factory = sessions


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _another_version(session: Session, seeded: Any, source_filename: str | None = None) -> str:
    documents = DocumentRepository()
    base = documents.get_version(session, VersionUid.parse(seeded.version_uid))
    return str(
        documents.publish_version(
            session,
            document_uid=DocumentUid.parse(seeded.document_uid),
            media_type=base.media_type,
            byte_size=base.byte_size,
            sha256=base.sha256,
            page_count=base.page_count,
            source_filename=source_filename,
            entries=base.manifest,
        )
    )


def _terminal_run(session: Session, seeded: Any, version_uid: str) -> str:
    run_id = str(RunId.new())
    runs = RunRepository()
    runs.create(
        session,
        run_id=run_id,
        project_uid=seeded.project_uid,
        version_uid=version_uid,
        analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id,
        provider_mode="recorded",
        frozen_input_digest="b" * 64,
        command_id=None,
    )
    runs.advance(session, run_id=run_id, from_state="created", to_state="queued")
    runs.advance(session, run_id=run_id, from_state="queued", to_state="running")
    runs.terminate(
        session, run_id=run_id, from_state="running", to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
    )
    return run_id


@pytest.fixture
def world(sessions: sessionmaker[Session], blob_store: Any, helpers: Any) -> Any:
    """Committed: one document (legacy section AR) with five versions, a foreign one, a source run."""
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        foreign = helpers.seed_version(session, blob_store)
        versions = {
            name: _another_version(session, seeded, filename)
            for name, filename in (
                ("kj", "Раздел-КЖ-01.pdf"),
                ("pb", None),
                ("ar", None),
                ("reaudit", None),
                ("conflict", None),
            )
        }
        source = _terminal_run(session, seeded, versions["reaudit"])
        session.commit()
    return type(
        "World", (), {
            "seeded": seeded, "foreign": foreign, "unclassified": seeded.version_uid,
            "source": source, **versions,
        },
    )


def _expert() -> tuple[str, str]:
    from am_test_accounts import provisioned_credential, provisioned_record

    label = "w59-section-expert"
    return provisioned_credential(SECRET, label), str(provisioned_record(label).user_uid)


def _admin_only(sessions: sessionmaker[Session]) -> str:
    """A complete account holding ``admin`` and not ``expert``, and a credential for it."""
    login = f"w59-admin-{uuid.uuid4().hex[:8]}@suite.invalid"
    users, accounts = UserAccessRepository(), AccountAccessRepository()
    with sessions() as session:
        created = users.create_user(session, login, "w59-admin-only-password")
        accounts.complete_profile(
            session, user_uid=str(created.user_uid), email=None,
            last_name="Админова", first_name="Ада",
        )
        accounts.grant_role(session, user_uid=str(created.user_uid), role="admin", granted_by=None)
        record = users.find_by_login(session, login)
        session.commit()
    signer = build_signer({API_TOKEN_VARIABLE: SECRET})
    assert signer is not None and record is not None
    return signer.issue(
        Subject(
            user_uid=str(record.user_uid), login=record.login,
            token_epoch=record.token_epoch, display_label=record.display_label,
        ),
        is_default_credential=False,
    ).token


def _client(sessions: sessionmaker[Session], blob_store: Any) -> tuple[TestClient, _Carrier]:
    carrier = _Carrier()
    run_adapter = RunAdapter(
        sessions, blob_store=None, adapter=None, provider_config=None, provider_mode="recorded",
        analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id), carrier=carrier,
        section_profiles=REGISTRY.section_profiles(), text_profiles=REGISTRY.resolve,
    )
    signer = build_signer({API_TOKEN_VARIABLE: SECRET})
    assert signer is not None
    router = build_router(
        projects=None,  # type: ignore[arg-type]
        documents=None,  # type: ignore[arg-type]
        runs=run_adapter,
        findings=None,  # type: ignore[arg-type]
        decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            sessions, users=UserAccessRepository(), accounts=AccountAccessRepository(), signer=signer
        ),
        execution=ExecutionAdapter(sessions, runs=run_adapter),
        sections=SectionAdapter(
            sessions, blob_store=blob_store, executable_sections=REGISTRY.executable_sections()
        ),
    )
    app = create_asgi_app(environ={API_TOKEN_VARIABLE: SECRET}, application=_Built(router, carrier, sessions))  # type: ignore[arg-type]
    return TestClient(app, raise_server_exceptions=False), carrier


def _headers(token: str, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if key is not None:
        headers[IDEMPOTENCY_HEADER] = key
    return headers


def _key() -> str:
    return "w59route-" + uuid.uuid4().hex[:16]



def _version_path(world: Any, version_uid: str, *, project: str | None = None, document: str | None = None) -> str:
    return (
        f"/projects/{project or world.seeded.project_uid}"
        f"/documents/{document or world.seeded.document_uid}/versions/{version_uid}"
    )


def _classify(client: TestClient, token: str, path: str, stage: str, code: str) -> Any:
    return client.put(
        f"{path}/classification",
        headers=_headers(token),
        content=json.dumps({"project_stage": stage, "section_code": code}).encode(),
    )


def _correct(
    client: TestClient, token: str, path: str, stage: str, code: str, reason: str, expected: Any,
) -> Any:
    return client.post(
        f"{path}/classification/corrections",
        headers=_headers(token),
        content=json.dumps(
            {"project_stage": stage, "section_code": code, "reason": reason, "expected_revision": expected}
        ).encode(),
    )


def _start(client: TestClient, token: str, version_uid: str, key: str) -> Any:
    return client.post(
        "/runs", headers=_headers(token, key), content=json.dumps({"version_uid": version_uid}).encode()
    )


def _count(sessions: sessionmaker[Session], sql: str, **params: Any) -> int:
    with sessions() as session:
        return int(session.execute(text(sql), params).scalar_one())


def _corrections(sessions: sessionmaker[Session], version_uid: str) -> int:
    return _count(
        sessions,
        "SELECT count(*) FROM document_version_classification_correction WHERE version_uid = :v",
        v=version_uid,
    )


REASON = "Раздел определён по штампу листа неверно"


class TestCorrect:
    def test_an_expert_corrects_and_the_review_shows_the_new_revision_and_the_history(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, user_uid = _expert()
        path = _version_path(world, world.kj)
        assert _classify(client, token, path, "P", "KJ").status_code == 200
        answer = _correct(client, token, path, "R", "AR", REASON, 1)
        assert answer.status_code == 201, answer.content
        body = answer.json()
        assert set(body) == {
            "version_uid", "project_stage", "section_code", "confirmed_by_user_uid", "confirmed_at", "revision",
        }
        assert (body["version_uid"], body["project_stage"], body["section_code"], body["revision"]) == (
            world.kj, "R", "AR", 2,
        )
        assert body["confirmed_by_user_uid"] == user_uid
        review = client.get(f"{path}/section-review", headers=_headers(token)).json()
        assert review["classification"] == body
        assert [(entry["revision"], entry["project_stage"], entry["section_code"], entry["reason"])
                for entry in review["revisions"]] == [
            (1, "P", "KJ", None),
            (2, "R", "AR", REASON),
        ]
        assert [entry["actor_user_uid"] for entry in review["revisions"]] == [user_uid, user_uid]
        assert all(set(entry) == {"revision", "project_stage", "section_code", "actor_user_uid", "at", "reason"}
                   for entry in review["revisions"])

    def test_an_exact_repeat_answers_the_same_body_and_writes_one_row(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.pb)
        _classify(client, token, path, "P", "PB")
        first = _correct(client, token, path, "R", "PB", REASON, 1)
        repeat = _correct(client, token, path, "R", "PB", REASON, 1)
        assert first.status_code == repeat.status_code == 201
        assert repeat.json() == first.json()
        assert _corrections(sessions, world.pb) == 1

    def test_a_stale_expected_revision_is_a_conflict_and_changes_nothing(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.conflict)
        _classify(client, token, path, "P", "OV")
        assert _correct(client, token, path, "R", "OV", REASON, 1).status_code == 201
        stale = _correct(client, token, path, "R", "VK", "Другая причина", 1)
        assert stale.status_code == 409, stale.content
        assert stale.json()["error_code"] == "conflict"
        assert stale.json()["details"] == {
            "aggregate_type": "DocumentVersionClassification",
            "conflict_reason": "classification_revision_stale",
        }
        # the same values with another reason are not a repeat either
        assert _correct(client, token, path, "R", "OV", "Другая причина", 1).status_code == 409
        assert _corrections(sessions, world.conflict) == 1

    def test_an_unclassified_version_has_nothing_to_correct(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        answer = _correct(client, token, _version_path(world, world.unclassified), "R", "AR", REASON, 1)
        assert answer.status_code == 409, answer.content
        assert answer.json()["details"] == {
            "aggregate_type": "DocumentVersionClassification",
            "conflict_reason": "version_not_classified",
        }

    def test_admin_alone_is_refused_and_nothing_is_written(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.ar)
        _classify(client, token, path, "P", "AR")
        answer = _correct(client, _admin_only(sessions), path, "R", "AR", REASON, 1)
        assert answer.status_code == 403, answer.content
        assert answer.json()["error_code"] == "permission_denied"
        assert answer.json()["details"] == {"required_capability": "role:expert"}
        assert _corrections(sessions, world.ar) == 0

    def test_a_foreign_chain_is_not_found(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        for aggregate, path in (
            ("DocumentVersion", _version_path(world, world.foreign.version_uid)),
            ("Document", _version_path(world, world.kj, document=world.foreign.document_uid)),
            ("Document", _version_path(world, world.kj, project=world.foreign.project_uid)),
            ("Project", _version_path(world, world.kj, project=str(ProjectUid.new()))),
        ):
            answer = _correct(client, token, path, "R", "AR", REASON, 1)
            assert answer.status_code == 404, (aggregate, answer.content)
            assert answer.json()["details"] == {"aggregate_type": aggregate}

    def test_the_request_is_validated(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.reaudit)
        _classify(client, token, path, "P", "AR")
        ahead = _correct(client, token, path, "R", "AR", REASON, 5)
        assert ahead.status_code == 422, ahead.content
        assert ahead.json()["details"] == {"field": "expected_revision", "constraint": "exceeds_current_revision"}
        no_op = _correct(client, token, path, "P", "AR", REASON, 1)
        assert no_op.status_code == 422, no_op.content
        assert no_op.json()["details"] == {"field": "section_code", "constraint": "differs_from_current"}
        blank = _correct(client, token, path, "R", "AR", "   ", 1)
        assert blank.status_code == 422, blank.content
        assert blank.json()["details"] == {"field": "reason", "constraint": "required"}
        for stage, code, reason, expected in (
            ("X", "AR", REASON, 1), ("R", "ZZ", REASON, 1), ("R", "AR", "", 1), ("R", "AR", "а" * 2001, 1),
            ("R", "AR", REASON, 0), ("R", "AR", REASON, None), ("R", "AR", REASON, 1.5),
        ):
            assert _correct(client, token, path, stage, code, reason, expected).status_code == 422, (
                stage, code, reason[:10], expected,
            )
        missing = client.post(
            f"{path}/classification/corrections", headers=_headers(token),
            content=json.dumps({"project_stage": "R", "section_code": "AR", "reason": REASON}).encode(),
        )
        extra = client.post(
            f"{path}/classification/corrections", headers=_headers(token),
            content=json.dumps({"project_stage": "R", "section_code": "AR", "reason": REASON,
                                "expected_revision": 1, "force": True}).encode(),
        )
        assert missing.status_code == extra.status_code == 422
        assert _corrections(sessions, world.reaudit) == 0

    def test_classify_after_a_correction_compares_against_the_current_classification(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.kj)
        assert _classify(client, token, path, "P", "KJ").status_code == 200
        corrected = _correct(client, token, path, "R", "AR", REASON, 1)
        assert corrected.status_code == 201
        # an exact repeat of the CURRENT values answers the current row ...
        same = _classify(client, token, path, "R", "AR")
        assert same.status_code == 200 and same.json() == corrected.json()
        # ... and a retry of the original request is the conflict it always was
        refused = _classify(client, token, path, "P", "KJ")
        assert refused.status_code == 409
        assert refused.json()["details"]["conflict_reason"] == "version_already_classified"


class TestRuns:
    def test_a_started_run_keeps_its_pin_and_a_later_start_routes_from_the_correction(
        self, sessions, blob_store, world
    ) -> None:
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.ar)
        _classify(client, token, path, "P", "AR")
        first_key = _key()
        first = _start(client, token, world.ar, first_key)
        assert first.status_code == 202, first.content
        assert first.json()["analysis_profile_id"] == str(AR_TEXT_PROFILE.analysis_profile_id)
        assert _correct(client, token, path, "P", "KJ", REASON, 1).status_code == 201
        kj_profile, kj_bundle = REGISTRY.section_profiles()["KJ"]
        second = _start(client, token, world.ar, _key())
        assert second.status_code == 202, second.content
        assert (second.json()["analysis_profile_id"], second.json()["prompt_bundle_id"]) == (kj_profile, kj_bundle)
        assert second.json()["run_id"] != first.json()["run_id"]
        replay = _start(client, token, world.ar, first_key)
        assert replay.status_code == 202 and replay.json()["run_id"] == first.json()["run_id"]
        assert replay.json()["analysis_profile_id"] == str(AR_TEXT_PROFILE.analysis_profile_id)
        with sessions() as session:
            pinned = RunRepository().get(session, first.json()["run_id"])
        assert pinned.analysis_profile_id == str(AR_TEXT_PROFILE.analysis_profile_id)
        assert len(carrier.submitted) == 2

    def test_a_correction_to_a_section_without_a_profile_refuses_the_next_start(
        self, sessions, blob_store, world
    ) -> None:
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.pb)
        assert _classify(client, token, path, "P", "AR").status_code == 200
        assert _correct(client, token, path, "R", "PB", REASON, 1).status_code == 201
        refused = _start(client, token, world.pb, _key())
        assert refused.status_code == 422, refused.content
        assert refused.json()["error_code"] == "section_profile_unavailable"
        assert "details" not in refused.json()
        assert carrier.submitted == []

    def test_a_reaudit_routes_from_the_corrected_section_and_the_source_keeps_its_pin(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.reaudit)
        assert _classify(client, token, path, "R", "TX").status_code == 200
        first = client.post(f"/runs/{world.source}/reaudit", headers=_headers(token, _key()))
        assert first.status_code == 202, first.content
        assert first.json()["analysis_profile_id"] == REGISTRY.section_profiles()["TX"][0]
        assert _correct(client, token, path, "R", "KJ", REASON, 1).status_code == 201
        # one re-audit of a source at a time: the first is still open, so a second source run of
        # the same version is the one re-audited after the correction
        with sessions() as session:
            second_source = _terminal_run(session, world.seeded, world.reaudit)
            session.commit()
        second = client.post(f"/runs/{second_source}/reaudit", headers=_headers(token, _key()))
        assert second.status_code == 202, second.content
        assert second.json()["analysis_profile_id"] == REGISTRY.section_profiles()["KJ"][0]
        with sessions() as session:
            source = RunRepository().get(session, world.source)
            earlier = RunRepository().get(session, first.json()["run_id"])
        assert (source.analysis_profile_id, source.prompt_bundle_id) == (
            world.seeded.analysis_profile_id, world.seeded.prompt_bundle_id,
        )
        assert earlier.analysis_profile_id == REGISTRY.section_profiles()["TX"][0]
