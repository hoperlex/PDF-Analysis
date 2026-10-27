#!/usr/bin/env python3
"""Render and extraction cost of comparison pages, measured per page in a child process
under a kernel memory ceiling (`CMP-MEASURE-01A`, ADR-0025 decisions 8 and 9).

Commands (run with the main venv: ``/root/projects/PDF-Analysis/.venv/bin/python``)::

    comparison_render.py run   --label NAME --results OUT.jsonl INPUT.pdf [INPUT.pdf ...]
    comparison_render.py table --results OUT.jsonl [--label NAME ...] [--by page|class]
    comparison_render.py levels --results OUT.jsonl --label NAME --file F.pdf --page N [--dpi 200]
    comparison_render.py fit   --results OUT.jsonl [--label NAME ...]

``run`` measures one page at a time, one child at a time (never in parallel; the host is
shared). For every page of every input it starts, each in a fresh child process:

* ``render`` at 200, 150 and 100 dpi (``--dpi`` to change; ``--dpi ""`` for none): ``pypdfium2`` renders the page,
  then from that raster a 1400 px preview PNG, a 220 px thumbnail PNG and a 512 px tile
  pyramid (every tile of every level encoded as PNG, so the byte figure is a measurement, not
  an estimate);
* ``extract``: ``pdfplumber`` words with boxes, then lines (with the other drawing counts the
  same parse yields);

and once per input a ``scan`` child (page count, displayed size, rotation, drawing elements
counted the way ``src/auditmanager/ingest/pdf_reader.py::_elements`` counts them), plus one
``baseline`` child (the interpreter and the three libraries imported, no page).

A child does what ``ingest/pdf_reader.py`` does before it loads anything: ``RLIMIT_CORE`` 0,
``RLIMIT_AS`` (default 768 MiB, ``--address-space-mib``) and ``RLIMIT_CPU`` (default 300 s,
``--cpu-seconds``); the parent adds a wall clock (default 600 s, ``--wall-seconds``) and kills
only its own child when it passes. The child imports nothing from the product; the product's
``PDFIUM_LOCK`` guards PDFium inside one process and has no work to do in a process of its own
with one thread.

Figures per job: the parent's wall clock (spawn to reap), the child's user+sys CPU and
``ru_maxrss`` (both from ``wait4``), and, read by the child itself from ``/proc/self/status``,
``VmHWM`` (its own peak resident set) and ``VmPeak`` (its peak address space, the quantity
``RLIMIT_AS`` limits). The kernel can fold the high-water mark of the address space a child
was started from into its ``ru_maxrss`` at ``exec``, so the parent here is a standard-library
process that never loads a page; on every completed job of the report ``ru_maxrss`` and
``VmHWM`` differ by at most 0.4 MiB. ``VmPeak`` is 13 to 32 MiB above ``VmHWM``.

A job that ends without a result is reported with its status (``overrun`` for a
``MemoryError`` under the ceiling, ``signal:NAME``, ``cpu``, ``wall`` or ``error:TYPE``). With
``--escalate 1024,1536`` (MiB) a failed job is re-run at each larger ceiling in turn until one passes,
and the record says which (``needs_mib``): the evidence that the first failure was the ceiling.

Raster pipelines (``--pipeline``): ``lean`` (default; PDFium renders ``RGBx``, 4 bytes a pixel,
and Pillow shares that buffer), ``naive`` (``to_pil()`` of the default 3-byte ``BGR`` bitmap,
which copies: about 7 bytes a pixel at the peak) and ``gray`` (1 byte a pixel; for
registration-style work, not for previews).

The real set under ``.local/comparison-measure/`` is client-like data. A record holds only
numbers, the file's base name and the page index; nothing of a page's content is read into a
record, printed or copied.

Nothing is installed and nothing is written outside ``--results`` (the rasters live in memory).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import resource
import selectors
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

MIB = 1024 * 1024
DEFAULT_ADDRESS_SPACE_MIB = 768
DEFAULT_CPU_SECONDS = 300
DEFAULT_WALL_SECONDS = 600
DEFAULT_DPIS = (200, 150, 100)
PREVIEW_PX = 1400
THUMBNAIL_PX = 220
TILE_PX = 512
PIPELINES = ("lean", "naive", "gray")
PT_PER_INCH = 72.0
MM_PER_INCH = 25.4

# --------------------------------------------------------------------------------------
# The child
# --------------------------------------------------------------------------------------


def _proc_status() -> dict[str, int]:
    """``VmPeak``, ``VmHWM``, ``VmRSS`` of this process in KiB, from ``/proc/self/status``."""
    wanted = {"VmPeak": "vm_peak_kib", "VmHWM": "vm_hwm_kib", "VmRSS": "vm_rss_kib"}
    found: dict[str, int] = {}
    try:
        with open("/proc/self/status", encoding="ascii") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                if key in wanted:
                    found[wanted[key]] = int(rest.split()[0])
    except OSError:
        pass
    return found


def _limit(settings: dict[str, Any]) -> None:
    """The kernel's ceilings, set before anything is imported (as ``pdf_reader._limit``)."""
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    address_space = int(settings["address_space"])
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    cpu_seconds = int(settings["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))


def _say(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _elements(raw: Any, page: Any) -> int:
    """Drawing elements as ``pdf_reader._elements`` counts them (a path by its segments,
    anything else as one, form XObjects walked), without its ceiling."""
    total = 0
    pending: list[tuple[Any, bool]] = [(page, False)]
    while pending:
        container, is_form = pending.pop()
        count = (raw.FPDFFormObj_CountObjects if is_form else raw.FPDFPage_CountObjects)(container)
        get = raw.FPDFFormObj_GetObject if is_form else raw.FPDFPage_GetObject
        for index in range(max(count, 0)):
            child = get(container, index)
            kind = raw.FPDFPageObj_GetType(child) if child else None
            if kind == raw.FPDF_PAGEOBJ_PATH:
                total += max(raw.FPDFPath_CountSegments(child), 1)
            else:
                total += 1
                if kind == raw.FPDF_PAGEOBJ_FORM:
                    pending.append((child, True))
    return total


def _child_baseline(settings: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    import pdfplumber  # noqa: F401
    import pypdfium2  # noqa: F401
    from PIL import Image  # noqa: F401

    return {"t_import_s": round(time.perf_counter() - t0, 4)}


def _child_scan(settings: dict[str, Any]) -> dict[str, Any]:
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    document = pdfium.PdfDocument(settings["pdf"])
    pages = []
    try:
        for index in range(len(document)):
            _say({"stage": f"scan page {index}"})
            page = document[index]
            try:
                width, height = page.get_size()
                pages.append(
                    {
                        "page": index,
                        "w_pt": round(width, 2),
                        "h_pt": round(height, 2),
                        "rotation": page.get_rotation(),
                        "elements": _elements(raw, page.raw),
                    }
                )
            finally:
                page.close()
    finally:
        document.close()
    return {"pages": pages, "page_count": len(pages)}


def _fit(width: int, height: int, long_side: int) -> tuple[int, int]:
    """The size with the long side at ``long_side`` (never up-scaled)."""
    longest = max(width, height)
    if longest <= long_side:
        return width, height
    factor = long_side / longest
    return max(1, round(width * factor)), max(1, round(height * factor))


def _png_bytes(image: Any) -> int:
    """Size of ``image`` as a PNG (Pillow defaults: compress level 6, no ``optimize``)."""
    if image.mode == "RGBX":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.tell()


def _child_render(settings: dict[str, Any]) -> dict[str, Any]:
    import pypdfium2 as pdfium
    from PIL import Image

    pipeline = settings["pipeline"]
    dpi = int(settings["dpi"])
    result: dict[str, Any] = {"pipeline": pipeline, "dpi": dpi}
    clock = time.perf_counter
    started = clock()

    _say({"stage": "open"})
    document = pdfium.PdfDocument(settings["pdf"])
    page = document[int(settings["page"])]
    width_pt, height_pt = page.get_size()
    result["w_pt"], result["h_pt"] = round(width_pt, 2), round(height_pt, 2)
    result["t_open_s"] = round(clock() - started, 4)

    _say({"stage": "render"})
    began = clock()
    options: dict[str, Any] = {}
    if pipeline == "lean":
        options = {"prefer_bgrx": True, "rev_byteorder": True}
    elif pipeline == "gray":
        options = {"grayscale": True}
    bitmap = page.render(scale=dpi / PT_PER_INCH, **options)
    image = bitmap.to_pil()
    page.close()
    result["t_render_s"] = round(clock() - began, 4)
    width, height = image.size
    result["w"], result["h"] = width, height
    result["mpx"] = round(width * height / 1e6, 3)
    result["raster_mode"] = image.mode
    result["bitmap_bytes"] = bitmap.stride * bitmap.height
    result["vm_hwm_after_render_kib"] = _proc_status().get("vm_hwm_kib")

    _say({"stage": "preview"})
    began = clock()
    size = _fit(width, height, PREVIEW_PX)
    preview = image if size == (width, height) else image.resize(
        size, Image.Resampling.LANCZOS, reducing_gap=3.0
    )
    result["preview"] = {"w": size[0], "h": size[1], "png_bytes": _png_bytes(preview)}
    del preview
    result["t_preview_s"] = round(clock() - began, 4)

    _say({"stage": "thumbnail"})
    began = clock()
    size = _fit(width, height, THUMBNAIL_PX)
    thumbnail = image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0) if size != (
        width,
        height,
    ) else image
    result["thumbnail"] = {"w": size[0], "h": size[1], "png_bytes": _png_bytes(thumbnail)}
    del thumbnail
    result["t_thumbnail_s"] = round(clock() - began, 4)

    _say({"stage": "tiles"})
    began = clock()
    levels = []
    current = image
    level = 0
    while True:
        level_w, level_h = current.size
        columns, rows = math.ceil(level_w / TILE_PX), math.ceil(level_h / TILE_PX)
        total, largest = 0, 0
        for row in range(rows):
            for column in range(columns):
                box = (
                    column * TILE_PX,
                    row * TILE_PX,
                    min((column + 1) * TILE_PX, level_w),
                    min((row + 1) * TILE_PX, level_h),
                )
                size_bytes = _png_bytes(current.crop(box))
                total += size_bytes
                largest = max(largest, size_bytes)
        levels.append(
            {
                "level": level,
                "w": level_w,
                "h": level_h,
                "tiles": columns * rows,
                "png_bytes": total,
                "largest_tile_png_bytes": largest,
            }
        )
        if max(level_w, level_h) <= TILE_PX:
            break
        reduced = current.reduce(2)
        if level > 0:
            del current
        current = reduced
        level += 1
    del current
    result["tile_pyramid"] = {
        "tile_px": TILE_PX,
        "levels": levels,
        "tiles": sum(item["tiles"] for item in levels),
        "png_bytes": sum(item["png_bytes"] for item in levels),
    }
    result["t_tiles_s"] = round(clock() - began, 4)
    result["t_child_s"] = round(clock() - started, 4)
    return result


def _child_extract(settings: dict[str, Any]) -> dict[str, Any]:
    import pdfplumber

    clock = time.perf_counter
    started = clock()
    result: dict[str, Any] = {}
    _say({"stage": "open"})
    pdf = pdfplumber.open(settings["pdf"])
    try:
        page = pdf.pages[int(settings["page"])]
        result["t_open_s"] = round(clock() - started, 4)

        _say({"stage": "words"})
        began = clock()
        words = page.extract_words()
        result["t_words_s"] = round(clock() - began, 4)
        result["words"] = len(words)
        result["words_with_boxes"] = sum(
            1 for word in words if all(key in word for key in ("x0", "x1", "top", "bottom"))
        )

        _say({"stage": "lines"})
        began = clock()
        lines = page.lines
        result["t_lines_s"] = round(clock() - began, 4)
        result["lines"] = len(lines)
        result["rects"] = len(page.rects)
        result["curves"] = len(page.curves)
        result["chars"] = len(page.chars)
        result["t_child_s"] = round(clock() - started, 4)
        page.flush_cache()
    finally:
        pdf.close()
    return result


_CHILD_MODES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "baseline": _child_baseline,
    "scan": _child_scan,
    "render": _child_render,
    "extract": _child_extract,
}


def _wraps_memory_error(failure: BaseException) -> bool:
    """Whether a ``MemoryError`` is the failure itself, its cause/context or one of its arguments."""
    seen: set[int] = set()
    pending: list[Any] = [failure]
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, MemoryError):
            return True
        if isinstance(item, BaseException):
            pending.extend([item.__cause__, item.__context__, *item.args])
    return False


def child_main(settings_json: str) -> int:
    settings = json.loads(settings_json)
    _limit(settings)
    _say({"stage": "limits_set"})
    try:
        payload = _CHILD_MODES[settings["mode"]](settings)
    except MemoryError:
        _say({"status": "overrun", "reason": "MemoryError", **_proc_status()})
        return 3
    except Exception as failure:  # noqa: BLE001 - reported to the parent as data
        if _wraps_memory_error(failure):
            # pdfplumber re-raises whatever pdfminer raised as `PdfminerException(original)`.
            _say(
                {
                    "status": "overrun",
                    "reason": f"MemoryError inside {type(failure).__name__}",
                    **_proc_status(),
                }
            )
            return 3
        _say(
            {
                "status": f"error:{type(failure).__name__}",
                "detail": str(failure)[:160].replace(str(settings.get("pdf", "")), "<pdf>"),
                **_proc_status(),
            }
        )
        return 4
    _say({"status": "ok", **payload, **_proc_status()})
    return 0


# --------------------------------------------------------------------------------------
# The parent
# --------------------------------------------------------------------------------------

_SIGNAL_NAMES = {int(number): number.name for number in signal.Signals}


def run_child(settings: dict[str, Any], wall_seconds: float) -> dict[str, Any]:
    """Start one child, wait for it, reap it with ``wait4`` and return its record.

    Only this child is ever signalled, by its own PID, and only past the wall clock.
    """
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "child", json.dumps(settings)]
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "PYTHONHASHSEED": "0"}
    load_before = os.getloadavg()[0]
    began = time.monotonic()
    child = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=environment,
        close_fds=True,
    )
    pid = child.pid
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)  # type: ignore[arg-type]
    chunks: list[bytes] = []
    timed_out = False
    while True:
        remaining = wall_seconds - (time.monotonic() - began)
        if remaining <= 0:
            timed_out = True
            os.kill(pid, signal.SIGKILL)  # our own child, by its PID
            break
        if selector.select(timeout=min(remaining, 5.0)):
            data = os.read(child.stdout.fileno(), 65536)  # type: ignore[union-attr]
            if not data:
                break
            chunks.append(data)
    if timed_out:
        # Drain what is already written, then reap.
        try:
            while True:
                data = os.read(child.stdout.fileno(), 65536)  # type: ignore[union-attr]
                if not data:
                    break
                chunks.append(data)
        except OSError:
            pass
    _, wait_status, usage = os.wait4(pid, 0)
    child.returncode = 0  # reaped here, not by Popen
    wall = time.monotonic() - began
    child.stdout.close()  # type: ignore[union-attr]
    selector.close()

    lines = [line for line in b"".join(chunks).decode("utf-8", "replace").splitlines() if line.startswith("{")]
    final: dict[str, Any] | None = None
    last_stage = None
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if "status" in item:
            final = item
        elif "stage" in item:
            last_stage = item["stage"]

    record: dict[str, Any] = {
        "wall_s": round(wall, 3),
        "cpu_s": round(usage.ru_utime + usage.ru_stime, 3),
        "ru_maxrss_kib": usage.ru_maxrss,
        "load1_before": round(load_before, 2),
        "load1_after": round(os.getloadavg()[0], 2),
        "ceiling_mib": round(int(settings["address_space"]) / MIB),
    }
    if timed_out:
        record["status"] = "wall"
        record["last_stage"] = last_stage
    elif final is not None:
        record.update(final)
        if final["status"] != "ok":
            record["last_stage"] = last_stage
    elif os.WIFSIGNALED(wait_status):
        number = os.WTERMSIG(wait_status)
        name = _SIGNAL_NAMES.get(number, str(number))
        record["status"] = "cpu" if number == signal.SIGXCPU else f"signal:{name}"
        record["last_stage"] = last_stage
    else:
        record["status"] = f"exit:{os.WEXITSTATUS(wait_status)}"
        record["last_stage"] = last_stage
    return record


