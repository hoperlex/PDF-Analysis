"""The conformance comparison: `app.openapi()` against the frozen contract.

**Why this module exists, in one paragraph.** Revision 1 of `ALPHA_ROADMAP.md` argued
against FastAPI on exactly one ground: *"a framework that generates its own OpenAPI over a
frozen one creates a second routing and schema authority, and that is a real drift risk."*
The owner overruled the conclusion and kept the objection. §3 `T-1` names what answers it:
*"What answers it is not an assurance but a gate ... Without that gate this decision is
worse than revision 1's; with it, it is better."* This module is that gate's engine. A
comparison here that cannot fail does not merely miss a defect - it removes the only thing
that made the owner's decision sound.

`contracts/api/v1/openapi.json` stays frozen and stays **the authority**. The generated
document conforms to it, never the other way round.

--------------------------------------------------------------------------------------
THE DECLARED NORMALIZATION
--------------------------------------------------------------------------------------

Byte-equality is not the goal and claiming it would be dishonest: FastAPI adds titles,
orders keys its own way, has no notion of a reusable parameter object and spells
optionality differently from the contract's author. So a fixed, enumerated set of
transformations is applied **identically to both documents**, and then everything that
remains must be equal.

Every entry below answers three questions, and the third is the one that decides whether
this gate is worth anything:

  1. **what differs**,
  2. **why FastAPI produces it**,
  3. **why erasing it cannot hide a semantic change.**

A normalization that is a list of "things that happened to differ" is a list that grows
until the test means nothing. Nothing is added here without a third answer, and
`test_openapi_conformance.py` carries a planted difference for every entry proving the
comparison still fails through it.

`N1 - local $refs into components.parameters, components.responses and components.headers
are resolved in place.`
  1. The contract factors ten parameters, nine responses and one header into `components`
     and refers to them 32, 47 and 22 times. FastAPI's document refers to nothing but
     `components.schemas`.
  2. FastAPI has no reusable-parameter concept: `Header(...)`, `Path(...)` and a
     `responses={}` entry are each expanded inline at generation time.
  3. A `$ref` *is* its target - the OpenAPI specification defines it as substitution. The
     component key (`NotFound`, `RunId`) is a spelling of the document's own internals and
     is not observable by any caller. Resolution replaces a name with the thing it names,
     on both sides, so the resolved parameter, response and header objects are compared in
     full: changing what `NotFound` resolves *to* still fails. Proof both ways in
     `test_component_key_rename_is_invisible` and `test_changed_component_target_is_caught`.
  4. Deliberately **not** resolved: `#/components/schemas/*`. Inlining those would make a
     renamed schema invisible, which is the exact drift this gate exists for. Schema
     references are compared as references and the 43 schema names are pinned.

`N2 - path-item level parameters are merged into every operation of that path item.`
  1. The contract declares `{project_uid}`, `{version_uid}`, `{run_id}` and
     `{finding_uid}` once on the path item. FastAPI declares every parameter on the
     operation.
  2. A FastAPI path operation is one function; its signature is the only place a parameter
     can be declared, so there is no path-item level to emit.
  3. The OpenAPI specification says a path-item parameter applies to every operation of
     that item, and an operation-level entry with the same `name` and `in` overrides it.
     The merge computes exactly that effective set, on both sides. Nothing is dropped:
     deleting the path-item parameter removes it from the merged set and fails.
     `test_parameter_moved_to_operation_level_is_invisible` and
     `test_dropped_path_level_parameter_is_caught`.

`N3 - parameters become a map keyed by "{in}:{name}", response headers a map by name, and
the set-valued keywords `required` and `enum` are sorted.`
  1. Ordering. FastAPI emits parameters in function-signature order; the contract is in
     editorial order. Pydantic emits `required` in field-declaration order.
  2. Both orders are arbitrary artefacts of how the document was produced.
  3. The specification gives parameter order no meaning and *requires* `(name, in)` to be
     unique within an operation, so the map is lossless - a collision is impossible, and an
     added, removed or renamed parameter changes the key set. `required` and `enum` are
     unordered by JSON Schema; sorting cannot merge two members or drop one, so any
     addition, removal or rename still changes the sorted list.
     `test_reordered_parameters_are_invisible`, `test_changed_required_list_is_caught`,
     `test_changed_enum_member_is_caught`.

`N4 - annotation-only keywords are dropped: description, summary, title, examples, example,
externalDocs, info and the top-level tag descriptions.`
  1. Pydantic writes a `title` on every model and every field, derived from the name.
     FastAPI writes an operation's `description` from the handler docstring and a
     property's from `Field(description=...)`.
  2. These are display strings. None of them validates a request, selects a response,
     names a field or constrains a value.
  3. Keeping them would make this gate a prose diff that nobody can hold green, and a gate
     that is red for prose reasons is a gate somebody switches off. Erasing them removes no
     identity: a schema's identity is its `components.schemas` key and a property's is its
     key in `properties`, both compared; an operation's is its `operationId`, compared.
     **The honest cost, stated rather than hidden:** a rule recorded *only* in a
     `description` is outside this gate. That is why the frozen document remains the
     authority and why `web/tests/contract/openapi-drift.contract.test.ts` pins its bytes.
     `test_changed_description_is_deliberately_invisible` records the blind spot as a test
     rather than as a promise, and `test_changed_pattern_is_caught` shows the boundary:
     prose moves freely, constraints do not.

`N5 - the two-branch nullable union is canonicalized to `anyOf` with the null branch last.`
  1. The contract spells its 21 optional fields `{"oneOf": [S, {"type": "null"}]}`.
     Pydantic spells `S | None` as `{"anyOf": [S, {"type": "null"}]}`.
  2. Pydantic emits `anyOf` for every `typing.Union`, including the optional case.
  3. The rewrite fires **only** on a union of exactly two branches, one of which is exactly
     `{"type": "null"}` and nothing else. For that shape `oneOf` and `anyOf` accept exactly
     the same documents: `null` matches the null branch, and matches `S` only if `S` itself
     admitted null - in which case the contract's own `oneOf` would already be unsatisfiable
     for `null`, so the frozen document cannot be relying on the distinction. Every other
     `oneOf`, `anyOf` and `allOf` is left exactly as written and compared branch by branch,
     so a genuine discriminated union can never be normalized into anything. The inner
     branch `S` is still compared in full.
     `test_oneof_to_anyof_nullable_is_invisible`, `test_dropped_null_branch_is_caught`,
     `test_changed_nullable_inner_branch_is_caught`,
     `test_three_branch_oneof_is_not_normalized`.

`N6 - a `type` that only restates the JSON type of a sibling `const` is dropped.`
  1. The contract writes `{"const": "application/pdf"}`. Pydantic writes
     `{"const": "application/pdf", "type": "string"}`.
  2. Pydantic emits the type of a `Literal`'s value alongside the literal.
  3. Dropped **only** when the declared `type` is the JSON type of the `const` value, where
     it admits every value `const` already admits and therefore constrains nothing. When
     the two disagree - `{"const": "x", "type": "integer"}`, a schema nothing can satisfy -
     the `type` is kept and the difference is reported.
     `test_type_beside_const_is_invisible`, `test_changed_const_is_caught`,
     `test_contradictory_type_beside_const_is_caught`.

`N7 - an operation's security is reduced to its effective value.`
  1. The contract may declare `security` at the document root, per operation, or both.
     FastAPI only ever emits it per operation, from the `Security()` dependencies in the
     signature.
  2. There is no document-level dependency in FastAPI.
  3. The specification defines the effective value exactly: an operation's own `security`
     if present, otherwise the root's. Computing it on both sides compares the thing that
     decides whether a caller needs a credential; where the declaration is written has no
     effect on that. An operation that loses its requirement fails.
     `test_dropped_operation_security_is_caught`,
     `test_security_moved_from_root_to_operation_is_invisible`.

--------------------------------------------------------------------------------------
WHAT IS COMPARED, AFTER ALL OF THAT
--------------------------------------------------------------------------------------

  * the `openapi` version string and the `servers` base paths;
  * the set of paths and, per path, the set of HTTP methods;
  * per operation: `operationId`, `tags`, effective `security`, `deprecated`;
  * per parameter: `in`, `name`, `required`, and its schema in full;
  * the request body: `required`, its media types, each media type's schema and its
    `encoding` (the contract declares `multipart/form-data` `file` as `application/pdf`,
    and a part whose declared content type vanished is a real change);
  * per response: the status code, its media types and their schemas, and every response
    header with its `required` flag and schema;
  * `components.securitySchemes`;
  * all 43 `components.schemas`, in full, including `additionalProperties`, `pattern`,
    `minimum`, `maximum`, `minLength`, `maxLength`, `format`, `const`, `enum`, `required`
    and every `$ref` target.
"""

