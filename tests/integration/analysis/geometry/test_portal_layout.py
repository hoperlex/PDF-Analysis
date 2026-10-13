"""The block list normalised into ``geometry.portal_blocks`` (`W55B-GEOMETRY-01`), without a store.

:func:`auditmanager.analysis.geometry.portal.read_layout` and the artifact body it feeds:
section 4.9's shape (held by the strict validator in ``geometry_support``, which is first
shown to refuse damaged copies), ``page_number = page_index + 1``, the order by page, ordinal
(null last) and id, ``polygon_points`` left out for a rectangle, ``portal_block_id`` verbatim,
``crop_url`` nowhere, and a refusal with ``portal_blocks_invalid`` for what the stage cannot
use.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from auditmanager.analysis.geometry.maths import GEOMETRY_MISMATCH, GEOMETRY_OK
from auditmanager.analysis.geometry.portal import (
    block_order,
    image_blocks_to_crop,
    portal_blocks_body,
    read_layout,
)
from auditmanager.analysis.ports.artifacts import ROLE_PORTAL_BLOCKS, envelope
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.analysis.geometry.geometry_support import (
    every_string,
    portal_blocks_violations,
)
from tests.integration.analysis.recognised.recognised_support import VERSION_UID, members

STAGE = "page_geometry_extraction"


def _document(raw: bytes) -> dict[str, Any]:
    return json.loads(raw)


def _raw(document: dict[str, Any]) -> bytes:
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _artifact(raw: bytes, page_count: int, verdicts: dict[int, str] | None = None) -> dict[str, Any]:
    layout = read_layout(raw, page_count=page_count, stage_id=STAGE)
    verdicts = verdicts or {page.page_number: GEOMETRY_OK for page in layout.pages}
    return envelope(ROLE_PORTAL_BLOCKS, VERSION_UID, **portal_blocks_body(layout, verdicts))


@pytest.fixture(scope="module")
def baseline() -> bytes:
    return members("ar_baseline.zip").block_list


def _refused(raw: bytes, page_count: int = 8) -> DomainError:
    with pytest.raises(DomainError) as refused:
        read_layout(raw, page_count=page_count, stage_id=STAGE)
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert dict(refused.value.detail_fields)["stage_id"] == STAGE
    return refused.value


# -- the validator is shown to refuse before it is trusted ---------------------------------


def test_the_strict_validator_refuses_damaged_copies(baseline) -> None:
    good = _artifact(baseline, 8)
    assert portal_blocks_violations(good) == []
    damages = [
        lambda d: d.pop("blocks_sha256"),
        lambda d: d.update(extra=1),
        lambda d: d["pages"][0].update(geometry="fine"),
        lambda d: d["pages"][1].update(page_number=7),
        lambda d: d["blocks"][0].update(polygon_points=[]),
        lambda d: d["blocks"][0].update(polygon_points=None),
        lambda d: d["blocks"][0].update(crop_url="https://x"),
        lambda d: d["blocks"][0].update(geometry=GEOMETRY_MISMATCH),
        lambda d: d["blocks"].reverse(),
        lambda d: d["blocks"][0].update(bbox_norm=[0.5, 0.5, 0.4, 0.6]),
        lambda d: d["blocks"][1].update(ordinal=3),            # the stamp
        lambda d: d["blocks"][0].update(portal_block_id="blk_" + "A" * 32),
    ]
    for damage in damages:
        copy_ = copy.deepcopy(good)
        damage(copy_)
        assert portal_blocks_violations(copy_), damage


# -- the shape, from the committed baseline bundle -----------------------------------------


def test_the_baseline_normalises_to_section_4_9(baseline) -> None:
    document = _artifact(baseline, 8)
    assert portal_blocks_violations(document) == []
    assert document["blocks_sha256"] == hashlib.sha256(baseline).hexdigest()
    source = _document(baseline)
    assert [page["page_number"] for page in document["pages"]] == list(range(1, 9))
    assert [(p["width_px"], p["height_px"], p["rotation_deg"]) for p in document["pages"]] == [
        (p["width_px"], p["height_px"], p["rotation"]) for p in source["pages"]
    ]
    by_id = {block["block_id"]: block for block in source["blocks"]}
    assert {b["portal_block_id"] for b in document["blocks"]} == set(by_id)
    for block in document["blocks"]:
        original = by_id[block["portal_block_id"]]          # the bundle's id, verbatim
        assert block["page_number"] == original["page_index"] + 1
        assert block["page_label"] == original["page_label"]
        assert block["ordinal"] == original["ordinal"]
        assert block["block_type"] == original["block_type"]
        assert block["status"] == original["status"]
        assert block["bbox_norm"] == original["coords_norm"]
        assert block["geometry"] == GEOMETRY_OK


def test_crop_url_and_the_portals_document_fields_reach_no_artifact(baseline) -> None:
    document = _artifact(baseline, 8)
    strings = set(every_string(document))
    for forbidden in ("crop_url", "document_id", "document_name", "document_path", "generated_at",
                      "shape_type", "export_status", "coords_norm", "page_index"):
        assert forbidden not in strings
    assert not any("://" in value or "portal.invalid" in value for value in strings)


def test_polygon_points_are_kept_for_a_polygon_and_left_out_for_a_rectangle(baseline) -> None:
    document = _artifact(baseline, 8)
    source = {b["block_id"]: b for b in _document(baseline)["blocks"]}
    polygons = [b for b in document["blocks"] if "polygon_points" in b]
    assert [b["portal_block_id"] for b in polygons] == ["blk_cf8cec69470764643bd45084fc86f83c"]
    assert polygons[0]["polygon_points"] == source[polygons[0]["portal_block_id"]]["polygon_points"]
    # null in the bundle: absent here, never null
    assert all(source[b["portal_block_id"]]["polygon_points"] is None
               for b in document["blocks"] if "polygon_points" not in b)


@pytest.mark.parametrize("spelling", [None, []])
def test_a_rectangles_null_or_empty_polygon_never_reaches_the_artifact(baseline, spelling) -> None:
    edited = _document(baseline)
    for block in edited["blocks"]:
        block["polygon_points"] = spelling
    document = _artifact(_raw(edited), 8)
    assert all("polygon_points" not in block for block in document["blocks"])
    edited["blocks"][0].pop("polygon_points")
    assert all("polygon_points" not in b for b in _artifact(_raw(edited), 8)["blocks"])


@pytest.mark.parametrize("count", [3, 64])
def test_a_polygon_of_three_to_sixty_four_vertices_is_kept(baseline, count) -> None:
    edited = _document(baseline)
    points = [[0.1 + 0.8 * i / count, 0.2 + 0.001 * i] for i in range(count)]
    edited["blocks"][0]["polygon_points"] = points
    document = _artifact(_raw(edited), 8)
    kept = next(b for b in document["blocks"] if b["portal_block_id"] == edited["blocks"][0]["block_id"])
    assert kept["polygon_points"] == points


@pytest.mark.parametrize(
    "points",
    [[[0.1, 0.1]], [[0.1, 0.1], [0.2, 0.2]], [[0.1, 0.1]] * 65, [[0.1, 0.1, 0.1]] * 3,
     [[0.1, 1.5]] * 3, [[0.1, True]] * 3, "0.1,0.1"],
)
def test_a_polygon_outside_the_rule_is_refused(baseline, points) -> None:
    edited = _document(baseline)
    edited["blocks"][4]["polygon_points"] = points
    assert dict(_refused(_raw(edited)).detail_fields)["reason"] == "portal_blocks_invalid"


# -- the order ---------------------------------------------------------------------------


def test_blocks_are_ordered_by_page_then_ordinal_with_null_last_then_id(baseline) -> None:
    edited = _document(baseline)
    template = edited["blocks"][0]
    extra = []
    for n, (page, ordinal) in enumerate([(2, 5), (2, 0), (2, None), (2, 5), (1, 0), (2, None)]):
        block = dict(template, block_id=f"blk_{0xf0 - n:032x}", page_index=page - 1, page_label=page,
                     ordinal=ordinal, block_type="stamp" if ordinal is None else "image")
        extra.append(block)
    edited["blocks"] = list(reversed(edited["blocks"] + extra))
    document = _artifact(_raw(edited), 8)
    keys = [(b["page_number"], b["ordinal"] is None, b["ordinal"] or 0, b["portal_block_id"])
            for b in document["blocks"]]
    assert keys == sorted(keys)
    page_two = [(b["ordinal"], b["portal_block_id"][-2:]) for b in document["blocks"] if b["page_number"] == 2]
    assert page_two[0][0] == 0 and page_two[-1][0] is None and page_two[-2][0] is None
    assert [o for o, _ in page_two].count(5) == 2
    fives = [i for o, i in page_two if o == 5]
    assert fives == sorted(fives), "equal ordinals fall back to the identifier"


def test_the_order_key_puts_a_null_ordinal_after_any_number() -> None:
    from auditmanager.analysis.geometry.portal import PortalBlockGeometry

    def block(ordinal, ident):
        return PortalBlockGeometry(ident, 1, 1, ordinal, "text", "recognized", (0, 0, 1, 1), None)

    assert block_order(block(10**9, "blk_b")) < block_order(block(None, "blk_a"))
    assert block_order(block(0, "blk_b")) < block_order(block(1, "blk_a"))


# -- the per-block geometry and the crop selection ---------------------------------------


def test_every_block_repeats_its_pages_verdict_and_only_ok_image_blocks_are_cut(baseline) -> None:
    layout = read_layout(baseline, page_count=8, stage_id=STAGE)
    verdicts = {page.page_number: GEOMETRY_OK for page in layout.pages}
    verdicts[3] = GEOMETRY_MISMATCH                          # the rectangle IMAGE block's page
    body = portal_blocks_body(layout, verdicts)
    assert {b["geometry"] for b in body["blocks"] if b["page_number"] == 3} == {GEOMETRY_MISMATCH}
    assert {b["geometry"] for b in body["blocks"] if b["page_number"] != 3} == {GEOMETRY_OK}
    assert body["pages"][2]["geometry"] == GEOMETRY_MISMATCH
    assert [b.portal_block_id for b in image_blocks_to_crop(layout, verdicts)] == [
        "blk_cf8cec69470764643bd45084fc86f83c"
    ]


# -- refusals ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(schema_version=2),
        lambda d: d.update(schema_version=True),
        lambda d: d.update(coordinate_space="normalized_page_bottom_left"),
        lambda d: d["pages"][0].update(width_px=0),
        lambda d: d["pages"][0].update(height_px=1.5),
        lambda d: d["pages"][0].update(rotation=45),
        lambda d: d["pages"][1].update(page_index=0),            # a page repeated
        lambda d: d["pages"][0].update(page_index=8),
        lambda d: d["blocks"][0].update(page_label=0),
        lambda d: d["blocks"][0].update(ordinal=-1),
        lambda d: d["blocks"][0].update(ordinal=True),
        lambda d: d["blocks"][0].update(status="Recognized"),
        lambda d: d["blocks"][0].update(coords_norm=[0.1, 0.1, 0.1, 0.2]),
        lambda d: d["blocks"][0].update(coords_norm=[0.1, 0.3, 0.2, 0.2]),
        lambda d: d["blocks"][0].update(coords_norm=[0.1, 0.1, 1.2, 0.2]),
        lambda d: d["blocks"][0].update(coords_norm=[0.1, 0.1, 0.2]),
        lambda d: d["blocks"][0].update(coords_norm=None),
        lambda d: d["pages"].__setitem__(0, "page"),
    ],
)
def test_what_the_stage_cannot_use_is_refused_as_portal_blocks_invalid(baseline, edit) -> None:
    edited = _document(baseline)
    edit(edited)
    error = _refused(_raw(edited))
    assert dict(error.detail_fields)["reason"] == "portal_blocks_invalid"


def test_the_recognised_readers_strict_checks_run_first(baseline) -> None:
    """``read_block_list`` (`W55B-RECOGNISED-01`) is called, not restated: its own refusals
    (a malformed id, a page count other than the PDF's) come back unchanged."""
    edited = _document(baseline)
    edited["blocks"][0]["block_id"] = "blk_short"
    assert dict(_refused(_raw(edited)).detail_fields)["reason"] == "portal_blocks_invalid"
    assert dict(_refused(baseline, page_count=9).detail_fields)["reason"] == "portal_blocks_page_mismatch"
    assert dict(_refused(b"\\xff not json").detail_fields)["reason"] == "portal_blocks_invalid"
