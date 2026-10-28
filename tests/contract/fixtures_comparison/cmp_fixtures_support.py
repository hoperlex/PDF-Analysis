"""Independent checks of the comparison corpus against its answer keys.

The generator (`tools/fixtures/comparison`) writes the PDFs and the keys from one authoring
model. Nothing it did proves that a PDF *reader* sees what the key says, so every claim here is
re-read from the PDF bytes with a library the generator does not use: `pypdf` (pages,
annotations, metadata, rotation), `pdfplumber` (words, lines, rectangles, tables, sizes) and
`pypdfium2` (pages, sizes, text, raster).

Each `check_*` function returns a list of problems, each starting with a tag in square brackets.
An empty list means the corpus agrees with the key. The tests assert emptiness, and the guard
tests change the key (or a file) and assert that the matching tag appears, so a check that
could never fail would be caught.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Mapping

import pdfplumber
import pypdf
import pypdfium2 as pdfium

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / "fixtures" / "comparison"

TOLERANCE_PT = 1.5


def load_files() -> dict[str, bytes]:
    """Every committed corpus file, by path relative to `fixtures/comparison`."""
    return {
        str(path.relative_to(CORPUS)): path.read_bytes()
        for path in sorted(CORPUS.rglob("*")) if path.is_file()
    }


def load_key(files: Mapping[str, bytes], name: str) -> dict:
    return json.loads(files[f"{name}/answer_key.json"].decode("utf-8"))


class Pdf:
    """One PDF opened with the three readers, lazily."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self._plumber: pdfplumber.PDF | None = None
        self._pypdf: pypdf.PdfReader | None = None
        self._pdfium: pdfium.PdfDocument | None = None

    @property
    def plumber(self) -> pdfplumber.PDF:
        if self._plumber is None:
            self._plumber = pdfplumber.open(io.BytesIO(self.data))
        return self._plumber

    @property
    def reader(self) -> pypdf.PdfReader:
        if self._pypdf is None:
            self._pypdf = pypdf.PdfReader(io.BytesIO(self.data))
        return self._pypdf

    @property
    def pdfium(self) -> pdfium.PdfDocument:
        if self._pdfium is None:
            self._pdfium = pdfium.PdfDocument(self.data)
        return self._pdfium

    def close(self) -> None:
        if self._plumber is not None:
            self._plumber.close()
        if self._pdfium is not None:
            self._pdfium.close()


def pdf_box(page, bbox: list[float], pad: float = 0.0) -> tuple[float, float, float, float]:
    """A key bounding box (PDF space, origin lower left) as a pdfplumber crop box, clamped to the page."""
    x0, y0, x1, y1 = bbox
    return (
        max(0.0, x0 - pad), max(0.0, float(page.height) - y1 - pad),
        min(float(page.width), x1 + pad), min(float(page.height), float(page.height) - y0 + pad),
    )


def norm(text: str) -> str:
    """Whitespace collapsed: pdfplumber joins words with one space, the generator may write two."""
    return " ".join(text.split())


def text_at(page, bbox: list[float]) -> str:
    """The text pdfplumber reads in the key's box (objects that touch it), whitespace collapsed."""
    return norm(page.crop(pdf_box(page, bbox, 0.2)).extract_text() or "")


def has_phrase(text: str, value: str) -> bool:
    """Do the words of `value` appear one after another among the words of `text`?

    Whole words, not a substring: a stamp field «П» must not be "found" inside «План».
    """
    words, wanted = text.split(), value.split()
    if not wanted:
        return False
    return any(words[i:i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1))


def at(page, bbox: list[float], value: str) -> bool:
    """Is `value` among the words pdfplumber reads in the box?"""
    return has_phrase(text_at(page, bbox), value)


def objects_near(page, bbox: list[float]) -> list[dict]:
    """Stroked lines, rectangles and curves whose centre is within tolerance of the box centre."""
    cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
    found = []
    for obj in (*page.lines, *page.rects, *page.curves):
        ox, oy = (obj["x0"] + obj["x1"]) / 2.0, float(page.height) - (obj["top"] + obj["bottom"]) / 2.0
        if abs(ox - cx) <= TOLERANCE_PT and abs(oy - cy) <= TOLERANCE_PT:
            found.append(obj)
    return found


def _color_close(a, b) -> bool:
    if a is None or b is None:
        return False
    return len(a) == len(b) and all(abs(float(x) - float(y)) < 0.011 for x, y in zip(a, b))


def _format(width: float, height: float) -> str:
    sizes = {"A4": (595.28, 841.89), "A3": (841.89, 1190.55), "A2": (1190.55, 1683.78), "A1": (1683.78, 2383.94)}
    short, long_ = sorted((round(width, 2), round(height, 2)))
    for name, (w, h) in sizes.items():
        if abs(short - w) < 0.02 and abs(long_ - h) < 0.02:
            return name
    return "?"