def _key(item: dict[str, Any]) -> tuple:
    return (item["label"], item["file"], item["kind"], item.get("page"), item.get("dpi"), item.get("pipeline"), item["ceiling_mib"])


def _measure(
    base: dict[str, Any],
    args: argparse.Namespace,
    done: set[tuple],
    sink: Any,
    escalate: list[int],
) -> dict[str, Any] | None:
    """One job, with the escalation ladder when it fails. Appends a record to ``sink``."""
    probe = {**base, "ceiling_mib": args.address_space_mib}
    if _key(probe) in done:
        return None
    settings = {k: v for k, v in base.items() if k not in ("label", "file")}
    settings["pdf"] = base["pdf"]
    settings["address_space"] = args.address_space_mib * MIB
    settings["cpu_seconds"] = args.cpu_seconds
    record = run_child(settings, args.wall_seconds)
    entry = {k: v for k, v in base.items() if k != "pdf"}
    entry.update(record)
    if record["status"] not in ("ok", "wall", "cpu"):
        for ceiling in escalate:
            if ceiling <= args.address_space_mib:
                continue
            settings["address_space"] = ceiling * MIB
            retry = run_child(settings, args.wall_seconds)
            if retry["status"] == "ok":
                entry["needs_mib"] = ceiling
                entry["escalated"] = retry
                break
            entry.setdefault("escalation_failed_at_mib", []).append(ceiling)
    sink.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    sink.flush()
    return entry


