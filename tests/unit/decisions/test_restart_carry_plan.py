"""`RUN-RESTART-01` (`R-155b`): which decisions of a restart's lineage are carried to which findings of the new run.

The plan is a pure function of the stored content of the findings and of the ledger events, so every matching rule is tested here without a
database: the exact match, the block finding without evidence, ties, the newest decision, the comments and what is not a source. Each rule has
a test in which only that rule can produce the outcome.
"""

from __future__ import annotations

import pytest

from auditmanager.decisions.restart_carry import (
    CARRY_DECISION_COMMAND_TYPE,
    COMMENT_CHARS,
    CarryEvent,
    CarryFinding,
    carried_comment_text,
    item_idempotency_key,
    marker_idempotency_key,
    plan_restart_carry,
)
from auditmanager.shared.identity import DecisionId, FindingObservationId, FindingUid, RunId, VersionUid

VERSION = VersionUid.new().value
ROOT = RunId.new().value
MIDDLE = RunId.new().value
TARGET = RunId.new().value

_SEQUENCE = iter(range(1, 10_000))


def finding(run: str, text: str = "Высота этажа не указана.", *, category: str = "dimensions", recommendation: str = "Указать высоту.",
            evidence: tuple[tuple[int, str, int, int], ...] = ((1, "Высота этажа 3,3 м.", 40, 60),), ref: str | None = None,
            eligible: bool = False) -> CarryFinding:
    return CarryFinding(
        finding_uid=FindingUid.new().value, run_id=run, version_uid=VERSION, version_ordinal=1,
        observation_id=FindingObservationId.new().value, category=category, finding_text=text, recommendation_text=recommendation,
        extended_ref=ref, severity_eligible=eligible, evidence=evidence,
    )


def event(subject: CarryFinding, event_type: str, *, comment: str | None = None, severity: str | None = None, author: str = "Иванов И. И.",
          carried_from: str | None = None, command_type: str | None = None, sequence: int | None = None) -> CarryEvent:
    verdict = {"accept": "accepted", "reject": "rejected", "revoke": "pending"}.get(event_type)
    return CarryEvent(
        decision_id=DecisionId.new().value, finding_uid=subject.finding_uid, sequence_no=sequence if sequence is not None else next(_SEQUENCE),
        event_type=event_type, verdict=verdict, severity=severity, comment=comment, author_label=author,
        carried_from_decision_id=carried_from, command_type=command_type,
    )


def plan(findings: list[CarryFinding], events: list[CarryEvent], lineage: tuple[str, ...] = (ROOT,)):
    grouped: dict[str, list[CarryEvent]] = {}
    for item in events:
        grouped.setdefault(item.finding_uid, []).append(item)
    return plan_restart_carry(target_run_id=TARGET, lineage_run_ids=lineage, findings=findings, events=grouped)


def kinds(result) -> list[tuple[str, str]]:  # noqa: ANN001
    return [(item.kind, item.event_type) for item in result.items]


