"""`CMP-AI-JOBS-01`: the vocabulary and the estimate protocol, container-free -- the scope shape, the A-12 limits on the images of a
call, the pricing, the two ceilings, and the digest (same inputs, same digest; a moved input moves it)."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from auditmanager.analysis.public import ModelPin
from auditmanager.comparison.ai_jobs.model import CHARS_PER_TOKEN_NUMERATOR, TOKENS_PER_IMAGE
from auditmanager.comparison.public import (
    AiCallGroup,
    AiCounts,
    AiMode,
    AiRoute,
    AiScope,
    ai_digest_of,
    ai_work_kind_of,
    build_ai_estimate,
)
from auditmanager.comparison.spend.model import DAY_CEILING_MICROS, JOB_CEILING_MICROS
from auditmanager.executors.public import MAX_IMAGES, MAX_TOTAL_IMAGE_BYTES

PIN = ModelPin(model_id="claude-opus-5", input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)
P, D = "prj_" + "0" * 26, "doc_" + "0" * 26


def scope(method: str = "pair_check", **over: Any) -> AiScope:
    ids = {"pair_check": {"matrix_id": "cmx_" + "1" * 26}, "spec": {"transition_id": "ctn_" + "1" * 26},
           "report": {"series_id": "cser_" + "1" * 26}, "sheet_changes": {"series_id": "cser_" + "1" * 26}}[method]
    return AiScope(method=method, project_uid=P, document_uid=D, **{**ids, **over})


def route(method: str = "pair_check", **over: Any) -> AiRoute:
    values: dict[str, Any] = {
        "work_kind": ai_work_kind_of(method), "connection_id": "exc_" + "1" * 26, "revision_id": "excr_" + "1" * 26,
        "pinned_model": "claude-opus-5", "gateway_model": "anthropic/claude-opus-5", "billing": "metered",
        "provider_mode": "live", "pin": PIN,
    }
    values.update(over)
    return AiRoute(**values)


def counts(calls: int = 10, **over: Any) -> AiCounts:
    group = AiCallGroup(calls=calls, prompt_chars=4000, output_tokens=1000, images=2, image_bytes=200_000)
    return AiCounts(groups=(group,), units=calls, **over)


def estimate(**over: Any) -> Any:
    values: dict[str, Any] = {"scope": scope(), "mode": AiMode.START, "prompt_version": "p1", "counts": counts(), "route": route()}
    values.update(over)
    return build_ai_estimate(**values)


# -- the scope -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["pair_check", "sheet_changes", "spec", "report"])
def test_each_method_has_its_executor_work_kind(method: str) -> None:
    assert ai_work_kind_of(method) == f"comparison_{method}" == scope(method).work_kind
    with pytest.raises(ValueError):
        ai_work_kind_of("stage_review")


@pytest.mark.parametrize("make", [
    lambda: AiScope(method="pair_check", project_uid=P, document_uid=D),  # a build is needed
    lambda: AiScope(method="pair_check", project_uid=P, document_uid=D, matrix_id="cmx_x", series_id="cser_x"),
    lambda: AiScope(method="spec", project_uid=P, document_uid=D, series_id="cser_x"),
    lambda: AiScope(method="report", project_uid=P, document_uid=D, transition_id="ctn_x"),
    lambda: AiScope(method="sheet_changes", project_uid=P, document_uid=D),  # a series or a sheet pair, one of them
    lambda: AiScope(method="sheet_changes", project_uid=P, document_uid=D, series_id="cser_x", sheet_pair_id="ctp_x"),
    lambda: AiScope(method="pair_check", project_uid=P, document_uid=D, matrix_id="cmx_x", restart=True),
    lambda: AiScope(method="nope", project_uid=P, document_uid=D, matrix_id="cmx_x"),
])
def test_a_scope_that_is_not_the_shape_the_table_allows_is_refused_before_a_statement(make: Any) -> None:
    with pytest.raises(ValueError):
        make()


def test_a_sheet_run_is_a_series_or_a_sheet_pair_and_may_be_restarted() -> None:
    assert scope("sheet_changes", restart=True).restart
    assert AiScope(method="sheet_changes", project_uid=P, document_uid=D, sheet_pair_id="ctp_x").sheet_pair_id == "ctp_x"


# -- the counts, A-12 -------------------------------------------------------------------------------------------------


def test_a_request_carries_at_most_the_executors_limit_of_images_and_bytes() -> None:
    AiCallGroup(calls=1, prompt_chars=1, output_tokens=1, images=MAX_IMAGES, image_bytes=MAX_TOTAL_IMAGE_BYTES)
    with pytest.raises(ValueError):
        AiCallGroup(calls=1, prompt_chars=1, output_tokens=1, images=MAX_IMAGES + 1)
    with pytest.raises(ValueError):
        AiCallGroup(calls=1, prompt_chars=1, output_tokens=1, images=1, image_bytes=MAX_TOTAL_IMAGE_BYTES + 1)
    with pytest.raises(ValueError):
        AiCallGroup(calls=1, prompt_chars=1, output_tokens=1, image_bytes=10)


@pytest.mark.parametrize("field", ["calls", "prompt_chars", "output_tokens", "images", "prompt_tokens"])
def test_a_figure_is_a_non_negative_integer(field: str) -> None:
    base: dict[str, Any] = {"calls": 1, "prompt_chars": 1, "output_tokens": 1}
    for bad in (-1, 1.5, True):
        with pytest.raises(ValueError):
            AiCallGroup(**{**base, field: bad})


def test_the_input_tokens_of_a_call_are_the_prompt_rounded_up_and_the_images_at_their_most() -> None:
    group = AiCallGroup(calls=3, prompt_chars=4001, output_tokens=10, images=2)
    assert group.input_tokens_per_call == -(-4001 * CHARS_PER_TOKEN_NUMERATOR // 1000) + 2 * TOKENS_PER_IMAGE == 1601 + 3200
    exact = AiCallGroup(calls=1, prompt_chars=99_999, output_tokens=0, prompt_tokens=700)
    assert exact.input_tokens_per_call == 700  # the method's own count wins over the conversion
    totals = AiCounts(groups=(group, exact), units=4).totals()
    assert (totals.calls, totals.images, totals.prompt_chars) == (4, 6, 3 * 4001 + 99_999)
    assert totals.input_tokens == 3 * (1601 + 3200) + 700 and totals.output_tokens == 30


def test_more_units_reused_than_there_are_is_refused() -> None:
    with pytest.raises(ValueError):
        AiCounts(groups=(), units=2, reused=3)


# -- the estimate ----------------------------------------------------------------------------------------------------


def test_the_estimate_is_the_pinned_rates_over_the_summed_tokens_rounded_up() -> None:
    made = estimate()
    # 10 calls x (1600 + 2 x 1600 = 4800 input tokens, 1000 output tokens) at USD 5 / 25 per million tokens
    assert (made.totals.input_tokens, made.totals.output_tokens) == (48_000, 10_000)
    assert made.estimate_micros == 240_000 + 250_000 == 490_000
    assert made.ceiling_micros == JOB_CEILING_MICROS and made.blocked_by is None and made.day_remaining_micros == DAY_CEILING_MICROS
    odd = estimate(counts=AiCounts(groups=(AiCallGroup(calls=1, prompt_chars=0, output_tokens=0, prompt_tokens=1),), units=1))
    assert odd.estimate_micros == 5  # 1 token at USD 5 per million is 5 micro-USD; and 1/3 of one would round up to 1


def test_the_estimate_in_the_contract_shape_names_every_figure_and_only_the_given_optional_ones() -> None:
    document = estimate(counts=counts(questions=7, pairs=2)).as_dict()
    assert set(document) == {
        "method", "estimate_digest", "route", "units", "reused", "calls", "images", "image_bytes", "prompt_chars", "input_tokens",
        "output_tokens", "estimate_micros", "ceiling_micros", "questions", "pairs", "day_remaining_micros",
    }
    frozen = estimate(job_spent_micros=1, day_committed_micros=2).as_dict(with_state=False)
    assert "day_remaining_micros" not in frozen and "blocked_by" not in frozen  # what a job stores is what was consented to
    assert document["image_bytes"] == 2_000_000 and document["images"] == 20


def test_a_connection_that_is_not_metered_has_no_money_and_no_ceiling() -> None:
    made = estimate(route=route(billing="not_metered", pin=None), counts=counts(100_000), day_committed_micros=DAY_CEILING_MICROS * 9)
    assert (made.estimate_micros, made.ceiling_micros, made.blocked_by, made.day_remaining_micros) == (0, 0, None, None)


def test_the_job_ceiling_is_crossed_only_above_it_and_what_the_job_has_spent_counts() -> None:
    at = estimate(job_spent_micros=JOB_CEILING_MICROS - 490_000)
    assert at.blocked_by is None
    over = estimate(job_spent_micros=JOB_CEILING_MICROS - 490_000 + 1)
    assert over.blocked_by == "job"
    assert estimate(counts=counts(250)).blocked_by == "job"


def test_the_day_ceiling_is_crossed_only_above_it_and_the_job_ceiling_is_named_first() -> None:
    assert estimate(day_committed_micros=DAY_CEILING_MICROS - 490_000).blocked_by is None
    over = estimate(day_committed_micros=DAY_CEILING_MICROS - 490_000 + 1)
    assert over.blocked_by == "day" and over.day_remaining_micros == 489_999
    both = estimate(counts=counts(250), day_committed_micros=DAY_CEILING_MICROS)
    assert both.blocked_by == "job"


def test_a_route_of_another_work_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        estimate(route=route("spec"))


# -- the digest ------------------------------------------------------------------------------------------------------


def test_the_same_inputs_make_the_same_digest_and_the_spend_state_is_not_in_it() -> None:
    first = estimate()
    assert len(first.estimate_digest) == 64 and first.estimate_digest == estimate().estimate_digest
    assert estimate(job_spent_micros=1_000, day_committed_micros=77).estimate_digest == first.estimate_digest
    # the digest of the stored document is the digest of the function over the same facts
    assert first.estimate_digest == ai_digest_of(
        scope=first.scope, mode=first.mode, route=first.route, prompt_version="p1", counts=first.counts,
        totals=first.totals, estimate_micros=first.estimate_micros, ceiling_micros=first.ceiling_micros)


@pytest.mark.parametrize("name, change", [
    ("scope", {"scope": scope(matrix_id="cmx_" + "2" * 26)}),
    ("restart", {"scope": scope("sheet_changes", restart=True), "route": route("sheet_changes")}),
    ("mode", {"mode": AiMode.LEFT}),
    ("prompt version", {"prompt_version": "p2"}),
    ("calls", {"counts": counts(11)}),
    ("units", {"counts": counts(10, reused=1)}),
    ("images", {"counts": AiCounts(groups=(AiCallGroup(calls=10, prompt_chars=4000, output_tokens=1000, images=3, image_bytes=200_000),), units=10)}),
    ("image bytes", {"counts": AiCounts(groups=(AiCallGroup(calls=10, prompt_chars=4000, output_tokens=1000, images=2, image_bytes=200_001),), units=10)}),
    ("a named figure", {"counts": counts(10, pairs=4)}),
    ("connection", {"route": route(connection_id="exc_" + "2" * 26)}),
    ("revision", {"route": route(revision_id="excr_" + "2" * 26)}),
    ("pinned model", {"route": route(pinned_model="claude-sonnet-5")}),
    ("provider mode", {"route": route(provider_mode="recorded")}),
    ("billing", {"route": route(billing="not_metered", pin=None)}),
])
def test_a_moved_input_moves_the_digest(name: str, change: dict[str, Any]) -> None:
    if name == "restart":
        base = estimate(scope=scope("sheet_changes"), route=route("sheet_changes"))
        assert estimate(**change).estimate_digest != base.estimate_digest
        return
    assert estimate(**change).estimate_digest != estimate().estimate_digest, name


def test_a_changed_rate_moves_the_digest_through_the_price() -> None:
    dearer = route(pin=dataclasses.replace(PIN, input_per_mtok_usd=6.0))
    assert estimate(route=dearer).estimate_digest != estimate().estimate_digest


def test_the_two_hard_ceilings_are_in_the_digest() -> None:
    made = estimate()
    base = dict(scope=made.scope, mode=made.mode, route=made.route, prompt_version="p1", counts=made.counts, totals=made.totals,
                estimate_micros=made.estimate_micros, ceiling_micros=made.ceiling_micros)
    from auditmanager.comparison.ai_jobs import model as module

    kept = module.DAY_CEILING_MICROS
    try:
        module.DAY_CEILING_MICROS = kept + 1
        assert ai_digest_of(**base) != made.estimate_digest
    finally:
        module.DAY_CEILING_MICROS = kept
