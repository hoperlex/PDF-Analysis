"""`EXEC-PULL-01`: a runner's answer held to the task's output schema (``executors/answers.py``).

The validator stands in for a JSON Schema library the runtime lock does not carry, so it is held
to the three response schemas the stage actually sends, and every refusal is shown to name a
location and a keyword and nothing of the document.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.analysis.profiles.ar_v2.response_schema import response_schema as ar_v2
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema as ar_v3
from auditmanager.analysis.text.prompt import RESPONSE_SCHEMA
from auditmanager.executors.answers import (
    AnswerInvalid,
    SchemaNotSupported,
    check_supported,
    read_answer,
    validate,
)

SENTINEL = "SENTINEL-DOCUMENT-TEXT-0451"


@pytest.mark.parametrize("schema", [RESPONSE_SCHEMA, ar_v2(), ar_v3()], ids=["v1", "ar_v2", "ar_v3"])
def test_every_response_schema_the_stage_sends_is_judgeable(schema) -> None:
    check_supported(schema)


def test_the_empty_answer_of_the_stage_schema_is_accepted() -> None:
    assert read_answer(RESPONSE_SCHEMA, '{"observations": []}') is None


def test_a_conforming_observation_is_accepted() -> None:
    answer = {"observations": [{
        "category": next(iter(RESPONSE_SCHEMA["properties"]["observations"]["items"]
                              ["properties"]["category"]["enum"])),
        "finding_text": "a", "recommendation_text": "b",
        "evidence": [{"page_number": 1, "quote": "q"}],
    }]}
    assert read_answer(RESPONSE_SCHEMA, json.dumps(answer)) is None


@pytest.mark.parametrize(("answer", "location", "keyword"), [
    ('{}', "$.observations", "required"),
    ('{"observations": {}}', "$.observations", "type"),
    ('{"observations": [], "extra": 1}', "$", "additionalProperties"),
    ('{"observations": [{"category": "nope", "finding_text": "a", '
     '"recommendation_text": "b", "evidence": [{"page_number": 1, "quote": "q"}]}]}',
     "$.observations[0].category", "enum"),
    ('{"observations": [{"category": "x"}]}', "$.observations[0].finding_text", "required"),
    ('{"observations": [{"finding_text": 1}]}', "$.observations[0].category", "required"),
])
def test_a_violation_names_the_first_location_and_keyword(answer, location, keyword) -> None:
    found = read_answer(RESPONSE_SCHEMA, answer)
    assert isinstance(found, AnswerInvalid)
    assert (found.location, found.keyword) == (location, keyword)


@pytest.mark.parametrize("text", [
    "", "not json", "```json\n{\"observations\": []}\n```", '{"observations": []} trailing',
    '{"observations": [],}',
])
def test_text_that_is_not_the_bare_document_is_refused_at_the_root(text: str) -> None:
    found = read_answer(RESPONSE_SCHEMA, text)
    assert found is not None and (found.location, found.keyword) == ("$", "json")


def test_a_violation_never_carries_the_document_text() -> None:
    answer = json.dumps({"observations": [{"category": SENTINEL, "finding_text": SENTINEL}],
                         SENTINEL: SENTINEL})
    found = read_answer(RESPONSE_SCHEMA, answer)
    assert found is not None and SENTINEL not in f"{found} {found!r}"
    # A name the answer invented is reported at its parent, never by name.
    invented = read_answer(RESPONSE_SCHEMA, json.dumps({"observations": [], SENTINEL: 1}))
    assert invented is not None and SENTINEL not in f"{invented} {invented!r}"
    assert invented.location == "$"


@pytest.mark.parametrize(("schema", "document", "keyword"), [
    ({"type": "string", "minLength": 2}, "a", "minLength"),
    ({"type": "string", "maxLength": 1}, "ab", "maxLength"),
    ({"type": "string", "pattern": "^a"}, "ba", "pattern"),
    ({"type": "integer", "minimum": 1}, 0, "minimum"),
    ({"type": "integer", "maximum": 1}, 2, "maximum"),
    ({"type": "array", "minItems": 1}, [], "minItems"),
    ({"type": "array", "maxItems": 1}, [1, 2], "maxItems"),
    ({"type": "integer"}, True, "type"),
    ({"type": "integer"}, 1.5, "type"),
    ({"const": 1}, 2, "const"),
    ({"oneOf": [{"type": "string"}, {"type": "string"}]}, "x", "oneOf"),
    ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, [], "anyOf"),
])
def test_each_supported_keyword_can_refuse(schema, document, keyword) -> None:
    found = validate(schema, document)
    assert found is not None and found.keyword == keyword


@pytest.mark.parametrize(("schema", "document"), [
    ({"type": "integer"}, 2.0),
    ({"type": ["string", "null"]}, None),
    ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, 3),
    ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "x"),
    ({"type": "object", "additionalProperties": {"type": "integer"}}, {"a": 1}),
    ({"title": "t", "description": "d", "default": 1, "type": "string"}, "x"),
])
def test_each_supported_keyword_can_accept(schema, document) -> None:
    assert validate(schema, document) is None


@pytest.mark.parametrize("schema", [
    {"type": "object", "if": {}}, {"$ref": "#/$defs/x"}, {"allOf": []}, {"format": "date"},
    {"type": "object", "properties": {"a": {"not": {}}}}, {"type": "nope"},
    {"pattern": "("}, [],
])
def test_a_keyword_this_validator_does_not_judge_is_refused_not_waved_through(schema) -> None:
    with pytest.raises(SchemaNotSupported):
        check_supported(schema)
