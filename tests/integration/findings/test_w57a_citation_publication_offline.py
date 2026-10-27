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


# --- `AR-V3-DECISIONS-01`: the AR v3 beta CITE stage as the certifying stage ---------------------


def _publish_v3(session: _Session, data: bytes, **overrides):
    return publish_grounded_v3_finding(
        session, run_id="run_" + "0" * 26, job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
        execution_token="secret-token", model_call_id="mc_" + "0" * 26, set_bytes=data,
        candidate=_candidate(), cite_stage_id="ar_v3_citation_review", **overrides,
    )


def _authority_params(session: _Session) -> dict[str, object]:
    return next(params for sql, params in session.calls if sql.lstrip().startswith("SELECT r.project_uid"))


def test_the_default_stage_is_norm_verification_and_the_effect_must_be_of_this_attempt() -> None:
    data = _set_bytes()
    session = _Session(data)
    _publish(session, data)
    params = _authority_params(session)
    assert params["cite_stage_id"] == "norm_verification" and params["same_attempt"] is True
    other = _Session(data)
    other.authority["effect_attempt_id"] = "att_" + "1" * 26
    with pytest.raises(CitationPublicationRefused, match="publication_authority_invalid"):
        _publish(other, data)
    assert _writes(other) == []


def test_the_v3_stage_publishes_when_the_call_was_completed_by_an_earlier_attempt_of_the_job() -> None:
    data = _set_bytes()
    session = _Session(data)
    session.authority["effect_attempt_id"] = "att_" + "1" * 26  # the worker died after the call
    result = _publish_v3(session, data)
    params = _authority_params(session)
    assert params["cite_stage_id"] == "ar_v3_citation_review" and params["same_attempt"] is False
    assert result.citation_count == 1 and len(_writes(session)) > 0


def test_the_v3_stage_still_needs_the_call_to_be_the_same_runs_succeeded_recorded_pair() -> None:
    data = _set_bytes()
    for key, value in (("effect_state", "started"), ("call_status", "failed"),
                       ("effect_response_sha256", "e" * 64), ("cite_status", "failed"),
                       ("run_state", "running"), ("execution_token", "other")):
        session = _Session(data)
        session.authority[key] = value
        with pytest.raises(CitationPublicationRefused, match="publication_authority_invalid"):
            _publish_v3(session, data)
        assert _writes(session) == [], key


@pytest.mark.parametrize("stage", ["text_analysis", "finding_merge", "", "AR_V3_CITATION_REVIEW"])
def test_an_unknown_certifying_stage_is_refused_before_the_database_is_asked(stage: str) -> None:
    data = _set_bytes()
    session = _Session(data)
    with pytest.raises(CitationPublicationRefused, match="cite_stage_unknown"):
        publish_grounded_v3_finding(
            session, run_id="run_" + "0" * 26, job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
            execution_token="secret-token", model_call_id="mc_" + "0" * 26, set_bytes=data,
            candidate=_candidate(), cite_stage_id=stage,
        )
    assert session.calls == []


@pytest.mark.parametrize("change", [
    {"category": "layout"}, {"category": "documentation"}, {"category": "internal_contradiction"},
    {"evidence": ()}, {"norm_citations": ()}, {"required_value": ""}, {"stated_value": ""},
])
def test_only_a_grounded_normative_candidate_is_written_and_nothing_is_asked_otherwise(change: dict[str, object]) -> None:
    """`AR-V3-DECISIONS-01`: the writer's own shape guard, for both certifying stages.

    The five normative categories only, one to five citations, evidence present, both values
    present; the refusal comes before any database statement.
    """
    data = _set_bytes()
    for stage in ("norm_verification", "ar_v3_citation_review"):
        session = _Session(data)
        with pytest.raises(CitationPublicationRefused, match="grounded_normative_candidate_required"):
            publish_grounded_v3_finding(
                session, run_id="run_" + "0" * 26, job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
                execution_token="secret-token", model_call_id="mc_" + "0" * 26, set_bytes=data,
                candidate=replace(_candidate(), **change), cite_stage_id=stage,
            )
        assert session.calls == []


def test_six_citations_are_refused_and_a_non_candidate_is_refused() -> None:
    data = _set_bytes()
    one = _candidate()
    session = _Session(data)
    with pytest.raises(CitationPublicationRefused, match="grounded_normative_candidate_required"):
        publish_grounded_v3_finding(
            session, run_id="run_" + "0" * 26, job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
            execution_token="secret-token", model_call_id="mc_" + "0" * 26, set_bytes=data,
            candidate=replace(one, norm_citations=one.norm_citations * 6),
        )
    with pytest.raises(CitationPublicationRefused, match="grounded_normative_candidate_required"):
        publish_grounded_v3_finding(
            session, run_id="run_" + "0" * 26, job_id="job_" + "0" * 26, attempt_id="att_" + "0" * 26,
            execution_token="secret-token", model_call_id="mc_" + "0" * 26, set_bytes=data,
            candidate="not a candidate",  # type: ignore[arg-type]
        )
    assert session.calls == []
