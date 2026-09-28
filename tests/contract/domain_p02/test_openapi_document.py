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

import copy
import json
import re
from typing import Any

import pytest

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

#: Every capability P2-API-01 enumerates, as the operationId that must implement it,
#: plus the three `R-5` added: P2-API-01's eleven capabilities are what a *client journey*
#: needs, and `W15-RUN` measured in a browser that the journey cannot be resumed without
#: a way to list what it produced. `DEBT_REGISTER.md` D-16.
#:
#: And `issueToken`, added by `W34-CONTRACT`. It implements no product capability: `R-3`
#: required a bearer credential on every operation and the document described no way to
#: obtain one, so the surface admitted only a caller already holding a credential from
#: somewhere this document does not name. It is the seam's own door and is listed here
#: because this set is the whole surface, not the product part of it.
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
    "issueToken",
    # `W38-KB`, under `R-24`. The decision journal across findings: the knowledge base
    # `R-23` requires reads it, and before it `listDecisionHistory` answered for one
    # finding only, so the only source was a client-side walk over every run.
    "listDecisions",
    # `W39-REVOKE`, under `R-26`. The password change, and with it the only way this
    # surface can take a credential back: the account's credential generation is raised by
    # the same write that stores the new digest. Like `issueToken` it implements no product
    # capability, and it is listed for the same reason -- this set is the whole surface, not
    # the product part of it.
    "changePassword",
    # `W45-BLOCKS`. The block index for one version, keyed by version_uid rather than by
    # run_id because page_geometry_extraction carries no model and no provider reference,
    # so its output is deterministic across every run of a version that reaches it.
    "getVersionBlocks",
    # `W46-SEAL`, `R-44`. One aggregate read serving all four dashboard panels, chosen
    # over three client-side walks because `R-24` was ruled for a listing operation and
    # against a walk.
    "getDashboardSummary",
}

#: The operations a caller reaches while holding no credential. Exactly one, and it is
#: the one that hands a credential out. `UNAUTHENTICATED_OPERATIONS` is a register of
#: *deliberate* exceptions, not a tolerance: anything else that opts itself out of the
#: root requirement is reported by `test_every_operation_requires_the_bearer_scheme`.
UNAUTHENTICATED_OPERATIONS = {"issueToken"}

WRITE_OPERATIONS = {"createProject", "uploadDocument", "startRun", "appendDecision"}

