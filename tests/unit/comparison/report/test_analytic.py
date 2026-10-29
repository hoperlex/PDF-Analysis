"""`CMP-VC-REPORT-01`: the analytic report's program checks (container-free): the analyst, the verifier and the composer are each checked by
the program, not trusted; an unconfirmed number or a reference outside what was shown is refused; the report is assembled from the passports of
the facts and validated."""

from __future__ import annotations

import json
from typing import Any

import pytest

from auditmanager.comparison.report import analytic, facts, parse

MD = """# Сводка изменений X-1

Переходы от первой версии к последней, 2 шт.

## 1. X-1: V1 → V2

A: V1, файл «a.pdf». B: V2, файл «b.pdf».

### л.1 · План (A стр. PDF 1 → B стр. PDF 1)

- **Кабель ВВГнг(А)-LS** — 3×2,5 → 3×4
- **Автомат QF1** — 16 А → 25 А

## 2. X-1: V2 → V3

A: V2, файл «b.pdf». B: V3, файл «c.pdf».

_По данным сравнения изменений содержания нет._

## Реестр покрытия

- V1→V2: листов 1 — совпадает по движку 0; только служебное 0; описано ИИ 1; СО целиком 0; неоднозначно 0; не обработано 0.
- V2→V3: листов 0 — совпадает по движку 0; только служебное 0; описано ИИ 0; СО целиком 0; неоднозначно 0; не обработано 0.
"""
SOURCE = {"filename": "x.md", "sha256": "0" * 64, "bytes": len(MD.encode())}
RUN = "crt_TESTRUN"


@pytest.fixture(scope="module")
def world() -> dict[str, Any]:
    manifest = parse.parse(MD.encode("utf-8"), "x.md")
    lines = parse.split_lines(MD)
    registry = facts.build(manifest, lines)
    plan = analytic.make_plan(manifest)
    return {"manifest": manifest, "lines": lines, "registry": registry, "plan": plan}


def lines_of(world: dict[str, Any], needle: str) -> int:
    return next(i for i, line in enumerate(world["lines"], 1) if needle in line)


def analyst_answer(world: dict[str, Any], **over: Any) -> dict[str, Any]:
    cable, breaker = lines_of(world, "ВВГнг"), lines_of(world, "QF1")
    base = {
        "run_id": RUN, "group_id": "G01", "processed_block_ids": ["B01"], "unprocessed_block_ids": [], "partial": False, "input_problems": [],
        "transitions": [{
            "transition_id": "T01", "analysis_complete": True, "content_status": "technical", "change_scope": "Локальные изменения",
            "significance": "Средняя", "assessment_basis": "замена кабеля и автомата", "systems": [],
            "facts": [
                {"fact_id": "F1", "object": "Кабель ВВГнг(А)-LS", "system": "", "before": "3×2,5", "after": "3×4", "possible_consequence": "",
                 "evidence": [{"md_from": cable, "md_to": cable}], "uncertainty": "", "related_objects": [], "serious_candidate": True},
                {"fact_id": "F2", "object": "Автомат QF1", "system": "", "before": "16 А", "after": "25 А", "possible_consequence": "",
                 "evidence": [{"md_from": breaker, "md_to": breaker}], "uncertainty": "", "related_objects": ["QF1"], "serious_candidate": False},
            ],
            "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка", "explicit_conditions": [], "contradictions": [],
            "missing_information": [],
        }],
    }
    base.update(over)
    return base


def test_the_plan_is_one_block_one_group_one_unit_per_transition(world) -> None:
    plan = world["plan"]
    assert [b["block_id"] for b in plan["blocks"]] == ["B01", "B02"] and [g["group_id"] for g in plan["groups"]] == ["G01", "G02"]
    assert [u["unit_id"] for u in plan["units"]] == ["U01", "U02"]
    assert plan["blocks"][0]["ranges"] == [[world["manifest"]["transitions"][0]["line_start"], world["manifest"]["transitions"][0]["line_end"]]]


