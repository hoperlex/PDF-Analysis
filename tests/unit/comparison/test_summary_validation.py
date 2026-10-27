"""`COMPARE-PERSISTED-SUMMARY-01` (B2): a summary reply is accepted only if every span it cites exists."""

from __future__ import annotations

import json

import pytest

from auditmanager.comparison.summary_prompt import (
    MAX_HUNKS_PER_STATEMENT,
    MAX_STATEMENT_CHARACTERS,
    MAX_STATEMENTS,
)
from auditmanager.comparison.summary_validation import (
    REASON_NOT_JSON,
    REASON_SHAPE,
    REASON_UNKNOWN_HUNK,
    REJECTION_REASONS,
    Statement,
    SummaryRejected,
    parse_reply,
    statements_json,
)

LINK = "sln_01M2545JSD15ETSNNV904XF001"
KNOWN = [f"{LINK}:0", f"{LINK}:1", f"{LINK}:2"]


def _reply(*statements: dict) -> str:
    return json.dumps({"statements": list(statements)}, ensure_ascii=False)


def _statement(text: str = "Размер изменён с 30 на 35.", ids=None) -> dict:
    return {"text": text, "hunk_ids": [KNOWN[1]] if ids is None else ids}


def test_a_well_formed_reply_is_kept_as_the_model_wrote_it() -> None:
    reply = _reply(_statement(), _statement("Изменена отметка изменения.", [KNOWN[0], KNOWN[2]]))
    parsed = parse_reply(reply, KNOWN)
    assert parsed == (
        Statement("Размер изменён с 30 на 35.", (KNOWN[1],)),
        Statement("Изменена отметка изменения.", (KNOWN[0], KNOWN[2])),
    )
    assert statements_json(parsed)[1] == {
        "text": "Изменена отметка изменения.", "hunk_ids": [KNOWN[0], KNOWN[2]],
    }


@pytest.mark.parametrize("unknown", [
    f"{LINK}:3",                                  # a span the input does not have
    "sln_01M2545JSD15ETSNNV904XF999:0",           # a link the input does not have
    f"{LINK}:00",                                 # a spelling that is not the identity
    "",
])
def test_one_unknown_reference_rejects_the_whole_reply(unknown: str) -> None:
    reply = _reply(_statement(), _statement("Ссылка на несуществующее.", [KNOWN[0], unknown]))
    with pytest.raises(SummaryRejected) as caught:
        parse_reply(reply, KNOWN)
    assert caught.value.reason in (REASON_UNKNOWN_HUNK, REASON_SHAPE)


def test_the_unknown_reference_reason_is_named_for_a_well_formed_but_absent_span() -> None:
    with pytest.raises(SummaryRejected) as caught:
        parse_reply(_reply(_statement(ids=[f"{LINK}:7"])), KNOWN)
    assert caught.value.reason == REASON_UNKNOWN_HUNK


@pytest.mark.parametrize("output", ["", "not json", "[1]", "null", "{"])
def test_a_reply_that_is_not_a_json_object_is_rejected_as_such(output: str) -> None:
    with pytest.raises(SummaryRejected) as caught:
        parse_reply(output, KNOWN)
    assert caught.value.reason in (REASON_NOT_JSON, REASON_SHAPE)


@pytest.mark.parametrize("document", [
    {},                                                                  # no statements
    {"statements": []},                                                  # an empty summary
    {"statements": "text"},
    {"statements": [_statement()], "note": "extra"},                     # an extra key
    {"statements": [{"text": "x"}]},                                     # no references
    {"statements": [{"text": "x", "hunk_ids": []}]},                     # a statement anchored to nothing
    {"statements": [{"text": "", "hunk_ids": [KNOWN[0]]}]},
    {"statements": [{"text": " x", "hunk_ids": [KNOWN[0]]}]},
    {"statements": [{"text": "x", "hunk_ids": [KNOWN[0], KNOWN[0]]}]},   # a repeated reference
    {"statements": [{"text": "x", "hunk_ids": [1]}]},
    {"statements": [{"text": "x", "hunk_ids": [KNOWN[0]], "score": 1}]},
    {"statements": [{"text": "A" * (MAX_STATEMENT_CHARACTERS + 1), "hunk_ids": [KNOWN[0]]}]},
    {"statements": [_statement()] * (MAX_STATEMENTS + 1)},
    {"statements": [{"text": "x", "hunk_ids": [f"{LINK}:0"] * (MAX_HUNKS_PER_STATEMENT + 1)}]},
])
def test_a_reply_outside_the_closed_shape_is_rejected(document: dict) -> None:
    with pytest.raises(SummaryRejected) as caught:
        parse_reply(json.dumps(document, ensure_ascii=False), KNOWN)
    assert caught.value.reason == REASON_SHAPE


def test_the_reasons_are_the_closed_vocabulary_the_table_restates() -> None:
    assert REJECTION_REASONS == (REASON_NOT_JSON, REASON_SHAPE, REASON_UNKNOWN_HUNK)
