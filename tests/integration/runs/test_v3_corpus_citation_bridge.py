"""Saved norm-set bytes feed one AR v3 request and local citation plan."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from auditmanager.analysis.public import SuppliedV3Response, TextLayer
from auditmanager.analysis.text.textlayer import Page
from auditmanager.findings.public import VerifiedRetrievalSetInput
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_citations
from auditmanager.runs.repository import RunRow


DOCUMENT = "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ"
SELECTED = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK"
HIDDEN = "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
SNAPSHOT = "ns_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
MAP_SHA = "a" * 64
PDF_QUOTE = "Ширина прохода 1,2 м"
NORM_QUOTE = "Минимальная ширина прохода составляет 1,4 м"
PROFILE = "ap_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
BUNDLE = "pb_01K7F4N2A9R8T6V5W3X2Y1Z0QH"
AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _set() -> bytes:
    rows = [dict(
        norm_document_id=DOCUMENT, norm_paragraph_id=paragraph,
        designation="СП 54", title="Жилые здания", ordinal=ordinal,
        clause_number="7.1.4", page_label="7", text=value,
        text_sha256=hashlib.sha256(value.encode()).hexdigest(),
    ) for ordinal, (paragraph, value) in enumerate((
        (SELECTED, NORM_QUOTE), (HIDDEN, "Скрытый нормативный абзац"),
    ))]
    prompt = _json({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(rows[0], item_id="item_a", label="N1")],
    }).decode("utf-8")
    return _json({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {"map_sha256": MAP_SHA,
                     "reviewed_content_key": "reviewed-key",
                     "norms_snapshot_id": SNAPSHOT,
                     "embedding_build": "bge-m3-dense-v1"},
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1",
        "prompt_part": prompt, "prompt_part_characters": len(prompt),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": rows,
    })


def _run() -> RunRow:
    return RunRow(
        run_id=AUTHORITY.run_id, project_uid="proj_test", version_uid="ver_test",
        state="running", analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE,
        norms_snapshot_id=SNAPSHOT, provider_mode="recorded",
        frozen_input_digest="c" * 64, command_id=None, terminal_reason=None,
        terminal_detail=None, interrupted_reason=None, degradation_set=(),
        created_at=datetime(2026, 10, 23, tzinfo=timezone.utc), terminal_at=None,
        norm_retrieval_set_id="nrs_test",
    )


def _layer() -> TextLayer:
    text = "АР. " + PDF_QUOTE + "."
    return TextLayer("ver_test", "NFC", (Page(1, 0, len(text), text),), text)


def _prepare(monkeypatch: pytest.MonkeyPatch, *, run: RunRow | None = None,
             saved: VerifiedRetrievalSetInput | None = None):
    raw = _set()
    verified = saved or VerifiedRetrievalSetInput(
        AUTHORITY.run_id, SNAPSHOT, "nrs_test", MAP_SHA,
        "blob_test", hashlib.sha256(raw).hexdigest(), raw,
    )
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: verified)
    return v3_citations.prepare_v3_corpus_request(
        object(), run=run or _run(), authority=AUTHORITY, blob_store=object(),
        text_layer=_layer(), profile_id=PROFILE, bundle_id=BUNDLE,
        map_sha256=MAP_SHA,
    )


def _response(digest: str, *, label: str = "N1", quote: str = NORM_QUOTE):
    return SuppliedV3Response(digest, _json({"observations": [{
        "category": "evacuation", "finding_text": "Проверить ширину прохода.",
        "recommendation_text": "Сверить проект и норму.",
        "proposed_severity": "operational",
        "evidence": [{"page_number": 1, "quote": PDF_QUOTE}],
        "norm_citations": [{"label": label, "quote": quote}],
        "required_value": "1,4 м", "stated_value": "1,2 м",
    }]}).decode("utf-8"), False)


def test_exact_saved_selection_forms_request_and_citation_candidate(monkeypatch):
    request = _prepare(monkeypatch)
    assert NORM_QUOTE in request.candidate.user_prompt
    assert "Скрытый нормативный абзац" not in request.candidate.user_prompt
    result = v3_citations.plan_v3_corpus_citations(
        request, _response(request.candidate.request_sha256), _layer(),
    )
    assert result.evaluation.grounding.rejected == ()
    assert len(result.normative_candidates) == 1
    saved = result.normative_candidates[0]
    assert saved.evidence[0].quote == PDF_QUOTE
    assert saved.norm_citations[0].paragraph_id == SELECTED
    assert saved.norm_citations[0].raw_quote == NORM_QUOTE


@pytest.mark.parametrize("change", [
    {"norms_snapshot_id": "ns_other"},
    {"norm_retrieval_set_id": "nrs_other"},
    {"analysis_profile_id": "ap_other"},
    {"state": "published"},
])
def test_foreign_run_pin_or_profile_refuses_before_prompt(monkeypatch, change):
    with pytest.raises(v3_citations.V3CorpusCitationRefused,
                       match="run_set_profile_binding_invalid"):
        _prepare(monkeypatch, run=replace(_run(), **change))


def test_unreviewed_map_refuses_before_prompt(monkeypatch):
    raw = _set()
    other = VerifiedRetrievalSetInput(
        AUTHORITY.run_id, SNAPSHOT, "nrs_test", "d" * 64,
        "blob_test", hashlib.sha256(raw).hexdigest(), raw,
    )
    with pytest.raises(v3_citations.V3CorpusCitationRefused,
                       match="run_set_profile_binding_invalid"):
        _prepare(monkeypatch, saved=other)


def test_wrong_label_is_withheld_and_never_becomes_publication_candidate(monkeypatch):
    request = _prepare(monkeypatch)
    result = v3_citations.plan_v3_corpus_citations(
        request, _response(request.candidate.request_sha256, label="N9"), _layer(),
    )
    assert result.normative_candidates == ()
    assert [item.reason for item in result.evaluation.grounding.rejected] == [
        "norm_label_unknown",
    ]


def test_replay_refuses_a_request_rebound_to_another_saved_set(monkeypatch):
    request = _prepare(monkeypatch)
    rebound = replace(
        request,
        verified_set=replace(request.verified_set, map_sha256="d" * 64),
    )
    with pytest.raises(v3_citations.V3CorpusCitationRefused,
                       match="pinned_request_set_mismatch"):
        v3_citations.plan_v3_corpus_citations(
            rebound, _response(request.candidate.request_sha256), _layer(),
        )
