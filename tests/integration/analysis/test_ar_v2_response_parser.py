"""Only complete, structurally valid AR v2 proposals survive parsing."""

from __future__ import annotations

import copy
import json

import pytest

from auditmanager.analysis.profiles.ar_v2.response import V2ResponseError, parse_response


def _proposal() -> dict[str, object]:
    return {
        "category": "dimensions",
        "finding_text": "Для одной стены указаны разные размеры.",
        "recommendation_text": "Согласовать размер стены в плане и ведомости.",
        "proposed_severity": "operational",
        "evidence": [
            {"page_number": 2, "quote": "Стена А — 200 мм"},
            {"page_number": 5, "quote": "Стена А — 250 мм"},
        ],
    }


def _reply(*items: object) -> str:
    return json.dumps({"observations": list(items)}, ensure_ascii=False)


def test_valid_proposal_keeps_both_quotes_and_only_proposes_severity() -> None:
    parsed = parse_response(_reply(_proposal()), truncated=False)
    assert parsed.salvaged is False
    assert parsed.malformed_count == 0
    assert len(parsed.observations) == 1
    observation = parsed.observations[0]
    assert observation.category == "dimensions"
    assert observation.proposed_severity == "operational"
    assert [(item.page_number, item.quote) for item in observation.evidence] == [
        (2, "Стена А — 200 мм"), (5, "Стена А — 250 мм")
    ]
    assert not hasattr(observation, "decided_severity")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "normative_refs"),
        ("proposed_severity", "urgent"),
        ("finding_text", ""),
        ("recommendation_text", " "),
        ("finding_text", "x" * 4001),
        ("evidence", []),
        ("evidence", [{"page_number": True, "quote": "есть"}]),
        ("evidence", [{"page_number": 0, "quote": "есть"}]),
        ("evidence", [{"page_number": 1, "quote": " "}]),
        ("evidence", [{"page_number": 1, "quote": "есть", "offset": 0}]),
    ],
)
def test_malformed_complete_proposal_is_counted_not_repaired(field: str, value: object) -> None:
    invalid = copy.deepcopy(_proposal())
    invalid[field] = value
    parsed = parse_response(_reply(_proposal(), invalid), truncated=False)
    assert len(parsed.observations) == 1
    assert parsed.malformed_count == 1


def test_extra_observation_field_is_rejected() -> None:
    extra = _proposal()
    extra["decided_severity"] = "critical"
    parsed = parse_response(_reply(extra), truncated=False)
    assert parsed.observations == ()
    assert parsed.malformed_count == 1


def test_truncation_salvages_only_complete_elements() -> None:
    first = json.dumps(_proposal(), ensure_ascii=False)
    cut = '{"observations":[' + first + ',{"category":"dimensions","evidence":['
    parsed = parse_response(cut, truncated=True)
    assert len(parsed.observations) == 1
    assert parsed.malformed_count == 0
    assert parsed.salvaged is True

    incomplete_first = '{"observations":[{"category":"dimensions","evidence":['
    empty = parse_response(incomplete_first, truncated=True)
    assert empty.observations == ()
    assert empty.salvaged is True


def test_malformed_without_truncation_and_wrong_envelope_fail_loudly() -> None:
    with pytest.raises(V2ResponseError, match="malformed_untruncated_response"):
        parse_response('{"observations":[', truncated=False)
    with pytest.raises(V2ResponseError, match="invalid_response_envelope"):
        parse_response('{"observations":[],"verdict":"accepted"}', truncated=False)
    with pytest.raises(V2ResponseError, match="invalid_response_envelope"):
        parse_response('{"observations":null}', truncated=False)


def test_provider_truncation_flag_is_reported_even_for_valid_json() -> None:
    parsed = parse_response(_reply(_proposal()), truncated=True)
    assert len(parsed.observations) == 1
    assert parsed.salvaged is True
