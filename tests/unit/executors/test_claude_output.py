"""``claude -p`` output parsing and the fail-closed model identity (`R-133`, `EXEC-SSH-01`).

The model must come from the per-model breakdown (``modelUsage``) or a ``system/init`` message.
Zero, several or conflicting models raise an identity error: the parser never guesses.
"""

from __future__ import annotations

import json

import pytest

from auditmanager.executors.claude_output import (
    ClaudeOutputError,
    ClaudeResult,
    ModelIdentityError,
    parse_claude_output,
)


def result_doc(**overrides) -> dict:
    document = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1234,
        "num_turns": 1,
        "result": '{"verdict": "ok"}',
        "session_id": "s-1",
        "total_cost_usd": 0.0123,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "modelUsage": {"claude-sonnet-5": {"inputTokens": 10, "outputTokens": 5, "costUSD": 0.0123}},
    }
    document.update(overrides)
    return document


INIT = {"type": "system", "subtype": "init", "model": "claude-sonnet-5", "tools": [], "mcp_servers": []}


def test_one_model_in_the_breakdown_is_the_reported_model() -> None:
    parsed = parse_claude_output(json.dumps(result_doc()))
    assert parsed == ClaudeResult('{"verdict": "ok"}', "claude-sonnet-5")
    text, model = parsed  # a plain tuple for callers
    assert (text, model) == ('{"verdict": "ok"}', "claude-sonnet-5")


@pytest.mark.parametrize("shape", ["text", "bytes", "padded", "object"])
def test_the_document_may_be_text_bytes_or_an_already_decoded_object(shape: str) -> None:
    document = result_doc()
    value = {
        "text": json.dumps(document),
        "bytes": json.dumps(document, ensure_ascii=False).encode("utf-8"),
        "padded": "\n  " + json.dumps(document) + "\n\n",
        "object": document,
    }[shape]
    assert parse_claude_output(value).reported_model == "claude-sonnet-5"


def test_the_snake_case_spelling_is_accepted_too() -> None:
    document = result_doc()
    document["model_usage"] = document.pop("modelUsage")
    assert parse_claude_output(document).reported_model == "claude-sonnet-5"


def test_a_dated_model_id_is_returned_exactly_as_reported() -> None:
    document = result_doc(modelUsage={"claude-sonnet-5-20261001": {}})
    assert parse_claude_output(document).reported_model == "claude-sonnet-5-20261001"


@pytest.mark.parametrize("usage", [{}, None])
def test_no_model_in_the_breakdown_is_an_identity_error(usage) -> None:
    document = result_doc()
    if usage is None:
        del document["modelUsage"]
    else:
        document["modelUsage"] = usage
    with pytest.raises(ModelIdentityError):
        parse_claude_output(document)


def test_a_top_level_model_field_is_not_evidence_and_is_never_used() -> None:
    document = result_doc(model="claude-sonnet-5")
    del document["modelUsage"]
    with pytest.raises(ModelIdentityError):
        parse_claude_output(document)


def test_two_models_in_the_breakdown_are_an_identity_error_that_lists_both() -> None:
    document = result_doc(modelUsage={"claude-sonnet-5": {}, "claude-haiku-5": {}})
    with pytest.raises(ModelIdentityError) as raised:
        parse_claude_output(document)
    assert raised.value.candidates == ("claude-haiku-5", "claude-sonnet-5")


@pytest.mark.parametrize("usage", [{"": {}}, {"  ": {}}, ["claude-sonnet-5"], "claude-sonnet-5"])
def test_a_malformed_breakdown_is_refused(usage) -> None:
    with pytest.raises(ClaudeOutputError):
        parse_claude_output(result_doc(modelUsage=usage))


def test_both_spellings_must_agree() -> None:
    document = result_doc(model_usage={"claude-opus-5": {}})
    with pytest.raises(ModelIdentityError):
        parse_claude_output(document)
    document = result_doc(model_usage={"claude-sonnet-5": {"x": 1}})
    assert parse_claude_output(document).reported_model == "claude-sonnet-5"


def test_stream_json_messages_use_the_system_init_model() -> None:
    document = result_doc()
    del document["modelUsage"]
    messages = [INIT, {"type": "assistant", "message": {"content": []}}, document]
    assert parse_claude_output(messages) == ClaudeResult('{"verdict": "ok"}', "claude-sonnet-5")


def test_stream_json_as_json_lines_text() -> None:
    document = result_doc()
    del document["modelUsage"]
    lines = "\n".join(json.dumps(message) for message in [INIT, document]) + "\n"
    assert parse_claude_output(lines.encode()).reported_model == "claude-sonnet-5"


def test_stream_json_init_and_breakdown_must_agree() -> None:
    assert parse_claude_output([INIT, result_doc()]).reported_model == "claude-sonnet-5"
    with pytest.raises(ModelIdentityError) as raised:
        parse_claude_output([{**INIT, "model": "claude-opus-5"}, result_doc()])
    assert raised.value.candidates == ("claude-opus-5", "claude-sonnet-5")


def test_stream_json_with_two_init_models_or_none_is_an_identity_error() -> None:
    document = result_doc()
    del document["modelUsage"]
    with pytest.raises(ModelIdentityError):
        parse_claude_output([INIT, {**INIT, "model": "claude-opus-5"}, document])
    with pytest.raises(ModelIdentityError):
        parse_claude_output([{"type": "system", "subtype": "hooks"}, document])
    with pytest.raises(ModelIdentityError):
        parse_claude_output([{"type": "system", "subtype": "init"}, document])


def test_an_empty_breakdown_is_not_rescued_by_an_init_model() -> None:
    with pytest.raises(ModelIdentityError):
        parse_claude_output([INIT, result_doc(modelUsage={})])


@pytest.mark.parametrize(
    "overrides",
    [
        {"is_error": True},
        {"subtype": "error_max_turns"},
        {"subtype": "error_during_execution"},
    ],
)
def test_an_unsuccessful_run_is_refused_without_echoing_its_content(overrides: dict) -> None:
    with pytest.raises(ClaudeOutputError) as raised:
        parse_claude_output(result_doc(result="DOCUMENT TEXT", **overrides))
    assert "DOCUMENT TEXT" not in str(raised.value)


def test_a_missing_or_non_text_result_is_refused() -> None:
    document = result_doc()
    del document["result"]
    with pytest.raises(ClaudeOutputError):
        parse_claude_output(document)
    with pytest.raises(ClaudeOutputError):
        parse_claude_output(result_doc(result={"verdict": "ok"}))


@pytest.mark.parametrize(
    "garbage",
    [b"", b"   ", b"not json", b"\xff\xfe", "[]", "[1, 2]", "3", '"text"', "null", b'{"type": "assistant"}'],
)
def test_garbage_is_a_parse_error(garbage) -> None:
    with pytest.raises(ClaudeOutputError):
        parse_claude_output(garbage)


def test_more_than_one_result_message_is_refused() -> None:
    with pytest.raises(ClaudeOutputError):
        parse_claude_output([INIT, result_doc(), result_doc()])


def test_a_json_line_that_is_not_json_poisons_the_whole_stream() -> None:
    lines = json.dumps(INIT) + "\nnoise\n" + json.dumps(result_doc())
    with pytest.raises(ClaudeOutputError):
        parse_claude_output(lines)


def test_the_result_text_is_returned_verbatim() -> None:
    text = '  {"a": 1}\né中 '
    assert parse_claude_output(result_doc(result=text)).result_text == text
