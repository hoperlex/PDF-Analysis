"""The OpenAPI document validates, and agrees with the frozen contracts.

"Validates" is done here with the standard library, deliberately and without a skip.
The runtime lock carries no OpenAPI validator, and adding a root dependency is a
single-owner task rather than a lane decision, so the alternative would be a test
that skips itself wherever the dependency is absent - which is where it matters.

What this asserts, and it is more than a metaschema pass would give: the document's
own structure; that every ``$ref`` resolves; that every enum drawn from a frozen
contract equals that contract; that every identity carries its contract pattern; and
that nothing in the surface leaks an address, a credential or a model payload.

``openapi_metaschema_check.py`` beside this file adds JSON Schema 2020-12 validation
of every schema object under the governance interpreter.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

#: Every capability P2-API-01 enumerates, as the operationId that must implement it,
#: plus the three `R-5` added: P2-API-01's eleven capabilities are what a *client journey*
#: needs, and `W15-RUN` measured in a browser that the journey cannot be resumed without
#: a way to list what it produced. `DEBT_REGISTER.md` D-16.
REQUIRED_OPERATIONS = {
    "createProject",
    "listProjects",
    "uploadDocument",
    "getDocumentVersion",
    "streamDocumentVersionContent",
    "startRun",
    "getRunStatus",
    "listRunFindings",
    "getFinding",
    "appendDecision",
    "listDecisionHistory",
    "exportRunCsv",
    "listDocuments",
    "listVersions",
    "listRuns",
}

WRITE_OPERATIONS = {"createProject", "uploadDocument", "startRun", "appendDecision"}

PAGINATED_OPERATIONS = {
    "listProjects",
    "listRunFindings",
    "listDecisionHistory",
    "listDocuments",
    "listVersions",
    "listRuns",
}


def _walk(node: Any, path: str = "$"):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def _operations(document: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                found[operation["operationId"]] = {**operation, "_path": path, "_method": method}
    return found


def _resolve(document: dict, reference: str) -> Any:
    assert reference.startswith("#/"), f"only local references are allowed: {reference}"
    node: Any = document
    for segment in reference[2:].split("/"):
        segment = segment.replace("~1", "/").replace("~0", "~")
        assert isinstance(node, dict) and segment in node, f"unresolvable: {reference}"
        node = node[segment]
    return node


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_the_document_is_openapi_31(openapi_document: dict) -> None:
    assert openapi_document["openapi"] == "3.1.0"
    assert openapi_document["info"]["title"]
    assert openapi_document["info"]["version"]
    assert openapi_document["servers"]


def test_the_document_is_canonical_json(openapi_document: dict) -> None:
    """A5 regenerates from this file and asserts no diff; it must round-trip."""
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "contracts" / "api" / "v1" / "openapi.json"
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert json.loads(raw) == openapi_document
    assert "\t" not in raw


def test_every_reference_resolves(openapi_document: dict) -> None:
    for path, node in _walk(openapi_document):
        if isinstance(node, dict) and "$ref" in node:
            _resolve(openapi_document, node["$ref"])


def test_no_component_is_unreachable(openapi_document: dict) -> None:
    """An orphaned component is a shape somebody meant to wire up and did not."""
    referenced = {
        node["$ref"]
        for _, node in _walk(openapi_document)
        if isinstance(node, dict) and "$ref" in node
    }
    for section in ("schemas", "parameters", "responses", "headers"):
        for name in openapi_document["components"].get(section, {}):
            reference = f"#/components/{section}/{name}"
            assert reference in referenced, f"{reference} is defined and never used"


def test_operation_ids_are_present_and_unique(openapi_document: dict) -> None:
    seen: list[str] = []
    for item in openapi_document["paths"].values():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                assert "operationId" in operation
                seen.append(operation["operationId"])
    assert len(seen) == len(set(seen))


def test_the_surface_is_exactly_the_declared_capabilities(openapi_document: dict) -> None:
    assert set(_operations(openapi_document)) == REQUIRED_OPERATIONS


def test_no_export_resource_identity_or_polling_exists(openapi_document: dict) -> None:
    """P2-EXP-01: nothing is created, so there is nothing to poll and no export_id."""
    serialized = json.dumps(openapi_document)
    assert "export_id" not in serialized
    assert "exported_at" not in serialized
    for path in openapi_document["paths"]:
        assert not path.startswith("/exports")


def test_every_operation_declares_its_path_parameters(openapi_document: dict) -> None:
    for path, item in openapi_document["paths"].items():
        expected = set(re.findall(r"\{([^}]+)\}", path))
        declared: set[str] = set()
        for parameter in item.get("parameters", []):
            resolved = (
                _resolve(openapi_document, parameter["$ref"])
                if "$ref" in parameter
                else parameter
            )
            if resolved["in"] == "path":
                declared.add(resolved["name"])
        for method, operation in item.items():
            if method not in HTTP_METHODS:
                continue
            operation_declared = set(declared)
            for parameter in operation.get("parameters", []):
                resolved = (
                    _resolve(openapi_document, parameter["$ref"])
                    if "$ref" in parameter
                    else parameter
                )
                if resolved["in"] == "path":
                    operation_declared.add(resolved["name"])
            assert operation_declared == expected, f"{method.upper()} {path}"


def test_every_path_parameter_is_required_and_pattern_bound(openapi_document: dict) -> None:
    for name, parameter in openapi_document["components"]["parameters"].items():
        if parameter["in"] != "path":
            continue
        assert parameter["required"] is True, name
        schema = _resolve(openapi_document, parameter["schema"]["$ref"])
        assert "pattern" in schema, f"{name} accepts any string"
        assert schema["pattern"].startswith("^"), name
        assert schema["pattern"].endswith("$"), name


def test_no_endpoint_addresses_a_resource_by_a_non_identity(openapi_document: dict) -> None:
    """No path keys on a file name, an ordinal, a sheet number or a checksum."""
    for path in openapi_document["paths"]:
        for parameter in re.findall(r"\{([^}]+)\}", path):
            assert parameter.endswith(("_uid", "_id")), (
                f"{path} addresses a resource by {parameter!r}, which is not an identity"
            )


# ---------------------------------------------------------------------------
# Idempotency, correlation and the error envelope
# ---------------------------------------------------------------------------


def test_every_write_requires_an_idempotency_key(openapi_document: dict) -> None:
    for name, operation in _operations(openapi_document).items():
        if name not in WRITE_OPERATIONS:
            continue
        headers = {
            _resolve(openapi_document, parameter["$ref"])["name"]
            if "$ref" in parameter
            else parameter["name"]
            for parameter in operation.get("parameters", [])
        }
        assert "Idempotency-Key" in headers, f"{name} is a write with no idempotency key"


def test_no_read_operation_demands_an_idempotency_key(openapi_document: dict) -> None:
    for name, operation in _operations(openapi_document).items():
        if name in WRITE_OPERATIONS:
            continue
        for parameter in operation.get("parameters", []):
            resolved = (
                _resolve(openapi_document, parameter["$ref"])
                if "$ref" in parameter
                else parameter
            )
            assert resolved["name"] != "Idempotency-Key", f"{name} is a read"


def test_every_response_carries_a_correlation_header(openapi_document: dict) -> None:
    for name, operation in _operations(openapi_document).items():
        for status, response in operation["responses"].items():
            resolved = (
                _resolve(openapi_document, response["$ref"]) if "$ref" in response else response
            )
            assert "X-Correlation-Id" in resolved.get("headers", {}), f"{name} {status}"


def test_every_error_response_is_the_envelope(openapi_document: dict) -> None:
    for name, operation in _operations(openapi_document).items():
        for status, response in operation["responses"].items():
            if status.startswith("2"):
                continue
            resolved = (
                _resolve(openapi_document, response["$ref"]) if "$ref" in response else response
            )
            schema = resolved["content"]["application/json"]["schema"]
            assert schema == {"$ref": "#/components/schemas/ErrorEnvelope"}, (
                f"{name} {status} does not return the error envelope"
            )


def test_every_write_declares_the_idempotency_conflict_response(
    openapi_document: dict,
) -> None:
    for name, operation in _operations(openapi_document).items():
        if name not in WRITE_OPERATIONS:
            continue
        assert "409" in operation["responses"], f"{name} cannot report a key conflict"


def test_every_operation_can_report_not_found_or_validation(openapi_document: dict) -> None:
    for name, operation in _operations(openapi_document).items():
        codes = set(operation["responses"])
        assert codes & {"404", "422", "409"}, f"{name} declares no client-fault response"
        assert "500" in codes, f"{name} cannot report an internal fault"


# ---------------------------------------------------------------------------
# The authorization seam (R-3, D-6)
# ---------------------------------------------------------------------------

#: Written out rather than read from the document under test. A guard that took the
#: scheme's name from the file it is checking would pass on a renamed scheme, which is
#: `OPERATING_CONSTRAINTS.md` section 12's shape and is on record three times.
BEARER_SCHEME = "bearerAuth"

#: Keys that would put an implementation inside the contract. `bearerFormat` names the
#: token format; `flows` and `openIdConnectUrl` name an issuer and a deployment URL;
#: `name` and `in` belong to an apiKey scheme, which carries a secret rather than an
#: identity. The public version replaces the implementation and must not need to touch
#: this document, so none of them may appear.
FORBIDDEN_SCHEME_KEYS = ("bearerFormat", "flows", "openIdConnectUrl", "name", "in")


def _effective_security(document: dict, operation: dict) -> list:
    """What OpenAPI 3.1 says applies to this operation.

    An operation's own `security` overrides the root one, and `security: []` removes the
    requirement entirely. Resolving it here rather than asserting a literal document
    shape means the guard holds however the requirement is expressed -- and catches an
    operation that opts itself out.
    """
    if "security" in operation:
        return operation["security"]
    return document.get("security", [])


def test_the_document_declares_exactly_one_security_scheme(openapi_document: dict) -> None:
    schemes = openapi_document["components"]["securitySchemes"]
    assert list(schemes) == [BEARER_SCHEME]
    scheme = schemes[BEARER_SCHEME]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"


def test_the_scheme_declares_the_seam_and_not_its_implementation(
    openapi_document: dict,
) -> None:
    """No issuer, no flow, no token format, no role or subject vocabulary.

    `T-6`: the alpha satisfies this seam with one static token and the public version
    replaces it with OIDC behind the same dependency. That is only true if nothing here
    describes either of them.
    """
    scheme = openapi_document["components"]["securitySchemes"][BEARER_SCHEME]
    assert set(scheme) == {"type", "scheme", "description"}, sorted(scheme)
    for key in FORBIDDEN_SCHEME_KEYS:
        assert key not in scheme, f"the scheme declares {key}, which is deployment detail"
    rendered = json.dumps(scheme)
    assert "http://" not in rendered and "https://" not in rendered


def test_every_declared_scheme_is_required_somewhere(openapi_document: dict) -> None:
    """The reachability rule `test_no_component_is_unreachable` applies by `$ref`.

    A security scheme is referenced by name instead, so it needs its own guard, in both
    directions: no orphaned scheme, and no requirement naming a scheme that is not
    declared.
    """
    declared = set(openapi_document["components"]["securitySchemes"])
    required: set[str] = set()
    for requirement in openapi_document.get("security", []):
        required |= set(requirement)
    for operation in _operations(openapi_document).values():
        for requirement in operation.get("security", []):
            required |= set(requirement)
    assert required == declared, f"declared={sorted(declared)} required={sorted(required)}"


def test_every_operation_requires_the_bearer_scheme(openapi_document: dict) -> None:
    """All twelve, and not by counting the ones that happen to be listed.

    `security: []` on an operation, or a root requirement containing an empty
    alternative, makes that operation unauthenticated. Both are checked, because both
    are how an operation quietly leaves the authorized surface.
    """
    operations = _operations(openapi_document)
    assert set(operations) == REQUIRED_OPERATIONS
    for name, operation in operations.items():
        effective = _effective_security(openapi_document, operation)
        assert effective, f"{name} requires no credential"
        for alternative in effective:
            assert alternative, f"{name} accepts an unauthenticated alternative"
            assert BEARER_SCHEME in alternative, f"{name} does not require {BEARER_SCHEME}"


def test_every_operation_can_report_401_and_403(openapi_document: dict) -> None:
    """A scheme with no declared refusal leaves a generated client no typed shape."""
    for name, operation in _operations(openapi_document).items():
        responses = operation["responses"]
        assert responses["401"]["$ref"] == "#/components/responses/AuthenticationRequired", name
        assert responses["403"]["$ref"] == "#/components/responses/PermissionDenied", name


def test_the_document_no_longer_says_it_has_no_authentication(
    openapi_document: dict,
) -> None:
    """The prose and the declaration have to agree.

    Until the reseal `info.description` read "this surface deliberately does not have:
    authentication, ...". A document that declares a scheme and denies having one is
    exactly the shape `D-8` records: a sentence repeated until nobody opens the file.
    """
    description = openapi_document["info"]["description"]
    assert "does not have: authentication" not in description
    assert "twenty-code catalog" not in description


def test_the_envelope_schema_mirrors_the_frozen_one(
    openapi_document: dict, error_envelope_schema: dict
) -> None:
    envelope = openapi_document["components"]["schemas"]["ErrorEnvelope"]
    assert set(envelope["required"]) == set(error_envelope_schema["required"])
    assert envelope["additionalProperties"] is False
    assert envelope["properties"]["contract_version"]["const"] == (
        error_envelope_schema["properties"]["contract_version"]["const"]
    )
    for field in ("message", "correlation_id"):
        source = error_envelope_schema["properties"][field]
        target = envelope["properties"][field]
        resolved = (
            _resolve(openapi_document, target["$ref"]) if "$ref" in target else target
        )
        assert resolved.get("maxLength") == source.get("maxLength"), field


def test_the_error_code_enum_equals_the_frozen_catalog(
    openapi_document: dict, error_codes_contract: dict
) -> None:
    declared = openapi_document["components"]["schemas"]["ErrorCode"]["enum"]
    assert set(declared) == set(error_codes_contract["codes"])
    assert len(declared) == len(set(declared)) == 22


# ---------------------------------------------------------------------------
# Vocabulary agreement
# ---------------------------------------------------------------------------


def test_the_run_state_enum_equals_the_audit_run_machine(
    openapi_document: dict, state_machines_contract: dict
) -> None:
    machine = state_machines_contract["machines"]["audit_run"]
    declared = {machine["initial"], *machine["terminal"]}
    for origin, targets in machine["transitions"].items():
        declared.add(origin)
        declared.update(targets)
    exposed = openapi_document["components"]["schemas"]["RunState"]["enum"]
    assert set(exposed) == declared


def test_run_state_never_exposes_succeeded(openapi_document: dict) -> None:
    """C-2: the run's success terminal is `published`."""
    assert "succeeded" not in openapi_document["components"]["schemas"]["RunState"]["enum"]
    assert "published" in openapi_document["components"]["schemas"]["RunState"]["enum"]


