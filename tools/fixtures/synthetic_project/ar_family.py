"""АР comparison family: a version series of «СИНТ-02-АР.1» (Р, Изм.0…Изм.3) for «Сравнение версий» and
a stage pair П «СИНТ-02-АР» → Р {«СИНТ-02-АР.1», «СИНТ-02-АР.2»} for «Сравнение стадий».

All of them are plain PDFs (the comparison modules take PDFs, not portal bundles). Sheet titles follow
the passport form «Тип. Корпус N. Уровень», so a sheet passport can match П and Р sheets. A sheet keeps
the «Изм.» of its last change; an unchanged sheet is byte-identical to its previous version.

Changes, authored here and written to `ar_family_key.json`:

V1→V2 (Изм.1): floor-1 plan — partition 104/105 moved 30,0 → 29,4 м (areas 45,0/45,0 → 40,5/49,5) and a
  second door into 102 from the vestibule; section 1-1 — parapet +7,200 → +7,500; specification — ДВ-1
  18 → 19.
V2→V3 (Изм.2): floor-2 plan — 209 «Комната отдыха» → «Переговорная», stair doors shown as fire-rated
  (red); facade — entrance canopy added, outline heavier; sheet 8 «Узел 1» added.
V3→V4 (Изм.3): permit table on sheet 1 declares: roof drains 4 → 6 (found), ОК-2 quantity changed (not
  done), and nobody declares the floor-1 rename 113 «Насосная» → «Насосная станция» (stamp not raised);
  roof plan — drains 4 → 6; specification — ДП-2 added, ДВ-3 removed, ОК-1 24 → 22.
"""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium

from comparison import scene

from . import building
from .building import A3_PLAN, AXES_X, DEPTH, LENGTH, ORGANISATION, Plan, Room, draw_plan
from .kit import BLUE, GREY, LIGHT, RED, WALL_FILL, Ops, font
from .model import A3L, A4

RED_DOOR = (0.85, 0.1, 0.1)


@dataclass(frozen=True)
class Variant:
    designation: str = "СИНТ-02-АР.1"
    stage: str = "Р"
    partition_104: float = 30.0
    door_102: bool = False
    pump_room: str = "Насосная"
    room_209: str = "Комната отдыха"
    fire_doors: bool = False
    parapet: str = "+7,200"
    canopy: bool = False
    drains: int = 4
    roof_slope: str = "2 %"
    permit: bool = False
    detail_sheet: bool = False
    spec: tuple = ()
    rev: dict = field(default_factory=dict)  # sheet key -> «Изм.N»
    date: dict = field(default_factory=dict)  # sheet key -> date
    p_stage: bool = False  # simplified П-stage drawing (no explication numbers on doors, ТЭП instead of permit)


BASE_SPEC = (
    ("ОК-1", "Блок оконный ПВХ 1800×1500", "12", "12", "24", ""),
    ("ОК-2", "Блок оконный ПВХ 1200×1500", "4", "4", "8", "Лестничные клетки"),
    ("ДН-1", "Дверь наружная остеклённая 1400×2100", "1", "—", "1", "Главный вход"),
    ("ДВ-1", "Дверь внутренняя 1000×2100", "10", "8", "18", ""),
    ("ДВ-2", "Дверь внутренняя 800×2100", "2", "2", "4", "Санузлы"),
    ("ДВ-3", "Дверь внутренняя 900×2100", "1", "1", "2", "Серверная, комната отдыха"),
    ("ДП-1", "Дверь противопожарная EI 30 1000×2100", "3", "2", "5", "Тех. помещения"),
)


def _spec_v2():
    return tuple(("ДВ-1", r[1], "11", "8", "19", "") if r[0] == "ДВ-1" else r for r in BASE_SPEC)


def _spec_v4():
    out = []
    for r in _spec_v2():
        if r[0] == "ДВ-3":
            continue
        if r[0] == "ОК-1":
            r = ("ОК-1", r[1], "11", "11", "22", "")
        out.append(r)
    out.append(("ДП-2", "Дверь противопожарная EI 60 1000×2100", "1", "1", "2", "Лестничные клетки"))
    return tuple(out)


def _floor1_rooms(v: Variant) -> tuple[Room, ...]:
    rooms = []
    for r in building.FLOOR1:
        if r.number == "104":
            r = dataclasses.replace(r, x1=v.partition_104)
        elif r.number == "105":
            r = dataclasses.replace(r, x0=v.partition_104)
        elif r.number == "113":
            r = dataclasses.replace(r, name=v.pump_room)
        rooms.append(r)
    return tuple(rooms)


def _floor2_rooms(v: Variant) -> tuple[Room, ...]:
    return tuple(dataclasses.replace(r, name=v.room_209) if r.number == "209" else r for r in building.FLOOR2)


