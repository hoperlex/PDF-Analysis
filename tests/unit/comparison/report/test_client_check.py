"""`CMP-VC-REPORT-01`: the client report's program check (container-free). **A point whose number, mark or direction the facts do not confirm
is dropped**; a point the facts do confirm is kept; the status of a point is set by the facts, not by the model; nothing service-like reaches
a customer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from auditmanager.comparison.report import client, disciplines, facts, parse
from auditmanager.comparison.report.summary import build_summary


def _load(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


samples = _load("cmp_report_unit_samples", Path(__file__).resolve().parent / "report_samples.py")
TRANSITION = {"from_version": "V1", "to_version": "V2", "from_date": None, "to_date": None}


@pytest.fixture(scope="module")
def world() -> dict[str, Any]:
    summary = build_summary(samples.summary_data())
    manifest = parse.parse(summary.text.encode("utf-8"))
    registry = facts.build(manifest, parse.split_lines(summary.text), dict(summary.records))
    profile = disciplines.resolve(samples.CODE)
    text, groups, support = client.packet(registry["facts"], "V1→V2", profile)
    ids = {f["text"][:12]: f["fact_id"] for f in registry["facts"]}
    cable = next(f["fact_id"] for f in registry["facts"] if "ВВГнг" in f["text"])
    breaker = next(f["fact_id"] for f in registry["facts"] if "QF1" in f["text"])
    return {"facts": registry["facts"], "groups": groups, "support": support, "text": text, "cable": cable, "breaker": breaker, "ids": ids}


def point(obj: str, text: str, fact_ids: list[str], values: list[dict[str, str]] | None = None, status: str = "confirmed") -> dict[str, Any]:
    return {"object": obj, "text": text, "fact_ids": fact_ids, "values": values or [], "status": status}


def answer(points: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    base = {"transition": "V1→V2", "change_scope": "Локальные изменения", "lead": "Заменены кабель и автомат питания.", "points": points,
            "impact": "", "impact_fact_ids": [], "questions": [], "not_included": []}
    base.update(over)
    return base


def check(world: dict[str, Any], ans: dict[str, Any]) -> dict[str, Any]:
    return client.check(ans, TRANSITION, world["facts"], world["groups"], world["support"])


def value(parameter: str, before: str, after: str, fact_id: str) -> dict[str, str]:
    return {"parameter": parameter, "before": before, "after": after, "fact_id": fact_id}


def test_a_point_the_facts_confirm_is_kept(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]], [value("сечение", "3×2,5", "3×4", world["cable"])])
    result = check(world, answer([good]))
    assert result["ok"] is True and [k["fact_ids"] for k in result["kept"]] == [[world["cable"]]] and result["dropped"] == []


def test_a_number_the_facts_do_not_hold_is_dropped(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    invented = point("Автомат QF1", "16 А → 63 А", [world["breaker"]])
    result = check(world, answer([good, invented]))
    assert [k["point"]["object"] for k in result["kept"]] == ["Кабель ВВГнг(А)-LS"]
    assert [d["point"]["object"] for d in result["dropped"]] == ["Автомат QF1"]
    assert "the number 63 is not found in the cited facts" in result["dropped"][0]["problems"]
    assert result["ok"] is False and result["hard"] == []  # a dropped point is not a retry while a fit one is left


def test_a_designation_the_facts_do_not_hold_is_dropped(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    result = check(world, answer([good, point("Щит ЩР-9", "новый щит", [world["breaker"]])]))
    assert any("«ЩР-9» is not in the cited facts" in p for d in result["dropped"] for p in d["problems"])
    assert len(result["kept"]) == 1


def test_a_direction_the_facts_do_not_confirm_is_dropped(world) -> None:
    good = point("Автомат QF1", "16 А → 25 А", [world["breaker"]], [value("ток", "16 А", "25 А", world["breaker"])])
    reversed_ = point("Кабель ВВГнг(А)-LS", "3×4 → 3×2,5", [world["cable"]], [value("сечение", "3×4", "3×2,5", world["cable"])])
    result = check(world, answer([good, reversed_]))
    assert [d["point"]["object"] for d in result["dropped"]] == ["Кабель ВВГнг(А)-LS"]
    assert any("side or direction" in p for p in result["dropped"][0]["problems"])


def test_a_point_citing_a_fact_of_another_transition_or_none_is_dropped(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    result = check(world, answer([good, point("Кабель", "3×4", ["Ф9999"]), point("Кабель", "3×4", [])]))
    problems = [p for d in result["dropped"] for p in d["problems"]]
    assert any("ID not from this transition: Ф9999" in p for p in problems) and "no facts" in problems


def test_the_status_of_a_point_is_set_by_the_facts_not_by_the_model(world) -> None:
    unclear = point("Автомат QF1", "16 А → 25 А", [world["breaker"]], status="confirmed")
    result = check(world, answer([unclear]))
    assert result["kept"][0]["point"]["status"] == "needs_clarification" and result["fixes"]


def test_a_stub_cut_in_the_packet_is_completed_from_the_cited_facts_or_dropped(world) -> None:
    fixed, left = client.repair_cut("марка FIRESTO… и щит", "марка FIRESTOP-12 для проходки")
    assert fixed == "марка FIRESTOP-12 и щит" and left is False
    kept, still = client.repair_cut("марка FIRESTO…", "марка другая")
    assert still is True and kept == "марка FIRESTO…"


@pytest.mark.parametrize("lead", ["", "Первое. Второе.", "x" * 231])
def test_a_lead_that_is_not_one_short_sentence_is_a_retry(world, lead) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    assert check(world, answer([good], lead=lead))["hard"]


@pytest.mark.parametrize("text", ["по сводке изменений", "см. стр. PDF 3", "из-за ошибки проектировщика", "затраты вырастут", "для A и B"])
def test_service_words_and_unfounded_reasons_never_reach_a_customer(world, text) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    result = check(world, answer([good], impact=text, impact_fact_ids=[world["cable"]]))
    assert any("in «" in h for h in result["hard"]), result["hard"]


def test_the_answer_of_another_transition_and_too_many_points_are_a_retry(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    assert any("instead of" in h for h in check(world, answer([good], transition="V2→V3"))["hard"])
    assert any("points" in h for h in check(world, answer([good] * (client.POINTS_MAX + 1)))["hard"])
    assert any("points" in h for h in check(world, answer([]))["hard"])


def test_an_impact_number_the_facts_do_not_hold_is_a_retry(world) -> None:
    good = point("Кабель ВВГнг(А)-LS", "3×2,5 → 3×4", [world["cable"]])
    result = check(world, answer([good], impact="Потребуется 500 м кабеля.", impact_fact_ids=[world["cable"]]))
    assert any("the number 500" in h for h in result["hard"])


def test_the_packet_marks_unclear_facts_and_folds_repeated_specification_positions() -> None:
    # two added positions of one name and mark fold into one group with a code «С001» and the sum of the quantity
    text = (
        "# Сводка изменений X\n\n## 1. X: V1 → V2\n\n### Спецификация целиком\n\n"
        "- Старая: —; новая: л.1 (стр. PDF 5). Добавлено: не было → Наименование Светильник; Марка LED-1; раздел А; Количество: 2 шт\n"
        "- Старая: —; новая: л.2 (стр. PDF 6). Добавлено: не было → Наименование Светильник; Марка LED-1; раздел Б; Количество: 3 шт\n"
    )
    manifest = parse.parse(text.encode("utf-8"))
    records = {str(ln): {"kind": "spec_entry", "change_kind": "added", "old_pages": [], "new_pages": [5]} for ln in (7, 8)}
    registry = facts.build(manifest, parse.split_lines(text), records)
    packet, groups, support = client.packet(registry["facts"], "V1→V2", disciplines.resolve(None))
    assert groups == {"С001": [f["fact_id"] for f in registry["facts"]]}
    assert "С001 добавлено позиций: 2: Светильник LED-1, всего 5 шт" in packet and "С001" in support


def test_a_section_profile_marks_what_matters_and_a_missing_one_marks_nothing() -> None:
    profile = disciplines.resolve("125/24-ГК-КЖ", "")
    assert profile["known"] is True and profile["key"] == "KZh" and profile["important"]
    assert disciplines.resolve(None)["known"] is False and disciplines.resolve(None)["important"] == {}
    assert disciplines.by_key("no-such-key")["key"] == "_neutral"
    fact = {"kind": "ai_change", "text": "Бетон B25 → B30", "details": {"change_kind": "замена", "fields": [{"name": "класс", "before": "B25", "after": "B30"}]}}
    assert client.important(fact, profile) is not None and client.important(fact, None) is None


def test_the_transitions_that_need_a_selection_are_all_but_the_confirmed_absence_of_changes() -> None:
    summary = build_summary(samples.summary_data())
    manifest = parse.parse(summary.text.encode("utf-8"))
    assert [t["label"] for t in client.edited_transitions(manifest)] == ["V1→V2"]
    assert client.is_unchanged(manifest["transitions"][1])
    row = client.row_of(manifest["transitions"][1], None)
    assert row["scale"] == client.SCOPE_NONE and row["lead"] == client.NO_CHANGES and row["points"] == []
