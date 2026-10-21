"""An OCR quote candidate is bound to one textless page and one checked TEXT region."""

from __future__ import annotations

import copy

import pytest

from auditmanager.analysis.recognised.region_candidate import (
    RecognisedRegionRefused,
    bind_recognised_region_candidate,
)


VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TEXT = "blk_" + "1" * 32
IMAGE = "blk_" + "2" * 32
OTHER = "blk_" + "3" * 32
QUOTE = "кровля плоская"


def _documents() -> tuple[dict, dict]:
    recognised = {
        "artifact_role": "prepared.recognised_text",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "results_sha256": "a" * 64,
        "entries": [
            {"portal_block_id": TEXT, "page_number": 1, "kind": "recognised_text",
             "quote_source": "recognised", "text": f"АР: {QUOTE}; уклон 2%",
             "flags": ["mixed_script"]},
            {"portal_block_id": IMAGE, "page_number": 1, "kind": "portal_description",
             "text": f"IMAGE: {QUOTE}"},
            {"portal_block_id": OTHER, "page_number": 2, "kind": "recognised_text",
             "quote_source": "recognised", "text": QUOTE, "flags": []},
        ],
    }
    geometry = {
        "artifact_role": "geometry.portal_blocks",
        "artifact_version": "1.0.0",
        "version_uid": VERSION,
        "blocks_sha256": "b" * 64,
        "pages": [
            {"page_number": 1, "width_px": 2000, "height_px": 1000,
             "rotation_deg": 0, "geometry": "ok"},
            {"page_number": 2, "width_px": 2000, "height_px": 1000,
             "rotation_deg": 0, "geometry": "ok"},
        ],
        "blocks": [
            {"portal_block_id": TEXT, "page_number": 1, "page_label": 1,
             "ordinal": 0, "block_type": "text", "status": "complete",
             "bbox_norm": [0.1, 0.2, 0.8, 0.7], "geometry": "ok",
             "polygon_points": [[0.1, 0.2], [0.8, 0.2], [0.8, 0.7]]},
            {"portal_block_id": IMAGE, "page_number": 1, "page_label": 1,
             "ordinal": 1, "block_type": "image", "status": "complete",
             "bbox_norm": [0.2, 0.2, 0.7, 0.8], "geometry": "ok"},
            {"portal_block_id": OTHER, "page_number": 2, "page_label": 2,
             "ordinal": 0, "block_type": "text", "status": "complete",
             "bbox_norm": [0.1, 0.2, 0.8, 0.7], "geometry": "ok"},
        ],
    }
    return recognised, geometry


def _bind(recognised: dict, geometry: dict, **changes: object):
    args = dict(
        version_uid=VERSION, textless_pages=(1,),
        recognised_document=recognised, portal_blocks_document=geometry,
        portal_block_id=TEXT, page_number=1, quote=QUOTE,
    )
    args.update(changes)
    return bind_recognised_region_candidate(**args)


def test_exact_quote_keeps_ocr_status_block_coordinates_and_quality() -> None:
    recognised, geometry = _documents()
    before = copy.deepcopy((recognised, geometry))
    candidate = _bind(recognised, geometry)
    assert (recognised, geometry) == before
    assert candidate == _bind(recognised, geometry)
    assert candidate.version_uid == VERSION
    assert (candidate.portal_block_id, candidate.page_number) == (TEXT, 1)
    assert (candidate.quote, candidate.quote_source) == (QUOTE, "recognised")
    assert (candidate.ocr_char_start, candidate.ocr_char_end) == (4, 4 + len(QUOTE))
    assert candidate.bbox_norm == (0.1, 0.2, 0.8, 0.7)
    assert candidate.polygon_points == ((0.1, 0.2), (0.8, 0.2), (0.8, 0.7))
    assert candidate.quality_flags == ("mixed_script",)
    assert candidate.results_sha256 == "a" * 64
    assert candidate.blocks_sha256 == "b" * 64


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"version_uid": "ver_wrong"}, "version_identity_invalid"),
        ({"textless_pages": None}, "unbound_legacy_recognition"),
        ({"textless_pages": ()}, "page_not_textless"),
        ({"portal_block_id": IMAGE}, "region_source_mismatch"),
        ({"portal_block_id": OTHER, "page_number": 2}, "page_not_textless"),
        ({"quote": "уклон 3%"}, "quote_absent_from_recognised_block"),
        ({"quote": " "}, "quote_claim_invalid"),
    ],
)
def test_a_claim_cannot_cross_page_block_kind_or_actual_ocr_text(change, reason) -> None:
    recognised, geometry = _documents()
    with pytest.raises(RecognisedRegionRefused, match=reason):
        _bind(recognised, geometry, **change)


