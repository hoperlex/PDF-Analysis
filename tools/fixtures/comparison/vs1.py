"""VS-1: five versions of one drawing set, and the answer key that states what changed.

The set is the electrical part (ЭМ) of an invented building, designation `СИНТ-01-ЭМ`. Seven
sheets exist over its life; every version is one PDF whose sheets carry a 185 x 55 mm title
block with the designation, the sheet's own revision «Изм.N» and a date. As in real sets a
sheet keeps the revision of its last change, so an untouched sheet keeps an old «Изм.» and the
version label (the highest «Изм.» in it) is a fact the profile reader has to derive.

    V1  Изм.0  15.01.2026   6 sheets   the base
    V2  Изм.1  12.02.2026   6 sheets   a label moved, a number in a table cell changed, a stamp-only
                                       revision, a PDF annotation added
    V3  Изм.2  10.03.2026   6 sheets   a sheet added (specification) and one removed (earthing), a
                                       line added, a colour changed, a line weight changed
    V4  Изм.3  07.04.2026   6 sheets   a change-permit table with three declared changes, one change
                                       nobody declared, one sheet replaced by a scan
    V5  Изм.4  05.05.2026   8 sheets   the A1 plan split in two, a duplicated sheet, specification
                                       positions added / removed / changed, one sheet byte-identical

How the answer key is made. Each sheet is a list of operations with authored ids
(`scene.py`); two versions of a sheet are compared by id (`scene.diff_sheets`), and the key's
change lists are that difference. What is *authored*, per transition and per sheet, is the
expected status. `build()` refuses to return when the authored status contradicts the computed
difference (for example `same` on a sheet whose operations differ), so the two cannot drift.
The key is written by this module and re-read from the PDF bytes by independent readers in
`tests/contract/fixtures_comparison`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from ar_corpus import pdfwrite

from . import scene
from .scene import (
    A1, A2, A3, A4, Annotation, Circle, Hatch, Line, Rect, Sheet, Text, bbox, diff_sheets,
    frame_and_stamp, landscape,
)

SCHEMA = "cmp-vs1-answer-key/1"
DESIGNATION = "СИНТ-01-ЭМ"
STAGE = "Р"
ORGANISATION = "СИНТЕТИКПРОЕКТ"
VERSIONS = ("V1", "V2", "V3", "V4", "V5")
REVISION_DATES = {0: "15.01.2026", 1: "12.02.2026", 2: "10.03.2026", 3: "07.04.2026", 4: "05.05.2026"}
LAYER_AXES = "Оси и размеры"

RED = (0.8, 0.0, 0.0)
BLUE = (0.0, 0.35, 0.8)
GREY = (0.85, 0.85, 0.85)

SHEETS: dict[str, dict[str, object]] = {
    "E01": {"no": "1", "title": "Общие данные", "size": A4},
    "E02": {"no": "2", "title": "План освещения. Корпус 1, этаж 1", "size": landscape(A3)},
    "E03": {"no": "3", "title": "Схема электрическая принципиальная ЩО-1", "size": landscape(A3)},
    "E04": {"no": "4", "title": "Схема электрическая вводного устройства ВРУ-1", "size": landscape(A3)},
    "E05": {"no": "5", "title": "План силовых сетей. Корпус 1, этаж 1", "size": landscape(A1)},
    "E06": {"no": "6", "title": "План заземления. Корпус 1", "size": landscape(A3)},
    "E07": {"no": "7", "title": "Спецификация оборудования, изделий и материалов", "size": A4},
}

#: The revision shown in each sheet's stamp, by version number. A sheet keeps the revision of
#: its last change, so most entries repeat.
STAMP_REVISION: dict[str, dict[int, int]] = {
    "E01": {1: 0, 2: 0, 3: 2, 4: 3, 5: 4},
    "E02": {1: 0, 2: 1, 3: 2, 4: 2, 5: 2},
    "E03": {1: 0, 2: 1, 3: 1, 4: 1, 5: 1},
    "E04": {1: 0, 2: 1, 3: 2, 4: 3, 5: 3},
    "E05": {1: 0, 2: 0, 3: 2, 4: 3, 5: 4},
    "E06": {1: 0, 2: 0},
    "E07": {3: 2, 4: 2, 5: 4},
}

#: Pages of each version in order: (sheet id, role). Roles: regular, duplicate, split1, split2.
ROSTER: dict[int, list[tuple[str, str]]] = {
    1: [(s, "regular") for s in ("E01", "E02", "E03", "E04", "E05", "E06")],
    2: [(s, "regular") for s in ("E01", "E02", "E03", "E04", "E05", "E06")],
    3: [(s, "regular") for s in ("E01", "E02", "E03", "E04", "E05", "E07")],
    4: [(s, "regular") for s in ("E01", "E02", "E03", "E04", "E05", "E07")],
    5: [("E01", "regular"), ("E02", "regular"), ("E03", "regular"), ("E04", "regular"),
        ("E05", "split1"), ("E05", "split2"), ("E07", "regular"), ("E03", "duplicate")],
}

#: Sheets drawn as a scan in a version (an image, no text layer).
SCANS = {("E04", 4), ("E04", 5)}

#: The split of the A1 plan: two A2 portrait parts, cut at the same x. The right part starts
#: 1 mm later, because two A2 widths (1190.55 pt) leave 2.84 pt of the A1 width (2383.94 pt) over.
SPLIT_LEFT = (0.0, 1190.55)
SPLIT_RIGHT = (1193.39, 2383.94)
SPLIT_TRANSLATION_RIGHT = -1193.39


def revision_label(number: int) -> str:
    return f"Изм.{number}"


def version_number(version: str) -> int:
    return int(version[1:])


# --------------------------------------------------------------------------------------
# Sheet content
# --------------------------------------------------------------------------------------


def _t(op_id: str, x: float, y: float, text: str, size: float = 10.0, **kw) -> Text:
    return Text(op_id, x=x, y=y, text=text, size=size, **kw)


def _grid(prefix: str, x_edges: list[float], y_edges: list[float], width: float = 0.6) -> list[Line]:
    out: list[Line] = []
    for index, y in enumerate(y_edges):
        out.append(Line(f"{prefix}.h{index}", x1=x_edges[0], y1=y, x2=x_edges[-1], y2=y, width=width))
    for index, x in enumerate(x_edges):
        out.append(Line(f"{prefix}.v{index}", x1=x, y1=y_edges[0], x2=x, y2=y_edges[-1], width=width))
    return out


def _listing(v: int) -> list[tuple[str, str, str]]:
    """The sheet list printed on the general data sheet: (key, number, title)."""
    out: list[tuple[str, str, str]] = []
    for sheet_id, role in ROSTER[v]:
        if role == "duplicate":
            continue
        if role == "split1":
            out.append(("E05.1", "5.1", f"{SHEETS['E05']['title']} (часть 1)"))
        elif role == "split2":
            out.append(("E05.2", "5.2", f"{SHEETS['E05']['title']} (часть 2)"))
        else:
            out.append((sheet_id, str(SHEETS[sheet_id]["no"]), str(SHEETS[sheet_id]["title"])))
    return out


PERMIT_TITLE = "Разрешение на внесение изменений"
PERMIT_HEADER = ("Изм.", "Лист", "Содержание изменения")
PERMIT_ROWS = (
    ("3", "5", "Дополнена трасса кабельного лотка"),
    ("3", "7", "Изменено сечение кабеля, поз. 4"),
    ("3", "4", "QF2 заменён: 100 А на 125 А"),
)


def _e01(v: int) -> list:
    ops: list = [_t("E01.title", 70, 790, "Общие данные", 14)]
    notes = (
        "Рабочая документация. Электроснабжение и электроосвещение корпуса 1.",
        "Напряжение сети 380/220 В, система заземления TN-S.",
        "Расчётная мощность Pр = 85,5 кВт, коэффициент мощности 0,92.",
        "Электромонтажные работы выполнять по действующим нормам.",
    )
    for index, note in enumerate(notes):
        ops.append(_t(f"E01.note.{index + 1}", 70, 760 - 15 * index, note, 10))
    ops.append(_t("E01.list.title", 70, 690, "Ведомость листов", 11))
    for index, (key, number, title) in enumerate(_listing(v)):
        ops.append(_t(f"E01.list.{key}", 70, 672 - 14 * index, f"{number}   {title}", 9))
    if v >= 4:
        ops.append(_t("E01.permit.title", 70, 540, PERMIT_TITLE, 11))
        x_edges = [70.0, 120.0, 170.0, 560.0]
        y_edges = [530.0, 512.0, 494.0, 476.0, 458.0]
        ops += _grid("E01.permit.grid", x_edges, y_edges)
        for column, head in enumerate(PERMIT_HEADER):
            ops.append(_t(f"E01.permit.h{column + 1}", x_edges[column] + 5, 518, head, 9))
        for row, values in enumerate(PERMIT_ROWS):
            for column, value in enumerate(values):
                ops.append(_t(f"E01.permit.r{row + 1}c{column + 1}", x_edges[column] + 5, 500 - 18 * row, value, 9))
    return ops


_LAMPS = [(190, 340), (350, 340), (190, 440), (350, 440), (190, 640), (350, 640),
          (500, 600), (640, 600), (500, 700), (640, 700), (800, 600), (940, 600)]


def _e02(v: int) -> list:
    ops: list = [
        Rect("E02.wall.outer", x=120, y=260, w=900, h=520, width=2.0),
        Line("E02.wall.p1", x1=420, y1=260, x2=420, y2=780, width=1.2),
        Line("E02.wall.p2", x1=720, y1=260, x2=720, y2=520, width=1.2),
        Line("E02.wall.p3", x1=420, y1=520, x2=1020, y2=520, width=1.2),
        Hatch("E02.hatch.elroom", x=730, y=270, w=280, h=140),
    ]
    for index, (x, name) in enumerate(((120, "1"), (420, "2"), (720, "3"), (1020, "4"))):
        ops.append(Line(f"E02.axis.v{name}", x1=x, y1=225, x2=x, y2=790, width=0.4,
                        dash=(8.0, 3.0, 2.0, 3.0), layer=LAYER_AXES))
        ops.append(_t(f"E02.axis.v{name}.mark", x - 3, 797, name, 10, layer=LAYER_AXES))
    for y, name in ((260, "А"), (520, "Б"), (780, "В")):
        ops.append(Line(f"E02.axis.h{name}", x1=88, y1=y, x2=1060, y2=y, width=0.4,
                        dash=(8.0, 3.0, 2.0, 3.0), layer=LAYER_AXES))
        ops.append(_t(f"E02.axis.h{name}.mark", 72, y - 3, name, 10, layer=LAYER_AXES))
    for index, (x, y) in enumerate(_LAMPS):
        ops.append(Circle(f"E02.lamp.{index + 1:02d}", cx=x, cy=y, r=9, width=1.0))
    for index, (x, y, text) in enumerate(((140, 745, "Помещение 1"), (440, 745, "Помещение 2"),
                                          (740, 745, "Помещение 3"), (740, 495, "Щитовая"))):
        ops.append(_t(f"E02.room.{index + 1}", x, y, text, 9))
    label = (740.0, 440.0) if v == 1 else (860.0, 470.0)
    ops.append(_t("E02.lbl.sho1", label[0], label[1], "ЩО-1", 11))
    ops.append(Circle("E02.legend.sym", cx=140, cy=232, r=6, width=1.0))
    ops.append(_t("E02.legend.txt", 156, 228, "светильник потолочный ЛПО 2×36", 8))
    ops.append(_t("E02.note.1", 140, 205, "Высота установки щита ЩО-1 — 1,5 м.", 8))
    ops.append(_t("E02.note.2", 140, 192, "Степень защиты светильников IP20.", 8))
    if v >= 3:
        ops.append(Line("E02.cable.new", x1=350, y1=440, x2=600, y2=440, width=0.8))
    return ops


_CABLES = {1: "ВВГнг 3×1,5", 2: "ВВГнг 3×2,5", 3: "ВВГнг 3×2,5", 4: "ВВГнг 3×1,5", 5: "ВВГнг 3×4", 6: "ВВГнг 3×1,5"}
_LOADS = {1: "1,2", 2: "2,4", 3: "3,0", 4: "1,8", 5: "4,5", 6: "0,8"}
_BREAKERS = {1: "16", 2: "25", 3: "32", 4: "16", 5: "40", 6: "10"}


def _e03(v: int) -> list:
    ops: list = [
        Line("E03.feed", x1=200, y1=720, x2=200, y2=640, width=1.0),
        Rect("E03.qf0.box", x=170, y=600, w=60, h=40, width=1.0),
        _t("E03.qf0.label", 176, 616, "QF0 80 А", 9),
        Line("E03.feed2", x1=200, y1=600, x2=200, y2=560, width=1.0),
        Line("E03.bus", x1=100, y1=560, x2=600, y2=560, width=2.0),
    ]
    for index in range(6):
        x = 130 + 80 * index
        ops.append(Line(f"E03.br.{index + 1}", x1=x + 15, y1=560, x2=x + 15, y2=500, width=0.8))
        ops.append(Rect(f"E03.qf{index + 1}.box", x=x, y=470, w=30, h=30, width=0.8))
        ops.append(_t(f"E03.qf{index + 1}.label", x + 2, 482, f"QF{index + 1}", 8))
        ops.append(_t(f"E03.grp.{index + 1}", x + 2, 452, f"Гр.{index + 1}", 8))
    x_edges = [70.0, 120.0, 210.0, 380.0, 480.0]
    y_edges = [440.0 - 18 * i for i in range(8)]
    ops += _grid("E03.table.grid", x_edges, y_edges)
    for column, head in enumerate(("№ гр.", "Нагрузка, кВт", "Кабель", "Автомат, А")):
        ops.append(_t(f"E03.table.h{column + 1}", x_edges[column] + 5, 426, head, 9))
    for row in range(1, 7):
        cable = _CABLES[row]
        if row == 2 and v >= 4:
            cable = "ВВГнг 3×4"
        load = _LOADS[row]
        if row == 3 and v >= 2:
            load = "3,6"
        values = (str(row), load, cable, _BREAKERS[row])
        for column, value in enumerate(values):
            ops.append(_t(f"E03.table.r{row}c{column + 1}", x_edges[column] + 5, 426 - 18 * row, value, 9))
    return ops


def _e04(v: int) -> list:
    ops: list = [
        Line("E04.feed", x1=400, y1=720, x2=400, y2=640, width=1.0),
        _t("E04.feed.label", 410, 700, "Ввод 1, ~380/220 В", 9),
        Line("E04.bus.l1", x1=100, y1=640, x2=700, y2=640, width=1.0),
        Line("E04.bus.l2", x1=100, y1=620, x2=700, y2=620, width=1.0),
        Line("E04.bus.l3", x1=100, y1=600, x2=700, y2=600, width=1.0),
        Line("E04.bus.pe", x1=100, y1=560, x2=700, y2=560, width=0.5 if v < 3 else 1.5),
    ]
    ratings = ("100 А", "100 А" if v < 4 else "125 А", "63 А", "40 А")
    targets = ("Щ-1", "ЩО-1", "Щ-3", "Резерв")
    for index in range(4):
        x = 130 + 150 * index
        ops.append(Line(f"E04.qf{index + 1}.in", x1=x + 35, y1=600, x2=x + 35, y2=530, width=0.8))
        ops.append(Rect(f"E04.qf{index + 1}.box", x=x, y=480, w=70, h=50, width=1.0))
        ops.append(_t(f"E04.qf{index + 1}.label", x + 4, 500, f"QF{index + 1} {ratings[index]}", 9))
        ops.append(Line(f"E04.qf{index + 1}.out", x1=x + 35, y1=480, x2=x + 35, y2=430, width=0.8))
        ops.append(_t(f"E04.qf{index + 1}.target", x + 4, 415, targets[index], 9))
    ops.append(_t("E04.note", 100, 360, "Все аппараты — на DIN-рейке, степень защиты щита IP31.", 8))
    return ops


_SPEC_ROWS: dict[str, tuple[str, str, str, str]] = {
    "1": ("СИНТ-ЩО.01", "Щит освещения ЩО-1", "1", "45,0"),
    "2": ("СИНТ-АВ.16", "Выключатель автоматический 16 А", "12", "0,15"),
    "3": ("СИНТ-АВ.63", "Выключатель автоматический 63 А", "2", "0,45"),
    "4": ("СИНТ-КБ.325", "Кабель ВВГнг 3×2,5, м", "320", "0,12"),
    "5": ("СИНТ-СВ.236", "Светильник ЛПО 2×36", "24", "3,2"),
    "6": ("СИНТ-ЗУ.01", "Заземлитель стальной", "4", "2,0"),
}


def spec_rows(v: int) -> dict[str, tuple[str, str, str, str]]:
    """The specification positions of version `v`: position -> (designation, name, qty, mass)."""
    rows = dict(_SPEC_ROWS)
    if v >= 5:
        rows["3"] = ("СИНТ-АВ.63", "Выключатель автоматический 63 А", "3", "0,45")
        del rows["6"]
        rows["7"] = ("СИНТ-СД.40", "Светильник светодиодный 40 Вт", "6", "1,4")
    return rows


SPEC_COLUMNS = ("Поз.", "Обозначение", "Наименование и тех. характеристика", "Кол.", "Масса ед., кг", "Прим.")
_SPEC_X = [56.7, 92.7, 222.7, 422.7, 458.7, 513.7, 581.1]


def _e07(v: int) -> list:
    ops: list = [_t("E07.title", 70, 795, "Спецификация оборудования, изделий и материалов", 12)]
    y_edges = [770.0, 744.0] + [744.0 - 22 * i for i in range(1, 8)]
    ops += _grid("E07.grid", _SPEC_X, y_edges)
    for column, head in enumerate(SPEC_COLUMNS):
        ops.append(_t(f"E07.hdr.{column + 1}", _SPEC_X[column] + 3, 753, head, 7))
    for position, (code, name, qty, mass) in spec_rows(v).items():
        base = 744.0 - 22 * int(position) + 7
        for column, value in enumerate((position, code, name, qty, mass)):
            ops.append(_t(f"E07.row{position}.{column + 1}", _SPEC_X[column] + 3, base, value, 8))
    ops.append(_t("E07.note", 70, 570, "Примечание: масса единицы указана справочно.", 8))
    return ops


def _e06(v: int) -> list:
    return [
        Rect("E06.outer", x=150, y=300, w=900, h=450, width=2.0),
        Rect("E06.loop", x=200, y=350, w=800, h=350, width=1.5, dash=(10.0, 4.0)),
        Line("E06.tap.1", x1=200, y1=525, x2=100, y2=525, width=1.5),
        Line("E06.tap.2", x1=1000, y1=525, x2=1100, y2=525, width=1.5),
        _t("E06.label.1", 220, 720, "Контур заземления — полоса 40×4, глубина 0,7 м", 10),
        _t("E06.label.2", 220, 330, "Сопротивление растеканию не более 4 Ом", 10),
        _t("E06.label.3", 90, 535, "К ВРУ-1", 9),
    ]


def _e05(v: int) -> list:
    """The A1 power plan: a left wing and a right wing, nothing across x = 1190..1194."""
    ops: list = []
    for side, x0 in (("L", 120.0), ("R", 1280.0)):
        width = 1000.0 if side == "L" else 1060.0
        ops.append(Rect(f"E05.{side}.wall", x=x0, y=300, w=width, h=1280, width=2.5))
        for index in range(6):
            y = 480 + 180 * index
            ops.append(Line(f"E05.{side}.part.{index + 1}", x1=x0, y1=y, x2=x0 + width, y2=y, width=1.2))
        for index, frac in enumerate((0.33, 0.66)):
            x = x0 + width * frac
            ops.append(Line(f"E05.{side}.pv.{index + 1}", x1=x, y1=300, x2=x, y2=1580, width=1.2))
        ops.append(Hatch(f"E05.{side}.hatch", x=x0 + 20, y=320, w=280, h=140))
        for k in range(1, 7):
            px, py = x0 + 60 + 150 * (k - 1), 520 + 180 * ((k - 1) % 3)
            ops.append(Rect(f"E05.{side}.panel.{k}", x=px, y=py, w=40, h=60, width=1.5, fill=GREY))
            ops.append(_t(f"E05.{side}.panel.{k}.lbl", px, py + 68, f"Щ-{k}", 12))
        for k in range(1, 9):
            mx, my = x0 + 80 + 110 * (k - 1), 1100 + 40 * (k % 3)
            ops.append(Circle(f"E05.{side}.motor.{k}", cx=mx, cy=my, r=14, width=1.2))
            ops.append(_t(f"E05.{side}.motor.{k}.lbl", mx - 5, my - 4, f"М{k}", 9))
        for k in range(1, 17):
            ax, ay = x0 + 100 + 55 * (k - 1), 580 + 180 * ((k - 1) % 3)
            bx, by = x0 + 80 + 110 * ((k - 1) % 8), 1100 + 40 * (((k - 1) % 8 + 1) % 3)
            ops.append(Line(f"E05.{side}.cable.{k}", x1=ax, y1=ay, x2=bx, y2=by - 14, width=0.7,
                            dash=(8.0, 4.0) if k % 4 == 0 else None))
        tray = RED if v < 3 else BLUE
        ops.append(Line(f"E05.{side}.tray.1", x1=x0 + 20, y1=1500, x2=x0 + width - 20, y2=1500, width=3.0, rgb=tray))
        ops.append(Line(f"E05.{side}.tray.2", x1=x0 + width - 20, y1=1500, x2=x0 + width - 20, y2=340,
                        width=3.0, rgb=tray))
        ops.append(Line(f"E05.{side}.tray.3", x1=x0 + width - 20, y1=340, x2=x0 + 320, y2=340, width=3.0, rgb=tray))
        for index, name in enumerate(("Цех 1", "Склад", "Бытовые помещения", "Насосная", "Венткамера", "Щитовая")):
            ops.append(_t(f"E05.{side}.room.{index + 1}", x0 + 20 + 330 * (index % 3),
                          1540 - 180 * (index // 3) - 60 * (index // 3), f"{name} ({side})", 12))
    if v >= 4:
        ops.append(Line("E05.L.tray.branch", x1=620, y1=1500, x2=620, y2=1040, width=3.0, rgb=BLUE))
    return ops


# --------------------------------------------------------------------------------------
# Sheets of a version
# --------------------------------------------------------------------------------------

_BODIES = {"E01": _e01, "E02": _e02, "E03": _e03, "E04": _e04, "E05": _e05, "E06": _e06, "E07": _e07}


def _stamped(
    font: pdfwrite.EmbeddedFont, size: tuple[float, float], body: list, *, sheet_id: str,
    title: str, sheet_no: str, revision: int, role: str = "regular", scan: bool = False,
) -> Sheet:
    stamp_ops, stamp_box = frame_and_stamp(
        size, designation=DESIGNATION, title=title, stage=STAGE, sheet_no=sheet_no,
        revision_label=revision_label(revision), date=REVISION_DATES[revision],
        organisation=ORGANISATION, font=font)
    return Sheet(sheet_id=sheet_id, title=title, sheet_no=sheet_no, size=size, ops=list(body) + stamp_ops,
                 scan=scan, revision=revision, stamp_bbox=tuple(round(v, 2) for v in stamp_box), role=role)


def _annotations(sheet_id: str, v: int) -> list[Annotation]:
    notes: list[Annotation] = []
    if sheet_id == "E05" and v >= 2:
        notes.append(Annotation("E05.note.1", "text", (600.0, 900.0, 624.0, 924.0),
                                "Проверить трассу лотка по оси Б", "Проверяющий", "D:20260212000000Z"))
    if sheet_id == "E07" and v >= 3:
        notes.append(Annotation("E07.sq.1", "square", (56.7, 656.0, 581.1, 678.0),
                                "Уточнить сечение", "Проверяющий", "D:20260310000000Z", (0.9, 0.1, 0.1)))
    return notes


def regular_sheet(font: pdfwrite.EmbeddedFont, sheet_id: str, v: int, role: str = "regular") -> Sheet:
    meta = SHEETS[sheet_id]
    sheet = _stamped(
        font, meta["size"], _BODIES[sheet_id](v), sheet_id=sheet_id, title=str(meta["title"]),
        sheet_no=str(meta["no"]), revision=STAMP_REVISION[sheet_id][v], role=role,
        scan=(sheet_id, v) in SCANS,
    )
    sheet.annotations = _annotations(sheet_id, v)
    return sheet


def _content_ops(sheet: Sheet) -> list:
    return [op for op in sheet.ops if op.zone == "content"]


@dataclass(frozen=True)
class SplitPart:
    sheet: Sheet
    region: tuple[float, float]
    translation: float


def split_sheets(font: pdfwrite.EmbeddedFont, v: int) -> list[SplitPart]:
    """The A1 plan of version `v` as two A2 portrait sheets, content only, translation only."""
    whole = regular_sheet(font, "E05", v - 1)
    parts: list[SplitPart] = []
    claimed: set[str] = set()
    for index, (region, shift) in enumerate(((SPLIT_LEFT, 0.0), (SPLIT_RIGHT, SPLIT_TRANSLATION_RIGHT)), start=1):
        body = []
        for op in _content_ops(whole):
            x0, _, x1, _ = bbox(op, font)
            if region[0] <= x0 and x1 <= region[1]:
                body.append(_translated(op, shift))
                claimed.add(op.id)
        title = f"{SHEETS['E05']['title']} (часть {index})"
        sheet = _stamped(font, A2, body, sheet_id="E05", title=title, sheet_no=f"5.{index}",
                         revision=STAMP_REVISION["E05"][v], role=f"split{index}")
        if index == 1:
            sheet.annotations = _annotations("E05", v)
        parts.append(SplitPart(sheet=sheet, region=region, translation=shift))
    unclaimed = {op.id for op in _content_ops(whole)} - claimed
    if unclaimed:
        raise ValueError(f"operations cross the split line: {sorted(unclaimed)}")
    return parts


def _translated(op, dx: float):
    if dx == 0.0:
        return op
    if isinstance(op, (Text, Rect, Hatch)):
        return replace(op, x=round(op.x + dx, 2))
    if isinstance(op, Line):
        return replace(op, x1=round(op.x1 + dx, 2), x2=round(op.x2 + dx, 2))
    if isinstance(op, Circle):
        return replace(op, cx=round(op.cx + dx, 2))
    raise TypeError(type(op).__name__)


def version_sheets(font: pdfwrite.EmbeddedFont, v: int) -> list[Sheet]:
    """The sheets of version `v` in page order."""
    out: list[Sheet] = []
    splits: list[SplitPart] | None = None
    for sheet_id, role in ROSTER[v]:
        if role in ("split1", "split2"):
            if splits is None:
                splits = split_sheets(font, v)
            out.append(splits[0 if role == "split1" else 1].sheet)
        else:
            out.append(regular_sheet(font, sheet_id, v, role))
    return out


# --------------------------------------------------------------------------------------
# The answer key
# --------------------------------------------------------------------------------------

STATUSES = ("same", "same_zones_changed", "different", "needs_review", "added", "removed")
CHANNELS = ("geometry", "color", "text", "text_coverage", "zones", "annotations", "warnings", "spec_positions")

#: Authored. Per transition and sheet id: the status a correct comparison reports. `build()`
#: checks each against the difference computed from the sheets' operations and refuses to
#: return when they disagree.
EXPECTED_STATUS: dict[tuple[str, str], dict[str, str]] = {
    ("V1", "V2"): {"E01": "same", "E02": "different", "E03": "different", "E04": "same_zones_changed",
                   "E05": "different", "E06": "same"},
    ("V2", "V3"): {"E01": "different", "E02": "different", "E03": "same", "E04": "different",
                   "E05": "different", "E06": "removed", "E07": "added"},
    ("V3", "V4"): {"E01": "different", "E02": "same", "E03": "different", "E04": "needs_review",
                   "E05": "different", "E07": "same"},
    ("V4", "V5"): {"E01": "different", "E02": "same", "E03": "needs_review", "E04": "same",
                   "E05": "needs_review", "E07": "different"},
}

#: Authored, per transition and sheet: what the generic derivation cannot know.
SPECIAL: dict[tuple[str, str, str], dict[str, object]] = {
    ("V3", "V4", "E04"): {
        "reasons": ["NO_TEXT_LAYER"],
        "required": ["text_coverage"],
        "unconstrained": ["geometry", "color", "text", "zones", "warnings"],
        "notes": (
            "Version 4 carries this sheet as a scan: one 1-bit image, no text layer. The sheet it "
            "replaces is vector with a text layer, so the text channel cannot be compared and "
            "text_coverage must say so. The drawn change (QF2 100 А -> 125 А, the stamp revision "
            "and date) exists only in the pixels and is listed under changes_in_pixels."
        ),
    },
    ("V4", "V5", "E03"): {
        "reasons": ["DUPLICATE_SHEET"],
        "required": ["warnings"],
        "unconstrained": [],
        "notes": (
            "Version 5 contains this sheet twice: page 3 and page 8 have identical content, "
            "identical stamps and the same sheet number. Neither differs from the version-4 sheet."
        ),
    },
    ("V4", "V5", "E05"): {
        "reasons": ["SPLIT_SHEET"],
        "required": [],
        "unconstrained": list(CHANNELS),
        "notes": (
            "The A1 plan of version 4 is two A2 portrait sheets in version 5, cut at x = 1190.55 / "
            "1193.39 pt of the A1 sheet and translated, never scaled. The content of each part is the "
            "content of its region of the old sheet; only the title block and the frame differ. "
            "A comparison that registers each part against its region must find no content "
            "difference (parts[].content_changes_in_region is empty)."
        ),
    },
}

#: The four reconciliation classes of the change permit, authored as the expected outcome.
EXPECTED_PERMIT = {
    "declared_and_found": ["E05"],
    "declared_not_found": ["E07"],
    "declared_unverifiable_scan": ["E04"],
    "found_not_declared": ["E03"],
}


class BuildError(RuntimeError):
    """The authored expectation contradicts the sheets it describes."""


@dataclass(frozen=True)
class VersionBuild:
    name: str
    number: int
    sheets: list[Sheet]
    built: scene.BuiltDocument
    filename: str


def _round(values) -> list[float]:
    return [round(float(v), 2) for v in values]


def _stamp_fields(sheet: Sheet) -> dict[str, str]:
    index = sheet.by_id()
    out: dict[str, str] = {}
    for name in ("designation", "title", "stage", "sheet_no", "revision", "date", "org"):
        op = index[f"stamp.{name}"]
        out["organisation" if name == "org" else name] = op.text  # type: ignore[attr-defined]
    return out


def _annotation_fact(note: Annotation) -> dict[str, object]:
    return {"id": note.id, "kind": note.kind, "contents": note.contents, "author": note.author,
            "rect": _round(note.rect)}


def _page_fact(sheet: Sheet, page: int, built: scene.BuiltPage) -> dict[str, object]:
    return {
        "page": page,
        "sheet_id": sheet.sheet_id,
        "role": sheet.role,
        "sheet_no": sheet.sheet_no,
        "title": sheet.title,
        "format": scene.format_name(sheet.width, sheet.height),
        "width_pt": round(sheet.width, 2),
        "height_pt": round(sheet.height, 2),
        "text_layer": not sheet.scan,
        "scan": sheet.scan,
        "stamp": _stamp_fields(sheet),
        "stamp_bbox": _round(sheet.stamp_bbox),
        "annotations": [_annotation_fact(n) for n in sheet.annotations],
        "content_sha256": hashlib.sha256(built.content).hexdigest(),
        "image_sha256": hashlib.sha256(built.image_bytes).hexdigest() if built.image_bytes else None,
    }


def _annotation_delta(a: Sheet | None, b: Sheet | None) -> dict[str, list[dict[str, object]]]:
    old = {n.id: n for n in (a.annotations if a else [])}
    new = {n.id: n for n in (b.annotations if b else [])}
    return {
        "added": [_annotation_fact(new[i]) for i in sorted(set(new) - set(old))],
        "removed": [_annotation_fact(old[i]) for i in sorted(set(old) - set(new))],
        "changed": [_annotation_fact(new[i]) for i in sorted(set(old) & set(new)) if old[i] != new[i]],
    }


def spec_delta(before: dict | None, after: dict | None) -> dict[str, object]:
    """Specification positions that were added, removed or changed. Each side is position -> row."""
    before, after = before or {}, after or {}
    names = ("designation", "name", "quantity", "mass")
    changed: list[dict[str, str]] = []
    for position in sorted(set(before) & set(after), key=int):
        for index, field_name in enumerate(names):
            if before[position][index] != after[position][index]:
                changed.append({"position": position, "field": field_name,
                                "before": before[position][index], "after": after[position][index]})
    return {
        "added": [_spec_row(p, after[p]) for p in sorted(set(after) - set(before), key=int)],
        "removed": [_spec_row(p, before[p]) for p in sorted(set(before) - set(after), key=int)],
        "changed": changed,
    }


def _spec_row(position: str, row: tuple[str, str, str, str]) -> dict[str, str]:
    return {"position": position, "designation": row[0], "name": row[1], "quantity": row[2], "mass": row[3]}


def _spec_table(v: int) -> list[dict[str, str]]:
    return [_spec_row(p, r) for p, r in sorted(spec_rows(v).items(), key=lambda item: int(item[0]))]


def derive_channels(
    changes: list[dict[str, object]], annotations: dict[str, list], spec_changed: bool,
    special: dict[str, object] | None,
) -> tuple[list[str], list[str]]:
    """(channels that must report a difference, channels that must report none).

    Channels in neither list are unconstrained: a correct engine may or may not report them
    (for instance `geometry` for a changed number, because the glyph pixels differ).
    """
    content = [c for c in changes if c["zone"] != "stamp"]
    kinds = {str(c["kind"]) for c in content}
    stamp = any(c["zone"] == "stamp" for c in changes)
    text_kinds = {k for k in kinds if k.startswith("text_")}
    graphic_kinds = {k for k in kinds if k.startswith("graphic_")}
    style = bool(graphic_kinds & {"graphic_color", "graphic_width", "graphic_dash"})
    shape = bool(graphic_kinds & {"graphic_added", "graphic_removed", "graphic_moved"})
    annot = any(annotations[k] for k in ("added", "removed", "changed"))

    required: set[str] = set()
    forbidden: set[str] = set()
    if stamp:
        required.add("zones")
    else:
        forbidden.add("zones")
    if text_kinds:
        required.add("text")
    else:
        forbidden.add("text")
    if style:
        required.add("color")
    elif not shape:
        forbidden.add("color")
    if shape:
        required.add("geometry")
    elif not graphic_kinds and not text_kinds:
        forbidden.add("geometry")
    elif graphic_kinds and not shape and not text_kinds:
        forbidden.add("geometry")  # a style-only change moves no coordinate
    if annot:
        required.add("annotations")
    else:
        forbidden.add("annotations")
    if spec_changed:
        required.add("spec_positions")
    else:
        forbidden.add("spec_positions")
    forbidden |= {"text_coverage", "warnings"}
    if special:
        required |= set(special.get("required", []))  # type: ignore[arg-type]
        forbidden -= set(special.get("required", []))  # type: ignore[arg-type]
        forbidden -= set(special.get("unconstrained", []))  # type: ignore[arg-type]
        required -= set(special.get("unconstrained", []))  # type: ignore[arg-type]
    return [c for c in CHANNELS if c in required], [c for c in CHANNELS if c in forbidden]


def _check_status(status: str, changes: list, annotations: dict, label: str) -> None:
    content = [c for c in changes if c["zone"] != "stamp"]
    stamp = [c for c in changes if c["zone"] == "stamp"]
    annot = any(annotations[k] for k in ("added", "removed", "changed"))
    if status == "same" and (changes or annot):
        raise BuildError(f"{label}: authored `same`, but the sheets differ: {changes[:2]} {annotations}")
    if status == "same_zones_changed" and (content or annot or not stamp):
        raise BuildError(f"{label}: authored `same_zones_changed`, computed content={content[:2]} stamp={len(stamp)}")
    if status == "different" and not (content or annot):
        raise BuildError(f"{label}: authored `different`, but only the stamp or nothing differs")


def _pairs(transition: tuple[str, str], builds: dict[str, VersionBuild], font) -> list[dict[str, object]]:
    a, b = builds[transition[0]], builds[transition[1]]
    index_a = {(s.sheet_id, s.role): (i + 1, s) for i, s in enumerate(a.sheets)}
    index_b = {(s.sheet_id, s.role): (i + 1, s) for i, s in enumerate(b.sheets)}
    expected = EXPECTED_STATUS[transition]
    entries: list[dict[str, object]] = []
    for sheet_id in expected:
        status = expected[sheet_id]
        special = SPECIAL.get((transition[0], transition[1], sheet_id))
        label = f"{transition[0]}->{transition[1]} {sheet_id}"
        meta = SHEETS[sheet_id]
        entry: dict[str, object] = {
            "sheet_id": sheet_id, "sheet_no": meta["no"], "title": meta["title"],
            "expected_status": status,
        }
        page_a = index_a.get((sheet_id, "regular"))
        page_b = index_b.get((sheet_id, "regular"))
        if status == "removed":
            assert page_a is not None and page_b is None, label
            entry.update({"relation": "removed", "from_page": page_a[0], "to_page": None,
                          "reasons": [], "channels_with_differences": [], "channels_without_differences": [],
                          "difference_kinds": ["sheet_removed"],
                          "notes": "The sheet is not in the next version and is not split or renamed."})
            entries.append(entry)
            continue
        if status == "added":
            assert page_a is None and page_b is not None, label
            sheet_b = page_b[1]
            entry.update({"relation": "added", "from_page": None, "to_page": page_b[0],
                          "reasons": [], "channels_with_differences": [], "channels_without_differences": [],
                          "difference_kinds": ["sheet_added"],
                          "annotations_on_page": [_annotation_fact(n) for n in sheet_b.annotations],
                          "notes": "The sheet is new in this version."})
            if sheet_id == "E07":
                entry["spec_positions_on_page"] = _spec_table(b.number)
            entries.append(entry)
            continue

        assert page_a is not None, label
        sheet_a = page_a[1]
        if special and "SPLIT_SHEET" in special["reasons"]:  # type: ignore[operator]
            entries.append(_split_entry(entry, transition, a, b, sheet_a, page_a[0], special, font, label))
            continue
        sheet_b = page_b[1] if page_b else None
        assert sheet_b is not None, label
        changes = diff_sheets(sheet_a, sheet_b, font)
        notes_delta = _annotation_delta(sheet_a, sheet_b)
        spec = None
        if sheet_id == "E07":
            spec = spec_delta(spec_rows(a.number), spec_rows(b.number))
        spec_changed = bool(spec and (spec["added"] or spec["removed"] or spec["changed"]))
        _check_status(status, changes, notes_delta, label)

        scan_pair = bool(special and "NO_TEXT_LAYER" in special["reasons"])  # type: ignore[operator]
        required, forbidden = derive_channels(changes, notes_delta, spec_changed, special)
        text_changes = [] if scan_pair else [c for c in changes if str(c["kind"]).startswith("text_")]
        graphic_changes = [] if scan_pair else [c for c in changes if str(c["kind"]).startswith("graphic_")]
        kinds = sorted({str(c["kind"]) for c in changes if c["zone"] != "stamp"})
        if any(c["zone"] == "stamp" for c in changes):
            kinds.append("stamp_changed")
        if any(notes_delta[k] for k in notes_delta):
            kinds.append("annotation_changed")
        if spec_changed:
            kinds.append("spec_positions_changed")
        built_a, built_b = a.built.pages[page_a[0] - 1], b.built.pages[page_b[0] - 1]
        identical = (built_a.content == built_b.content and built_a.media_box == built_b.media_box
                     and built_a.image_bytes == built_b.image_bytes and not any(notes_delta[k] for k in notes_delta))
        entry.update({
            "relation": "duplicate" if special and "DUPLICATE_SHEET" in special["reasons"] else "one_to_one",  # type: ignore[operator]
            "from_page": page_a[0],
            "to_page": page_b[0],
            "reasons": list(special["reasons"]) if special else [],  # type: ignore[arg-type]
            "channels_with_differences": required,
            "channels_without_differences": forbidden,
            "difference_kinds": kinds,
            "text_changes": text_changes,
            "graphic_changes": graphic_changes,
            "annotation_changes": notes_delta,
            "byte_identical_page": identical,
        })
        if scan_pair:
            entry["changes_in_pixels"] = changes
        if special and "DUPLICATE_SHEET" in special["reasons"]:  # type: ignore[operator]
            dup = index_b[(sheet_id, "duplicate")]
            entry["to_pages"] = [page_b[0], dup[0]]
            entry["duplicate_pages_identical"] = (
                b.built.pages[dup[0] - 1].content == b.built.pages[page_b[0] - 1].content)
            if not entry["duplicate_pages_identical"]:
                raise BuildError(f"{label}: the duplicate page differs from the original")
        if spec is not None:
            entry["spec_positions"] = {
                "table_layout": "ГОСТ 21.110: позиция, обозначение, наименование, кол., масса ед., примечание",
                "columns": list(SPEC_COLUMNS),
                "table_bbox": [_SPEC_X[0], 590.0, _SPEC_X[-1], 770.0],
                "positions_before": _spec_table(a.number), "positions_after": _spec_table(b.number),
                **spec,
            }
        if special:
            entry["notes"] = special["notes"]
        entries.append(entry)
    return entries


def _split_entry(entry, transition, a, b, sheet_a, page_a, special, font, label) -> dict[str, object]:
    parts = []
    for part_index, role in ((1, "split1"), (2, "split2")):
        number = [i for i, s in enumerate(b.sheets) if s.sheet_id == "E05" and s.role == role][0] + 1
        part_sheet = b.sheets[number - 1]
        split = split_sheets(font, b.number)[part_index - 1]
        # The part's content, moved back into the old sheet's coordinates, against the old
        # sheet's content that lies in the region: nothing may differ.
        whole_ops = [op for op in _content_ops(sheet_a)
                     if split.region[0] <= bbox(op, font)[0] and bbox(op, font)[2] <= split.region[1]]
        back = [_translated(op, -split.translation) for op in _content_ops(part_sheet)]
        content_diff = diff_sheets(Sheet("E05", "", "", sheet_a.size, whole_ops),
                                   Sheet("E05", "", "", sheet_a.size, back), font)
        if content_diff:
            raise BuildError(f"{label}: split part {part_index} differs from its region: {content_diff[:2]}")
        stamp_diff = diff_sheets(
            Sheet("E05", "", "", sheet_a.size, [op for op in sheet_a.ops if op.zone == "stamp"]),
            Sheet("E05", "", "", sheet_a.size, [op for op in part_sheet.ops if op.zone == "stamp"]), font)
        parts.append({
            "to_page": number,
            "sheet_no": part_sheet.sheet_no,
            "format": scene.format_name(part_sheet.width, part_sheet.height),
            "region_in_old_sheet_x": _round(split.region),
            "translation_x": round(split.translation, 2),
            "scale": 1.0,
            "content_changes_in_region": content_diff,
            "operations_in_region": len(whole_ops),
            "stamp_changes": [c for c in stamp_diff if c["kind"] == "text_changed"],
            "annotations": [_annotation_fact(n) for n in part_sheet.annotations],
        })
    covered = sum(p["operations_in_region"] for p in parts)  # type: ignore[misc]
    if covered != len(_content_ops(sheet_a)):
        raise BuildError(f"{label}: the parts cover {covered} of {len(_content_ops(sheet_a))} operations")
    entry.update({
        "relation": "split",
        "from_page": page_a,
        "to_pages": [p["to_page"] for p in parts],
        "reasons": list(special["reasons"]),
        "channels_with_differences": [],
        "channels_without_differences": [],
        "difference_kinds": ["split"],
        "parts": parts,
        "parts_cover_whole_old_sheet": True,
        "notes": special["notes"],
    })
    return entry


def _permit(entries: list[dict[str, object]]) -> dict[str, object]:
    """Reconcile the permit table of version 4 with what the sheets show."""
    by_no = {str(SHEETS[s]["no"]): s for s in SHEETS}
    status = {str(e["sheet_id"]): e for e in entries}
    declared = []
    classes: dict[str, list[str]] = {k: [] for k in EXPECTED_PERMIT}
    declared_ids: set[str] = set()
    for number, (change_no, sheet_no, text) in enumerate(PERMIT_ROWS, start=1):
        sheet_id = by_no[sheet_no]
        declared_ids.add(sheet_id)
        found = status[sheet_id]
        content = [c for c in found.get("text_changes", []) + found.get("graphic_changes", [])  # type: ignore[operator]
                   if c["zone"] != "stamp"]
        if "NO_TEXT_LAYER" in found["reasons"]:  # type: ignore[operator]
            klass = "declared_unverifiable_scan"
        elif content:
            klass = "declared_and_found"
        else:
            klass = "declared_not_found"
        classes[klass].append(sheet_id)
        declared.append({
            "entry": number, "change_no": change_no, "sheet_no": sheet_no, "sheet_id": sheet_id,
            "text": text, "reconciliation": klass,
            "evidence_ids": [str(c["id"]) for c in content],
        })
    for sheet_id, found in status.items():
        content = [c for c in found.get("text_changes", []) + found.get("graphic_changes", [])  # type: ignore[operator]
                   if c["zone"] != "stamp"]
        if content and sheet_id not in declared_ids and sheet_id != "E01":
            classes["found_not_declared"].append(sheet_id)
    if classes != EXPECTED_PERMIT:
        raise BuildError(f"permit reconciliation {classes} differs from the authored {EXPECTED_PERMIT}")
    return {
        "carrier_sheet": "E01",
        "table_title": PERMIT_TITLE,
        "columns": list(PERMIT_HEADER),
        "table_bbox": [70.0, 458.0, 560.0, 530.0],
        "declared": declared,
        "classes": classes,
        "found_not_declared": [
            {"sheet_id": s,
             "text_change_ids": [str(c["id"]) for c in status[s]["text_changes"] if c["zone"] != "stamp"]}  # type: ignore[index]
            for s in classes["found_not_declared"]
        ],
        "notes": (
            "Entry 1 is declared and found (a tray branch line appears on sheet 5). Entry 2 is declared "
            "and not found (sheet 7 is unchanged in version 4). Entry 3 is declared on a sheet that is a "
            "scan in version 4, so it can be neither confirmed nor refuted from text. A cable in the "
            "table of sheet 3 changed and no entry mentions it, and its stamp revision was not raised."
        ),
    }


def _identity(builds: dict[str, VersionBuild]) -> list[dict[str, object]]:
    out = []
    for sheet_id, meta in SHEETS.items():
        pages: dict[str, list[int]] = {}
        for name, build_ in builds.items():
            found = [i + 1 for i, s in enumerate(build_.sheets) if s.sheet_id == sheet_id]
            if found:
                pages[name] = found
        out.append({"sheet_id": sheet_id, "sheet_no": meta["no"], "title": meta["title"], "pages": pages})
    return out


def build() -> tuple[dict[str, bytes], dict[str, object]]:
    """The five PDFs (file name -> bytes) and the answer key."""
    font = scene.load_font()
    builds: dict[str, VersionBuild] = {}
    for name in VERSIONS:
        number = version_number(name)
        sheets = version_sheets(font, number)
        meta = scene.DocumentMeta(
            title=f"{DESIGNATION}. {revision_label(number - 1)}. Рабочие чертежи (синтетический комплект)",
            subject="Синтетическая фикстура сравнения версий VS-1. Не проектная документация.",
            doc_id_seed=f"cmp-fixtures-01/vs1/{name}",
            creation_date=f"D:{REVISION_DATES[number - 1][6:]}{REVISION_DATES[number - 1][3:5]}"
                          f"{REVISION_DATES[number - 1][:2]}000000Z")
        builds[name] = VersionBuild(name, number, sheets, scene.build_document(sheets, meta, font),
                                    f"{name.lower()}.pdf")

    files = {f"vs1/{b.filename}": b.built.data for b in builds.values()}

    versions = []
    for name, b in builds.items():
        revisions = [s.revision for s in b.sheets]
        top = max(revisions)
        versions.append({
            "id": name, "file": f"vs1/{b.filename}",
            "sha256": hashlib.sha256(b.built.data).hexdigest(), "bytes": len(b.built.data),
            "label": revision_label(top), "date": REVISION_DATES[top], "designation": DESIGNATION,
            "page_count": len(b.sheets),
            "pdf_title": f"{DESIGNATION}. {revision_label(b.number - 1)}. Рабочие чертежи (синтетический комплект)",
            "pages": [_page_fact(s, i + 1, p) for i, (s, p) in enumerate(zip(b.sheets, b.built.pages))],
        })

    transitions = []
    for transition in EXPECTED_STATUS:
        entries = _pairs(transition, builds, font)
        counts = {s: 0 for s in STATUSES}
        for e in entries:
            counts[str(e["expected_status"])] += 1
        record: dict[str, object] = {
            "id": f"{transition[0]}->{transition[1]}", "from": transition[0], "to": transition[1],
            "from_label": versions[version_number(transition[0]) - 1]["label"],
            "to_label": versions[version_number(transition[1]) - 1]["label"],
            "status_counts": counts, "sheets": entries,
        }
        if transition == ("V3", "V4"):
            record["permit"] = _permit(entries)
        transitions.append(record)

    key: dict[str, object] = {
        "schema": SCHEMA,
        "synthetic": True,
        "notice": ("Synthetic corpus. Every name, mark and number is invented; no customer, production or "
                   "real project bytes (owner decision OD-17)."),
        "generated_by": "tools/fixtures/comparison/build.py",
        "regenerate": "python3 tools/fixtures/comparison/build.py",
        "designation": DESIGNATION,
        "statuses": list(STATUSES),
        "channels": list(CHANNELS),
        "channel_rules": {
            "channels_with_differences": "the engine must report a difference in each of these channels",
            "channels_without_differences": "the engine must report no difference in any of these channels",
            "unconstrained": ("a channel in neither list may or may not report; for example a changed "
                              "number may or may not also show in geometry because its glyph pixels differ"),
        },
        "coordinates": ("PDF points, origin at the lower left of the MediaBox, as written; no sheet in this "
                        "set has /Rotate or a CropBox. bbox = [x0, y0, x1, y1]."),
        "versions": versions,
        "sheet_identity": _identity(builds),
        "transitions": transitions,
    }
    return files, key
