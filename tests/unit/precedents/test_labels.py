"""`plan-v5` 2.3 and 2.4: the labels, the cancel conditions, the critic gates (V3, a plan with no critic) and the stop words."""

from __future__ import annotations

import pytest

from auditmanager.precedents.labels import (
    BLOCKER_CANCEL_SHARE,
    BLOCKER_CRITIC_NOT_IN_PLAN,
    BLOCKER_CRITIC_VETO,
    BLOCKER_INDEPENDENT_VOTES,
    BLOCKER_LAST_VOTE,
    BLOCKER_NOT_REVIEWED,
    BLOCKER_PROJECTS,
    BLOCKER_STOP_WORD,
)
from auditmanager.precedents.models import CriticCandidate
from auditmanager.precedents.stemming import compile_stop_words
from tests.unit.precedents.builders import ACCEPTED, REJECTED, advise, case, corpus, critic, finding, scored


def _label(items, candidates=(), **kwargs):
    return advise(items, candidates, **kwargs).label


# ---- the plain labels -----------------------------------------------------------------------------------------------------------------


def test_no_votes_and_few_votes_show_nothing():
    assert _label([]).code == "none" and _label([]).caption is None
    four = _label(corpus(4))
    assert four.code == "few" and four.caption is None


@pytest.mark.parametrize("count", [5, 6, 9])
def test_unanimous_rejections_are_never_mixed(count):
    label = _label(corpus(count), [critic("reject")])
    assert label.code != "mixed"
    assert label.code in {"often_rejected", "cancel_suggested"}


def test_unanimous_acceptances_are_likely_accepted_not_mixed():
    label = _label(corpus(0, 6))
    assert (label.code, label.caption) == ("likely_accepted", "Обычно принимают · 6 из 6")


@pytest.mark.parametrize(
    ("rejected", "accepted", "code", "caption"),
    [
        (4, 1, "often_rejected", "Прецедентов: 5 (критик не разбирал)"),  # exactly 80 %, no critic record: neutral
        (3, 2, "mixed", "Решения расходятся · 2 ✓ / 3 ✕"),
        (5, 2, "mixed", "Решения расходятся · 2 ✓ / 5 ✕"),  # 71 % is below 80 %
        (1, 4, "likely_accepted", "Обычно принимают · 4 из 5"),  # exactly 80 % accepted
        (2, 3, "mixed", "Решения расходятся · 3 ✓ / 2 ✕"),
    ],
)
def test_the_share_boundaries_of_the_labels(rejected, accepted, code, caption):
    label = _label(corpus(rejected, accepted))
    assert (label.code, label.caption) == (code, caption)


def test_often_rejected_shows_its_share_when_the_critic_reviewed_the_finding():
    label = _label(corpus(8, 2), [critic("accept")])
    assert (label.code, label.neutral, label.caption) == ("often_rejected", False, "Обычно отклоняют · 8 из 10")


# ---- cancel_suggested ------------------------------------------------------------------------------------------------------------------


def test_five_independent_rejections_from_two_projects_reviewed_by_the_critic_suggest_a_cancel():
    advice = advise(corpus(5), [critic("reject")])
    label = advice.label
    assert (label.code, label.caption, label.in_cancel_queue) == ("cancel_suggested", "Рекомендуется снять · 5 из 5", True)
    assert label.cancel_blockers == () and label.cancel_eligible_by_precedent and label.shown_code == "cancel_suggested"


def test_without_five_independent_votes_there_is_no_cancel():
    dependent = scored(case("dep", REJECTED, days_ago=100, project="p1", label="often_rejected"))
    label = _label([*corpus(4), dependent], [critic("reject")])
    assert label.votes_total == 5 and label.independent_total == 4
    assert label.code == "often_rejected"
    assert BLOCKER_INDEPENDENT_VOTES in label.cancel_blockers and not label.cancel_eligible_by_precedent


def test_five_votes_are_not_enough_when_four_of_them_are_dependent():
    deps = [scored(case(f"d{i}", REJECTED, days_ago=100 - i, project=f"p{i % 2}", label="cancel_suggested")) for i in range(4)]
    label = _label([*deps, *corpus(1)], [critic("reject")])
    assert label.independent_total == 1 and label.code == "often_rejected"


