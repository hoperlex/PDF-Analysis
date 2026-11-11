"""`PREC-PASS`: the critic's records of a run, read into the core's inputs (`ADR-0029` decisions 5 and 14, V3).

What is shown, each next to the case that must come out the other way:

* the AI critic of plan v3: ``accept`` and ``needs_human`` veto, ``reject`` and ``borderline`` do not, a record it cannot read is an objection, and a
  candidate outside its window (``not_reviewed``) is not reviewed at all;
* the deterministic critic of plan v2: it **counts as a review** (a finding it reviewed can get «снять»), it **never vetoes** (its ``pass`` is mapped to
  ``accept`` for the expert's eyes and must not become the AI's ``accept``), and a v2 run without its marker has no critic in plan;
* a finding no critic reviewed can never get «снять», in v2 and in v3, and one outside the AI critic's window neither;
* the link of a finding to its candidates (by reference for a candidate-finding, by restated words for a text finding), and the stored projection that
  lets a read evaluate again without the artifact.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.precedents.run_pass.critic_input import (
    DECISION_DETERMINISTIC,
    NO_CRITIC,
    candidates_from_projection,
    critic_projection,
    link,
    link_token,
    possible_norms,
    read_critic_plan,
)
from tests.unit.precedents.builders import advise, corpus, finding

CATEGORY = "dimensions"
WORDS = "Толщина защитного слоя не соответствует проекту."
NDOC = "ndoc_01M2545JSD15ETSNNV904X991K"
NPAR = "npar_01M2545JSD15ETSNNV904X991K"
UID = "fnd_01M2545JSD15ETSNNV904X991K"


def ai_record(decision: str) -> dict[str, Any]:
    return {"input_id": "xri_1", "llm_decision": decision, "explanation": "..."}


def deterministic_record(decision: str = "accept", verdict: str = "pass") -> dict[str, Any]:
    return {"input_id": "xrd_1", "llm_decision": decision, "mode": "deterministic", "model_called": False, "policy": "deterministic-v1",
            "original_verdict": verdict}


def candidate(identity: str = "xobs_a", *, sources: list[str] | None = None, critic: dict[str, Any] | None = None, status: str | None = None,
              **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"observation_id": identity, "source_ids": sources if sources is not None else ["primary_text_aa"],
                            "title": CATEGORY, "description": WORDS, **extra}
    if critic is not None:
        item.update(critic=critic, review_status=status or "reviewed")
    elif status is not None:
        item["review_status"] = status
    return item


def document(workflow: str, observations: list[dict[str, Any]], **result: Any) -> dict[str, Any]:
    return {"run_id": "run_x", "status": "completed", "result": {"workflow_version": workflow, "observations": observations, **result}}


V3 = "extended-review-v3"
V2 = "extended-review-v2"
MARKER = {"original_review": {"version": "deterministic-v1", "mode": "deterministic", "model_called": False}}


def advice_for(plan_document: Any, *, refs: tuple[str, ...] = (), words: str = WORDS, category: str = CATEGORY) -> Any:
    """The core's advice for a finding with seven independent refusals around it, the critic's part read from ``plan_document``."""
    plan = read_critic_plan(plan_document)
    linked = link(plan, extended_observation_refs=refs, category=category, finding_text=words)
    in_plan, candidates = candidates_from_projection(critic_projection(plan, linked), UID)
    return advise(corpus(7), candidates, f=finding(finding_uid=UID, primary_source_id=link_token(UID)), critic_in_plan=in_plan)


# -- the AI critic of plan v3 ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("decision", ["accept", "needs_human"])
def test_an_ai_accept_and_an_ai_needs_human_are_a_veto(decision: str) -> None:
    advice = advice_for(document(V3, [candidate(critic=ai_record(decision))]))
    assert advice.review.reviewed and advice.review.veto
    assert advice.label.code == "often_rejected" and "critic_veto" in advice.label.cancel_blockers


@pytest.mark.parametrize("decision", ["reject", "borderline", "rewrite"])
def test_an_ai_reject_borderline_or_rewrite_is_a_review_without_a_veto_and_the_finding_enters_the_queue(decision: str) -> None:
    advice = advice_for(document(V3, [candidate(critic=ai_record(decision))]))
    assert advice.review.reviewed and not advice.review.veto
    assert advice.label.code == "cancel_suggested" and advice.label.in_cancel_queue


def test_an_ai_record_the_pass_cannot_read_is_an_objection_not_silence() -> None:
    for bad in ({"input_id": "x"}, {"input_id": "x", "llm_decision": "maybe"}, {"input_id": "x", "llm_decision": None}):
        advice = advice_for(document(V3, [candidate(critic=bad)]))
        assert advice.review.veto and advice.label.code == "often_rejected", bad


def test_a_finding_outside_the_ai_critics_window_never_enters_the_queue() -> None:
    outside = candidate(status="not_reviewed", review_reason="outside_critic_window")
    advice = advice_for(document(V3, [outside]))
    assert not advice.review.reviewed and advice.label.neutral and not advice.label.in_cancel_queue
    assert advice.label.caption == "Прецедентов: 7 (критик не разбирал)"
    # the same finding with the critic's record in the window is the case that differs
    assert advice_for(document(V3, [candidate(critic=ai_record("reject"))])).label.in_cancel_queue


def test_a_finding_no_candidate_stands_for_is_not_reviewed_in_v3() -> None:
    advice = advice_for(document(V3, [candidate("xobs_other", sources=["blk_" + "a" * 32], critic=ai_record("reject"))]))
    assert not advice.review.reviewed and not advice.label.in_cancel_queue


# -- the deterministic critic of plan v2 ---------------------------------------------------------------------------------------------------------


def test_a_v2_finding_the_deterministic_critic_reviewed_without_a_veto_can_enter_the_queue() -> None:
    v2 = document(V2, [candidate(sources=["text:0"], critic=deterministic_record())], **MARKER)
    advice = advice_for(v2)
    assert advice.review.reviewed and not advice.review.veto
    assert advice.label.code == "cancel_suggested" and advice.label.in_cancel_queue


@pytest.mark.parametrize(("decision", "verdict"), [("accept", "pass"), ("needs_human", "no_evidence"), ("needs_human", "phantom_block"),
                                                  ("rewrite", "page_mismatch")])
def test_no_verdict_of_the_deterministic_critic_is_a_veto(decision: str, verdict: str) -> None:
    v2 = document(V2, [candidate(sources=["text:0"], critic=deterministic_record(decision, verdict))], **MARKER)
    plan = read_critic_plan(v2)
    assert [row.decision for row in plan.candidates] == [DECISION_DETERMINISTIC] and plan.kind == "deterministic"
    advice = advice_for(v2)
    assert advice.review.reviewed and not advice.review.veto and advice.label.in_cancel_queue


def test_the_same_pass_verdict_is_a_veto_when_it_is_the_ai_critics_accept() -> None:
    """The deterministic row and the AI row carry the same word (``accept``); only the AI's is the veto."""
    ai = advice_for(document(V3, [candidate(critic=ai_record("accept"))]))
    deterministic = advice_for(document(V2, [candidate(sources=["text:0"], critic=deterministic_record("accept", "pass"))], **MARKER))
    assert ai.review.veto and not ai.label.in_cancel_queue
    assert not deterministic.review.veto and deterministic.label.in_cancel_queue


