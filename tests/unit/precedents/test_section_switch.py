"""`PREC-PASS`: the per-section switch of the refusal labels (`ADR-0029` decision 6), without a database.

The switch is the administrator's act from a replay report: ``section_labels`` is the whole state in one object and a switch **on** names the digest of the
report it was made from. What is shown: the value's shape (refused with its own constraint, so a switch that would do nothing is never journalled), the
reader that takes anything it cannot read as off, the tuned threshold that travels with a section, and what a reader is shown with the switch off -- no
label to refusal, no hint that speaks of one, no queue -- next to the same finding with it on.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.precedents import settings as journal
from auditmanager.precedents.models import CaseComment
from auditmanager.precedents.run_pass import evaluation
from auditmanager.precedents.run_pass.evaluation import apply_section_switch, effective_thresholds, view_from_advice, view_from_stored
from auditmanager.precedents.run_pass.reads import PassFinding
from auditmanager.precedents.setting_journal.service import checked_value
from auditmanager.precedents.similarity import Thresholds
from auditmanager.precedents.stemming import compile_stop_words
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.unit.precedents.builders import ACCEPTED, NOW, REJECTED, advise, ago, case, corpus, critic, finding, scored

DIGEST = "a" * 64


def refused(name: str, value: Any) -> dict[str, Any]:
    with pytest.raises(DomainError) as caught:
        checked_value(name, value)
    assert caught.value.code == ErrorCode.VALIDATION_FAILED
    return dict(caught.value.detail_fields)


# -- the value -------------------------------------------------------------------------------------------------------------------------------


def test_a_section_switched_on_names_its_report_and_may_carry_the_threshold_the_report_chose() -> None:
    assert checked_value("section_labels", {"AR": {"enabled": True, "report_sha256": DIGEST}}) == {"AR": {"enabled": True, "report_sha256": DIGEST}}
    assert checked_value("section_labels", {"PS": {"enabled": True, "report_sha256": DIGEST, "analogous": 0.9}}) == {
        "PS": {"enabled": True, "report_sha256": DIGEST, "analogous": 0.9}}
    assert checked_value("section_labels", {}) == {}, "every section off is a value too"
    assert checked_value("section_labels", {"AR": {"enabled": False}}) == {"AR": {"enabled": False}}, "a switch off needs no report"


@pytest.mark.parametrize("bad", [
    {"AR": {"enabled": True}},                                         # on, with no report to point at
    {"AR": {"enabled": True, "report_sha256": "A" * 64}},              # not lowercase hex
    {"AR": {"enabled": True, "report_sha256": "a" * 63}},
    {"AR": {"enabled": "yes", "report_sha256": DIGEST}},
    {"AR": {"enabled": True, "report_sha256": DIGEST, "note": "x"}},
    {"AR": {"enabled": True, "report_sha256": DIGEST, "analogous": 1.5}},
    {"AR": {"enabled": True, "report_sha256": DIGEST, "analogous": True}},
    {"ar": {"enabled": False}}, {"": {"enabled": False}}, {"AR": True}, {"AR": None},
])
def test_a_value_the_pass_could_not_read_is_refused_with_its_constraint(bad: Any) -> None:
    assert refused("section_labels", bad) == {"field": "value", "constraint": "section_labels_shape"}


def test_the_other_two_settings_have_their_shapes_too() -> None:
    assert checked_value("stop_words", {"words": [" срочно ", "в силу"]}) == {"words": ["срочно", "в силу"]}
    assert checked_value("thresholds", {"analogous": 0.9, "similar": 0.8, "history": 0.95}) == {"analogous": 0.9, "similar": 0.8, "history": 0.95}
    for bad in ({}, {"words": "x"}, {"words": [""]}, {"words": ["—"]}, {"words": [1]}, {"words": ["a"], "x": 1}, {"words": ["я"] * 201}):
        assert refused("stop_words", bad) == {"field": "value", "constraint": "stop_words_shape"}, bad
    for bad in ({}, {"analogous": 0.9}, {"analogous": 0.7, "similar": 0.8, "history": 0.95}, {"analogous": 0.9, "similar": 0.8, "history": 1.2},
                {"analogous": "x", "similar": 0.8, "history": 0.9}, {"analogous": True, "similar": 0.5, "history": 1.0}):
        assert refused("thresholds", bad) == {"field": "value", "constraint": "thresholds_shape"}, bad


# -- the reader ---------------------------------------------------------------------------------------------------------------------------------


def test_the_reader_takes_what_it_cannot_read_as_off_entry_by_entry() -> None:
    on = journal.parse_section_labels({
        "AR": {"enabled": True, "report_sha256": DIGEST, "analogous": 0.9},
        "KM": {"enabled": True},                       # a switch with no report is not one
        "OV": {"enabled": False, "report_sha256": DIGEST},
        "bad code": {"enabled": True, "report_sha256": DIGEST},
        "PS": "yes",
    })
    assert set(on) == {"AR"} and on["AR"] == journal.SectionLabelSwitch("AR", DIGEST, 0.9)
    for nothing in (None, [], "x", 0):
        assert journal.parse_section_labels(nothing) == {}                      # type: ignore[arg-type]


def test_a_section_is_computed_at_the_threshold_its_report_chose_and_not_at_all_when_that_threshold_cannot_stand() -> None:
    base = Thresholds()
    tuned = journal.SectionLabelSwitch("AR", DIGEST, 0.9)
    assert effective_thresholds(base, "AR", {"AR": tuned}) == (Thresholds(analogous=0.9, similar=0.75, history=0.92), True)
    assert effective_thresholds(base, "KM", {"AR": tuned}) == (base, False), "another section is neither on nor tuned"
    assert effective_thresholds(base, None, {"AR": tuned}) == (base, False)
    assert effective_thresholds(base, "AR", {"AR": journal.SectionLabelSwitch("AR", DIGEST)}) == (base, True), "no tuned value keeps the installation's"
    impossible = journal.SectionLabelSwitch("AR", DIGEST, 0.7)       # below `similar`: the section was not admitted at a value that cannot exist
    assert effective_thresholds(base, "AR", {"AR": impossible}) == (base, False)


# -- what is shown --------------------------------------------------------------------------------------------------------------------------------


def cancel_advice() -> Any:
    advice = advise(corpus(7), [critic("reject")])
    assert advice.label.code == "cancel_suggested"
    return advice


def test_with_the_switch_off_a_label_to_refusal_is_not_shown_and_the_finding_is_not_in_the_queue() -> None:
    on, off = view_from_advice(cancel_advice(), section_on=True), view_from_advice(cancel_advice(), section_on=False)
    assert (on.label, on.in_queue, on.masked, on.shown_code) == ("cancel_suggested", True, False, "cancel_suggested")
    assert (off.label, off.in_queue, off.masked, off.shown_code) == ("few", False, True, "few")
    assert dict(off.votes) == dict(on.votes) and off.votes["total"] == 7, "the counts stay: only the mark is hidden"
    assert off.critic_reviewed is True


@pytest.mark.parametrize("make", [
    lambda: advise(corpus(8), [critic("accept")]),            # often rejected, the critic vetoed
    lambda: advise(corpus(8), [], critic_in_plan=False),      # often rejected, shown neutrally: the critic did not review it
    lambda: advise(corpus(8), [critic("reject")], f=finding(finding_text="Это срочно.", recommendation_text=""),
                   stop_words=compile_stop_words(["срочно"])),
])
def test_every_label_to_refusal_is_hidden_with_the_switch_off_whatever_made_it_not_cancel(make: Any) -> None:
    advice = make()
    assert advice.label.code == "often_rejected"
    on, off = view_from_advice(advice, section_on=True), view_from_advice(advice, section_on=False)
    assert on.label == "often_rejected" and not on.masked
    assert off.label == "few" and off.masked and not off.in_queue


def test_a_neutral_label_is_shown_with_the_switch_off_and_on() -> None:
    for advice, code in ((advise(corpus(0, 8)), "likely_accepted"), (advise(corpus(3, 3)), "mixed"), (advise(corpus(2)), "few"), (advise([]), "none")):
        assert advice.label.code == code
        for section_on in (True, False):
            view = view_from_advice(advice, section_on=section_on)
            assert (view.label, view.masked) == (code, False)


def test_the_switch_changes_what_is_shown_never_what_is_stored() -> None:
    advice = cancel_advice()
    subject = PassFinding("fnd_01M2545JSD15ETSNNV904X991K", "fobs_01M2545JSD15ETSNNV904X991K", "dimensions", "Текст.", "", ())
    row = evaluation.row_of(evaluation.Evaluation(finding=subject, advice=advice, projection={"in_plan": True, "linked": 1, "records": []}, scored=()))
    assert (row["label"], row["critic_reviewed"]) == ("cancel_suggested", True), "the pass stores the label the rules gave"
    assert row["votes"]["total"] == 7 and row["votes"]["critic"] == {"in_plan": True, "linked": 1, "records": []}


def test_the_hints_that_speak_of_refusal_go_with_the_label_and_the_neutral_fact_of_the_history_stays() -> None:
    assert apply_section_switch("cancel_suggested", True, ["p1", "p4", "p5"], section_on=False) == ("few", ("p5",), True)
    assert apply_section_switch("often_rejected", False, ["p1"], section_on=False) == ("few", (), True)
    assert apply_section_switch("cancel_suggested", True, ["p1", "p5"], section_on=True) == ("cancel_suggested", ("p1", "p5"), False)
    assert apply_section_switch("likely_accepted", True, ["p4"], section_on=False) == ("likely_accepted", ("p4",), False), "P4 beside a label to acceptance is neutral"


def test_p1_the_reason_for_the_refusals_is_an_experts_comment_and_it_is_not_shown_with_the_switch_off() -> None:
    items = corpus(7)
    items[0] = scored(case("cr00", REJECTED, days_ago=200, project="p0", comments=(CaseComment("Не относится к этому разделу", ago(100)),)), 0.97)
    advice = advise(items, [critic("reject")])
    assert [hint.code for hint in advice.hints] == ["П1"] and advice.hints[0].text == "Не относится к этому разделу"
    assert view_from_advice(advice, section_on=True).hint_codes == ("p1",)
    assert view_from_advice(advice, section_on=False).hint_codes == ()


def test_the_view_read_from_a_stored_row_is_the_view_the_core_gave_when_it_wrote_it() -> None:
    advice = cancel_advice()
    stored = {"total": 7, "rejected": 7, "accepted": 0, "independent": 7, "projects": 2, "critic": {"in_plan": True}}
    for section_on in (True, False):
        again = view_from_stored("cancel_suggested", True, stored, [], section_on=section_on)
        assert again == view_from_advice(advice, section_on=section_on)
    neutral = view_from_stored("often_rejected", False, stored, [], section_on=True)
    assert neutral.shown_code == "neutral" and neutral.label == "often_rejected" and not neutral.in_queue
    assert view_from_stored("often_rejected", False, stored, [], section_on=False).shown_code == "few"


def test_a_label_that_was_hidden_is_recorded_as_what_was_shown_so_it_never_costs_the_next_vote_its_independence() -> None:
    from auditmanager.precedents.models import DecisionEvent
    from auditmanager.precedents.votes import is_independent

    hidden = view_from_advice(cancel_advice(), section_on=False)
    shown = view_from_advice(cancel_advice(), section_on=True)
    assert is_independent(DecisionEvent(ACCEPTED, NOW, "direct", hidden.shown_code, None)) is True
    assert is_independent(DecisionEvent(ACCEPTED, NOW, "direct", shown.shown_code, None)) is False
