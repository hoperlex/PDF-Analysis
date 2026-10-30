"""`CMP-SEAL-C0`: the nineteen comparison operations of contract `1.9.0`, served by the composition root.

Every one is a sealed stub: it answers ``503 dependency_unavailable`` (``details.dependency`` one of
three stable class names) to an account that holds the role it needs, and nothing is read or written.
The module set (``AUDITMANAGER_COMPARISON_MODULES``) reaches the web through ``getProductVersion``:
``none`` by default, the configured set otherwise, and a value outside the three stops the process while
it is wiring. Each rule is shown failing: the role map is compared with a literal written here, and the
mutation tests below break the thing under test and watch the assertion go red.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE, OPERATION_ROLES
from auditmanager.bootstrap.settings import ConfigurationError
from auditmanager.comparison.public import COMPARISON_MODULES_ENV
from tests.integration.composition.test_router_answers import DEPLOYMENT_SECRET, static_token
from tests.support.expected_facts import FACTS

PRJ = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOC = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VER = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
UP = "cbt_01ARZ3NDEKTSV4RRFFQ69G5FAV"
FILE = "cuf_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SET = "cus_01ARZ3NDEKTSV4RRFFQ69G5FAV"
PROFILE = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64
KEY = "key-comparison-stub"

#: operationId -> (method, path, json body, bytes body, keyed). Written here, not read from the contract.
REQUESTS: dict[str, tuple[str, str, Any, bytes | None, bool]] = {
    "createComparisonUpload": ("POST", f"/projects/{PRJ}/comparison-uploads",
                               {"files": [{"display_name": "a.pdf", "size_bytes": 10, "sha256": SHA}]}, None, True),
    "listComparisonUploads": ("GET", f"/projects/{PRJ}/comparison-uploads", None, None, False),
    "getComparisonUpload": ("GET", f"/comparison-uploads/{UP}", None, None, False),
    "getComparisonUploadProposal": ("GET", f"/comparison-uploads/{UP}/proposal", None, None, False),
    "uploadComparisonUploadPart": ("PUT", f"/comparison-uploads/{UP}/files/{FILE}/parts?part_number=1",
                                   None, b"bytes", True),
    "completeComparisonUploadFile": ("POST", f"/comparison-uploads/{UP}/files/{FILE}/completion", None, None, True),
    "confirmComparisonUploadSet": ("POST", f"/comparison-uploads/{UP}/sets/{SET}/confirmation",
                                   {"files": [{"file_id": FILE}]}, None, True),
    "excludeComparisonUploadSet": ("POST", f"/comparison-uploads/{UP}/sets/{SET}/exclusion", None, None, True),
    "retryComparisonUploadSet": ("POST", f"/comparison-uploads/{UP}/sets/{SET}/retry", None, None, True),
    "pauseComparisonUpload": ("POST", f"/comparison-uploads/{UP}/pause", None, None, True),
    "resumeComparisonUpload": ("POST", f"/comparison-uploads/{UP}/resume", None, None, True),
    "cancelComparisonUpload": ("POST", f"/comparison-uploads/{UP}/cancellation", None, None, True),
    "listComparisonVersionOrders": ("GET", f"/projects/{PRJ}/documents/{DOC}/comparison-version-orders",
                                    None, None, False),
    "appendComparisonVersionOrder": ("POST", f"/projects/{PRJ}/documents/{DOC}/comparison-version-orders",
                                     {"version_uids": [VER], "base_revision_no": 0}, None, True),
    "listVersionPageProfiles": ("GET", f"/versions/{VER}/page-profiles", None, None, False),
    "getVersionPageProfile": ("GET", f"/page-profiles/{PROFILE}", None, None, False),
    "streamVersionPagePreview": ("GET", f"/page-profiles/{PROFILE}/preview", None, None, False),
    "streamVersionPageThumbnail": ("GET", f"/page-profiles/{PROFILE}/thumbnail", None, None, False),
    "streamVersionPageTile": ("GET", f"/page-profiles/{PROFILE}/tile?level=0&column=0&row=0", None, None, False),
}
EXPERT_WRITES = {name for name, (_m, _p, _b, _c, keyed) in REQUESTS.items() if keyed}
DEPENDENCIES = {"comparison_uploads", "comparison_version_orders", "version_pages"}
#: `CMP-INGEST-01` serves the first eight, `CMP-INGEST-02` the next six and `CMP-PROFILE-01` the five page reads; they
#: are no longer stubs. The lane that
#: serves one more adds it here and the stub test below stops asking it for `503`; the role, key and shape tests below
#: still judge it.
WIRED = frozenset({
    "createComparisonUpload", "getComparisonUpload", "getComparisonUploadProposal", "uploadComparisonUploadPart",
    "completeComparisonUploadFile", "confirmComparisonUploadSet", "listComparisonVersionOrders",
    "appendComparisonVersionOrder",
    "listComparisonUploads", "excludeComparisonUploadSet", "retryComparisonUploadSet", "pauseComparisonUpload",
    "resumeComparisonUpload", "cancelComparisonUpload",
    "listVersionPageProfiles", "getVersionPageProfile", "streamVersionPagePreview", "streamVersionPageThumbnail",
    "streamVersionPageTile",
})
STUBS = sorted(set(REQUESTS) - WIRED)


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
    method, path, body, raw, keyed = REQUESTS[name]
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if keyed and key is not None:
        headers["Idempotency-Key"] = key
    kwargs: dict[str, Any] = {}
    if body is not None:
        headers["content-type"] = "application/json"
        kwargs["content"] = json.dumps(body).encode()
    if raw is not None:
        headers["content-type"] = "application/octet-stream"
        kwargs["content"] = raw
    return client.request(method, path, headers=headers, **kwargs)


def test_the_requests_cover_exactly_the_nineteen_operations_the_contract_added() -> None:
    document = json.load(open("contracts/api/v1/openapi.json", encoding="utf-8"))
    comparison = {op["operationId"] for item in document["paths"].values() for m, op in item.items()
                  if m in ("get", "post", "put", "patch", "delete") and "comparison" in op.get("tags", [])}
    # `CMP-SEAL-C1` tags seventeen more operations `comparison`; they are `test_comparison_core_stub_operations.py`'s.
    assert set(REQUESTS) <= comparison and len(REQUESTS) == 19
    assert {triple[2] for triple in FACTS.operations} >= comparison


@pytest.mark.parametrize("name", STUBS)
def test_every_comparison_operation_answers_dependency_unavailable_and_nothing_else(
    client: TestClient, name: str
) -> None:
    response = _call(client, name, token=static_token())
    body = response.json()
    assert response.status_code == 503, (name, response.status_code, body)
    assert body["error_code"] == "dependency_unavailable"
    assert body["details"]["dependency"] in DEPENDENCIES, body
    assert body["retryable"] is True


@pytest.mark.parametrize("name", sorted(WIRED))
def test_a_wired_operation_names_what_it_was_asked_about_and_is_no_longer_a_stub(client: TestClient, name: str) -> None:
    """Every identity in the requests above names nothing, so a served operation answers ``404 not_found`` (the
    project, the batch, the file, the set or the document), never the stub's ``503``."""
    response = _call(client, name, token=static_token())
    assert response.status_code == 404, (name, response.status_code, response.text)
    assert response.json()["error_code"] == "not_found"


