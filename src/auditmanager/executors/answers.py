"""Reading a runner's answer against the task's output schema (`EXEC-PULL-01`).

An ``http_api`` answer is read by the stage's own parser (``analysis/text/response.py``), which
checks each element and drops, counts and never repairs what does not fit. The pull channel
adds a check **before the answer is accepted**, so a runner that can still correct its answer is
told which part is wrong while its claim holds: the same document that the stage will read,
held to the schema the task carried.

The runtime lock carries no JSON Schema library and a root dependency is not this slice's to
add, so this is a small validator for exactly the keywords the stage's response schemas use
(``AR v1`` ``RESPONSE_SCHEMA``, ``ar_v2`` and ``ar_v3``)::

    type  enum  const  properties  required  additionalProperties  items
    minItems  maxItems  minLength  maxLength  minimum  maximum  pattern  oneOf  anyOf

Annotation keywords (``title``, ``description``, ``$schema``, ``default``, ``examples``, ``$id``)
are ignored. **Any other keyword is refused** by :func:`check_supported`, which the adapter calls
before it writes a task: a schema this module cannot judge must not be waved through as valid
(`AGENTS.md` section 4, no silent fallback), and an answer to it would be accepted unread.

A violation is reported as a **location and a keyword**, never the document text: the message
that reaches a runner (and a log) names ``$.observations[3].category`` and ``enum``, not the
value that failed. A location holds only names the *schema* declares (``properties``) and array
indices; a name the answer invented (``additionalProperties``) is reported at its parent.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "AnswerInvalid",
    "SchemaNotSupported",
    "check_supported",
    "read_answer",
    "validate",
]

_ANNOTATIONS: Final[frozenset[str]] = frozenset(
    {"title", "description", "$schema", "$id", "default", "examples", "$comment"}
)
_KEYWORDS: Final[frozenset[str]] = frozenset({
    "type", "enum", "const", "properties", "required", "additionalProperties", "items",
    "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum", "pattern",
    "oneOf", "anyOf",
}) | _ANNOTATIONS
_TYPES: Final[frozenset[str]] = frozenset(
    {"object", "array", "string", "integer", "number", "boolean", "null"}
)
_MAX_DEPTH: Final[int] = 64
#: Cut a location to what a message may carry (the envelope screens a message's length).
_LOCATION_LIMIT: Final[int] = 120


class SchemaNotSupported(ValueError):
    """The schema uses a keyword this validator does not judge. ``keyword`` names it."""

    def __init__(self, keyword: str, location: str) -> None:
        super().__init__(f"{keyword} at {location}")
        self.keyword = keyword
        self.location = location


@dataclass(frozen=True, slots=True)
class AnswerInvalid:
    """The answer is not JSON, or violates the schema. Carries no part of the document.

    A value and not an exception: the caller decides what refusal it becomes."""

    location: str
    keyword: str

    def __str__(self) -> str:
        return f"{self.keyword} at {self.location}"


def check_supported(schema: Any, location: str = "$", depth: int = 0) -> None:
    """Raise :class:`SchemaNotSupported` for a keyword this module does not judge."""
    if depth > _MAX_DEPTH:
        raise SchemaNotSupported("depth", location)
    if schema is True or schema is False:
        return
    if not isinstance(schema, Mapping):
        raise SchemaNotSupported("schema_not_object", location)
    for keyword in schema:
        if keyword not in _KEYWORDS:
            raise SchemaNotSupported(str(keyword), location)
    declared = schema.get("type")
    for name in (declared if isinstance(declared, list) else [declared]):
        if name is not None and name not in _TYPES:
            raise SchemaNotSupported("type", location)
    pattern = schema.get("pattern")
    if pattern is not None:
        try:
            re.compile(pattern)
        except (re.error, TypeError):
            raise SchemaNotSupported("pattern", location) from None
    for name, child in (schema.get("properties") or {}).items():
        check_supported(child, f"{location}.{name}", depth + 1)
    additional = schema.get("additionalProperties")
    if isinstance(additional, Mapping):
        check_supported(additional, f"{location}.*", depth + 1)
    if "items" in schema:
        check_supported(schema["items"], f"{location}[]", depth + 1)
    for keyword in ("oneOf", "anyOf"):
        for index, child in enumerate(schema.get(keyword) or ()):
            check_supported(child, f"{location}<{keyword}{index}>", depth + 1)


def _is(value: Any, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer()
        )
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _first(schema: Mapping[str, Any], value: Any, location: str) -> AnswerInvalid | None:
    """The first violation, depth first, in the keyword order below; ``None`` when none."""
    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        if not any(_is(value, name) for name in names):
            return AnswerInvalid(location, "type")
    if "const" in schema and schema["const"] != value:
        return AnswerInvalid(location, "const")
    if "enum" in schema and value not in schema["enum"]:
        return AnswerInvalid(location, "enum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            return AnswerInvalid(location, "minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return AnswerInvalid(location, "maxLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return AnswerInvalid(location, "pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            return AnswerInvalid(location, "minimum")
        if "maximum" in schema and value > schema["maximum"]:
            return AnswerInvalid(location, "maximum")
    if isinstance(value, dict):
        for name in schema.get("required") or ():
            if name not in value:
                return AnswerInvalid(f"{location}.{name}", "required")
        properties = schema.get("properties") or {}
        additional = schema.get("additionalProperties")
        for name, child in value.items():
            if name in properties:
                found = _check(properties[name], child, f"{location}.{name}")
            elif additional is False:
                # The offending name is the answer's, not the schema's: only the parent is named.
                return AnswerInvalid(location, "additionalProperties")
            elif isinstance(additional, Mapping):
                found = _check(additional, child, f"{location}.*")
            else:
                continue
            if found is not None:
                return found
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            return AnswerInvalid(location, "minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            return AnswerInvalid(location, "maxItems")
        if "items" in schema:
            for index, child in enumerate(value):
                found = _check(schema["items"], child, f"{location}[{index}]")
                if found is not None:
                    return found
    if "anyOf" in schema:
        if not any(_check(option, value, location) is None for option in schema["anyOf"]):
            return AnswerInvalid(location, "anyOf")
    if "oneOf" in schema:
        matching = sum(1 for option in schema["oneOf"] if _check(option, value, location) is None)
        if matching != 1:
            return AnswerInvalid(location, "oneOf")
    return None


def _check(schema: Any, value: Any, location: str) -> AnswerInvalid | None:
    if schema is True:
        return None
    if schema is False:
        return AnswerInvalid(location, "false_schema")
    return _first(schema, value, location)


def validate(schema: Any, document: Any) -> AnswerInvalid | None:
    """``None`` when ``document`` satisfies ``schema``, else the first violation."""
    violation = _check(schema, document, "$")
    if violation is None:
        return None
    return AnswerInvalid(violation.location[:_LOCATION_LIMIT], violation.keyword)


def read_answer(schema: Any, output_text: str) -> AnswerInvalid | None:
    """Parse ``output_text`` as one JSON document and hold it to ``schema``.

    ``None`` when it is acceptable. A document that is not JSON, or JSON with trailing
    material, is the violation ``json`` at ``$``; a code fence is therefore refused, as the
    wire contract says (``output_text`` is the bare document)."""
    try:
        document = json.loads(output_text)
    except (ValueError, RecursionError):
        return AnswerInvalid("$", "json")
    return validate(schema, document)
