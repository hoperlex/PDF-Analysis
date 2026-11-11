"""`NORM-VECTOR-TEMP-01` (temporary): candidates near an observation's meaning, behind ``AUDITMANAGER_NORM_EMBED_URL``.

No service and no database: the embedder is a local HTTP stub and the vector search a recorder. What these hold:
* the client asks ``POST /v1/embed`` and returns a unit vector, and refuses an answer it cannot use;
* the run looks up only observations a word search left without a paragraph (nothing found, or no query proposed), and nothing at
  all when the address is unset;
* a failure turns the lookup off for the run with a warning -- the run goes on.
"""

from __future__ import annotations

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from auditmanager.norms import semantic
from auditmanager.runs import extended_review as er

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"


def _serve(answer: Any) -> tuple[ThreadingHTTPServer, str, list[Any]]:
    seen: list[Any] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            body = json.dumps(answer).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}", seen


def test_the_client_returns_the_services_vector_as_a_unit_vector() -> None:
    server, url, seen = _serve({"vectors": [[3.0, 4.0] + [0.0] * 1022]})
    try:
        vector = semantic.embed_text(url, "катет углового шва")
    finally:
        server.shutdown()
    assert seen == [("/v1/embed", {"texts": ["катет углового шва"]})]
    assert len(vector) == 1024 and vector[:2] == [0.6, 0.8] and math.isclose(sum(v * v for v in vector), 1.0)


@pytest.mark.parametrize("answer", [{"vectors": []}, {"vectors": [[1.0] * 3]}, {"vectors": [[0.0] * 1024]}, {"oops": 1}, ["x"]])
def test_an_unusable_answer_is_refused(answer: Any) -> None:
    server, url, _ = _serve(answer)
    try:
        with pytest.raises(semantic.SemanticUnavailable):
            semantic.embed_text(url, "x")
    finally:
        server.shutdown()


def test_a_service_that_does_not_answer_is_refused() -> None:
    with pytest.raises(semantic.SemanticUnavailable):
        semantic.embed_text("http://127.0.0.1:9", "x", timeout=1.0)


def test_the_address_is_read_from_the_environment_and_blank_is_off() -> None:
    assert semantic.norm_embed_url({}) is None and semantic.norm_embed_url({semantic.EMBED_URL_ENV: "  "}) is None
    assert semantic.norm_embed_url({semantic.EMBED_URL_ENV: "http://norm-embed:8080"}) == "http://norm-embed:8080"


def candidate(paragraph: str) -> dict[str, Any]:
    return {"snapshot_id": SNAPSHOT, "document_id": "ndoc_1", "paragraph_id": paragraph, "designation": "СП 16.13330.2017",
            "clause_number": "14.1.7", "quote": "Катет углового сварного шва…", "page_label": 42, "status": "candidate_not_verified"}


class Session:
    def __init__(self) -> None:
        self.rollbacks = 0

    def rollback(self) -> None:
        self.rollbacks += 1


def items() -> list[dict[str, Any]]:
    return [
        {"title": "Противоречие в марке стали", "description": "С245 и С255", "norm_status": "unavailable", "norm_reason": "query_not_proposed"},
        {"title": "Катет шва", "description": "6 мм", "norm_status": "not_found", "norm_reason": None},
        {"title": "Уже найдено", "description": "d", "norm_status": "candidates", "norm_candidates": [candidate("npar_w")]},
        {"title": "Не нормативный", "description": "d", "norm_status": "not_applicable", "norm_reason": "no_normative_question"},
        {"title": "Поиск отказал", "description": "d", "norm_status": "unavailable", "norm_reason": "lookup_unavailable"},
    ]