PAGINATED_OPERATIONS = {
    "listProjects",
    "listRunFindings",
    "listDecisionHistory",
    "listDecisions",
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


def _takes_caller_input(document: dict, operation: dict) -> bool:
    """A path parameter, a query parameter, a cookie parameter, a header other than
    ``X-Correlation-Id``, or a request body -- derived from the document itself, never
    from a name list.

    `F-2b` (``docs/program/reviews/W46-JUDGE-A.md`` section 3): before this wave "every
    operation can report a client fault" and "every operation takes caller input" were
    the same set for all nineteen operations, so the old rule -- built on the first
    premise -- could not tell which one it was actually guarding
    (``OPERATING_CONSTRAINTS.md`` section 12: a rule that shares an assumption with its
    subject). ``getDashboardSummary`` is the first operation without input, and deriving
    the answer from the document is what keeps the next one from silently falling under
    the old assumption again.

    `X-7` (``docs/program/reviews/W46-JUDGE-X.md``): OpenAPI 3.1 has a fourth parameter
    location, ``cookie`` (``path``, ``query``, ``header``, ``cookie`` -- the
    specification's own enum for ``in``), and this derivation counted only three of the
    four. A required, malformable cookie parameter is exactly as much caller input as a
    query parameter of the same shape -- the caller controls the bytes either way -- so
    an operation that gains one is still caller input, with no ``X-Correlation-Id``-style
    exemption: nothing in this document declares a cookie today
    (``test_no_operation_takes_a_cookie_parameter_yet`` pins that), so there is no
    existing cookie whose presence this exemption would need to preserve.

    ``operation`` is one of ``_operations()``'s values, which carries ``_path`` but not
    the path item's own shared ``parameters`` -- OpenAPI declares a parameter once on the
    path item when every operation of that path takes it (``X-Correlation-Id`` and every
    ``{..._uid}`` in this document are declared that way; see
    ``test_every_operation_declares_its_path_parameters``, which merges the same two
    lists for the same reason). Skipping the path item here would have called
    ``getDocumentVersion`` input-less -- measured, not assumed, while writing this.
    """
    path_item = document["paths"][operation["_path"]]
    parameters = list(path_item.get("parameters", [])) + list(operation.get("parameters", []))
    for parameter in parameters:
        resolved = (
            _resolve(document, parameter["$ref"]) if "$ref" in parameter else parameter
        )
        if resolved["in"] in ("path", "query", "cookie"):
            return True
        if resolved["in"] == "header" and resolved["name"] != "X-Correlation-Id":
            return True
    return "requestBody" in operation


#: `F-2` (`D-105`'s pin family, see `docs/program/W46-SPEND.md`): the input-less set,
#: pinned as a literal so a second input-less operation is a decision someone makes
#: rather than a drift nobody notices. Moves on a reseal that adds or removes every
#: parameter, header and body an operation takes.
INPUT_LESS_OPERATIONS: frozenset[str] = frozenset({"getDashboardSummary"})


def test_every_operation_that_takes_input_can_report_a_client_fault(
    openapi_document: dict,
) -> None:
    """Restated from `test_every_operation_can_report_not_found_or_validation`, gate red
    #5 on `2ffca8c`. `W46-JUDGE-A`'s ruling (section 3, `F-2b`): the rule was wrong and
    the operation was right, because the rule encoded an incidental fact -- every
    operation took caller input, so far -- as a law, and adding a client-fault response
    to `getDashboardSummary` to satisfy it would be a declared response no request can
    produce: no `404` (it addresses no identity), no `409` (it writes nothing), no `422`
    (it has no input to be malformed).

    **Two-sided**, so the exemption cannot become a hiding place: an operation with no
    caller input must declare **none** of `404`/`409`/`422`, so a stray `422` added to
    `getDashboardSummary` later, with nothing able to produce it, reddens here rather
    than passing unnoticed. `500` stays required for every operation, unchanged from the
    rule this replaces.
    """
    for name, operation in _operations(openapi_document).items():
        _assert_client_fault_rule(openapi_document, name, operation)


def _assert_client_fault_rule(document: dict, name: str, operation: dict) -> None:
    """One operation's half of `test_every_operation_that_takes_input_can_report_a_
    client_fault`, pulled out so a mutation test can run the exact same rule the real
    guard runs, rather than a hand-written approximation of it that could itself drift
    from the guard it is meant to prove is repaired.
    """
    codes = set(operation["responses"])
    assert "500" in codes, f"{name} cannot report an internal fault"
    client_fault = codes & {"404", "409", "422"}
    if _takes_caller_input(document, operation):
        assert client_fault, f"{name} takes caller input and declares no client-fault response"
    else:
        assert not client_fault, (
            f"{name} takes no caller input but declares {sorted(client_fault)} -- "
            "a response no request can produce"
        )


def test_the_input_less_operation_set_is_exactly_the_pinned_one(openapi_document: dict) -> None:
    """The literal pin, checked independently of the rule above: `_takes_caller_input`
    could be internally consistent (every input-less op declares no client fault, every
    input-taking op declares one) while the *membership* of the input-less set drifted
    out from under whoever last read it. This is `D-105`'s fourth-pin shape -- a set
    that is right today and silently wrong on the next operation -- pinned as a literal
    so that drift is a decision, not an accident.
    """
    input_less = {
        name
        for name, operation in _operations(openapi_document).items()
        if not _takes_caller_input(openapi_document, operation)
    }
    assert input_less == INPUT_LESS_OPERATIONS


def test_no_operation_declares_a_cookie_parameter_today(openapi_document: dict) -> None:
    """`X-7`: the premise the ``cookie`` exemption's absence of an exemption relies on.

    ``header`` carries a named exception (``X-Correlation-Id``) because this document
    already declares that header on every operation and it is not caller input.
    ``cookie`` carries no such exception because nothing in the document declares one
    today -- checked here, independently of `_takes_caller_input`, by walking every
    path item's and every operation's own ``parameters`` and resolving every ``$ref``,
    so this pin cannot share `_takes_caller_input`'s own blind spot with the thing it
    is meant to catch a regression in (`OPERATING_CONSTRAINTS.md` section 12). The day
    this document declares a real cookie parameter, this test is the one that goes red
    and forces a decision about whether it is exempt, rather than the exemption being
    invented silently in `_takes_caller_input` to keep this test passing.
    """
    found: list[str] = []
    for path, item in openapi_document["paths"].items():
        for parameter in item.get("parameters", []):
            resolved = (
                _resolve(openapi_document, parameter["$ref"])
                if "$ref" in parameter
                else parameter
            )
            if resolved["in"] == "cookie":
                found.append(f"{path} (path item): {resolved['name']}")
        for method, operation in item.items():
            if method not in HTTP_METHODS:
                continue
            for parameter in operation.get("parameters", []):
                resolved = (
                    _resolve(openapi_document, parameter["$ref"])
                    if "$ref" in parameter
                    else parameter
                )
                if resolved["in"] == "cookie":
                    found.append(f"{operation['operationId']}: {resolved['name']}")
    assert found == [], f"a cookie parameter now exists and needs a decision: {found}"


def test_a_required_cookie_parameter_makes_getdashboardsummary_take_input(
    openapi_document: dict,
) -> None:
    """`X-7`'s own mutation: a required cookie parameter added to `getDashboardSummary`,
    the one operation this document declares as input-less.

    Before this repair, `_takes_caller_input` counted ``path``, ``query`` and a
    ``header`` other than ``X-Correlation-Id`` -- three of OpenAPI 3.1's four parameter
    locations -- so a required, malformable cookie left the operation classified
    input-less. That is wrong in both directions X measured: the two-sided rule then
    required **no** client-fault response for an operation a malformed cookie could
    genuinely fail (silence where a `422` belongs), and once one was added honestly,
    the same blind spot called it a response *no request can produce* and rejected the
    correct declaration.

    This is the repair shown working: a deep copy of the real document (never the
    shared session fixture -- mutating that would poison every other test in this
    session), the exact parameter object X quoted, `_takes_caller_input` now reports
    the operation takes input.
    """
    mutated = copy.deepcopy(openapi_document)
    operation = mutated["paths"]["/dashboard"]["get"]
    operation.setdefault("parameters", []).append(
        {
            "in": "cookie",
            "name": "am_scope",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        }
    )

    operations = _operations(mutated)
    assert _takes_caller_input(mutated, operations["getDashboardSummary"]) is True

    # The real two-sided rule, run against the mutated document: now that the cookie
    # counts, a `getDashboardSummary` that still declares no client-fault response is
    # the defect X's first direction names -- caller input with no way to report it
    # malformed -- and the rule itself, unchanged, is what catches it.
    with pytest.raises(AssertionError, match="takes caller input and declares no client-fault"):
        _assert_client_fault_rule(mutated, "getDashboardSummary", operations["getDashboardSummary"])


def test_a_required_cookie_parameter_with_its_client_fault_response_is_accepted(
    openapi_document: dict,
) -> None:
    """`X-7`'s *"honest repair"* direction: the same cookie, plus the `422` a malformed
    one would need. Before this repair this was refused -- *"takes no caller input but
    declares ['422']"* -- which is the blind spot rejecting the one response a caller
    input parameter is allowed to add. With the cookie counted, this is now the
    ordinary case every other input-taking operation is already in.
    """
    mutated = copy.deepcopy(openapi_document)
    operation = mutated["paths"]["/dashboard"]["get"]
    operation.setdefault("parameters", []).append(
        {
            "in": "cookie",
            "name": "am_scope",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        }
    )
    operation["responses"]["422"] = {
        "description": "validation_failed",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
        },
    }

    operations = _operations(mutated)
    assert _takes_caller_input(mutated, operations["getDashboardSummary"]) is True
    # The real rule, run against the honestly-repaired mutation: no exception.
    _assert_client_fault_rule(mutated, "getDashboardSummary", operations["getDashboardSummary"])


