"""`NORM-ANY-WORDS-01`: a norm query that finds nothing word-for-word is asked once more with its words joined by ``or``.

The prod run of 2026-11-11 (section КМ) sent 19 distinct norm queries from its blocks; every one found 0 paragraphs in a 674-document
snapshot, because the search wants every word of a phrase in one paragraph. These tests drive :func:`_norms` on a recorded search.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.runs import extended_review as er
from auditmanager.shared.errors import DomainError, ErrorCode

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
PHRASE = "СП 16.13330 расчет сварных соединений опорных узлов стальных балок"


def hit(paragraph: str) -> Any:
    return SimpleNamespace(norms_snapshot_id=SNAPSHOT, norm_document_id="ndoc_1", norm_paragraph_id=paragraph,
                           designation="СП 16.13330.2017", clause_number="14.1.7", page_label="42",
                           fragment=SimpleNamespace(text="Катет углового сварного шва следует принимать по расчёту."))


class Search:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def __call__(self, session: Any, *, q: str, norms_snapshot_id: str, cursor: Any, limit: int, timeout_ms: int) -> Any:
        assert norms_snapshot_id == SNAPSHOT and limit == 3
        self.asked.append(q)
        answer = self.answers.get(q, [])
        if isinstance(answer, Exception):
            raise answer
        return SimpleNamespace(items=answer, next_cursor=None)


class Session:
    def __init__(self) -> None:
        self.rollbacks = 0

    def rollback(self) -> None:
        self.rollbacks += 1


def observation(*queries: str) -> dict[str, Any]:
    return {"observation_id": "obs_1", "title": "Катет шва", "description": "d", "source_ids": ["src_1"], "norm_queries": list(queries)}


def test_the_any_words_query_keeps_the_designation_and_the_clause() -> None:
    assert er._any_words_query(PHRASE) == "СП 16.13330 расчет or сварных or соединений or опорных or узлов or стальных or балок"
    assert er._any_words_query("СП 16.13330 п. 14.1.7 катет шва") == "СП 16.13330 п. 14.1.7 катет or шва"
    assert er._any_words_query("ГОСТ 5264-80 соединение Т1 размеры швов") == "ГОСТ 5264-80 соединение or размеры or швов"
    assert er._any_words_query("СП 16.13330") is None and er._any_words_query("катет") is None, "nothing to widen"
    words = [f"слово{chr(0x430 + index) * 6}" for index in range(14)]  # letters only: a digit would extend the designation
    long = "СП 16.13330 " + " ".join(words)
    widened = er._any_words_query(long)
    assert len(long) <= 200 and widened is not None and len(widened) <= 200, "joined by or it would not fit: the tail words go"
    assert widened.startswith(f"СП 16.13330 {words[0]} or ") and widened.count(" or ") < 13


def test_a_phrase_with_no_hit_is_asked_again_with_any_of_its_words(monkeypatch: pytest.MonkeyPatch) -> None:
    widened = er._any_words_query(PHRASE)
    search = Search({widened: [hit("npar_1")]})
    monkeypatch.setattr(er, "search_norms", search)
    item = observation(PHRASE)
    receipts: list[dict[str, Any]] = []
    er._norms(Session(), [item], SNAPSHOT, full_document=True, lookup_receipts=receipts)
    assert search.asked == [PHRASE, widened]
    assert item["norm_status"] == "candidates" and [c["paragraph_id"] for c in item["norm_candidates"]] == ["npar_1"]
    assert item["norm_candidates"][0]["status"] == "candidate_not_verified", "the norm review still judges it"
    assert receipts[0]["queries"][0]["any_words_query"] == widened


def test_a_refused_second_pass_leaves_the_query_without_a_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    widened = er._any_words_query(PHRASE)
    search = Search({widened: DomainError(ErrorCode.VALIDATION_FAILED, field="q", constraint="norms_search_too_broad")})
    monkeypatch.setattr(er, "search_norms", search)
    session, item = Session(), observation(PHRASE)
    er._norms(session, [item], SNAPSHOT, full_document=True)
    assert search.asked == [PHRASE, widened] and session.rollbacks == 1
    assert item["norm_status"] == "not_found" and item["norm_candidates"] == []


def test_a_phrase_that_finds_something_is_not_widened(monkeypatch: pytest.MonkeyPatch) -> None:
    search = Search({PHRASE: [hit("npar_2")]})
    monkeypatch.setattr(er, "search_norms", search)
    item = observation(PHRASE)
    er._norms(Session(), [item], SNAPSHOT, full_document=True)
    assert search.asked == [PHRASE]
    assert [c["paragraph_id"] for c in item["norm_candidates"]] == ["npar_2"]
