"""The v2 workflow with the original's deterministic critic and corrector (`V2-ORIGINAL-REVIEW-01`): wiring, not the checks.

The checks themselves are `test_original_deterministic.py`. Here: what a v2 consent with the marker does after the norms, that one
without the marker is what it was, and that a defect in the new step is a visible failed procedure that keeps the paid results.
"""
from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace as NS
import json

from auditmanager.analysis.public import CostMeter, ProviderConfig, ProviderMode
from auditmanager.runs import extended_review as runtime
from tests.unit.analysis_extended.test_core import VERSION, documents
from tests.unit.analysis_extended.test_runtime import Jobs, Journal, Session, Store
from tests.unit.analysis_extended.test_workflow_runtime import WorkflowAdapter

V2 = {"enabled": True, "max_blocks": "all", "plan_version": "extended-review-v2"}
MARKED = {**V2, "original_review": "deterministic-v1"}
QUOTE = "Толщина утеплителя наружной стены 150 мм"
#: One primary text observation whose quotation stands on page 7, not on the page 3 it states.
PRIMARY = {"observations": [{"category": "Теплотехника", "finding_text": "Утеплитель тоньше нормы", "evidence": [{"page_number": 3, "quote": QUOTE}]}]}
NOT_REVIEW_KEYS = {"critic", "review_status", "correction"}


def run_v2(monkeypatch, policy, *, observations_document=None, corpus=True):
    portal, manifest, blobs = documents(10)
    texts = {n: "Настоящий текст страницы" for n in range(1, 11)}
    texts[7] = f"Раздел 2. {QUOTE}. Далее по тексту."
    docs = {"geometry.portal_blocks": portal, "geometry.page_crops": manifest,
        "prepared.text_layer": {"pages": [{"page_number": n, "text": text} for n, text in texts.items()]},
        "context.document_graph": {"sections": []}}
    for role, doc in docs.items():
        blobs[role] = json.dumps(doc).encode()
    monkeypatch.setattr(runtime, "DocumentRepository", lambda: NS(get_version=lambda *_: NS(
        classification=NS(section_code="AR"), page_count=10)))
    import auditmanager.analysis.public as public
    monkeypatch.setattr(public, "read_artifact", lambda _store, bid, **_: (docs[str(bid)], "a" * 64))
    monkeypatch.setattr(runtime, "parse_blob_id", lambda value: value)
    monkeypatch.setattr(runtime, "extended_unit", lambda *_args, **_kw: None)
    monkeypatch.setattr(runtime, "search_norms", lambda _session, **kwargs: NS(items=(NS(
        norms_snapshot_id="snapshot", norm_document_id="doc", norm_paragraph_id="paragraph",
        designation="СП", clause_number="1", fragment=NS(text="Реальная цитата"), page_label=1),)))
    adapter, saved = WorkflowAdapter(), []

    def publish(_role, doc):
        raw = json.dumps(doc).encode()
        key = "reply" + str(len(blobs))
        blobs[key] = raw
        return NS(blob_id=key, sha256=sha256(raw).hexdigest(), size_bytes=len(raw))
    result = runtime.run_extended_review(Session(), run=NS(run_id="run", version_uid=VERSION), authority=NS(), jobs=Jobs(), journal=Journal(),
        binding=NS(adapter=adapter, config=ProviderConfig(ProviderMode.RECORDED, "claude-opus-5", 50., None, False), call=None),
        outputs=NS(refs={k: NS(blob_id=k) for k in docs}), store=Store(blobs), meter=CostMeter(50.), publish=publish,
        progress=lambda status, value: saved.append((status, json.loads(json.dumps(value)))), checkpoint=lambda _: None,
        observations_document=observations_document, snapshot_id="snapshot" if corpus else None, policy=policy)
    return result, adapter, saved


def plain(observation):
    return {key: value for key, value in observation.items() if key not in NOT_REVIEW_KEYS}