@pytest.mark.parametrize(("rejected", "accepted", "cancel"), [(9, 1, True), (8, 2, False)])
def test_the_cancel_share_is_90_percent_of_the_independent_votes(rejected, accepted, cancel):
    label = _label(corpus(rejected, accepted), [critic("reject")])
    assert (label.code == "cancel_suggested") is cancel
    if not cancel:
        assert label.code == "often_rejected" and BLOCKER_CANCEL_SHARE in label.cancel_blockers


def test_the_latest_vote_must_be_a_rejection():
    newest_accept = scored(case("new", ACCEPTED, days_ago=1, project="p0"))
    label = _label([*corpus(9), newest_accept], [critic("reject")])
    assert label.votes_rejected == 9 and label.code == "often_rejected"
    assert label.cancel_blockers == (BLOCKER_LAST_VOTE,)


def test_a_dependent_acceptance_after_the_label_still_blocks_the_cancel():
    newest = scored(case("new", ACCEPTED, days_ago=1, project="p0", label="often_rejected"))
    label = _label([*corpus(9), newest], [critic("reject")])
    assert label.independent_total == 9 and label.independent_rejected == 9
    assert label.code == "often_rejected" and BLOCKER_LAST_VOTE in label.cancel_blockers


def test_the_cancel_needs_two_projects():
    label = _label(corpus(6, projects=1), [critic("reject")])
    assert label.code == "often_rejected" and label.cancel_blockers == (BLOCKER_PROJECTS,)
    assert _label(corpus(6, projects=2), [critic("reject")]).code == "cancel_suggested"


def test_two_projects_must_be_two_projects_of_rejections():
    lone_accept = scored(case("acc", ACCEPTED, days_ago=300, project="p9"))
    label = _label([*corpus(9, projects=1), lone_accept], [critic("reject")])
    assert label.votes_total == 10 and label.code == "often_rejected" and BLOCKER_PROJECTS in label.cancel_blockers


def test_a_cancel_is_a_part_of_often_rejected_over_all_votes():
    # nine independent rejections, but three dependent acceptances: 9 of 12 is 75 % over all votes, so not often_rejected at all
    dependent_accepts = [scored(case(f"da{i}", ACCEPTED, days_ago=50 - i, project="p0", label="often_rejected")) for i in range(3)]
    label = _label([*corpus(9), *dependent_accepts], [critic("reject")])
    assert label.independent_total == 9 and label.independent_rejected == 9
    assert label.code == "mixed"


def test_cancel_suggested_always_satisfies_the_often_rejected_counts():
    for rejected in range(5, 12):
        for accepted in range(0, 6):
            label = _label(corpus(rejected, accepted), [critic("reject")])
            if label.code == "cancel_suggested":
                assert label.votes_rejected * 100 >= 80 * label.votes_total


# ---- V3 and a plan with no critic: the critic took part and reviewed --------------------------------------------------------------------------


def test_a_finding_the_critic_did_not_review_never_gets_a_cancel_and_is_shown_neutrally():
    advice = advise(corpus(6))  # a critic is in the plan, but no candidate is linked to this finding
    label = advice.label
    assert label.code == "often_rejected" and label.neutral and not label.in_cancel_queue
    assert label.caption == "Прецедентов: 6 (критик не разбирал)" and label.shown_code == "neutral"
    assert label.cancel_eligible_by_precedent and label.cancel_blockers == (BLOCKER_NOT_REVIEWED,)


def test_a_linked_candidate_without_a_critic_record_is_not_a_review():
    label = _label(corpus(6), [critic(None)])
    assert label.neutral and not label.in_cancel_queue


def test_a_candidate_linked_to_another_finding_is_not_a_review():
    elsewhere = critic("reject", candidate_id="other", sources=("primary_text_other",))
    assert _label(corpus(6), [elsewhere]).neutral


