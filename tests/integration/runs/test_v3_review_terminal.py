"""AR v3 closes a Run on the saved review; `R-146as` publishes the provisional findings first."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_review_terminal as terminal
from auditmanager.runs.repository import StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode
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
    "provisional_citation_count": 0,
    "withheld_proposal_count": 2, "rejected_proposal_count": 0,
}
PROVISIONAL_METRICS = {**METRICS, "provisional_citation_count": 2}


def _row(stage_id, *, status="succeeded", metrics=None, artifacts=(), error=None):
    return StageResultRow(
        stage_id=stage_id, stage_version="1.0.0", status=status,
        artifacts=artifacts, metrics={} if metrics is None else metrics,
        error=error,
    )


def _rows(*, cite_status="succeeded", metrics=METRICS):
    citation = _row(
        "ar_v3_citation_review", status=cite_status,
        metrics=metrics if cite_status == "succeeded" else {},
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


def _finish(runs, jobs, **kwargs):
    return terminal.finish_v3_review_run(
        object(), authority=AUTHORITY, registry=object(), jobs=jobs, runs=runs, **kwargs,
    )


def test_a_review_with_no_provisional_proposal_publishes_no_finding_and_rebuilds_nothing(monkeypatch):
    """Before `R-146as` this was the only success: the Run closes on the sealed review alone."""
    runs, jobs = _arrange(monkeypatch)
    monkeypatch.setattr(terminal, "_rebuild_candidates", lambda *a, **k: pytest.fail("nothing to rebuild"))
    monkeypatch.setattr(terminal, "_publish_candidates", lambda *a, **k: pytest.fail("nothing to publish"))
    result = _finish(runs, jobs)
    assert result.published_findings == ()
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


# --- `R-146as`: the provisional proposals become findings, inside the terminal transaction --------

CANDIDATES = ("candidate-0", "candidate-1")


def _publishing(monkeypatch, *, metrics=PROVISIONAL_METRICS):
    runs, jobs = _arrange(monkeypatch, _rows(metrics=metrics))
    order = runs.events

    def rebuild(session, **kwargs):
        order.append("rebuild")
        assert kwargs["review"].metrics["provisional_citation_count"] == 2
        return CANDIDATES, b"set-bytes"

    def publish(session, *, authority, model_call_id, set_bytes, candidates):
        order.append(("publish", candidates))
        assert authority is AUTHORITY and model_call_id == "call_test" and set_bytes == b"set-bytes"
        return tuple(SimpleNamespace(finding_uid=f"fnd_{i}") for i, _ in enumerate(candidates))

    monkeypatch.setattr(terminal, "_rebuild_candidates", rebuild)
    monkeypatch.setattr(terminal, "_publish_candidates", publish)
    return runs, jobs


def test_provisional_proposals_are_rebuilt_before_the_run_leaves_running_and_published_before_it_terminates(monkeypatch):
    runs, jobs = _publishing(monkeypatch)
    result = _finish(runs, jobs, blob_store=object())
    assert [e if isinstance(e, str) else e[0] for e in runs.events] == [
        "rebuild", "advance", "publish", "terminate",
    ]
    assert runs.events[2] == ("publish", CANDIDATES)
    assert len(result.published_findings) == 2
    assert result.selection.state == "published" and jobs.finished is True


def test_a_failure_while_publishing_closes_nothing(monkeypatch):
    runs, jobs = _publishing(monkeypatch)

    def refuse(*args, **kwargs):
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="publication_refused:x")

    monkeypatch.setattr(terminal, "_publish_candidates", refuse)
    with pytest.raises(DomainError):
        _finish(runs, jobs, blob_store=object())
    assert [e for e in runs.events if isinstance(e, tuple)] == []  # no terminate was reached
    assert jobs.finished is None


def test_a_rebuild_that_cannot_be_done_refuses_before_the_run_transition(monkeypatch):
    runs, jobs = _publishing(monkeypatch)

    def refuse(*args, **kwargs):
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="rebuilt_review_differs_from_sealed")

    monkeypatch.setattr(terminal, "_rebuild_candidates", refuse)
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs, blob_store=object())
    assert caught.value.detail_fields["reason"] == "rebuilt_review_differs_from_sealed"
    assert runs.events == [] and jobs.finished is None


def test_a_failed_run_publishes_nothing_whatever_the_metrics_say(monkeypatch):
    runs, jobs = _publishing(monkeypatch)
    runs.rows = _rows(cite_status="failed")
    result = _finish(runs, jobs, blob_store=object())
    assert result.selection.state == "failed" and result.published_findings == ()
    assert "rebuild" not in runs.events and not any(isinstance(e, tuple) and e[0] == "publish" for e in runs.events)


def test_a_second_publication_for_a_run_is_refused_before_anything_is_rebuilt(monkeypatch):
    runs, jobs = _publishing(monkeypatch)
    monkeypatch.setattr(terminal, "publication_rows_exist", lambda *args: True)
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs, blob_store=object())
    assert caught.value.detail_fields["reason"] == "canonical_finding_already_published"
    assert runs.events == []


def test_rows_that_appear_after_the_transition_refuse_before_publishing(monkeypatch):
    runs, jobs = _publishing(monkeypatch)
    answers = iter([False, True])  # none at the first look, a row after `advance`
    monkeypatch.setattr(terminal, "publication_rows_exist", lambda *args: next(answers))
    with pytest.raises(DomainError) as caught:
        _finish(runs, jobs, blob_store=object())
    assert caught.value.detail_fields["reason"] == "review_inputs_changed_before_terminal"
    assert not any(isinstance(e, tuple) for e in runs.events)


# --- the rebuild and the writer, with their own pieces stood in ---------------------------------


def _sealed_review():
    return SimpleNamespace(
        artifacts=(SimpleNamespace(sha256=SHA("f"), size_bytes=100),),
        metrics=PROVISIONAL_METRICS,
    )


def _preflight(monkeypatch, *, artifact_sha=SHA("f"), size=100, candidates=CANDIDATES):
    verified = SimpleNamespace(data=b"set-bytes")
    prepared = SimpleNamespace(pinned_corpus=SimpleNamespace(verified_set=verified))
    monkeypatch.setattr(terminal, "prepare_v3_cite_preflight",
                        lambda *a, **k: SimpleNamespace(prepared=prepared, review="review"))
    monkeypatch.setattr(terminal, "build_v3_beta_review_artifact",
                        lambda preflight: SimpleNamespace(sha256=artifact_sha, size_bytes=size))
    monkeypatch.setattr(terminal, "provisional_publication_candidates", lambda review: candidates)


def _rebuild(**overrides):
    kwargs = dict(review=_sealed_review(), authority=AUTHORITY, registry=object(),
                  blob_store=object(), max_text_bytes=1, jobs=object(), runs=object(), documents=None)
    kwargs.update(overrides)
    return terminal._rebuild_candidates(object(), **kwargs)


def test_the_rebuild_returns_the_candidates_and_the_verified_set_bytes(monkeypatch):
    _preflight(monkeypatch)
    assert _rebuild() == (CANDIDATES, b"set-bytes")


@pytest.mark.parametrize("override,reason", (
    ({"blob_store": None}, "publication_inputs_missing"),
))
def test_the_rebuild_needs_the_blob_store(monkeypatch, override, reason):
    _preflight(monkeypatch)
    with pytest.raises(DomainError) as caught:
        _rebuild(**override)
    assert caught.value.detail_fields["reason"] == reason


@pytest.mark.parametrize("kwargs", ({"artifact_sha": SHA("0")}, {"size": 101}))
def test_a_rebuild_that_is_not_byte_equal_to_the_sealed_review_is_refused(monkeypatch, kwargs):
    _preflight(monkeypatch, **kwargs)
    with pytest.raises(DomainError) as caught:
        _rebuild()
    assert caught.value.detail_fields["reason"] == "rebuilt_review_differs_from_sealed"


def test_a_candidate_count_other_than_the_sealed_count_is_refused(monkeypatch):
    _preflight(monkeypatch, candidates=CANDIDATES[:1])
    with pytest.raises(DomainError) as caught:
        _rebuild()
    assert caught.value.detail_fields["reason"] == "provisional_count_differs_from_sealed"


def test_a_pure_gate_refusal_while_rebuilding_is_a_typed_refusal(monkeypatch):
    _preflight(monkeypatch)

    def refuse(review):
        raise ValueError("provisional_ordinal_not_accepted")

    monkeypatch.setattr(terminal, "provisional_publication_candidates", refuse)
    with pytest.raises(DomainError) as caught:
        _rebuild()
    assert caught.value.detail_fields["reason"].startswith("publication_rebuild_refused:")


def test_the_writer_is_called_per_candidate_with_this_runs_authority_and_the_v3_stage(monkeypatch):
    calls = []

    def writer(session, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(finding_uid=f"fnd_{len(calls)}")

    monkeypatch.setattr(terminal, "publish_grounded_v3_finding", writer)
    out = terminal._publish_candidates(
        object(), authority=AUTHORITY, model_call_id="call_test", set_bytes=b"s", candidates=CANDIDATES,
    )
    assert len(out) == 2
    assert [c["candidate"] for c in calls] == list(CANDIDATES)
    for call in calls:
        assert call["cite_stage_id"] == "ar_v3_citation_review" and call["model_call_id"] == "call_test"
        assert (call["run_id"], call["job_id"], call["attempt_id"], call["execution_token"]) == (
            "run_test", "job_test", "att_test", "secret")


def test_a_refusal_of_the_writer_is_a_typed_refusal(monkeypatch):
    def writer(session, **kwargs):
        raise terminal.CitationPublicationRefused("publication_authority_invalid")

    monkeypatch.setattr(terminal, "publish_grounded_v3_finding", writer)
    with pytest.raises(DomainError) as caught:
        terminal._publish_candidates(
            object(), authority=AUTHORITY, model_call_id="c", set_bytes=b"s", candidates=CANDIDATES,
        )
    assert caught.value.detail_fields["reason"] == "publication_refused:publication_authority_invalid"