def _summary_line(entry: dict[str, Any]) -> str:
    bits = [entry["label"], entry["file"], entry["kind"]]
    if entry.get("page") is not None:
        bits.append(f"p{entry['page'] + 1}")
    if entry.get("dpi"):
        bits.append(f"{entry['dpi']}dpi")
    bits.append(entry["status"])
    bits.append(f"{entry['wall_s']}s")
    bits.append(f"rss={entry['ru_maxrss_kib'] // 1024}MiB")
    if "needs_mib" in entry:
        bits.append(f"needs>={entry['needs_mib']}MiB")
    return " ".join(str(bit) for bit in bits)


def cmd_run(args: argparse.Namespace) -> int:
    results = Path(args.results)
    results.parent.mkdir(parents=True, exist_ok=True)
    done: set[tuple] = set()
    if results.exists():
        for line in results.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(_key(json.loads(line)))
    escalate = sorted(int(value) for value in args.escalate.split(",") if value.strip())
    dpis = [int(value) for value in args.dpi.split(",") if value.strip()]
    wanted_pages = None if not args.pages else {int(value) - 1 for value in args.pages.split(",")}
    with results.open("a", encoding="utf-8") as sink:
        if not args.skip_baseline:
            base = {"label": args.label, "file": "-", "kind": "baseline", "pdf": "-", "mode": "baseline"}
            entry = _measure(base, args, done, sink, [])
            if entry:
                print(_summary_line(entry), flush=True)
        for path in args.inputs:
            pdf = Path(path).resolve()
            name = pdf.name
            scan = _measure(
                {"label": args.label, "file": name, "kind": "scan", "pdf": str(pdf), "mode": "scan"},
                args, done, sink, escalate,
            )
            if scan is not None:
                print(_summary_line(scan), flush=True)
            else:
                scan = _load_scan(results, args.label, name, args.address_space_mib)
            if scan is None or scan.get("status") != "ok":
                print(f"skip {name}: no scan", flush=True)
                continue
            for page in scan["pages"]:
                index = page["page"]
                if wanted_pages is not None and index not in wanted_pages:
                    continue
                for dpi in dpis:
                    base = {
                        "label": args.label, "file": name, "kind": "render", "pdf": str(pdf),
                        "mode": "render", "page": index, "dpi": dpi, "pipeline": args.pipeline,
                    }
                    entry = _measure(base, args, done, sink, escalate)
                    if entry:
                        print(_summary_line(entry), flush=True)
                if not args.no_extract:
                    base = {
                        "label": args.label, "file": name, "kind": "extract", "pdf": str(pdf),
                        "mode": "extract", "page": index,
                    }
                    entry = _measure(base, args, done, sink, escalate)
                    if entry:
                        print(_summary_line(entry), flush=True)
    return 0


