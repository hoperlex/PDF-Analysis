"""`HOSTS-LAYOUT-01`, `LIMITS-01`: every place that hard-coded an effort takes the cell's, and an answer figure is never the cell's.

Each builder is asked twice: with no settings (the request every run had before the layout: ``max_tokens`` and ``effort`` are the old
constants) and with a cell (the cell's model is the request's and the cell's effort is the body's). A request is hashed, so the two differ by
exactly the effort. A cell has **no answer limit** (`R-153n`): the body's ``max_tokens`` is the builder's own estimate figure, and the cell's
timeout is the constant of its row (`R-153o`).
"""

from __future__ import annotations

import hashlib
import json

import pytest

from auditmanager.analysis.extended import core, review, workflow
from auditmanager.analysis.extended.cross_window_review import build_global_cross_window_request
from auditmanager.analysis.extended.project_parameters import build_request as build_parameters_request
from auditmanager.analysis.public import (
    CellSettings, COMPARISON_TIMEOUT_SECONDS, DEFAULT_EFFORT, ROW_ESTIMATE_OUTPUT_TOKENS, ROW_TIMEOUT_SECONDS, extended_cross_window_policy,
    project_parameters_policy,
)
from auditmanager.analysis.text.cell_settings import apply_to_body, apply_to_bundle, effort_of, limit_of
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE

CELL = CellSettings("text:main", "claude-opus-5-5", "medium", "api")


def settings(row: str, **more) -> CellSettings:
    values = dict(cell_key=f"{row}:main", model_id="gpt-6-sol", effort="low", access="api")
    return CellSettings(**(values | more))


def effort(request) -> str:
    return request.body["output_config"]["effort"]


def item(identity: str = "i1") -> dict:
    return {"title": "Заголовок", "description": "Описание", "source_ids": ["image-1"], "norm_queries": [], "input_id": identity}


COMPREHENSIVE = {"visual_observations": [], "text_observations": [], "sources": [], "native_context": []}


def _blocks(**kw):
    return core.build_request(model_id="m", run_id="run", phase="blocks", section="EOM", payload={"sources": []}, **kw)


def _merge(**kw):
    return core.build_request(model_id="m", run_id="run", phase="merge", section="AR", payload={}, **kw)


def _blocks_v3(**kw):
    return core.build_request_v3(model_id="m", run_id="run", phase="blocks", section="AR", payload={"sources": []}, window_id="w1", **kw)


def _comprehensive(**kw):
    return workflow.build_comprehensive_request(model_id="m", run_id="run", section="AR", payload=dict(COMPREHENSIVE), **kw)


def _comprehensive_v3(**kw):
    return workflow.build_comprehensive_request_v3(model_id="m", run_id="run", section="AR", payload=dict(COMPREHENSIVE), window_id="w1", **kw)


def _comprehensive_batched(**kw):
    return workflow.build_comprehensive_request_batched_v3(
        model_id="m", run_id="run", section="AR", payload=dict(COMPREHENSIVE, coverage_version="batched-v1"), window_id="w1", **kw)


def _norm(**kw):
    return workflow.build_norm_review_request(model_id="m", run_id="run", section="AR", payload={"observations": [item()]}, **kw)


def _norm_v3(**kw):
    return workflow.build_norm_review_request_v3(
        model_id="m", run_id="run", section="AR", payload={"observations": [item()]}, window_id="w1", **kw)


def _norm_batched(**kw):
    return workflow.build_norm_review_request_batched_v3(
        model_id="m", run_id="run", section="AR", payload={"coverage_version": "batched-v1", "observations": [item()], "norm_context": []},
        window_id="w1", **kw)