# --------------------------------------------------------------------------------------
# VS-1
# --------------------------------------------------------------------------------------


def check_vs1(files: Mapping[str, bytes], key: dict) -> list[str]:
    problems: list[str] = []
    pdfs: dict[str, Pdf] = {}
    try:
        for version in key["versions"]:
            data = files.get(version["file"])
            if data is None:
                problems.append(f"[files] {version['file']} is missing")
                continue
            if hashlib.sha256(data).hexdigest() != version["sha256"] or len(data) != version["bytes"]:
                problems.append(f"[sha] {version['file']} does not match the key's digest")
            pdfs[version["id"]] = Pdf(data)
        for version in key["versions"]:
            if version["id"] in pdfs:
                problems += _check_version(pdfs[version["id"]], version)
        for transition in key["transitions"]:
            if transition["from"] in pdfs and transition["to"] in pdfs:
                problems += _check_transition(pdfs[transition["from"]], pdfs[transition["to"]], transition, key, pdfs)
        problems += _check_identity(pdfs, key)
    finally:
        for pdf in pdfs.values():
            pdf.close()
    return problems


def _stamp_text(page, stamp_bbox: list[float]) -> str:
    return page.crop(pdf_box(page, stamp_bbox)).extract_text() or ""


def _check_version(pdf: Pdf, version: dict) -> list[str]:
    out: list[str] = []
    name = version["file"]
    counts = {"pypdf": len(pdf.reader.pages), "pdfplumber": len(pdf.plumber.pages), "pdfium": len(pdf.pdfium)}
    if set(counts.values()) != {version["page_count"]} or len(version["pages"]) != version["page_count"]:
        out.append(f"[pages] {name}: readers see {counts}, the key says {version['page_count']}")
        return out
    title = (pdf.reader.metadata or {}).get("/Title")
    if title != version["pdf_title"]:
        out.append(f"[title] {name}: /Title is {title!r}, the key says {version['pdf_title']!r}")
    revisions: list[tuple[int, str]] = []
    for fact in version["pages"]:
        number = fact["page"]
        label = f"{name} page {number}"
        plumber_page, ref_page, fium_page = pdf.plumber.pages[number - 1], pdf.reader.pages[number - 1], pdf.pdfium[number - 1]
        # sizes, by all three readers
        for reader_name, (w, h) in (
            ("pdfplumber", (float(plumber_page.width), float(plumber_page.height))),
            ("pypdf", (float(ref_page.mediabox.width), float(ref_page.mediabox.height))),
            ("pdfium", fium_page.get_size()),
        ):
            if abs(w - fact["width_pt"]) > 0.02 or abs(h - fact["height_pt"]) > 0.02:
                out.append(f"[size] {label}: {reader_name} sees {w:.2f} x {h:.2f}, the key says {fact['width_pt']} x {fact['height_pt']}")
        if _format(fact["width_pt"], fact["height_pt"]) != fact["format"]:
            out.append(f"[size] {label}: {fact['width_pt']} x {fact['height_pt']} is not {fact['format']}")
        # text layer / scan
        chars = len(plumber_page.chars)
        fium_chars = fium_page.get_textpage().count_chars()
        if fact["text_layer"]:
            if chars == 0 or fium_chars == 0:
                out.append(f"[scan] {label}: the key says a text layer, readers see {chars} / {fium_chars} characters")
            if plumber_page.images:
                out.append(f"[scan] {label}: a vector page carries an image")
        else:
            if chars or fium_chars or (ref_page.extract_text() or "").strip():
                out.append(f"[scan] {label}: the key says no text layer, readers see {chars} / {fium_chars} characters")
            if len(plumber_page.images) != 1 or len(plumber_page.lines) + len(plumber_page.rects) + len(plumber_page.curves):
                out.append(f"[scan] {label}: a scan must be one image and no vector content")
        # stamp fields and the title
        if fact["text_layer"]:
            text = _stamp_text(plumber_page, fact["stamp_bbox"])
            for field_name, value in fact["stamp"].items():
                if not has_phrase(norm(text), value):
                    out.append(f"[stamp] {label}: stamp {field_name} {value!r} is not in the stamp zone ({text[:60]!r}...)")
            if fact["title"] != fact["stamp"]["title"]:
                out.append(f"[stamp] {label}: the key's title differs from its own stamp title")
            if fact["stamp"]["designation"] != version["designation"]:
                out.append(f"[stamp] {label}: designation differs from the version's")
            revision = fact["stamp"]["revision"]
            if revision.startswith("Изм."):
                revisions.append((int(revision[4:]), fact["stamp"]["date"]))
        # annotations
        annots = ref_page.get("/Annots") or []
        annots = [a.get_object() for a in annots]
        if len(annots) != len(fact["annotations"]):
            out.append(f"[annots] {label}: pypdf sees {len(annots)} annotations, the key says {len(fact['annotations'])}")
        else:
            for found, wanted in zip(annots, fact["annotations"]):
                subtype = str(found.get("/Subtype"))
                expected = {"text": "/Text", "square": "/Square"}[wanted["kind"]]
                rect = [round(float(v), 2) for v in found["/Rect"]]
                contents = str(found.get("/Contents"))
                if subtype != expected or rect != wanted["rect"] or contents != wanted["contents"]:
                    out.append(f"[annots] {label}: annotation {wanted['id']} reads as {subtype} {rect} {contents!r}")
    if revisions:
        top = max(revisions)
        if f"Изм.{top[0]}" != version["label"] or top[1] != version["date"]:
            out.append(f"[version] {name}: the highest stamp revision is Изм.{top[0]} {top[1]}, the key says {version['label']} {version['date']}")
    return out


