"""Real response bodies validate against the frozen schemas, under Draft 2020-12.

The bodies here come out of the routers, driven against real PostgreSQL and real
object storage. They are not hand-written examples: an example is a statement about
what the author believed the router produced, and this suite exists to check that
belief.

The validator is the pinned ``jsonschema`` in the **governance** environment, driven
through ``tests/contract/api_v1/schema_validation_check.py``. The runtime lock carries
no validator and adding a root dependency is a single-owner task, not a lane decision.
Re-implementing 2020-12 evaluation here would be asserting the belief under test --
which is exactly how the ``FindingDetail`` ``allOf`` defect survived until a real
validator was pointed at it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy.orm import Session

from auditmanager.api.routers import Router, dispatch
from auditmanager.api.routers.http import Request

from .conftest import PublishedRun


def _body(router: Router, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = dispatch(router, Request.build(method, path, **kwargs))
    assert response.status < 300, (response.status, response.body)
    return json.loads(response.body)


def _valid(results: dict[str, Any], name: str) -> None:
    result = results[name]
    assert result["valid"], f"{name} does not validate: {result['messages']}"


# ---------------------------------------------------------------------------
# The three the gate names
# ---------------------------------------------------------------------------


def test_a_real_finding_detail_body_validates(
    router: Router,
    published_run: PublishedRun,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    body = _body(router, "GET", f"/findings/{published_run.finding_uid}")

    results = validate_against_schema(
        openapi_document, [{"name": "detail", "schema": "FindingDetail", "payload": body}]
    )
    _valid(results, "detail")

    # `FindingDetail` is `Finding` plus exactly two properties; the reduced body must
    # still satisfy the closed `Finding`.
    reduced = {
        key: value
        for key, value in body.items()
        if key not in {"latest_comment", "decision_event_count"}
    }
    results = validate_against_schema(
        openapi_document, [{"name": "finding", "schema": "Finding", "payload": reduced}]
    )
    _valid(results, "finding")


def test_a_real_finding_page_validates(
    router: Router,
    published_run: PublishedRun,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    body = _body(router, "GET", f"/runs/{published_run.run_id}/findings")
    assert body["items"], "the fixture published no findings, so this proves nothing"

    results = validate_against_schema(
        openapi_document, [{"name": "page", "schema": "FindingPage", "payload": body}]
    )
    _valid(results, "page")


def test_a_real_run_status_body_validates(
    router: Router,
    published_run: PublishedRun,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    body = _body(router, "GET", f"/runs/{published_run.run_id}")

    results = validate_against_schema(
        openapi_document, [{"name": "status", "schema": "RunStatus", "payload": body}]
    )
    _valid(results, "status")
    assert body["state"] != "succeeded", "there is no `succeeded` run state"


def test_a_real_decision_body_validates(
    router: Router,
    published_run: PublishedRun,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    appended = _body(
        router,
        "POST",
        f"/findings/{published_run.finding_uid}/decisions",
        headers={"Idempotency-Key": "decision-0001", "Content-Type": "application/json"},
        body=json.dumps(
            {
                "event_type": "accept",
                "finding_observation_id": published_run.finding_observation_id,
            }
        ).encode("utf-8"),
    )
    history = _body(router, "GET", f"/findings/{published_run.finding_uid}/decisions")

    results = validate_against_schema(
        openapi_document,
        [
            {
                "name": "appended",
                "schema": "AppendDecisionResponse",
                "payload": appended,
            },
            {"name": "history", "schema": "DecisionEventPage", "payload": history},
            {"name": "event", "schema": "DecisionEvent", "payload": appended["event"]},
        ],
    )
    _valid(results, "appended")
    _valid(results, "history")
    _valid(results, "event")

    assert appended["current_verdict"] == "accepted"
    assert history["items"], "the appended event is not in the history"


# ---------------------------------------------------------------------------
# The rest of the surface, for completeness
# ---------------------------------------------------------------------------


def test_a_real_project_and_page_validate(
    router: Router, openapi_document: dict[str, Any], validate_against_schema
) -> None:
    created = _body(
        router,
        "POST",
        "/projects",
        headers={"Idempotency-Key": "project-0001", "Content-Type": "application/json"},
        body=json.dumps({"name": "Проект АР"}).encode("utf-8"),
    )
    page = _body(router, "GET", "/projects")

    results = validate_against_schema(
        openapi_document,
        [
            {"name": "project", "schema": "Project", "payload": created},
            {"name": "page", "schema": "ProjectPage", "payload": page},
        ],
    )
    _valid(results, "project")
    _valid(results, "page")


def test_a_real_document_version_validates(
    router: Router,
    corpus_pdf: bytes,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    """The whole ingest path, against real PostgreSQL and a real private bucket."""
    project = _body(
        router,
        "POST",
        "/projects",
        headers={"Idempotency-Key": "project-0002", "Content-Type": "application/json"},
        body=json.dumps({"name": "Проект"}).encode("utf-8"),
    )
    boundary = "----b6"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="ar_baseline.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + corpus_pdf + (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="display_title"\r\n\r\n'
        "Годовой отчёт\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    version = _body(
        router,
        "POST",
        f"/projects/{project['project_uid']}/documents",
        headers={
            "Idempotency-Key": "upload-0001",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        body=body,
    )
    fetched = _body(router, "GET", f"/versions/{version['version_uid']}")

    results = validate_against_schema(
        openapi_document,
        [
            {"name": "uploaded", "schema": "DocumentVersion", "payload": version},
            {"name": "fetched", "schema": "DocumentVersion", "payload": fetched},
        ],
    )
    _valid(results, "uploaded")
    _valid(results, "fetched")
    assert fetched == version


def test_every_error_body_validates_as_the_envelope(
    router: Router, openapi_document: dict[str, Any], validate_against_schema
) -> None:
    """Every non-2xx body on this surface is the frozen ``ErrorEnvelope``.

    Four different failure classes, each reached through the router rather than
    constructed: an unknown path, a missing required header, a malformed body and a
    rejected query parameter.
    """
    cases = {
        "not_found": Request.build("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
        "missing_key": Request.build(
            "POST",
            "/projects",
            headers={"Content-Type": "application/json"},
            body=b'{"name": "x"}',
        ),
        "bad_json": Request.build(
            "POST",
            "/projects",
            headers={"Idempotency-Key": "k1", "Content-Type": "application/json"},
            body=b"{not json",
        ),
        "bad_limit": Request.build("GET", "/projects?limit=0"),
    }
    payloads = []
    for name, request in cases.items():
        response = dispatch(router, request)
        assert response.status >= 400, f"{name} answered {response.status}"
        payloads.append(
            {
                "name": name,
                "schema": "ErrorEnvelope",
                "payload": json.loads(response.body),
            }
        )

    results = validate_against_schema(openapi_document, payloads)
    for name in cases:
        _valid(results, name)


def test_the_validator_can_fail(
    router: Router,
    published_run: PublishedRun,
    openapi_document: dict[str, Any],
    validate_against_schema,
) -> None:
    """The schema check is capable of rejecting something.

    Without this, every assertion above would also pass against a validator that
    returned ``valid: true`` unconditionally -- and a green suite that cannot go red is
    the failure mode this programme has caught five times.
    """
    body = _body(router, "GET", f"/findings/{published_run.finding_uid}")

    smuggled = dict(body, smuggled_field="x")
    dropped = {k: v for k, v in body.items() if k != "finding_uid"}
    wrong_shape = dict(body, current_verdict="approved")

    results = validate_against_schema(
        openapi_document,
        [
            {"name": "smuggled", "schema": "FindingDetail", "payload": smuggled},
            {"name": "dropped", "schema": "FindingDetail", "payload": dropped},
            {"name": "enum", "schema": "FindingDetail", "payload": wrong_shape},
        ],
    )
    assert not results["smuggled"]["valid"], "the closed schema accepted an extra property"
    assert not results["dropped"]["valid"], "the schema accepted a missing required property"
    assert not results["enum"]["valid"], "the schema accepted a value outside the enum"
