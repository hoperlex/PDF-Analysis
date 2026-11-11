"""The one fictional object every section describes, and its floor plans.

Object «СИНТ-02»: «Производственно-административный комплекс «Синтез-2»» (synthetic; no address,
customer or person). Корпус 1 — two-storey administrative block, 36,0 × 18,0 м in axes 1–7 / А–Г,
floor height 3,3 м. Корпус 2 — one-storey production hall, 48,0 × 24,0 м in axes 1–9 / А–Д, height
7,2 м. Engineering sections draw their systems over the plan of Корпус 1, floor 1 (it holds the
technical rooms: switchboard, heat unit, ventilation plant, server room, pump room).

`Plan` maps metres of a building to page points; `draw_plan` draws walls, doors, windows, stairs,
axes and room tags, either in full (АР) or as a light underlay for the engineering sections.
"""

from __future__ import annotations

from dataclasses import dataclass

from .kit import GREY, Ops

OBJECT_CODE = "СИНТ-02"
OBJECT_NAME = "Производственно-административный комплекс «Синтез-2»"
ORGANISATION = "СИНТЕТИКПРОЕКТ"
DISCLAIMER = "Синтетический учебный документ. Не проектная документация и не нормативное заключение."

AXES_X = (("1", 0.0), ("2", 6.0), ("3", 12.0), ("4", 18.0), ("5", 24.0), ("6", 30.0), ("7", 36.0))
AXES_Y = (("А", 0.0), ("Б", 7.5), ("В", 10.5), ("Г", 18.0))
LENGTH, DEPTH = 36.0, 18.0
CORRIDOR = (7.5, 10.5)


@dataclass(frozen=True)
class Room:
    number: str
    name: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def area_text(self) -> str:
        return f"{self.area:.1f}".replace(".", ",")

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


FLOOR1 = (
    Room("101", "Лестничная клетка Л1", 0, 0, 6, 7.5),
    Room("102", "Гардероб", 6, 0, 12, 7.5),
    Room("103", "Вестибюль", 12, 0, 24, 7.5),
    Room("104", "Кабинет", 24, 0, 30, 7.5),
    Room("105", "Кабинет", 30, 0, 36, 7.5),
    Room("106", "Коридор", 0, 7.5, 36, 10.5),
    Room("107", "Электрощитовая", 0, 10.5, 4, 18),
    Room("108", "Тепловой пункт", 4, 10.5, 10, 18),
    Room("109", "Венткамера", 10, 10.5, 16, 18),
    Room("110", "Серверная", 16, 10.5, 20, 18),
    Room("111", "Санузел муж.", 20, 10.5, 23, 18),
    Room("112", "Санузел жен.", 23, 10.5, 26, 18),
    Room("113", "Насосная", 26, 10.5, 30, 18),
    Room("114", "Лестничная клетка Л2", 30, 10.5, 36, 18),
)

FLOOR2 = (
    Room("201", "Лестничная клетка Л1", 0, 0, 6, 7.5),
    Room("202", "Зал совещаний", 6, 0, 18, 7.5),
    Room("203", "Кабинет", 18, 0, 24, 7.5),
    Room("204", "Кабинет", 24, 0, 30, 7.5),
    Room("205", "Кабинет", 30, 0, 36, 7.5),
    Room("206", "Коридор", 0, 7.5, 36, 10.5),
    Room("207", "Кабинет", 0, 10.5, 10, 18),
    Room("208", "Кабинет", 10, 10.5, 16, 18),
    Room("209", "Комната отдыха", 16, 10.5, 20, 18),
    Room("210", "Санузел муж.", 20, 10.5, 23, 18),
    Room("211", "Санузел жен.", 23, 10.5, 26, 18),
    Room("212", "Кладовая", 26, 10.5, 30, 18),
    Room("213", "Лестничная клетка Л2", 30, 10.5, 36, 18),
)

FLOORS = {1: FLOOR1, 2: FLOOR2}


@dataclass(frozen=True)
class Plan:
    """Metres -> points: x = ox + m * scale, y = oy + m * scale."""

    ox: float
    oy: float
    scale: float = 20.0

    def p(self, mx: float, my: float) -> tuple[float, float]:
        return (self.ox + mx * self.scale, self.oy + my * self.scale)

    def x(self, mx: float) -> float:
        return self.ox + mx * self.scale

    def y(self, my: float) -> float:
        return self.oy + my * self.scale

    def box(self, margin: float = 40.0) -> tuple[float, float, float, float]:
        """The plan's extent with its axis bubbles, in points: (x0, y0, x1, y1)."""
        return (self.ox - margin, self.oy - margin, self.x(LENGTH) + margin, self.y(DEPTH) + margin)


# Plan placed on an A3 landscape sheet: 36 m x 20 pt = 720 pt wide, 18 m = 360 pt tall.
A3_PLAN = Plan(ox=110.0, oy=330.0, scale=20.0)