def _content_bytes(pdf: Pdf, page_number: int) -> bytes:
    contents = pdf.reader.pages[page_number - 1].get_contents()
    return contents.get_data() if contents is not None else b""


def _image_bytes(pdf: Pdf, page_number: int) -> bytes:
    page = pdf.reader.pages[page_number - 1]
    images = page.images
    return b"".join(i.data for i in images)


def _same_page(a: Pdf, pa: int, b: Pdf, pb: int) -> bool:
    page_a, page_b = a.reader.pages[pa - 1], b.reader.pages[pb - 1]
    if [float(v) for v in page_a.mediabox] != [float(v) for v in page_b.mediabox]:
        return False
    if _content_bytes(a, pa) != _content_bytes(b, pb) or _image_bytes(a, pa) != _image_bytes(b, pb):
        return False
    notes_a = [(str(x.get_object().get("/Subtype")), str(x.get_object().get("/Contents")), [float(v) for v in x.get_object()["/Rect"]])
               for x in page_a.get("/Annots") or []]
    notes_b = [(str(x.get_object().get("/Subtype")), str(x.get_object().get("/Contents")), [float(v) for v in x.get_object()["/Rect"]])
               for x in page_b.get("/Annots") or []]
    return notes_a == notes_b


def _check_transition(a: Pdf, b: Pdf, transition: dict, key: dict, pdfs: dict[str, Pdf]) -> list[str]:
    out: list[str] = []
    tid = transition["id"]
    counts = {s: 0 for s in key["statuses"]}
    for sheet in transition["sheets"]:
        label = f"{tid} {sheet['sheet_id']}"
        status = sheet["expected_status"]
        if status not in key["statuses"]:
            out.append(f"[status] {label}: {status!r} is not one of the six statuses")
            continue
        counts[status] += 1
        for channel in sheet["channels_with_differences"] + sheet["channels_without_differences"]:
            if channel not in key["channels"]:
                out.append(f"[status] {label}: {channel!r} is not one of the eight channels")
        if set(sheet["channels_with_differences"]) & set(sheet["channels_without_differences"]):
            out.append(f"[status] {label}: a channel is both required and forbidden")
        if status == "removed":
            if sheet["from_page"] is None or sheet["to_page"] is not None:
                out.append(f"[status] {label}: a removed sheet has a page only on the old side")
            continue
        if status == "added":
            if sheet["from_page"] is not None or sheet["to_page"] is None:
                out.append(f"[status] {label}: an added sheet has a page only on the new side")
            continue
        from_page, to_page = sheet["from_page"], sheet.get("to_page")
        if sheet["relation"] == "split":
            out += _check_split(a, b, sheet, label)
            continue
        plumber_a = a.plumber.pages[from_page - 1]
        plumber_b = b.plumber.pages[to_page - 1]
        # identical page claim
        same = _same_page(a, from_page, b, to_page)
        if sheet["byte_identical_page"] != same:
            out.append(f"[identical] {label}: the key says byte_identical_page={sheet['byte_identical_page']}, the pages say {same}")
        if status == "same" and not same:
            out.append(f"[identical] {label}: authored `same` but the page content differs")
        # text changes
        for change in sheet["text_changes"]:
            kind = change["kind"]
            if kind in ("text_changed", "text_removed", "text_moved"):
                if not at(plumber_a, change["bbox_before"], change["before"]):
                    out.append(f"[text_change] {label}: {change['id']} before {change['before']!r} is not at its box on page {from_page}")
            if kind in ("text_changed", "text_added", "text_moved"):
                if not at(plumber_b, change["bbox_after"], change["after"]):
                    out.append(f"[text_change] {label}: {change['id']} after {change['after']!r} is not at its box on page {to_page}")
            if kind == "text_added" and at(plumber_a, change["bbox_after"], change["after"]):
                out.append(f"[text_change] {label}: {change['id']} is said to be added but page {from_page} already has it there")
            if kind == "text_removed" and at(plumber_b, change["bbox_before"], change["before"]):
                out.append(f"[text_change] {label}: {change['id']} is said to be removed but page {to_page} still has it there")
            if kind == "text_moved" and at(plumber_b, change["bbox_before"], change["before"]):
                out.append(f"[text_change] {label}: {change['id']} is said to have moved but is still at its old box")
            if kind == "text_changed" and at(plumber_a, change["bbox_before"], change["after"]):
                out.append(f"[text_change] {label}: {change['id']} already read {change['after']!r} on the old page")
        # graphics
        for change in sheet["graphic_changes"]:
            kind = change["kind"]
            if kind == "graphic_added":
                if not objects_near(plumber_b, change["bbox_after"]):
                    out.append(f"[style] {label}: added {change['id']} is not on page {to_page}")
                if objects_near(plumber_a, change["bbox_after"]):
                    out.append(f"[style] {label}: added {change['id']} is already on page {from_page}")
            elif kind == "graphic_color":
                before = [o for o in objects_near(plumber_a, change["bbox_before"]) if _color_close(o["stroking_color"], change["before"])]
                after = [o for o in objects_near(plumber_b, change["bbox_after"]) if _color_close(o["stroking_color"], change["after"])]
                if not before or not after:
                    out.append(f"[style] {label}: {change['id']} colour {change['before']} -> {change['after']} is not what the readers see")
            elif kind == "graphic_width":
                before = [o for o in objects_near(plumber_a, change["bbox_before"]) if abs(o["linewidth"] - change["before"]) < 0.01]
                after = [o for o in objects_near(plumber_b, change["bbox_after"]) if abs(o["linewidth"] - change["after"]) < 0.01]
                if not before or not after:
                    out.append(f"[style] {label}: {change['id']} width {change['before']} -> {change['after']} is not what the readers see")
        # annotations
        notes = sheet["annotation_changes"]
        found_a = len(a.reader.pages[from_page - 1].get("/Annots") or [])
        found_b = len(b.reader.pages[to_page - 1].get("/Annots") or [])
        if found_b - found_a != len(notes["added"]) - len(notes["removed"]):
            out.append(f"[annots] {label}: the pages hold {found_a} and {found_b} annotations, the key's change is +{len(notes['added'])} -{len(notes['removed'])}")
        # scan pairs
        if "NO_TEXT_LAYER" in sheet["reasons"]:
            if plumber_b.chars or not plumber_a.chars:
                out.append(f"[scan] {label}: a NO_TEXT_LAYER pair needs a text page and then an image-only page")
        # duplicates
        if sheet.get("to_pages"):
            first, second = sheet["to_pages"]
            if not _same_page(b, first, b, second):
                out.append(f"[duplicate] {label}: pages {first} and {second} of {transition['to']} are not identical")
            if (b.plumber.pages[first - 1].extract_text() or "") != (b.plumber.pages[second - 1].extract_text() or ""):
                out.append(f"[duplicate] {label}: the duplicate pages read differently")
        # specification table
        if "spec_positions" in sheet:
            out += _check_spec(a, from_page, b, to_page, sheet["spec_positions"], label)
    if transition["status_counts"] != counts:
        out.append(f"[status] {tid}: status_counts {transition['status_counts']} differ from the sheets {counts}")
    if "permit" in transition:
        out += _check_permit(b, transition, pdfs, key)
    return out


