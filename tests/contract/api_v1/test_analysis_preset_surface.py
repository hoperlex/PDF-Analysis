"""`ANALYSIS-PRESETS-01`: the sealed shape of a preset and of its use at run start.

Two kinds of claim, both judged against the frozen document (a real JSON Schema 2020-12 validator, the
`validate` fixture) and not against a hand-written copy of its rules:

* **a preset holds only what a run start can take.** The premise of the lane is that a start selects one
  setting per run, the executor connection; the cost ceiling is a process-wide setting and no threshold
  is an input of a start. This file pins the set of start fields and shows every setting of a preset is
  one of them, so a per-run limit added to `StartRunRequest` later is a decision somebody makes about
  presets too, and a field added to a preset that no start could take is red here;
* **the wire shapes**: closure, the id pattern (`evt_`), the bounds, the optional-and-nullable
  `RunStatus.preset`, and `StartRunRequest.preset_id` optional and not nullable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.schemas.runs import RunPresetView, RunStatusView, run_status_body

Validate = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]

PRESET = "evt_01M2545JSD15ETSNNV904X991N"
REVISION = "evt_01M2545JSD15ETSNNV904X991P"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991N"
USER = "usr_01M2545JSD15ETSNNV904X991N"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PRESET_BODY = {
    "preset_id": PRESET, "revision_id": REVISION, "revision_no": 2, "name": "Быстрый черновик",
    "executor_connection_id": CONNECTION, "state": "active",
    "created_at": "2026-10-27T10:00:00Z", "revised_at": "2026-10-27T11:00:00Z", "revised_by": USER,
}
RUN = {
    "run_id": "run_01M2545JSD15ETSNNV904X993K", "project_uid": "prj_01M2545JSD15ETSNNV904X991F",
    "version_uid": VERSION, "state": "queued", "provider_mode": "live", "stages": [],
    "created_at": "2026-10-27T12:00:00Z",
}


def _verdicts(validate: Validate, document: dict[str, Any], schema: str, cases: dict[str, Any]) -> dict[str, bool]:
    results = validate(
        document, [{"name": name, "schema": schema, "payload": payload} for name, payload in cases.items()],
    )
    return {name: results[name]["valid"] for name in cases}


# --- the premise: a preset holds what a start can take -------------------------------------------


def test_a_run_start_takes_exactly_these_fields(openapi_document: dict[str, Any]) -> None:
    """The set that the premise was captured from. A new field here (a per-run cost limit, a
    threshold) means somebody decides whether a preset holds it too, and then edits this literal."""
    start = openapi_document["components"]["schemas"]["StartRunRequest"]
    assert set(start["properties"]) == {"version_uid", "provider_mode", "executor_connection_id", "preset_id"}
    assert start["required"] == ["version_uid"]
    reaudit = openapi_document["paths"]["/runs/{run_id}/reaudit"]["post"]
    assert "requestBody" not in reaudit  # a re-audit takes nothing, so a preset cannot fill anything there


def test_every_setting_of_a_preset_is_a_field_a_run_start_takes(openapi_document: dict[str, Any]) -> None:
    schemas = openapi_document["components"]["schemas"]
    settings = set(schemas["SaveAnalysisPresetRequest"]["properties"]) - {"name"}
    assert settings == {"executor_connection_id"}
    start_fields = set(schemas["StartRunRequest"]["properties"]) - {"version_uid", "preset_id"}
    # `provider_mode` is a start field a preset deliberately does not hold: the deployment's own mode
    # is the only one a start may name, so there is nothing to choose.
    assert settings <= start_fields
    assert start_fields - settings == {"provider_mode"}
    # and the setting a preset names is the same type the start field is
    assert (schemas["SaveAnalysisPresetRequest"]["properties"]["executor_connection_id"]["$ref"]
            == schemas["StartRunRequest"]["properties"]["executor_connection_id"]["$ref"]
            == "#/components/schemas/ExecutorConnectionId")


def test_a_preset_holds_no_limit_no_threshold_and_no_mode(openapi_document: dict[str, Any]) -> None:
    for name in ("AnalysisPreset", "SaveAnalysisPresetRequest"):
        properties = set(openapi_document["components"]["schemas"][name]["properties"])
        forbidden = {key for key in properties if any(
            word in key for word in ("cost", "limit", "ceiling", "threshold", "budget", "provider_mode"))}
        assert forbidden == set(), (name, forbidden)


# --- the preset ----------------------------------------------------------------------------------


def test_a_preset_is_closed_and_its_ids_are_evt_identities(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    cases = {
        "complete": PRESET_BODY,
        "archived": {**PRESET_BODY, "state": "archived"},
        "an_extra_property": {**PRESET_BODY, "note": "x"},
        "an_unknown_state": {**PRESET_BODY, "state": "deleted"},
        "a_connection_id_for_the_preset": {**PRESET_BODY, "preset_id": CONNECTION},
        "revision_zero": {**PRESET_BODY, "revision_no": 0},
        "an_empty_name": {**PRESET_BODY, "name": ""},
        "a_name_of_121": {**PRESET_BODY, "name": "Я" * 121},
        "a_missing_author": {k: v for k, v in PRESET_BODY.items() if k != "revised_by"},
    }
    verdicts = _verdicts(validate, openapi_document, "AnalysisPreset", cases)
    assert verdicts == {name: name in ("complete", "archived") for name in cases}


def test_the_save_request_is_the_full_settings_and_nothing_else(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    ok = {"name": "Быстрый черновик", "executor_connection_id": CONNECTION}
    cases = {
        "complete": ok,
        "no_name": {"executor_connection_id": CONNECTION},
        "no_connection": {"name": "Имя"},
        "null_connection": {**ok, "executor_connection_id": None},
        "a_patch_field": {**ok, "state": "archived"},
        "a_cost_limit": {**ok, "cost_limit_usd": 1},
        "empty_name": {**ok, "name": ""},
        "another_id_kind": {**ok, "executor_connection_id": PRESET},
    }
    assert _verdicts(validate, openapi_document, "SaveAnalysisPresetRequest", cases) == {
        name: name == "complete" for name in cases}


def test_the_list_is_bounded_to_the_hundred_presets_that_can_exist(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    cases = {"empty": {"items": []}, "one": {"items": [PRESET_BODY]}, "too_many": {"items": [PRESET_BODY] * 101},
             "no_items": {}}
    assert _verdicts(validate, openapi_document, "AnalysisPresetList", cases) == {
        "empty": True, "one": True, "too_many": False, "no_items": False}


# --- the start and the status --------------------------------------------------------------------


def test_the_start_request_accepts_a_preset_and_refuses_a_null_and_a_wrong_id(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    start = {"version_uid": VERSION}
    cases = {
        "absent": start,
        "named": {**start, "preset_id": PRESET},
        "null_is_not_absent": {**start, "preset_id": None},
        "a_connection_id": {**start, "preset_id": CONNECTION},
        "not_a_ulid": {**start, "preset_id": "evt_not-a-ulid"},
        "a_number": {**start, "preset_id": 7},
    }
    assert _verdicts(validate, openapi_document, "StartRunRequest", cases) == {
        name: name in ("absent", "named") for name in cases}


def test_the_run_status_may_carry_a_closed_preset_and_may_omit_it(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    preset = {"preset_id": PRESET, "revision_no": 2, "name": "Быстрый черновик"}
    cases = {
        "none": RUN,
        "a_preset": {**RUN, "preset": preset},
        "null": {**RUN, "preset": None},
        "a_revision_id": {**RUN, "preset": {**preset, "revision_id": REVISION}},
        "no_name": {**RUN, "preset": {"preset_id": PRESET, "revision_no": 2}},
        "revision_zero": {**RUN, "preset": {**preset, "revision_no": 0}},
    }
    assert _verdicts(validate, openapi_document, "RunStatus", cases) == {
        name: name in ("none", "a_preset", "null") for name in cases}


def test_the_body_renderer_carries_the_preset_only_when_the_run_used_one(
    validate: Validate, openapi_document: dict[str, Any]
) -> None:
    created = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def view(**extra: Any) -> RunStatusView:
        return RunStatusView(
            run_id=RUN["run_id"], project_uid=RUN["project_uid"], version_uid=VERSION, state="queued",
            provider_mode="live", created_at=created, **extra)

    without = run_status_body(view())
    assert "preset" not in without  # a run with no preset has the body it always had
    with_preset = run_status_body(view(preset=RunPresetView(preset_id=PRESET, revision_no=2, name="Быстрый черновик")))
    assert with_preset["preset"] == {"preset_id": PRESET, "revision_no": 2, "name": "Быстрый черновик"}
    assert _verdicts(validate, openapi_document, "RunStatus", {"without": without, "with": with_preset}) == {
        "without": True, "with": True}


def test_the_models_the_router_validates_with_accept_and_refuse_the_same_ids() -> None:
    models.StartRunRequest.model_validate({"version_uid": VERSION, "preset_id": PRESET})
    for bad in (None, CONNECTION, "evt_x", 7):
        with pytest.raises(Exception):
            models.StartRunRequest.model_validate({"version_uid": VERSION, "preset_id": bad})
    models.SaveAnalysisPresetRequest.model_validate({"name": "Имя", "executor_connection_id": CONNECTION})
    with pytest.raises(Exception):
        models.SaveAnalysisPresetRequest.model_validate({"name": "", "executor_connection_id": CONNECTION})
