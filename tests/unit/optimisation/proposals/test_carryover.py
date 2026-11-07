"""`UI-B-14`: which decisions of an earlier version's pass are carried, container-free.

The planner matches by content and by nothing else; these cases hold each rule of the module docstring to a result a
reader can see: a display number, a page, a quantity or a price-list identity never decides a match, a name alone never
does either, a doubtful match is counted and not guessed, and a target an expert has touched is left as it is.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.optimisation.proposals import policy
from auditmanager.optimisation.proposals.carryover import content_key, plan_carryover
from auditmanager.optimisation.proposals.repository import (
    OptimisationProposalRecord,
    PositionSummary,
    ProposalDecisionRecord,
)
from auditmanager.shared.errors import DomainError, ErrorCode

MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "db"
    / "migrations"
    / "versions"
    / "20261107_0057_decision_carryover.py"
)

_AT = datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc)


def _decision(proposal: str, verdict: str, *, seq: int = 1, comment: str | None = None) -> ProposalDecisionRecord:
    return ProposalDecisionRecord(
        f"opd_{proposal[4:]}", proposal, seq, verdict, comment, "usr_01M2545JSD15ETSNNV904XA001", _AT
    )


def _proposal(number: int, *, verdict: str | None = None, **overrides: object) -> OptimisationProposalRecord:
    identity = f"opr_{number:026d}"
    values: dict[str, object] = {
        "optimisation_proposal_id": identity,
        "optimisation_pass_id": "opp_01M2545JSD15ETSNNV904XA001",
        "ordinal": number,
        "proposal_type": "cheaper_analog",
        "spec_row_key": "sr-" + "0" * 32,
        "page_number": 2,
        "sheet_label": "10",
        "line_start": 4,
        "line_end": 5,
        "table_ordinal": 1,
        "row_position": str(number),
        "row_text": "Дверь противопожарная ДПМ-01/60",
        "matched_basis": "mark",
        "analog_basis": "name_similarity",
        "name_similarity": Decimal("0.6666"),
        "proposed_vendor": "Кнауф Гипс",
        "unit": "шт",
        "quantity": Decimal("4"),
        "quantity_text": "4",
        "current_unit_price": Decimal("25000"),
        "proposed_unit_price": Decimal("19500.50"),
        "currency": "RUB",
        "saving": Decimal("21998.00"),
        "rationale": "Более дешёвый аналог",
        "matched_position": PositionSummary("prp_" + f"{number:026d}", 3, None, "Дверь", "ДПМ-01/60", "Другой"),
        "proposed_position": PositionSummary(
            "prp_" + f"{number + 500:026d}", 4, "К-1", "Дверь металлическая", None, "Кнауф Гипс"
        ),
        "current_decision": None if verdict is None else _decision(identity, verdict),
    }
    values.update(overrides)
    return OptimisationProposalRecord(**values)  # type: ignore[arg-type]


def _outcomes(source: list[OptimisationProposalRecord], target: list[OptimisationProposalRecord]) -> list[str]:
    return [match.outcome for match in plan_carryover(source, target)]


def test_an_identical_proposal_is_carried_to_the_one_with_the_same_content() -> None:
    (match,) = plan_carryover([_proposal(1, verdict="accept")], [_proposal(9)])
    assert match.outcome == "carried"
    assert match.source.optimisation_proposal_id == _proposal(1).optimisation_proposal_id
    assert match.target is not None and match.target.optimisation_proposal_id == _proposal(9).optimisation_proposal_id


def test_where_a_proposal_stands_is_not_content() -> None:
    """A later version moves rows: ordinal, page, line span, position, sheet, quantity, the price-list revision's
    identities and the algorithm's own bases are not what was decided about."""
    moved = _proposal(
        7,
        ordinal=40,
        page_number=9,
        sheet_label="12",
        line_start=30,
        line_end=31,
        table_ordinal=3,
        row_position="14",
        quantity=Decimal("400"),
        quantity_text="400",
        saving=Decimal("2199800"),
        matched_basis="name",
        analog_basis="mark",
        name_similarity=Decimal("0.9"),
        rationale="другой текст",
        matched_position=PositionSummary("prp_" + "A" * 26, 30, None, "Дверь", "ДПМ-01/60", "Другой"),
        proposed_position=PositionSummary("prp_" + "B" * 26, 31, "К-1", "Дверь металлическая", None, "Кнауф Гипс"),
    )
    assert content_key(moved) == content_key(_proposal(1))
    assert _outcomes([_proposal(1, verdict="reject")], [moved]) == ["carried"]