def test_a_marked_consent_runs_the_critic_and_the_corrector_after_the_norms_without_a_call(monkeypatch):
    marked, marked_adapter, saved = run_v2(monkeypatch, MARKED, observations_document=PRIMARY)
    bare, bare_adapter, bare_saved = run_v2(monkeypatch, V2, observations_document=PRIMARY)
    # no model call and no cost: the same requests, in the same number
    assert len(marked_adapter.requests) == len(bare_adapter.requests) >= 4
    assert [r.idempotency_scope for r in marked_adapter.requests] == [r.idempotency_scope for r in bare_adapter.requests]
    procedures = {p["id"]: p for p in marked["procedures"]}
    assert list(procedures) == ["block_analysis", "comprehensive_analysis", "finding_merge", "norm_verification",
        "finding_review", "finding_correction"]
    assert procedures["finding_review"]["status"] == procedures["finding_correction"]["status"] == "completed"
    assert procedures["finding_review"]["model_called"] is False and procedures["finding_correction"]["model_called"] is False
    assert saved[0][1]["procedures"][-1]["id"] == "finding_correction" and all(p["status"] == "queued" for p in saved[0][1]["procedures"])
    # the two procedures add no degradation: the run ends as the run without them ends
    assert saved[-1][0] == bare_saved[-1][0] and marked["workflow_version"] == "extended-review-v2"
    # every observation is reviewed, and nothing but the review annotations differs from the run without the marker
    assert marked["observations"] and all(o["review_status"] == "reviewed" and o["critic"]["mode"] == "deterministic" for o in marked["observations"])
    assert [plain(o) for o in marked["observations"]] == bare["observations"]
    flagged = [o for o in marked["observations"] if o["critic"]["original_verdict"] == "page_mismatch"]
    assert len(flagged) == 1 and flagged[0]["correction"]["action"] == "propose_revision"
    assert flagged[0]["correction"]["candidate"]["description"].startswith(flagged[0]["description"])
    assert flagged[0]["correction"]["original"]["description"] == flagged[0]["description"]
    assert all(o["critic"]["llm_decision"] != "reject" for o in marked["observations"])
    review = marked["original_review"]
    assert review["reviewed"] == len(marked["observations"]) and review["verdicts"]["page_mismatch"] == 1
    assert review["proposals"] == {"propose_revision": 1} and review["model_called"] is False and review["proposals_only"] is True


def test_a_consent_without_the_marker_is_what_it_was(monkeypatch):
    result, adapter, saved = run_v2(monkeypatch, V2, observations_document=PRIMARY)
    assert [p["id"] for p in result["procedures"]] == ["block_analysis", "comprehensive_analysis", "finding_merge", "norm_verification"]
    assert "original_review" not in result and all(not (NOT_REVIEW_KEYS & set(o)) for o in result["observations"])
    assert all("original_review" not in state for _, state in saved)
    assert runtime.planned_workflow_result(policy=V2) == runtime.planned_workflow_result()
    assert runtime.planned_workflow_result(policy=None) == runtime.planned_workflow_result()


def test_the_marker_means_nothing_to_another_plan_or_another_word():
    assert runtime._original_review_enabled(MARKED) is True
    assert runtime._original_review_enabled(V2) is False and runtime._original_review_enabled(None) is False
    assert runtime._original_review_enabled({**MARKED, "plan_version": "extended-review-v3"}) is False
    assert runtime._original_review_enabled({**MARKED, "original_review": "deterministic-v2"}) is False


def test_an_unknown_marker_is_a_failed_review_and_never_a_run_without_the_critic(monkeypatch):
    result, adapter, saved = run_v2(monkeypatch, {**V2, "original_review": "deterministic-v2"})
    assert saved[-1][0] == "failed" and "original_review_policy_invalid" in result["warnings"]
    assert adapter.requests == [] and all(p["status"] in {"failed", "skipped"} for p in result["procedures"])


def test_a_defect_in_the_critic_is_a_visible_failed_procedure_and_keeps_the_paid_results(monkeypatch):
    def broken(*_args):
        raise KeyError("source_id")
    monkeypatch.setattr(runtime, "original_review_critic", broken)
    result, adapter, saved = run_v2(monkeypatch, MARKED, observations_document=PRIMARY)
    bare, _, _ = run_v2(monkeypatch, V2, observations_document=PRIMARY)
    procedures = {p["id"]: p for p in result["procedures"]}
    assert (procedures["finding_review"]["status"], procedures["finding_review"]["reason"]) == ("failed", "original_review_failed")
    assert (procedures["finding_correction"]["status"], procedures["finding_correction"]["reason"]) == ("skipped", "dependency_failed")
    assert procedures["norm_verification"]["status"] == {p["id"]: p for p in bare["procedures"]}["norm_verification"]["status"]
    assert result["observations"] and [plain(o) for o in result["observations"]] == bare["observations"]
    assert all(not (NOT_REVIEW_KEYS & set(o)) for o in result["observations"])
    assert "original_review_failed" in result["warnings"] and saved[-1][0] == "partial"


