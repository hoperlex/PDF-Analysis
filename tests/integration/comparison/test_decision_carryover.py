"""Exact selection and refusal rules for the W59 pure carryover preparation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.comparison.decision_carryover import (
    ConfirmedCarryoverPlan,
    DecisionCarryoverRefused,
    MAX_CARRYOVER_MATCHES,
    MatchedDecision,
    confirm_decision_carryover,
    offer_decision_carryover,
)
from auditmanager.comparison.finding_match_suggestions import MAX_FINDINGS_PER_RUN


def _id(prefix: str, suffix: str) -> str:
    return f"{prefix}_01M25P3TH08VVTTGJRXYBZZ7R{suffix}"


EXPERT = _id("usr", "P")
_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _numbered_id(prefix: str, number: int) -> str:
    return _id(prefix, "P")[:-2] + _ULID_ALPHABET[number // 32] + _ULID_ALPHABET[number % 32]


def _match(suffix: str = "P", **changes: object) -> MatchedDecision:
    values: dict[str, object] = dict(
        comparison_id=_id("cmp", "P"),
        source_version_uid=_id("ver", "P"),
        target_version_uid=_id("ver", "Q"),
        source_finding_uid=_id("fnd", suffix),
        target_finding_uid=_id("fnd", "R" if suffix == "P" else "S"),
        source_decision_id=_id("dec", suffix),
        source_current_verdict="accepted",
        source_event_count=1,
        target_event_count=0,
        matching_revision=3,
        matching_evidence_sha256="a" * 64,
    )
    values.update(changes)
    return MatchedDecision(**values)  # type: ignore[arg-type]


def _confirm(
    matches: tuple[MatchedDecision, ...], selected: tuple[str, ...], **changes: object
) -> tuple[ConfirmedCarryoverPlan, ...]:
    values: dict[str, object] = dict(
        current_matches=matches,
        selected_offer_sha256s=selected,
        expert_user_uid=EXPERT,
        actor_roles=frozenset({"expert"}),
    )
    values.update(changes)
    return confirm_decision_carryover(**values)  # type: ignore[arg-type]


def test_offer_is_deterministic_and_keeps_source_provenance_without_writing() -> None:
    first, second = _match("P"), _match("Q", source_current_verdict="rejected")
    offers = offer_decision_carryover((second, first))
    assert offers == offer_decision_carryover((first, second))
    assert [offer.match.source_current_verdict for offer in offers] == ["accepted", "rejected"]
    assert [offer.match.source_decision_id for offer in offers] == [
        first.source_decision_id,
        second.source_decision_id,
    ]
    assert all(len(offer.offer_sha256) == 64 for offer in offers)
    assert offer_decision_carryover(()) == ()


def test_single_and_bulk_selection_require_exact_current_offer() -> None:
    matches = (_match("Q"), _match("P"))
    offers = offer_decision_carryover(matches)
    single = _confirm(matches, (offers[1].offer_sha256,))
    assert single == (ConfirmedCarryoverPlan(offers[1], EXPERT),)
    bulk = _confirm(matches, tuple(reversed([offer.offer_sha256 for offer in offers])))
    assert bulk == tuple(ConfirmedCarryoverPlan(offer, EXPERT) for offer in offers)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"source_current_verdict": "pending"}, "source_verdict_not_decided"),
        ({"source_current_verdict": "needs_manual_review"}, "source_verdict_not_decided"),
        ({"source_event_count": 0}, "source_event_count_invalid"),
        ({"target_event_count": 1}, "target_already_has_events"),
        ({"matching_revision": 0}, "matching_revision_invalid"),
        ({"matching_evidence_sha256": "A" * 64}, "matching_evidence_sha256_invalid"),
        ({"source_version_uid": _id("ver", "Q")}, "same_version"),
        ({"target_finding_uid": _id("fnd", "P")}, "same_finding"),
        ({"source_decision_id": _id("fnd", "P")}, "source_decision_id_invalid"),
    ],
)
def test_unattributable_or_already_decided_matches_refuse(
    change: dict[str, object], reason: str
) -> None:
    with pytest.raises(DecisionCarryoverRefused, match=f"^{reason}$"):
        offer_decision_carryover((_match(**change),))


def test_stale_revision_source_event_or_target_event_refuses_whole_selection() -> None:
    original = _match()
    shown = offer_decision_carryover((original,))[0].offer_sha256
    for current in (
        replace(original, matching_revision=4),
        replace(original, source_event_count=2),
        replace(original, source_decision_id=_id("dec", "Q")),
        replace(original, matching_evidence_sha256="b" * 64),
    ):
        with pytest.raises(DecisionCarryoverRefused, match="^selection_stale_or_unknown$"):
            _confirm((current,), (shown,))
    with pytest.raises(DecisionCarryoverRefused, match="^target_already_has_events$"):
        _confirm((replace(original, target_event_count=1),), (shown,))


def test_bulk_refuses_duplicate_or_ambiguous_matches_and_selection() -> None:
    first = _match()
    shown = offer_decision_carryover((first,))[0].offer_sha256
    with pytest.raises(DecisionCarryoverRefused, match="^match_not_one_to_one$"):
        offer_decision_carryover((first, replace(first, source_decision_id=_id("dec", "Q"))))
    with pytest.raises(DecisionCarryoverRefused, match="^comparison_revision_mismatch$"):
        offer_decision_carryover((first, _match("Q", matching_revision=4)))
    with pytest.raises(DecisionCarryoverRefused, match="^selection_duplicate$"):
        _confirm((first,), (shown, shown))
    with pytest.raises(DecisionCarryoverRefused, match="^selection_stale_or_unknown$"):
        _confirm((first,), (shown, "b" * 64))


def test_only_an_explicit_expert_selection_produces_a_plan() -> None:
    match = _match()
    shown = offer_decision_carryover((match,))[0].offer_sha256
    for roles in (frozenset(), frozenset({"admin"}), frozenset({"expert", "unknown"})):
        with pytest.raises(DecisionCarryoverRefused, match="^expert_role_required$"):
            _confirm((match,), (shown,), actor_roles=roles)
    with pytest.raises(DecisionCarryoverRefused, match="^expert_identity_invalid$"):
        _confirm((match,), (shown,), expert_user_uid=_id("fnd", "P"))
    with pytest.raises(DecisionCarryoverRefused, match="^selection_empty_or_invalid$"):
        _confirm((match,), ())


def test_carryover_batches_are_bounded_before_item_work() -> None:
    assert MAX_CARRYOVER_MATCHES == MAX_FINDINGS_PER_RUN == 200
    with pytest.raises(DecisionCarryoverRefused, match="^matches_too_large$"):
        offer_decision_carryover([object()] * 201)  # type: ignore[list-item]
    match = _match()
    shown = offer_decision_carryover((match,))[0].offer_sha256
    with pytest.raises(DecisionCarryoverRefused, match="^selection_too_large$"):
        _confirm((match,), (shown,) * 201)


def test_exact_200_match_and_selection_boundary_is_repeatable() -> None:
    matches = tuple(
        replace(
            _match(),
            source_finding_uid=_numbered_id("fnd", number),
            target_finding_uid=_numbered_id("fnd", number + 200),
            source_decision_id=_numbered_id("dec", number),
        )
        for number in range(200)
    )
    offers = offer_decision_carryover(matches)
    assert len(offers) == 200
    selected = tuple(offer.offer_sha256 for offer in offers)
    plans = _confirm(matches, selected)
    assert len(plans) == 200
    assert plans == _confirm(tuple(reversed(matches)), tuple(reversed(selected)))