from __future__ import annotations

import copy
import json
from typing import Any

__all__ = [
    "ANNOTATION_KEYS",
    "differences",
    "normalize_schema",
    "operation_index",
    "surface",
]

#: HTTP methods the OpenAPI specification allows in a path item. Anything else in a path
#: item (`parameters`, `summary`, `description`, `servers`, `$ref`) is not an operation.
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")

#: `N4`. Dropped wherever a schema, operation, parameter, response, header or media-type
#: object may carry them. Never dropped from a *property name* - see `_normalize_schema`,
#: which walks by JSON Schema keyword position and not by key spelling, so a schema with a
#: property literally called `description` keeps it.
ANNOTATION_KEYS = frozenset(
    {"description", "summary", "title", "examples", "example", "externalDocs"}
)

#: `N3`. JSON Schema defines these as sets, so their order carries no meaning.
SET_VALUED_KEYWORDS = ("required", "enum")

#: `N1`. Resolved. `#/components/schemas/` is deliberately absent.
RESOLVED_COMPONENT_SECTIONS = ("parameters", "responses", "headers")

# JSON Schema keyword positions, so the walker knows a sub-schema from a data value.
_SCHEMA_VALUED = (
    "items",
    "not",
    "propertyNames",
    "contains",
    "if",
    "then",
    "else",
    "unevaluatedItems",
    "unevaluatedProperties",
    "additionalItems",
)
_SCHEMA_LIST_VALUED = ("allOf", "anyOf", "oneOf", "prefixItems")
_SCHEMA_MAP_VALUED = (
    "properties",
    "patternProperties",
    "$defs",
    "definitions",
    "dependentSchemas",
)

