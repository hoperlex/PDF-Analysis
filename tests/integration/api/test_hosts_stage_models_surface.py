"""`HOSTS-SEAL-1` (contract 1.45.0): the fifteen host and stage-layout operations over the shipped stubs and the real seam.

HEAVY: real PostgreSQL rows for the accounts, inside the suite's rolled-back transaction, through the shipped ``CredentialAdapter``.

Three groups, each shown able to fail:

* **the seam** -- the viewer («Наблюдатель», `R-150w`) is denied every one of the fifteen, and an expert is denied the administrator's;
* **the stubs** -- with the shipped adapters wired, an administrator's well-formed call to each operation answers ``503
  dependency_unavailable`` naming the lane's dependency, and nothing is read or written (a stub that answered 200 with an empty body would
  be a silent fallback, AGENTS section 4);
* **the behaviour the wave-1 lanes owe** -- written now as ``xfail(strict=True)``: each is red against the stubs and turns green when the
  lane implements the operation, at which point the strict marker fails the run until it is removed, so a lane cannot forget to take its
  own marker off.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.api.routers import build_router
from auditmanager.bootstrap.adapters import CredentialAdapter
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.stage_plan_adapter import StageModelAdapter
from w13_api_driver import Surface

from .identity_surface import SIGNER, credential_for, make_account

HOST = "exh_01ARZ3NDEKTSV4RRFFQ69G5FAV"
INSTALL = "exai_01ARZ3NDEKTSV4RRFFQ69G5FAV"
FINGERPRINT = "SHA256:" + "A" * 43
CELL = {"cell_key": "text:main", "row": "text", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
        "max_output_tokens": 16000, "timeout_seconds": 600}

#: (operationId, method, path, body, administrator only, dependency the stub names)
OPERATIONS: list[tuple[str, str, str, Any, bool, str]] = [
    ("listExecutorHosts", "GET", "/executor-hosts", None, False, "executor_hosts"),
    ("getExecutorHost", "GET", f"/executor-hosts/{HOST}", None, False, "executor_hosts"),
    ("getExecutorHostDetails", "GET", f"/executor-hosts/{HOST}/details", None, True, "executor_hosts"),
    ("setExecutorHostEnabled", "PUT", f"/executor-hosts/{HOST}/enabled", {"enabled": False}, True, "executor_hosts"),
    ("setExecutorHostSlots", "PUT", f"/executor-hosts/{HOST}/slots", {"slots": {"codex": 2}}, True, "executor_hosts"),
    ("archiveExecutorHost", "POST", f"/executor-hosts/{HOST}/archive", None, True, "executor_hosts"),
    ("issueExecutorHostEnrollment", "POST", "/executor-hosts/enrollments", {"display_name": "adm1.hlab.kz"}, True, "executor_hosts"),
    ("createExecutorHostAgentInstall", "POST", "/executor-hosts/agent-installs",
     {"display_name": "adm1.hlab.kz", "access": "generated_key", "ssh_host": "adm1.hlab.kz", "ssh_port": 22, "ssh_user": "root"},
     True, "executor_hosts"),
    ("getExecutorHostAgentInstall", "GET", f"/executor-hosts/{HOST}/agent-installs/{INSTALL}", None, True, "executor_hosts"),
    ("confirmExecutorHostAgentInstallHostKey", "POST", f"/executor-hosts/{HOST}/agent-installs/{INSTALL}/confirm-host-key",
     {"host_key_fingerprint": FINGERPRINT}, True, "executor_hosts"),
    ("getStageModelLayout", "GET", "/model-layout", None, False, "stage_models"),
    ("reviseStageModelLayout", "POST", "/model-layout/revisions", {"kit": "custom", "cells": [CELL]}, True, "stage_models"),
    ("setStageModelLayoutEnabled", "PUT", "/model-layout/enabled", {"enabled": True}, True, "stage_models"),
    ("listModelCatalogue", "GET", "/model-catalogue", None, False, "stage_models"),
    ("getRunStartReadiness", "POST", "/runs/start-readiness", {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, False, "stage_models"),
]
IDS = [operation[0] for operation in OPERATIONS]


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return Surface(
        build_router(
            projects=None, documents=None, runs=None, findings=None, decisions=None, exports=None,  # type: ignore[arg-type]
            credentials=CredentialAdapter(session_factory, users=UserRepository(), accounts=AccountRepository(), signer=SIGNER),
            executor_hosts=ExecutorHostAdapter(session_factory),
            stage_models=StageModelAdapter(session_factory),
        )
    )


@pytest.fixture
def people(session: Session) -> Any:
    def person(tag: str, roles: tuple[str, ...]) -> str:
        return make_account(session, login=f"hosts-{tag}-{secrets.token_hex(4)}@suite.invalid", names=("Тестов", tag, None), roles=roles)

    built = {"admin": person("admin", ("admin",)), "expert": person("expert", ("expert",)), "viewer": person("viewer", ("viewer",))}
    session.commit()
    return type("People", (), built)


def _call(surface: Surface, session: Session, who: str, operation: tuple[str, str, str, Any, bool, str]) -> Any:
    _, method, path, body, _, _ = operation
    headers = {"Idempotency-Key": secrets.token_hex(8)} if method != "GET" and operation[0] != "getRunStartReadiness" else {}
    payload = b""
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")
    return surface.send(method, path, headers=headers, body=payload, credential=credential_for(session, who))


def _json(answer: Any) -> Any:
    return json.loads(answer.body)


@pytest.mark.parametrize("operation", OPERATIONS, ids=IDS)
def test_the_viewer_is_denied_every_new_operation(surface: Surface, session: Session, people: Any, operation: Any) -> None:
    answer = _call(surface, session, people.viewer, operation)
    assert answer.status == 403, (operation[0], answer.status, answer.body)
    assert _json(answer)["error_code"] == "permission_denied"


@pytest.mark.parametrize("operation", [o for o in OPERATIONS if o[4]], ids=[o[0] for o in OPERATIONS if o[4]])
def test_an_expert_is_denied_what_only_the_administrator_may_do(surface: Surface, session: Session, people: Any, operation: Any) -> None:
    answer = _call(surface, session, people.expert, operation)
    assert answer.status == 403, (operation[0], answer.status, answer.body)


@pytest.mark.parametrize("operation", OPERATIONS, ids=IDS)
def test_the_shipped_stub_refuses_an_administrator_with_dependency_unavailable(
    surface: Surface, session: Session, people: Any, operation: Any
) -> None:
    answer = _call(surface, session, people.admin, operation)
    assert answer.status == 503, (operation[0], answer.status, answer.body)
    envelope = _json(answer)
    assert envelope["error_code"] == "dependency_unavailable"
    assert envelope["details"]["dependency"] == operation[5], envelope


# --- what the lanes owe -----------------------------------------------------------------------

BACKEND = "HOSTS-BACKEND-01 implements the servers; remove this marker with it"
LAYOUT = "HOSTS-LAYOUT-01 implements the layout, the catalogue and the readiness; remove this marker with it"


@pytest.mark.xfail(strict=True, reason=BACKEND)
def test_an_empty_stand_lists_no_servers_and_a_zero_summary(surface: Surface, session: Session, people: Any) -> None:
    answer = _call(surface, session, people.admin, OPERATIONS[0])
    assert answer.status == 200
    assert _json(answer) == {"items": [], "online": 0, "total": 0, "slots_free": 0, "slots_total": 0}


@pytest.mark.xfail(strict=True, reason=BACKEND)
def test_an_unknown_server_is_not_found(surface: Surface, session: Session, people: Any) -> None:
    assert _call(surface, session, people.admin, OPERATIONS[1]).status == 404


@pytest.mark.xfail(strict=True, reason=LAYOUT)
def test_before_the_first_revision_the_layout_is_off_and_empty(surface: Surface, session: Session, people: Any) -> None:
    answer = _call(surface, session, people.expert, OPERATIONS[10])
    assert answer.status == 200
    body = _json(answer)
    assert body["enabled"] is False and "current" not in body and body["history"] == []


@pytest.mark.xfail(strict=True, reason=LAYOUT)
def test_the_catalogue_is_the_file_of_the_contract(surface: Surface, session: Session, people: Any) -> None:
    from pathlib import Path

    file = json.loads((Path(__file__).resolve().parents[3] / "contracts/analysis/v1/model-catalogue.json").read_text(encoding="utf-8"))
    answer = _call(surface, session, people.expert, OPERATIONS[13])
    assert answer.status == 200
    assert _json(answer)["items"] == file["entries"]


@pytest.mark.xfail(strict=True, reason=LAYOUT)
def test_with_the_layout_off_a_start_is_ready_on_the_legacy_route(surface: Surface, session: Session, people: Any) -> None:
    answer = _call(surface, session, people.expert, OPERATIONS[14])
    assert answer.status in (200, 404)  # 404 only for a version that does not exist
    if answer.status == 200:
        assert _json(answer)["route"] == "legacy"
    else:  # pragma: no cover - the stub never gets here; the lane seeds a version
        raise AssertionError(answer.body)