def test_the_stage_status_enum_equals_the_stage_result_schema(
    openapi_document: dict, stage_result_schema: dict
) -> None:
    assert set(openapi_document["components"]["schemas"]["StageStatus"]["enum"]) == set(
        stage_result_schema["properties"]["status"]["enum"]
    )


def test_the_stage_id_enum_equals_the_registry(
    openapi_document: dict, stage_registry_contract: dict
) -> None:
    declared = [stage["stage_id"] for stage in stage_registry_contract["stages"]]
    assert openapi_document["components"]["schemas"]["StageId"]["enum"] == declared


def test_the_verdict_enum_is_the_closed_four(openapi_document: dict) -> None:
    assert set(openapi_document["components"]["schemas"]["Verdict"]["enum"]) == {
        "pending",
        "accepted",
        "rejected",
        "needs_manual_review",
    }


def test_identity_schemas_carry_their_contract_pattern(
    openapi_document: dict, identifiers_contract: dict
) -> None:
    template = identifiers_contract["pattern_template"]
    expected = {
        "ProjectUid": "prj",
        "DocumentUid": "doc",
        "VersionUid": "ver",
        "RunId": "run",
        "FindingUid": "fnd",
        "FindingObservationId": "fobs",
        "DecisionId": "dec",
        "AnalysisProfileId": "ap",
        "PromptBundleId": "pb",
        "ModelCallId": "mc",
    }
    for name, prefix in expected.items():
        schema = openapi_document["components"]["schemas"][name]
        assert schema["pattern"] == template.replace("{prefix}", prefix), name


