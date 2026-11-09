"""`UI-B-27` (contract 1.35.0): the accepted optimisation proposals of a section's projects.

A proposal is listed exactly while the decision in force on it is an acceptance: a rejection, a request to revise, a
withdrawal that followed the acceptance or no decision at all keeps it off; a new acceptance after a withdrawal brings
it back. The filters are filters, not parents; the order is newest acceptance first.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from auditmanager.optimisation.proposals.public import (
    decide_optimisation_proposal,
    list_accepted_proposals,
    list_optimisation_proposals,
    start_optimisation_pass,
)
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import HOSTILE_VENDOR, World, published_reader


@pytest.fixture
def started(unit, cast, ready: World) -> dict[str, Any]:
    record = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=ready.document,
        idempotency_key="pass-1",
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    page = unit(
        list_optimisation_proposals,
        optimisation_pass_id=record.optimisation_pass_id,
        actor_roles=frozenset({"expert"}),
    )
    return {"pass": record, "proposals": [item.optimisation_proposal_id for item in page.items]}


def _decide(unit, cast, proposal: str, verdict: str, key: str, comment: str | None = None, **extra):
    arguments: dict[str, Any] = {
        "proposal_id": proposal,
        "verdict": verdict,
        "comment": comment,
        "idempotency_key": key,
        "actor_uid": cast.expert,
    }
    arguments.update(extra)
    return unit(decide_optimisation_proposal, **arguments)


def _accepted(unit, **filters: Any):
    return unit(list_accepted_proposals, actor_roles=frozenset({"expert"}), **filters)


def test_a_proposal_is_listed_exactly_while_an_acceptance_is_the_decision_in_force(
    unit, cast, started, ready: World
) -> None:
    door, window, anchor, tape = started["proposals"]
    assert _accepted(unit, project_uid=ready.project) == ()  # nobody decided anything

    _decide(unit, cast, door, "accept", "a-1", "подходит")
    _decide(unit, cast, window, "reject", "a-2", "хуже по теплотехнике")
    _decide(unit, cast, anchor, "revise", "a-3", "уточнить поставщика")
    _decide(unit, cast, tape, "accept", "a-4", actor_uid=cast.other_expert)
    listed = _accepted(unit, project_uid=ready.project)
    # Newest acceptance first.
    assert [row.optimisation_proposal_id for row in listed] == [tape, door]
    row_tape, row_door = listed
    assert (row_door.comment, row_door.actor_user_uid) == ("подходит", cast.expert)
    assert (row_tape.comment, row_tape.actor_user_uid) == (None, cast.other_expert)
    assert row_door.project_uid == ready.project and row_door.project_name
    assert (row_door.document_uid, row_door.version_uid, row_door.section) == (
        ready.document, ready.version, "AR",
    )
    assert row_door.optimisation_pass_id == started["pass"].optimisation_pass_id
    assert (row_door.current_unit_price, row_door.proposed_unit_price, row_door.saving) == (25000, 21000, 16000)
    assert (row_door.unit, row_door.currency, row_door.proposed_vendor) == ("шт", "RUB", "Кнауф Гипс")
    assert row_door.matched_name and row_door.proposed_name and row_door.row_text
    # The tape's quantity is not a number: no saving, never ``0``.
    assert (row_tape.quantity, row_tape.saving) == (None, None)
    # `D-346`: the percent of the price, the very figure the proposals read states; the tape has it where it has no amount.
    assert (row_door.saving_percent, row_tape.saving_percent) == (Decimal("16"), Decimal("33.33"))
    states = {
        item.optimisation_proposal_id: item.saving_percent
        for item in unit(
            list_optimisation_proposals, optimisation_pass_id=started["pass"].optimisation_pass_id,
            actor_roles=frozenset({"expert"}),
        ).items
    }
    assert states[door] == row_door.saving_percent and states[tape] == row_tape.saving_percent

    # A withdrawal takes it off; a later acceptance puts it back, newest first again.
    _decide(unit, cast, door, "revoke", "a-5")
    assert [row.optimisation_proposal_id for row in _accepted(unit, project_uid=ready.project)] == [tape]
    _decide(unit, cast, door, "reject", "a-6", "передумал")
    assert [row.optimisation_proposal_id for row in _accepted(unit, project_uid=ready.project)] == [tape]
    _decide(unit, cast, door, "accept", "a-7", "всё же берём")
    assert [row.optimisation_proposal_id for row in _accepted(unit, project_uid=ready.project)] == [door, tape]
    # A later decision on the tape that is not an acceptance takes it off.
    _decide(unit, cast, tape, "reject", "a-8", "ошибся")
    assert [row.optimisation_proposal_id for row in _accepted(unit, project_uid=ready.project)] == [door]


def test_the_filters_narrow_and_are_never_parents(unit, cast, started, ready: World) -> None:
    door = started["proposals"][0]
    _decide(unit, cast, door, "accept", "f-1")
    here = {row.optimisation_proposal_id for row in _accepted(unit, project_uid=ready.project, section="AR")}
    assert here == {door}
    # A section or a project nothing was accepted in is an empty answer, not ``not_found``.
    assert _accepted(unit, project_uid=ready.project, section="KJ") == ()
    assert _accepted(unit, project_uid=cast.other_project) == ()
    assert _accepted(unit, project_uid="prj_01M2545JSD15ETSNNV904X991F") == ()
    # Without a project filter every project's acceptances are read, this one's among them.
    assert door in {row.optimisation_proposal_id for row in _accepted(unit)}
    assert door in {row.optimisation_proposal_id for row in _accepted(unit, section="AR")}


def test_reading_needs_a_role_and_a_well_formed_project(unit, cast, started, ready: World) -> None:
    for roles in (frozenset(), frozenset({"nobody"})):
        with pytest.raises(DomainError) as denied:
            unit(list_accepted_proposals, actor_roles=roles)
        assert denied.value.code is ErrorCode.PERMISSION_DENIED
    for role in ("admin", "viewer"):  # `R-150e`: the viewer reads product data
        assert unit(list_accepted_proposals, actor_roles=frozenset({role})) is not None
    with pytest.raises(DomainError) as malformed:
        _accepted(unit, project_uid="opp_01M2545JSD15ETSNNV904X991F")
    assert malformed.value.code is ErrorCode.VALIDATION_FAILED
    assert malformed.value.detail_fields["field"] == "project_uid"


def test_a_hostile_vendor_is_carried_as_text(unit, cast, started, ready: World) -> None:
    """The list renders text, never evaluates it: the vendor that a spreadsheet would read as a formula is the stored string."""
    anchor = started["proposals"][2]
    _decide(unit, cast, anchor, "accept", "h-1")
    (row,) = _accepted(unit, project_uid=ready.project)
    assert row.proposed_vendor == HOSTILE_VENDOR
