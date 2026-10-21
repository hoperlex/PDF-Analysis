"""`W59-SECTION-SEAL-01`, over HTTP: classify a version, review it, and route run start from it.

The shipped ``SectionAdapter``, ``RunAdapter`` and ``ExecutionAdapter`` behind the shipped
``build_router`` and the real ASGI app, driven through ``starlette``'s test client with real
bearer credentials for real accounts, against the lane's own PostgreSQL and MinIO. The
section table is the **real** text-profile registry (AR from the v1 constants plus every
``text-profile/1`` package in the tree), so the refusal for a section without a profile is
proved on the section that genuinely has none (``PB``).

Cases (the decision's tests 3-5 and the task's failure list):

* classify is expert-only -- an ``admin``-only account is ``403 role:expert`` -- an exact
  repeat answers the stored row with the first confirmer, a different stage or section is
  ``409 conflict`` (``version_already_classified``) and changes nothing, and a version named
  under a foreign document or project is ``404``;
* every version read projects the classification; a version nobody classified carries none,
  even when its document has the legacy ``section`` ``AR``;
* the review lists all fifteen choices, marks ``executable`` exactly as the registry does and
  never pre-selects;
* ``startRun`` on an unclassified version is ``422 version_classification_required`` (no details;
  ``BETA-CONTRACT-SEAL-01``, ``D-179``) and leaves no run and no command record; on a
  ``PB`` version ``422 section_profile_unavailable``; on a ``KJ`` version
  the run pins the ``KJ`` package's profile and bundle, and an ``AR`` version pins the v1 pair;
* a replay of an accepted key answers the run it created; a re-audit routes from the version's
  classification now, and an older run keeps the profile it pinned.

**This module commits**, for the reason ``test_input_budget_over_http.py`` gives, and binds no
``_no_network`` guard: the model adapter is ``None`` and the carrier only records, so nothing
is executed or spent.
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

SECRET = "w59-section-routing-http-token"
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


def _start(client: TestClient, token: str, version_uid: str, key: str) -> Any:
    return client.post(
        "/runs", headers=_headers(token, key), content=json.dumps({"version_uid": version_uid}).encode()
    )


def _count(sessions: sessionmaker[Session], sql: str, **params: Any) -> int:
    with sessions() as session:
        return int(session.execute(text(sql), params).scalar_one())


def _assert_unroutable(answer: Any, code: str) -> None:
    assert answer.status_code == 422, answer.content
    body = answer.json()
    assert body["error_code"] == code
    assert body["retryable"] is False
    assert "details" not in body, "a routing refusal carries no details (BETA-CONTRACT-SEAL-01)"


class TestClassify:
    def test_an_expert_classifies_and_an_exact_repeat_keeps_the_first_confirmer(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, user_uid = _expert()
        path = _version_path(world, world.kj)
        first = _classify(client, token, path, "R", "KJ")
        assert first.status_code == 200, first.content
        body = first.json()
        assert set(body) == {
            "version_uid", "project_stage", "section_code", "confirmed_by_user_uid", "confirmed_at",
            "revision",
        }
        assert body["revision"] == 1
        assert (body["version_uid"], body["project_stage"], body["section_code"]) == (world.kj, "R", "KJ")
        assert body["confirmed_by_user_uid"] == user_uid
        repeat = _classify(client, token, path, "R", "KJ")
        assert repeat.status_code == 200 and repeat.json() == body
        assert _count(
            sessions, "SELECT count(*) FROM document_version_classification WHERE version_uid = :v",
            v=world.kj,
        ) == 1

    def test_a_different_stage_or_section_is_a_conflict_and_changes_nothing(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.conflict)
        stored = _classify(client, token, path, "P", "OV")
        assert stored.status_code == 200, stored.content
        for stage, code in (("P", "VK"), ("R", "OV"), ("R", "VK")):
            answer = _classify(client, token, path, stage, code)
            assert answer.status_code == 409, answer.content
            assert answer.json()["error_code"] == "conflict"
            assert answer.json()["details"] == {
                "aggregate_type": "DocumentVersionClassification",
                "conflict_reason": "version_already_classified",
            }
        again = _classify(client, token, path, "P", "OV")
        assert again.json() == stored.json()

    def test_admin_alone_is_refused_and_nothing_is_written(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        answer = _classify(client, _admin_only(sessions), _version_path(world, world.pb), "R", "PB")
        assert answer.status_code == 403, answer.content
        assert answer.json()["error_code"] == "permission_denied"
        assert answer.json()["details"] == {"required_capability": "role:expert"}
        assert _count(
            sessions, "SELECT count(*) FROM document_version_classification WHERE version_uid = :v",
            v=world.pb,
        ) == 0

    def test_a_foreign_chain_is_not_found(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        cases = (
            # A version of another document under this document.
            ("DocumentVersion", _version_path(world, world.foreign.version_uid)),
            # Another project's document under this project, and this document under it.
            ("Document", _version_path(world, world.kj, document=world.foreign.document_uid)),
            ("Document", _version_path(world, world.kj, project=world.foreign.project_uid)),
            # A project that does not exist.
            ("Project", _version_path(world, world.kj, project=str(ProjectUid.new()))),
        )
        for aggregate, path in cases:
            for answer in (
                _classify(client, token, path, "R", "KJ"),
                client.get(f"{path}/section-review", headers=_headers(token)),
            ):
                assert answer.status_code == 404, (aggregate, answer.content)
                assert answer.json()["details"] == {"aggregate_type": aggregate}
        assert _count(
            sessions, "SELECT count(*) FROM document_version_classification WHERE version_uid = :v",
            v=world.foreign.version_uid,
        ) == 0

    def test_an_unknown_section_or_stage_is_a_validation_failure(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.pb)
        for stage, code in (("X", "KJ"), ("P", "ZZ"), ("P", "ar")):
            assert _classify(client, token, path, stage, code).status_code == 422


class TestReview:
    def test_fifteen_choices_executable_as_registered_and_nothing_preselected(
        self, sessions, blob_store, world
    ) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        path = _version_path(world, world.kj)
        before = client.get(f"{path}/section-review", headers=_headers(token))
        assert before.status_code == 200, before.content
        review = before.json()
        codes = [option["section_code"] for option in review["options"]]
        assert sorted(codes) == sorted(
            ["AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS"]
        )
        executable = {option["section_code"] for option in review["options"] if option["executable"]}
        assert executable == set(REGISTRY.executable_sections())
        assert "PB" not in executable and {"AR", "KJ"} <= executable
        assert review["recognised_text_consulted"] is False
        suggested = {
            option["section_code"]: option["suggestion"]
            for option in review["options"]
            if option["suggestion"] is not None
        }
        assert "KJ" in suggested and suggested["KJ"]["filename_patterns"]
        _classify(client, token, path, "R", "KJ")
        after = client.get(f"{path}/section-review", headers=_headers(token)).json()
        assert after["classification"]["section_code"] == "KJ"
        assert after["options"] == review["options"]

    def test_admin_may_read_a_review(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        answer = client.get(
            f"{_version_path(world, world.pb)}/section-review",
            headers=_headers(_admin_only(sessions)),
        )
        assert answer.status_code == 200, answer.content
        assert answer.json()["classification"] is None


class TestRunStart:
    def test_an_unclassified_version_is_refused_even_with_legacy_section_ar(
        self, sessions, blob_store, world
    ) -> None:
        with sessions() as session:
            record = DocumentRepository().get_version(session, VersionUid.parse(world.unclassified))
        assert record.section == "AR" and record.classification is None
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        key = _key()
        before = _count(sessions, "SELECT count(*) FROM audit_run WHERE version_uid = :v", v=world.unclassified)
        _assert_unroutable(_start(client, token, world.unclassified, key), "version_classification_required")
        assert _count(sessions, "SELECT count(*) FROM audit_run WHERE version_uid = :v", v=world.unclassified) == before
        assert _count(sessions, "SELECT count(*) FROM command_record WHERE idempotency_key = :k", k=key) == 0
        assert carrier.submitted == []

    def test_a_section_without_a_profile_is_refused_without_an_ar_fallback(
        self, sessions, blob_store, world
    ) -> None:
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        assert _classify(client, token, _version_path(world, world.pb), "P", "PB").status_code == 200
        key = _key()
        _assert_unroutable(_start(client, token, world.pb, key), "section_profile_unavailable")
        assert _count(sessions, "SELECT count(*) FROM audit_run WHERE version_uid = :v", v=world.pb) == 0
        assert _count(sessions, "SELECT count(*) FROM command_record WHERE idempotency_key = :k", k=key) == 0
        assert carrier.submitted == []

    def test_a_classified_version_pins_its_sections_profile_and_a_replay_answers_it(
        self, sessions, blob_store, world
    ) -> None:
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        _classify(client, token, _version_path(world, world.kj), "R", "KJ")
        key = _key()
        accepted = _start(client, token, world.kj, key)
        assert accepted.status_code == 202, accepted.content
        run = accepted.json()
        kj_profile, kj_bundle = REGISTRY.section_profiles()["KJ"]
        assert (run["analysis_profile_id"], run["prompt_bundle_id"]) == (kj_profile, kj_bundle)
        assert kj_profile != str(AR_TEXT_PROFILE.analysis_profile_id)
        replay = _start(client, token, world.kj, key)
        assert replay.status_code == 202 and replay.json()["run_id"] == run["run_id"]
        assert len(carrier.submitted) == 1

    def test_an_ar_classified_version_pins_the_v1_pair(self, sessions, blob_store, world) -> None:
        client, _ = _client(sessions, blob_store)
        token, _ = _expert()
        _classify(client, token, _version_path(world, world.ar), "P", "AR")
        accepted = _start(client, token, world.ar, _key())
        assert accepted.status_code == 202, accepted.content
        assert accepted.json()["analysis_profile_id"] == str(AR_TEXT_PROFILE.analysis_profile_id)
        assert accepted.json()["prompt_bundle_id"] == str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id)


class TestReaudit:
    def test_a_reaudit_routes_from_the_classification_now_and_the_source_keeps_its_pin(
        self, sessions, blob_store, world
    ) -> None:
        client, carrier = _client(sessions, blob_store)
        token, _ = _expert()
        refused = client.post(f"/runs/{world.source}/reaudit", headers=_headers(token, _key()))
        _assert_unroutable(refused, "version_classification_required")
        _classify(client, token, _version_path(world, world.reaudit), "R", "TX")
        accepted = client.post(f"/runs/{world.source}/reaudit", headers=_headers(token, _key()))
        assert accepted.status_code == 202, accepted.content
        tx_profile, tx_bundle = REGISTRY.section_profiles()["TX"]
        assert (accepted.json()["analysis_profile_id"], accepted.json()["prompt_bundle_id"]) == (tx_profile, tx_bundle)
        with sessions() as session:
            source = RunRepository().get(session, world.source)
        assert (source.analysis_profile_id, source.prompt_bundle_id) == (
            world.seeded.analysis_profile_id, world.seeded.prompt_bundle_id,
        )
        assert len(carrier.submitted) == 1
