#!/usr/bin/env python3
"""Rebuild (or check) the omission specimens of `SECTION-CATEGORY-OCR-01` (`R-146ao`).

    python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py          # check
    python3 -I fixtures/recorded/sections_widen/omission/build_specimens.py --write  # rewrite

Ten hand-authored files, one positive and one negative for each of AI TX EOM SS ITP, written under
``fixtures/recorded/sections_widen/omission/<code>/<case>.json``. The cases below are the source; the files are
generated from them, and ``tests/integration/sections/test_section_omission_specimens.py`` holds the files equal
to what this builder writes, so neither can drift. Imports nothing from ``auditmanager``.

A positive is a text in which a term is named on a scheme, plan or explication and does not occur in the schedule
or specification, with the reply a model might give; a negative is a reply the stage's absence check must refuse
(the term is in the schedule in another case, with another dash, wrapped over a line, on the second page of the
range; a page of the range has no text). No model produced any of it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
TASK = "SECTION-CATEGORY-OCR-01"
STATEMENT = (
    "Text and reply authored by hand for SECTION-CATEGORY-OCR-01 to show what the omission rule is meant to "
    "publish and what the stage's absence check must refuse. No model produced this reply. Not field evidence "
    "for any profile's expert review; it says nothing about how a model answers."
)


def omission(label, term, naming_page, naming_quote, first, last, heading_page, heading_quote, finding):
    return {
        "category": "documentation",
        "finding_text": f"Синтетический ответ ({label}), не результат вызова модели: {finding}",
        "recommendation_text": "Сверить ведомость или спецификацию с местом, которое называет запись.",
        "evidence": [{"page_number": naming_page, "quote": naming_quote}],
        "omission": {
            "term": term,
            "first_page": first,
            "last_page": last,
            "heading": {"page_number": heading_page, "quote": heading_quote},
        },
    }


CASES = {
    "AI": {
        "label": "АИ",
        "positive": dict(
            pages=[
                "План пола. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000.",
                "Ведомость дверных заполнений\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д-2 Дверь межкомнатная, 6 шт.\nМарка Д-3 Дверь в кухню, 1 шт.",
            ],
            expect="finding", reason=None,
            reply=("Д-5", 1, "Дверь Д-5 в санузел", 2, 2, 2, "Ведомость дверных заполнений",
                   "марка Д-5 названа на плане на странице 1 и не найдена в ведомости дверных заполнений."),
        ),
        "dash_negative": dict(
            pages=[
                "План пола. Помещение 4 — санузел. Дверь Д-5 в санузел, ширина 800 мм. Отметка чистого пола 0,000.",
                "Ведомость дверных заполнений\nМарка Д-1 Дверь входная, 2 шт.\nМарка Д–5 Дверь в санузел, 1 шт.\nМарка Д-3 Дверь в кухню, 1 шт.",
            ],
            expect="dropped", reason="term_present_in_range",
            reply=("Д-5", 1, "Дверь Д-5 в санузел", 2, 2, 2, "Ведомость дверных заполнений",
                   "марка Д-5 названа на плане и не найдена в ведомости (в ведомости она записана через длинное тире)."),
        ),
    },
    "TX": {
        "label": "ТХ",
        "positive": dict(
            pages=[
                "Экспликация оборудования. Поз. ММ-2 мойка двухсекционная. Поз. ХШ-4 шкаф холодильный. Поз. ПЭ-6 плита электрическая.",
                "Спецификация оборудования\nПоз. ММ-2 Мойка двухсекционная, 1 шт.\nПоз. ПЭ-6 Плита электрическая, 1 шт.\nПоз. СТ-8 Стол производственный, 3 шт.",
            ],
            expect="finding", reason=None,
            reply=("ХШ-4", 1, "Поз. ХШ-4 шкаф холодильный", 2, 2, 2, "Спецификация оборудования",
                   "позиция ХШ-4 названа в экспликации на странице 1 и не найдена в спецификации оборудования."),
        ),
        "wrapped_negative": dict(
            pages=[
                "Экспликация оборудования. Поз. ММ-2 мойка двухсекционная. Поз. ХШ-4 шкаф холодильный. Поз. ПЭ-6 плита электрическая.",
                "Спецификация оборудования\nПоз. ММ-2 Мойка двухсекционная, 1 шт.\nПоз. ХШ-\n4 Шкаф холодильный, 1 шт.\nПоз. СТ-8 Стол производственный, 3 шт.",
            ],
            expect="dropped", reason="term_present_in_range",
            reply=("ХШ-4", 1, "Поз. ХШ-4 шкаф холодильный", 2, 2, 2, "Спецификация оборудования",
                   "позиция ХШ-4 названа в экспликации и не найдена в спецификации (в спецификации обозначение перенесено на новую строку)."),
        ),
    },
    "EOM": {
        "label": "ЭОМ",
        "positive": dict(
            pages=[
                "Однолинейная схема. Щит ЩО-3 (освещение этажа): вводной автомат, групповые автоматы, УЗО. Щит ЩР-1 (розеточная сеть).",
                "Спецификация оборудования и материалов\nЩит ЩР-1 в сборе, 1 шт.\nАвтоматический выключатель, 1 шт.\nКабель ВВГнг-LS, 120 м.",
            ],
            expect="finding", reason=None,
            reply=("ЩО-3", 1, "Щит ЩО-3 (освещение этажа)", 2, 2, 2, "Спецификация оборудования и материалов",
                   "щит ЩО-3 назван на схеме на странице 1 и не найден в спецификации."),
        ),
        "case_negative": dict(
            pages=[
                "Однолинейная схема. Щит ЩО-3 (освещение этажа): вводной автомат, групповые автоматы, УЗО. Щит ЩР-1 (розеточная сеть).",
                "Спецификация оборудования и материалов\nЩит ЩР-1 в сборе, 1 шт.\nЩит що-3 в сборе, 1 шт.\nКабель ВВГнг-LS, 120 м.",
            ],
            expect="dropped", reason="term_present_in_range",
            reply=("ЩО-3", 1, "Щит ЩО-3 (освещение этажа)", 2, 2, 2, "Спецификация оборудования и материалов",
                   "щит ЩО-3 назван на схеме и не найден в спецификации (в спецификации он записан строчными буквами)."),
        ),
    },
    "SS": {
        "label": "СС",
        "positive": dict(
            pages=[
                "Структурная схема видеонаблюдения. Камера К-12 у входа, камера К-13 во дворе, коммутатор КМ-1 в серверной.",
                "Кабельный журнал\nКабель К-13 — витая пара, 40 м.\nКабель К-14 — витая пара, 25 м.\nКабель КМ-1 — оптика, 15 м.",
                "Продолжение кабельного журнала\nКабель К-15 — витая пара, 32 м.\nКабель К-16 — витая пара, 18 м.\nИтого кабеля: 130 м.",
            ],
            expect="finding", reason=None,
            reply=("К-12", 1, "Камера К-12 у входа", 2, 3, 2, "Кабельный журнал",
                   "камера К-12 названа на схеме на странице 1 и не найдена в кабельном журнале на страницах 2–3."),
        ),
        "second_page_negative": dict(
            pages=[
                "Структурная схема видеонаблюдения. Камера К-12 у входа, камера К-13 во дворе, коммутатор КМ-1 в серверной.",
                "Кабельный журнал\nКабель К-13 — витая пара, 40 м.\nКабель К-14 — витая пара, 25 м.\nКабель КМ-1 — оптика, 15 м.",
                "Продолжение кабельного журнала\nКабель К-12 — витая пара, 22 м.\nКабель К-16 — витая пара, 18 м.\nИтого кабеля: 120 м.",
            ],
            expect="dropped", reason="term_present_in_range",
            reply=("К-12", 1, "Камера К-12 у входа", 2, 3, 2, "Кабельный журнал",
                   "камера К-12 названа на схеме и не найдена в кабельном журнале (запись есть на второй странице журнала)."),
        ),
    },
    "ITP": {
        "label": "ИТП",
        "positive": dict(
            pages=[
                "Принципиальная схема ИТП. Насос Н-2 циркуляционный, теплообменник ТО-1 отопления, регулятор РТ-3.",
                "Спецификация оборудования\nТеплообменник ТО-1, 1 шт.\nРегулятор РТ-3, 1 шт.\nНасос Н-1 циркуляционный, 1 шт.",
            ],
            expect="finding", reason=None,
            reply=("Н-2", 1, "Насос Н-2 циркуляционный", 2, 2, 2, "Спецификация оборудования",
                   "насос Н-2 назван на схеме на странице 1 и не найден в спецификации оборудования."),
        ),
        "scan_negative": dict(
            pages=[
                "Принципиальная схема ИТП. Насос Н-2 циркуляционный, теплообменник ТО-1 отопления, регулятор РТ-3.",
                "Спецификация оборудования\nТеплообменник ТО-1, 1 шт.\nРегулятор РТ-3, 1 шт.\nНасос Н-1 циркуляционный, 1 шт.",
                "Лист 3",
            ],
            expect="dropped", reason="range_page_without_text",
            reply=("Н-2", 1, "Насос Н-2 циркуляционный", 2, 3, 2, "Спецификация оборудования",
                   "насос Н-2 назван на схеме и не найден в спецификации на страницах 2–3 (третья страница без текста)."),
        ),
    },
}


def documents() -> dict[Path, str]:
    """Every file this builder owns: path -> exact text."""
    out: dict[Path, str] = {}
    for code, group in CASES.items():
        for case, body in group.items():
            if case == "label":
                continue
            document = {
                "format": "section-omission-specimen/1",
                "section_code": code,
                "case": case,
                "expect": body["expect"],
                "expect_reason": body["reason"],
                "origin": {
                    "kind": "synthetic",
                    "statement": STATEMENT,
                    "task_id": TASK,
                    "source_report": f"docs/program/{TASK}.md",
                    "filed_by": TASK,
                },
                "pages": body["pages"],
                "observations": [omission(group["label"], *body["reply"])],
            }
            out[OUT / code.lower() / f"{case}.json"] = json.dumps(document, ensure_ascii=False, indent=1) + "\n"
    return out


def main(argv: list[str]) -> int:
    planned = documents()
    if argv == ["--write"]:
        for path, text in planned.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        print(f"wrote {len(planned)} specimens")
        return 0
    if argv:
        print(__doc__)
        return 2
    found = {path for path in OUT.glob("*/*.json")}
    drift = sorted(
        str(path.relative_to(ROOT))
        for path in found | set(planned)
        if (planned.get(path) is None) or not path.is_file() or path.read_text(encoding="utf-8") != planned[path]
    )
    if drift:
        print("specimens differ from the builder:", *drift, sep="\n  ")
        return 1
    print("specimens match")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
