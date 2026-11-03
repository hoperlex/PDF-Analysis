"""`UI-PARITY-P0A`: the wire body of a decision record, the page's ``total``, and the declared parameters.

Pure functions and the generated document -- no database. What the SQL does is asserted on real PostgreSQL in
``tests/integration/dashboard/test_project_scope.py`` and ``tests/integration/api/test_decision_journal.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from auditmanager.api.app import create_documentation_app
from auditmanager.api.schemas import models
from auditmanager.api.schemas.decisions import DecisionRecordView, decision_record_body

_RECORDED = datetime(2026, 11, 4, 9, 30, tzinfo=timezone.utc)


def _view(**overrides: object) -> DecisionRecordView:
    fields: dict[str, object] = dict(
        decision_id="dec_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        finding_uid="fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        finding_observation_id="fobs_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        event_type="accept",
        author_label="Петрова А. И.",
        recorded_at=_RECORDED,
        project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        document_uid="doc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        project_name="Школа",
        document_name="АР-1",
        category="internal_contradiction",
        finding_text="Текст.",
        current_verdict="accepted",
        decision_event_count=1,
        verdict="accepted",
    )
    fields.update(overrides)
    return DecisionRecordView(**fields)  # type: ignore[arg-type]


def test_the_record_body_carries_where_the_decision_belongs() -> None:
    body = decision_record_body(_view())
    assert body["project_uid"] == "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert body["document_uid"] == "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert body["version_uid"] == "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert (body["project_name"], body["document_name"]) == ("Школа", "АР-1")


def test_an_unclassified_version_has_no_section_key_and_a_classified_one_has_its_code() -> None:
    assert "section" not in decision_record_body(_view()), "absent, never sent as null"
    assert decision_record_body(_view(section="AR"))["section"] == "AR"


def test_the_record_body_validates_against_the_closed_contract_model() -> None:
    """``DecisionRecord`` is closed (``additionalProperties: false``): a body key the model does not know is a defect."""
    record = models.DecisionRecord.model_validate(decision_record_body(_view(section="PS")))
    assert record.section is not None and record.document_name == "АР-1"
    models.DecisionRecord.model_validate(decision_record_body(_view()))
    with pytest.raises(ValueError):
        models.DecisionRecord.model_validate({**decision_record_body(_view()), "record_type": "finding"})


def test_a_page_without_total_is_not_a_decision_record_page() -> None:
    """``total`` is required: the knowledge base shows «N записей» from it, and a page that omitted it would show none."""
    page = {"items": [], "page": {"next_cursor": None}}
    with pytest.raises(ValueError):
        models.DecisionRecordPage.model_validate(page)
    assert models.DecisionRecordPage.model_validate({**page, "total": 0}).total == 0
    with pytest.raises(ValueError):
        models.DecisionRecordPage.model_validate({**page, "total": -1})


def test_both_operations_declare_the_optional_project_filter_as_a_project_identity() -> None:
    document = create_documentation_app().openapi()
    for path, operation_id in (("/dashboard", "getDashboardSummary"), ("/decisions", "listDecisions")):
        operation = document["paths"][path]["get"]
        assert operation["operationId"] == operation_id
        (parameter,) = [p for p in operation["parameters"] if p.get("name") == "project_uid"]
        assert parameter["in"] == "query" and parameter.get("required") is False
        assert parameter["schema"] == {"$ref": "#/components/schemas/ProjectUid"}


def test_the_dashboard_declares_the_answers_a_filter_can_produce() -> None:
    document = create_documentation_app().openapi()
    declared = set(document["paths"]["/dashboard"]["get"]["responses"])
    assert {"404", "422"} <= declared, "an unknown project is not_found and a malformed one is validation_failed"
    assert "404" not in document["paths"]["/decisions"]["get"]["responses"], (
        "listDecisions filters and does not address a parent: an unknown project is an empty page"
    )
