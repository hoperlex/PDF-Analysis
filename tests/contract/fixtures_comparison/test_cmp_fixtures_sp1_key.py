"""SP-1: one П document and an assembly of three Р documents, and the key that links them."""

from __future__ import annotations

import sys
from pathlib import Path

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
    return support.load_key(files, "sp1")


def test_every_claim_of_the_key_is_read_back_from_the_pdfs(files, key) -> None:
    assert support.check_sp1(files, key) == []


def test_one_p_document_and_an_assembly_of_three_r_documents(key) -> None:
    sides = {d["name"]: d["side"] for d in key["documents"]}
    assert sorted(n for n, s in sides.items() if s == "old") == ["old_p"]
    assert sorted(n for n, s in sides.items() if s == "new") == ["new_r1", "new_r2", "new_r3"]
    stages = {d["name"]: d["stage"] for d in key["documents"]}
    assert stages == {"old_p": "П", "new_r1": "Р", "new_r2": "Р", "new_r3": "Р"}
    assert key["assembly"]["new"] == ["new_r1", "new_r2", "new_r3"]


def test_sheet_titles_carry_type_building_and_level(key) -> None:
    for sheet in key["sheets"]:
        passport = sheet["passport"]
        assert passport["type"] and passport["building"].startswith("Корпус ")
        assert passport["level"].startswith(("Этаж ", "Кровля", "Уровень "))
    levels = {s["passport"]["level"] for s in key["sheets"]}
    assert {"Этаж 1", "Этаж 2", "Кровля", "Уровень +0,000"} <= levels


def test_five_sheets_are_linked_and_one_sheet_is_left_on_each_side(key) -> None:
    assert [(l["old"], l["new"]) for l in key["sheet_links"]] == [
        ("P1", "R1"), ("P2", "R2"), ("P3", "R3"), ("P4", "R4"), ("P5", "R5")]
    assert [s["sheet_id"] for s in key["sheets_without_pair"]["old_only"]] == ["P6"]
    assert [s["sheet_id"] for s in key["sheets_without_pair"]["new_only"]] == ["R6"]
    for link in key["sheet_links"]:
        assert link["basis"] == ["type", "building", "level"]
        assert {d["field"] for d in link["stamp_differences"]} >= {"designation", "stage", "date"}


def test_text_fragments_changed_added_removed_and_moved(key) -> None:
    classes = key["text_fragments"]
    assert [(r["before"], r["after"]) for r in classes["changed"] if r["key"] == "rm101"] == [
        ("101  Холл  24,5 м²", "101  Холл  25,1 м²")]
    assert {r["key"] for r in classes["changed"]} == {"rm101", "roof1"}
    assert {r["key"] for r in classes["added"]} == {"rm106", "note2", "cutbox2", "cut4", "cut5"}
    assert {r["key"] for r in classes["removed"]} == {"rm105", "roof2", "exhdr", "exarea"}
    moved = classes["moved_between_sheets"]
    assert {(r["key"], r["old_sheet"], r["new_sheet"]) for r in moved} == {
        ("ex1", "P6", "R4"), ("ex2", "P6", "R4"), ("ex3", "P6", "R4")}
    assert len(classes["unchanged"]) >= 10, "unchanged text is part of the key: a comparison must not report it"
    assert all(r["before"] == r["after"] for r in classes["unchanged"])