@pytest.mark.parametrize("which", ["recognised", "geometry"])
def test_both_artifacts_must_name_the_exact_version(which: str) -> None:
    recognised, geometry = _documents()
    document = recognised if which == "recognised" else geometry
    document["version_uid"] = "ver_" + "0" * 26
    with pytest.raises(RecognisedRegionRefused, match="artifact_mismatch"):
        _bind(recognised, geometry)


@pytest.mark.parametrize("field", ["page", "block"])
def test_mismatched_geometry_cannot_create_a_region(field: str) -> None:
    recognised, geometry = _documents()
    selected = geometry["pages"][0] if field == "page" else geometry["blocks"][0]
    selected["geometry"] = "geometry_mismatch"
    with pytest.raises(RecognisedRegionRefused, match="portal_geometry_unverified"):
        _bind(recognised, geometry)


def test_other_page_or_image_text_never_repairs_a_claim() -> None:
    recognised, geometry = _documents()
    recognised["entries"][0]["text"] = "АР: другая крыша"
    with pytest.raises(RecognisedRegionRefused, match="quote_absent_from_recognised_block"):
        _bind(recognised, geometry)


def test_region_and_source_page_must_match() -> None:
    recognised, geometry = _documents()
    geometry["blocks"][0]["page_number"] = 2
    with pytest.raises(RecognisedRegionRefused, match="region_source_mismatch"):
        _bind(recognised, geometry)


@pytest.mark.parametrize("collection", ["blocks", "pages"])
def test_duplicate_region_or_page_refuses(collection: str) -> None:
    recognised, geometry = _documents()
    geometry[collection].append(copy.deepcopy(geometry[collection][0]))
    with pytest.raises(RecognisedRegionRefused, match="region_binding_ambiguous_or_absent"):
        _bind(recognised, geometry)


@pytest.mark.parametrize("box", [[0.8, 0.2, 0.1, 0.7], [0.1, 0.2, float("nan"), 0.7]])
def test_invalid_geometry_box_refuses(box: list[float]) -> None:
    recognised, geometry = _documents()
    geometry["blocks"][0]["bbox_norm"] = box
    with pytest.raises(RecognisedRegionRefused, match="portal_region_invalid"):
        _bind(recognised, geometry)


def test_two_exact_occurrences_are_ambiguous_without_an_explicit_ocr_offset() -> None:
    recognised, geometry = _documents()
    recognised["entries"][0]["text"] = f"{QUOTE}; {QUOTE}"
    with pytest.raises(RecognisedRegionRefused, match="quote_ambiguous_in_recognised_block"):
        _bind(recognised, geometry)


def test_unknown_ocr_flag_refuses_instead_of_becoming_a_quality_signal() -> None:
    recognised, geometry = _documents()
    recognised["entries"][0]["flags"] = ["invented"]
    with pytest.raises(RecognisedRegionRefused, match="invalid_recognised_entry"):
        _bind(recognised, geometry)


def test_committed_portal_bundle_producers_feed_the_pure_candidate() -> None:
    """Use the W55b readers/builders, without a database, Blob or stage runner."""
    from auditmanager.analysis.geometry.maths import GEOMETRY_OK
    from auditmanager.analysis.geometry.portal import portal_blocks_body, read_layout
    from auditmanager.analysis.ports.artifacts import ROLE_PORTAL_BLOCKS, envelope
    from auditmanager.analysis.recognised.artifact import build_recognised_text
    from auditmanager.analysis.recognised.portal import read_portal
    from tests.integration.analysis.recognised.recognised_support import members

    bundle = members("ar_baseline.zip")
    portal = read_portal(bundle.markdown, bundle.block_list, page_count=8)
    layout = read_layout(bundle.block_list, page_count=8)
    recognised = build_recognised_text(portal, version_uid=VERSION, markdown=bundle.markdown)
    geometry = envelope(
        ROLE_PORTAL_BLOCKS, VERSION,
        **portal_blocks_body(layout, {page.page_number: GEOMETRY_OK for page in layout.pages}),
    )
    entry = next(item for item in recognised["entries"]
                 if item["kind"] == "recognised_text" and item["text"].strip())
    candidate = _bind(
        recognised, geometry, textless_pages=(entry["page_number"],),
        portal_block_id=entry["portal_block_id"], page_number=entry["page_number"],
        quote=entry["text"],
    )
    assert candidate.quote == entry["text"]
    assert candidate.quote_source == "recognised"
    assert candidate.portal_block_id == entry["portal_block_id"]