def test_the_analyst_prompt_carries_the_numbered_lines_the_rules_and_a_data_boundary(world) -> None:
    prompt = analytic.analyst_prompt(RUN, SOURCE, world["manifest"], world["plan"], world["plan"]["groups"][0], world["lines"])
    assert f"[{lines_of(world, 'ВВГнг')}] - **Кабель ВВГнг(А)-LS** — 3×2,5 → 3×4" in prompt
    assert "Правила достоверности" in prompt and "Источник определяет предел вывода" in prompt  # the rules file is the original's
    assert "Текущий запуск: crt_TESTRUN" in prompt and "Группа: G01" in prompt and "{{" not in prompt
    begin = next(w for w in prompt.split() if w.startswith("<<<ДАННЫЕ-"))
    assert prompt.count(begin) >= 3  # the label of the data block is repeated and not in the data


def test_the_analyst_answer_is_checked_not_trusted(world) -> None:
    group = world["plan"]["groups"][0]
    check = lambda a: analytic.check_analyst(a, RUN, group, world["plan"], world["manifest"])  # noqa: E731
    assert check(analyst_answer(world))["ok"] is True
    assert not check(analyst_answer(world, run_id="other"))["ok"]
    assert not check(analyst_answer(world, processed_block_ids=[], unprocessed_block_ids=["B01"]))["ok"]
    outside = analyst_answer(world)
    outside["transitions"][0]["facts"][0]["evidence"] = [{"md_from": 400, "md_to": 401}]
    assert any("outside the assigned text" in h for h in check(outside)["hard"])
    bare = analyst_answer(world)
    bare["transitions"][0]["facts"][0]["evidence"] = []
    assert any("without lines of the source" in h for h in check(bare)["hard"])
    wrong = analyst_answer(world)
    wrong["transitions"][0]["transition_id"] = "T02"
    assert not check(wrong)["ok"]


