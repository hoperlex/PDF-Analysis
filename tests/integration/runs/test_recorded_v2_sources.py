"""Saved AR v2 source references and Blob reads bind one offline request."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.public import (
    ArtifactRef,
    ProviderConfig,
    ProviderMode,
    RecordedGenerationSettings,
)
from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.runs.recorded_v2_sources import load_recorded_v2_input
from auditmanager.runs.repository import RunRow, StageResultRow
from auditmanager.shared.errors import DomainError, ErrorCode


VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991J"
RUN = "run_01M2545JSD15ETSNNV904X991J"


class _Adapter:
    provider_mode = ProviderMode.RECORDED

    def complete(self, _request: object) -> None:
        raise AssertionError("source read must never replay a recording")


class _Runs:
    def __init__(self, run: RunRow, stage: StageResultRow) -> None:
        self.run = run
        self.stage = stage
        self.events: list[str] = []

    def get(self, _session: object, run_id: str) -> RunRow:
        self.events.append("run")
        assert run_id == RUN
        return self.run

    def stage_results(self, _session: object, run_id: str) -> tuple[StageResultRow, ...]:
        self.events.append("stage")
        assert run_id == RUN
        return (self.stage,)


class _Documents:
    def __init__(self, *, textless_pages: tuple[int, ...] | None = (2,),
                 project_uid: str = PROJECT) -> None:
        self.version = SimpleNamespace(
            version_uid=VERSION, project_uid=project_uid,
            textless_pages=textless_pages, page_count=2,
        )
        self.events: list[str] = []

    def get_version(self, _session: object, version_uid: object) -> Any:
        self.events.append("version")
        assert str(version_uid) == VERSION
        return self.version


class _Store:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = blobs
        self.reads: list[str] = []

    def read(self, blob_id: object, *, verify: bool) -> bytes:
        assert verify is True
        key = str(blob_id)
        self.reads.append(key)
        return self.blobs[key]


def _run() -> RunRow:
    return RunRow(
        run_id=RUN, project_uid=PROJECT, version_uid=VERSION, state="running",
        analysis_profile_id=str(PROFILE_ID), prompt_bundle_id=str(PROMPT_BUNDLE_ID),
        norms_snapshot_id=None, provider_mode="recorded", frozen_input_digest="a" * 64,
        command_id=None, terminal_reason=None, terminal_detail=None,
        interrupted_reason=None, degradation_set=(),
        created_at=datetime(2026, 10, 15, tzinfo=timezone.utc), terminal_at=None,
    )


def _reference(document: dict[str, Any], role: str, digit: str) -> tuple[ArtifactRef, bytes]:
    payload = canonical_bytes(document)
    return ArtifactRef(
        role, "blob_" + digit * 26, sha256_hex(payload), len(payload), "application/json"
    ), payload


def _fixtures(*, portal: bool = True) -> tuple[_Runs, _Documents, _Store]:
    text = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": VERSION, "normalization": {"id": "NFC"},
        "pages": [
            {"page_number": 1, "char_start": 0, "char_end": 13, "text": "Стена: 200 мм"},
            {"page_number": 2, "char_start": 13, "char_end": 13, "text": ""},
        ],
        "total_char_count": 13,
    }
    ocr = {
        "artifact_role": "prepared.recognised_text", "artifact_version": "1.0.0",
        "version_uid": VERSION, "results_sha256": "b" * 64,
        "entries": [{
            "portal_block_id": "blk_ocr", "page_number": 2,
            "kind": "recognised_text", "quote_source": "recognised",
            "text": "распознано с листа 2", "flags": [],
        }],
    }
    inventory_ref, _ = _reference({"artifact_role": "prepared.page_inventory"},
                                  "prepared.page_inventory", "0")
    text_ref, text_bytes = _reference(text, "prepared.text_layer", "1")
    ocr_ref, ocr_bytes = _reference(ocr, "prepared.recognised_text", "2")
    artifacts = (inventory_ref.to_document(), text_ref.to_document())
    blobs = {text_ref.blob_id: text_bytes}
    if portal:
        artifacts += (ocr_ref.to_document(),)
        blobs[ocr_ref.blob_id] = ocr_bytes
    stage = StageResultRow(
        stage_id="source_preparation", stage_version="1.0.0", status="succeeded",
        artifacts=artifacts, metrics={}, error=None,
    )
    return _Runs(_run(), stage), _Documents(textless_pages=(2,) if portal else None), _Store(blobs)


def _load(runs: _Runs, documents: _Documents, store: _Store):
    return load_recorded_v2_input(
        object(), run_id=RUN, blob_store=store, adapter=_Adapter(),
        provider_config=ProviderConfig(
            mode=ProviderMode.RECORDED, model_id="offline-candidate",
            run_cost_ceiling_usd=1.0, api_key=None, ceiling_is_explicit=False,
        ),
        fixture_model_id="fixture/ar-v2-recorded",
        settings=RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
        runs=runs, documents=documents,
    )


def test_saved_portal_source_reads_exact_refs_and_retains_both_digests() -> None:
    runs, documents, store = _fixtures()
    result = _load(runs, documents, store)
    again = _load(runs, documents, store)

    assert runs.events == ["run", "stage", "run", "stage"]
    assert documents.events == ["version", "version"]
    assert store.reads == ["blob_" + "1" * 26, "blob_" + "2" * 26] * 2
    assert (result.request_sha256, result.source_binding_sha256) == (
        again.request_sha256, again.source_binding_sha256,
    )
    assert result.request_sha256 != result.source_binding_sha256
    assert result.textless_pages == (2,)
    assert tuple(item.page_number for item in result.recognised_context) == (2,)


def test_legacy_pdf_without_portal_reads_text_only() -> None:
    runs, documents, store = _fixtures(portal=False)
    result = _load(runs, documents, store)
    assert result.recognised_ref is None
    assert result.textless_pages is None
    assert len(store.reads) == 1


@pytest.mark.parametrize("change", ["profile", "mode", "state"])
def test_run_preflight_refuses_before_version_or_blob_read(change: str) -> None:
    runs, documents, store = _fixtures()
    if change == "profile":
        runs.run = replace(runs.run, analysis_profile_id="ap_01M2545JSD15ETSNNV904X991J")
    elif change == "mode":
        runs.run = replace(runs.run, provider_mode="live")
    else:
        runs.run = replace(runs.run, state="published")
    with pytest.raises(DomainError) as error:
        _load(runs, documents, store)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert documents.events == []
    assert store.reads == []


def test_wrong_project_refuses_before_stage_or_blob_read() -> None:
    runs, documents, store = _fixtures()
    documents.version.project_uid = "prj_01M2545JSD15ETSNNV904X991K"
    with pytest.raises(DomainError, match="saved recorded AR v2 source"):
        _load(runs, documents, store)
    assert runs.events == ["run"]
    assert store.reads == []


@pytest.mark.parametrize("change", ["missing_ocr", "duplicate_text", "failed_stage", "wrong_version"])
def test_stage_or_portal_mismatch_refuses_before_blob_read(change: str) -> None:
    runs, documents, store = _fixtures()
    if change == "missing_ocr":
        runs.stage = replace(runs.stage, artifacts=runs.stage.artifacts[:-1])
    elif change == "duplicate_text":
        runs.stage = replace(runs.stage, artifacts=(*runs.stage.artifacts, runs.stage.artifacts[1]))
    elif change == "failed_stage":
        runs.stage = replace(runs.stage, status="failed")
    else:
        documents.version.version_uid = "ver_01M2545JSD15ETSNNV904X991K"
    with pytest.raises(DomainError) as error:
        _load(runs, documents, store)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert store.reads == []


def test_changed_published_blob_bytes_refuse_the_saved_reference() -> None:
    runs, documents, store = _fixtures()
    store.blobs["blob_" + "1" * 26] += b" "
    with pytest.raises(ValueError, match="artifact_digest_mismatch"):
        _load(runs, documents, store)
    assert len(store.reads) == 2


def test_incomplete_page_provenance_refuses_after_verified_reads() -> None:
    runs, documents, store = _fixtures()
    documents.version.page_count = 3
    with pytest.raises(DomainError) as error:
        _load(runs, documents, store)
    assert error.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.value.detail_fields["reason"] == "source_page_count_mismatch"
    assert len(store.reads) == 2


def test_unexpected_ocr_on_legacy_pdf_refuses_before_blob_read() -> None:
    runs, _documents, store = _fixtures()
    documents = _Documents(textless_pages=None)
    with pytest.raises(DomainError) as error:
        _load(runs, documents, store)
    assert error.value.detail_fields["reason"] == "recognised_reference_mismatch"
    assert store.reads == []


def test_duplicate_source_stage_result_refuses_before_blob_read() -> None:
    runs, documents, store = _fixtures()
    stage_results = runs.stage_results

    def duplicated(session: object, run_id: str) -> tuple[StageResultRow, ...]:
        return stage_results(session, run_id) * 2

    runs.stage_results = duplicated  # type: ignore[method-assign]
    with pytest.raises(DomainError) as error:
        _load(runs, documents, store)
    assert error.value.detail_fields["reason"] == "source_stage_result_missing_or_duplicate"
    assert store.reads == []
