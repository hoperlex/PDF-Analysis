"""A complete recorded AR v2 output has one honest registry-bound stage result."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from auditmanager.analysis.engine.result import ArtifactRef, StageStatus
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_call import build_recorded_call_facts
from auditmanager.analysis.profiles.ar_v2.recorded_stage_result import (
    RecordedStageSealError, seal_recorded_v2_stage_result,
)
from tests.integration.analysis.test_ar_v2_recorded_artifact import (
    CALL, RUN, VERSION, _build, _prepared, _replay,
)


START = datetime(2026, 10, 16, 4, 0, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=2)


def _inputs(tmp_path: Path, *, truncated: bool = False, with_ocr: bool = False) -> dict:
    prepared = _prepared(with_ocr=with_ocr)
    replay = _replay(tmp_path, prepared, truncated=truncated)
    artifact = _build(prepared, replay)
    return {
        "artifact": artifact,
        "published_ref": ArtifactRef(
            artifact.role, "blob_" + "2" * 26,
            artifact.sha256, artifact.size_bytes, artifact.media_type,
        ),
        "call": build_recorded_call_facts(
            prepared=prepared, replay=replay, model_call_id=CALL,
        ),
        "prepared": prepared,
        "run_id": RUN, "version_uid": VERSION,
        "started_at": START, "finished_at": FINISH,
    }


def _mutate_document(inputs: dict, **updates) -> dict:
    document = json.loads(inputs["artifact"].payload)
    document.update(updates)
    payload = canonical_bytes(document)
    artifact = replace(inputs["artifact"], payload=payload, sha256=sha256_hex(payload))
    reference = replace(inputs["published_ref"], sha256=artifact.sha256,
                        size_bytes=artifact.size_bytes)
    return {**inputs, "artifact": artifact, "published_ref": reference}


def test_complete_replay_seals_exact_ref_call_and_registry_contract(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    result = seal_recorded_v2_stage_result(**inputs)
    document = result.to_document()
    assert result.status is StageStatus.SUCCEEDED
    assert result.stage_id == "text_analysis" and result.stage_version == "1.1.0"
    assert result.artifacts == (inputs["published_ref"],)
    assert document["metrics"] == {
        "provider_mode": "recorded", "model_call_count": 1,
        "input_tokens": 100, "output_tokens": 40, "latency_ms": 5,
    }
    assert "error" not in document and "cost_usd" not in document["metrics"]
    assert document["started_at"] == "2026-10-16T04:00:00Z"


def test_truncated_replay_cannot_claim_complete_stage(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, truncated=True)
    with pytest.raises(RecordedStageSealError, match="truncated_reply_needs_partial_coverage_policy"):
        seal_recorded_v2_stage_result(**inputs)


def test_ref_and_provenance_mismatch_fail_before_result(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    with pytest.raises(RecordedStageSealError, match="published_artifact_ref_mismatch"):
        seal_recorded_v2_stage_result(
            **{**inputs, "published_ref": replace(inputs["published_ref"], sha256="f" * 64)}
        )
    changed = _mutate_document(inputs, model_call_id="mc_" + "3" * 26)
    with pytest.raises(RecordedStageSealError, match="recorded_stage_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)
    changed = _mutate_document(inputs, profile_content_sha256="f" * 64)
    with pytest.raises(RecordedStageSealError, match="recorded_stage_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)
    with pytest.raises(RecordedStageSealError, match="recorded_stage_provenance_mismatch"):
        seal_recorded_v2_stage_result(**{
            **inputs,
            "call": replace(inputs["call"], request_sha256="f" * 64),
        })


def test_false_page_coverage_and_bad_times_are_refused(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    changed = _mutate_document(inputs, pages_analysed=[])
    with pytest.raises(RecordedStageSealError, match="recorded_source_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)
    with pytest.raises(RecordedStageSealError, match="stage_times_invalid"):
        seal_recorded_v2_stage_result(
            **{**inputs, "finished_at": START - timedelta(seconds=1)}
        )
    with pytest.raises(RecordedStageSealError, match="stage_times_invalid"):
        seal_recorded_v2_stage_result(
            **{**inputs, "started_at": START.replace(tzinfo=None)}
        )


def test_jointly_trimmed_artifact_pages_cannot_fake_complete_coverage(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, with_ocr=True)
    document = json.loads(inputs["artifact"].payload)
    assert len(document["page_sources"]) == 2
    changed = _mutate_document(
        inputs,
        page_sources=document["page_sources"][:1],
        pages_analysed=document["pages_analysed"][:1],
    )
    with pytest.raises(RecordedStageSealError, match="recorded_source_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)


def test_source_ref_and_textless_selection_drift_are_refused(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, with_ocr=True)
    source_artifacts = json.loads(inputs["artifact"].payload)["source_artifacts"]
    source_artifacts["text_layer"]["sha256"] = "f" * 64
    changed = _mutate_document(inputs, source_artifacts=source_artifacts)
    with pytest.raises(RecordedStageSealError, match="recorded_source_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)
    text_ref = replace(inputs["prepared"].text_layer_ref, sha256="f" * 64)
    prepared = replace(inputs["prepared"], text_layer_ref=text_ref)
    with pytest.raises(RecordedStageSealError, match="recorded_source_provenance_mismatch"):
        seal_recorded_v2_stage_result(**{**inputs, "prepared": prepared})
    changed = _mutate_document(inputs, textless_pages=[])
    with pytest.raises(RecordedStageSealError, match="recorded_source_provenance_mismatch"):
        seal_recorded_v2_stage_result(**changed)


def test_noncanonical_or_changed_bytes_cannot_be_sealed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    altered = replace(inputs["artifact"], payload=inputs["artifact"].payload + b" ")
    with pytest.raises(RecordedStageSealError, match="recorded_artifact_digest_mismatch"):
        seal_recorded_v2_stage_result(**{**inputs, "artifact": altered})
    altered = replace(altered, sha256=sha256_hex(altered.payload))
    ref = replace(inputs["published_ref"], sha256=altered.sha256,
                  size_bytes=altered.size_bytes)
    with pytest.raises(RecordedStageSealError, match="recorded_artifact_not_canonical"):
        seal_recorded_v2_stage_result(**{**inputs, "artifact": altered, "published_ref": ref})
