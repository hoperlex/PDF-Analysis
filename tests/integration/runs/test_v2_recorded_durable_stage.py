"""Recorded v2 stage keeps the durable call, Blob and result in evidence order."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    ProviderConfig, ProviderMode, RecordedAdapter,
)
from auditmanager.analysis.engine.result import StageStatus
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.jobs.repository import AttemptAuthority, JobRepository
from auditmanager.runs import recorded_v2_stage as stage
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ModelCallId
from auditmanager.storage.public import derive_blob_id
from tests.integration.analysis.test_ar_v2_recorded_artifact import (
    CALL, MODEL, RUN, VERSION, _prepared, _replay,
)


class _Session:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def commit(self) -> None:
        self.events.append("commit")


class _Runs:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.row = SimpleNamespace(
            state="running", version_uid=VERSION,
            analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
            prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        )

    def get(self, _session: _Session, _run_id: str):
        return self.row

    def stage_results(self, _session: _Session, _run_id: str):
        return ()

    def stage_started(self, _session: _Session, *, run_id: str, stage_id: str) -> None:
        assert (run_id, stage_id) == (RUN, "text_analysis")
        self.events.append("stage_started")


class _Jobs:
    def __init__(self, events: list[str], *, occupied: bool = False) -> None:
        self.events = events
        self.occupied = occupied
        self.call: dict | None = None

    def require_current(self, _session: _Session, _authority: AttemptAuthority) -> None:
        self.events.append("authority_checked")

    def require_recorded_stage_call_available(
        self, _session: _Session, _authority: AttemptAuthority
    ) -> None:
        self.events.append("call_available_checked")
        if self.occupied:
            raise DomainError(ErrorCode.CONFLICT, message="existing call")

    def prepare_provider_call(self, _session: _Session, _authority: AttemptAuthority, **kwargs):
        assert kwargs["provider_mode"] == "recorded"
        self.events.append("call_prepared")
        return ModelCallId.parse(CALL)

    def record_provider_response(self, _session: _Session, _authority: AttemptAuthority, **kwargs):
        assert kwargs["model_call_id"] == ModelCallId.parse(CALL)
        self.events.append("response_recorded")

    def complete_provider_call(self, _session: _Session, _authority: AttemptAuthority,
                               *, call: dict) -> None:
        self.call = call
        self.events.append("call_completed")


class _PublishedStore:
    def __init__(self, events: list[str], *, corrupt_read: bool = False) -> None:
        self.events = events
        self.corrupt_read = corrupt_read
        self.payload = b""

    def put_blob(self, payload: bytes, *, declared_sha256: str, declared_size: int,
                 role: str, media_type: str):
        assert len(payload) == declared_size and role == "analysis_text_observations"
        self.events.append("blob_published")
        self.payload = payload
        return SimpleNamespace(
            blob_id=derive_blob_id(sha256=declared_sha256, size=declared_size),
            sha256=declared_sha256, size=declared_size, media_type=media_type,
        )

    def read(self, _blob_id: str, *, verify: bool) -> bytes:
        assert verify
        self.events.append("blob_readback")
        return b"bad" if self.corrupt_read else self.payload


def _config(mode: ProviderMode = ProviderMode.RECORDED) -> ProviderConfig:
    return ProviderConfig(mode, "unused-v1-pin", 1.0, None, False)


def _exercise(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
              *, corrupt_read: bool = False, occupied: bool = False,
              truncated: bool = False,
              config_mode: ProviderMode = ProviderMode.RECORDED):
    prepared = _prepared()
    _replay(tmp_path, prepared, truncated=truncated)  # writes an exact-key recording
    events: list[str] = []
    session = _Session(events)
    runs = _Runs(events)
    jobs = _Jobs(events, occupied=occupied)
    published = _PublishedStore(events, corrupt_read=corrupt_read)
    monkeypatch.setattr(stage, "load_recorded_v2_input", lambda *_args, **_kw: (
        events.append("source_read") or prepared
    ))
    monkeypatch.setattr(stage, "_publication_store", lambda *_args, **_kw: published)
    monkeypatch.setattr(stage, "_persist_and_bind", lambda *_args, **_kw: (
        events.append("stage_bound")
    ))
    start = datetime(2026, 10, 16, 5, 0, tzinfo=timezone.utc)
    times = iter((start, start + timedelta(seconds=1)))
    authority = AttemptAuthority(RUN, "job_1", "att_1", "lease_1", "token")
    def execute():
        return stage.run_recorded_v2_stage(
            session, authority=authority, blob_store=object(),
            adapter=RecordedAdapter(tmp_path), provider_config=_config(config_mode),
            fixture_model_id=MODEL,
            settings=RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
            runs=runs, jobs=jobs, blobs=object(), clock=lambda: next(times),
        )
    return execute, events, jobs


def test_exact_recorded_call_precedes_verified_blob_and_stage_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, jobs = _exercise(monkeypatch, tmp_path)
    result = execute()
    assert result.status is StageStatus.SUCCEEDED
    assert result.artifacts[0].role == "analysis.text_observations"
    assert jobs.call is not None
    assert jobs.call["cost_usd"] is None and jobs.call["cost_basis"] == "estimated"
    assert jobs.call["request_sha256"] != jobs.call["response_sha256"]
    assert "cost_usd" not in result.metrics
    assert events.index("source_read") < events.index("authority_checked")
    assert events.index("call_prepared") < events.index("response_recorded")
    assert events.index("response_recorded") < events.index("call_completed")
    assert events.index("call_completed") < events.index("blob_published")
    assert events.index("blob_published") < events.index("blob_readback")
    assert events.index("blob_readback") < events.index("stage_bound")
    assert events[-1] == "commit"


def test_wrong_blob_readback_keeps_call_but_refuses_stage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, jobs = _exercise(monkeypatch, tmp_path, corrupt_read=True)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert jobs.call is not None and "stage_bound" not in events


def test_existing_call_refuses_before_recording_or_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, _ = _exercise(monkeypatch, tmp_path, occupied=True)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.CONFLICT
    assert "call_prepared" not in events and "blob_published" not in events


def test_truncated_call_is_retained_without_success_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, jobs = _exercise(monkeypatch, tmp_path, truncated=True)
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_FAILED
    assert jobs.call is not None and jobs.call["status"] == "truncated"
    assert "blob_published" not in events and "stage_bound" not in events


def test_live_configuration_refuses_before_source_or_journal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    execute, events, _ = _exercise(
        monkeypatch, tmp_path, config_mode=ProviderMode.LIVE,
    )
    with pytest.raises(DomainError) as failure:
        execute()
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert events == []


@pytest.mark.parametrize("occupied", [False, True])
def test_job_repository_checks_existing_effect_under_current_attempt(
    monkeypatch: pytest.MonkeyPatch, occupied: bool,
) -> None:
    from auditmanager.jobs import repository as jobs_module

    seen = []
    class DbSession:
        def execute(self, statement, parameters):
            assert statement is jobs_module._EXISTING_RECORDED_STAGE_CALL
            seen.append(parameters)
            return SimpleNamespace(scalar_one=lambda: occupied)

    monkeypatch.setattr(JobRepository, "require_current", lambda *_args: seen.append("current"))
    authority = AttemptAuthority(RUN, "job_1", "att_1", "lease_1", "token")
    if occupied:
        with pytest.raises(DomainError) as failure:
            JobRepository().require_recorded_stage_call_available(DbSession(), authority)
        assert failure.value.code is ErrorCode.CONFLICT
    else:
        JobRepository().require_recorded_stage_call_available(DbSession(), authority)
    assert seen == ["current", {"run_id": RUN}]


@pytest.mark.parametrize(("provider_mode", "cost_usd", "expected_micros"), [
    ("recorded", None, None), ("live", 0.0344, 34400),
])
def test_job_writer_preserves_unknown_and_existing_numeric_costs(
    monkeypatch: pytest.MonkeyPatch, provider_mode: str, cost_usd: float | None,
    expected_micros: int | None,
) -> None:
    from auditmanager.jobs import repository as jobs_module

    inserted: dict = {}
    # The prepared effect carries the connection revision and the identity basis, both set or
    # both NULL (migration 0030): a recorded call has neither, a live one the pair of its route.
    effect = (
        {"connection_revision_id": None, "identity_basis": None} if provider_mode == "recorded"
        else {"connection_revision_id": "exr_01M2545JSD15ETSNNV904X991J", "identity_basis": "reported"}
    )

    class DbSession:
        def execute(self, statement, parameters):
            if statement is jobs_module._PROVIDER_FOR_COMPLETION:
                return SimpleNamespace(
                    mappings=lambda: SimpleNamespace(first=lambda: effect))
            if statement is jobs_module._INSERT_MODEL_CALL:
                inserted.update(parameters)
                return SimpleNamespace(rowcount=1)
            if statement is jobs_module._COMPLETE_PROVIDER:
                return SimpleNamespace(rowcount=1)
            raise AssertionError(str(statement))

    monkeypatch.setattr(JobRepository, "require_current", lambda *_args: None)
    monkeypatch.setattr(jobs_module, "append_execution_event", lambda *_args, **_kw: None)
    authority = AttemptAuthority(RUN, "job_1", "att_1", "lease_1", "token")
    JobRepository().complete_provider_call(DbSession(), authority, call={
        "model_call_id": CALL, "provider": "anthropic", "model_id": MODEL,
        "provider_mode": provider_mode, "parameters": {},
        "request_sha256": "a" * 64, "response_sha256": "b" * 64,
        "input_tokens": 100, "output_tokens": 40, "latency_ms": 5,
        "cost_usd": cost_usd, "cost_basis": "estimated", "status": "succeeded",
    })
    assert inserted["cost_micros"] == expected_micros
    assert inserted["cost_basis"] == "estimated"
    assert inserted["provider_mode"] == provider_mode
    assert (inserted["connection_revision_id"], inserted["identity_basis"]) == (
        effect["connection_revision_id"], effect["identity_basis"])
