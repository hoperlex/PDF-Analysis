"""The packet of a sheet: candidates, pictures, the text for the model (`CMP-VC-AISHEET-01`).

A port of the original's ``sheet_changes/pack.py`` (`23f379fd`, lines 1-433). One call per sheet. The pictures are: the overview of sheet B
with the frames of the candidates; for the places on the drawing, shared crops of neighbouring places (A and B in one picture); for the
tables, the crop of the table of A and B when the answer cannot be checked without a picture (numbers with units in the changed text,
graphics in a row, a whole table). Purely textual changes of rows go without pictures. **No coordinates are written into the text of
the model.**

Differences from the original, each for a stated reason:

* **At most eight pictures per request** (``A-12``, ADR-0025 decision 18; ``MAX_IMAGES``). The original sends as many as it builds. Here
  the overview comes first, then the tables, then the places by the number of pointers they hold; what does not fit is told to the model
  ("pictures: none, the limit of the request -- zoom on request") and stays a candidate it must still sort.
* **No overlay picture** (the original's third part of a place: red only-A, blue only-B). The engine's mask is a different, packed format
  (``mask_codec``) and the packet reads raw boxes only.
* **No captions are drawn** on the pictures (see :mod:`.images`); the text lists each picture and says what is in it.
* **The pictures are rendered after the plan.** :func:`assemble` with ``render=False`` plans them (their number and an estimate of their
  size) -- that is all an estimate needs and it reads no picture; with ``render=True`` it cuts them. A picture that cannot be cut
  (the page has no stored pyramid) is dropped and the ones after it keep their order; the text is written after, from what exists.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets import images as pix
from auditmanager.comparison.ai_sheets.candidates import UNIT_NUMBER, Collected, PageText, collect
from auditmanager.comparison.ai_sheets.material import SheetMaterial
from auditmanager.comparison.ai_sheets.model import IMAGE_MAX_PX, MAX_OUTPUT_TOKENS
from auditmanager.comparison.ai_sheets.schema import PROMPT_DIGEST, PROMPT_TEMPLATE, PROMPT_VERSION

__all__ = [
    "GROUP_MAX_PT",
    "MAX_PACKET_IMAGES",
    "Packet",
    "SheetFacts",
    "assemble",
    "boundary",
    "cell",
    "engine_notes",
    "render_data",
    "render_prompt",
]

SCHEMA: Final[str] = "cmp-sheet-changes-packet/1"
GROUP_MAX_PT: Final[float] = 520.0  # pack.py:36
TEXT_PX: Final[float] = 14.0  # pack.py:38
DPI_RANGE: Final[tuple[float, float]] = (150.0, 300.0)  # pack.py:39
XREF_LIMIT: Final[int] = 2  # pack.py:40
POINTERS_SHOWN: Final[int] = 30  # pack.py:41
MAX_XREF_MARKS: Final[int] = 30  # context.py:221
_MARKS: Final = re.compile(r"[A-Za-zА-Яа-яЁё]{1,4}-[0-9][0-9A-Za-zА-Яа-яЁё*/.]*")  # pack.py:218
#: What the estimate adds for the other-sheet lines of a packet that names designations (``XREF_LIMIT`` lines of 900 characters at
#: most); the estimate does not look for them (that reads every page of two versions), the run does.
XREF_ALLOWANCE_CHARS: Final[int] = 900 * XREF_LIMIT

#: The `ai_sheets` request carries the overview and the crops; the limit of ``A-12`` (``executors.public.MAX_IMAGES``).
MAX_PACKET_IMAGES: Final[int] = 8

# ``prompt.py:18-45`` (the Russian labels of the engine's channels and reasons).
CHANNELS: Final[Mapping[str, str]] = {
    "geometry": "графика", "color": "цвет и оформление линий", "text": "текст", "text_coverage": "текстовый слой",
    "zones": "служебные зоны", "annotations": "пометки (аннотации)", "warnings": "предупреждения", "spec_positions": "позиции СО",
}
REASONS: Final[Mapping[str, str]] = {
    "MATCH_LOW_CONFIDENCE": "сопоставление листов с низкой уверенностью",
    "MATCH_AMBIGUOUS": "сопоставление листов неоднозначно",
    "MATCH_UNRESOLVED": "лист не сопоставлен",
    "ALIGNMENT_UNRELIABLE": "совмещение листов ненадёжно",
    "ALIGNMENT_PARTIAL": "совмещена только часть листа",
    "PARTIAL_COVERAGE": "часть площади не проверена (предупреждение)",
    "DUPLICATE_SHEET": "дубль листа в версии",
    "RENDER_FAILED": "рендер не выполнен",
    "PAGE_TOO_LARGE": "страница больше допустимого размера",
    "FRAME_MISMATCH": "размер страницы по тексту и по растру не совпал",
    "NO_TEXT_LAYER": "нет текстового слоя",
    "TEXT_UNREADABLE_IN_DIFF_AREA": "в областях отличий есть надписи без текстового слоя",
    "STAMP_NOT_RECOGNIZED": "штамп не распознан",
    "SPEC_NOT_PARSED": "спецификация не разобрана",
}
STATUS_LABELS: Final[Mapping[str, str]] = {  # ``version_comparison/status.py`` (the words of the sheet statuses)
    "same": "Совпадает", "same_zones_changed": "Совпадает, изменены служебные зоны", "different": "Есть отличия",
    "needs_review": "Нужна проверка", "added": "Лист добавлен", "removed": "Лист удалён", "unmatched": "Не сопоставлен",
}
_UNCHECKED: Final = re.compile(r"^UNCHECKED_CHANNEL_([A-Z_]+)$")


def cell(value: Any, limit: int = 300) -> str:
    """``prompt.py:73-78``."""
    text = "" if value is None else str(value)
    text = " / ".join(part.strip() for part in text.splitlines() if part.strip())
    if len(text) > limit:
        text = text[:limit] + " …"
    return text.replace("|", "\\|") or "—"


def boundary(seed: str, body: str) -> tuple[str, str]:
    """The marks that fence the data off from the instructions: a token that does not occur in the data (``prompt.py:64-70``)."""
    for salt in range(100):
        token = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()[:12]
        if token not in body:
            return f"<<<ДАННЫЕ {token}>>>", f"<<<КОНЕЦ ДАННЫХ {token}>>>"
    raise ValueError("не удалось подобрать метку блока данных")


def engine_notes(reasons: Sequence[str]) -> list[str]:
    """The engine's reasons as the sentences of the packet (``pack.py:238-247``)."""
    notes = []
    for reason in reasons:
        unchecked = _UNCHECKED.match(reason)
        if unchecked:
            channel = unchecked.group(1).lower()
            notes.append(f"не проверен канал «{CHANNELS.get(channel, channel)}»")
        else:
            notes.append(REASONS.get(reason, reason))
    return notes


