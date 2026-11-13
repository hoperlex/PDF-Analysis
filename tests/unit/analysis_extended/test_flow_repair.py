"""Focused fresh-consent regressions: source binding, original merge, partial work."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from auditmanager.analysis.extended.flow_repair import (
    build_flow_review_request, consolidate_flow, current_corrections, flow_policy,
    parse_flow_comprehensive_reply, parse_flow_review_reply, validate_flow_policy,
)
from auditmanager.analysis.public import ModelResponse, finding_proposal_policy, v2_quality_policy
from auditmanager.runs import extended_review as runtime
from tests.unit.analysis_extended import test_original_review_runtime as harness
from tests.unit.analysis_extended.test_v2_quality import review_record
from tests.unit.analysis_extended.test_v2_quality_runtime import QualityAdapter


def source(ref="s1", *, kind="text", page=1, quote="Реальная цитата"):
    return {"source_id": ref, "kind": kind, "page_number": page, "quote": quote}


def observation(ref="o1", sources=None):
    return {"observation_id": ref, "origin_id": "origin_"+ref, "title": "ВРУ-К",
        "description": "Неясность расчёта ВРУ-К", "source_ids": sources or ["s1"]}


@pytest.fixture
def norm_context_reader(monkeypatch):
    from auditmanager.runs import norm_context

    def read(_session, **kwargs):
        return {"snapshot_id": kwargs["snapshot_id"], "document_id": kwargs["document_id"],
            "paragraph_id": kwargs["paragraph_id"], "search_quote_literal_in_paragraph": True,
            "primary": {"text": kwargs["quote"], "truncated": False}, "neighbors": []}

    monkeypatch.setattr(norm_context, "read_norm_paragraph_context", read)
    return read


@pytest.mark.parametrize("dependency", ["analysis/extended/core.py", "analysis/extended/review.py",
    "precedents/candidate_context.py", "runs/norm_queries.py"])
def test_changed_parser_or_human_context_requires_fresh_consent(monkeypatch, dependency):
    accepted = flow_policy()
    target = Path(runtime.__file__).resolve().parents[1] / dependency
    read_bytes = Path.read_bytes

    def changed(path):
        original = read_bytes(path)
        return original + b"\n# changed implementation\n" if path == target else original

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="flow_repair_changed_requires_consent"):
        validate_flow_policy(accepted)


def test_request_has_single_authoritative_input_id_and_per_input_evidence_allowance():
    item = {"input_id": "o1", "title": "t", "description": "d", "source_ids": ["s1"],
        "structural_checks": {"input_id": "xrd_old", "observation_id": "other"}}
    request = build_flow_review_request(model_id="m", run_id="r", section="EOM", items=[item],
        sources=[source()], context={}, image_ids=set())
    payload = json.loads(request.body["messages"][0]["content"])
    sent = payload["observations"][0]
    assert sent["input_id"] == "o1" and "input_id" not in sent["structural_checks"]
    assert sent["allowed_text_source_ids"] == ["s1"] and sent["allowed_image_source_ids"] == []
    schema = request.body["output_config"]["format"]["schema"]
    assert schema["properties"]["reviews"]["items"]["properties"]["input_id"]["enum"] == ["o1"]


def test_image_cannot_masquerade_as_literal_text_but_allowed_related_image_can_be_reviewed():
    inputs = {"o1": {"source_ids": ["s1"], "evidence_source_ids": ["s1", "img"], "context_complete": True}}
    sources = [source(), source("img", kind="image", quote="")]
    bad = review_record(source_evidence=[{"source_id": "img", "quote": "Видимое слово"}])
    rejected = []
    assert parse_flow_review_reply(json.dumps({"reviews": [bad]}), inputs=inputs, sources=sources,
        attached_image_ids={"img"}, rejected=rejected) == []
    assert rejected[0]["reason"] == "substantive_review_visual_not_literal_text"
    good = review_record(source_evidence=[], visual_evidence=[{"source_id": "img", "explanation": "Деталь на схеме"}])
    accepted = parse_flow_review_reply(json.dumps({"reviews": [good]}), inputs=inputs, sources=sources,
        attached_image_ids={"img"})
    assert accepted[0]["source_ids"] == ["s1"] and accepted[0]["llm_decision"] == "accept"


@pytest.mark.parametrize("relation,count", [("match", 1), ("extension", 1), ("disputed", 2), ("unrelated", 2)])
def test_original_semantic_merge_preserves_differently_worded_origins(relation, count):
    rows = [observation("t", ["s1"]), observation("g", ["img"])]
    rows[1].update(title="Схема питания", description="Расчётная нагрузка на схеме не согласована")
    before = deepcopy(rows)
    result = consolidate_flow(rows, sources=[source(), source("img", kind="image")], version_uid="v",
        relationships=[{"left_origin_id": "origin_t", "right_origin_id": "origin_g", "relation": relation,
            "explanation": "Один объект и режим"}])
    assert len(result["consolidated_observations"]) == count
    assert sum(group["origin_count"] for group in result["consolidated_observations"]) == 2
    assert rows == before


def test_comprehensive_keeps_valid_independent_finding_when_another_record_is_invalid():
    valid = {"title": "Новая проблема", "description": "Независимое расхождение", "source_ids": ["s1"], "norm_queries": []}
    rejected = []
    found, links, missing = parse_flow_comprehensive_reply(json.dumps({"observations": [valid,
        {**valid, "source_ids": ["foreign"]}], "relationships": []}), allowed_sources={"s1"},
        origins={"t", "g"}, required_pairs=[("g", "t")], rejected=rejected)
    assert found == [valid] and links == [] and missing == [["g", "t"]]
    assert {row["reason"] for row in rejected} == {"observation_sources_or_limits_invalid", "flow_required_pairs_missing"}


def test_current_corrector_uses_actual_suggested_fix_and_keeps_raw_text():
    item = observation()
    item["critic"] = {"original_verdict": "not_confirmed", "needs_correction": True,
        "source_dependency": "enough_source", "suggested_fix": "Сопоставить нагрузку ВРУ-К в одном режиме"}
    rows = current_corrections([item])
    assert rows[0]["candidate"]["description"] == item["critic"]["suggested_fix"]
    assert item["description"] == "Неясность расчёта ВРУ-К" and rows[0]["expert_decision"] is False


def test_current_corrector_requests_source_for_unsupported_new_numeric_detail():
    item = observation()
    item["critic"] = {"needs_correction": True, "source_dependency": "enough_source",
        "suggested_fix": "Установить автомат 400 А", "source_evidence": []}
    correction, = current_corrections([item])
    assert correction["action"] == "needs_context" and correction["candidate"] is None
    assert "чисел и марок" in correction["required_context"][0]
    assert item["description"] == "Неясность расчёта ВРУ-К"


def test_fresh_primary_member_reuses_actual_text_without_category_heading():
    item = {"observation_id": "o", "title": "missing_detail", "description": "Проверить исполнение узла",
        "source_ids": ["text:0"], "original_primary_observation": {"category": "missing_detail",
            "finding_text": "Проверить исполнение узла", "recommendation_text": "Сверить узел на листе 2"}}
    arguments = {"registry": {"text:0": source("text:0")}, "conflicts": set(), "ordinals": {"text:0": 7}}
    member = runtime._candidate_member(item, reviewable=True, **arguments)
    assert member.finding_text == "Проверить исполнение узла"
    assert member.primary_text_ordinals == (7,) and member.recommendation_text == "Сверить узел на листе 2"
    assert runtime._candidate_member(item, **arguments).finding_text == "missing_detail\n\nПроверить исполнение узла"


class FlowAdapter(QualityAdapter):
    def complete(self, request):
        payload = json.loads(request.body["messages"][0]["content"])
        if payload.get("procedure") == "comprehensive_analysis":
            self.requests.append(request)
            relationships = [{"left_origin_id": pair[0], "right_origin_id": pair[1], "relation": "match",
                "explanation": "Один вопрос одного объекта"} for pair in payload.get("required_pairs", [])]
            return ModelResponse(json.dumps({"observations": [], "relationships": relationships}), "end_turn", 100, 100, 1)
        response = super().complete(request)
        if payload.get("version") == "substantive-v2-v1":
            document = json.loads(response.output_text)
            for row in document["reviews"]:
                row.update(proposed_severity="check_adjacent", recommendation_text="Сопоставить обозначения в одном режиме")
            return ModelResponse(json.dumps(document), "end_turn", 100, 100, 1)
        return response


def test_new_flow_executes_existing_stages_with_explicit_semantic_coverage(monkeypatch):
    import auditmanager.jobs.public as jobs_public
    import auditmanager.precedents.public as precedents_public
    # This fixture drives runtime packet/correction wiring. Real DB retrieval,
    # dispatch fencing and paid-response replay have their own boundary tests.
    monkeypatch.setattr(jobs_public, "extended_context_unit", lambda *_, **__: None)
    monkeypatch.setattr(jobs_public, "has_ambiguous_provider_effect", lambda *_, **__: False)
    monkeypatch.setattr(precedents_public, "candidate_context_request", lambda _session, *, run_id, request: request, raising=False)
    monkeypatch.setattr(precedents_public, "candidate_context_receipt", lambda request: {}, raising=False)
    monkeypatch.setattr(harness, "WorkflowAdapter", FlowAdapter)
    state, adapter, saved = harness.run_v2(monkeypatch, {**harness.MARKED,
        "quality_policy": v2_quality_policy(), "finding_proposals": finding_proposal_policy(),
        "flow_repair_policy": flow_policy(), "semantic_repair_attempts": 1, "semantic_pair_call_limit": 20}, corpus=False)
    assert saved[-1][0] in {"completed", "partial"}, state["warnings"]
    assert len(state["procedures"]) == 6
    assert state["consolidation"]["version"] == "v2-flow-repair-v1"
    assert state["block_candidates"]
    assert state["comprehensive_batches"] and all(row["status"] == "completed" for row in state["procedures"][:3])
    assert state["substantive_review"]["reviewed"] == len(state["observations"])
    assert any("allowed_text_source_ids" in row for request in adapter.requests
        for row in json.loads(request.body["messages"][0]["content"]).get("observations", []))


def test_negative_norm_search_and_insufficient_assessment_are_execution_complete(monkeypatch):
    monkeypatch.setattr(runtime, "search_norms", lambda *_, **__: NS(items=[], next_cursor=None))
    item = {**observation(), "norm_queries": ["СП 16.13330.2017"]}
    state = {"observations": [item], "warnings": [], "sources": [source()], "source_sha256": "a"*64,
        "procedures": [{"id": "norm_verification"}]}
    phases = []
    runtime._full_norm_verification(session=NS(rollback=lambda: None), run=NS(run_id="r"), model_id="m",
        section="EOM", state=state, snapshot_id="s", call=lambda *_: pytest.fail("negative lookup needs no model"),
        phase=lambda *args: phases.append(args), checkpoint=None, flow_policy=flow_policy())
    assert phases[-1][1] == "completed"
    assert item["norm_status"] == "not_found" and item["finding_norm_status"] == "not_verified"
    assert state["norm_lookup_receipts"][0]["queries_answered"] == 1
    assert state["procedures"][0]["input_accounting"] == {"expected": 1, "valid": 1, "pending": 0,
        "refused": 0, "excluded": 0, "exclusion_reason": "no_normative_question"}


def test_missing_query_retains_an_implicit_norm_claim_as_undetermined(monkeypatch):
    monkeypatch.setattr(runtime, "search_norms", lambda *_, **__: pytest.fail("do not invent a query"))
    claim = {**observation(), "title": "Высота прохода",
        "description": "Высота прохода 1,8 м недостаточна для эвакуации.", "norm_queries": []}
    internal = {**observation("internal"), "category": "internal_contradiction",
        "description": "Не совпадают расчётные нагрузки в таблице и на схеме.", "norm_queries": []}
    state = {"observations": [claim, internal], "warnings": [], "sources": [source()],
        "source_sha256": "a"*64, "procedures": [{"id": "norm_verification"}]}
    phases = []
    runtime._full_norm_verification(session=NS(rollback=lambda: None), run=NS(run_id="r"), model_id="m",
        section="EOM", state=state, snapshot_id="s", call=lambda *_: pytest.fail("no added model call"),
        phase=lambda *args: phases.append(args), checkpoint=None, flow_policy=flow_policy())
    assert claim["norm_status"] == "unavailable" and claim["norm_reason"] == "normative_query_required"
    assert claim["norm_query_plan"]["reason"] == "normative_question_undetermined"
    assert claim["norm_query_plan"]["normative_question"] is None
    assert internal["norm_status"] == "not_applicable"
    assert internal["norm_reason"] == "internal_project_consistency"
    assert phases[-1] == ("norm_verification", "partial", "norm_inputs_unresolved")
    assert state["procedures"][0]["input_accounting"]["pending"] == 1
    assert state["procedures"][0]["input_accounting"]["excluded"] == 1
    legacy = {**observation(), "title": "Высота прохода",
        "description": claim["description"], "norm_queries": []}
    runtime._norms(NS(rollback=lambda: None), [legacy], "s", query_planning=True)
    assert legacy["norm_status"] == "not_applicable"
    assert legacy["norm_reason"] == "no_normative_question"


def test_broader_norm_lookup_failure_is_pending_not_a_completed_negative(monkeypatch):
    from auditmanager.shared.errors import DomainError, ErrorCode
    searched = []

    def search(*_, **kwargs):
        searched.append(kwargs["q"])
        if len(searched) == 1:
            return NS(items=[], next_cursor=None)
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE)

    monkeypatch.setattr(runtime, "search_norms", search)
    monkeypatch.setattr(runtime, "norm_embed_url", lambda: None)
    claim = {**observation(), "norm_queries": ["СП 16.13330.2017 сварные соединения"]}
    state = {"observations": [claim], "warnings": [], "sources": [source()],
        "source_sha256": "a"*64, "procedures": [{"id": "norm_verification"}]}
    phases = []
    runtime._full_norm_verification(session=NS(rollback=lambda: None), run=NS(run_id="r"), model_id="m",
        section="EOM", state=state, snapshot_id="s", call=lambda *_: pytest.fail("no normative context"),
        phase=lambda *args: phases.append(args), checkpoint=None, flow_policy=flow_policy())
    assert len(searched) == 2 and " or " in searched[1]
    assert claim["norm_status"] == "unavailable" and claim["norm_reason"] == "lookup_unavailable"
    receipt = state["norm_lookup_receipts"][0]
    assert receipt["additional_search_performed"] and receipt["queries_answered"] == 0
    assert receipt["queries"][0]["status"] == "failed"
    assert phases[-1] == ("norm_verification", "partial", "norm_inputs_unresolved")


def test_bound_negative_norm_search_never_accepts_foreign_semantic_document(monkeypatch):
    monkeypatch.setattr(runtime, "search_norms", lambda *_, **__: NS(items=[], next_cursor=None))
    monkeypatch.setattr(runtime, "norm_embed_url", lambda: "http://recorded-embed")
    calls = []
    def foreign(*args, **kwargs):
        calls.append(kwargs)
        return [{"paragraph_id": "foreign", "designation": "СП 20.13330.2020", "quote": "Нерелевантный сосед"}]
    monkeypatch.setattr(runtime, "semantic_norm_candidates", foreign)
    item = {**observation(), "description": "Проверить по СП 16.13330.2017 п. 14.1.7",
        "norm_queries": ["катет шва"]}
    receipts = []
    runtime._norms(NS(rollback=lambda: None), [item], "snapshot", full_document=True,
        query_planning=True, strict_scope=True, lookup_receipts=receipts)
    assert calls == [] and item["norm_status"] == "not_found" and item["norm_candidates"] == []
    assert item["norm_query_plan"]["semantic_lookup"] == "not_requested_bound_scope"
    assert receipts[0]["proposed_queries"] == ["СП 16.13330.2017 п. 14.1.7 катет шва"]


def test_same_paragraph_different_fragments_reach_norm_request_and_return_own_quotes(monkeypatch, norm_context_reader):
    rows = [observation("a"), observation("b")]
    def lookups(_session, items, _snapshot, **kwargs):
        for index, item in enumerate(items):
            item.update(norm_status="candidates", norm_candidates=[{"paragraph_id": "same", "quote": f"Фрагмент {index}",
                    "document_id": "doc", "snapshot_id": _snapshot}])
        return []
    monkeypatch.setattr(runtime, "_norms", lookups)
    requests = []
    def call(request, identity):
        payload = json.loads(request.body["messages"][0]["content"]); requests.append(payload)
        observations = [{"title": item["title"], "description": item["description"], "source_ids": item["source_ids"],
            "input_ids": [item["input_id"]], "norm_queries": [], "norm_assessment": {"relation": "insufficient",
                "explanation": "Цитата не доказывает факт проекта", "citations": [{"paragraph_id": item["norm_candidate_ids"][0]}]}}
            for item in payload["observations"]]
        return ModelResponse(json.dumps({"observations": observations}), "end_turn", 100, 100, 1)
    state = {"observations": rows, "warnings": [], "sources": [source()], "source_sha256": "a"*64,
        "procedures": [{"id": "norm_verification"}]}
    phases = []
    runtime._full_norm_verification(session=None, run=NS(run_id="r"), model_id="m", section="EOM", state=state,
        snapshot_id="s", call=call, phase=lambda *args: phases.append(args), checkpoint=None, flow_policy=flow_policy())
    assert {row["quote"] for item in requests[0]["norm_context_by_input"]
        for row in item["norm_candidates"]} == {"Фрагмент 0", "Фрагмент 1"}
    assert len(requests[0]["norm_paragraph_context"]["paragraphs"]) == 2
    assert [row["norm_assessment"]["citations"] for row in rows] == [
        [{"paragraph_id": "same", "quote": "Фрагмент 0"}], [{"paragraph_id": "same", "quote": "Фрагмент 1"}]]
    assert phases[-1][1] == "completed" and all(row["finding_norm_status"] == "not_verified" for row in rows)


@pytest.mark.parametrize("defect", ["missing", "truncated", "fabricated"])
def test_missing_required_norm_context_does_not_lower_the_other_input(monkeypatch, norm_context_reader, defect):
    from auditmanager.runs import norm_context
    from auditmanager.shared.errors import DomainError, ErrorCode
    rows = [observation("n0"), observation("n1")]

    def lookups(_session, items, _snapshot, **_kwargs):
        for index, item in enumerate(items):
            item.update(norm_status="candidates", norm_candidates=[{"snapshot_id": "s", "document_id": "d",
                "paragraph_id": "same", "quote": f"Фрагмент {index}"}])
        return []

    def read(session, **kwargs):
        if kwargs["quote"] == "Фрагмент 0" and defect == "missing":
            raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE)
        context = norm_context_reader(session, **kwargs)
        if kwargs["quote"] == "Фрагмент 0":
            if defect == "truncated":
                context["primary"]["truncated"] = True
            else:
                context["search_quote_literal_in_paragraph"] = False
        return context

    monkeypatch.setattr(runtime, "_norms", lookups)
    monkeypatch.setattr(norm_context, "read_norm_paragraph_context", read)

    def call(request, _identity):
        payload = json.loads(request.body["messages"][0]["content"])
        outputs = [{"title": item["title"], "description": item["description"], "source_ids": item["source_ids"],
            "input_ids": [item["input_id"]], "norm_queries": [], "norm_assessment": {"relation": "supports",
                "explanation": "Модель предложила нормативную связь", "citations": [{"paragraph_id": item["norm_candidate_ids"][0]}]}}
            for item in payload["observations"]]
        return ModelResponse(json.dumps({"observations": outputs}), "end_turn", 100, 100, 1)

    state = {"observations": rows, "warnings": [], "sources": [source()], "source_sha256": "a"*64,
        "procedures": [{"id": "norm_verification"}]}
    phases = []
    runtime._full_norm_verification(session=None, run=NS(run_id="r"), model_id="m", section="EOM", state=state,
        snapshot_id="s", call=call, phase=lambda *args: phases.append(args), checkpoint=None, flow_policy=flow_policy())
    assert rows[0]["norm_review_status"] == rows[1]["norm_review_status"] == "reviewed"
    assert rows[0]["normative_context"]["complete"] is False
    assert rows[0]["finding_norm_status"] == "not_verified"
    assert rows[1]["normative_context"]["complete"] is True
    assert rows[1]["finding_norm_status"] == "partially_verified"
    assert state["procedures"][0]["input_accounting"]["valid"] == 1
    assert state["procedures"][0]["input_accounting"]["pending"] == 1
    assert phases[-1] == ("norm_verification", "partial", "norm_inputs_unresolved")


def test_cross_page_object_pair_is_actually_colocated_in_a_priced_packet():
    text = observation("t", ["text:0"])
    visual = observation("g", ["blk_"+"0"*32])
    state = {"text_items": [text], "sources": [source("text:0", page=1),
        source("blk_"+"0"*32, kind="image", page=2)], "source_sha256": "a"*64, "coverage": {}}
    packets = []
    def call(request, identity):
        payload = json.loads(request.body["messages"][0]["content"]); packets.append(payload)
        links = [{"left_origin_id": pair[0], "right_origin_id": pair[1], "relation": "extension",
            "explanation": "Два описания одной неясности ВРУ-К"} for pair in payload["required_pairs"]]
        return ModelResponse(json.dumps({"observations": [], "relationships": links}), "end_turn", 100, 100, 1)
    runtime._full_comprehensive_review(run=NS(run_id="r", version_uid="v"), model_id="m", section="EOM",
        state=state, pages=[{"page_number": 1, "text": "ВРУ-К расчёт"}, {"page_number": 2, "text": "ВРУ-К схема"}],
        block_items=[visual], call=call, flow_policy=flow_policy(), pair_call_limit=1, phase=lambda *_: None)
    joined = [packet for packet in packets if packet["pair_packet"]]
    assert len(joined) == 1 and joined[0]["text_observations"] and joined[0]["visual_observations"]
    assert state["semantic_pair_coverage"]["expected"] == state["semantic_pair_coverage"]["valid"] == 1
    assert state["semantic_pair_coverage"]["pending"] == 0


def test_late_unreadable_comprehensive_batch_preserves_checkpointed_success():
    state = {"text_items": [], "sources": [], "source_sha256": "a"*64, "coverage": {}}
    snapshots = []
    def call(request, identity):
        payload = json.loads(request.body["messages"][0]["content"])
        if identity != "comprehensive:0":
            return ModelResponse("unreadable", "end_turn", 100, 100, 1)
        finding = {"title": "Сохранённый вопрос", "description": "Конкретная инженерная неясность",
            "source_ids": [payload["native_context"][0]["source_id"]], "norm_queries": []}
        return ModelResponse(json.dumps({"observations": [finding], "relationships": []}), "end_turn", 100, 100, 1)
    found = runtime._full_comprehensive_review(run=NS(run_id="r", version_uid="v"), model_id="m", section="EOM",
        state=state, pages=[{"page_number": 1, "text": "Исходный текст"}, {"page_number": 2, "text": "Другой текст"}],
        block_items=[], call=call, flow_policy=flow_policy(), pair_call_limit=0,
        phase=lambda *_: snapshots.append(deepcopy(state["observations"])))
    assert len(found) == 1 and snapshots[0][0]["title"] == "Сохранённый вопрос"
    assert state["observations"][0]["title"] == "Сохранённый вопрос"
    assert state["comprehensive_execution_complete"] is False


def test_disputed_identical_members_cannot_be_rejoined_through_a_third_member():
    rows = [observation("a"), observation("b"), observation("c")]
    links = [{"left_origin_id": "origin_a", "right_origin_id": "origin_b", "relation": "disputed", "explanation": "Конфликт"},
        {"left_origin_id": "origin_a", "right_origin_id": "origin_c", "relation": "match", "explanation": "Сходство"},
        {"left_origin_id": "origin_b", "right_origin_id": "origin_c", "relation": "match", "explanation": "Сходство"}]
    result = consolidate_flow(rows, sources=[source()], version_uid="v", relationships=links)
    groups = result["consolidated_observations"]
    assert len(groups) == 2
    assert all(not {"a", "b"} <= {origin["observation_id"] for origin in group["origin_records"]} for group in groups)


def test_unknown_repair_outcome_does_not_erase_valid_first_comprehensive_records():
    from auditmanager.shared.errors import DomainError, ErrorCode
    state = {"text_items": [], "sources": [], "source_sha256": "a"*64, "coverage": {}}
    snapshots = []
    def call(request, identity):
        if identity.endswith(":repair:1"):
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="extended_provider_outcome_unknown")
        payload = json.loads(request.body["messages"][0]["content"])
        valid = {"title": "Первый вопрос", "description": "Реальная неясность",
            "source_ids": [payload["native_context"][0]["source_id"]], "norm_queries": []}
        return ModelResponse(json.dumps({"observations": [valid, {**valid, "source_ids": ["invented"]}],
            "relationships": []}), "end_turn", 100, 100, 1)
    with pytest.raises(DomainError):
        runtime._full_comprehensive_review(run=NS(run_id="r", version_uid="v"), model_id="m", section="EOM",
            state=state, pages=[{"page_number": 1, "text": "Текст"}], block_items=[], call=call,
            flow_policy=flow_policy(), pair_call_limit=0, phase=lambda *_: snapshots.append(deepcopy(state["observations"])))
    assert snapshots[-1][0]["title"] == state["observations"][0]["title"] == "Первый вопрос"


def test_norm_missing_input_gets_one_addressed_repair_without_rewriting_valid_answer(monkeypatch, norm_context_reader):
    rows = [observation("a"), observation("b")]
    def lookups(_session, items, _snapshot, **kwargs):
        for item in items:
            item.update(norm_status="candidates", norm_candidates=[{"paragraph_id": "p", "quote": "Реальный абзац",
                "snapshot_id": _snapshot, "document_id": "doc"}])
        return []
    monkeypatch.setattr(runtime, "_norms", lookups)
    calls, snapshots = [], []
    def call(request, identity):
        calls.append(identity)
        payload = json.loads(request.body["messages"][0]["content"])
        chosen = payload["observations"][1 if identity.endswith(":repair:1") else 0]
        if identity.endswith(":repair:1"):
            schema = request.body["output_config"]["format"]["schema"]
            assert schema["properties"]["observations"]["maxItems"] == 1
            assert schema["properties"]["observations"]["items"]["properties"]["input_ids"]["items"]["enum"] == [chosen["input_id"]]
            assert rows[0]["norm_review_status"] == "reviewed"
        output = {"title": chosen["title"], "description": chosen["description"], "source_ids": chosen["source_ids"],
            "norm_queries": [], "input_ids": [chosen["input_id"]], "norm_assessment": {"relation": "supports",
                "explanation": "Только нормативная связь", "citations": [{"paragraph_id": chosen["norm_candidate_ids"][0]}]}}
        return ModelResponse(json.dumps({"observations": [output]}), "end_turn", 100, 100, 1)
    state = {"observations": rows, "warnings": [], "sources": [source()], "source_sha256": "a"*64,
        "procedures": [{"id": "norm_verification"}]}
    runtime._full_norm_verification(session=None, run=NS(run_id="r"), model_id="m", section="EOM", state=state,
        snapshot_id="s", call=call, phase=lambda *_: snapshots.append(deepcopy(rows)), checkpoint=None, flow_policy=flow_policy())
    assert len(calls) == 2 and all(item["norm_review_status"] == "reviewed" for item in rows)
    assert state["reply_refusals"][0]["status"] == "resolved"
    assert rows[0]["norm_assessment"]["citations"] == [{"paragraph_id": "p", "quote": "Реальный абзац"}]


def test_two_required_pairs_complete_from_first_a_and_addressed_repair_b():
    text = observation("t", ["text:0"])
    visuals = [observation("g1", ["img1"]), observation("g2", ["img2"])]
    state = {"text_items": [text], "sources": [source("text:0"), source("img1", kind="image"),
        source("img2", kind="image")], "source_sha256": "a"*64, "coverage": {}}
    calls = []
    def call(request, identity):
        calls.append(identity)
        payload = json.loads(request.body["messages"][0]["content"])
        pair = payload["required_pairs"][0]
        if identity.endswith(":repair:1"):
            feedback = json.loads(request.body["messages"][-1]["content"])
            assert len(feedback["required_pairs"]) == len(feedback["accepted_relationships"]) == 1
            pair = feedback["required_pairs"][0]
        return ModelResponse(json.dumps({"observations": [], "relationships": [{"left_origin_id": pair[0],
            "right_origin_id": pair[1], "relation": "match", "explanation": "Один вопрос"}]}), "end_turn", 100, 100, 1)
    runtime._full_comprehensive_review(run=NS(run_id="r", version_uid="v"), model_id="m", section="EOM",
        state=state, pages=[{"page_number": 1, "text": "ВРУ-К"}], block_items=visuals, call=call,
        flow_policy=flow_policy(), pair_call_limit=0, phase=lambda *_: None)
    assert calls == ["comprehensive:0", "comprehensive:0:repair:1"]
    assert state["semantic_pair_coverage"]["valid"] == state["semantic_pair_coverage"]["expected"] == 2
    assert state["semantic_pair_coverage"]["pending"] == 0 and state["comprehensive_execution_complete"] is True
    assert state["comprehensive_batches"][0]["missing_pairs"] == []
    assert state["comprehensive_batches"][0]["unresolved_records"] == []


def test_wrapper_failure_after_valid_rows_publishes_partial_readable_candidates(monkeypatch):
    import auditmanager.jobs.public as jobs_public
    from auditmanager.shared.errors import DomainError, ErrorCode
    monkeypatch.setattr(jobs_public, "has_ambiguous_provider_effect", lambda *_, **__: False)
    class UnknownRepair(FlowAdapter):
        def complete(self, request):
            payload = json.loads(request.body["messages"][0]["content"])
            if payload.get("procedure") == "comprehensive_analysis":
                self.requests.append(request)
                if len(request.body["messages"]) > 1:
                    raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="extended_provider_outcome_unknown")
                valid = {"title": "Сохранённая комплексная находка", "description": "Конкретная проблема",
                    "source_ids": [payload["native_context"][0]["source_id"]], "norm_queries": []}
                return ModelResponse(json.dumps({"observations": [valid, {**valid, "source_ids": ["foreign"]}],
                    "relationships": []}), "end_turn", 100, 100, 1)
            return super().complete(request)
    monkeypatch.setattr(harness, "WorkflowAdapter", UnknownRepair)
    state, _, saved = harness.run_v2(monkeypatch, {**harness.MARKED,
        "quality_policy": v2_quality_policy(), "finding_proposals": finding_proposal_policy(),
        "flow_repair_policy": flow_policy(), "semantic_repair_attempts": 1, "semantic_pair_call_limit": 2}, corpus=False)
    assert saved[-1][0] == "partial" and state["execution_failure_reason"] == "extended_provider_outcome_unknown"
    procedure = next(p for p in state["procedures"] if p["id"] == "comprehensive_analysis")
    assert procedure["status"] == "failed" and procedure["reason"] == "extended_provider_outcome_unknown"
    groups, unread = runtime.read_candidate_groups({"artifact_role": "analysis.extended_review", "run_id": "run",
        "version_uid": harness.VERSION, "status": saved[-1][0], "result": saved[-1][1]}, run_id="run", version_uid=harness.VERSION)
    assert groups and not unread
    assert any("Сохранённая комплексная находка" in member.finding_text for group in groups for member in group.members)
