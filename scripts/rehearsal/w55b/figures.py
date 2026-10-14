#!/usr/bin/env python3
"""Turn the phase figures under ``.local/rehearsal-w55b/figures/`` into the report's tables.

    python scripts/rehearsal/w55b/figures.py            # Markdown on stdout

Reads only what the other tools wrote (counts, sizes, timings, the context of each figure) and
prints one table per part. Every row carries the tree, the load average and ``MemAvailable`` of the
figure it comes from. Nothing here reads the stack, the document or the store.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402

MiB = 1024


def load(name: str) -> dict | None:
    path = common.FIGURES / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def ctx(figure: dict, key: str = "context") -> str:
    context = figure.get(key) or figure.get("context") or {}
    tree = context.get("tree", {})
    head = tree.get("head", "")[:8] + ("" if tree.get("clean", True) else " (dirty)")
    load_avg = "/".join(context.get("loadavg", []))
    available = context.get("mem_available_kib")
    return f"`{head}`, {load_avg}, {available // MiB if available else '?'} MiB"


def mib(kib: int | None) -> str:
    return "-" if kib is None else f"{kib / MiB:.1f}"


def upload_rows(names: list[str]) -> list[str]:
    rows = ["| phase | archive | answer | wall s | API `VmHWM` growth MiB | API sampled peak RSS MiB | API scope `memory.peak` MiB | Next `VmHWM` growth MiB | tree, load, MemAvailable at start |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for name in names:
        f = load(name)
        if f is None:
            continue
        web = f.get("web_process") or {}
        web_growth = (web["vmhwm_after_kib"] - web["vmhwm_after_reset_kib"]) if web else None
        peak = (f.get("scope_after") or {}).get("memory_peak")
        peak_text = f"{peak / common.MiB:.1f}" if peak else "-"
        rows.append(
            f"| {name} | {f['archive_bytes'] / common.MiB:.2f} MiB | {f['response']['status']} | {f['wall_seconds']} | "
            f"{mib(f['vmhwm_growth_kib'])} | {mib(f['sampled'].get('peak_rss_kib'))} | {peak_text} | "
            f"{mib(web_growth) if web else '-'} | {ctx(f, 'context_at_start')} |")
    return rows


def run_rows(names: list[str]) -> list[str]:
    rows = ["| phase | stage | status | `duration_ms` | wall s | RSS at start MiB | peak RSS MiB | growth MiB | metrics |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    keep = ("page_count", "crop_count", "crop_blob_count", "geometry_mismatch_page_count",
            "portal_block_count", "portal_image_block_count", "pages_without_text_layer",
            "recognised_entry_count")
    for name in names:
        f = load(name)
        if f is None:
            continue
        for stage in f["stages"]:
            memory = stage.get("memory") or {}
            metrics = ", ".join(f"{k} {stage['metrics'][k]}" for k in keep if k in stage["metrics"])
            reason = f" ({stage['error_reason']})" if stage.get("error_reason") else ""
            rows.append(f"| {name} | {stage['stage_id']} | {stage['status']}{reason} | "
                        f"{stage['metrics'].get('duration_ms', '-')} | {stage['wall_seconds']} | "
                        f"{mib(memory.get('rss_at_start_kib'))} | {mib(memory.get('peak_rss_kib'))} | "
                        f"{mib(memory.get('peak_growth_kib'))} | {metrics} |")
    return rows


def per_page_rows(names: list[str]) -> list[str]:
    rows = ["| phase | pass | count | RSS MiB after 1 / 10 / 50 / 100 / 250 / 500 / last | max MiB | seconds |",
            "| --- | --- | ---: | --- | ---: | ---: |"]
    for name in names:
        f = load(name)
        if f is None:
            continue
        for key, value in f.get("per_page", {}).items():
            after = value["rss_kib_after_k"]
            series = " / ".join(mib(after.get(k)) if k in after else "-" for k in ("1", "10", "50", "100", "250", "500", "last"))
            rows.append(f"| {name} | {key} | {value['count']} | {series} | {mib(value['max_rss_kib'])} | "
                        f"{value['last_t'] - value['first_t']:.1f} |")
    return rows


def browser_rows(names: list[str]) -> list[str]:
    rows = ["| phase | blocks | presses | first page ms | press ms min / median / max | last press ms | all loaded ms | DOM elements | JS heap MiB | crops loaded / chosen | tree, load, MemAvailable |",
            "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |"]
    for name in names:
        f = load(name)
        if f is None:
            continue
        presses = sorted(p["ms"] for p in f["presses"]) or [0]
        crops = f.get("crops") or {}
        rows.append(
            f"| {name} | {f['loaded']}/{f['block_count_shown']} | {len(f['presses'])} | {f['first_page_ms']} | "
            f"{presses[0]} / {presses[len(presses) // 2]} / {presses[-1]} | "
            f"{f['presses'][-1]['ms'] if f['presses'] else '-'} | {f['all_loaded_ms']} | {f['after_all']['dom_elements']} | "
            f"{f['after_all']['js_heap_used_bytes'] / common.MiB:.1f} | "
            f"{crops.get('loaded', '-')} / {crops.get('chosen', '-')} | {ctx(f)} |")
    return rows


def main() -> int:
    print("### Uploads\n")
    print("\n".join(upload_rows(["a-upload-1", "a-upload-2", "a-upload-dedup", "a-upload-via-bff", "b-upload",
                                 "b-upload-via-bff", "b-upload-via-bff-2", "c-upload", "v-upload"])))
    print("\n### Runs, stage by stage\n")
    print("\n".join(run_rows(["b-run-1", "b-run-2", "c-run", "v-run"])))
    print("\n### Resident set per page\n")
    print("\n".join(per_page_rows(["b-run-1", "b-run-2", "c-run", "v-run"])))
    print("\n### «Блоки» in the browser\n")
    print("\n".join(browser_rows(["b-browser-1", "b-browser-2-all-crops", "c-browser"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