def _table(page, bbox: list[float]) -> list[list[str]]:
    cropped = page.crop(pdf_box(page, bbox, 0.5))
    rows = cropped.extract_table({"vertical_strategy": "lines", "horizontal_strategy": "lines"}) or []
    return [[(cell or "").replace("\n", " ").strip() for cell in row] for row in rows]


def _check_spec(a: Pdf, pa: int, b: Pdf, pb: int, spec: dict, label: str) -> list[str]:
    out: list[str] = []
    bbox = spec["table_bbox"]
    before = {r[0]: r for r in _table(a.plumber.pages[pa - 1], bbox)[1:] if r[0]}
    after = {r[0]: r for r in _table(b.plumber.pages[pb - 1], bbox)[1:] if r[0]}
    header = _table(b.plumber.pages[pb - 1], bbox)[0]
    if header != spec["columns"]:
        out.append(f"[spec] {label}: the table header reads {header}, the key says {spec['columns']}")

    def keyed(rows: list[dict]) -> dict[str, list[str]]:
        return {r["position"]: [r["position"], r["designation"], r["name"], r["quantity"], r["mass"]] for r in rows}

    for side, read, wanted in (("before", before, keyed(spec["positions_before"])),
                               ("after", after, keyed(spec["positions_after"]))):
        got = {p: row[:5] for p, row in read.items()}
        if got != wanted:
            out.append(f"[spec] {label}: the {side} table reads {got}, the key says {wanted}")
    added = sorted(set(after) - set(before), key=int)
    removed = sorted(set(before) - set(after), key=int)
    changed = []
    for position in sorted(set(before) & set(after), key=int):
        for index, field_name in enumerate(("position", "designation", "name", "quantity", "mass")):
            if index and before[position][index] != after[position][index]:
                changed.append((position, field_name, before[position][index], after[position][index]))
    if added != [r["position"] for r in spec["added"]]:
        out.append(f"[spec] {label}: added positions read {added}, the key says {[r['position'] for r in spec['added']]}")
    if removed != [r["position"] for r in spec["removed"]]:
        out.append(f"[spec] {label}: removed positions read {removed}, the key says {[r['position'] for r in spec['removed']]}")
    if changed != [(c["position"], c["field"], c["before"], c["after"]) for c in spec["changed"]]:
        out.append(f"[spec] {label}: changed positions read {changed}, the key says {spec['changed']}")
    return out


