"""The order-independent comparison of two streams of positions (`CMP-VC-SPEC-01`, part A and the compare of part B).

The rules are those of ``spec.compare`` of the original (PDF-proverka at ``23f379fd``, ``spec.py:435-536``): positions are matched
by what they are, never by where they are, in three passes; a renamed position is *changed*; a page move is not a change.
"""

from __future__ import annotations

import ast
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from auditmanager.comparison.specification import diff, table

SRC = Path(__file__).resolve().parents[4] / "src" / "auditmanager" / "comparison" / "specification"


def _items(*rows: dict[str, str], page: int = 1, sections: dict[int, str] | None = None) -> list[dict]:
    """Items as ``table.assemble`` makes them, from the cells of positions (a row with only a ``section`` key is a section title)."""
    parsed = []
    for row in rows:
        if "section" in row:
            parsed.append({"cells": {"name": row["section"]}, "bbox": [0, 0, 1, 1], "centered": True, "bold": False, "span": True})
        else:
            parsed.append({"cells": dict(row), "bbox": [0, 0, 1, 1], "centered": False, "bold": False})
    return table.assemble([{"page": page, "rows": parsed}])["items"]


def _shape(result: dict) -> list[tuple]:
    return sorted((c["kind"], c["label"], json.dumps(c["fields"], sort_keys=True, ensure_ascii=False)) for c in result["changes"])


def _pos(pos: str, name: str, mark: str, qty: str = "1", **more: str) -> dict[str, str]:
    return {"pos": pos, "name": name, "mark": mark, "quantity": qty, **more}


BASE = [_pos("1", "Щит освещения", "ЩО-1", "1"), _pos("2", "Выключатель 16 А", "АВ-16", "12"), _pos("3", "Выключатель 63 А", "АВ-63", "2"),
        _pos("4", "Кабель", "КБ-325", "320", unit="м"), _pos("5", "Светильник", "СВ-236", "24")]


def test_two_equal_streams_have_no_change() -> None:
    result = diff.compare(_items(*BASE), _items(*BASE))
    assert result["changes"] == [] and result["matched"] == 5
    assert result["totals"] == {"changed": 0, "removed": 0, "added": 0, "unclear": 0, "renumbered": 0, "moved": 0}


def test_the_answer_of_the_comparison_does_not_depend_on_the_order_of_either_side() -> None:
    a = list(BASE)
    b = [dict(BASE[0]), _pos("3", "Выключатель 63 А", "АВ-63", "3"), dict(BASE[1]), dict(BASE[3]), _pos("7", "Светильник LED", "СД-40", "6")]
    straight = diff.compare(_items(*a), _items(*b))
    for seed in range(5):
        shuffled_a, shuffled_b = list(a), list(b)
        random.Random(seed).shuffle(shuffled_a)
        random.Random(seed + 100).shuffle(shuffled_b)
        assert _shape(diff.compare(_items(*shuffled_a), _items(*shuffled_b))) == _shape(straight)
    assert straight["totals"]["changed"] == 1 and straight["totals"]["removed"] == 1 and straight["totals"]["added"] == 1


def test_a_quantity_is_compared_as_a_number_and_every_other_field_as_text() -> None:
    a = _items(_pos("1", "Кабель", "КБ-1", "2,0", note="по проекту"))
    b = _items(_pos("1", "Кабель", "КБ-1", "2", note="по  проекту"))
    assert diff.compare(a, b)["changes"] == []
    changed = diff.compare(a, _items(_pos("1", "Кабель", "КБ-1", "3", note="по проекту")))["changes"]
    assert [(c["kind"], c["fields"]) for c in changed] == [("changed", {"quantity": ["2,0", "3"]})]


def test_a_renamed_position_with_the_same_mark_is_changed_and_not_removed_and_added() -> None:
    a = _items(_pos("1", "Светильник светодиодный 40 Вт", "СД-40"))
    b = _items(_pos("1", "Светильник светодиодный 40 Вт IP65", "СД-40"))
    changes = diff.compare(a, b)["changes"]
    assert [c["kind"] for c in changes] == ["changed"] and list(changes[0]["fields"]) == ["name"]


def test_a_replaced_mark_under_the_same_name_is_changed() -> None:
    a = _items(_pos("1", "Ввод питания 63 А", "ABB-1"))
    b = _items(_pos("1", "Ввод питания 63 А", "SCHNEIDER-X"))
    changes = diff.compare(a, b)["changes"]
    assert [(c["kind"], list(c["fields"])) for c in changes] == [("changed", ["mark"])]


def test_a_position_that_has_nothing_in_common_is_removed_and_added() -> None:
    changes = diff.compare(_items(_pos("6", "Заземлитель", "ЗУ-01", "4")), _items(_pos("7", "Светильник LED", "СД-40", "6")))["changes"]
    assert [c["kind"] for c in changes] == ["removed", "added"]
    assert changes[0]["fields"] == {"quantity": ["4", ""]} and changes[1]["fields"] == {"quantity": ["", "6"]}
    assert changes[0]["b"] is None and changes[1]["a"] is None


def test_a_position_that_only_changed_its_number_is_renumbered() -> None:
    a = _items(_pos("3", "Выключатель", "АВ-63", "2"))
    b = _items(_pos("4", "Выключатель", "АВ-63", "2"))
    changes = diff.compare(a, b)["changes"]
    assert [(c["kind"], c["fields"]) for c in changes] == [("renumbered", {"pos": ["3", "4"]})]


