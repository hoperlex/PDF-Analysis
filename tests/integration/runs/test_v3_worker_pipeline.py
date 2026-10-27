"""The v3 worker consumes a completed call without sending it again."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.jobs.public import AttemptAuthority
from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID, ProviderConfig,
    ProviderMode, StageStatus,
)
from auditmanager.findings.public import TerminalSelection
from auditmanager.runs import executor, v3_worker
from auditmanager.runs.repository import RunRow
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.runs.v3_review_terminal import V3ReviewTerminal
from auditmanager.shared.errors import DomainError, ErrorCode


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")


class Jobs:
    def __init__(self, *, completed, cost_micros=4200, cost_basis="measured"):
        self.completed = completed
        self.reads = 0
        self.cost_micros = cost_micros
        self.cost_basis = cost_basis

    def completed_v3_call(self, session, authority, *, lock_authority):
        assert authority is AUTHORITY and lock_authority is False
        self.reads += 1
        if not self.completed:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                stage_id="text_analysis", reason="v3_call_missing_or_duplicate",
            )
        return SimpleNamespace(
            model_call_id="saved_call", cost_micros=self.cost_micros,
            cost_basis=self.cost_basis,
        )


class Runs:
    def __init__(self, *, citation=False, prior_cost=None):
        self.citation = citation
        self.prior_cost = prior_cost

    def cost(self, session, run_id):
        assert run_id == AUTHORITY.run_id
        return self.prior_cost

    def stage_results(self, session, run_id):
        assert run_id == AUTHORITY.run_id
        return ((SimpleNamespace(stage_id="ar_v3_citation_review"),)
                if self.citation else ())


blob_store = object()


def _arrange(monkeypatch, *, completed=False, citation=False,
             prior_cost=None, cost_micros=4200, cost_basis="measured"):
    order = []
    jobs = Jobs(completed=completed, cost_micros=cost_micros,
                cost_basis=cost_basis)
    runs = Runs(citation=citation, prior_cost=prior_cost)

    def dispatch(*args, **kwargs):
        assert kwargs["settings"] == v3_worker.V3_BETA_SETTINGS
        assert kwargs["max_text_bytes"] == v3_worker.MAX_V3_SAVED_TEXT_BYTES
        order.append("dispatch")
        jobs.completed = True

    def cite(*args, **kwargs):
        assert "settings" not in kwargs
        order.append("cite")

    def finish(*args, **kwargs):
        # `R-146as`: the terminal publishes from the saved evidence, so it gets the Blob store,
        # the document repository and the saved-text bound the CITE stage used.
        assert kwargs["blob_store"] is blob_store
        assert kwargs["max_text_bytes"] == v3_worker.MAX_V3_SAVED_TEXT_BYTES
        assert "documents" in kwargs
        order.append("terminal")
        return SimpleNamespace(selection=SimpleNamespace(state="published"))

    monkeypatch.setattr(v3_worker, "dispatch_v3_provider_call", dispatch)
    monkeypatch.setattr(v3_worker, "run_v3_cite_stage", cite)
    monkeypatch.setattr(v3_worker, "finish_v3_review_run", finish)
    return jobs, runs, order


def _run(jobs, runs, *, provider_for_dispatch=lambda: object(),
         cost_ceiling_usd=1.0):
    return v3_worker.run_v3_worker_chain(
        object(), authority=AUTHORITY, registry=object(), blob_store=blob_store,
        provider_for_dispatch=provider_for_dispatch,
        cost_ceiling_usd=cost_ceiling_usd, jobs=jobs, runs=runs,
    )


def test_first_attempt_dispatches_then_cites_then_terminates(monkeypatch):
    jobs, runs, order = _arrange(monkeypatch)
    result = _run(jobs, runs)
    assert result.dispatched is True
    assert result.terminal.selection.state == "published"
    assert jobs.reads == 2
    assert order == ["dispatch", "cite", "terminal"]


def test_completed_prior_attempt_replays_without_dispatch(monkeypatch):
    jobs, runs, order = _arrange(monkeypatch, completed=True)
    result = _run(
        jobs, runs,
        provider_for_dispatch=lambda: pytest.fail("replay resolved provider secret"),
    )
    assert result.dispatched is False
    assert jobs.reads == 1
    assert order == ["cite", "terminal"]


def test_existing_citation_only_runs_terminal(monkeypatch):
    jobs, runs, order = _arrange(monkeypatch, completed=True, citation=True)
    result = _run(
        jobs, runs,
        provider_for_dispatch=lambda: pytest.fail("saved citation resolved provider"),
    )
    assert result.dispatched is False
    assert jobs.reads == 1
    assert order == ["terminal"]


def test_invalid_prior_effect_refuses_without_dispatch(monkeypatch):
    jobs, runs, order = _arrange(monkeypatch)

    def invalid(*args, **kwargs):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            stage_id="text_analysis", reason="v3_call_pair_invalid",
        )

    jobs.completed_v3_call = invalid
    with pytest.raises(DomainError) as caught:
        _run(jobs, runs)
    assert caught.value.detail_fields["reason"] == "v3_call_pair_invalid"
    assert order == []


def test_exhausted_opening_balance_refuses_before_dispatch(monkeypatch):
    jobs, runs, order = _arrange(
        monkeypatch, prior_cost=SimpleNamespace(cost_micros=1_000_000),
    )
    with pytest.raises(DomainError) as caught:
        _run(jobs, runs, cost_ceiling_usd=1.0)
    assert caught.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert order == []


@pytest.mark.parametrize("completed,citation", (
    (False, False), (True, False), (True, True),
))
def test_over_ceiling_completed_call_never_reaches_review_or_terminal(
    monkeypatch, completed, citation,
):
    jobs, runs, order = _arrange(
        monkeypatch, completed=completed, citation=citation,
        cost_micros=1_000_001,
    )
    with pytest.raises(DomainError) as caught:
        _run(jobs, runs)
    assert caught.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert order == (["dispatch"] if not completed else [])


def test_unknown_metered_cost_cannot_publish(monkeypatch):
    jobs, runs, order = _arrange(
        monkeypatch, completed=True, cost_micros=None, cost_basis="estimated",
    )
    with pytest.raises(DomainError) as caught:
        _run(jobs, runs)
    assert caught.value.detail_fields["reason"] == "v3_metered_cost_unknown"
    assert order == []


def test_explicit_unmetered_call_may_publish(monkeypatch):
    jobs, runs, order = _arrange(
        monkeypatch, completed=True, cost_micros=0, cost_basis="unmetered",
    )
    assert _run(jobs, runs).terminal.selection.state == "published"
    assert order == ["cite", "terminal"]


def test_executor_routes_exact_v3_pair_to_review_only_chain(monkeypatch):
    run_id = "run_01M25P3TH08VVTTGJRXYBZZ7RP"
    events = []
    run = RunRow(
        run_id=run_id, project_uid="prj_01M25P3TH08VVTTGJRXYBZZ7RP",
        version_uid="ver_01M25P3TH08VVTTGJRXYBZZ7RP", state="queued",
        analysis_profile_id=str(AR_V3_BETA_PROFILE_ID),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID),
        norms_snapshot_id="ns_01M59N8QNBVN91ACA2HCE6VE74",
        provider_mode="recorded", frozen_input_digest="0" * 64,
        command_id=None, terminal_reason=None, terminal_detail=None,
        interrupted_reason=None, degradation_set=(),
        created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
        terminal_at=None, norm_retrieval_set_id="nrs_01M25P3TH08VVTTGJRXYBZZ7RP",
    )

    class RunRows:
        def __init__(self):
            self.row = run

        def cost(self, *_args):
            return None

        def get(self, *_args):
            return self.row

        def advance(self, _session, *, from_state, to_state, **_kwargs):
            assert self.row.state == from_state
            self.row = replace(self.row, state=to_state)
            events.append("run:" + to_state)

        def stage_started(self, _session, *, stage_id, **_kwargs):
            events.append("start:" + stage_id)

    class JobRows:
        def start_execution(self, _session, *, run_id):
            events.append("attempt")
            return AttemptAuthority(run_id, "job_test", "att_test", "lease_test", "secret")

    class Documents:
        def get_version(self, *_args):
            return SimpleNamespace(
                entry=lambda _role: SimpleNamespace(
                    blob_id="blob_01M25P3TH08VVTTGJRXYBZZ7RP",
                    sha256="0" * 64, size_bytes=12, media_type="application/pdf",
                ), manifest=(),
            )

    class Session:
        def commit(self):
            events.append("commit")

    monkeypatch.setattr(TrustedPackRegistry, "select_beta", lambda self: object())
    monkeypatch.setattr(executor, "start_attempt_lease_heartbeat", lambda *_a: None)
    monkeypatch.setattr(executor, "stop_attempt_lease_heartbeat", lambda: None)
    monkeypatch.setattr(executor, "_publication_store", lambda *_a, **_k: object())
    monkeypatch.setattr(executor, "_persist_and_bind", lambda *_a, **_k: events.append("bound"))
    monkeypatch.setattr(executor, "run_stage", lambda stage_id, **_k: (
        events.append("stage:" + stage_id) or SimpleNamespace(
            stage_id=stage_id, status=StageStatus.SUCCEEDED, artifacts=(),
        )
    ))
    monkeypatch.setattr(executor, "_run_text_analysis_stage", lambda **_k: (
        pytest.fail("AR v3 reached legacy text analysis")
    ))

    def chain(*args, **kwargs):
        events.append("v3_chain")
        assert kwargs["provider_for_dispatch"] is not None
        return v3_worker.V3WorkerOutcome(
            V3ReviewTerminal(TerminalSelection("published"), {
                "ar_v3_citation_review": "succeeded",
            }), True,
        )

    monkeypatch.setattr(v3_worker, "run_v3_worker_chain", chain)
    result = executor.execute_run(
        Session(), run_id, blob_store=object(),
        adapter=SimpleNamespace(provider_mode=ProviderMode.RECORDED),
        provider_config=ProviderConfig(ProviderMode.RECORDED, "fixture/v3", 1.0, None, False),
        runs=RunRows(), jobs=JobRows(), documents=Documents(), blob_metadata=object(),
        text_profiles=lambda *_: pytest.fail("AR v3 resolved legacy text profile"),
        ar_v3_pack_registry=TrustedPackRegistry.empty(),
    )
    assert result.terminal_state == "published"
    assert result.published_finding_count == 0
    assert result.attempts == 1
    assert events.index("attempt") < events.index("v3_chain")
    assert events.index("stage:document_context_build") < events.index("v3_chain")
