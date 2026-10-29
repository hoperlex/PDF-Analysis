"""The ``pair_result`` kind: its payload, its key, its place in the shipped tuple (`CMP-ENGINE-01`)."""

from __future__ import annotations

import pytest

from auditmanager.comparison import public
from auditmanager.comparison.engine import handler
from auditmanager.comparison.engine.enqueue import pair_result_dedupe_key
from auditmanager.comparison.work.model import WorkDependencies
from auditmanager.comparison.work.registry import HandlerRegistry

A, B = "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", "cpr_01ARZ3NDEKTSV4RRFFQ69G5FAW"


def test_the_kind_is_pair_result_and_the_public_name_is_the_same() -> None:
    assert handler.PAIR_RESULT_KIND == "pair_result" == public.PAIR_RESULT_KIND


def test_the_shipped_tuple_has_one_handler_for_each_kind() -> None:
    kinds = [factory(WorkDependencies(None, None, None, None)).kind for factory in public.HANDLER_FACTORIES]  # type: ignore[arg-type]
    shipped = ["comparison_pair_check", "matrix_build", "page_profile", "pair_result", "series_after_preparation", "series_drive", "series_pair"]
    assert sorted(kinds) == shipped
    registry = HandlerRegistry.build(public.HANDLER_FACTORIES, WorkDependencies(None, None, None, None))  # type: ignore[arg-type]
    assert registry.kinds == set(shipped)


def test_the_payload_round_trips_and_sorts_the_reasons() -> None:
    payload = handler.pair_result_payload(A, B, reasons=["Z", "A", "A"], part="split")
    assert payload == {"page_a": A, "page_b": B, "reasons": ["A", "Z"], "part": "split"}
    assert handler.read_payload(payload) == (A, B, ["A", "Z"], "split")
    assert handler.read_payload({"page_a": A, "page_b": B}) == (A, B, [], None)


@pytest.mark.parametrize("payload", [
    {}, {"page_a": A}, {"page_a": A, "page_b": "nope"}, {"page_a": A, "page_b": B, "path": "/x"},
    {"page_a": A, "page_b": 7}, {"page_a": A, "page_b": B, "reasons": "X"}, {"page_a": A, "page_b": B, "reasons": [3]},
    {"page_a": A, "page_b": B, "part": "half"}, {"page_a": "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV", "page_b": B},
])
def test_a_payload_of_another_shape_is_refused(payload: dict) -> None:
    with pytest.raises(ValueError):
        handler.read_payload(payload)


def test_the_dedupe_key_is_a_function_of_the_two_pages_only() -> None:
    assert pair_result_dedupe_key(A, B) == f"pair_result:{A}:{B}"
    assert pair_result_dedupe_key(A, B) != pair_result_dedupe_key(B, A)
    assert len(pair_result_dedupe_key(A, B)) <= 256


def test_the_factory_costs_nothing_and_touches_nothing() -> None:
    h = handler.pair_result_handler(WorkDependencies(None, None, None, None))  # type: ignore[arg-type]
    assert h.kind == "pair_result"


def test_the_entry_points_are_exported_through_the_public_surface() -> None:
    for name in ("compare_sheet_pair", "enqueue_pair_result", "pair_result_handler", "encode_mask", "decode_mask", "MASK_FORMAT",
                 "PairOutcome", "ENGINE_ALGO_VERSION"):
        assert name in public.__all__ and hasattr(public, name)
