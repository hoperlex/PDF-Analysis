"""`CMP-SEAL-C2`: the fifty operations of the version comparison AI, specifications, launch queue and reports (contract
`1.11.0`), served by the composition root.

Every one is a sealed stub. Written here as literals, not read back from the contract, and each rule shown failing:

* **the module flag** (ADR-0025 decision 23, ``A-12``): with ``AUDITMANAGER_COMPARISON_MODULES`` unset, ``none`` is
  the default and every operation, read or write, answers ``503 dependency_unavailable`` naming ``comparison_modules``
  before anything is read or written; with the versions module on it answers the stable class name of its lane
  (``comparison_ai_pairs``, ``comparison_ai_sheets``, ``comparison_specification``, ``comparison_launch_queue`` or
  ``comparison_reports``);
* **roles** (decision 16): reads are any one role, every one of the twenty-seven writes is the expert's act;
* **keys**: a write without its ``Idempotency-Key`` is refused before the stub, a read demands none;
* **the shape of the request** is judged before the stub: a consent that is not a digest and a boolean, a stray field,
  an MD file over 20 MiB, a bound outside its range.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, OPERATION_ROLES
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from tests.integration.composition.test_router_answers import DEPLOYMENT_SECRET, static_token
from tests.support.expected_facts import FACTS

PRJ = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOC = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SER = "cser_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TRN = "ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PAIR = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CPR = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
JOB = "cai_01ARZ3NDEKTSV4RRFFQ69G5FAV"
RPT = "crt_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ENTRY = "cle_01ARZ3NDEKTSV4RRFFQ69G5FAV"
KEY = "key-comparison-ai-stub"
DIGEST = "a" * 64
CONSENT = {"estimate_digest": DIGEST, "confirmed": True}
START = {"consent": CONSENT}
DOCUMENT = f"/projects/{PRJ}/documents/{DOC}"

#: operationId -> (method, path, json body, keyed, the dependency it names once the module is on). Written here.
REQUESTS: dict[str, tuple[str, str, Any, bool, str]] = {
    # AI check of the doubtful pairs
    "estimateComparisonAiPairCheck": ("GET", f"{DOCUMENT}/comparison-ai-pair-check/estimate", None, False, "comparison_ai_pairs"),
    "startComparisonAiPairCheck": ("POST", f"{DOCUMENT}/comparison-ai-pair-check", START, True, "comparison_ai_pairs"),
    "getComparisonAiPairCheck": ("GET", f"{DOCUMENT}/comparison-ai-pair-check", None, False, "comparison_ai_pairs"),
    "pauseComparisonAiPairCheck": ("POST", f"/comparison-ai-pair-checks/{JOB}/pause", None, True, "comparison_ai_pairs"),
    "resumeComparisonAiPairCheck": ("POST", f"/comparison-ai-pair-checks/{JOB}/resume", {}, True, "comparison_ai_pairs"),
    "cancelComparisonAiPairCheck": ("POST", f"/comparison-ai-pair-checks/{JOB}/cancellation", None, True, "comparison_ai_pairs"),
    "listComparisonAiPairHints": ("GET", f"{DOCUMENT}/comparison-ai-pair-hints", None, False, "comparison_ai_pairs"),
    # AI description of changes
    "estimateComparisonAiSheetChanges": ("GET", f"/comparison-series/{SER}/ai-sheet-changes/estimate", None, False, "comparison_ai_sheets"),
    "startComparisonAiSheetChanges": ("POST", f"/comparison-series/{SER}/ai-sheet-changes", START, True, "comparison_ai_sheets"),
    "getComparisonAiSheetChanges": ("GET", f"/comparison-series/{SER}/ai-sheet-changes", None, False, "comparison_ai_sheets"),
    "pauseComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/pause", None, True, "comparison_ai_sheets"),
    "resumeComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/resume", {}, True, "comparison_ai_sheets"),
    "cancelComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/cancellation", None, True, "comparison_ai_sheets"),
    "finishComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/finish", None, True, "comparison_ai_sheets"),
    "dequeueComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/dequeue", None, True, "comparison_ai_sheets"),
    "retryComparisonAiSheetChanges": ("POST", f"/comparison-ai-sheet-jobs/{JOB}/retry", START, True, "comparison_ai_sheets"),
    "getComparisonSheetDescription": ("GET", f"/comparison-sheet-pairs/{PAIR}/description", None, False, "comparison_ai_sheets"),
    "listComparisonSheetDescriptionHistory": ("GET", f"/comparison-sheet-pairs/{PAIR}/description-history", None, False, "comparison_ai_sheets"),
    "estimateComparisonSheetDescription": ("GET", f"/comparison-sheet-pairs/{PAIR}/description/estimate", None, False, "comparison_ai_sheets"),
    "startComparisonSheetDescription": ("POST", f"/comparison-sheet-pairs/{PAIR}/description", START, True, "comparison_ai_sheets"),
    "streamComparisonSheetDescriptionMd": ("GET", f"/comparison-sheet-pairs/{PAIR}/description/md", None, False, "comparison_ai_sheets"),
    "listComparisonReviewSheets": ("GET", f"/comparison-transitions/{TRN}/review-sheets", None, False, "comparison_ai_sheets"),
    # specifications
    "getVersionPageSpecPositions": ("GET", f"/page-profiles/{CPR}/spec-positions", None, False, "comparison_specification"),
    "getComparisonSheetPairSpecPositions": ("GET", f"/comparison-sheet-pairs/{PAIR}/spec-positions", None, False, "comparison_specification"),
    "listComparisonSpecifications": ("GET", f"/comparison-series/{SER}/specifications", None, False, "comparison_specification"),
    "getComparisonSpecification": ("GET", f"/comparison-transitions/{TRN}/specification", None, False, "comparison_specification"),
    "listComparisonSpecificationChanges": ("GET", f"/comparison-transitions/{TRN}/specification/changes", None, False, "comparison_specification"),
    "estimateComparisonSpecification": ("GET", f"/comparison-transitions/{TRN}/specification/estimate", None, False, "comparison_specification"),
    "startComparisonSpecification": ("POST", f"/comparison-transitions/{TRN}/specification", START, True, "comparison_specification"),
    "cancelComparisonSpecification": ("POST", f"/comparison-ai-spec-jobs/{JOB}/cancellation", None, True, "comparison_specification"),
    # the launch queue and the installation's AI queue
    "getComparisonLaunchQueue": ("GET", f"/projects/{PRJ}/comparison-launch-queue", None, False, "comparison_launch_queue"),
    "enqueueComparisonLaunch": ("POST", f"/projects/{PRJ}/comparison-launch-queue/entries",
                                {"items": [{"document_uid": DOC, "step": "series"}]}, True, "comparison_launch_queue"),
    "pauseComparisonLaunchQueue": ("POST", f"/projects/{PRJ}/comparison-launch-queue/pause", None, True, "comparison_launch_queue"),
    "resumeComparisonLaunchQueue": ("POST", f"/projects/{PRJ}/comparison-launch-queue/resume", None, True, "comparison_launch_queue"),
    "clearComparisonLaunchQueue": ("POST", f"/projects/{PRJ}/comparison-launch-queue/clear", None, True, "comparison_launch_queue"),
    "removeComparisonLaunchEntry": ("POST", f"/comparison-launch-entries/{ENTRY}/removal", None, True, "comparison_launch_queue"),
    "getComparisonAiQueue": ("GET", "/execution/comparison-ai-queue", None, False, "comparison_launch_queue"),
    # the MD summary and the reports
    "streamComparisonSeriesSummary": ("GET", f"/comparison-series/{SER}/summary-md", None, False, "comparison_reports"),
    "createComparisonReport": ("POST", f"/comparison-series/{SER}/reports", {}, True, "comparison_reports"),
    "uploadComparisonReportSource": ("POST", f"/comparison-series/{SER}/reports/upload", b"## 1. A \xe2\x86\x92 B\n", True, "comparison_reports"),
    "listComparisonReports": ("GET", f"/comparison-series/{SER}/reports", None, False, "comparison_reports"),
    "getComparisonReport": ("GET", f"/comparison-reports/{RPT}", None, False, "comparison_reports"),
    "startComparisonReport": ("POST", f"/comparison-reports/{RPT}/start", START, True, "comparison_reports"),
    "cancelComparisonReport": ("POST", f"/comparison-reports/{RPT}/cancellation", None, True, "comparison_reports"),
    "continueComparisonReport": ("POST", f"/comparison-reports/{RPT}/continuation", {}, True, "comparison_reports"),
    "rebuildComparisonReportPdf": ("POST", f"/comparison-reports/{RPT}/pdf-rebuild", None, True, "comparison_reports"),
    "deleteComparisonReport": ("POST", f"/comparison-reports/{RPT}/deletion", None, True, "comparison_reports"),
    "prepareComparisonClientReport": ("POST", f"/comparison-reports/{RPT}/client-report", {}, True, "comparison_reports"),
    "streamComparisonReportPdf": ("GET", f"/comparison-reports/{RPT}/pdf", None, False, "comparison_reports"),
    "streamComparisonReportSourceMd": ("GET", f"/comparison-reports/{RPT}/source-md", None, False, "comparison_reports"),
}
EXPERT_WRITES = {name for name, row in REQUESTS.items() if row[3]}
DEPENDENCIES = {row[4] for row in REQUESTS.values()}
#: Lanes that serve one of them remove it from the list of stubs by adding it here; the role, key and shape tests still
#: judge it. Empty at the seal.
WIRED: frozenset[str] = frozenset({
    # `CMP-VC-AISHEET-01`: the fifteen operations of `ComparisonAiSheetAdapter`.
    "estimateComparisonAiSheetChanges", "getComparisonAiSheetChanges", "startComparisonAiSheetChanges",
    "pauseComparisonAiSheetChanges", "resumeComparisonAiSheetChanges", "cancelComparisonAiSheetChanges",
    "finishComparisonAiSheetChanges", "dequeueComparisonAiSheetChanges", "retryComparisonAiSheetChanges",
    "getComparisonSheetDescription", "startComparisonSheetDescription", "listComparisonSheetDescriptionHistory",
    "estimateComparisonSheetDescription", "streamComparisonSheetDescriptionMd", "listComparisonReviewSheets",
})
STUBS = sorted(set(REQUESTS) - WIRED)
LANES = {
    "comparison_ai_pairs": "CMP-VC-AIPAIR-01", "comparison_ai_sheets": "CMP-VC-AISHEET-01",
    "comparison_specification": "CMP-VC-SPEC-01", "comparison_launch_queue": "CMP-VC-QUEUE-01",
    "comparison_reports": "CMP-VC-REPORT-01",
}


def _client(modules: str | None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
    if modules is not None:
        environ[COMPARISON_MODULES_ENV] = modules
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def off() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return _client(None)


@pytest.fixture(scope="module")
def on() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return _client("versions")


def _call(client: TestClient, name: str, *, token: str | None, key: str | None = KEY) -> Any:
    method, path, body, keyed, _dependency = REQUESTS[name]
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if keyed and key is not None:
        headers["Idempotency-Key"] = key
    kwargs: dict[str, Any] = {}
    if isinstance(body, bytes):
        headers["content-type"] = "text/markdown"
        kwargs["content"] = body
    elif body is not None:
        headers["content-type"] = "application/json"
        kwargs["content"] = json.dumps(body).encode()
    return client.request(method, path, headers=headers, **kwargs)


def test_the_requests_cover_exactly_the_fifty_operations_the_contract_added() -> None:
    document = json.load(open("contracts/api/v1/openapi.json", encoding="utf-8"))
    paths = {(m.upper(), p): op["operationId"] for p, item in document["paths"].items()
             for m, op in item.items() if m in ("get", "post", "put", "patch", "delete")}
    templated = {name: (method, re_path(path)) for name, (method, path, *_rest) in REQUESTS.items()}
    assert len(REQUESTS) == 50 and len(EXPERT_WRITES) == 27
    for name, (method, template) in templated.items():
        assert paths.get((method, template)) == name, (name, method, template)
    assert {triple[2] for triple in FACTS.operations} >= set(REQUESTS)


def re_path(path: str) -> str:
    """The contract's template of a path written with the identities above."""
    for value, parameter in ((PRJ, "project_uid"), (DOC, "document_uid"), (SER, "comparison_series_id"),
                             (TRN, "comparison_transition_id"), (PAIR, "comparison_sheet_pair_id"),
                             (CPR, "comparison_page_profile_id"), (JOB, "comparison_ai_job_id"),
                             (RPT, "comparison_report_id"), (ENTRY, "comparison_launch_entry_id")):
        path = path.replace(value, "{" + parameter + "}")
    return path