_JSON_TYPE_OF = {
    bool: "boolean",
    str: "string",
    int: "integer",
    float: "number",
    list: "array",
    dict: "object",
    type(None): "null",
}


def _json_type(value: Any) -> str:
    # `bool` before `int`: in Python `True` is an `int`, in JSON it is not a number.
    if isinstance(value, bool):
        return "boolean"
    return _JSON_TYPE_OF.get(type(value), "unknown")


# ---------------------------------------------------------------------------------------
# N1 - component reference resolution
# ---------------------------------------------------------------------------------------


def _resolve_component_refs(node: Any, document: dict[str, Any], seen: tuple[str, ...] = ()) -> Any:
    """Replace `$ref`s into the three resolved component sections with their targets.

    Sibling keys beside a `$ref` are allowed by OpenAPI 3.1 and override the target, so
    they are applied on top rather than discarded. The contract carries none today; a
    generated document that grew one would still be compared correctly.
    """
    if isinstance(node, list):
        return [_resolve_component_refs(item, document, seen) for item in node]
    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if isinstance(ref, str):
        for section in RESOLVED_COMPONENT_SECTIONS:
            prefix = f"#/components/{section}/"
            if not ref.startswith(prefix):
                continue
            if ref in seen:
                raise ValueError(f"cyclic component reference: {' -> '.join((*seen, ref))}")
            key = ref[len(prefix) :]
            try:
                target = document["components"][section][key]
            except (KeyError, TypeError):
                raise ValueError(f"dangling reference {ref}") from None
            resolved = _resolve_component_refs(target, document, (*seen, ref))
            overrides = {k: v for k, v in node.items() if k != "$ref"}
            if overrides:
                resolved = {
                    **resolved,
                    **{k: _resolve_component_refs(v, document, seen) for k, v in overrides.items()},
                }
            return resolved

    return {key: _resolve_component_refs(value, document, seen) for key, value in node.items()}


# ---------------------------------------------------------------------------------------
# N3 to N6 - the schema normalizer
# ---------------------------------------------------------------------------------------


def _is_null_branch(branch: Any) -> bool:
    """Exactly `{"type": "null"}` and nothing else. Deliberately strict - see `N5`."""
    return isinstance(branch, dict) and branch == {"type": "null"}


