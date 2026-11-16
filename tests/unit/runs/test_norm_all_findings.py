"""`NORM-ALL-FINDINGS-01` (owner 2026-11-16): every finding is checked by the norms.

The prod run ``run_01M7HH1MPV5W1FEZMX5ZK29PTA`` (section KJ, 43 findings) checked 18: 25 had no norm query, 15 got paragraphs from an any-words
fallback that returned unrelated text, and the paragraph-context budget delivered 7 of 52 contexts. What is held here, with the model, the
corpus and the embedding service all stubbed (no database, no network):

* B1 -- the norm stage model formulates queries for the findings that have none, one batched call per forty, only for those, before any lookup;
  its record is read per record and cannot name a paragraph;
* B2 -- a finding that asked a question and has no query is still looked up by meaning;
* B3 -- a query that names a standard is answered by meaning inside that standard, the whole-snapshot lookup otherwise, the word search with a
  named warning when the service is off, a failed service as a gap;
* B4 -- every candidate's paragraph context is delivered, in as many calls as it takes;
* B5 -- the estimate prices the planning calls and the context batches, and a consent of the previous code is refused;
* the planning call belongs to the «Нормы» chip and runs on the norms cell.

New symbols are imported inside the tests, so each test reports on the base commit instead of failing the collection of the file.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace as NS
from typing import Any

import pytest

from auditmanager.analysis.extended.flow_repair import flow_policy
from auditmanager.analysis.public import ModelResponse
from auditmanager.runs import extended_review as runtime

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
PLANNING = "norm_verification:queries:"
QUERY = "СП 16.13330 расчёт закладных деталей"


# ------------------------------------------------------------------------------------------------------------------ fixtures


def finding(ref: str, **more: Any) -> dict[str, Any]:
    """A flow observation as the block legs leave it: no ``norm_queries``, so its plan is ``requires_query``."""
    return {"observation_id": ref, "origin_id": "origin_" + ref, "title": f"Замечание {ref}",
            "description": "Закладная деталь без проверки на выдёргивание", "source_ids": ["s1"], **more}


def hit(paragraph: str, text: str = "Фрагмент нормы", *, document: str = "ndoc_1") -> NS:
    return NS(norms_snapshot_id=SNAPSHOT, norm_document_id=document, norm_paragraph_id=paragraph, designation="СП 16.13330.2017",
              clause_number="14.1.7", page_label=3, fragment=NS(text=text))


def page(*hits: NS) -> NS:
    return NS(items=list(hits), next_cursor=None)


def candidate(paragraph: str, text: str = "Фрагмент нормы") -> dict[str, Any]:
    return {"snapshot_id": SNAPSHOT, "document_id": "ndoc_1", "paragraph_id": paragraph, "designation": "СП 16.13330.2017",
            "clause_number": "14.1.7", "quote": text, "page_label": 3, "status": "candidate_not_verified"}


class Model:
    """The norm stage model: answers the planning call from ``decisions`` (by finding title) and the review call with ``supports``."""

    def __init__(self, decisions: dict[str, str] | None = None, *, forget: frozenset[str] = frozenset(),
                 forget_on_repair: bool = False, query: str = QUERY) -> None:
        self.decisions, self.forget, self.forget_on_repair, self.query = decisions or {}, forget, forget_on_repair, query
        self.calls: list[tuple[str, Any, dict[str, Any]]] = []

    @property
    def identities(self) -> list[str]:
        return [identity for identity, _, _ in self.calls]

    def planning_calls(self) -> list[tuple[str, Any, dict[str, Any]]]:
        return [row for row in self.calls if row[0].startswith(PLANNING)]

    def __call__(self, request: Any, identity: str) -> ModelResponse:
        payload = json.loads(request.body["messages"][0]["content"])
        self.calls.append((identity, request, payload))
        if identity.startswith(PLANNING):
            return self.plan(request, identity, payload)
        outputs = [{"title": row["title"], "description": row["description"], "source_ids": row["source_ids"],
                    "input_ids": [row["input_id"]], "norm_queries": [], "norm_assessment": {
                        "relation": "supports", "explanation": "Модель предложила нормативную связь",
                        "citations": [{"paragraph_id": row["norm_candidate_ids"][0]}]}}
                   for row in payload["observations"]]
        return ModelResponse(json.dumps({"observations": outputs}), "end_turn", 100, 100, 1)

    def plan(self, request: Any, identity: str, payload: dict[str, Any]) -> ModelResponse:
        repairing = identity.endswith(":repair:1")
        allowed = request.body["output_config"]["format"]["schema"]["properties"]["plans"]["items"]["properties"]["input_id"]["enum"]
        rows = []
        for row in payload["observations"]:
            if row["input_id"] not in allowed or (row["title"] in self.forget and (not repairing or self.forget_on_repair)):
                continue
            decision = self.decisions.get(row["title"], "search")
            rows.append({"input_id": row["input_id"], "decision": decision, "queries": [self.query] if decision == "search" else [],
                         "reason": "" if decision == "search" else "Внутренняя сверка данных проекта"})
        return ModelResponse(json.dumps({"plans": rows}), "end_turn", 100, 100, 1)


@pytest.fixture
def corpus(monkeypatch: pytest.MonkeyPatch) -> NS:
    """The corpus: a word search that answers by query text, no embedding service, and a paragraph reader of a settable size."""
    from auditmanager.runs import norm_context

    state = NS(searched=[], answers={}, context_characters=1500, reads=[])

    def search(_session: Any, *, q: str, **_kwargs: Any) -> NS:
        state.searched.append(q)
        return state.answers.get(q, page())

    def read(_session: Any, **kwargs: Any) -> dict[str, Any]:
        state.reads.append(kwargs["paragraph_id"])
        return {"snapshot_id": kwargs["snapshot_id"], "document_id": kwargs["document_id"], "paragraph_id": kwargs["paragraph_id"],
                "search_quote_literal_in_paragraph": True, "neighbors": [],
                "primary": {"text": "т" * state.context_characters, "truncated": False}}

    monkeypatch.setattr(runtime, "search_norms", search)
    monkeypatch.setattr(runtime, "norm_embed_url", lambda: None)
    monkeypatch.setattr(norm_context, "read_norm_paragraph_context", read)
    return state


def stage(rows: list[dict[str, Any]], model: Model) -> tuple[dict[str, Any], list[tuple[Any, ...]]]:
    state = {"observations": rows, "warnings": [], "sources": [{"source_id": "s1", "kind": "text", "page_number": 1, "quote": "Цитата"}],
             "source_sha256": "a" * 64, "procedures": [{"id": "norm_verification"}]}
    phases: list[tuple[Any, ...]] = []
    runtime._full_norm_verification(session=NS(rollback=lambda: None), run=NS(run_id="r"), model_id="m", section="KJ", state=state,
                                    snapshot_id=SNAPSHOT, call=model, phase=lambda *args: phases.append(args), checkpoint=None,
                                    flow_policy=flow_policy())
    return state, phases


# ------------------------------------------------------------------------------------------------------------------------ B1


def test_the_planning_request_is_one_strict_batch_on_the_norms_row() -> None:
    from auditmanager.analysis.public import build_norm_query_request

    rows = [{"input_id": f"xnq_{i}", "title": f"T{i}", "description": f"D{i}", "source_ids": ["s1"]} for i in range(3)]
    request = build_norm_query_request(model_id="m", run_id="r", section="KJ", payload={"observations": rows, "source_sha256": "a" * 64})
    schema = request.body["output_config"]["format"]["schema"]
    item = schema["properties"]["plans"]["items"]
    assert schema["additionalProperties"] is False and item["additionalProperties"] is False
    assert item["properties"]["input_id"]["enum"] == ["xnq_0", "xnq_1", "xnq_2"]
    assert item["properties"]["decision"]["enum"] == ["search", "no_normative_question"]
    assert item["properties"]["queries"]["maxItems"] == 3 and set(item["required"]) == {"input_id", "decision", "queries", "reason"}
    assert json.loads(request.body["messages"][0]["content"])["observations"] == rows
    with pytest.raises(ValueError, match="norm_query_planning_window_invalid"):
        build_norm_query_request(model_id="m", run_id="r", section="KJ", payload={"observations": rows * 15})  # duplicate ids and > 40
    with pytest.raises(ValueError, match="norm_query_planning_window_invalid"):
        build_norm_query_request(model_id="m", run_id="r", section="KJ", payload={"observations": []})


def test_a_record_is_search_text_or_no_question_and_one_bad_record_costs_only_itself() -> None:
    from auditmanager.analysis.public import parse_norm_queries

    inputs = {key: {} for key in ("a", "b", "c", "d", "e", "f", "g")}
    rows = [
        {"input_id": "a", "decision": "search", "queries": ["  СП 16.13330   расчёт  узлов ", "сп 16.13330 расчёт узлов", "ГОСТ 5264-80 швы"], "reason": ""},
        {"input_id": "b", "decision": "no_normative_question", "queries": [], "reason": "Внутреннее несоответствие данных"},
        {"input_id": "c", "decision": "search", "queries": ["абзац npar_01M2545JSD15ETSNNV904X991J"], "reason": ""},  # an invented identifier
        {"input_id": "d", "decision": "no_normative_question", "queries": ["всё же запрос"], "reason": "x"},
        {"input_id": "e", "decision": "search", "queries": ["а", "б", "в", "г"], "reason": ""},  # four queries
        {"input_id": "zzz", "decision": "search", "queries": ["запрос"], "reason": ""},  # an input this call never carried
        {"input_id": "a", "decision": "search", "queries": ["повтор"], "reason": ""},  # the same input again
        {"input_id": "f", "decision": "search", "queries": [], "reason": ""},  # search with nothing to search
        {"input_id": "g", "decision": "search", "queries": ["запрос"], "reason": "", "paragraph_id": "npar_x"},  # a field the schema has not
    ]
    rejected: list[dict[str, Any]] = []
    accepted = parse_norm_queries(json.dumps({"plans": rows}, ensure_ascii=False), inputs=inputs, rejected=rejected)
    assert [(row["input_id"], row["decision"]) for row in accepted] == [("a", "search"), ("b", "no_normative_question")]
    assert accepted[0]["queries"] == ["СП 16.13330 расчёт узлов", "ГОСТ 5264-80 швы"], "whitespace collapsed, the repeat dropped"
    assert [row["reason"] for row in rejected] == [
        "norm_query_identifier_invented", "norm_query_no_question_invalid", "norm_query_queries_invalid",
        "norm_query_input_binding_invalid", "norm_query_input_binding_invalid", "norm_query_queries_invalid",
        "norm_query_record_shape_invalid"]
    with pytest.raises(ValueError, match="norm_query_identifier_invented"):
        parse_norm_queries(json.dumps({"plans": rows[2:3]}, ensure_ascii=False), inputs=inputs)
    for text in ("not json", json.dumps({"plans": "x"}), json.dumps({"plans": [], "extra": 1}), json.dumps(["x"])):
        with pytest.raises(ValueError):
            parse_norm_queries(text, inputs=inputs, rejected=[])


def test_only_findings_without_a_query_are_asked_in_batches_of_forty_before_any_lookup(corpus: NS) -> None:
    asked = [finding(f"n{i:02d}") for i in range(45)]
    proposed = finding("own", norm_queries=["ГОСТ 5264-80 швы"])
    internal = finding("internal", category="internal_contradiction")
    model = Model()
    corpus.answers[QUERY] = page(hit("npar_1", "Закладные детали рассчитывают на выдёргивание"))
    corpus.answers["ГОСТ 5264-80 швы"] = page(hit("npar_2", "Швы сварных соединений"))
    state, phases = stage([*asked[:20], proposed, *asked[20:], internal], model)
    assert [identity for identity, _, _ in model.planning_calls()] == [PLANNING + "0", PLANNING + "1"]
    carried = [[row["title"] for row in payload["observations"]] for _, _, payload in model.planning_calls()]
    assert [len(batch) for batch in carried] == [40, 5]
    assert sorted(title for batch in carried for title in batch) == sorted(item["title"] for item in asked)
    assert "Замечание own" not in sum(carried, []) and "Замечание internal" not in sum(carried, [])
    first_review = next(position for position, identity in enumerate(model.identities) if not identity.startswith(PLANNING))
    assert all(identity.startswith(PLANNING) for identity in model.identities[:first_review]) and first_review == 2
    assert QUERY in corpus.searched and "ГОСТ 5264-80 швы" in corpus.searched
    assert state["norm_query_planning"][0]["inputs"] == 40 and state["norm_query_planning"][1]["inputs"] == 5


def test_the_models_queries_are_searched_and_recorded_as_model_proposed_with_their_provenance(corpus: NS) -> None:
    corpus.answers[QUERY] = page(hit("npar_1", "Закладные детали рассчитывают на выдёргивание"))
    row = finding("one")
    state, phases = stage([row], Model())
    assert corpus.searched == [QUERY]
    assert row["norm_status"] == "candidates" and row["norm_candidates"][0]["paragraph_id"] == "npar_1"
    plan = row["norm_query_plan"]
    assert (plan["status"], plan["reason"], plan["queries"]) == ("model_proposed", "model_query_planning", [QUERY])
    assert plan["provenance"][0]["source_kind"] == "model_query_planning" and plan["provenance"][0]["literal"] == QUERY
    receipt = state["norm_lookup_receipts"][0]
    assert receipt["query_plan"]["status"] == "model_proposed" and receipt["proposed_queries"] == [QUERY]
    assert receipt["query_plan"]["provenance"][0]["source_kind"] == "model_query_planning"
    assert row["norm_review_status"] == "reviewed" and phases[-1] == ("norm_verification", "completed", None)


def test_the_model_saying_there_is_no_question_is_a_label_the_lookup_counts_excluded(corpus: NS) -> None:
    rows = [finding("a", title="Расчётная нагрузка не совпадает"), finding("b")]
    corpus.answers[QUERY] = page(hit("npar_1"))
    model = Model({"Расчётная нагрузка не совпадает": "no_normative_question"})
    state, phases = stage(rows, model)
    asked, searched = rows
    assert (asked["norm_status"], asked["norm_reason"]) == ("not_applicable", "model_no_normative_question")
    assert asked["norm_query_plan"]["status"] == "not_applicable" and asked["norm_query_plan"]["planning"]["model_reason"]
    assert (asked["norm_review_status"], asked["finding_norm_status"]) == ("not_required", "not_applicable")
    assert corpus.searched == [QUERY], "the finding with no question is never searched"
    accounting = state["procedures"][0]["input_accounting"]
    assert accounting["outcomes"]["not_applicable"] == 1 and accounting["excluded"] == 1
    assert accounting["technical"] == {} and phases[-1][1] == "completed"


def test_a_missing_record_gets_one_repair_and_a_record_still_missing_is_a_gap_with_its_reason(corpus: NS) -> None:
    rows = [finding("a", title="Первое"), finding("b", title="Второе"), finding("c", title="Третье")]
    repaired = Model(forget=frozenset({"Второе"}))
    state, phases = stage(deepcopy(rows), repaired)
    assert repaired.identities[:2] == [PLANNING + "0", PLANNING + "0:repair:1"]
    ids = repaired.calls[1][1].body["output_config"]["format"]["schema"]["properties"]["plans"]["items"]["properties"]["input_id"]["enum"]
    assert len(ids) == 1, "the repair asks for the one record that is missing"
    assert phases[-1][1] == "completed" and state["reply_refusals"][0]["status"] == "resolved"

    stuck = Model(forget=frozenset({"Второе"}), forget_on_repair=True)
    gapped = deepcopy(rows)
    state, phases = stage(gapped, stuck)
    assert stuck.identities.count(PLANNING + "0:repair:1") == 1, "one repair, no more"
    second = next(item for item in gapped if item["title"] == "Второе")
    assert (second["norm_status"], second["norm_reason"]) == ("unavailable", "norm_query_planning_refused")
    assert second["norm_review_status"] == "not_reviewed" and QUERY in corpus.searched
    assert phases[-1] == ("norm_verification", "partial", "norm_inputs_unresolved")
    assert state["procedures"][0]["input_accounting"]["technical"] == {"norm_query_planning_refused": 1}


def test_a_finding_that_already_carries_its_plan_is_not_asked_again(corpus: NS) -> None:
    model = Model()
    done = finding("a", norm_query_plan={"status": "model_proposed", "queries": [QUERY]})
    state = {"observations": [done], "warnings": [], "sources": [], "source_sha256": "a" * 64, "procedures": [{"id": "norm_verification"}]}
    assert runtime._plan_norm_queries_with_model(state=state, items=[done], snapshot_id=SNAPSHOT, model_id="m", section="KJ", settings=None,
                                                 run=NS(run_id="r"), call=model, phase=lambda *_: None) == {} and model.calls == []


def test_no_planning_call_is_paid_when_nothing_would_be_searched(corpus: NS) -> None:
    model = Model()
    row = finding("a")
    state = {"observations": [row], "warnings": [], "sources": [], "source_sha256": "a" * 64, "procedures": [{"id": "norm_verification"}]}
    plans = runtime._plan_norm_queries_with_model(state=state, items=[row], snapshot_id=None, model_id="m", section="KJ", settings=None,
                                                  run=NS(run_id="r"), call=model, phase=lambda *_: None)
    assert plans == {} and model.calls == []


# ---------------------------------------------------------------------------------------- the planning call belongs to «Нормы»


@pytest.mark.parametrize("identity", [PLANNING + "0", PLANNING + "3", PLANNING + "0:repair:1"])
def test_the_planning_call_is_placed_on_the_norms_chip_and_row(identity: str) -> None:
    """The cell binding of these identities is held in ``test_stage_plan_binding`` (``norms:main``)."""
    from auditmanager.runs import stage_layout as layout
    from auditmanager.runs.stage_facts import chip_of_call, chip_of_phase

    assert layout.row_of_phase(identity) == "norms" and layout.role_of_phase(identity) == "main"
    assert chip_of_phase("v2:" + identity) == "norms" == chip_of_call(None, {"extended_phase": "v2:" + identity})


# ------------------------------------------------------------------------------------------------------------------------ B2


def embedded(monkeypatch: pytest.MonkeyPatch, *, whole=None, scoped=None) -> NS:
    log = NS(whole=[], scoped=[])
    monkeypatch.setattr(runtime, "norm_embed_url", lambda: "http://norm-embed:8080")

    def snapshot_wide(_session: Any, **kwargs: Any) -> list[dict[str, Any]]:
        log.whole.append(kwargs)
        return [candidate("npar_w1"), candidate("npar_w2")] if whole is None else whole(kwargs)

    def in_documents(_session: Any, **kwargs: Any) -> Any:
        from auditmanager.norms.public import ScopedSemanticResult

        log.scoped.append(kwargs)
        found = [candidate("npar_d1", "Из названного документа")] if scoped is None else scoped(kwargs)
        return ScopedSemanticResult(kwargs["designation"], ("ndoc_1",) if found else (), found)

    monkeypatch.setattr(runtime, "semantic_norm_candidates", snapshot_wide)
    # ``raising=False``: on the base commit the scoped lookup does not exist, and the B2 test must fail there on its own assertion
    monkeypatch.setattr(runtime, "semantic_norm_candidates_in_documents", in_documents, raising=False)
    return log


def test_a_finding_that_asked_a_question_and_has_no_query_is_still_looked_up_by_meaning(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    """The regression: ``(unavailable, normative_query_required)`` was not a semantic target, so such a finding was never looked up. Fails on
    the base commit (no lookup, the finding stays «норма не названа»)."""
    log = embedded(monkeypatch)
    row = finding("a", title="Высота прохода", description="Высота прохода 1,8 м недостаточна для эвакуации.")
    runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                   lookup_receipts=[])
    assert len(log.whole) == 1 and log.scoped == [], "no query names no document: the whole snapshot"
    assert row["norm_status"] == "candidates" and [c["paragraph_id"] for c in row["norm_candidates"]] == ["npar_w1", "npar_w2"]
    assert corpus.searched == [], "no query, so no word search"


def test_the_windowed_path_keeps_its_semantic_targets(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the flow reaches ``normative_query_required``; the other paths keep ``not_found`` and ``query_not_proposed``."""
    log = embedded(monkeypatch)
    rows = [finding("a", norm_status="unavailable", norm_reason="normative_query_required"),
            finding("b", norm_status="unavailable", norm_reason="query_not_proposed")]
    runtime._semantic_candidates(NS(rollback=lambda: None), rows, SNAPSHOT, checkpoint=None, warnings=[], full_document=True,
                                 url="http://norm-embed:8080")
    assert len(log.whole) == 1 and rows[0]["norm_status"] == "unavailable" and rows[1]["norm_status"] == "candidates"


