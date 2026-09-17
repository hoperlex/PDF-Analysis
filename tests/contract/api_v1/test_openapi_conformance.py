"""The conformance gate, and the proof it can fail.

`W13-CONF`, stage 3 of wave 13. The comparison engine, and the enumerated declaration of
every normalization it applies, is `openapi_conformance.py` beside this file; read it
first. This file is the part that has to be true: for **every** declared normalization,
two tests - one showing the difference it erases really is invisible, one showing a real
semantic change still survives it and is reported with its location.

`ALPHA_ROADMAP.md` §4, wave 13, stage 3: *"Each normalization is a place a real difference
can hide, so each one gets a planted difference proving the comparison still fails. A
conformance test that has never been shown to fail is the most expensive kind of green in
this programme's history."*

--------------------------------------------------------------------------------------
HOW THE PLANTED DIFFERENCES WORK, AND WHY THEY ARE NOT A SELF-COMPARISON
--------------------------------------------------------------------------------------

`fastapi_flavoured()` below re-spells the frozen contract the way FastAPI would: it inlines
every component reference, hoists path-item parameters onto the operations and reverses
them, adds a Pydantic `title` to every schema and property, rewrites `oneOf` nullables as
`anyOf` with the null branch first, puts a `type` beside every `const`, drops the
`examples`, replaces all the prose and re-serializes with a different key order. Nothing
about the API surface changes. `test_the_fastapi_flavour_is_invisible` asserts the
comparison reports **nothing** against it - which is what proves the normalization does the
job it claims, without needing stage 2's application to exist.

Every plant is then applied **on top of that flavoured copy**, so each one is shown to
survive normalization rather than merely to differ from the pristine document.

`OPERATING_CONSTRAINTS.md` §12: *"never build an expectation, or an input, out of the thing
under test."* What is under test here is the comparison, not the contract. Its expectations
are literals in this file: the seven normalization identifiers, the twelve
`(method, path, operationId)` triples, the forty-three schema names, the version string,
and the exact dotted location each plant must be reported at. The contract is read from
disk as an **authority**, from a path anchored on this file, which §12 names as the
opposite case and which the `tests/integration/exports/test_frozen_column_list.py` guard
resolves the same way.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Callable

import pytest

_HERE = Path(__file__).resolve().parent
_REPOSITORY_ROOT = _HERE.parents[2]

#: The frozen document is the authority. It is read from disk on every run rather than
#: cached at import: `W13-SEAL` reseals it during this same wave, adding `securitySchemes`
#: and the operations' `security`, and a gate that compared what the file said when the
#: session started would be comparing against a document that no longer exists.
CONTRACT_PATH = _REPOSITORY_ROOT / "contracts" / "api" / "v1" / "openapi.json"


def _load_engine():
    """Import the comparison engine by path.

    `pyproject.toml` sets `--import-mode=importlib` and `pythonpath = ["src"]`, so a test
    module cannot import a sibling by bare name and is explicitly forbidden from reaching
    for a `sys.path` hack to get around it. The path is anchored on `__file__`, so a
    mutation copy of the tree loads that copy's engine and not this one's.
    """
    spec = importlib.util.spec_from_file_location(
        "w13conf_openapi_conformance", _HERE / "openapi_conformance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conformance = _load_engine()
differences = conformance.differences
surface = conformance.surface


# =======================================================================================
# The literals. None of these is derived from the document or from the engine.
# =======================================================================================

#: `ALPHA_ROADMAP.md` §3 `T-1` and the measurement in the `W13-CONF` brief.
FROZEN_OPENAPI_VERSION = "3.1.0"
FROZEN_OPERATION_COUNT = 12
FROZEN_SCHEMA_COUNT = 43
FROZEN_SERVER_URL = "/api/v1"

#: The twelve operations, written out. Deliberately not derived from the document: an
#: operation that disappears from the contract has to fail *here*, not silently reduce the
#: size of the thing both sides are compared through.
FROZEN_OPERATIONS: tuple[tuple[str, str, str], ...] = (
    ("POST", "/projects", "createProject"),
    ("GET", "/projects", "listProjects"),
    ("POST", "/projects/{project_uid}/documents", "uploadDocument"),
    ("GET", "/versions/{version_uid}", "getDocumentVersion"),
    ("GET", "/versions/{version_uid}/content", "streamDocumentVersionContent"),
    ("POST", "/runs", "startRun"),
    ("GET", "/runs/{run_id}", "getRunStatus"),
    ("GET", "/runs/{run_id}/findings", "listRunFindings"),
    ("GET", "/findings/{finding_uid}", "getFinding"),
    ("POST", "/findings/{finding_uid}/decisions", "appendDecision"),
    ("GET", "/findings/{finding_uid}/decisions", "listDecisionHistory"),
    ("GET", "/runs/{run_id}/export.csv", "exportRunCsv"),
)

#: The forty-three `components.schemas` keys, written out. These are the names the
#: Pydantic models must carry (`ALPHA_ROADMAP.md` §4, stage 2: *"named exactly as the
#: contract's `components.schemas` keys"*). If FastAPI splits a model into `X-Input` and
#: `X-Output`, this set changes and the gate fails - which is the correct outcome. The fix
#: belongs in the application (`separate_input_output_schemas=False`), never here.
FROZEN_SCHEMA_NAMES: frozenset[str] = frozenset(
    {
        "AnalysisProfileId",
        "AppendDecisionRequest",
        "AppendDecisionResponse",
        "CorrelationId",
        "CreateProjectRequest",
        "Cursor",
        "DecisionEvent",
        "DecisionEventPage",
        "DecisionEventType",
        "DecisionId",
        "DocumentUid",
        "DocumentVersion",
        "ErrorCode",
        "ErrorEnvelope",
        "Evidence",
        "Finding",
        "FindingCategory",
        "FindingDetail",
        "FindingObservation",
        "FindingObservationId",
        "FindingPage",
        "FindingUid",
        "IdempotencyKey",
        "InputManifestEntry",
        "ModelCallId",
        "ObservationProvenance",
        "PageInfo",
        "Project",
        "ProjectPage",
        "ProjectUid",
        "PromptBundleId",
        "ProviderMode",
        "RunId",
        "RunState",
        "RunStatus",
        "Sha256",
        "StageId",
        "StageState",
        "StageStatus",
        "StartRunRequest",
        "UploadDocumentRequest",
        "Verdict",
        "VersionUid",
    }
)

#: The declared normalization, by identifier. Pinned here so that a normalization added to
#: the engine without a planted difference proving it still fails is itself a failure.
DECLARED_NORMALIZATIONS: tuple[str, ...] = ("N1", "N2", "N3", "N4", "N5", "N6", "N7")


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    """The frozen document, re-read from disk. The authority, never modified."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


