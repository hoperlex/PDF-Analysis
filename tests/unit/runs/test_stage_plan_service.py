"""`HOSTS-LAYOUT-01`: the layout service -- who may revise and enable, what is refused, the journal, the idempotency and the freezer."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.api.schemas import models
from auditmanager.bootstrap import stage_plan_service as service_module
from auditmanager.bootstrap.stage_plan_service import StagePlanService
from auditmanager.runs import stage_layout as layout
from auditmanager.runs.public import StagePlanFreezer
from auditmanager.shared.errors import DomainError, ErrorCode

from .stage_layout_fakes import (
    ADMIN, API_ONLY, EXPERT, NOWHERE, ROLES, VIEWER, FakeSessions, MemoryAvailability, MemoryCommands, MemoryStore, SUBSCRIPTION,
    everything, with_revision,
)


@pytest.fixture
def events(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(service_module, "append_execution_event", lambda session, **kw: seen.append(kw))
    monkeypatch.setattr(service_module, "_roles", lambda session, uid: ROLES[uid])
    return seen


def make(provider_source="database", availability=None, store=None):
    store = store or MemoryStore()
    service = StagePlanService(
        session_factory=FakeSessions(), store=store, commands=MemoryCommands(), provider_source=provider_source,
        availability=availability or everything(),
    )
    return service, store


def request(kit="claude_only", edit=None):
    cells = layout.cells_to_wire(layout.preset_cells(kit))
    for cell in cells:
        if edit and cell["row"] in edit:
            cell.update(edit[cell["row"]])
    return models.ReviseStageModelLayoutRequest.model_validate({"kit": kit, "cells": cells})


def refusal(call, *args, **kwargs) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    return caught.value


def test_an_administrator_revises_and_the_revision_is_the_current_one(events):
    service, store = make()
    view = service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="k1")
    assert view["current"]["revision_no"] == 1 and view["current"]["kit"] == "claude_only"
    assert view["current"]["created_by"] == ADMIN and view["enabled"] is False
    assert [cell["cell_key"] for cell in view["current"]["cells"]] == [c.cell_key for c in layout.preset_cells("claude_only")]
    assert events[0]["event_type"] == "stage_layout.revised" and events[0]["payload"]["actor_uid"] == ADMIN
    # the wire shape holds
    models.StageModelLayout.model_validate(view)
    second = service.revise_layout(body=request("codex_only"), user_uid=ADMIN, idempotency_key="k2")
    assert [row["revision_no"] for row in second["history"]] == [2, 1]
    assert second["current"]["kit"] == "codex_only"


@pytest.mark.parametrize("user", [EXPERT, VIEWER])
def test_only_an_administrator_revises_or_switches(events, user):
    service, store = make()
    assert refusal(service.revise_layout, body=request(), user_uid=user, idempotency_key="k").code is ErrorCode.PERMISSION_DENIED
    assert refusal(service.set_layout_enabled, enabled=True, user_uid=user, idempotency_key="k").code is ErrorCode.PERMISSION_DENIED
    assert not store.revisions and not store.events and not events


@pytest.mark.parametrize("edit,constraint", [
    ({"text": {"model_id": "claude-haiku-5"}}, "model_not_in_catalogue"),
    ({"text": {"effort": "high", "model_id": "claude-sonnet-5-5"}}, None),     # fine: Sonnet high
    ({"blocks": {"effort": "low"}}, "effort_not_offered_for_model"),             # Opus low
    ({"blocks": {"model_id": "claude-sonnet-5-5"}}, "block_scheme_not_listed"),
])
def test_a_layout_the_catalogue_does_not_offer_is_refused_and_writes_nothing(events, edit, constraint):
    service, store = make()
    body = request("claude_only", edit) if constraint is None else None
    if constraint is not None:
        # a hand-made body: the wire enums would stop `xhigh`, and the service must stop what they let through
        cells = layout.cells_to_wire(layout.preset_cells("claude_only"))
        for cell in cells:
            if cell["row"] in edit:
                cell.update(edit[cell["row"]])
        body = models.ReviseStageModelLayoutRequest.model_validate({"kit": "custom", "cells": cells})
        error = refusal(service.revise_layout, body=body, user_uid=ADMIN, idempotency_key="k")
        assert error.code is ErrorCode.VALIDATION_FAILED and error.detail_fields["constraint"] == constraint
        assert not store.revisions and not events and not service._commands.records
    else:
        service.revise_layout(body=models.ReviseStageModelLayoutRequest.model_validate(
            {"kit": "custom", "cells": body.model_dump(mode="json")["cells"]}), user_uid=ADMIN, idempotency_key="k")
        assert len(store.revisions) == 1


def test_a_named_kit_that_is_not_its_table_is_refused(events):
    service, store = make()
    body = request("claude_only", {"text": {"model_id": "claude-opus-5-5"}})
    error = refusal(service.revise_layout, body=body, user_uid=ADMIN, idempotency_key="k")
    assert error.detail_fields["constraint"] == "kit_does_not_match_cells" and not store.revisions


def test_a_cell_key_that_is_not_its_row_and_role_is_refused(events):
    service, store = make()
    body = request()
    body.cells[0].cell_key = "norms:main"
    assert refusal(service.revise_layout, body=body, user_uid=ADMIN, idempotency_key="k").detail_fields["constraint"] == "cell_key_mismatch"


def test_the_same_key_replays_and_another_payload_under_it_is_a_reuse(events):
    service, store = make()
    service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="k")
    again = service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="k")
    assert len(store.revisions) == 1 and again["current"]["revision_no"] == 1
    assert refusal(service.revise_layout, body=request("codex_only"), user_uid=ADMIN, idempotency_key="k").code is ErrorCode.IDEMPOTENCY_KEY_REUSE


def test_the_switch_needs_a_revision_and_the_database_source(events):
    service, store = make()
    error = refusal(service.set_layout_enabled, enabled=True, user_uid=ADMIN, idempotency_key="s1")
    assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "no_layout_revision"
    service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="r1")
    environment, env_store = make(provider_source="environment")
    environment.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="r1")
    error = refusal(environment.set_layout_enabled, enabled=True, user_uid=ADMIN, idempotency_key="s2")
    assert error.detail_fields["conflict_reason"] == "provider_source_not_database" and not env_store.events
    view = service.set_layout_enabled(enabled=True, user_uid=ADMIN, idempotency_key="s3")
    assert view["enabled"] is True and view["switch_journal"][0] == {"enabled": True, "set_at": store.events[0].set_at, "set_by": ADMIN}
    models.StageModelLayout.model_validate(view)


def test_switching_off_needs_nothing_and_a_repeat_of_the_state_in_force_records_nothing(events):
    service, store = make(provider_source="environment")
    # an environment stand cannot switch on, but off is always possible and records nothing when already off
    view = service.set_layout_enabled(enabled=False, user_uid=ADMIN, idempotency_key="s")
    assert view["enabled"] is False and not store.events
    on, on_store = make()
    on.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="r")
    on.set_layout_enabled(enabled=True, user_uid=ADMIN, idempotency_key="a")
    on.set_layout_enabled(enabled=True, user_uid=ADMIN, idempotency_key="b")
    assert [e.enabled for e in on_store.events] == [True]
    off = on.set_layout_enabled(enabled=False, user_uid=ADMIN, idempotency_key="c")
    assert off["enabled"] is False and [e.enabled for e in on_store.events] == [True, False]
    assert [e["payload"]["state"] for e in events if e["event_type"] == "stage_layout.switched"] == ["on", "off"]


def test_the_layout_names_the_cells_no_server_serves(events):
    service, store = make(availability=MemoryAvailability({
        "claude-sonnet-5-5": SUBSCRIPTION, "claude-opus-5-5": NOWHERE}))
    service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="k")
    assert service.get_layout()["unavailable_cell_keys"] == ["blocks:leg1"]


def test_the_catalogue_read_offers_only_what_the_layout_may_name():
    service, _ = make()
    catalogue = models.ModelCatalogue.model_validate(service.list_catalogue())
    for item in catalogue.items:
        assert "haiku" not in item.model_id and {e.value for e in item.efforts} <= {"low", "medium", "high"}
        if item.model_id == "claude-opus-5-5":
            assert {e.value for e in item.efforts} == {"medium", "high"}


def test_the_freezer_is_none_while_off_and_a_draft_while_on(events):
    service, store = make()
    session = service._sessions().__enter__()
    assert service.freezer(session) is None
    service.revise_layout(body=request(), user_uid=ADMIN, idempotency_key="r")
    assert service.freezer(session) is None
    service.set_layout_enabled(enabled=True, user_uid=ADMIN, idempotency_key="e")
    draft = service.freezer(session)
    assert draft.layout_revision_id == store.current_revision(None).layout_revision_id and draft.kit == "claude_only"


def test_a_layout_switched_on_under_another_source_or_with_no_revision_refuses_the_start():
    store = MemoryStore()
    store.append_switch(None, enabled=True, set_by=ADMIN)
    session = FakeSessions().session
    environment = StagePlanFreezer(store=store, availability=everything(), provider_source="environment")
    assert refusal(environment, session).detail_fields["conflict_reason"] == "provider_source_not_database"
    database = StagePlanFreezer(store=store, availability=everything(), provider_source="database")
    assert refusal(database, session).detail_fields["conflict_reason"] == "no_layout_revision"
    with_revision(store, layout.preset_cells("claude_only"))
    assert database(session) is not None
    nothing = StagePlanFreezer(store=store, availability=None, provider_source="database")
    assert refusal(nothing, session).code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_the_access_is_a_subscription_when_one_serves_the_model_else_an_api_key_and_a_missing_model_refuses():
    store = MemoryStore()
    store.append_switch(None, enabled=True, set_by=ADMIN)
    with_revision(store, layout.preset_cells("claude_only"))
    session = FakeSessions().session
    served = MemoryAvailability({"claude-sonnet-5-5": SUBSCRIPTION, "claude-opus-5-5": API_ONLY})
    draft = StagePlanFreezer(store=store, availability=served, provider_source="database")(session)
    plan = draft.freeze(layout.STAGE_ROWS)
    assert {cell.model_id: cell.access for cell in plan.cells} == {"claude-sonnet-5-5": "subscription", "claude-opus-5-5": "api"}
    assert plan.access == "mixed"
    # a model nothing serves: the start is refused, the cell is not dropped and nothing is substituted
    gone = StagePlanFreezer(store=store, availability=MemoryAvailability({"claude-sonnet-5-5": SUBSCRIPTION}),
                            provider_source="database")(session)
    error = refusal(gone.freeze, layout.STAGE_ROWS)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE and "blocks:leg1" in str(error)
    # ... but a run that never calls the blocks row is not refused for it
    assert gone.freeze(("text", "cross_check")).rows == ("text", "cross_check")


def test_a_revision_does_not_change_a_plan_already_frozen():
    store = MemoryStore()
    store.append_switch(None, enabled=True, set_by=ADMIN)
    with_revision(store, layout.preset_cells("claude_only"))
    session = FakeSessions().session
    freezer = StagePlanFreezer(store=store, availability=everything(), provider_source="database")
    frozen = freezer(session).freeze(layout.STAGE_ROWS)
    document, digest = frozen.to_json(), frozen.digest
    with_revision(store, layout.preset_cells("codex_only"), kit="codex_only")
    later = freezer(session).freeze(layout.STAGE_ROWS)
    assert later.digest != digest and later.kit == "codex_only"
    assert layout.parse_plan(document).digest == digest