# ------------------------------------------------------------------------------------------------------------------------ B3


def test_a_query_that_names_a_standard_is_answered_by_meaning_inside_it_and_the_any_words_fallback_is_not_run(
        corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    log = embedded(monkeypatch)
    row = finding("a", norm_queries=["СП 16.13330 расчёт сварных соединений опорных узлов"])
    receipts: list[dict[str, Any]] = []
    warnings = runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True,
                              strict_scope=True, lookup_receipts=receipts)
    assert corpus.searched == ["СП 16.13330 расчёт сварных соединений опорных узлов"], "the exact search only: no ' or ' relaxation"
    assert [call["designation"] for call in log.scoped] == ["СП 16.13330"] and log.whole == []
    assert log.scoped[0]["value"] == "Замечание a\nЗакладная деталь без проверки на выдёргивание"
    assert row["norm_status"] == "candidates" and row["norm_candidates"][0]["paragraph_id"] == "npar_d1"
    assert row["norm_lookup_method"] == "semantic_temporary", "the label the screen already reads"
    assert receipts[0]["norm_lookup_method"] == "semantic_scoped" and receipts[0]["status"] == "candidates"
    assert receipts[0]["semantic_lookups"] == [{"scope": "document", "designation": "СП 16.13330", "document_ids": ["ndoc_1"], "candidates": 1}]
    assert receipts[0]["queries"][0]["any_words_replaced_by_semantic"] is True and "norm_semantic_lookup_off" not in warnings


