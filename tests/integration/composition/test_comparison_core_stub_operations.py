"""`CMP-SEAL-C1`: the eighteen operations of the version comparison core (contract `1.10.0`), served by the
composition root.

Every one is a sealed stub: it answers ``503 dependency_unavailable`` (``details.dependency`` one of four stable
class names) to an account that holds the role it needs, and nothing is read or written. The role map is compared with
a literal written here, and the mutation tests below break the thing under test and watch the assertion go red. The
three ``0035`` operations answer ``503`` with the dependency ``comparison_versions_module`` while the module
«Сравнение версий» is on (ADR-0025 decision 13), and work as before while it is off.
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
VER = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
CMX = "cmx_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SER = "cser_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TRN = "ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PAIR = "ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV"
KEY = "key-comparison-core-stub"
BASE = {"matrix_id": CMX, "edit_no": 0}
PAGE = {"version_uid": VER, "page_number": 1}
OTHER_VER = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAW"
DOCUMENT = f"/projects/{PRJ}/documents/{DOC}"

#: operationId -> (method, path, json body, keyed). Written here, not read from the contract.
REQUESTS: dict[str, tuple[str, str, Any, bool]] = {
    "getComparisonMatrix": ("GET", f"{DOCUMENT}/comparison-matrix", None, False),
    "prepareComparisonMatrix": ("POST", f"{DOCUMENT}/comparison-matrix/preparation", None, True),
    "listComparisonMatrixEdits": ("GET", f"{DOCUMENT}/comparison-matrix/edits", None, False),
    "applyComparisonMatrixEdits": ("POST", f"{DOCUMENT}/comparison-matrix/edits",
                                   {"base_revision": BASE, "edits": [
                                       {"kind": "link", "page": PAGE, "other_page": {**PAGE, "version_uid": OTHER_VER}}]}, True),
    "undoComparisonMatrixEdit": ("POST", f"{DOCUMENT}/comparison-matrix/edits/undo", {"base_revision": BASE}, True),
    "listComparisonAiLinks": ("GET", f"{DOCUMENT}/comparison-ai-links", None, False),
    "startComparisonSeries": ("POST", f"{DOCUMENT}/comparison-series", {}, True),
    "listComparisonSeries": ("GET", f"{DOCUMENT}/comparison-series", None, False),
    "getComparisonSeries": ("GET", f"/comparison-series/{SER}", None, False),
    "pauseComparisonSeries": ("POST", f"/comparison-series/{SER}/pause", None, True),
    "resumeComparisonSeries": ("POST", f"/comparison-series/{SER}/resume", None, True),
    "cancelComparisonSeries": ("POST", f"/comparison-series/{SER}/cancellation", None, True),
    "finishComparisonSeries": ("POST", f"/comparison-series/{SER}/finish", None, True),
    "listComparisonSheetPairs": ("GET", f"/comparison-transitions/{TRN}/sheet-pairs", None, False),
    "getComparisonSheetPair": ("GET", f"/comparison-sheet-pairs/{PAIR}", None, False),
    "streamComparisonPairTile": ("GET", f"/comparison-sheet-pairs/{PAIR}/tile?mode=overlay&level=0&column=0&row=0",
                                 None, False),
    "getComparisonOverview": ("GET", f"/projects/{PRJ}/comparison-overview", None, False),
    "getComparisonQueueSummary": ("GET", "/execution/comparison-queue", None, False),
}
EXPERT_WRITES = {name for name, (_m, _p, _b, keyed) in REQUESTS.items() if keyed}
DEPENDENCIES = {"comparison_matrix", "comparison_series", "comparison_pair_tiles", "comparison_overview"}
#: Lanes that serve one of them remove it from the stub list below and add it here; the role, key and shape tests
#: still judge it.
#: `CMP-MATRIX-01` serves the six matrix operations; `CMP-VIEWER-01` serves the pair tile; `CMP-SERIES-01` serves the nine
#: series operations.
WIRED: frozenset[str] = frozenset({
    "getComparisonMatrix", "prepareComparisonMatrix", "listComparisonMatrixEdits", "applyComparisonMatrixEdits",
    "undoComparisonMatrixEdit", "listComparisonAiLinks",
    "streamComparisonPairTile",
    "startComparisonSeries", "listComparisonSeries", "getComparisonSeries", "pauseComparisonSeries",
    "resumeComparisonSeries", "cancelComparisonSeries", "finishComparisonSeries", "listComparisonSheetPairs",
    "getComparisonSheetPair",
    "getComparisonOverview", "getComparisonQueueSummary",  # `CMP-VC-OVERVIEW-01`
})
STUBS = sorted(set(REQUESTS) - WIRED)
THE_THREE = ("approveSheetPairing", "withdrawSheetPairing", "generateComparisonSummary")


def _client(extra: dict[str, str] | None = None) -> TestClient:
    environ = {k: v for k, v in os.environ.items() if k != COMPARISON_MODULES_ENV} | {
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET} | (extra or {})
    application = create_app(environ=environ)
    return TestClient(create_asgi_app(environ=environ, application=application), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    return _client()


def _call(client: TestClient, name: str, *, token: str | None, key: str | None = KEY) -> Any:
    method, path, body, keyed = REQUESTS[name]
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if keyed and key is not None:
        headers["Idempotency-Key"] = key
    kwargs: dict[str, Any] = {}
    if body is not None:
        headers["content-type"] = "application/json"
        kwargs["content"] = json.dumps(body).encode()
    return client.request(method, path, headers=headers, **kwargs)


def test_the_requests_cover_exactly_the_eighteen_operations_the_contract_added() -> None:
    document = json.load(open("contracts/api/v1/openapi.json", encoding="utf-8"))
    first_wave = {"createComparisonUpload", "listComparisonUploads", "getComparisonUpload",
                  "getComparisonUploadProposal", "uploadComparisonUploadPart", "completeComparisonUploadFile",
                  "confirmComparisonUploadSet", "excludeComparisonUploadSet", "retryComparisonUploadSet",
                  "pauseComparisonUpload", "resumeComparisonUpload", "cancelComparisonUpload",
                  "listComparisonVersionOrders", "appendComparisonVersionOrder", "listVersionPageProfiles",
                  "getVersionPageProfile", "streamVersionPagePreview", "streamVersionPageThumbnail",
                  "streamVersionPageTile"}
    sealed = {op["operationId"] for item in document["paths"].values() for m, op in item.items()
              if m in ("get", "post", "put", "patch", "delete") and "comparison" in op.get("tags", [])} | {
        "getComparisonQueueSummary"}
    assert set(REQUESTS) == sealed - first_wave and len(REQUESTS) == 18
    assert {triple[2] for triple in FACTS.operations} >= set(REQUESTS)


@pytest.mark.parametrize("name", STUBS)
def test_every_core_operation_answers_dependency_unavailable_and_nothing_else(
    client: TestClient, name: str
) -> None:
    response = _call(client, name, token=static_token())
    body = response.json()
    assert response.status_code == 503, (name, response.status_code, body)
    assert body["error_code"] == "dependency_unavailable"
    assert body["details"]["dependency"] in DEPENDENCIES, body
    assert body["retryable"] is True


@pytest.mark.parametrize("name", sorted(REQUESTS))
def test_an_unauthenticated_request_is_refused_before_the_stub(client: TestClient, name: str) -> None:
    response = _call(client, name, token=None)
    assert response.status_code == 401 and response.json()["error_code"] == "authentication_required", name


@pytest.mark.parametrize("name", sorted(EXPERT_WRITES))
def test_a_write_without_its_idempotency_key_is_refused_not_stubbed(client: TestClient, name: str) -> None:
    response = _call(client, name, token=static_token(), key=None)
    assert response.status_code == 422 and response.json()["error_code"] == "validation_failed", name


def test_a_malformed_body_is_refused_before_the_stub(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY,
               "content-type": "application/json"}
    edits = f"{DOCUMENT}/comparison-matrix/edits"
    page = {"version_uid": VER, "page_number": 1}
    for bad in ({}, {"base_revision": BASE}, {"base_revision": BASE, "edits": []},
                {"base_revision": {"matrix_id": "x", "edit_no": 0}, "edits": [{"kind": "unlink", "page": page}]},
                {"base_revision": {**BASE, "edit_no": -1}, "edits": [{"kind": "unlink", "page": page}]},
                {"base_revision": BASE, "edits": [{"kind": "undo", "page": page}]},
                {"base_revision": BASE, "edits": [{"kind": "unlink", "page": {**page, "page_number": 0}}]},
                {"base_revision": BASE, "edits": [{"kind": "unlink", "page": page}] * 501}):
        response = client.post(edits, content=json.dumps(bad).encode(), headers=headers)
        assert response.status_code == 422, (str(bad)[:80], response.status_code)
    series = f"{DOCUMENT}/comparison-series"
    for bad in ({"restart": "maybe"}, {"base_order_revision_no": -1}, {"surprise": True}):
        assert client.post(series, content=json.dumps(bad).encode(), headers=headers).status_code == 422, bad


def test_a_tile_or_list_query_outside_its_bounds_is_refused_before_the_stub(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {static_token()}"}
    tile = f"/comparison-sheet-pairs/{PAIR}/tile"
    assert client.get(tile, headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=overlay&level=0&column=0", headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=sideways&level=0&column=0&row=0", headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=a&level=13&column=0&row=0", headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=a&level=0&column=4096&row=0", headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=a&level=0&column=0&row=0&layers=hidden", headers=headers).status_code == 422
    assert client.get(f"{tile}?mode=a&level=0&column=0&row=0&layers=main,hidden", headers=headers).status_code == 422
    # `CMP-VIEWER-01` serves the tile: a well-formed query about a pair that does not exist is `404`, not the stub's `503`.
    assert client.get(f"{tile}?mode=a&level=0&column=0&row=0&layers=main,noise&align_blocks=true",
                      headers=headers).status_code == 404
    pairs = f"/comparison-transitions/{TRN}/sheet-pairs"
    assert client.get(f"{pairs}?status=sideways", headers=headers).status_code == 422
    assert client.get(f"{pairs}?limit=0", headers=headers).status_code == 422
    # `CMP-SERIES-01` serves the list: a well-formed query about a transition that does not exist is `404`.
    assert client.get(f"{pairs}?status=different&only_changes=true&limit=200", headers=headers).status_code == 404


def test_the_roles_are_the_ones_the_adr_gives() -> None:
    """Reads are any one role; every write is the expert's act (decision 16). A literal, not a read-back."""
    for name in REQUESTS:
        expected = frozenset({"expert"}) if name in EXPERT_WRITES else frozenset({"expert", "admin"})
        assert OPERATION_ROLES[name] == expected, name


