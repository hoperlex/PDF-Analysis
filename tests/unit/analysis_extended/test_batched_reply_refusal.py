"""`REVIEW-FIX-ANALYSIS-1102` (S1-sprints-03): a refused paid reply costs its own batch, not the window.

The batched critic, corrector and norm procedures parse each batch's saved reply. A parser refusal
used to reach the single handler at the end of the window, which skipped every later batch, the
corrector and the report. Now the window goes on and the batch says it was refused.

Since `HOTFIX-RUN-COMPLETE-1106` (70159bed6) the critic and the corrector read a reply through
``_received_reply``, which keeps the records that parsed and returns the refusal instead of raising it: the batch is
``partial`` with the ``<kind>_reply_refused`` reason, and the parser's own code is a receipt in ``state["reply_refusals"]``.
The norm procedure still fails a refused batch whole (its parser has no per-record refusals), with the coarse code.
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
    """The `phase` and `call` doubles of one window; replies are chosen by the batch identity.

    The reply double carries what a ``ModelResponse`` always carries and the runtime reads: the text, its digest and ``truncated``
    (the provider cut the reply short). The identities in ``truncated`` answer with that flag set.
    """

    def __init__(self, replies, truncated=()):
        self.replies, self.truncated, self.phases, self.identities = replies, frozenset(truncated), [], []

    def phase(self, identity, status, reason=None):
        self.phases.append((identity, status, reason))

    def call(self, request, identity):
        self.identities.append(identity)
        return NS(output_text=self.replies[identity](json.loads(request.body["messages"][0]["content"])),
            response_sha256="b" * 64, truncated=identity in self.truncated)

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


def _refusal(state, identity):
    """The receipt of the reply refusal of one batch call, and the codes the parser gave for it."""
    receipt, = (row for row in state["reply_refusals"] if row["phase_key"] == identity)
    return receipt, [row["reason"] for row in receipt["rejected_records"]]


@pytest.mark.parametrize("refusal,code", [
    ("not json at all", "reply_unreadable"),
    (json.dumps({"reviews": "x"}), "review_array_schema_invalid"),
])
def test_a_refused_critic_reply_fails_its_batch_and_the_window_goes_on(refusal, code):
    state = _state()
    run = Run({"finding_review:b000": lambda _: refusal, "finding_review:b001": _critic_reply(correct=False)})
    _review(state, run)
    assert run.identities == ["finding_review:b000", "finding_review:b001"]
    refused, done = _receipt(state, "finding_review", 0), _receipt(state, "finding_review", 1)
    assert (refused["status"], refused["reason"]) == ("partial", "finding_review_reply_refused")
    receipt, codes = _refusal(state, "finding_review:b000")
    assert (codes, receipt["status"], receipt["accepted_record_count"]) == ([code], "unresolved", 0)
    assert done["status"] == "completed" and "finding_review:b001" not in {row["phase_key"] for row in state["reply_refusals"]}
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
    refused, done = _receipt(state, "finding_correction", 0), _receipt(state, "finding_correction", 1)
    assert (refused["status"], refused["reason"]) == ("partial", "finding_correction_reply_refused")
    assert _refusal(state, "finding_correction:b000")[1] == ["review_object_schema_invalid"]  # `{}` lacks the `corrections` key of the envelope
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


def test_an_item_the_critic_reply_left_out_says_its_answer_was_refused_not_that_the_plan_cut_it():
    """The records that parsed are kept; the one the reply did not carry is not a casualty of the call limit."""
    whole = _critic_reply(correct=False)

    def short(payload):
        reply = json.loads(whole(payload))
        reply["reviews"].pop()
        return json.dumps(reply, ensure_ascii=False)

    state = _state()
    _review(state, Run({"finding_review:b000": short, "finding_review:b001": whole}))
    receipt, codes = _refusal(state, "finding_review:b000")
    assert (codes, receipt["accepted_record_count"]) == (["critic_input_partition_invalid"], 19)
    assert [item["review_status"] for item in state["observations"][:19]] == ["reviewed"] * 19
    assert (state["observations"][19]["review_status"], state["observations"][19]["review_reason"]) == (
        "not_reviewed", "finding_review_reply_refused")
    assert (_receipt(state, "finding_review", 0)["status"], len(state["reviews"])) == ("partial", COUNT - 1)


def test_a_truncated_critic_reply_keeps_its_valid_records_and_leaves_the_batch_partial():
    """A reply the provider cut short is refused as a whole, yet what parsed is kept (`semantic_repair_attempts` is not approved here)."""
    state = _state()
    run = Run({"finding_review:b000": _critic_reply(correct=False), "finding_review:b001": _critic_reply(correct=False)},
        truncated={"finding_review:b000"})
    _review(state, run)
    assert run.identities == ["finding_review:b000", "finding_review:b001"]  # no repair call without the approval
    refusal, = state["reply_refusals"]
    assert (refusal["phase_key"], refusal["status"], refusal["accepted_record_count"]) == ("finding_review:b000", "unresolved", 20)
    assert refusal["rejected_records"] == [{"reason": "extended_response_truncated", "reply_ordinal": None}]
    cut, whole = _receipt(state, "finding_review", 0), _receipt(state, "finding_review", 1)
    assert (cut["status"], cut["reason"]) == ("partial", "finding_review_reply_refused")
    assert whole["status"] == "completed"
    assert len(state["reviews"]) == COUNT and all(item["review_status"] == "reviewed" for item in state["observations"])
    assert run.last("finding_review") == ("partial", "finding_review_reply_refused")
    assert state["phase_coverage"]["finding_review"]["completed"] == 1


def test_a_refused_norm_reply_fails_its_batch_and_the_other_batch_is_reviewed():
    state, run = _state(candidates=True), Run({"norm_verification:b000": lambda _: "{broken", "norm_verification:b001": _norm_reply})
    runtime._norm_batched_v3(session=None, run=RUN, binding=BINDING, state=state, snapshot_id=None, phase=run.phase,
        call=run.call, checkpoint=lambda _: None, window_context=WINDOW)
    assert run.identities == ["norm_verification:b000", "norm_verification:b001"]
    failed, done = _receipt(state, "norm_verification", 0), _receipt(state, "norm_verification", 1)
    # the batch fails whole under the coarse code; what the parser said about the reply is the refusal receipt
    assert (failed["status"], failed["reason"], failed["error_code"]) == (
        "failed", "norm_verification_reply_refused", "norm_verification_reply_refused")
    assert _refusal(state, "norm_verification:b000")[1] == ["reply_unreadable"]
    assert done["status"] == "completed"
    assert {item["norm_review_reason"] for item in state["observations"][:20]} == {"norm_verification_reply_refused"}
    assert state["observations"][20]["norm_review_status"] == "reviewed" and "norm_assessment" in state["observations"][20]
    assert all("norm_assessment" not in item for item in state["observations"][:20])
    assert run.last("norm_verification") == ("partial", "norm_verification_reply_refused")


def test_the_error_code_of_a_refusal_keeps_a_parser_code_and_drops_a_decoder_message():
    assert runtime._reply_refusal_code(ValueError("critic_input_partition_invalid")) == "critic_input_partition_invalid"
    assert runtime._reply_refusal_code(ValueError("Expecting value: line 1 column 1 (char 0)")) == "reply_unreadable"
    assert runtime._reply_refusal_code(ValueError("")) == "reply_unreadable"