def test_a_query_that_names_no_document_is_answered_over_the_whole_snapshot(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    log = embedded(monkeypatch)
    row = finding("a", norm_queries=["расчёт закладных деталей на выдёргивание"])
    receipts: list[dict[str, Any]] = []
    runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                   lookup_receipts=receipts)
    assert len(log.whole) == 1 and log.scoped == []
    assert receipts[0]["norm_lookup_method"] == "semantic" and row["norm_lookup_method"] == "semantic_temporary"


def test_a_finding_that_names_two_standards_is_looked_up_in_each_and_a_lookup_counts_once(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    log = embedded(monkeypatch, scoped=lambda kwargs: [candidate("npar_" + kwargs["designation"].split()[0], "q")])
    row = finding("a", norm_queries=["СП 16.13330 швы", "ГОСТ 5264-80 швы", "швы сварных соединений"])
    runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                   lookup_receipts=[])
    assert [call["designation"] for call in log.scoped] == ["СП 16.13330", "ГОСТ 5264-80"] and len(log.whole) == 1
    assert {candidate["paragraph_id"] for candidate in row["norm_candidates"]} >= {"npar_СП", "npar_ГОСТ", "npar_w1"}
    assert len(row["norm_candidates"]) <= 6


def test_a_designation_the_snapshot_does_not_hold_is_not_found_and_never_another_standard(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    log = embedded(monkeypatch, scoped=lambda kwargs: [])
    row = finding("a", norm_queries=["СП 99.99999 расчёт"])
    receipts: list[dict[str, Any]] = []
    runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                   lookup_receipts=receipts)
    assert log.whole == [] and row["norm_status"] == "not_found" and row["norm_candidates"] == []
    assert receipts[0]["semantic_lookups"][0]["document_ids"] == [] and receipts[0]["norm_lookup_method"] == "semantic_scoped"


