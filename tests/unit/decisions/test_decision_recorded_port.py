"""`ADR-0027`: the ledger's port to the decision memory, and the origin an event is recorded with."""

from __future__ import annotations

import pytest

from auditmanager.decisions import ledger
from auditmanager.decisions.public import (
    ORIGIN_KINDS,
    register_decision_recorded,
    registered_decision_recorded,
)
from auditmanager.shared.errors import DomainError, ErrorCode


@pytest.fixture(autouse=True)
def _no_port_left_behind():
    before = registered_decision_recorded()
    yield
    register_decision_recorded(before)


class TestTheRegistration:
    def test_no_port_is_registered_until_a_composition_root_registers_one(self) -> None:
        register_decision_recorded(None)
        assert registered_decision_recorded() is None

    def test_a_registered_port_is_the_one_returned_and_can_be_replaced_or_removed(self) -> None:
        def first(session: object, event: object, origin_kind: str) -> None: ...
        def second(session: object, event: object, origin_kind: str) -> None: ...

        register_decision_recorded(first)
        assert registered_decision_recorded() is first
        register_decision_recorded(second)
        assert registered_decision_recorded() is second
        register_decision_recorded(None)
        assert registered_decision_recorded() is None


class TestTheOriginOfAnEvent:
    def test_it_is_direct_unless_the_event_names_the_decision_it_carries_over(self) -> None:
        assert ledger._origin_kind(None, None) == "direct"
        assert ledger._origin_kind(None, "dec_01M5F21PBT7E8WRN3M61BDQFDD") == "carried"

    def test_a_caller_may_say_imported_and_it_is_kept(self) -> None:
        assert ledger._origin_kind("imported", None) == "imported"
        assert ledger._origin_kind("direct", None) == "direct"

    @pytest.mark.parametrize(("requested", "carried"), [
        ("carried", None),                                  # carried without a source
        ("direct", "dec_01M5F21PBT7E8WRN3M61BDQFDD"),       # a source named, yet "direct"
        ("imported", "dec_01M5F21PBT7E8WRN3M61BDQFDD"),
        ("invented", None),
    ])
    def test_a_word_that_disagrees_with_the_link_or_is_unknown_is_refused(self, requested: str, carried: str | None) -> None:
        with pytest.raises(DomainError) as refused:
            ledger._origin_kind(requested, carried)
        assert refused.value.code is ErrorCode.VALIDATION_FAILED

    def test_the_kinds_are_the_three_the_memory_stores(self) -> None:
        assert ORIGIN_KINDS == ("direct", "carried", "imported")
