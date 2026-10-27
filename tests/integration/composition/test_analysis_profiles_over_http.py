"""`W59-ANALYSIS-SETTINGS-01`, end to end: ``listAnalysisProfiles`` over the composed application.

The shipped ``create_asgi_app`` (recorded provider) against the lane's own PostgreSQL and
MinIO, driven with a real expert credential. What is held:

* the answer is the registry the application routes runs through, not a copy: fifteen rows in
  the project-structure order (``PROJECT_STRUCTURE_ORDER``), named from the reviewed section
  catalogue; every registered section carries exactly its registry entry's identities,
  version, status and content hashes; AR carries ``profile: null`` (`PROD-11-AR-V1-V2-REMOVAL-01`:
  the АР analysis path is the v3 group, not a text profile, and ``startRun`` refuses an АР
  version for the same reason); every package carries
  the status and version its line of ``section_profile_expectations.json`` names (`draft` at
  ``1.0.0`` until a section's review moves its line) and the source its ``profile.json``
  declares; ``PB`` (`PB-PROFILE-01`) is an authored profile that declares ``source: null``, and
  it is the only row with a profile and no source;
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
#: One line per non-AR package: the status and version it must be served with
#: (`PROD-14-0-EXPECTATIONS-01`). A section lane edits its own line, not this suite.
EXPECTATIONS = (
    REPOSITORY_ROOT / "tests" / "unit" / "analysis" / "text_profiles" / "section_profile_expectations.json"
)


def _expected_sections() -> dict[str, tuple[str, str]]:
    """``code -> (status, profile_version)`` for every non-AR package of this tree."""
    rows = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))["sections"]
    return {row["code"]: (row["status"], row["profile_version"]) for row in rows}


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
    expected = _expected_sections()
    by_code = {item["section_code"]: item["profile"] for item in listing["items"]}
    # `PROD-11-AR-V1-V2-REMOVAL-01`: АР is the one row with no profile.
    assert {code for code, profile in by_code.items() if profile is None} == {"AR"}
    assert by_code["AR"] is None
    assert set(registry.entries) == {code for code, profile in by_code.items() if profile}
    assert len(registry.entries) == 14 and len(by_code) == 15
    packages = set(registry.entries)
    assert packages - set(expected) == set(), "a served package has no line in the expectations file"
    assert set(expected) - packages == set(), "a line of the expectations file has no served package"

    for code, entry in registry.entries.items():
        profile = by_code[code]
        assert profile["analysis_profile_id"] == entry.analysis_profile_id
        assert profile["prompt_bundle_id"] == entry.prompt_bundle_id
        assert profile["profile_version"] == entry.profile.profile_version
        assert profile["prompt_bundle_sha256"] == entry.profile.prompt_bundle.content_sha256
        assert profile["content_sha256"] == entry.profile.content_sha256
        assert (profile["status"], profile["profile_version"]) == expected[code], (
            f"{code}: the served (status, profile_version) is not the expectations file's"
        )
        declared = json.loads(
            (PACKAGES_ROOT / code.lower() / "profile.json").read_text(encoding="utf-8")
        )
        assert profile["source"] == declared["source"]

    pb = by_code["PB"]
    assert (pb["status"], pb["profile_version"]) == expected["PB"], "the authored profile is served as expected"
    assert pb["source"] is None, "PB has no legacy source and says so"
    assert pb["analysis_profile_id"] == registry.entries["PB"].analysis_profile_id


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
