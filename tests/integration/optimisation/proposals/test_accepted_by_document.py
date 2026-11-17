"""`UIP-S11-05` (programme `UI-PARITY-R3`): the accepted proposals of one document set.

`listAcceptedOptimisationProposals` takes an optional ``document_uid`` beside its two older filters. It is a filter like
them and not a parent: a document set nothing was accepted in, one that does not exist, one of another project than the
named one and one of another section than the named one are all the same empty answer. Without it, nothing changes.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.optimisation.proposals.public import (
    decide_optimisation_proposal,
    list_accepted_proposals,
    list_optimisation_proposals,
    start_optimisation_pass,
)
from auditmanager.shared.errors import DomainError, ErrorCode

from .conftest import World, classify, global_vendors, published_reader

UNKNOWN_DOCUMENT = "doc_01M2545JSD15ETSNNV904X991F"


def _start(unit, cast, ready: World, document: str, key: str) -> list[str]:
    record = unit(
        start_optimisation_pass,
        project_uid=ready.project,
        document_uid=document,
        idempotency_key=key,
        actor_uid=cast.expert,
        reader=published_reader(ready),
    ).optimisation_pass
    page = unit(
        list_optimisation_proposals,
        optimisation_pass_id=record.optimisation_pass_id,
        actor_roles=frozenset({"expert"}),
    )
    return [item.optimisation_proposal_id for item in page.items]


def _accept(unit, cast, proposal: str, key: str) -> None:
    unit(
        decide_optimisation_proposal,
        proposal_id=proposal,
        verdict="accept",
        comment=None,
        idempotency_key=key,
        actor_uid=cast.expert,
    )


def _accepted(unit, **filters: Any) -> set[str]:
    return {
        row.optimisation_proposal_id
        for row in unit(list_accepted_proposals, actor_roles=frozenset({"expert"}), **filters)
    }


@pytest.fixture
def accepted(unit, cast, ready: World) -> dict[str, str]:
    """One acceptance on each of two document sets of the project: the first confirmed AR, the second KJ."""
    classify(unit, cast, ready, "KJ", document=ready.other_document, version=ready.other_version)
    global_vendors(unit, cast, section="KJ")  # a pass needs the vendor list of its version's own section
    first = _start(unit, cast, ready, ready.document, "d-pass-1")[0]
    second = _start(unit, cast, ready, ready.other_document, "d-pass-2")[0]
    _accept(unit, cast, first, "d-accept-1")
    _accept(unit, cast, second, "d-accept-2")
    return {"first": first, "second": second}


def test_the_document_filter_narrows_to_one_set(unit, cast, ready: World, accepted) -> None:
    both = {accepted["first"], accepted["second"]}
    assert _accepted(unit, project_uid=ready.project) == both
    assert _accepted(unit, document_uid=ready.document) == {accepted["first"]}
    assert _accepted(unit, document_uid=ready.other_document) == {accepted["second"]}
    # Without it the answer is what it was: every acceptance, this project's among them.
    assert _accepted(unit, document_uid=None) == _accepted(unit) and both <= _accepted(unit)
    rows = unit(list_accepted_proposals, actor_roles=frozenset({"expert"}), document_uid=ready.document)
    (row,) = rows
    assert (row.document_uid, row.project_uid, row.version_uid, row.section) == (
        ready.document, ready.project, ready.version, "AR",
    )


def test_the_document_filter_composes_with_the_other_filters_by_intersection(unit, cast, ready: World, accepted) -> None:
    first, second = accepted["first"], accepted["second"]
    assert _accepted(unit, document_uid=ready.document, project_uid=ready.project) == {first}
    assert _accepted(unit, document_uid=ready.document, section="AR") == {first}
    assert _accepted(unit, document_uid=ready.other_document, section="KJ") == {second}
    assert _accepted(unit, document_uid=ready.document, project_uid=ready.project, section="AR") == {first}
    # Another project than the set's own, and another section than the set's own, match no row: an empty answer.
    assert _accepted(unit, document_uid=ready.document, project_uid=cast.other_project) == set()
    assert _accepted(unit, document_uid=ready.document, section="KJ") == set()
    assert _accepted(unit, document_uid=ready.other_document, section="AR") == set()


def test_a_document_nothing_was_accepted_in_is_an_empty_answer_never_not_found(unit, cast, ready: World, accepted) -> None:
    # It exists but has no pass; it belongs to another project; it does not exist at all: one answer, as for a project.
    assert _accepted(unit, document_uid=ready.foreign_document) == set()
    assert _accepted(unit, document_uid=UNKNOWN_DOCUMENT) == set()
    assert _accepted(unit, project_uid="prj_01M2545JSD15ETSNNV904X991F") == set()
    # A decision that is not an acceptance, or a withdrawn one, takes the set's row away.
    unit(
        decide_optimisation_proposal,
        proposal_id=accepted["second"],
        verdict="revoke",
        comment=None,
        idempotency_key="d-revoke-2",
        actor_uid=cast.expert,
    )
    assert _accepted(unit, document_uid=ready.other_document) == set()
    assert _accepted(unit, document_uid=ready.document) == {accepted["first"]}


def test_a_malformed_document_filter_is_refused(unit, cast, ready: World, accepted) -> None:
    for value in ("doc_bad", "prj_01M2545JSD15ETSNNV904X991F", "opp_01M2545JSD15ETSNNV904X991F", 7):
        with pytest.raises(DomainError) as refused:
            _accepted(unit, document_uid=value)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED, value
        assert refused.value.detail_fields["field"] == "document_uid", value


def test_the_shipped_adapter_hands_the_document_filter_to_the_rule(unit, cast, factory, ready: World, accepted) -> None:
    """The port's implementation (the one the router calls) maps the wire models and keeps the filter on the way."""
    from auditmanager.bootstrap.adapters import OptimisationProposalAdapter

    adapter = OptimisationProposalAdapter(factory, blob_store=None)

    def listed(**filters: Any) -> list[str]:
        rows = adapter.list_accepted_optimisation_proposals(
            project_uid=filters.pop("project_uid", None),
            section_code=filters.pop("section_code", None),
            user_uid=cast.expert,
            **filters,
        )
        return [row.optimisation_proposal_id for row in rows]

    assert set(listed()) >= {accepted["first"], accepted["second"]}
    assert listed(document_uid=ready.document) == [accepted["first"]]
    assert listed(document_uid=ready.other_document) == [accepted["second"]]
    assert listed(document_uid=ready.other_document, section_code="AR") == []
    assert listed(document_uid=ready.document, project_uid=cast.other_project) == []
    assert listed(document_uid=UNKNOWN_DOCUMENT) == []
    with pytest.raises(DomainError) as refused:
        listed(document_uid="doc_bad")
    assert refused.value.code is ErrorCode.VALIDATION_FAILED