def test_a_run_whose_plan_has_no_critic_never_gets_a_cancel_even_with_six_unanimous_rejections_from_three_projects():
    items = corpus(6, projects=3)
    # even a record that was linked by mistake does not make a finding «reviewed» when the caller says no critic took part
    stray = [critic("reject")]
    no_critic = advise(items, stray, critic_in_plan=False).label
    assert no_critic.code == "often_rejected" and no_critic.neutral and not no_critic.in_cancel_queue
    assert no_critic.caption == "Прецедентов: 6 (критик не разбирал)" and no_critic.shown_code == "neutral"
    assert no_critic.cancel_blockers == (BLOCKER_CRITIC_NOT_IN_PLAN,) and no_critic.cancel_eligible_by_precedent
    assert advise(items, [], critic_in_plan=False).label.code == "often_rejected"
    # the counterpart: the same corpus with a critic in the plan that reviewed the finding without a veto does suggest the cancel
    with_critic = advise(items, stray, critic_in_plan=True).label
    assert with_critic.code == "cancel_suggested" and not with_critic.neutral


@pytest.mark.parametrize(("decision", "cancel"), [("accept", False), ("needs_human", False), ("reject", True), ("borderline", True), ("rewrite", True)])
def test_only_accept_and_needs_human_are_a_veto(decision, cancel):
    label = _label(corpus(6), [critic(decision)])
    assert (label.code == "cancel_suggested") is cancel
    if not cancel:
        assert label.code == "often_rejected" and not label.neutral and label.cancel_blockers == (BLOCKER_CRITIC_VETO,)
        assert label.caption == "Обычно отклоняют · 6 из 6"


def test_a_veto_by_any_linked_candidate_counts():
    both = [critic("reject", candidate_id="c-1"), critic("accept", candidate_id="c-2", sources=("primary_text_k1", "block_7"))]
    assert _label(corpus(6), both).code == "often_rejected"
    assert _label(corpus(6), list(reversed(both))).code == "often_rejected"
    only_rejecting = [critic("reject", candidate_id="c-1"), critic("needs_human", candidate_id="c-3", sources=("primary_text_zzz",))]
    assert _label(corpus(6), only_rejecting).code == "cancel_suggested"  # c-3 is not linked to the finding


def test_a_candidate_finding_is_linked_through_the_extended_observation_ref():
    candidate_finding = finding(primary_source_id=None, extended_observation_ref="cand-9")
    accept = [CriticCandidate("cand-9", (), "accept")]
    reject = [CriticCandidate("cand-9", (), "reject")]
    assert advise(corpus(6), accept, f=candidate_finding).label.cancel_blockers == (BLOCKER_CRITIC_VETO,)
    assert advise(corpus(6), reject, f=candidate_finding).label.code == "cancel_suggested"
    assert advise(corpus(6), [CriticCandidate("cand-8", (), "reject")], f=candidate_finding).label.neutral


def test_the_neutral_display_applies_to_rejection_labels_only():
    assert _label(corpus(0, 6)).neutral is False
    assert _label(corpus(3, 3)).neutral is False


# ---- stop words ------------------------------------------------------------------------------------------------------------------------


def test_a_stop_word_in_another_case_still_matches_and_blocks_the_cancel():
    f = finding(finding_text="Не указана марка арматурой класса А500.", recommendation_text="Проверить.")
    matcher = compile_stop_words(["арматура"])
    advice = advise(corpus(6), [critic("reject")], f=f, stop_words=matcher)
    assert advice.stop_words_found == ("арматура",)
    assert advice.label.code == "often_rejected" and BLOCKER_STOP_WORD in advice.label.cancel_blockers and not advice.label.neutral
    assert advise(corpus(6), [critic("reject")], f=f).label.code == "cancel_suggested"


def test_a_stop_word_is_found_in_the_recommendation_too():
    f = finding(finding_text="Нет данных.", recommendation_text="Согласовать с ответственным за бетонирование.")
    advice = advise(corpus(6), [critic("reject")], f=f, stop_words=compile_stop_words(["ответственный"]))
    assert advice.stop_words_found == ("ответственный",) and advice.label.code == "often_rejected"


def test_a_stop_word_that_is_not_in_the_text_changes_nothing():
    advice = advise(corpus(6), [critic("reject")], stop_words=compile_stop_words(["кровля", "лифт"]))
    assert advice.stop_words_found == () and advice.label.code == "cancel_suggested"