def test_a_deterministic_row_inside_a_v3_document_is_still_never_a_veto() -> None:
    advice = advice_for(document(V3, [candidate(critic=deterministic_record("needs_human", "no_evidence"))]))
    assert advice.review.reviewed and not advice.review.veto


def test_a_v2_run_without_the_marker_has_no_critic_in_plan_and_nothing_is_reviewed() -> None:
    advice = advice_for(document(V2, [candidate(sources=["text:0"], critic=deterministic_record())]))
    plan = read_critic_plan(document(V2, [candidate(sources=["text:0"], critic=deterministic_record())]))
    assert not plan.in_plan and plan.kind == "none" and [row.decision for row in plan.candidates] == [None]
    assert not advice.review.reviewed and not advice.label.in_cancel_queue and advice.label.neutral


def test_a_v2_finding_the_deterministic_critic_did_not_reach_is_not_reviewed() -> None:
    advice = advice_for(document(V2, [candidate(sources=["text:0"])], **MARKER))
    assert not advice.review.reviewed and not advice.label.in_cancel_queue


@pytest.mark.parametrize("bad", [None, {}, {"status": "unavailable"}, {"result": None}, {"result": []}, {"result": {"workflow_version": "extended-review-v1"}},
                                 {"result": {"workflow_version": "extended-review-v9", "observations": []}}, "text", 5])
