"""SP-1: a stage pair. One П document and an assembly of three Р documents, with its answer key.

    OLD  `old_p.pdf`   СИНТ-02-АР    stage П, 6 sheets (P1..P6)
    NEW  `new_r1.pdf`  СИНТ-02-АР.1  stage Р, 3 sheets (R1..R3)   building 1
         `new_r2.pdf`  СИНТ-02-АР.2  stage Р, 1 sheet  (R4)       building 2
         `new_r3.pdf`  СИНТ-02-АР.3  stage Р, 2 sheets (R5, R6)   sections

A sheet title carries the sheet's type, building and level («План. Корпус 1. Этаж 1»,
«План. Корпус 1. Кровля», «Разрез 1-1. Корпус 1. Уровень +0,000»), which is what a sheet
passport is built from, so the five sheets that have a pair match on all three of them. The
pair also holds:

*   text changed (a room area, a roof slope), added (a note) and removed (a parapet note) on linked sheets;
*   a fragment moved to another sheet: the room schedule of building 2 stood on its own sheet in
    П (P6) and is a block on the plan sheet R4 in Р;
*   a sheet without a pair on each side: P6 (only in OLD) and R6 (only in NEW).

The answer key lists the links, the unpaired sheets and the text fragments by class. A fragment
is a `Text` operation whose id has the form `<sheet>.f.<key>`; the key is the identity of the
fragment across the two stages, authored. Title-block fields are not fragments: their expected
differences are listed per link under `stamp_differences`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ar_corpus import pdfwrite

from . import scene
from .scene import A3, A4, Line, Rect, Sheet, Text, bbox, frame_and_stamp, landscape

SCHEMA = "cmp-sp1-answer-key/1"
PROJECT = "СИНТ-02-АР"
ORGANISATION = "СИНТЕТИКПРОЕКТ"
OLD_DATE = "20.02.2026"
NEW_DATE = "20.04.2026"
A3L = landscape(A3)

Room = tuple[str, str, tuple[float, float, float, float]]
Note = tuple[str, str, tuple[float, float]]


@dataclass(frozen=True)
class Spec:
    sheet_id: str
    document: str
    title: str
    size: tuple[float, float]
    rooms: tuple[Room, ...] = ()
    notes: tuple[Note, ...] = ()
    lines: tuple[tuple[float, float, float, float], ...] = ()


@dataclass(frozen=True)
class Document:
    name: str
    file: str
    designation: str
    stage: str
    date: str
    title: str


DOCUMENTS = {
    "old_p": Document("old_p", "sp1/old_p.pdf", PROJECT, "П", OLD_DATE,
                      "СИНТ-02-АР. Стадия П. Архитектурные решения (синтетический документ)"),
    "new_r1": Document("new_r1", "sp1/new_r1.pdf", f"{PROJECT}.1", "Р", NEW_DATE,
                       "СИНТ-02-АР.1. Стадия Р. Корпус 1 (синтетический документ)"),
    "new_r2": Document("new_r2", "sp1/new_r2.pdf", f"{PROJECT}.2", "Р", NEW_DATE,
                       "СИНТ-02-АР.2. Стадия Р. Корпус 2 (синтетический документ)"),
    "new_r3": Document("new_r3", "sp1/new_r3.pdf", f"{PROJECT}.3", "Р", NEW_DATE,
                       "СИНТ-02-АР.3. Стадия Р. Разрезы (синтетический документ)"),
}
OLD_DOCUMENTS = ("old_p",)
NEW_DOCUMENTS = ("new_r1", "new_r2", "new_r3")

_EXPLICATION = (
    ("ex1", "Экспликация: 301 — производственный зал, 96,0 м²"),
    ("ex2", "Экспликация: 302 — бытовая, 14,0 м²"),
    ("ex3", "Экспликация: 303 — склад, 22,5 м²"),
)

OLD_SPECS = (
    Spec("P1", "old_p", "План. Корпус 1. Этаж 1", A3L,
         rooms=(("rm101", "101  Холл  24,5 м²", (120, 500, 350, 220)),
                ("rm102", "102  Кабинет  18,0 м²", (470, 500, 350, 220)),
                ("rm103", "103  Санузел  6,2 м²", (820, 500, 250, 220)),
                ("rm104", "104  Лестничная клетка  14,8 м²", (120, 260, 350, 240)),
                ("rm105", "105  Склад  12,4 м²", (470, 260, 350, 240))),
         notes=(("note1", "Высота помещений 3,0 м", (130, 215)),)),
    Spec("P2", "old_p", "План. Корпус 1. Этаж 2", A3L,
         rooms=(("rm201", "201  Зал  42,0 м²", (120, 480, 500, 260)),
                ("rm202", "202  Кабинет  16,5 м²", (620, 480, 300, 260)),
                ("rm203", "203  Санузел  6,2 м²", (920, 480, 200, 260)))),
    Spec("P3", "old_p", "План. Корпус 1. Кровля", A3L,
         rooms=(("roof", "Кровля корпуса 1", (120, 400, 900, 340)),),
         notes=(("roof1", "Уклон кровли 2 %", (140, 360)),
                ("roof2", "Парапет h = 600 мм", (140, 340)),
                ("roof3", "Водосток: 4 воронки", (140, 320)))),
    Spec("P4", "old_p", "План. Корпус 2. Этаж 1", A3L,
         rooms=(("rm301", "301  Производственный зал  96,0 м²", (120, 400, 600, 320)),
                ("rm302", "302  Бытовая  14,0 м²", (720, 400, 350, 320))),
         notes=(("note3", "Высота помещений 4,2 м", (130, 350)),)),
    Spec("P5", "old_p", "Разрез 1-1. Корпус 1. Уровень +0,000", A3L,
         rooms=(("cutbox", "Разрез 1-1", (200, 300, 700, 420)),),
         notes=(("cut1", "Отметка пола +0,000", (220, 280)),
                ("cut2", "Высота этажа 3,3 м", (220, 262)),
                ("cut3", "Отметка парапета +7,200", (220, 244))),
         lines=((200, 510, 900, 510),)),
    Spec("P6", "old_p", "Экспликация помещений. Корпус 2. Этаж 1", A4,
         notes=(("exhdr", "Экспликация помещений. Корпус 2, этаж 1", (70, 790)),
                *(( key, text, (70, 760 - 18 * i)) for i, (key, text) in enumerate(_EXPLICATION)),
                ("exarea", "Площадь застройки: 412 м²", (70, 690)))),
)

NEW_SPECS = (
    Spec("R1", "new_r1", "План. Корпус 1. Этаж 1", A3L,
         rooms=(("rm101", "101  Холл  25,1 м²", (120, 500, 350, 220)),
                ("rm102", "102  Кабинет  18,0 м²", (470, 500, 350, 220)),
                ("rm103", "103  Санузел  6,2 м²", (820, 500, 250, 220)),
                ("rm104", "104  Лестничная клетка  14,8 м²", (120, 260, 350, 240)),
                ("rm106", "106  Тамбур  4,2 м²", (470, 260, 350, 240))),
         notes=(("note1", "Высота помещений 3,0 м", (130, 215)),)),
    Spec("R2", "new_r1", "План. Корпус 1. Этаж 2", A3L,
         rooms=(("rm201", "201  Зал  42,0 м²", (120, 480, 500, 260)),
                ("rm202", "202  Кабинет  16,5 м²", (620, 480, 300, 260)),
                ("rm203", "203  Санузел  6,2 м²", (920, 480, 200, 260))),
         notes=(("note2", "Отметка чистого пола +3,300", (130, 440)),)),
    Spec("R3", "new_r1", "План. Корпус 1. Кровля", A3L,
         rooms=(("roof", "Кровля корпуса 1", (120, 400, 900, 340)),),
         notes=(("roof1", "Уклон кровли 3 %", (140, 360)),
                ("roof3", "Водосток: 4 воронки", (140, 320)))),
    Spec("R4", "new_r2", "План. Корпус 2. Этаж 1", A3L,
         rooms=(("rm301", "301  Производственный зал  96,0 м²", (120, 400, 600, 320)),
                ("rm302", "302  Бытовая  14,0 м²", (720, 400, 350, 320))),
         notes=(("note3", "Высота помещений 4,2 м", (130, 350)),
                *((key, text, (130, 320 - 18 * i)) for i, (key, text) in enumerate(_EXPLICATION)))),
    Spec("R5", "new_r3", "Разрез 1-1. Корпус 1. Уровень +0,000", A3L,
         rooms=(("cutbox", "Разрез 1-1", (200, 300, 700, 420)),),
         notes=(("cut1", "Отметка пола +0,000", (220, 280)),
                ("cut2", "Высота этажа 3,3 м", (220, 262)),
                ("cut3", "Отметка парапета +7,200", (220, 244))),
         lines=((200, 510, 900, 510),)),
    Spec("R6", "new_r3", "Разрез 2-2. Корпус 2. Уровень +0,000", A3L,
         rooms=(("cutbox2", "Разрез 2-2", (200, 300, 700, 420)),),
         notes=(("cut4", "Отметка пола +0,000 (корпус 2)", (220, 280)),
                ("cut5", "Высота этажа 4,2 м", (220, 262)))),
)

#: Authored: which old sheet pairs with which new sheet, and why.
LINKS = (("P1", "R1"), ("P2", "R2"), ("P3", "R3"), ("P4", "R4"), ("P5", "R5"))
OLD_ONLY = ("P6",)
NEW_ONLY = ("R6",)

#: Authored: the expected text outcome, checked against the sheets by `build()`.
EXPECTED_TEXT = {
    "changed": [("rm101", "P1", "R1"), ("roof1", "P3", "R3")],
    "added": [("rm106", "R1"), ("note2", "R2"), ("cutbox2", "R6"), ("cut4", "R6"), ("cut5", "R6")],
    "removed": [("rm105", "P1"), ("roof2", "P3"), ("exhdr", "P6"), ("exarea", "P6")],
    "moved_between_sheets": [("ex1", "P6", "R4"), ("ex2", "P6", "R4"), ("ex3", "P6", "R4")],
}


class BuildError(RuntimeError):
    pass


def _sheet(font: pdfwrite.EmbeddedFont, spec: Spec, number: int) -> Sheet:
    doc = DOCUMENTS[spec.document]
    ops: list = []
    for key, text, (x, y, w, h) in spec.rooms:
        ops.append(Rect(f"{spec.sheet_id}.r.{key}", x=x, y=y, w=w, h=h, width=1.2))
        ops.append(Text(f"{spec.sheet_id}.f.{key}", x=x + 10, y=y + h - 22, text=text, size=11))
    for key, text, (x, y) in spec.notes:
        ops.append(Text(f"{spec.sheet_id}.f.{key}", x=x, y=y, text=text, size=10))
    for index, (x1, y1, x2, y2) in enumerate(spec.lines):
        ops.append(Line(f"{spec.sheet_id}.l.{index + 1}", x1=x1, y1=y1, x2=x2, y2=y2, width=1.0))
    stamp_ops, stamp_box = frame_and_stamp(
        spec.size, designation=doc.designation, title=spec.title, stage=doc.stage,
        sheet_no=str(number), revision_label="Изм.0", date=doc.date, organisation=ORGANISATION, font=font)
    return Sheet(sheet_id=spec.sheet_id, title=spec.title, sheet_no=str(number), size=spec.size,
                 ops=ops + stamp_ops, revision=0, stamp_bbox=tuple(round(v, 2) for v in stamp_box))


def passport(title: str) -> dict[str, str]:
    """Type, building and level read from a sheet title of the form «Тип. Корпус N. Уровень»."""
    parts = [p.strip() for p in title.split(". ")]
    return {"type": parts[0], "building": parts[1], "level": ". ".join(parts[2:]) if len(parts) > 2 else ""}


def _fragments(sheet: Sheet, font) -> dict[str, tuple[str, list[float]]]:
    out = {}
    for op in sheet.ops:
        if isinstance(op, Text) and op.zone == "content" and ".f." in op.id:
            out[op.id.split(".f.", 1)[1]] = (op.text, list(bbox(op, font)))
    return out


def _stamp_text(sheet: Sheet, field_name: str) -> str:
    return sheet.by_id()[f"stamp.{field_name}"].text  # type: ignore[attr-defined]


def _stamp_differences(old: Sheet, new: Sheet) -> list[dict[str, str]]:
    out = []
    for name in ("designation", "stage", "sheet_no", "revision", "date"):
        before, after = _stamp_text(old, name), _stamp_text(new, name)
        if before != after:
            out.append({"field": name, "before": before, "after": after})
    return out


def build() -> tuple[dict[str, bytes], dict[str, object]]:
    font = scene.load_font()
    sheets: dict[str, Sheet] = {}
    pages: dict[str, tuple[str, int]] = {}
    per_doc: dict[str, list[Sheet]] = {name: [] for name in DOCUMENTS}
    for spec in (*OLD_SPECS, *NEW_SPECS):
        number = len(per_doc[spec.document]) + 1
        sheet = _sheet(font, spec, number)
        sheets[spec.sheet_id] = sheet
        per_doc[spec.document].append(sheet)
        pages[spec.sheet_id] = (spec.document, number)

    built: dict[str, scene.BuiltDocument] = {}
    files: dict[str, bytes] = {}
    for name, doc in DOCUMENTS.items():
        meta = scene.DocumentMeta(
            title=doc.title, subject="Синтетическая фикстура сравнения стадий SP-1. Не проектная документация.",
            doc_id_seed=f"cmp-fixtures-01/sp1/{name}",
            creation_date=f"D:{doc.date[6:]}{doc.date[3:5]}{doc.date[:2]}000000Z")
        built[name] = scene.build_document(per_doc[name], meta, font)
        files[doc.file] = built[name].data

    sheet_facts = []
    for name, doc in DOCUMENTS.items():
        for index, sheet in enumerate(per_doc[name]):
            sheet_facts.append({
                "sheet_id": sheet.sheet_id, "document": name, "file": doc.file, "page": index + 1,
                "side": "old" if name in OLD_DOCUMENTS else "new",
                "title": sheet.title, "passport": passport(sheet.title),
                "format": scene.format_name(sheet.width, sheet.height),
                "width_pt": round(sheet.width, 2), "height_pt": round(sheet.height, 2),
                "text_layer": True,
                "stamp": {n: _stamp_text(sheet, n) for n in ("designation", "title", "stage", "sheet_no", "revision", "date")},
                "stamp_bbox": [round(v, 2) for v in sheet.stamp_bbox],
                "fragments": [{"key": k, "text": t, "bbox": b} for k, (t, b) in sorted(_fragments(sheet, font).items())],
                "content_sha256": hashlib.sha256(built[name].pages[index].content).hexdigest(),
            })

    # Fragment classes, derived from the authored fragment keys.
    old_frags = {s: _fragments(sheets[s], font) for s in (spec.sheet_id for spec in OLD_SPECS)}
    new_frags = {s: _fragments(sheets[s], font) for s in (spec.sheet_id for spec in NEW_SPECS)}
    where_new = {k: s for s, fr in new_frags.items() for k in fr}
    where_old = {k: s for s, fr in old_frags.items() for k in fr}

    changed, unchanged, removed, added, moved = [], [], [], [], []
    paired_old = {o for o, _ in LINKS}
    paired_new = {n for _, n in LINKS}
    for old_id, new_id in LINKS:
        of, nf = old_frags[old_id], new_frags[new_id]
        for key in sorted(set(of) | set(nf)):
            if key in of and key in nf:
                record = {"key": key, "old_sheet": old_id, "new_sheet": new_id,
                          "before": of[key][0], "after": nf[key][0],
                          "bbox_before": of[key][1], "bbox_after": nf[key][1]}
                (changed if of[key][0] != nf[key][0] else unchanged).append(record)
            elif key in of:
                if key in where_new:
                    moved.append({"key": key, "text": of[key][0], "old_sheet": old_id, "new_sheet": where_new[key],
                                  "bbox_before": of[key][1], "bbox_after": new_frags[where_new[key]][key][1]})
                else:
                    removed.append({"key": key, "old_sheet": old_id, "before": of[key][0], "bbox_before": of[key][1]})
            else:
                if key in where_old and where_old[key] not in paired_old:
                    continue  # recorded from the unpaired old sheet below
                if key in where_old:
                    moved.append({"key": key, "text": nf[key][0], "old_sheet": where_old[key], "new_sheet": new_id,
                                  "bbox_before": old_frags[where_old[key]][key][1], "bbox_after": nf[key][1]})
                else:
                    added.append({"key": key, "new_sheet": new_id, "after": nf[key][0], "bbox_after": nf[key][1]})
    for old_id in OLD_ONLY:
        for key, (text, box) in sorted(old_frags[old_id].items()):
            if key in where_new:
                moved.append({"key": key, "text": text, "old_sheet": old_id, "new_sheet": where_new[key],
                              "bbox_before": box, "bbox_after": new_frags[where_new[key]][key][1]})
            else:
                removed.append({"key": key, "old_sheet": old_id, "before": text, "bbox_before": box})
    for new_id in NEW_ONLY:
        for key, (text, box) in sorted(new_frags[new_id].items()):
            added.append({"key": key, "new_sheet": new_id, "after": text, "bbox_after": box})

    computed = {
        "changed": sorted((r["key"], r["old_sheet"], r["new_sheet"]) for r in changed),
        "added": sorted((r["key"], r["new_sheet"]) for r in added),
        "removed": sorted((r["key"], r["old_sheet"]) for r in removed),
        "moved_between_sheets": sorted((r["key"], r["old_sheet"], r["new_sheet"]) for r in moved),
    }
    authored = {k: sorted(v) for k, v in EXPECTED_TEXT.items()}
    if computed != authored:
        raise BuildError(f"fragment classes {computed} differ from the authored {authored}")

    links = []
    for old_id, new_id in LINKS:
        old, new = sheets[old_id], sheets[new_id]
        if passport(old.title) != passport(new.title):
            raise BuildError(f"{old_id}/{new_id}: passports differ")
        links.append({
            "old": old_id, "new": new_id, "old_document": pages[old_id][0], "new_document": pages[new_id][0],
            "old_page": pages[old_id][1], "new_page": pages[new_id][1],
            "kind": "matched", "basis": ["type", "building", "level"], "passport": passport(old.title),
            "expected_confidence": "high",
            "stamp_differences": _stamp_differences(old, new),
            "counts": {
                "changed": sum(1 for r in changed if r["old_sheet"] == old_id),
                "added": sum(1 for r in added if r["new_sheet"] == new_id),
                "removed": sum(1 for r in removed if r["old_sheet"] == old_id),
                "unchanged": sum(1 for r in unchanged if r["old_sheet"] == old_id),
                "moved_out": sum(1 for r in moved if r["old_sheet"] == old_id),
                "moved_in": sum(1 for r in moved if r["new_sheet"] == new_id),
            },
        })
    # No two sheets of one side may share a passport, or the links above would be ambiguous.
    for side in (OLD_SPECS, NEW_SPECS):
        seen = [tuple(passport(s.title).values()) for s in side]
        if len(seen) != len(set(seen)):
            raise BuildError("two sheets on one side have the same passport")

    key: dict[str, object] = {
        "schema": SCHEMA,
        "synthetic": True,
        "notice": ("Synthetic corpus. Every name, mark and number is invented; no customer, production or "
                   "real project bytes (owner decision OD-17)."),
        "generated_by": "tools/fixtures/comparison/build.py",
        "regenerate": "python3 tools/fixtures/comparison/build.py",
        "project": PROJECT,
        "coordinates": "PDF points, origin at the lower left of the MediaBox; bbox = [x0, y0, x1, y1].",
        "documents": [
            {"name": name, "file": doc.file, "side": "old" if name in OLD_DOCUMENTS else "new",
             "designation": doc.designation, "stage": doc.stage, "date": doc.date, "revision": "Изм.0",
             "pdf_title": doc.title, "sha256": hashlib.sha256(built[name].data).hexdigest(),
             "bytes": len(built[name].data), "page_count": len(per_doc[name]),
             "sheets": [s.sheet_id for s in per_doc[name]]}
            for name, doc in DOCUMENTS.items()
        ],
        "assembly": {"old": list(OLD_DOCUMENTS), "new": list(NEW_DOCUMENTS),
                     "notes": "NEW is an assembly of three Р documents; OLD is one П document."},
        "sheets": sheet_facts,
        "sheet_links": links,
        "sheets_without_pair": {
            "old_only": [{"sheet_id": s, "reason": (
                "the room schedule of building 2 is a block on plan sheet R4 in the Р stage; the sheet "
                "itself has no Р counterpart")} for s in OLD_ONLY],
            "new_only": [{"sheet_id": s, "reason": "a section sheet that did not exist in the П stage"}
                         for s in NEW_ONLY],
        },
        "text_fragments": {
            "classes": ("changed: same key on linked sheets, text differs; added / removed: key only on the "
                        "new / old side (on a linked or unpaired sheet) and nowhere else; moved_between_sheets: "
                        "same key and same text on a different sheet than its link; unchanged: same key and text "
                        "on linked sheets"),
            "changed": changed,
            "added": added,
            "removed": removed,
            "moved_between_sheets": moved,
            "unchanged": unchanged,
        },
        "stamp_note": ("Title-block fields (designation, stage, sheet number, revision, date) are service "
                       "zones, not fragments; their expected differences are in sheet_links[].stamp_differences."),
    }
    return files, key
