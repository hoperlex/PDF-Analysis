"""One current group member yields exact v3 transport bytes from saved set input."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.analysis.public import (
    AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID, V3GenerationSettings,
)
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.findings.public import VerifiedRetrievalSetInput
from auditmanager.jobs.public import AttemptAuthority
from auditmanager.runs import v3_citations, v3_execution_request
from auditmanager.runs.repository import RunRow
from auditmanager.runs.v3_execution_binding import V3ExecutionBinding
from auditmanager.runs.reference_text_input import SavedReferenceTextInput
from auditmanager.shared.errors import DomainError, ErrorCode


AUTHORITY = AttemptAuthority("run_test", "job_test", "att_test", "lease_test", "secret")
SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
SETTINGS = V3GenerationSettings(4096, "high", {"type": "adaptive"})
TEXT = "АР. Ширина прохода 1,2 м."
NORM = "Ширина прохода по условию составляет 1,4 м"
HIDDEN = "Скрытый абзац только для локальной проверки"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _paragraph(ordinal: int, value: str) -> dict[str, object]:
    return {
        "norm_document_id": "ndoc_01K7F4N2A9R8T6V5W3X2Y1Z0QJ",
        "norm_paragraph_id": (
            "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QK" if ordinal == 0
            else "npar_01K7F4N2A9R8T6V5W3X2Y1Z0QM"
        ),
        "designation": "СП 54", "title": "Жилые здания", "ordinal": ordinal,
        "clause_number": "7.1.4", "page_label": "7", "text": value,
        "text_sha256": hashlib.sha256(value.encode()).hexdigest(),
    }


def _set(scope_id: str) -> bytes:
    selected, hidden = _paragraph(0, NORM), _paragraph(1, HIDDEN)
    part = _canonical({
        "builder_version": "norm-ranking-prep-v1",
        "paragraphs": [dict(selected, item_id=item, label=f"N{index}")
                       for index, item in enumerate(scope_membership(scope_id).item_ids, 1)],
    }).decode("utf-8")
    return _canonical({
        "builder_version": "norm-retrieval-set-prep-v1",
        "identity": {"map_sha256": "a" * 64,
                     "reviewed_content_key": "synthetic-test-only",
                     "norms_snapshot_id": SNAPSHOT,
                     "embedding_build": "bge-m3-dense-v1"},
        "snapshot_content_digest": "b" * 64,
        "ranking_version": "norm-ranking-prep-v1",
        "norm_quote_version": "norm-quote-v1",
        "norm_value_version": "norm-value-v1",
        "prompt_part": part, "prompt_part_characters": len(part),
        "windows_per_item": 0, "inside_target_windows_dropped": True,
        "rebinding_paragraphs": [selected, hidden],
    })


def _layer(version: str = "ver_test") -> TextLayer:
    return TextLayer(version, "NFC", (Page(1, 0, len(TEXT), TEXT),), TEXT)


def _run() -> RunRow:
    return RunRow(
        run_id=AUTHORITY.run_id, project_uid="proj_test", version_uid="ver_test",
        state="running", analysis_profile_id=str(AR_V3_BETA_PROFILE_ID),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID), norms_snapshot_id=SNAPSHOT,
        provider_mode="recorded", frozen_input_digest="c" * 64,
        command_id=None, terminal_reason=None, terminal_detail=None,
        interrupted_reason=None, degradation_set=(),
        created_at=datetime(2026, 10, 23, tzinfo=timezone.utc),
        terminal_at=None, norm_retrieval_set_id="nrs_test",
    )


def _binding(scope_id: str, raw: bytes) -> V3ExecutionBinding:
    return V3ExecutionBinding(
        group_id="arg_test", run_id=AUTHORITY.run_id, scope_id=scope_id,
        project_uid="proj_test", version_uid="ver_test", norms_snapshot_id=SNAPSHOT,
        analysis_profile_id=str(AR_V3_BETA_PROFILE_ID),
        prompt_bundle_id=str(AR_V3_BETA_BUNDLE_ID), provider_mode="recorded",
        composition_sha256=scope_membership(scope_id).composition_sha256,
        policy_sha256="d" * 64, pack_sha256="e" * 64,
        map_sha256="a" * 64, norm_retrieval_set_id="nrs_test",
        set_sha256=hashlib.sha256(raw).hexdigest(), frozen_input_digest="c" * 64,
    )


def _arrange(monkeypatch: pytest.MonkeyPatch, scope_id: str = "F1"):
    raw = _set(scope_id)
    binding = _binding(scope_id, raw)
    saved = VerifiedRetrievalSetInput(
        AUTHORITY.run_id, SNAPSHOT, "nrs_test", "a" * 64,
        "blob_test", hashlib.sha256(raw).hexdigest(), raw,
    )
    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding",
                        lambda *args, **kwargs: binding)
    monkeypatch.setattr(v3_execution_request, "load_saved_reference_text",
                        lambda *args, **kwargs: SavedReferenceTextInput(_layer(), "ver_test", 1))
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: saved)
    monkeypatch.setattr(v3_execution_request, "recheck_saved_reference_text_facts",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(v3_execution_request, "recheck_verified_retrieval_set_facts",
                        lambda *args, **kwargs: None)
    return binding, saved


def _prepare(monkeypatch: pytest.MonkeyPatch, scope_id: str = "F1", **overrides):
    binding, saved = _arrange(monkeypatch, scope_id)
    values = dict(
        authority=AUTHORITY, registry=object(), blob_store=object(),
        max_text_bytes=100_000, expected_provider_mode="recorded",
        model_identity="fixture/ar-v3-beta", settings=SETTINGS,
        idempotency_scope="attempt-1",
        runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
    )
    values.update(overrides)
    return binding, saved, v3_execution_request.prepare_v3_execution_request(
        object(), **values,
    )


@pytest.mark.parametrize("scope_id", ("F1", "F2", "A1", "A2", "S1", "S2"))
def test_six_scopes_bind_saved_bytes_to_one_transport_body(monkeypatch, scope_id):
    binding, saved, prepared = _prepare(monkeypatch, scope_id)
    assert prepared.binding == binding
    assert prepared.saved_text.text_layer == _layer()
    assert prepared.pinned_corpus.verified_set == saved
    assert prepared.sealed.candidate == prepared.pinned_corpus.candidate
    assert prepared.candidate_sha256 != prepared.provider_body_sha256
    assert prepared.model_request.request_sha256 == prepared.provider_body_sha256
    assert NORM in prepared.model_request.body["messages"][0]["content"]
    assert HIDDEN not in str(prepared.model_request.body)
    _, _, replay = _prepare(monkeypatch, scope_id, idempotency_scope="attempt-2")
    assert replay.provider_body_sha256 == prepared.provider_body_sha256


def test_nonlocking_blob_reads_precede_one_final_locked_fence(monkeypatch):
    binding, saved = _arrange(monkeypatch)
    order = []

    def resolve(*args, **kwargs):
        order.append("lock" if kwargs.get("lock_authority", True) else "peek")
        return binding

    def source(*args, **kwargs):
        assert kwargs["lock_authority"] is False
        assert "lock" not in order
        order.append("text_blob")
        return SavedReferenceTextInput(_layer(), "ver_test", 1)

    def norm_set(*args, **kwargs):
        assert kwargs["lock_authority"] is False
        assert "lock" not in order
        order.append("set_blob")
        return saved

    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding", resolve)
    monkeypatch.setattr(v3_execution_request, "load_saved_reference_text", source)
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set", norm_set)
    monkeypatch.setattr(v3_execution_request, "recheck_saved_reference_text_facts",
                        lambda *args, **kwargs: order.append("text_witness"))
    monkeypatch.setattr(v3_execution_request, "recheck_verified_retrieval_set_facts",
                        lambda *args, **kwargs: order.append("set_witness"))
    v3_execution_request.prepare_v3_execution_request(
        object(), authority=AUTHORITY, registry=object(), blob_store=object(),
        max_text_bytes=100_000, expected_provider_mode="recorded",
        model_identity="fixture/model", settings=SETTINGS,
        runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
    )
    assert order == ["peek", "text_blob", "set_blob", "lock",
                     "text_witness", "set_witness"]


def test_cite_can_defer_request_fence_until_after_reply_blob(monkeypatch):
    binding, saved = _arrange(monkeypatch)
    order = []

    def resolve(*args, **kwargs):
        order.append("lock" if kwargs.get("lock_authority", True) else "peek")
        return binding

    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding", resolve)
    monkeypatch.setattr(v3_execution_request, "load_saved_reference_text",
                        lambda *args, **kwargs: (
                            order.append("text_blob")
                            or SavedReferenceTextInput(_layer(), "ver_test", 1)))
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: order.append("set_blob") or saved)
    monkeypatch.setattr(v3_execution_request, "recheck_saved_reference_text_facts",
                        lambda *args, **kwargs: order.append("text_witness"))
    monkeypatch.setattr(v3_execution_request, "recheck_verified_retrieval_set_facts",
                        lambda *args, **kwargs: order.append("set_witness"))
    prepared = v3_execution_request.prepare_v3_execution_request(
        object(), authority=AUTHORITY, registry=object(), blob_store=object(),
        max_text_bytes=100_000, expected_provider_mode="recorded",
        model_identity="fixture/model", settings=SETTINGS,
        runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        defer_final_fence=True,
    )
    order.append("reply_blob")
    v3_execution_request.fence_v3_execution_request(
        object(), authority=AUTHORITY, registry=object(), prepared=prepared,
        jobs=object(), runs=object(),
    )
    assert order == ["peek", "text_blob", "set_blob", "reply_blob", "lock",
                     "text_witness", "set_witness"]


@pytest.mark.parametrize("changed", ["text", "set"])
def test_changed_db_witness_refuses_after_final_locked_fence(monkeypatch, changed):
    binding, _ = _arrange(monkeypatch)
    order = []

    def resolve(*args, **kwargs):
        order.append("lock" if kwargs.get("lock_authority", True) else "peek")
        return binding

    def changed_witness(*args, **kwargs):
        assert order[-1] == "lock" or order[-1] == "text_witness"
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="witness_changed")

    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding", resolve)
    monkeypatch.setattr(v3_execution_request, "recheck_saved_reference_text_facts",
                        changed_witness if changed == "text"
                        else lambda *args, **kwargs: order.append("text_witness"))
    monkeypatch.setattr(v3_execution_request, "recheck_verified_retrieval_set_facts",
                        changed_witness if changed == "set"
                        else lambda *args, **kwargs: order.append("set_witness"))
    with pytest.raises(DomainError) as caught:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )
    assert caught.value.detail_fields["reason"] == "witness_changed"
    assert order[:2] == ["peek", "lock"]


def test_wrong_provider_mode_or_source_version_refuses_before_set_read(monkeypatch):
    _arrange(monkeypatch)
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: pytest.fail("set read was reached"))
    base = dict(registry=object(), blob_store=object(), model_identity="fixture/model",
                settings=SETTINGS, runs=SimpleNamespace(get=lambda *args: _run()),
                jobs=object())
    with pytest.raises(DomainError) as mode:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, max_text_bytes=100_000,
            expected_provider_mode="live", **base,
        )
    assert mode.value.detail_fields["reason"] == "provider_mode_mismatch"
    monkeypatch.setattr(v3_execution_request, "load_saved_reference_text",
                        lambda *args, **kwargs: SavedReferenceTextInput(
                            _layer("ver_foreign"), "ver_foreign", 1))
    with pytest.raises(DomainError) as version:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, max_text_bytes=100_000,
            expected_provider_mode="recorded", **base,
        )
    assert version.value.detail_fields["reason"] == "run_or_text_binding_mismatch"


def test_changed_set_pin_and_group_after_blob_read_refuse(monkeypatch):
    binding, saved = _arrange(monkeypatch)
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: replace(saved, norm_retrieval_set_id="nrs_other"))
    with pytest.raises(v3_citations.V3CorpusCitationRefused,
                       match="run_set_profile_binding_invalid"):
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )
    # A group change after the first lookup is checked after constructing the body.
    _arrange(monkeypatch)
    calls = iter((binding, replace(binding, pack_sha256="f" * 64)))
    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding",
                        lambda *args, **kwargs: next(calls))
    with pytest.raises(DomainError) as drift:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )
    assert drift.value.detail_fields["reason"] == "group_binding_changed_during_read"


def test_stale_attempt_and_failed_blob_custody_refuse(monkeypatch):
    _arrange(monkeypatch)
    monkeypatch.setattr(v3_execution_request, "resolve_v3_execution_binding",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            DomainError(ErrorCode.EXECUTION_TOKEN_INVALID)))
    with pytest.raises(DomainError) as stale:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )
    assert stale.value.code is ErrorCode.EXECUTION_TOKEN_INVALID
    _arrange(monkeypatch)
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            ValueError("set_blob_unreadable")))
    with pytest.raises(ValueError, match="set_blob_unreadable"):
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )


def test_missing_saved_source_refuses_before_norm_set_read(monkeypatch):
    _arrange(monkeypatch)
    monkeypatch.setattr(v3_execution_request, "load_saved_reference_text",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            DomainError(ErrorCode.ANALYSIS_INPUT_INVALID,
                                        reason="source_stage_missing_or_duplicate")))
    monkeypatch.setattr(v3_citations, "load_verified_retrieval_set",
                        lambda *args, **kwargs: pytest.fail("set read was reached"))
    with pytest.raises(DomainError) as missing:
        v3_execution_request.prepare_v3_execution_request(
            object(), authority=AUTHORITY, registry=object(), blob_store=object(),
            max_text_bytes=100_000, expected_provider_mode="recorded",
            model_identity="fixture/model", settings=SETTINGS,
            runs=SimpleNamespace(get=lambda *args: _run()), jobs=object(),
        )
    assert missing.value.detail_fields["reason"] == "source_stage_missing_or_duplicate"
