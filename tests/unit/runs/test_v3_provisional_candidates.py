"""``provisional_publication_candidates``: which accepted proposals become publication candidates.

Only a proposal that passed both pure gates (it is in ``grounding.accepted``) and cites only
provisional topics (its ordinal is in ``provisional_proposal_ordinals``) yields a candidate. A
withheld one, a rejected one and an accepted non-normative one yield none. Pure: the review is built
from plain objects, so each rule is reached on purpose.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.findings.public import V3PublicationCandidate
from auditmanager.runs.v3_citations import (
    V3BetaCitationReview, V3CorpusCitationRefused, provisional_publication_candidates,
)


def _accepted(ordinal: int, *, cited: bool = True, category: str = "evacuation") -> SimpleNamespace:
    anchor = SimpleNamespace(page_number=7, quote=f"quote {ordinal}", char_start=10, char_end=19, block_id=None)
    proposal = SimpleNamespace(
        category=category, finding_text=f"text {ordinal}", recommendation_text="advice",
        proposed_severity="operational", required_value="1,4 м", stated_value="1,2 м",
    )
    citation = SimpleNamespace(label="N1")
    return SimpleNamespace(
        proposal_ordinal=ordinal, proposal=proposal, evidence=(anchor,),
        norm_citations=(citation,) if cited else (),
    )


def _review(accepted, provisional, withheld=()) -> V3BetaCitationReview:
    return V3BetaCitationReview(
        request=None, evaluation=SimpleNamespace(grounding=SimpleNamespace(accepted=tuple(accepted), rejected=())),
        source_policy_sha256="0" * 64, scenario="s", numeric_output_policy="expert_review_required",
        topics=(), provisional_proposal_ordinals=tuple(provisional), withheld_proposal_ordinals=tuple(withheld),
    )


def test_only_the_provisional_ordinals_become_candidates_in_proposal_order() -> None:
    review = _review([_accepted(0), _accepted(1), _accepted(2), _accepted(3, cited=False)], [2, 0], [1])
    candidates = provisional_publication_candidates(review)
    assert [c.finding_text for c in candidates] == ["text 0", "text 2"]
    assert all(isinstance(c, V3PublicationCandidate) for c in candidates)
    assert candidates[0].evidence[0].quote == "quote 0" and candidates[0].required_value == "1,4 м"


def test_no_provisional_ordinal_means_no_candidate() -> None:
    assert provisional_publication_candidates(_review([_accepted(0)], [], [0])) == ()


def test_a_withheld_proposal_cannot_also_be_provisional() -> None:
    with pytest.raises(V3CorpusCitationRefused, match="provisional_ordinal_not_accepted"):
        provisional_publication_candidates(_review([_accepted(0)], [0], [0]))


def test_a_provisional_ordinal_that_was_not_accepted_by_the_gates_is_refused() -> None:
    with pytest.raises(V3CorpusCitationRefused, match="provisional_ordinal_not_accepted"):
        provisional_publication_candidates(_review([_accepted(0)], [0, 5]))


def test_a_repeated_ordinal_is_refused() -> None:
    with pytest.raises(V3CorpusCitationRefused, match="provisional_ordinal_not_accepted"):
        provisional_publication_candidates(_review([_accepted(0)], [0, 0]))


def test_a_candidate_without_its_values_is_refused() -> None:
    accepted = _accepted(0)
    accepted.proposal.stated_value = None
    with pytest.raises(V3CorpusCitationRefused, match="normative_value_missing"):
        provisional_publication_candidates(_review([accepted], [0]))


def test_only_a_beta_review_is_accepted() -> None:
    with pytest.raises(V3CorpusCitationRefused, match="beta_review_required"):
        provisional_publication_candidates(object())  # type: ignore[arg-type]