def test_a_cookie_parameter_declared_on_the_path_item_also_counts(
    openapi_document: dict,
) -> None:
    """A mutation of my own, not X's: X's reproduction adds the cookie to the
    *operation's own* ``parameters``. This document also declares parameters at the
    *path-item* level, merged in beside the operation's own
    (`_takes_caller_input`'s own docstring: ``X-Correlation-Id`` and every
    ``{..._uid}`` are declared that way, and skipping that list once already made
    `getDocumentVersion` look input-less by accident). A cookie parameter placed there
    instead of on the operation must count exactly the same way, and nothing in X's own
    reproduction exercises that merge for the ``cookie`` branch specifically.
    """
    mutated = copy.deepcopy(openapi_document)
    path_item = mutated["paths"]["/dashboard"]
    path_item.setdefault("parameters", []).append(
        {
            "in": "cookie",
            "name": "am_scope",
            "required": True,
            "schema": {"type": "string", "minLength": 1},
        }
    )
    assert path_item["get"]["parameters"] == [{"$ref": "#/components/parameters/CorrelationId"}], (
        "the mutation must land on the path item, not the operation's own parameters"
    )

    operations = _operations(mutated)
    assert _takes_caller_input(mutated, operations["getDashboardSummary"]) is True
    with pytest.raises(AssertionError, match="takes caller input and declares no client-fault"):
        _assert_client_fault_rule(mutated, "getDashboardSummary", operations["getDashboardSummary"])


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
    """All of them but the registered exception, and not by counting the listed ones.

    `security: []` on an operation, or a root requirement containing an empty
    alternative, makes that operation unauthenticated. Both are checked, because both
    are how an operation quietly leaves the authorized surface.

    `W34-CONTRACT` added the one operation that is *supposed* to be reachable without a
    credential, since it is what a caller with none uses to obtain one. The exception is
    a register of names, so the guard reports any **other** operation that opts itself
    out instead of widening to "whatever is unauthenticated today".
    """
    operations = _operations(openapi_document)
    assert set(operations) == REQUIRED_OPERATIONS
    opened: set[str] = set()
    for name, operation in operations.items():
        effective = _effective_security(openapi_document, operation)
        if not effective:
            opened.add(name)
            continue
        for alternative in effective:
            if not alternative:
                opened.add(name)
                continue
            assert BEARER_SCHEME in alternative, f"{name} does not require {BEARER_SCHEME}"
    assert opened == UNAUTHENTICATED_OPERATIONS, (
        "the set of operations reachable with no credential is not the registered one: "
        f"opened={sorted(opened)} registered={sorted(UNAUTHENTICATED_OPERATIONS)}"
    )


