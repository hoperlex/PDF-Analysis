"""Hand-authored issue and near-miss archetypes from W56A-FREEZE-01 §3.

These are project statements, not normative claims. One source line is one PDF
text operator; the oracle cites the extracted PDF text, never portal markdown.
"""

from __future__ import annotations

from dataclasses import dataclass


PROFILE = "ar_v2"
CATEGORIES = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout",
    "facade", "roof", "documentation",
)


@dataclass(frozen=True)
class Issue:
    id: str
    category: str
    archetype: str
    statements: tuple[str, ...]
    missing_content: str | None = None


@dataclass(frozen=True)
class Control:
    id: str
    category: str
    archetype: str
    statement: str
    scope: str
    why_not_issue: str


ISSUES = (
    Issue("ic_area", "internal_contradiction", "room_area", (
        "План: помещение 101, площадь 18,0 м2.",
        "Экспликация: помещение 101, площадь 21,0 м2.")),
    Issue("ic_date", "internal_contradiction", "revision_date", (
        "Лист АР-01: дата изменения 12.05.2026.",
        "Лист АР-01: дата изменения 14.05.2026.")),
    Issue("ic_use", "internal_contradiction", "room_use", (
        "Таблица помещений: номер 102, кухня.",
        "Экспликация: номер 102, спальня.")),
    Issue("ph_note", "explicit_placeholder", "active_note", (
        "Действующее примечание: отделку лестницы уточнить.",)),
    Issue("ph_cell", "explicit_placeholder", "active_table_cell", (
        "Действующая ведомость дверей: материал TBD.",)),
    Issue("ph_callout", "explicit_placeholder", "active_callout", (
        "Действующая выноска: узел примыкания не определено.",)),
    Issue("di_room", "dimensions", "room_length", (
        "План: длина помещения 201 равна 4,20 м.",
        "Ведомость: длина помещения 201 равна 4,80 м.")),
    Issue("di_floor", "dimensions", "floor_height", (
        "Разрез: высота этажа 2 равна 3,30 м.",
        "Примечание: высота этажа 2 равна 3,60 м.")),
    Issue("di_door", "dimensions", "door_width", (
        "Ведомость: ширина двери Д-01 равна 900 мм.",
        "Выноска: ширина двери Д-01 равна 800 мм.")),
    Issue("la_adjacent", "layout", "room_adjacency", (
        "Легенда плана: помещение 301 граничит с коридором.",
        "Примечание к плану: помещение 301 граничит с кладовой.")),
    Issue("la_entrance", "layout", "entrance_side", (
        "Подпись плана: главный вход с востока.",
        "Текст проекта: главный вход с запада.")),
    Issue("la_placement", "layout", "room_placement", (
        "Ведомость 1 этажа: помещение 302 у северной стены.",
        "Ведомость 1 этажа: помещение 302 у южной стены.")),
    Issue("fa_material", "facade", "facade_material", (
        "Фасад северный: облицовка кирпич.",
        "Примечание к северному фасаду: облицовка штукатурка.")),
    Issue("fa_windows", "facade", "window_count", (
        "Ведомость северного фасада: 8 окон.",
        "Примечание к северному фасаду: 10 окон.")),
    Issue("fa_colour", "facade", "colour_code", (
        "Фасад южный: цвет RAL 9010.",
        "Ведомость отделки южного фасада: цвет RAL 7016.")),
    Issue("ro_slope", "roof", "roof_slope", (
        "План кровли: уклон зоны А равен 2 процента.",
        "Примечание к кровле: уклон зоны А равен 5 процентов.")),
    Issue("ro_drains", "roof", "drain_count", (
        "План кровли: воронок 4 штуки.",
        "Ведомость кровли: воронок 6 штук.")),
    Issue("ro_parapet", "roof", "parapet_height", (
        "Деталь кровли: парапет 600 мм.",
        "Примечание к кровле: парапет 800 мм.")),
    Issue("do_sheet", "documentation", "promised_sheet_missing", (
        "Реестр комплекта: лист АР-99 План кровли включен.",),
        missing_content="лист АР-99 План кровли"),
    Issue("do_section", "documentation", "promised_section_missing", (
        "Оглавление: раздел 4 Ведомость отделки включен.",),
        missing_content="раздел 4 Ведомость отделки"),
    Issue("do_title", "documentation", "sheet_title_mismatch", (
        "Реестр: лист АР-02 План фасадов.",
        "Заголовок листа АР-02: План помещений.")),
)

CONTROLS = (
    Control("control_area", "internal_contradiction", "different_rooms",
            "Помещение 401 имеет 18,0 м2, помещение 402 имеет 21,0 м2.",
            "разные помещения", "Площади относятся к разным помещениям."),
    Control("control_resolved", "explicit_placeholder", "resolved_note",
            "Уточнение выполнено: отделка лестницы назначена.",
            "завершенное примечание", "Фраза сообщает о выполненном уточнении."),
    Control("control_units", "dimensions", "equivalent_units",
            "Длина стены 3,00 м равна 3000 мм.",
            "одна стена", "Записи задают одну и ту же длину."),
    Control("control_floors", "layout", "different_floors",
            "План 1 этажа: кухня слева; план 2 этажа: кухня справа.",
            "разные этажи", "Два явно названных этажа могут различаться."),
    Control("control_facades", "facade", "different_facades",
            "Северный фасад кирпич; южный фасад штукатурка.",
            "разные фасады", "Материалы относятся к разным фасадам."),
    Control("control_zones", "roof", "different_roof_zones",
            "Кровля, зона А: уклон 2 процента; зона Б: 5 процентов.",
            "разные зоны", "Уклоны относятся к разным названным зонам."),
    Control("control_unpromised", "documentation", "unpromised_sheet",
            "Реестр содержит листы АР-01 и АР-02.",
            "комплект без обещания АР-99", "Реестр не обещает отсутствующий лист АР-99."),
)