def test_a_document_that_names_no_known_workflow_is_no_critic(bad: Any) -> None:
    assert read_critic_plan(bad) is NO_CRITIC or read_critic_plan(bad) == NO_CRITIC
    advice = advice_for(bad)
    assert not advice.review.reviewed and advice.review.critic_in_plan is False and not advice.label.in_cancel_queue


# -- the link ---------------------------------------------------------------------------------------------------------------------------------


def test_a_candidate_finding_is_linked_by_the_reference_of_its_observations_and_a_text_finding_by_the_words_it_restates() -> None:
    plan = read_critic_plan(document(V3, [
        candidate("xobs_text", sources=["primary_text_aa"], original_primary_observation={"category": CATEGORY, "finding_text": WORDS}),
        candidate("xobs_block", sources=["blk_" + "b" * 32]),
        candidate("xobs_elsewhere", sources=["primary_text_bb"], original_primary_observation={"category": CATEGORY, "finding_text": "Другое."}),
    ]))
    assert [row.candidate_id for row in link(plan, extended_observation_refs=(), category=CATEGORY, finding_text=WORDS)] == ["xobs_text"]
    assert [row.candidate_id for row in link(plan, extended_observation_refs=("xobs_block",), category="cross_source", finding_text="любое")] == ["xobs_block"]
    both = link(plan, extended_observation_refs=("xobs_block",), category=CATEGORY, finding_text=WORDS)
    assert [row.candidate_id for row in both] == ["xobs_text", "xobs_block"]


def test_every_candidate_that_restates_a_finding_is_linked_so_that_a_veto_on_any_of_them_counts() -> None:
    twins = [candidate("xobs_1", sources=["primary_text_aa"], critic=ai_record("reject")),
             candidate("xobs_2", sources=["primary_text_bb"], critic=ai_record("needs_human"))]
    advice = advice_for(document(V3, twins))
    assert advice.review.veto and len(advice.review.linked) == 2


def test_the_v2_cut_of_a_long_text_still_links() -> None:
    long = "Длинное описание. " * 400
    v2 = document(V2, [candidate(sources=["text:3"], critic=deterministic_record(), title=CATEGORY, description=long[:3000])], **MARKER)
    plan = read_critic_plan(v2)
    assert len(link(plan, extended_observation_refs=(), category=CATEGORY, finding_text=long)) == 1
    assert link(plan, extended_observation_refs=(), category="layout", finding_text=long) == ()


def test_a_candidate_that_is_not_a_restatement_is_never_linked_by_its_words() -> None:
    plan = read_critic_plan(document(V3, [candidate("xobs_vis", sources=["blk_" + "c" * 32])]))
    assert link(plan, extended_observation_refs=(), category=CATEGORY, finding_text=WORDS) == ()


# -- the projection -------------------------------------------------------------------------------------------------------------------------------


def test_a_stored_projection_gives_the_core_the_same_review_as_the_artifact_did() -> None:
    for observations in ([candidate(critic=ai_record("reject"))], [candidate(critic=ai_record("accept"))], [candidate(status="not_reviewed")], []):
        plan = read_critic_plan(document(V3, observations))
        linked = link(plan, extended_observation_refs=(), category=CATEGORY, finding_text=WORDS)
        in_plan, candidates = candidates_from_projection(critic_projection(plan, linked), UID)
        again = advise(corpus(7), candidates, f=finding(finding_uid=UID, primary_source_id=link_token(UID)), critic_in_plan=in_plan)
        assert again.review.reviewed == any(row.decision is not None for row in linked)
        assert again.review.veto == any(row.decision in ("accept", "needs_human") for row in linked)
        assert len(again.review.linked) == len(linked)


