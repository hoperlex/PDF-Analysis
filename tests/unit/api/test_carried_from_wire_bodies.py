"""`UI-A-73` (contract 1.39.0): the wire bodies of a carried finding decision, and the frozen shapes that carry it.

Pure functions and the frozen document -- no database. What the SQL reads is asserted on real PostgreSQL in
``tests/integration/comparison/test_decision_carryover_db.py`` and ``tests/integration/api``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from auditmanager.api.schemas import models
from auditmanager.api.schemas.decisions import (
    DecisionCarriedFromView,
    DecisionEventView,
    DecisionRecordView,
    decision_event_body,
    decision_record_body,
)
from auditmanager.api.schemas.findings import (
    EvidenceView,
    FindingDetailView,
    FindingView,
    ObservationView,
    ProvenanceView,
    finding_body,
    finding_detail_body,
)

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "api" / "v1" / "openapi.json"
_AT = datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)
_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
_ORIGIN = DecisionCarriedFromView(
    decision_id=f"dec_{_ULID}", finding_uid=f"fnd_{_ULID}", version_uid=f"ver_{_ULID}", version_ordinal=2,
)
_ORIGIN_BODY = {
    "decision_id": f"dec_{_ULID}", "finding_uid": f"fnd_{_ULID}", "version_uid": f"ver_{_ULID}", "version_ordinal": 2,
}


def _schemas() -> dict[str, dict]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"]


def _event(**overrides: object) -> DecisionEventView:
    fields: dict[str, object] = dict(
        decision_id=f"dec_{_ULID}", finding_uid=f"fnd_{_ULID}", finding_observation_id=f"fobs_{_ULID}",
        event_type="accept", author_label="Петрова А. И.", recorded_at=_AT, verdict="accepted",
    )
    fields.update(overrides)
    return DecisionEventView(**fields)  # type: ignore[arg-type]


def _record(**overrides: object) -> DecisionRecordView:
    fields: dict[str, object] = dict(
        decision_id=f"dec_{_ULID}", finding_uid=f"fnd_{_ULID}", finding_observation_id=f"fobs_{_ULID}",
        event_type="accept", author_label="Петрова А. И.", recorded_at=_AT, project_uid=f"prj_{_ULID}",
        run_id=f"run_{_ULID}", document_uid=f"doc_{_ULID}", version_uid=f"ver_{_ULID}", project_name="Школа",
        document_name="АР-1", category="internal_contradiction", finding_text="Текст.", current_verdict="accepted",
        decision_event_count=1, verdict="accepted",
    )
    fields.update(overrides)
    return DecisionRecordView(**fields)  # type: ignore[arg-type]


def _finding(**overrides: object) -> FindingView:
    observation = ObservationView(
        finding_observation_id=f"fobs_{_ULID}", run_id=f"run_{_ULID}", category="internal_contradiction",
        finding_text="Конфликт", recommendation_text="Сверить", evidence=(EvidenceView(0, 1, "цитата", 0, 6),),
        provenance=ProvenanceView("text_analysis", f"ap_{_ULID}", f"pb_{_ULID}", "recorded"),
    )
    fields: dict[str, object] = dict(
        finding_uid=f"fnd_{_ULID}", project_uid=f"prj_{_ULID}", version_uid=f"ver_{_ULID}", run_id=f"run_{_ULID}",
        category="internal_contradiction", observation=observation, current_verdict="accepted",
    )
    fields.update(overrides)
    return FindingView(**fields)  # type: ignore[arg-type]


def test_an_event_made_directly_has_no_carried_from_key_and_a_carried_one_names_its_source() -> None:
    assert "carried_from" not in decision_event_body(_event()), "absent, never sent as null"
    body = decision_event_body(_event(carried_from=_ORIGIN))
    assert body["carried_from"] == _ORIGIN_BODY
    models.DecisionEvent.model_validate(body)  # closed: a key the model does not know would raise
    models.DecisionEvent.model_validate(decision_event_body(_event()))


def test_a_journal_record_carries_the_same_object() -> None:
    assert "carried_from" not in decision_record_body(_record())
    body = decision_record_body(_record(carried_from=_ORIGIN))
    assert body["carried_from"] == _ORIGIN_BODY
    assert models.DecisionRecord.model_validate(body).carried_from is not None
    assert models.DecisionRecord.model_validate(decision_record_body(_record())).carried_from is None


@pytest.mark.parametrize("carried", [None, _ORIGIN])
def test_a_finding_and_its_detail_name_where_the_current_verdict_came_from(carried: DecisionCarriedFromView | None) -> None:
    view = _finding(current_verdict_carried_from=carried)
    for body, model in (
        (finding_body(view), models.Finding),
        (finding_detail_body(FindingDetailView(finding=view, latest_comment=None, decision_event_count=1)), models.FindingDetail),
    ):
        if carried is None:
            assert "current_verdict_carried_from" not in body
        else:
            assert body["current_verdict_carried_from"] == _ORIGIN_BODY
        assert (model.model_validate(body).current_verdict_carried_from is None) == (carried is None)


def test_an_origin_that_is_not_the_four_identities_is_refused_by_the_closed_model() -> None:
    body = {**decision_event_body(_event(carried_from=_ORIGIN))}
    for broken in (
        {**_ORIGIN_BODY, "version_ordinal": 0},
        {**_ORIGIN_BODY, "decision_id": f"fnd_{_ULID}"},
        {**_ORIGIN_BODY, "extra": 1},
        {key: value for key, value in _ORIGIN_BODY.items() if key != "version_uid"},
    ):
        with pytest.raises(ValueError):
            models.DecisionEvent.model_validate({**body, "carried_from": broken})


def test_the_frozen_contract_declares_the_origin_and_where_it_is_optional() -> None:
    schemas = _schemas()
    origin = schemas["DecisionCarriedFrom"]
    assert origin["additionalProperties"] is False
    assert sorted(origin["required"]) == ["decision_id", "finding_uid", "version_ordinal", "version_uid"]
    assert origin["properties"]["version_ordinal"]["minimum"] == 1
    reference = {"$ref": "#/components/schemas/DecisionCarriedFrom"}
    for name, key in (
        ("DecisionEvent", "carried_from"), ("DecisionRecord", "carried_from"),
        ("Finding", "current_verdict_carried_from"), ("FindingDetail", "current_verdict_carried_from"),
    ):
        assert schemas[name]["properties"][key] == reference, name
        assert key not in schemas[name]["required"], f"{name}.{key} is optional: absent means made directly"
    # The optimisation side's twin on the accepted list (`D-335`) is required and nullable, as on `ProposalDecision`.
    accepted = schemas["AcceptedOptimisationProposal"]
    assert "carried_from" in accepted["required"]
    assert accepted["properties"]["carried_from"] == schemas["ProposalDecision"]["properties"]["carried_from"]


def test_the_record_still_restates_the_event_property_set_plus_the_context() -> None:
    schemas = _schemas()
    event = set(schemas["DecisionEvent"]["properties"])
    record = set(schemas["DecisionRecord"]["properties"])
    assert event < record and "carried_from" in event
    assert record - event == {
        "project_uid", "run_id", "document_uid", "version_uid", "project_name", "document_name", "section",
        "category", "finding_text", "current_verdict", "decision_event_count",
    }