def test_correlation_and_idempotency_carry_their_contract_pattern(
    openapi_document: dict, identifiers_contract: dict
) -> None:
    schemas = openapi_document["components"]["schemas"]
    assert schemas["CorrelationId"]["pattern"] == (
        identifiers_contract["correlation_identifiers"]["correlation_id"]["pattern"]
    )
    assert schemas["IdempotencyKey"]["pattern"] == (
        identifiers_contract["command_keys"]["idempotency_key"]["pattern"]
    )


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


def test_no_schema_property_names_an_address_or_a_secret(openapi_document: dict) -> None:
    banned = {
        "bucket",
        "bucket_name",
        "object_key",
        "s3_key",
        "storage_key",
        "storage_path",
        "file_path",
        "filesystem_path",
        "directory",
        "download_url",
        "presigned_url",
        "credential",
        "password",
        "secret",
        "api_key",
        "token",
        "execution_token",
        "fencing_token",
        "authority_token",
        "prompt",
        "prompt_text",
        "raw_response",
        "response_body",
        "idempotency_key",
    }
    offenders = []
    for name, schema in openapi_document["components"]["schemas"].items():
        for path, node in _walk(schema, name):
            if not path.endswith(".properties"):
                continue
            offenders.extend(f"{path}.{key}" for key in node if key in banned)
    assert offenders == [], f"response shapes leak {offenders}"