def _doors(v: Variant, floor: int) -> list:
    doors = [list(d) for d in building._DOORS[floor]]
    if floor == 1 and v.door_102:
        doors.append([12, 3.0, 1.0, "es"])
    if v.fire_doors and floor == 2:
        for d in doors:
            if (d[0], d[1]) in ((3, 7.5), (31, 10.5)):
                d.append(RED_DOOR)
    return [tuple(d) for d in doors]


# --------------------------------------------------------------------------------------------- sheets

def _explication(o: Ops, x: float, top: float, rooms: tuple[Room, ...], floor: int, key: str) -> None:
    o.text(x, top + 8, f"Экспликация помещений этажа {floor}", 9)
    rows = [["Номер", "Наименование", "Площадь, м²"]]
    for r in rooms:
        rows.append([r.number, r.name, r.area_text()])
    total = sum(r.area for r in rooms)
    rows.append(["", "Итого по этажу", f"{total:.1f}".replace(".", ",")])
    o.table(x, top, [42, 160, 62], rows, size=7.2, row_h=13.5, key=key)


def sheet_general(v: Variant, sheets: list[str]) -> Ops:
    o = Ops("G")
    o.text(70, 800, f"{v.designation}. Архитектурные решения. Корпус 1. Стадия {v.stage}", 12)
    o.text(70, 784, building.OBJECT_NAME + " (синтетический объект)", 9)
    y = 760
    paras = [
        "1. " + building.FACTS["k1"] + "; высота этажа 3,3 м.",
        "2. " + building.FACTS["zero"] + ".",
        "3. Наружные стены — газобетонные блоки 400 мм с облицовкой; перегородки — 150 мм.",
        "4. Кровля плоская, уклон " + v.roof_slope + ", внутренний водосток.",
        "5. С" + building.FACTS["fire"][1:] + "; " + building.FACTS["fire_k1"] + ".",
        "6. " + building.DISCLAIMER,
    ]
    for i, p in enumerate(paras, 1):
        y = o.para(70, y, 520, p, 8.5, key=f"gp{i}") - 3
    o.text(70, y - 10, "Ведомость листов", 9.5)
    rows = [["Лист", "Наименование"]] + [[str(i + 1), t] for i, t in enumerate(sheets)]
    o.table(70, y - 16, [40, 330], rows, size=7.6, row_h=14, key="vl")
    if v.p_stage:
        o.text(660, 800, "Технико-экономические показатели", 9.5)
        o.table(660, 792, [300, 90], [
            ["Показатель", "Значение"],
            ["Площадь застройки корпуса 1, м²", "648,0"],
            ["Общая площадь корпуса 1, м²", "1 184,0"],
            ["Строительный объём, м³", "4 860,0"],
            ["Этажность", "2"],
        ], size=7.8, row_h=15, key="tep")
    if v.permit:
        o.text(660, 800, "Разрешение на внесение изменений № 3 от 02.11.2026", 9.5)
        o.table(660, 792, [36, 300, 74], [
            ["Лист", "Содержание изменения", "Изм."],
            ["4", "Количество водосточных воронок изменено с 4 на 6", "Изм.3"],
            ["7", "Изменено количество оконных блоков ОК-2", "Изм.3"],
        ], size=7.8, row_h=15, key="permit")
    return o


def sheet_plan1(v: Variant) -> Ops:
    o = Ops("P1")
    o.text(110, 790, "План этажа 1. Корпус 1. М 1:100", 11, key="title")
    rooms = _floor1_rooms(v)
    draw_plan(o, A3_PLAN, 1, rooms=rooms, doors=_doors(v, 1), key_prefix="room", dims=True)
    _explication(o, 880, 760, rooms, 1, "expl")
    if not v.p_stage:
        o.para(880, 360, 290, "Отметка чистого пола этажа 1 — 0,000. Двери показаны по спецификации, лист 7.", 7.8,
               key="note1")
    return o


def sheet_plan2(v: Variant) -> Ops:
    o = Ops("P2")
    o.text(110, 790, "План этажа 2. Корпус 1. М 1:100", 11, key="title")
    rooms = _floor2_rooms(v)
    draw_plan(o, A3_PLAN, 2, rooms=rooms, doors=_doors(v, 2), key_prefix="room", dims=True)
    _explication(o, 880, 760, rooms, 2, "expl")
    o.para(880, 360, 290, "Отметка чистого пола этажа 2 — +3,300.", 7.8, key="note1")
    if v.fire_doors:
        o.para(880, 340, 290, "Двери лестничных клеток — противопожарные EI 60, показаны красным.", 7.8, key="note2")
    return o