def _check_permit(b: Pdf, transition: dict, pdfs: dict[str, Pdf], key: dict) -> list[str]:
    out: list[str] = []
    permit = transition["permit"]
    carrier = next(s for s in transition["sheets"] if s["sheet_id"] == permit["carrier_sheet"])
    page = b.plumber.pages[carrier["to_page"] - 1]
    rows = _table(page, permit["table_bbox"])
    if not rows or rows[0] != permit["columns"]:
        out.append(f"[permit] the permit table header reads {rows[:1]}, the key says {permit['columns']}")
    read = [tuple(r) for r in rows[1:]]
    wanted = [(d["change_no"], d["sheet_no"], d["text"]) for d in permit["declared"]]
    if read != wanted:
        out.append(f"[permit] the permit table reads {read}, the key says {wanted}")
    if permit["table_title"] not in (page.extract_text() or ""):
        out.append(f"[permit] the title {permit['table_title']!r} is not on page {carrier['to_page']}")
    previous = pdfs[transition["from"]]
    if permit["table_title"] in (previous.plumber.pages[carrier["from_page"] - 1].extract_text() or ""):
        out.append("[permit] the previous version already carries the permit table")
    by_id = {s["sheet_id"]: s for s in transition["sheets"]}
    classes: dict[str, list[str]] = {k: [] for k in permit["classes"]}
    for entry in permit["declared"]:
        sheet = by_id[entry["sheet_id"]]
        if entry["reconciliation"] not in classes:
            out.append(f"[permit] entry {entry['entry']}: unknown class {entry['reconciliation']!r}")
            continue
        classes[entry["reconciliation"]].append(entry["sheet_id"])
        content = [c for c in sheet["text_changes"] + sheet["graphic_changes"] if c["zone"] != "stamp"]
        found = bool(content)
        scan = "NO_TEXT_LAYER" in sheet["reasons"]
        expected = ("declared_unverifiable_scan" if scan else "declared_and_found" if found else "declared_not_found")
        if entry["reconciliation"] != expected:
            out.append(f"[permit] entry {entry['entry']}: class {entry['reconciliation']} but the sheet's changes say {expected}")
    for item in permit["found_not_declared"]:
        classes["found_not_declared"].append(item["sheet_id"])
        if item["sheet_id"] in {d["sheet_id"] for d in permit["declared"]}:
            out.append(f"[permit] {item['sheet_id']} is both declared and found-not-declared")
        if not item["text_change_ids"]:
            out.append(f"[permit] found_not_declared {item['sheet_id']} has no evidence")
    if classes != permit["classes"]:
        out.append(f"[permit] classes {permit['classes']} are not what the entries add up to {classes}")
    declared_sheets = {d["sheet_id"] for d in permit["declared"]}
    for sheet in transition["sheets"]:
        content = [c for c in sheet["text_changes"] + sheet["graphic_changes"] if c["zone"] != "stamp"]
        if content and sheet["sheet_id"] not in declared_sheets and sheet["sheet_id"] != permit["carrier_sheet"]:
            if sheet["sheet_id"] not in permit["classes"]["found_not_declared"]:
                out.append(f"[permit] {sheet['sheet_id']} changed and is neither declared nor listed as found-not-declared")
    return out