def verifier_answer(world: dict[str, Any], claims: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    cable = lines_of(world, "ВВГнг")
    base = {
        "run_id": RUN, "unit_id": "U01",
        "claims": [{"claim_id": c["claim_id"], "verdict": "supported", "verified_wording": f"{c['text'][:80]}", "evidence": c["evidence"],
                    "brief_reason": "", "missing_information": [], "linked_claim_ids": []} for c in claims],
        "transitions": [{"transition_id": "T01", "content_status": "technical", "change_scope": "Локальные изменения", "significance": "Средняя",
                         "assessment_basis": "основание", "main_changes": "Заменены кабель и автомат.",
                         "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка",
                         "key_claim_ids": [c["claim_id"] for c in claims], "evidence": [{"md_from": cable, "md_to": cable}]}],
        "significant_candidates": [{"title": "Замена кабеля", "claim_ids": [claims[1]["claim_id"]], "version_range": "V1→V2", "before_after": "3×2,5 → 3×4",
                                    "consequence": "потребуется проверка", "evidence": [{"md_from": cable, "md_to": cable}]}],
        "unresolved_questions": [], "missing_transitions_or_blocks": [],
    }
    base.update(over)
    return base


def test_the_verifier_must_give_a_verdict_for_every_claim_and_only_cite_what_it_was_shown(world) -> None:
    results = {"G01": analyst_answer(world)}
    claims = analytic.claims_for_unit(results)
    assert [c["claim_id"] for c in claims] == ["G01.T01.A", "G01.T01.F1", "G01.T01.F2"]
    prompt, shown = analytic.verifier_prompt(RUN, SOURCE, world["manifest"], world["plan"], world["plan"]["units"][0], results, claims, world["lines"])
    assert "Для КАЖДОГО claim_id" in prompt and "Полный текст переходов этой единицы." in prompt and "G01.T01.F2" in prompt
    unit = world["plan"]["units"][0]
    good = verifier_answer(world, claims)
    assert analytic.check_verifier(good, RUN, unit, claims, shown)["ok"] is True
    missing = verifier_answer(world, claims[:2])
    assert any("no verdict for the claims: G01.T01.F2" in h for h in analytic.check_verifier(missing, RUN, unit, claims, shown)["hard"])
    far = verifier_answer(world, claims)
    far["claims"][1]["evidence"] = [{"md_from": 900, "md_to": 901}] * 5
    assert any("not shown in the task" in h for h in analytic.check_verifier(far, RUN, unit, claims, shown)["hard"])
    extra = dict(good, claims=[*good["claims"], dict(good["claims"][0], claim_id="G99.X")])
    cleaned = analytic.clean_verifier(extra, claims, shown)
    assert [c["claim_id"] for c in cleaned["claims"]] == [c["claim_id"] for c in claims]


def test_a_candidate_resting_on_a_rejected_claim_is_dropped(world) -> None:
    results = {"G01": analyst_answer(world)}
    claims = analytic.claims_for_unit(results)
    _, shown = analytic.verifier_prompt(RUN, SOURCE, world["manifest"], world["plan"], world["plan"]["units"][0], results, claims, world["lines"])
    answer = verifier_answer(world, claims)
    answer["claims"][1]["verdict"] = "rejected"
    cleaned = analytic.clean_verifier(answer, claims, shown)
    assert cleaned["significant_candidates"] == [] and cleaned["transitions"][0]["key_claim_ids"] == ["G01.T01.A", "G01.T01.F2"]


@pytest.fixture
def verified(world) -> dict[str, dict[str, Any]]:
    results = {"G01": analyst_answer(world)}
    claims = analytic.claims_for_unit(results)
    _, shown = analytic.verifier_prompt(RUN, SOURCE, world["manifest"], world["plan"], world["plan"]["units"][0], results, claims, world["lines"])
    one = analytic.clean_verifier(verifier_answer(world, claims), claims, shown)
    quiet = {"run_id": RUN, "unit_id": "U02", "claims": [], "transitions": [{
        "transition_id": "T02", "content_status": "no_content_changes", "change_scope": "Нет изменений содержания",
        "significance": "Нет новых технических изменений", "assessment_basis": "", "main_changes": "Изменений нет.",
        "construction_impact": "дополнительных технических последствий не выявлено", "key_claim_ids": [], "evidence": []}],
        "significant_candidates": [], "unresolved_questions": [], "missing_transitions_or_blocks": []}
    return {"U01": one, "U02": quiet}


def composer_answer(world: dict[str, Any], **over: Any) -> dict[str, Any]:
    by_text = {f["text"][:20]: f["fact_id"] for f in world["registry"]["facts"]}
    cable = next(f["fact_id"] for f in world["registry"]["facts"] if "ВВГнг" in f["text"])
    base = {
        "run_id": RUN, "summary": ["Раздел переработан локально."], "summary_fact_ids": [cable],
        "transitions": [
            {"transition_id": "T01", "change_scope": "Локальные изменения", "significance": "Средняя", "main_changes": "Заменены кабель и автомат.",
             "changes": [{"object": "Кабель ВВГнг(А)-LS", "before": "3×2,5", "after": "3×4", "fact_ids": [cable]}],
             "construction_impact": "при выполнении по предыдущей версии потребовалась бы проверка", "impact_fact_ids": [cable]},
            {"transition_id": "T02", "change_scope": "Нет изменений содержания", "significance": "Нет новых технических изменений",
             "main_changes": "Изменений нет.", "changes": [], "construction_impact": "дополнительных технических последствий не выявлено", "impact_fact_ids": []},
        ],
        "significant_changes": [{"priority": "P2", "title": "Замена кабеля", "version_range": "V1→V2", "before_after": "3×2,5 → 3×4",
                                 "consequence": "потребуется проверка", "claim_ids": ["G01.T01.F1"], "fact_ids": [cable]}],
        "limitations": ["Исходные PDF не проверялись."],
    }
    base.update(over)
    return base


def test_the_composer_answer_passes_when_every_number_is_in_the_facts_or_the_verified_wordings(world, verified) -> None:
    result = analytic.check_composer(composer_answer(world), RUN, world["manifest"], verified, world["lines"], world["registry"])
    assert result["ok"] is True, result


def test_a_number_that_no_fact_or_wording_holds_is_refused(world, verified) -> None:
    bad = composer_answer(world)
    bad["significant_changes"][0]["before_after"] = "3×2,5 → 3×16"
    result = analytic.check_composer(bad, RUN, world["manifest"], verified, world["lines"], world["registry"])
    assert result["ok"] is False and any("16" in u["numbers"] for u in result["unconfirmed_numbers"])


def test_more_than_five_serious_changes_and_a_rejected_claim_are_refused(world, verified) -> None:
    many = composer_answer(world)
    many["significant_changes"] = many["significant_changes"] * (analytic.MAX_SERIOUS + 1)
    assert any("at most 5" in h for h in analytic.check_composer(many, RUN, world["manifest"], verified, world["lines"], world["registry"])["hard"])
    rejected = composer_answer(world)
    rejected["significant_changes"][0]["claim_ids"] = ["G99.T01.F9"]
    assert any("unknown or rejected" in h for h in analytic.check_composer(rejected, RUN, world["manifest"], verified, world["lines"], world["registry"])["hard"])


def test_the_composer_must_name_exactly_the_transitions_and_may_not_leak_internal_ids(world, verified) -> None:
    short = composer_answer(world)
    short["transitions"] = short["transitions"][:1]
    assert analytic.check_composer(short, RUN, world["manifest"], verified, world["lines"], world["registry"])["hard"]
    leaky = composer_answer(world)
    leaky["transitions"][0]["main_changes"] = "T01 и Ф0002 заменены"
    result = analytic.check_composer(leaky, RUN, world["manifest"], verified, world["lines"], world["registry"])
    assert any("internal identifiers" in f for f in result["fixable"])


def test_a_chain_of_values_needs_one_confirmed_line(world, verified) -> None:
    chain = composer_answer(world)
    chain["significant_changes"][0]["before_after"] = "3×2,5 → 3×4 → 3×6"
    first = next(f["fact_id"] for f in world["registry"]["facts"] if "ВВГнг" in f["text"])
    second = next(f["fact_id"] for f in world["registry"]["facts"] if "QF1" in f["text"])
    chain["significant_changes"][0]["fact_ids"] = [first, second]
    result = analytic.check_composer(chain, RUN, world["manifest"], verified, world["lines"], world["registry"])
    assert result["chains"] and any("without a confirmed single line" in f for f in result["fixable"])


def test_the_verified_assessment_replaces_the_composers_and_a_split_never_lowers_it() -> None:
    parts = {"T01": [{"change_scope": "Существенные изменения", "significance": "Высокая"}, {"change_scope": "Локальные изменения", "significance": "Низкая"}]}
    composed = {"change_scope": "Локальные изменения", "significance": "Средняя"}
    scope, significance, note = analytic.final_assessment("T01", composed, parts)
    assert (scope, significance) == ("Существенные изменения", "Высокая") and "поднят" in note
    single = {"T01": [{"change_scope": "Только оформление", "significance": "Низкая"}]}
    assert analytic.final_assessment("T01", composed, single)[:2] == ("Только оформление", "Низкая")


def test_the_report_is_assembled_from_passports_validated_and_counted_by_the_program(world, verified) -> None:
    report = analytic.assemble(composer_answer(world), world["manifest"], verified, SOURCE, world["lines"], world["registry"])
    assert analytic.validate_report(report, world["manifest"]["lines_total"]) == []
    assert analytic.consistency(report, world["manifest"]) == []
    assert report["schema_version"] == "report_v2" and [t["from_version"] for t in report["transitions"]] == ["V1", "V2"]
    assert report["transitions"][0]["completeness"]["text"] == "обработаны все 1 листов"
    assert analytic.distribution(report) == {"total": 2, "technical": 1, "no_content_change": 1, "formatting_only": 0, "unknown": 0}
    assert {f["fact_id"] for f in report["facts"]} == set(report["summary_sources"]) | set(report["transitions"][0]["sources"])
    json.dumps(report, ensure_ascii=False)  # the report is plain JSON: it is the stored text of the PDF


def test_a_fact_of_another_transition_or_an_unknown_one_is_dropped_from_the_report_not_trusted(world, verified) -> None:
    answer = composer_answer(world)
    answer["transitions"][0]["changes"][0]["fact_ids"] = ["Ф9999"]
    report = analytic.assemble(answer, world["manifest"], verified, SOURCE, world["lines"], world["registry"])
    assert report["transitions"][0]["changes"] == [] and any("Ф9999" in w for w in report["reference_warnings"])


def test_the_report_contract_refuses_a_row_with_no_fact_and_an_unknown_scale(world, verified) -> None:
    report = analytic.assemble(composer_answer(world), world["manifest"], verified, SOURCE, world["lines"], world["registry"])
    report["transitions"][0]["changes"][0]["sources"] = []
    report["transitions"][1]["change_scope"] = "Огромные"
    problems = analytic.validate_report(report)
    assert any("a change must have a fact" in p for p in problems) and any("unknown value" in p for p in problems)
