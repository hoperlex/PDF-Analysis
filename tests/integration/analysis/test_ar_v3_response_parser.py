"""Only complete, correctly partitioned v3 model proposals survive parsing."""

from __future__ import annotations

import copy
import json

import pytest

from auditmanager.analysis.profiles.ar_v3.response import V3ResponseError, parse_response


def _base(category: str = "dimensions") -> dict[str, object]:
    return {
        "category": category,
        "finding_text": "Указанное значение требует проверки.",
        "recommendation_text": "Сверить с исходными данными.",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 2, "quote": "Ширина прохода 1,2 м"}],
    }


def _norm() -> dict[str, object]:
    return {
        **_base("evacuation"),
        "norm_citations": [{
            "label": "N1", "quote": "Минимальная ширина прохода составляет 1,4 м",
        }],
        "required_value": "1,4 м",
        "stated_value": "1,2 м",
    }


def _reply(*items: object) -> str:
    return json.dumps({"observations": list(items)}, ensure_ascii=False)


def test_parses_two_disjoint_proposal_shapes_without_granting_authority() -> None:
    parsed = parse_response(_reply(_base(), _norm()), truncated=False)
    assert parsed.malformed_count == 0
    assert parsed.salvaged is False
    ordinary, normative = parsed.observations
    assert ordinary.norm_citations is None
    assert ordinary.required_value is None and ordinary.stated_value is None
    assert normative.category == "evacuation"
    assert [(c.label, c.quote) for c in normative.norm_citations or ()] == [
        ("N1", "Минимальная ширина прохода составляет 1,4 м"),
    ]
    assert (normative.required_value, normative.stated_value) == ("1,4 м", "1,2 м")
    assert not hasattr(normative, "finding_uid")
    assert not hasattr(normative, "state")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("norm_citations", []),
        ("norm_citations", [_norm()["norm_citations"][0]] * 6),
        ("norm_citations", [{"label": "N0", "quote": "Минимальная ширина прохода составляет 1,4 м"}]),
        ("norm_citations", [{"label": "N1", "quote": "слишком коротко"}]),
        ("norm_citations", [{"label": "N1", "quote": "x" * 1001}]),
        ("norm_citations", [{"label": "N1", "quote": "x" * 20, "offset": 0}]),
        ("required_value", None),
        ("required_value", " "),
        ("required_value", "x" * 201),
        ("stated_value", ""),
        ("evidence", [{"page_number": True, "quote": "есть"}]),
        ("evidence", [{"page_number": 0, "quote": "есть"}]),
        ("evidence", [{"page_number": 1, "quote": "x" * 2001}]),
        ("category", "normative_refs"),
        ("proposed_severity", "urgent"),
    ],
)
def test_bad_normative_fields_drop_only_that_complete_proposal(field: str, value: object) -> None:
    bad = copy.deepcopy(_norm())
    bad[field] = value
    parsed = parse_response(_reply(_base(), bad), truncated=False)
    assert len(parsed.observations) == 1
    assert parsed.observations[0].category == "dimensions"
    assert parsed.malformed_count == 1


def test_missing_norm_fields_and_nonnormative_norm_fields_are_refused() -> None:
    missing = _norm()
    del missing["stated_value"]
    smuggled = {**_base(), "norm_citations": []}
    null_smuggled = {**_base(), "required_value": None}
    parsed = parse_response(_reply(missing, smuggled, null_smuggled), truncated=False)
    assert parsed.observations == ()
    assert parsed.malformed_count == 3


def test_truncation_keeps_only_whole_initial_proposals() -> None:
    initial = json.dumps(_base(), ensure_ascii=False)
    cut = '{"observations":[' + initial + ',{"category":"evacuation","norm_citations":['
    parsed = parse_response(cut, truncated=True)
    assert [item.category for item in parsed.observations] == ["dimensions"]
    assert parsed.malformed_count == 0
    assert parsed.salvaged is True
    with pytest.raises(V3ResponseError, match="malformed_untruncated_response"):
        parse_response(cut, truncated=False)
    complete_but_flagged = parse_response(_reply(_norm()), truncated=True)
    assert complete_but_flagged.salvaged is True


def test_wrong_envelope_duplicate_keys_and_input_types_fail_closed() -> None:
    with pytest.raises(V3ResponseError, match="invalid_response_envelope"):
        parse_response('{"observations":[],"verdict":"accepted"}', truncated=False)
    with pytest.raises(V3ResponseError, match="invalid_response_envelope"):
        parse_response('{"observations":null}', truncated=False)
    with pytest.raises(V3ResponseError, match="malformed_untruncated_response"):
        parse_response('{"observations":[],"observations":[]}', truncated=False)
    with pytest.raises(V3ResponseError, match="invalid_response_input"):
        parse_response(_reply(), truncated=1)  # type: ignore[arg-type]