def _check_split(a: Pdf, b: Pdf, sheet: dict, label: str) -> list[str]:
    out: list[str] = []
    old_page = a.plumber.pages[sheet["from_page"] - 1]
    if sheet["to_pages"] != [p["to_page"] for p in sheet["parts"]]:
        out.append(f"[split] {label}: to_pages and parts disagree")
    x_covered: list[tuple[float, float]] = []
    for part in sheet["parts"]:
        new_page = b.plumber.pages[part["to_page"] - 1]
        if _format(float(new_page.width), float(new_page.height)) != part["format"]:
            out.append(f"[split] {label}: part page {part['to_page']} is not {part['format']}")
        shift = part["translation_x"]
        lo, hi = part["region_in_old_sheet_x"]
        x_covered.append((lo, hi))
        # every vector object of the part, moved back, is an object of the old page inside the region
        part_objects = [o for o in (*new_page.lines, *new_page.rects, *new_page.curves)
                        if not _in_stamp_or_frame(new_page, o)]
        old_objects = [o for o in (*old_page.lines, *old_page.rects, *old_page.curves)
                       if lo - 0.5 <= o["x0"] and o["x1"] <= hi + 0.5 and not _in_stamp_or_frame(old_page, o)]
        moved_back = sorted((_q(o["x0"] - shift), _q(o["top"]), _q(o["x1"] - shift), _q(o["bottom"])) for o in part_objects)
        in_region = sorted((_q(o["x0"]), _q(o["top"]), _q(o["x1"]), _q(o["bottom"])) for o in old_objects)
        if moved_back != in_region:
            out.append(f"[split] {label}: part {part['sheet_no']} is not its region of the old sheet "
                       f"({len(moved_back)} objects against {len(in_region)})")
        old_words = sorted((w["text"], _q(w["x0"]), _q(w["top"])) for w in old_page.extract_words()
                           if lo <= w["x0"] and w["x1"] <= hi and w["top"] < float(old_page.height) - 175)
        new_words = sorted((w["text"], _q(w["x0"] - shift), _q(w["top"])) for w in new_page.extract_words()
                           if w["top"] < float(new_page.height) - 175)
        if old_words != new_words:
            out.append(f"[split] {label}: the words of part {part['sheet_no']} are not those of its region")
        if part["content_changes_in_region"]:
            out.append(f"[split] {label}: the key lists content changes inside a region")
    if not x_covered or x_covered[0][0] > 0.5 or x_covered[-1][1] < float(old_page.width) - 0.5:
        out.append(f"[split] {label}: the parts do not span the old sheet")
    if not sheet["parts_cover_whole_old_sheet"]:
        out.append(f"[split] {label}: parts_cover_whole_old_sheet is false")
    return out


def _q(value: float) -> float:
    """A coordinate to one decimal, nudged so that a value that is exact in the key never rounds down."""
    return round(value + 1e-6, 1)


def _in_stamp_or_frame(page, obj: dict) -> bool:
    """Frame and title-block objects: near the sheet edge, or inside the 185 x 55 mm stamp."""
    height = float(page.height)
    top, bottom = obj["top"], obj["bottom"]
    width = float(page.width)
    on_frame = obj["x0"] < 58.0 or obj["x1"] > width - 16.0 or top < 16.0 or bottom > height - 16.0
    in_stamp = obj["x0"] >= width - 15.0 - 524.5 and bottom > height - 171.0
    return bool(on_frame or in_stamp)


def _check_identity(pdfs: dict[str, Pdf], key: dict) -> list[str]:
    out: list[str] = []
    versions = {v["id"]: v for v in key["versions"]}
    for sheet in key["sheet_identity"]:
        for version_id, pages in sheet["pages"].items():
            if version_id not in pdfs:
                continue
            for number in pages:
                fact = versions[version_id]["pages"][number - 1]
                if fact["sheet_id"] != sheet["sheet_id"]:
                    out.append(f"[identity] {version_id} page {number} is {fact['sheet_id']} in the pages, {sheet['sheet_id']} in the identity table")
                    continue
                if not fact["text_layer"]:
                    continue
                page = pdfs[version_id].plumber.pages[number - 1]
                text = _stamp_text(page, fact["stamp_bbox"])
                if not has_phrase(norm(text), sheet["title"]) and fact["role"] == "regular":
                    out.append(f"[identity] {version_id} page {number}: the stamp does not carry the title {sheet['title']!r}")
                if not has_phrase(norm(text), fact["sheet_no"]):
                    out.append(f"[identity] {version_id} page {number}: the stamp does not carry sheet number {fact['sheet_no']}")
                number_ok = fact["sheet_no"] == sheet["sheet_no"] or (
                    fact["role"].startswith("split") and fact["sheet_no"].startswith(sheet["sheet_no"] + "."))
                if not number_ok:
                    out.append(f"[identity] {version_id} page {number}: sheet number {fact['sheet_no']} is not sheet {sheet['sheet_no']}'s")
    seen: set[tuple[str, int]] = set()
    for sheet in key["sheet_identity"]:
        for version_id, pages in sheet["pages"].items():
            for number in pages:
                if (version_id, number) in seen:
                    out.append(f"[identity] {version_id} page {number} belongs to two sheets")
                seen.add((version_id, number))
    for version in key["versions"]:
        for number in range(1, version["page_count"] + 1):
            if (version["id"], number) not in seen:
                out.append(f"[identity] {version['id']} page {number} belongs to no sheet")
    return out


