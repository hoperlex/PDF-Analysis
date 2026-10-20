"""`W59-ANALYSIS-SETTINGS-01`, end to end: ``listAnalysisProfiles`` over the composed application.

The shipped ``create_asgi_app`` (recorded provider) against the lane's own PostgreSQL and
MinIO, driven with a real expert credential. What is held:

* the answer is the registry the application routes runs through, not a copy: fifteen rows in
  the project-structure order (``PROJECT_STRUCTURE_ORDER``), named from the reviewed section
  catalogue; every registered section carries exactly its registry entry's identities,
  version, status and content hashes; AR is ``builtin`` with no source; every package is
  ``draft`` with the source its ``profile.json`` declares; ``PB`` -- the one section run start
  refuses for want of a profile -- carries ``profile: null``;
* every object carries exactly its frozen schema's properties;
* no credential is ``401``; the role decision (any one role) is the role register's, held by
  ``tests/integration/api/test_role_register.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.analysis.text.profile import AR_TEXT_PROFILE
from auditmanager.analysis.text.profile_registry import (
    PACKAGES_ROOT,
    PROJECT_STRUCTURE_ORDER,
    load_text_profile_registry,
)
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.sections.public import section_names

DEPLOYMENT_SECRET = "w59-analysis-settings-over-http-token"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"


@pytest.fixture(scope="module")
def client() -> TestClient:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    for leaked in ("ANTHROPIC_API_KEY", "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN"):
        assert leaked not in os.environ, f"{leaked} reached this suite"
    from auditmanager.api.app import create_asgi_app

    app = create_asgi_app(environ=dict(os.environ) | {
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET,
    })
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def listing(client: TestClient) -> dict[str, Any]:
    from am_test_accounts import provisioned_credential

    token = provisioned_credential(DEPLOYMENT_SECRET, "w59-analysis-settings")
    answer = client.get("/analysis/profiles", headers={"Authorization": f"Bearer {token}"})
    assert answer.status_code == 200, answer.content
    assert answer.headers.get("X-Correlation-Id")
    return answer.json()


def test_fifteen_rows_in_the_project_structure_order_named_from_the_catalogue(
    listing: dict[str, Any],
) -> None:
    names = section_names()
    assert [item["section_code"] for item in listing["items"]] == list(PROJECT_STRUCTURE_ORDER)
    assert len(listing["items"]) == 15
    for item in listing["items"]:
        assert item["section_name"] == names[item["section_code"]]


def test_every_row_is_the_registry_entry_the_application_routes_by(
    listing: dict[str, Any],
) -> None:
    registry = load_text_profile_registry()
    by_code = {item["section_code"]: item["profile"] for item in listing["items"]}
    assert {code for code, profile in by_code.items() if profile is None} == {"PB"}
    assert set(registry.entries) == {code for code, profile in by_code.items() if profile}

    for code, entry in registry.entries.items():
        profile = by_code[code]
        assert profile["analysis_profile_id"] == entry.analysis_profile_id
        assert profile["prompt_bundle_id"] == entry.prompt_bundle_id
        assert profile["profile_version"] == entry.profile.profile_version
        assert profile["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
        assert profile["content_sha256"] == entry.profile.content_sha256
        if code == "AR":
            assert profile["status"] == "builtin"
            assert profile["source"] is None
            assert profile["analysis_profile_id"] == str(AR_TEXT_PROFILE.analysis_profile_id)
            continue
        assert profile["status"] == "draft"
        declared = json.loads(
            (PACKAGES_ROOT / code.lower() / "profile.json").read_text(encoding="utf-8")
        )
        assert profile["source"] == declared["source"]


def test_every_object_carries_exactly_the_frozen_schemas_properties(
    listing: dict[str, Any],
) -> None:
    """Closed objects: each carries the properties its frozen schema requires, no more."""
    schemas = json.loads(CONTRACT.read_text(encoding="utf-8"))["components"]["schemas"]

    def keys(name: str) -> set[str]:
        assert schemas[name]["additionalProperties"] is False
        assert set(schemas[name]["required"]) == set(schemas[name]["properties"])
        return set(schemas[name]["properties"])

    assert set(listing) == keys("AnalysisProfileList")
    for item in listing["items"]:
        assert set(item) == keys("AnalysisProfileListItem")
        profile = item["profile"]
        if profile is None:
            continue
        assert set(profile) == keys("AnalysisProfileSummary")
        assert profile["status"] in schemas["AnalysisProfileStatus"]["enum"]
        if profile["source"] is not None:
            assert set(profile["source"]) == keys("AnalysisProfileSource")
            for file in profile["source"]["files"]:
                assert set(file) == keys("AnalysisProfileSourceFile")


def test_no_credential_is_refused(client: TestClient) -> None:
    answer = client.get("/analysis/profiles")
    assert answer.status_code == 401
    assert answer.json()["error_code"] == "authentication_required"