@pytest.mark.parametrize(
    "change",
    [
        {"proposal_type": "other_type"},
        {"row_text": "Дверь противопожарная ДПМ-02/60"},
        {"unit": "м"},
        {"currency": "EUR"},
        {"current_unit_price": Decimal("24999")},
        {"proposed_unit_price": Decimal("19500.51")},
        {"matched_position": PositionSummary("prp_" + "1" * 26, 3, None, "Дверь", "ДПМ-01/60", "Третий")},
        {"matched_position": PositionSummary("prp_" + "1" * 26, 3, "К-9", "Дверь", "ДПМ-01/60", "Другой")},
        {"matched_position": PositionSummary("prp_" + "1" * 26, 3, None, "Дверь стальная", "ДПМ-01/60", "Другой")},
        {"matched_position": PositionSummary("prp_" + "1" * 26, 3, None, "Дверь", "ДПМ-02/60", "Другой")},
        {"proposed_position": PositionSummary("prp_" + "2" * 26, 4, "К-1", "Дверь металлическая", None, "Промет")},
        {"proposed_position": PositionSummary("prp_" + "2" * 26, 4, "К-2", "Дверь металлическая", None, "Кнауф Гипс")},
        {"proposed_position": PositionSummary("prp_" + "2" * 26, 4, "К-1", "Дверь листовая", None, "Кнауф Гипс")},
        {"proposed_position": PositionSummary("prp_" + "2" * 26, 4, "К-1", "Дверь металлическая", "М", "Кнауф Гипс")},
    ],
    ids=lambda change: next(iter(change)) + ":" + str(next(iter(change.values())))[:24],
)
def test_a_difference_in_what_the_proposal_says_is_no_match(change: dict[str, object]) -> None:
    """Each of the type, the row's text, the unit and currency, either position's code, mark, name and supplier, and
    either price is content: a proposal that differs in any of them is a different proposal."""
    assert _outcomes([_proposal(1, verdict="accept")], [_proposal(2, **change)]) == ["unmatched"]


def test_a_name_alone_is_not_a_match() -> None:
    same_name_other_everything = _proposal(
        2,
        row_text="Совсем другая строка",
        current_unit_price=Decimal("1"),
        proposed_unit_price=Decimal("0.5"),
        unit="м",
    )
    assert _outcomes([_proposal(1, verdict="accept")], [same_name_other_everything]) == ["unmatched"]


def test_whitespace_and_the_scale_of_a_price_are_not_content_but_case_is() -> None:
    spaced = _proposal(
        2,
        row_text="  Дверь  противопожарная\n ДПМ-01/60 ",
        current_unit_price=Decimal("25000.00"),
        proposed_unit_price=Decimal("19500.5"),
    )
    assert content_key(spaced) == content_key(_proposal(1))
    assert _outcomes([_proposal(1, verdict="accept")], [spaced]) == ["carried"]
    shouted = _proposal(3, row_text="ДВЕРЬ ПРОТИВОПОЖАРНАЯ ДПМ-01/60")
    assert _outcomes([_proposal(1, verdict="accept")], [shouted]) == ["unmatched"]


def test_two_proposals_with_the_same_content_on_either_side_are_never_guessed() -> None:
    one_source, two_sources = [_proposal(1, verdict="accept")], [_proposal(1, verdict="accept"), _proposal(2)]
    # Two targets with the content of one source decision: which one is meant is unknown.
    assert _outcomes(one_source, [_proposal(10), _proposal(11)]) == ["ambiguous"]
    # Two sources with the content (even if the second was not decided): the one target cannot be told apart.
    assert _outcomes(two_sources, [_proposal(10)]) == ["ambiguous"]
    # Both sides doubled: still nothing is carried.
    assert _outcomes(two_sources, [_proposal(10), _proposal(11)]) == ["ambiguous"]