# --------------------------------------------------------------------------------------
# SP-1
# --------------------------------------------------------------------------------------


def passport_of(title: str) -> tuple[str, str, str]:
    """Type, building and level from a title «Тип. Корпус N. Уровень», read independently of the generator."""
    parts = [p.strip() for p in title.split(". ")]
    return parts[0], parts[1], ". ".join(parts[2:])


def check_sp1(files: Mapping[str, bytes], key: dict) -> list[str]:
    out: list[str] = []
    docs: dict[str, Pdf] = {}
    try:
        for doc in key["documents"]:
            data = files.get(doc["file"])
            if data is None:
                out.append(f"[files] {doc['file']} is missing")
                continue
            if hashlib.sha256(data).hexdigest() != doc["sha256"] or len(data) != doc["bytes"]:
                out.append(f"[sha] {doc['file']} does not match the key's digest")
            pdf = Pdf(data)
            docs[doc["name"]] = pdf
            counts = {len(pdf.reader.pages), len(pdf.plumber.pages), len(pdf.pdfium)}
            if counts != {doc["page_count"]}:
                out.append(f"[pages] {doc['file']}: readers see {counts}, the key says {doc['page_count']}")
            title = (pdf.reader.metadata or {}).get("/Title")
            if title != doc["pdf_title"]:
                out.append(f"[title] {doc['file']}: /Title is {title!r}")
        if out:
            return out

        by_id = {s["sheet_id"]: s for s in key["sheets"]}
        titles: dict[str, str] = {}
        for sheet in key["sheets"]:
            pdf = docs[sheet["document"]]
            page = pdf.plumber.pages[sheet["page"] - 1]
            label = f"sp1 {sheet['sheet_id']}"
            if abs(float(page.width) - sheet["width_pt"]) > 0.02 or abs(float(page.height) - sheet["height_pt"]) > 0.02:
                out.append(f"[size] {label}: pdfplumber sees {page.width} x {page.height}")
            if _format(float(page.width), float(page.height)) != sheet["format"]:
                out.append(f"[size] {label}: not {sheet['format']}")
            if not page.chars or pdf.pdfium[sheet["page"] - 1].get_textpage().count_chars() == 0:
                out.append(f"[scan] {label}: no text layer")
            text = _stamp_text(page, sheet["stamp_bbox"])
            for field_name, value in sheet["stamp"].items():
                if not has_phrase(norm(text), value):
                    out.append(f"[stamp] {label}: stamp {field_name} {value!r} is not in the stamp zone")
            titles[sheet["sheet_id"]] = sheet["stamp"]["title"]
            if sheet["passport"] != dict(zip(("type", "building", "level"), passport_of(sheet["stamp"]["title"]))):
                out.append(f"[links] {label}: the key's passport is not the one its title gives")
            for fragment in sheet["fragments"]:
                if not at(page, fragment["bbox"], fragment["text"]):
                    out.append(f"[fragments] {label}: fragment {fragment['key']} {fragment['text']!r} is not at its box")

        # links: exactly the pairs of old/new sheets that share a passport
        old = [s for s in key["sheets"] if s["side"] == "old"]
        new = [s for s in key["sheets"] if s["side"] == "new"]
        derived = sorted((o["sheet_id"], n["sheet_id"]) for o in old for n in new
                         if passport_of(o["stamp"]["title"]) == passport_of(n["stamp"]["title"]))
        listed = sorted((link["old"], link["new"]) for link in key["sheet_links"])
        if derived != listed:
            out.append(f"[links] the passports pair {derived}, the key links {listed}")
        paired_old = {o for o, _ in listed}
        paired_new = {n for _, n in listed}
        want_old = sorted(s["sheet_id"] for s in old if s["sheet_id"] not in paired_old)
        want_new = sorted(s["sheet_id"] for s in new if s["sheet_id"] not in paired_new)
        got_old = sorted(x["sheet_id"] for x in key["sheets_without_pair"]["old_only"])
        got_new = sorted(x["sheet_id"] for x in key["sheets_without_pair"]["new_only"])
        if want_old != got_old or want_new != got_new:
            out.append(f"[links] sheets without a pair are {want_old}/{want_new}, the key says {got_old}/{got_new}")
        for link in key["sheet_links"]:
            o, n = by_id[link["old"]], by_id[link["new"]]
            if (link["old_page"], link["new_page"]) != (o["page"], n["page"]) or (link["old_document"], link["new_document"]) != (o["document"], n["document"]):
                out.append(f"[links] {link['old']}->{link['new']}: pages or documents disagree with the sheet table")

        # stage and designation differences read from the pages
        for link in key["sheet_links"]:
            o, n = by_id[link["old"]], by_id[link["new"]]
            diffs = [{"field": f, "before": o["stamp"][f], "after": n["stamp"][f]}
                     for f in ("designation", "stage", "sheet_no", "revision", "date") if o["stamp"][f] != n["stamp"][f]]
            if diffs != link["stamp_differences"]:
                out.append(f"[links] {link['old']}->{link['new']}: stamp differences read {diffs}")

        out += _check_fragments(docs, key, by_id)
    finally:
        for pdf in docs.values():
            pdf.close()
    return out


