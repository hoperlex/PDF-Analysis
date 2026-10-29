"""Helpers of the report lane's run tests: start a report, ask which request the handler will make and record its answer by digest."""

from __future__ import annotations

import io
import json
from typing import Any

from pypdf import PdfReader

from auditmanager.comparison.report import analytic, plan as plan_module
from auditmanager.comparison.report.model import UNCONFIRMED_LABEL
from auditmanager.comparison.report.repository import ReportRepository
from tests.integration.comparison.report.conftest import EXPERT, support


def start(db: Any, report: dict[str, Any], *, key: str = "start-1", service: Any = None, digest: str | None = None) -> dict[str, Any]:
    return (service or db.service()).start_report(
        report_id=report["report_id"], consent=db.consent(digest or report["estimate"]["estimate_digest"]), user_uid=support.ACTOR,
        actor_roles=EXPERT, idempotency_key=key,
    )


def source_of(db: Any, report_id: str) -> Any:
    with db.sessions() as session:
        row = ReportRepository().get(session, report_id)
        assert row is not None
        return db.service().source_doc(session, row)


def record_client(db: Any, world: dict[str, Any], report: dict[str, Any], route: Any, *, label: str = "V1→V2", answer: dict[str, Any] | None = None) -> str:
    """Record the answer to the request the handler will make for the client kind's transition ``label``; answers its digest."""
    doc = source_of(db, report["report_id"])
    request, *_ = support.client_request(doc, label, route.pinned_model, world["project"])
    return db.answers.record(request, json.dumps(answer or support.good_client_answer(doc, label), ensure_ascii=False))


def pdf_text(content: bytes) -> list[str]:
    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]


def reread(db: Any, report: dict[str, Any]) -> dict[str, Any]:
    return db.service().get_report(report_id=report["report_id"])