def sheet_roof(v: Variant) -> Ops:
    o = Ops("R")
    p = A3_PLAN
    o.text(110, 790, "План кровли. Корпус 1. М 1:100", 11, key="title")
    o.rect(p.x(0), p.y(0), LENGTH * p.scale, DEPTH * p.scale, 1.4)
    o.rect(p.x(0) + 8, p.y(0) + 8, LENGTH * p.scale - 16, DEPTH * p.scale - 16, 0.5)  # parapet inner line
    # ridge/valley lines towards the drains
    drains = [(9, 9), (27, 9), (9, 4.5), (27, 13.5), (18, 4.5), (18, 13.5)][: v.drains]
    if v.drains == 4:
        drains = [(9, 4.5), (9, 13.5), (27, 4.5), (27, 13.5)]
    else:
        drains = [(9, 4.5), (9, 13.5), (27, 4.5), (27, 13.5), (18, 4.5), (18, 13.5)]
    o.line(p.x(18), p.y(0) + 8, p.x(18), p.y(DEPTH) - 8, 0.4, GREY, dash=(6, 3))
    o.line(p.x(0) + 8, p.y(9), p.x(LENGTH) - 8, p.y(9), 0.4, GREY, dash=(6, 3))
    for i, (mx, my) in enumerate(drains, 1):
        x, y = p.p(mx, my)
        o.circle(x, y, 7, 0.8, BLUE)
        o.circle(x, y, 2.5, 0.6, BLUE)
        o.text(x + 10, y + 6, f"ВР-{i}", 7.5)
    for (mx, my, dx, dy) in ((4, 2, 1, 0), (32, 2, -1, 0), (4, 16, 1, 0), (32, 16, -1, 0)):
        x, y = p.p(mx, my)
        o.arrow(x, y, x + dx * 40, y + dy * 40, 0.6)
        o.text(x + (dx * 4 if dx > 0 else -36), y + 5, f"i = {v.roof_slope}", 7.5)
    for label, xm in AXES_X:
        o.axis_bubble(p.x(xm), p.y(DEPTH) + 30, label)
        o.line(p.x(xm), p.y(DEPTH) + 21, p.x(xm), p.y(DEPTH), 0.25, GREY, dash=(12, 3, 2, 3))
    for label, ym in (("А", 0.0), ("Г", 18.0)):
        o.axis_bubble(p.x(0) - 30, p.y(ym), label)
        o.line(p.x(0) - 21, p.y(ym), p.x(0), p.y(ym), 0.25, GREY, dash=(12, 3, 2, 3))
    y = 760
    o.text(880, y, "Примечания", 9.5)
    y -= 16
    notes = [
        f"1. Уклон кровли {v.roof_slope} к водосточным воронкам.",
        f"2. Водосток внутренний: {v.drains} воронки." if v.drains == 4 else f"2. Водосток внутренний: {v.drains} воронок.",
        "3. Парапет h = 600 мм по всему периметру.",
        "4. Утеплитель — минераловатные плиты 200 мм.",
    ]
    for i, n in enumerate(notes, 1):
        y = o.para(880, y, 290, n, 8, key=f"note{i}") - 3
    return o


def sheet_section(v: Variant) -> Ops:
    o = Ops("S")
    o.text(110, 790, "Разрез 1-1. Корпус 1. М 1:100", 11, key="title")
    s, ox, oy = 30.0, 130.0, 340.0
    parapet = 7.2 if v.parapet == "+7,200" else 7.5
    o.line(ox - 60, oy - 1.2 * s, ox + 18 * s + 60, oy - 1.2 * s, 1.0)  # ground
    for i in range(14):
        o.line(ox - 60 + i * 30, oy - 1.2 * s, ox - 70 + i * 30, oy - 1.2 * s - 8, 0.4)
    o.rect(ox, oy - 1.2 * s, 0.4 * s, (parapet + 1.2) * s, 0.8, fill=WALL_FILL)
    o.rect(ox + 18 * s - 0.4 * s, oy - 1.2 * s, 0.4 * s, (parapet + 1.2) * s, 0.8, fill=WALL_FILL)
    for lvl in (0.0, 3.3, 6.6):
        o.rect(ox, oy + lvl * s - 0.22 * s, 18 * s, 0.22 * s, 0.6, fill=(0.6, 0.6, 0.6))
    for wall in (7.5, 10.5):
        o.rect(ox + wall * s - 0.075 * s, oy, 0.15 * s, 6.6 * s - 0.22 * s, 0.4, fill=WALL_FILL)
    for lvl in (0.0, 3.3):
        for wx in (0.0, 18.0):
            x = ox + wx * s - (0.0 if wx == 0 else 0.4 * s)
            o.rect(x, oy + (lvl + 0.9) * s, 0.4 * s, 1.5 * s, 0.4, fill=(1, 1, 1))
    o.hatch(ox + 0.4 * s, oy + 6.6 * s, 18 * s - 0.8 * s, 0.25 * s)
    levels = [("0,000", 0.0, "lv0"), ("+3,300", 3.3, "lv1"), ("+6,600", 6.6, "lv2"), (v.parapet, parapet, "lvp"),
              ("−1,200", -1.2, "lvg")]
    for label, lvl, key in levels:
        x, y = ox + 18 * s + 30, oy + lvl * s
        o.line(ox + 18 * s, y, x + 40, y, 0.3, GREY)
        o.polyline([(x, y), (x - 5, y + 7), (x + 5, y + 7)], 0.6, closed=True)
        o.text(x + 8, y + 3, label, 8, key=key)
    o.dim(ox, oy - 1.2 * s - 30, ox + 18 * s, oy - 1.2 * s - 30, "18000", offset=0)
    for label, ym in (("А", 0.0), ("Б", 7.5), ("В", 10.5), ("Г", 18.0)):
        o.axis_bubble(ox + ym * s, oy - 1.2 * s - 60, label)
    o.ctext(ox + 3.75 * s, oy + 1.5 * s, "103", 8)
    o.ctext(ox + 14.2 * s, oy + 1.5 * s, "109", 8)
    o.ctext(ox + 3.75 * s, oy + 4.8 * s, "202", 8)
    o.ctext(ox + 14.2 * s, oy + 4.8 * s, "208", 8)
    y = 760
    o.text(880, y, "Примечания", 9.5)
    y -= 16
    for i, n in enumerate([f"1. Отметка верха парапета {v.parapet}.", "2. Высота этажа 3,3 м.",
                           "3. Перекрытия — монолитные плиты 220 мм."], 1):
        y = o.para(880, y, 290, n, 8, key=f"note{i}") - 3
    return o