# =======================================================================================
# Part 1 - the frozen document's own side, pinned
# =======================================================================================


class TestTheFrozenDocument:
    """What the contract must still contain, in literals. Nothing here reads the app."""

    def test_the_contract_file_exists_where_the_gate_looks_for_it(self) -> None:
        assert CONTRACT_PATH.is_file(), (
            f"{CONTRACT_PATH} is missing. The frozen contract is this gate's authority; "
            "without it there is nothing to conform to and the gate must not pass."
        )

    def test_declares_openapi_3_1_0(self, contract: dict[str, Any]) -> None:
        assert contract["openapi"] == FROZEN_OPENAPI_VERSION

    def test_declares_exactly_twelve_operations(self, contract: dict[str, Any]) -> None:
        index = conformance.operation_index(contract)
        assert len(index) == FROZEN_OPERATION_COUNT
        assert index == {
            (method, path): operation_id for method, path, operation_id in FROZEN_OPERATIONS
        }

    def test_declares_exactly_the_forty_three_schemas(self, contract: dict[str, Any]) -> None:
        names = set(contract["components"]["schemas"])
        assert len(names) == FROZEN_SCHEMA_COUNT
        assert names == set(FROZEN_SCHEMA_NAMES), {
            "absent from the contract": sorted(FROZEN_SCHEMA_NAMES - names),
            "not pinned here": sorted(names - FROZEN_SCHEMA_NAMES),
        }

    def test_serves_the_version_prefixed_base_path(self, contract: dict[str, Any]) -> None:
        assert [server["url"] for server in contract["servers"]] == [FROZEN_SERVER_URL]

    def test_every_operation_answers_with_a_correlation_id_header(
        self, contract: dict[str, Any]
    ) -> None:
        """Every response of every operation, success or failure, carries it.

        Written out because it is the one response header the whole surface shares, and a
        generated document that dropped it from a single status code would otherwise be
        one line in a large report.
        """
        reduced = surface(contract)
        missing = [
            f"{method.upper()} {path} {code}"
            for path, operations in reduced["paths"].items()
            for method, operation in operations.items()
            for code, response in operation["responses"].items()
            if "X-Correlation-Id" not in response["headers"]
        ]
        assert missing == []

    def test_the_surface_reduces_to_the_twelve_operations(self, contract: dict[str, Any]) -> None:
        reduced = surface(contract)
        seen = {
            (method.upper(), path)
            for path, operations in reduced["paths"].items()
            for method in operations
        }
        assert seen == {(method, path) for method, path, _ in FROZEN_OPERATIONS}
        assert set(reduced["schemas"]) == set(FROZEN_SCHEMA_NAMES)


# =======================================================================================
# Part 2 - the comparison itself
# =======================================================================================


class TestTheComparison:
    def test_a_document_conforms_to_itself(self, contract: dict[str, Any]) -> None:
        assert differences(surface(contract), surface(contract)) == []

    def test_the_normalizer_never_mutates_its_argument(self, contract: dict[str, Any]) -> None:
        """A planted-difference suite mutates copies; a normalizer that edited in place
        would corrupt every case after the first and the greens would mean nothing."""
        before = json.dumps(contract, sort_keys=True)
        surface(contract)
        assert json.dumps(contract, sort_keys=True) == before

    def test_a_difference_names_what_and_where(self, contract: dict[str, Any]) -> None:
        mutated = copy.deepcopy(contract)
        mutated["paths"]["/runs/{run_id}/export.csv"]["get"]["responses"]["200"]["headers"].pop(
            "Content-Disposition"
        )
        report = differences(surface(contract), surface(mutated))
        assert len(report) == 1
        line = report[0]
        assert line.startswith(
            "paths./runs/{run_id}/export.csv.get.responses.200.headers.Content-Disposition:"
        )
        assert "missing from the generated document" in line

    def test_an_empty_report_is_not_the_only_thing_it_can_produce(
        self, contract: dict[str, Any]
    ) -> None:
        """The vacuity check. A comparison that returned `[]` unconditionally would pass
        every test above; it cannot pass this one."""
        assert differences({"a": 1}, {"a": 2}) != []
        assert differences({"a": 1}, {}) != []
        assert differences({}, {"a": 1}) != []
        assert differences([1, 2], [1, 2, 3]) != []

    def test_a_true_is_not_a_one(self) -> None:
        """`True == 1` in Python and not in JSON. A required flag that became the integer
        one is a difference, not a match."""
        assert differences({"required": True}, {"required": 1}) != []

    def test_every_declared_normalization_has_a_planted_difference(self) -> None:
        """The guard on the declaration itself.

        The engine's docstring enumerates the normalization; this file must carry a test
        class for each entry. Adding `N8` to the engine without proving the comparison
        still fails through it fails here.
        """
        declared = set(re.findall(r"^`(N\d+) - ", conformance.__doc__ or "", re.MULTILINE))
        assert declared == set(DECLARED_NORMALIZATIONS), {
            "declared in the engine": sorted(declared),
            "pinned in this file": sorted(DECLARED_NORMALIZATIONS),
        }
        proven = {
            name[len("Test") : len("Test") + 2]
            for name in globals()
            if name.startswith("TestN") and name[len("Test") : len("Test") + 2] in declared
        }
        assert proven == set(DECLARED_NORMALIZATIONS), {
            "declared but never shown able to fail": sorted(declared - proven)
        }