@dataclass(frozen=True, slots=True)
class SheetFacts:
    """What the header of the packet says about the sheet pair; every member is data of the stored rows."""

    sheet_pair_id: str
    title: str
    project_title: str
    designation: str
    label_a: str
    label_b: str
    page_a: int
    page_b: int
    sheet_number: str
    status: str
    reasons: tuple[str, ...]
    page_profile_a: str
    page_profile_b: str
    version_a: str
    version_b: str


@dataclass(slots=True)
class Packet:
    """The packet: ``document`` is the data the text and the check read; ``image_bytes`` holds the rendered pictures by id."""

    document: dict[str, Any]
    prompt: str
    image_bytes: dict[str, bytes] = field(default_factory=dict)
    rendered: bool = False

    @property
    def packet_id(self) -> str:
        return str(self.document["packet_id"])

    @property
    def images(self) -> list[dict[str, Any]]:
        return list(self.document["images"])

    @property
    def candidates(self) -> list[dict[str, Any]]:
        return list(self.document["candidates"])


# -- pictures ------------------------------------------------------------------------------------------------------------------


def _text_dpi(words: Sequence[Sequence[Any]], box: Sequence[float]) -> float:
    """The dpi that makes the text of the area about 14 px high (``pack.py:69-73``)."""
    sizes = [min(w[2] - w[0], w[3] - w[1]) for w in words if geo.intersects(box, [float(v) for v in w[:4]])]
    sizes = [s for s in sizes if 1.0 < s < 40]
    dpi = TEXT_PX * 72.0 / statistics.median(sizes) if sizes else 200.0
    return max(DPI_RANGE[0], min(DPI_RANGE[1], dpi))