# row -> (builder, the constant it had)
BUILDERS = {
    "blocks": (_blocks, 6000), "merge": (_merge, 6000), "blocks_v3": (_blocks_v3, 6000),
    "comprehensive": (_comprehensive, 6000), "comprehensive_v3": (_comprehensive_v3, 6000),
    "comprehensive_batched": (_comprehensive_batched, 6000),
    "norm": (_norm, 12000), "norm_v3": (_norm_v3, 12000), "norm_batched": (_norm_batched, 12000),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_a_builder_keeps_its_constants_without_a_cell_and_takes_only_the_cells_effort_with_one(name):
    build, constant = BUILDERS[name]
    plain = build()
    assert plain.body["max_tokens"] == constant and effort(plain) == DEFAULT_EFFORT == "high"
    celled = build(settings=settings("x"))
    assert celled.body["max_tokens"] == constant, "a cell has no answer limit: the figure is the builder's own"
    assert effort(celled) == "low"
    assert celled.request_sha256 != plain.request_sha256, "the cell's effort is part of the request that is hashed and saved"
    # nothing else changed: the two bodies are the same but for the effort
    other = json.loads(json.dumps(celled.body))
    other["output_config"]["effort"] = "high"
    assert other == json.loads(json.dumps(plain.body))
    assert build(settings=None).request_sha256 == plain.request_sha256


def test_the_model_of_a_request_is_the_one_the_caller_names_and_the_cell_does_not_rename_it():
    request = _blocks(settings=settings("x", model_id="claude-opus-5-5"))
    assert request.model_id == request.body["model"] == "m", "the caller passes the cell's model; settings only carry the effort"


def test_the_critic_and_the_corrector_take_the_cells_effort_and_no_limit():
    observations = {"i1": {"title": "Т", "description": "О", "source_ids": ["s1"]}}
    sources = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": "Размер проёма 1200 мм"}]
    critic = lambda **kw: review.build_critic_request(model_id="m", run_id="run", section="AR", observations=observations,
                                                      sources=sources, window_id="w1", **kw)
    assert critic().body["max_tokens"] == 12000 and effort(critic()) == "high"
    assert critic(settings=settings("review")).body["max_tokens"] == 12000 and effort(critic(settings=settings("review"))) == "low"
    critiques = [{"input_id": "i1", "source_ids": ["s1"], "llm_decision": "needs_human", "human_taxonomy_reason": "other",
                  "confidence": 0.5, "explanation": "x", "evidence_checked": False, "source_dependency": "needs_context",
                  "needs_correction": True, "suggested_fix": "", "source_evidence": []}]
    corrector = lambda **kw: review.build_corrector_request(model_id="m", run_id="run", section="AR", observations=observations,
                                                            critiques=critiques, sources=sources, window_id="w1", **kw)
    plain, celled = corrector(), corrector(settings=settings("correction", effort="medium"))
    assert plain.body["max_tokens"] == 12000 and effort(plain) == "high"
    assert celled.body["max_tokens"] == 12000 and effort(celled) == "medium"


def test_the_parameter_passport_keeps_the_consented_figure_and_takes_the_cells_effort():
    accepted = project_parameters_policy("AR", full_coverage=True, candidate_refusals=True)
    batch = {"batch_key": "b000", "source": {"source_id": "s1", "kind": "text", "page_number": 1, "quote": "Этажность 5"}}
    build = lambda **kw: build_parameters_request(model_id="m", run_id="run", section="AR", batch=batch, accepted=accepted,
                                                  source_sha256="s" * 64, **kw)
    plain, celled = build(), build(settings=settings("cross_check"))
    assert plain.body["max_tokens"] == accepted["output_tokens"] and effort(plain) == "high"
    assert celled.body["max_tokens"] == accepted["output_tokens"] and effort(celled) == "low"


def test_the_global_cross_window_request_takes_the_cells_effort_and_no_limit():
    policy = extended_cross_window_policy(full_coverage=False)
    sources = [{"kind": "text", "source_id": key, "window_id": window, "source_sha256": "a" * 64, "character_field": "text",
                "page_number": number, "version_uid": "ver_01M2545JSD15ETSNNV904X991J", "character_start": 0, "character_end": 5,
                "quote": "Текст", "text_sha256": hashlib.sha256("Текст".encode("utf-8")).hexdigest()} for key, window, number in (("a", "w1", 1), ("b", "w2", 40))]
    batch = {"sources": sources, "batch_key": "gcwb_1", "batch_sha256": "b" * 64}
    build = lambda **kw: build_global_cross_window_request(model_id="m", run_id="run", section="AR", batch=batch,
                                                           source_sha256="a" * 64, policy=policy, **kw)
    plain, celled = build(), build(settings=settings("cross_check"))
    assert plain.body["max_tokens"] == 6000 and effort(plain) == "high"
    assert celled.body["max_tokens"] == 6000 and effort(celled) == "low"


def test_the_text_bundle_takes_the_cells_effort_and_the_rows_estimate_figure_and_is_otherwise_untouched():
    assert apply_to_bundle(AR_TEXT_PROMPT_BUNDLE, None) is AR_TEXT_PROMPT_BUNDLE
    bundle = apply_to_bundle(AR_TEXT_PROMPT_BUNDLE, settings("text", effort="medium"))
    assert (bundle.max_output_tokens, bundle.effort) == (ROW_ESTIMATE_OUTPUT_TOKENS["text"], "medium")
    assert bundle.system_prompt == AR_TEXT_PROMPT_BUNDLE.system_prompt and bundle.response_schema == AR_TEXT_PROMPT_BUNDLE.response_schema
    assert AR_TEXT_PROMPT_BUNDLE.max_output_tokens == 16000 and AR_TEXT_PROMPT_BUNDLE.effort == "high"


def test_the_estimate_figures_are_the_constants_the_builders_carry():
    assert ROW_ESTIMATE_OUTPUT_TOKENS == {"text": 16000, "blocks": 6000, "cross_check": 6000, "norms": 12000,
                                           "review": 12000, "correction": 12000}
    assert AR_TEXT_PROMPT_BUNDLE.max_output_tokens == ROW_ESTIMATE_OUTPUT_TOKENS["text"]
    assert review.REVIEW_OUTPUT_TOKENS == ROW_ESTIMATE_OUTPUT_TOKENS["review"]
    assert review.CORRECTION_OUTPUT_TOKENS == ROW_ESTIMATE_OUTPUT_TOKENS["correction"]
    assert _blocks().body["max_tokens"] == ROW_ESTIMATE_OUTPUT_TOKENS["blocks"]
    assert _comprehensive().body["max_tokens"] == ROW_ESTIMATE_OUTPUT_TOKENS["cross_check"]
    assert _norm().body["max_tokens"] == ROW_ESTIMATE_OUTPUT_TOKENS["norms"]


def test_a_cell_carries_no_answer_limit_and_no_stored_timeout():
    """`R-153n`: the cell has no ``max_output_tokens`` to send as a cap, and `R-153o`: no ``timeout_seconds`` to edit."""
    assert not {"max_output_tokens", "timeout_seconds"} & set(CellSettings.__dataclass_fields__)
    with pytest.raises(TypeError):
        CellSettings("text:main", "gpt-6-sol", "low", max_output_tokens=3333)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        CellSettings("text:main", "gpt-6-sol", "low", timeout_seconds=77)  # type: ignore[call-arg]


def test_a_cells_timeout_is_the_constant_of_its_row_as_in_the_original():
    """`R-153o`: text 1800, blocks 1800 (every role of the ensemble), cross_check 3600, norms 600, review 600, correction 600."""
    assert ROW_TIMEOUT_SECONDS == {"text": 1800, "blocks": 1800, "cross_check": 3600, "norms": 600, "review": 600, "correction": 600}
    for row, seconds in ROW_TIMEOUT_SECONDS.items():
        assert settings(row).timeout_seconds == seconds
    for role in ("leg1", "leg2", "judge"):
        assert CellSettings(f"blocks:{role}", "gpt-6-sol", "medium").timeout_seconds == 1800
    assert COMPARISON_TIMEOUT_SECONDS == {"comparison_pair_check": 900, "comparison_sheet_changes": 1800, "comparison_spec": 900,
                                          "comparison_report": 2400}
    for kind, seconds in COMPARISON_TIMEOUT_SECONDS.items():
        assert CellSettings(f"{kind}:main", "gpt-6-sol", "high").timeout_seconds == seconds


def test_a_cell_of_no_row_has_no_timeout_and_a_comparison_cell_has_no_estimate_figure():
    with pytest.raises(ValueError):
        CellSettings("x:main", "gpt-6-sol", "low").timeout_seconds
    with pytest.raises(ValueError):
        CellSettings("comparison_spec:main", "gpt-6-sol", "high").estimate_output_tokens


def test_the_helpers_do_nothing_without_a_cell():
    assert effort_of(None) == "high" and limit_of(None, 77) == 77
    assert effort_of(CELL) == "medium" and limit_of(CELL, 77) == 77, "a cell never changes the figure of a request"
    body = {"model": "m", "max_tokens": 1, "output_config": {"effort": "high", "format": {"x": 1}}}
    assert apply_to_body(body, None) == body and apply_to_body(body, None) is not body
    assert apply_to_body(body, CELL) == {"model": "m", "max_tokens": 1, "output_config": {"effort": "medium", "format": {"x": 1}}}
    assert body["output_config"]["effort"] == "high", "the input is never changed"
