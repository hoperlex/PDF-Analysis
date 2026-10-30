"""Small real interpreter cases plus process-protocol/cancellation failures."""

from __future__ import annotations

import contextlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject

from auditmanager.analysis.stages import pdf_precheck, source_preparation
from auditmanager.analysis.stages.extraction import ExtractedDocument, ExtractedPage
from auditmanager.analysis.stages.extraction import extract_document as reference_extract
from auditmanager.analysis.stages.pdf_precheck import PdfPrecheckLimits
from auditmanager.shared.errors import DomainError, ErrorCode


def _pdf(path: Path, *, broken_font: bool = False) -> Path:
    writer = PdfWriter()
    for index in range(2):
        page = writer.add_blank_page(width=400, height=500)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        if broken_font and index == 1:
            font[NameObject("/Subtype")] = NameObject("/Type0")
            font[NameObject("/DescendantFonts")] = ArrayObject()
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
        })
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 30 400 Td (Page " + str(index + 1).encode() + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    return path


def test_full_interpreter_returns_exact_existing_extraction_and_every_page_receipt(tmp_path):
    source = _pdf(tmp_path / "small.pdf")
    receipts = []
    result = pdf_precheck.extract_document(source, expected_page_count=2, progress=receipts.append)
    assert result == reference_extract(source)
    assert [page.text for page in result.pages] == ["Page 1", "Page 2"]
    assert [(entry.phase, entry.completed_pages, entry.total_pages) for entry in receipts] == [
        ("checking", 0, 2), ("checking", 1, 2), ("checking", 2, 2),
    ]


def test_envelope_readable_but_invalid_font_resource_is_refused_before_any_partial_result(tmp_path):
    source = _pdf(tmp_path / "broken.pdf", broken_font=True)
    receipts = []
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(source, progress=receipts.append)
    assert raised.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert raised.value.detail_fields["reason"] == "source_unreadable"
    assert [entry.completed_pages for entry in receipts] == [0, 1]


def test_stored_page_count_disagreement_is_not_accepted(tmp_path):
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(_pdf(tmp_path / "two.pdf"), expected_page_count=1)
    assert raised.value.detail_fields["reason"] == "page_count_disagreement"


def test_real_child_memory_bound_refuses_without_parent_fallback(tmp_path):
    limits = replace(PdfPrecheckLimits(), address_space_bytes=16 * 1024 * 1024)
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(_pdf(tmp_path / "small.pdf"), limits=limits)
    assert raised.value.detail_fields["reason"] == "pdf_precheck_unavailable"


def _child_script(tmp_path, monkeypatch, body):
    child = tmp_path / "receipt_child.py"
    child.write_text("import json, sys, time\n" + body, encoding="utf-8")
    monkeypatch.setattr(pdf_precheck, "_CHILD", child)
    source = tmp_path / "unused.pdf"
    source.write_bytes(b"%PDF-1.7")
    return source


def test_cancel_during_page_kills_and_reaps_the_child(tmp_path, monkeypatch):
    source = _child_script(tmp_path, monkeypatch,
        'print(json.dumps({"kind":"ready"}), flush=True)\n'
        'print(json.dumps({"kind":"document","page_count":1}), flush=True)\n'
        'print(json.dumps({"kind":"page_started","page_number":1}), flush=True)\n'
        'time.sleep(60)\n')
    processes = []
    real_popen = pdf_precheck.subprocess.Popen

    def capture(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(pdf_precheck.subprocess, "Popen", capture)
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        if calls >= 4:
            raise DomainError(ErrorCode.STALE_ATTEMPT, aggregate_type="Attempt")

    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(source, checkpoint=cancelled)
    assert raised.value.code is ErrorCode.STALE_ATTEMPT
    assert len(processes) == 1 and processes[0].returncode is not None
    assert processes[0].stdout.closed


def test_page_timeout_is_explicit_and_child_is_reaped(tmp_path, monkeypatch):
    source = _child_script(tmp_path, monkeypatch,
        'print(json.dumps({"kind":"ready"}), flush=True)\n'
        'print(json.dumps({"kind":"document","page_count":1}), flush=True)\n'
        'print(json.dumps({"kind":"page_started","page_number":1}), flush=True)\n'
        'time.sleep(60)\n')
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(source, limits=replace(PdfPrecheckLimits(), page_seconds=0.1))
    assert raised.value.detail_fields["reason"] == "pdf_precheck_page_timeout"


@pytest.mark.parametrize("ending,reason", [
    ('print(json.dumps({"kind":"failed","reason":"secret parser exception"}), flush=True)\n', "source_unreadable"),
    ("", "pdf_precheck_incomplete"),
    ('print("broken receipt", flush=True)\n', "pdf_precheck_receipt_invalid"),
])
def test_partial_malformed_or_untrusted_failure_receipts_never_succeed(tmp_path, monkeypatch, ending, reason):
    source = _child_script(tmp_path, monkeypatch,
        'print(json.dumps({"kind":"ready"}), flush=True)\n'
        'print(json.dumps({"kind":"document","page_count":1}), flush=True)\n' + ending)
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(source)
    assert raised.value.detail_fields["reason"] == reason
    assert "secret" not in str(raised.value.detail_fields)


def test_output_bound_is_enforced_before_receipt_deserialization(tmp_path, monkeypatch):
    source = _child_script(tmp_path, monkeypatch, 'print("x" * 1024, flush=True)\n')
    with pytest.raises(DomainError) as raised:
        pdf_precheck.extract_document(source, limits=replace(PdfPrecheckLimits(), max_output_bytes=128))
    assert raised.value.detail_fields["reason"] == "pdf_precheck_limits"


def test_blank_page_failure_is_recorded_without_completed_or_artifact_publication(monkeypatch):
    document = ExtractedDocument((ExtractedPage(1, 400, 500, 0, "", ()),))

    @contextlib.contextmanager
    def source_file(*args, **kwargs):
        yield "not-used.pdf", "0" * 64

    monkeypatch.setattr(source_preparation, "_source_file", source_file)
    monkeypatch.setattr(source_preparation, "extract_document", lambda *args, **kwargs: document)
    monkeypatch.setattr(source_preparation, "_portal_members", lambda context: None)
    receipts = []
    context = SimpleNamespace(blob=lambda _: "blob", blob_store=object())
    with pytest.raises(DomainError) as raised:
        source_preparation.run_source_preparation_with_progress(
            context, progress=receipts.append, checkpoint=lambda: None, expected_page_count=1,
        )
    assert raised.value.code is ErrorCode.VALIDATION_FAILED
    assert [entry.phase for entry in receipts] == ["started", "failed"]
    assert receipts[-1].error_code == ErrorCode.VALIDATION_FAILED.value
    assert receipts[-1].reason == "pdf_precheck_failed"


def test_receipt_rejects_nonfinite_geometry_before_accepting_a_page():
    payload = {"page_number": 1, "width_pt": float("nan"), "height_pt": 500,
               "rotation_deg": 0, "text": "", "lines": []}
    with pytest.raises(DomainError) as raised:
        pdf_precheck._page(json.loads(json.dumps(payload)), 1, PdfPrecheckLimits())
    assert raised.value.detail_fields["reason"] == "pdf_precheck_receipt_invalid"