def test_without_the_service_address_the_word_search_stays_and_the_run_says_so(corpus: NS) -> None:
    receipts: list[dict[str, Any]] = []
    row = finding("a", norm_queries=["СП 16.13330 расчёт сварных соединений опорных узлов"])
    corpus.answers["СП 16.13330 расчёт сварных соединений опорных узлов"] = page()
    corpus.answers["СП 16.13330 расчёт or сварных or соединений or опорных or узлов"] = page(hit("npar_9", "Нашлось по словам"))
    warnings = runtime._norms(NS(rollback=lambda: None), [row], SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                              lookup_receipts=receipts)
    assert len(corpus.searched) == 2 and " or " in corpus.searched[1], "the fallback still runs"
    assert row["norm_status"] == "candidates" and "norm_lookup_method" not in row
    assert receipts[0]["norm_lookup_method"] == "word"
    assert "norm_semantic_lookup_off" in warnings
    quiet = runtime._norms(NS(rollback=lambda: None), [finding("b", norm_queries=["x"])], None, full_document=True, query_planning=True,
                           strict_scope=True, lookup_receipts=[])
    assert "norm_semantic_lookup_off" not in quiet, "no corpus at all is its own outcome, not a missing service"


def test_a_failed_service_is_a_named_gap_with_its_traceback_and_never_the_fallback(corpus: NS, monkeypatch: pytest.MonkeyPatch,
                                                                                 caplog: pytest.LogCaptureFixture) -> None:
    from auditmanager.norms.public import SemanticUnavailable

    def down(_kwargs: Any) -> list[dict[str, Any]]:
        raise SemanticUnavailable("norm-embed did not answer: URLError")

    embedded(monkeypatch, whole=down, scoped=down)
    rows = [finding("a", norm_queries=["СП 16.13330 швы"]), finding("b", norm_queries=["швы"])]
    with caplog.at_level(logging.ERROR):
        warnings = runtime._norms(NS(rollback=lambda: None), rows, SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                                  lookup_receipts=[])
    assert [(row["norm_status"], row["norm_reason"]) for row in rows] == [("unavailable", "semantic_lookup_failed")] * 2
    assert "norm_semantic_lookup_failed" in warnings
    assert len(corpus.searched) == 2, "the exact search only: a failure does not fall back to the any-words search"
    assert any("norm semantic lookup failed" in record.getMessage() and record.exc_info for record in caplog.records)
    from auditmanager.runs.norm_stage_accounting import account_norm_inputs
    outcome = account_norm_inputs(rows)
    assert (outcome.status, outcome.reason) == ("partial", "norm_inputs_unresolved")