# =======================================================================================
# The FastAPI flavour - the generated document's spelling, without the app
# =======================================================================================


def fastapi_flavoured(document: dict[str, Any]) -> dict[str, Any]:
    """Re-spell a document the way FastAPI would, changing nothing a caller can observe.

    Each step corresponds to a declared normalization, so a comparison that reports
    anything against the result is a normalization that does not work.
    """
    document = copy.deepcopy(document)

    # N1 - FastAPI has no reusable parameter, response or header object.
    document = conformance._resolve_component_refs(document, document)
    for section in conformance.RESOLVED_COMPONENT_SECTIONS:
        document.get("components", {}).pop(section, None)

    for path_item in document["paths"].values():
        shared = path_item.pop("parameters", [])  # N2 - hoisted onto the operations
        for method in conformance.HTTP_METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            # The effective set, not a concatenation: a FastAPI signature cannot declare
            # the same `(name, in)` twice, so an operation that overrode a path-item
            # parameter would reach the generated document as the override alone.
            merged: dict[str, Any] = {}
            for parameter in [*shared, *operation.get("parameters", [])]:
                merged[f"{parameter.get('in')}:{parameter.get('name')}"] = parameter
            # N3 - and in the reverse order, because a signature is not an editorial list.
            operation["parameters"] = list(reversed(list(merged.values())))
            operation["description"] = "Generated from the handler docstring."
            operation.pop("summary", None)

    document["components"]["schemas"] = {
        name: _pydantic_flavoured(schema, name)
        for name, schema in document["components"]["schemas"].items()
    }
    for path_item in document["paths"].values():
        for method in conformance.HTTP_METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            for parameter in operation["parameters"]:
                if "schema" in parameter:
                    parameter["schema"] = _pydantic_flavoured(parameter["schema"], None)
            for response in operation["responses"].values():
                for header in response.get("headers", {}).values():
                    if "schema" in header:
                        header["schema"] = _pydantic_flavoured(header["schema"], None)

    # Prose and metadata the gate does not compare, moved so that is on the record.
    document["info"] = {"title": "AuditManager", "version": "0.0.0-generated"}
    document["tags"] = [
        {"name": tag["name"], "description": "Generated tag prose."}
        for tag in reversed(document.get("tags", []))
    ]
    document["servers"] = [
        {"url": server["url"], "description": "Generated server prose."}
        for server in document.get("servers", [])
    ]

    # Key order churn, the way a different serializer would produce it.
    return json.loads(json.dumps(document, sort_keys=True))


def _pydantic_flavoured(schema: Any, title: str | None) -> Any:
    """`N3` to `N6` in reverse: what Pydantic writes for the same meaning."""
    if isinstance(schema, list):
        return [_pydantic_flavoured(item, None) for item in schema]
    if isinstance(schema, bool) or not isinstance(schema, dict):
        return schema

    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "examples":
            continue  # N4 - Pydantic does not carry the contract's examples
        if key == "oneOf":
            # Pydantic writes every union as `anyOf`, the optional case included.
            out["anyOf"] = [_pydantic_flavoured(branch, None) for branch in value]
        elif key in conformance._SCHEMA_VALUED or key == "additionalProperties":
            out[key] = (
                _pydantic_flavoured(value, None) if isinstance(value, (dict, list, bool)) else value
            )
        elif key in conformance._SCHEMA_LIST_VALUED:
            out[key] = [_pydantic_flavoured(branch, None) for branch in value]
        elif key in conformance._SCHEMA_MAP_VALUED:
            out[key] = {
                name: _pydantic_flavoured(sub, name.replace("_", " ").title())
                for name, sub in value.items()
            }
        elif key == "required" and isinstance(value, list):
            out[key] = list(reversed(value))  # N3 - declaration order, not editorial order
        else:
            out[key] = value

    # N5 - the null branch first, which is neither side's canonical form.
    def _is_null(branch: Any) -> bool:
        # The title this function adds is not part of what makes a branch the null branch.
        return isinstance(branch, dict) and branch.get("type") == "null" and set(branch) <= {
            "type",
            "title",
        }

    branches = out.get("anyOf")
    if isinstance(branches, list) and len(branches) == 2:
        nulls = [b for b in branches if _is_null(b)]
        others = [b for b in branches if not _is_null(b)]
        if len(nulls) == 1 and len(others) == 1:
            out["anyOf"] = [nulls[0], others[0]]

    # N6 - the type of the literal, beside the literal.
    if "const" in out and "type" not in out:
        out["type"] = conformance._json_type(out["const"])

    # N4 - a title on everything.
    if title is not None:
        out["title"] = title
    elif "$ref" not in out:
        out.setdefault("title", "Generated")

    out.pop("description", None)  # N4
    return out


