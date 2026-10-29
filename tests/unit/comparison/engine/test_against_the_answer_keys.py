"""The engine against the answer keys of the synthetic corpus (`CMP-FIXTURES-01`), the oracle authored beside the
content that creates each difference. The real page children and the real engine child run on every pair.

Every disagreement between the keys and the engine is named here, with the reason, and the test fails if a disagreement
the list does not name appears or one it names goes away: a key is read, not matched by adjusting the engine until it
agrees. The named disagreements are reported in `docs/program/CMP-ENGINE-01.md` section 5. (`CMP-VC-SPEC-01` built the `spec_positions` channel,
so the fifth, V4 to V5 sheet E07, is gone: the channel reports the key's three position differences.)
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine.mask_codec import decode_mask
from auditmanager.comparison.engine.validate import validate_outcome

VERSIONS = {"V1": "vs1/v1.pdf", "V2": "vs1/v2.pdf", "V3": "vs1/v3.pdf", "V4": "vs1/v4.pdf", "V5": "vs1/v5.pdf"}

#: ``(transition, sheet, what)``: the keys' claim that the engine, by the rules of the original, does not meet.
DISAGREEMENTS = {
    # The bus line weight 0.5 -> 1.5 pt: the key calls it a colour/pen change (`color` must report, `geometry` must
    # not); by the original's rules the extra pixels of the thicker pen are light elements only in B (class `light`),
    # and `light` is counted in `geometry`.
    ("V2->V3", "E04", "color"),
    ("V2->V3", "E04", "geometry"),
    # A duplicate of a sheet: the pages are byte-identical, so every channel is `checked` with no difference (the
    # original's fast path); the key wants `warnings` to report. `DUPLICATE_SHEET` is the reason that forces the status.
    ("V4->V5", "E03", "warnings"),
    # A split sheet: the engine compares the part against the sheet; `needs_review` with `SPLIT_SHEET` is the series'
    # verdict from the coverage of all the parts (the original's `_parts_phase`), not a property of one pair.
    ("V4->V5", "E05", "status"),
}


def _pairs(key: dict):
    versions = [v["id"] for v in key["versions"]]
    for index, transition in enumerate(key["transitions"]):
        name = transition["transition"] if "transition" in transition else transition["id"]
        for sheet in transition["sheets"]:
            to_page = sheet.get("to_page") or (sheet.get("to_pages") or [None])[0]
            if sheet["from_page"] is None or to_page is None:
                continue
            yield pytest.param(name, versions[index], versions[index + 1], sheet, to_page, id=f"{name}-{sheet['sheet_id']}")


def _reports(channel: dict, name: str) -> bool:
    """The channel reports a difference, or (for the coverage of text) says it could not look."""
    if channel["state"] == "checked":
        return channel.get("diffs", 0) > 0
    return channel["state"] == "unchecked" and name == "text_coverage"


def _cases():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[4] / "fixtures" / "comparison" / "vs1" / "answer_key.json"
    return list(_pairs(json.loads(path.read_text(encoding="utf-8"))))


@pytest.mark.parametrize("name,a_id,b_id,sheet,to_page", _cases())
def test_the_status_and_the_channels_of_a_sheet_are_those_of_the_key(compare, name, a_id, b_id, sheet, to_page) -> None:
    part = "split" if sheet["relation"] == "split" else None
    link_reasons = tuple(r for r in sheet["reasons"] if r == "DUPLICATE_SHEET")
    computed = compare(VERSIONS[a_id], sheet["from_page"], VERSIONS[b_id], to_page, reasons=link_reasons, part=part)
    outcome = computed.outcome
    validate_outcome(outcome["channels"], outcome["result"], outcome["reasons"])  # the reasons fit the contract's pattern
    assert not any(":" in reason for reason in outcome["reasons"])
    sid = sheet["sheet_id"]

    if (name, sid, "status") in DISAGREEMENTS:
        assert outcome["status"] != sheet["expected_status"], "the named disagreement is gone: remove it from the list"
    else:
        assert outcome["status"] == sheet["expected_status"], (outcome["status"], outcome["reasons"])
    for reason in sheet["reasons"]:
        if reason in ("NO_TEXT_LAYER", "DUPLICATE_SHEET"):
            assert reason in outcome["reasons"]

    for channel in sheet["channels_without_differences"]:
        state = outcome["channels"][channel]
        quiet = state["state"] != "unchecked" and state.get("diffs", 0) == 0
        if (name, sheet["sheet_id"], channel) in DISAGREEMENTS:
            assert not quiet, f"the named disagreement on {channel} is gone: remove it from the list"
        else:
            assert quiet, (channel, state)
    for channel in sheet["channels_with_differences"]:
        reported = _reports(outcome["channels"][channel], channel)
        if (name, sid, channel) in DISAGREEMENTS:
            assert not reported, f"the named disagreement on {channel} is gone: remove it from the list"
        else:
            assert reported, (channel, outcome["channels"][channel])

    # A `same` result holds no mask; every other result's mask, if there is one, decodes to the grid it declares.
    if outcome["status"] == "same":
        assert computed.mask is None and outcome["result"]["mask"] is None
    elif computed.mask is not None:
        info = outcome["result"]["mask"]
        decoded = decode_mask(computed.mask)
        assert (decoded.width_px, decoded.height_px) == (info["width_px"], info["height_px"])
        assert info["dpi"] == outcome["result"]["how_compared"]["dpi"]
        import math

        canvas = outcome["result"]["canvas"]
        assert decoded.width_px == math.ceil(canvas["width_pt"] * info["dpi"] / 72)
        assert decoded.height_px == math.ceil(canvas["height_pt"] * info["dpi"] / 72)


def test_every_disagreement_the_list_names_is_a_sheet_of_the_keys(vs1_key) -> None:
    seen = {(t["transition"] if "transition" in t else t["id"], s["sheet_id"]) for t in vs1_key["transitions"] for s in t["sheets"]}
    assert {(n, s) for n, s, _ in DISAGREEMENTS} <= seen


def test_the_moved_label_is_found_where_the_key_says(compare, vs1_key) -> None:
    """V1 to V2, sheet E02: the label «ЩО-1» moved by (+120, +30) pt. The key's boxes are PDF points with the origin at
    the lower left; the engine's are the displayed page with the origin at the top left."""
    transition = next(t for t in vs1_key["transitions"] if (t.get("transition") or t.get("id")) == "V1->V2")
    sheet = next(s for s in transition["sheets"] if s["sheet_id"] == "E02")
    height = next(p for v in vs1_key["versions"] if v["id"] == "V1" for p in v["pages"] if p.get("sheet_id") == "E02")["height_pt"]
    computed = compare("vs1/v1.pdf", 2, "vs1/v2.pdf", 2)
    boxes = [(c["box"]["x"], c["box"]["y"], c["box"]["x"] + c["box"]["width"], c["box"]["y"] + c["box"]["height"])
             for c in computed.outcome["result"]["text_changes"] if "box" in c]
    expected = [change for change in sheet["text_changes"] if change["zone"] == "content"]
    assert expected, "the key holds a content text change for this sheet"

    def overlaps(box, key_box) -> bool:
        x0, y0, x1, y1 = key_box[0], height - key_box[3], key_box[2], height - key_box[1]
        return not (box[2] < x0 or box[0] > x1 or box[3] < y0 or box[1] > y1)

    for change in expected:
        # Both places are found: where the label was (removed) and where it is (added). The key calls this `text_moved`;
        # the original's rule (`WORD_MOVE_PT` = 20 pt) calls a shift of 120 pt a removal and an addition.
        for box in (change["bbox_before"], change["bbox_after"]):
            assert any(overlaps(b, box) for b in boxes), (change, boxes)
    kinds = sorted(c["kind"] for c in computed.outcome["result"]["text_changes"] if c.get("before") == "ЩО-1" or c.get("after") == "ЩО-1")
    assert kinds == ["added", "removed"]


def test_a_table_number_that_changed_is_listed_with_its_numbers(compare) -> None:
    """V1 to V2, sheet E03: `3,0` became `3,6` in a table cell."""
    changes = compare("vs1/v1.pdf", 3, "vs1/v2.pdf", 3).outcome["result"]["text_changes"]
    numbers = [n for c in changes for n in c.get("numbers", [])]
    assert {"before": "3,0", "after": "3,6"} in numbers or any(n["after"].startswith("3") and n["before"] != n["after"] for n in numbers)
