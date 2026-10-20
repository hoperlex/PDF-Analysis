"""`NORM-REFS-RUN-01`: ``getRunNormReferences`` is served, role-guarded and conforms to its schema.

Container-free. The route is mounted on a bare application over a stand-in port, so what is
measured is the transport: the operation and its role, the responses it declares (no ``422``:
a malformed run identity is ``404`` by design), and the wire bytes -- an answer that is not
``ready`` omits the list's properties, a ``ready`` one carries all of them, and no property
is ever ``null`` because the contract declares them optional and not nullable. Every body is
evaluated by the real Draft 2020-12 validator against the frozen ``RunNormReferences``
(``validate_against_schema``), including the body the shipped adapter's own mapping
(``_norm_references_view``) builds from the real read model. The composition (the run, its
text, its snapshot) is proved by ``tests/integration/runs/test_reference_norm_references.py``
and the PostgreSQL suite beside it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from starlette.testclient import TestClient

from auditmanager.api.app import create_documentation_app
from auditmanager.api.routers.runs import build_run_routes
from auditmanager.api.schemas import models
from auditmanager.api.security import OPERATION_ROLES
from auditmanager.bootstrap.adapters import _RunSavedText, _norm_references_view
from auditmanager.norms.references.read_model import build_reference_read_model
from auditmanager.norms.references.snapshot_catalogue import catalogue_from_rows
from auditmanager.norms.references.tokens import sql_designation_tokens
from auditmanager.runs.public import RunNormReferences, SavedRunPageText

RUN = "run_01M2545JSD15ETSNNV904X991K"
VERSION = "ver_01M2545JSD15ETSNNV904X991K"
SNAPSHOT = "ns_01M2545JSD15ETSNNV904X991K"
PATH = f"/runs/{RUN}/norm-references"

SLUGS = (
    "СП_54_13330_2022__Свод_правил__Здания_жилые",
    "СП_54_13330_2024__Свод_правил__Здания_жилые",
    "ГОСТ_21_101-2020__Система_проектной_документации",
    "МДС_12-24_2006__Устройство_обычных",
)
PAGES = {
    1: "По СП 54.13330.2022 и ГОСТ 21.101-2021, см. ГОСТ Р 99999-2020.",
    2: "",
    3: "Снова СП 54.13330.2022; СП 54.13330 не читается.",
}


def _catalogue():
    rows = [
        {
            "norm_document_id": f"ndoc_{number:026d}",
            "slug": slug,
            "designation_tokens": list(sql_designation_tokens(slug)),
        }
        for number, slug in enumerate(SLUGS, 1)
    ]
    return catalogue_from_rows(snapshot_id=SNAPSHOT, declared_count=len(rows), rows=rows)


def _ready_view() -> dict[str, Any]:
    model = build_reference_read_model(pages=PAGES, catalogue=_catalogue(), pinned_snapshot_id=SNAPSHOT)
    answer = RunNormReferences(
        run_id=RUN, version_uid=VERSION, state="ready", page_count=3,
        norms_snapshot_id=SNAPSHOT, text_layer_sha256="a" * 64, references=model,
    )
    return _norm_references_view(answer)


def _stopped_view(state: str, **changes: Any) -> dict[str, Any]:
    answer = RunNormReferences(
        run_id=RUN, version_uid=VERSION, state=state, page_count=3,
        norms_snapshot_id=changes.get("norms_snapshot_id"),
        text_layer_sha256=changes.get("text_layer_sha256"), references=None,
    )
    return _norm_references_view(answer)


class _Port:
    def __init__(self, view: dict[str, Any]) -> None:
        self.view = view
        self.asked: list[str] = []

    def get_run_norm_references(self, *, run_id: str) -> models.RunNormReferences:
        self.asked.append(run_id)
        return models.RunNormReferences.model_validate(self.view)


def _serve(view: dict[str, Any]) -> tuple[Any, _Port]:
    port = _Port(view)
    router = APIRouter()
    build_run_routes(router, port)  # type: ignore[arg-type]
    application = FastAPI()
    application.include_router(router)
    return TestClient(application).get(PATH), port


def _nulls(value: Any, where: str = "$") -> list[str]:
    if value is None:
        return [where]
    if isinstance(value, dict):
        return [hit for key, item in value.items() for hit in _nulls(item, f"{where}.{key}")]
    if isinstance(value, list):
        return [hit for index, item in enumerate(value) for hit in _nulls(item, f"{where}[{index}]")]
    return []


# --- the operation ---------------------------------------------------------------------------


def test_the_operation_is_served_for_any_one_role_and_declares_no_422() -> None:
    operation = create_documentation_app().openapi()["paths"]["/runs/{run_id}/norm-references"]["get"]

    assert operation["operationId"] == "getRunNormReferences"
    assert OPERATION_ROLES["getRunNormReferences"] == frozenset({"expert", "admin"})
    assert set(operation["responses"]) == {"200", "401", "403", "404", "500", "503"}
    assert OPERATION_ROLES["getRunNormReferences"] == OPERATION_ROLES["getRunStatus"]


# --- the wire ----------------------------------------------------------------------------------


def test_a_ready_answer_carries_every_property_and_validates(
    openapi_document: dict[str, Any], validate_against_schema
) -> None:
    response, port = _serve(_ready_view())

    assert (response.status_code, port.asked) == (200, [RUN])
    body = json.loads(response.content)
    assert _nulls(body) == []
    assert body["state"] == "ready"
    assert [(item["cited"], item["outcome"]) for item in body["items"]] == [
        ("СП 54.13330.2022", "newer_edition"),
        ("ГОСТ 21.101-2021", "older_edition_only"),
        ("ГОСТ Р 99999-2020", "not_in_corpus"),
        ("СП 54.13330", "not_recognised"),
    ]
    assert body["counts"] == {
        "in_corpus": 0, "newer_edition": 1, "older_edition_only": 1,
        "not_in_corpus": 1, "not_recognised": 1,
    }
    assert body["unread_pages"] == [2]
    assert [u["slug"] for u in body["unrecognised"]] == [SLUGS[3]]
    # An outcome that matches nothing omits the matched properties, rather than nulling them.
    unmatched = next(i for i in body["items"] if i["outcome"] == "not_in_corpus")
    assert not {"matched_norm_document_id", "matched_designation", "matched_title"} & set(unmatched)
    matched = next(i for i in body["items"] if i["outcome"] == "newer_edition")
    assert matched["matched_norm_document_id"] == f"ndoc_{2:026d}"
    assert matched["matched_designation"] == "СП 54.13330.2024"
    results = validate_against_schema(
        openapi_document, [{"name": "ready", "schema": "RunNormReferences", "payload": body}]
    )
    assert results["ready"]["valid"], results["ready"]["messages"]


@pytest.mark.parametrize(
    ("state", "changes"),
    [
        ("snapshot_not_pinned", {}),
        ("text_unavailable", {"norms_snapshot_id": SNAPSHOT}),
        ("too_many_citations", {"norms_snapshot_id": SNAPSHOT, "text_layer_sha256": "b" * 64}),
    ],
)
def test_a_state_that_stops_the_list_omits_the_list_and_validates(
    openapi_document: dict[str, Any], validate_against_schema, state, changes
) -> None:
    response, _ = _serve(_stopped_view(state, **changes))

    body = json.loads(response.content)
    assert response.status_code == 200 and body["state"] == state
    assert _nulls(body) == []
    assert not {"counts", "items", "unrecognised", "unread_pages", "occurrence_count",
                "snapshot_document_count"} & set(body)
    assert ("norms_snapshot_id" in body) is ("norms_snapshot_id" in changes)
    results = validate_against_schema(
        openapi_document, [{"name": state, "schema": "RunNormReferences", "payload": body}]
    )
    assert results[state]["valid"], results[state]["messages"]


def test_a_ready_answer_with_nothing_cited_is_an_empty_list_with_zero_counts(
    openapi_document: dict[str, Any], validate_against_schema
) -> None:
    model = build_reference_read_model(
        pages={1: "Общие данные."}, catalogue=_catalogue(), pinned_snapshot_id=SNAPSHOT
    )
    view = _norm_references_view(RunNormReferences(
        run_id=RUN, version_uid=VERSION, state="ready", page_count=1,
        norms_snapshot_id=SNAPSHOT, text_layer_sha256="c" * 64, references=model,
    ))

    response, _ = _serve(view)

    body = json.loads(response.content)
    assert body["items"] == [] and body["occurrence_count"] == 0
    assert body["counts"] == {code: 0 for code in body["counts"]} and len(body["counts"]) == 5
    results = validate_against_schema(
        openapi_document, [{"name": "empty", "schema": "RunNormReferences", "payload": body}]
    )
    assert results["empty"]["valid"], results["empty"]["messages"]


def test_the_frozen_schema_refuses_what_the_mapping_must_never_emit(
    openapi_document: dict[str, Any], validate_against_schema
) -> None:
    """The validator can fail here: a null where the property may only be absent."""
    body = json.loads(_serve(_ready_view())[0].content)
    nulled = json.loads(json.dumps(body))
    nulled["items"][2]["matched_title"] = None
    extra = json.loads(json.dumps(body))
    extra["items"][0]["severity"] = "major"
    sixth = json.loads(json.dumps(body))
    sixth["items"][0]["outcome"] = "ambiguous"

    results = validate_against_schema(openapi_document, [
        {"name": "null", "schema": "RunNormReferences", "payload": nulled},
        {"name": "extra", "schema": "RunNormReferences", "payload": extra},
        {"name": "sixth", "schema": "RunNormReferences", "payload": sixth},
    ])

    assert [results[name]["valid"] for name in ("null", "extra", "sixth")] == [False, False, False]


# --- the saved-text port ---------------------------------------------------------------------


class _ComparisonReader:
    """Stands for ``_AnalysisReader``: answers the comparison's shape or ``None``."""

    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str, int]] = []

    def saved_page_text(self, session: Any, *, run_id: str, version: Any) -> Any:
        self.asked.append((run_id, version.version_uid, version.page_count))
        return self.answer


def test_the_runs_saved_text_port_wraps_the_comparisons_reader_and_keeps_none() -> None:
    from types import SimpleNamespace

    reader = _RunSavedText(blob_store=object())
    reader._analyses = _ComparisonReader(  # type: ignore[assignment]
        SimpleNamespace(run_id=RUN, text_layer_sha256="a" * 64, pages={1: "СП 54.13330.2022", 2: ""})
    )

    saved = reader.saved_page_text(None, run_id=RUN, version_uid=VERSION, page_count=2)  # type: ignore[arg-type]

    assert saved == SavedRunPageText(RUN, "a" * 64, {1: "СП 54.13330.2022", 2: ""})
    assert reader._analyses.asked == [(RUN, VERSION, 2)]  # type: ignore[attr-defined]
    reader._analyses = _ComparisonReader(None)  # type: ignore[assignment]
    assert reader.saved_page_text(None, run_id=RUN, version_uid=VERSION, page_count=2) is None  # type: ignore[arg-type]