def test_a_target_an_expert_has_touched_is_left_as_it_is() -> None:
    decided = _proposal(10, verdict="reject")
    withdrawn = _proposal(11, verdict="revoke", row_text="Другая строка")
    plan = plan_carryover(
        [_proposal(1, verdict="accept"), _proposal(2, verdict="accept", row_text="Другая строка")],
        [decided, withdrawn],
    )
    assert [match.outcome for match in plan] == ["target_decided", "target_decided"]
    assert [match.target for match in plan] == [decided, withdrawn]


def test_only_a_decision_in_force_is_carried() -> None:
    withdrawn = _proposal(2, verdict="revoke", row_text="Вторая строка")
    pending = _proposal(3, row_text="Третья строка")
    source = [_proposal(1, verdict="accept"), withdrawn, pending]
    target = [_proposal(10), _proposal(11, row_text="Вторая строка"), _proposal(12, row_text="Третья строка")]
    plan = plan_carryover(source, target)
    # The withdrawn and the undecided source proposals have nothing in force: they are not counted at all.
    assert [match.outcome for match in plan] == ["carried"]
    assert plan[0].source.optimisation_proposal_id == _proposal(1).optimisation_proposal_id


def test_every_source_decision_comes_to_exactly_one_outcome_in_the_source_order() -> None:
    source = [
        _proposal(1, verdict="accept"),
        _proposal(2, verdict="reject", row_text="Вторая"),
        _proposal(3, verdict="revise", row_text="Третья"),
        _proposal(4, verdict="accept", row_text="Четвёртая"),
        _proposal(5, row_text="Пятая"),
    ]
    target = [
        _proposal(21),
        _proposal(22, row_text="Вторая", verdict="accept"),
        _proposal(23, row_text="Четвёртая"),
        _proposal(24, row_text="Четвёртая"),
    ]
    plan = plan_carryover(source, target)
    assert [match.outcome for match in plan] == ["carried", "target_decided", "unmatched", "ambiguous"]
    assert set(match.outcome for match in plan) <= set(policy.CARRYOVER_OUTCOMES)


def test_nothing_is_planned_for_a_pass_without_decisions_or_without_proposals() -> None:
    assert plan_carryover([_proposal(1)], [_proposal(2)]) == ()
    assert plan_carryover([], [_proposal(2)]) == ()
    assert _outcomes([_proposal(1, verdict="accept")], []) == ["unmatched"]


def test_the_carryover_is_an_experts_act_and_its_refusals_are_registered() -> None:
    policy.require_expert(
        frozenset({"expert"}), aggregate_type=policy.AGGREGATE_OPTIMISATION_PASS, act="carry over"
    )
    for roles in (frozenset({"admin"}), frozenset({"viewer"}), frozenset()):
        with pytest.raises(DomainError) as caught:
            policy.require_expert(roles, aggregate_type=policy.AGGREGATE_OPTIMISATION_PASS, act="carry over")
        assert caught.value.code is ErrorCode.PERMISSION_DENIED
    assert policy.CARRYOVER_REFUSAL_REASONS == (
        "carryover_source_unknown",
        "carryover_source_is_target",
        "carryover_source_other_document",
        "carryover_source_not_earlier",
    )
    assert policy.CARRYOVER_OUTCOMES == ("carried", "target_decided", "ambiguous", "unmatched")
    # Both command types match `ck_command_record_command_type` (lowercase snake case, 3-64 characters).
    for command_type in (policy.COMMAND_TYPE_CARRY_OVER, policy.COMMAND_TYPE_CARRY_OVER_ONE):
        assert 3 <= len(command_type) <= 64 and command_type == command_type.lower()
        assert command_type.replace("_", "").isalpha()


def test_the_migration_chains_on_the_withdrawal_and_keeps_its_names() -> None:
    spec = importlib.util.spec_from_file_location("migration_0057", MIGRATION)
    assert spec is not None and spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0057_decision_carryover"
    assert module.down_revision == "0056_optimisation_decisions"
    assert len(module.revision) <= 32  # the width of alembic_version.version_num
