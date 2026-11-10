"""`REVIEW-FIX-ANALYSIS-1102` (S3-05): a context decorator enlarges a request after the builder's size check.

The builders refuse a body over the ceiling; the project-parameter and norm-paragraph contexts are
attached afterwards (16 000 to 18 000 characters, twice that in bytes for Cyrillic). Each decorator
measures the final body again and refuses it, so the window fails cleanly instead of sending a request
the declared ceiling would have refused.
"""
import json
from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.extended import parameter_context, parameter_review_context, review, workflow
from auditmanager.analysis.extended.core import canonical
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.runs import extended_review as runtime

CEILING = 900_000
PARAMETERS_POLICY = {"bundle_sha256": "0" * 64}
PARAMETERS = {"policy": PARAMETERS_POLICY, "status": "ready", "facts": [], "source_sha256": None, "manifest_sha256": None}


def _request(size):
    """A request whose body is exactly ``size`` bytes, the way the builders measure it."""
    def body(pad):
        payload = {"sources": [{"source_id": "s1", "page_number": 1}], "pad": pad}
        return {"model": "m", "system": "s", "messages": [{"role": "user", "content": canonical(payload)}]}
    base = len(canonical(body("")).encode("utf-8"))
    request = ModelRequest("m", body("x" * (size - base)), idempotency_scope="scope")
    assert len(canonical(request.body).encode("utf-8")) == size
    return request


def _review_attach(request, procedure, **options):
    return parameter_review_context.attach(request, parameters=PARAMETERS,
        accepted=parameter_review_context.policy(PARAMETERS_POLICY), parameters_policy=PARAMETERS_POLICY,
        procedure=procedure, **options)


def _visual_attach(request, **options):
    return parameter_context.attach(request, parameters=PARAMETERS,
        accepted=parameter_context.policy(PARAMETERS_POLICY), parameters_policy=PARAMETERS_POLICY, **options)


def test_the_ceilings_the_decorators_hold_are_the_builders():
    assert workflow.v3_request_ceiling() == workflow.MAX_V3_REQUEST_BYTES == review.MAX_REQUEST_BYTES == CEILING
    assert workflow.v3_request_ceiling(True) == workflow.LIFTED_V3_REQUEST_BYTES
    # extended_review.py cannot import the analysis internals; its copy of the figure is pinned here
    assert runtime._NORM_REQUEST_BODY_BYTES == workflow.MAX_V3_REQUEST_BYTES
    with pytest.raises(ValueError, match="extended_relaxed_limits_invalid"):
        workflow.v3_request_ceiling(1)


@pytest.mark.parametrize("procedure", ["finding_review", "finding_correction", "comprehensive_analysis"])
def test_the_parameter_review_context_refuses_a_body_it_pushes_over_the_ceiling(procedure):
    with pytest.raises(ValueError, match="project_parameter_review_context_request_window_too_large"):
        _review_attach(_request(CEILING - 100), procedure)
    attached, receipt = _review_attach(_request(CEILING - 20_000), procedure)
    assert receipt["procedure"] == procedure and len(canonical(attached.body).encode("utf-8")) <= CEILING


def test_the_parameter_review_context_lifts_only_a_comprehensive_request_of_a_relaxed_run():
    big = _request(CEILING - 100)
    attached, _ = _review_attach(big, "comprehensive_analysis", relaxed_limits=True)
    assert len(canonical(attached.body).encode("utf-8")) > CEILING
    for procedure in ("finding_review", "finding_correction"):  # the critic and corrector hold the review figure
        with pytest.raises(ValueError, match="request_window_too_large"):
            _review_attach(big, procedure, relaxed_limits=True)


def test_the_visual_parameter_context_refuses_a_body_it_pushes_over_the_ceiling():
    with pytest.raises(ValueError, match="project_parameter_context_request_window_too_large"):
        _visual_attach(_request(CEILING - 100))
    attached, receipt = _visual_attach(_request(CEILING - 20_000))
    assert len(canonical(attached.body).encode("utf-8")) <= CEILING and receipt["provided_only"] is True
    lifted, _ = _visual_attach(_request(CEILING - 100), relaxed_limits=True)
    assert len(canonical(lifted.body).encode("utf-8")) > CEILING


def test_a_decorator_keeps_refusing_a_relaxed_flag_that_is_not_a_boolean():
    with pytest.raises(ValueError, match="extended_relaxed_limits_invalid"):
        _visual_attach(_request(1_000), relaxed_limits="yes")
    with pytest.raises(ValueError, match="extended_relaxed_limits_invalid"):
        _review_attach(_request(1_000), "finding_review", relaxed_limits=1)


# -- the norm paragraph context is attached by runs/norm_context.py, so the runtime measures the result --

def _norm_run(monkeypatch, *, attached_size, policy, calls):
    """`_norm_batched_v3` over one observation, with the norm context double enlarging the body to a size."""
    state = {"section": "AR", "source_sha256": "a" * 64, "warnings": [], "sources": [{"source_id": "s1"}],
        "observations": [{"title": "Наблюдение", "description": "Описание", "source_ids": ["s1"],
            "norm_candidates": [{"snapshot_id": "ns_x", "document_id": "ndoc_x", "paragraph_id": "p1",
                "designation": "СП 1", "clause_number": "1.1", "quote": "Цитата", "page_label": 1,
                "status": "candidate_not_verified"}]}]}
    def attach(session, request, **_):
        return _request(attached_size), {"contexts_not_provided": 0, "context": {"paragraphs": []}}
    import auditmanager.runs.norm_context as norm_context
    monkeypatch.setattr(norm_context, "attach", attach)
    window = {"window_id": "w1", "policy": {"phase_call_limits": {"norm_verification": 8},
        "norm_paragraph_context_policy": {"version": "v"}, **policy}}
    def call(request, identity):
        calls.append(identity)
        return NS(output_text=json.dumps({"assessments": [{"input_id": row["input_id"], "norm_assessment": {
            "relation": "insufficient", "explanation": "Цитата не раскрывает условие",
            "citations": [{"paragraph_id": "p1", "quote": "Цитата"}]}} for row in json.loads(
                request.body["messages"][0]["content"]).get("observations", [])]}), response_sha256="b" * 64,
            truncated=False)  # the runtime reads `truncated` of every reply it receives, as `ModelResponse` carries it
    runtime._norm_batched_v3(session=None, run=NS(run_id="run"), binding=NS(config=NS(model_id="m")), state=state,
        snapshot_id=None, phase=lambda *_: None, call=call, checkpoint=lambda _: None, window_context=window)


def test_the_norm_context_that_pushes_the_request_over_the_ceiling_fails_before_the_call(monkeypatch):
    calls = []
    with pytest.raises(ValueError, match="norm_paragraph_context_request_window_too_large"):
        _norm_run(monkeypatch, attached_size=CEILING + 1, policy={}, calls=calls)
    assert calls == []


def test_the_norm_context_within_the_ceiling_and_a_relaxed_run_reach_the_call(monkeypatch):
    # the request double carries no observations, so the reply double answers none and the batch is refused
    # after the call: what is shown here is only that the size check lets the paid call happen
    for size, policy in ((CEILING, {}), (CEILING + 1, {"unbounded_stats": True})):
        calls = []
        _norm_run(monkeypatch, attached_size=size, policy=policy, calls=calls)
        assert calls == ["norm_verification:b000"]