@pytest.mark.parametrize("name", STUBS)
def test_every_operation_answers_its_lane_class_when_the_versions_module_is_on(on: TestClient, name: str) -> None:
    response = _call(on, name, token=static_token())
    body = response.json()
    assert response.status_code == 503, (name, response.status_code, body)
    assert body["error_code"] == "dependency_unavailable"
    assert body["details"]["dependency"] == REQUESTS[name][4], body
    assert body["retryable"] is True


@pytest.mark.parametrize("name", STUBS)
def test_every_operation_refuses_naming_the_module_while_the_versions_module_is_off(off: TestClient, name: str) -> None:
    """ADR-0025 decision 23 and ``A-12``: nothing is read, written or sent to a model while the module is off."""
    response = _call(off, name, token=static_token())
    body = response.json()
    assert response.status_code == 503, (name, response.status_code, body)
    assert body["error_code"] == "dependency_unavailable"
    assert body["details"]["dependency"] == "comparison_modules", (name, body)


@pytest.mark.parametrize("value", ["none", "versions,stages"])
def test_the_module_value_decides_which_class_a_stub_names(value: str) -> None:
    """``none`` is off; ``versions,stages`` serves the versions module too."""
    client = _client(value)
    response = _call(client, "startComparisonAiPairCheck", token=static_token())
    expected = "comparison_modules" if value == "none" else "comparison_ai_pairs"
    assert response.status_code == 503 and response.json()["details"]["dependency"] == expected, response.text