_DOORS = {  # floor -> list of (x_m, y_m, width_m, direction)
    1: [(18.9, 0, 1.4, "nw"), (3, 7.5, 1.0, "nw"), (8, 7.5, 1.0, "nw"), (13, 7.5, 1.2, "nw"), (26, 7.5, 1.0, "nw"),
        (32, 7.5, 1.0, "nw"), (1, 10.5, 1.0, "se"), (5, 10.5, 1.0, "se"), (11, 10.5, 1.0, "se"),
        (17, 10.5, 0.9, "se"), (21, 10.5, 0.8, "se"), (24, 10.5, 0.8, "se"), (27, 10.5, 1.0, "se"),
        (31, 10.5, 1.0, "se")],
    2: [(3, 7.5, 1.0, "nw"), (9, 7.5, 1.2, "nw"), (19, 7.5, 1.0, "nw"), (25, 7.5, 1.0, "nw"), (31, 7.5, 1.0, "nw"),
        (1, 10.5, 1.0, "se"), (11, 10.5, 1.0, "se"), (17, 10.5, 0.9, "se"), (21, 10.5, 0.8, "se"),
        (24, 10.5, 0.8, "se"), (27, 10.5, 1.0, "se"), (31, 10.5, 1.0, "se")],
}


def draw_plan(ops: Ops, plan: Plan, floor: int, *, underlay: bool = False, tags: bool = True,
              axes: bool = True, dims: bool = True, key_prefix: str | None = None,
              rooms: tuple[Room, ...] | None = None, doors: list | None = None) -> None:
    """Walls, openings, stairs, axes and (optionally) room tags of Корпус 1 at `floor`.

    `key_prefix` gives room tags stable fragment keys (`<prefix>.<number>`), so a tag changed
    between two versions is one object. `rooms` and `doors` replace the floor's defaults (the АР
    version series moves a partition and adds a door); a door entry may carry a fifth item, an
    RGB colour, to mark it (fire-rated doors).
    """
    s = plan.scale
    ext, inner = 0.4 * s, 0.15 * s
    rooms = FLOORS[floor] if rooms is None else rooms
    # exterior walls
    for (x1, y1, x2, y2) in ((0, 0, LENGTH, 0), (0, DEPTH, LENGTH, DEPTH)):
        ops.wall(plan.x(x1), plan.y(y1), plan.x(x2), plan.y(y2), ext, underlay)
    for xm in (0, LENGTH):
        ops.wall(plan.x(xm), plan.y(0), plan.x(xm), plan.y(DEPTH), ext, underlay)
    # corridor walls
    for ym in CORRIDOR:
        ops.wall(plan.x(0), plan.y(ym), plan.x(LENGTH), plan.y(ym), inner, underlay)
    # partitions: every room boundary inside a row
    seen: set[tuple[float, float, float]] = set()
    for room in rooms:
        if room.y0 == CORRIDOR[0] and room.y1 == CORRIDOR[1]:
            continue
        for xm in (room.x0, room.x1):
            if 0 < xm < LENGTH and (xm, room.y0, room.y1) not in seen:
                seen.add((xm, room.y0, room.y1))
                ops.wall(plan.x(xm), plan.y(room.y0), plan.x(xm), plan.y(room.y1), inner, underlay)
    # windows on the long facades, one per 6 m bay, skipping stair bays' second window
    for bay in range(6):
        cx = bay * 6 + 3
        for ym in (0, DEPTH):
            if floor == 1 and ym == 0 and bay == 3:
                continue  # the entrance
            ops.window(plan.x(cx - 0.9), plan.y(ym), plan.x(cx + 0.9), plan.y(ym), ext, underlay)
    for entry in (_DOORS[floor] if doors is None else doors):
        xm, ym, wm, direction = entry[:4]
        if len(entry) > 4 and not underlay:
            before = len(ops.ops)
            ops.door(plan.x(xm), plan.y(ym), wm * s, direction, underlay)
            import dataclasses as _dc
            ops.ops[before:] = [_dc.replace(op, rgb=entry[4]) for op in ops.ops[before:]]
        else:
            ops.door(plan.x(xm), plan.y(ym), wm * s, direction, underlay)
    # stairs
    for room in rooms:
        if room.name.startswith("Лестничная"):
            ops.stairs(plan.x(room.x0 + 0.6), plan.y(room.y0 + 1.2), (room.x1 - room.x0 - 1.2) * s,
                       (room.y1 - room.y0 - 2.4) * s, 12, underlay)
    if axes:
        top, bottom = plan.y(DEPTH) + 30, plan.y(0) - 30
        for label, xm in AXES_X:
            x = plan.x(xm)
            ops.line(x, bottom + 9, x, top - 9, 0.25, GREY, dash=(12, 3, 2, 3))
            ops.axis_bubble(x, top, label)
            ops.axis_bubble(x, bottom, label)
        left, right = plan.x(0) - 30, plan.x(LENGTH) + 30
        for label, ym in AXES_Y:
            y = plan.y(ym)
            ops.line(left + 9, y, right - 9, y, 0.25, GREY, dash=(12, 3, 2, 3))
            ops.axis_bubble(left, y, label)
            ops.axis_bubble(right, y, label)
    if dims and not underlay:
        for (_, a), (_, b) in zip(AXES_X, AXES_X[1:]):
            ops.dim(plan.x(a), plan.y(0) - 48, plan.x(b), plan.y(0) - 48, f"{int((b - a) * 1000)}", offset=0)
        ops.dim(plan.x(0), plan.y(0) - 64, plan.x(LENGTH), plan.y(0) - 64, "36000", offset=0)
    if tags:
        for room in rooms:
            cx, cy = room.centre
            x, y = plan.p(cx, cy)
            size = 7.0 if underlay else 7.5
            label = f"{room.number}" if underlay else f"{room.number} {room.name}"
            k = None if key_prefix is None else f"{key_prefix}.{room.number}"
            if room.number in ("106", "206"):
                y += 10 if underlay else 0
            from .kit import width_of, wrap
            room_w = (room.x1 - room.x0) * plan.scale - 6
            if underlay or width_of(label, size) <= room_w:
                ops.ctext(x, y + 3, label, size, GREY if underlay else (0, 0, 0), key=k)
            else:  # a narrow room: the number, then the name wrapped to the room's width
                ops.ctext(x, y + 3 + 9 * len(wrap(room.name, 6.5, room_w)), room.number, size, key=k)
                for i, part in enumerate(wrap(room.name, 6.5, room_w)):
                    kn = None if key_prefix is None else f"{key_prefix}.{room.number}.name{i + 1}"
                    ops.ctext(x, y + 3 + 9 * (len(wrap(room.name, 6.5, room_w)) - 1 - i), part, 6.5, key=kn)
            if not underlay:
                ka = None if key_prefix is None else f"{key_prefix}.{room.number}.area"
                ops.ctext(x, y - 7, f"{room.area_text()} м²", 7.0, key=ka)