def _place_groups(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Neighbouring places share one picture (``pack.py:76-89``)."""
    groups: list[dict[str, Any]] = []
    for c in candidates:
        if c["kind"] not in ("place", "shift") or not c.get("context_a"):
            continue
        box = c["context_a"]
        for group in groups:
            joined = geo.union([group["box"], box])
            if joined is not None and max(joined[2] - joined[0], joined[3] - joined[1]) <= GROUP_MAX_PT:
                group["box"], group["ids"] = joined, [*group["ids"], c["id"]]
                break
        else:
            groups.append({"box": list(box), "ids": [c["id"]]})
    return groups


def _needs_table_image(candidate: Mapping[str, Any], pointers: Mapping[str, Mapping[str, Any]]) -> bool:
    """Without a picture the answer cannot be checked: a whole table, a graphic in a row, a number with a unit (``pack.py:92-101``)."""
    if candidate["full"]:
        return True
    for pid in candidate["pointers"]:
        pointer = pointers[pid]
        if pointer["type"] == "region":
            return True
        if UNIT_NUMBER.search(f"{pointer['before']} {pointer['after']}"):
            return True
    return False


def _place_plan(group: Mapping[str, Any], words_a: Sequence[Sequence[Any]], transform: Sequence[float]) -> dict[str, Any]:
    """The picture of a place: the crops of A and B, one under the other for a wide place, side by side for a tall one (``pack.py:138-168``)."""
    box_a = [round(v, 1) for v in group["box"]]
    box_b = [round(v, 1) for v in geo.a_to_b_page(transform, box_a)]
    width, height = box_a[2] - box_a[0], box_a[3] - box_a[1]
    long_pt, short_pt = max(width, height), min(width, height)
    dpi = min(
        _text_dpi(words_a, box_a), IMAGE_MAX_PX * 72.0 / max(long_pt, 1.0), IMAGE_MAX_PX * 72.0 / (2.6 * short_pt + 40),
    )
    crop_w, crop_h = max(1, int(width * dpi / 72)), max(1, int(height * dpi / 72))
    size = (crop_w, 2 * crop_h + 8) if width >= height else (2 * crop_w + 8, crop_h)
    scale = min(1.0, IMAGE_MAX_PX / max(size))
    return {
        "kind": "place", "candidates": list(group["ids"]), "box_a": box_a, "box_b": box_b, "dpi": round(dpi, 1),
        "vertical_stack": width >= height, "size_px": [max(1, int(size[0] * scale)), max(1, int(size[1] * scale))],
    }


def _table_plan(candidate: Mapping[str, Any], words: Mapping[str, Sequence[Sequence[Any]]]) -> dict[str, Any]:
    """The picture of a table: the table of A, under it the table of B -- whole, or the header and the touched rows (``pack.py:170-201``)."""
    parts: dict[str, list[list[float]]] = {}
    dpis: dict[str, float] = {}
    for side, key in (("A", "region_a"), ("B", "region_b")):
        region = candidate.get(key)
        if not region:
            continue
        if candidate["full"]:
            boxes = [geo.expand(region, 4.0)]
        else:
            boxes = [geo.expand(b, 2.0) for b in (([candidate["header_box"]] if candidate.get("header_box") else [])
                                                  + [row["box"] for row in candidate["rows_" + side.lower()]])]
        width = max(b[2] - b[0] for b in boxes)
        height = sum(b[3] - b[1] for b in boxes)
        union = geo.union(boxes) or boxes[0]
        dpis[side] = min(
            _text_dpi(words[side], union), IMAGE_MAX_PX * 72.0 / max(width, 1.0), IMAGE_MAX_PX * 72.0 / (2.1 * height + 40),
        )
        parts[side] = [[round(v, 1) for v in b] for b in boxes]
    width_px = height_px = 1
    for side, boxes in parts.items():
        width_px = max(width_px, int(max(b[2] - b[0] for b in boxes) * dpis[side] / 72))
        height_px += int(sum(b[3] - b[1] for b in boxes) * dpis[side] / 72) + 8
    scale = min(1.0, IMAGE_MAX_PX / max(width_px, height_px))
    return {
        "kind": "table", "candidates": [candidate["id"]], "parts": parts, "dpi": {s: round(v, 1) for s, v in dpis.items()},
        "size_px": [max(1, int(width_px * scale)), max(1, int(height_px * scale))],
    }


def _overview_plan(candidates: Sequence[Mapping[str, Any]], page_b: Any) -> dict[str, Any] | None:
    ids = [c["id"] for c in candidates if c.get("area")]
    if not ids:
        return None
    long_px = min(IMAGE_MAX_PX, 1400)  # the stored preview is 1400 px on its long side (profile limits)
    if page_b.width_pt <= 0 or page_b.height_pt <= 0:
        return None
    scale = long_px / max(page_b.width_pt, page_b.height_pt)
    return {
        "kind": "overview", "candidates": ids,
        "size_px": [max(1, int(page_b.width_pt * scale)), max(1, int(page_b.height_pt * scale))],
    }


def _plan_images(
    collected: Collected, texts: Mapping[str, PageText], page_b: Any, transform: Sequence[float],
) -> list[dict[str, Any]]:
    """The pictures to cut, at most eight: the overview, the tables (the larger first), the places (the larger first)."""
    candidates = collected.candidates
    by_id = {c["id"]: c for c in candidates}
    overview = _overview_plan(candidates, page_b)
    tables = [
        _table_plan(c, {"A": texts["A"].words, "B": texts["B"].words})
        for c in candidates if c["kind"] == "table" and _needs_table_image(c, collected.pointers)
    ]
    places = [_place_plan(g, texts["A"].words, transform) for g in _place_groups(candidates)]
    size = lambda plan: -sum(len(by_id[i]["pointers"]) for i in plan["candidates"])  # noqa: E731
    tables.sort(key=lambda p: (size(p), p["candidates"]))
    places.sort(key=lambda p: (size(p), p["candidates"]))
    chosen = ([overview] if overview else []) + tables + places
    chosen = chosen[:MAX_PACKET_IMAGES]
    order = {"overview": 0, "table": 1, "place": 2}
    chosen.sort(key=lambda p: (order[p["kind"]], int(p["candidates"][0][1:])))
    for number, plan in enumerate(chosen, 1):
        plan["id"] = f"I{number}"
        plan["bytes"] = pix.estimate_bytes(*plan["size_px"])
    return chosen


def _render(plan: Mapping[str, Any], material: SheetMaterial, facts: SheetFacts, candidates: Mapping[str, Mapping[str, Any]],
            scale: float, transform: Sequence[float]) -> bytes | None:
    """One picture cut from the stored pages, or ``None`` when a part of it cannot be cut."""
    kind = plan["kind"]
    if kind == "overview":
        data = material.overview(facts.page_profile_b)
        if data is None:
            return None
        image = pix.decode(data)
        # the frames of the candidates, in the pixels of the picture (pack.py:120-136)
        page = material.page(facts.page_profile_b)
        sx, sy = image.width / page.width_pt, image.height / page.height_pt
        frames = []
        for cid in plan["candidates"]:
            area = candidates[cid].get("area")
            if area:
                b = geo.a_to_b_page(transform, geo.expand(area, 4.0))
                frames.append((cid, [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy]))
        return pix.encode_png(pix.draw_frames(image, frames))
    if kind == "place":
        long_px = max(1, int(IMAGE_MAX_PX / (1 if plan["vertical_stack"] else 2)))
        a = material.crop(facts.page_profile_a, plan["box_a"], long_side_px=min(long_px, IMAGE_MAX_PX))
        b = material.crop(facts.page_profile_b, plan["box_b"], long_side_px=min(long_px, IMAGE_MAX_PX))
        if a is None or b is None:
            return None
        pair = [pix.decode(a), pix.decode(b)]
        composed = pix.vstack(pair) if plan["vertical_stack"] else pix.hstack(pair)
        return pix.encode_png(pix.fit_long_side(composed, IMAGE_MAX_PX))
    # table
    sides = []
    for side, boxes in plan["parts"].items():
        profile = facts.page_profile_a if side == "A" else facts.page_profile_b
        pieces = []
        for box in boxes:
            dpi = plan["dpi"][side]
            long_side = max(1, int(max(box[2] - box[0], box[3] - box[1]) * dpi / 72))
            data = material.crop(profile, box, long_side_px=min(long_side, IMAGE_MAX_PX))
            if data is None:
                return None
            pieces.append(pix.decode(data))
        sides.append(pix.vstack(pieces, gap=3) if len(pieces) > 1 else pieces[0])
    if not sides:
        return None
    return pix.encode_png(pix.fit_long_side(pix.vstack(sides), IMAGE_MAX_PX))


# -- the text for the model --------------------------------------------------------------------------------------------------


def render_data(document: Mapping[str, Any]) -> str:
    """The data block: the header, the pictures, the candidates, the other sheets (``pack.py:256-331``)."""
    a, b = document["a"], document["b"]
    lines = [
        f"# Лист «{cell(document['title'], 160)}» · A стр. PDF {a['page']} → B стр. PDF {b['page']}", "",
        f"Проект: {cell(document['project'].get('title'))} (шифр {cell(document['project'].get('code'))}). "
        f"A — {cell(a['label'])}. B — {cell(b['label'])}. Лист по штампу: {cell(document['sheet_number'])}.",
        f"Статус сравнения: {cell(document['engine']['status_label'])}"
        + (f"; ограничения: {'; '.join(document['engine']['notes'])}" if document["engine"]["notes"] else "") + ".", "",
        "## Изображения (приложены в этом порядке)", "",
    ]
    for k, image in enumerate(document["images"], 1):
        what = {
            "overview": "обзор листа B целиком, рамки кандидатов",
            "place": "сверху или слева A, затем B (одно и то же место)",
            "table": "таблица: сверху A, ниже B",
        }[image["kind"]]
        lines.append(f"{k}. {image['id']} — {what}; кандидаты: {', '.join(image['candidates'])}")
    if not document["images"]:
        lines.append("Изображений нет.")
    lines += ["", "## Кандидаты", ""]
    pointers = document["pointers"]
    xref_by: dict[str, list[Mapping[str, Any]]] = {}
    for x in document["xrefs"]:
        for cid in x["for"]:
            xref_by.setdefault(cid, []).append(x)
    for c in document["candidates"]:
        shown_images = [im["id"] for im in document["images"] if c["id"] in im["candidates"] and im["kind"] != "overview"]
        if c["kind"] == "table":
            title = cell(c["title"] or "без названия", 200)
            scope = "таблица целиком" if c["full"] else "только затронутые строки и строки с теми же обозначениями"
            lines.append(f"### {c['id']} — таблица «{title}» · строк A: {len(c['rows_a'])}, B: {len(c['rows_b'])} · {scope}")
            if c["header"]:
                lines.append(f"Заголовок: {cell(c['header'], 600)}")
            for side, key in (("A", "rows_a"), ("B", "rows_b")):
                lines.append(f"Строки {side}:")
                lines += [f"- {cell(r['text'], 1500)}" for r in c[key]] or ["- нет"]
            pairs = ", ".join(x["key"] for x in c["pairs"]) or "нет"
            lines.append(
                "Предварительно по обозначению (может быть неверным: марка и место строки могут меняться): "
                f"есть в A и B — {pairs}; только в A — {', '.join(c['unpaired_a']) or 'нет'}; "
                f"только в B — {', '.join(c['unpaired_b']) or 'нет'}."
            )
        else:
            head = "место на чертеже" if c["kind"] == "place" else ("сдвиг элемента" if c["kind"] == "shift" else "запись")
            extra = []
            if c.get("view"):
                extra.append(f"вид: {cell(c['view'], 120)}")
            if c.get("anchors"):
                extra.append("рядом: " + ", ".join(c["anchors"]))
            lines.append(f"### {c['id']} — {head}" + (" · " + " · ".join(extra) if extra else ""))
            if c.get("labels_a") or c.get("labels_b"):
                lines.append(
                    f"Изменённые надписи: A — {', '.join('«' + cell(t, 120) + '»' for t in c['labels_a']) or 'нет'}; "
                    f"B — {', '.join('«' + cell(t, 120) + '»' for t in c['labels_b']) or 'нет'}."
                )
            if c.get("words_a") is not None:
                lines.append(f"Слова в области A: {cell(c.get('words_a'), 1500)}")
                lines.append(f"Слова в области B: {cell(c.get('words_b'), 1500)}")
        shown = c["pointers"][:POINTERS_SHOWN]
        described = []
        for pid in shown:
            q = pointers[pid]
            ba = ""
            if q["before"] or q["after"]:
                ba = f" «{cell(q['before'], 120) or '—'}» → «{cell(q['after'], 120) or '—'}»"
            described.append(f"{pid} {q['what']}{ba}")
        more = len(c["pointers"]) - len(shown)
        lines.append(
            "Указатели движка (позиционные; не доказательство замены изделия): " + "; ".join(described)
            + (f"; и ещё {more}" if more > 0 else "") + "."
        )
        if c.get("attached"):
            lines.append(
                f"Внутри этого места ещё {len(c['attached'])} мелких указателей (сдвиги надписей, толщина линий, "
                "сдвиги элементов) — смотри на изображении."
            )
        if c.get("links"):
            lines.append(f"Те же обозначения на этом листе: {', '.join(c['links'])}.")
        if xref_by.get(c["id"]):
            lines.append("Те же обозначения на других листах этих же версий: " + ", ".join(x["id"] for x in xref_by[c["id"]]) + ".")
        lines.append(f"Изображения: {', '.join(shown_images) if shown_images else 'нет — изменение текстовое; при необходимости zoom'}.")
        lines.append("")
    if document["xrefs"]:
        lines += ["## Другие листы этих же двух версий (найдено по обозначениям, только текст)", ""]
        for x in document["xrefs"]:
            label = f" ({cell(x['page_label'], 100)})" if x.get("page_label") else ""
            lines.append(f"- {x['id']} — {x['side']}, стр. PDF {x['page']}{label}, «{cell(x['mark'])}»: {cell(x['text'], 900)}")
        lines.append("")
    return "\n".join(lines)


def render_prompt(document: Mapping[str, Any]) -> str:
    """The instructions, the task and the data, the data fenced off by marks that do not occur in it (``pack.py:334-340``)."""
    body = render_data(document)
    begin, end = boundary(str(document["packet_id"]), body)
    instructions = PROMPT_TEMPLATE.replace("{{BEGIN}}", begin).replace("{{END}}", end)
    task = (
        f"ЗАДАНИЕ\n\npacket_id: {document['packet_id']}\npart_id: {document['part_id']}\n"
        f"Кандидатов: {len(document['candidates'])}. Изображений: {len(document['images'])}.\n"
    )
    return f"{instructions}\n{task}\n{begin}\n{body}\n{end}\n"


def prompt_with(document: Mapping[str, Any], *, addendum: str = "") -> str:
    return render_prompt(document) + addendum


# -- assembly -----------------------------------------------------------------------------------------------------------------


def _marks_wanted(candidates: Sequence[Mapping[str, Any]]) -> tuple[list[str], dict[str, list[str]]]:
    """The designations the candidates name, and which candidates name each (``pack.py:204-221``)."""
    from auditmanager.comparison.ai_sheets.candidates import norm_mark

    want: dict[str, list[str]] = {}
    for c in candidates:
        for mark in c.get("marks") or []:
            want.setdefault(mark, []).append(c["id"])
    marks: list[str] = []
    for c in candidates:
        texts = list(c.get("labels_a") or []) + list(c.get("labels_b") or [])
        texts += [r["key"] for r in (c.get("rows_a") or []) + (c.get("rows_b") or []) if r.get("key")]
        for text in texts:
            for mark in _MARKS.findall(text or ""):
                if mark not in marks:
                    marks.append(mark)
    marks = [m for m in marks if norm_mark(m) in want][:MAX_XREF_MARKS]
    return marks, want


def assemble(
    facts: SheetFacts, result: Mapping[str, Any], material: SheetMaterial, *, render: bool, xrefs: bool,
) -> Packet:
    """The packet of a sheet pair. ``render`` cuts the pictures (otherwise they are planned); ``xrefs`` looks for the designations on
    the other pages of the two versions (otherwise the packet has none and the estimate adds an allowance)."""
    page_a, page_b = material.page(facts.page_profile_a), material.page(facts.page_profile_b)
    transform = (result.get("how_compared") or {}).get("transform") or geo.IDENTITY
    texts = {
        "A": PageText(page_a.words, page_a.lines, revision_number=page_a.stamp.revision_number),
        "B": PageText(page_b.words, page_b.lines, revision_number=page_b.stamp.revision_number),
    }
    collected = collect(result, texts["A"], texts["B"], transform)
    by_id = {c["id"]: c for c in collected.candidates}
    found: list[dict[str, Any]] = []
    if xrefs:
        marks, want = _marks_wanted(collected.candidates)
        if marks:
            hits = material.find_marks(
                {"A": facts.version_a, "B": facts.version_b}, marks, skip_pages={"A": facts.page_a, "B": facts.page_b}, limit=XREF_LIMIT,
            )
            from auditmanager.comparison.ai_sheets.candidates import norm_mark

            for hit in hits:
                found.append({
                    "id": hit["id"], "side": hit["side"], "page": hit["page"], "page_label": hit.get("page_label", ""),
                    "mark": hit["mark"], "text": str(hit.get("text") or "")[:900], "bbox": hit.get("bbox"),
                    "for": want.get(norm_mark(hit["mark"]), []),
                })
    plans = _plan_images(collected, texts, page_b, transform)
    image_bytes: dict[str, bytes] = {}
    if render:
        kept: list[dict[str, Any]] = []
        for plan in plans:
            data = _render(plan, material, facts, by_id, 1.0, transform)
            if data is None:
                continue
            kept.append(plan)
            plan["_data"] = data
        for number, plan in enumerate(kept, 1):
            old = plan["id"]
            plan["id"] = f"I{number}"
            data = plan.pop("_data")
            image_bytes[plan["id"]] = data
            plan["bytes"] = len(data)
            plan["sha256"] = hashlib.sha256(data).hexdigest()
            plan["rendered_from"] = old
        plans = kept
    status_label = STATUS_LABELS.get(facts.status, facts.status)
    document: dict[str, Any] = {
        "schema": SCHEMA, "method": {"prompt_version": PROMPT_VERSION, "prompt_digest": PROMPT_DIGEST},
        "packet_id": None, "part_id": "P1", "sheet_pair_id": facts.sheet_pair_id, "title": facts.title,
        "project": {"title": facts.project_title, "code": facts.designation}, "sheet_number": facts.sheet_number,
        "a": {"label": facts.label_a, "page": facts.page_a}, "b": {"label": facts.label_b, "page": facts.page_b},
        "engine": {"status": facts.status, "status_label": status_label, "notes": engine_notes(facts.reasons)},
        "candidates": collected.candidates, "pointers": collected.pointers, "ledger": collected.ledger, "counts": collected.counts,
        "xrefs": found, "images": plans, "izm_b": collected.izm_b, "transform": list(transform),
        "canvas": result.get("canvas"),
    }
    identity = {
        k: (v if k != "images" else [{"kind": i["kind"], "candidates": i["candidates"]} for i in v])
        for k, v in document.items() if k not in ("packet_id", "sheet_pair_id", "ledger")
    }
    document["packet_id"] = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    prompt = render_prompt(document)
    data_text = render_data(document)
    document["budget"] = {
        "prompt_chars": len(prompt) + (0 if xrefs or not any(c.get("marks") for c in collected.candidates) else XREF_ALLOWANCE_CHARS),
        "data_chars": len(data_text), "images": len(plans), "image_bytes": sum(int(i["bytes"]) for i in plans),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }
    return Packet(document=document, prompt=prompt, image_bytes=image_bytes, rendered=render)
