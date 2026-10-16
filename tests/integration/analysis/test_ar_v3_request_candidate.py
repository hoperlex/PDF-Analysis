"""An AR v3 request candidate binds selected prompt text without corpus leakage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pytest

from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
from auditmanager.analysis.profiles.ar_v3.request_candidate import (
    V3RequestRefused,
    prepare_v3_request_candidate,
)
from auditmanager.analysis.profiles.ar_v3.response_schema import response_schema
from auditmanager.analysis.text.textlayer import Page, TextLayer


DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
SELECTED = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
HIDDEN = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
SNAPSHOT = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
MAP_SHA = "a" * 64
SELECTED_TEXT = "Минимальная ширина прохода составляет 1,4 м"
HIDDEN_TEXT = "ПОЛНЫЙ ТЕКСТ ТОЛЬКО ДЛЯ ПЕРЕПРИВЯЗКИ"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _set_bytes(*, hidden_text: str = HIDDEN_TEXT) -> bytes:
    rows = [dict(
        norm_document_id=DOCUMENT, norm_paragraph_id=paragraph,
        designation="СП 54", title="Жилые здания", ordinal=ordinal,
        clause_number="7.1.4", page_label="7", text=value,
        text_sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
    ) for ordinal, (paragraph, value) in enumerate((
        (SELECTED, SELECTED_TEXT), (HIDDEN, hidden_text),
    ))]
    part = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(rows[0], item_id="item_a", label="N1")],
    }).decode("utf-8")
    return _canonical({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {
            "map_sha256": MAP_SHA, "reviewed_content_key": "reviewed-key",
            "norms_snapshot_id": SNAPSHOT, "embedding_build": "bge-m3-dense-v1",
        },
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1", "norm_value_version": "norm-value-v1",
        "prompt_part": part, "prompt_part_characters": len(part),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": rows,
    })


def _layer(text: str = "АР. Ширина прохода 1,2 м.") -> TextLayer:
    return TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)


def _candidate(*, set_bytes: bytes | None = None, **overrides: object):
    raw = set_bytes if set_bytes is not None else _set_bytes()
    arguments = dict(
        expected_version_uid="ver_fixture",
        expected_set_sha256=hashlib.sha256(raw).hexdigest(),
        expected_snapshot_id=SNAPSHOT,
        expected_map_sha256=MAP_SHA,
    )
    arguments.update(overrides)
    return prepare_v3_request_candidate(_layer(), raw, **arguments)


def test_request_contains_selected_norm_only_and_exact_v3_schema():
    result = _candidate(
        recognised_context=(RecognisedContext(1, "OCR только контекст", ("mixed_script",)),),
    )
    exported = json.dumps(asdict(result), ensure_ascii=False)
    assert SELECTED_TEXT in result.user_prompt
    assert "OCR только контекст" in result.user_prompt
    assert HIDDEN_TEXT not in exported
    assert SELECTED_TEXT not in result.system_prompt
    assert result.selected_label_count == 1
    assert json.loads(result.response_schema_json) == response_schema()
    assert "norm_citations" in result.response_schema_json
    assert not set(asdict(result)) & {"model_id", "max_output_tokens", "provider_mode"}


def test_digest_binds_pdf_and_complete_set_identity_even_when_prompt_is_same():
    first = _candidate()
    assert first == _candidate()
    changed_pdf = prepare_v3_request_candidate(
        _layer("АР. Ширина прохода 1,3 м."), _set_bytes(),
        expected_version_uid="ver_fixture",
        expected_set_sha256=first.set_sha256,
        expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
    )
    changed_hidden = _candidate(set_bytes=_set_bytes(hidden_text="ДРУГОЙ НЕВЫБРАННЫЙ АБЗАЦ"))
    assert first.request_sha256 != changed_pdf.request_sha256
    assert first.request_sha256 != changed_hidden.request_sha256
    assert first.user_prompt == changed_hidden.user_prompt
    assert len(first.request_sha256) == 64


@pytest.mark.parametrize("wrong", [
    {"expected_version_uid": "ver_other"},
    {"expected_snapshot_id": "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QQ"},
    {"expected_map_sha256": "c" * 64},
    {"expected_set_sha256": "d" * 64},
    {"recognised_context": (RecognisedContext(2, "чужая страница", ()),)},
])
def test_foreign_identity_or_context_refuses(wrong):
    with pytest.raises(V3RequestRefused):
        _candidate(**wrong)


def test_modified_set_bytes_refuse_before_request_creation():
    raw = _set_bytes()
    with pytest.raises(V3RequestRefused):
        prepare_v3_request_candidate(
            _layer(), raw.replace(b"N1", b"N2", 1),
            expected_version_uid="ver_fixture",
            expected_set_sha256=hashlib.sha256(raw).hexdigest(),
            expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
        )
