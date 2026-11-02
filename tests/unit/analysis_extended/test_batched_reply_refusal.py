"""`REVIEW-FIX-ANALYSIS-1102` (S1-sprints-03): a refused paid reply costs its own batch, not the window.

The batched critic, corrector and norm procedures parse each batch's saved reply. A parser refusal
used to reach the single handler at the end of the window, which skipped every later batch, the
corrector and the report. Now the batch gets a ``failed`` receipt and the window goes on.
"""
import json
from types import SimpleNamespace as NS

import pytest

from auditmanager.runs import extended_review as runtime

QUOTE = "Размер проёма 1200 мм принят по проекту"
SOURCES = [{"source_id": "s1", "kind": "text", "source_type": "native_text", "page_number": 1, "quote": QUOTE}]
LIMITS = {kind: 8 for kind in ("finding_review", "finding_correction", "norm_verification")}
WINDOW = {"window_id": "w1", "policy": {"phase_call_limits": LIMITS}}
RUN = NS(run_id="run")
BINDING = NS(config=NS(model_id="claude-opus-5"))
COUNT = 21  # one batch of 20 observations and a second of 1


def _state(*, candidates=False):
    observations = []
    for number in range(COUNT):
        item = {"title": f"Наблюдение {number:02d}", "description": "Описание", "source_ids": ["s1"]}
        if candidates:
            item["norm_candidates"] = [{"snapshot_id": "ns_x", "document_id": "ndoc_x", "paragraph_id": f"p{number:02d}",
                "designation": "СП 1", "clause_number": "1.1", "quote": f"Цитата {number:02d}", "page_label": 1,
                "status": "candidate_not_verified"}]
        observations.append(item)
    return {"section": "AR", "source_sha256": "a" * 64, "sources": SOURCES, "observations": observations,
        "warnings": [], "coverage": {"blocks_total": 0, "blocks_processed": 0, "blocks_remaining": 0}}


class Run:
    """The `phase` and `call` doubles of one window; replies are chosen by the batch identity."""

    def __init__(self, replies):
        self.replies, self.phases, self.identities = replies, [], []

    def phase(self, identity, status, reason=None):
        self.phases.append((identity, status, reason))

    def call(self, request, identity):
        self.identities.append(identity)
        return NS(output_text=self.replies[identity](json.loads(request.body["messages"][0]["content"])),
            response_sha256="b" * 64)

    def last(self, identity):
        return [row[1:] for row in self.phases if row[0] == identity][-1]


def _critic_reply(*, correct):
    def reply(payload):
        return json.dumps({"reviews": [{"input_id": row["input_id"], "source_ids": row["source_ids"],
            "llm_decision": "rewrite" if correct else "accept", "human_taxonomy_reason": "other", "confidence": 0.5,
            "explanation": "Пояснение", "evidence_checked": True, "source_dependency": "enough_source",
            "needs_correction": correct, "suggested_fix": "Уточнить" if correct else "", "source_evidence": []}
            for row in payload["observations"]]}, ensure_ascii=False)
    return reply


def _corrector_reply(payload):
    return json.dumps({"corrections": [{"input_id": row["input_id"], "action": "retain",
        "source_ids": row["source_ids"], "proposed_title": row["title"], "proposed_description": row["description"],
        "proposed_source_ids": row["source_ids"], "source_evidence": [], "explanation": "Достаточно",
        "required_context": []} for row in payload["observations"]]}, ensure_ascii=False)


def _norm_reply(payload):
    quotes = {row["paragraph_id"]: row["quote"] for row in payload["norm_context"]}
    return json.dumps({"assessments": [{"input_id": row["input_id"], "norm_assessment": {
        "relation": "insufficient", "explanation": "Цитата не раскрывает условие",
        "citations": [{"paragraph_id": row["norm_candidate_ids"][0], "quote": quotes[row["norm_candidate_ids"][0]]}]}}
        for row in payload["observations"]]}, ensure_ascii=False)


def _review(state, run):
    runtime._review_batched_v3(run=RUN, binding=BINDING, state=state, phase=run.phase, call=run.call,
        window_context=WINDOW, contexts=[])


def _receipt(state, kind, index):
    return next(row for row in state["batches"] if row["procedure"] == kind and row["index"] == index)


