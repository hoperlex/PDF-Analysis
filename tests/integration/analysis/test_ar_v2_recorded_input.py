"""The AR v2 offline request binds only exact PDF and marked OCR sources."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import canonical_bytes, sha256_hex
from auditmanager.analysis.profiles.ar_v2.recorded_input import (
    PdfPageSource,
    RecordedInputError,
    prepare_recorded_v2_input,
)
from auditmanager.analysis.profiles.ar_v2.recorded_request import RecordedGenerationSettings
from auditmanager.analysis.profiles.ar_v2.registered import PROFILE_ID, PROMPT_BUNDLE_ID
from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContextError


VERSION = "ver_01M2545JSD15ETSNNV904X991J"


def _reference(document: dict[str, Any], *, role: str, suffix: str) -> ArtifactRef:
    payload = canonical_bytes(document)
    return ArtifactRef(
        role=role, blob_id="blob_" + suffix * 26,
        sha256=sha256_hex(payload), size_bytes=len(payload), media_type="application/json",
    )


def _sources() -> tuple[dict[str, Any], ArtifactRef, dict[str, Any], ArtifactRef]:
    pdf = {
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
        "version_uid": VERSION, "results_sha256": "a" * 64,
        "entries": [
            {"portal_block_id": "blk_pdf", "page_number": 1,
             "kind": "recognised_text", "quote_source": "recognised",
             "text": "не брать с PDF-страницы", "flags": []},
            {"portal_block_id": "blk_ocr", "page_number": 2,
             "kind": "recognised_text", "quote_source": "recognised",
             "text": "распознано с листа 2", "flags": []},
            {"portal_block_id": "blk_image", "page_number": 2,
             "kind": "portal_description", "text": "не брать из описания изображения"},
        ],
    }
    return (
        pdf, _reference(pdf, role="prepared.text_layer", suffix="0"),
        ocr, _reference(ocr, role="prepared.recognised_text", suffix="1"),
    )


def _prepare(**changes: Any):
    pdf, pdf_ref, ocr, ocr_ref = _sources()
    arguments = {
        "version_uid": VERSION,
        "textless_pages": (2,),
        "text_layer_document": pdf,
        "text_layer_ref": pdf_ref,
        "text_layer_read_sha256": pdf_ref.sha256,
        "recognised_document": ocr,
        "recognised_ref": ocr_ref,
        "recognised_read_sha256": ocr_ref.sha256,
        "analysis_profile_id": PROFILE_ID,
        "prompt_bundle_id": PROMPT_BUNDLE_ID,
        "fixture_model_id": "fixture/ar-v2-recorded",
        "settings": RecordedGenerationSettings(4096, "high", {"type": "adaptive"}),
    }
    arguments.update(changes)
    return prepare_recorded_v2_input(**arguments)


def test_exact_bind_retains_raw_pdf_page_provenance_and_only_marked_ocr() -> None:
    first = _prepare()
    second = _prepare()
    assert first.request_sha256 == second.request_sha256
    assert first.source_binding_sha256 == second.source_binding_sha256
    assert first.text_layer_ref.sha256 == _sources()[1].sha256
    assert first.recognised_ref == _sources()[3]
    assert first.page_sources == (PdfPageSource(1, 0, 13), PdfPageSource(2, 13, 13))
    assert tuple((item.page_number, item.text) for item in first.recognised_context) == (
        (2, "распознано с листа 2"),
    )
    prompt = first.request.body["messages"][0]["content"]
    assert "Стена: 200 мм" in prompt
    assert "распознано с листа 2" in prompt
    assert "не брать с PDF-страницы" not in prompt
    assert "не брать из описания изображения" not in prompt
    assert "не цитировать" in prompt


def test_changed_pdf_or_ocr_bytes_need_new_reference_and_request_key() -> None:
    original = _prepare()
    pdf, _pdf_ref, ocr, _ocr_ref = _sources()
    pdf["pages"][0]["text"] = "Стена: 250 мм"
    changed_pdf = _reference(pdf, role="prepared.text_layer", suffix="2")
    result_pdf = _prepare(
        text_layer_document=pdf, text_layer_ref=changed_pdf,
        text_layer_read_sha256=changed_pdf.sha256,
    )
    assert result_pdf.request_sha256 != original.request_sha256
    assert result_pdf.source_binding_sha256 != original.source_binding_sha256
    ocr["entries"][1]["text"] = "распознано иначе"
    changed_ocr = _reference(ocr, role="prepared.recognised_text", suffix="3")
    result_ocr = _prepare(
        recognised_document=ocr, recognised_ref=changed_ocr,
        recognised_read_sha256=changed_ocr.sha256,
    )
    assert result_ocr.request_sha256 != original.request_sha256
    assert result_ocr.source_binding_sha256 != original.source_binding_sha256


def test_unrendered_source_metadata_changes_binding_but_not_request_key() -> None:
    original = _prepare()
    _pdf, _pdf_ref, ocr, _ocr_ref = _sources()
    ocr["results_sha256"] = "b" * 64
    changed = _reference(ocr, role="prepared.recognised_text", suffix="5")
    rebound = _prepare(
        recognised_document=ocr, recognised_ref=changed,
        recognised_read_sha256=changed.sha256,
    )
    assert rebound.request_sha256 == original.request_sha256
    assert rebound.source_binding_sha256 != original.source_binding_sha256


@pytest.mark.parametrize("field", ["text_layer_read_sha256", "recognised_read_sha256"])
def test_read_digest_mismatch_is_refused(field: str) -> None:
    with pytest.raises(RecordedInputError, match="artifact_digest_mismatch"):
        _prepare(**{field: "f" * 64})


def test_document_mutation_and_declared_size_mismatch_are_refused() -> None:
    pdf, pdf_ref, _ocr, _ocr_ref = _sources()
    pdf["pages"][0]["text"] = "Стена: 250 мм"
    with pytest.raises(RecordedInputError, match="artifact_digest_mismatch"):
        _prepare(text_layer_document=pdf)
    size_ref = ArtifactRef(
        pdf_ref.role, pdf_ref.blob_id, pdf_ref.sha256,
        pdf_ref.size_bytes + 1, pdf_ref.media_type,
    )
    with pytest.raises(RecordedInputError, match="artifact_digest_mismatch"):
        _prepare(text_layer_ref=size_ref)


def test_version_and_role_mismatch_are_refused() -> None:
    with pytest.raises(RecordedInputError, match="artifact_identity_mismatch"):
        _prepare(version_uid="ver_01M2545JSD15ETSNNV904X991K")
    pdf, _pdf_ref, _ocr, _ocr_ref = _sources()
    pdf["artifact_role"] = "prepared.recognised_text"
    with pytest.raises(RecordedInputError, match="artifact_identity_mismatch"):
        _prepare(text_layer_document=pdf)


def test_missing_or_out_of_range_recognition_is_refused() -> None:
    with pytest.raises(RecordedInputError, match="incomplete_recognised_binding"):
        _prepare(recognised_ref=None)
    with pytest.raises(RecognisedContextError, match="missing_recognised_artifact"):
        _prepare(
            recognised_document=None, recognised_ref=None,
            recognised_read_sha256=None,
        )
    with pytest.raises(RecordedInputError, match="textless_page_absent_from_pdf"):
        _prepare(textless_pages=(3,))


def test_multiple_text_blocks_on_one_page_fail_explicitly() -> None:
    _pdf, _pdf_ref, ocr, _ocr_ref = _sources()
    ocr = deepcopy(ocr)
    ocr["entries"].append({
        "portal_block_id": "blk_second", "page_number": 2,
        "kind": "recognised_text", "quote_source": "recognised",
        "text": "второй блок", "flags": [],
    })
    reference = _reference(ocr, role="prepared.recognised_text", suffix="4")
    with pytest.raises(RecordedInputError, match="multiple_text_blocks_for_page"):
        _prepare(
            recognised_document=ocr, recognised_ref=reference,
            recognised_read_sha256=reference.sha256,
        )


def test_legacy_absent_recognition_stays_explicitly_empty() -> None:
    result = _prepare(
        textless_pages=None,
        recognised_document=None, recognised_ref=None,
        recognised_read_sha256=None,
    )
    assert result.recognised_ref is None
    assert result.recognised_context == ()
    assert "не цитировать" not in result.request.body["messages"][0]["content"]