@pytest.mark.parametrize("name", sorted(REQUESTS))
def test_an_unauthenticated_request_is_refused_before_the_stub(client: TestClient, name: str) -> None:
    response = _call(client, name, token=None)
    assert response.status_code == 401 and response.json()["error_code"] == "authentication_required", name


@pytest.mark.parametrize("name", sorted(EXPERT_WRITES))
def test_a_write_without_its_idempotency_key_is_refused_not_stubbed(client: TestClient, name: str) -> None:
    response = _call(client, name, token=static_token(), key=None)
    assert response.status_code == 422 and response.json()["error_code"] == "validation_failed", name


def test_a_malformed_body_is_refused_before_the_stub(client: TestClient) -> None:
    method, path, _body, _raw, _keyed = REQUESTS["createComparisonUpload"]
    for bad in ({"files": []}, {}, {"files": [{"display_name": "", "size_bytes": 1, "sha256": SHA}]},
                {"files": [{"display_name": "a", "size_bytes": 0, "sha256": SHA}]},
                {"files": [{"display_name": "a", "size_bytes": 1, "sha256": "x"}]}):
        response = client.request(method, path, content=json.dumps(bad).encode(),
                                  headers={"Authorization": f"Bearer {static_token()}",
                                           "Idempotency-Key": KEY, "content-type": "application/json"})
        assert response.status_code == 422, (bad, response.status_code)