def test_the_envelope_forbids_the_catalog_forbidden_detail_keys(
    openapi_document: dict, error_codes_contract: dict
) -> None:
    """A caller must not be able to receive a bucket name in `details`."""
    envelope = openapi_document["components"]["schemas"]["ErrorEnvelope"]
    details = envelope["properties"]["details"]
    assert details["propertyNames"]["pattern"] == "^[a-z][a-z0-9_]{0,63}$"
    assert details["maxProperties"] == 16
    assert details["additionalProperties"]["maxLength"] == 256
    forbidden = set(error_codes_contract["safety"]["forbidden_detail_keys"])
    assert "execution_token" in forbidden and "bucket" in forbidden


def test_the_viewer_streams_bytes_and_is_never_redirected(openapi_document: dict) -> None:
    operation = _operations(openapi_document)["streamDocumentVersionContent"]
    assert "application/pdf" in operation["responses"]["200"]["content"]
    assert "302" not in operation["responses"]
    assert "307" not in operation["responses"]
    assert "Location" not in operation["responses"]["200"].get("headers", {})


def test_the_export_returns_csv_and_refuses_with_a_state_code(
    openapi_document: dict,
) -> None:
    operation = _operations(openapi_document)["exportRunCsv"]
    assert "text/csv" in operation["responses"]["200"]["content"]
    assert "409" in operation["responses"]
    description = operation["description"]
    assert "publishes_result" in description
    assert "state_transition_not_allowed" in description
    assert "partial_result_not_publishable` is never emitted" in description


def test_growing_lists_are_cursor_paginated(openapi_document: dict) -> None:
    for name in PAGINATED_OPERATIONS:
        operation = _operations(openapi_document)[name]
        parameters = {
            _resolve(openapi_document, parameter["$ref"])["name"]
            if "$ref" in parameter
            else parameter["name"]
            for parameter in operation.get("parameters", [])
        }
        assert {"cursor", "limit"} <= parameters, f"{name} is not cursor-paginated"
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        page = _resolve(openapi_document, schema["$ref"])
        assert set(page["required"]) == {"items", "page"}


@pytest.mark.parametrize(
    "schema_name",
    ["Project", "DocumentVersion", "RunStatus", "Finding", "DecisionEvent", "Evidence"],
)
def test_response_shapes_are_closed(openapi_document: dict, schema_name: str) -> None:
    """`additionalProperties: false`, so a field added without a contract change fails."""
    schema = openapi_document["components"]["schemas"][schema_name]
    assert schema["additionalProperties"] is False, schema_name