def test_that_check_fails_when_a_write_is_opened_to_an_administrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: an administrator without the expert role would apply a matrix edit."""
    from types import MappingProxyType
    from auditmanager.api import security
    widened = MappingProxyType({**OPERATION_ROLES, "applyComparisonMatrixEdits": frozenset({"expert", "admin"})})
    monkeypatch.setattr(security, "OPERATION_ROLES", widened)
    with pytest.raises(AssertionError):
        for name in REQUESTS:
            expected = frozenset({"expert"}) if name in EXPERT_WRITES else frozenset({"expert", "admin"})
            assert security.OPERATION_ROLES[name] == expected, name


# -- the upload flag --------------------------------------------------------------------------------


def test_the_upload_flag_is_accepted_true_and_false_and_reaches_the_operation(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY,
               "content-type": "application/json"}
    file = {"display_name": "a.pdf", "size_bytes": 10, "sha256": "a" * 64}
    path = f"/projects/{PRJ}/comparison-uploads"
    # `CMP-SERIES-01` stores the flag: ``true`` is no longer refused with ``503``; like ``false`` it reaches the
    # operation, which does not know the project (the storing itself is proved on a real project in
    # ``tests/integration/comparison/series/test_upload_flag.py``).
    asked = client.post(path, content=json.dumps({"files": [file], "compare_after_preparation": True}).encode(),
                        headers=headers)
    assert asked.status_code == 404, asked.text
    wrong = client.post(path, content=json.dumps({"files": [file], "compare_after_preparation": "maybe"}).encode(),
                        headers=headers)
    assert wrong.status_code == 422
    # absent and false reach the operation too
    for body in ({"files": [file]}, {"files": [file], "compare_after_preparation": False}):
        assert client.post(path, content=json.dumps(body).encode(), headers=headers).status_code == 404


# -- the three 0035 operations while the versions module is on (ADR-0025 decision 13) --------------------


_PAIRING = f"{DOCUMENT}/versions/{VER}/comparison/sheet-pairings"
_THREE_REQUESTS: dict[str, tuple[str, str, Any]] = {
    "approveSheetPairing": ("POST", _PAIRING, {
        "target_version_uid": OTHER_VER, "mode": "version", "source_page_number": 1,
        "target_page_number": 1, "suggestion_sha256": "a" * 64}),
    "withdrawSheetPairing": ("POST", f"{_PAIRING}/sln_01ARZ3NDEKTSV4RRFFQ69G5FAV/withdrawals", {"mode": "version"}),
    "generateComparisonSummary": ("POST", f"{DOCUMENT}/versions/{VER}/comparison/summaries", {
        "target_version_uid": OTHER_VER, "mode": "version"}),
}


def _three(served: TestClient, name: str) -> Any:
    method, path, body = _THREE_REQUESTS[name]
    return served.request(method, path, content=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY, "content-type": "application/json"})


@pytest.mark.parametrize("value", ["versions", "versions,stages"])
@pytest.mark.parametrize("name", THE_THREE)
def test_the_three_sheet_pairing_operations_answer_dependency_unavailable_while_the_module_is_on(
    name: str, value: str
) -> None:
    response = _three(_client({COMPARISON_MODULES_ENV: value}), name)
    assert response.status_code == 503, (name, response.status_code, response.text)
    assert response.json()["details"]["dependency"] == "comparison_versions_module"


@pytest.mark.parametrize("name", THE_THREE)
def test_the_three_sheet_pairing_operations_keep_working_while_the_module_is_off(
    client: TestClient, name: str
) -> None:
    """With the module off they reach their own handler: the version they name does not exist, so ``404``."""
    response = _three(client, name)
    assert response.status_code == 404, (name, response.status_code, response.text)
    assert response.json()["error_code"] == "not_found"