def normalize_schema(schema: Any) -> Any:
    """Apply `N3`, `N4`, `N5` and `N6` to a schema object, recursively.

    Walks by JSON Schema keyword position, never by key spelling, so a property named
    `title` or `description` is normalized as a schema and not mistaken for an annotation.
    """
    if isinstance(schema, list):
        return [normalize_schema(item) for item in schema]
    if isinstance(schema, bool) or not isinstance(schema, dict):
        return schema

    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key in ANNOTATION_KEYS:
            continue  # N4
        if key in _SCHEMA_VALUED:
            out[key] = normalize_schema(value) if isinstance(value, (dict, list, bool)) else value
        elif key in _SCHEMA_LIST_VALUED:
            out[key] = [normalize_schema(branch) for branch in value]
        elif key in _SCHEMA_MAP_VALUED:
            out[key] = {name: normalize_schema(sub) for name, sub in value.items()}
        elif key == "additionalProperties":
            out[key] = normalize_schema(value) if isinstance(value, (dict, bool)) else value
        elif key in SET_VALUED_KEYWORDS and isinstance(value, list):
            out[key] = sorted(value, key=_stable_key)  # N3
        else:
            out[key] = value

    # N5 - the two-branch nullable union, and only that shape.
    for union in ("oneOf", "anyOf"):
        branches = out.get(union)
        if not (isinstance(branches, list) and len(branches) == 2):
            continue
        nulls = [b for b in branches if _is_null_branch(b)]
        others = [b for b in branches if not _is_null_branch(b)]
        if len(nulls) == 1 and len(others) == 1:
            rest = {k: v for k, v in out.items() if k != union}
            out = {**rest, "anyOf": [others[0], {"type": "null"}]}
            break

    # N6 - a `type` that only restates the JSON type of a sibling `const`.
    if "const" in out and isinstance(out.get("type"), str):
        if out["type"] == _json_type(out["const"]):
            out = {k: v for k, v in out.items() if k != "type"}

    return out


def _stable_key(value: Any) -> tuple[str, str]:
    """Total order over mixed JSON scalars, so sorting a `required` or `enum` never raises."""
    return (_json_type(value), json.dumps(value, sort_keys=True))


# ---------------------------------------------------------------------------------------
# N2 - effective parameters, and the parameter map of N3
# ---------------------------------------------------------------------------------------


def _parameter_key(parameter: dict[str, Any]) -> str:
    return f"{parameter.get('in')}:{parameter.get('name')}"


