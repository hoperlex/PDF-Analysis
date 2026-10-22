"""`BETA-CONTRACT-SEAL-01` phase A (`D-179`): the two run-routing refusals have codes of their own.

``startRun`` and ``reauditRun`` route a run's analysis profile from the version's expert-confirmed
classification and refuse before the idempotency key is claimed. A draft of the contract
reported both refusals as ``required_norm_unavailable``, told apart by ``details.reference_kind``
(``version_classification`` / ``analysis_profile``); the final catalogue gives each a code.

Every expectation below is a literal written here, not read from the thing it judges: the
catalogue, the envelope schema, the served document and the enum all derive their numbers from
one another elsewhere, so a pin that read them back could not say that one of them moved. The
HTTP status and the retry rule are the ones of the code the refusals replace, because a caller's
retry logic must not change by moving to the new codes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditmanager.api.schemas import models
from auditmanager.shared.errors import ErrorCode

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = json.loads((ROOT / "contracts/domain/v1/error-codes.json").read_text("utf-8"))
ENVELOPE = json.loads((ROOT / "contracts/domain/v1/error-envelope.schema.json").read_text("utf-8"))
CODES_SCHEMA = json.loads((ROOT / "contracts/domain/v1/error-codes.schema.json").read_text("utf-8"))
API = json.loads((ROOT / "contracts/api/v1/openapi.json").read_text("utf-8"))
MIRROR = json.loads((ROOT / "web/openapi/openapi.json").read_text("utf-8"))

#: code -> (HTTP status, retryable, category), the replaced code's status and rule.
NEW_CODES = {
    "version_classification_required": (422, False, "policy"),
    "section_profile_unavailable": (422, False, "dependency"),
}


def test_the_replaced_code_is_the_one_whose_rule_the_new_codes_keep() -> None:
    old = CATALOGUE["codes"]["required_norm_unavailable"]
    assert (old["http"], old["retryable"]) == (422, False)
    for http, retryable, _category in NEW_CODES.values():
        assert (http, retryable) == (old["http"], old["retryable"])


@pytest.mark.parametrize("code", sorted(NEW_CODES))
def test_the_catalogue_entry(code: str) -> None:
    http, retryable, category = NEW_CODES[code]
    entry = CATALOGUE["codes"][code]
    assert (entry["http"], entry["retryable"], entry["category"]) == (http, retryable, category)
    assert entry["category"] in CATALOGUE["categories"]
    assert entry["safe_detail_keys"] == [], "a routing refusal carries no details"
    assert "D-179" in entry["evidence"]
    assert entry["notes"], "the entry says when it is answered and what the old wire was"


@pytest.mark.parametrize("code", sorted(NEW_CODES))
def test_the_enum_carries_the_code_with_the_catalogues_rule(code: str) -> None:
    http, retryable, _category = NEW_CODES[code]
    member = ErrorCode(code)
    assert (member.http_status, member.retryable) == (http, retryable)
    assert models.ErrorCode(code).value == code
    assert member.safe_detail_keys == frozenset()


@pytest.mark.parametrize("code", sorted(NEW_CODES))
def test_the_envelope_schema_admits_the_code_and_pins_its_retry_flag(code: str) -> None:
    assert code in ENVELOPE["properties"]["error_code"]["enum"]
    pins = [
        branch["then"]["properties"]["retryable"]["const"]
        for branch in ENVELOPE["allOf"]
        if branch["if"]["properties"]["error_code"].get("const") == code
    ]
    assert pins == [NEW_CODES[code][1]], f"the envelope must pin retryable for {code} exactly once"
    assert code in CODES_SCHEMA["properties"]["codes"]["required"]


@pytest.mark.parametrize("document", [API, MIRROR], ids=["contract", "web mirror"])
@pytest.mark.parametrize("code", sorted(NEW_CODES))
def test_the_served_document_enumerates_and_declares_the_code(document: dict, code: str) -> None:
    assert code in document["components"]["schemas"]["ErrorCode"]["enum"]
    # startRun's 422 is where a caller meets it; the frontend derives its render subset from
    # the codes this description names in backticks (`web/tests/contract/pc01-error-codes`).
    assert f"`{code}`" in document["components"]["responses"]["RunInputInvalid"]["description"]


def test_the_catalogue_and_the_document_still_agree_on_the_size() -> None:
    assert len(CATALOGUE["codes"]) == 27 == len(API["components"]["schemas"]["ErrorCode"]["enum"])
    # The schema requires the stored vocabulary: the 27 codes less the two nothing stores.
    assert len(CODES_SCHEMA["properties"]["codes"]["required"]) == 25
    assert CODES_SCHEMA["properties"]["codes"]["minProperties"] == 27
    assert CODES_SCHEMA["properties"]["codes"]["maxProperties"] == 27


def test_required_norm_unavailable_no_longer_names_the_two_routing_values() -> None:
    """The reference kinds it still registers are norms, a pinned profile pair and a retrieval set.

    ``analysis_profile`` stays, for the executor's refusal of a pair the deployment does not
    register; ``version_classification`` is gone from the list of values it registers.
    """
    notes = " ".join(CATALOGUE["codes"]["required_norm_unavailable"]["notes"])
    assert "reference_kind analysis_profile" in notes
    assert "version_classification_required" in notes and "section_profile_unavailable" in notes
    assert "version_classification: the version has no persisted" not in notes