def test_a_defect_in_the_corrector_leaves_the_critic_rows_and_no_half_correction(monkeypatch):
    def broken(_done):
        raise TypeError("row")
    monkeypatch.setattr(runtime, "original_review_corrector", broken)
    result, _, saved = run_v2(monkeypatch, MARKED, observations_document=PRIMARY)
    procedures = {p["id"]: p for p in result["procedures"]}
    assert procedures["finding_review"]["status"] == "completed" and procedures["finding_correction"]["status"] == "failed"
    assert all("critic" in o and "correction" not in o for o in result["observations"])
    assert saved[-1][0] == "partial"


def test_a_marked_run_without_observations_completes_both_procedures_with_their_reasons(monkeypatch):
    state = {"observations": [], "sources": [], "warnings": [], "procedures": [
        {"id": "finding_review", "status": "queued"}, {"id": "finding_correction", "status": "queued"}]}
    seen = []

    def phase(identity, status, reason=None):
        seen.append((identity, status, reason))
    runtime._review_original_v2(state=state, phase=phase, pages={})
    assert seen == [("finding_review", "running", None), ("finding_review", "completed", "no_observations"),
        ("finding_correction", "running", None), ("finding_correction", "completed", "no_corrections_requested")]


def test_the_planned_and_terminal_receipts_of_a_marked_consent_list_the_two_procedures():
    queued = runtime.planned_workflow_result(policy=MARKED)
    assert [p["id"] for p in queued["procedures"]][-2:] == ["finding_review", "finding_correction"]
    assert all(p["status"] == "queued" for p in queued["procedures"]) and queued["original_review"]["model_called"] is False
    stopped = runtime.planned_workflow_result(reason="provider_outcome_unknown", terminal=True, policy=MARKED)
    assert len(stopped["procedures"]) == 6 and all(p["status"] == "skipped" for p in stopped["procedures"])
    assert len(runtime.planned_workflow_result(policy=V2)["procedures"]) == 4


def test_the_read_helper_shows_the_marked_plan_before_the_worker_has_saved_anything(monkeypatch):
    class Context:
        def __enter__(self):
            return Session()

        def __exit__(self, *_):
            pass
    monkeypatch.setattr(runtime, "RunRepository", lambda: NS(get=lambda *_: NS(state="queued", version_uid="ver_run"), stage_results=lambda *_: []))
    import auditmanager.runs.cost_policy as cost
    monkeypatch.setattr(cost, "read_run_cost_policy", lambda *_, **__: NS(extended_review=MARKED))
    value = runtime.read_extended_review(Context, None, "run")
    assert value["status"] == "not_started" and len(value["result"]["procedures"]) == 6
    assert value["result"]["original_review"]["version"] == "deterministic-v1"


def test_a_chip_of_deterministic_procedures_has_no_plan_line_of_a_model():
    from auditmanager.runs import stage_facts
    run = stage_facts.RunRow("run", "published", None, stage_facts.RunBinding("Сервер", "claude-opus-5", "api"))
    review = {"status": "completed", "result": {"procedures": [
        {"id": "norm_verification", "status": "completed"},
        {"id": "finding_review", "status": "completed", "model_called": False},
        {"id": "finding_correction", "status": "completed", "model_called": False}]}}
    items = {item["chip"]: item for item in stage_facts.assemble_run_stage_facts(
        run=run, stage_rows=[], calls=[], review=review, cell_bindings={}, include_server=True)["items"]}
    assert items["norms"]["plan"] and items["review"]["plan"] == [] and items["correction"]["plan"] == []
    assert items["review"]["facts"]["state"] == "done" and items["review"]["facts"]["calls_succeeded"] == 0
    # a v3 procedure names no such thing, and keeps its line
    v3 = {"status": "completed", "result": {"procedures": [{"id": "finding_review", "status": "completed"}]}}
    kept = stage_facts.assemble_run_stage_facts(run=run, stage_rows=[], calls=[], review=v3, cell_bindings={}, include_server=True)["items"]
    assert kept[0]["chip"] == "review" and kept[0]["plan"] != []