def _load_scan(results: Path, label: str, name: str, ceiling_mib: int) -> dict[str, Any] | None:
    for line in results.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if (item["label"], item["file"], item["kind"], item["ceiling_mib"]) == (label, name, "scan", ceiling_mib):
            return item
    return None


# --------------------------------------------------------------------------------------
# Tables and the fit
# --------------------------------------------------------------------------------------


def _load(results: str, labels: list[str] | None) -> list[dict[str, Any]]:
    items = [json.loads(line) for line in Path(results).read_text(encoding="utf-8").splitlines() if line.strip()]
    return [item for item in items if not labels or item["label"] in labels]


def _mm(page: dict[str, Any]) -> tuple[int, int]:
    return (
        round(page["w_pt"] * MM_PER_INCH / PT_PER_INCH),
        round(page["h_pt"] * MM_PER_INCH / PT_PER_INCH),
    )


def _size_class(page: dict[str, Any]) -> str:
    long_mm, short_mm = sorted(_mm(page), reverse=True)
    return f"{long_mm}x{short_mm}"


def _mib(kib: int | None) -> str:
    return "-" if kib is None else f"{kib / 1024:.0f}"


def _best(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The highest-dpi job that completed under the ceiling."""
    done = [entry for entry in entries if entry["status"] == "ok"]
    return max(done, key=lambda entry: entry["dpi"]) if done else None


def _index(items: list[dict[str, Any]]) -> dict[tuple, Any]:
    table: dict[tuple, Any] = {}
    for item in items:
        if item["kind"] == "render":
            table[(item["label"], item["file"], "render", item["page"], item["dpi"], item.get("pipeline"))] = item
        elif item["kind"] == "extract":
            table[(item["label"], item["file"], "extract", item["page"])] = item
        elif item["kind"] == "scan":
            table[(item["label"], item["file"], "scan")] = item
    return table


def _state(entry: dict[str, Any] | None) -> str:
    """Why a job has no figures: its status, with the ceiling that let it pass if one did."""
    if entry is None:
        return "-"
    suffix = f" (ok at {entry['needs_mib']} MiB)" if "needs_mib" in entry else ""
    return entry["status"].upper() + suffix


def _triple(entries: list[dict[str, Any] | None], field: Callable[[dict[str, Any]], str]) -> str:
    return " / ".join(field(entry) if entry is not None and entry["status"] == "ok" else _state(entry) for entry in entries)


def cmd_table(args: argparse.Namespace) -> int:
    labels = args.label or None
    items = _load(args.results, labels)
    table = _index(items)
    dpis = [int(value) for value in args.dpi.split(",")]
    files = sorted({(item["label"], item["file"]) for item in items if item["kind"] == "scan"})
    for label, name in files:
        scan = table[(label, name, "scan")]
        if scan.get("status") != "ok":
            print(f"\n{label} / {name}: scan {scan['status']}\n")
            continue
        print(f"\n#### {label} / {name} ({scan['page_count']} pages)\n")
        if args.by == "page":
            _table_pages(table, label, name, scan, dpis, args.pipeline)
        else:
            _table_classes(table, label, name, scan, dpis, args.pipeline)
    return 0


def _jobs(table: dict[tuple, Any], label: str, name: str, index: int, dpis: list[int], pipeline: str) -> list[Any]:
    return [table.get((label, name, "render", index, dpi, pipeline)) for dpi in dpis]


def _sizes(best: dict[str, Any] | None) -> tuple[str, str, str, str]:
    if best is None:
        return ("-", "-", "-", "-")
    return (
        str(best["preview"]["png_bytes"]),
        str(best["thumbnail"]["png_bytes"]),
        str(best["tile_pyramid"]["tiles"]),
        str(best["tile_pyramid"]["png_bytes"]),
    )


def _table_pages(table: dict[tuple, Any], label: str, name: str, scan: dict[str, Any], dpis: list[int], pipeline: str) -> None:
    dpi_text = "/".join(str(dpi) for dpi in dpis)
    print(f"| p | mm | elements | Mpx at {dpis[0]} | render s at {dpi_text} dpi | peak RSS MiB at {dpi_text} | preview B | thumbnail B | tiles | tiles B | at dpi | words | lines | extract s | extract RSS MiB |")
    print("| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for page in scan["pages"]:
        index = page["page"]
        jobs = _jobs(table, label, name, index, dpis, pipeline)
        first = jobs[0]
        mpx = f"{first['mpx']:.2f}" if first is not None and first["status"] == "ok" else _state(first)
        best = _best([job for job in jobs if job is not None])
        sizes = _sizes(best)
        seconds = _triple(jobs, lambda e: f"{e['wall_s']:.1f}")
        rss = " / ".join(_mib(job["ru_maxrss_kib"]) if job is not None else "-" for job in jobs)
        extract = table.get((label, name, "extract", index))
        if extract is not None and extract["status"] == "ok":
            ext = f"{extract['words']} | {extract['lines']} | {extract['wall_s']:.1f} | {_mib(extract['ru_maxrss_kib'])}"
        else:
            ext = f"- | - | {_state(extract)} | {_mib(extract['ru_maxrss_kib']) if extract else '-'}"
        at = best["dpi"] if best is not None else "-"
        print(
            f"| {index + 1} | {'x'.join(str(v) for v in _mm(page))} | {page['elements']} | {mpx} | {seconds} | {rss} |"
            f" {sizes[0]} | {sizes[1]} | {sizes[2]} | {sizes[3]} | {at} | {ext} |"
        )


def _stats(values: list[float], digits: int = 1) -> str:
    if not values:
        return "-"
    return f"{min(values):.{digits}f} / {statistics.median(values):.{digits}f} / {max(values):.{digits}f}"


def _table_classes(table: dict[tuple, Any], label: str, name: str, scan: dict[str, Any], dpis: list[int], pipeline: str) -> None:
    classes: dict[str, list[dict[str, Any]]] = {}
    for page in scan["pages"]:
        classes.setdefault(_size_class(page), []).append(page)
    dpi_text = "/".join(str(dpi) for dpi in dpis)
    print(
        f"| mm | pages | max elements | Mpx at {dpis[0]} | worst render s at {dpi_text} dpi | worst peak RSS MiB at {dpi_text} |"
        " preview B median (max) | thumbnail B median (max) | tiles B median (max) | worst extract s | worst extract RSS MiB | jobs over the ceiling |"
    )
    print("| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |")
    ordered = sorted(classes.items(), key=lambda kv: -int(kv[0].split("x")[0]) * int(kv[0].split("x")[1]))
    for key, pages in ordered:
        per_dpi = [[table.get((label, name, "render", p["page"], dpi, pipeline)) for p in pages] for dpi in dpis]
        flat = [job for jobs in per_dpi for job in jobs if job is not None]
        good_first = [job for job in per_dpi[0] if job is not None and job["status"] == "ok"]
        mpx = f"{max(job['mpx'] for job in good_first):.2f}" if good_first else "-"
        seconds = " / ".join(
            f"{max((job['wall_s'] for job in jobs if job is not None and job['status'] == 'ok'), default=0):.1f}" for jobs in per_dpi
        )
        rss = " / ".join(
            _mib(max((job["ru_maxrss_kib"] for job in jobs if job is not None), default=None)) for jobs in per_dpi
        )
        bests = [_best([j for j in (table.get((label, name, "render", p["page"], dpi, pipeline)) for dpi in dpis) if j is not None]) for p in pages]
        bests = [b for b in bests if b is not None]

        def med(selector: Callable[[dict[str, Any]], int]) -> str:
            values = [selector(b) for b in bests]
            return f"{int(statistics.median(values))} ({max(values)})" if values else "-"

        extracts = [table.get((label, name, "extract", p["page"])) for p in pages]
        extracts = [e for e in extracts if e is not None]
        good = [e for e in extracts if e["status"] == "ok"]
        over = sum(1 for job in flat if job["status"] != "ok") + sum(1 for e in extracts if e["status"] != "ok")
        print(
            f"| {key} | {len(pages)} | {max(p['elements'] for p in pages)} | {mpx} | {seconds} | {rss} |"
            f" {med(lambda b: b['preview']['png_bytes'])} | {med(lambda b: b['thumbnail']['png_bytes'])} |"
            f" {med(lambda b: b['tile_pyramid']['png_bytes'])} |"
            f" {max((e['wall_s'] for e in good), default=0):.1f} | {_mib(max((e['ru_maxrss_kib'] for e in extracts), default=None))} | {over} |"
        )


def cmd_levels(args: argparse.Namespace) -> int:
    """The tile pyramid of one render job, level by level."""
    for item in _load(args.results, [args.label]):
        if (
            item["kind"] == "render"
            and item["file"] == args.file
            and item["page"] == args.page - 1
            and item["dpi"] == args.dpi
            and item.get("pipeline") == args.pipeline
            and item["status"] == "ok"
        ):
            print(f"{args.label} {args.file} p{args.page} {args.dpi} dpi, {item['mpx']} Mpx: preview {item['preview']['png_bytes']} B, thumbnail {item['thumbnail']['png_bytes']} B")
            print("| level | px | tiles | PNG bytes | largest tile B |")
            print("| ---: | --- | ---: | ---: | ---: |")
            for level in item["tile_pyramid"]["levels"]:
                print(f"| {level['level']} | {level['w']}x{level['h']} | {level['tiles']} | {level['png_bytes']} | {level['largest_tile_png_bytes']} |")
            print(f"| all | | {item['tile_pyramid']['tiles']} | {item['tile_pyramid']['png_bytes']} | |")
            return 0
    print("no such job", file=sys.stderr)
    return 1


def _least_squares(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """slope, intercept, max residual of ``y = slope * x + intercept``."""
    count = len(points)
    mean_x = sum(x for x, _ in points) / count
    mean_y = sum(y for _, y in points) / count
    sxx = sum((x - mean_x) ** 2 for x, _ in points)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / sxx if sxx else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept, max(abs(y - (slope * x + intercept)) for x, y in points)


def cmd_fit(args: argparse.Namespace) -> int:
    """Peak RSS and peak address space against megapixels, for render jobs that passed."""
    items = _load(args.results, args.label or None)
    for pipeline in PIPELINES:
        jobs = [i for i in items if i["kind"] == "render" and i.get("pipeline") == pipeline and i["status"] == "ok"]
        # Pages whose job passed only after escalation are included through their escalated record.
        jobs += [
            {**i, **i["escalated"], "status": "ok"}
            for i in items
            if i["kind"] == "render" and i.get("pipeline") == pipeline and "escalated" in i
        ]
        if len(jobs) < 3:
            continue
        for field, name in (("ru_maxrss_kib", "ru_maxrss"), ("vm_hwm_kib", "VmHWM"), ("vm_peak_kib", "VmPeak")):
            points = [(j["mpx"], j[field] / 1024) for j in jobs if j.get(field)]
            if len(points) < 3:
                continue
            slope, intercept, residual = _least_squares(points)
            print(
                f"{pipeline:6s} {name:10s} n={len(points):3d}  MiB = {slope:6.2f} x Mpx + {intercept:6.1f}"
                f"   (max residual {residual:.1f} MiB; {slope * 1.048576:.2f} bytes per pixel)"
            )
        big = max(jobs, key=lambda j: j["mpx"])
        print(f"       largest passing: {big['mpx']} Mpx, ceiling {big['ceiling_mib']} MiB")
    return 0


# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "child":
        return child_main(argv[1])

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="measure every page of every input")
    run.add_argument("inputs", nargs="+", help="PDF files")
    run.add_argument("--label", required=True, help="name of the input set in the results")
    run.add_argument("--results", required=True, help="JSON-lines file to append to (resumes: finished jobs are skipped)")
    run.add_argument("--address-space-mib", type=int, default=DEFAULT_ADDRESS_SPACE_MIB)
    run.add_argument("--cpu-seconds", type=int, default=DEFAULT_CPU_SECONDS)
    run.add_argument("--wall-seconds", type=float, default=DEFAULT_WALL_SECONDS)
    run.add_argument("--dpi", default=",".join(str(d) for d in DEFAULT_DPIS), help="comma list")
    run.add_argument("--pipeline", choices=PIPELINES, default="lean")
    run.add_argument("--escalate", default="", help="comma list of larger ceilings (MiB) tried in turn for a failed job")
    run.add_argument("--pages", default="", help="comma list of 1-based pages (default all)")
    run.add_argument("--no-extract", action="store_true")
    run.add_argument("--skip-baseline", action="store_true")
    run.set_defaults(func=cmd_run)

    table = commands.add_parser("table", help="Markdown tables from a results file")
    table.add_argument("--results", required=True)
    table.add_argument("--label", action="append")
    table.add_argument("--by", choices=("page", "class"), default="class")
    table.add_argument("--dpi", default=",".join(str(d) for d in DEFAULT_DPIS))
    table.add_argument("--pipeline", choices=PIPELINES, default="lean")
    table.set_defaults(func=cmd_table)

    levels = commands.add_parser("levels", help="the tile pyramid of one render job")
    levels.add_argument("--results", required=True)
    levels.add_argument("--label", required=True)
    levels.add_argument("--file", required=True)
    levels.add_argument("--page", type=int, required=True, help="1-based")
    levels.add_argument("--dpi", type=int, default=200)
    levels.add_argument("--pipeline", choices=PIPELINES, default="lean")
    levels.set_defaults(func=cmd_levels)

    fit = commands.add_parser("fit", help="peak memory against megapixels")
    fit.add_argument("--results", required=True)
    fit.add_argument("--label", action="append")
    fit.set_defaults(func=cmd_fit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
