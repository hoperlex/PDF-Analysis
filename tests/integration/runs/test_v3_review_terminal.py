"""AR v3 closes a Run on the saved review without publishing findings."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_review_terminal as terminal
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError
from auditmanager.storage.public import derive_blob_id


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")
SHA = lambda letter: letter * 64
REF = {
    "role": "analysis.v3_beta_review",
    "blob_id": str(derive_blob_id(sha256=SHA("f"), size=100)),
    "sha256": SHA("f"), "size_bytes": 100, "media_type": "application/json",
}
METRICS = {
    "model_call_id": "call_test", "candidate_sha256": SHA("a"),
    "provider_body_sha256": SHA("b"),
    "provider_response_sha256": SHA("c"),
    "set_sha256": SHA("d"), "reply_blob_sha256": SHA("e"),
    "provisional_citation_count": 1,
    "withheld_proposal_count": 2, "rejected_proposal_count": 0,
}


def _row(stage_id, *, status="succeeded", metrics=None, artifacts=(), error=None):
    return StageResultRow(
        stage_id=stage_id, stage_version="1.0.0", status=status,
        artifacts=artifacts, metrics={} if metrics is None else metrics,
        error=error,
    )


def _rows(*, cite_status="succeeded"):
    citation = _row(
        "ar_v3_citation_review", status=cite_status,
        metrics=METRICS if cite_status == "succeeded" else {},
        artifacts=(REF,) if cite_status == "succeeded" else (),
        error=None if cite_status == "succeeded" else {
            "code": "analysis_input_invalid", "details": {},
        },
    )
    return tuple(_row(stage) for stage in (
        "source_preparation", "page_geometry_extraction", "document_context_build",
    )) + (citation,)


class Runs:
    def __init__(self, rows):
        self.rows = rows
        self.events = []
        self.change_after_advance = False

    def stage_results(self, session, run_id):
        assert run_id == AUTHORITY.run_id
        if self.change_after_advance and "advance" in self.events:
            return self.rows[:-1]
        return self.rows

    def advance(self, session, **kwargs):
        assert kwargs["from_state"] == "running"
        self.events.append("advance")

    def terminate(self, session, **kwargs):
        self.events.append(("terminate", kwargs))


class Jobs:
    def __init__(self):
        self.finished = None
        self.call = SimpleNamespace(
            run_id=AUTHORITY.run_id, scope_id="F1", set_sha256=SHA("d"),
            status="succeeded", model_call_id="call_test",
            candidate_sha256=SHA("a"), request_sha256=SHA("b"),
            response_sha256=SHA("c"), reply_blob_sha256=SHA("e"),
        )
        self.reads = 0

    def completed_v3_call(self, session, authority):
        self.reads += 1
        return self.call

    def finish_execution(self, session, authority, *, publishes_result):
        assert authority is AUTHORITY
        self.finished = publishes_result


def _arrange(monkeypatch, rows=None):
    runs = Runs(_rows() if rows is None else rows)
    jobs = Jobs()
    monkeypatch.setattr(terminal, "resolve_v3_execution_binding",
                        lambda *args, **kwargs: SimpleNamespace(
                            run_id=AUTHORITY.run_id, scope_id="F1", set_sha256=SHA("d"),
                        ))
    monkeypatch.setattr(terminal, "publication_rows_exist", lambda *args: False)
    return runs, jobs


def _finish(runs, jobs):
    return terminal.finish_v3_review_run(
        object(), authority=AUTHORITY, registry=object(), jobs=jobs, runs=runs,
    )


def test_success_publishes_only_review_stage(monkeypatch):
    runs, jobs = _arrange(monkeypatch)
    result = _finish(runs, jobs)
    assert result.selection.state == "published"
    assert jobs.reads == 1 and jobs.finished is True
    assert runs.events[0] == "advance"
    assert runs.events[1][0] == "terminate"
    assert runs.events[1][1]["to_state"] == "published"
    assert set(result.stage_statuses) == {
        "source_preparation", "page_geometry_extraction",
        "document_context_build", "ar_v3_citation_review",
    }


def test_failed_citation_terminates_failed_without_completed_call(monkeypatch):
    runs, jobs = _arrange(monkeypatch, _rows(cite_status="failed"))
    result = _finish(runs, jobs)
    assert result.selection.state == "failed"
    assert jobs.reads == 0 and jobs.finished is False
    assert runs.events[1][1]["to_state"] == "failed"


def test_unexpected_legacy_stage_cannot_publish_v3(monkeypatch):
    runs, jobs = _arrange(monkeypatch, _rows() + (_row("finding_merge"),))
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs)
    assert caught.value.detail_fields["reason"] == "unexpected_stage_result"
    assert runs.events == [] and jobs.finished is None


def test_changed_call_or_stage_refuses_before_terminal(monkeypatch):
    runs, jobs = _arrange(monkeypatch)
    jobs.call = SimpleNamespace(**{**vars(jobs.call), "response_sha256": SHA("9")})
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs)
    assert caught.value.detail_fields["reason"] == "review_call_binding_changed"
    assert runs.events == []

    runs, jobs = _arrange(monkeypatch)
    runs.change_after_advance = True
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs)
    assert caught.value.detail_fields["reason"] == "review_inputs_changed_before_terminal"
    assert runs.events == ["advance"] and jobs.finished is None
