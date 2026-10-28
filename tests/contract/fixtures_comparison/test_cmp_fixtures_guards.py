"""Every guard of the corpus is shown failing.

A check that cannot fail proves nothing, so each tag that `check_vs1` / `check_sp1` can report is
made to appear here by changing the key (or a file) in memory, and the unmodified corpus is shown
clean first. The generator's own refusals (an authored expectation that contradicts the sheets) are
shown the same way.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TOOLS_DIR = REPO_ROOT / "tools" / "fixtures"
for path in (str(TOOLS_DIR), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cmp_fixtures_support as support  # noqa: E402
from comparison import build, sp1, vs1  # noqa: E402


@pytest.fixture(scope="module")
def files() -> dict[str, bytes]:
    return support.load_files()


@pytest.fixture(scope="module")
def vs_key(files) -> dict:
    return support.load_key(files, "vs1")


@pytest.fixture(scope="module")
def sp_key(files) -> dict:
    return support.load_key(files, "sp1")


def tags(problems: list[str]) -> set[str]:
    return {p.split("]", 1)[0] + "]" for p in problems}


def page(key: dict, version: str, number: int) -> dict:
    return next(v for v in key["versions"] if v["id"] == version)["pages"][number - 1]


def sheet(key: dict, a: str, b: str, sheet_id: str) -> dict:
    t = next(t for t in key["transitions"] if t["from"] == a and t["to"] == b)
    return next(s for s in t["sheets"] if s["sheet_id"] == sheet_id)


def test_the_unmodified_corpus_is_clean(files, vs_key, sp_key) -> None:
    assert support.check_vs1(files, vs_key) == []
    assert support.check_sp1(files, sp_key) == []


# -- VS-1: a change to the key is caught by the tag that owns it -----------------------------


def _stamp_revision(key):
    page(key, "V2", 2)["stamp"]["revision"] = "Изм.7"


def _page_count(key):
    key["versions"][0]["page_count"] = 5


def _page_size(key):
    page(key, "V1", 2)["width_pt"] = 1000.0


def _annotation_added(key):
    page(key, "V1", 1)["annotations"].append(
        {"id": "x", "kind": "text", "contents": "x", "author": "x", "rect": [0, 0, 10, 10]})


def _annotation_text(key):
    page(key, "V2", 5)["annotations"][0]["contents"] = "другой текст"


def _scan_marked_as_text(key):
    page(key, "V4", 4)["text_layer"] = True


def _text_marked_as_scan(key):
    page(key, "V1", 1)["text_layer"] = False


def _pdf_title(key):
    key["versions"][2]["pdf_title"] = "не тот заголовок"


def _identical_claim(key):
    sheet(key, "V1", "V2", "E02")["byte_identical_page"] = True


def _identical_denied(key):
    sheet(key, "V3", "V4", "E02")["byte_identical_page"] = False


def _text_after(key):
    next(c for c in sheet(key, "V1", "V2", "E03")["text_changes"] if c["id"] == "E03.table.r3c2")["after"] = "9,9"


def _text_added_but_present(key):
    change = next(c for c in sheet(key, "V3", "V4", "E03")["text_changes"])
    change["kind"] = "text_added"
    change["bbox_after"] = change["bbox_before"]
    change["after"] = change["before"]


def _colour(key):
    sheet(key, "V2", "V3", "E05")["graphic_changes"][0]["after"] = [0.0, 1.0, 0.0]


def _width(key):
    sheet(key, "V2", "V3", "E04")["graphic_changes"][0]["after"] = 3.0


def _added_line_elsewhere(key):
    change = sheet(key, "V2", "V3", "E02")["graphic_changes"][0]
    change["bbox_after"] = [10.0, 10.0, 20.0, 20.0]


def _spec_quantity(key):
    sheet(key, "V4", "V5", "E07")["spec_positions"]["positions_after"][2]["quantity"] = "9"


def _spec_added(key):
    sheet(key, "V4", "V5", "E07")["spec_positions"]["added"][0]["position"] = "8"


def _spec_changed_field(key):
    sheet(key, "V4", "V5", "E07")["spec_positions"]["changed"][0]["field"] = "mass"


def _permit_row(key):
    permit = next(t for t in key["transitions"] if t["id"] == "V3->V4")["permit"]
    permit["declared"][0]["text"] = "Другое изменение"


def _permit_class(key):
    permit = next(t for t in key["transitions"] if t["id"] == "V3->V4")["permit"]
    permit["declared"][1]["reconciliation"] = "declared_and_found"


def _permit_missing_found_not_declared(key):
    permit = next(t for t in key["transitions"] if t["id"] == "V3->V4")["permit"]
    permit["found_not_declared"] = []
    permit["classes"]["found_not_declared"] = []


def _status_count(key):
    next(t for t in key["transitions"] if t["id"] == "V1->V2")["status_counts"]["same"] = 5


def _status_name(key):
    sheet(key, "V1", "V2", "E01")["expected_status"] = "mostly_same"


def _channel_overlap(key):
    entry = sheet(key, "V1", "V2", "E01")
    entry["channels_with_differences"] = ["text"]
    entry["channels_without_differences"] = ["text"]


def _identity(key):
    key["sheet_identity"][1]["pages"]["V1"] = [3]


def _version_label(key):
    key["versions"][2]["label"] = "Изм.9"


def _split_region(key):
    sheet(key, "V4", "V5", "E05")["parts"][0]["region_in_old_sheet_x"] = [0.0, 600.0]


def _split_translation(key):
    sheet(key, "V4", "V5", "E05")["parts"][1]["translation_x"] = -1000.0


def _duplicate_target(key):
    sheet(key, "V4", "V5", "E03")["to_pages"] = [3, 7]


def _scan_pair_reason(key):
    """NO_TEXT_LAYER on a pair that has a text layer on both sides."""
    sheet(key, "V1", "V2", "E02")["reasons"] = ["NO_TEXT_LAYER"]


@pytest.mark.parametrize(("mutation", "tag"), [
    (_stamp_revision, "[stamp]"),
    (_page_count, "[pages]"),
    (_page_size, "[size]"),
    (_annotation_added, "[annots]"),
    (_annotation_text, "[annots]"),
    (_scan_marked_as_text, "[scan]"),
    (_text_marked_as_scan, "[scan]"),
    (_pdf_title, "[title]"),
    (_identical_claim, "[identical]"),
    (_identical_denied, "[identical]"),
    (_text_after, "[text_change]"),
    (_text_added_but_present, "[text_change]"),
    (_colour, "[style]"),
    (_width, "[style]"),
    (_added_line_elsewhere, "[style]"),
    (_spec_quantity, "[spec]"),
    (_spec_added, "[spec]"),
    (_spec_changed_field, "[spec]"),
    (_permit_row, "[permit]"),
    (_permit_class, "[permit]"),
    (_permit_missing_found_not_declared, "[permit]"),
    (_status_count, "[status]"),
    (_status_name, "[status]"),
    (_channel_overlap, "[status]"),
    (_identity, "[identity]"),
    (_version_label, "[version]"),
    (_split_region, "[split]"),
    (_split_translation, "[split]"),
    (_duplicate_target, "[duplicate]"),
    (_scan_pair_reason, "[scan]"),
], ids=lambda value: getattr(value, "__name__", value))
def test_a_wrong_vs1_key_is_reported_under_its_tag(files, vs_key, mutation, tag) -> None:
    broken = copy.deepcopy(vs_key)
    mutation(broken)
    assert tag in tags(support.check_vs1(files, broken))


def test_a_swapped_pdf_is_caught_by_its_digest_and_by_the_content_checks(files, vs_key) -> None:
    swapped = dict(files)
    swapped["vs1/v3.pdf"] = files["vs1/v2.pdf"]
    found = tags(support.check_vs1(swapped, vs_key))
    assert "[sha]" in found and found & {"[text_change]", "[style]", "[identical]", "[pages]"}


def test_a_missing_pdf_is_reported(files, vs_key) -> None:
    missing = {k: v for k, v in files.items() if k != "vs1/v5.pdf"}
    assert "[files]" in tags(support.check_vs1(missing, vs_key))


def test_a_pdf_with_its_text_layer_removed_is_caught_without_the_digest(files, vs_key) -> None:
    """Only the digest in the key is changed to match, so the content checks must carry the proof."""
    import hashlib

    data = files["vs1/v1.pdf"].replace(b"Tj", b"TJ"[:2] + b"")  # same bytes: a null edit, then really break it
    data = files["vs1/v1.pdf"].replace(b"<", b"(").replace(b">", b")")  # the glyph strings become garbage
    broken_key = copy.deepcopy(vs_key)
    broken_key["versions"][0]["sha256"] = hashlib.sha256(data).hexdigest()
    broken_key["versions"][0]["bytes"] = len(data)
    mutated = dict(files)
    mutated["vs1/v1.pdf"] = data
    try:
        problems = support.check_vs1(mutated, broken_key)
    except Exception:  # an unreadable file is also a refusal
        return
    assert problems, "a PDF whose text was destroyed passed every check"


# -- SP-1 -------------------------------------------------------------------------------------


def _link_target(key):
    key["sheet_links"][0]["new"] = "R2"


def _link_removed(key):
    key["sheet_links"].pop()


def _unpaired(key):
    key["sheets_without_pair"]["old_only"] = []


def _stamp_stage(key):
    next(s for s in key["sheets"] if s["sheet_id"] == "R1")["stamp"]["stage"] = "П"


def _stamp_differences(key):
    key["sheet_links"][0]["stamp_differences"] = []


def _changed_after(key):
    key["text_fragments"]["changed"][0]["after"] = "101  Холл  99,9 м²"


def _added_that_is_old(key):
    record = key["text_fragments"]["added"][0]
    record["after"] = "101  Холл  24,5 м²"


def _removed_that_survives(key):
    key["text_fragments"]["removed"][0]["before"] = "Высота помещений 3,0 м"


def _moved_onto_its_link(key):
    record = key["text_fragments"]["moved_between_sheets"][0]
    record["new_sheet"] = "R4"
    record["old_sheet"] = "P4"


def _unchanged_that_changed(key):
    key["text_fragments"]["unchanged"][0]["after"] = "что-то другое"


def _passport(key):
    next(s for s in key["sheets"] if s["sheet_id"] == "P3")["passport"]["level"] = "Этаж 9"


def _sp_digest(key):
    key["documents"][0]["sha256"] = "0" * 64


@pytest.mark.parametrize(("mutation", "tag"), [
    (_link_target, "[links]"),
    (_link_removed, "[links]"),
    (_unpaired, "[links]"),
    (_stamp_stage, "[stamp]"),
    (_stamp_differences, "[links]"),
    (_changed_after, "[fragments]"),
    (_added_that_is_old, "[fragments]"),
    (_removed_that_survives, "[fragments]"),
    (_moved_onto_its_link, "[fragments]"),
    (_unchanged_that_changed, "[fragments]"),
    (_passport, "[links]"),
    (_sp_digest, "[sha]"),
], ids=lambda value: getattr(value, "__name__", value))
def test_a_wrong_sp1_key_is_reported_under_its_tag(files, sp_key, mutation, tag) -> None:
    broken = copy.deepcopy(sp_key)
    mutation(broken)
    assert tag in tags(support.check_sp1(files, broken))


# -- the generators refuse to write a key their own sheets contradict ---------------------------


def test_the_generator_refuses_a_status_that_the_sheets_contradict(monkeypatch) -> None:
    statuses = copy.deepcopy(vs1.EXPECTED_STATUS)
    statuses[("V1", "V2")]["E03"] = "same"
    monkeypatch.setattr(vs1, "EXPECTED_STATUS", statuses)
    with pytest.raises(vs1.BuildError, match="authored `same`"):
        vs1.build()


def test_the_generator_refuses_a_stamp_only_status_on_a_content_change(monkeypatch) -> None:
    statuses = copy.deepcopy(vs1.EXPECTED_STATUS)
    statuses[("V1", "V2")]["E02"] = "same_zones_changed"
    monkeypatch.setattr(vs1, "EXPECTED_STATUS", statuses)
    with pytest.raises(vs1.BuildError, match="same_zones_changed"):
        vs1.build()


def test_the_generator_refuses_different_on_a_stamp_only_change(monkeypatch) -> None:
    statuses = copy.deepcopy(vs1.EXPECTED_STATUS)
    statuses[("V1", "V2")]["E04"] = "different"
    monkeypatch.setattr(vs1, "EXPECTED_STATUS", statuses)
    with pytest.raises(vs1.BuildError, match="different"):
        vs1.build()


def test_the_generator_refuses_a_permit_outcome_the_sheets_contradict(monkeypatch) -> None:
    expected = copy.deepcopy(vs1.EXPECTED_PERMIT)
    expected["declared_and_found"], expected["declared_not_found"] = ["E07"], ["E05"]
    monkeypatch.setattr(vs1, "EXPECTED_PERMIT", expected)
    with pytest.raises(vs1.BuildError, match="permit reconciliation"):
        vs1.build()


def test_the_generator_refuses_a_text_class_the_sheets_contradict(monkeypatch) -> None:
    expected = copy.deepcopy(sp1.EXPECTED_TEXT)
    expected["moved_between_sheets"] = expected["moved_between_sheets"][:-1]
    monkeypatch.setattr(sp1, "EXPECTED_TEXT", expected)
    with pytest.raises(sp1.BuildError, match="fragment classes"):
        sp1.build()


def test_the_generator_refuses_operations_that_cross_the_split_line(monkeypatch) -> None:
    monkeypatch.setattr(vs1, "SPLIT_LEFT", (0.0, 1000.0))
    with pytest.raises(ValueError, match="cross the split line"):
        vs1.build()


def test_the_text_layer_check_of_the_build_can_fail(monkeypatch) -> None:
    """`build.verify_text_layer` reads the PDFs back; give it a key that lies about a stamp."""
    files_, key_ = vs1.build()
    _sp_files, sp_key_ = sp1.build()
    key_["versions"][0]["pages"][0]["stamp"]["revision"] = "Изм.5"
    problems = build.verify_text_layer({**files_, **_sp_files}, key_, sp_key_)
    assert any("stamp revision" in p for p in problems)