class TestTheMatch:
    def test_a_finding_with_the_same_stored_content_receives_the_decision(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        accepted = event(source, "accept")
        result = plan([source, target], [accepted])
        assert [(item.target, item.source, item.source_event) for item in result.items] == [(target, source, accepted)]
        assert (result.sources_decided, result.unmatched_decisions, result.ties_skipped) == (1, 0, 0)

    @pytest.mark.parametrize(
        "changed",
        [
            {"text": "Высота этажа указана."},
            {"recommendation": "Проверить высоту."},
            {"category": "layout"},
            {"evidence": ((1, "Высота этажа 3,3 м.", 41, 61),)},                     # the span moved by one character
            {"evidence": ((2, "Высота этажа 3,3 м.", 40, 60),)},                     # the page
            {"evidence": ((1, "Высота этажа 3,4 м.", 40, 60),)},                     # the quote
            {"evidence": ((1, "Высота этажа 3,3 м.", 40, 60), (2, "Ещё одна цитата.", 10, 26))},   # a second evidence row
        ],
    )
    def test_each_field_of_the_content_keeps_a_different_finding_out(self, changed: dict) -> None:
        source, other = finding(ROOT), finding(TARGET, **changed)
        result = plan([source, other], [event(source, "accept")])
        assert result.items == ()
        assert result.unmatched_decisions == 1

    def test_identities_and_numbers_are_not_the_match(self) -> None:
        # Another finding_uid, another observation id, another version ordinal, another reference: the same finding.
        source = finding(ROOT, ref="primary_text_1")
        target = finding(TARGET, ref="primary_text_9")
        result = plan([source, target], [event(source, "reject")])
        assert [item.target for item in result.items] == [target]

    def test_a_block_finding_without_evidence_matches_on_text_and_category(self) -> None:
        source = finding(ROOT, evidence=())
        target = finding(TARGET, evidence=())
        assert [item.target for item in plan([source, target], [event(source, "accept")]).items] == [target]
        assert plan([source, finding(TARGET, evidence=(), category="layout")], [event(source, "accept")]).items == ()

    def test_a_block_finding_does_not_match_a_text_finding_of_the_same_words(self) -> None:
        source = finding(ROOT, evidence=())
        assert plan([source, finding(TARGET)], [event(source, "accept")]).items == ()

    def test_only_the_lineage_is_read_not_a_stranger_run(self) -> None:
        stranger = RunId.new().value
        source, target = finding(stranger), finding(TARGET)
        result = plan([source, target], [event(source, "accept")])
        assert result.items == () and result.sources_decided == 0

    def test_an_undecided_source_is_nothing_to_carry_and_not_unmatched(self) -> None:
        source = finding(ROOT)
        result = plan([source], [])
        assert result.items == () and result.unmatched_decisions == 0 and result.sources_decided == 0

    def test_a_decision_with_no_matching_finding_is_counted_once_per_content(self) -> None:
        first, second = finding(ROOT, "Текст А."), finding(MIDDLE, "Текст А.")
        gone = finding(ROOT, "Текст Б.")
        result = plan([first, second, gone], [event(first, "accept"), event(second, "reject"), event(gone, "accept")], (MIDDLE, ROOT))
        assert result.items == ()
        assert (result.sources_decided, result.unmatched_decisions) == (3, 2)


class TestTheVerdict:
    def test_an_accept_and_a_reject_carry_as_themselves_with_a_link_to_the_source_event(self) -> None:
        accepted, rejected = finding(ROOT, "А."), finding(ROOT, "Б.")
        result = plan([accepted, rejected, finding(TARGET, "А."), finding(TARGET, "Б.")], [event(accepted, "accept"), event(rejected, "reject")])
        assert sorted(kinds(result)) == [("verdict", "accept"), ("verdict", "reject")]
        assert {item.source_event.finding_uid for item in result.items} == {accepted.finding_uid, rejected.finding_uid}

    def test_the_current_verdict_is_the_one_carried_not_the_first(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        first, second = event(source, "accept"), event(source, "reject")
        result = plan([source, target], [first, second])
        assert [item.source_event for item in result.items] == [second]

    def test_the_newest_decision_wins_across_the_runs_of_the_lineage(self) -> None:
        older, newer, target = finding(ROOT), finding(MIDDLE), finding(TARGET)
        said_accept, said_reject = event(older, "accept", sequence=10), event(newer, "reject", sequence=20)
        result = plan([older, newer, target], [said_accept, said_reject], (MIDDLE, ROOT))
        assert [(item.event_type, item.source) for item in result.items] == [("reject", newer)]
        # the same content, the order of the events swapped: the other run now wins -- the order is the events', not the runs'
        flipped = plan([older, newer, target], [event(older, "accept", sequence=30), event(newer, "reject", sequence=20)], (MIDDLE, ROOT))
        assert [(item.event_type, item.source) for item in flipped.items] == [("accept", older)]

    def test_a_withdrawal_that_is_newest_carries_nothing_and_is_counted(self) -> None:
        older, newer, target = finding(ROOT), finding(MIDDLE), finding(TARGET)
        result = plan(
            [older, newer, target], [event(older, "accept", sequence=10), event(newer, "revoke", sequence=20)], (MIDDLE, ROOT),
        )
        assert result.items == () and result.withdrawn == 1

    def test_a_carried_copy_of_an_earlier_restart_is_a_source_of_the_verdict(self) -> None:
        # The run before the last already carried the root's decision; the chain does not need the root to be read again.
        original, copy, target = finding(ROOT), finding(MIDDLE), finding(TARGET)
        direct = event(original, "accept", sequence=10)
        carried = event(copy, "accept", sequence=20, carried_from=direct.decision_id, command_type=CARRY_DECISION_COMMAND_TYPE)
        result = plan([original, copy, target], [direct, carried], (MIDDLE, ROOT))
        assert [item.source_event for item in result.items] == [carried]

    def test_a_severity_is_carried_when_the_target_can_hold_it(self) -> None:
        source, target = finding(ROOT), finding(TARGET, eligible=True)
        result = plan([source, target], [event(source, "accept", severity="critical")])
        (item,) = result.items
        assert (item.severity, item.severity_skipped) == ("critical", False)

    def test_a_severity_the_target_cannot_hold_is_dropped_and_the_verdict_still_carries(self) -> None:
        source, target = finding(ROOT), finding(TARGET, eligible=False)
        result = plan([source, target], [event(source, "accept", severity="critical")])
        (item,) = result.items
        assert (item.event_type, item.severity, item.severity_skipped) == ("accept", None, True)

    def test_an_accept_with_no_severity_is_not_a_skipped_severity(self) -> None:
        source, target = finding(ROOT), finding(TARGET, eligible=False)
        (item,) = plan([source, target], [event(source, "accept")]).items
        assert item.severity_skipped is False


class TestTheComments:
    def test_every_direct_comment_of_the_matching_findings_is_carried_after_the_verdict_in_the_order_written(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        events = [
            event(source, "comment", comment="Первое.", sequence=1),
            event(source, "accept", sequence=2),
            event(source, "comment", comment="Второе.", sequence=3),
        ]
        result = plan([source, target], events)
        assert kinds(result) == [("verdict", "accept"), ("comment", "comment"), ("comment", "comment")]
        assert [item.source_event.comment for item in result.items if item.kind == "comment"] == ["Первое.", "Второе."]

    def test_a_comment_alone_is_carried_with_no_verdict(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        assert kinds(plan([source, target], [event(source, "comment", comment="Уточнить.")])) == [("comment", "comment")]

    def test_the_words_on_a_verdict_event_are_a_comment_too_and_the_verdict_keeps_none_of_them(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        result = plan([source, target], [event(source, "accept", comment="Согласен.")])
        assert kinds(result) == [("verdict", "accept"), ("comment", "comment")]
        assert result.items[0].source_event is result.items[1].source_event

    def test_a_comment_a_restart_itself_wrote_is_not_a_source_but_the_original_is(self) -> None:
        original, copy, target = finding(ROOT), finding(MIDDLE), finding(TARGET)
        words = event(original, "comment", comment="Слова эксперта.", sequence=1)
        echo = event(copy, "comment", comment="Перенесено при перезапуске ... Слова эксперта.", sequence=2,
                     command_type=CARRY_DECISION_COMMAND_TYPE)
        result = plan([original, copy, target], [words, echo], (MIDDLE, ROOT))
        assert [item.source_event for item in result.items] == [words]

    def test_the_sentence_of_a_carried_verdict_is_not_the_experts_words(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        confirmed = event(source, "accept", comment="Решение перенесено из версии 1 ...", carried_from=DecisionId.new().value)
        assert kinds(plan([source, target], [confirmed])) == [("verdict", "accept")]

    def test_a_blank_comment_is_not_a_comment(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        assert plan([source, target], [event(source, "comment", comment="   ")]).items == ()


class TestTies:
    def test_equal_twins_are_paired_in_the_order_of_their_references_natural_sorted(self) -> None:
        sources = [finding(ROOT, ref="primary_text_10"), finding(ROOT, ref="primary_text_2")]
        targets = [finding(TARGET, ref="primary_text_7"), finding(TARGET, ref="primary_text_30")]
        accept_two, reject_ten = event(sources[1], "accept"), event(sources[0], "reject")
        result = plan([*sources, *targets], [accept_two, reject_ten])
        pairs = {item.target.extended_ref: (item.event_type, item.source.extended_ref) for item in result.items}
        # 2 < 10 and 7 < 30: the 2nd pairs the 7th, the 10th the 30th -- not "primary_text_10" < "primary_text_2" as plain text
        assert pairs == {"primary_text_7": ("accept", "primary_text_2"), "primary_text_30": ("reject", "primary_text_10")}
        assert result.ties_skipped == 0

    def test_twins_with_no_reference_are_not_paired_and_are_counted(self) -> None:
        sources = [finding(ROOT), finding(ROOT)]
        targets = [finding(TARGET), finding(TARGET)]
        result = plan([*sources, *targets], [event(sources[0], "accept"), event(sources[1], "reject")])
        assert result.items == () and result.ties_skipped == 2

    def test_twins_that_share_a_reference_are_not_paired(self) -> None:
        sources = [finding(ROOT, ref="a"), finding(ROOT, ref="a")]
        targets = [finding(TARGET, ref="b"), finding(TARGET, ref="c")]
        result = plan([*sources, *targets], [event(sources[0], "accept")])
        assert result.items == () and result.ties_skipped == 2

    def test_a_different_number_of_twins_is_not_paired(self) -> None:
        sources = [finding(ROOT, ref="a"), finding(ROOT, ref="b")]
        targets = [finding(TARGET, ref="a"), finding(TARGET, ref="b"), finding(TARGET, ref="c")]
        result = plan([*sources, *targets], [event(sources[0], "accept")])
        assert result.items == () and result.ties_skipped == 3

    def test_one_target_with_two_equal_sources_in_one_run_is_not_paired(self) -> None:
        sources = [finding(ROOT, ref="a"), finding(ROOT, ref="b")]
        target = finding(TARGET, ref="a")
        result = plan([*sources, target], [event(sources[0], "accept"), event(sources[1], "reject")])
        assert result.items == () and result.ties_skipped == 1

    def test_an_undecided_twin_group_is_not_a_tie_worth_reporting(self) -> None:
        sources = [finding(ROOT), finding(ROOT)]
        targets = [finding(TARGET), finding(TARGET)]
        result = plan([*sources, *targets], [])
        assert result.items == () and result.ties_skipped == 0

    def test_a_run_whose_twins_cannot_be_paired_does_not_stop_the_run_that_can(self) -> None:
        messy = [finding(ROOT), finding(ROOT)]                      # no references: not paired
        clean = finding(MIDDLE)
        target = finding(TARGET)
        result = plan([*messy, clean, target], [event(messy[0], "accept"), event(clean, "reject")], (MIDDLE, ROOT))
        assert [(item.event_type, item.source) for item in result.items] == [("reject", clean)]
        assert result.ties_skipped == 1


class TestDeterminism:
    def test_the_same_input_is_the_same_plan(self) -> None:
        sources = [finding(ROOT, f"Текст {n}.") for n in range(5)]
        targets = [finding(TARGET, f"Текст {n}.") for n in range(5)]
        events = [event(source, "accept" if index % 2 else "reject", comment=f"К {index}.") for index, source in enumerate(sources)]
        first = plan([*sources, *targets], events)
        second = plan([*reversed(targets), *reversed(sources)], list(reversed(events)))
        assert [(item.kind, item.target.finding_uid, item.source_event.decision_id) for item in first.items] == [
            (item.kind, item.target.finding_uid, item.source_event.decision_id) for item in second.items
        ]


class TestKeysAndSentences:
    def test_a_key_is_the_target_run_the_source_decision_and_the_role(self) -> None:
        source, target = finding(ROOT), finding(TARGET)
        said = event(source, "accept", comment="Слова.")
        verdict, comment = plan([source, target], [said]).items
        assert item_idempotency_key(TARGET, verdict) == f"restart-carry:{TARGET}:{said.decision_id}:v"
        assert item_idempotency_key(TARGET, comment) == f"restart-carry:{TARGET}:{said.decision_id}:c"
        assert item_idempotency_key(TARGET, verdict) != item_idempotency_key(RunId.new().value, verdict)
        assert len(item_idempotency_key(TARGET, verdict)) <= 128
        assert marker_idempotency_key(TARGET) == f"restart-carry-run:{TARGET}"

    def test_a_comment_names_the_source_run_and_the_original_author_then_the_words(self) -> None:
        text, cut = carried_comment_text(ROOT, "Иванов И. И.", "Слова эксперта.")
        assert text == f"Перенесено при перезапуске из прогона {ROOT} (автор: Иванов И. И.): Слова эксперта." and cut is False

    def test_a_comment_too_long_for_the_ledger_is_cut_and_says_so(self) -> None:
        text, cut = carried_comment_text(ROOT, "Иванов И. И.", "я" * COMMENT_CHARS)
        assert cut is True and len(text) == COMMENT_CHARS and text.endswith("…")
        exact_room = COMMENT_CHARS - len(carried_comment_text(ROOT, "Иванов И. И.", "")[0])
        text, cut = carried_comment_text(ROOT, "Иванов И. И.", "я" * exact_room)
        assert cut is False and len(text) == COMMENT_CHARS
