"""Offline refusal probes for the unserved W57a transaction writer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.findings.citation_publication import (
    CitationEvidence,
    CitationPublicationRefused,
    V3PublicationCandidate,
    publish_grounded_v3_finding,
)
from auditmanager.norms.public import GroundedNormCitation


_PARAGRAPH = "**Требуемое значение сопротивления не менее 3,5 м²·К/Вт для данного объекта.**"
_QUOTE = "Требуемое значение сопротивления не менее 3,5 м²·К/Вт"
_DOCUMENT = "ndoc_" + "0" * 26
_PARAGRAPH_ID = "npar_" + "0" * 26
_SNAPSHOT = "ns_" + "0" * 26


def _candidate() -> V3PublicationCandidate:
    return V3PublicationCandidate(
        category="insulation", finding_text="Сопротивление недостаточно",
        recommendation_text="Проверить конструкцию", proposed_severity="operational",
        evidence=(CitationEvidence(1, "Фактически 2,5 м²·К/Вт", 0, len("Фактически 2,5 м²·К/Вт")),),
        norm_citations=(GroundedNormCitation(
            "N1", _DOCUMENT, _PARAGRAPH_ID, _PARAGRAPH.index(_QUOTE), _QUOTE, "verified",
        ),),
        required_value="3,5", stated_value="2,5",
    )


def _set_bytes() -> bytes:
    prompt = {"paragraphs": [{
        "label": "N1", "norm_document_id": _DOCUMENT,
        "norm_paragraph_id": _PARAGRAPH_ID, "text": _PARAGRAPH,
    }]}
    payload = {
        "identity": {
            "norms_snapshot_id": _SNAPSHOT, "map_sha256": "a" * 64,
            "reviewed_content_key": "reviewed-key",
        },
        "prompt_part": json.dumps(prompt, ensure_ascii=False),
        "rebinding_paragraphs": [{
            "norm_document_id": _DOCUMENT, "norm_paragraph_id": _PARAGRAPH_ID,
            "text": _PARAGRAPH,
            "text_sha256": hashlib.sha256(_PARAGRAPH.encode()).hexdigest(),
        }],
    }
    return json.dumps(payload, ensure_ascii=False).encode()


class _Mappings:
    def __init__(self, value: dict[str, object] | None):
        self.value = value

    def one_or_none(self) -> dict[str, object] | None:
        return self.value


class _Result:
    rowcount = 1

    def __init__(self, value: dict[str, object] | None = None):
        self.value = value

    def mappings(self) -> _Mappings:
        return _Mappings(self.value)


class _Session:
    def __init__(self, data: bytes):
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.authority: dict[str, object] | None = {
            "project_uid": "prj_" + "0" * 26,
            "version_uid": "ver_" + "0" * 26,
            "analysis_profile_id": "ap_" + "0" * 26,
            "prompt_bundle_id": "pb_" + "0" * 26,
            "provider_mode": "recorded",
            "norms_snapshot_id": _SNAPSHOT,
            "norm_retrieval_set_id": "nrs_" + "0" * 26,
            "run_state": "validating", "job_state": "running",
            "attempt_state": "running", "execution_token": "secret-token",
            "set_state": "verified",
            "observed_set_sha256": hashlib.sha256(data).hexdigest(),
            "set_size_bytes": len(data),
            "map_sha256": "a" * 64,
            "reviewed_content_key": "reviewed-key",
            "call_status": "succeeded", "call_mode": "recorded",
            "call_request_sha256": "b" * 64,
            "call_response_sha256": "c" * 64,
            "effect_state": "completed", "effect_attempt_id": "att_" + "0" * 26,
            "effect_mode": "recorded",
            "effect_request_sha256": "b" * 64,
            "effect_response_sha256": "c" * 64,
            "cite_status": "succeeded",
        }

    def execute(self, statement: object, params: dict[str, object]) -> _Result:
        sql = str(statement)
        self.calls.append((sql, params))
        if sql.lstrip().startswith("SELECT r.project_uid"):
            return _Result(self.authority)
        return _Result()


def _publish(session: _Session, data: bytes, candidate: V3PublicationCandidate | None = None):
    return publish_grounded_v3_finding(
        session, run_id="run_" + "0" * 26,
        job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
        execution_token="secret-token", model_call_id="mc_" + "0" * 26,
        set_bytes=data, candidate=candidate or _candidate(),
    )


def _writes(session: _Session) -> list[str]:
    return [sql for sql, _ in session.calls if sql.lstrip().startswith(("INSERT", "UPDATE"))]


def test_exact_set_and_active_attempt_publish_one_canonical_citation_partition() -> None:
    data = _set_bytes()
    session = _Session(data)
    result = _publish(session, data)
    assert result.citation_count == 1
    assert len(_writes(session)) == 5
    assert any("finding_observation_norm_citation" in sql for sql in _writes(session))
    citation = next(
        params for sql, params in session.calls
        if "INSERT INTO finding_observation_norm_citation" in sql
    )
    assert citation["quote"] == _QUOTE
    assert citation["char_start"] == _PARAGRAPH.index(_QUOTE)
    assert citation["snapshot_id"] == _SNAPSHOT
    observation = next(
        params for sql, params in session.calls
        if "INSERT INTO finding_observation (" in sql
    )
    assert observation["citation_count"] == 1
    assert observation["required_value"] == "3,5"


@pytest.mark.parametrize("change", [
    {"attempt_state": "superseded"}, {"effect_attempt_id": "att_" + "1" * 26},
    {"set_state": "rejected"}, {"cite_status": "failed"},
    {"execution_token": "other"}, {"call_status": "failed"},
    {"effect_request_sha256": "d" * 64},
])
def test_stale_or_incomplete_persisted_authority_writes_nothing(change: dict[str, object]) -> None:
    data = _set_bytes()
    session = _Session(data)
    assert session.authority is not None
    session.authority.update(change)
    with pytest.raises(CitationPublicationRefused, match="publication_authority_invalid"):
        _publish(session, data)
    assert _writes(session) == []


def test_digest_match_is_required_even_when_supplied_json_looks_correct() -> None:
    data = _set_bytes()
    session = _Session(data)
    tampered = data.replace(b"reviewed-key", b"reviewed-KEY")
    with pytest.raises(CitationPublicationRefused, match="set_bytes_differ_from_custody"):
        _publish(session, tampered)
    assert _writes(session) == []


def test_selected_label_and_raw_span_must_match_exact_set_bytes() -> None:
    data = _set_bytes()
    session = _Session(data)
    candidate = _candidate()
    wrong_label = replace(candidate.norm_citations[0], label="N2")
    with pytest.raises(CitationPublicationRefused, match="citation_outside_selected_set"):
        _publish(session, data, replace(candidate, norm_citations=(wrong_label,)))
    wrong_span = replace(candidate.norm_citations[0], raw_offset=0)
    with pytest.raises(CitationPublicationRefused, match="citation_raw_span_invalid"):
        _publish(session, data, replace(candidate, norm_citations=(wrong_span,)))
    assert _writes(session) == []
