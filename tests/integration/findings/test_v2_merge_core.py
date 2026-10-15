"""W56a's pure merge rule, without a provider, database or stage executor."""

from __future__ import annotations

import pytest

from auditmanager.analysis.stages.finding_merge import (
    MergeEvidence, MergeObservation, merge_grounded,
)


def observation(
    ordinal: int, *spans: tuple[int, int, int, str], category: str = "dimensions"
) -> MergeObservation:
    return MergeObservation(
        ordinal, category,
        tuple(MergeEvidence(page, start, end, quote) for page, start, end, quote in spans),
    )


def groups(*items: MergeObservation) -> list[dict]:
    return merge_grounded(items)["groups"]  # type: ignore[return-value]


def test_same_category_overlapping_half_open_spans_link() -> None:
    result = groups(
        observation(2, (1, 5, 15, "one")),
        observation(1, (1, 10, 20, "two")),
    )
    assert result == [{
        "observation_ordinals": [1, 2], "canonical_ordinal": 2,
        "merge_rule_version": "1.0.0",
    }]


def test_touching_endpoints_are_not_overlap() -> None:
    assert len(groups(
        observation(1, (1, 0, 10, "one")), observation(2, (1, 10, 20, "two"))
    )) == 2


def test_short_equal_quotes_do_not_link_distant_spans() -> None:
    assert len(groups(
        observation(1, (1, 0, 15, "Короткая цитата")),
        observation(2, (1, 40, 55, "Короткая цитата")),
    )) == 2


def test_long_equal_quotes_link_on_one_page_after_normalisation() -> None:
    assert groups(
        observation(1, (1, 0, 30, "ПОМЕЩЁНИЕ А,  ПЛОЩАДЬ 20 М2")),
        observation(2, (1, 80, 110, "помеще\u0308ние а, площадь   20 м2")),
    )[0]["observation_ordinals"] == [1, 2]


def test_equal_quotes_on_different_pages_do_not_link() -> None:
    quote = "Помещение имеет площадь двадцать метров"
    assert len(groups(
        observation(1, (1, 0, 40, quote)), observation(2, (2, 0, 40, quote))
    )) == 2


def test_different_categories_do_not_link_even_with_equal_spans_and_quotes() -> None:
    quote = "Помещение имеет площадь двадцать метров"
    assert len(groups(
        observation(1, (1, 0, 40, quote), category="dimensions"),
        observation(2, (1, 0, 40, quote), category="layout"),
    )) == 2


def test_overlap_chain_is_one_connected_component() -> None:
    assert groups(
        observation(3, (1, 18, 30, "third")),
        observation(1, (1, 0, 10, "first")),
        observation(2, (1, 8, 20, "second")),
    )[0]["observation_ordinals"] == [1, 2, 3]


def test_one_observation_with_two_evidence_items_bridges_components() -> None:
    assert groups(
        observation(1, (1, 0, 10, "first")),
        observation(2, (1, 5, 15, "middle"), (2, 50, 60, "bridge")),
        observation(3, (2, 55, 65, "last")),
    )[0]["observation_ordinals"] == [1, 2, 3]


def test_canonical_member_uses_earliest_page_then_span_then_ordinal() -> None:
    result = groups(
        observation(9, (2, 0, 30, "The exact matching quotation is long enough"),
                    (1, 40, 50, "late")),
        observation(4, (1, 40, 70, "overlap")),
        observation(2, (1, 40, 60, "same start")),
    )
    assert result[0]["canonical_ordinal"] == 2


def test_input_permutation_cannot_change_artifact_or_discard_a_member() -> None:
    items = (
        observation(8, (2, 0, 10, "other")),
        observation(3, (1, 0, 10, "first")),
        observation(5, (1, 5, 15, "second")),
    )
    first = merge_grounded(items)
    assert first == merge_grounded(tuple(reversed(items)))
    assert first["artifact_role"] == "findings.merged"
    assert first["artifact_version"] == "1.0.0"
    assert [group["observation_ordinals"] for group in first["groups"]] == [[3, 5], [8]]
    assert {member for group in first["groups"] for member in group["observation_ordinals"]} == {3, 5, 8}


def test_empty_grounded_sequence_has_an_empty_artifact() -> None:
    assert merge_grounded(()) == {
        "artifact_role": "findings.merged", "artifact_version": "1.0.0", "groups": [],
    }


@pytest.mark.parametrize("items,reason", [
    ((observation(1, (1, 0, 3, "a")), observation(1, (1, 5, 8, "b"))), "distinct"),
    ((observation(-1, (1, 0, 3, "a")),), "nonnegative"),
    ((observation(1),), "no grounded evidence"),
    ((observation(1, (0, 0, 3, "a")),), "invalid page"),
    ((observation(1, (1, 3, 3, "a")),), "invalid evidence span"),
    ((observation(1, (1, 0, 3, "")),), "empty evidence quote"),
])
def test_malformed_observation_is_refused(items, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        merge_grounded(items)
