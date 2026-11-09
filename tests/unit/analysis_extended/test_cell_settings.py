"""`HOSTS-LAYOUT-01`: every place that hard-coded an effort or an answer limit takes the cell's, and keeps its constant without one.

Each builder is asked twice: with no settings (the request every run had before the layout: ``max_tokens`` and ``effort`` are the old
constants) and with a cell (the cell's model is the request's, the cell's limit and effort are the body's). A request is hashed, so the
two differ by exactly those two fields.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from auditmanager.analysis.extended import core, review, workflow
from auditmanager.analysis.extended.cross_window_review import build_global_cross_window_request
from auditmanager.analysis.extended.project_parameters import build_request as build_parameters_request
from auditmanager.analysis.public import (
    CellSettings, DEFAULT_EFFORT, ROW_DEFAULT_MAX_OUTPUT_TOKENS, extended_cross_window_policy, project_parameters_policy,
)
from auditmanager.analysis.text.cell_settings import apply_to_body, apply_to_bundle, effort_of, limit_of
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE

CELL = CellSettings("x:main", "claude-opus-5-5", "medium", 4321, 90, "api")


def settings(row: str, **more) -> CellSettings:
    values = dict(cell_key=f"{row}:main", model_id="gpt-6-sol", effort="low", max_output_tokens=3333, timeout_seconds=77, access="api")
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
def test_a_builder_keeps_its_constants_without_a_cell_and_takes_the_cells_limit_and_effort_with_one(name):
    build, constant = BUILDERS[name]
    plain = build()
    assert plain.body["max_tokens"] == constant and effort(plain) == DEFAULT_EFFORT == "high"
    celled = build(settings=settings("x"))
    assert celled.body["max_tokens"] == 3333 and effort(celled) == "low"
    assert celled.request_sha256 != plain.request_sha256, "the cell's parameters are part of the request that is hashed and saved"
    # nothing else changed: the two bodies are the same but for those two values
    other = json.loads(json.dumps(celled.body))
    other["max_tokens"], other["output_config"]["effort"] = constant, "high"
    assert other == json.loads(json.dumps(plain.body))
    assert build(settings=None).request_sha256 == plain.request_sha256


def test_the_model_of_a_request_is_the_one_the_caller_names_and_the_cell_does_not_rename_it():
    request = _blocks(settings=settings("x", model_id="claude-opus-5-5"))
    assert request.model_id == request.body["model"] == "m", "the caller passes the cell's model; settings only carry the limits"


def test_the_critic_and_the_corrector_take_the_cells_limits():
    observations = {"i1": {"title": "Т", "description": "О", "source_ids": ["s1"]}}
    sources = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": "Размер проёма 1200 мм"}]
    critic = lambda **kw: review.build_critic_request(model_id="m", run_id="run", section="AR", observations=observations,
                                                      sources=sources, window_id="w1", **kw)
    assert critic().body["max_tokens"] == 12000 and effort(critic()) == "high"
    assert critic(settings=settings("review")).body["max_tokens"] == 3333 and effort(critic(settings=settings("review"))) == "low"
    critiques = [{"input_id": "i1", "source_ids": ["s1"], "llm_decision": "needs_human", "human_taxonomy_reason": "other",
                  "confidence": 0.5, "explanation": "x", "evidence_checked": False, "source_dependency": "needs_context",
                  "needs_correction": True, "suggested_fix": "", "source_evidence": []}]
    corrector = lambda **kw: review.build_corrector_request(model_id="m", run_id="run", section="AR", observations=observations,
                                                            critiques=critiques, sources=sources, window_id="w1", **kw)
    plain, celled = corrector(), corrector(settings=settings("correction", max_output_tokens=2222, effort="medium"))
    assert plain.body["max_tokens"] == 12000 and effort(plain) == "high"
    assert celled.body["max_tokens"] == 2222 and effort(celled) == "medium"


def test_the_parameter_passport_takes_the_cells_limit_over_the_consented_one():
    accepted = project_parameters_policy("AR", full_coverage=True, candidate_refusals=True)
    batch = {"batch_key": "b000", "source": {"source_id": "s1", "kind": "text", "page_number": 1, "quote": "Этажность 5"}}
    build = lambda **kw: build_parameters_request(model_id="m", run_id="run", section="AR", batch=batch, accepted=accepted,
                                                  source_sha256="s" * 64, **kw)
    plain, celled = build(), build(settings=settings("cross_check"))
    assert plain.body["max_tokens"] == accepted["output_tokens"] and effort(plain) == "high"
    assert celled.body["max_tokens"] == 3333 and effort(celled) == "low"


def test_the_global_cross_window_request_takes_the_cells_limit():
    policy = extended_cross_window_policy(full_coverage=False)
    sources = [{"kind": "text", "source_id": key, "window_id": window, "source_sha256": "a" * 64, "character_field": "text",
                "page_number": number, "version_uid": "ver_01M2545JSD15ETSNNV904X991J", "character_start": 0, "character_end": 5,
                "quote": "Текст", "text_sha256": hashlib.sha256("Текст".encode("utf-8")).hexdigest()} for key, window, number in (("a", "w1", 1), ("b", "w2", 40))]
    batch = {"sources": sources, "batch_key": "gcwb_1", "batch_sha256": "b" * 64}
    build = lambda **kw: build_global_cross_window_request(model_id="m", run_id="run", section="AR", batch=batch,
                                                           source_sha256="a" * 64, policy=policy, **kw)
    plain, celled = build(), build(settings=settings("cross_check"))
    assert plain.body["max_tokens"] == 6000 and effort(plain) == "high"
    assert celled.body["max_tokens"] == 3333 and effort(celled) == "low"


def test_the_text_bundle_takes_the_cells_limit_and_effort_and_is_otherwise_untouched():
    assert apply_to_bundle(AR_TEXT_PROMPT_BUNDLE, None) is AR_TEXT_PROMPT_BUNDLE
    bundle = apply_to_bundle(AR_TEXT_PROMPT_BUNDLE, settings("text", max_output_tokens=8000, effort="medium"))
    assert (bundle.max_output_tokens, bundle.effort) == (8000, "medium")
    assert bundle.system_prompt == AR_TEXT_PROMPT_BUNDLE.system_prompt and bundle.response_schema == AR_TEXT_PROMPT_BUNDLE.response_schema
    assert AR_TEXT_PROMPT_BUNDLE.max_output_tokens == 16000 and AR_TEXT_PROMPT_BUNDLE.effort == "high"


def test_the_defaults_are_the_constants_the_builders_carry():
    assert ROW_DEFAULT_MAX_OUTPUT_TOKENS == {"text": 16000, "blocks": 6000, "cross_check": 6000, "norms": 12000,
                                              "review": 12000, "correction": 12000}
    assert AR_TEXT_PROMPT_BUNDLE.max_output_tokens == ROW_DEFAULT_MAX_OUTPUT_TOKENS["text"]
    assert review.REVIEW_OUTPUT_TOKENS == ROW_DEFAULT_MAX_OUTPUT_TOKENS["review"]
    assert review.CORRECTION_OUTPUT_TOKENS == ROW_DEFAULT_MAX_OUTPUT_TOKENS["correction"]
    assert _blocks().body["max_tokens"] == ROW_DEFAULT_MAX_OUTPUT_TOKENS["blocks"]
    assert _comprehensive().body["max_tokens"] == ROW_DEFAULT_MAX_OUTPUT_TOKENS["cross_check"]
    assert _norm().body["max_tokens"] == ROW_DEFAULT_MAX_OUTPUT_TOKENS["norms"]


def test_the_helpers_do_nothing_without_a_cell():
    assert effort_of(None) == "high" and limit_of(None, 77) == 77
    assert effort_of(CELL) == "medium" and limit_of(CELL, 77) == 4321
    body = {"model": "m", "max_tokens": 1, "output_config": {"effort": "high", "format": {"x": 1}}}
    assert apply_to_body(body, None) == body and apply_to_body(body, None) is not body
    assert apply_to_body(body, CELL) == {"model": "m", "max_tokens": 4321, "output_config": {"effort": "medium", "format": {"x": 1}}}
    assert body["max_tokens"] == 1, "the input is never changed"
