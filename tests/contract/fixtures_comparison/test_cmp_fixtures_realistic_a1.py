"""The realistic A1 sheet is generated on demand into a temporary directory and never committed.

Measured the way the product measures: `pypdfium2` page objects, a path counted by its segments
(`src/auditmanager/ingest/pdf_reader.py::_elements`).
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import sys
from pathlib import Path

import pypdf
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
import pytest
from PIL import ImageChops

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
SCRIPT = TOOLS_DIR / "comparison" / "realistic_a1.py"
for path in (str(TOOLS_DIR), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from comparison import realistic_a1  # noqa: E402


def reader_elements(page) -> tuple[int, int]:
    """(elements as the product's reader counts them, painted path objects) of a pypdfium2 page."""
    total = paths = 0
    pending = [(page.raw, False)]
    while pending:
        container, is_form = pending.pop()
        count = (pdfium_raw.FPDFFormObj_CountObjects if is_form else pdfium_raw.FPDFPage_CountObjects)(container)
        get = pdfium_raw.FPDFFormObj_GetObject if is_form else pdfium_raw.FPDFPage_GetObject
        for index in range(max(count, 0)):
            child = get(container, index)
            kind = pdfium_raw.FPDFPageObj_GetType(child) if child else None
            if kind == pdfium_raw.FPDF_PAGEOBJ_PATH:
                total += max(pdfium_raw.FPDFPath_CountSegments(child), 1)
                paths += 1
            else:
                total += 1
                if kind == pdfium_raw.FPDF_PAGEOBJ_FORM:
                    pending.append((child, True))
    return total, paths


@pytest.fixture(scope="module")
def sheets(tmp_path_factory) -> dict[str, Path]:
    directory = tmp_path_factory.mktemp("realistic_a1")
    first, second = directory / "sheet_a.pdf", directory / "sheet_b.pdf"
    report = realistic_a1.write(first, second)
    assert report["painted_paths"] >= 75_000
    return {"a": first, "b": second}


def test_the_sheet_is_written_where_the_caller_says_and_not_into_the_repository(sheets) -> None:
    for path in sheets.values():
        assert path.is_file() and path.stat().st_size > 1_000_000
        assert REPO_ROOT not in path.resolve().parents
    committed = sorted((REPO_ROOT / "fixtures" / "comparison").rglob("*.pdf"))
    assert committed and max(p.stat().st_size for p in committed) < 400_000, "an A1-sized file was committed"


def test_the_sheet_has_at_least_75000_drawing_elements_by_the_products_count(sheets) -> None:
    document = pdfium.PdfDocument(str(sheets["a"]))
    try:
        elements, paths = reader_elements(document[0])
    finally:
        document.close()
    assert elements >= 75_000 and paths >= 75_000
    expected = realistic_a1.generate()[0]
    assert (elements, paths) == (expected.elements, expected.painted_paths), "the generator's own count is exact"


def test_the_lighter_variant_lands_near_the_largest_real_page(tmp_path: Path) -> None:
    path = tmp_path / "light.pdf"
    realistic_a1.write(path, None, paint_ops=0)
    document = pdfium.PdfDocument(str(path))
    try:
        elements, paths = reader_elements(document[0])
    finally:
        document.close()
    assert 75_000 <= elements <= 80_000 and paths < 75_000


def test_rotate_cropbox_offset_and_one_hidden_optional_content_group(sheets) -> None:
    reader = pypdf.PdfReader(str(sheets["a"]))
    page = reader.pages[0]
    assert page.rotation == 90
    media, crop = [float(v) for v in page.mediabox], [float(v) for v in page.cropbox]
    assert media == [0.0, 0.0, 1683.78, 2383.94]
    assert crop != media and crop[0] > 0 and crop[1] > 0
    properties = reader.trailer["/Root"]["/OCProperties"]
    assert len(properties["/OCGs"]) == 1
    assert len(properties["/D"]["/OFF"]) == 1 and properties["/D"]["/OFF"][0].idnum == properties["/OCGs"][0].idnum
    assert b"/OC /OC1 BDC" in page.get_contents().get_data()
    document = pdfium.PdfDocument(str(sheets["a"]))
    try:
        width, height = document[0].get_size()
        assert document[0].get_rotation() == 90
        assert (round(width, 2), round(height, 2)) == (round(crop[3] - crop[1], 2), round(crop[2] - crop[0], 2))
    finally:
        document.close()


def test_the_text_is_strokes_so_the_page_has_no_text_layer(sheets) -> None:
    document = pdfium.PdfDocument(str(sheets["a"]))
    try:
        assert document[0].get_textpage().count_chars() == 0
    finally:
        document.close()
    content = pypdf.PdfReader(str(sheets["a"])).pages[0].get_contents().get_data()
    assert b" Tj" not in content and b"BT" not in content
    assert b"] 0 d" in content, "dashes"
    assert b"/Pattern cs" in content, "a tiling-pattern hatch"


def test_the_second_producer_draws_the_same_sheet_in_another_operator_order(sheets) -> None:
    data_a, data_b = sheets["a"].read_bytes(), sheets["b"].read_bytes()
    assert data_a != data_b
    page_a, page_b = pypdf.PdfReader(io.BytesIO(data_a)).pages[0], pypdf.PdfReader(io.BytesIO(data_b)).pages[0]
    content_a, content_b = page_a.get_contents().get_data(), page_b.get_contents().get_data()
    assert content_a != content_b and len(content_b) < len(content_a), "grouped by style, so fewer q/Q and state operators"
    producers = [str(pypdf.PdfReader(io.BytesIO(d)).metadata["/Producer"]) for d in (data_a, data_b)]
    assert producers[0] != producers[1]
    counts = []
    images = []
    for path in sheets.values():
        document = pdfium.PdfDocument(str(path))
        try:
            counts.append(reader_elements(document[0]))
            images.append(document[0].render(scale=0.25).to_pil().convert("L"))
        finally:
            document.close()
    assert counts[0] == counts[1], "the same marks"
    histogram = ImageChops.difference(*images).histogram()
    mean = sum(value * count for value, count in enumerate(histogram)) / sum(histogram)
    assert mean < 8.0, f"the two renderings differ by {mean:.2f} grey levels on average"
    assert images[0].tobytes() != images[1].tobytes(), "they are not pixel-identical either"


def test_generation_is_deterministic_across_processes(sheets) -> None:
    expected = hashlib.sha256(sheets["a"].read_bytes()).hexdigest()
    for seed in ("0", "777"):
        completed = subprocess.run(
            [sys.executable, "-c",
             "import hashlib, sys;"
             f"sys.path.insert(0, {str(TOOLS_DIR)!r});"
             "from comparison import realistic_a1;"
             "print(hashlib.sha256(realistic_a1.generate()[0].data).hexdigest())"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": seed})
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.strip() == expected


def test_the_command_line_writes_where_asked_and_refuses_the_repository(tmp_path: Path) -> None:
    target = tmp_path / "out" / "a1.pdf"
    completed = subprocess.run([sys.executable, str(SCRIPT), str(target), "--paint-ops", "0", "--elements", "76000"],
                               capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert completed.returncode == 0, completed.stderr
    assert target.is_file()
    inside = REPO_ROOT / "fixtures" / "comparison" / "must_not_exist.pdf"
    refused = subprocess.run([sys.executable, str(SCRIPT), str(inside)], capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert refused.returncode == 2 and not inside.exists()


def test_a_nearly_full_disk_is_refused_not_filled(tmp_path: Path, monkeypatch) -> None:
    import shutil
    from collections import namedtuple

    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: usage(100, 99, 1024))
    with pytest.raises(SystemExit, match="refusing to write"):
        realistic_a1.write(tmp_path / "x.pdf")
    assert not (tmp_path / "x.pdf").exists()
