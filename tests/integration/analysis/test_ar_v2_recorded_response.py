"""The recorded response bridge keeps replay and grounding provenance together."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_input import prepare_recorded_v2_input
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.analysis.profiles.ar_v2.recorded_response import (
    RecordedResponseError,
    replay_recorded_response,
)
from auditmanager.analysis.profiles.ar_shared.v2_identities import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.config import ProviderMode
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.shared.errors import DomainError


VERSION = "ver_01M2545JSD15ETSNNV904X991J"
MODEL = "fixture/ar-v2-recorded"


def _prepared():
    text = "Стена: 200 мм"
    document = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": VERSION, "normalization": {"id": "NFC"},
        "pages": [{"page_number": 1, "char_start": 0,
                   "char_end": len(text), "text": text}],
        "total_char_count": len(text),
    }
    payload = canonical_bytes(document)
    reference = ArtifactRef(
        role="prepared.text_layer", blob_id="blob_" + "0" * 26,
        sha256=sha256_hex(payload), size_bytes=len(payload),
        media_type="application/json",
    )
    return prepare_recorded_v2_input(
        version_uid=VERSION, textless_pages=None,
        text_layer_document=document, text_layer_ref=reference,
        text_layer_read_sha256=reference.sha256,
        recognised_document=None, recognised_ref=None, recognised_read_sha256=None,
        analysis_profile_id=PROFILE_ID, prompt_bundle_id=PROMPT_BUNDLE_ID,
        fixture_model_id=MODEL,
        settings=RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
    )


def _replay(prepared, adapter: RecordedAdapter, **changes):
    arguments = {
        "prepared": prepared, "adapter": adapter,
        "expected_request_sha256": prepared.request_sha256,
        "expected_model_id": MODEL,
        "expected_source_binding_sha256": prepared.source_binding_sha256,
    }
    arguments.update(changes)
    return replay_recorded_response(**arguments)


def _record(tmp_path: Path, prepared, *, model_id: str = MODEL) -> None:
    output = json.dumps({"observations": [
        {
            "category": "dimensions", "finding_text": "Размер стены",
            "recommendation_text": "Проверить", "proposed_severity": "operational",
            "evidence": [{"page_number": 1, "quote": "Стена: 200 мм"}],
        },
        {
            "category": "dimensions", "finding_text": "Нет цитаты",
            "recommendation_text": "Проверить", "proposed_severity": "operational",
            "evidence": [{"page_number": 1, "quote": "Несуществующий текст"}],
        },
    ]}, ensure_ascii=False)
    recording = recording_document(
        request=prepared.request, output_text=output, stop_reason="end_turn",
        input_tokens=100, output_tokens=40, latency_ms=5, note="offline fixture",
    )
    recording["model_id"] = model_id
    (tmp_path / f"{prepared.request_sha256}.json").write_text(
        json.dumps(recording, ensure_ascii=False), encoding="utf-8",
    )


def test_exact_offline_replay_retains_three_digests_and_rejected_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    _record(tmp_path, prepared)
    calls = []
    original = RecordedAdapter.complete

    def counted(self, request):
        calls.append(request.request_sha256)
        return original(self, request)

    monkeypatch.setattr(RecordedAdapter, "complete", counted)
    result = _replay(prepared, RecordedAdapter(tmp_path))
    assert calls == [prepared.request_sha256]
    assert result.provider_mode is ProviderMode.RECORDED
    assert result.model_id == MODEL
    assert result.request_sha256 == prepared.request_sha256
    assert result.source_binding_sha256 == prepared.source_binding_sha256
    assert result.response_sha256 == result.finished.response_sha256
    assert len(result.response_sha256) == 64
    assert result.finished.merge.source_proposal_ordinals == (0,)
    assert result.finished.grounding.accepted[0].evidence[0].quote == "Стена: 200 мм"
    assert result.finished.grounding.rejected[0].failures[0].reason == "quotation_absent"
    with pytest.raises(FrozenInstanceError):
        result.model_id = "other"


@pytest.mark.parametrize("field,value,reason", [
    ("expected_request_sha256", "0" * 64, "recorded_request_mismatch"),
    ("expected_model_id", "fixture/other", "recorded_model_mismatch"),
    ("expected_source_binding_sha256", "0" * 64, "recorded_source_binding_mismatch"),
])
def test_context_mismatch_refused_before_adapter_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    field: str, value: str, reason: str,
) -> None:
    prepared = _prepared()
    monkeypatch.setattr(
        RecordedAdapter, "complete", lambda *_args: pytest.fail("replayed"),
    )
    with pytest.raises(RecordedResponseError, match=reason):
        _replay(prepared, RecordedAdapter(tmp_path), **{field: value})


def test_mutated_request_body_and_source_binding_refused_before_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    monkeypatch.setattr(
        RecordedAdapter, "complete", lambda *_args: pytest.fail("replayed"),
    )
    mutated_body = dict(prepared.request.body)
    mutated_body["max_tokens"] = 2048
    changed = replace(
        prepared, request=ModelRequest(prepared.request.model_id, mutated_body)
    )
    with pytest.raises(RecordedResponseError, match="recorded_request_mismatch"):
        _replay(changed, RecordedAdapter(tmp_path),
                expected_request_sha256=prepared.request_sha256)
    changed = replace(prepared, source_binding_sha256="0" * 64)
    with pytest.raises(RecordedResponseError, match="recorded_source_binding_mismatch"):
        _replay(changed, RecordedAdapter(tmp_path))


def test_live_or_imitation_adapter_refused_before_call(tmp_path: Path) -> None:
    prepared = _prepared()

    class Imitation:
        provider_mode = ProviderMode.RECORDED

        def complete(self, _request):
            pytest.fail("called imitation")

    with pytest.raises(RecordedResponseError, match="recorded_adapter_required"):
        _replay(prepared, Imitation())  # type: ignore[arg-type]

    adapter = RecordedAdapter(tmp_path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(RecordedAdapter, "_PROVIDER_MODE", ProviderMode.LIVE)
        with pytest.raises(RecordedResponseError, match="recorded_adapter_required"):
            _replay(prepared, adapter)


def test_recording_model_mismatch_and_missing_recording_propagate_without_fallback(
    tmp_path: Path,
) -> None:
    prepared = _prepared()
    adapter = RecordedAdapter(tmp_path)
    with pytest.raises(DomainError) as missing:
        _replay(prepared, adapter)
    assert missing.value.detail_fields["reason"] == "recording_missing"
    _record(tmp_path, prepared, model_id="fixture/wrong")
    with pytest.raises(DomainError) as mismatched:
        _replay(prepared, adapter)
    assert mismatched.value.detail_fields["reason"] == "recording_model_mismatch"
