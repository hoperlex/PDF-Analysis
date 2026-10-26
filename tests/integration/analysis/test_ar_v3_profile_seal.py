"""The unserved beta profile seals exact six-scope provider material."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import auditmanager.analysis.profiles.ar_v3.prompt_material as prompt_material
import auditmanager.analysis.profiles.ar_v3.v3_profile as seal
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import SNAPSHOT_ID
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.text.textlayer import Page, TextLayer
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE


DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
SELECTED = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
HIDDEN = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
SELECTED_TEXT = "Ширина прохода по условию составляет 1,4 м"
HIDDEN_TEXT = "ТОЛЬКО ЛОКАЛЬНОЕ ПЕРЕПРИВЯЗЫВАНИЕ"
MAP_SHA = "a" * 64


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _source(paragraph_id: str, ordinal: int, text: str) -> dict[str, object]:
    return {
        "norm_document_id": DOCUMENT,
        "norm_paragraph_id": paragraph_id,
        "designation": "СП 54",
        "title": "Жилые здания",
        "ordinal": ordinal,
        "clause_number": "7.1.4",
        "page_label": "7",
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _set_bytes(item_ids: tuple[str, ...], *, oversized: bool = False) -> bytes:
    selected = _source(SELECTED, 0, SELECTED_TEXT)
    hidden = _source(HIDDEN, 1, HIDDEN_TEXT)
    part = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [
            dict(selected, item_id=item_id, label=f"N{index}")
            for index, item_id in enumerate(item_ids, 1)
        ],
    }).decode("utf-8")
    if oversized:
        part += " " * (22_001 - len(part))
    return _canonical({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {
            "map_sha256": MAP_SHA,
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


def _layer() -> TextLayer:
    text = "АР. Ширина прохода 1,2 м."
    return TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)


def _request(requested_scope: str, raw: bytes | None = None, **overrides: object) -> seal.SealedV3Request:
    data = raw if raw is not None else _set_bytes(scope_membership(requested_scope).item_ids)
    arguments: dict[str, object] = {
        "analysis_profile_id": seal.PROFILE_ID,
        "prompt_bundle_id": seal.PROMPT_BUNDLE_ID,
        "expected_version_uid": "ver_fixture",
        "expected_set_sha256": hashlib.sha256(data).hexdigest(),
        "expected_snapshot_id": SNAPSHOT_ID,
        "expected_map_sha256": MAP_SHA,
        "scope_id": requested_scope,
        "expected_composition_sha256": scope_membership("F1").composition_sha256,
    }
    arguments.update(overrides)
    return seal.prepare_beta_v3_request(_layer(), data, **arguments)


GOLDEN_MATERIAL_SHA256 = {
    "F1": "83c220a93cc3ca8ace1627b1adb6592e56be24b890cf835e2c2c863c178d60eb",
    "F2": "cc462f47d727903efad42e48fb4b053988190e90094ec5d52ccc9251258a4e81",
    "A1": "f7bed96a9d1e0b6d183187da7de178ce7b7a3947f0e5ffe0272e388e97aa6730",
    "A2": "242aaafc381e29121da0f50bce05931579e654e96dc180d71afcc1294ff8bf85",
    "S1": "545d0beaf53a2e733ff8e884aacc53cccbe238f84953b1d49e89eb57d14a1a2f",
    "S2": "198ca5a3b9c81b752f4057424889d39a3bb575a7d43c96a9a440aca3e27d2621",
}


def test_profile_identity_bundle_and_historical_profile_are_distinct() -> None:
    profile = seal.resolve_beta_v3_profile(seal.PROFILE_ID, seal.PROMPT_BUNDLE_ID)
    assert profile.profile_version == "3.0.0-beta.1"
    assert profile.content_sha256 == seal.PROFILE_CONTENT_SHA256
    assert profile.bundle_sha256 == seal.BUNDLE_CONTENT_SHA256
    assert profile.scopes == ("F1", "F2", "A1", "A2", "S1", "S2")
    assert profile.analysis_profile_id != V1_REFERENCE_PROFILE.analysis_profile_id
    assert profile.prompt_bundle_id != V1_REFERENCE_PROFILE.prompt_bundle.prompt_bundle_id
    assert profile.content_sha256 != V1_REFERENCE_PROFILE.content_sha256
    assert profile.policy_sha256 == (
        "9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58"
    )


@pytest.mark.parametrize("scope_id", tuple(GOLDEN_MATERIAL_SHA256))
def test_every_scope_has_stable_request_bytes_without_hidden_corpus_text(scope_id: str) -> None:
    result = _request(scope_id)
    replay = _request(scope_id)
    material = result.material_json.encode("utf-8")
    assert result == replay
    assert result.material_sha256 == hashlib.sha256(material).hexdigest()
    assert result.material_sha256 == GOLDEN_MATERIAL_SHA256[scope_id]
    assert result.candidate.item_ids == scope_membership(scope_id).item_ids
    assert result.candidate.scope_id == scope_id
    assert HIDDEN_TEXT not in result.material_json
    assert SELECTED_TEXT in result.material_json
    decoded = json.loads(result.material_json)
    assert _canonical(decoded) == material
    assert decoded["profile_content_sha256"] == result.profile.content_sha256
    assert decoded["request_sha256"] == result.candidate.request_sha256
    assert decoded["set_sha256"] == result.candidate.set_sha256
    assert decoded["system_prompt"] == result.profile.system_prompt
    assert decoded["response_schema_json"] == result.profile.response_schema_json


@pytest.mark.parametrize("overrides", [
    {"scope_id": None},
    {"scope_id": "Z9"},
    {"expected_composition_sha256": "0" * 64},
    {"expected_snapshot_id": "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"},
    {"analysis_profile_id": "ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH"},
    {"prompt_bundle_id": "pb_01K7F4N2A9R8T6V5W3X2Y1Z0QH"},
])
def test_missing_or_foreign_profile_scope_and_snapshot_refuse(overrides: dict[str, object]) -> None:
    with pytest.raises(seal.BetaV3ProfileRefused):
        _request("F1", **overrides)


def test_foreign_set_item_order_and_oversized_part_refuse() -> None:
    with pytest.raises(seal.BetaV3ProfileRefused, match="scope_set_item_mismatch"):
        _request("F1", _set_bytes(("C03", "C02", "C01")))
    with pytest.raises(seal.BetaV3ProfileRefused, match="prompt_part_size_invalid"):
        _request("F1", _set_bytes(scope_membership("F1").item_ids, oversized=True))


def test_changed_original_topic_or_system_prompt_refuses_before_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "original_topics.md"
    changed.write_bytes(prompt_material._TOPICS_PATH.read_bytes() + b"changed")
    monkeypatch.setattr(prompt_material, "_TOPICS_PATH", changed)
    with pytest.raises(seal.BetaV3ProfileRefused, match="v3_profile_source_invalid"):
        _request("F1")
    monkeypatch.undo()
    monkeypatch.setattr(prompt_material, "_SYSTEM_RULES", prompt_material._SYSTEM_RULES + "changed")
    with pytest.raises(seal.BetaV3ProfileRefused, match="v3_profile_material_changed"):
        _request("F1")


def test_identity_collision_refuses_even_with_matching_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(seal, "PROFILE_ID", V1_REFERENCE_PROFILE.analysis_profile_id)
    with pytest.raises(seal.BetaV3ProfileRefused, match="v3_profile_identity_collision"):
        seal.resolve_beta_v3_profile(seal.PROFILE_ID, seal.PROMPT_BUNDLE_ID)


def test_request_digest_changes_with_project_text_or_set_bytes() -> None:
    first = _request("F1")
    text = "АР. Ширина прохода 1,3 м."
    changed_layer = TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)
    changed_project = seal.prepare_beta_v3_request(
        changed_layer, _set_bytes(scope_membership("F1").item_ids),
        analysis_profile_id=seal.PROFILE_ID,
        prompt_bundle_id=seal.PROMPT_BUNDLE_ID,
        expected_version_uid="ver_fixture",
        expected_set_sha256=first.candidate.set_sha256,
        expected_snapshot_id=SNAPSHOT_ID,
        expected_map_sha256=MAP_SHA,
        scope_id="F1",
        expected_composition_sha256=first.profile.composition_sha256,
    )
    assert changed_project.material_sha256 != first.material_sha256
    raw = _set_bytes(scope_membership("F1").item_ids)
    changed = json.loads(raw)
    changed["rebinding_paragraphs"][1]["text"] = "ИНОЕ СКРЫТОЕ СОДЕРЖИМОЕ"
    changed["rebinding_paragraphs"][1]["text_sha256"] = hashlib.sha256(
        changed["rebinding_paragraphs"][1]["text"].encode("utf-8")
    ).hexdigest()
    changed_set = _request("F1", _canonical(changed))
    assert changed_set.candidate.user_prompt == first.candidate.user_prompt
    assert changed_set.material_sha256 != first.material_sha256


def test_bundle_digest_rechecks_schema_and_scope_material(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seal, "response_schema", lambda: {"type": "object"})
    with pytest.raises(seal.BetaV3ProfileRefused, match="v3_profile_material_changed"):
        _request("F1")
