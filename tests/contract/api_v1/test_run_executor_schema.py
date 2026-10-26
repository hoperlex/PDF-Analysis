"""`EXEC-PAR-START-01`: the sealed shape of a run's executor choice and report.

The frozen document is the authority and a real JSON Schema 2020-12 validator judges it (the
`validate` fixture drives the governance interpreter), so closure, the id pattern and the nullable
union are proven by the validator and not by a hand-written copy of those rules. The models the
server answers with are held to the same document.

* `StartRunRequest.executor_connection_id` is **optional and not nullable**: absent is today's
  route, `null` is a malformed request, a wrong-shaped id is refused;
* `RunStatus.executor` is optional and nullable, and names three properties of a closed
  `RunExecutor` -- the connection, its display name and the pinned model -- so no kind, address,
  key, probe or token can ride along;
* what the server's body renderer produces for a run on an executor passes the contract, and for a
  run on none carries no `executor` key at all.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Callable

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.schemas.runs import RunExecutorView, RunStatusView, run_status_body

Validate = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]

CONNECTION = "exc_01M2545JSD15ETSNNV904X991N"
EXECUTOR = {"connection_id": CONNECTION, "display_name": "Сервер 1", "pin_id": "anthropic/claude-opus-5"}
RUN = {
    "run_id": "run_01M2545JSD15ETSNNV904X993K",
    "project_uid": "prj_01M2545JSD15ETSNNV904X991F",
    "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
    "state": "queued",
    "provider_mode": "live",
    "stages": [],
    "created_at": "2026-10-26T12:00:00Z",
}
START = {"version_uid": "ver_01M2545JSD15ETSNNV904X991J"}


def _verdicts(validate: Validate, document: dict[str, Any], schema: str, cases: dict[str, Any]) -> dict[str, bool]:
    results = validate(
        document, [{"name": name, "schema": schema, "payload": payload} for name, payload in cases.items()],
    )
    return {name: results[name]["valid"] for name in cases}


# --- StartRunRequest ---------------------------------------------------------------------------


def test_the_start_request_accepts_a_named_connection_and_stays_valid_without_one(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    cases = {
        "absent_is_the_route": START,
        "named": {**START, "executor_connection_id": CONNECTION},
        "named_beside_the_mode": {**START, "provider_mode": "live", "executor_connection_id": CONNECTION},
    }
    assert _verdicts(validate, openapi_document, "StartRunRequest", cases) == {name: True for name in cases}


def test_the_start_request_refuses_a_null_a_wrong_shaped_id_and_any_other_property(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    cases = {
        "null_is_not_absent": {**START, "executor_connection_id": None},
        "an_id_of_another_kind": {**START, "executor_connection_id": "usr_01M2545JSD15ETSNNV904X991N"},
        "not_a_ulid": {**START, "executor_connection_id": "exc_not-a-ulid"},
        "lower_case": {**START, "executor_connection_id": CONNECTION.lower()},
        "a_number": {**START, "executor_connection_id": 7},
        "a_second_name_for_it": {**START, "executor": CONNECTION},
        "no_version": {"executor_connection_id": CONNECTION},
    }
    assert _verdicts(validate, openapi_document, "StartRunRequest", cases) == {name: False for name in cases}


def test_the_model_the_router_validates_with_accepts_and_refuses_the_same_ids() -> None:
    assert models.StartRunRequest.model_validate({**START, "executor_connection_id": CONNECTION}).executor_connection_id == CONNECTION
    assert models.StartRunRequest.model_validate(START).executor_connection_id is None
    for refused in ({**START, "executor_connection_id": None}, {**START, "executor_connection_id": "exc_x"}):
        with pytest.raises(ValueError):
            models.StartRunRequest.model_validate(refused)


def test_the_request_schema_declares_the_field_optional_and_by_reference(openapi_document: dict[str, Any]) -> None:
    schema = openapi_document["components"]["schemas"]["StartRunRequest"]
    assert schema["required"] == ["version_uid"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["executor_connection_id"]["$ref"] == "#/components/schemas/ExecutorConnectionId"
    assert set(schema["properties"]) == {"version_uid", "provider_mode", "executor_connection_id"}


# --- RunStatus.executor --------------------------------------------------------------------------


def test_the_status_accepts_an_executor_a_null_and_no_executor(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    cases = {
        "on_an_executor": {**RUN, "executor": EXECUTOR},
        "explicit_null": {**RUN, "executor": None},
        "none_at_all": RUN,
    }
    assert _verdicts(validate, openapi_document, "RunStatus", cases) == {name: True for name in cases}


def _executor_with(**changes: Any) -> dict[str, Any]:
    return {**RUN, "executor": {**EXECUTOR, **changes}}


def test_the_status_refuses_anything_beyond_the_three_properties_of_the_executor(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    cases = {
        "a_kind": _executor_with(kind="http_api"),
        "an_address": _executor_with(base_url="https://gateway.example"),
        "a_key": _executor_with(api_key="sk-sentinel"),
        "a_token": _executor_with(token="runner-token"),
        "a_probe": _executor_with(probe_outcome="ok"),
        "a_revision": _executor_with(revision_id="exr_01M2545JSD15ETSNNV904X991N"),
        "no_connection": {**RUN, "executor": {k: v for k, v in EXECUTOR.items() if k != "connection_id"}},
        "no_name": {**RUN, "executor": {k: v for k, v in EXECUTOR.items() if k != "display_name"}},
        "no_pin": {**RUN, "executor": {k: v for k, v in EXECUTOR.items() if k != "pin_id"}},
        "empty_name": _executor_with(display_name=""),
        "name_over_120": _executor_with(display_name="я" * 121),
        "connection_of_another_kind": _executor_with(connection_id="run_01M2545JSD15ETSNNV904X993K"),
        "executor_as_a_string": {**RUN, "executor": CONNECTION},
        "executor_as_a_list": {**RUN, "executor": [EXECUTOR]},
    }
    assert _verdicts(validate, openapi_document, "RunStatus", cases) == {name: False for name in cases}


def test_the_executor_schema_is_closed_and_names_exactly_three_properties(openapi_document: dict[str, Any]) -> None:
    schemas = openapi_document["components"]["schemas"]
    executor = schemas["RunExecutor"]
    assert set(executor["properties"]) == {"connection_id", "display_name", "pin_id"}
    assert set(executor["required"]) == set(executor["properties"])
    assert executor["additionalProperties"] is False
    status = schemas["RunStatus"]
    assert "executor" in status["properties"] and "executor" not in status["required"]
    assert status["properties"]["executor"]["oneOf"] == [
        {"$ref": "#/components/schemas/RunExecutor"}, {"type": "null"},
    ]


@pytest.mark.parametrize("forbidden", [
    "kind", "base_url", "api_key", "token", "secret", "secrets", "host_key", "ssh_host", "probe",
    "revision_id", "settings", "allow_client_documents",
])
def test_no_secret_address_or_probe_property_is_declared_on_the_executor(
    openapi_document: dict[str, Any], forbidden: str,
) -> None:
    assert forbidden not in openapi_document["components"]["schemas"]["RunExecutor"]["properties"]


# --- what the server renders -----------------------------------------------------------------------


def _view(executor: RunExecutorView | None) -> RunStatusView:
    return RunStatusView(
        run_id=RUN["run_id"], project_uid=RUN["project_uid"], version_uid=RUN["version_uid"],
        state="queued", provider_mode="live", created_at=datetime(2026, 10, 26, 12, tzinfo=timezone.utc),
        executor=executor,
    )


def test_what_the_body_renderer_answers_passes_the_contract_with_and_without_an_executor(
    validate: Validate, openapi_document: dict[str, Any],
) -> None:
    on = run_status_body(_view(RunExecutorView(**EXECUTOR)))
    off = run_status_body(_view(None))
    assert on["executor"] == EXECUTOR
    assert "executor" not in off, "a run on no executor is rendered exactly as before the field"
    assert _verdicts(validate, openapi_document, "RunStatus", {"on": on, "off": off}) == {
        "on": True, "off": True,
    }
    assert models.RunStatus.model_validate(on).executor.connection_id == CONNECTION
    assert models.RunStatus.model_validate(off).executor is None


def test_the_served_model_and_the_frozen_document_declare_the_same_executor(
    openapi_document: dict[str, Any],
) -> None:
    served = models.RunExecutor.model_json_schema()
    frozen = copy.deepcopy(openapi_document["components"]["schemas"]["RunExecutor"])
    assert set(served["properties"]) == set(frozen["properties"])
    assert set(served["required"]) == set(frozen["required"])
    assert served["additionalProperties"] is False
