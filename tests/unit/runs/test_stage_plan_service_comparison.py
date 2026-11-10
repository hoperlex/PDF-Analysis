"""`HOSTS-CMP-01`: the layout service with the comparison cells -- the request, the stored revision, the view and the cells no server serves."""

from __future__ import annotations

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap import stage_plan_service as service_module
from auditmanager.runs import stage_layout as layout

from .stage_layout_fakes import ADMIN, NOWHERE, ROLES, SUBSCRIPTION, MemoryAvailability
from .test_stage_plan_service import make, refusal

KINDS = layout.COMPARISON_KINDS


@pytest.fixture
def events(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(service_module, "append_execution_event", lambda session, **kw: seen.append(kw))
    monkeypatch.setattr(service_module, "_roles", lambda session, uid: ROLES[uid])
    return seen


def body(kit="codex_only", *, comparison="table", edit=None, rows_edit=None):
    cells = layout.cells_to_wire(layout.preset_cells(kit if kit != "custom" else "claude_only"))
    for cell in cells:
        if rows_edit and cell["row"] in rows_edit:
            cell.update(rows_edit[cell["row"]])
    document: dict = {"kit": kit, "cells": cells}
    if comparison == "table":
        wire = layout.comparison_cells_to_wire(layout.comparison_preset_cells(kit if kit != "custom" else "codex_only"))
        for item in wire:
            if edit and item["work_kind"] in edit:
                item.update(edit[item["work_kind"]])
        document["comparison_cells"] = wire
    elif comparison is not None:
        document["comparison_cells"] = comparison
    return models.ReviseStageModelLayoutRequest.model_validate(document)


def test_a_revision_with_the_comparison_cells_stores_them_and_the_view_returns_them(events):
    service, store = make()
    view = service.revise_layout(body=body(), user_uid=ADMIN, idempotency_key="k")
    assert [item["work_kind"] for item in view["current"]["comparison_cells"]] == list(KINDS)
    assert view["current"]["comparison_cells"][0] == {
        "work_kind": "comparison_pair_check", "model_id": "gpt-6-astra", "effort": "high", "max_output_tokens": 1_200,
        "timeout_seconds": 900}
    assert store.revisions[0].comparison_cells == layout.comparison_preset_cells("codex_only")
    assert not {cell["row"] for cell in view["current"]["cells"]} & set(KINDS), "the analysis cells stay the six rows"
    models.StageModelLayout.model_validate(view)


def test_a_kit_may_lengthen_a_window_and_custom_may_choose_any_pair_of_the_catalogue(events):
    service, store = make()
    longer = body("claude_only", edit={"comparison_report": {"timeout_seconds": 3_000, "max_output_tokens": 4_000}})
    view = service.revise_layout(body=longer, user_uid=ADMIN, idempotency_key="a")
    report = view["current"]["comparison_cells"][3]
    assert (report["timeout_seconds"], report["max_output_tokens"], view["current"]["kit"]) == (3_000, 4_000, "claude_only")
    other = body("custom", edit={"comparison_spec": {"model_id": "claude-opus-5-5", "effort": "medium"}})
    custom = service.revise_layout(body=other, user_uid=ADMIN, idempotency_key="b")
    assert custom["current"]["comparison_cells"][2]["model_id"] == "claude-opus-5-5" and custom["current"]["kit"] == "custom"


def test_a_revision_without_the_list_follows_its_sets_table_and_a_custom_one_has_none(events):
    service, store = make()
    named = service.revise_layout(body=body("claude_only", comparison=None), user_uid=ADMIN, idempotency_key="a")
    assert store.revisions[0].comparison_cells is None, "nothing is stored that the request did not carry"
    assert [(i["work_kind"], i["model_id"]) for i in named["current"]["comparison_cells"]] == [(k, "claude-sonnet-5-5") for k in KINDS]
    custom = service.revise_layout(body=body("custom", comparison=None), user_uid=ADMIN, idempotency_key="b")
    assert "comparison_cells" not in custom["current"], "no model is chosen for a comparison by a « Свой набор » saved without them"
    models.StageModelLayout.model_validate(custom)


@pytest.mark.parametrize("edit,constraint", [
    ({"comparison_spec": {"model_id": "claude-haiku-5"}}, "model_not_in_catalogue"),
    ({"comparison_spec": {"effort": "low", "model_id": "claude-opus-5-5"}}, "effort_not_offered_for_model"),
    ({"comparison_spec": {"model_id": "claude-sonnet-5-5"}}, "kit_does_not_match_cells"),
])
def test_a_comparison_cell_the_catalogue_or_the_set_does_not_allow_is_refused_and_writes_nothing(events, edit, constraint):
    service, store = make()
    kit = "codex_only"
    error = refusal(service.revise_layout, body=body(kit, edit=edit), user_uid=ADMIN, idempotency_key="k")
    assert error.detail_fields["constraint"] == constraint
    assert not store.revisions and not events and not service._commands.records


def test_a_list_with_a_kind_missing_or_repeated_is_refused(events):
    service, store = make()
    wire = layout.comparison_cells_to_wire(layout.comparison_preset_cells("codex_only"))
    with pytest.raises(Exception):  # the wire is four cells, each once: three are not a request
        body(comparison=wire[:3])
    with pytest.raises(Exception):
        body(comparison=[*wire, wire[0]])
    # four cells with one kind twice get through the wire and are the service's to refuse: a kind is missing and another is repeated
    twice = body(comparison=[wire[0], wire[0], wire[1], wire[2]])
    assert refusal(service.revise_layout, body=twice, user_uid=ADMIN, idempotency_key="b").detail_fields == {
        "field": "comparison_cells", "constraint": "cell_repeated"}
    assert not store.revisions


def test_the_stage_review_is_not_a_kind_of_the_wire():
    wire = layout.comparison_cells_to_wire(layout.comparison_preset_cells("codex_only"))
    wire[0]["work_kind"] = "comparison_stage_review"
    with pytest.raises(Exception):
        body(comparison=wire)


def test_the_comparison_list_is_part_of_the_requests_identity_only_when_it_was_sent(events):
    service, store = make()
    service.revise_layout(body=body("claude_only", comparison=None), user_uid=ADMIN, idempotency_key="k")
    again = service.revise_layout(body=body("claude_only", comparison=None), user_uid=ADMIN, idempotency_key="k")
    assert len(store.revisions) == 1 and again["current"]["revision_no"] == 1
    with_list = body("claude_only")
    assert refusal(service.revise_layout, body=with_list, user_uid=ADMIN, idempotency_key="k").code.value == "idempotency_key_reuse"


def test_the_layout_names_the_comparison_cells_no_server_serves(events):
    # Codex is on a server for the rows' models but nothing serves gpt-6-astra: its two comparison cells are « нет на серверах »
    service, _ = make(availability=MemoryAvailability({
        "claude-opus-5-5": SUBSCRIPTION, "claude-sonnet-5-5": SUBSCRIPTION, "gpt-6.1-sol": SUBSCRIPTION, "gpt-6-sol": SUBSCRIPTION,
        "gpt-6-astra": NOWHERE}))
    service.revise_layout(body=body("codex_only"), user_uid=ADMIN, idempotency_key="k")
    keys = service.get_layout()["unavailable_cell_keys"]
    assert "comparison_pair_check:main" in keys and "comparison_spec:main" in keys
    assert "comparison_report:main" not in keys and "comparison_sheet_changes:main" not in keys
    assert "norms:main" in keys, "the rows are named as before"
    assert len(keys) <= 32
    models.StageModelLayout.model_validate(service.get_layout())