def sheet_facade(v: Variant) -> Ops:
    o = Ops("F")
    o.text(110, 790, "Фасад 1-7. Корпус 1. М 1:100", 11, key="title")
    s, ox, oy = 20.0, 110.0, 380.0
    parapet = 7.2 if v.parapet == "+7,200" else 7.5
    o.line(ox - 30, oy, ox + LENGTH * s + 30, oy, 1.2)
    o.rect(ox, oy, LENGTH * s, parapet * s, 1.6 if v.canopy else 0.8)
    for row, lvl in enumerate((0.9, 4.2)):
        for bay in range(6):
            cx = bay * 6 + 3
            if row == 0 and bay == 3:
                continue
            o.rect(ox + (cx - 0.9) * s, oy + lvl * s, 1.8 * s, 1.5 * s, 0.6, BLUE, fill=(0.88, 0.93, 1.0))
            o.line(ox + cx * s, oy + lvl * s, ox + cx * s, oy + (lvl + 1.5) * s, 0.4, BLUE)
    o.rect(ox + 18.2 * s, oy, 1.4 * s, 2.1 * s, 0.8, fill=(0.85, 0.85, 0.85))
    if v.canopy:
        o.rect(ox + 16.9 * s, oy + 2.6 * s, 4.0 * s, 0.25 * s, 0.8, fill=(0.4, 0.4, 0.4))
        o.line(ox + 17.0 * s, oy + 2.85 * s, ox + 17.0 * s, oy + 3.4 * s, 0.6)
        o.line(ox + 20.8 * s, oy + 2.85 * s, ox + 20.8 * s, oy + 3.4 * s, 0.6)
        o.text(ox + 21.2 * s, oy + 2.7 * s, "Козырёк над входом", 7.5, key="canopy")
    for label, xm in AXES_X:
        o.axis_bubble(ox + xm * s, oy - 30, label)
        o.line(ox + xm * s, oy - 21, ox + xm * s, oy, 0.25, GREY, dash=(12, 3, 2, 3))
    for label, lvl, key in (("0,000", 0.0, "lv0"), ("+3,300", 3.3, "lv1"), (v.parapet, parapet, "lvp")):
        x, y = ox + LENGTH * s + 20, oy + lvl * s
        o.polyline([(x, y), (x - 5, y + 7), (x + 5, y + 7)], 0.6, closed=True)
        o.text(x + 8, y + 3, label, 8, key=key)
    y = 300
    o.text(110, y, "Отделка фасада", 9.5)
    o.table(110, y - 8, [40, 330, 120], [
        ["Поз.", "Наименование", "Цвет"],
        ["1", "Облицовка фиброцементными панелями", "Светло-серый"],
        ["2", "Цоколь — керамогранит", "Графит"],
        ["3", "Оконные блоки ПВХ", "Белый"],
    ], size=7.6, row_h=14, key="finish")
    return o


def sheet_spec(v: Variant) -> Ops:
    o = Ops("SP")
    o.text(110, 790, "Спецификация заполнения проёмов. Корпус 1", 11, key="title")
    rows = [["Поз.", "Наименование", "Этаж 1", "Этаж 2", "Всего", "Примечание"]] + [list(r) for r in v.spec]
    o.table(110, 770, [50, 330, 60, 60, 60, 220], rows, size=8, row_h=17, key="spec")
    # window type sketches
    for i, (label, w, h) in enumerate((("ОК-1", 1.8, 1.5), ("ОК-2", 1.2, 1.5), ("ДН-1", 1.4, 2.1))):
        s, x0, y0 = 40.0, 140 + i * 170, 220
        o.rect(x0, y0, w * s, h * s, 0.9)
        o.line(x0 + w * s / 2, y0, x0 + w * s / 2, y0 + h * s, 0.5)
        o.ctext(x0 + w * s / 2, y0 + h * s + 8, label, 8)
        o.dim(x0, y0, x0 + w * s, y0, f"{int(w * 1000)}", offset=-14)
    return o