def resealed(document: dict[str, Any]) -> dict[str, Any]:
    """The contract as `W13-SEAL` will leave it: a scheme, and `security` per operation.

    `T-6` and stage 0b. Built here so the comparison is shown to handle a contract that
    carries security on all twelve operations **before** the reseal lands, rather than
    discovering at merge time that it does not.
    """
    document = copy.deepcopy(document)
    document.setdefault("components", {})["securitySchemes"] = {
        "bearerAuth": {"type": "http", "scheme": "bearer", "description": "The alpha's token."}
    }
    for path_item in document["paths"].values():
        for method in conformance.HTTP_METHODS:
            operation = path_item.get(method)
            if operation is not None:
                operation["security"] = [{"bearerAuth": []}]
    return document


def plant(document: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Apply a deliberate difference to a copy. The argument is never touched."""
    mutated = copy.deepcopy(document)
    mutate(mutated)
    return mutated


def report_for(contract: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> list[str]:
    """Plant a difference, re-spell the result the way FastAPI would, and compare.

    The flavour is applied **after** the plant, so every case below is a difference that
    has been through the entire declared normalization and come out the other side. A
    plant that a normalization erased would show up here as an empty report, and
    `assert_reported_at` fails on an empty report.
    """
    return differences(surface(contract), surface(fastapi_flavoured(plant(contract, mutate))))


def assert_reported_at(report: list[str], location: str) -> str:
    __tracebackhide__ = True
    matches = [line for line in report if line.startswith(f"{location}:")]
    assert matches, (
        f"the comparison did not report a difference at `{location}`. "
        f"It reported {len(report)} difference(s): " + json.dumps(report[:10], indent=2)
    )
    return matches[0]


def assert_silent(report: list[str]) -> None:
    __tracebackhide__ = True
    assert report == [], (
        "the comparison reported a difference where the normalization claims there is "
        "none: " + json.dumps(report[:10], indent=2)
    )


class TestTheFlavourItself:
    def test_the_fastapi_flavour_is_invisible(self, contract: dict[str, Any]) -> None:
        """The whole normalization, end to end, against a document re-spelled the way
        FastAPI spells things. Nothing about the API surface changed, so nothing is
        reported."""
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(contract))))

    def test_the_flavour_really_did_change_the_bytes(self, contract: dict[str, Any]) -> None:
        """Otherwise the test above proves only that a document equals itself."""
        flavoured = fastapi_flavoured(contract)
        assert json.dumps(flavoured, sort_keys=True) != json.dumps(contract, sort_keys=True)
        assert "parameters" not in flavoured["components"]
        assert "responses" not in flavoured["components"]
        assert "headers" not in flavoured["components"]
        assert "title" in flavoured["components"]["schemas"]["Project"]
        assert "oneOf" not in json.dumps(flavoured["components"]["schemas"]["PageInfo"])
        assert flavoured["components"]["schemas"]["DocumentVersion"]["properties"]["media_type"][
            "type"
        ] == "string"


# =======================================================================================
# Part 3 - the planted differences, one pair per declared normalization
# =======================================================================================


class TestN1ComponentReferenceResolution:
    """`N1`: a `$ref` into components.parameters/responses/headers is replaced by its
    target. The component *key* is erased; what it resolves to is not."""

    def test_component_key_rename_is_invisible(self, contract: dict[str, Any]) -> None:
        # The rename has to happen before the flavour inlines the references, so it is
        # done on a copy of the pristine document and flavoured afterwards.
        renamed = copy.deepcopy(contract)
        target = renamed["components"]["responses"].pop("NotFound")
        renamed["components"]["responses"]["ResourceAbsent"] = target
        as_text = json.dumps(renamed).replace(
            "#/components/responses/NotFound", "#/components/responses/ResourceAbsent"
        )
        renamed = json.loads(as_text)
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(renamed))))

    def test_changed_component_target_is_caught(self, contract: dict[str, Any]) -> None:
        """The reason the key can be erased and the target cannot."""
        report = report_for(
            contract,
            lambda document: document["components"]["responses"]["NotFound"]["content"][
                "application/json"
            ].__setitem__("schema", {"$ref": "#/components/schemas/Finding"}),
        )
        line = assert_reported_at(
            report,
            "paths./findings/{finding_uid}.get.responses.404.content.application/json.schema.$ref",
        )
        assert "ErrorEnvelope" in line and "Finding" in line
        # Every operation that referenced it, not just one.
        assert len(report) == 10, report

    def test_a_dangling_reference_is_refused_rather_than_ignored(
        self, contract: dict[str, Any]
    ) -> None:
        broken = copy.deepcopy(contract)
        broken["paths"]["/projects"]["post"]["responses"]["404"] = {
            "$ref": "#/components/responses/NoSuchThing"
        }
        with pytest.raises(ValueError, match="dangling reference"):
            surface(broken)


class TestN2PathItemParameterMerge:
    """`N2`: a path-item parameter applies to every operation of that item."""

    def test_parameter_moved_to_operation_level_is_invisible(
        self, contract: dict[str, Any]
    ) -> None:
        moved = copy.deepcopy(contract)
        item = moved["paths"]["/runs/{run_id}/export.csv"]
        shared = item.pop("parameters")
        item["get"]["parameters"] = [*shared, *item["get"]["parameters"]]
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(moved))))

    def test_dropped_path_level_parameter_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}/export.csv"].pop("parameters"),
        )
        assert_reported_at(
            report, "paths./runs/{run_id}/export.csv.get.parameters.path:run_id"
        )

    def test_an_operation_level_override_wins_and_is_compared(
        self, contract: dict[str, Any]
    ) -> None:
        """The override rule is not a hole: an operation that redeclares the path
        parameter with a different schema is reported, not silently merged away."""
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}/export.csv"]["get"][
                "parameters"
            ].append({"name": "run_id", "in": "path", "required": True, "schema": {"type": "integer"}}),
        )
        assert_reported_at(
            report, "paths./runs/{run_id}/export.csv.get.parameters.path:run_id.schema.$ref"
        )


class TestN3OrderingAndSetValuedKeywords:
    """`N3`: parameter and header order, and the order of `required` and `enum`."""

    def test_reordered_parameters_are_invisible(self, contract: dict[str, Any]) -> None:
        reordered = copy.deepcopy(contract)
        item = reordered["paths"]["/projects/{project_uid}/documents"]["post"]
        item["parameters"] = list(reversed(item["parameters"]))
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(reordered))))

    def test_reordered_required_list_is_invisible(self, contract: dict[str, Any]) -> None:
        reordered = copy.deepcopy(contract)
        schema = reordered["components"]["schemas"]["DocumentVersion"]
        schema["required"] = sorted(schema["required"])
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(reordered))))

    def test_changed_required_list_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["DocumentVersion"][
                "required"
            ].remove("sha256"),
        )
        line = assert_reported_at(report, "schemas.DocumentVersion.required")
        assert "10 entries" in line and "9 entries" in line
        assert "sha256" not in line.split(" - generated ")[-1]

    def test_changed_enum_member_is_caught(self, contract: dict[str, Any]) -> None:
        """`published` to `succeeded` - the rename the frontend guard also probes for, on
        the Python side of the same contract."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["RunState"].__setitem__(
                "enum",
                [
                    "succeeded" if state == "published" else state
                    for state in document["components"]["schemas"]["RunState"]["enum"]
                ],
            ),
        )
        assert any(line.startswith("schemas.RunState.enum") for line in report), report

    def test_a_dropped_parameter_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects/{project_uid}/documents"]["post"][
                "parameters"
            ].__delitem__(0),
        )
        assert_reported_at(
            report,
            "paths./projects/{project_uid}/documents.post.parameters.header:Idempotency-Key",
        )

    def test_a_relaxed_parameter_requirement_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["parameters"]["IdempotencyKey"].__setitem__(
                "required", False
            ),
        )
        line = assert_reported_at(
            report,
            "paths./projects/{project_uid}/documents.post.parameters."
            "header:Idempotency-Key.required",
        )
        assert "true" in line and "false" in line


