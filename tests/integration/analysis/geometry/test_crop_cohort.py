"""The W56b crop input is all checked IMAGE blocks or an explicit refusal."""

from __future__ import annotations

import copy

import pytest

from auditmanager.analysis.geometry.crop_cohort import (
    CropCohortRefused,
    prepare_image_crop_cohort,
)


VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
IMAGE_OK = "blk_" + "1" * 32
TEXT = "blk_" + "2" * 32
IMAGE_SKIPPED = "blk_" + "3" * 32
BLOB = "blob_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _documents() -> tuple[dict, dict]:
    portal = {
        "artifact_role": "geometry.portal_blocks", "artifact_version": "1.0.0",
        "version_uid": VERSION, "blocks_sha256": "a" * 64,
        "pages": [
            {"page_number": 1, "width_px": 2000, "height_px": 1000,
             "rotation_deg": 0, "geometry": "ok"},
            {"page_number": 2, "width_px": 2000, "height_px": 1000,
             "rotation_deg": 0, "geometry": "geometry_mismatch"},
        ],
        "blocks": [
            {"portal_block_id": IMAGE_OK, "page_number": 1, "page_label": 1,
             "ordinal": 0, "block_type": "image", "status": "complete",
             "bbox_norm": [0.1, 0.2, 0.8, 0.7], "geometry": "ok"},
            {"portal_block_id": TEXT, "page_number": 1, "page_label": 1,
             "ordinal": 1, "block_type": "text", "status": "complete",
             "bbox_norm": [0.2, 0.2, 0.7, 0.8], "geometry": "ok"},
            {"portal_block_id": IMAGE_SKIPPED, "page_number": 2, "page_label": 2,
             "ordinal": 0, "block_type": "image", "status": "complete",
             "bbox_norm": [0.1, 0.2, 0.8, 0.7], "geometry": "geometry_mismatch"},
        ],
    }
    crop = {
        "portal_block_id": IMAGE_OK, "page_number": 1,
        "bbox_norm": [0.1, 0.2, 0.8, 0.7],
        "render_profile": {
            "renderer": "pypdfium2 test", "scale": 4.0,
            "min_long_side_px": 800, "max_pixels": 4_000_000, "format": "png",
        },
        "blob_id": BLOB, "sha256": "b" * 64, "size_bytes": 1234,
        "width_px": 1000, "height_px": 500,
    }
    manifest = {
        "artifact_role": "geometry.page_crops", "artifact_version": "1.0.0",
        "version_uid": VERSION, "crop_policy": "portal_image_blocks",
        "crops": [crop],
    }
    return portal, manifest


def _prepare(portal: dict, manifest: dict, **changes: object):
    values = dict(
        version_uid=VERSION, portal_blocks_document=portal,
        crop_manifest_document=manifest,
    )
    values.update(changes)
    return prepare_image_crop_cohort(**values)


def test_complete_cohort_keeps_blob_identity_and_explicit_geometry_skip() -> None:
    portal, manifest = _documents()
    before = copy.deepcopy((portal, manifest))
    cohort = _prepare(portal, manifest)
    assert (portal, manifest) == before
    assert cohort == _prepare(portal, manifest)
    assert (cohort.version_uid, cohort.blocks_sha256) == (VERSION, "a" * 64)
    assert len(cohort.crops) == 1
    crop = cohort.crops[0]
    assert (crop.portal_block_id, crop.page_number, crop.bbox_norm) == (
        IMAGE_OK, 1, (0.1, 0.2, 0.8, 0.7)
    )
    assert (crop.blob.role, crop.blob.blob_id, crop.blob.sha256,
            crop.blob.size_bytes, crop.blob.media_type) == (
        "geometry.crop_image", BLOB, "b" * 64, 1234, "image/png"
    )
    assert [(item.portal_block_id, item.page_number, item.reason)
            for item in cohort.skipped] == [(IMAGE_SKIPPED, 2, "geometry_mismatch")]


@pytest.mark.parametrize("which", ["portal", "manifest"])
def test_foreign_version_document_refuses(which: str) -> None:
    portal, manifest = _documents()
    document = portal if which == "portal" else manifest
    document["version_uid"] = "ver_" + "0" * 26
    with pytest.raises(CropCohortRefused, match="artifact_role_version_or_shape_mismatch"):
        _prepare(portal, manifest)


def test_missing_checked_crop_refuses_the_whole_cohort() -> None:
    portal, manifest = _documents()
    manifest["crops"].clear()
    with pytest.raises(CropCohortRefused, match="crop_cohort_incomplete_or_extra"):
        _prepare(portal, manifest)


@pytest.mark.parametrize("replacement", [TEXT, IMAGE_SKIPPED])
def test_crop_of_text_or_unchecked_image_is_not_accepted(replacement: str) -> None:
    portal, manifest = _documents()
    manifest["crops"][0]["portal_block_id"] = replacement
    with pytest.raises(CropCohortRefused, match="crop_cohort_incomplete_or_extra"):
        _prepare(portal, manifest)