def _page_text(docs: dict[str, Pdf], sheet: dict) -> str:
    return norm(docs[sheet["document"]].plumber.pages[sheet["page"] - 1].extract_text() or "")


def _check_fragments(docs: dict[str, Pdf], key: dict, by_id: dict[str, dict]) -> list[str]:
    out: list[str] = []
    classes = key["text_fragments"]
    new_text_all = " \n".join(_page_text(docs, s) for s in key["sheets"] if s["side"] == "new")
    for record in classes["changed"]:
        o, n = by_id[record["old_sheet"]], by_id[record["new_sheet"]]
        page_o, page_n = docs[o["document"]].plumber.pages[o["page"] - 1], docs[n["document"]].plumber.pages[n["page"] - 1]
        if record["before"] == record["after"]:
            out.append(f"[fragments] changed {record['key']} has identical before and after")
        if not at(page_o, record["bbox_before"], record["before"]) or not at(page_n, record["bbox_after"], record["after"]):
            out.append(f"[fragments] changed {record['key']}: before/after are not at their boxes")
        if norm(record["after"]) in _page_text(docs, o) or norm(record["before"]) in _page_text(docs, n):
            out.append(f"[fragments] changed {record['key']}: the other text is also on the other sheet")
    for record in classes["unchanged"]:
        o, n = by_id[record["old_sheet"]], by_id[record["new_sheet"]]
        page_o, page_n = docs[o["document"]].plumber.pages[o["page"] - 1], docs[n["document"]].plumber.pages[n["page"] - 1]
        if record["before"] != record["after"] or not at(page_o, record["bbox_before"], record["before"]) \
                or not at(page_n, record["bbox_after"], record["after"]):
            out.append(f"[fragments] unchanged {record['key']} is not the same text on both sheets")
    for record in classes["added"]:
        n = by_id[record["new_sheet"]]
        page_n = docs[n["document"]].plumber.pages[n["page"] - 1]
        if not at(page_n, record["bbox_after"], record["after"]):
            out.append(f"[fragments] added {record['key']} is not on {record['new_sheet']}")
        old_text_all = " \n".join(_page_text(docs, s) for s in key["sheets"] if s["side"] == "old")
        if norm(record["after"]) in old_text_all:
            out.append(f"[fragments] added {record['key']} {record['after']!r} is already on an old sheet")
    for record in classes["removed"]:
        o = by_id[record["old_sheet"]]
        page_o = docs[o["document"]].plumber.pages[o["page"] - 1]
        if not at(page_o, record["bbox_before"], record["before"]):
            out.append(f"[fragments] removed {record['key']} is not on {record['old_sheet']}")
        if norm(record["before"]) in new_text_all:
            out.append(f"[fragments] removed {record['key']} {record['before']!r} is still on a new sheet")
    for record in classes["moved_between_sheets"]:
        o, n = by_id[record["old_sheet"]], by_id[record["new_sheet"]]
        page_o, page_n = docs[o["document"]].plumber.pages[o["page"] - 1], docs[n["document"]].plumber.pages[n["page"] - 1]
        if not at(page_o, record["bbox_before"], record["text"]) or not at(page_n, record["bbox_after"], record["text"]):
            out.append(f"[fragments] moved {record['key']} is not at both boxes")
        if record["old_sheet"] == record["new_sheet"]:
            out.append(f"[fragments] moved {record['key']} does not change sheet")
        linked_new = [l["new"] for l in key["sheet_links"] if l["old"] == record["old_sheet"]]
        if record["new_sheet"] in linked_new:
            out.append(f"[fragments] moved {record['key']} moved onto the linked sheet, so it did not move")
    return out
