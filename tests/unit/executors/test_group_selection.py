"""`EXEC2-GROUP-STORE-01`: the pure selection among the members of a group (B3 section 11 items 1 and 19, the selection half).

No database, no clock: :func:`~auditmanager.executors.group_selection.choose` and
:func:`~auditmanager.executors.group_selection.member_issue` are functions of their arguments. What is held here:

* the member with the lowest ``used / capacity`` among those with a free unit is chosen -- the ratio, not the count in
  use, so a big connection with more work in flight still beats a small one that is fuller;
* the ratio is compared exactly (no float, no rounding), and nothing divides: a capacity of zero, or none given, is a
  member with no free unit and never an error;
* a full member, and one whose capacity was lowered below what it already serves, is never chosen; with no free unit
  anywhere the answer is ``None`` and nothing is sent;
* members that tie on the ratio are ordered (``tie_break_order``, those without one last, then ``connection_id``) and the
  persisted rotation picks among *those*; the same inputs give the same answer in whatever order the members are
  listed, and as the rotation advances equal members take turns;
* what a caller must never pass is refused, not repaired;
* ``member_issue`` reports the first of the contract's six reasons, in the contract's order.

Written and **not run** in EXEC-2 (`R-149d`); each test would pass against the implementation it names.
"""

from __future__ import annotations

import itertools

import pytest

from auditmanager.executors.group_selection import (
    ISSUE_AT_CAPACITY,
    ISSUE_CONNECTION_ARCHIVED,
    ISSUE_NOT_SERVED,
    ISSUE_PROBE_NOT_OK,
    ISSUE_REVISION_CHANGED,
    ISSUE_RUNNER_OFFLINE,
    GroupMember,
    MemberFacts,
    choose,
    member_issue,
)
from auditmanager.executors.model import GROUP_MEMBER_ISSUES

A, B, C, D = "exc_A", "exc_B", "exc_C", "exc_D"


def member(connection_id: str, order: int | None = None) -> GroupMember:
    return GroupMember(connection_id, order)


def pick(members, used, capacity, rotation=0):
    return choose(members, used, capacity, rotation)


# --- the lowest ratio wins ------------------------------------------------------------------------------------------


def test_the_lowest_ratio_of_used_to_capacity_is_chosen() -> None:
    members = [member(A), member(B), member(C)]
    assert pick(members, {A: 2, B: 1, C: 1}, {A: 4, B: 4, C: 2}) == B      # 0.5, 0.25, 0.5


def test_it_is_the_ratio_and_not_the_count_in_use_that_decides() -> None:
    # A has fewer units in use but is half full; B serves more work and is a quarter full.
    assert pick([member(A), member(B)], {A: 1, B: 2}, {A: 2, B: 8}) == B
    # And the other way round, so "the biggest capacity" or "the most in use" cannot pass either.
    assert pick([member(A), member(B)], {A: 3, B: 1}, {A: 16, B: 2}) == A


def test_an_idle_member_beats_a_busy_one_whatever_their_capacities() -> None:
    assert pick([member(A), member(B)], {A: 1, B: 0}, {A: 16, B: 1}) == B


def test_the_ratio_is_compared_exactly_and_not_as_a_rounded_float() -> None:
    # 333333/1000000 is below 1/3 by 1/3,000,000; a comparison rounded to six digits would call them equal.
    assert pick([member(A), member(B)], {A: 1, B: 333333}, {A: 3, B: 1_000_000}) == B
    assert pick([member(A), member(B)], {A: 1, B: 333334}, {A: 3, B: 1_000_000}) == A


def test_a_member_missing_from_used_has_nothing_in_use() -> None:
    assert pick([member(A), member(B)], {A: 1}, {A: 2, B: 2}) == B


# --- who can be chosen at all ---------------------------------------------------------------------------------------


def test_a_full_member_is_never_chosen_and_a_free_one_beside_it_is() -> None:
    assert pick([member(A), member(B)], {A: 2, B: 3}, {A: 2, B: 16}) == B


def test_with_no_free_unit_anywhere_the_answer_is_none() -> None:
    assert pick([member(A), member(B)], {A: 2, B: 1}, {A: 2, B: 1}) is None


def test_a_capacity_lowered_below_what_is_in_use_is_full_and_not_negative_room() -> None:
    assert pick([member(A)], {A: 3}, {A: 1}) is None
    assert pick([member(A), member(B)], {A: 3, B: 1}, {A: 1, B: 4}) == B


def test_no_members_is_none() -> None:
    assert pick([], {}, {}) is None


@pytest.mark.parametrize("capacity", [{A: 0}, {}, {A: -1}])
def test_a_capacity_of_zero_or_none_is_a_member_with_no_free_unit_and_never_a_division(capacity) -> None:
    assert pick([member(A)], {A: 0}, capacity) is None
    assert pick([member(A), member(B)], {A: 0, B: 0}, {**capacity, B: 2}) == B


# --- ties and the persisted rotation ----------------------------------------------------------------------------------


def test_equal_members_take_turns_as_the_rotation_advances() -> None:
    members = [member(A), member(B), member(C)]
    used, capacity = {A: 1, B: 1, C: 1}, {A: 2, B: 2, C: 2}
    assert [pick(members, used, capacity, rotation) for rotation in range(7)] == [A, B, C, A, B, C, A]


def test_the_tie_break_order_comes_before_the_rotation_and_a_member_without_one_comes_last() -> None:
    members = [member(A, 3), member(B, 1), member(C)]
    used, capacity = {A: 0, B: 0, C: 0}, {A: 1, B: 1, C: 1}
    assert [pick(members, used, capacity, rotation) for rotation in range(4)] == [B, A, C, B]


