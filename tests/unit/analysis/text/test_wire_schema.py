"""``to_wire_schema``: the provider-safe wire form of a response schema (`AR-V3-WIRE-SCHEMA-01`).

One case per rule of the function, then the real AR v3 schema, then the safety net: the local v3
parser still rejects what the wire form no longer forbids.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from auditmanager.analysis.profiles.ar_v3.response import ParsedResponse, parse_response
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.text.prompt import CATEGORIES, RESPONSE_SCHEMA, response_schema_for
from auditmanager.analysis.text.wire_schema import to_wire_schema, with_wire_schema

SIX = ("minLength", "maxLength", "minimum", "maxItems", "pattern")
DROPPED = (*SIX, "maximum")

#: Name-bearing mappings: their keys are property names, never keywords.
NAME_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}


def keywords(node: Any) -> list[str]:
    """Every key that is a KEYWORD (a schema position's key), at any depth. Keys of a name map are
    names and are skipped; their values are schemas and are visited."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.append(key)
            if key in NAME_MAPS and isinstance(value, dict):
                for child in value.values():
                    found.extend(keywords(child))
            elif key in ("enum", "const", "required", "default", "examples"):
                continue
            else:
                found.extend(keywords(value))
    elif isinstance(node, list):
        for member in node:
            found.extend(keywords(member))
    return found


def collect(node: Any, keyword: str) -> list[Any]:
    """Every value of ``keyword`` met in a schema position, in document order."""
    found: list[Any] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == keyword:
                found.append(value)
            if key in NAME_MAPS and isinstance(value, dict):
                for child in value.values():
                    found.extend(collect(child, keyword))
            elif key in ("enum", "const", "required", "default", "examples"):
                continue
            else:
                found.extend(collect(value, keyword))
    elif isinstance(node, list):
        for member in node:
            found.extend(collect(member, keyword))
    return found


def names(node: Any) -> list[str]:
    """Every property name declared anywhere in a schema."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for name, child in value.items():
                    found.append(name)
                    found.extend(names(child))
            elif key in ("enum", "const", "required", "default", "examples"):
                continue
            else:
                found.extend(names(value))
    elif isinstance(node, list):
        for member in node:
            found.extend(names(member))
    return found


CLUTTER: dict[str, Any] = {
    "minLength": 1, "maxLength": 9, "minimum": 1, "maximum": 5, "maxItems": 3, "pattern": "^x$",
}


# -- rule 1: a new object, never mutating, idempotent --------------------------------------------


def test_the_result_is_a_new_object_and_the_argument_is_not_changed() -> None:
    schema = response_schema()
    before = copy.deepcopy(schema)
    wire = to_wire_schema(schema)
    assert schema == before, "the argument is never mutated"
    assert wire is not schema
    assert wire != schema, "the real v3 schema does change"


def test_nothing_in_the_result_is_shared_with_the_argument() -> None:
    schema = {"type": "object", "required": ["a"], "properties": {
        "a": {"type": "string", "enum": ["x", "y"], "maxLength": 3}}, "title": "t"}
    before = copy.deepcopy(schema)
    wire = to_wire_schema(schema)
    wire["required"].append("b")
    wire["properties"]["a"]["enum"].append("z")
    wire["properties"]["extra"] = {}
    assert schema == before, "the sealed schema cannot be reached through the wire form"


@pytest.mark.parametrize("schema", [
    response_schema(), RESPONSE_SCHEMA,
    {"oneOf": [{"oneOf": [{"type": "string", **CLUTTER}]}], "anyOf": [{"oneOf": []}]},
    {"properties": {"oneOf": {"oneOf": [{"pattern": "x"}]}, "pattern": {"pattern": "y"}}},
])
def test_applying_it_to_its_own_result_changes_nothing(schema: dict[str, Any]) -> None:
    once = to_wire_schema(schema)
    assert to_wire_schema(once) == once
    assert json.dumps(to_wire_schema(once)) == json.dumps(once)


# -- rule 2: the schema positions ------------------------------------------------------------------


def _at(position: str, inner: dict[str, Any]) -> dict[str, Any]:
    return {
        "root": inner,
        "items": {"type": "array", "items": inner},
        "properties": {"type": "object", "properties": {"field": inner}},
        "anyOf": {"anyOf": [{"type": "null"}, inner]},
        "oneOf": {"oneOf": [{"type": "null"}, inner]},
        "allOf": {"allOf": [inner]},
        "additionalProperties": {"type": "object", "additionalProperties": inner},
    }[position]


def _inner_of(wire: dict[str, Any], position: str) -> dict[str, Any]:
    return {
        "root": lambda: wire,
        "items": lambda: wire["items"],
        "properties": lambda: wire["properties"]["field"],
        "anyOf": lambda: wire["anyOf"][1],
        "oneOf": lambda: wire["anyOf"][1],
        "allOf": lambda: wire["allOf"][0],
        "additionalProperties": lambda: wire["additionalProperties"],
    }[position]()


POSITIONS = ["root", "items", "properties", "anyOf", "oneOf", "allOf", "additionalProperties"]


@pytest.mark.parametrize("position", POSITIONS)
@pytest.mark.parametrize("keyword", DROPPED)
def test_a_provider_refused_constraint_is_removed_in_every_schema_position(
    position: str, keyword: str,
) -> None:
    inner = {"type": "string", keyword: "^x$" if keyword == "pattern" else 2, "description": "kept"}
    cleaned = _inner_of(to_wire_schema(_at(position, inner)), position)
    assert cleaned == {"type": "string", "description": "kept"}


@pytest.mark.parametrize("position", POSITIONS)
def test_one_of_becomes_any_of_in_every_schema_position(position: str) -> None:
    inner = {"oneOf": [{"type": "string", "maxLength": 3}, {"type": "integer", "minimum": 1}]}
    cleaned = _inner_of(to_wire_schema(_at(position, inner)), position)
    assert cleaned == {"anyOf": [{"type": "string"}, {"type": "integer"}]}


def test_one_of_is_replaced_in_place_so_the_key_order_is_kept() -> None:
    wire = to_wire_schema({"type": "array", "oneOf": [{"type": "string"}], "title": "t"})
    assert list(wire) == ["type", "anyOf", "title"]


@pytest.mark.parametrize("value, kept", [(0, True), (1, True), (2, False), (5, False)])
def test_min_items_stays_only_when_it_is_zero_or_one(value: int, kept: bool) -> None:
    wire = to_wire_schema({"type": "array", "minItems": value, "items": {"type": "string"}})
    assert ("minItems" in wire) is kept
    if kept:
        assert wire["minItems"] == value


@pytest.mark.parametrize("value", [True, False, 1.0, "1", None])
def test_min_items_that_is_not_an_int_zero_or_one_is_removed(value: Any) -> None:
    assert "minItems" not in to_wire_schema({"type": "array", "minItems": value})


def test_a_node_with_both_one_of_and_any_of_loses_neither() -> None:
    schema = {"anyOf": [{"type": "string", "maxLength": 3}], "oneOf": [{"type": "integer", "minimum": 1}]}
    wire = to_wire_schema(schema)
    assert "oneOf" not in wire
    assert wire["anyOf"] == [{"type": "string"}]
    assert wire["allOf"] == [{"anyOf": [{"type": "integer"}]}], "both alternatives must still hold"
    assert to_wire_schema(wire) == wire

    with_all_of = to_wire_schema({"allOf": [{"type": "object"}], "anyOf": [{}], "oneOf": [{"type": "null"}]})
    assert with_all_of["allOf"] == [{"type": "object"}, {"anyOf": [{"type": "null"}]}]


# -- rule 3: names are not keywords ----------------------------------------------------------------


def test_a_property_named_like_a_keyword_survives_and_only_its_schema_is_cleaned() -> None:
    schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "pattern": "^a$", "maxLength": 4},
            "oneOf": {"type": "array", "minItems": 3, "items": {"oneOf": [{"type": "string"}]}},
            "maxLength": {"type": "integer", "minimum": 0},
            "minItems": {"type": "integer", "maximum": 9},
            "properties": {"type": "object", "properties": {"pattern": {"pattern": "z"}}},
        },
        "required": ["pattern", "oneOf", "maxLength", "minItems", "properties"],
        "additionalProperties": False,
    }
    wire = to_wire_schema(schema)
    assert list(wire["properties"]) == ["pattern", "oneOf", "maxLength", "minItems", "properties"]
    assert wire["properties"]["pattern"] == {"type": "string"}
    assert wire["properties"]["oneOf"] == {"type": "array", "items": {"anyOf": [{"type": "string"}]}}
    assert wire["properties"]["maxLength"] == {"type": "integer"}
    assert wire["properties"]["minItems"] == {"type": "integer"}
    assert wire["properties"]["properties"] == {
        "type": "object", "properties": {"pattern": {}}}
    assert wire["required"] == schema["required"]


@pytest.mark.parametrize("mapping", ["patternProperties", "$defs", "definitions"])
def test_the_keys_of_the_other_name_mappings_are_names_too(mapping: str) -> None:
    schema = {mapping: {"pattern": {"type": "string", "maxLength": 3}, "oneOf": {"oneOf": [{}]}}}
    wire = to_wire_schema(schema)
    assert wire == {mapping: {"pattern": {"type": "string"}, "oneOf": {"anyOf": [{}]}}}


# -- rule 4: everything else is kept ---------------------------------------------------------------


def test_everything_else_is_kept_as_it_is() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "T", "description": "D",
        "type": ["object", "null"], "default": {"oneOf": 1, "maxLength": 2},
        "examples": [{"pattern": "p"}], "const": {"minimum": 1},
        "properties": {"kind": {"type": "string", "enum": ["a", "b"], "const": "a"}},
        "required": ["kind"], "additionalProperties": False,
        "anyOf": [{"type": "object"}, {"type": "null"}],
    }
    wire = to_wire_schema(schema)
    assert wire == schema
    assert list(wire) == list(schema)


def test_data_valued_keywords_are_not_cleaned() -> None:
    wire = to_wire_schema({"enum": [{"oneOf": 1, "pattern": "p"}, "maxLength"], "const": {"minLength": 3}})
    assert wire == {"enum": [{"oneOf": 1, "pattern": "p"}, "maxLength"], "const": {"minLength": 3}}


# -- rule 5: not a mapping, and the depth ---------------------------------------------------------


@pytest.mark.parametrize("value", [None, True, "x", 3, [{"oneOf": []}], ("a",)])
def test_a_value_that_is_not_a_mapping_is_returned_unchanged(value: Any) -> None:
    assert to_wire_schema(value) is value


def test_the_pull_default_schema_is_a_mapping_and_stays_what_it_is() -> None:
    assert to_wire_schema({"type": "object"}) == {"type": "object"}


def _chain(levels: int) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "string", "maxLength": 1}
    for _ in range(levels):
        node = {"type": "array", "items": node}
    return node


def test_nesting_up_to_64_levels_is_cleaned_and_one_more_is_refused() -> None:
    wire = to_wire_schema(_chain(64))
    leaf: Any = wire
    for _ in range(64):
        leaf = leaf["items"]
    assert leaf == {"type": "string"}
    with pytest.raises(ValueError):
        to_wire_schema(_chain(65))


def test_the_depth_is_counted_through_every_schema_position() -> None:
    node: dict[str, Any] = {"type": "string"}
    for _ in range(40):
        node = {"properties": {"p": {"anyOf": [node]}}}
    # 40 x (properties value + anyOf member) = 80 schema levels
    with pytest.raises(ValueError):
        to_wire_schema(node)


# -- rule 6: the v1 text-analysis schema ----------------------------------------------------------


def test_the_v1_text_analysis_schema_comes_out_equal_down_to_the_bytes() -> None:
    wire = to_wire_schema(RESPONSE_SCHEMA)
    assert wire == RESPONSE_SCHEMA
    assert json.dumps(wire, sort_keys=False) == json.dumps(RESPONSE_SCHEMA, sort_keys=False)
    assert json.dumps(wire, sort_keys=True) == json.dumps(RESPONSE_SCHEMA, sort_keys=True)
    assert wire["properties"]["observations"]["items"]["properties"]["evidence"]["minItems"] == 1


def test_the_widened_three_category_v1_schema_also_comes_out_equal() -> None:
    widened = response_schema_for((*CATEGORIES, "documentation"))
    assert to_wire_schema(widened) == widened


# -- the real AR v3 schema ------------------------------------------------------------------------


def test_the_real_v3_schema_has_no_one_of_and_none_of_the_refused_constraints() -> None:
    sealed = response_schema()
    # the premise (P-01): the sealed schema does use all of them
    sealed_keywords = set(keywords(sealed))
    assert {"oneOf", *DROPPED} - {"maximum"} <= sealed_keywords

    wire = to_wire_schema(sealed)
    left = set(keywords(wire))
    assert not left & {"oneOf", *DROPPED}
    assert "anyOf" in left
    # in no position at all, names or not: the v3 schema declares no property with such a name
    for refused in ("oneOf", *DROPPED):
        assert f'"{refused}"' not in json.dumps(wire)


def test_the_real_v3_schema_keeps_every_required_and_enum_entry_and_every_property() -> None:
    sealed = response_schema()
    wire = to_wire_schema(sealed)
    assert collect(wire, "required") == collect(sealed, "required")
    assert collect(wire, "enum") == collect(sealed, "enum")
    assert collect(wire, "required") and collect(wire, "enum")
    assert collect(wire, "additionalProperties") == collect(sealed, "additionalProperties")
    assert collect(wire, "type") == collect(sealed, "type")
    assert names(wire) == names(sealed)
    wire_items = wire["properties"]["observations"]["items"]
    assert [member["properties"]["category"]["enum"] for member in wire_items["anyOf"]] == [
        member["properties"]["category"]["enum"]
        for member in sealed["properties"]["observations"]["items"]["oneOf"]
    ]


def test_the_real_v3_schema_keeps_min_items_of_one_and_drops_max_items() -> None:
    wire = to_wire_schema(response_schema())
    assert collect(wire, "minItems") == collect(response_schema(), "minItems") == [1, 1, 1]
    assert collect(wire, "maxItems") == []


def test_the_sealed_v3_schema_is_untouched_by_the_conversion() -> None:
    first = response_schema()
    to_wire_schema(first)
    assert first == response_schema(), "response_schema() hands out a fresh sealed tree every time"


# -- the body helper ------------------------------------------------------------------------------


def _body(schema: Any) -> dict[str, Any]:
    return {
        "model": "m", "max_tokens": 5, "system": "s", "messages": [{"role": "user", "content": "u"}],
        "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}},
    }


def test_the_body_helper_replaces_only_the_schema_and_leaves_its_argument_alone() -> None:
    body = _body(response_schema())
    before = copy.deepcopy(body)
    sent = with_wire_schema(body)
    assert body == before
    assert sent is not body
    assert sent["output_config"]["effort"] == "high"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["output_config"]["format"]["schema"] == to_wire_schema(response_schema())
    assert {key: value for key, value in sent.items() if key != "output_config"} == {
        key: value for key, value in body.items() if key != "output_config"}


@pytest.mark.parametrize("body", [
    {"model": "m"}, {"model": "m", "output_config": None},
    {"model": "m", "output_config": {"effort": "high"}},
    {"model": "m", "output_config": {"format": "text"}},
    {"model": "m", "output_config": {"format": {"type": "json_object"}}},
])
def test_a_body_without_a_schema_is_copied_as_it_is(body: dict[str, Any]) -> None:
    sent = with_wire_schema(body)
    assert sent == body and sent is not body


# -- the safety net: the local parser is still the authority --------------------------------------


def _proposal(**change: Any) -> dict[str, Any]:
    base = {
        "category": "dimensions", "finding_text": "Указанное значение требует проверки.",
        "recommendation_text": "Сверить с исходными данными.", "proposed_severity": "operational",
        "evidence": [{"page_number": 2, "quote": "Ширина прохода 1,2 м"}],
    }
    return {**base, **change}


def _norm(**change: Any) -> dict[str, Any]:
    return {
        **_proposal(category="evacuation"),
        "norm_citations": [{"label": "N1", "quote": "Минимальная ширина прохода составляет 1,4 м"}],
        "required_value": "1,4 м", "stated_value": "1,2 м", **change,
    }


def _one_dropped(raw: dict[str, Any]) -> None:
    parsed = parse_response(json.dumps({"observations": [raw]}, ensure_ascii=False), truncated=False)
    assert isinstance(parsed, ParsedResponse)
    assert parsed.observations == () and parsed.malformed_count == 1


@pytest.mark.parametrize(("raw", "constraint"), [
    (_proposal(finding_text="x" * 4001), "maxLength"),
    (_proposal(recommendation_text=""), "minLength"),
    (_proposal(evidence=[{"page_number": 0, "quote": "есть"}]), "minimum"),
    (_proposal(evidence=[{"page_number": 1, "quote": "x" * 2001}]), "maxLength"),
    (_norm(norm_citations=[{"label": "N1", "quote": "Минимальная ширина прохода составляет 1,4 м"}] * 6),
     "maxItems"),
    (_norm(norm_citations=[{"label": "X1", "quote": "Минимальная ширина прохода составляет 1,4 м"}]),
     "pattern"),
    (_norm(norm_citations=[{"label": "N1", "quote": "коротко"}]), "minLength"),
    (_norm(required_value="x" * 201), "maxLength"),
])
def test_the_v3_parser_still_rejects_what_the_wire_schema_no_longer_forbids(
    raw: dict[str, Any], constraint: str,
) -> None:
    wire = to_wire_schema(response_schema())
    members = wire["properties"]["observations"]["items"]["anyOf"]
    assert constraint not in json.dumps(members), "the provider is no longer told this constraint"
    _one_dropped(raw)
