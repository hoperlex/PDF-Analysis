"""What a series was started on and why it later reads stale (`CMP-SERIES-01`; plan ``R3-32``: digests, never timestamps)."""

from __future__ import annotations

from auditmanager.comparison.series.inputs import (
    CurrentInputs,
    SeriesInputs,
    chain_of,
    input_digest,
    stale_reasons,
)

BOUND = SeriesInputs(chain=("v1", "v2", "v3"), matrix_id="cmx_1", edit_no=2, profile_signature="sig", engine_algo="e1")


def now(**changes: object) -> CurrentInputs:
    base = {"order": ("v1", "v2", "v3"), "matrix_id": "cmx_1", "edit_no": 2, "profile_signature": "sig", "engine_algo": "e1"}
    return CurrentInputs(**(base | changes))  # type: ignore[arg-type]


def test_the_same_inputs_are_not_stale() -> None:
    assert stale_reasons(input_digest(BOUND), BOUND, now()) == []


def test_a_reorder_or_a_new_version_is_order_changed() -> None:
    digest = input_digest(BOUND)
    assert stale_reasons(digest, BOUND, now(order=("v1", "v3", "v2"))) == ["order_changed"]
    assert stale_reasons(digest, BOUND, now(order=("v1", "v2", "v3", "v4"))) == ["order_changed"]


def test_a_rebuild_or_an_edit_is_matrix_changed() -> None:
    digest = input_digest(BOUND)
    assert stale_reasons(digest, BOUND, now(edit_no=3)) == ["matrix_changed"]
    assert stale_reasons(digest, BOUND, now(matrix_id="cmx_2")) == ["matrix_changed"]
    assert stale_reasons(digest, BOUND, now(matrix_id=None)) == ["matrix_changed"]


def test_other_page_profiles_or_another_engine_algorithm_is_profiles_changed() -> None:
    digest = input_digest(BOUND)
    assert stale_reasons(digest, BOUND, now(profile_signature="other")) == ["profiles_changed"]
    # a change of the engine's algorithm leaves every component the series knows equal: the digest says it, the catch-all names it
    assert stale_reasons(digest, BOUND, now(engine_algo="e2")) == ["profiles_changed"]


def test_several_reasons_come_in_a_fixed_order() -> None:
    assert stale_reasons(input_digest(BOUND), BOUND, now(order=("v2", "v1", "v3"), edit_no=9, profile_signature="x")) == [
        "order_changed", "matrix_changed", "profiles_changed"]


def test_the_digest_is_a_function_of_every_input_and_of_nothing_else() -> None:
    base = input_digest(BOUND)
    assert input_digest(SeriesInputs(("v1", "v2", "v3"), "cmx_1", 2, "sig", "e1")) == base
    for changed in (
        SeriesInputs(("v1", "v3", "v2"), "cmx_1", 2, "sig", "e1"),
        SeriesInputs(("v1", "v2", "v3"), "cmx_2", 2, "sig", "e1"),
        SeriesInputs(("v1", "v2", "v3"), "cmx_1", 3, "sig", "e1"),
        SeriesInputs(("v1", "v2", "v3"), "cmx_1", 2, "sig2", "e1"),
        SeriesInputs(("v1", "v2", "v3"), "cmx_1", 2, "sig", "e2"),
    ):
        assert input_digest(changed) != base
    assert len(base) == 64 and set(base) <= set("0123456789abcdef")


def test_the_chain_is_read_back_from_the_transitions() -> None:
    assert chain_of([("a", "b"), ("b", "c"), ("c", "d")]) == ("a", "b", "c", "d")
    assert chain_of([]) == ()
