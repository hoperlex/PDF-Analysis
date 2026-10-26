"""Recorded AR v2 observation bytes preserve provenance and diagnostic partition."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.merge_input import prepare_merge
from auditmanager.analysis.profiles.ar_v2.proposal_grounding import GroundedProposal
from auditmanager.analysis.profiles.ar_v2.recorded_artifact import (
    ARTIFACT_ROLE,
    ARTIFACT_VERSION,
    RecordedArtifactError,
    build_recorded_observation_artifact,
    read_recorded_merge_input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_input import prepare_recorded_v2_input
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.analysis.profiles.ar_v2.recorded_response import replay_recorded_response
from auditmanager.analysis.profiles.ar_shared.v2_identities import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.analysis.text.anchors import ResolvedAnchor
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.findings.artifacts import ObservationSet
from auditmanager.shared.identity import ModelCallId, RunId
from auditmanager.storage.public import derive_blob_id


VERSION = "ver_01M2545JSD15ETSNNV904X991J"
MODEL = "fixture/ar-v2-recorded"
RUN = "run_01M2545JSD15ETSNNV904X991J"
CALL = "mc_01M2545JSD15ETSNNV904X991J"


def _prepared(*, with_ocr: bool = False):
    text = "Стена: 200 мм"
    pages = [{"page_number": 1, "char_start": 0,
              "char_end": len(text), "text": text}]
    if with_ocr:
        pages.append({"page_number": 2, "char_start": len(text),
                      "char_end": len(text), "text": ""})
    document = {
        "artifact_role": "prepared.text_layer", "artifact_version": "1.0.0",
        "version_uid": VERSION, "normalization": {"id": "NFC"},
        "pages": pages,
        "total_char_count": len(text),
    }
    payload = canonical_bytes(document)
    reference = ArtifactRef(
        role="prepared.text_layer", blob_id="blob_" + "0" * 26,
        sha256=sha256_hex(payload), size_bytes=len(payload),
        media_type="application/json",
    )
    recognised = None
    recognised_ref = None
    if with_ocr:
        recognised = {
            "artifact_role": "prepared.recognised_text", "artifact_version": "1.0.0",
            "version_uid": VERSION, "results_sha256": "a" * 64,
            "entries": [{
                "portal_block_id": "blk_ocr", "page_number": 2,
                "kind": "recognised_text", "quote_source": "recognised",
                "text": "OCR: фасад", "flags": [],
            }],
        }
        recognised_payload = canonical_bytes(recognised)
        recognised_ref = ArtifactRef(
            role="prepared.recognised_text", blob_id="blob_" + "1" * 26,
            sha256=sha256_hex(recognised_payload), size_bytes=len(recognised_payload),
            media_type="application/json",
        )
    return prepare_recorded_v2_input(
        version_uid=VERSION, textless_pages=(2,) if with_ocr else None,
        text_layer_document=document, text_layer_ref=reference,
        text_layer_read_sha256=reference.sha256,
        recognised_document=recognised, recognised_ref=recognised_ref,
        recognised_read_sha256=None if recognised_ref is None else recognised_ref.sha256,
        analysis_profile_id=PROFILE_ID, prompt_bundle_id=PROMPT_BUNDLE_ID,
        fixture_model_id=MODEL,
        settings=RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
    )


def _replay(tmp_path: Path, prepared, *, truncated: bool = False, ocr_only: bool = False):
    proposals = [
        {
            "category": "dimensions", "finding_text": "Размер стены",
            "recommendation_text": "Проверить", "proposed_severity": "operational",
            "evidence": [{"page_number": 1, "quote": "Стена: 200 мм"}],
        },
        {
            "category": "dimensions", "finding_text": "Нет цитаты",
            "recommendation_text": "Проверить", "proposed_severity": "recommendation",
            "evidence": [{"page_number": 1, "quote": "Несуществующий текст"}],
        },
        {"bad": "element"},
    ]
    if ocr_only:
        proposals = [{
            "category": "facade", "finding_text": "OCR claim",
            "recommendation_text": "Проверить", "proposed_severity": "recommendation",
            "evidence": [{"page_number": 2, "quote": "OCR: фасад"}],
        }]
    output = json.dumps({"observations": proposals}, ensure_ascii=False)
    recording = recording_document(
        request=prepared.request, output_text=output,
        stop_reason="max_tokens" if truncated else "end_turn",
        input_tokens=100, output_tokens=40, latency_ms=5, note="offline fixture",
    )
    (tmp_path / f"{prepared.request_sha256}.json").write_text(
        json.dumps(recording, ensure_ascii=False), encoding="utf-8",
    )
    return replay_recorded_response(
        prepared=prepared, adapter=RecordedAdapter(tmp_path),
        expected_request_sha256=prepared.request_sha256,
        expected_model_id=MODEL,
        expected_source_binding_sha256=prepared.source_binding_sha256,
    )


def _build(prepared, replay, **changes):
    arguments = {
        "prepared": prepared, "replay": replay,
        "run_id": RUN, "model_call_id": CALL,
        "analysis_profile_id": str(PROFILE_ID),
        "prompt_bundle_id": str(PROMPT_BUNDLE_ID),
    }
    arguments.update(changes)
    return build_recorded_observation_artifact(**arguments)


def _read_saved(payload: bytes):
    digest = sha256_hex(payload)
    reference = ArtifactRef(
        ARTIFACT_ROLE, str(derive_blob_id(sha256=digest, size=len(payload))),
        digest, len(payload), "application/json",
    )

    class Store:
        def read(self, _blob_id, *, verify: bool = True):
            assert verify
            return payload

    return read_recorded_merge_input(
        Store(), reference, run_id=RUN, version_uid=VERSION,
        analysis_profile_id=str(PROFILE_ID), prompt_bundle_id=str(PROMPT_BUNDLE_ID),
    )


def test_saved_reader_retains_typed_proposals_diagnostics_and_call_facts(tmp_path: Path) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    saved = _read_saved(_build(prepared, replay).payload)
    assert saved.model_id == MODEL
    assert saved.model_call_id == CALL
    assert saved.request_sha256 == replay.request_sha256
    assert saved.response_sha256 == replay.response_sha256
    assert saved.source_binding_sha256 == prepared.source_binding_sha256
    assert saved.grounding.accepted[0].proposal.finding_text == "Размер стены"
    assert saved.grounding.accepted[0].proposal.proposed_severity == "operational"
    assert saved.grounding.accepted[0].evidence[0].block_id is None
    assert saved.grounding.rejected[0].failures[0].reason == "quotation_absent"
    assert saved.grounding.malformed_count == 1


@pytest.mark.parametrize("field", ["evidence_ordinal", "page_number", "quote"])
def test_nullable_rejected_diagnostic_fails_closed(tmp_path: Path, field: str) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    document = json.loads(_build(prepared, replay).payload)
    document["diagnostics"]["rejected"][0]["failures"][0][field] = None
    with pytest.raises(RecordedArtifactError, match="recorded_diagnostics_invalid"):
        _read_saved(canonical_bytes(document))


def test_canonical_bytes_are_gate_readable_and_keep_all_diagnostics(tmp_path: Path) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    built = _build(prepared, replay)
    document = json.loads(built.payload)
    assert built.role == ARTIFACT_ROLE == "analysis.text_observations"
    assert built.version == ARTIFACT_VERSION == "2.0.0"
    assert built.media_type == "application/json"
    assert built.sha256 == sha256_hex(built.payload)
    assert built.size_bytes == len(built.payload)
    assert built.payload == canonical_bytes(document)
    assert document["request_sha256"] == replay.request_sha256
    assert document["source_binding_sha256"] == replay.source_binding_sha256
    assert document["response_sha256"] == replay.response_sha256
    assert document["source_artifacts"]["text_layer"] == prepared.text_layer_ref.to_document()
    assert document["source_artifacts"]["recognised_text"] is None
    assert document["model_call_id"] == CALL
    assert document["provider_mode"] == "recorded"
    assert document["pages_analysed"] == [1]
    assert document["page_sources"] == [{"page_number": 1, "char_start": 0, "char_end": 13}]
    assert len(document["observations"]) == 1
    assert document["observations"][0]["source_proposal_ordinal"] == 0
    assert document["observations"][0]["proposed_severity"] == "operational"
    assert document["diagnostics"]["rejected"][0]["source_proposal_ordinal"] == 1
    assert document["diagnostics"]["rejected"][0]["failures"][0]["reason"] == "quotation_absent"
    assert document["diagnostics"]["malformed_count"] == 1
    assert document["diagnostics"]["salvaged"] is False
    assert document["diagnostics"]["truncated"] is False
    gate_input = ObservationSet.from_artifact(document)
    assert len(gate_input.observations) == 1
    assert gate_input.observations[0].model_call_id == CALL
    assert gate_input.observations[0].evidence[0].quote == "Стена: 200 мм"


def test_role_and_media_type_match_frozen_text_analysis_output() -> None:
    root = Path(__file__).resolve().parents[3]
    registry = json.loads((root / "contracts/analysis/v1/stage-registry.json").read_text())
    stages = registry["stages"]
    stage = next(item for item in stages if item["stage_id"] == "text_analysis")
    output = next(item for item in stage["produced_outputs"] if item["role"] == ARTIFACT_ROLE)
    assert stage["stage_version"] == "1.1.0"
    assert any(
        item["role"] == "norms.snapshot" and item["required"] is False
        for item in stage["required_inputs"]
    )
    assert output["media_type"] == "application/json"
    assert output["required"] is True


def test_equal_inputs_yield_equal_bytes_and_id_changes_change_hash(tmp_path: Path) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    first = _build(prepared, replay)
    assert _build(prepared, replay) == first
    other_run = _build(prepared, replay, run_id=str(RunId.new()))
    other_call = _build(prepared, replay, model_call_id=str(ModelCallId.new()))
    assert other_run.sha256 != first.sha256
    assert other_call.sha256 != first.sha256


def test_truncation_and_salvage_are_diagnostic_not_stage_status(tmp_path: Path) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared, truncated=True)
    document = json.loads(_build(prepared, replay).payload)
    assert document["diagnostics"]["truncated"] is True
    assert document["diagnostics"]["salvaged"] is True
    assert len(document["observations"]) == 1
    assert "status" not in document


def test_marked_ocr_source_is_retained_but_ocr_only_quote_is_diagnostic(tmp_path: Path) -> None:
    prepared = _prepared(with_ocr=True)
    replay = _replay(tmp_path, prepared, ocr_only=True)
    document = json.loads(_build(prepared, replay).payload)
    assert document["source_artifacts"]["recognised_text"] == prepared.recognised_ref.to_document()
    assert document["textless_pages"] == [2]
    assert document["pages_analysed"] == [1, 2]
    assert document["observations"] == []
    assert document["diagnostics"]["rejected"][0]["failures"][0]["reason"] == "quote_in_recognised_text"


@pytest.mark.parametrize("field", [
    "request_sha256", "source_binding_sha256", "response_sha256", "provider_mode",
])
def test_replay_provenance_mismatch_is_refused(tmp_path: Path, field: str) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    value = "0" * 64 if field != "provider_mode" else "live"
    with pytest.raises(RecordedArtifactError):
        _build(prepared, replace(replay, **{field: value}))


def test_forged_merge_and_pdf_anchor_are_refused(tmp_path: Path) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    wrong_merge = replace(replay.finished.merge, artifact={
        "artifact_role": "findings.merged", "artifact_version": "1.0.0", "groups": [],
    })
    with pytest.raises(RecordedArtifactError, match="merge_preparation_mismatch"):
        _build(prepared, replace(replay, finished=replace(replay.finished, merge=wrong_merge)))

    accepted = replay.finished.grounding.accepted[0]
    forged_anchor = ResolvedAnchor(1, "Стена: 200 мм", 1, 14)
    forged = GroundedProposal(accepted.proposal_ordinal, accepted.proposal, (forged_anchor,))
    grounding = replace(replay.finished.grounding, accepted=(forged,))
    finished = replace(replay.finished, grounding=grounding, merge=prepare_merge(grounding))
    with pytest.raises(RecordedArtifactError, match="evidence_not_grounded_in_pdf"):
        _build(prepared, replace(replay, finished=finished))


@pytest.mark.parametrize("changes", [
    {"run_id": VERSION},
    {"model_call_id": RUN},
    {"analysis_profile_id": "ap_01M2545JSD15ETSNNV904X991J"},
])
def test_wrong_identity_or_registration_is_refused(tmp_path: Path, changes: dict) -> None:
    prepared = _prepared()
    replay = _replay(tmp_path, prepared)
    with pytest.raises(ValueError):
        _build(prepared, replay, **changes)