def sheet_detail(v: Variant) -> Ops:
    o = Ops("D")
    o.text(110, 790, "Узел 1. Примыкание кровли к парапету. М 1:10", 11, key="title")
    ox, oy, s = 300.0, 260.0, 100.0  # 1 m = 100 pt
    o.rect(ox, oy, 0.4 * s, 4.2 * s, 0.9, fill=WALL_FILL)  # parapet wall
    o.rect(ox + 0.4 * s, oy, 3.0 * s, 0.22 * s, 0.8, fill=(0.6, 0.6, 0.6))  # slab
    o.hatch(ox + 0.4 * s, oy + 0.22 * s, 3.0 * s, 0.2 * s)  # insulation
    o.rect(ox + 0.4 * s, oy + 0.42 * s, 3.0 * s, 0.05 * s, 0.6, fill=(0.2, 0.2, 0.2))  # membrane
    o.polyline([(ox + 0.4 * s, oy + 0.47 * s), (ox + 0.4 * s, oy + 1.0 * s), (ox - 0.05 * s, oy + 1.0 * s)], 1.2)
    o.rect(ox - 0.08 * s, oy + 4.2 * s, 0.56 * s, 0.06 * s, 0.8, fill=(0.3, 0.3, 0.3))  # coping
    for label, (x1, y1, x2, y2) in {
        "Парапетная крышка, оцинкованная сталь": (ox + 0.2 * s, oy + 4.26 * s, ox + 1.0 * s, oy + 4.6 * s),
        "Наплавляемая мембрана в 2 слоя": (ox + 1.5 * s, oy + 0.45 * s, ox + 2.0 * s, oy + 1.4 * s),
        "Утеплитель 200 мм": (ox + 2.2 * s, oy + 0.3 * s, ox + 2.6 * s, oy + 1.0 * s),
        "Плита покрытия 220 мм": (ox + 3.0 * s, oy + 0.1 * s, ox + 3.6 * s, oy + 0.6 * s),
    }.items():
        o.leader(x1, y1, x2, y2, label, 8)
    o.dim(ox, oy + 4.2 * s, ox, oy, "600", offset=30)
    return o


SHEET_TITLES = {
    "general": "Общие данные. Корпус 1",
    "plan1": "План. Корпус 1. Этаж 1",
    "plan2": "План. Корпус 1. Этаж 2",
    "roof": "План. Корпус 1. Кровля",
    "section": "Разрез 1-1. Корпус 1. Уровень +0,000",
    "facade": "Фасад 1-7. Корпус 1",
    "spec": "Спецификация. Корпус 1. Проёмы",
    "detail": "Узел 1. Корпус 1. Кровля",
}


def k2_plan(variant: str) -> Ops:
    """Корпус 2, production hall, 48 × 24 м, axes 1–9 / А–Д; Р adds a partition and a finished-goods store."""
    o = Ops("K2")
    p = Plan(ox=110.0, oy=300.0, scale=15.0)
    o.text(110, 790, "План этажа 1. Корпус 2. М 1:200", 11, key="title")
    o.rect(p.x(0), p.y(0), 48 * p.scale, 24 * p.scale, 1.6)
    o.rect(p.x(0) + 4, p.y(0) + 4, 48 * p.scale - 8, 24 * p.scale - 8, 0.5)
    for i in range(9):
        for j in range(5):
            o.rect(p.x(i * 6) - 4, p.y(j * 6) - 4, 8, 8, 0.5, fill=(0.2, 0.2, 0.2))
    for i, label in enumerate("123456789"):
        o.axis_bubble(p.x(i * 6), p.y(24) + 28, label)
    for j, label in enumerate("АБВГД"):
        o.axis_bubble(p.x(0) - 28, p.y(j * 6), label)
    o.rect(p.x(21), p.y(0) - 3, 4 * p.scale, 6, 0.8, fill=(1, 1, 1))
    o.text(p.x(21), p.y(0) - 16, "Ворота 4,0 × 4,2 м", 7.5, key="gate")
    if variant == "П":
        o.ctext(p.x(24), p.y(15), "301 Производственный зал 1 152,0 м²", 9, key="r301")
    else:
        o.rect(p.x(42) - 2, p.y(0), 4, 24 * p.scale, 0.6, fill=WALL_FILL)
        o.ctext(p.x(21), p.y(15), "301 Производственный зал 1 008,0 м²", 9, key="r301")
        o.ctext(p.x(45), p.y(15) + 6, "302 Склад готовой", 8, key="r302")
        o.ctext(p.x(45), p.y(15) - 6, "продукции 144,0 м²", 8, key="r302b")
    o.dim(p.x(0), p.y(0) - 34, p.x(48), p.y(0) - 34, "48000", offset=0)
    o.dim(p.x(48), p.y(0), p.x(48), p.y(24), "24000", offset=-40)
    o.para(940, 760, 230, "Высота до низа несущих конструкций покрытия 7,2 м.", 8, key="h")
    if variant == "Р":
        o.para(940, 730, 230, "Склад готовой продукции отделён перегородкой по оси 8.", 8, key="store")
    return o