def test_only_observations_left_without_a_paragraph_are_looked_up(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    def lookup(session: Any, *, snapshot_id: str, value: str, url: str, limit: int) -> list[dict[str, Any]]:
        asked.append(value)
        return [candidate("npar_s" + str(len(asked)))]

    monkeypatch.setattr(er, "semantic_norm_candidates", lookup)
    observations, warnings = items(), []
    er._semantic_candidates(Session(), observations, SNAPSHOT, checkpoint=None, warnings=warnings, full_document=True,
                            url="http://norm-embed:8080")
    assert asked == ["Противоречие в марке стали\nС245 и С255", "Катет шва\n6 мм"]
    assert [item["norm_status"] for item in observations[:2]] == ["candidates", "candidates"]
    assert {item.get("norm_lookup_method") for item in observations[:2]} == {"semantic_temporary"}
    assert observations[2]["norm_candidates"] == [candidate("npar_w")] and "norm_lookup_method" not in observations[2]
    assert observations[3]["norm_status"] == "not_applicable" and observations[4]["norm_status"] == "unavailable"
    assert warnings == []


def test_nothing_is_looked_up_when_the_address_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(semantic.EMBED_URL_ENV, raising=False)
    monkeypatch.setattr(er, "semantic_norm_candidates", lambda *a, **k: pytest.fail("called with the feature off"))
    observations = items()
    er._semantic_candidates(Session(), observations, SNAPSHOT, checkpoint=None, warnings=[], full_document=True)
    assert observations == items()


@pytest.mark.parametrize("failure", [semantic.SemanticUnavailable("norm-embed did not answer"),
                                     __import__("sqlalchemy.exc").exc.OperationalError("SELECT", {}, Exception("gone"))])
def test_a_failure_is_a_named_gap_never_a_quiet_skip(monkeypatch: pytest.MonkeyPatch, failure: Exception,
                                                     caplog: pytest.LogCaptureFixture) -> None:
    calls = []

    def lookup(session: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append(kwargs["value"])
        raise failure

    monkeypatch.setattr(er, "semantic_norm_candidates", lookup)
    session, observations, warnings = Session(), items(), []
    er._semantic_candidates(session, observations, SNAPSHOT, checkpoint=None, warnings=warnings, full_document=True,
                            url="http://norm-embed:8080")
    assert len(calls) == 1 and session.rollbacks == 1
    assert warnings == ["norm_semantic_lookup_failed"]
    assert [(item["norm_status"], item["norm_reason"]) for item in observations[:2]] == [
        ("unavailable", "semantic_lookup_failed"), ("unavailable", "semantic_lookup_failed")], "every target says why"
    assert er._asked_norm_question(observations[0]) and er._asked_norm_question(observations[1]), "so the procedure is partial"
    assert any("norm semantic lookup failed" in record.getMessage() and record.exc_info for record in caplog.records)


def test_lookups_past_the_window_are_named_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(er, "_SEMANTIC_LOOKUPS_PER_RUN", 1)
    monkeypatch.setattr(er, "semantic_norm_candidates", lambda session, **kwargs: [])
    observations, warnings = items(), []
    er._semantic_candidates(Session(), observations, SNAPSHOT, checkpoint=None, warnings=warnings, full_document=True,
                            url="http://norm-embed:8080")
    assert observations[0]["norm_reason"] == "query_not_proposed", "looked up, nothing near: still no question"
    assert (observations[1]["norm_status"], observations[1]["norm_reason"]) == ("unavailable", "semantic_lookup_window_exhausted")
    assert warnings == ["norm_semantic_lookup_window_exhausted"]


def test_the_word_search_runs_the_semantic_step_last(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(er, "search_norms", lambda session, **kwargs: SimpleNamespace(items=[], next_cursor=None))
    monkeypatch.setenv(semantic.EMBED_URL_ENV, "http://norm-embed:8080")
    monkeypatch.setattr(er, "semantic_norm_candidates", lambda session, **kwargs: [candidate("npar_v")])
    item = {"observation_id": "obs_1", "title": "Катет шва", "description": "6 мм", "source_ids": ["s"],
            "norm_queries": ["СП 16.13330 катет углового шва опорного узла"]}
    er._norms(Session(), [item], SNAPSHOT, full_document=True)
    assert item["norm_status"] == "candidates" and item["norm_lookup_method"] == "semantic_temporary"
    assert [c["paragraph_id"] for c in item["norm_candidates"]] == ["npar_v"]