def run_client_report(db: Any, world: dict[str, Any], make: Any, route: Any, *, answer: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """A client report started and run to its end with one good answer for the transition that has a description."""
    report = make(world)
    record_client(db, world, report, route, answer=answer)
    started = start(db, report)
    db.drain(db.handler())
    return report, started


__all__ = ["UNCONFIRMED_LABEL", "analytic", "pdf_text", "plan_module", "reread", "record_client", "run_client_report", "source_of", "start"]


# -- the analytic kind -----------------------------------------------------------------------------------------------------------

def _line(doc: Any, needle: str) -> int:
    return next(i for i, line in enumerate(doc.lines, 1) if needle in line)


def record_analytic(db: Any, report: dict[str, Any], route: Any, *, composer: dict[str, Any] | None = None, skip_verifier: tuple[str, ...] = ()) -> tuple[dict[str, Any], dict[str, Any]]:
    """Record the analyst's, the verifier's and the composer's answers to the requests the handler will make for every transition of an analytic
    report, built through the same functions, in the order the answers depend on one another. Answers ``(verified results by unit, the composer's answer)``."""
    doc = source_of(db, report["report_id"])
    manifest, report_id, model = doc.manifest, report["report_id"], route.pinned_model
    plan = analytic.make_plan(manifest)
    verified: dict[str, dict[str, Any]] = {}
    for index, transition in enumerate(manifest["transitions"]):
        group, unit = plan["groups"][index], plan["units"][index]
        facts = []
        if "Кабель" in "\n".join(doc.lines[transition["line_start"] - 1:transition["line_end"]]):
            number = _line(doc, "ВВГнг")
            facts = [{"fact_id": "F1", "object": "Кабель ВВГнг(А)-LS", "system": "", "before": "3×2,5", "after": "3×4", "possible_consequence": "",
                      "evidence": [{"md_from": number, "md_to": number}], "uncertainty": "", "related_objects": [], "serious_candidate": True}]
        answer = {
            "run_id": report_id, "group_id": group["group_id"], "processed_block_ids": [plan["blocks"][index]["block_id"]], "unprocessed_block_ids": [],
            "partial": False, "input_problems": [],
            "transitions": [{
                "transition_id": transition["transition_id"], "analysis_complete": True, "content_status": "technical" if facts else "unknown",
                "change_scope": "Локальные изменения" if facts else "Не установлено", "significance": "Средняя" if facts else "Не установлена",
                "assessment_basis": "замена кабеля" if facts else "описания нет", "systems": [], "facts": facts,
                "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка", "explicit_conditions": [], "contradictions": [],
                "missing_information": [],
            }],
        }
        prompt = analytic.analyst_prompt(report_id, doc.source, manifest, plan, group, doc.lines)
        db.answers.record(plan_module.request_for(model, prompt, analytic.ANALYST_SCHEMA, plan_module.MAX_TOKENS["analyst"]), json.dumps(answer, ensure_ascii=False))
        results = {group["group_id"]: answer}
        claims = analytic.claims_for_unit(results)
        v_prompt, shown = analytic.verifier_prompt(report_id, doc.source, manifest, plan, unit, results, claims, doc.lines)
        first = transition["line_start"]
        key_claims = [c["claim_id"] for c in claims if c["claim_id"].endswith(".F1")]
        verdict = {
            "run_id": report_id, "unit_id": unit["unit_id"],
            "claims": [{"claim_id": c["claim_id"], "verdict": "supported", "verified_wording": c["text"][:120], "evidence": c["evidence"], "brief_reason": "",
                        "missing_information": [], "linked_claim_ids": []} for c in claims],
            "transitions": [{"transition_id": transition["transition_id"], "content_status": "technical" if facts else "unknown",
                             "change_scope": "Локальные изменения" if facts else "Не установлено", "significance": "Средняя" if facts else "Не установлена",
                             "assessment_basis": "основание", "main_changes": "Заменён кабель." if facts else "Описания нет.",
                             "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка", "key_claim_ids": key_claims,
                             "evidence": [{"md_from": first, "md_to": first}]}],
            "significant_candidates": [{"title": "Замена кабеля", "claim_ids": key_claims, "version_range": "V1→V2", "before_after": "3×2,5 → 3×4",
                                        "consequence": "потребуется проверка", "evidence": claims[1]["evidence"]}] if facts else [],
            "unresolved_questions": [], "missing_transitions_or_blocks": [],
        }
        if transition["transition_id"] not in skip_verifier:
            db.answers.record(plan_module.request_for(model, v_prompt, analytic.VERIFIER_SCHEMA, plan_module.MAX_TOKENS["verifier"]), json.dumps(verdict, ensure_ascii=False))
        verified[unit["unit_id"]] = analytic.clean_verifier(verdict, claims, shown)
    cable = next(f["fact_id"] for f in doc.registry["facts"] if "ВВГнг" in f["text"])
    answer = {
        "run_id": report_id, "summary": ["Раздел переработан локально."], "summary_fact_ids": [cable],
        "transitions": [
            {"transition_id": "T01", "change_scope": "Локальные изменения", "significance": "Средняя", "main_changes": "Заменён кабель.",
             "changes": [{"object": "Кабель ВВГнг(А)-LS", "before": "3×2,5", "after": "3×4", "fact_ids": [cable]}],
             "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка", "impact_fact_ids": [cable]},
            *[{"transition_id": f"T0{n}", "change_scope": "Не установлено", "significance": "Не установлена", "main_changes": "Описания нет.",
               "changes": [], "construction_impact": "последствия не установлены, нужна проверка", "impact_fact_ids": []} for n in (2, 3)],
        ],
        "significant_changes": [{"priority": "P2", "title": "Замена кабеля", "version_range": "V1→V2", "before_after": "3×2,5 → 3×4",
                                 "consequence": "потребуется проверка", "claim_ids": ["G01.T01.F1"], "fact_ids": [cable]}],
        "limitations": ["Исходные PDF не проверялись."],
    }
    answer.update(composer or {})
    prompt = analytic.composer_prompt(report_id, doc.source, manifest, verified, retry_note="", registry=doc.registry)
    db.answers.record(plan_module.request_for(model, prompt, analytic.COMPOSER_SCHEMA, plan_module.MAX_TOKENS["composer"]), json.dumps(answer, ensure_ascii=False))
    return verified, answer


def record_composer_retry(db: Any, report: dict[str, Any], route: Any, verified: dict[str, Any], answer: dict[str, Any]) -> None:
    """Record the answer to the composer's second request: the same answer, asked with the program's remarks on the first one."""
    from auditmanager.comparison.report import handler as handler_module

    doc = source_of(db, report["report_id"])
    checked = analytic.check_composer(answer, report["report_id"], doc.manifest, verified, doc.lines, doc.registry)
    note = handler_module._FEEDBACK.format(problems="\n- ".join(checked["hard"] + checked["fixable"]))
    prompt = analytic.composer_prompt(report["report_id"], doc.source, doc.manifest, verified, retry_note=note, registry=doc.registry)
    db.answers.record(plan_module.request_for(route.pinned_model, prompt, analytic.COMPOSER_SCHEMA, plan_module.MAX_TOKENS["composer"]), json.dumps(answer, ensure_ascii=False))
