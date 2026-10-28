"""VS-1: the PDFs agree with the answer key, and the key states what the task requires of it.

`check_vs1` re-reads every claim of the key from the PDF bytes with pypdf, pdfplumber and
pypdfium2 (sizes, stamps, titles, annotations, scans, byte identity, text and style changes,
the permit and specification tables, split parts, duplicates). The explicit tests below name the
facts a later lane relies on, so that deleting one from the key is a red test and not a silent loss.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber
import pypdf
import pypdfium2 as pdfium
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import cmp_fixtures_support as support  # noqa: E402


@pytest.fixture(scope="module")
def files() -> dict[str, bytes]:
    return support.load_files()


@pytest.fixture(scope="module")
def key(files) -> dict:
    return support.load_key(files, "vs1")


def transition(key: dict, a: str, b: str) -> dict:
    return next(t for t in key["transitions"] if t["from"] == a and t["to"] == b)


def sheet(key: dict, a: str, b: str, sheet_id: str) -> dict:
    return next(s for s in transition(key, a, b)["sheets"] if s["sheet_id"] == sheet_id)


def kinds(entry: dict) -> set[str]:
    return {c["kind"] for c in entry["text_changes"] + entry["graphic_changes"]}


def test_every_claim_of_the_key_is_read_back_from_the_pdfs(files, key) -> None:
    assert support.check_vs1(files, key) == []


# -- shape of the set ---------------------------------------------------------------------


def test_five_versions_of_one_designation_with_rising_labels_and_dates(key) -> None:
    versions = key["versions"]
    assert [v["id"] for v in versions] == ["V1", "V2", "V3", "V4", "V5"]
    assert {v["designation"] for v in versions} == {"СИНТ-01-ЭМ"}
    assert [v["label"] for v in versions] == ["Изм.0", "Изм.1", "Изм.2", "Изм.3", "Изм.4"]
    dates = [v["date"] for v in versions]
    assert dates == ["15.01.2026", "12.02.2026", "10.03.2026", "07.04.2026", "05.05.2026"]
    assert [v["page_count"] for v in versions] == [6, 6, 6, 6, 8]


def test_the_set_has_a4_a3_and_one_a1_sheet_and_cyrillic_stamps(key) -> None:
    formats = [p["format"] for p in key["versions"][0]["pages"]]
    assert formats.count("A1") == 1 and "A3" in formats and "A4" in formats
    for version in key["versions"]:
        for page in version["pages"]:
            if page["text_layer"]:
                assert page["stamp"]["designation"] == "СИНТ-01-ЭМ"
                assert page["stamp"]["revision"].startswith("Изм.")
                assert any("А" <= ch <= "я" for ch in page["stamp"]["title"])


def test_every_status_and_every_channel_is_exercised_by_some_transition(key) -> None:
    statuses = {s["expected_status"] for t in key["transitions"] for s in t["sheets"]}
    assert statuses == set(key["statuses"]) == {"same", "same_zones_changed", "different", "needs_review", "added", "removed"}
    required = {c for t in key["transitions"] for s in t["sheets"] for c in s["channels_with_differences"]}
    assert required == set(key["channels"])


def test_the_sheet_identity_table_maps_every_page_of_every_version(key) -> None:
    identity = {s["sheet_id"]: s for s in key["sheet_identity"]}
    assert identity["E06"]["pages"] == {"V1": [6], "V2": [6]}
    assert identity["E07"]["pages"] == {"V3": [6], "V4": [6], "V5": [7]}
    assert identity["E05"]["pages"]["V5"] == [5, 6]
    assert identity["E03"]["pages"]["V5"] == [3, 8]
    assert identity["E04"]["pages"]["V3"] == [4] and identity["E04"]["pages"]["V4"] == [4]


# -- V1 -> V2 -----------------------------------------------------------------------------


def test_v1_v2_moved_label_changed_cell_stamp_revision_and_annotation(key) -> None:
    e02 = sheet(key, "V1", "V2", "E02")
    moved = [c for c in e02["text_changes"] if c["kind"] == "text_moved"]
    assert [(c["before"], c["after"]) for c in moved] == [("ЩО-1", "ЩО-1")]
    assert moved[0]["bbox_before"] != moved[0]["bbox_after"]

    e03 = sheet(key, "V1", "V2", "E03")
    cells = [c for c in e03["text_changes"] if c["kind"] == "text_changed" and c["zone"] == "content"]
    assert [(c["before"], c["after"]) for c in cells] == [("3,0", "3,6")]

    e04 = sheet(key, "V1", "V2", "E04")
    assert e04["expected_status"] == "same_zones_changed"
    assert e04["channels_with_differences"] == ["zones"]
    stamp = {c["before"]: c["after"] for c in e04["text_changes"]}
    assert stamp == {"Изм.0": "Изм.1", "15.01.2026": "12.02.2026"}
    assert e04["byte_identical_page"] is False and not e04["graphic_changes"]

    e05 = sheet(key, "V1", "V2", "E05")
    assert e05["expected_status"] == "different" and e05["channels_with_differences"] == ["annotations"]
    added = e05["annotation_changes"]["added"]
    assert len(added) == 1 and added[0]["kind"] == "text" and not e05["text_changes"] and not e05["graphic_changes"]


def test_the_pdf_annotations_are_read_by_pypdf(files, key) -> None:
    v2 = pypdf.PdfReader(io.BytesIO(files["vs1/v2.pdf"]))
    v1 = pypdf.PdfReader(io.BytesIO(files["vs1/v1.pdf"]))
    assert "/Annots" not in v1.pages[4]
    annots = [a.get_object() for a in v2.pages[4]["/Annots"]]
    assert [str(a["/Subtype"]) for a in annots] == ["/Text"]
    assert str(annots[0]["/Contents"]) == "Проверить трассу лотка по оси Б"
    v3 = pypdf.PdfReader(io.BytesIO(files["vs1/v3.pdf"]))
    squares = [a.get_object() for a in v3.pages[5]["/Annots"]]
    assert [str(a["/Subtype"]) for a in squares] == ["/Square"]


# -- V2 -> V3 -----------------------------------------------------------------------------


def test_v2_v3_added_and_removed_sheet_added_line_colour_and_thickness(key) -> None:
    t = transition(key, "V2", "V3")
    assert t["status_counts"]["added"] == 1 and t["status_counts"]["removed"] == 1
    assert sheet(key, "V2", "V3", "E07")["expected_status"] == "added"
    assert sheet(key, "V2", "V3", "E06")["expected_status"] == "removed"
    assert "graphic_added" in kinds(sheet(key, "V2", "V3", "E02"))
    e05 = sheet(key, "V2", "V3", "E05")
    assert kinds(e05) == {"text_changed", "graphic_color"} and e05["channels_with_differences"] == ["color", "zones"]
    colours = {(tuple(c["before"]), tuple(c["after"])) for c in e05["graphic_changes"]}
    assert colours == {((0.8, 0.0, 0.0), (0.0, 0.35, 0.8))}
    e04 = sheet(key, "V2", "V3", "E04")
    widths = [(c["before"], c["after"]) for c in e04["graphic_changes"]]
    assert widths == [(0.5, 1.5)] and "color" in e04["channels_with_differences"]
    assert "geometry" in e04["channels_without_differences"]


# -- V3 -> V4: permit, scan ---------------------------------------------------------------


def test_v3_v4_permit_table_has_all_four_reconciliation_classes(key) -> None:
    permit = transition(key, "V3", "V4")["permit"]
    assert permit["table_title"] == "Разрешение на внесение изменений"
    assert permit["classes"] == {
        "declared_and_found": ["E05"], "declared_not_found": ["E07"],
        "declared_unverifiable_scan": ["E04"], "found_not_declared": ["E03"],
    }
    by_class = {d["reconciliation"]: d for d in permit["declared"]}
    assert by_class["declared_and_found"]["evidence_ids"] == ["E05.L.tray.branch"]
    assert by_class["declared_not_found"]["evidence_ids"] == []
    assert permit["found_not_declared"] == [{"sheet_id": "E03", "text_change_ids": ["E03.table.r2c3"]}]
    silent = sheet(key, "V3", "V4", "E03")
    assert "zones" in silent["channels_without_differences"], "the silent change did not raise the stamp revision"


def test_v3_v4_the_scan_page_has_no_text_layer_and_is_needs_review(files, key) -> None:
    entry = sheet(key, "V3", "V4", "E04")
    assert entry["expected_status"] == "needs_review" and entry["reasons"] == ["NO_TEXT_LAYER"]
    assert "text_coverage" in entry["channels_with_differences"]
    assert entry["text_changes"] == [] and entry["changes_in_pixels"]
    page = key["versions"][3]["pages"][3]
    assert page["scan"] is True and page["text_layer"] is False and page["image_sha256"]
    v4 = files["vs1/v4.pdf"]
    with pdfplumber.open(io.BytesIO(v4)) as plumber:
        assert plumber.pages[3].chars == [] and len(plumber.pages[3].images) == 1
        assert plumber.pages[2].chars, "the neighbouring page keeps its text layer"
    document = pdfium.PdfDocument(v4)
    assert document[3].get_textpage().count_chars() == 0
    assert document[2].get_textpage().count_chars() > 100


# -- V4 -> V5 -----------------------------------------------------------------------------


def test_v4_v5_split_duplicate_specification_and_identical_sheet(key) -> None:
    split = sheet(key, "V4", "V5", "E05")
    assert split["relation"] == "split" and split["expected_status"] == "needs_review"
    assert split["to_pages"] == [5, 6] and [p["format"] for p in split["parts"]] == ["A2", "A2"]
    assert all(p["content_changes_in_region"] == [] and p["scale"] == 1.0 for p in split["parts"])
    assert split["parts"][1]["translation_x"] == -1193.39
    assert sum(p["operations_in_region"] for p in split["parts"]) > 100

    duplicate = sheet(key, "V4", "V5", "E03")
    assert duplicate["to_pages"] == [3, 8] and duplicate["duplicate_pages_identical"] is True
    assert duplicate["reasons"] == ["DUPLICATE_SHEET"] and duplicate["expected_status"] == "needs_review"

    spec = sheet(key, "V4", "V5", "E07")["spec_positions"]
    assert [r["position"] for r in spec["added"]] == ["7"]
    assert [r["position"] for r in spec["removed"]] == ["6"]
    assert spec["changed"] == [{"position": "3", "field": "quantity", "before": "2", "after": "3"}]
    assert spec["columns"][:4] == ["Поз.", "Обозначение", "Наименование и тех. характеристика", "Кол."]

    identical = sheet(key, "V4", "V5", "E02")
    assert identical["expected_status"] == "same" and identical["byte_identical_page"] is True
    assert sheet(key, "V3", "V4", "E02")["byte_identical_page"] is True


def test_the_identical_sheets_really_are_the_same_page(files) -> None:
    pages = {}
    for name in ("v3", "v4", "v5"):
        reader = pypdf.PdfReader(io.BytesIO(files[f"vs1/{name}.pdf"]))
        pages[name] = reader.pages[1].get_contents().get_data()
    assert pages["v3"] == pages["v4"] == pages["v5"]
    v2 = pypdf.PdfReader(io.BytesIO(files["vs1/v2.pdf"])).pages[1].get_contents().get_data()
    assert v2 != pages["v3"]


def test_the_split_parts_carry_the_old_annotation_once(files) -> None:
    reader = pypdf.PdfReader(io.BytesIO(files["vs1/v5.pdf"]))
    assert len(reader.pages[4]["/Annots"]) == 1 and "/Annots" not in reader.pages[5]
    assert [float(v) for v in reader.pages[4].mediabox] == [0, 0, 1190.55, 1683.78]


def test_the_optional_content_layer_is_declared_and_used_by_the_lighting_plan(files) -> None:
    reader = pypdf.PdfReader(io.BytesIO(files["vs1/v1.pdf"]))
    properties = reader.trailer["/Root"]["/OCProperties"]
    assert len(properties["/OCGs"]) == 1 and "/OFF" not in properties["/D"]
    assert b"/OC /OC1 BDC" in reader.pages[1].get_contents().get_data()
    assert str(properties["/OCGs"][0].get_object()["/Name"]) == "Оси и размеры"


def test_dashes_and_the_hatch_pattern_are_in_the_lighting_plan(files) -> None:
    reader = pypdf.PdfReader(io.BytesIO(files["vs1/v1.pdf"]))
    page = reader.pages[1]
    content = page.get_contents().get_data()
    assert b"] 0 d" in content and b"/Pattern cs /P1 scn" in content
    pattern = page["/Resources"]["/Pattern"]["/P1"].get_object()
    assert int(pattern["/PatternType"]) == 1
