"""`BETA-CONTRACT-SEAL-01` phase B: the contract is sealed at ``1.0.0``, everywhere it is declared.

One ``contract_version`` literal is shared by the API document, the three domain catalogs, the
analysis and events families, the application, the edge's own error bodies and the web client.
A seal that moved nine of them and left a tenth on ``1.0.0-draft.1`` would answer two versions
from one deployment, so this module reads every holder of the literal and requires the same
string from each.

Every expectation is a literal written here. The facts file, the catalogs and the code derive
their version from one another elsewhere; a pin that read the version back from the thing it
judges could not say that the thing moved.

The freeze is judged separately from the version: the domain catalogs must say ``frozen``, the
schemas must refuse a catalog that does not, and the one undecided owner question
(``OPEN-RETENTION``) must stay undecided and must not have grown a number.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from auditmanager.analysis.engine import CONTRACT_VERSION as ANALYSIS_CONTRACT_VERSION
from auditmanager.api.routers import CONTRACT_VERSION as API_CONTRACT_VERSION
from auditmanager.api.schemas.models import ErrorEnvelope
from auditmanager.shared.errors import CONTRACT_VERSION as DOMAIN_CONTRACT_VERSION
from tests.support.expected_facts import FACTS

ROOT = Path(__file__).resolve().parents[3]
SEALED = "1.10.0"
DRAFT = "1.0.0-draft.1"
PREVIOUS = "1.9.0"
FAMILIES = ("analysis", "domain", "events")
DOMAIN = ROOT / "contracts/domain/v1"
CATALOGS = ("error-codes.json", "identifiers.json", "state-machines.json")
SCHEMAS = ("error-codes.schema.json", "identifiers.schema.json", "state-machines.schema.json")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _family_files(family: str) -> list[Path]:
    return sorted((ROOT / "contracts" / family / "v1").rglob("*.json"))


def _version_values(node: object, found: list[tuple[str, str]], where: str = "") -> None:
    """Every value a contract file declares for a version-bearing key."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"contract_version", "name_map_contract_version"} and isinstance(value, str):
                found.append((f"{where}/{key}", value))
            elif (
                key == "const"
                and isinstance(value, str)
                and where.endswith(("/contract_version", "/name_map_contract_version"))
                and value.startswith(("1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "1.7.0", "1.8.0", "1.9.0"))
            ):
                found.append((f"{where}/const", value))
            _version_values(value, found, f"{where}/{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _version_values(item, found, f"{where}[{index}]")


def test_the_facts_file_names_the_sealed_version() -> None:
    assert FACTS.contract_version == SEALED


@pytest.mark.parametrize("family", FAMILIES)
def test_every_json_artifact_of_a_family_declares_only_the_sealed_version(family: str) -> None:
    files = _family_files(family)
    assert files, family
    seen = 0
    for path in files:
        found: list[tuple[str, str]] = []
        _version_values(_json(path), found)
        for where, value in found:
            seen += 1
            assert value == SEALED, f"{path.relative_to(ROOT)}{where} says {value!r}, not {SEALED!r}"
    assert seen >= len(files) // 2, f"{family}: the walk found almost no version-bearing keys"


def test_the_api_document_and_its_web_copy_declare_the_sealed_version() -> None:
    for path in (ROOT / "contracts/api/v1/openapi.json", ROOT / "web/openapi/openapi.json"):
        document = _json(path)
        assert document["info"]["version"] == SEALED, path
        assert document["components"]["schemas"]["ErrorEnvelope"]["properties"]["contract_version"] == {
            "const": SEALED
        }, path
    assert (ROOT / "contracts/api/v1/openapi.json").read_bytes() == (ROOT / "web/openapi/openapi.json").read_bytes()


def test_the_application_constants_are_the_sealed_version() -> None:
    assert API_CONTRACT_VERSION == SEALED
    assert ANALYSIS_CONTRACT_VERSION == SEALED
    assert DOMAIN_CONTRACT_VERSION == SEALED  # read from the domain catalog at import
    assert ErrorEnvelope.model_json_schema()["properties"]["contract_version"] == {
        "const": SEALED, "title": "Contract Version", "type": "string",
    }


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
def test_the_edge_answers_its_own_error_bodies_with_the_sealed_version(name: str) -> None:
    source = (ROOT / "infra/deploy/proxy" / name).read_text(encoding="utf-8")
    versions = re.findall(r'"contract_version":"([^"]*)"', source)
    assert versions, f"{name} no longer carries an error body"
    assert set(versions) == {SEALED}, f"{name}: {sorted(set(versions))}"


def test_the_web_forwarder_answers_its_own_error_body_with_the_sealed_version() -> None:
    source = (ROOT / "web/src/shared/api/credentialed-forward.ts").read_text(encoding="utf-8")
    assert re.findall(r"contract_version: '([^']*)'", source) == [SEALED]


def test_no_live_contract_artifact_still_names_the_draft_as_its_own_version() -> None:
    """The draft survives only as the version the sealed contract supersedes."""
    for family in FAMILIES:
        for path in _family_files(family):
            found: list[tuple[str, str]] = []
            _version_values(_json(path), found)
            assert all(value != DRAFT for _where, value in found), path
    for path in (ROOT / "contracts/api/v1/openapi.json",):
        assert _json(path)["info"]["version"] != DRAFT


@pytest.mark.parametrize("name", CATALOGS)
def test_a_domain_catalog_is_frozen_at_the_sealed_round(name: str) -> None:
    catalog = _json(DOMAIN / name)
    assert (catalog["contract_version"], catalog["supersedes"]) == (SEALED, PREVIOUS)
    assert (catalog["status"], catalog["frozen"]) == ("frozen", True)
    assert catalog["candidate_revision"] == 28


@pytest.mark.parametrize("name", SCHEMAS)
def test_a_domain_schema_refuses_a_catalog_that_is_not_frozen(name: str) -> None:
    properties = _json(DOMAIN / name)["properties"]
    assert properties["contract_version"] == {"const": SEALED}
    assert properties["supersedes"] == {"const": PREVIOUS}
    assert properties["status"] == {"const": "frozen"}
    assert properties["frozen"] == {"const": True}
    assert properties["candidate_revision"]["const"] == 28


def test_the_envelope_schema_pins_the_sealed_version() -> None:
    schema = _json(DOMAIN / "error-envelope.schema.json")
    assert schema["properties"]["contract_version"]["const"] == SEALED


def test_the_catalog_is_frozen_with_all_twenty_seven_codes() -> None:
    catalog = _json(DOMAIN / "error-codes.json")
    assert len(catalog["codes"]) == 27
    assert {entry["status"] for entry in catalog["open_owner_decisions"]} <= {
        "approved", "approved_with_modification", "not_decided",
    }


def test_the_retention_question_stays_undecided_and_declares_no_window() -> None:
    catalog = _json(DOMAIN / "error-codes.json")
    (retention,) = [d for d in catalog["open_owner_decisions"] if d["id"] == "OPEN-RETENTION"]
    assert retention["status"] == "not_decided"
    assert retention["affects"] == ["idempotency_key_stale"]
    text = retention["statement"] + " " + retention["gate"]
    assert "At the 1.0.0 freeze" in text and "declares no retention window" in text
    # The freeze states that no window exists; it must not have invented one.
    assert not re.search(r"\b\d+\s*(?:day|days|hour|hours|minute|minutes|month|months|year|years)\b", text, re.I)
    stale = catalog["codes"]["idempotency_key_stale"]
    assert "retention" not in stale["summary"].lower() or "not" in stale["summary"].lower()


def test_the_rate_limited_note_names_the_credential_exchange() -> None:
    notes = " ".join(_json(DOMAIN / "error-codes.json")["codes"]["rate_limited"]["notes"])
    for call in ("POST /registrations", "POST /registrations/status", "POST /auth/token"):
        assert call in notes, call
    openapi = _json(ROOT / "contracts/api/v1/openapi.json")
    assert "`rate_limited` (`429`)" in openapi["paths"]["/auth/token"]["post"]["description"]


def test_the_two_prose_rules_the_seal_corrected_are_corrected() -> None:
    description = _json(ROOT / "contracts/api/v1/openapi.json")["info"]["description"]
    assert "Reading product data needs any active account with a complete profile;" not in description
    assert "at least one role (`R-80`" in description
    assert "with one exception: the portal block identity `portal_block_id`" in description
    assert "is reserved for the future proposal pipeline" not in description
    assert "in the reserved `contracts/optimization/v1` family" not in description
