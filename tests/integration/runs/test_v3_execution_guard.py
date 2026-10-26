"""The uninstalled v3 executor cannot send a grouped Run through AR v1."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import (
    AR_TEXT_PROFILE,
    AR_V3_BETA_BUNDLE_ID,
    AR_V3_BETA_PROFILE_ID,
    ProviderConfig,
    ProviderMode,
    resolve_beta_v3_profile,
)
from auditmanager.runs.executor import execute_run
from auditmanager.runs.repository import RunRow
from auditmanager.runs.v3_group import TrustedPackRegistry
from auditmanager.shared.errors import DomainError, ErrorCode


RUN_ID = "run_01M25P3TH08VVTTGJRXYBZZ7RP"


def _run(**changes: object) -> RunRow:
    return replace(RunRow(
        run_id=RUN_ID,
        project_uid="prj_01M25P3TH08VVTTGJRXYBZZ7RP",
        version_uid="ver_01M25P3TH08VVTTGJRXYBZZ7RP",
        state="queued",
        analysis_profile_id=str(AR_V3_BETA_PROFILE_ID),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID),
        norms_snapshot_id="ns_01M59N8QNBVN91ACA2HCE6VE74",
        provider_mode="recorded",
        frozen_input_digest="0" * 64,
        command_id=None,
        terminal_reason=None,
        terminal_detail=None,
        interrupted_reason=None,
        degradation_set=(),
        created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
        terminal_at=None,
        norm_retrieval_set_id="nrs_01M25P3TH08VVTTGJRXYBZZ7RP",
    ), **changes)


class _NoEffects:
    def __getattr__(self, name: str):
        def refuse(*_args: object, **_kwargs: object) -> None:
            raise AssertionError(f"effect reached: {name}")
        return refuse


class _Runs(_NoEffects):
    def __init__(self, row: RunRow) -> None:
        self.row = row

    def cost(self, *_args: object) -> None:
        return None

    def get(self, *_args: object) -> RunRow:
        return self.row


class _Adapter(_NoEffects):
    provider_mode = ProviderMode.RECORDED


CONFIG = ProviderConfig(
    mode=ProviderMode.RECORDED,
    model_id="fixture/ar-v3-guard",
    run_cost_ceiling_usd=1.0,
    api_key=None,
    ceiling_is_explicit=False,
)


def test_public_pair_is_the_exact_sealed_v3_profile() -> None:
    profile = resolve_beta_v3_profile(AR_V3_BETA_PROFILE_ID, AR_V3_BETA_BUNDLE_ID)
    assert str(profile.analysis_profile_id) == str(AR_V3_BETA_PROFILE_ID)
    assert str(profile.prompt_bundle_id) == str(AR_V3_BETA_BUNDLE_ID)


@pytest.mark.parametrize("pair", ["exact", "profile_only", "bundle_only"])
@pytest.mark.parametrize("resolver", [None, lambda *_: AR_TEXT_PROFILE], ids=["no_registry", "v1_registry"])
def test_v3_identity_refuses_before_every_effect(pair: str, resolver) -> None:
    row = _run()
    if pair == "profile_only":
        row = replace(row, prompt_bundle_id=str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id))
    elif pair == "bundle_only":
        row = replace(row, analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id))
    with pytest.raises(DomainError) as raised:
        execute_run(
            _NoEffects(), RUN_ID,
            blob_store=_NoEffects(), adapter=_Adapter(), provider_config=CONFIG,
            runs=_Runs(row), documents=_NoEffects(), jobs=_NoEffects(),
            blob_metadata=_NoEffects(), text_profiles=resolver,
        )
    assert raised.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE


class _PassedV3Guard(Exception):
    pass


class _V1DocumentProbe:
    def get_version(self, *_args: object) -> None:
        raise _PassedV3Guard


def test_historical_v1_reaches_its_existing_path() -> None:
    row = _run(
        analysis_profile_id=str(AR_TEXT_PROFILE.analysis_profile_id),
        prompt_bundle_id=str(AR_TEXT_PROFILE.prompt_bundle.prompt_bundle_id),
        norms_snapshot_id=None,
        norm_retrieval_set_id=None,
    )
    with pytest.raises(_PassedV3Guard):
        execute_run(
            _NoEffects(), RUN_ID,
            blob_store=_NoEffects(), adapter=_Adapter(), provider_config=CONFIG,
            runs=_Runs(row), documents=_V1DocumentProbe(), jobs=_NoEffects(),
            blob_metadata=_NoEffects(),
        )


def test_exact_v3_with_injected_reviewed_registry_passes_early_guard(monkeypatch) -> None:
    monkeypatch.setattr(TrustedPackRegistry, "select_beta", lambda self: object())
    with pytest.raises(_PassedV3Guard):
        execute_run(
            _NoEffects(), RUN_ID,
            blob_store=_NoEffects(), adapter=_Adapter(), provider_config=CONFIG,
            runs=_Runs(_run()), documents=_V1DocumentProbe(), jobs=_NoEffects(),
            blob_metadata=_NoEffects(),
            text_profiles=lambda *_: pytest.fail("v3 cannot resolve a legacy text profile"),
            ar_v3_pack_registry=TrustedPackRegistry.empty(),
        )
