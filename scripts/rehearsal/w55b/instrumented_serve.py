#!/usr/bin/env python3
"""``infra/deploy/serve.py``, run unchanged, with the API's resident memory recorded per page.

The product's code is not edited. Before ``serve.py`` runs, four functions are wrapped in this
process only, each so that it appends one JSON line to ``REHEARSAL_PROGRESS_LOG`` after it
returns: the wall time, which stage called it (found by walking the caller frames for the
stage modules), the page (or crop) it handled and this process's ``VmRSS``:

* ``analysis.stages.extraction._extract_page`` -- the pdfplumber pass that BOTH
  ``source_preparation`` and ``page_geometry_extraction`` make over every page;
* ``analysis.geometry.render.PdfiumDocument.page_geometry`` -- the page-box check, every page;
* ``analysis.geometry.render.PdfiumDocument.render`` -- each crop's clip render;
* ``analysis.geometry.crops.CropPublisher.publish`` -- each crop's PNG published.

That is what lets the report give the resident set after page 10, 50, 100, 250 and 500 of each
stage's pass, the "before" figures a later fix can be measured against. The cost is one read of
``/proc/self/status`` and one short line written per page or crop.
"""

from __future__ import annotations

import json
import os
import runpy
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from auditmanager.analysis.geometry import crops as _crops  # noqa: E402
from auditmanager.analysis.geometry import render as _render  # noqa: E402
from auditmanager.analysis.stages import extraction as _extraction  # noqa: E402

_LOG = open(os.environ["REHEARSAL_PROGRESS_LOG"], "a", buffering=1, encoding="utf-8")  # noqa: SIM115
_LOCK = threading.Lock()
_STAGES = ("source_preparation", "page_geometry_extraction")


def _rss_kib() -> int:
    with open("/proc/self/status", encoding="ascii") as status:
        for line in status:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return -1


def _stage() -> str | None:
    frame = sys._getframe(2)
    while frame is not None:
        name = frame.f_globals.get("__name__", "")
        for stage in _STAGES:
            if name.endswith(stage):
                return stage
        frame = frame.f_back
    return None


def _record(what: str, number: int) -> None:
    line = json.dumps({"t": round(time.time(), 3), "what": what, "stage": _stage(),
                       "n": number, "rss_kib": _rss_kib()})
    with _LOCK:
        _LOG.write(line + "\n")


_extract_page = _extraction._extract_page


def _extract_page_recorded(page, page_number):
    result = _extract_page(page, page_number)
    _record("extract", page_number)
    return result


_page_geometry = _render.PdfiumDocument.page_geometry
_render_crop = _render.PdfiumDocument.render
_publish = _crops.CropPublisher.publish
_published = {"n": 0}


def _page_geometry_recorded(self, page_number):
    result = _page_geometry(self, page_number)
    _record("pagebox", page_number)
    return result


def _render_recorded(self, page_number, plan):
    result = _render_crop(self, page_number, plan)
    _record("render", page_number)
    return result


def _publish_recorded(self, png):
    result = _publish(self, png)
    with _LOCK:
        _published["n"] += 1
        number = _published["n"]
    _record("publish", number)
    return result


_extraction._extract_page = _extract_page_recorded
_render.PdfiumDocument.page_geometry = _page_geometry_recorded
_render.PdfiumDocument.render = _render_recorded
_crops.CropPublisher.publish = _publish_recorded

if __name__ == "__main__":
    sys.argv = [str(ROOT / "infra/deploy/serve.py")]
    runpy.run_path(str(ROOT / "infra/deploy/serve.py"), run_name="__main__")
