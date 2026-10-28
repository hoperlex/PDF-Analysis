#!/usr/bin/env python3
"""Time, memory and bytes of the comparison engine over a version set, per pair of adjacent versions
(`CMP-ENGINE-01`, ADR-0025 decisions 8 and 9, wave brief `CMP-WAVE-C1` section 4 item 5).

    comparison_engine.py [--set DIR] [--out RESULTS.jsonl] [--pairs v1:v2,v2:v3,v3:v4] [--work-dir DIR]
                         [--address-space-mib 768] [--keep-profiles]

For every adjacent transition it pairs the pages of the two versions **by the sheet number the page profile reads from
the stamp** (a number that is read on exactly one page of each version) and, for the pages for which no such number is
read, **by index** (the page at the same position), and runs the engine's child on each pair under the ceilings of
decision 8. Each record holds only numbers and words that name a state: ``transition``, ``a_page``, ``b_page``,
``paired_by`` (``sheet_number`` or ``index``), ``size_pt``, ``dpi``, ``path`` (``child`` or ``identical`` when the two
pages have the same content and no child is started), ``status``, ``reasons``, the child's ``wall_s``, ``cpu_s``,
``vm_hwm_kib`` (the child's own ``VmHWM``, its peak resident set: **this is the peak RSS**), ``vm_peak_kib`` (the child's
own ``VmPeak``, the quantity ``RLIMIT_AS`` limits), ``ru_maxrss_kib`` (the kernel's figure from ``wait4``, which here
includes the resident set of this parent at the moment of the ``fork`` -- the profile report's remark about ``ru_maxrss`` --
and is kept only to show that; do not read it as the child's peak), the number of ``differences`` and ``text_changes``, and ``mask_bytes``.
A summary closes the run: pairs by method, the worst wall time, the worst peak RSS and its page size, the total mask
bytes, and whether the worst peak passed the ceiling.

**The set is client-like data.** It is read by this program only; no page, word, text or raster is printed, written or
shown (the outcome of a pair holds before/after texts, which this script never touches: it counts them). Profiles are
built by the real page-profile children into a scratch directory that is deleted at the end. Nothing of the set is
committed. The run is one child at a time, never in parallel (the host is shared), and it stops when the free space of
the filesystem passes under 1.5 GiB.

Run it with the lane's interpreter: ``PYTHONPATH=$PWD/src .venv/bin/python tools/measure/comparison_engine.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIB = 1024 * 1024
STOP_FREE_BYTES = int(1.5 * 1024 * MIB)
DEFAULT_SET = "/root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA"


def _free_bytes(path: str) -> int:
    usage = shutil.disk_usage(path)
    return usage.free


def _profile_version(path: Path, runner: Any) -> list[Any]:
    """The typed profile of every page of one PDF, from the real children (one page at a time)."""
    from auditmanager.comparison.profile.models import PageProfileRow
    from auditmanager.comparison.profile.profiling import profile_page
    from auditmanager.comparison.profile.reader import PageProfileReader
    from pypdf import PdfReader

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with open(path, "rb") as handle:
        count = len(PdfReader(handle, strict=False).pages)
    pages = []
    for index in range(count):
        outcome = profile_page(runner, pdf_path=str(path), page_index=index, version_sha256=digest)
        row = PageProfileRow(
            page_profile_id="cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV", version_uid="ver_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            page_number=index + 1, content_key=outcome.content_key, algo_version="cmp-profile/1", status=outcome.status,
            reason=outcome.reason, summary=outcome.summary, profile_blob_id="blob_unused", preview_blob_id=None,
            thumbnail_blob_id=None, created_at=datetime.now(timezone.utc))
        if outcome.pack is not None:
            reader = PageProfileReader(None, None)  # type: ignore[arg-type]
            reader._blob = lambda blob_id, pack=outcome.pack: pack  # type: ignore[method-assign]
            data = reader.open_profile(row)
        else:
            from auditmanager.comparison.profile.models import PageProfileData

            data = PageProfileData(row=row, width_pt=0.0, height_pt=0.0, rotation=0, has_text_layer=False, scan=False,
                                   content_merkle=None)
        pages.append(data)
    return pages


def _pair_pages(a: list[Any], b: list[Any]) -> list[tuple[int, int, str]]:
    """``(a index, b index, method)``: by a sheet number read exactly once in each version, else by index."""
    def numbers(pages: list[Any]) -> dict[str, list[int]]:
        found: dict[str, list[int]] = {}
        for i, page in enumerate(pages):
            number = (page.stamp.sheet_number or "").strip()
            if number:
                found.setdefault(number, []).append(i)
        return found

    na, nb = numbers(a), numbers(b)
    pairs: dict[int, tuple[int, str]] = {}
    used_b: set[int] = set()
    for number, ia in na.items():
        ib = nb.get(number)
        if ib and len(ia) == 1 and len(ib) == 1:
            pairs[ia[0]] = (ib[0], "sheet_number")
            used_b.add(ib[0])
    out = []
    for i in range(len(a)):
        if i in pairs:
            out.append((i, pairs[i][0], "sheet_number"))
        elif i < len(b) and i not in used_b and i not in {p[0] for p in pairs.values()}:
            out.append((i, i, "index"))
    return out


def _record(transition: str, ia: int, ib: int, method: str, a: Any, b: Any, path_a: str, path_b: str,
            address_space_mib: int, work_dir: str) -> dict[str, Any]:
    from auditmanager.comparison.engine.service import compute_pair
    from auditmanager.comparison.profile.limits import ChildLimits

    record: dict[str, Any] = {
        "transition": transition, "a_page": ia + 1, "b_page": ib + 1, "paired_by": method,
        "size_pt": [round(a.width_pt, 1), round(a.height_pt, 1)],
        "raster": list(a.raster) if a.raster else None,
    }
    if a.row.status != "ready" or b.row.status != "ready":
        record.update(path="profile_not_ready", status=None, profile_status=[a.row.status, b.row.status])
        return record
    started = time.monotonic()
    computed = compute_pair(a, b, path_a=path_a, path_b=path_b, work_dir=work_dir,
                            child_limits=ChildLimits(address_space_mib * MIB, 300, 600.0))
    outcome = computed.outcome
    record.update(
        path="identical" if computed.end == "identical" else "child", end=computed.end, status=outcome["status"],
        reasons=[r for r in outcome["reasons"] if not r.startswith("UNCHECKED_CHANNEL")],
        channels={name: (c["state"], c.get("diffs")) for name, c in outcome["channels"].items()},
        differences=len(outcome["result"]["differences"]), text_changes=len(outcome["result"]["text_changes"]),
        mask_bytes=len(computed.mask) if computed.mask else 0, wall_total_s=round(time.monotonic() - started, 3),
    )
    if computed.child is not None:
        child = computed.child
        record.update(
            wall_s=child.wall_s, cpu_s=child.cpu_s, ru_maxrss_kib=child.max_rss_kib,
            vm_peak_kib=child.facts.get("vm_peak_kib"), vm_hwm_kib=child.facts.get("vm_hwm_kib"),
            child_status=child.status, job_s=child.facts.get("t_job_s"), marks=child.facts.get("marks"),
            bands=child.facts.get("bands"),
        )
    return record


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--set", default=DEFAULT_SET, help="the directory holding v1.pdf, v2.pdf, ...")
    parser.add_argument("--out", required=True, help="the JSON-lines file for the records (outside git)")
    parser.add_argument("--pairs", default="v1:v2,v2:v3,v3:v4")
    parser.add_argument("--work-dir", default=None, help="scratch directory (deleted at the end)")
    parser.add_argument("--address-space-mib", type=int, default=768)
    args = parser.parse_args(argv)

    from auditmanager.comparison.profile.runner import SubprocessChildRunner

    scratch = tempfile.mkdtemp(prefix="cmp-engine-measure-", dir=args.work_dir)
    os.environ["TMPDIR"] = scratch
    tempfile.tempdir = scratch
    records: list[dict[str, Any]] = []
    profiles: dict[str, list[Any]] = {}
    runner = SubprocessChildRunner()
    try:
        with open(args.out, "w", encoding="utf-8") as sink:
            for spec in args.pairs.split(","):
                left, right = spec.split(":")
                for name in (left, right):
                    if name not in profiles:
                        if _free_bytes(scratch) < STOP_FREE_BYTES:
                            print("STOP: under 1.5 GiB free", file=sys.stderr)
                            return 3
                        began = time.monotonic()
                        profiles[name] = _profile_version(Path(args.set) / f"{name}.pdf", runner)
                        print(f"profiled {name}: {len(profiles[name])} pages in {time.monotonic() - began:.1f} s", flush=True)
                pairs = _pair_pages(profiles[left], profiles[right])
                for ia, ib, method in pairs:
                    if _free_bytes(scratch) < STOP_FREE_BYTES:
                        print("STOP: under 1.5 GiB free", file=sys.stderr)
                        return 3
                    record = _record(f"{left}->{right}", ia, ib, method, profiles[left][ia], profiles[right][ib],
                                     str(Path(args.set) / f"{left}.pdf"), str(Path(args.set) / f"{right}.pdf"),
                                     args.address_space_mib, scratch)
                    records.append(record)
                    sink.write(json.dumps(record, ensure_ascii=True) + "\n")
                    sink.flush()
                    print(json.dumps({k: record.get(k) for k in (
                        "transition", "a_page", "b_page", "paired_by", "path", "status", "wall_s", "vm_hwm_kib", "vm_peak_kib", "mask_bytes")}),
                        flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    childs = [r for r in records if r.get("path") == "child"]
    worst_rss = max(childs, key=lambda r: r.get("vm_hwm_kib") or 0, default=None)
    worst_peak = max(childs, key=lambda r: r.get("vm_peak_kib") or 0, default=None)
    worst_wall = max(childs, key=lambda r: r.get("wall_s") or 0, default=None)
    summary = {
        "pairs": len(records),
        "by_method": {m: sum(1 for r in records if r["paired_by"] == m) for m in ("sheet_number", "index")},
        "by_path": {p: sum(1 for r in records if r.get("path") == p) for p in ("child", "identical", "profile_not_ready")},
        "statuses": {s: sum(1 for r in records if r.get("status") == s)
                     for s in sorted({r.get("status") for r in records if r.get("status")})},
        "worst_wall_s": worst_wall and {"wall_s": worst_wall["wall_s"], "size_pt": worst_wall["size_pt"], "raster": worst_wall["raster"]},
        "worst_peak_rss": worst_rss and {"vm_hwm_kib": worst_rss["vm_hwm_kib"], "vm_peak_kib": worst_rss["vm_peak_kib"],
                                         "size_pt": worst_rss["size_pt"], "raster": worst_rss["raster"]},
        "worst_vm_peak": worst_peak and {"vm_peak_kib": worst_peak["vm_peak_kib"], "vm_hwm_kib": worst_peak["vm_hwm_kib"],
                                         "size_pt": worst_peak["size_pt"], "raster": worst_peak["raster"]},
        "total_mask_bytes": sum(r.get("mask_bytes", 0) for r in records),
        "ceiling_kib": args.address_space_mib * 1024,
        "worst_vm_peak_under_ceiling": all((r.get("vm_peak_kib") or 0) < args.address_space_mib * 1024 for r in childs),
        "ended_without_result": [r["a_page"] for r in childs if r.get("child_status") != "ok"],
    }
    print("SUMMARY " + json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
