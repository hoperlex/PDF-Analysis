"""Six durable Run outcomes stay separate in the review projection."""

from __future__ import annotations

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from auditmanager.runs import v3_group_review as review
from auditmanager.runs.v3_group import GroupMember, GroupView, SCOPES
from auditmanager.runs.v3_review_reader import V3SavedReview
from auditmanager.shared.errors import DomainError, ErrorCode


GROUP_ID = "arg_01M25P3TH08VVTTGJRXYBZZ7RP"
RUN_IDS = tuple(f"run_{scope}" for scope in SCOPES)


def _group(states=("published", "failed", "queued", "partial", "running", "cancelled")):
    return GroupView(
        GROUP_ID, "prj_test", "ver_test", "ns_test",
        "ap_test", "pb_test", "a" * 64, "recorded",
        tuple(GroupMember(
            scope, run_id, state, "b" * 64, f"nrs_{scope}",
        ) for scope, run_id, state in zip(SCOPES, RUN_IDS, states)),
    )


def _saved(run_id, scope):
    return V3SavedReview(run_id, GROUP_ID, scope, {
        "topics": [{
            "item_id": "C01", "mode": "provisional_citation",
            "reason": "edition to review", "source_ids": ["D1_LOCAL"],
            "review_status": "requires_expert_review",
            "provisional_citation_count": 1,
        }, {
            "item_id": "C05", "mode": "context_only",
            "reason": "classification only", "source_ids": ["D6_LOCAL"],
            "review_status": "requires_expert_review",
            "provisional_citation_count": 0,
        }],
        "provisional_citations": [{
            "proposal_ordinal": 0,
            "evidence": [{
                "page_number": 3, "quote": "door width", "block_id": "blk_secret",
            }],
            "citations": [{
                "item_id": "C01", "label": "N1", "document_id": "doc_1",
                "paragraph_id": "par_1", "raw_quote": "approved wording",
                "state": "grounded", "raw_offset": 42,
            }],
        }],
        "withheld_proposals": [], "rejected_proposals": [],
        "reply_ref": {"blob_id": "blob_secret"},
        "provider_body_sha256": "f" * 64,
        "model_payload": "secret answer",
    })


def _arrange(monkeypatch, *, group=None, changed_group=None, refused=False):
    group = _group() if group is None else group
    observed = {"reads": [], "groups": 0}

    def get_group(session, group_id):
        assert group_id == GROUP_ID
        observed["groups"] += 1
        if changed_group is not None and observed["groups"] == 2:
            return changed_group
        return group

    def read_saved(session, run_id, **kwargs):
        observed["reads"].append(run_id)
        if refused and run_id == RUN_IDS[3]:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                stage_id="ar_v3_citation_review", reason="review_blob_digest_invalid",
            )
        return _saved(run_id, SCOPES[RUN_IDS.index(run_id)])

    class Runs:
        def get(self, session, run_id):
            state = group.members[RUN_IDS.index(run_id)].state
            return SimpleNamespace(
                state=state,
                terminal_reason="analysis_failed" if state == "failed" else None,
            )

    monkeypatch.setattr(review, "get_ar_v3_group", get_group)
    monkeypatch.setattr(review, "read_v3_saved_review", read_saved)
    return Runs(), observed


def test_all_six_scopes_keep_their_outcome_and_visible_review(monkeypatch):
    runs, observed = _arrange(monkeypatch, refused=True)
    result = review.read_v3_group_review(
        object(), GROUP_ID, blob_store=object(), runs=runs, blobs=object(),
    )
    assert tuple(member.scope_id for member in result.members) == SCOPES
    assert tuple(member.review_state for member in result.members) == (
        "available", "failed", "pending", "verification_refused", "pending", "failed",
    )
    assert result.members[1].terminal_reason == "analysis_failed"
    assert result.members[3].refusal_code == ErrorCode.ANALYSIS_INPUT_INVALID.value
    assert result.members[3].review is None
    assert result.members[0].review.topics[1].mode == "context_only"
    assert result.members[0].review.topics[1].review_status == "requires_expert_review"
    assert observed["reads"] == [RUN_IDS[0], RUN_IDS[3]]
    assert observed["groups"] == 2


def test_projection_excludes_internal_custody_and_model_payload(monkeypatch):
    runs, observed = _arrange(monkeypatch)
    result = review.read_v3_group_review(
        object(), GROUP_ID, blob_store=object(), runs=runs,
    )
    visible = asdict(result.members[0].review)
    serialised = str(visible)
    assert "blob_secret" not in serialised
    assert "secret answer" not in serialised
    assert "provider_body_sha256" not in serialised
    assert "block_id" not in serialised
    assert "raw_offset" not in serialised
    assert visible["provisional_citations"][0]["citations"][0]["raw_quote"] == "approved wording"


def test_changed_group_membership_refuses_whole_read(monkeypatch):
    initial = _group()
    changed = replace(initial, members=(
        replace(initial.members[0], state="failed"), *initial.members[1:],
    ))
    runs, observed = _arrange(monkeypatch, group=initial, changed_group=changed)
    with pytest.raises(DomainError) as caught:
        review.read_v3_group_review(
            object(), GROUP_ID, blob_store=object(), runs=runs,
        )
    assert caught.value.detail_fields["reason"] == "group_changed_during_review_read"


def test_corrupted_membership_refuses_before_any_review_read(monkeypatch):
    initial = _group()
    malformed = replace(initial, members=initial.members[:-1])
    runs, observed = _arrange(monkeypatch, group=malformed)
    with pytest.raises(DomainError) as caught:
        review.read_v3_group_review(
            object(), GROUP_ID, blob_store=object(), runs=runs,
        )
    assert caught.value.detail_fields["reason"] == "group_members_invalid"
    assert observed["reads"] == []


def test_unexpected_read_error_is_not_hidden_as_member_refusal(monkeypatch):
    runs, observed = _arrange(monkeypatch)

    def unexpected(*args, **kwargs):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="blob_store")

    monkeypatch.setattr(review, "read_v3_saved_review", unexpected)
    with pytest.raises(DomainError) as caught:
        review.read_v3_group_review(
            object(), GROUP_ID, blob_store=object(), runs=runs,
        )
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
