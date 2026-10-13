"""`W55B-BUDGET-01`, over HTTP: ``startRun`` and ``reauditRun`` answer ``422 analysis_input_budget_exceeded``.

The shipped ``RunAdapter`` and ``ExecutionAdapter`` behind the shipped ``build_router`` and the
real ASGI app, driven through ``starlette``'s test client with a real bearer credential. What
the wire carries is asserted, not what the command raised: status ``422``, the sealed code,
``retryable: false`` and ``details`` of exactly ``character_count`` and ``budget_characters``.
A refused request leaves no run and no command record, and a client that retries the same key
against a deployment whose operator has since raised the ceiling is accepted -- while a key
the ledger already knows is replayed whatever the budget is now.

**This module commits.** Its versions and its source run are written through a committing
session, because the accepted requests write through the adapters' own sessions, which a
rolled-back harness transaction would hide from. The rows are immutable and the lane is
private, as in ``composition/test_the_run_leaves_the_request_thread.py``.

**It binds no ``_no_network`` guard.** ``TestClient`` opens a socketpair for its portal, which
the run suite's autouse guard refuses. The property that guard exists for -- nothing here can
spend -- is held by construction: the model adapter is ``None`` and the carrier below only
records, so no run is ever executed.
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
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.routers.idempotency import IDEMPOTENCY_HEADER
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter, ExecutionAdapter, RunAdapter
from auditmanager.documents.public import DocumentRepository
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import DocumentUid, RunId, VersionUid

SECRET = "w55b-budget-http-token"
BUDGET = 50_000


@pytest.fixture(autouse=True)
def _no_network() -> None:
    """Replaces the run suite's guard for this module; see the module docstring."""


class _Carrier:
    """Records the jobs it is handed and runs none of them."""

    def __init__(self) -> None:
        self.submitted: list[object] = []

    def submit(self, job: object) -> None:
        self.submitted.append(job)

    def shutdown(self) -> None:
        return None


class _Built:
    """Just enough of ``Application`` for ``create_asgi_app``."""

    __slots__ = ("router", "carrier", "session_factory")

    def __init__(self, router: Any, carrier: Any, sessions: Any) -> None:
        self.router = router
        self.carrier = carrier
        self.session_factory = sessions


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _counted_version(session: Session, seeded: Any, count: int | None) -> str:
    documents = DocumentRepository()
    base = documents.get_version(session, VersionUid.parse(seeded.version_uid))
    counts = (
        {}
        if count is None
        else {
            "text_character_count": count,
            "textless_pages": (),
            "recognised_character_count": 0,
        }
    )
    return str(
        documents.publish_version(
            session,
            document_uid=DocumentUid.parse(seeded.document_uid),
            media_type=base.media_type,
            byte_size=base.byte_size,
            sha256=base.sha256,
            page_count=base.page_count,
            source_filename=None,
            entries=base.manifest,
            **counts,
        )
    )


def _terminal_source(session: Session, seeded: Any, version_uid: str) -> str:
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
        session,
        run_id=run_id,
        from_state="running",
        to_state="failed",
        terminal_reason=ErrorCode.ANALYSIS_FAILED.value,
    )
    return run_id


@pytest.fixture
def world(sessions: sessionmaker[Session], blob_store: Any, helpers: Any) -> Any:
    """Committed: a document, a version with no count, and versions at, over and under the budget."""
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        over = _counted_version(session, seeded, BUDGET + 1)
        at = _counted_version(session, seeded, BUDGET)
        source_over = _terminal_source(session, seeded, over)
        source_at = _terminal_source(session, seeded, at)
        session.commit()
    return type(
        "World", (), {
            "seeded": seeded, "null": seeded.version_uid, "over": over, "at": at,
            "source_over": source_over, "source_at": source_at,
        },
    )


def _credential() -> str:
    from am_test_accounts import provisioned_credential

    return provisioned_credential(SECRET, "input-budget-http")


def _client(sessions: sessionmaker[Session], world: Any, budget: int | None) -> tuple[TestClient, _Carrier]:
    # Named `run_adapter`, not `runs`: `test_every_port_implementation_is_whole.py` resolves a wired port by
    # the variable's name anywhere in the module, and `runs` above this function is a `RunRepository`.
    carrier = _Carrier()
    run_adapter = RunAdapter(
        sessions, blob_store=None, adapter=None, provider_config=None, provider_mode="recorded",
        analysis_profile_id=world.seeded.analysis_profile_id,
        prompt_bundle_id=world.seeded.prompt_bundle_id, carrier=carrier,
        input_budget_characters=budget,
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
    )
    app = create_asgi_app(environ={API_TOKEN_VARIABLE: SECRET}, application=_Built(router, carrier, sessions))  # type: ignore[arg-type]
    return TestClient(app, raise_server_exceptions=False), carrier


def _key() -> str:
    return "w55bbudget-" + uuid.uuid4().hex[:16]


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_credential()}",
        IDEMPOTENCY_HEADER: key,
        "Content-Type": "application/json",
    }


