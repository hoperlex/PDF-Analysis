"""W56b TEXT windows start only from matching supplied artifact bytes."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.text.chunk_preflight import ChunkPreflightError
from auditmanager.analysis.text.source_bytes import (
    SuppliedTextSourceRefused,
    check_supplied_text_window_bytes,
)


VERSION = "ver_01M2545JSD15ETSNNV904X991J"
BLOB = "blob_01M2545JSD15ETSNNV904X991J"


def _document(*texts: str) -> dict:
    pages = []
    offset = 0
    for number, body in enumerate(texts, start=1):
        pages.append({
            "page_number": number, "char_start": offset,
            "char_end": offset + len(body), "text": body,
        })
        offset += len(body)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "extractor": {
            "name": "fixture", "version": "1.0.0", "options_sha256": "a" * 64,
        },
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset,
        "pages": pages,
    }


def _source(document: dict) -> tuple[ArtifactRef, bytes]:
    payload = canonical_bytes(document)
    return ArtifactRef(
        role="prepared.text_layer", blob_id=BLOB, sha256=sha256_hex(payload),
        size_bytes=len(payload), media_type="application/json",
    ), payload


def _check(ref: ArtifactRef, payload: bytes, *, count: int = 3, ceiling: int = 2):
    return check_supplied_text_window_bytes(
        version_uid=VERSION,
        expected_page_count=count,
        text_layer_ref=ref,
        supplied_bytes=payload,
        max_chunk_characters=ceiling,
    )


def test_verified_russian_source_keeps_unicode_offsets_and_blank_page() -> None:
    ref, payload = _source(_document("А😀", "", "БВ"))

    checked = _check(ref, payload)

    assert checked.text_layer_ref == ref
    assert checked.text_layer.document_text == "А😀БВ"
    assert [(w.first_page, w.last_page, w.char_start, w.char_end)
            for w in checked.windows] == [(1, 2, 0, 2), (3, 3, 2, 4)]
    assert checked == _check(ref, payload)


@pytest.mark.parametrize("mutation", ["different_bytes", "size", "digest", "role", "media"])
def test_reference_and_supplied_bytes_must_agree(mutation: str) -> None:
    ref, payload = _source(_document("А😀", "", "БВ"))
    if mutation == "different_bytes":
        payload = payload[:-1] + b" "
    elif mutation == "size":
        ref = replace(ref, size_bytes=ref.size_bytes + 1)
    elif mutation == "digest":
        ref = replace(ref, sha256="b" * 64)
    elif mutation == "role":
        ref = replace(ref, role="prepared.page_inventory")
    else:
        ref = replace(ref, media_type="text/plain")
    with pytest.raises(SuppliedTextSourceRefused, match="supplied_text_bytes_mismatch"):
        _check(ref, payload)


def test_noncanonical_json_refuses_even_with_matching_digest() -> None:
    document = _document("А😀", "", "БВ")
    payload = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    ref = replace(_source(document)[0], sha256=sha256_hex(payload), size_bytes=len(payload))
    with pytest.raises(SuppliedTextSourceRefused, match="text_layer_not_canonical_json"):
        _check(ref, payload)


@pytest.mark.parametrize("mutation", ["page_string", "offset_bool", "foreign_version", "bad_total"])
def test_self_consistent_bytes_still_need_valid_text_layer(mutation: str) -> None:
    document = _document("А😀", "", "БВ")
    if mutation == "page_string":
        document["pages"][0]["page_number"] = "1"
    elif mutation == "offset_bool":
        document["pages"][0]["char_start"] = False
    elif mutation == "foreign_version":
        document["version_uid"] = "ver_01M2545JSD15ETSNNV904X991K"
    else:
        document["total_char_count"] += 1
    ref, payload = _source(document)
    with pytest.raises(SuppliedTextSourceRefused):
        _check(ref, payload)


def test_frozen_page_count_and_later_oversized_page_refuse_whole_plan() -> None:
    ref, payload = _source(_document("А😀", "", "БВГ"))
    with pytest.raises(SuppliedTextSourceRefused, match="text_layer_page_count_or_version_mismatch"):
        _check(ref, payload, count=2)
    with pytest.raises(ChunkPreflightError, match="page_exceeds_limit") as caught:
        _check(ref, payload)
    assert caught.value.page_number == 3


def test_blank_source_refuses_before_any_window() -> None:
    ref, payload = _source(_document("", "", ""))
    with pytest.raises(ChunkPreflightError, match="empty_text_layer"):
        _check(ref, payload)