#: Shared project parameters. Every section that states one of these uses this value, unless the
#: section deliberately plants a contradiction INSIDE its own document (the answer key says so).
FACTS = {
    "object": OBJECT_NAME,
    "k1": "Корпус 1 — административно-бытовой, 2 этажа, 36,0 × 18,0 м в осях 1–7 / А–Г",
    "k1_floor_height": "3,3 м",
    "k1_parapet": "+7,200",
    "k1_footprint": "648,0 м²",
    "k1_total_area": "1 184,0 м²",
    "k1_staff": "64 сотрудника",
    "k2": "Корпус 2 — производственный, 1 этаж, 48,0 × 24,0 м в осях 1–9 / А–Д",
    "k2_height": "7,2 м до низа несущих конструкций покрытия",
    "k2_footprint": "1 152,0 м²",
    "k2_staff": "36 работающих в одну смену",
    "zero": "Отметка 0,000 соответствует абсолютной отметке 214,60",
    "fire": "степень огнестойкости II, класс конструктивной пожарной опасности С0",
    "fire_k1": "класс функциональной пожарной опасности корпуса 1 — Ф4.3",
    "fire_k2": "класс функциональной пожарной опасности корпуса 2 — Ф5.1, категория по взрывопожарной и пожарной опасности — В",
    "site": "участок 180 × 90 м, площадь 1,62 га",
    "outdoor_t": "расчётная температура наружного воздуха для отопления −32 °С",
    "heat_source": "городская тепловая сеть, теплоноситель 130/70 °С; внутренний контур отопления 80/60 °С",
    "heat_k1": "тепловая нагрузка корпуса 1: отопление 0,145 Гкал/ч, вентиляция 0,082 Гкал/ч, ГВС 0,038 Гкал/ч",
    "water": "водоснабжение от городской сети, ввод Ду100; водопотребление корпуса 1 — 6,4 м³/сут",
    "sewer": "бытовая канализация в городскую сеть, выпуск Ду150",
    "power": "II категория надёжности, 380/220 В, TN-C-S, ВРУ-1 в электрощитовой 107, установленная мощность рабочего режима 92,1 кВт",
    "vent": "приточная установка П1 (венткамера 109) 6 200 м³/ч, вытяжная В1 5 800 м³/ч, дымоудаление ВД1",
    "rooms_tech": "107 электрощитовая, 108 тепловой пункт, 109 венткамера, 110 серверная, 113 насосная",
    "concrete": "монолитный железобетон, бетон B25, арматура A500C, плита перекрытия 220 мм",
    "steel": "каркас корпуса 2 — стальной, сталь С345, фермы пролётом 24 м с шагом 6 м",
    "construction_time": "продолжительность строительства 14 месяцев",
}