def test_the_window_of_semantic_lookups_is_three_hundred_and_counts_lookups(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    assert runtime._SEMANTIC_LOOKUPS_PER_RUN == 300
    log = embedded(monkeypatch, scoped=lambda kwargs: [])
    monkeypatch.setattr(runtime, "_SEMANTIC_LOOKUPS_PER_RUN", 3)
    rows = [finding("a", norm_queries=["СП 1.1 x", "СП 2.2 x"]), finding("b", norm_queries=["СП 3.3 x", "СП 4.4 x"])]
    warnings = runtime._norms(NS(rollback=lambda: None), rows, SNAPSHOT, full_document=True, query_planning=True, strict_scope=True,
                              lookup_receipts=[])
    assert len(log.scoped) == 2, "the first finding took two of the three lookups; the second needs two and does not start"
    assert rows[0]["norm_status"] == "not_found"
    assert (rows[1]["norm_status"], rows[1]["norm_reason"]) == ("unavailable", "semantic_lookup_window_exhausted")
    assert "norm_semantic_lookup_window_exhausted" in warnings


# ------------------------------------------------- the scoped lookup itself: SQL on a recording session and the embedding HTTP stub


class Result:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def all(self) -> list[Any]:
        return self.rows

    def one_or_none(self) -> Any:
        return self.rows[0] if self.rows else None

    def scalar_one_or_none(self) -> Any:
        return self.rows[0] if self.rows else None


class Recorder:
    """A session that answers the four statements of the scoped lookup and records them."""

    def __init__(self, documents: list[NS]) -> None:
        self.documents, self.log = documents, []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Result:
        sql = getattr(statement, "text", str(statement))
        self.log.append((sql, params))
        if "FROM norm_document d" in sql and "designation_tokens" in sql:
            return Result(self.documents if params["designation"].startswith("СП") else [])
        if "FROM norm_embedding_build" in sql:
            return Result(["chunking-profile-1"])
        if "FROM norm_embedding e" in sql and "norm_document_pk IN" in sql:
            return Result([NS(norm_chunk_pk=11, window_ordinal=0, inner_product=0.9), NS(norm_chunk_pk=12, window_ordinal=1, inner_product=0.8)])
        if "norm_paragraph p" in sql:
            chunk = params["chunk"]
            return Result([NS(norm_paragraph_id=f"npar_{chunk}", clause_number="14.1.7", text="Текст абзаца", page_label=4,
                              norm_document_id="ndoc_A", slug="sp_16_13330_2017")])
        raise AssertionError(sql)


UNIT = [1.0] + [0.0] * 1023


def test_the_scoped_lookup_resolves_the_designation_then_searches_only_those_documents() -> None:
    from auditmanager.norms.public import semantic_norm_candidates_in_documents

    session = Recorder([NS(norm_document_pk=7, norm_document_id="ndoc_A"), NS(norm_document_pk=9, norm_document_id="ndoc_B")])
    embedded: list[str] = []
    result = semantic_norm_candidates_in_documents(session, snapshot_id=SNAPSHOT, value="катет шва", url="http://x", designation="СП 16.13330",
                                                   limit=2, embed=lambda url, value: embedded.append(value) or UNIT)
    assert embedded == ["катет шва"] and result.document_ids == ("ndoc_A", "ndoc_B")
    assert [c["paragraph_id"] for c in result.candidates] == ["npar_11", "npar_12"] and result.candidates[0]["status"] == "candidate_not_verified"
    nearest = next(params for sql, params in session.log if "FROM norm_embedding e" in sql)
    assert nearest["documents"] == [7, 9] and nearest["snapshot"] == SNAPSHOT and nearest["chunking_profile"] == "chunking-profile-1"
    sql = next(sql for sql, _ in session.log if "FROM norm_embedding e" in sql)
    assert "+ 0" in sql and "norm_document_pk IN" in sql, "an exact scan of those documents, not a filtered HNSW walk"


def test_a_designation_that_resolves_to_no_document_embeds_nothing_and_returns_nothing() -> None:
    from auditmanager.norms.public import semantic_norm_candidates_in_documents

    session = Recorder([])
    result = semantic_norm_candidates_in_documents(session, snapshot_id=SNAPSHOT, value="x", url="http://x", designation="ГОСТ 5264-80",
                                                   embed=lambda *_: pytest.fail("nothing to search, nothing to embed"))
    assert result.document_ids == () and result.candidates == [] and len(session.log) == 1


def test_the_scoped_lookup_goes_through_the_embedding_http_service() -> None:
    from auditmanager.norms.public import semantic_norm_candidates_in_documents

    seen: list[Any] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            body = json.dumps({"vectors": [UNIT]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = semantic_norm_candidates_in_documents(Recorder([NS(norm_document_pk=7, norm_document_id="ndoc_A")]), snapshot_id=SNAPSHOT,
                                                       value="катет углового шва", url=f"http://127.0.0.1:{server.server_address[1]}",
                                                       designation="СП 16.13330", limit=1)
    finally:
        server.shutdown()
    assert seen == [("/v1/embed", {"texts": ["катет углового шва"]})] and len(result.candidates) == 1


# ------------------------------------------------------------------------------------------------------------------------ B4


def candidate_rows(item_ref: str, count: int, *, size: int = 40) -> list[dict[str, Any]]:
    return [{"snapshot_id": SNAPSHOT, "document_id": "ndoc_1", "paragraph_id": f"npar_{item_ref}_{n}", "designation": "СП 16.13330.2017",
             "clause_number": "1", "quote": "К" * size + f" {item_ref}-{n}", "page_label": 1, "status": "candidate_not_verified"}
            for n in range(count)]


def with_candidates(monkeypatch: pytest.MonkeyPatch, per_item: dict[str, int]) -> None:
    def lookups(_session: Any, items: list[dict[str, Any]], _snapshot: Any, **_kwargs: Any) -> list[str]:
        for item in items:
            item.update(norm_status="candidates", norm_candidates=candidate_rows(item["observation_id"], per_item[item["observation_id"]]))
        return []

    monkeypatch.setattr(runtime, "_norms", lookups)


def delivered(model: Model) -> list[list[str]]:
    return [[row["paragraph_id"] for row in payload["norm_paragraph_context"]["paragraphs"]]
            for identity, _, payload in model.calls if not identity.startswith(PLANNING) and ":repair:" not in identity]


def test_every_candidates_context_is_delivered_in_as_many_calls_as_it_takes(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    """The shape of the prod run: 52 distinct paragraph contexts. The old budget (12 paragraphs, 18 000 characters) delivered 7 of them and the
    rest of the assessments ran on a cut context. Fails on the base commit."""
    from auditmanager.runs import norm_context

    corpus.context_characters = 2000
    per_item = {f"o{n:02d}": 4 for n in range(13)}
    with_candidates(monkeypatch, per_item)
    rows = [finding(ref, norm_queries=["x"]) for ref in per_item]
    model = Model()
    state, phases = stage(rows, model)
    batches = delivered(model)
    assert len(batches) >= 3, "52 contexts do not fit one call"
    assert sum(len(batch) for batch in batches) == 52 and len({paragraph for batch in batches for paragraph in batch}) == 52
    budget = norm_context.policy()
    for identity, _, payload in model.calls:
        context = payload["norm_paragraph_context"]
        assert context["contexts_not_provided"] == 0 and context["contexts_provided"] == context["candidate_quote_contexts"]
        assert len(context["paragraphs"]) <= budget["max_paragraphs"]
        assert len(json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))) <= budget["max_characters"]
    assert all(row["normative_context"]["complete"] for row in rows)
    assert all(row["norm_review_reason"] is None for row in rows), "norm_paragraph_context_incomplete appears nowhere"
    assert state["norm_batch_plan"] == {"batches": len(batches), "candidate_inputs": 13, "over_budget_inputs": 0,
                                        "contexts_read": 52, "contexts_unavailable": 0}
    assert sorted(corpus.reads) == sorted(set(corpus.reads)), "every context is read once, not once for the packing and once more for the call"
    assert phases[-1] == ("norm_verification", "completed", None)


def test_a_context_two_inputs_share_is_carried_once_and_inputs_keep_their_order(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    def lookups(_session: Any, items: list[dict[str, Any]], _snapshot: Any, **_kwargs: Any) -> list[str]:
        for item in items:
            item.update(norm_status="candidates", norm_candidates=candidate_rows("shared", 2))
        return []

    monkeypatch.setattr(runtime, "_norms", lookups)
    model = Model()
    stage([finding("a", norm_queries=["x"]), finding("b", norm_queries=["x"])], model)
    assert len(delivered(model)) == 1 and len(delivered(model)[0]) == 2, "two inputs, two distinct contexts, one call"


def test_one_input_whose_own_contexts_fit_no_call_is_a_technical_gap_with_its_reason(corpus: NS, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus.context_characters = 6000
    with_candidates(monkeypatch, {"huge": 12, "small": 1})
    rows = [finding("huge", norm_queries=["x"]), finding("small", norm_queries=["x"])]
    model = Model()
    state, phases = stage(rows, model)
    huge, small = rows
    assert (huge["norm_status"], huge["norm_reason"]) == ("unavailable", "norm_paragraph_context_over_budget")
    assert (huge["norm_review_status"], huge["norm_review_reason"], huge["finding_norm_status"]) == (
        "not_reviewed", "norm_paragraph_context_over_budget", "not_verified")
    assert small["norm_review_status"] == "reviewed" and small["normative_context"]["complete"] is True
    assert all(huge["norm_candidates"][0]["paragraph_id"] not in batch for batch in delivered(model)), "never sent on a cut context"
    assert phases[-1] == ("norm_verification", "partial", "norm_inputs_unresolved")
    assert state["procedures"][0]["input_accounting"]["technical"] == {"norm_paragraph_context_over_budget": 1}
    assert state["norm_batch_plan"]["over_budget_inputs"] == 1


def test_a_call_stays_inside_the_per_call_input_ceiling() -> None:
    from auditmanager.runs import norm_context

    budget = norm_context.policy()
    assert budget["input_tokens_per_call"] == 100_000
    # observation part + context part, at the estimate's 5/7 token per character, is the ceiling of one call
    assert (norm_context.OBSERVATION_CHARACTERS_PER_CALL + budget["max_characters"]) * 5 / 7 <= budget["input_tokens_per_call"]
    assert norm_context.validate_policy(budget)
    for stale in ({"max_paragraphs": 12}, {"max_characters": 18_000}):
        with pytest.raises(ValueError, match="norm_paragraph_context_changed_requires_consent"):
            norm_context.validate_policy({**budget, **stale})


# ------------------------------------------------------------------------------------------------------------------------ B5

FLOW_ESTIMATE_BASE = {"calls": 375, "input_tokens": 36_645_582, "output_tokens": 4_330_000}  # 0.28.1, version("AR", 500, 1), v2 flow


def estimate_flow(monkeypatch: pytest.MonkeyPatch) -> Any:
    from auditmanager.analysis.text.profile_registry import load_text_profile_registry
    from tests.unit.runs.test_cost_preflight import estimate, service, version

    monkeypatch.delenv("AUDITMANAGER_V2_QUALITY", raising=False)
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v2")
    return estimate(service(load_text_profile_registry()), version("AR", 500, 1))


def test_the_estimate_prices_the_planning_calls_and_the_extra_context_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    """One page: 13 image calls, 16 comprehensive calls and 1 window make 30 norm calls (one per forty findings the calls above can return).
    Fails on the base commit (375 calls)."""
    from auditmanager.runs.norm_context import estimated_calls_per_review_call

    value = estimate_flow(monkeypatch)
    public = value.as_dict()
    norm_calls = 30
    queries = math.ceil(norm_calls * 40 / 40)
    contexts = norm_calls * (estimated_calls_per_review_call() - 1)
    assert estimated_calls_per_review_call() == 11 and (queries, contexts) == (30, 300)
    added = queries + contexts
    assert public["calls"] == FLOW_ESTIMATE_BASE["calls"] + 2 * added, "every call is also reserved one repair"
    assert public["input_tokens"] == FLOW_ESTIMATE_BASE["input_tokens"] + 2 * added * 100_000
    assert public["output_tokens"] == FLOW_ESTIMATE_BASE["output_tokens"] + 2 * added * 12_000


def test_a_planned_estimate_puts_the_same_calls_on_the_norms_row_and_the_totals_agree(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.analysis.text.profile_registry import load_text_profile_registry
    from tests.unit.runs import test_stage_plan_consent as planned

    monkeypatch.delenv("AUDITMANAGER_V2_QUALITY", raising=False)
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v2")
    monkeypatch.setattr(planned.Preflight, "version", planned.source_version("AR", 500, 1))
    seen: dict[str, Any] = {}
    original = planned.Preflight._value_planned

    def capture(self: Any, **kwargs: Any) -> Any:
        seen.update(kwargs["ledger"])
        return original(self, **kwargs)

    monkeypatch.setattr(planned.Preflight, "_value_planned", capture)
    value = planned.estimate(planned.service(load_text_profile_registry()), planned.draft())
    # the norms cell: 30 review calls, 330 planning and context calls, and one repair for each of the 360
    assert seen["norms:main"][0] == 30 + 330 + 360
    assert seen["norms:main"][1] == (30 + 330 + 360) * 100_000
    lines = value.as_dict()["models"]
    assert sum(line["calls"] for line in lines) == value.as_dict()["calls"]
    assert sum(line["input_tokens"] for line in lines) == value.as_dict()["input_tokens"]


def test_a_fresh_windowed_consent_carries_the_context_policy_it_will_be_validated_against(monkeypatch: pytest.MonkeyPatch) -> None:
    """The windowed path (v3) does not run the flow, but it shares the norm paragraph context: the consent a fresh estimate freezes must pass
    the strict check at its run's start, and the consent frozen with the old budget must not (it is asked again)."""
    from auditmanager.analysis.text.profile_registry import load_text_profile_registry
    from auditmanager.runs import norm_context
    from tests.unit.runs.test_cost_preflight import estimate, service, version

    monkeypatch.delenv("AUDITMANAGER_V2_QUALITY", raising=False)
    monkeypatch.setenv("AUDITMANAGER_EXTENDED_ANALYSIS_PLAN", "v3")
    value = estimate(service(load_text_profile_registry()), version("AR", 500, 1))
    frozen = json.loads(value.authority_json)["extended_review"]["norm_paragraph_context_policy"]
    assert frozen == norm_context.policy() and norm_context.validate_policy(frozen)
    old_budget = {**frozen, "max_paragraphs": 12, "max_characters": 18_000}
    for compare_bundle in (True, False):
        with pytest.raises(ValueError, match="norm_paragraph_context_changed_requires_consent"):
            norm_context.validate_policy(old_budget, compare_bundle=compare_bundle)
    with pytest.raises(ValueError, match="norm_paragraph_context_changed_requires_consent"):
        norm_context.validate_policy({**frozen, "bundle_sha256": "0" * 64})


def test_the_consent_of_the_previous_code_is_refused_and_the_fresh_estimate_runs_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.analysis.public import validate_flow_repair_policy

    value = estimate_flow(monkeypatch)
    authority = json.loads(value.authority_json)
    accepted = value.approve({"estimate_digest": value.estimate_digest,
                              "ceiling_micros": value.as_dict()["recommended_ceiling_micros"], "confirmed": True}, actor_user_uid="expert")
    flow = accepted["extended_review"]["flow_repair_policy"]
    assert flow == authority["extended_review"]["flow_repair_policy"] == flow_policy()
    assert validate_flow_repair_policy(flow, compare_bundle=False), "the approval's shape check"
    assert validate_flow_repair_policy(flow), "the run's start: the digest is the digest of the code that runs"
    stale = {**flow, "bundle_sha256": "410f1310291f2d5746824a33e82e3d04ebc0b896397049fb1433a1b81455bbf0"}
    assert validate_flow_repair_policy(stale, compare_bundle=False)
    with pytest.raises(ValueError, match="flow_repair_changed_requires_consent"):
        validate_flow_repair_policy(stale)
    changed = deepcopy(authority)
    changed["extended_review"]["flow_repair_policy"] = stale
    from auditmanager.runs import preflight
    assert preflight._digest(changed) != value.estimate_digest, "an old digest is another estimate: the user is asked again"