def situational() -> Ops:
    o = Ops("SIT")
    o.text(110, 790, "Ситуационная схема. М 1:2000", 11, key="title")
    ox, oy, s = 300.0, 330.0, 3.0  # 1 m = 3 pt
    o.rect(ox, oy, 180 * s, 90 * s, 1.2, dash=(8, 3))
    o.rect(ox + 20 * s, oy + 50 * s, 36 * s, 18 * s, 0.8, fill=(0.85, 0.85, 0.85))
    o.ctext(ox + 38 * s, oy + 57 * s, "Корпус 1", 8, key="k1")
    o.rect(ox + 100 * s, oy + 30 * s, 48 * s, 24 * s, 0.8, fill=(0.85, 0.85, 0.85))
    o.ctext(ox + 124 * s, oy + 40 * s, "Корпус 2", 8, key="k2")
    o.line(ox - 40, oy - 20, ox + 180 * s + 40, oy - 20, 3.0, GREY)
    o.text(ox, oy - 36, "Проектируемый проезд (вымышленный)", 8, key="road")
    o.north_arrow(ox + 180 * s + 60, oy + 80 * s)
    return o


SPEC_ORDER = ("general", "plan1", "plan2", "roof", "section", "facade", "spec", "detail")
BUILDERS = {"general": None, "plan1": sheet_plan1, "plan2": sheet_plan2, "roof": sheet_roof,
            "section": sheet_section, "facade": sheet_facade, "spec": sheet_spec, "detail": sheet_detail}


def _sheet(o: Ops, key: str, number: int, title: str, v: Variant, size=A3L, sheet_id: str = "") -> scene.Sheet:
    stamp_ops, box = scene.frame_and_stamp(
        size, designation=v.designation, title=title, stage=v.stage, sheet_no=str(number),
        revision_label=v.rev.get(key, "Изм.0"), date=v.date.get(key, v.date.get("*", "")),
        organisation=ORGANISATION, font=font())
    return scene.Sheet(sheet_id=sheet_id or key, title=title, sheet_no=str(number), size=size,
                       ops=list(o.ops) + stamp_ops, stamp_bbox=box)


def series_document(v: Variant) -> tuple[bytes, list[str]]:
    keys = [k for k in SPEC_ORDER if k != "detail" or v.detail_sheet]
    titles = [SHEET_TITLES[k] for k in keys]
    sheets = []
    for n, k in enumerate(keys, 1):
        o = sheet_general(v, titles) if k == "general" else BUILDERS[k](v)
        sheets.append(_sheet(o, k, n, SHEET_TITLES[k], v))
    return _pdf(sheets, v, "series"), keys


def _pdf(sheets: list[scene.Sheet], v: Variant, seed: str) -> bytes:
    rev = max((s.ops[-1] for s in sheets), key=lambda _: 0)  # noqa: F841 (keeps the call shape simple)
    meta = scene.DocumentMeta(
        title=f"{v.designation}. Архитектурные решения. Стадия {v.stage} (синтетический документ)",
        subject=f"{building.OBJECT_NAME}. {building.DISCLAIMER}",
        doc_id_seed=f"synthetic-prod-2026-11-09/ar/{seed}/{v.designation}/{v.stage}",
        creation_date="D:20261102000000Z")
    return scene.build_document(sheets, meta, font()).data


# ----------------------------------------------------------------------------------------- versions

def versions() -> list[tuple[str, Variant]]:
    d1, d2, d3, d4 = "10.08.2026", "07.09.2026", "05.10.2026", "02.11.2026"
    v1 = Variant(spec=BASE_SPEC, rev={}, date={"*": d1})
    v2 = dataclasses.replace(v1, partition_104=29.4, door_102=True, parapet="+7,500", spec=_spec_v2(),
                             rev={"plan1": "Изм.1", "section": "Изм.1", "spec": "Изм.1", "facade": "Изм.1"},
                             date={"*": d1, "plan1": d2, "section": d2, "spec": d2, "facade": d2})
    v3 = dataclasses.replace(v2, room_209="Переговорная", fire_doors=True, canopy=True, detail_sheet=True,
                             rev={**v2.rev, "plan2": "Изм.2", "facade": "Изм.2", "detail": "Изм.2", "general": "Изм.2"},
                             date={**v2.date, "plan2": d3, "facade": d3, "detail": d3, "general": d3})
    v4 = dataclasses.replace(v3, pump_room="Насосная станция", drains=6, permit=True, spec=_spec_v4(),
                             rev={**v3.rev, "general": "Изм.3", "roof": "Изм.3", "spec": "Изм.3"},
                             date={**v3.date, "general": d4, "roof": d4, "spec": d4})
    return [("v1", v1), ("v2", v2), ("v3", v3), ("v4", v4)]