def _effective_parameters(
    path_item: dict[str, Any], operation: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """`N2` then `N3`: the path item's parameters, overridden by the operation's, as a map."""
    merged: dict[str, dict[str, Any]] = {}
    for parameter in path_item.get("parameters", []) or []:
        merged[_parameter_key(parameter)] = parameter
    for parameter in operation.get("parameters", []) or []:
        merged[_parameter_key(parameter)] = parameter
    return {
        key: {
            "required": bool(parameter.get("required", False)),
            "schema": normalize_schema(parameter.get("schema")),
            # A parameter may carry `content` instead of `schema`; neither side uses it
            # today, and leaving it in the comparison means a document that grew one is
            # reported rather than silently ignored.
            "content": _media_types(parameter.get("content")),
            "deprecated": bool(parameter.get("deprecated", False)),
            "allowEmptyValue": bool(parameter.get("allowEmptyValue", False)),
            "style": parameter.get("style"),
            "explode": parameter.get("explode"),
        }
        for key, parameter in sorted(merged.items())
    }


# ---------------------------------------------------------------------------------------
# media types, responses, headers
# ---------------------------------------------------------------------------------------


def _encoding(encoding: dict[str, Any] | None) -> dict[str, Any] | None:
    if not encoding:
        return None
    return {
        part: {k: v for k, v in spec.items() if k not in ANNOTATION_KEYS}
        for part, spec in sorted(encoding.items())
    }


def _media_types(content: dict[str, Any] | None) -> dict[str, Any] | None:
    if content is None:
        return None
    return {
        media_type: {
            "schema": normalize_schema(body.get("schema")),
            "encoding": _encoding(body.get("encoding")),
        }
        for media_type, body in sorted(content.items())
    }


def _headers(headers: dict[str, Any] | None) -> dict[str, Any]:
    if not headers:
        return {}
    return {
        name: {
            "required": bool(header.get("required", False)),
            "schema": normalize_schema(header.get("schema")),
            "deprecated": bool(header.get("deprecated", False)),
        }
        for name, header in sorted(headers.items())
    }


def _responses(responses: dict[str, Any]) -> dict[str, Any]:
    return {
        str(code): {
            "content": _media_types(response.get("content")),
            "headers": _headers(response.get("headers")),
        }
        for code, response in sorted(responses.items(), key=lambda item: str(item[0]))
    }


def _request_body(body: dict[str, Any] | None) -> dict[str, Any] | None:
    if body is None:
        return None
    return {
        "required": bool(body.get("required", False)),
        "content": _media_types(body.get("content")),
    }


# ---------------------------------------------------------------------------------------
# N7 - effective security
# ---------------------------------------------------------------------------------------


def _normalize_security(requirements: Any) -> Any:
    if requirements is None:
        return None
    normalized = [
        {scheme: sorted(scopes) for scheme, scopes in sorted(requirement.items())}
        for requirement in requirements
    ]
    return sorted(normalized, key=lambda requirement: json.dumps(requirement, sort_keys=True))


def _strip_annotations(node: Any) -> Any:
    """Drop `N4` keys from a non-schema object tree (used for `securitySchemes`)."""
    if isinstance(node, list):
        return [_strip_annotations(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {k: _strip_annotations(v) for k, v in sorted(node.items()) if k not in ANNOTATION_KEYS}


# ---------------------------------------------------------------------------------------
# the surface
# ---------------------------------------------------------------------------------------


def surface(document: dict[str, Any]) -> dict[str, Any]:
    """Reduce an OpenAPI document to the comparable surface, applying `N1` to `N7`.

    The argument is never mutated: a mutated copy of the frozen contract is exactly how the
    planted-difference tests work, and a normalizer that edited its input in place would
    corrupt the next case in the same session.
    """
    document = _resolve_component_refs(copy.deepcopy(document), document)  # N1
    root_security = document.get("security")
    components = document.get("components", {}) or {}

    paths: dict[str, Any] = {}
    for path, path_item in sorted((document.get("paths") or {}).items()):
        operations: dict[str, Any] = {}
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            operations[method] = {
                "operationId": operation.get("operationId"),
                "tags": sorted(operation.get("tags", []) or []),
                "deprecated": bool(operation.get("deprecated", False)),
                # N7: the operation's own requirement, else the document's.
                "security": _normalize_security(
                    operation["security"] if "security" in operation else root_security
                ),
                "parameters": _effective_parameters(path_item, operation),  # N2, N3
                "requestBody": _request_body(operation.get("requestBody")),
                "responses": _responses(operation.get("responses") or {}),
            }
        paths[path] = operations

    return {
        "openapi": document.get("openapi"),
        "servers": [server.get("url") for server in document.get("servers", []) or []],
        "tags": sorted(tag.get("name") for tag in document.get("tags", []) or []),
        "securitySchemes": _strip_annotations(components.get("securitySchemes")),
        "paths": paths,
        "schemas": {
            name: normalize_schema(schema)
            for name, schema in sorted((components.get("schemas") or {}).items())
        },
    }


def operation_index(document: dict[str, Any]) -> dict[tuple[str, str], str]:
    """`(method, path) -> operationId` for every operation, straight from a document."""
    index: dict[tuple[str, str], str] = {}
    for path, path_item in (document.get("paths") or {}).items():
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if operation is not None:
                index[(method.upper(), path)] = operation.get("operationId")
    return index


# ---------------------------------------------------------------------------------------
# the difference report
# ---------------------------------------------------------------------------------------


def _render(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, default=str)
    return text if len(text) <= 240 else text[:237] + "..."


def differences(expected: Any, generated: Any, path: str = "") -> list[str]:
    """Every semantic difference, each naming **what** differs and **where**.

    `expected` is the frozen contract's surface and is the authority; `generated` is the
    surface of `app.openapi()`. The report is a list of lines shaped like

        paths./runs/{run_id}/export.csv.get.responses.200.headers.X-Correlation-Id.required:
            contract has true, generated document has false

    because "paths differ" is useless at two in the morning and a dotted location is not.
    An empty list means the two documents agree on everything the module compares.
    """
    here = path or "<document>"

    if isinstance(expected, dict) and isinstance(generated, dict):
        out: list[str] = []
        for key in sorted(set(expected) | set(generated)):
            child = f"{path}.{key}" if path else key
            if key not in generated:
                out.append(
                    f"{child}: missing from the generated document "
                    f"(the contract has {_render(expected[key])})"
                )
            elif key not in expected:
                out.append(
                    f"{child}: present only in the generated document "
                    f"({_render(generated[key])}); the contract does not declare it"
                )
            else:
                out.extend(differences(expected[key], generated[key], child))
        return out

    if isinstance(expected, list) and isinstance(generated, list):
        if len(expected) != len(generated):
            return [
                f"{here}: the contract has {len(expected)} entries and the generated "
                f"document has {len(generated)} entries - contract {_render(expected)} "
                f"- generated {_render(generated)}"
            ]
        out = []
        for index, (left, right) in enumerate(zip(expected, generated)):
            out.extend(differences(left, right, f"{path}[{index}]" if path else f"[{index}]"))
        return out

    if type(expected) is not type(generated) or expected != generated:
        return [
            f"{here}: the contract has {_render(expected)}, "
            f"the generated document has {_render(generated)}"
        ]
    return []