def test_a_part_over_sixteen_mebibytes_is_refused_before_the_stub(client: TestClient) -> None:
    method, path, _b, _raw, _k = REQUESTS["uploadComparisonUploadPart"]
    headers = {"Authorization": f"Bearer {static_token()}", "Idempotency-Key": KEY,
               "content-type": "application/octet-stream"}
    assert client.request(method, path, headers=headers, content=b"x" * (16 * 1024 * 1024 + 1)).status_code == 422
    # A part of exactly 16 MiB is within the bound and reaches the operation; the batch it names does not exist.
    assert client.request(method, path, headers=headers, content=b"x" * (16 * 1024 * 1024)).status_code == 404
    assert client.request(method, path.replace("part_number=1", "part_number=0"), headers=headers,
                          content=b"x").status_code == 422


def test_a_tile_address_outside_its_bounds_is_refused_before_the_stub(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {static_token()}"}
    base = f"/page-profiles/{PROFILE}/tile"
    assert client.get(base, headers=headers).status_code == 422
    assert client.get(f"{base}?level=13&column=0&row=0", headers=headers).status_code == 422
    assert client.get(f"{base}?level=0&column=4096&row=0", headers=headers).status_code == 422
    # `CMP-PROFILE-01` serves the tile: an address inside its bounds reaches the read, and the profile it names
    # does not exist.
    assert client.get(f"{base}?level=12&column=4095&row=4095", headers=headers).status_code == 404


def test_the_roles_are_the_ones_the_adr_gives() -> None:
    """Reads are any one role; every write is the expert's act (decision 16). A literal, not a read-back."""
    writes = EXPERT_WRITES
    for name in REQUESTS:
        expected = frozenset({"expert"}) if name in writes else frozenset({"expert", "admin"})
        assert OPERATION_ROLES[name] == expected, name


def test_that_check_fails_when_a_write_is_opened_to_an_administrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: an administrator without the expert role would reach «Порядок версий»."""
    from types import MappingProxyType
    from auditmanager.api import security
    widened = MappingProxyType({**OPERATION_ROLES, "appendComparisonVersionOrder": frozenset({"expert", "admin"})})
    monkeypatch.setattr(security, "OPERATION_ROLES", widened)
    with pytest.raises(AssertionError):
        for name in REQUESTS:
            expected = frozenset({"expert"}) if name in EXPERT_WRITES else frozenset({"expert", "admin"})
            assert security.OPERATION_ROLES[name] == expected, name


# -- the module set --------------------------------------------------------------------------------


def test_the_product_version_says_none_unless_the_deployment_names_a_module_set(client: TestClient) -> None:
    response = client.get("/system/version", headers={"Authorization": f"Bearer {static_token()}"})
    assert response.status_code == 200
    body = response.json()
    assert body["comparison_modules"] == "none" and body["contract_version"] == "1.12.0"


@pytest.mark.parametrize("value", ["versions", "versions,stages"])
def test_the_product_version_carries_the_configured_module_set(value: str) -> None:
    served = _client({COMPARISON_MODULES_ENV: value})
    response = served.get("/system/version", headers={"Authorization": f"Bearer {static_token()}"})
    assert response.json()["comparison_modules"] == value


@pytest.mark.parametrize("value", ["stages", "everything", "versions;stages"])
def test_a_module_set_outside_the_three_stops_the_process_while_it_wires(value: str) -> None:
    environ = {k: v for k, v in os.environ.items()} | {
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET, COMPARISON_MODULES_ENV: value}
    with pytest.raises(ConfigurationError):
        create_app(environ=environ)