def test_the_unauthenticated_operation_is_the_one_that_hands_out_a_credential(
    openapi_document: dict,
) -> None:
    """The register is only worth something if what it admits is what it says it admits.

    A name in `UNAUTHENTICATED_OPERATIONS` excuses an operation from the requirement the
    whole surface is built on, so this pins what that one operation actually is: it takes
    a credential and returns one, and it is the only path in the document that does.
    """
    operations = _operations(openapi_document)
    for name in UNAUTHENTICATED_OPERATIONS:
        operation = operations[name]
        assert operation["_method"] == "post", name
        body = _resolve(
            openapi_document,
            operation["requestBody"]["content"]["application/json"]["schema"]["$ref"],
        )
        assert set(body["required"]) == {"login", "password"}, name
        success = _resolve(
            openapi_document,
            operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        )
        assert set(success["required"]) == {"token", "expires_in"}, name
        # `T-6`: the document describes the exchange and never the credential. A format,
        # an issuer or a flow would be a promise the deployment has to keep for ever.
        assert "bearerFormat" not in openapi_document["components"]["securitySchemes"][
            BEARER_SCHEME
        ], "the token format is back in the document"
        assert set(success["properties"]["token"]) <= {"type", "description", "minLength"}, (
            "the token schema constrains its own structure, which pins the credential "
            "format the scheme deliberately leaves open"
        )