VERSION_CHANGES = {
    "v1->v2": {
        "label": "Изм.0 → Изм.1",
        "changed_sheets": {
            "2 План. Корпус 1. Этаж 1": ["перегородка 104/105 перенесена с 30,0 на 29,4 м (геометрия)",
                                         "площади 104: 45,0 → 40,5 м², 105: 45,0 → 49,5 м² (текст, экспликация)",
                                         "добавлена дверь из вестибюля 103 в гардероб 102 (графика)"],
            "5 Разрез 1-1": ["отметка верха парапета +7,200 → +7,500 (текст и геометрия)"],
            "6 Фасад 1-7": ["отметка парапета +7,200 → +7,500, фасад выше на 0,3 м"],
            "7 Спецификация": ["ДВ-1: этаж 1 10 → 11, всего 18 → 19"],
        },
        "unchanged_sheets": ["1", "3", "4"],
        "stamps": "листы 2, 5, 6, 7 — Изм.1, 07.09.2026",
    },
    "v2->v3": {
        "label": "Изм.1 → Изм.2",
        "changed_sheets": {
            "1 Общие данные": ["в ведомость листов добавлен лист 8"],
            "3 План. Корпус 1. Этаж 2": ["209 «Комната отдыха» → «Переговорная» (текст)",
                                         "двери лестничных клеток показаны красным — противопожарные (цвет), добавлено примечание"],
            "6 Фасад 1-7": ["добавлен козырёк над входом (графика + подпись)", "контур фасада толще (0,8 → 1,6)"],
        },
        "added_sheets": ["8 Узел 1. Корпус 1. Кровля"],
        "unchanged_sheets": ["2", "4", "5", "7"],
        "stamps": "листы 1, 3, 6, 8 — Изм.2, 05.10.2026",
    },
    "v3->v4": {
        "label": "Изм.2 → Изм.3",
        "changed_sheets": {
            "1 Общие данные": ["добавлена таблица «Разрешение на внесение изменений № 3»"],
            "2 План. Корпус 1. Этаж 1": ["113 «Насосная» → «Насосная станция» — НЕ объявлено, штамп не поднят (Изм.1)"],
            "4 План. Корпус 1. Кровля": ["водосточных воронок 4 → 6 (ВР-5, ВР-6), примечание 2 изменено"],
            "7 Спецификация": ["добавлена позиция ДП-2", "удалена позиция ДВ-3", "ОК-1: 24 → 22"],
        },
        "unchanged_sheets": ["3", "5", "6", "8"],
        "permit": {"declared_and_found": ["лист 4: воронки 4 → 6"],
                   "declared_not_found": ["лист 7: количество ОК-2 (ОК-2 не изменён)"],
                   "found_not_declared": ["лист 2: 113 «Насосная» → «Насосная станция»"]},
        "stamps": "листы 1, 4, 7 — Изм.3, 02.11.2026; лист 2 остался Изм.1",
    },
}


# ------------------------------------------------------------------------------------------- stages

def stage_documents() -> dict[str, bytes]:
    """П «СИНТ-02-АР» (8 sheets) and the Р assembly «СИНТ-02-АР.1» (= series V4) + «СИНТ-02-АР.2» (Корпус 2)."""
    p = Variant(designation="СИНТ-02-АР", stage="П", p_stage=True, spec=BASE_SPEC, date={"*": "20.05.2026"})
    p_titles = [SHEET_TITLES[k] for k in ("general", "plan1", "plan2", "roof", "section", "facade")] + [
        "План. Корпус 2. Этаж 1", "Ситуационная схема"]
    p_sheets = []
    for n, k in enumerate(("general", "plan1", "plan2", "roof", "section", "facade"), 1):
        o = sheet_general(p, p_titles) if k == "general" else BUILDERS[k](p)
        p_sheets.append(_sheet(o, k, n, SHEET_TITLES[k], p, sheet_id=f"P{n}"))
    p_sheets.append(_sheet(k2_plan("П"), "k2", 7, "План. Корпус 2. Этаж 1", p, sheet_id="P7"))
    p_sheets.append(_sheet(situational(), "sit", 8, "Ситуационная схема", p, sheet_id="P8"))
    old = _pdf(p_sheets, p, "stage")
    v4 = versions()[-1][1]
    r1, _ = series_document(v4)
    r2v = Variant(designation="СИНТ-02-АР.2", stage="Р", date={"*": "02.11.2026"})
    r2 = _pdf([_sheet(k2_plan("Р"), "k2", 1, "План. Корпус 2. Этаж 1", r2v, sheet_id="R2-1")], r2v, "stage")
    return {"П/СИНТ-02-АР.pdf": old, "Р/СИНТ-02-АР.1.pdf": r1, "Р/СИНТ-02-АР.2.pdf": r2}


