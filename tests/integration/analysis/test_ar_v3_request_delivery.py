"""A sealed AR v3 scope becomes one exact body for every model transport."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID,
    AR_V3_BETA_PROFILE_ID,
    V3DeliveryRefused,
    V3GenerationSettings,
    build_v3_model_request,
    prepare_beta_v3_request,
)
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.text.textlayer import Page, TextLayer


SETTINGS = V3GenerationSettings(4096, "high", {"type": "adaptive"})
SCOPES = ("F1", "F2", "A1", "A2", "S1", "S2")
GOLDEN_BODY_SHA256 = {
    "F1": "bacf77f46f2f9f5d2f9c84359b74fc597878573437b5aa57eb1cf73ae703155d",
    "F2": "3dcf0dc58bf5e3bbe82619c52965fac675ad626391348dd5a034121d6b60ea6a",
    "A1": "3894dff710d46bd1713a3c561d65c0bd4c0dc55f0a0ba54fe6ad3a96bdf64216",
    "A2": "b227b8efbe77f11e0ab6d3e982e71f8e0afee7189eca759f233adacc863fc49d",
    "S1": "795b16695d5319b12023b94cde31ccd9146fd6faf9a272cf77039ad1367421fc",
    "S2": "99dd2ee518260c3d00f45457a4925d10a69d42177ea3549865525fe5eabd4d7f",
}
SNAPSHOT_ID = "ns_01M59N8QNBVN91ACA2HCE6VE74"
SELECTED_TEXT = "Ширина прохода по условию составляет 1,4 м"
HIDDEN_TEXT = "ТОЛЬКО ЛОКАЛЬНОЕ ПЕРЕПРИВЯЗЫВАНИЕ"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _paragraph(paragraph_id: str, ordinal: int, text: str) -> dict[str, object]:
    return {
        "norm_document_id": "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ",
        "norm_paragraph_id": paragraph_id,
        "designation": "СП 54", "title": "Жилые здания", "ordinal": ordinal,
        "clause_number": "7.1.4", "page_label": "7", "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _request(scope_id: str):
    selected = _paragraph("npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK", 0, SELECTED_TEXT)
    hidden = _paragraph("npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM", 1, HIDDEN_TEXT)
    part = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [
            dict(selected, item_id=item_id, label=f"N{index}")
            for index, item_id in enumerate(scope_membership(scope_id).item_ids, 1)
        ],
    }).decode("utf-8")
    raw = _canonical({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {
            "map_sha256": "a" * 64,
            "reviewed_content_key": "synthetic-test-only",
            "norms_snapshot_id": SNAPSHOT_ID,
            "embedding_build": "bge-m3-dense-v1",
        },
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1",
        "prompt_part": part,
        "prompt_part_characters": len(part),
        "windows_per_item": 0,
        "inside_target_windows_dropped": True,
        "rebinding_paragraphs": [selected, hidden],
    })
    text = "АР. Ширина прохода 1,2 м."
    layer = TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)
    return prepare_beta_v3_request(
        layer, raw,
        analysis_profile_id=AR_V3_BETA_PROFILE_ID,
        prompt_bundle_id=AR_V3_BETA_BUNDLE_ID,
        expected_version_uid="ver_fixture",
        expected_set_sha256=hashlib.sha256(raw).hexdigest(),
        expected_snapshot_id=SNAPSHOT_ID,
        expected_map_sha256="a" * 64,
        scope_id=scope_id,
        expected_composition_sha256=scope_membership(scope_id).composition_sha256,
    )


@pytest.mark.parametrize("scope_id", SCOPES)
def test_six_scopes_have_one_transport_independent_body(scope_id: str) -> None:
    sealed = _request(scope_id)
    first = build_v3_model_request(
        sealed, model_identity="fixture/ar-v3-beta", settings=SETTINGS,
        idempotency_scope="attempt-1",
    )
    second = build_v3_model_request(
        sealed, model_identity="fixture/ar-v3-beta", settings=SETTINGS,
        idempotency_scope="attempt-2",
    )
    assert first.body == second.body
    assert first.request_sha256 == second.request_sha256
    assert first.idempotency_scope != second.idempotency_scope
    assert first.model_id == "fixture/ar-v3-beta"
    assert first.body["model"] == first.model_id
    assert first.body["system"] == sealed.profile.system_prompt
    assert first.body["messages"] == [
        {"role": "user", "content": sealed.candidate.user_prompt}
    ]
    assert first.body["output_config"] == {
        "effort": "high",
        "format": {
            "type": "json_schema",
            "schema": json.loads(sealed.profile.response_schema_json),
        },
    }
    assert first.body["max_tokens"] == 4096
    assert first.body["thinking"] == {"type": "adaptive"}
    rendered = json.dumps(first.body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert first.request_sha256 == hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    assert first.request_sha256 == GOLDEN_BODY_SHA256[scope_id]
    assert HIDDEN_TEXT not in rendered
    assert SELECTED_TEXT in rendered
    assert sealed.candidate.request_sha256 != first.request_sha256


def test_body_digest_changes_with_model_or_generation_pins() -> None:
    sealed = _request("F1")
    baseline = build_v3_model_request(
        sealed, model_identity="fixture/ar-v3-beta", settings=SETTINGS,
    )
    model = build_v3_model_request(
        sealed, model_identity="fixture/ar-v3-beta-2", settings=SETTINGS,
    )
    settings = build_v3_model_request(
        sealed, model_identity="fixture/ar-v3-beta",
        settings=V3GenerationSettings(2048, "high", {"type": "adaptive"}),
    )
    assert len({baseline.request_sha256, model.request_sha256, settings.request_sha256}) == 3


@pytest.mark.parametrize("mutation", [
    lambda sealed: replace(sealed, material_sha256="0" * 64),
    lambda sealed: replace(sealed, material_json=sealed.material_json + " "),
    lambda sealed: replace(sealed, candidate=replace(sealed.candidate, user_prompt="подмена")),
    lambda sealed: replace(sealed, candidate=replace(sealed.candidate, scope_id="Z9")),
    lambda sealed: replace(sealed, candidate=replace(sealed.candidate, response_schema_json="[]")),
    lambda sealed: replace(sealed, profile=replace(sealed.profile, profile_version="v1")),
])
def test_changed_profile_scope_or_material_refuses(mutation) -> None:
    with pytest.raises(V3DeliveryRefused):
        build_v3_model_request(
            mutation(_request("F1")), model_identity="fixture/ar-v3-beta",
            settings=SETTINGS,
        )


@pytest.mark.parametrize("model", ["", "stub", "placeholder", "unknown", "model with spaces"])
def test_unpinned_or_placeholder_model_refuses(model: str) -> None:
    with pytest.raises(V3DeliveryRefused, match="v3_model_identity_invalid"):
        build_v3_model_request(_request("F1"), model_identity=model, settings=SETTINGS)


@pytest.mark.parametrize("settings", [
    None,  # type: ignore[list-item]
    V3GenerationSettings(4096, "high", {"type": "adaptive"}),
])
def test_settings_type_and_scope_are_checked(settings) -> None:
    if settings is None:
        with pytest.raises(V3DeliveryRefused, match="v3_generation_settings_required"):
            build_v3_model_request(_request("F1"), model_identity="fixture/ar-v3-beta", settings=settings)
    else:
        with pytest.raises(V3DeliveryRefused, match="v3_idempotency_scope_invalid"):
            build_v3_model_request(
                _request("F1"), model_identity="fixture/ar-v3-beta",
                settings=settings, idempotency_scope="",
            )


@pytest.mark.parametrize("values", [
    (0, "high", {"type": "adaptive"}),
    (16_001, "high", {"type": "adaptive"}),
    (4096, "unknown", {"type": "adaptive"}),
    (4096, "high", {"type": "enabled"}),
])
def test_generation_settings_refuse_invalid_values(values) -> None:
    with pytest.raises(V3DeliveryRefused, match="v3_generation_settings_invalid"):
        V3GenerationSettings(*values)
