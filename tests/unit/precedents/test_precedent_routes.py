"""`PREC-PASS`: the two reads of the surface answer through their port, and the viewer is denied (contract 1.51.0).

The routes are mounted alone with a fake port that holds what the service would answer (the service itself is shown over a database in
``tests/integration/precedents/test_precedent_pass.py``). What is shown: the contract's shapes on the wire (a member with no value is absent, never null),
the sleeping answer kept when no port is wired, the errors of the port as the contract's catalogue says them, the register that keeps the viewer out,
and the service's own refusal of a role that is neither expert nor administrator **before it reads anything**.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.routers.precedents import build_precedent_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES, ROLE_ADMIN, ROLE_EXPERT, ROLE_VIEWER, RunnerIdentity, Subject, current_runner, current_subject
from auditmanager.precedents.public import PrecedentService
from auditmanager.shared.errors import DomainError, ErrorCode

RUN = "run_01M2545JSD15ETSNNV904X991K"
FINDING = "fnd_01M2545JSD15ETSNNV904X991K"
CASE = "dmc_01M2545JSD15ETSNNV904X991K"
USER = "usr_01M2545JSD15ETSNNV904X991K"


class FakePort:
    def __init__(self) -> None:
        self.asked: list[tuple[str, str, str]] = []
        self.run_answer: Mapping[str, Any] = {"run_id": RUN, "available": False, "items": []}
        self.finding_answer: Mapping[str, Any] = {"finding_uid": FINDING, "run_id": RUN, "available": False, "hints": [], "cases": [], "possible_norms": []}
        self.error: DomainError | None = None

    def get_run_precedents(self, *, run_id: str, user_uid: str) -> Mapping[str, Any]:
        self.asked.append(("run", run_id, user_uid))
        if self.error is not None:
            raise self.error
        return self.run_answer

    def get_finding_precedents(self, *, finding_uid: str, user_uid: str) -> Mapping[str, Any]:
        self.asked.append(("finding", finding_uid, user_uid))
        if self.error is not None:
            raise self.error
        return self.finding_answer


def client_for(port: FakePort | None) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_precedent_routes(router, precedents=port)
    app.include_router(router)
    app.dependency_overrides[current_subject] = lambda: Subject(user_uid=USER, login="e@suite.invalid", token_epoch=1, display_label="E")
    app.dependency_overrides[current_runner] = lambda: RunnerIdentity(token_id="ert_01M2545JSD15ETSNNV904X991K", connection_id=None,
                                                                      host_id="exh_01M2545JSD15ETSNNV904X991K")
    return TestClient(app, raise_server_exceptions=False)


def test_without_a_port_the_two_reads_keep_the_sealed_answer() -> None:
    client = client_for(None)
    for path in (f"/runs/{RUN}/precedents", f"/findings/{FINDING}/precedents"):
        answer = client.get(path)
        assert answer.status_code == 503 and answer.json()["details"] == {"dependency": "precedents"}, answer.text


def test_a_run_nobody_computed_is_available_false_with_an_empty_list_and_no_pass_state() -> None:
    port = FakePort()
    answer = client_for(port).get(f"/runs/{RUN}/precedents")
    assert answer.status_code == 200 and answer.json() == {"run_id": RUN, "available": False, "items": []}, "optional members are absent, never null"
    assert port.asked == [("run", RUN, USER)], "the caller's identity reaches the port"
    models.RunPrecedents.model_validate(answer.json())


def test_a_run_with_a_result_answers_the_contracts_shape() -> None:
    port = FakePort()
    port.run_answer = {"run_id": RUN, "available": True, "pass_state": "done", "revision": 3, "items": [
        {"finding_uid": FINDING, "label": "cancel_suggested", "critic_reviewed": True, "hint_codes": ["p1"], "revision": 3,
         "votes": {"total": 7, "rejected": 7, "accepted": 0, "independent": 7, "projects": 2}}]}
    answer = client_for(port).get(f"/runs/{RUN}/precedents")
    assert answer.status_code == 200, answer.text
    body = models.RunPrecedents.model_validate(answer.json())
    assert (body.available, body.pass_state.value, body.revision, body.items[0].label.value) == (True, "done", 3, "cancel_suggested")


def test_a_card_without_an_answer_has_no_label_and_may_still_have_norms() -> None:
    port = FakePort()
    norm = {"norm_document_id": "ndoc_01M2545JSD15ETSNNV904X991K", "norm_paragraph_id": "npar_01M2545JSD15ETSNNV904X991K",
            "designation": "СП 1", "clause_number": None, "page_label": 3}
    port.finding_answer = {**port.finding_answer, "possible_norms": [norm]}
    answer = client_for(port).get(f"/findings/{FINDING}/precedents")
    assert answer.status_code == 200, answer.text
    assert "label" not in answer.json() and answer.json()["available"] is False
    assert models.FindingPrecedents.model_validate(answer.json()).possible_norms[0].clause_number is None


def test_a_card_with_an_answer_carries_label_hints_cases_and_norms() -> None:
    port = FakePort()
    port.finding_answer = {
        "finding_uid": FINDING, "run_id": RUN, "available": True,
        "label": {"finding_uid": FINDING, "label": "often_rejected", "critic_reviewed": False, "hint_codes": ["p5"], "revision": 2,
                  "votes": {"total": 6, "rejected": 5, "accepted": 1, "independent": 6, "projects": 3}},
        "hints": [{"code": "p5", "case_id": CASE}],
        "cases": [{"case_id": CASE, "verdict": "rejected", "category": "dimensions", "similarity": 0.91, "finding_text": "Текст"}],
        "possible_norms": []}
    body = models.FindingPrecedents.model_validate(client_for(port).get(f"/findings/{FINDING}/precedents").json())
    assert body.label.label.value == "often_rejected" and body.hints[0].code.value == "p5" and body.cases[0].similarity == 0.91


@pytest.mark.parametrize(("code", "status"), [(ErrorCode.NOT_FOUND, 404), (ErrorCode.PERMISSION_DENIED, 403), (ErrorCode.DEPENDENCY_UNAVAILABLE, 503)])
def test_the_errors_of_the_port_are_the_catalogues(code: ErrorCode, status: int) -> None:
    port = FakePort()
    port.error = DomainError(code, aggregate_type="Run") if code is ErrorCode.NOT_FOUND else DomainError(code)
    for path in (f"/runs/{RUN}/precedents", f"/findings/{FINDING}/precedents"):
        answer = client_for(port).get(path)
        assert answer.status_code == status and answer.json()["error_code"] == code.value, answer.text


def test_the_register_keeps_the_viewer_out_of_both_reads() -> None:
    for operation in ("getRunPrecedents", "getFindingPrecedents"):
        assert OPERATION_ROLES[operation] == frozenset({ROLE_EXPERT, ROLE_ADMIN}) and ROLE_VIEWER not in OPERATION_ROLES[operation]


class _NothingToRead:
    """A session that fails the test if the service touches it: the role is checked before anything is read."""

    def __enter__(self) -> "_NothingToRead":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, *_: object, **__: object) -> None:
        raise AssertionError("a viewer's request read the database")


@pytest.mark.parametrize("roles", [frozenset({"viewer"}), frozenset(), frozenset({"runner"})])
def test_the_service_denies_a_caller_who_is_neither_expert_nor_administrator_before_it_reads_anything(roles: frozenset[str]) -> None:
    service = PrecedentService(lambda: _NothingToRead(), roles_of=lambda _session, _user: roles)  # type: ignore[arg-type]
    for call in (lambda: service.get_run_precedents(run_id=RUN, user_uid=USER), lambda: service.get_finding_precedents(finding_uid=FINDING, user_uid=USER)):
        with pytest.raises(DomainError) as caught:
            call()
        assert caught.value.code is ErrorCode.PERMISSION_DENIED
        assert caught.value.detail_fields["required_capability"] == "role:admin|expert"


def test_an_expert_and_an_administrator_pass_the_role_check() -> None:
    for roles in (frozenset({"expert"}), frozenset({"admin"}), frozenset({"viewer", "expert"})):
        service = PrecedentService(lambda: _NothingToRead(), roles_of=lambda _session, _user, roles=roles: roles)  # type: ignore[arg-type]
        with pytest.raises(AssertionError, match="read the database"):      # past the check, into the first read
            service.get_run_precedents(run_id=RUN, user_uid=USER)
