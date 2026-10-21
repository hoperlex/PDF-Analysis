"""Recorded AR v2 response reaches only deterministic, grounded SQL writes."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace

import pytest

from auditmanager.analysis.public import ModelResponse, RecognisedContext
from auditmanager.analysis.profiles.ar_v2.response import V2ResponseError
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.findings.v2_publication import V2PublicationContext
from auditmanager.findings.v2_recorded import publish_recorded_v2_response
from auditmanager.shared.identity import (
    AnalysisProfileId, ModelCallId, ProjectUid, PromptBundleId, RunId, VersionUid,
)


class _Result:
    rowcount = 1


class _Session:
    def __init__(self) -> None:
        self.sql: list[tuple[str, dict[str, object]]] = []
        self.savepoints = 0

    @contextmanager
    def begin_nested(self):
        self.savepoints += 1
        yield self

    def execute(self, statement: object, parameters: dict[str, object]) -> _Result:
        self.sql.append((str(statement), dict(parameters)))
        return _Result()


_TEXT = "Стена А имеет толщину 200 мм. Окно Б имеет ширину 1200 мм."
_QUOTE = "Стена А имеет толщину 200 мм"


def _layer() -> TextLayer:
    return TextLayer("ver_recorded", "NFC", (Page(1, 0, len(_TEXT), _TEXT),), _TEXT)


def _context() -> V2PublicationContext:
    return V2PublicationContext(
        RunId.new().value, ProjectUid.new().value, VersionUid.new().value,
        AnalysisProfileId.new().value, PromptBundleId.new().value,
        "recorded", ModelCallId.new().value,
    )


def _proposal(quote: str, *, severity: str = "operational") -> dict[str, object]:
    return {
        "category": "dimensions",
        "finding_text": "Указанные размеры требуют сверки",
        "recommendation_text": "Уточнить размер в проекте",
        "proposed_severity": severity,
        "evidence": [{"page_number": 1, "quote": quote}],
    }


def _response(proposals: list[dict[str, object]], *, truncated: bool = False) -> ModelResponse:
    return ModelResponse(
        output_text=json.dumps({"observations": proposals}, ensure_ascii=False),
        stop_reason="max_tokens" if truncated else "end_turn",
        input_tokens=50,
        output_tokens=30,
        latency_ms=5,
    )


def test_recorded_chain_merges_grounded_members_and_keeps_rejected_diagnostic() -> None:
    session = _Session()
    response = _response([
        _proposal(_QUOTE),
        _proposal("Нет такой цитаты"),
        _proposal(_QUOTE, severity="critical"),
    ])
    result = publish_recorded_v2_response(
        session, response=response, text_layer=_layer(), context=_context(),
    )

    assert result.finished.response_sha256 == response.response_sha256
    assert result.finished.merge.source_proposal_ordinals == (0, 2)
    assert result.publication.finding_count == 1
    assert result.publication.observation_count == 2
    assert [member.source_proposal_ordinal for member in result.publication.findings[0].members] == [0, 2]
    assert [item.proposal_ordinal for item in result.publication.rejected] == [1]
    assert result.publication.rejected[0].failures[0].reason == "quotation_absent"
    assert session.savepoints == 1
    assert len(session.sql) == 6  # finding, two observations and evidence, canonical update
    observations = [params for sql, params in session.sql if sql.startswith("INSERT INTO finding_observation")]
    evidence = [params for sql, params in session.sql if sql.startswith("INSERT INTO finding_evidence")]
    assert [item["proposed_severity"] for item in observations] == ["operational", "critical"]
    assert all(item["finding_uid"] == result.publication.findings[0].finding_uid for item in observations)
    assert [item["quote"] for item in evidence] == [_QUOTE, _QUOTE]
    assert all(_layer().slice(item["char_start"], item["char_end"]) == item["quote"] for item in evidence)


def test_untruncated_malformed_response_never_opens_savepoint() -> None:
    session = _Session()
    response = ModelResponse('{"observations":[', "end_turn", 1, 1, 1)
    with pytest.raises(V2ResponseError, match="malformed_untruncated_response"):
        publish_recorded_v2_response(
            session, response=response, text_layer=_layer(), context=_context(),
        )
    assert session.savepoints == 0 and session.sql == []


def test_live_context_is_refused_before_processing_or_writing() -> None:
    session = _Session()
    with pytest.raises(ValueError, match="recorded_v2_context_required"):
        publish_recorded_v2_response(
            session, response=_response([_proposal(_QUOTE)]), text_layer=_layer(),
            context=replace(_context(), provider_mode="live"),
        )
    assert session.savepoints == 0 and session.sql == []


def test_ocr_only_quote_remains_diagnostic_without_finding() -> None:
    session = _Session()
    result = publish_recorded_v2_response(
        session,
        response=_response([_proposal("Только OCR: толщина 250 мм")]),
        text_layer=_layer(),
        context=_context(),
        recognised_context=(RecognisedContext(1, "Только OCR: толщина 250 мм", ()),),
    )
    assert result.publication.finding_count == 0
    assert result.publication.rejected[0].failures[0].reason == "quote_in_recognised_text"
    assert session.sql == []


def test_max_token_salvage_publishes_only_complete_grounded_proposal() -> None:
    session = _Session()
    complete = json.dumps(_proposal(_QUOTE), ensure_ascii=False)
    response = ModelResponse(
        '{"observations":[' + complete + ',{"category":"dimensions"',
        "max_tokens", 1, 1, 1,
    )
    result = publish_recorded_v2_response(
        session, response=response, text_layer=_layer(), context=_context(),
    )
    assert result.finished.truncated and result.finished.grounding.salvaged
    assert result.publication.finding_count == 1
    assert result.publication.observation_count == 1
    assert result.publication.malformed_count == 0