def _start(client: TestClient, version_uid: str, key: str) -> Any:
    return client.post(
        "/runs", headers=_headers(key), content=json.dumps({"version_uid": version_uid}).encode()
    )


def _reaudit(client: TestClient, run_id: str, key: str) -> Any:
    return client.post(f"/runs/{run_id}/reaudit", headers=_headers(key))


def _count(sessions: sessionmaker[Session], sql: str, **params: Any) -> int:
    with sessions() as session:
        return int(session.execute(text(sql), params).scalar_one())


def _runs_of(sessions: sessionmaker[Session], version_uid: str) -> int:
    return _count(sessions, "SELECT count(*) FROM audit_run WHERE version_uid = :v", v=version_uid)


def _commands_with_key(sessions: sessionmaker[Session], key: str) -> int:
    return _count(
        sessions, "SELECT count(*) FROM command_record WHERE idempotency_key = :k", k=key
    )


def _assert_the_envelope(answer: Any, *, character_count: int, budget: int) -> None:
    assert answer.status_code == 422, answer.content
    body = answer.json()
    assert body["error_code"] == "analysis_input_budget_exceeded"
    assert body["retryable"] is False
    assert body["details"] == {"character_count": character_count, "budget_characters": budget}
    assert all(type(value) is int for value in body["details"].values())
    assert answer.headers["content-type"].startswith("application/json")


class TestStartRun:
    def test_a_version_above_the_budget_is_a_422_and_leaves_nothing(self, sessions, world) -> None:
        client, carrier = _client(sessions, world, BUDGET)
        key = _key()
        before = _runs_of(sessions, world.over)  # the fixture's own terminal source run
        answer = _start(client, world.over, key)
        _assert_the_envelope(answer, character_count=BUDGET + 1, budget=BUDGET)
        assert _runs_of(sessions, world.over) == before
        assert _commands_with_key(sessions, key) == 0
        assert carrier.submitted == []

    def test_a_version_exactly_at_the_budget_is_accepted(self, sessions, world) -> None:
        client, carrier = _client(sessions, world, BUDGET)
        answer = _start(client, world.at, _key())
        assert answer.status_code == 202, answer.content
        assert answer.json()["state"] == "queued" and len(carrier.submitted) == 1

    def test_a_version_with_no_recorded_count_is_accepted(self, sessions, world) -> None:
        client, _ = _client(sessions, world, 1)
        assert _start(client, world.null, _key()).status_code == 202

    def test_the_same_key_after_the_operator_raises_the_ceiling_is_a_fresh_start(
        self, sessions, world
    ) -> None:
        key = _key()
        before = _runs_of(sessions, world.over)
        strict, _ = _client(sessions, world, BUDGET)
        _assert_the_envelope(_start(strict, world.over, key), character_count=BUDGET + 1, budget=BUDGET)

        raised, carrier = _client(sessions, world, BUDGET + 1)
        accepted = _start(raised, world.over, key)
        assert accepted.status_code == 202, accepted.content
        assert len(carrier.submitted) == 1 and _runs_of(sessions, world.over) == before + 1

        # And now that the key is known, even the strict deployment replays it.
        replayed = _start(strict, world.over, key)
        assert replayed.status_code == 202, replayed.content
        assert replayed.json()["run_id"] == accepted.json()["run_id"]
        assert _runs_of(sessions, world.over) == before + 1


class TestReauditRun:
    def test_a_source_whose_version_is_above_the_budget_is_a_422_and_leaves_nothing(
        self, sessions, world
    ) -> None:
        client, carrier = _client(sessions, world, BUDGET)
        key = _key()
        before = _runs_of(sessions, world.over)
        answer = _reaudit(client, world.source_over, key)
        _assert_the_envelope(answer, character_count=BUDGET + 1, budget=BUDGET)
        assert _runs_of(sessions, world.over) == before
        assert _commands_with_key(sessions, key) == 0
        assert carrier.submitted == []

    def test_a_source_at_the_budget_is_accepted(self, sessions, world) -> None:
        client, carrier = _client(sessions, world, BUDGET)
        answer = _reaudit(client, world.source_at, _key())
        assert answer.status_code == 202, answer.content
        assert len(carrier.submitted) == 1

    def test_the_same_key_after_the_operator_raises_the_ceiling_is_a_fresh_re_audit(
        self, sessions, world
    ) -> None:
        key = _key()
        strict, _ = _client(sessions, world, BUDGET)
        _assert_the_envelope(
            _reaudit(strict, world.source_over, key), character_count=BUDGET + 1, budget=BUDGET
        )
        raised, carrier = _client(sessions, world, BUDGET + 1)
        accepted = _reaudit(raised, world.source_over, key)
        assert accepted.status_code == 202, accepted.content
        assert len(carrier.submitted) == 1
        replayed = _reaudit(strict, world.source_over, key)
        assert replayed.status_code == 202 and replayed.json()["run_id"] == accepted.json()["run_id"]