def test_the_dependencies_are_the_five_class_names_of_the_lanes() -> None:
    assert DEPENDENCIES == set(LANES)


@pytest.mark.parametrize("name", sorted(REQUESTS))
def test_an_unauthenticated_request_is_refused_before_the_stub(off: TestClient, name: str) -> None:
    response = _call(off, name, token=None)
    assert response.status_code == 401 and response.json()["error_code"] == "authentication_required", name


@pytest.mark.parametrize("name", sorted(EXPERT_WRITES))
def test_a_write_without_its_idempotency_key_is_refused_not_stubbed(on: TestClient, name: str) -> None:
    response = _call(on, name, token=static_token(), key=None)
    assert response.status_code == 422 and response.json()["error_code"] == "validation_failed", name


def test_the_roles_are_the_ones_the_adr_gives() -> None:
    """Reads are any one role; every write is the expert's act (decision 16). A literal, not a read-back."""
    for name in REQUESTS:
        expected = frozenset({"expert"}) if name in EXPERT_WRITES else frozenset({"expert", "admin"})
        assert OPERATION_ROLES[name] == expected, name


def test_that_check_fails_when_a_write_is_opened_to_an_administrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: an administrator without the expert role would start an AI job."""
    from types import MappingProxyType
    from auditmanager.api import security
    widened = MappingProxyType({**OPERATION_ROLES, "startComparisonAiPairCheck": frozenset({"expert", "admin"})})
    monkeypatch.setattr(security, "OPERATION_ROLES", widened)
    with pytest.raises(AssertionError):
        for name in REQUESTS:
            expected = frozenset({"expert"}) if name in EXPERT_WRITES else frozenset({"expert", "admin"})
            assert security.OPERATION_ROLES[name] == expected, name


def test_that_check_fails_when_the_module_flag_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: a stub that skips the module flag would answer its lane class while the module is off."""
    from auditmanager.bootstrap import adapters

    monkeypatch.setattr(adapters._VersionsModuleGate, "_require_versions_module", lambda self: None)
    client = _client(None)
    response = _call(client, "startComparisonAiPairCheck", token=static_token())
    with pytest.raises(AssertionError):
        assert response.json()["details"]["dependency"] == "comparison_modules"