class TestN4AnnotationKeywords:
    """`N4`: prose is dropped. This is the one place the gate deliberately cannot see."""

    def test_changed_description_is_deliberately_invisible(
        self, contract: dict[str, Any]
    ) -> None:
        """The blind spot, recorded as a test rather than as a promise.

        A rule that lives only in a `description` is outside this gate. The frozen
        document stays the authority for prose and
        `web/tests/contract/openapi-drift.contract.test.ts` pins its bytes; nothing here
        should be read as covering it.
        """
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["ProjectUid"].__setitem__(
                "description", "Something else entirely."
            ),
        )
        assert_silent(report)

    def test_a_property_named_description_is_not_mistaken_for_prose(self) -> None:
        """The walker goes by JSON Schema keyword position, not by key spelling."""
        schema = {
            "type": "object",
            "description": "prose",
            "properties": {
                "description": {"type": "string", "description": "prose", "maxLength": 40},
                "title": {"type": "string", "title": "prose"},
            },
        }
        normalized = conformance.normalize_schema(schema)
        assert "description" not in normalized
        assert set(normalized["properties"]) == {"description", "title"}
        assert normalized["properties"]["description"] == {"type": "string", "maxLength": 40}

    def test_changed_pattern_is_caught(self, contract: dict[str, Any]) -> None:
        """The boundary: prose moves freely, constraints do not."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["ProjectUid"].__setitem__(
                "pattern", "^prj_[0-9a-z]{26}$"
            ),
        )
        line = assert_reported_at(report, "schemas.ProjectUid.pattern")
        assert "0-9A-HJKMNP-TV-Z" in line

    def test_a_dropped_length_bound_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["ErrorEnvelope"]["properties"][
                "message"
            ].pop("maxLength"),
        )
        assert_reported_at(report, "schemas.ErrorEnvelope.properties.message.maxLength")

    def test_a_relaxed_closure_is_caught(self, contract: dict[str, Any]) -> None:
        """`additionalProperties: false` is the contract's refusal of unknown fields and
        stage 2's `extra="forbid"`. Losing it is a semantic change, not a spelling."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["ErrorEnvelope"].__setitem__(
                "additionalProperties", True
            ),
        )
        line = assert_reported_at(report, "schemas.ErrorEnvelope.additionalProperties")
        assert "false" in line and "true" in line


