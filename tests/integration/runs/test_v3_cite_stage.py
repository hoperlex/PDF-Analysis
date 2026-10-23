"""The CITE stage binds review Blob and StageResult under one Attempt."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import StageStatus
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_cite_stage as stage
from auditmanager.runs.v3_review_artifact import BuiltV3ReviewArtifact
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import derive_blob_id


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_cite", "lease_test", "secret")
NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)
PAYLOAD = b'{"format":"ar-v3-beta-citation-review/1"}'
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
ARTIFACT = BuiltV3ReviewArtifact("analysis.v3_beta_review", PAYLOAD, DIGEST, len(PAYLOAD))


class FakeSession:
    def __init__(self, events):
        self.events = events

    def commit(self):
        self.events.append("commit")


class FakeRuns:
    def __init__(self, events):
        self.events = events
        self.before = (SimpleNamespace(stage_id="source_preparation"),)
        self.existing = False
        self.change_after_publish = False
        self.change_before_publish = False
        self.preflight_complete = False
        self.published = False
        self.records = []

    def stage_results(self, session, run_id):
        assert run_id == AUTHORITY.run_id
        if self.existing:
            return self.before + (SimpleNamespace(stage_id="ar_v3_citation_review"),)
        if self.change_after_publish and self.published:
            return self.before + (SimpleNamespace(stage_id="foreign"),)
        if self.change_before_publish and self.preflight_complete:
            return self.before + (SimpleNamespace(stage_id="foreign"),)
        return self.before

    def stage_started(self, session, *, run_id, stage_id):
        assert run_id == AUTHORITY.run_id
        assert stage_id == "ar_v3_citation_review"
        self.events.append("stage_started")

    def record_stage_result(self, session, *, run_id, document):
        assert run_id == AUTHORITY.run_id
        self.events.append("stage_recorded")
        self.records.append(document)


class FakeJobs:
    def __init__(self, events, call):
        self.events = events
        self.call = call
        self.stale_after_publish = False
        self.published = False

    def require_current(self, session, authority):
        assert authority is AUTHORITY
        self.events.append("current_checked")
        if self.stale_after_publish and self.published:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    def completed_v3_call(self, session, authority):
        self.require_current(session, authority)
        return self.call

    def bind_artifacts(self, session, authority, *, stage_id, artifacts):
        self.require_current(session, authority)
        assert stage_id == "ar_v3_citation_review"
        assert len(artifacts) == 1
        self.events.append("artifact_bound")
        return (artifacts[0].blob_id,)


class FakeBlobs:
    def __init__(self, events):
        self.events = events

    def mark_available(self, session, blob_id):
        self.events.append("blob_available")


class FakePublication:
    def __init__(self, session, events, runs, jobs):
        self.session = session
        self.events = events
        self.runs = runs
        self.jobs = jobs
        self.bad_readback = False

    def put_blob(self, payload, *, declared_sha256, declared_size, role, media_type):
        assert payload == PAYLOAD
        assert declared_sha256 == DIGEST and declared_size == len(PAYLOAD)
        assert role == "analysis_v3_beta_review"
        assert media_type == "application/json"
        self.events.append("outbox_intent")
        self.session.commit()
        self.events.append("blob_published")
        self.runs.published = self.jobs.published = True
        return SimpleNamespace(
            blob_id=derive_blob_id(sha256=DIGEST, size=len(PAYLOAD)),
            sha256=DIGEST, size=len(PAYLOAD), media_type=media_type,
        )

    def read(self, blob_id, *, verify):
        assert verify is True
        self.events.append("blob_readback")
        return b"wrong" if self.bad_readback else PAYLOAD


def _arrange(monkeypatch):
    events = []
    session = FakeSession(events)
    binding = SimpleNamespace(run_id=AUTHORITY.run_id, scope_id="F1")
    call = SimpleNamespace(
        model_call_id="call_test", candidate_sha256="a" * 64,
        request_sha256="b" * 64, response_sha256="c" * 64,
        set_sha256="d" * 64, reply_blob_sha256="e" * 64,
    )
    runs = FakeRuns(events)
    jobs = FakeJobs(events, call)
    blobs = FakeBlobs(events)
    publication = FakePublication(session, events, runs, jobs)
    preflight = SimpleNamespace(
        prepared=SimpleNamespace(binding=binding), completed_call=call,
        review=SimpleNamespace(
            provisional_proposal_ordinals=(0,), withheld_proposal_ordinals=(1,),
            evaluation=SimpleNamespace(grounding=SimpleNamespace(rejected=())),
        ),
    )

    def prepare(session_, **kwargs):
        assert session_ is session
        assert kwargs["authority"] is AUTHORITY
        assert "settings" not in kwargs
        events.append("preflight")
        runs.preflight_complete = True
        return preflight

    monkeypatch.setattr(stage, "resolve_v3_execution_binding",
                        lambda *args, **kwargs: binding)
    monkeypatch.setattr(stage, "prepare_v3_cite_preflight", prepare)
    monkeypatch.setattr(stage, "build_v3_beta_review_artifact",
                        lambda value: ARTIFACT)
    monkeypatch.setattr(stage, "_publication_store",
                        lambda *args, **kwargs: publication)
    return session, runs, jobs, blobs, publication, events


def _run(session, runs, jobs, blobs):
    return stage.run_v3_cite_stage(
        session, authority=AUTHORITY, registry=object(), blob_store=object(),
        max_text_bytes=100_000,
        jobs=jobs, runs=runs, blobs=blobs, clock=lambda: NOW,
    )


def test_success_commits_intent_before_blob_then_result_and_binding_together(monkeypatch):
    session, runs, jobs, blobs, _, events = _arrange(monkeypatch)
    result = _run(session, runs, jobs, blobs)
    assert result.status is StageStatus.SUCCEEDED
    assert result.artifact("analysis.v3_beta_review").sha256 == DIGEST
    assert result.metrics["model_call_id"] == "call_test"
    assert runs.records == [result.to_document()]
    assert events.index("stage_started") < events.index("preflight")
    assert events.index("outbox_intent") < events.index("blob_published")
    assert events.index("blob_readback") < events.index("stage_recorded")
    assert events[-5:] == [
        "stage_recorded", "current_checked", "artifact_bound",
        "blob_available", "commit",
    ]


def test_existing_cite_stage_refuses_before_a_new_event(monkeypatch):
    session, runs, jobs, blobs, _, events = _arrange(monkeypatch)
    runs.existing = True
    with pytest.raises(DomainError) as caught:
        _run(session, runs, jobs, blobs)
    assert caught.value.detail_fields["reason"] == "citation_stage_already_recorded"
    assert "stage_started" not in events and "outbox_intent" not in events


def test_grounding_refusal_records_failed_stage_without_blob(monkeypatch):
    session, runs, jobs, blobs, _, events = _arrange(monkeypatch)

    def refuse(*args, **kwargs):
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                          stage_id="text_analysis", reason="quote_missing")

    monkeypatch.setattr(stage, "prepare_v3_cite_preflight", refuse)
    result = _run(session, runs, jobs, blobs)
    assert result.status is StageStatus.FAILED
    assert result.artifacts == ()
    assert runs.records == [result.to_document()]
    assert "outbox_intent" not in events
    assert events[-2:] == ["stage_recorded", "commit"]


def test_prior_stage_change_after_preflight_refuses_before_blob(monkeypatch):
    session, runs, jobs, blobs, _, events = _arrange(monkeypatch)
    runs.change_before_publish = True
    with pytest.raises(DomainError) as caught:
        _run(session, runs, jobs, blobs)
    assert caught.value.detail_fields["reason"] == "citation_inputs_changed_before_publication"
    assert "outbox_intent" not in events
    assert "stage_recorded" not in events


@pytest.mark.parametrize("failure", ["stale", "rows", "readback"])
def test_post_publication_refusal_never_records_success(monkeypatch, failure):
    session, runs, jobs, blobs, publication, events = _arrange(monkeypatch)
    if failure == "stale":
        jobs.stale_after_publish = True
    elif failure == "rows":
        runs.change_after_publish = True
    else:
        publication.bad_readback = True
    with pytest.raises(DomainError):
        _run(session, runs, jobs, blobs)
    assert "outbox_intent" in events
    assert "stage_recorded" not in events
    assert "artifact_bound" not in events
