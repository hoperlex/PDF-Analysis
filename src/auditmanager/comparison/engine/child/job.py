"""The comparison job of the engine's child: one pair of pages, rendered and compared a band of rows at a time.

`CMP-ENGINE-01`, ADR-0025 decisions 8 and 9. The job is the port of ``engine.compute_sheet_pair``
(``engine.py:477-1027``) with the differences the notes in the other modules give: the canvas is the page of A; the
pages are rendered through :mod:`.render` a band at a time; the planes live in a :class:`~.planes.PlaneStore`; the words
and the zones come from the page profile; there is no stream-level separation of overlays.

Order of work (each step names what it keeps in memory):

1. zones and registration, from the profile alone (words, long lines, the 36 dpi masks);
2. A's bands are rendered and kept compressed, then A's document is closed;
3. B's bands are rendered through the registration matrix, each is compared with A's band, and the core rows of the
   layers go into the plane store (a dozen planes of one bit a pixel);
4. words, moved blocks and text changes;
5. the regions: grouping on the reduced canvas, classes, the checks on windows;
6. the channels, the status, the eight planes of the mask and the ``result``.

It writes ``outcome.json`` (see :mod:`.result`) and, if there is anything to show, ``mask.bin`` (the blob, format 1)
into the output directory, and returns the small facts for the answer line of the child.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any

import cv2
import numpy

try:  # as part of the product (the worker, the tests) ...
    from .. import mask_codec
except ImportError:  # ... and in the child program, which loads the codec beside this package
    from . import _mask_codec as mask_codec  # type: ignore[no-redef]

try:  # as part of the product (the worker, the tests) ...
    from ...specification import diff as spec_diff, table as spec_table
except ImportError:  # ... and in the child program, which loads the specification package beside this one (``_amc_spec``)
    import importlib

    spec_diff = importlib.import_module("_amc_spec.diff")
    spec_table = importlib.import_module("_amc_spec.table")

from . import annotations as annotations_module
from . import blocks, regions as regions_module, settings, textdiff, zones as zones_module
from . import status as st
from .geometry import Canvas, bands, invert, matrix_to_pdf
from .layers import compute_band
from .planes import PlaneStore
from .registration import register
from .render import BandStore, open_page, render_rows
from .result import build_result, difference, text_change
from .words import (
    DATE_RE,
    center,
    classify_kind,
    compare_words,
    in_rects,
    make_words,
    norm,
    reading_order_words,
    rect_through,
    warning_lines,
)

__all__ = ["run", "spec_positions_channel"]

#: The planes the band loop fills (the others are made later from these).
_BAND_PLANES = ("dark_a", "dark_b", "any_a", "any_b", "a_only", "b_only", "light_a", "light_b", "color", "style",
                "noise", "within_tol")
#: The planes of the mask blob, in the order of ``ComparisonLayer`` (``mask_codec.LAYERS``), and where each comes from.
_MASK_ORDER = ("main", "light_elements", "color_change", "line_style", "moved", "within_tolerance", "noise", "service_zones")
SHIFT_CLASSES = ("text_moved", "block_moved", "shifted")


def _vm_peak_mib() -> int:
    """The child's peak address space so far, MiB (the quantity ``RLIMIT_AS`` limits)."""
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("VmPeak:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def _load(settings_: dict[str, Any]) -> dict[str, Any]:
    with open(str(settings_["inputs"]), encoding="utf-8") as handle:
        return json.load(handle)


def _mask36(page: dict[str, Any]) -> Any:
    info = page.get("mask36")
    if not info:
        return None
    with open(info["file"], "rb") as handle:
        data = handle.read()
    rows = numpy.frombuffer(data, dtype=numpy.uint8).reshape(info["height_px"], info["row_bytes"])
    return numpy.ascontiguousarray(numpy.unpackbits(rows, axis=1)[:, : info["width_px"]])


def _lines(page: dict[str, Any]) -> Any:
    info = page.get("lines")
    if not info:
        return None
    return numpy.fromfile(info["file"], dtype=numpy.float32).reshape(-1, 4)


def _spec_flow(page: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The positions of the specification table of one page, or ``None`` and the reason there are none (``CMP-VC-SPEC-01``).

    Read from the page's own words, its vector lines (only the long axis-parallel ones can be a rule of the table, which also keeps
    a page of 187 000 lines from becoming a Python list) and its title-block zone, in the frame of the page: the pure parser of
    :mod:`auditmanager.comparison.specification.table`. A table with no position is no positions: a parser that read nothing
    must not claim that everything was removed."""
    lines = _lines(page)
    rules: list[list[float]] = []
    if lines is not None and len(lines):
        dx = numpy.abs(lines[:, 2] - lines[:, 0])
        dy = numpy.abs(lines[:, 3] - lines[:, 1])
        rules = lines[((dx < 0.8) & (dy > 8.0)) | ((dy < 0.8) & (dx > 8.0))].tolist()
    parsed = spec_table.parse_page(page["words"], rules, float(page["width_pt"]), float(page["height_pt"]), page.get("stamp_zone"))
    if parsed is None:
        return None, "таблица спецификации не найдена"
    if not parsed.get("parsed"):
        return None, str(parsed.get("reason") or "таблица не разобрана")
    flow = spec_table.assemble([{"page": 1, "rows": parsed["rows"]}])
    if not flow["items"]:
        return None, "в таблице нет позиций"
    return flow, ""


def spec_positions_channel(a: dict[str, Any], b: dict[str, Any], main_diffs: int) -> dict[str, Any]:
    """The channel ``spec_positions`` of a pair in which one page at least is a specification sheet (``CMP-VC-SPEC-01``).

    * The graphics, the colour and the text have no difference: ``checked(0)``. The positions are read from the same words, so they
      cannot differ (the original's own rule, ``engine.py:997``).
    * Otherwise the positions of **both** pages are read and compared order-independently; ``checked`` with the number of
      positions changed, added or removed (a renumbered position and a position that only changed its section are not counted, as
      the original does not count them, ``jobs.py:857``). A page is read alone here, so no boundary at a page break can be unclear
      (``spec.py:312``); the version-wide read of ``getComparisonSheetPairSpecPositions`` is where ``unclear`` appears.
    * A page with no readable positions leaves the channel ``unchecked`` with the reason, never ``checked``: the pair is then
      ``needs_review`` or ``different`` by the other channels, never ``same`` (the status rules).
    """
    if main_diffs == 0:
        return st.checked(0)
    flow_a, why_a = _spec_flow(a)
    flow_b, why_b = _spec_flow(b)
    if flow_a is None or flow_b is None:
        side, why = ("A", why_a) if flow_a is None else ("B", why_b)
        return st.unchecked(f"позиции спецификации не прочитаны (лист {side}): {why}")
    totals = spec_diff.compare(flow_a["items"], flow_b["items"])["totals"]
    return st.checked(totals["changed"] + totals["added"] + totals["removed"])


def _part_area(mask36: Any, zones_b: list[list[float]], m: Any) -> list[float] | None:
    """The extent of the content of B outside its service zones, in the frame of A, with 3 mm to spare (``engine.py:461-474``)."""
    if mask36 is None:
        return None
    k = settings.MASK_DPI / 72.0
    mk = mask36.copy()
    for z in zones_b:
        mk[max(0, int(z[1] * k)) : int(z[3] * k) + 1, max(0, int(z[0] * k)) : int(z[2] * k) + 1] = 0
    ys, xs = numpy.nonzero(mk)
    if not len(xs):
        return None
    pad = 3 * 72 / 25.4
    rb = [xs.min() / k - pad, ys.min() / k - pad, (xs.max() + 1) / k + pad, (ys.max() + 1) / k + pad]
    return rect_through(m, rb)


def _ink_outside(mask36: Any, m: Any, width_pt: float, height_pt: float) -> int:
    """Pixels of ink of B's 36 dpi mask that, carried onto A, fall more than ``OUTSIDE_CANVAS_PT`` outside A's canvas:
    what the canvas of A does not compare."""
    if mask36 is None:
        return 0
    ys, xs = numpy.nonzero(mask36)
    if not len(xs):
        return 0
    if len(xs) > 50_000:
        step = len(xs) // 50_000 + 1
        ys, xs = ys[::step], xs[::step]
    k = 72.0 / settings.MASK_DPI
    px, py = (xs + 0.5) * k, (ys + 0.5) * k
    tx = m[0][0] * px + m[0][1] * py + m[0][2]
    ty = m[1][0] * px + m[1][1] * py + m[1][2]
    d = settings.OUTSIDE_CANVAS_PT
    outside = (tx < -d) | (ty < -d) | (tx > width_pt + d) | (ty > height_pt + d)
    return int(outside.sum())


def _rects_px(canvas: Canvas, rects: list[list[float]]) -> list[list[int]]:
    return [canvas.px(r) for r in rects]


def run(job: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    early: dict[str, int] = {}
    inputs = _load(job)
    early["inputs"] = _vm_peak_mib()
    out_dir = str(job["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    a, b = inputs["a"], inputs["b"]
    reasons: list[str] = list(inputs.get("reasons") or ())
    part_kind = inputs.get("part")
    tol_pt = float(inputs.get("tolerance_pt") or settings.TOLERANCE_PT)
    clock = {"analysis_deadline": time.process_time() + settings.REGION_ANALYSIS_SECONDS}
    budget_spent = False

    canvas = Canvas(float(a["width_pt"]), float(a["height_pt"]), int(inputs["dpi"]))
    width, height = canvas.width_px, canvas.height_px
    if width * height > 40_000_000:
        raise PageTooLarge(float(a["width_pt"]), float(a["height_pt"]))
    mm_px = canvas.dpi / 25.4

    # 1. zones and registration, from the profile alone ---------------------------------------
    mask_a, mask_b = _mask36(a), _mask36(b)
    zones_a = zones_module.page_zones(
        make_words(a["words"]), a["width_pt"], a["height_pt"], a["frame_segments"], a.get("stamp_zone"),
        bool(a.get("stamp")), mask_a)
    zones_b = zones_module.page_zones(
        make_words(b["words"]), b["width_pt"], b["height_pt"], b["frame_segments"], b.get("stamp_zone"),
        bool(b.get("stamp")), mask_b)
    early["zones"] = _vm_peak_mib()
    reg = register(a["words"], b["words"], [z["bbox"] for z in zones_a], [z["bbox"] for z in zones_b], mask_a, mask_b,
                   settings.MASK_DPI, _lines(a), _lines(b), crop=part_kind == "split")
    early["registration"] = _vm_peak_mib()
    m = numpy.array(reg["matrix"], dtype=numpy.float64)
    inv = invert(m)
    if not reg["reliable"]:
        reasons.append("ALIGNMENT_UNRELIABLE")
    elif reg.get("dice36") is not None and reg["dice36"] < settings.ALIGN_MIN_DICE:
        reasons.append("ALIGNMENT_PARTIAL")
    if _ink_outside(mask_b, m, canvas.width_pt, canvas.height_pt) >= 3:
        reasons.append("PARTIAL_COVERAGE")

    zone_rects_a_pt = [z["bbox"] for z in zones_a]
    zone_rects_b_in_a = [rect_through(m, z["bbox"]) for z in zones_b]
    zone_types = sorted({z["type"] for z in zones_a} | {z["type"] for z in zones_b})
    zone_px: dict[str, list[list[int]]] = {
        kind: _rects_px(canvas, [z["bbox"] for z in zones_a if z["type"] == kind]
                        + [rect_through(m, z["bbox"]) for z in zones_b if z["type"] == kind])
        for kind in zone_types
    }
    all_zone_px = [r for kind in zone_types for r in zone_px[kind]]
    part_rect_a = None
    if part_kind == "split":
        part_rect_a = _part_area(mask_b, [z["bbox"] for z in zones_b], m)
    part_px = [canvas.px(part_rect_a)] if part_rect_a is not None else None

    radius = max(1, int(round(tol_pt * canvas.s)))
    margin = 2 * radius + 10
    band_list = list(bands(width, height, pixels=settings.BAND_PIXELS, margin=margin))

    # 2. A's bands, compressed; then A's document is closed --------------------------------------
    scale = canvas.s
    store_a = BandStore()
    document, page = open_page(str(a["pdf"]), int(a["index"]))
    try:
        for i, band in enumerate(band_list):
            store_a.put(i, render_rows(page, [scale, 0, 0, scale, 0, 0], width, band.ext0, band.ext1))
    finally:
        page.close()
        document.close()
    t_render_a = time.monotonic() - started
    peaks: dict[str, int] = {**early, "start": _vm_peak_mib()}

    # 3. B's bands, the layers, the plane store ----------------------------------------------------
    planes = PlaneStore(width, height, (*_BAND_PLANES, "moved", "zones"))
    matrix_b = [scale * m[0][0], scale * m[1][0], scale * m[0][1], scale * m[1][1], scale * m[0][2], scale * m[1][2]]
    zone_stats = {kind: [0, 0] for kind in zone_types}
    totals = {"within": 0, "noise": 0, "ink_a_main": 0, "ink_a_in_part": 0}
    document, page = open_page(str(b["pdf"]), int(b["index"]))
    try:
        for i, band in enumerate(band_list):
            rows = band.ext1 - band.ext0
            bgr_b = render_rows(page, matrix_b, width, band.ext0, band.ext1)
            bgr_a = store_a.get(i)
            main_full = 1 - regions_module.rect_arrays(all_zone_px, rows, width, band.ext0)
            part = regions_module.rect_arrays(part_px, rows, width, band.ext0) if part_px is not None else None
            zone_masks = {kind: regions_module.rect_arrays(zone_px[kind], rows, width, band.ext0) for kind in zone_types}
            layers = compute_band(bgr_a, bgr_b, main_full, part, radius=radius,
                                  core=(band.core0 - band.ext0, band.core1 - band.ext0), zone_masks=zone_masks)
            lo, hi = band.core0 - band.ext0, band.core1 - band.ext0
            for name in _BAND_PLANES:
                planes.put_rows(name, band.core0, layers[name][lo:hi])
            planes.put_rows("zones", band.core0, (1 - main_full)[lo:hi])
            for kind, (diff_px, strict_px) in layers["zone_stats"].items():
                zone_stats[kind][0] += diff_px
                zone_stats[kind][1] += strict_px
            totals["within"] += layers["within_components"]
            totals["noise"] += layers["noise_components"]
            totals["ink_a_main"] += layers["ink_a_main"]
            totals["ink_a_in_part"] += layers["ink_a_in_part"]
            del bgr_a, bgr_b, layers
    finally:
        page.close()
        document.close()
    del store_a
    t_bands = time.monotonic() - started
    peaks["bands"] = _vm_peak_mib()

    part_info = None
    if part_kind == "split" and part_rect_a is not None:
        part_info = {
            "kind": "split", "area_a_pt": [round(v, 2) for v in part_rect_a],
            "coverage_a": round(totals["ink_a_in_part"] / totals["ink_a_main"], 4) if totals["ink_a_main"] else None,
            "reliable": bool(reg["reliable"]),
        }
    elif part_kind == "floors":
        part_info = {"kind": "floors", "reliable": bool(reg["reliable"])}

    marks: dict[str, float] = {"bands": time.monotonic() - started}

    # 4. words, moved blocks, text changes -------------------------------------------------------------
    words_a_all = make_words(a["words"])
    words_b_all = make_words(b["words"], m)
    words_all = words_a_all + words_b_all
    wa = [w for w in words_a_all if not in_rects(w["pt"], zone_rects_a_pt + zone_rects_b_in_a)]
    wb = [w for w in words_b_all if not in_rects(w["pt"], zone_rects_a_pt + zone_rects_b_in_a)]
    if part_rect_a is not None:
        wa = [w for w in wa if in_rects(w["pt"], [part_rect_a])]
        wb = [w for w in wb if in_rects(w["pt"], [part_rect_a])]
    same_pt = max(tol_pt, 0.25)
    words_cmp = compare_words(wa, wb, same_pt)

    moves = blocks.confirm(blocks.find(words_cmp), planes, canvas)
    for k, mv in enumerate(moves, 1):
        only_a_ids = {id(w) for w in words_cmp["only_a"]}
        only_b_ids = {id(w) for w in words_cmp["only_b"]}
        gone_a: set[int] = set()
        gone_b: set[int] = set()
        for wa_, wb_ in zip(mv["a_words"], mv["b_words"]):
            if id(wa_) in only_a_ids and id(wb_) in only_b_ids:
                gone_a.add(id(wa_))
                gone_b.add(id(wb_))
                d = math.hypot(*mv["vector"])
                words_cmp["moved"].append({"text": wa_["text"], "a_pt": wa_["pt"], "b_in_a_pt": wb_["pt"],
                                           "shift_pt": round(d, 2), "dir": wa_.get("dir"), "block": k})
        words_cmp["only_a"] = [w for w in words_cmp["only_a"] if id(w) not in gone_a]
        words_cmp["only_b"] = [w for w in words_cmp["only_b"] if id(w) not in gone_b]
        mv["words"] = len(mv["a_words"])

    def to_b_page(rect: list[float]) -> list[float]:
        return rect_through(inv, rect)

    block_changes: list[dict[str, Any]] = []
    for k, mv in enumerate(moves, 1):
        ba, bb = mv["bbox_a_pt"], mv["bbox_b_in_a_pt"]
        dx, dy = mv["vector"]
        in_a = [w for w in words_cmp["only_a"] if in_rects(w["pt"], [ba])]
        in_b = [w for w in words_cmp["only_b"] if in_rects(w["pt"], [bb])]
        if not (in_a or in_b):
            continue
        ids_a, ids_b = {id(w) for w in in_a}, {id(w) for w in in_b}
        words_cmp["only_a"] = [w for w in words_cmp["only_a"] if id(w) not in ids_a]
        words_cmp["only_b"] = [w for w in words_cmp["only_b"] if id(w) not in ids_b]
        for c in textdiff.build(in_a, textdiff.shifted(in_b, -dx, -dy), []):
            if c["b_in_a_bbox"]:
                bx_ = c["b_in_a_bbox"]
                c["b_in_a_bbox"] = [round(bx_[0] + dx, 2), round(bx_[1] + dy, 2), round(bx_[2] + dx, 2), round(bx_[3] + dy, 2)]
                c["b_bbox"] = [round(v, 2) for v in to_b_page(c["b_in_a_bbox"])]
            c["block"] = f"b{k}"
            if c["kind"] == "changed" and c["before"].split() == c["after"].split():
                (ax, ay), (bx, by) = center(c["a_bbox"]), center(c["b_in_a_bbox"])
                c.update(kind="moved", shift_pt=[round(bx - ax, 2), round(by - ay, 2)], norm=None, numbers=[])
            block_changes.append(c)
        words_cmp["only_a"] += in_a
        words_cmp["only_b"] += in_b
        mv["only_words"] = (ids_a, ids_b)
    skip_a = {i for mv in moves for i in mv.get("only_words", (set(), set()))[0]}
    skip_b = {i for mv in moves for i in mv.get("only_words", (set(), set()))[1]}
    text_changes = textdiff.finalize(
        textdiff.build([w for w in words_cmp["only_a"] if id(w) not in skip_a],
                       [w for w in words_cmp["only_b"] if id(w) not in skip_b], words_cmp["moved"], to_b_page=to_b_page)
        + block_changes)

    # 5. regions ----------------------------------------------------------------------------------------------
    regions_module.close_union(planes, canvas, band_pixels=settings.BAND_PIXELS)
    labels, stats, factor = regions_module.label_regions(planes, band_pixels=settings.BAND_PIXELS)
    n_labels = int(stats.shape[0])
    moved_rects: list[list[int]] = []
    pad_moved = radius + 1
    for mv_w in words_cmp["moved"]:
        for rect in (mv_w["a_pt"], mv_w["b_in_a_pt"]):
            x0, y0, x1, y1 = canvas.px(rect)
            moved_rects.append([max(0, x0 - pad_moved), max(0, y0 - pad_moved), x1 + radius + 2, y1 + radius + 2])

    def exclude(y0: int, y1: int) -> Any:
        return regions_module.rect_arrays(moved_rects, y1 - y0, width, y0) if moved_rects else None

    counts = regions_module.layer_counts(
        planes, labels, n_labels, factor, ("a_only", "b_only", "light_a", "light_b", "color", "style", "out"),
        band_pixels=settings.BAND_PIXELS, exclude=exclude)
    marks["close_label_counts"] = time.monotonic() - started
    peaks["labels"] = _vm_peak_mib()
    index = _WordIndexes(words_cmp, words_all, text_changes)
    regions, pending = _classify_regions(
        planes, canvas, labels, stats, factor, counts, index, text_changes, moves, mm_px)
    del labels, stats, counts

    # The windows rendered again, A then B: the colours around a region for the overdraw check, and the QR codes.
    qr_box = _qr_boxes(zones_a, zones_b, a, b)
    windows = _render_windows(
        a, b, matrix_b, scale, canvas, planes, regions, pending, qr_box, radius)
    marks["classify_windows"] = time.monotonic() - started
    peaks["windows"] = _vm_peak_mib()
    unreadable, budget_spent = _shift_and_glyph(planes, canvas, regions, index, moves, mm_px, clock)
    marks["shift_glyph"] = time.monotonic() - started

    for k, mv in enumerate(moves, 1):
        ba, bb = mv["bbox_a_pt"], mv["bbox_b_in_a_pt"]
        box_pt = [min(ba[0], bb[0]), min(ba[1], bb[1]), max(ba[2], bb[2]), max(ba[3], bb[3])]
        regions.append({
            "id": f"b{k}", "class": "block_moved", "bbox_px": canvas.px(box_pt), "bbox_a_pt": [round(v, 2) for v in ba],
            "bbox_b_in_a_pt": [round(v, 2) for v in bb], "shift_pt": [round(v, 2) for v in mv["vector"]],
            "words": mv.get("words", 0), "share": mv["share"], "text_before": [], "text_after": [], "moved_text": [],
            "text_unreadable": False,
        })
    regions.sort(key=lambda rg: (rg["class"] in SHIFT_CLASSES, rg["bbox_px"][1] // max(1, int(20 * mm_px)), rg["bbox_px"][0]))
    if budget_spent:
        reasons.append("PARTIAL_COVERAGE")

    # 6. channels, status, mask, result ---------------------------------------------------------------------------------
    channels: dict[str, dict[str, Any]] = {}
    shift_regions = sum(1 for rg in regions if rg["class"] in SHIFT_CLASSES)
    geom_regions = sum(1 for rg in regions if rg["class"] not in ("color", "style", *SHIFT_CLASSES))
    style_regions = sum(1 for rg in regions if rg["class"] == "style")
    color_regions = sum(1 for rg in regions if rg["class"] == "color")
    channels["geometry"] = st.checked(geom_regions)
    channels["color"] = st.checked(color_regions + style_regions)

    has_ink = planes.any("dark_a") or planes.any("dark_b")
    text_a_present, text_b_present = bool(a["words"]), bool(b["words"])
    if not text_a_present and not text_b_present:
        channels["text"] = st.checked(textdiff.significant(text_changes))
    elif not (text_a_present and text_b_present):
        channels["text"] = st.unchecked("у одной из страниц нет текстового слоя: текст не сравнивался")
    else:
        channels["text"] = st.checked(textdiff.significant(text_changes))
    if has_ink and not (text_a_present and text_b_present):
        channels["text_coverage"] = st.unchecked("нет текстового слоя: надписи сравнены только графически")
        reasons.append("NO_TEXT_LAYER")
    elif unreadable:
        channels["text_coverage"] = st.unchecked("в областях отличий есть надписи без текстового слоя")
        reasons.append("TEXT_UNREADABLE_IN_DIFF_AREA")
    else:
        channels["text_coverage"] = st.checked(0)

    # Service zones: every zone type on its own, then the fields.
    zone_results = []
    zone_words: dict[str, tuple[list[str], list[str]]] = {}
    for kind in zone_types:
        rects = [z["bbox"] for z in zones_a if z["type"] == kind] + [rect_through(m, z["bbox"]) for z in zones_b if z["type"] == kind]
        za = [w for w in words_a_all if in_rects(w["pt"], rects)]
        zb = [w for w in words_b_all if in_rects(w["pt"], rects)]
        zc = compare_words(za, zb, same_pt)
        zone_words[kind] = ([w["text"] for w in reading_order_words(za)], [w["text"] for w in reading_order_words(zb)])
        diff_px, strict_px = zone_stats[kind]
        zone_results.append({"type": kind, "changed": bool(diff_px or zc["only_a"] or zc["only_b"]),
                             "diff_px": diff_px, "within_tolerance_px": strict_px - diff_px})
    service_fields = _service_fields(a, b, zones_a, zones_b, zone_words, windows)
    zone_changes = sum(1 for z in zone_results if z["changed"])
    if service_fields and not zone_changes:
        zone_changes = len(service_fields)
    channels["zones"] = st.checked(zone_changes)

    ann = annotations_module.compare_annotations(
        a.get("annotations") or [], b.get("annotations") or [], matrix=m, a_height=a["height_pt"], a_rotation=a["rotation"],
        b_height=b["height_pt"], b_rotation=b["rotation"], identity=bool(reg["identity"]))
    ann_diffs = annotations_module.diff_count(ann)
    channels["annotations"] = (st.checked(ann_diffs) if (a.get("annotations") or b.get("annotations"))
                               else st.not_applicable("аннотаций нет ни в A, ни в B"))

    baked = {"a": warning_lines(wa), "b": warning_lines(wb)}
    if baked["a"] or baked["b"]:
        channels["warnings"] = st.unchecked("предупреждение вшито в содержимое листа и не отделено: отличия под ним могут быть скрыты им самим")
        reasons.append("PARTIAL_COVERAGE")
    else:
        channels["warnings"] = st.not_applicable("предупреждений не обнаружено")

    main_diffs = channels["geometry"]["diffs"] + channels["color"]["diffs"] + (
        channels["text"].get("diffs", 0) if channels["text"]["state"] == "checked" else 0)
    is_spec = "spec" in (classify_kind(words_a_all, (a.get("stamp") or {}).get("designation"), a["height_pt"]),
                         classify_kind(words_b_all, (b.get("stamp") or {}).get("designation"), b["height_pt"]))
    if is_spec:
        channels["spec_positions"] = spec_positions_channel(a, b, main_diffs)
    else:
        channels["spec_positions"] = st.not_applicable("не спецификация")
    status, kept_reasons = st.decide(channels, reasons)

    # The mask: eight planes in the order of ``ComparisonLayer``.
    mask_info = _write_mask(planes, out_dir, canvas, status)
    aligned = _aligned_blocks(moves)
    service_notes = _service_notes(service_fields) + annotations_module.notes(ann)
    differences = [difference(rg) for rg in regions]
    outcome = {
        "status": status, "reasons": kept_reasons, "channels": channels,
        "result": build_result(
            width_pt=canvas.width_pt, height_pt=canvas.height_pt, dpi=canvas.dpi, matrix_pdf=matrix_to_pdf(m),
            differences=differences, text_changes=[text_change(c) for c in text_changes],
            service_notes=service_notes, aligned_blocks=aligned, within=totals["within"], noise=totals["noise"],
            separated=sum(1 for z in zones_a + zones_b if z["type"] == "release_stamp"), mask=mask_info, part=part_info),
        "counts": {
            "regions": len(regions), "differences": len(differences), "shifts": shift_regions,
            "text_changes": len(text_changes), "registration": reg["method"], "reliable": reg["reliable"],
            "dice36": reg.get("dice36"), "budget_spent": budget_spent,
        },
    }
    with open(os.path.join(out_dir, "outcome.json"), "w", encoding="utf-8") as sink:
        json.dump(outcome, sink, ensure_ascii=False, separators=(",", ":"))
    return {
        "pair_status": status, "dpi": canvas.dpi, "width_px": width, "height_px": height, "bands": len(band_list),
        "mask": mask_info is not None, "regions": len(regions),
        "t_render_a_s": round(t_render_a, 3), "t_bands_s": round(t_bands, 3), "t_job_s": round(time.monotonic() - started, 3),
        "marks": {k: round(v, 2) for k, v in marks.items()}, "peaks_mib": peaks,
    }


class PageTooLarge(Exception):
    """The canvas of A would pass the 40 Mpx cap (the profile refuses such a page, so this is a guard)."""

    def __init__(self, width_pt: float, height_pt: float) -> None:
        super().__init__("PAGE_TOO_LARGE")
        self.reason = "PAGE_TOO_LARGE"
        self.width_pt = width_pt
        self.height_pt = height_pt


# -- the regions ------------------------------------------------------------------------------------------------------

class _WordIndexes:
    """Spatial indexes over the words of the comparison, to ask what stands in the box of a region."""

    def __init__(self, words_cmp: dict[str, Any], words_all: list[dict], text_changes: list[dict]) -> None:
        self.only_a = regions_module.RectIndex()
        self.only_b = regions_module.RectIndex()
        self.moved = regions_module.RectIndex()
        self.all = regions_module.RectIndex()
        self.changes = regions_module.RectIndex()
        for w in words_cmp["only_a"]:
            self.only_a.add(w["pt"], w)
        for w in words_cmp["only_b"]:
            self.only_b.add(w["pt"], w)
        for mv in words_cmp["moved"]:
            self.moved.add(mv["a_pt"], mv)
            self.moved.add(mv["b_in_a_pt"], mv)
        for w in words_all:
            self.all.add(w["pt"], w)
        for c in text_changes:
            for key in ("a_bbox", "b_in_a_bbox"):
                if c.get(key):
                    self.changes.add(c[key], c)
        self.word_rects = (
            [w["pt"] for w in words_cmp["only_a"] + words_cmp["only_b"]]
            + [mv[k] for mv in words_cmp["moved"] for k in ("a_pt", "b_in_a_pt")]
            + [c[k] for c in text_changes for k in ("a_bbox", "b_in_a_bbox") if c.get(k)]
        )


def _texts(words: list[dict]) -> list[str]:
    seen: set[int] = set()
    unique = [w for w in words if not (id(w) in seen or seen.add(id(w)))]
    return [w["text"] for w in reading_order_words(unique)]


def _classify_regions(
    planes: PlaneStore, canvas: Canvas, labels: Any, stats: Any, factor: int, counts: dict[str, Any],
    index: _WordIndexes, text_changes: list[dict], moves: list[dict], mm_px: float,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Group the labelled components (one text change is one region) and give each group its class, up to the
    checks that need pixels (``engine.py:779-863``). A group of colour only is left ``pending`` for the overdraw check."""
    n = int(stats.shape[0])
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    block_boxes = [b for mv in moves for b in (mv["bbox_a_pt"], mv["bbox_b_in_a_pt"])]
    for rect in index.word_rects:
        if block_boxes and in_rects(rect, block_boxes):
            continue  # the words of a moved block do not glue its old place to its new one
        x0, y0, x1, y1 = canvas.px(rect)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(planes.width, x1 + 1), min(planes.height, y1 + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        ids = numpy.unique(labels[y0 // factor : -(-y1 // factor), x0 // factor : -(-x1 // factor)])
        members = [int(v) for v in ids if v > 0]
        for other in members[1:]:
            parent[find(other)] = find(members[0])
    groups: dict[int, list[int]] = {}
    for i in range(1, n):
        groups.setdefault(find(i), []).append(i)

    regions: list[dict[str, Any]] = []
    pending: list[int] = []
    for number, member_list in enumerate(groups.values(), 1):
        members = numpy.array(member_list)
        x = int(stats[members, 0].min()) * factor
        y = int(stats[members, 1].min()) * factor
        x_end = min(planes.width, int((stats[members, 0] + stats[members, 2]).max()) * factor)
        y_end = min(planes.height, int((stats[members, 1] + stats[members, 3]).max()) * factor)
        box_px = [x, y, x_end, y_end]
        box_pt = canvas.pt(box_px)
        text_a = _texts(index.only_a.query(box_pt))
        text_b = _texts(index.only_b.query(box_pt))
        moved_entries = index.moved.query(box_pt)
        moved_text = [mv["text"] for mv in moved_entries]
        has_words = bool(index.all.query(box_pt))
        ca, cb, cla, clb, cc, cs = (int(counts[k][members].sum()) for k in ("a_only", "b_only", "light_a", "light_b", "color", "style"))
        out_moved = int(counts["out"][members].sum())
        wait = False
        if not (ca or cb or cla or clb or cc):
            kind = "style"
        elif text_a or text_b:
            kind = "text"
        elif moved_text and out_moved <= settings.NOISE_MAX_PX:
            kind = "text_moved"
        elif ca and cb:
            kind = "changed"
        elif cb:
            kind = "added"
        elif ca:
            kind = "removed"
        elif cs:
            kind = "style"
        elif cc:
            kind, wait = "color", True
        else:
            kind = "light"
        regions.append({
            "id": f"r{number}", "class": kind, "bbox_px": box_px, "bbox_a_pt": [round(v, 2) for v in box_pt],
            "text_before": text_a[:40], "text_after": text_b[:40], "moved_text": moved_text[:40],
            "has_words": has_words, "text_unreadable": False,
            "a_only_px": ca, "b_only_px": cb, "light_a_px": cla, "light_b_px": clb, "color_px": cc, "style_px": cs,
        })
        if wait:
            pending.append(len(regions) - 1)
    return regions, pending


def _shift_and_glyph(
    planes: PlaneStore, canvas: Canvas, regions: list[dict[str, Any]], index: _WordIndexes, moves: list[dict],
    mm_px: float, clock: dict[str, float],
) -> tuple[list[int], bool]:
    """The checks that look at the pixels around a region: a shift of a neighbouring inscription (``engine.py:853-863``)
    and a line of glyphs with no text layer (``:864-871``). Returns the regions that hold unreadable inscriptions, and
    whether the time allowed for the checks ran out (the rest were classified by the cheap rules alone)."""
    deadline = clock["analysis_deadline"]
    near = settings.SHIFT_NEAR_MM * mm_px / canvas.s
    unreadable: list[int] = []
    spent = False
    for number, rg in enumerate(regions):
        kind = rg["class"]
        if kind not in ("added", "removed", "changed", "style", "light"):
            continue
        if time.process_time() > deadline:
            spent = True
            continue
        box_pt = rg["bbox_a_pt"]
        wide = [box_pt[0] - near, box_pt[1] - near, box_pt[2] + near, box_pt[3] + near]
        vectors = {
            (round(c[0], 1), round(c[1], 1))
            for c in [(center(mv["b_in_a_pt"])[0] - center(mv["a_pt"])[0], center(mv["b_in_a_pt"])[1] - center(mv["a_pt"])[1])
                      for mv in index.moved.query(wide)]
            + [tuple(mv["vector"]) for mv in moves
               if not (mv["bbox_a_pt"][2] < wide[0] or mv["bbox_a_pt"][0] > wide[2] or mv["bbox_a_pt"][3] < wide[1] or mv["bbox_a_pt"][1] > wide[3])
               or not (mv["bbox_b_in_a_pt"][2] < wide[0] or mv["bbox_b_in_a_pt"][0] > wide[2] or mv["bbox_b_in_a_pt"][3] < wide[1] or mv["bbox_b_in_a_pt"][1] > wide[3])]
        }
        if vectors and regions_module.shift_explains(planes, sorted(vectors), rg["bbox_px"], canvas, deadline):
            rg["class"] = "text_moved" if rg["moved_text"] else "shifted"
            continue
        if kind in ("added", "removed", "changed") and not rg["has_words"]:
            x0, y0, x1, y1 = rg["bbox_px"]
            if (x1 - x0) * (y1 - y0) > regions_module.WINDOW_PIXELS:
                continue
            sub = planes.window("a_only", x0, y0, x1, y1) | planes.window("b_only", x0, y0, x1, y1)
            common = (planes.window("dark_a", x0, y0, x1, y1) & planes.window("dark_b", x0, y0, x1, y1)
                      & (1 - planes.window("zones", x0, y0, x1, y1)))
            try:
                found = regions_module.glyph_line(sub, mm_px, common, deadline)
            except regions_module.BudgetSpent:
                spent = True
                continue
            if found:
                rg["text_unreadable"] = True
                unreadable.append(number)
    return unreadable, spent


# -- windows rendered again: the overdraw check and the QR codes --------------------------------------------------

_MAX_OVERDRAW_WINDOWS = 48


def _qr_boxes(zones_a: list[dict], zones_b: list[dict], a: dict, b: dict) -> list[float] | None:
    box = zones_module.qr_search_box(zones_a, a["width_pt"], a["height_pt"])
    return box


def _render_windows(
    a: dict[str, Any], b: dict[str, Any], matrix_b: list[float], scale: float, canvas: Canvas, planes: PlaneStore,
    regions: list[dict[str, Any]], pending: list[int], qr_box: list[float] | None, radius: int,
) -> dict[str, Any]:
    """Render the windows of the pending regions (overdraw) and the QR search box once for A and once for B, decide
    the pending regions, and read the QR codes. Returns ``{"qr": {"a": ..., "b": ...}}``."""
    pad = 2 * radius + 4
    jobs: list[tuple[int, list[int]]] = []
    for number in pending[:_MAX_OVERDRAW_WINDOWS]:
        x0, y0, x1, y1 = regions[number]["bbox_px"]
        win = [max(0, x0 - pad), max(0, y0 - pad), min(planes.width, x1 + pad), min(planes.height, y1 + pad)]
        if (win[2] - win[0]) * (win[3] - win[1]) <= regions_module.WINDOW_PIXELS:
            jobs.append((number, win))
    qr_px = canvas.px(qr_box) if qr_box else None
    if qr_px:
        qr_px = [max(0, qr_px[0]), max(0, qr_px[1]), min(planes.width, qr_px[2]), min(planes.height, qr_px[3])]
        if (qr_px[2] - qr_px[0]) * (qr_px[3] - qr_px[1]) > regions_module.WINDOW_PIXELS or qr_px[2] <= qr_px[0] or qr_px[3] <= qr_px[1]:
            qr_px = None
    out: dict[str, Any] = {"qr": {"a": None, "b": None}}
    if not jobs and not qr_px:
        return out
    rendered: dict[str, list[Any]] = {}
    for side, page_info, matrix in (("a", a, [scale, 0, 0, scale, 0, 0]), ("b", b, matrix_b)):
        document, page = open_page(str(page_info["pdf"]), int(page_info["index"]))
        try:
            rendered[side] = [render_rows(page, matrix, w[2] - w[0], w[1], w[3], w[0]) for _, w in jobs]
            if qr_px:
                rendered[side].append(render_rows(page, matrix, qr_px[2] - qr_px[0], qr_px[1], qr_px[3], qr_px[0]))
        finally:
            page.close()
            document.close()
    for position, (number, win) in enumerate(jobs):
        x0, y0, x1, y1 = regions[number]["bbox_px"]
        box_rel = [x0 - win[0], y0 - win[1], x1 - win[0], y1 - win[1]]
        color_w = planes.window("color", *win)
        dark_a_w, dark_b_w = planes.window("dark_a", *win), planes.window("dark_b", *win)
        style = regions_module.overdraw(rendered["a"][position], rendered["b"][position], color_w, dark_a_w, dark_b_w, box_rel, pad)
        regions[number]["class"] = "style" if style else "color"
    if qr_px:
        for side in ("a", "b"):
            gray = cv2.cvtColor(rendered[side][len(jobs)], cv2.COLOR_BGR2GRAY)
            out["qr"][side] = zones_module.read_qr(gray)
    return out


# -- the service fields ------------------------------------------------------------------------------------------------

_STAMP_FIELDS = (
    ("designation", "Обозначение"), ("sheet_title", "Название листа"), ("sheet_number", "Лист"),
    ("revision_number", "Последнее «Изм.»"), ("release_date", "Дата"),
)


def _change(before: str, after: str) -> str:
    if before and not after:
        return "removed"
    if after and not before:
        return "added"
    return "changed"


def _service_fields(a: dict, b: dict, zones_a: list[dict], zones_b: list[dict], zone_words: dict[str, tuple[list[str], list[str]]],
                    windows: dict[str, Any]) -> list[dict[str, Any]]:
    """What changed in the service zones, field by field, «было → стало» (``service.compare``, ``service.py:125-183``).
    Nothing is hidden and nothing is read as an approval."""
    out: list[dict[str, Any]] = []
    sa, sb = a.get("stamp") or {}, b.get("stamp") or {}
    for field, label in _STAMP_FIELDS:
        va, vb = norm(sa.get(field)), norm(sb.get(field))
        if va != vb:
            out.append({"zone": "stamp", "field": field, "label": label, "change": _change(va, vb), "before": va, "after": vb})
    words_a, words_b = zone_words.get("release_stamp", ([], []))
    release_a = zones_module.release_text(zones_a, words_a)
    release_b = zones_module.release_text(zones_b, words_b)
    if release_a or release_b:
        da, db = DATE_RE.findall(release_a), DATE_RE.findall(release_b)
        if da != db:
            out.append({"zone": "release_stamp", "field": "date", "label": "Отметка выпуска: дата",
                        "change": _change(", ".join(da), ", ".join(db)), "before": ", ".join(da), "after": ", ".join(db)})
        rest_a, rest_b = norm(DATE_RE.sub("", release_a)), norm(DATE_RE.sub("", release_b))
        if rest_a != rest_b:
            out.append({"zone": "release_stamp", "field": "text", "label": "Отметка выпуска: текст",
                        "change": _change(rest_a, rest_b), "before": rest_a, "after": rest_b})
    qa, qb = windows["qr"]["a"], windows["qr"]["b"]
    if qa or qb:
        def show(q: dict | None) -> str:
            if not q:
                return ""
            return ", ".join(q["content"]) if q["decoded"] else f"(не читается, отпечаток {q['fingerprint']})"

        key_a = (qa or {}).get("content") or (qa or {}).get("fingerprint")
        key_b = (qb or {}).get("content") or (qb or {}).get("fingerprint")
        if key_a != key_b:
            out.append({"zone": "qr", "field": "qr", "label": "QR-код",
                        "change": "changed" if (qa and qb) else ("added" if qb else "removed"), "before": show(qa), "after": show(qb)})
    ia = _stamp_images(a, zones_a)
    ib = _stamp_images(b, zones_b)
    if ia != ib:
        out.append({"zone": "stamp", "field": "images", "label": "Подписи (изображения в штампе)",
                    "change": _change(str(ia) if ia else "", str(ib) if ib else ""),
                    "before": f"{ia} шт." if ia else "", "after": f"{ib} шт." if ib else ""})
    return out


def _stamp_images(page: dict[str, Any], zones: list[dict]) -> int:
    box = zones_module.zone_bbox(zones, "stamp")
    if not box:
        return 0
    return sum(1 for r in page.get("image_boxes") or ()
               if box[0] <= (r[0] + r[2]) / 2 <= box[2] and box[1] <= (r[1] + r[3]) / 2 <= box[3])


def _service_notes(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``ComparisonServiceNote`` for each field change."""
    notes: list[dict[str, Any]] = []
    for f in fields:
        kind = {"release_stamp": "stamp", "qr": "qr"}.get(f["zone"], "field")
        note: dict[str, Any] = {"kind": kind, "change": f["change"], "zone": f["zone"], "field": f["field"]}
        if f["before"]:
            note["before"] = f["before"][:2000]
        if f["after"]:
            note["after"] = f["after"][:2000]
        notes.append(note)
    return notes


# -- the aligned blocks and the mask --------------------------------------------------------------------------------------

def _overlap(a: list[float], b: list[float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _aligned_blocks(moves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The blocks the viewer may align (``block_alignment.moves``, ``block_alignment.py:16-24``): moved with at least
    90 % of the pixels explained, and with no competing translation over the same area."""
    candidates = [mv for mv in moves if mv.get("share", 0) >= settings.ALIGN_MIN_SHARE]
    selected = [
        mv for mv in candidates
        if not any(_overlap(x, y) for other in candidates if other is not mv
                   for x in (mv["bbox_a_pt"], mv["bbox_b_in_a_pt"]) for y in (other["bbox_a_pt"], other["bbox_b_in_a_pt"]))
    ]
    return [{"box_a": list(mv["bbox_b_in_a_pt"]), "dx_pt": round(mv["vector"][0], 2), "dy_pt": round(mv["vector"][1], 2)}
            for mv in selected]


def _write_mask(planes: PlaneStore, out_dir: str, canvas: Canvas, status: str) -> dict[str, int] | None:
    """The mask blob of format 1, only for a pair that is not ``same`` and only if some plane has a pixel set."""
    if status == "same":
        return None
    data = planes.data
    main = data["a_only"] | data["b_only"]
    stack = [
        main, data["light_a"] | data["light_b"], data["color"], data["style"], data["moved"], data["within_tol"],
        data["noise"], data["zones"],
    ]
    if not any(plane.any() for plane in stack):
        return None
    blob = mask_codec.encode_packed_planes(stack, planes.width, planes.height)
    with open(os.path.join(out_dir, "mask.bin"), "wb") as sink:
        sink.write(blob)
    return {"format": mask_codec.MASK_FORMAT, "dpi": canvas.dpi, "width_px": planes.width, "height_px": planes.height}
