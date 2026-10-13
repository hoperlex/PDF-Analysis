"""Check a JSON value against the subset of JSON Schema the pinned block-list schema uses.

`jsonschema` is not in the repository's lock, and adding it is not this lane's to do. The
pinned schema (`contracts/analysis/v1/portal-blocks.schema.json`) uses a handful of
keywords, so they are implemented here directly -- and the validator reads the schema from
the contract file instead of copying its rules, so the two cannot drift apart.

Anything the subset does not cover is refused loudly (`SchemaSubsetError`) when the schema
is loaded, never skipped while checking: a rule added to the contract that this module
ignored would make every bundle look valid.
"""

from __future__ import annotations

import re

# Keywords that describe the schema and constrain nothing.
ANNOTATIONS = frozenset({
    "$schema", "$id", "title", "description", "contract_version", "x-envelope-rules",
})
CONSTRAINTS = frozenset({
    "type", "enum", "const", "required", "properties", "items",
    "minItems", "maxItems", "minimum", "maximum", "pattern",
})


class SchemaSubsetError(ValueError):
    """The schema uses a keyword this checker does not implement."""


def assert_supported(schema: object, where: str = "$") -> None:
    if not isinstance(schema, dict):
        raise SchemaSubsetError(f"{where}: a schema must be an object")
    unknown = sorted(set(schema) - ANNOTATIONS - CONSTRAINTS)
    if unknown:
        raise SchemaSubsetError(f"{where}: unsupported keyword(s) {unknown}")
    for name, sub in schema.get("properties", {}).items():
        assert_supported(sub, f"{where}.{name}")
    if "items" in schema:
        assert_supported(schema["items"], f"{where}[]")


def _is_type(value: object, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise SchemaSubsetError(f"unknown type name {name!r}")


def check(value: object, schema: dict, path: str = "$") -> list[str]:
    """Every violation of `schema` by `value`, as `path: message` strings."""
    errors: list[str] = []
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, n) for n in names):
            return [f"{path}: expected {'|'.join(names)}, found {type(value).__name__}"]
    if "const" in schema and (value != schema["const"] or isinstance(value, bool)
                              != isinstance(schema["const"], bool)):
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and not any(
        value == option and isinstance(value, bool) == isinstance(option, bool)
        for option in schema["enum"]
    ):
        errors.append(f"{path}: not one of {schema['enum']!r}")
    if isinstance(value, str) and "pattern" in schema:
        if re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: does not match {schema['pattern']!r}")
    if _is_type(value, "number") and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below the minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above the maximum {schema['maximum']}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += check(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required property {name!r}")
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                errors += check(value[name], sub, f"{path}.{name}")
    return errors
