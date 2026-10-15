"""Recorded AR v2 preflight is inert until a separately pinned profile exists."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import (
    AR_TEXT_PROFILE,
    AR_V2_RECORDED_BUNDLE_ID,
    AR_V2_RECORDED_PROFILE_ID,
    ProviderConfig,
    ProviderMode,
)
from auditmanager.runs.executor import plan_recorded_v2_execution
from auditmanager.runs.repository import RunRow
from auditmanager.shared.errors import DomainError, ErrorCode


V2_PROFILE = str(AR_V2_RECORDED_PROFILE_ID)
V2_BUNDLE = str(AR_V2_RECORDED_BUNDLE_ID)


class NoCallAdapter:
    def __init__(self, mode: ProviderMode) -> None:
        self.provider_mode = mode
        self.calls = 0

    def complete(self, _request: object) -> None:
        self.calls += 1
        raise AssertionError("preflight must not call the provider")


def _run(**changes: object) -> RunRow:
    row = RunRow(
        run_id="run_01M25P3TH08VVTTGJRXYBZZ7RP",
        project_uid="prj_01M25P3TH08VVTTGJRXYBZZ7RP",
        version_uid="ver_01M25P3TH08VVTTGJRXYBZZ7RP",
        state="queued",
        analysis_profile_id=V2_PROFILE,
        prompt_bundle_id=V2_BUNDLE,
        norms_snapshot_id=None,
        provider_mode="recorded",
        frozen_input_digest="0" * 64,
        command_id=None,
        terminal_reason=None,
        terminal_detail=None,
        interrupted_reason=None,
        degradation_set=(),
        created_at=datetime(2026, 10, 15, tzinfo=timezone.utc),
        terminal_at=None,
    )
    return replace(row, **changes)


def _config(mode: ProviderMode = ProviderMode.RECORDED) -> ProviderConfig:
    return ProviderConfig(
        mode=mode,
        model_id="pinned-model-candidate",
        run_cost_ceiling_usd=1.0,
        api_key=None,
        ceiling_is_explicit=False,
    )


def _plan(run: RunRow, adapter: NoCallAdapter, config: ProviderConfig,
          *, profile: str = V2_PROFILE, bundle: str = V2_BUNDLE):
    return plan_recorded_v2_execution(
        run=run,
        adapter=adapter,
        provider_config=config,
        registered_profile_id=profile,
        registered_bundle_id=bundle,
    )


def test_matching_recorded_intent_retains_persisted_run_identity_without_effects() -> None:
    adapter = NoCallAdapter(ProviderMode.RECORDED)
    run = _run()

    intent = _plan(run, adapter, _config())

    assert (intent.run_id, intent.analysis_profile_id, intent.prompt_bundle_id) == (
        run.run_id, V2_PROFILE, V2_BUNDLE,
    )
    assert adapter.calls == 0


@pytest.mark.parametrize(
    ("run_changes", "adapter_mode", "config_mode", "profile", "bundle"),
    [
        ({"analysis_profile_id": "ap_01M25P3TH08VVTTGJRXYBZZ7RR"}, ProviderMode.RECORDED, ProviderMode.RECORDED, V2_PROFILE, V2_BUNDLE),
        ({"prompt_bundle_id": "pb_01M25P3TH0PDQYVKTRQFEM0CYS"}, ProviderMode.RECORDED, ProviderMode.RECORDED, V2_PROFILE, V2_BUNDLE),
        ({"provider_mode": "live"}, ProviderMode.RECORDED, ProviderMode.RECORDED, V2_PROFILE, V2_BUNDLE),
        ({}, ProviderMode.LIVE, ProviderMode.RECORDED, V2_PROFILE, V2_BUNDLE),
        ({}, ProviderMode.RECORDED, ProviderMode.LIVE, V2_PROFILE, V2_BUNDLE),
        ({"state": "published"}, ProviderMode.RECORDED, ProviderMode.RECORDED, V2_PROFILE, V2_BUNDLE),
        ({"analysis_profile_id": str(AR_TEXT_PROFILE.analysis_profile_id)}, ProviderMode.RECORDED, ProviderMode.RECORDED, str(AR_TEXT_PROFILE.analysis_profile_id), V2_BUNDLE),
    ],
)
def test_mismatch_refuses_before_provider_or_persistence(
    run_changes: dict[str, object], adapter_mode: ProviderMode,
    config_mode: ProviderMode, profile: str, bundle: str,
) -> None:
    adapter = NoCallAdapter(adapter_mode)
    with pytest.raises(DomainError) as failure:
        _plan(_run(**run_changes), adapter, _config(config_mode),
              profile=profile, bundle=bundle)
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert adapter.calls == 0


def test_malformed_registration_refuses_even_for_matching_row() -> None:
    adapter = NoCallAdapter(ProviderMode.RECORDED)
    with pytest.raises(DomainError):
        _plan(_run(analysis_profile_id="unregistered"), adapter, _config(),
              profile="unregistered")
    assert adapter.calls == 0


def test_well_formed_but_unregistered_identity_is_refused() -> None:
    adapter = NoCallAdapter(ProviderMode.RECORDED)
    unknown = "ap_01M25P3TH08VVTTGJRXYBZZ7RQ"
    with pytest.raises(DomainError) as failure:
        _plan(_run(analysis_profile_id=unknown), adapter, _config(), profile=unknown)
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert adapter.calls == 0


def test_reviewed_content_drift_is_refused_before_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.analysis.profiles.ar_v2 import registered

    adapter = NoCallAdapter(ProviderMode.RECORDED)
    monkeypatch.setattr(registered, "material_sha256", lambda: "0" * 64)
    with pytest.raises(DomainError) as failure:
        _plan(_run(), adapter, _config())
    assert failure.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert adapter.calls == 0
