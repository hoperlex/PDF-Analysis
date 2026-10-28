"""Page profiles of the synthetic corpus against its answer keys (`CMP-PROFILE-01`).

Every page of the five VS-1 versions goes through the real children (a render child under 768 MiB and an
extraction child under 1024 MiB, one page each). The keys are authored next to the content that creates the
facts, so each assertion below is a test of the profile against something it did not produce: the sheet
number, the sheet title, the designation, the revision and the date from the stamp; the scan flag and the
missing text layer of the two scanned pages; the size, the annotation count; and, for the SP-1 pair, the
sheet numbers and titles of its twelve sheets.
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import numpy as np
import pytest
from PIL import Image

from auditmanager.comparison.profile import limits, pack
from auditmanager.comparison.profile.profiling import profile_page

PNG = b"\x89PNG\r\n\x1a\n"


def _pages(key: dict):
    for version in key["versions"]:
        for index, page in enumerate(version["pages"]):
            yield version["id"], index, page


def test_every_page_is_ready_and_has_what_its_key_says(vs1_key: dict, vs1_profiles: dict) -> None:
    wrong = []
    for version, index, key in _pages(vs1_key):
        outcome = vs1_profiles[version][index]
        summary = outcome.summary
        stamp = summary["stamp"]
        expected_stamp = key["stamp"]
        day, month, year = expected_stamp["date"].split(".")
        facts = {
            "status": (outcome.status, outcome.reason),
            "text_layer": summary["text_layer"],
            "scan": summary["scan"],
            "size": (round(summary["width_pt"], 1), round(summary["height_pt"], 1)),
            "annotations": summary["counts"]["annotations"],
            "stamp": (
                stamp.get("designation"), stamp.get("sheet_number"), stamp.get("sheet_name"),
                stamp.get("revision_number"), stamp.get("release_date"),
            ),
        }
        expected = {
            "status": ("ready", None),
            "text_layer": key["text_layer"],
            "scan": key["scan"],
            "size": (round(key["width_pt"], 1), round(key["height_pt"], 1)),
            "annotations": len(key["annotations"]),
            "stamp": (
                (expected_stamp["designation"], key["sheet_no"], key["title"],
                 expected_stamp["revision"].removeprefix("Изм."), f"{year}-{month}-{day}")
                if key["text_layer"] else (None, None, None, None, None)
            ),
        }
        if facts != expected:
            wrong.append((version, index + 1, {k: (facts[k], expected[k]) for k in facts if facts[k] != expected[k]}))
    assert wrong == []


def test_the_two_scanned_pages_are_flagged_and_have_no_text_nor_stamp(vs1_key: dict, vs1_profiles: dict) -> None:
    scans = [(v, i + 1) for v, i, key in _pages(vs1_key) if key["scan"]]
    assert scans == [("V4", 4), ("V5", 4)]
    for version, number in scans:
        summary = vs1_profiles[version][number - 1].summary
        assert summary["scan"] is True and summary["text_layer"] is False
        assert summary["counts"]["words"] == 0 and summary["counts"]["images"] == 1
        assert summary["image_coverage"] >= 0.99 and summary["stamp"]["labels"] == []
        # The page is not empty: its mask has ink (the image shows a drawing), and a preview exists.
        assert summary["ink"]["ratio"] > 0.01
    others = [
        vs1_profiles[v][i].summary["scan"] for v, i, key in _pages(vs1_key) if not key["scan"]
    ]
    assert others and not any(others)


def test_the_sheet_numbers_and_titles_follow_the_split_and_the_duplicate(vs1_key: dict, vs1_profiles: dict) -> None:
    v5 = vs1_profiles["V5"]
    assert [outcome.summary["stamp"].get("sheet_number") for outcome in v5] == [
        "1", "2", "3", None, "5.1", "5.2", "7", "3",
    ]
    assert v5[4].summary["stamp"]["sheet_name"].endswith("(часть 1)")
    assert v5[2].summary["stamp"]["sheet_name"] == v5[7].summary["stamp"]["sheet_name"]


def test_the_sp1_pair_reads_as_its_key_says(sp1_key: dict, fixtures_dir, runner) -> None:
    wrong, seen = [], 0
    digests = {}
    for sheet in sp1_key["sheets"]:
        path = fixtures_dir / sheet["file"]
        digests.setdefault(sheet["file"], hashlib.sha256(path.read_bytes()).hexdigest())
        outcome = profile_page(runner, pdf_path=str(path), page_index=sheet["page"] - 1, version_sha256=digests[sheet["file"]])
        stamp = outcome.summary["stamp"]
        seen += 1
        expected = (sheet["stamp"]["designation"], sheet["stamp"]["sheet_no"], sheet["title"])
        actual = (stamp.get("designation"), stamp.get("sheet_number"), stamp.get("sheet_name"))
        if outcome.status != "ready" or expected != actual:
            wrong.append((sheet["sheet_id"], outcome.status, expected, actual))
    assert seen == 12 and wrong == []


def test_the_archive_of_a_page_holds_its_words_lines_mask_and_the_stored_tile_levels(vs1_profiles: dict) -> None:
    for outcome in vs1_profiles["V1"]:
        reader = pack.PackReader(outcome.pack)
        document = reader.document()
        assert document["schema"] == "cmp-page-profile-pack/1" and document["algo_version"] == limits.ALGO_VERSION
        assert len(document["words"]) == outcome.summary["counts"]["words"] > 0
        assert len(document["lines"]) == outcome.summary["counts"]["lines"] > 0
        levels = outcome.summary["tiles"]["levels"]
        stored = sorted(
            (lv["level"], c, r)
            for lv in levels if lv["stored"] for c in range(lv["columns"]) for r in range(lv["rows"])
        )
        assert [name for name in reader.tile_names()] == [f"tiles/{lv}/{c}_{r}.png" for lv, c, r in stored]
        assert all(lv["level"] >= limits.FIRST_STORED_TILE_LEVEL for lv in levels if lv["stored"])
        assert all(not lv["stored"] for lv in levels if lv["level"] < limits.FIRST_STORED_TILE_LEVEL)
        for level, column, row in stored:
            assert reader.tile(level, column, row).startswith(PNG)
        assert outcome.summary["tiles"]["stored_count"] == len(stored)


def test_the_a1_plan_is_the_one_page_with_several_stored_levels(vs1_profiles: dict) -> None:
    a1 = vs1_profiles["V1"][4].summary
    assert a1["raster"] == {"dpi": 200, "width_px": 6623, "height_px": 4678}
    assert [(lv["level"], lv["stored"]) for lv in a1["tiles"]["levels"]] == [
        (0, False), (1, False), (2, True), (3, True), (4, True),
    ]
    assert a1["tiles"]["stored_count"] == 12 + 4 + 1
    # An A4 sheet is 1654 x 2339 at 200 dpi: levels 0 to 3, the last one a single tile.
    a4 = vs1_profiles["V1"][0].summary
    assert [(lv["level"], lv["columns"], lv["rows"]) for lv in a4["tiles"]["levels"]] == [
        (0, 4, 5), (1, 2, 3), (2, 1, 2), (3, 1, 1),
    ]
    assert [lv["level"] for lv in a4["tiles"]["levels"] if lv["stored"]] == [2, 3]


def test_the_previews_and_thumbnails_are_pngs_of_the_sizes_the_measurement_used(vs1_profiles: dict) -> None:
    for version in ("V1", "V4"):
        for outcome in vs1_profiles[version]:
            for blob, long_side, key in ((outcome.preview, 1400, "preview"), (outcome.thumbnail, 220, "thumbnail")):
                assert blob.startswith(PNG)
                image = Image.open(io.BytesIO(blob))
                assert max(image.size) == min(long_side, max(outcome.summary["raster"]["width_px"], outcome.summary["raster"]["height_px"]))
                assert image.mode == "RGB"
                assert (image.size[0], image.size[1]) == (outcome.summary[key]["width_px"], outcome.summary[key]["height_px"])
    # The measured sizes of MEASURE-RENDER-01 for VS-1 v1's A1 sheet, to the byte.
    assert len(vs1_profiles["V1"][4].preview) == 187156 and len(vs1_profiles["V1"][4].thumbnail) == 11933


def test_the_ink_mask_has_ink_where_the_words_are_and_none_in_the_margin(vs1_profiles: dict) -> None:
    for outcome in vs1_profiles["V1"] + vs1_profiles["V2"][:3]:
        document = pack.PackReader(outcome.pack).document()
        mask_info = document["mask"]
        assert (mask_info["dpi"], mask_info["below"]) == (36, 230)
        raw = pack.PackReader(outcome.pack).mask()
        ink = np.unpackbits(
            np.frombuffer(raw, dtype=np.uint8).reshape(mask_info["height_px"], mask_info["row_bytes"]), axis=1
        )[:, : mask_info["width_px"]].astype(bool)
        assert ink.shape == (mask_info["height_px"], mask_info["width_px"])
        scale = 36 / 72
        under, with_ink = 0, 0
        for x0, top, x1, bottom, _text in document["words"]:
            left, upper, right, lower = int(x0 * scale), int(top * scale), int(x1 * scale) + 1, int(bottom * scale) + 1
            if left < 0 or upper < 0 or right > ink.shape[1] or lower > ink.shape[0]:
                continue
            under += 1
            with_ink += bool(ink[upper:lower, left:right].any())
        assert under > 20 and with_ink == under, "every word's box has ink in the mask"
        # A 12 x 12 pt corner of the sheet is white in every sheet of the corpus.
        assert not ink[:6, :6].any()
        # A shifted frame would fail the test above: the same boxes moved 30 pt right find less ink.
        shifted = sum(
            bool(ink[int(top * scale): int(bottom * scale) + 1, int((x0 + 30) * scale): int((x1 + 30) * scale) + 1].any())
            for x0, top, x1, bottom, _ in document["words"]
            if int((x1 + 30) * scale) + 1 <= ink.shape[1] and int(bottom * scale) + 1 <= ink.shape[0]
        )
        assert shifted < under


def test_a_stored_archive_is_a_valid_zip_and_its_size_is_what_the_summary_says(vs1_profiles: dict) -> None:
    for outcome in vs1_profiles["V3"]:
        assert zipfile.is_zipfile(io.BytesIO(outcome.pack))
        assert outcome.summary["pack_bytes"] == len(outcome.pack)


def test_every_page_of_the_corpus_has_one_agreeing_frame(vs1_profiles: dict) -> None:
    for version in vs1_profiles.values():
        for outcome in version:
            assert outcome.summary["frame"] == {"offset": [0.0, 0.0], "agrees": True}


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_words_sit_on_ink_in_the_displayed_frame_of_a_rotated_and_asymmetrically_cropped_page(
    rotation: int, fixtures_dir, runner, tmp_path
) -> None:
    """The frame of the words is the raster's (CropBox applied, /Rotate applied), not pdfplumber's own
    (the rotated MediaBox): on a page cropped 40/25 pt asymmetrically and turned by every quarter, each
    word that is inside the displayed page has ink under its box in the 36 dpi mask."""
    from pypdf import PdfWriter
    from pypdf.generic import RectangleObject

    writer = PdfWriter(clone_from=str(fixtures_dir / "vs1" / "v1.pdf"))
    page = writer.pages[1]
    page.cropbox = RectangleObject([40, 25, 1100, 800])
    if rotation:
        page.rotate(rotation)
    path = tmp_path / f"rotated-{rotation}.pdf"
    with open(path, "wb") as sink:
        writer.write(sink)
    outcome = profile_page(runner, pdf_path=str(path), page_index=1, version_sha256="0" * 64)
    assert outcome.status == "ready", outcome.summary
    assert outcome.summary["rotation"] == rotation
    assert {round(outcome.summary["width_pt"]), round(outcome.summary["height_pt"])} == {1060, 775}
    assert outcome.summary["frame"]["agrees"] is True
    reader = pack.PackReader(outcome.pack)
    document, info = reader.document(), reader.document()["mask"]
    ink = np.unpackbits(
        np.frombuffer(reader.mask(), dtype=np.uint8).reshape(info["height_px"], info["row_bytes"]), axis=1
    )[:, : info["width_px"]].astype(bool)
    scale = 36 / 72
    under = with_ink = 0
    for x0, top, x1, bottom, _ in document["words"]:
        left, upper, right, lower = int(x0 * scale), int(top * scale), int(x1 * scale) + 1, int(bottom * scale) + 1
        if left < 0 or upper < 0 or right > ink.shape[1] or lower > ink.shape[0]:
            continue
        under += 1
        with_ink += bool(ink[upper:lower, left:right].any())
    assert under >= 30 and with_ink == under
