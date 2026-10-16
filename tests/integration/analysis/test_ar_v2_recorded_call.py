"""Recorded call facts retain the exact offline response without a second read."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_call import (
    RecordedCallFactsError, build_recorded_call_facts,
)
from auditmanager.analysis.profiles.ar_v2.recorded_input import prepare_recorded_v2_input
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.analysis.profiles.ar_v2.recorded_response import replay_recorded_response
from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document


VERSION = "ver_01M2545JSD15ETSNNV904X991J"
CALL = "mc_01M2545JSD15ETSNNV904X991J"
MODEL = "fixture/ar-v2-recorded"


def _replay(tmp_path: Path, *, truncated: bool = False):
    text = "Стена: 200 мм"
    source = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": VERSION, "normalization": {"id": "NFC"},
        "pages": [{"page_number": 1, "char_start": 0, "char_end": len(text), "text": text}],
        "total_char_count": len(text),
    }
    payload = canonical_bytes(source)
    ref = ArtifactRef("prepared.text_layer", "blob_" + "0" * 26,
                      sha256_hex(payload), len(payload), "application/json")
    prepared = prepare_recorded_v2_input(
        version_uid=VERSION, textless_pages=None,
        text_layer_document=source, text_layer_ref=ref,
        text_layer_read_sha256=ref.sha256,
        recognised_document=None, recognised_ref=None, recognised_read_sha256=None,
        analysis_profile_id=PROFILE_ID, prompt_bundle_id=PROMPT_BUNDLE_ID,
        fixture_model_id=MODEL,
        settings=RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
    )
    output = json.dumps({"observations": [{
        "category": "dimensions", "finding_text": "Размер стены",
        "recommendation_text": "Проверить", "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": text}],
    }]}, ensure_ascii=False)
    recording = recording_document(
        request=prepared.request, output_text=output,
        stop_reason="max_tokens" if truncated else "end_turn",
        input_tokens=101, output_tokens=42, latency_ms=7, note="offline fixture",
    )
    path = tmp_path / f"{prepared.request_sha256}.json"
    path.write_text(json.dumps(recording, ensure_ascii=False), encoding="utf-8")
    replay = replay_recorded_response(
        prepared=prepared, adapter=RecordedAdapter(tmp_path),
        expected_request_sha256=prepared.request_sha256,
        expected_model_id=MODEL,
        expected_source_binding_sha256=prepared.source_binding_sha256,
    )
    return prepared, replay, path


@pytest.mark.parametrize("truncated,status", [(False, "succeeded"), (True, "truncated")])
def test_one_replay_supplies_exact_call_usage_after_recording_is_removed(
    tmp_path: Path, truncated: bool, status: str,
) -> None:
    prepared, replay, path = _replay(tmp_path, truncated=truncated)
    path.unlink()
    facts = build_recorded_call_facts(prepared=prepared, replay=replay, model_call_id=CALL)

    assert facts.model_call_id == CALL
    assert facts.model_id == MODEL
    assert facts.provider_mode is ProviderMode.RECORDED
    assert facts.request_sha256 == prepared.request_sha256
    assert facts.response_sha256 == replay.response.response_sha256
    assert facts.source_binding_sha256 == prepared.source_binding_sha256
    assert (facts.input_tokens, facts.output_tokens, facts.latency_ms) == (101, 42, 7)
    assert facts.status == status
    assert facts.parameters == prepared.request.parameters
    assert "messages" not in facts.parameters
    mutable_copy = facts.parameters
    mutable_copy["max_tokens"] = 1
    assert facts.parameters["max_tokens"] == 4096


def test_changed_response_or_source_binding_is_refused(tmp_path: Path) -> None:
    prepared, replay, _ = _replay(tmp_path)
    with pytest.raises(RecordedCallFactsError, match="recorded_response_mismatch"):
        build_recorded_call_facts(
            prepared=prepared, replay=replace(replay, response_sha256="f" * 64),
            model_call_id=CALL,
        )
    with pytest.raises(RecordedCallFactsError, match="recorded_source_binding_mismatch"):
        build_recorded_call_facts(
            prepared=prepared, replay=replace(replay, source_binding_sha256="f" * 64),
            model_call_id=CALL,
        )


def test_live_relabel_and_invalid_call_id_are_refused(tmp_path: Path) -> None:
    prepared, replay, _ = _replay(tmp_path)
    with pytest.raises(RecordedCallFactsError, match="recorded_request_mismatch"):
        build_recorded_call_facts(
            prepared=prepared, replay=replace(replay, provider_mode=ProviderMode.LIVE),
            model_call_id=CALL,
        )
    with pytest.raises(RecordedCallFactsError, match="invalid_model_call_id"):
        build_recorded_call_facts(prepared=prepared, replay=replay, model_call_id="path.pdf")


def test_forged_usage_and_cost_are_refused(tmp_path: Path) -> None:
    prepared, replay, _ = _replay(tmp_path)
    with pytest.raises(RecordedCallFactsError, match="recorded_usage_invalid"):
        build_recorded_call_facts(
            prepared=prepared, replay=replace(replay, response=replace(replay.response, latency_ms=-1)),
            model_call_id=CALL,
        )
    with pytest.raises(RecordedCallFactsError, match="recorded_response_mismatch"):
        build_recorded_call_facts(
            prepared=prepared,
            replay=replace(replay, response=replace(replay.response, reported_cost_usd=1.0)),
            model_call_id=CALL,
        )