class TestN5TheNullableUnion:
    """`N5`: `oneOf`/`anyOf` of exactly two branches, one of them exactly `{"type": "null"}`."""

    def test_oneof_to_anyof_nullable_is_invisible(self, contract: dict[str, Any]) -> None:
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(contract))))
        # And directly, without the rest of the flavour in the way:
        assert conformance.normalize_schema(
            {"oneOf": [{"$ref": "#/components/schemas/Cursor"}, {"type": "null"}]}
        ) == conformance.normalize_schema(
            {"anyOf": [{"type": "null"}, {"$ref": "#/components/schemas/Cursor"}]}
        )

    def test_dropped_null_branch_is_caught(self, contract: dict[str, Any]) -> None:
        """A field that stopped being nullable is a breaking change for every client."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["PageInfo"]["properties"].__setitem__(
                "next_cursor", {"$ref": "#/components/schemas/Cursor"}
            ),
        )
        assert any(
            line.startswith("schemas.PageInfo.properties.next_cursor") for line in report
        ), report

    def test_changed_nullable_inner_branch_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["PageInfo"]["properties"][
                "next_cursor"
            ].__setitem__(
                "oneOf", [{"$ref": "#/components/schemas/RunId"}, {"type": "null"}]
            ),
        )
        line = assert_reported_at(
            report, "schemas.PageInfo.properties.next_cursor.anyOf[0].$ref"
        )
        assert "Cursor" in line and "RunId" in line

    def test_a_three_branch_union_is_not_normalized(self) -> None:
        """The narrowness of the rule, shown rather than asserted in prose."""
        three = {
            "oneOf": [{"type": "string"}, {"type": "integer"}, {"type": "null"}],
        }
        assert conformance.normalize_schema(three)["oneOf"] == three["oneOf"]
        assert "anyOf" not in conformance.normalize_schema(three)

    def test_a_two_branch_union_without_a_null_is_not_normalized(self) -> None:
        two = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        assert conformance.normalize_schema(two) == two

    def test_a_null_branch_carrying_anything_else_is_not_normalized(self) -> None:
        """`{"type": "null", "const": null}` is still exactly null, but the rule refuses to
        reason about that: it fires on the literal shape and nothing wider."""
        near = {"oneOf": [{"type": "string"}, {"type": "null", "enum": [None]}]}
        assert "oneOf" in conformance.normalize_schema(near)


class TestN6TheTypeBesideAConst:
    """`N6`: a `type` that only restates the JSON type of its sibling `const`."""

    def test_type_beside_const_is_invisible(self, contract: dict[str, Any]) -> None:
        assert conformance.normalize_schema({"const": "application/pdf", "type": "string"}) == {
            "const": "application/pdf"
        }
        assert conformance.normalize_schema({"const": 7, "type": "integer"}) == {"const": 7}

    def test_changed_const_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["DocumentVersion"]["properties"][
                "media_type"
            ].__setitem__("const", "application/xml"),
        )
        line = assert_reported_at(report, "schemas.DocumentVersion.properties.media_type.const")
        assert "application/pdf" in line and "application/xml" in line

    def test_contradictory_type_beside_const_is_caught(self, contract: dict[str, Any]) -> None:
        """A `type` that does *not* match the const is kept, so the unsatisfiable schema
        surfaces instead of being normalized into agreement."""
        normalized = conformance.normalize_schema({"const": "application/pdf", "type": "integer"})
        assert normalized == {"const": "application/pdf", "type": "integer"}
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["DocumentVersion"]["properties"][
                "media_type"
            ].__setitem__("type", "integer"),
        )
        assert_reported_at(report, "schemas.DocumentVersion.properties.media_type.type")

    def test_the_contract_version_const_is_still_compared(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["ErrorEnvelope"]["properties"][
                "contract_version"
            ].__setitem__("const", "2.0.0"),
        )
        assert_reported_at(report, "schemas.ErrorEnvelope.properties.contract_version.const")


class TestN7EffectiveSecurity:
    """`N7`: the operation's own `security`, else the document's.

    `W13-SEAL` adds `securitySchemes` and the operations' `security` during this wave
    (`ALPHA_ROADMAP.md` §3 `T-6`, §4 stage 0b). These cases are built on a resealed copy so
    the comparison is shown to handle that contract before it lands.
    """

    def test_a_resealed_contract_conforms_to_itself(self, contract: dict[str, Any]) -> None:
        sealed = resealed(contract)
        assert_silent(differences(surface(sealed), surface(fastapi_flavoured(sealed))))
        reduced = surface(sealed)
        assert reduced["securitySchemes"] == {
            "bearerAuth": {"type": "http", "scheme": "bearer"}
        }
        assert reduced["paths"]["/projects"]["post"]["security"] == [{"bearerAuth": []}]

    def test_security_moved_from_root_to_operation_is_invisible(
        self, contract: dict[str, Any]
    ) -> None:
        sealed = resealed(contract)
        rooted = copy.deepcopy(sealed)
        rooted["security"] = [{"bearerAuth": []}]
        for path_item in rooted["paths"].values():
            for method in conformance.HTTP_METHODS:
                if method in path_item:
                    path_item[method].pop("security")
        assert_silent(differences(surface(rooted), surface(fastapi_flavoured(sealed))))

    def test_dropped_operation_security_is_caught(self, contract: dict[str, Any]) -> None:
        """One unauthenticated operation among twelve authenticated ones."""
        sealed = resealed(contract)
        mutated = plant(
            fastapi_flavoured(sealed),
            lambda document: document["paths"]["/projects"]["post"].__setitem__("security", []),
        )
        line = assert_reported_at(
            differences(surface(sealed), surface(mutated)), "paths./projects.post.security"
        )
        assert "bearerAuth" in line

    def test_a_dropped_security_scheme_is_caught(self, contract: dict[str, Any]) -> None:
        sealed = resealed(contract)
        mutated = plant(
            fastapi_flavoured(sealed),
            lambda document: document["components"].pop("securitySchemes"),
        )
        assert_reported_at(differences(surface(sealed), surface(mutated)), "securitySchemes")

    def test_a_weakened_security_scheme_is_caught(self, contract: dict[str, Any]) -> None:
        sealed = resealed(contract)
        mutated = plant(
            fastapi_flavoured(sealed),
            lambda document: document["components"]["securitySchemes"]["bearerAuth"].__setitem__(
                "scheme", "basic"
            ),
        )
        assert_reported_at(
            differences(surface(sealed), surface(mutated)), "securitySchemes.bearerAuth.scheme"
        )

    def test_an_unsealed_contract_still_compares(self, contract: dict[str, Any]) -> None:
        """Before the reseal, `security` is absent on both sides and that is not a
        difference. The gate must not turn red merely because stage 0b has not landed."""
        assert surface(contract)["paths"]["/projects"]["post"]["security"] is None
        assert_silent(differences(surface(contract), surface(fastapi_flavoured(contract))))


# =======================================================================================
# Part 4 - the planted differences the brief names, beyond the per-normalization pairs
# =======================================================================================


class TestThePlantedDifferences:
    """The six the `W13-CONF` brief names by hand, plus the ones a generated document is
    most likely to produce on its own."""

    def test_a_moved_operation_id_is_caught(self, contract: dict[str, Any]) -> None:
        """Two operations swap identities. Nothing is added or removed, so a comparison
        that only counted operations would stay green."""

        def swap(document: dict[str, Any]) -> None:
            document["paths"]["/projects"]["get"]["operationId"] = "getRunStatus"
            document["paths"]["/runs/{run_id}"]["get"]["operationId"] = "listProjects"

        report = report_for(contract, swap)
        assert "listProjects" in assert_reported_at(report, "paths./projects.get.operationId")
        assert "getRunStatus" in assert_reported_at(
            report, "paths./runs/{run_id}.get.operationId"
        )
        assert len(report) == 2, report

    def test_a_dropped_response_header_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}/export.csv"]["get"]["responses"][
                "200"
            ]["headers"].pop("X-Correlation-Id"),
        )
        assert_reported_at(
            report,
            "paths./runs/{run_id}/export.csv.get.responses.200.headers.X-Correlation-Id",
        )

    def test_a_renamed_schema_property_is_caught(self, contract: dict[str, Any]) -> None:
        def rename(document: dict[str, Any]) -> None:
            schema = document["components"]["schemas"]["Finding"]
            schema["properties"]["verdict_now"] = schema["properties"].pop("current_verdict")

        report = report_for(contract, rename)
        assert_reported_at(report, "schemas.Finding.properties.current_verdict")
        assert_reported_at(report, "schemas.Finding.properties.verdict_now")

    def test_a_renamed_schema_is_caught(self, contract: dict[str, Any]) -> None:
        """The reason `components.schemas` refs are deliberately left unresolved."""

        def rename(document: dict[str, Any]) -> None:
            schemas = document["components"]["schemas"]
            schemas["PageMarker"] = schemas.pop("PageInfo")

        report = report_for(contract, rename)
        assert_reported_at(report, "schemas.PageInfo")
        assert_reported_at(report, "schemas.PageMarker")

    def test_a_moved_status_code_is_caught(self, contract: dict[str, Any]) -> None:
        """`201` to `200` on `createProject` - the wave-13 rewrite risk `ALPHA_ROADMAP.md`
        names in so many words: *"a programme discovers in wave 15, in a browser, that a
        status code moved."*"""
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects"]["post"]["responses"].__setitem__(
                "200", document["paths"]["/projects"]["post"]["responses"].pop("201")
            ),
        )
        assert_reported_at(report, "paths./projects.post.responses.201")
        assert_reported_at(report, "paths./projects.post.responses.200")

    def test_a_changed_media_type_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}/export.csv"]["get"]["responses"][
                "200"
            ]["content"].__setitem__(
                "application/csv",
                document["paths"]["/runs/{run_id}/export.csv"]["get"]["responses"]["200"][
                    "content"
                ].pop("text/csv"),
            ),
        )
        assert_reported_at(
            report, "paths./runs/{run_id}/export.csv.get.responses.200.content.text/csv"
        )
        assert_reported_at(
            report,
            "paths./runs/{run_id}/export.csv.get.responses.200.content.application/csv",
        )

    def test_a_changed_request_body_media_type_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects/{project_uid}/documents"]["post"][
                "requestBody"
            ]["content"].__setitem__(
                "application/json",
                document["paths"]["/projects/{project_uid}/documents"]["post"]["requestBody"][
                    "content"
                ].pop("multipart/form-data"),
            ),
        )
        assert_reported_at(
            report,
            "paths./projects/{project_uid}/documents.post.requestBody.content.multipart/form-data",
        )

    def test_a_dropped_multipart_encoding_is_caught(self, contract: dict[str, Any]) -> None:
        """The contract declares the `file` part as `application/pdf`. FastAPI does not
        emit `encoding` on its own, so stage 2 has to declare it (`openapi_extra`); this is
        the case that says so rather than letting it disappear."""
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects/{project_uid}/documents"]["post"][
                "requestBody"
            ]["content"]["multipart/form-data"].pop("encoding"),
        )
        assert_reported_at(
            report,
            "paths./projects/{project_uid}/documents.post.requestBody.content."
            "multipart/form-data.encoding",
        )

    def test_a_relaxed_request_body_requirement_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects/{project_uid}/documents"]["post"][
                "requestBody"
            ].__setitem__("required", False),
        )
        assert_reported_at(
            report, "paths./projects/{project_uid}/documents.post.requestBody.required"
        )

    def test_a_missing_operation_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract, lambda document: document["paths"]["/projects"].pop("get")
        )
        assert_reported_at(report, "paths./projects.get")

    def test_a_missing_path_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract, lambda document: document["paths"].pop("/runs/{run_id}/export.csv")
        )
        assert_reported_at(report, "paths./runs/{run_id}/export.csv")

    def test_an_extra_operation_is_caught(self, contract: dict[str, Any]) -> None:
        """A route FastAPI serves that the contract does not declare - `T-3`'s health plane
        leaking onto the contract surface is exactly this shape."""
        report = report_for(
            contract,
            lambda document: document["paths"].__setitem__(
                "/healthz",
                {"get": {"operationId": "healthz", "responses": {"200": {"description": "ok"}}}},
            ),
        )
        assert_reported_at(report, "paths./healthz")

    def test_an_extra_schema_is_caught(self, contract: dict[str, Any]) -> None:
        """FastAPI adds `HTTPValidationError` and `ValidationError` to any application that
        has not taken its default 422 away. `ALPHA_ROADMAP.md` §4 stage 2 requires *"every
        failure rendered by `envelope_response` and nothing else"*, so this must fail."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"].__setitem__(
                "HTTPValidationError",
                {"type": "object", "properties": {"detail": {"type": "array"}}},
            ),
        )
        assert_reported_at(report, "schemas.HTTPValidationError")

    def test_an_undeclared_response_code_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}"]["get"]["responses"].__setitem__(
                "422",
                {"description": "FastAPI's own", "content": {"application/json": {"schema": {}}}},
            ),
        )
        assert_reported_at(report, "paths./runs/{run_id}.get.responses.422")

    def test_a_changed_http_method_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/projects"].__setitem__(
                "put", document["paths"]["/projects"].pop("post")
            ),
        )
        assert_reported_at(report, "paths./projects.post")
        assert_reported_at(report, "paths./projects.put")

    def test_a_changed_base_path_is_caught(self, contract: dict[str, Any]) -> None:
        """`T-2`: the API is served at `/api/v1`. A document that dropped the prefix from
        `servers` and pushed it into every path would still be a different document."""
        report = report_for(
            contract,
            lambda document: document["servers"].__setitem__(0, {"url": "/"}),
        )
        assert_reported_at(report, "servers[0]")

    def test_a_changed_openapi_version_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract, lambda document: document.__setitem__("openapi", "3.0.3")
        )
        assert_reported_at(report, "openapi")

    def test_a_changed_operation_tag_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/runs/{run_id}/export.csv"]["get"].__setitem__(
                "tags", ["exports"]
            ),
        )
        assert_reported_at(report, "paths./runs/{run_id}/export.csv.get.tags[0]")

    def test_a_widened_numeric_bound_is_caught(self, contract: dict[str, Any]) -> None:
        """`page_count` maximum 30 is `PROTOTYPE_PROFILE.md`'s ingest limit expressed in the
        contract; a generated document that lost it would accept a document the pipeline
        refuses."""
        report = report_for(
            contract,
            lambda document: document["components"]["schemas"]["DocumentVersion"]["properties"][
                "page_count"
            ].__setitem__("maximum", 3000),
        )
        line = assert_reported_at(report, "schemas.DocumentVersion.properties.page_count.maximum")
        assert "30" in line and "3000" in line

    def test_a_changed_parameter_default_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["parameters"]["Limit"]["schema"].__setitem__(
                "default", 500
            ),
        )
        assert_reported_at(report, "paths./projects.get.parameters.query:limit.schema.default")

    def test_a_changed_response_header_schema_is_caught(self, contract: dict[str, Any]) -> None:
        report = report_for(
            contract,
            lambda document: document["paths"]["/versions/{version_uid}/content"]["get"][
                "responses"
            ]["200"]["headers"]["Content-Length"].__setitem__("schema", {"type": "string"}),
        )
        assert_reported_at(
            report,
            "paths./versions/{version_uid}/content.get.responses.200.headers."
            "Content-Length.schema.type",
        )

    def test_a_response_header_that_stopped_being_required_is_caught(
        self, contract: dict[str, Any]
    ) -> None:
        report = report_for(
            contract,
            lambda document: document["components"]["headers"]["CorrelationId"].__setitem__(
                "required", False
            ),
        )
        assert_reported_at(
            report, "paths./projects.post.responses.201.headers.X-Correlation-Id.required"
        )
