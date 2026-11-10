"""`plan-v5` 2.5 after R-154: hints P1, P4 and P5, at most two per finding, with no model text and no P2 / P3."""

from __future__ import annotations

from auditmanager.precedents import models
from auditmanager.precedents.hints import MAX_HINT_TEXT
from auditmanager.precedents.models import CaseComment
from tests.unit.precedents.builders import ACCEPTED, NOW, REJECTED, advise, ago, case, corpus, critic, finding, scored


def _codes(advice):
    return [hint.code for hint in advice.hints]


def _commented(case_id, text, *, cosine=0.9, days_ago=100, project="p0", verdict=REJECTED):
    comments = (CaseComment(text, ago(days_ago - 1)),)
    return scored(case(case_id, verdict, days_ago=days_ago, project=project, comments=comments), cosine)


def test_only_the_three_surviving_hints_exist():
    assert {name for name in dir(models) if name.startswith("HINT_")} == {"HINT_REJECTION_REASON", "HINT_CRITIC_DIVERGES", "HINT_DOCUMENT_HISTORY"}
    assert (models.HINT_REJECTION_REASON, models.HINT_CRITIC_DIVERGES, models.HINT_DOCUMENT_HISTORY) == ("П1", "П4", "П5")


# ---- P1, the reason for the rejections ----------------------------------------------------------------------------------------------


def test_p1_is_the_comment_of_the_most_similar_rejecting_voice_and_only_for_a_rejection_label():
    items = [*corpus(5), _commented("far", "дальний комментарий", cosine=0.86), _commented("near", "ближний комментарий", cosine=0.97)]
    advice = advise(items, [critic("reject")])
    hint = advice.hints[0]
    assert (hint.code, hint.case_id, hint.text, hint.verdict) == ("П1", "near", "ближний комментарий", REJECTED)
    # a likely-accepted finding has no rejection reason to show, even with the same comments around
    accepted_side = advise([*corpus(0, 6), _commented("c", "причина", verdict=REJECTED)], [critic("accept")])
    assert accepted_side.label.code == "likely_accepted" and "П1" not in _codes(accepted_side)


def test_p1_ignores_the_comments_of_accepting_voices_and_blank_comments():
    items = [*corpus(6), _commented("acc", "принято, потому что", verdict=ACCEPTED), _commented("blank", "   ")]
    assert "П1" not in _codes(advise(items, [critic("reject")]))


def test_p1_is_not_shown_while_the_label_is_neutral():
    items = [*corpus(5), _commented("c", "причина отказа")]
    neutral = advise(items)  # the critic did not review the finding
    assert neutral.label.neutral and _codes(neutral) == []
    assert _codes(advise(items, [critic("reject")])) == ["П1"]


def test_p1_text_is_clipped_to_a_line_and_a_later_comment_wins_within_a_case():
    long_text = "а" * (MAX_HINT_TEXT + 50)
    clipped = advise([*corpus(5), _commented("c", long_text)], [critic("reject")]).hints[0].text
    assert len(clipped) == MAX_HINT_TEXT and clipped.endswith("…")
    twice = case("two", REJECTED, days_ago=100, comments=(CaseComment("первый", ago(90)), CaseComment("последний", ago(80))))
    assert advise([*corpus(5), scored(twice)], [critic("reject")]).hints[0].text == "последний"


# ---- P4, the critic diverges --------------------------------------------------------------------------------------------------------


def test_p4_when_the_precedents_lean_to_cancel_and_the_only_candidate_is_accepted_by_the_critic():
    advice = advise(corpus(6), [critic("accept")])
    assert advice.label.code == "often_rejected"  # the veto took the cancel away ...
    assert [(hint.code, hint.critic_decision) for hint in advice.hints] == [("П4", "accept")]  # ... and the divergence is said


def test_p4_when_the_precedents_say_accepted_and_the_critic_says_reject():
    advice = advise(corpus(0, 6), [critic("reject")])
    assert advice.label.code == "likely_accepted"
    assert _codes(advice) == ["П4"]


def test_p4_needs_exactly_one_linked_candidate_and_a_real_contradiction():
    two = [critic("accept", candidate_id="a"), critic("accept", candidate_id="b")]
    assert _codes(advise(corpus(6), two)) == []
    assert _codes(advise(corpus(6), [critic("reject")])) == []  # agrees with a cancel
    assert _codes(advise(corpus(6), [critic("needs_human")])) == []  # no stance to contradict
    assert _codes(advise(corpus(0, 6), [critic("accept")])) == []  # agrees with likely_accepted
    assert _codes(advise(corpus(3, 3), [critic("accept")])) == []  # no lean
    assert _codes(advise(corpus(6), [critic(None)])) == []  # not reviewed


def test_p4_never_fires_for_a_run_without_a_critic_in_its_plan():
    assert _codes(advise(corpus(6), [critic("accept")], critic_in_plan=False)) == []
    assert _codes(advise(corpus(0, 6), [critic("reject")], critic_in_plan=False)) == []


# ---- P5, the document's history ------------------------------------------------------------------------------------------------------


def _history(case_id="h", *, cosine=0.95, document="doc-F", version="ver-old", verdict=REJECTED):
    return scored(case(case_id, verdict, days_ago=150, document=document, version=version), cosine)


def test_p5_is_a_voice_from_an_earlier_version_of_the_same_document_at_cosine_092_or_more():
    advice = advise([*corpus(2), _history(cosine=0.92)])
    hint = advice.hints[0]
    assert (hint.code, hint.case_id, hint.verdict, hint.cosine) == ("П5", "h", REJECTED, 0.92)
    assert _codes(advise([*corpus(2), _history(cosine=0.9199)])) == []
    assert _codes(advise([*corpus(2), _history(document="doc-other")])) == []
    assert _codes(advise([*corpus(2), _history(version="ver-F")])) == []  # the same version is not a past version


def test_p5_is_a_neutral_fact_for_an_accepted_voice_as_well_and_the_closest_one_wins():
    advice = advise([_history("a", cosine=0.93, version="v-a", verdict=ACCEPTED), _history("b", cosine=0.96, version="v-b")])
    assert [(hint.case_id, hint.verdict) for hint in advice.hints] == [("b", REJECTED)]


def test_p5_comes_only_from_a_counted_vote():
    out_of_section = scored(case("h", REJECTED, section="S2", document="doc-F", version="ver-old"), 0.97)
    assert _codes(advise([out_of_section])) == []


# ---- the cap -------------------------------------------------------------------------------------------------------------------------


def test_at_most_two_hints_per_finding_in_the_order_of_the_plans_table():
    items = [*corpus(6), _commented("why", "причина"), _history()]
    advice = advise(items, [critic("accept")])  # P1 (rejection label, shown), P4 (critic accepts) and P5 (history) all apply
    assert advice.label.code == "often_rejected" and not advice.label.neutral
    assert _codes(advice) == ["П1", "П4"]
    without_p1 = advise([*corpus(6), _history()], [critic("accept")])
    assert _codes(without_p1) == ["П4", "П5"]