# -- the shape of a request is judged before the stub ------------------------------------------------


def _post(client: TestClient, path: str, body: Any, *, media: str = "application/json") -> Any:
    headers = {"Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY, "content-type": media}
    content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return client.post(path, content=content, headers=headers)


def test_a_consent_that_is_not_a_digest_and_a_boolean_is_refused_before_the_stub(on: TestClient) -> None:
    start = f"{DOCUMENT}/comparison-ai-pair-check"
    for bad in ({}, {"consent": {}}, {"consent": {"estimate_digest": DIGEST}}, {"consent": {"confirmed": True}},
                {"consent": {"estimate_digest": "A" * 64, "confirmed": True}},
                {"consent": {"estimate_digest": "a" * 63, "confirmed": True}},
                {"consent": {"estimate_digest": DIGEST, "confirmed": "yes please"}},
                {"consent": CONSENT, "ceiling_usd": 9999}, {"consent": CONSENT, "surprise": True}):
        response = _post(on, start, bad)
        assert response.status_code == 422, (str(bad)[:80], response.status_code, response.text)
    # a consent with `confirmed` false is well formed: the lane refuses it with `comparison_consent_required`
    assert _post(on, start, {"consent": {**CONSENT, "confirmed": False}}).status_code == 503


def test_the_sheet_start_takes_restart_and_the_retry_takes_a_consent(on: TestClient) -> None:
    start = f"/comparison-series/{SER}/ai-sheet-changes"
    assert _post(on, start, {"consent": CONSENT, "restart": True}).status_code == 503
    assert _post(on, start, {"consent": CONSENT, "restart": "later"}).status_code == 422
    assert _post(on, f"/comparison-ai-sheet-jobs/{JOB}/retry", {}).status_code == 422
    assert _post(on, f"/comparison-ai-sheet-jobs/{JOB}/resume", {"consent": {"confirmed": True}}).status_code == 422
    assert _post(on, f"/comparison-ai-sheet-jobs/{JOB}/resume", {"consent": CONSENT}).status_code == 503


def test_the_queue_request_is_bounded_and_names_a_queueable_step(on: TestClient) -> None:
    path = f"/projects/{PRJ}/comparison-launch-queue/entries"
    item = {"document_uid": DOC, "step": "series"}
    assert _post(on, path, {"items": [item]}).status_code == 503
    assert _post(on, path, {"items": [{**item, "step": "ai_changes", "consent": CONSENT}], "restart": True}).status_code == 503
    for bad in ({}, {"items": []}, {"items": [item] * 201}, {"items": [{**item, "step": "sideways"}]},
                {"items": [{"step": "series"}]}, {"items": [{**item, "document_uid": "x"}]},
                {"items": [item], "restart": "maybe"}):
        assert _post(on, path, bad).status_code == 422, str(bad)[:80]


def test_a_report_upload_is_bounded_and_takes_a_kind(on: TestClient) -> None:
    path = f"/comparison-series/{SER}/reports/upload"
    md = "## 1. A → B\n".encode()
    assert _post(on, path, md, media="text/markdown").status_code == 503
    assert _post(on, path + "?kind=analytic&reuse=true&source_name=summary.md", md, media="text/markdown").status_code == 503
    assert _post(on, path + "?kind=poster", md, media="text/markdown").status_code == 422
    assert _post(on, path + "?source_name=", md, media="text/markdown").status_code == 422
    assert _post(on, path, b"x" * (20 * 1024 * 1024 + 1), media="text/markdown").status_code in (413, 422)


def test_a_list_or_query_outside_its_bounds_is_refused_before_the_stub(on: TestClient) -> None:
    headers = {"Authorization": f"Bearer {static_token()}"}
    for path in (f"{DOCUMENT}/comparison-ai-pair-hints", f"/comparison-sheet-pairs/{PAIR}/description-history",
                 f"/comparison-transitions/{TRN}/review-sheets", f"/comparison-series/{SER}/specifications",
                 f"/comparison-transitions/{TRN}/specification/changes", f"/comparison-series/{SER}/reports"):
        assert on.get(f"{path}?limit=0", headers=headers).status_code == 422, path
        assert on.get(f"{path}?limit=201", headers=headers).status_code == 422, path
        assert on.get(path, headers=headers).status_code == 503, path
    changes = f"/comparison-transitions/{TRN}/specification/changes"
    assert on.get(f"{changes}?kind=sideways", headers=headers).status_code == 422
    assert on.get(f"{changes}?kind=added", headers=headers).status_code == 503
    estimate = f"/comparison-series/{SER}/ai-sheet-changes/estimate"
    assert on.get(f"{estimate}?only_failed=maybe", headers=headers).status_code == 422
    assert on.get(f"{estimate}?only_failed=true", headers=headers).status_code == 503


def test_an_identity_that_is_not_the_pattern_is_not_found_before_the_stub(on: TestClient) -> None:
    """A path identity of the wrong shape or of another entity names nothing: ``404`` and never the stub's ``503``."""
    headers = {"Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY}
    for response in (
        on.post("/comparison-ai-pair-checks/cai_x/pause", headers=headers),
        on.post(f"/comparison-ai-pair-checks/{RPT}/pause", headers=headers),
        on.get("/comparison-reports/crt_x", headers=headers),
        on.post(f"/comparison-launch-entries/{JOB}/removal", headers=headers),
    ):
        assert response.status_code == 404 and response.json()["error_code"] == "not_found", response.text


def test_the_work_kinds_of_the_executor_routes_include_the_four_comparison_kinds() -> None:
    """ADR-0025 decision 17: the model, the contract enum and the database constraint agree."""
    from auditmanager.api.schemas import models
    from auditmanager.executors.model import SERVES, WORK_KINDS

    kinds = ("comparison_pair_check", "comparison_sheet_changes", "comparison_spec", "comparison_report")
    assert WORK_KINDS == ("text_analysis", *kinds)
    assert {kind.value for kind in models.ExecutorWorkKind} == set(WORK_KINDS)
    assert set(SERVES) == set(WORK_KINDS) and all(SERVES[kind] for kind in WORK_KINDS)
    assert "comparison_stage_review" not in WORK_KINDS  # SEAL-C4
