"""`UIP-S12-01` (contract 1.56.0, rulings `Г12-B`, `Г9-B`): the execution status in the decision journal, and the filter by it.

No database. The route is mounted alone on a bare ``FastAPI`` application over a recording port, so what is under test is the edge:
how ``?execution_status=`` is read (one value, a comma-separated list, the parameter written twice, the empty string), what is refused,
what reaches the port, and the wire body of a record that carries a status and of one that does not. The SQL (the join, the filter, the
count) is asserted on real PostgreSQL in ``tests/integration/decisions/test_execution_status.py`` and over HTTP in
``tests/integration/api/test_decision_execution_status.py``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.routers.decisions import build_decision_routes
from auditmanager.api.routers.handlers import install_exception_handlers
from auditmanager.api.schemas import models
from auditmanager.api.schemas.decisions import DecisionRecordView, decision_record_body

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "contracts" / "api" / "v1" / "openapi.json"
_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
_AT = datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)
_SET_AT = datetime(2026, 11, 9, 10, 15, 30, tzinfo=timezone.utc)
STATUSES = ("taken_into_account", "amended", "declined", "agreed")


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


class _Port:
    """A decision port that records what the edge asked of it and answers one record."""

    def __init__(self, rows: list[DecisionRecordView]) -> None:
        self.rows = rows
        self.asked: list[dict[str, Any]] = []

    def decision_journal(self, *, category: Any, verdict: Any, project_uid: Any, execution_statuses: Any = None) -> list[DecisionRecordView]:
        self.asked.append({"category": category, "verdict": verdict, "project_uid": project_uid, "execution_statuses": execution_statuses})
        return list(self.rows)

    def proposal_decision_journal(self, *, project_uid: Any) -> list[Any]:
        return []


def _client(port: _Port) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)
    router = APIRouter()
    build_decision_routes(router, port, None)  # type: ignore[arg-type]
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------- the wire body


def test_a_record_of_a_finding_with_no_status_has_neither_key_and_is_what_it_was() -> None:
    body = decision_record_body(_record())
    assert "execution_status" not in body and "execution_status_at" not in body, "absent, never sent as null"
    assert models.DecisionRecord.model_validate(body).execution_status is None


def test_a_record_of_a_finding_with_a_status_carries_both_and_nothing_else_moves() -> None:
    bare = decision_record_body(_record())
    body = decision_record_body(_record(execution_status="amended", execution_status_at=_SET_AT))
    assert body["execution_status"] == "amended"
    assert body["execution_status_at"] == "2026-11-09T10:15:30Z"
    # The status is read beside the record: every other key is the record's own, to the byte.
    assert {key: value for key, value in body.items() if not key.startswith("execution_status")} == bare
    parsed = models.DecisionRecord.model_validate(body)  # closed: a key the model does not know would raise
    assert parsed.execution_status is models.FindingExecutionStatus.AMENDED and parsed.execution_status_at == _SET_AT


@pytest.mark.parametrize("status", STATUSES)
def test_every_status_of_the_frozen_vocabulary_is_carried(status: str) -> None:
    body = decision_record_body(_record(execution_status=status, execution_status_at=_SET_AT))
    assert models.DecisionRecord.model_validate(body).execution_status.value == status  # type: ignore[union-attr]


def test_a_status_outside_the_vocabulary_is_not_a_record() -> None:
    body = decision_record_body(_record(execution_status="done", execution_status_at=_SET_AT))
    with pytest.raises(ValueError):
        models.DecisionRecord.model_validate(body)


# ---------------------------------------------------------------------------- the filter, as the edge reads it


@pytest.mark.parametrize(("query", "handed"), [
    ("", None),
    ("?execution_status=", None),
    ("?execution_status=&execution_status=", None),
    ("?execution_status=agreed", ("agreed",)),
    ("?execution_status=agreed,amended", ("agreed", "amended")),
    ("?execution_status=amended,agreed", ("amended", "agreed")),
    ("?execution_status=agreed&execution_status=amended", ("agreed", "amended")),
    ("?execution_status=agreed,amended&execution_status=declined", ("agreed", "amended", "declined")),
    ("?execution_status=agreed,agreed&execution_status=agreed", ("agreed",)),
    ("?execution_status=taken_into_account,amended,declined,agreed", STATUSES),
], ids=["absent", "empty", "empty-twice", "one", "comma", "comma-reversed", "repeated", "mixed", "duplicates", "all-four"])
def test_the_edge_hands_the_port_each_status_once_or_nothing_at_all(query: str, handed: tuple[str, ...] | None) -> None:
    port = _Port([_record()])
    answer = _client(port).get(f"/decisions{query}")
    assert answer.status_code == 200, answer.text
    assert port.asked == [{"category": None, "verdict": None, "project_uid": None, "execution_statuses": handed}]


@pytest.mark.parametrize("value", [
    "done", "Agreed", "AGREED", " agreed", "agreed ", "agreed,", ",agreed", "agreed,,amended", "agreed;amended", "agreed|amended",
    "agreed,done", "accepted", "pending", "taken-into-account", ",",
], ids=repr)
def test_a_value_outside_the_vocabulary_is_refused_and_never_answered_with_an_empty_page(value: str) -> None:
    port = _Port([_record()])
    answer = _client(port).get("/decisions", params={"execution_status": value})
    assert answer.status_code == 422, answer.text
    body = json.loads(answer.content)
    assert body["error_code"] == "validation_failed"
    assert body["details"]["field"] == "execution_status" and body["details"]["constraint"] == "enum", body
    assert port.asked == [], "a refused request reached the port"


def test_one_bad_element_among_good_ones_refuses_the_whole_request_even_when_repeated() -> None:
    port = _Port([_record()])
    answer = _client(port).get("/decisions?execution_status=agreed&execution_status=done")
    assert answer.status_code == 422 and port.asked == []


def test_the_filter_composes_with_the_others_and_total_is_the_length_of_what_the_port_returned() -> None:
    rows = [_record(decision_id=f"dec_{_ULID[:-1]}{index}", execution_status="agreed", execution_status_at=_SET_AT) for index in range(3)]
    port = _Port(rows)
    answer = _client(port).get(
        f"/decisions?execution_status=agreed&verdict=accepted&category=internal_contradiction&project_uid=prj_{_ULID}&limit=1"
    )
    assert answer.status_code == 200, answer.text
    assert port.asked == [{
        "category": "internal_contradiction", "verdict": "accepted", "project_uid": f"prj_{_ULID}", "execution_statuses": ("agreed",),
    }]
    page = json.loads(answer.content)
    models.DecisionRecordPage.model_validate(page)
    assert len(page["items"]) == 1 and page["total"] == 3, "a group's count is `total`, read with limit=1"
    assert page["items"][0]["execution_status"] == "agreed"


def test_a_page_mixes_records_with_and_without_a_status_each_as_its_own_body() -> None:
    port = _Port([
        _record(decision_id=f"dec_{_ULID[:-1]}1", execution_status="declined", execution_status_at=_SET_AT),
        _record(decision_id=f"dec_{_ULID[:-1]}2"),
    ])
    page = json.loads(_client(port).get("/decisions").content)
    with_status, without = page["items"]
    assert with_status["execution_status"] == "declined" and "execution_status" in with_status
    assert "execution_status" not in without and "execution_status_at" not in without


def test_the_knowledge_base_entry_carries_the_status_of_its_finding_and_asks_for_no_filter() -> None:
    port = _Port([_record(execution_status="agreed", execution_status_at=_SET_AT)])
    answer = _client(port).get("/knowledge-base/entries")
    assert answer.status_code == 200, answer.text
    assert port.asked == [{"category": None, "verdict": None, "project_uid": None, "execution_statuses": None}]
    page = json.loads(answer.content)
    models.KnowledgeBaseEntryPage.model_validate(page)
    finding = page["items"][0]["finding"]
    assert (finding["execution_status"], finding["execution_status_at"]) == ("agreed", "2026-11-09T10:15:30Z")


# ---------------------------------------------------------------------------- the frozen document


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_the_contract_declares_the_filter_inline_optional_and_the_two_record_properties_optional() -> None:
    document = _contract()
    declared = {p["name"]: p for p in document["paths"]["/decisions"]["get"]["parameters"] if "name" in p}
    parameter = declared["execution_status"]
    assert parameter["in"] == "query" and parameter["required"] is False
    # One string: the generated transport sends one string per name, so the list rides in the value.
    assert parameter["schema"] == {"type": "string"}
    # The knowledge base's «Все» takes no such filter: it is not part of this operation set.
    assert "execution_status" not in {p.get("name") for p in document["paths"]["/knowledge-base/entries"]["get"]["parameters"]}

    schemas = document["components"]["schemas"]
    record = schemas["DecisionRecord"]
    assert record["properties"]["execution_status"] == {"$ref": "#/components/schemas/FindingExecutionStatus"}, (
        "the existing status schema is reused, not restated"
    )
    assert record["properties"]["execution_status_at"]["format"] == "date-time"
    assert not {"execution_status", "execution_status_at"} & set(record["required"])
    assert schemas["Finding"]["properties"]["execution_status"] == record["properties"]["execution_status"]
    # The proposal journal has its own decision and no execution status.
    assert not {"execution_status", "execution_status_at"} & set(schemas["ProposalDecisionRecord"]["properties"])
    assert schemas["FindingExecutionStatus"]["enum"] == list(STATUSES)