def test_members_without_an_order_are_ordered_by_connection_id() -> None:
    members = [member(C), member(A), member(B)]
    used, capacity = {A: 0, B: 0, C: 0}, {A: 1, B: 1, C: 1}
    assert [pick(members, used, capacity, rotation) for rotation in range(3)] == [A, B, C]


def test_the_rotation_picks_among_the_tied_members_only() -> None:
    members = [member(A), member(B), member(C)]
    used, capacity = {A: 0, B: 0, C: 1}, {A: 2, B: 2, C: 2}
    chosen = [pick(members, used, capacity, rotation) for rotation in range(6)]
    assert chosen == [A, B, A, B, A, B], "C is busier and is never reached, however the cursor stands"


def test_a_single_best_member_is_chosen_whatever_the_rotation() -> None:
    members = [member(A), member(B)]
    assert {pick(members, {A: 0, B: 1}, {A: 2, B: 2}, rotation) for rotation in range(5)} == {A}


def test_the_answer_does_not_depend_on_the_order_the_members_are_listed_in() -> None:
    used, capacity = {A: 1, B: 1, C: 1, D: 3}, {A: 2, B: 2, C: 2, D: 4}
    for rotation in range(6):
        answers = {
            pick([member(cid) for cid in order], used, capacity, rotation)
            for order in itertools.permutations([A, B, C, D])
        }
        assert len(answers) == 1, (rotation, answers)


def test_the_same_inputs_give_the_same_answer_again() -> None:
    members = [member(A, 2), member(B, 1)]
    first = pick(members, {A: 0, B: 0}, {A: 1, B: 1}, 5)
    assert all(pick(members, {A: 0, B: 0}, {A: 1, B: 1}, 5) == first for _ in range(3))


# --- what a caller must never pass -------------------------------------------------------------------------------------


def test_a_negative_rotation_is_refused() -> None:
    with pytest.raises(ValueError):
        pick([member(A)], {A: 0}, {A: 1}, -1)


def test_a_negative_number_of_units_in_use_is_refused() -> None:
    with pytest.raises(ValueError):
        pick([member(A)], {A: -1}, {A: 1})


def test_a_connection_listed_twice_is_refused_and_not_merged() -> None:
    with pytest.raises(ValueError):
        pick([member(A), member(A)], {A: 0}, {A: 1})


# --- member_issue -----------------------------------------------------------------------------------------------------------


def facts(**over) -> MemberFacts:
    base = dict(
        connection_id=A, tie_break_order=None, revision_is_snapshot=True, archived=False, served=True,
        probed_ok=True, runner_online=True, capacity=2, used=1,
    )
    return MemberFacts(**{**base, **over})


def test_a_healthy_member_with_a_free_unit_has_no_issue() -> None:
    assert member_issue(facts()) is None


@pytest.mark.parametrize(("over", "issue"), [
    ({"revision_is_snapshot": False}, ISSUE_REVISION_CHANGED),
    ({"archived": True}, ISSUE_CONNECTION_ARCHIVED),
    ({"served": False}, ISSUE_NOT_SERVED),
    ({"probed_ok": False}, ISSUE_PROBE_NOT_OK),
    ({"runner_online": False}, ISSUE_RUNNER_OFFLINE),
    ({"used": 2}, ISSUE_AT_CAPACITY),
    ({"used": 5}, ISSUE_AT_CAPACITY),
    ({"capacity": 0, "used": 0}, ISSUE_AT_CAPACITY),
])
def test_each_condition_alone_is_the_issue_reported(over, issue: str) -> None:
    assert member_issue(facts(**over)) == issue


def test_the_issues_are_the_contracts_six_in_the_contracts_order() -> None:
    assert GROUP_MEMBER_ISSUES == (
        ISSUE_REVISION_CHANGED, ISSUE_CONNECTION_ARCHIVED, ISSUE_NOT_SERVED, ISSUE_PROBE_NOT_OK,
        ISSUE_RUNNER_OFFLINE, ISSUE_AT_CAPACITY,
    )


def test_when_several_apply_the_first_of_the_enumeration_is_reported() -> None:
    everything = dict(
        revision_is_snapshot=False, archived=True, served=False, probed_ok=False, runner_online=False, used=2)
    # Take the conditions off one at a time, in order: each removal exposes the next reason.
    expected = list(GROUP_MEMBER_ISSUES)
    cure = {
        ISSUE_REVISION_CHANGED: {"revision_is_snapshot": True},
        ISSUE_CONNECTION_ARCHIVED: {"archived": False},
        ISSUE_NOT_SERVED: {"served": True},
        ISSUE_PROBE_NOT_OK: {"probed_ok": True},
        ISSUE_RUNNER_OFFLINE: {"runner_online": True},
        ISSUE_AT_CAPACITY: {"used": 1},
    }
    state = dict(everything)
    seen = []
    for issue in expected:
        seen.append(member_issue(facts(**state)))
        state.update(cure[issue])
    assert seen == expected
    assert member_issue(facts(**state)) is None


def test_a_member_whose_only_issue_is_capacity_is_still_in_service_and_a_changed_one_is_not() -> None:
    assert facts(used=2).in_service is True and facts(used=2).has_free_unit is False
    assert facts(revision_is_snapshot=False).in_service is False
    assert facts(archived=True).in_service is False


def test_a_member_is_handed_to_choose_as_its_connection_and_its_order() -> None:
    assert facts(connection_id=B, tie_break_order=4).as_member() == GroupMember(B, 4)
