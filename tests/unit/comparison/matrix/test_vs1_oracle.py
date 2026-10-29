"""The built matrix of the synthetic corpus against its answer key, and its determinism (`CMP-MATRIX-01`).

The profiles are the product's own, made by the real children (``conftest.vs1``); the oracle is the key's
``sheet_identity`` and the facts it states about V1..V5 (a sheet added and one removed in V3, a scan in V4, the A1 plan
split into two A2 parts and a duplicated sheet in V5). Determinism is shown three ways: the same input twice, a mask
cache of one byte against one of a hundred megabytes, and two processes with different string hash seeds."""

from __future__ import annotations

import hashlib
import json
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.effective import canonical_json
from auditmanager.comparison.matrix.features import MaskCache, PageFeatures
from auditmanager.comparison.matrix.lineage import build_rows


def _features(vs1: dict[str, Any], budget: int = 96 * 1024 * 1024) -> tuple[list[str], dict[str, list[PageFeatures]]]:
    cache = MaskCache(budget)
    order = [vs1["versions"][name][0] for name in vs1["order"]]
    features: dict[str, list[PageFeatures]] = {}
    for name in vs1["order"]:
        uid, pages = vs1["versions"][name]
        fs = [PageFeatures(p, rules=settings.RULES, cache=cache) for p in pages]
        for position, f in enumerate(fs):
            f.rel = position / max(1, len(fs) - 1)
        features[uid] = fs
    return order, features


def test_the_rows_hold_the_sheets_of_the_key(vs1: dict[str, Any], vs1_key: dict[str, Any]) -> None:
    order, features = _features(vs1)
    result = build_rows(order, features)
    key_pages = {uid: vs1_key["versions"][i]["pages"] for i, uid in enumerate(order)}
    by_sheet: dict[str, list[dict]] = {}
    for row in result["rows"]:
        ids = {key_pages[c["version_uid"]][c["page_number"] - 1]["sheet_id"] for c in row["cells"] if c["state"] == "matched"}
        assert len(ids) == 1, "one row is one sheet"
        by_sheet.setdefault(ids.pop(), []).append(row)
    assert sorted(by_sheet) == [s["sheet_id"] for s in vs1_key["sheet_identity"]]
    for identity in vs1_key["sheet_identity"]:
        for index, uid in enumerate(order):
            wanted = identity["pages"].get(vs1_key["versions"][index]["id"], [])
            found = sorted(r["cells"][index]["page_number"] for r in by_sheet[identity["sheet_id"]] if r["cells"][index]["state"] == "matched")
            assert found == sorted(wanted[:2] if identity["sheet_id"] == "E05" else wanted[:1]), (identity["sheet_id"], index)
    assert result["unassigned"] == [] and result["duplicates"] == {order[4]: {"8": 3}}


def test_the_flags_the_key_calls_for_stand_on_the_right_cells(vs1: dict[str, Any], vs1_key: dict[str, Any]) -> None:
    order, features = _features(vs1)
    result = build_rows(order, features)
    flagged: dict[str, set[tuple[int, int]]] = {}
    for row in result["rows"]:
        for index, cell in enumerate(row["cells"]):
            for flag in cell.get("flags", ()):
                flagged.setdefault(flag, set()).add((index, cell["page_number"]))
    scans = {(i, p["page"]) for i, v in enumerate(vs1_key["versions"]) for p in v["pages"] if p["scan"]}
    assert flagged["scan"] == scans == {(3, 4), (4, 4)}
    assert flagged["duplicate"] == {(4, 3)}
    assert flagged["split"] == {(3, 5), (4, 5), (4, 6)}
    assert "bridge" not in flagged
    grades = {c.get("confidence") for row in result["rows"] for c in row["cells"] if c["state"] == "matched"}
    assert grades <= {None, "high", "medium"}
    [split] = result["splits"]
    assert (split["a_version_uid"], split["b_version_uid"], split["kind"], split["role"]) == (order[3], order[4], "split", "part")
    assert split["a"]["page_number"] == 5 and [p["page_number"] for p in split["parts"]] == [5, 6] and 0 < split["covered_percent"] < 100