def test_duplicate_crop_refuses_even_when_both_records_are_valid() -> None:
    portal, manifest = _documents()
    manifest["crops"].append(copy.deepcopy(manifest["crops"][0]))
    with pytest.raises(CropCohortRefused, match="crop_duplicate"):
        _prepare(portal, manifest)


def test_duplicate_or_unsorted_portal_block_refuses() -> None:
    portal, manifest = _documents()
    portal["blocks"].append(copy.deepcopy(portal["blocks"][0]))
    with pytest.raises(CropCohortRefused, match="portal_blocks_invalid"):
        _prepare(portal, manifest)
    portal, manifest = _documents()
    portal["blocks"][:2] = portal["blocks"][:2][::-1]
    with pytest.raises(CropCohortRefused, match="portal_blocks_unordered"):
        _prepare(portal, manifest)


@pytest.mark.parametrize("field", ["page_number", "bbox_norm"])
def test_crop_must_match_exact_block_region(field: str) -> None:
    portal, manifest = _documents()
    manifest["crops"][0][field] = 2 if field == "page_number" else [0.1, 0.2, 0.9, 0.7]
    with pytest.raises(CropCohortRefused, match="crop_block_region_mismatch"):
        _prepare(portal, manifest)


def test_page_and_block_geometry_verdicts_must_agree() -> None:
    portal, manifest = _documents()
    portal["blocks"][0]["geometry"] = "geometry_mismatch"
    with pytest.raises(CropCohortRefused, match="portal_blocks_invalid"):
        _prepare(portal, manifest)


@pytest.mark.parametrize(
    ("field", "value"),
    [("blob_id", "blob_bad"), ("sha256", "f" * 63),
     ("size_bytes", 0), ("width_px", 9000), ("height_px", 0)],
)
def test_malformed_or_over_budget_crop_refuses(field: str, value: object) -> None:
    portal, manifest = _documents()
    manifest["crops"][0][field] = value
    with pytest.raises(CropCohortRefused, match="crop_record_invalid|crop_reference_invalid"):
        _prepare(portal, manifest)


def test_no_checked_images_is_explicitly_distinct_from_missing_crops() -> None:
    portal, manifest = _documents()
    portal["pages"][0]["geometry"] = "geometry_mismatch"
    for block in portal["blocks"][:2]:
        block["geometry"] = "geometry_mismatch"
    manifest["crops"].clear()
    cohort = _prepare(portal, manifest)
    assert cohort.crops == ()
    assert {item.portal_block_id for item in cohort.skipped} == {IMAGE_OK, IMAGE_SKIPPED}


def test_nonfinite_and_huge_numeric_inputs_refuse_as_validation_errors() -> None:
    portal, manifest = _documents()
    manifest["crops"][0]["render_profile"]["scale"] = 10 ** 1000
    with pytest.raises(CropCohortRefused, match="crop_record_invalid"):
        _prepare(portal, manifest)
    portal, manifest = _documents()
    portal["blocks"][0]["bbox_norm"][2] = 10 ** 1000
    with pytest.raises(CropCohortRefused, match="region_invalid"):
        _prepare(portal, manifest)


def test_committed_bundle_geometry_producer_feeds_selector_without_rendering() -> None:
    from auditmanager.analysis.engine.result import ArtifactRef
    from auditmanager.analysis.geometry.maths import CropPlan, GEOMETRY_OK
    from auditmanager.analysis.geometry.portal import portal_blocks_body, read_layout
    from auditmanager.analysis.geometry.crops import crop_record
    from auditmanager.analysis.ports.artifacts import ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS, envelope
    from tests.integration.analysis.recognised.recognised_support import members

    raw = members("ar_baseline.zip").block_list
    layout = read_layout(raw, page_count=8)
    portal = envelope(ROLE_PORTAL_BLOCKS, VERSION, **portal_blocks_body(
        layout, {page.page_number: GEOMETRY_OK for page in layout.pages}
    ))
    images = [block for block in layout.blocks if block.block_type == "image"]
    records = [crop_record(
        block, CropPlan(4.0, 2000, 1000, 0, 0, 800, 800),
        ArtifactRef("geometry.crop_image", "blob_" + str(index) * 26,
                    str(index) * 64, 1234, "image/png"),
        "pypdfium2 test",
    ) for index, block in enumerate(images, start=1)]
    manifest = envelope(ROLE_PAGE_CROPS, VERSION,
                        crop_policy="portal_image_blocks", crops=records)
    cohort = _prepare(portal, manifest)
    assert [item.portal_block_id for item in cohort.crops] == [
        block.portal_block_id for block in images
    ]
    assert cohort.skipped == ()