@pytest.mark.parametrize("refusal,code", [
    ("not json at all", "reply_unreadable"),
    (json.dumps({"reviews": "x"}), "review_array_schema_invalid"),
])
def test_a_refused_critic_reply_fails_its_batch_and_the_window_goes_on(refusal, code):
    state = _state()
    run = Run({"finding_review:b000": lambda _: refusal, "finding_review:b001": _critic_reply(correct=False)})
    _review(state, run)
    assert run.identities == ["finding_review:b000", "finding_review:b001"]
    failed, done = _receipt(state, "finding_review", 0), _receipt(state, "finding_review", 1)
    assert (failed["status"], failed["reason"], failed["error_code"]) == ("failed", "finding_review_reply_refused", code)
    assert done["status"] == "completed"
    # the items of the failed batch say why they have no critique; the other batch's item has one
    assert {item["review_reason"] for item in state["observations"][:20]} == {"finding_review_reply_refused"}
    assert all(item["review_status"] == "not_reviewed" for item in state["observations"][:20])
    assert state["observations"][20]["review_status"] == "reviewed" and len(state["reviews"]) == 1
    # the procedure is partial with the refusal as its reason, and the report still ran
    assert run.last("finding_review") == ("partial", "finding_review_reply_refused")
    assert run.last("report_generation") == ("completed", None) and state["report"]["observation_count"] == COUNT
    assert state["phase_coverage"]["finding_review"]["completed"] == 1
    assert state["phase_coverage"]["finding_review"]["remaining"] == 1


def test_a_refused_corrector_reply_fails_its_batch_and_the_later_batch_is_still_corrected():
    state = _state()
    run = Run({"finding_review:b000": _critic_reply(correct=True), "finding_review:b001": _critic_reply(correct=True),
        "finding_correction:b000": lambda _: "{}", "finding_correction:b001": _corrector_reply})
    _review(state, run)
    assert run.identities[-2:] == ["finding_correction:b000", "finding_correction:b001"]
    failed, done = _receipt(state, "finding_correction", 0), _receipt(state, "finding_correction", 1)
    assert (failed["status"], failed["reason"]) == ("failed", "finding_correction_reply_refused")
    assert done["status"] == "completed"
    assert len(state["corrections"]) == 1 and run.last("finding_correction") == ("partial", "finding_correction_reply_refused")
    assert run.last("finding_review") == ("completed", None)
    assert run.last("report_generation") == ("completed", None)


def test_a_clean_run_leaves_every_batch_completed():
    state = _state()
    run = Run({"finding_review:b000": _critic_reply(correct=False), "finding_review:b001": _critic_reply(correct=False)})
    _review(state, run)
    assert [row["status"] for row in state["batches"] if row["procedure"] == "finding_review"] == ["completed"] * 2
    assert run.last("finding_review") == ("completed", None) and run.last("finding_correction") == ("completed", "no_corrections_requested")


def test_a_refused_norm_reply_fails_its_batch_and_the_other_batch_is_reviewed():
    state, run = _state(candidates=True), Run({"norm_verification:b000": lambda _: "{broken", "norm_verification:b001": _norm_reply})
    runtime._norm_batched_v3(session=None, run=RUN, binding=BINDING, state=state, snapshot_id=None, phase=run.phase,
        call=run.call, checkpoint=lambda _: None, window_context=WINDOW)
    assert run.identities == ["norm_verification:b000", "norm_verification:b001"]
    failed, done = _receipt(state, "norm_verification", 0), _receipt(state, "norm_verification", 1)
    assert (failed["status"], failed["reason"], failed["error_code"]) == ("failed", "norm_verification_reply_refused", "reply_unreadable")
    assert done["status"] == "completed"
    assert {item["norm_review_reason"] for item in state["observations"][:20]} == {"norm_verification_reply_refused"}
    assert state["observations"][20]["norm_review_status"] == "reviewed" and "norm_assessment" in state["observations"][20]
    assert all("norm_assessment" not in item for item in state["observations"][:20])
    assert run.last("norm_verification") == ("partial", "norm_verification_reply_refused")


def test_the_error_code_of_a_refusal_keeps_a_parser_code_and_drops_a_decoder_message():
    assert runtime._reply_refusal_code(ValueError("critic_input_partition_invalid")) == "critic_input_partition_invalid"
    assert runtime._reply_refusal_code(ValueError("Expecting value: line 1 column 1 (char 0)")) == "reply_unreadable"
    assert runtime._reply_refusal_code(ValueError("")) == "reply_unreadable"