def test_a_projection_that_is_missing_or_not_the_shape_is_no_critic_never_an_invented_review() -> None:
    for bad in (None, {}, {"in_plan": False}, {"in_plan": "yes"}, [], "x"):
        assert candidates_from_projection(bad, UID) == (False, ())  # type: ignore[arg-type]


def test_the_projection_keeps_the_decisions_that_can_veto_first_and_counts_every_linked_candidate() -> None:
    rows = [candidate(f"xobs_{i}", critic=ai_record("reject")) for i in range(12)] + [candidate("xobs_veto", critic=ai_record("accept")),
                                                                                      candidate("xobs_none", status="not_reviewed")]
    plan = read_critic_plan(document(V3, rows))
    projection = critic_projection(plan, plan.candidates)
    assert projection["linked"] == 14 and projection["in_plan"] is True
    assert len(projection["records"]) == 8 and projection["records"][0]["d"] == "accept", "a veto never falls off the end of the list"
    in_plan, candidates = candidates_from_projection(projection, UID)
    assert in_plan and len(candidates) == 14 and sum(1 for item in candidates if item.decision is not None) == 8


def test_the_context_kinds_the_critic_saw_travel_with_its_record() -> None:
    plan = read_critic_plan(document(V3, [candidate(critic=ai_record("reject"), context_kinds=["norm_text"])]))
    assert plan.candidates[0].context_kinds == frozenset({"norm_text"})
    in_plan, candidates = candidates_from_projection(critic_projection(plan, plan.candidates), UID)
    assert candidates[0].context_kinds == frozenset({"norm_text"}) and in_plan


# -- the norms ----------------------------------------------------------------------------------------------------------------------------------


def norm(paragraph: str = NPAR, *, document_id: str = NDOC, designation: str = "СП 54.13330.2022", clause: Any = "6.1", page: Any = 12) -> dict[str, Any]:
    return {"document_id": document_id, "paragraph_id": paragraph, "designation": designation, "clause_number": clause, "page_label": page, "quote": "x"}


def test_possible_norms_are_the_paragraphs_the_linked_candidates_stand_on_each_once_and_at_most_five() -> None:
    paragraphs = [f"npar_01M2545JSD15ETSNNV904X99{i:02d}"[:31].ljust(31, "0") for i in range(8)]
    items = [candidate("xobs_1", norm_candidates=[norm(p) for p in paragraphs[:4]]), candidate("xobs_2", norm_candidates=[norm(p) for p in paragraphs[2:8]])]
    plan = read_critic_plan(document(V3, items))
    found = possible_norms(plan.candidates)
    assert len(found) == 5 and len({row.norm_paragraph_id for row in found}) == 5
    assert found[0].as_dict() == {"norm_document_id": NDOC, "norm_paragraph_id": paragraphs[0], "designation": "СП 54.13330.2022",
                                  "clause_number": "6.1", "page_label": 12}


@pytest.mark.parametrize("bad", [norm(document_id="doc-1"), norm("par-1"), norm(designation=""), norm(page=0), norm(page="12"), norm(page=True), {"x": 1}, "x"])
def test_a_norm_row_that_is_not_the_contracts_shape_is_left_out(bad: Any) -> None:
    plan = read_critic_plan(document(V3, [candidate(norm_candidates=[bad, norm()])]))
    assert [row.norm_paragraph_id for row in plan.candidates[0].norms] == [NPAR]


def test_a_clause_that_is_not_text_is_null_not_a_guess() -> None:
    plan = read_critic_plan(document(V3, [candidate(norm_candidates=[norm(clause=7)])]))
    assert plan.candidates[0].norms[0].clause_number is None


def test_a_run_without_a_critic_in_plan_still_shows_its_possible_norms() -> None:
    plan = read_critic_plan(document(V2, [candidate(sources=["text:0"], norm_candidates=[norm()])]))
    assert not plan.in_plan and [row.norm_paragraph_id for row in possible_norms(plan.candidates)] == [NPAR]
