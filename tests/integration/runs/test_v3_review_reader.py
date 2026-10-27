"""The historical AR v3 review reader accepts only a bound settled artifact."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID, canonical_bytes, sha256_hex,
)
from auditmanager.runs import v3_review_reader as reader
from auditmanager.runs.repository import StageResultRow
from auditmanager.runs.v3_group import GroupMember, GroupView
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


RUN_ID = "run_01M25P3TH08VVTTGJRXYBZZ7RP"
GROUP_ID = "arg_01M25P3TH08VVTTGJRXYBZZ7RP"
SET_ID = "nrs_01M25P3TH08VVTTGJRXYBZZ7RP"
SNAPSHOT_ID = "ns_01M59N8QNBVN91ACA2HCE6VE74"
VERSION_ID = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
SHA = lambda letter: letter * 64
METRICS = {
    "model_call_id": "call_test", "candidate_sha256": SHA("a"),
    "provider_body_sha256": SHA("b"),
    "provider_response_sha256": SHA("c"), "set_sha256": SHA("d"),
    "reply_blob_sha256": SHA("e"),
    "provisional_citation_count": 1,
    "withheld_proposal_count": 0, "rejected_proposal_count": 0,
}


def _document():
    return {
        "format": reader.FORMAT, "artifact_role": reader.ROLE,
        "artifact_version": "1.0.0", "run_id": RUN_ID,
        "group_id": GROUP_ID, "scope_id": "F1", "version_uid": VERSION_ID,
        "norms_snapshot_id": SNAPSHOT_ID, "norm_retrieval_set_id": SET_ID,
        "analysis_profile_id": str(AR_V3_BETA_PROFILE_ID),
        "prompt_bundle_id": str(AR_V3_BETA_BUNDLE_ID),
        "source_policy_sha256": SHA("f"),
        "scenario": "new_multi_apartment_residential_F1.3",
        "numeric_output_policy": "expert_review_required",
        "map_sha256": SHA("1"), "set_sha256": SHA("d"),
        "candidate_sha256": SHA("a"), "provider_body_sha256": SHA("b"),
        "provider_response_sha256": SHA("c"),
        "answer_text_sha256": SHA("2"), "model_call_id": "call_test",
        "reply_ref": {"blob_id": str(derive_blob_id(sha256=SHA("e"), size=32)),
                      "sha256": SHA("e"), "size_bytes": 32},
        "topics": [{
            "item_id": "C01", "mode": "provisional_citation", "reason": "verify edition",
            "source_ids": ["D1_LOCAL"], "review_status": "requires_expert_review",
            "provisional_citation_count": 1,
        }, {
            "item_id": "C05", "mode": "context_only", "reason": "classification only",
            "source_ids": ["D6_LOCAL"], "review_status": "requires_expert_review",
            "provisional_citation_count": 0,
        }],
        "provisional_citations": [{
            "proposal_ordinal": 0, "evidence": [{"page_number": 1, "quote": "door"}],
            "citations": [{"item_id": "C01", "label": "N1"}],
        }],
        "withheld_proposals": [], "rejected_proposals": [],
    }


def _arrange(monkeypatch, document=None, *, payload_override=None):
    document = _document() if document is None else document
    payload = canonical_bytes(document) if payload_override is None else payload_override
    digest = sha256_hex(payload)
    blob_id = str(derive_blob_id(sha256=digest, size=len(payload)))
    reference = {
        "role": reader.ROLE, "blob_id": blob_id, "sha256": digest,
        "size_bytes": len(payload), "media_type": "application/json",
    }
    citation = StageResultRow(
        "ar_v3_citation_review", "1.0.0", "succeeded", (reference,), METRICS, None,
    )
    stages = tuple(StageResultRow(
        stage_id, "1.0.0", "succeeded", (), {}, None,
    ) for stage_id in (
        "source_preparation", "page_geometry_extraction", "document_context_build",
    )) + (citation,)
    run = SimpleNamespace(
        run_id=RUN_ID, state="published", version_uid=VERSION_ID,
        norms_snapshot_id=SNAPSHOT_ID, norm_retrieval_set_id=SET_ID,
        analysis_profile_id=str(AR_V3_BETA_PROFILE_ID),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID), provider_mode="recorded",
    )
    scopes = ("F1", "F2", "A1", "A2", "S1", "S2")
    members = tuple(GroupMember(
        scope_id=scope, run_id=RUN_ID if scope == "F1" else f"run_{scope}",
        state="published" if scope == "F1" else "queued",
        map_sha256=SHA("1"), norm_retrieval_set_id=SET_ID,
    ) for scope in scopes)
    group = GroupView(
        GROUP_ID, "prj_test", VERSION_ID, SNAPSHOT_ID,
        str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID), SHA("3"),
        "recorded", members,
    )

    class Runs:
        def __init__(self):
            self.run = run
            self.stages = stages
            self.change_after_read = False
            self.reads = 0

        def get(self, session, run_id):
            assert run_id == RUN_ID
            self.reads += 1
            if self.change_after_read and self.reads == 2:
                return SimpleNamespace(**{**vars(self.run), "state": "failed"})
            return self.run

        def stage_results(self, session, run_id):
            return self.stages

    class Blobs:
        def __init__(self):
            self.metadata = SimpleNamespace(
                is_available=True, sha256=digest, size_bytes=len(payload),
                media_type="application/json",
            )

        def get(self, session, requested):
            assert str(requested) == blob_id
            return self.metadata

    class Store:
        def __init__(self):
            self.payload = payload

        def read(self, requested, *, verify):
            assert str(requested) == blob_id and verify is True
            return self.payload

    runs, blobs, store = Runs(), Blobs(), Store()
    monkeypatch.setattr(reader, "get_ar_v3_group", lambda session, group_id: group)
    # `R-146as`: the Run's findings are none, or the review's provisional proposals (the helper
    # has its own tests); here it answers "none" unless a case says otherwise.
    monkeypatch.setattr(reader, "check_run_published_findings", lambda *args, **kwargs: ())
    return runs, blobs, store, group


def _read(runs, blobs, store):
    return reader.read_v3_saved_review(
        object(), RUN_ID, blob_store=store, runs=runs, blobs=blobs,
    )


def test_saved_review_is_verified_without_current_pack(monkeypatch):
    runs, blobs, store, group = _arrange(monkeypatch)
    review = _read(runs, blobs, store)
    assert (review.run_id, review.group_id, review.scope_id) == (RUN_ID, GROUP_ID, "F1")
    assert review.document["topics"][1]["review_status"] == "requires_expert_review"
    assert runs.reads == 2


@pytest.mark.parametrize("change", ("legacy", "failed", "duplicate", "finding", "blob"))
def test_missing_or_changed_saved_authority_refuses(monkeypatch, change):
    runs, blobs, store, group = _arrange(monkeypatch)
    if change == "legacy":
        runs.run.analysis_profile_id = "legacy-profile"
    elif change == "failed":
        runs.run.state = "failed"
    elif change == "duplicate":
        runs.stages += runs.stages
    elif change == "finding":
        def unexplained(*args, **kwargs):
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID, reason="published_finding_not_in_review",
            )

        monkeypatch.setattr(reader, "check_run_published_findings", unexplained)
    else:
        store.payload += b"x"
    with pytest.raises(DomainError):
        _read(runs, blobs, store)


@pytest.mark.parametrize("field,value", (
    ("scope_id", "F2"), ("map_sha256", SHA("9")),
    ("set_sha256", SHA("9")), ("numeric_output_policy", "model_verdict"),
))
def test_artifact_group_or_metric_drift_refuses(monkeypatch, field, value):
    document = _document()
    document[field] = value
    runs, blobs, store, group = _arrange(monkeypatch, document)
    with pytest.raises(DomainError):
        _read(runs, blobs, store)


def test_context_only_citation_refuses(monkeypatch):
    document = _document()
    document["provisional_citations"][0]["citations"][0]["item_id"] = "C05"
    runs, blobs, store, group = _arrange(monkeypatch, document)
    with pytest.raises(DomainError) as caught:
        _read(runs, blobs, store)
    assert caught.value.detail_fields["reason"] == "review_context_citation_invalid"


def test_noncanonical_json_with_matching_blob_digest_refuses(monkeypatch):
    document = _document()
    formatted = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    runs, blobs, store, group = _arrange(
        monkeypatch, document, payload_override=formatted,
    )
    with pytest.raises(DomainError) as caught:
        _read(runs, blobs, store)
    assert caught.value.detail_fields["reason"] == "review_json_invalid"


def test_succeeded_stage_with_saved_error_refuses(monkeypatch):
    runs, blobs, store, group = _arrange(monkeypatch)
    citation = runs.stages[-1]
    runs.stages = runs.stages[:-1] + (StageResultRow(
        citation.stage_id, citation.stage_version, citation.status,
        citation.artifacts, citation.metrics, {"code": "analysis_failed"},
    ),)
    with pytest.raises(DomainError) as caught:
        _read(runs, blobs, store)
    assert caught.value.detail_fields["reason"] == "review_stage_or_findings_invalid"


def test_changed_run_after_blob_read_refuses(monkeypatch):
    runs, blobs, store, group = _arrange(monkeypatch)
    runs.change_after_read = True
    with pytest.raises(DomainError) as caught:
        _read(runs, blobs, store)
    assert caught.value.detail_fields["reason"] == "review_saved_facts_changed"


def test_findings_the_review_explains_do_not_refuse_and_are_checked_on_both_sides_of_the_read(monkeypatch):
    runs, blobs, store, group = _arrange(monkeypatch)
    calls = []

    def explained(session, **kwargs):
        calls.append(kwargs)
        return ("finding",)

    monkeypatch.setattr(reader, "check_run_published_findings", explained)
    review = _read(runs, blobs, store)
    assert review.run_id == RUN_ID
    assert len(calls) == 2  # once to verify, once more in the final recheck
    assert calls[0]["run_id"] == RUN_ID and calls[0]["version_uid"] == VERSION_ID
    assert calls[0]["profile_id"] == str(AR_V3_BETA_PROFILE_ID)
    assert calls[0]["document"]["provisional_citations"] == _document()["provisional_citations"]


def test_findings_that_change_during_the_read_refuse(monkeypatch):
    runs, blobs, store, group = _arrange(monkeypatch)
    answers = iter([(), ("finding",)])
    monkeypatch.setattr(reader, "check_run_published_findings", lambda *a, **k: next(answers))
    with pytest.raises(DomainError) as caught:
        _read(runs, blobs, store)
    assert caught.value.detail_fields["reason"] == "review_saved_facts_changed"