def test_every_operation_can_report_401_and_403(openapi_document: dict) -> None:
    """A scheme with no declared refusal leaves a generated client no typed shape.

    `W34-CONTRACT`: the 403 is `permission_denied`, which the response component defines
    as *"the authenticated subject is not permitted"*. The credential exchange has no
    authenticated subject -- it is the operation that produces one -- so it declares the
    401 and must **not** declare a 403, and that is asserted rather than skipped.
    """
    for name, operation in _operations(openapi_document).items():
        responses = operation["responses"]
        assert responses["401"]["$ref"] == "#/components/responses/AuthenticationRequired", name
        if name in UNAUTHENTICATED_OPERATIONS:
            assert "403" not in responses, (
                f"{name} presents no credential, so it has no subject a 403 could deny"
            )
        else:
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


#: The only two places a banned property name is the correct name, each as an exact
#: `Schema.properties.key` location and never as a bare name. `W34-CONTRACT`: the
#: credential exchange takes a password and returns a token, and a schema that could not
#: spell either could not describe the operation at all. Registered this way, `password`
#: on any other schema is still a leak -- which is the whole point of the ban -- and
#: `test_the_admitted_secret_properties_are_real_and_exhaustive` proves each entry still
#: names something, so a rename cannot leave a dead exemption behind.
ADMITTED_SECRET_PROPERTIES = frozenset(
    {
        "IssueTokenRequest.properties.password",
        "IssueTokenResponse.properties.token",
    }
)


def _secret_property_offenders(document: dict) -> list[str]:
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
    for name, schema in document["components"]["schemas"].items():
        for path, node in _walk(schema, name):
            if not path.endswith(".properties"):
                continue
            offenders.extend(f"{path}.{key}" for key in node if key in banned)
    return offenders


def test_no_schema_property_names_an_address_or_a_secret(openapi_document: dict) -> None:
    offenders = [
        found
        for found in _secret_property_offenders(openapi_document)
        if found not in ADMITTED_SECRET_PROPERTIES
    ]
    assert offenders == [], f"response shapes leak {offenders}"


def test_the_admitted_secret_properties_are_real_and_exhaustive(
    openapi_document: dict,
) -> None:
    """Every registered exception still names a property, and nothing more is excused.

    An exemption for a property that no longer exists is an exemption nobody is reading,
    and the next schema to carry that name inherits it silently.
    """
    found = set(_secret_property_offenders(openapi_document))
    assert ADMITTED_SECRET_PROPERTIES <= found, sorted(ADMITTED_SECRET_PROPERTIES - found)
    assert found == ADMITTED_SECRET_PROPERTIES, sorted(found - ADMITTED_SECRET_PROPERTIES)


def test_the_secret_property_detector_would_report_a_real_leak(
    openapi_document: dict,
) -> None:
    """The exemption is a filter over a detector that still works. Shown, not assumed."""
    import copy

    planted = copy.deepcopy(openapi_document)
    planted["components"]["schemas"]["Project"]["properties"]["password"] = {"type": "string"}
    planted["components"]["schemas"]["IssueTokenResponse"]["properties"]["object_key"] = {
        "type": "string"
    }
    offenders = [
        found
        for found in _secret_property_offenders(planted)
        if found not in ADMITTED_SECRET_PROPERTIES
    ]
    assert sorted(offenders) == [
        "IssueTokenResponse.properties.object_key",
        "Project.properties.password",
    ], offenders


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
