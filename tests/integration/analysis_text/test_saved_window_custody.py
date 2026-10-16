"""Supplied run-scoped source refs must select the exact W56b TEXT Blob."""

from __future__ import annotations

from dataclasses import replace

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.text.chunk_preflight import ChunkPreflightError
from auditmanager.analysis.text.saved_window_custody import (
    RunScopedTextStage,
    SavedTextCustodyRefused,
    check_run_text_window_input,
    select_run_text_layer_ref,
)


RUN = "run_01M2545JSD15ETSNNV904X991J"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"


def _reference(role: str, blob_suffix: str, payload: bytes) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        blob_id="blob_01M2545JSD15ETSNNV904X991" + blob_suffix,
        sha256=sha256_hex(payload),
        size_bytes=len(payload),
        media_type="application/json",
    )


def _source(*texts: str) -> tuple[RunScopedTextStage, ArtifactRef, bytes]:
    pages = []
    offset = 0
    for number, body in enumerate(texts, start=1):
        pages.append({
            "page_number": number,
            "char_start": offset,
            "char_end": offset + len(body),
            "text": body,
        })
        offset += len(body)
    payload = canonical_bytes({
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "extractor": {
            "name": "fixture", "version": "1.0.0", "options_sha256": "a" * 64,
        },
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset,
        "pages": pages,
    })
    inventory = _reference("prepared.page_inventory", "K", b"{}")
    text = _reference("prepared.text_layer", "J", payload)
    stage = RunScopedTextStage(
        run_id=RUN,
        stage_id="source_preparation",
        stage_version="1.0.0",
        status="succeeded",
        artifacts=(inventory.to_document(), text.to_document()),
    )
    return stage, text, payload


def _check(stage: RunScopedTextStage, payload: bytes, *, count: int = 3, ceiling: int = 2):
    return check_run_text_window_input(
        run_id=RUN,
        version_uid=VERSION,
        expected_page_count=count,
        stage=stage,
        supplied_text_bytes=payload,
        max_chunk_characters=ceiling,
    )


def test_select_exact_stage_reference_then_bind_supplied_unicode_bytes() -> None:
    stage, text_ref, payload = _source("А😀", "", "БВ")
    recognised = _reference("prepared.recognised_text", "M", b"{}")
    stage = replace(stage, artifacts=(*stage.artifacts, recognised.to_document()))

    assert select_run_text_layer_ref(run_id=RUN, stage=stage) == text_ref
    bound = _check(stage, payload)

    assert bound.run_id == RUN
    assert bound.source.text_layer_ref == text_ref
    assert bound.source.text_layer.document_text == "А😀БВ"
    assert [(window.first_page, window.last_page, window.char_start, window.char_end)
            for window in bound.source.windows] == [(1, 2, 0, 2), (3, 3, 2, 4)]
    assert bound == _check(stage, payload)


@pytest.mark.parametrize("change", ["foreign_run", "wrong_stage", "wrong_version", "partial"])
def test_wrong_stage_identity_or_status_refuses(change: str) -> None:
    stage, _, _ = _source("А😀", "", "БВ")
    changes = {
        "foreign_run": {"run_id": "run_01M2545JSD15ETSNNV904X991K"},
        "wrong_stage": {"stage_id": "text_analysis"},
        "wrong_version": {"stage_version": "9.9.9"},
        "partial": {"status": "partial"},
    }
    with pytest.raises(SavedTextCustodyRefused, match="saved_stage_identity_or_status_invalid"):
        select_run_text_layer_ref(run_id=RUN, stage=replace(stage, **changes[change]))


@pytest.mark.parametrize("change", ["missing", "duplicate_role", "duplicate_blob", "extra_role", "bad_media", "zero_size"])
def test_saved_artifact_set_must_be_complete_and_unambiguous(change: str) -> None:
    stage, text_ref, _ = _source("А😀", "", "БВ")
    inventory, text = stage.artifacts
    if change == "missing":
        artifacts = (inventory,)
    elif change == "duplicate_role":
        artifacts = (inventory, text, text)
    elif change == "duplicate_blob":
        artifacts = (inventory, {**text, "blob_id": inventory["blob_id"]})
    elif change == "extra_role":
        artifacts = (inventory, text, {**text_ref.to_document(), "role": "geometry.block_index"})
    elif change == "bad_media":
        artifacts = (inventory, {**text, "media_type": "text/plain"})
    else:
        artifacts = (inventory, {**text, "size_bytes": 0})
    with pytest.raises(SavedTextCustodyRefused):
        select_run_text_layer_ref(run_id=RUN, stage=replace(stage, artifacts=artifacts))


def test_corrupt_or_foreign_supplied_text_refuses_after_stage_selection() -> None:
    stage, _, payload = _source("А😀", "", "БВ")
    with pytest.raises(SavedTextCustodyRefused, match="supplied_text_source_invalid"):
        _check(stage, payload[:-1] + b" ")
    with pytest.raises(SavedTextCustodyRefused, match="supplied_text_source_invalid"):
        _check(stage, payload, count=2)


def test_oversized_later_page_keeps_explicit_page_number() -> None:
    stage, _, payload = _source("А😀", "", "БВГ")
    with pytest.raises(ChunkPreflightError, match="page_exceeds_limit") as caught:
        _check(stage, payload)
    assert caught.value.page_number == 3
