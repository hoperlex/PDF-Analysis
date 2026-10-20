"""Hand-authored issue and near-miss archetypes from W56A-FREEZE-01 §3.

These are project statements, not normative claims. One source line is one PDF
text operator; the oracle cites the extracted PDF text, never portal markdown.

The vocabulary is the sealed ``FindingCategory`` enum of the API contract, in its
order (``test_seeded_categories_equal_the_sealed_api_enum``). The seven original
categories come from W56A-FREEZE-01. The five normative ones (``evacuation``,
``fire_safety``, ``accessibility``, ``insulation``, ``sound``), added to the enum by
W57A-SEAL-01B, were given their cases by GATE-FIX-CONTRACT-01 with the same rule as
the original seven: a planted contradiction between two statements of the document
itself (three per category), or one near-miss whose two values belong to different
named objects (one per category). No case names a norm, a clause or a normative
threshold, so the oracle needs no norm text: whether a value would also violate a
norm is the retrieval layer's question, not this corpus's.
"""

from __future__ import annotations

from dataclasses import dataclass


PROFILE = "ar_v2"
CATEGORIES = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout",
    "facade", "roof", "documentation",
    "evacuation", "fire_safety", "accessibility", "insulation", "sound",
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
    Issue("ev_width", "evacuation", "exit_width", (
        "План эвакуации: ширина выхода Э-1 равна 1,20 м.",
        "Ведомость выходов: ширина выхода Э-1 равна 0,80 м.")),
    Issue("ev_route", "evacuation", "route_length", (
        "План 5 этажа: путь эвакуации из помещения 501 равен 25 м.",
        "Схема эвакуации: путь эвакуации из помещения 501 равен 40 м.")),
    Issue("ev_stairs", "evacuation", "stair_count", (
        "Пояснение к плану: со 2 этажа ведут 2 эвакуационные лестницы.",
        "Схема эвакуации: со 2 этажа ведет 1 эвакуационная лестница.")),
    Issue("fs_rating", "fire_safety", "partition_fire_rating", (
        "Ведомость перегородок: перегородка ПР-1 имеет предел огнестойкости EI 45.",
        "Примечание к плану: перегородка ПР-1 имеет предел огнестойкости EI 15.")),
    Issue("fs_door", "fire_safety", "fire_door_type", (
        "Ведомость дверей: дверь Д-05 противопожарная, тип EI 30.",
        "Выноска: дверь Д-05 обычная, без предела огнестойкости.")),
    Issue("fs_class", "fire_safety", "structural_fire_class", (
        "Пояснение: класс конструктивной пожарной опасности здания С0.",
        "Экспликация: класс конструктивной пожарной опасности здания С1.")),
    Issue("ac_ramp", "accessibility", "ramp_slope", (
        "План входа: уклон пандуса ПН-1 равен 5 процентов.",
        "Примечание к плану: уклон пандуса ПН-1 равен 10 процентов.")),
    Issue("ac_lift", "accessibility", "lift_cabin_depth", (
        "Ведомость лифтов: глубина кабины лифта Л-1 равна 2100 мм.",
        "Примечание к плану: глубина кабины лифта Л-1 равна 1400 мм.")),
    Issue("ac_parking", "accessibility", "accessible_parking", (
        "План участка: на стоянке выделено 4 места для маломобильных групп.",
        "Пояснительная записка: на стоянке выделено 2 места для маломобильных групп.")),
    Issue("in_thickness", "insulation", "insulation_thickness", (
        "Ведомость стен: толщина утеплителя стены НС-1 равна 150 мм.",
        "Узел стены: толщина утеплителя стены НС-1 равна 100 мм.")),
    Issue("in_material", "insulation", "insulation_material", (
        "Ведомость полов: утеплитель пола 1 этажа экструдированный пенополистирол.",
        "Деталь пола: утеплитель пола 1 этажа минеральная вата.")),
    Issue("in_glazing", "insulation", "glazing_chambers", (
        "Ведомость окон: стеклопакет окна ОК-2 двухкамерный.",
        "Узел окна: стеклопакет окна ОК-2 однокамерный.")),
    Issue("so_index", "sound", "partition_sound_index", (
        "Ведомость перегородок: индекс звукоизоляции перегородки ПГ-1 равен 52 дБ.",
        "Примечание к плану: индекс звукоизоляции перегородки ПГ-1 равен 41 дБ.")),
    Issue("so_impact", "sound", "impact_noise_level", (
        "Ведомость перекрытий: уровень ударного шума под перекрытием Пк-1 равен 58 дБ.",
        "Узел перекрытия: уровень ударного шума под перекрытием Пк-1 равен 70 дБ.")),
    Issue("so_layer", "sound", "sound_layer_thickness", (
        "Узел перегородки ПГ-2: звукоизоляционный слой толщиной 50 мм.",
        "Ведомость перегородок: звукоизоляционный слой перегородки ПГ-2 толщиной 30 мм.")),
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
    Control("control_exits", "evacuation", "different_exits",
            "Выход Э-2 шириной 1,20 м на 1 этаже; выход Э-3 шириной 0,80 м в цоколе.",
            "разные выходы", "Ширины относятся к разным выходам."),
    Control("control_ratings", "fire_safety", "different_fire_partitions",
            "Перегородка ПР-2 имеет предел EI 45; перегородка ПР-3 имеет предел EI 15.",
            "разные перегородки", "Пределы огнестойкости относятся к разным перегородкам."),
    Control("control_ramps", "accessibility", "different_ramps",
            "Пандус ПН-2 имеет уклон 5 процентов; пандус ПН-3 имеет уклон 8 процентов.",
            "разные пандусы", "Уклоны относятся к разным пандусам."),
    Control("control_walls", "insulation", "different_walls",
            "Утеплитель стены НС-2 толщиной 150 мм; утеплитель стены НС-3 толщиной 100 мм.",
            "разные стены", "Толщины относятся к разным стенам."),
    Control("control_partitions", "sound", "different_sound_partitions",
            "Перегородка ПГ-3 имеет индекс 52 дБ; перегородка ПГ-4 имеет индекс 41 дБ.",
            "разные перегородки", "Индексы звукоизоляции относятся к разным перегородкам."),
)
