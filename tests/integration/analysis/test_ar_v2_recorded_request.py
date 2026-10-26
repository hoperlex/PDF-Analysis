"""The AR v2 recorded request is reproducible and never selects a live model."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from auditmanager.analysis.profiles.ar_shared import v2_identities
from auditmanager.analysis.profiles.ar_v2 import prompt_material, registered
from auditmanager.analysis.profiles.ar_shared.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v2.recorded_request import (
    RecordedGenerationSettings,
    RecordedRequestError,
    build_recorded_request,
)
from auditmanager.analysis.profiles.ar_v2.response_pipeline import finish_response
from auditmanager.analysis.text.adapter import ModelRequest
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.shared.errors import DomainError


def _layer(text: str = "Стена А: 200 мм") -> TextLayer:
    return TextLayer(
        version_uid="ver_fixture_1", normalization_id="NFC",
        pages=(Page(1, 0, len(text), text),), document_text=text,
    )


def _build(**changes: object) -> ModelRequest:
    arguments = {
        "analysis_profile_id": v2_identities.PROFILE_ID,
        "prompt_bundle_id": v2_identities.PROMPT_BUNDLE_ID,
        "fixture_model_id": "fixture/ar-v2-recorded",
        "settings": RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
        "text_layer": _layer(),
    }
    arguments.update(changes)
    return build_recorded_request(**arguments)  # type: ignore[arg-type]


def test_exact_body_is_stable_and_bound_to_reviewed_material() -> None:
    first = _build()
    second = _build()
    assert first.body == second.body
    assert first.request_sha256 == second.request_sha256
    assert first.model_id == "fixture/ar-v2-recorded"
    assert first.body["model"] == first.model_id
    assert first.body["system"] == prompt_material.system_prompt()
    assert first.body["messages"] == [{
        "role": "user", "content": prompt_material.render_user_prompt(_layer()),
    }]
    assert first.body["output_config"]["format"]["schema"] == registered.response_schema()
    assert first.body["max_tokens"] == 4096
    assert first.body["thinking"] == {"type": "adaptive"}
    assert first.body["output_config"]["effort"] == "high"


def test_text_ocr_model_and_parameters_change_checksum() -> None:
    original = _build().request_sha256
    variations = (
        _build(text_layer=_layer("Стена А: 250 мм")),
        _build(recognised_context=(RecognisedContext(1, "OCR: фасад", ()),)),
        _build(fixture_model_id="fixture/ar-v2-second"),
        _build(settings=RecordedGenerationSettings(8192, "high", {"type": "adaptive"})),
    )
    assert all(item.request_sha256 != original for item in variations)
    changed_ocr = _build(recognised_context=(RecognisedContext(1, "OCR: крыша", ()),))
    assert changed_ocr.request_sha256 != variations[1].request_sha256
    assert "не цитировать" in variations[1].body["messages"][0]["content"]


def test_checksum_covers_prompt_and_schema_body_fields() -> None:
    original = _build()
    changed_prompt = deepcopy(original.body)
    changed_prompt["system"] += "\nНовая инструкция"
    changed_schema = deepcopy(original.body)
    changed_schema["output_config"]["format"]["schema"]["properties"]["observations"]["maxItems"] = 1
    assert ModelRequest(original.model_id, changed_prompt).request_sha256 != original.request_sha256
    assert ModelRequest(original.model_id, changed_schema).request_sha256 != original.request_sha256


@pytest.mark.parametrize("model", ["", "proxy", "anthropic/claude-opus-5", "fixture/", "fixture/Upper", " fixture/ar-v2"])
def test_unpinned_or_malformed_model_identity_is_refused(model: str) -> None:
    with pytest.raises(RecordedRequestError, match="invalid_fixture_model_id"):
        _build(fixture_model_id=model)


@pytest.mark.parametrize("values", [
    (0, "high", {"type": "adaptive"}),
    (True, "high", {"type": "adaptive"}),
    (4096, "unknown", {"type": "adaptive"}),
    (4096, "high", {"type": "enabled", "budget_tokens": 1000}),
])
def test_unpinned_generation_settings_are_refused(values: tuple[object, ...]) -> None:
    with pytest.raises(RecordedRequestError):
        RecordedGenerationSettings(*values)  # type: ignore[arg-type]


def test_mutated_settings_are_revalidated() -> None:
    settings = RecordedGenerationSettings(4096, "high", {"type": "adaptive"})
    settings.thinking["type"] = "enabled"  # type: ignore[index]
    with pytest.raises(RecordedRequestError, match="invalid_thinking"):
        _build(settings=settings)


def test_profile_and_bundle_are_checked_before_request_material(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt_material, "render_user_prompt", lambda *_a, **_k: pytest.fail("rendered"))
    with pytest.raises(registered.RecordedProfileError, match="not registered"):
        _build(analysis_profile_id="ap_invalid")
    with pytest.raises(registered.RecordedProfileError, match="not registered"):
        _build(prompt_bundle_id="pb_invalid")


def test_reviewed_prompt_or_schema_tamper_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompt_material, "_SYSTEM_RULES", "changed")
    with pytest.raises(registered.RecordedProfileError, match="material has changed"):
        _build()
    monkeypatch.undo()
    monkeypatch.setattr(registered, "response_schema", lambda: {"type": "null"})
    with pytest.raises(registered.RecordedProfileError, match="material has changed"):
        _build()


def test_invalid_text_and_ocr_are_refused() -> None:
    bad_layer = TextLayer(
        version_uid="ver_fixture_1", normalization_id="NFC",
        pages=(Page(1, 0, 4, "текст"),), document_text="other",
    )
    with pytest.raises(RecordedRequestError, match="invalid_text_layer"):
        _build(text_layer=bad_layer)
    with pytest.raises(RecordedRequestError, match="invalid_recognised_context"):
        _build(recognised_context=(RecognisedContext(2, "OCR", ()),))
    with pytest.raises(RecordedRequestError, match="invalid_recognised_context"):
        _build(recognised_context=(RecognisedContext(1, "first", ()), RecognisedContext(1, "again", ())))


@pytest.mark.parametrize("bad_page", [
    Page(1, 0, 4, None),  # type: ignore[arg-type]
    Page(1, "0", 4, "тест"),  # type: ignore[arg-type]
    Page(1, 0, "4", "тест"),  # type: ignore[arg-type]
])
def test_malformed_page_fields_raise_typed_request_error(bad_page: Page) -> None:
    malformed = TextLayer("ver_fixture_1", "NFC", (bad_page,), "тест")
    with pytest.raises(RecordedRequestError, match="invalid_text_layer"):
        _build(text_layer=malformed)


def test_offline_recorded_adapter_and_response_pipeline(tmp_path: Path) -> None:
    request = _build()
    output = json.dumps({"observations": [{
        "category": "dimensions",
        "finding_text": "Проверить размер стены",
        "recommendation_text": "Сверить значение в проекте",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": "Стена А: 200 мм"}],
    }]}, ensure_ascii=False)
    recording = recording_document(
        request=request, output_text=output, stop_reason="end_turn",
        input_tokens=100, output_tokens=40, latency_ms=5, note="offline fixture",
    )
    (tmp_path / f"{request.request_sha256}.json").write_text(
        json.dumps(recording, ensure_ascii=False), encoding="utf-8"
    )
    adapter = RecordedAdapter(tmp_path)
    response = adapter.complete(request)
    finished = finish_response(response, _layer())
    assert finished.merge.source_proposal_ordinals == (0,)
    assert finished.grounding.accepted[0].evidence[0].quote == "Стена А: 200 мм"
    assert adapter.provider_mode.value == "recorded"
    with pytest.raises(DomainError) as failure:
        adapter.complete(_build(text_layer=_layer("Стена А: 250 мм")))
    assert failure.value.detail_fields["reason"] == "recording_missing"
