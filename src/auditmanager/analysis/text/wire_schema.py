"""The provider-safe wire form of a response schema (`AR-V3-WIRE-SCHEMA-01`).

Strict structured-output providers refuse part of JSON Schema outright: the live stand's first AR v3
Runs all failed with ``output_config.format.schema: Schema type 'oneOf' is not supported``. The sealed
AR v3 schema (``analysis/profiles/ar_v3/response_schema.py``) uses ``oneOf`` and a set of value
constraints (``minLength``, ``maxLength``, ``minimum``, ``maxItems``, ``pattern``) that the same providers
reject, so every transport hands the provider the **wire form** of the schema instead. The sealed schema,
the prompt, the pack and every digest stay as they are; the request's own body is not changed.

What the wire form is, rule by rule (each rule has a test):

1. a **new** object: the argument is never mutated and nothing in the result is shared with it; applying
   the function to its own result changes nothing (idempotent);
2. in a **schema position** (the schema itself, ``items``, each value of ``properties``, the members of
   ``anyOf``/``oneOf``/``allOf``, ``additionalProperties`` when it is a mapping) ``oneOf`` becomes
   ``anyOf`` and ``minLength``, ``maxLength``, ``minimum``, ``maximum``, ``maxItems`` and ``pattern`` are
   removed; ``minItems`` stays when it is 0 or 1 (the only values the providers accept) and is removed
   otherwise;
3. in a **name position** nothing is filtered: the keys of ``properties`` (and of ``patternProperties``,
   ``$defs``, ``definitions``) are names, so a property called ``pattern`` or ``oneOf`` survives and only
   its own sub-schema is cleaned;
4. everything else is kept as it is: ``type``, ``enum``, ``const``, ``required``,
   ``additionalProperties``, annotations, ``anyOf``;
5. a value that is not a mapping is returned unchanged; nesting deeper than 64 levels is refused with
   :class:`ValueError`;
6. a schema that uses none of the above (the v1 text-analysis schema) comes out equal to what went in,
   key order included.

Dropping a constraint from what the provider is told does not drop it from what is accepted. The model's
answer is read by the local parser (``analysis/profiles/ar_v3/response.py``), which re-checks every
dropped constraint itself and drops a malformed proposal, so the local parser stays the authority on what
is accepted; the wire form only keeps the provider from refusing the request.

A schema node that carries both ``oneOf`` and ``anyOf`` cannot hold two ``anyOf`` keys. The converted
``oneOf`` is then appended to ``allOf`` as ``{"anyOf": [...]}``, which says the same thing (both
alternatives must hold) and loses nothing silently.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Final

__all__ = ["to_wire_schema", "with_wire_schema"]

MAX_DEPTH: Final[int] = 64

#: Removed from every schema position. ``minItems`` is handled apart: it stays when it is 0 or 1.
_DROPPED: Final[frozenset[str]] = frozenset(
    {"minLength", "maxLength", "minimum", "maximum", "maxItems", "pattern"}
)
#: Keywords whose value is one sub-schema (``items`` may also be a list of them).
_SCHEMA_VALUED: Final[frozenset[str]] = frozenset({
    "items", "additionalProperties", "additionalItems", "contains", "not", "if", "then", "else",
    "propertyNames",
})
#: Keywords whose value is a list of sub-schemas.
_SCHEMA_LISTS: Final[frozenset[str]] = frozenset({"anyOf", "oneOf", "allOf", "prefixItems"})
#: Keywords whose value is a mapping of NAME -> sub-schema. The names are data, never keywords.
_NAME_MAPS: Final[frozenset[str]] = frozenset(
    {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
)


def to_wire_schema(schema: Any) -> Any:
    """The wire form of ``schema`` (see the module text); ``schema`` itself is never changed.

    Anything that is not a mapping is returned as it came. Raises :class:`ValueError` when the schema
    nests deeper than :data:`MAX_DEPTH` levels (the same bound as the runner-side validator).
    """
    if not isinstance(schema, Mapping):
        return schema
    return _schema(schema, 0)


def with_wire_schema(body: Mapping[str, Any]) -> dict[str, Any]:
    """A shallow copy of an Anthropic-shaped request body whose ``output_config.format.schema`` is in
    wire form. ``body`` is not changed; a body with no such schema is copied as it is."""
    sent = dict(body)
    output = body.get("output_config")
    if isinstance(output, Mapping):
        form = output.get("format")
        if isinstance(form, Mapping) and "schema" in form:
            sent["output_config"] = {**output, "format": {**form, "schema": to_wire_schema(form["schema"])}}
    return sent


def _schema(node: Mapping[Any, Any], depth: int) -> dict[Any, Any]:
    if depth > MAX_DEPTH:
        raise ValueError(f"the response schema nests deeper than {MAX_DEPTH} levels")
    cleaned: dict[Any, Any] = {}
    for key, value in node.items():
        if key in _DROPPED:
            continue
        if key == "minItems":
            if type(value) is int and value in (0, 1):
                cleaned[key] = value
        elif key == "oneOf":
            if "anyOf" not in node:
                cleaned["anyOf"] = _members(value, depth)
        elif key in _SCHEMA_LISTS:
            cleaned[key] = _members(value, depth)
        elif key in _SCHEMA_VALUED:
            cleaned[key] = _sub(value, depth)
        elif key in _NAME_MAPS and isinstance(value, Mapping):
            cleaned[key] = {name: _sub(child, depth) for name, child in value.items()}
        else:
            cleaned[key] = copy.deepcopy(value)
    if "oneOf" in node and "anyOf" in node:
        alternatives = {"anyOf": _members(node["oneOf"], depth)}
        existing = cleaned.get("allOf")
        cleaned["allOf"] = [*existing, alternatives] if isinstance(existing, list) else [alternatives]
    return cleaned


def _sub(value: Any, depth: int) -> Any:
    """A sub-schema position: a mapping is cleaned one level deeper, a list (tuple-form ``items``) is
    cleaned member by member, anything else (``true``/``false``) is copied."""
    if isinstance(value, Mapping):
        return _schema(value, depth + 1)
    if isinstance(value, (list, tuple)):
        return _members(value, depth)
    return copy.deepcopy(value)


def _members(value: Any, depth: int) -> Any:
    if isinstance(value, (list, tuple)):
        return [_sub(member, depth) for member in value]
    return copy.deepcopy(value)