STAGE_CHANGES = {
    "links": [
        ["П1 Общие данные. Корпус 1", "АР.1 лист 1", "ТЭП (П) заменены разрешением на изменения (Р); ведомость листов другая"],
        ["П2 План. Корпус 1. Этаж 1", "АР.1 лист 2", "104/105: 45,0/45,0 → 40,5/49,5 м²; дверь в 102; 113 «Насосная станция»; примечание добавлено"],
        ["П3 План. Корпус 1. Этаж 2", "АР.1 лист 3", "209 «Переговорная»; противопожарные двери; примечание добавлено"],
        ["П4 План. Корпус 1. Кровля", "АР.1 лист 4", "воронок 4 → 6"],
        ["П5 Разрез 1-1. Корпус 1", "АР.1 лист 5", "парапет +7,200 → +7,500"],
        ["П6 Фасад 1-7. Корпус 1", "АР.1 лист 6", "козырёк над входом; парапет +7,500"],
        ["П7 План. Корпус 2. Этаж 1", "АР.2 лист 1", "перегородка по оси 8, добавлено помещение 302; площадь 301: 1 152,0 → 1 008,0 м²"],
    ],
    "only_old": ["П8 Ситуационная схема"],
    "only_new": ["АР.1 лист 7 Спецификация", "АР.1 лист 8 Узел 1"],
}


def _zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            info = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= 0x800
            z.writestr(info, data)
    return buf.getvalue()


def _check_pdf(name: str, data: bytes) -> int:
    doc = pdfium.PdfDocument(data)
    for i in range(len(doc)):
        if not doc[i].get_textpage().get_text_range().strip():
            raise RuntimeError(f"{name}: page {i + 1} has no text layer")
    return len(doc)


def write(out: Path, previews: bool = True) -> dict:
    base = out / "ar_family"
    (base / "versions").mkdir(parents=True, exist_ok=True)
    (base / "stages").mkdir(parents=True, exist_ok=True)
    manifest: dict = {"versions": [], "stages": []}
    members = {}
    for label, v in versions():
        data, keys = series_document(v)
        pages = _check_pdf(label, data)
        name = f"СИНТ-02-АР.1_{label}_{max(v.rev.values(), default='Изм.0', key=lambda r: int(r[4:]))}.pdf"
        name = name.replace("Изм.", "Изм")
        (base / "versions" / name).write_bytes(data)
        members[f"СИНТ-02-АР.1/{name}"] = data
        manifest["versions"].append({"file": f"ar_family/versions/{name}", "pages": pages, "sheets": keys,
                                     "sha256": hashlib.sha256(data).hexdigest()})
        if previews:
            _previews(data, out / "previews" / f"ar_versions_{label}")
    vzip = _zip(members)
    (base / "AR-versions-v1-v4.zip").write_bytes(vzip)
    manifest["versions_zip"] = {"file": "ar_family/AR-versions-v1-v4.zip", "sha256": hashlib.sha256(vzip).hexdigest()}
    stages = stage_documents()
    for name, data in stages.items():
        pages = _check_pdf(name, data)
        target = base / "stages" / name.replace("/", "_")
        target.write_bytes(data)
        manifest["stages"].append({"member": name, "file": f"ar_family/stages/{target.name}", "pages": pages,
                                   "sha256": hashlib.sha256(data).hexdigest()})
        if previews and name.startswith("П"):
            _previews(data, out / "previews" / "ar_stage_P")
        if previews and name.endswith("АР.2.pdf"):
            _previews(data, out / "previews" / "ar_stage_R2")
    old_zip = _zip({k: v for k, v in stages.items() if k.startswith("П/")})
    new_zip = _zip({k: v for k, v in stages.items() if k.startswith("Р/")})
    (base / "AR-stage-P.zip").write_bytes(old_zip)
    (base / "AR-stage-R.zip").write_bytes(new_zip)
    key = {"schema": "synthetic-prod-ar-family-key/1", "versions": VERSION_CHANGES, "stages": STAGE_CHANGES,
           "disclaimer": building.DISCLAIMER}
    (base / "ar_family_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n")
    print(f"ar_family: 4 versions ({', '.join(str(v['pages']) for v in manifest['versions'])} pages), "
          f"stage П {manifest['stages'][0]['pages']} pages, Р {manifest['stages'][1]['pages']}+{manifest['stages'][2]['pages']}")
    return manifest


def _previews(data: bytes, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(data)
    for i in range(len(doc)):
        doc[i].render(scale=60 / 72).to_pil().save(out_dir / f"page_{i + 1:02d}.png")
