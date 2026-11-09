"""`HOSTS-SEAL-1` (contract 1.45.0): the fifteen host and stage-layout operations over the real seam, with the services `HOSTS-BACKEND-01` and
`HOSTS-LAYOUT-01` filled and `HOSTS-INT-WIRE-01` wired.

HEAVY: real PostgreSQL rows for the accounts, inside the suite's rolled-back transaction, through the shipped ``CredentialAdapter``.

Three groups, each shown able to fail:

* **the seam** -- the viewer («Наблюдатель», `R-150w`) is denied every one of the fifteen, and an expert is denied the administrator's;
* **the services** -- an administrator's well-formed call to each operation reaches its service and answers what the service answers (an unknown
  server is ``404``, an empty stand lists nothing, a layout that cannot be switched on is a ``409``), and **none** is the old stub's ``503
  dependency_unavailable`` naming ``executor_hosts`` or ``stage_models``: a stub that answered 200 with an empty body would be a silent fallback
  (AGENTS section 4), and one that was never replaced would hide that the lanes are not wired;
* **what the lanes owe, now owed no more** -- the ``xfail(strict=True)`` cases of the stubs' time, turned into plain tests: the empty stand, the
  unknown server, the layout and the catalogue as the contract's file, and the readiness that refuses typed while no cost preflight is attached.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.api.routers import build_router
from auditmanager.api.schemas import models
from auditmanager.bootstrap.adapters import CredentialAdapter
from auditmanager.bootstrap.hosts_adapter import ExecutorHostAdapter
from auditmanager.bootstrap.stage_plan_adapter import StageModelAdapter
from auditmanager.bootstrap.stage_plan_service import StagePlanService
from w13_api_driver import Surface

from .identity_surface import SIGNER, credential_for, make_account

HOST = "exh_01ARZ3NDEKTSV4RRFFQ69G5FAV"
INSTALL = "exai_01ARZ3NDEKTSV4RRFFQ69G5FAV"
FINGERPRINT = "SHA256:" + "A" * 43
CELL = {"cell_key": "text:main", "row": "text", "role": "main", "model_id": "claude-sonnet-5-5", "effort": "medium",
        "max_output_tokens": 16000, "timeout_seconds": 600}

#: (operationId, method, path, body, administrator only, the answers the service gives an administrator: (status, ``details.dependency``))
OPERATIONS: list[tuple[str, str, str, Any, bool, frozenset[tuple[int, str | None]]]] = [
    ("listExecutorHosts", "GET", "/executor-hosts", None, False, frozenset({(200, None)})),
    ("getExecutorHost", "GET", f"/executor-hosts/{HOST}", None, False, frozenset({(404, None)})),
    ("getExecutorHostDetails", "GET", f"/executor-hosts/{HOST}/details", None, True, frozenset({(404, None)})),
    ("setExecutorHostEnabled", "PUT", f"/executor-hosts/{HOST}/enabled", {"enabled": False}, True, frozenset({(404, None)})),
    ("setExecutorHostSlots", "PUT", f"/executor-hosts/{HOST}/slots", {"slots": {"codex": 2}}, True, frozenset({(404, None)})),
    ("archiveExecutorHost", "POST", f"/executor-hosts/{HOST}/archive", None, True, frozenset({(404, None)})),
    # no agent package is built into a test run: the service says so typed (``agent_package``) and a built one is a ``201``
    ("issueExecutorHostEnrollment", "POST", "/executor-hosts/enrollments", {"display_name": "adm1.hlab.kz"}, True,
     frozenset({(201, None), (503, "agent_package")})),
    # the API of this stand holds no public key of the secrets ring: the key of an install is not sealed, typed (``secrets_public_key_missing``)
    ("createExecutorHostAgentInstall", "POST", "/executor-hosts/agent-installs",
     {"display_name": "adm1.hlab.kz", "access": "generated_key", "ssh_host": "adm1.hlab.kz", "ssh_port": 22, "ssh_user": "root"},
     True, frozenset({(201, None), (503, "secrets_public_key_missing"), (503, "agent_package")})),
    ("getExecutorHostAgentInstall", "GET", f"/executor-hosts/{HOST}/agent-installs/{INSTALL}", None, True, frozenset({(404, None)})),
    ("confirmExecutorHostAgentInstallHostKey", "POST", f"/executor-hosts/{HOST}/agent-installs/{INSTALL}/confirm-host-key",
     {"host_key_fingerprint": FINGERPRINT}, True, frozenset({(404, None)})),
    ("getStageModelLayout", "GET", "/model-layout", None, False, frozenset({(200, None)})),
    # one cell is not a layout: every row has its cell
    ("reviseStageModelLayout", "POST", "/model-layout/revisions", {"kit": "custom", "cells": [CELL]}, True, frozenset({(422, None)})),
    # the surface's service has the process's provider source, which is not ``database``: the switch cannot be turned on
    ("setStageModelLayoutEnabled", "PUT", "/model-layout/enabled", {"enabled": True}, True, frozenset({(409, None)})),
    ("listModelCatalogue", "GET", "/model-catalogue", None, False, frozenset({(200, None)})),
    # no cost preflight is attached to this service: the readiness refuses typed, it does not answer a route it did not read
    ("getRunStartReadiness", "POST", "/runs/start-readiness", {"version_uid": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, False,
     frozenset({(503, "analysis_cost_preflight")})),
]
IDS = [operation[0] for operation in OPERATIONS]


@pytest.fixture
def surface(session_factory: sessionmaker[Session]) -> Surface:
    return Surface(
        build_router(
            projects=None, documents=None, runs=None, findings=None, decisions=None, exports=None,  # type: ignore[arg-type]
            credentials=CredentialAdapter(session_factory, users=UserRepository(), accounts=AccountRepository(), signer=SIGNER),
            executor_hosts=ExecutorHostAdapter(session_factory, public_origin="https://stand.example"),
            stage_models=StageModelAdapter(
                session_factory, service=StagePlanService(session_factory=session_factory, provider_source="environment")),
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
def test_an_administrators_call_reaches_its_service_and_is_never_the_old_stub(
    surface: Surface, session: Session, people: Any, operation: Any
) -> None:
    answer = _call(surface, session, people.admin, operation)
    envelope = _json(answer)
    dependency = envelope.get("details", {}).get("dependency") if answer.status == 503 else None
    assert dependency not in ("executor_hosts", "stage_models"), (operation[0], "the stub still answers", envelope)
    assert (answer.status, dependency) in operation[5], (operation[0], answer.status, answer.body)


# --- what the lanes owed ---------------------------------------------------------------------


def test_an_empty_stand_lists_no_servers_and_a_zero_summary(surface: Surface, session: Session, people: Any) -> None:
    answer = _call(surface, session, people.admin, OPERATIONS[0])
    assert answer.status == 200
    assert _json(answer) == {"items": [], "online": 0, "total": 0, "slots_free": 0, "slots_total": 0}


def test_an_unknown_server_is_not_found(surface: Surface, session: Session, people: Any) -> None:
    assert _call(surface, session, people.admin, OPERATIONS[1]).status == 404


def test_the_layout_is_the_wire_shape_and_an_expert_reads_it(surface: Surface, session: Session, people: Any) -> None:
    answer = _call(surface, session, people.expert, OPERATIONS[10])
    assert answer.status == 200
    layout = models.StageModelLayout.model_validate(_json(answer))
    assert isinstance(layout.enabled, bool) and isinstance(layout.history, list)


def test_the_catalogue_is_the_file_of_the_contract(surface: Surface, session: Session, people: Any) -> None:
    file = json.loads((Path(__file__).resolve().parents[3] / "contracts/analysis/v1/model-catalogue.json").read_text(encoding="utf-8"))
    answer = _call(surface, session, people.expert, OPERATIONS[13])
    assert answer.status == 200
    body = _json(answer)
    assert body["contract_version"] == file["contract_version"]
    assert [(item["provider"], item["model_id"], item["access"], item["accepted_reported"]) for item in body["items"]] == [
        (entry["provider"], entry["model_id"], entry["access"], entry["accepted_reported"]) for entry in file["entries"]]
