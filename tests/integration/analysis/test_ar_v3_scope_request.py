"""Pure scope-to-canonical-set request binding; no Run or provider call."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

import auditmanager.analysis.profiles.ar_v3.request_candidate as request_module
from auditmanager.analysis.profiles.ar_v3.request_candidate import (
    V3RequestRefused,
    prepare_v3_scoped_request_candidate,
)
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.profiles.ar_v3.set_input import parse_v3_set_input
from auditmanager.analysis.text.textlayer import Page, TextLayer


DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
PARAGRAPH = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
SNAPSHOT = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
MAP_SHA = "a" * 64
TEXT = "Минимальная ширина прохода составляет 1,4 м"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _set_bytes(item_ids: tuple[str, ...]) -> bytes:
    source = {
        "norm_document_id": DOCUMENT, "norm_paragraph_id": PARAGRAPH,
        "designation": "СП 54", "title": "Жилые здания", "ordinal": 0,
        "clause_number": "7.1.4", "page_label": "7", "text": TEXT,
        "text_sha256": hashlib.sha256(TEXT.encode("utf-8")).hexdigest(),
    }
    part = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [
            dict(source, item_id=item_id, label=f"N{index}")
            for index, item_id in enumerate(item_ids, 1)
        ],
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
        "rebinding_paragraphs": [source],
    })


def _layer() -> TextLayer:
    text = "АР. Ширина прохода 1,2 м."
    return TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)


def _candidate(
    raw: bytes, scope_id: str, *, composition_sha256: str | None = None,
):
    digest = (composition_sha256 if composition_sha256 is not None
              else scope_membership(scope_id).composition_sha256)
    return prepare_v3_scoped_request_candidate(
        _layer(), raw, expected_version_uid="ver_fixture",
        expected_set_sha256=hashlib.sha256(raw).hexdigest(),
        expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
        scope_id=scope_id, expected_composition_sha256=digest,
    )


def test_canonical_parser_retains_exact_item_order_and_scopes_change_request_digest() -> None:
    first_scope = scope_membership("F1")
    second_scope = scope_membership("F2")
    first_set = _set_bytes(first_scope.item_ids)
    second_set = _set_bytes(second_scope.item_ids)
    parsed = parse_v3_set_input(
        first_set, expected_sha256=hashlib.sha256(first_set).hexdigest(),
        expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
    )
    assert parsed.selected_item_ids == ("C01", "C02", "C03")
    first = _candidate(first_set, "F1")
    second = _candidate(second_set, "F2")
    assert first == _candidate(first_set, "F1")
    assert first.scope_id == "F1" and second.scope_id == "F2"
    assert first.composition_sha256 == second.composition_sha256 == first_scope.composition_sha256
    assert first.item_ids == first_scope.item_ids
    assert second.item_ids == second_scope.item_ids
    assert first.request_sha256 != second.request_sha256
    assert TEXT in first.user_prompt and TEXT in second.user_prompt


def test_composition_revision_changes_digest_with_identical_set_and_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_membership = scope_membership("F1")
    raw = _set_bytes(original_membership.item_ids)
    original = _candidate(raw, "F1")
    revised_membership = replace(original_membership, composition_sha256="c" * 64)
    monkeypatch.setattr(request_module, "scope_membership", lambda scope_id: revised_membership)
    revised = _candidate(raw, "F1", composition_sha256=revised_membership.composition_sha256)
    assert revised.set_sha256 == original.set_sha256
    assert revised.user_prompt == original.user_prompt
    assert revised.item_ids == original.item_ids
    assert revised.request_sha256 != original.request_sha256


@pytest.mark.parametrize(
    ("item_ids", "scope_id", "digest"),
    [
        (("C01", "C02", "C04"), "F1", None),   # mixed F1/F2 set
        (("C03", "C02", "C01"), "F1", None),   # right IDs, wrong order
        (("C01", "C02"), "F1", None),            # missing C03
        (("C01", "C02", "C03"), "F2", None),   # foreign scope
        (("C01", "C02", "C03"), "F1", "0" * 64),  # stale composition
        (("C01", "C02", "C03"), "Z9", "0" * 64),  # unknown scope
    ],
)
def test_wrong_set_scope_or_digest_refuses_before_prompt_material(
    monkeypatch: pytest.MonkeyPatch,
    item_ids: tuple[str, ...], scope_id: str, digest: str | None,
) -> None:
    def should_not_render(*args: object, **kwargs: object) -> None:
        raise AssertionError("provider-facing prompt material was attempted")

    monkeypatch.setattr(request_module, "prepare_v3_prompt", should_not_render)
    with pytest.raises(V3RequestRefused):
        _candidate(_set_bytes(item_ids), scope_id, composition_sha256=digest)


def test_rehashed_substituted_item_ids_still_refuse_and_untrusted_sha_refuses() -> None:
    raw = _set_bytes(("C01", "C02", "C04"))
    with pytest.raises(V3RequestRefused, match="scope_set_item_mismatch"):
        _candidate(raw, "F1")
    with pytest.raises(V3RequestRefused, match="set_input_identity_invalid"):
        prepare_v3_scoped_request_candidate(
            _layer(), raw, expected_version_uid="ver_fixture",
            expected_set_sha256="0" * 64,
            expected_snapshot_id=SNAPSHOT, expected_map_sha256=MAP_SHA,
            scope_id="F1",
            expected_composition_sha256=scope_membership("F1").composition_sha256,
        )
