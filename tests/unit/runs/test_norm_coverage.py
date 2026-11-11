"""`NORM-COVERAGE-01`: the norm verification is complete when every observation that asked a norm question has its candidates.

Prod run run_01M74QBEJZ42TEVSG43XPZDV59 (2026-11-11, section КМ): 37 observations, 14 asked a norm question and all 14 got candidates
and an assessment; 23 asked none (primary text findings, cross-check points with no query). The procedure was ``partial`` -- and
the whole run with it -- because it counted the 23 as gaps. These tests drive :func:`_full_norm_verification` on a recorded search
and a recorded model.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.runs import extended_review as er

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"


def hit(paragraph: str) -> Any:
    return SimpleNamespace(norms_snapshot_id=SNAPSHOT, norm_document_id="ndoc_1", norm_paragraph_id=paragraph,
                           designation="СП 16.13330.2017", clause_number="14.1.7", page_label="42",
                           fragment=SimpleNamespace(text="Катет углового сварного шва следует принимать по расчёту."))


def observation(index: int, *queries: str) -> dict[str, Any]:
    return {"observation_id": f"obs_{index}", "title": f"Замечание {index}", "description": "d", "source_ids": ["src_1"],
            "norm_queries": list(queries)}


class Phases:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def __call__(self, identity: str, status: str, reason: str | None = None) -> None:
        self.calls.append((identity, status, reason))


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> Phases:
    def search(session: Any, *, q: str, norms_snapshot_id: str, cursor: Any, limit: int, timeout_ms: int) -> Any:
        return SimpleNamespace(items=[] if "нет" in q else [hit("npar_" + str(abs(hash(q)) % 1000))], next_cursor=None)

    def review_request(**kwargs: Any) -> Any:
        return SimpleNamespace(payload=kwargs["payload"])

    def parse(text: str, *, observations: dict[str, Any], allowed_sources: Any) -> list[dict[str, Any]]:
        return [{"input_ids": [key], "norm_assessment": {"relation": "supports"}} for key in json.loads(text)]

    import auditmanager.analysis.public as analysis_public

    monkeypatch.setattr(er, "search_norms", search)
    monkeypatch.setattr(analysis_public, "build_norm_review_request", review_request)
    monkeypatch.setattr(analysis_public, "parse_norm_review", parse)
    return Phases()


def verify(items: list[dict[str, Any]], phases: Phases) -> None:
    def call(request: Any, identity: str) -> Any:
        return SimpleNamespace(output_text=json.dumps([row["input_id"] for row in request.payload["observations"]]))

    state = {"observations": items, "warnings": [], "sources": [{"source_id": "src_1"}], "source_sha256": "0" * 64}
    er._full_norm_verification(session=SimpleNamespace(rollback=lambda: None), run=SimpleNamespace(run_id="run_1"),
                               model_id="gpt-6-astra", section="КМ", state=state, snapshot_id=SNAPSHOT, call=call,
                               phase=phases, checkpoint=None)


def test_observations_without_a_norm_question_are_not_gaps(recorded: Phases) -> None:
    items = [observation(1, "СП 16.13330 катет шва"), observation(2, "СП 16.13330 расчет сварных швов"),
             observation(3), observation(4), observation(5)]  # 3..5: no norm question, as a primary text finding
    verify(items, recorded)
    assert recorded.calls[-1] == ("norm_verification", "completed", None)
    assert all(item.get("norm_assessment") for item in items[:2])
    assert {item["norm_reason"] for item in items[2:]} == {"query_not_proposed"}


def test_a_norm_question_without_a_paragraph_keeps_the_procedure_partial(recorded: Phases) -> None:
    items = [observation(1, "СП 16.13330 катет шва"), observation(2, "нет такого пункта"), observation(3)]
    verify(items, recorded)
    assert recorded.calls[-1] == ("norm_verification", "partial", None), "a question with no paragraph is a real gap"


def test_a_run_whose_observations_asked_no_norm_question_is_complete_with_the_reason(recorded: Phases) -> None:
    verify([observation(1), observation(2)], recorded)
    assert recorded.calls == [("norm_verification", "completed", "no_normative_question")]


def test_questions_that_found_nothing_leave_it_unavailable(recorded: Phases) -> None:
    verify([observation(1, "нет такого пункта"), observation(2)], recorded)
    assert recorded.calls == [("norm_verification", "unavailable", "candidate_context_unavailable")]
