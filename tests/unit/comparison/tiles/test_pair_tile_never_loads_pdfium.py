"""The API process never calls PDFium for a pair tile (ADR-0025 decision 9 and the addendum of 2026-10-27; wave brief C1).

Two proofs, as for the page tile: a static scan of the package (no PDF library, no process of its own), and a fresh
interpreter that imports the composition root and runs the whole pipeline -- the bounded mask reader, the reduction, the
warp of page B, the aligned blocks, the overlay and the PNG encode -- and then looks at ``sys.modules``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "src" / "auditmanager" / "comparison" / "tiles"
BANNED = {"pypdfium2", "pdfplumber", "pypdf", "fitz", "pymupdf", "subprocess", "multiprocessing", "ctypes", "pdfminer"}
BANNED_PREFIXES = ("auditmanager.analysis", "auditmanager.ingest")


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_no_module_of_the_package_imports_a_pdf_library_or_starts_a_process() -> None:
    files = sorted(PACKAGE.glob("*.py"))
    assert len(files) >= 12
    offenders = {}
    for path in files:
        bad = {name for name in _imports(path) if name.split(".")[0] in BANNED or name.startswith(BANNED_PREFIXES)}
        if bad:
            offenders[path.name] = sorted(bad)
    assert offenders == {}


def test_that_scan_fails_on_a_module_that_imports_pdfium(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text("import pypdfium2\nfrom auditmanager.analysis.public import PdfiumDocument\n")
    assert {n for n in _imports(probe) if n.split(".")[0] in BANNED or n.startswith(BANNED_PREFIXES)} == {
        "pypdfium2", "auditmanager.analysis.public"}


_PROGRAM = r"""
import sys, struct, zlib
sys.path.insert(0, %(src)r)
import numpy
import auditmanager.bootstrap.composition  # the whole product's imports
from auditmanager.comparison.tiles import aligned, compose, grid, mask, reduction, warp

levels = [(1300, 900, 3, 2), (650, 450, 1, 1)]
summary = {"width_pt": 1300.0, "height_pt": 900.0, "raster": {"dpi": 72, "width_px": 1300, "height_px": 900},
           "tiles": {"tile_px": 512, "levels": [
               {"level": 0, "width_px": 1300, "height_px": 900, "columns": 3, "rows": 2, "stored": False},
               {"level": 1, "width_px": 650, "height_px": 450, "columns": 2, "rows": 1, "stored": False}]}}
g = grid.PageGrid.from_summary(summary)
page = numpy.full((900, 1300, 3), 255, numpy.uint8); page[100:120, 100:120] = 0
def fetch(level, column, row):
    box = g.tile_box(level, column, row)
    if box is None: return None
    image = page if level == 0 else page[::2, ::2]
    return image[box[1]:box[3], box[0]:box[2]].copy()
to_a = grid.Affine.from_sequence([1, 0, 0, 1, -10, 0])
b = aligned.warp_aligned(fetch, warp.SourceBudget(), blocks=[aligned.AlignedBlock(95, 95, 125, 125, 10, 0)], grid_a=g,
                         level_a=0, origin=(0, 0), size=(512, 512), grid_b=g, to_a=to_a)
planes = numpy.zeros((8, 900, 1300), bool); planes[0, 100, 100] = True
blob = struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, 1300, 900) + zlib.compress(numpy.packbits(planes, axis=-1).tobytes())
m = mask.read_mask(blob)
xs, xe = reduction.axis_starts(0, 512, 1, 1, 1300); ys, ye = reduction.axis_starts(0, 512, 1, 1, 900)
hit = reduction.reduce_max(m.plane("main"), xs, xe, ys, ye)
image = compose.paint_layers(compose.min_composite(b, b), {"main": hit}, (0, 0))
assert compose.decode_png(compose.encode_png(image)).shape == (512, 512, 3)
loaded = sorted(n for n in sys.modules if n.split(".")[0] in {"pypdfium2", "pdfplumber", "pypdf", "fitz", "pdfminer"})
print("LOADED", loaded)
"""


def test_a_fresh_interpreter_runs_the_whole_pipeline_and_loads_no_pdf_library() -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-c", _PROGRAM % {"src": str(ROOT / "src")}],
        capture_output=True, text=True, timeout=120, cwd="/",
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().endswith("LOADED []"), result.stdout
