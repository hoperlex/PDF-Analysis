"""The beta review artifact contains citations and dispositions, never a verdict."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auditmanager.analysis.profiles.ar_v3.citation_grounding import (
    GroundedV3Candidate, RejectedV3Proposal, V3GroundingResult,
)
from auditmanager.analysis.profiles.ar_v3.local_evaluation import LocalV3Evaluation
from auditmanager.analysis.profiles.ar_v3.response import (
    ProposedEvidence, ProposedNormCitation, ProposedObservation,
)
from auditmanager.analysis.public import ModelResponse, sha256_hex
from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.norms.public import GroundedNormCitation
from auditmanager.runs.v3_citations import V3BetaCitationReview, V3BetaTopicReview
from auditmanager.runs.v3_cite_preflight import V3CitePreflight
from auditmanager.runs import v3_review_artifact as artifact
from auditmanager.shared.errors import DomainError, ErrorCode


def _proposal(label: str) -> ProposedObservation:
    return ProposedObservation(
        category="evacuation", finding_text="Вывод 999 м — проверить",
        recommendation_text="Исправить до 999 м", proposed_severity="operational",
        evidence=(ProposedEvidence(1, "Ширина 1,2 м"),),
        norm_citations=(ProposedNormCitation(label, "Пункт 1,4 м"),),
        required_value="999 м", stated_value="1,2 м",
    )


def _accepted(ordinal: int, label: str) -> GroundedV3Candidate:
    return GroundedV3Candidate(
        ordinal, _proposal(label),
        (ResolvedAnchor(1, "Ширина 1,2 м", 4, 17),),
        (GroundedNormCitation(
            label, "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ",
            "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK", 20,
            "Пункт 1,4 м", "verified",
        ),),
    )


def _value() -> V3CitePreflight:
    set_bytes = json.dumps({
        "prompt_part": json.dumps({"paragraphs": [
            {"label": "N1", "item_id": "C01"},
            {"label": "N2", "item_id": "C05"},
        ]}),
    }).encode()
    request = SimpleNamespace(
        candidate=SimpleNamespace(item_ids=("C01", "C05"), scope_id="F2"),
        verified_set=SimpleNamespace(
            data=set_bytes, set_sha256="c" * 64,
            norms_snapshot_id="ns_test", map_sha256="d" * 64,
        ),
    )
    binding = SimpleNamespace(
        run_id="run_test", group_id="arg_test", scope_id="F2",
        version_uid="ver_test", norms_snapshot_id="ns_test",
        norm_retrieval_set_id="nrs_test", analysis_profile_id="ap_test",
        prompt_bundle_id="pb_test", map_sha256="d" * 64,
        set_sha256="c" * 64, policy_sha256="f" * 64,
    )
    prepared = SimpleNamespace(
        pinned_corpus=request, binding=binding,
        candidate_sha256="a" * 64, provider_body_sha256="b" * 64,
    )
    response = ModelResponse("ответ 999 м", "end_turn", 11, 13, 17, 0.012)
    call = SimpleNamespace(
        run_id="run_test", scope_id="F2", model_call_id="call_test",
        set_sha256="c" * 64, candidate_sha256="a" * 64,
        request_sha256="b" * 64, response_sha256=response.response_sha256,
        reply_blob_id="blob_01M2545JSD15ETSNNV904X991J",
        reply_blob_sha256="e" * 64, reply_blob_size=401,
    )
    evaluation = LocalV3Evaluation(
        "a" * 64, sha256_hex(response.output_text.encode()),
        V3GroundingResult(
            (_accepted(0, "N1"), _accepted(1, "N2")),
            (RejectedV3Proposal(2, "quotation_absent"),), 0, False,
        ),
    )
    review = V3BetaCitationReview(
        request, evaluation, "f" * 64,
        "new_multi_apartment_residential_F1.3", "expert_review_required",
        (V3BetaTopicReview("C01", "provisional_citation", "check edition", ("SP54",)),
         V3BetaTopicReview("C05", "context_only", "unresolved", ("SP51",))),
        (0,), (1,),
    )
    return V3CitePreflight(prepared, call, SimpleNamespace(model_response=response), review)


def test_canonical_artifact_has_all_topics_and_only_provisional_grounded_quotes():
    value = _value()
    first = artifact.build_v3_beta_review_artifact(value)
    second = artifact.build_v3_beta_review_artifact(value)
    document = json.loads(first.payload)
    assert first == second
    assert first.sha256 == sha256_hex(first.payload)
    assert first.size_bytes == len(first.payload)
    assert document["format"] == artifact.FORMAT
    assert document["model_call_id"] == "call_test"
    assert [row["item_id"] for row in document["topics"]] == ["C01", "C05"]
    assert [row["review_status"] for row in document["topics"]] == [
        "requires_expert_review", "requires_expert_review",
    ]
    assert [row["provisional_citation_count"] for row in document["topics"]] == [1, 0]
    assert document["provisional_citations"][0]["citations"][0]["item_id"] == "C01"
    assert document["withheld_proposals"] == [
        {"proposal_ordinal": 1, "reason": "context_only_or_mixed_source"},
    ]
    assert document["rejected_proposals"] == [
        {"proposal_ordinal": 2, "reason": "quotation_absent"},
    ]
    assert b"required_value" not in first.payload
    assert b"stated_value" not in first.payload
    assert b"999" not in first.payload
    assert b"recommendation_text" not in first.payload


@pytest.mark.parametrize("change", [
    "request", "response", "topics", "classification", "salvaged", "malformed",
    "context_laundered", "duplicate_label",
])
def test_mismatched_or_incomplete_review_refuses(change):
    value = _value()
    if change == "request":
        value = replace(value, prepared=SimpleNamespace(
            **{**vars(value.prepared), "candidate_sha256": "0" * 64}))
    elif change == "response":
        value = replace(value, review=replace(
            value.review, evaluation=replace(
                value.review.evaluation, response_sha256="0" * 64)))
    elif change == "topics":
        value = replace(value, review=replace(
            value.review, topics=value.review.topics[:1]))
    elif change == "classification":
        value = replace(value, review=replace(
            value.review, withheld_proposal_ordinals=()))
    elif change == "salvaged":
        value = replace(value, review=replace(value.review, evaluation=replace(
            value.review.evaluation, grounding=replace(
                value.review.evaluation.grounding, salvaged=True))))
    elif change == "malformed":
        value = replace(value, review=replace(value.review, evaluation=replace(
            value.review.evaluation, grounding=replace(
                value.review.evaluation.grounding, malformed_count=1))))
    elif change == "context_laundered":
        value = replace(value, review=replace(
            value.review, provisional_proposal_ordinals=(0, 1),
            withheld_proposal_ordinals=()))
    else:
        raw = json.loads(value.prepared.pinned_corpus.verified_set.data)
        raw["prompt_part"] = json.dumps({"paragraphs": [
            {"label": "N1", "item_id": "C01"},
            {"label": "N1", "item_id": "C05"},
        ]})
        value.prepared.pinned_corpus.verified_set.data = json.dumps(raw).encode()
    with pytest.raises(DomainError) as caught:
        artifact.build_v3_beta_review_artifact(value)
    assert caught.value.code is ErrorCode.ANALYSIS_INPUT_INVALID


def test_artifact_cap_refuses(monkeypatch):
    monkeypatch.setattr(artifact, "MAX_REVIEW_BYTES", 100)
    with pytest.raises(DomainError) as caught:
        artifact.build_v3_beta_review_artifact(_value())
    assert caught.value.detail_fields["reason"] == "review_artifact_too_large"
