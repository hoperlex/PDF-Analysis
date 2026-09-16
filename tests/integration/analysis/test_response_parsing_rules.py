"""``analysis.text.response``: reading a reply, including one the provider cut short.

`W10-ANL` mutation sweep, rows RP-01 to RP-10. **All ten were green** across
`tests/integration/analysis_engine`, `tests/integration/analysis_text` and `tests/replay`.
Not one rule in this module could be reddened by anything.

This is the module that decides what survives a truncated reply, which is the status wave 2
made first-class. Its docstring states the rule it exists for: an element that did not finish
serializing "is an element whose evidence list may be missing its second quotation, and a
half-written contradiction reads exactly like a whole one - so it is never salvaged by
patching the JSON, only by requiring each element to parse on its own". `RP-07` makes
`_salvage_array` append a `{}` for the tail it could not decode — the closest thing to
guessing at it — and nothing noticed.

The existing coverage is `test_the_incomplete_tail_of_a_truncated_reply_is_discarded`, which
replays a recorded truncated variant end to end. It asserts the *outcome* of the whole stage
over one fixed reply. `parse_response` is a pure function of a string and a flag, so the
rules are reached here directly with replies built in the test — no recording is added to any
frozen fixture directory.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.analysis.text.response import parse_response

#: Pinned literals. `CATEGORIES` is the closed set; the authority is
#: `db/migrations/versions/20260910_0002_pc01_schema.py` → `FINDING_CATEGORIES`, checked in
#: `test_profile_identity_is_pinned.py`. Written out here rather than imported.
VALID_CATEGORY = "internal_contradiction"
OTHER_VALID_CATEGORY = "explicit_placeholder"


def _observation(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "category": VALID_CATEGORY,
        "finding_text": "Две суммы не сходятся.",
        "recommendation_text": "Сверить показатели.",
        "evidence": [{"page_number": 1, "quote": "Отчёт"}],
    }
    item.update(overrides)
    return item


def _reply(*observations: dict[str, Any]) -> str:
    return json.dumps({"observations": list(observations)}, ensure_ascii=False)


# --- the well-formed reply ----------------------------------------------------------


def test_a_complete_reply_yields_its_observations_and_is_not_salvaged() -> None:
    parsed = parse_response(_reply(_observation(), _observation()), truncated=False)
    assert len(parsed.observations) == 2
    assert parsed.salvaged is False
    assert parsed.malformed_count == 0
    assert parsed.observations[0].category == VALID_CATEGORY
    assert parsed.observations[0].evidence[0].page_number == 1
    assert parsed.observations[0].evidence[0].quote == "Отчёт"


def test_both_declared_categories_are_accepted() -> None:
    parsed = parse_response(
        _reply(_observation(), _observation(category=OTHER_VALID_CATEGORY)), truncated=False
    )
    assert [o.category for o in parsed.observations] == [VALID_CATEGORY, OTHER_VALID_CATEGORY]


# --- RP-08: the provider's stop reason is authoritative ------------------------------


def test_a_complete_json_reply_is_salvaged_when_the_provider_says_it_was_cut_short() -> None:
    """RP-08. A reply can be syntactically complete and still have been cut short."""
    complete = _reply(_observation())
    assert parse_response(complete, truncated=True).salvaged is True
    assert parse_response(complete, truncated=False).salvaged is False


# --- RP-07: the incomplete tail is discarded, never guessed at -----------------------


def test_an_unfinished_trailing_element_is_discarded_and_not_replaced() -> None:
    """RP-07. Two complete elements survive; the half-written third does not become one.

    The expected count is the literal 2, not `len(something the module produced)`.
    """
    whole = _reply(_observation(), _observation())
    cut = whole[: whole.rindex("]")] + ', {"category": "internal_contradiction", "find'
    parsed = parse_response(cut, truncated=True)
    assert len(parsed.observations) == 2
    assert parsed.malformed_count == 0
    assert parsed.salvaged is True


def test_a_reply_cut_before_any_element_completes_yields_nothing() -> None:
    cut = '{"observations": [{"category": "internal_cont'
    parsed = parse_response(cut, truncated=True)
    assert len(parsed.observations) == 0
    assert parsed.salvaged is True


def test_a_reply_with_no_observations_key_yields_nothing() -> None:
    parsed = parse_response('{"result": "nothing to report"}', truncated=False)
    assert len(parsed.observations) == 0
    assert parsed.salvaged is True


def test_a_reply_that_is_not_json_at_all_yields_nothing() -> None:
    parsed = parse_response("I could not complete this task.", truncated=False)
    assert len(parsed.observations) == 0
    assert parsed.salvaged is True


# --- RP-01 to RP-06, RP-09, RP-10: a proposal is dropped and counted, never repaired --


@pytest.mark.parametrize(
    ("label", "proposal"),
    [
        ("category_absent", _observation(category=None)),
        ("category_unknown", _observation(category="unsupported_claim")),
        ("category_wrong_case", _observation(category="INTERNAL_CONTRADICTION")),
        ("finding_not_a_string", _observation(finding_text=42)),
        ("finding_blank", _observation(finding_text="   ")),
        ("finding_empty", _observation(finding_text="")),
        ("recommendation_not_a_string", _observation(recommendation_text=None)),
        ("recommendation_blank", _observation(recommendation_text="\t\n")),
        ("evidence_not_a_list", _observation(evidence={"page_number": 1, "quote": "x"})),
        ("evidence_empty", _observation(evidence=[])),
        ("evidence_item_not_a_dict", _observation(evidence=["Отчёт"])),
        ("page_number_a_string", _observation(evidence=[{"page_number": "1", "quote": "Отчёт"}])),
        ("page_number_a_bool", _observation(evidence=[{"page_number": True, "quote": "Отчёт"}])),
        ("page_number_absent", _observation(evidence=[{"quote": "Отчёт"}])),
        ("quote_empty", _observation(evidence=[{"page_number": 1, "quote": ""}])),
        ("quote_not_a_string", _observation(evidence=[{"page_number": 1, "quote": 5}])),
        ("quote_absent", _observation(evidence=[{"page_number": 1}])),
    ],
)
def test_a_proposal_that_does_not_satisfy_the_shape_is_dropped_and_counted(
    label: str, proposal: dict[str, Any]
) -> None:
    """RP-01 to RP-06 and RP-09.

    Both halves matter and are asserted together: the proposal must **not** appear among
    the observations, and it must be **counted** as malformed. A rule that dropped it
    without counting would pass a test that only checked the first.
    """
    parsed = parse_response(_reply(proposal), truncated=False)
    assert len(parsed.observations) == 0, label
    assert parsed.malformed_count == 1, label


def test_a_non_dict_element_is_dropped_and_counted() -> None:
    """RP-10."""
    reply = json.dumps({"observations": ["не объект", 42, None, []]})
    parsed = parse_response(reply, truncated=False)
    assert len(parsed.observations) == 0
    assert parsed.malformed_count == 4


def test_a_page_number_of_true_is_not_read_as_page_one() -> None:
    """RP-05, stated on its own because `isinstance(True, int)` is `True` in Python.

    Without the explicit `isinstance(page, bool)` exclusion, `True` becomes page 1 and a
    proposal that named no page at all acquires one.
    """
    parsed = parse_response(
        _reply(_observation(evidence=[{"page_number": True, "quote": "Отчёт"}])), truncated=False
    )
    assert parsed.observations == ()
    assert parsed.malformed_count == 1


def test_one_malformed_proposal_does_not_discard_the_valid_ones() -> None:
    """The negative half: dropping is per-proposal, not per-reply."""
    parsed = parse_response(
        _reply(_observation(), _observation(category="unsupported_claim"), _observation()),
        truncated=False,
    )
    assert len(parsed.observations) == 2
    assert parsed.malformed_count == 1


def test_an_observation_keeps_every_evidence_item_it_declared() -> None:
    proposal = _observation(
        evidence=[
            {"page_number": 1, "quote": "Отчёт"},
            {"page_number": 2, "quote": "Выручка"},
        ]
    )
    parsed = parse_response(_reply(proposal), truncated=False)
    assert len(parsed.observations[0].evidence) == 2
    assert parsed.observations[0].evidence[1].page_number == 2
    assert parsed.observations[0].evidence[1].quote == "Выручка"


def test_one_bad_evidence_item_drops_the_whole_observation() -> None:
    """An observation is not published with a silently shortened evidence list."""
    proposal = _observation(
        evidence=[{"page_number": 1, "quote": "Отчёт"}, {"page_number": 2, "quote": ""}]
    )
    parsed = parse_response(_reply(proposal), truncated=False)
    assert len(parsed.observations) == 0
    assert parsed.malformed_count == 1
