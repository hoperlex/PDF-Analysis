"""`CMP-VC-REPORT-01`: the deterministic MD summary and the intake of an MD file (container-free).

The summary is **the same bytes for the same data**; it reads back through the intake parser into the transitions it wrote; a sheet with
no stored description reads «ИИ-описание не запускалось» and is never «no changes»; the tiers and the unconfirmed mark are in the text."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.comparison.report import facts, parse
from auditmanager.comparison.report.summary import MARK_UNCONFIRMED, build_summary, verdict_text


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


def test_the_same_data_give_the_same_bytes_whatever_the_order_the_sheets_arrive_in() -> None:
    first = build_summary(samples.summary_data())
    again = build_summary(samples.summary_data())
    shuffled = build_summary(samples.summary_data(shuffled=True))
    assert first.text == again.text == shuffled.text
    assert first.text.encode("utf-8") == shuffled.text.encode("utf-8")
    assert first.records == shuffled.records
    assert first.filename == "Сводка_изменений_133_23-ГК-ЭМ2.md"


def test_the_time_in_the_header_is_the_time_of_the_data_not_of_the_making() -> None:
    summary = build_summary(samples.summary_data())
    assert "Данные на 29.10.2026 05:00 UTC." in summary.text
    older = replace(samples.summary_data(), data_at=samples.WHEN.replace(hour=4))
    assert build_summary(older).text != summary.text


def test_the_summary_reads_back_into_the_transitions_it_wrote() -> None:
    summary = build_summary(samples.summary_data())
    manifest = parse.parse(summary.text.encode("utf-8"), summary.filename)
    assert [t["label"] for t in manifest["transitions"]] == ["V1→V2", "V2→V3"]
    assert [t["number"] for t in manifest["transitions"]] == [1, 2]
    assert manifest["transitions"][0]["a_file"] == "a.pdf" and manifest["transitions"][0]["b_file"] == "b.pdf"
    assert [len(t["sheets"]) for t in manifest["transitions"]] == [2, 0]
    assert manifest["transitions"][1]["explicit_no_content_changes"] is True  # the engine found nothing and the transition is complete
    assert manifest["registry"] is not None and len(manifest["registry"]["rows"]) == 2
    assert manifest["project_code"] == samples.CODE


def test_a_sheet_with_no_stored_description_is_a_gap_in_the_source_and_never_no_changes() -> None:
    summary = build_summary(samples.summary_data())
    manifest = parse.parse(summary.text.encode("utf-8"))
    first = manifest["transitions"][0]
    undescribed = next(s for s in first["sheets"] if s["a_page"] == 3)
    assert undescribed["not_described"], "the parse reads «ИИ-описание не запускалось» as a gap"
    assert first["source_incomplete"] and first["explicit_no_content_changes"] is False
    assert any(issue["code"] == "SOURCE_INCOMPLETE" for issue in manifest["issues"])
    row = manifest["registry"]["rows"][0]
    assert row["counts"]["не обработано"] == 1 and row["counts"]["совпадает по движку"] == 1


def test_the_tiers_the_questions_and_the_unconfirmed_mark_are_in_the_text() -> None:
    summary = build_summary(samples.summary_data())
    assert "**Кабель ВВГнг(А)-LS** — 3×2,5 → 3×4 (с изображения)" in summary.text
    assert "**Автомат QF1** — 16 А → 25 А (не подтверждено, неясно)" in summary.text
    assert "_Требует уточнения: 1 (вопросы — в портале по этому листу)._" in summary.text
    assert f"_Описания листов подготовлены моделью: {MARK_UNCONFIRMED}._" in summary.text
    assert summary.text.count(MARK_UNCONFIRMED) == 2  # the header and the one transition that holds descriptions
    assert "Часть пар листов (1) опирается на связь, принятую по ответу ИИ" in summary.text  # an AI-shaped transition is marked


def test_a_recorded_answer_is_labelled_as_such() -> None:
    summary = build_summary(samples.summary_data(recorded=True))
    assert "записанные (тестовые) ответы" in summary.text
    assert "записанные (тестовые) ответы" not in build_summary(samples.summary_data()).text


def test_nothing_is_rendered_for_a_description_or_a_specification_that_does_not_exist() -> None:
    plain = build_summary(replace(samples.summary_data(), transitions=tuple(
        replace(t, sheets=tuple(replace(s, description=None) for s in t.sheets)) for t in samples.summary_data().transitions
    )))
    assert "Модель: —." in plain.text
    assert "Спецификация целиком" not in plain.text and MARK_UNCONFIRMED in plain.text.splitlines()[5]  # only the header says it
    assert "Описания листов подготовлены" not in plain.text and plain.sheets == 0 and plain.changes == 0


def test_the_whole_specification_comparison_is_a_section_of_its_own() -> None:
    summary = build_summary(samples.spec_data())
    assert "### Спецификация целиком" in summary.text
    assert "- Старая: л.12 (стр. PDF 5); новая: л.12 (стр. PDF 6). Наименование Светильник; Марка LED-1; Количество: 2 → 3" in summary.text
    assert "- Старая: —; новая: л.? (стр. PDF 6). Добавлено: не было → Наименование Кабель; Марка ВВГ 3х2,5; Количество: 100 м" in summary.text
    manifest = parse.parse(summary.text.encode("utf-8"))
    kinds = [r["change_kind"] for r in summary.records.values() if r["kind"] == "spec_entry"]
    assert kinds == ["changed", "added"]
    registry = facts.build(manifest, parse.split_lines(summary.text), dict(summary.records))
    spec = [f for f in registry["facts"] if f["kind"] == "spec_entry"]
    assert [f["pages_b"] for f in spec] == [[6], [6]] and spec[0]["pages_a"] == [5]


def test_the_records_name_the_lines_that_carry_them() -> None:
    summary = build_summary(samples.summary_data())
    lines = parse.split_lines(summary.text)
    for number, record in summary.records.items():
        assert lines[int(number) - 1].startswith("- "), (number, record["kind"])
    change = next(r for r in summary.records.values() if r["kind"] == "ai_change" and r["change_id"] == "c1")
    assert change["fields"][0]["before"] == "3×2,5" and change["confirmation"] == "image"
    registry = facts.build(parse.parse(summary.text.encode("utf-8")), lines, dict(summary.records))
    by_code = {f["confirmation_code"] for f in registry["facts"]}
    assert {"image", "unverified", "question", "gap"} <= by_code


@pytest.mark.parametrize(("verdict", "figures", "expected"), [
    (("incomplete",), {}, "переход досчитан не полностью"),
    (("content_same", "zones_only"), {}, "основное содержание совпадает, изменены только служебные зоны"),
    (("different",), {"different": 3, "style_only": 1}, "есть отличия на 3 л., из них только оформление линий — 1"),
    (("composition_changed",), {"added": 2, "removed": 1}, "изменён состав (+2 / −1 л.)"),
    (("needs_review", "calculation_failed"), {"needs_review": 4, "failed": 2}, "нужна проверка: 4; ошибка расчёта: 2"),
])
def test_the_engines_verdict_is_worded_as_the_original_worded_it(verdict, figures, expected) -> None:
    assert verdict_text(figures, verdict) == expected


# -- the intake of an MD file -----------------------------------------------------------------------------------------------------

def test_an_md_file_that_is_not_utf8_is_refused_not_recoded() -> None:
    with pytest.raises(ValueError, match="not UTF-8"):
        parse.parse("# Сводка\n".encode("cp1251"))


def test_a_file_with_no_transition_has_no_transition_and_says_so() -> None:
    manifest = parse.parse("# Заметки\n\nпросто текст\n".encode("utf-8"))
    assert manifest["transitions"] == [] and manifest["issues"][0]["code"] == "NO_TRANSITIONS"


def test_the_numbers_of_the_lines_are_those_of_the_file_and_a_bom_and_crlf_shift_nothing() -> None:
    text = "# Сводка изменений X\r\n\r\n## 1. X: V1 → V2\r\n\r\n### л.1 · План (A стр. PDF 1 → B стр. PDF 2)\r\n\r\n- **Щит** — 1 → 2\r\n"
    plain = parse.parse(text.encode("utf-8"))
    bom = parse.parse(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert plain["transitions"][0]["line_start"] == bom["transitions"][0]["line_start"] == 3
    sheet = plain["transitions"][0]["sheets"][0]
    assert (sheet["line_start"], sheet["a_page"], sheet["b_page"], sheet["items"]) == (5, 1, 2, 1)
    assert parse.locate(plain, 7)["sheet"] is sheet


def test_a_break_in_the_chain_and_a_repeated_pair_are_reported_not_completed() -> None:
    text = "# Сводка изменений X\n\n## 1. X: V1 → V2\n\n- a\n\n## 2. X: V3 → V4\n\n- b\n\n## 3. X: V3 → V4\n\n- c\n"
    codes = [i["code"] for i in parse.parse(text.encode("utf-8"))["issues"]]
    assert codes.count("CHAIN_GAP") == 2 and codes.count("DUPLICATE_PAIR") == 1