def test_a_sheet_added_and_a_sheet_removed_are_rows_with_absent_cells(vs1: dict[str, Any]) -> None:
    order, features = _features(vs1)
    states = [[c["state"] for c in row["cells"]] for row in build_rows(order, features)["rows"]]
    assert ["absent", "absent", "matched", "matched", "matched"] in states, "the specification, new in V3"
    assert ["matched", "matched", "absent", "absent", "absent"] in states, "sheet 6, removed in V3"


def test_the_same_input_twice_and_a_tiny_mask_cache_give_the_same_bytes(vs1: dict[str, Any]) -> None:
    order, features = _features(vs1)
    first = canonical_json(build_rows(order, features))
    assert canonical_json(build_rows(order, features)) == first
    order_small, features_small = _features(vs1, budget=1)
    assert canonical_json(build_rows(order_small, features_small)) == first


def test_two_processes_with_other_hash_seeds_give_the_same_bytes(vs1: dict[str, Any], tmp_path: Path) -> None:
    payload = tmp_path / "vs1.pickle"
    payload.write_bytes(pickle.dumps(vs1))
    program = (
        "import hashlib, pickle, sys\n"
        "sys.path.insert(0, sys.argv[2])\n"
        "from auditmanager.comparison.matrix import settings\n"
        "from auditmanager.comparison.matrix.effective import canonical_json\n"
        "from auditmanager.comparison.matrix.features import MaskCache, PageFeatures\n"
        "from auditmanager.comparison.matrix.lineage import build_rows\n"
        "vs1 = pickle.load(open(sys.argv[1], 'rb'))\n"
        "cache = MaskCache(); order = [vs1['versions'][n][0] for n in vs1['order']]; features = {}\n"
        "for n in vs1['order']:\n"
        "    uid, pages = vs1['versions'][n]\n"
        "    fs = [PageFeatures(p, rules=settings.RULES, cache=cache) for p in pages]\n"
        "    for i, f in enumerate(fs): f.rel = i / max(1, len(fs) - 1)\n"
        "    features[uid] = fs\n"
        "print(hashlib.sha256(canonical_json(build_rows(order, features))).hexdigest())\n"
    )
    digests = set()
    for seed in ("1", "2", "31337"):
        done = subprocess.run(
            [sys.executable, "-I", "-c", program, str(payload), str(Path(__file__).resolve().parents[4] / "src")],
            capture_output=True, text=True, check=True, env={"PYTHONHASHSEED": seed, "PATH": ""},
        )
        digests.add(done.stdout.strip())
    assert len(digests) == 1 and len(next(iter(digests))) == 64
    order, features = _features(vs1)
    assert hashlib.sha256(canonical_json(build_rows(order, features))).hexdigest() in digests


def test_a_page_that_ended_without_a_result_is_a_page_of_its_own_row_not_a_lost_page(vs1: dict[str, Any]) -> None:
    """A profile that is ``needs_review`` has no words and no mask: it cannot be matched, and it must not vanish."""
    from dataclasses import replace

    order, features = _features(vs1)
    uid, pages = vs1["versions"]["V2"]
    broken = replace(pages[1], row=replace(pages[1].row, status="needs_review", reason="RENDER_FAILED"),
                     words=(), lines=(), ink_mask=None, stamp=type(pages[1].stamp)())
    features[uid] = [PageFeatures(p, rules=settings.RULES, cache=MaskCache()) if p is not pages[1]
                     else PageFeatures(broken, rules=settings.RULES, cache=MaskCache()) for p in pages]
    for position, f in enumerate(features[uid]):
        f.rel = position / 5
    result = build_rows(order, features)
    held = {(c["version_uid"], c["page_number"]) for row in result["rows"] for c in row["cells"] if c["state"] == "matched"}
    assert (uid, 2) in held and sum(1 for v, _ in held if v == uid) == 6
