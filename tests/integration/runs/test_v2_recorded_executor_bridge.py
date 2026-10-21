"""The explicit recorded bridge routes a persisted v2 Run without serving wiring."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import (
    AR_V2_RECORDED_BUNDLE_ID, AR_V2_RECORDED_PROFILE_ID,
    RecordedAdapter, RecordedGenerationSettings, StageStatus,
    ProviderConfig, ProviderMode,
)
from auditmanager.findings.public import TerminalSelection
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import executor
from auditmanager.runs.repository import RunRow
from auditmanager.shared.errors import DomainError, ErrorCode


RUN_ID = "run_01M25P3TH08VVTTGJRXYBZZ7RP"
VERSION_ID = "ver_01M25P3TH08VVTTGJRXYBZZ7RP"
MODEL_ID = "fixture/ar-v2-recorded"
SETTINGS = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})


def _run(**changes: object) -> RunRow:
    return replace(RunRow(
        run_id=RUN_ID,
        project_uid="prj_01M25P3TH08VVTTGJRXYBZZ7RP",
        version_uid=VERSION_ID,
        state="queued",
        analysis_profile_id=str(AR_V2_RECORDED_PROFILE_ID),
        prompt_bundle_id=str(AR_V2_RECORDED_BUNDLE_ID),
        norms_snapshot_id=None,
        provider_mode="recorded",
        frozen_input_digest="0" * 64,
        command_id=None,
        terminal_reason=None,
        terminal_detail=None,
        interrupted_reason=None,
        degradation_set=(),
        created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
        terminal_at=None,
    ), **changes)


def _config(**changes: object) -> ProviderConfig:
    return replace(ProviderConfig(
        mode=ProviderMode.RECORDED,
        model_id="v1-locked-identity-not-used-by-v2",
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=False,
    ), **changes)


class _Session:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def commit(self) -> None:
        self.events.append("commit")


class _Runs:
    def __init__(self, row: RunRow, events: list[str]) -> None:
        self.row = row
        self.events = events

    def cost(self, *_args):
        return None

    def get(self, *_args):
        return self.row

    def advance(self, _session, *, run_id: str, from_state: str, to_state: str) -> None:
        assert run_id == RUN_ID and self.row.state == from_state
        self.row = replace(self.row, state=to_state)
        self.events.append(f"run:{to_state}")

    def stage_started(self, _session, *, run_id: str, stage_id: str) -> None:
        assert run_id == RUN_ID
        self.events.append(f"start:{stage_id}")

    def stage_statuses(self, *_args):
        return {
            "source_preparation": "succeeded",
            "page_geometry_extraction": "succeeded",
            "document_context_build": "succeeded",
            "text_analysis": "succeeded",
            "finding_merge": "succeeded",
        }


class _Jobs:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def start_execution(self, _session, *, run_id: str):
        assert run_id == RUN_ID
        self.events.append("attempt:started")
        return AttemptAuthority(RUN_ID, "job_1", "att_1", "lease_1", "token")


class _Documents:
    def get_version(self, *_args):
        return SimpleNamespace(
            entry=lambda _role: SimpleNamespace(
                blob_id="blob_01M25P3TH08VVTTGJRXYBZZ7RP",
                sha256="0" * 64, size_bytes=12, media_type="application/pdf",
            ),
            manifest=(),
        )


def test_v2_bridge_commits_authority_before_stages_and_calls_gate_last(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from auditmanager.runs import recorded_v2_stage, recorded_v2_merge, recorded_v2_publication

    events: list[str] = []
    runs = _Runs(_run(), events)
    jobs = _Jobs(events)
    monkeypatch.setattr(executor, "start_attempt_lease_heartbeat", lambda *_args: events.append("heartbeat"))
    monkeypatch.setattr(executor, "stop_attempt_lease_heartbeat", lambda: events.append("heartbeat:stop"))
    monkeypatch.setattr(executor, "_publication_store", lambda *_args, **_kw: object())
    monkeypatch.setattr(executor, "_persist_and_bind", lambda *_args, **_kw: events.append("stage:bound"))
    monkeypatch.setattr(executor, "run_stage", lambda stage_id, **_kw: (
        events.append(f"stage:{stage_id}") or SimpleNamespace(
            stage_id=stage_id, status=StageStatus.SUCCEEDED, artifacts=(),
        )
    ))

    def text(_session, **kwargs):
        assert kwargs["authority"].run_id == RUN_ID
        assert kwargs["fixture_model_id"] == MODEL_ID
        assert kwargs["settings"] is SETTINGS
        events.append("recorded:text")
        return SimpleNamespace(status=StageStatus.SUCCEEDED)

    monkeypatch.setattr(recorded_v2_stage, "run_recorded_v2_stage", text)
    monkeypatch.setattr(recorded_v2_merge, "run_recorded_v2_merge_stage", lambda *_a, **_k: (
        events.append("recorded:merge")
    ))
    monkeypatch.setattr(recorded_v2_publication, "publish_recorded_v2_run", lambda *_a, **_k: (
        events.append("recorded:gate") or SimpleNamespace(
            selection=TerminalSelection("published", (), None),
            finding_count=2, rejected_count=1,
        )
    ))
    monkeypatch.setattr(executor, "_run_text_analysis_stage", lambda **_kw: (
        pytest.fail("v1 model stage reached by v2 run")
    ))

    result = executor.execute_run(
        _Session(events), RUN_ID, blob_store=object(),
        adapter=RecordedAdapter(tmp_path), provider_config=_config(),
        runs=runs, jobs=jobs, documents=_Documents(), blob_metadata=object(),
        recorded_fixture_model_id=MODEL_ID, recorded_generation_settings=SETTINGS,
    )

    assert result.terminal_state == "published"
    assert result.published_finding_count == 2 and result.diagnostic_count == 1
    assert result.attempts == 1 and result.model_attempts.attempt_budget == 1
    assert events.index("attempt:started") < events.index("run:running")
    assert events.index("run:running") < events.index("recorded:text")
    assert events.index("recorded:text") < events.index("recorded:merge")
    assert events.index("recorded:merge") < events.index("recorded:gate")
    assert events[-1] == "heartbeat:stop"


@pytest.mark.parametrize("run_change, config_change, adapter_type, model, settings", [
    ({}, {}, "recorded", None, SETTINGS),
    ({}, {}, "recorded", "anthropic/claude-opus-5", SETTINGS),
    ({}, {}, "recorded", MODEL_ID, None),
    ({}, {"mode": ProviderMode.LIVE}, "recorded", MODEL_ID, SETTINGS),
    ({}, {"api_key": "credential"}, "recorded", MODEL_ID, SETTINGS),
    ({}, {}, "claiming", MODEL_ID, SETTINGS),
    ({"provider_mode": "live"}, {}, "recorded", MODEL_ID, SETTINGS),
    ({"prompt_bundle_id": "pb_01M25P3TH0PDQYVKTRQFEM0CYS"}, {}, "recorded", MODEL_ID, SETTINGS),
])
def test_v2_refuses_invalid_mode_or_fixture_before_authority_and_blob_access(
    tmp_path: Path, run_change: dict, config_change: dict,
    adapter_type: str, model: str | None, settings: RecordedGenerationSettings | None,
) -> None:
    events: list[str] = []
    adapter = (RecordedAdapter(tmp_path) if adapter_type == "recorded"
               else SimpleNamespace(provider_mode=ProviderMode.RECORDED))
    with pytest.raises(DomainError) as failure:
        executor.execute_run(
            _Session(events), RUN_ID, blob_store=object(),
            adapter=adapter, provider_config=_config(**config_change),
            runs=_Runs(_run(**run_change), events), jobs=_Jobs(events),
            documents=_Documents(), blob_metadata=object(),
            recorded_fixture_model_id=model, recorded_generation_settings=settings,
        )
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert events == []


def test_v1_row_refuses_stray_v2_fixture_before_effects(tmp_path: Path) -> None:
    events: list[str] = []
    with pytest.raises(DomainError) as failure:
        executor.execute_run(
            _Session(events), RUN_ID, blob_store=object(),
            adapter=RecordedAdapter(tmp_path), provider_config=_config(),
            runs=_Runs(_run(
                analysis_profile_id="ap_01M25P3TH08VVTTGJRXYBZZ7RP",
                prompt_bundle_id="pb_01M25P3TH08VVTTGJRXYBZZ7RP",
            ), events), jobs=_Jobs(events), documents=_Documents(),
            blob_metadata=object(), recorded_fixture_model_id=MODEL_ID,
            recorded_generation_settings=SETTINGS,
        )
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert events == []


def test_v1_without_fixture_still_reaches_legacy_model_stage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(executor, "start_attempt_lease_heartbeat", lambda *_a: None)
    monkeypatch.setattr(executor, "stop_attempt_lease_heartbeat", lambda: None)
    monkeypatch.setattr(executor, "_publication_store", lambda *_a, **_k: object())
    monkeypatch.setattr(executor, "_persist_and_bind", lambda *_a, **_k: None)
    monkeypatch.setattr(executor, "run_stage", lambda stage_id, **_k: SimpleNamespace(
        stage_id=stage_id, status=StageStatus.SUCCEEDED, artifacts=(),
    ))

    def legacy_stage(**_kwargs):
        events.append("legacy:text_analysis")
        raise RuntimeError("legacy_stage_reached")

    monkeypatch.setattr(executor, "_run_text_analysis_stage", legacy_stage)
    row = _run(
        analysis_profile_id="ap_01M25P3TH08VVTTGJRXYBZZ7RP",
        prompt_bundle_id="pb_01M25P3TH08VVTTGJRXYBZZ7RP",
    )
    with pytest.raises(RuntimeError, match="legacy_stage_reached"):
        executor.execute_run(
            _Session(events), RUN_ID, blob_store=object(),
            adapter=RecordedAdapter(tmp_path), provider_config=_config(),
            runs=_Runs(row, events), jobs=_Jobs(events), documents=_Documents(),
            blob_metadata=object(),
        )
    assert events.count("legacy:text_analysis") == 1


def test_v2_deterministic_halt_reaches_failure_gate_without_recording(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from auditmanager.runs import recorded_v2_stage, recorded_v2_merge, recorded_v2_publication

    events: list[str] = []
    monkeypatch.setattr(executor, "start_attempt_lease_heartbeat", lambda *_a: None)
    monkeypatch.setattr(executor, "stop_attempt_lease_heartbeat", lambda: None)
    monkeypatch.setattr(executor, "_publication_store", lambda *_a, **_k: object())
    monkeypatch.setattr(executor, "_persist_and_bind", lambda *_a, **_k: None)
    monkeypatch.setattr(executor, "run_stage", lambda stage_id, **_k: (
        events.append(f"stage:{stage_id}") or SimpleNamespace(
            stage_id=stage_id, status=StageStatus.FAILED, artifacts=(),
        )
    ))
    monkeypatch.setattr(recorded_v2_stage, "run_recorded_v2_stage", lambda *_a, **_k: (
        pytest.fail("halted run replayed a fixture")
    ))
    monkeypatch.setattr(recorded_v2_merge, "run_recorded_v2_merge_stage", lambda *_a, **_k: (
        pytest.fail("halted run merged findings")
    ))
    monkeypatch.setattr(recorded_v2_publication, "publish_recorded_v2_run", lambda *_a, **_k: (
        events.append("recorded:failure_gate") or SimpleNamespace(
            selection=TerminalSelection("failed", ("text_analysis",), "analysis_failed"),
            finding_count=0, rejected_count=0,
        )
    ))

    result = executor.execute_run(
        _Session(events), RUN_ID, blob_store=object(),
        adapter=RecordedAdapter(tmp_path), provider_config=_config(),
        runs=_Runs(_run(), events), jobs=_Jobs(events),
        documents=_Documents(), blob_metadata=object(),
        recorded_fixture_model_id=MODEL_ID, recorded_generation_settings=SETTINGS,
    )
    assert result.terminal_state == "failed" and result.attempts == 0
    assert result.gate_ran is False
    assert events.count("recorded:failure_gate") == 1
    assert not any(event.startswith("stage:page_geometry") for event in events)