def test_the_same_position_in_another_section_is_moved_without_being_changed() -> None:
    a = _items({"section": "Щиты"}, _pos("1", "Автомат", "АВ-1", "2"), {"section": "Кабели"}, _pos("2", "Кабель", "КБ-1", "5"))
    b = _items({"section": "Кабели"}, _pos("2", "Кабель", "КБ-1", "5"), {"section": "Резерв"}, _pos("1", "Автомат", "АВ-1", "2"))
    result = diff.compare(a, b)
    assert [(c["kind"], c["label"]) for c in result["changes"]] == [("moved", "Автомат — АВ-1")]
    assert "Перенесено без изменения" in result["changes"][0]["text"]


def test_a_move_to_another_page_is_not_a_change() -> None:
    a = _items(*BASE, page=2)
    b = _items(*BASE, page=5)
    assert diff.compare(a, b)["changes"] == []


def test_an_ambiguous_boundary_with_no_difference_is_unclear_and_with_a_difference_is_changed() -> None:
    a, b = _items(*BASE), _items(*BASE)
    a[1]["ambiguous"] = True
    result = diff.compare(a, b)
    assert [(c["kind"], c["ambiguous"]) for c in result["changes"]] == [("unclear", True)]
    b2 = _items(*BASE[:1], _pos("2", "Выключатель 16 А", "АВ-16", "13"), *BASE[2:])
    a2 = _items(*BASE)
    a2[1]["ambiguous"] = True
    assert [(c["kind"], c["ambiguous"]) for c in diff.compare(a2, b2)["changes"]] == [("changed", True)]


def test_the_list_is_in_the_order_changed_removed_added_unclear_renumbered_moved_and_numbered() -> None:
    a = _items(_pos("1", "А", "М-1", "1"), _pos("2", "Б", "М-2", "1"), _pos("3", "В", "М-3", "1"))
    b = _items(_pos("1", "А", "М-1", "5"), _pos("9", "Г", "М-9", "1"), _pos("4", "В", "М-3", "1"))
    result = diff.compare(a, b)
    assert [c["kind"] for c in result["changes"]] == ["changed", "removed", "added", "renumbered"]
    assert [c["id"] for c in result["changes"]] == ["s1", "s2", "s3", "s4"]
    assert all(__import__("re").fullmatch(r"[a-z0-9][a-z0-9_.-]{0,31}", c["id"]) for c in result["changes"])


def test_the_sentence_of_a_change_fits_the_contract() -> None:
    long_name = "Очень длинное наименование " * 40
    result = diff.compare(_items(_pos("1", long_name, "М-1", "1")), _items(_pos("1", long_name, "М-1", "2")))
    text = result["changes"][0]["text"]
    assert 1 <= len(text) <= 600


def test_page_changes_select_the_changes_that_touch_a_page() -> None:
    a = _items(_pos("1", "А", "М-1", "1"), page=3)
    b = _items(_pos("1", "А", "М-1", "2"), page=7)
    changes = diff.compare(a, b)["changes"]
    assert len(diff.page_changes(changes, "a", 3)) == 1 and diff.page_changes(changes, "a", 7) == []
    assert len(diff.page_changes(changes, "b", 7)) == 1 and diff.page_changes(changes, "b", 3) == []


def test_a_specification_of_thousands_of_rows_is_not_quadratic() -> None:
    a = _items(*[_pos(str(i), f"Позиция номер {i}", f"М-{i}", "1") for i in range(3000)])
    b = _items(*[_pos(str(i), f"Позиция номер {i} исп", f"Н-{i}", "1") for i in range(3000)])
    started = time.monotonic()
    result = diff.compare(a, b)
    assert time.monotonic() - started < 20
    assert result["totals"]["removed"] + result["totals"]["added"] + result["totals"]["changed"] > 0


def test_the_pure_modules_import_nothing_of_the_product() -> None:
    """The engine's child loads ``table`` and ``diff`` by path with ``python -I``; they must need nothing but the standard library."""
    for name in ("__init__.py", "table.py", "diff.py"):
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] in sys.stdlib_module_names for a in node.names), (name, node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 1 or (node.module or "").split(".")[0] in sys.stdlib_module_names, (name, node.module)


def test_the_package_loads_the_way_the_engine_child_loads_it() -> None:
    """``python -I -B`` with no path to the product: the package is loaded by file under ``_amc_spec`` and compares two streams."""
    program = f"""
import importlib, importlib.util, json, sys
d = {str(SRC)!r}
spec = importlib.util.spec_from_file_location("_amc_spec", d + "/__init__.py", submodule_search_locations=[d])
module = importlib.util.module_from_spec(spec); sys.modules["_amc_spec"] = module; spec.loader.exec_module(module)
table = importlib.import_module("_amc_spec.table"); diff = importlib.import_module("_amc_spec.diff")
row = lambda q: {{"cells": {{"pos": "1", "name": "Кабель", "mark": "КБ", "quantity": q}}, "bbox": [0, 0, 1, 1], "centered": False, "bold": False}}
a = table.assemble([{{"page": 1, "rows": [row("2")]}}])["items"]; b = table.assemble([{{"page": 1, "rows": [row("3")]}}])["items"]
print(json.dumps(diff.compare(a, b)["totals"]), "auditmanager" in sys.modules)
"""
    done = subprocess.run([sys.executable, "-I", "-B", "-c", program], capture_output=True, text=True, timeout=60, check=True)
    totals, product = done.stdout.split()[:-1], done.stdout.split()[-1]
    assert json.loads(" ".join(totals))["changed"] == 1 and product == "False"
