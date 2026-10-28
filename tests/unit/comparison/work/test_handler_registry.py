"""One handler per kind (`CMP-WORK-01`, ADR-0025 decision 4; ADR verification 16). Container-free.

The registry refuses to build on a duplicate kind, a malformed one and a handler that cannot run; and
the tuple that ships (``comparison.public.HANDLER_FACTORIES``, which every later slice appends to)
makes a registry in which each factory contributes exactly one kind.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.public import HANDLER_FACTORIES, HandlerRegistry, HandlerRegistryError


class Handler:
    def __init__(self, kind: object) -> None:
        self.kind = kind

    def run(self, item: Any) -> Any:  # pragma: no cover - never run here
        raise AssertionError


def factory(kind: object):  # type: ignore[no-untyped-def]
    return lambda dependencies: Handler(kind)


DEPENDENCIES: Any = SimpleNamespace()


def test_each_kind_has_exactly_one_handler_and_the_registry_answers_it() -> None:
    registry = HandlerRegistry.build([factory("page_profile"), factory("pair_check")], DEPENDENCIES)
    assert registry.kinds == {"page_profile", "pair_check"}
    assert registry.handler("pair_check").kind == "pair_check"


def test_a_kind_registered_twice_is_a_refusal_naming_the_kind() -> None:
    with pytest.raises(HandlerRegistryError, match="page_profile"):
        HandlerRegistry.build([factory("page_profile"), factory("pair_check"), factory("page_profile")], DEPENDENCIES)


@pytest.mark.parametrize("kind", ["Page", "ab", "x" * 65, "9lives", "has-dash", "", None, 7])
def test_a_kind_the_column_would_refuse_is_refused_while_wiring(kind: object) -> None:
    with pytest.raises(HandlerRegistryError):
        HandlerRegistry.build([factory(kind)], DEPENDENCIES)


def test_a_handler_without_a_run_is_refused() -> None:
    class NoRun:
        kind = "page_profile"

    with pytest.raises(HandlerRegistryError, match="run"):
        HandlerRegistry.build([lambda dependencies: NoRun()], DEPENDENCIES)  # type: ignore[list-item]


def test_a_kind_with_no_handler_is_a_refusal_not_a_none() -> None:
    registry = HandlerRegistry.build([factory("page_profile")], DEPENDENCIES)
    with pytest.raises(HandlerRegistryError, match="pair_check"):
        registry.handler("pair_check")


def test_every_factory_receives_the_one_dependency_bundle() -> None:
    seen: list[object] = []

    def recording(dependencies: object) -> Handler:
        seen.append(dependencies)
        return Handler(f"kind_{len(seen)}")

    HandlerRegistry.build([recording, recording], DEPENDENCIES)
    assert seen == [DEPENDENCIES, DEPENDENCIES] and seen[0] is seen[1]


def test_the_shipped_tuple_makes_a_registry_with_one_kind_per_factory() -> None:
    """The guard every later slice meets when it appends a factory: a duplicate fails here."""
    registry = HandlerRegistry.build(HANDLER_FACTORIES, DEPENDENCIES)
    assert len(registry.kinds) == len(HANDLER_FACTORIES)
    kinds = [factory_(DEPENDENCIES).kind for factory_ in HANDLER_FACTORIES]
    assert len(kinds) == len(set(kinds)), "a kind appears in two factories"
    assert isinstance(HANDLER_FACTORIES, tuple)
