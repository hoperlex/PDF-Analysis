"""The runtime processes retained queries and does not mark valid block answers partial."""
from __future__ import annotations

import json

import pytest

from auditmanager.runs import extended_review as er
from auditmanager.runs.norm_queries import plan_norm_queries
from tests.unit.runs.test_blocks_ensemble import Harness, default_answer
from tests.unit.runs.test_norm_any_words import SNAPSHOT, Search, Session, hit, observation


def test_literal_query_planning_retains_every_normative_passage():
    quotes = ["Требования к кабелям сохраняются.", "Требования к двигателям сохраняются.",
              "Требования к защите сохраняются."]
    planned = plan_norm_queries({"title": "Проверка", "description": "Сверить проект.",
        "source_evidence": [{"source_id": "s1", "quote": quote} for quote in quotes]})
    assert planned["queries"] == quotes
    assert [row["literal"] for row in planned["provenance"]] == quotes


@pytest.mark.parametrize("full_document", [False, True])
def test_norm_lookup_searches_the_third_and_fourth_queries(monkeypatch, full_document):
    queries = [f"Запрос {i}" for i in range(4)]
    search = Search({query: [hit(f"npar_{i}")] for i, query in enumerate(queries)})
    monkeypatch.setattr(er, "search_norms", search)
    monkeypatch.setattr(er, "_semantic_candidates", lambda *args, **kwargs: None)
    item = observation(*queries)
    receipts = []
    er._norms(Session(), [item], SNAPSHOT, full_document=full_document, lookup_receipts=receipts)
    assert search.asked == queries
    assert [candidate["paragraph_id"] for candidate in item["norm_candidates"]] == [f"npar_{i}" for i in range(4)]
    assert receipts[0]["queries_answered"] == 4
    assert receipts[0]["queries_without_answer"] == 0


def test_the_existing_search_budget_is_explicit_for_queries_beyond_its_window(monkeypatch):
    queries = [f"Запрос {i}" for i in range(13)]
    search = Search({query: [hit(f"npar_{i}")] for i, query in enumerate(queries)})
    monkeypatch.setattr(er, "search_norms", search)
    monkeypatch.setattr(er, "_semantic_candidates", lambda *args, **kwargs: None)
    item = observation(*queries)
    receipts = []
    warnings = er._norms(Session(), [item], SNAPSHOT, lookup_receipts=receipts)
    assert search.asked == queries[:12]
    assert warnings == ["norm_lookup_window_exhausted"]
    assert item["norm_reason"] == "lookup_window_exhausted"
    assert receipts[0]["queries_without_answer"] == 1


def test_v2_blocks_complete_with_three_queries_and_a_long_relationship(monkeypatch):
    reason = "Обоснование связи наблюдений. " * 30

    def answer(cell_key, request, nth):
        if cell_key in {"blocks:leg1", "blocks:leg2"}:
            document = json.loads(default_answer(cell_key, request, nth))
            document["observations"][0]["norm_queries"] = ["Норма А", "Норма Б", "Норма В"]
            return json.dumps(document)
        if cell_key == "blocks:judge":
            return json.dumps({"relationships": [{"left_ref": "leg1:001", "right_ref": "leg2:001",
                "relation": "extension", "extends": "both", "confidence": 0.98, "reason": reason.strip()}],
                "gap_observations": [], "gap_search": {"performed": True, "status": "no_new_findings",
                    "searched_categories": [], "summary": ""}})
        return default_answer(cell_key, request, nth)

    harness = Harness(monkeypatch, kit="codex_only", answer=answer)
    state = harness.run_v2(monkeypatch, blocks=1)
    stage = next(row for row in state["procedures"] if row["id"] == "block_analysis")
    assert stage["status"] == "completed"
    assert state.get("reply_refusals", []) == []
    assert state["coverage"]["blocks_processed"] == 1
    assert state["block_ensemble"]["batches"][0]["relationships"][0]["reason"] == reason.strip()
