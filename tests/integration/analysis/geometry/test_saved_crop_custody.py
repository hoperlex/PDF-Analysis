"""Supplied saved geometry refs and bytes agree before future IMAGE analysis."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace

import pytest
from PIL import Image

from auditmanager.analysis.engine.result import ArtifactRef, StageResult, StageStatus
from auditmanager.analysis.engine.serialization import canonical_bytes
from auditmanager.analysis.geometry.crops import crop_record, encode_png
from auditmanager.analysis.geometry.maths import CropPlan, GEOMETRY_OK
from auditmanager.analysis.geometry.portal import portal_blocks_body, read_layout
from auditmanager.analysis.geometry.saved_crop_custody import (
    RunScopedGeometryStage,
    SavedCropCustodyRefused,
    check_saved_crop_bytes,
)
from auditmanager.analysis.ports.artifacts import ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS, envelope
from tests.integration.analysis.recognised.recognised_support import members


RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _reference(role: str, blob_number: int, payload: bytes) -> ArtifactRef:
    return ArtifactRef(
        role=role, blob_id="blob_" + str(blob_number) * 26,
        sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload),
        media_type="image/png" if role == "geometry.crop_image" else "application/json",
    )


def _fixture() -> tuple[RunScopedGeometryStage, dict[str, bytes]]:
    raw = members("ar_baseline.zip").block_list
    layout = read_layout(raw, page_count=8)
    portal = envelope(
        ROLE_PORTAL_BLOCKS, VERSION,
        **portal_blocks_body(layout, {page.page_number: GEOMETRY_OK for page in layout.pages}),
    )
    portal_bytes = canonical_bytes(portal)
    portal_ref = _reference(ROLE_PORTAL_BLOCKS, 2, portal_bytes)
    image_blocks = [block for block in layout.blocks if block.block_type == "image"]
    records = []
    crop_refs = []
    payloads = {portal_ref.blob_id: portal_bytes}
    for index, block in enumerate(image_blocks, start=4):
        image = Image.new("RGB", (800, 800), (index * 20, 10, 10))
        png = encode_png(image)
        ref = _reference("geometry.crop_image", index, png)
        records.append(crop_record(
            block, CropPlan(4.0, 2000, 1000, 0, 0, 800, 800), ref,
            "pypdfium2 test",
        ))
        crop_refs.append(ref)
        payloads[ref.blob_id] = png
    manifest = envelope(
        ROLE_PAGE_CROPS, VERSION, crop_policy="portal_image_blocks", crops=records,
    )
    manifest_bytes = canonical_bytes(manifest)
    manifest_ref = _reference(ROLE_PAGE_CROPS, 3, manifest_bytes)
    payloads[manifest_ref.blob_id] = manifest_bytes
    block_ref = _reference("geometry.block_index", 1, b'{"ignored":"by_this_seam"}')
    produced = StageResult(
        stage_id="page_geometry_extraction", stage_version="1.0.0",
        status=StageStatus.SUCCEEDED,
        artifacts=(block_ref, manifest_ref, portal_ref, *crop_refs),
    ).to_document()
    stage = RunScopedGeometryStage(
        run_id=RUN, stage_id=produced["stage_id"],
        stage_version=produced["stage_version"], status=produced["status"],
        artifacts=tuple(produced["artifacts"]),
    )
    return stage, payloads


def _check(stage: RunScopedGeometryStage, payloads: dict[str, bytes], **changes: object):
    args = dict(run_id=RUN, version_uid=VERSION, stage=stage, supplied_blob_bytes=payloads)
    args.update(changes)
    return check_saved_crop_bytes(**args)


def _record(stage: RunScopedGeometryStage, role: str) -> dict:
    return next(raw for raw in stage.artifacts if raw["role"] == role)


def _replace_json(
    stage: RunScopedGeometryStage, payloads: dict[str, bytes], role: str, document: dict
) -> None:
    ref = _record(stage, role)
    value = canonical_bytes(document)
    ref["sha256"] = hashlib.sha256(value).hexdigest()
    ref["size_bytes"] = len(value)
    payloads[ref["blob_id"]] = value


def _replace_first_png(
    stage: RunScopedGeometryStage, payloads: dict[str, bytes], value: bytes
) -> None:
    crop_ref = _record(stage, "geometry.crop_image")
    crop_ref["sha256"] = hashlib.sha256(value).hexdigest()
    crop_ref["size_bytes"] = len(value)
    payloads[crop_ref["blob_id"]] = value
    manifest_ref = _record(stage, ROLE_PAGE_CROPS)
    manifest = json.loads(payloads[manifest_ref["blob_id"]])
    manifest["crops"][0]["sha256"] = crop_ref["sha256"]
    manifest["crops"][0]["size_bytes"] = crop_ref["size_bytes"]
    _replace_json(stage, payloads, ROLE_PAGE_CROPS, manifest)


def test_generated_w55b_stage_refs_and_png_bytes_form_a_checked_candidate() -> None:
    stage, payloads = _fixture()
    before = copy.deepcopy((stage, payloads))
    checked = _check(stage, payloads)
    assert (stage, payloads) == before
    assert checked == _check(stage, payloads)
    assert checked.run_id == RUN
    assert checked.cohort.version_uid == VERSION
    assert len(checked.cohort.crops) == len(checked.checked_blob_sha256) == 2
    assert checked.cohort.skipped == ()
    for candidate in checked.cohort.crops:
        assert (candidate.blob.blob_id, candidate.blob.sha256) in checked.checked_blob_sha256


@pytest.mark.parametrize("field", ["run_id", "stage_id", "stage_version", "status"])
def test_saved_stage_identity_must_match_exact_running_request(field: str) -> None:
    stage, payloads = _fixture()
    bad = {"run_id": "run_" + "0" * 26, "stage_id": "text_analysis",
           "stage_version": "9.9.9", "status": "failed"}[field]
    with pytest.raises(SavedCropCustodyRefused, match="saved_stage_identity_or_status_invalid"):
        _check(replace(stage, **{field: bad}), payloads)


def test_duplicate_or_unexpected_saved_reference_refuses() -> None:
    stage, payloads = _fixture()
    duplicate = copy.deepcopy(_record(stage, ROLE_PORTAL_BLOCKS))
    duplicate["blob_id"] = "blob_" + "9" * 26
    with pytest.raises(SavedCropCustodyRefused, match="saved_artifact_reference_invalid"):
        _check(replace(stage, artifacts=stage.artifacts + (duplicate,)), payloads)
    bad = copy.deepcopy(stage)
    bad.artifacts[0]["role"] = "unrelated.role"
    with pytest.raises(SavedCropCustodyRefused, match="saved_artifact_reference_invalid"):
        _check(bad, payloads)


def test_missing_or_extra_blob_payload_refuses_before_any_png_check() -> None:
    stage, payloads = _fixture()
    payloads.pop(_record(stage, ROLE_PORTAL_BLOCKS)["blob_id"])
    with pytest.raises(SavedCropCustodyRefused, match="supplied_blob_set_invalid"):
        _check(stage, payloads)
    stage, payloads = _fixture()
    payloads["blob_" + "9" * 26] = b"extra"
    with pytest.raises(SavedCropCustodyRefused, match="supplied_blob_set_invalid"):
        _check(stage, payloads)


def test_one_changed_byte_is_rejected_against_saved_artifact_digest() -> None:
    stage, payloads = _fixture()
    ref = _record(stage, ROLE_PORTAL_BLOCKS)
    original = payloads[ref["blob_id"]]
    payloads[ref["blob_id"]] = original[:-1] + bytes([original[-1] ^ 1])
    with pytest.raises(SavedCropCustodyRefused, match="supplied_blob_bytes_mismatch"):
        _check(stage, payloads)


def test_foreign_version_inside_checksum_valid_artifact_refuses() -> None:
    stage, payloads = _fixture()
    portal_ref = _record(stage, ROLE_PORTAL_BLOCKS)
    portal = json.loads(payloads[portal_ref["blob_id"]])
    portal["version_uid"] = "ver_" + "0" * 26
    _replace_json(stage, payloads, ROLE_PORTAL_BLOCKS, portal)
    with pytest.raises(SavedCropCustodyRefused, match="crop_cohort_invalid"):
        _check(stage, payloads)


def test_checksum_valid_noncanonical_json_refuses() -> None:
    stage, payloads = _fixture()
    ref = _record(stage, ROLE_PORTAL_BLOCKS)
    noncanonical = json.dumps(json.loads(payloads[ref["blob_id"]]), indent=2).encode()
    ref["sha256"] = hashlib.sha256(noncanonical).hexdigest()
    ref["size_bytes"] = len(noncanonical)
    payloads[ref["blob_id"]] = noncanonical
    with pytest.raises(SavedCropCustodyRefused, match="supplied_artifact_not_canonical"):
        _check(stage, payloads)


def test_checksum_valid_nonstandard_json_number_refuses_with_typed_error() -> None:
    stage, payloads = _fixture()
    ref = _record(stage, ROLE_PORTAL_BLOCKS)
    invalid = payloads[ref["blob_id"]].replace(b'"version_uid":', b'"unexpected":NaN,"version_uid":')
    ref["sha256"] = hashlib.sha256(invalid).hexdigest()
    ref["size_bytes"] = len(invalid)
    payloads[ref["blob_id"]] = invalid
    with pytest.raises(SavedCropCustodyRefused, match="supplied_artifact_json_invalid"):
        _check(stage, payloads)


def test_saved_crop_reference_must_equal_the_checked_manifest_reference() -> None:
    stage, payloads = _fixture()
    crop_ref = _record(stage, "geometry.crop_image")
    manifest_ref = _record(stage, ROLE_PAGE_CROPS)
    manifest = json.loads(payloads[manifest_ref["blob_id"]])
    manifest["crops"][0]["sha256"] = "f" * 64
    _replace_json(stage, payloads, ROLE_PAGE_CROPS, manifest)
    assert crop_ref["sha256"] != manifest["crops"][0]["sha256"]
    with pytest.raises(SavedCropCustodyRefused, match="saved_crop_reference_mismatch"):
        _check(stage, payloads)


def test_png_dimensions_and_decode_are_checked_after_matching_digests() -> None:
    stage, payloads = _fixture()
    image = Image.new("RGB", (1000, 800), (5, 5, 5))
    _replace_first_png(stage, payloads, encode_png(image))
    with pytest.raises(SavedCropCustodyRefused, match="crop_png_shape_mismatch"):
        _check(stage, payloads)
    stage, payloads = _fixture()
    _replace_first_png(stage, payloads, b"not a PNG")
    with pytest.raises(SavedCropCustodyRefused, match="crop_png_unreadable"):
        _check(stage, payloads)
