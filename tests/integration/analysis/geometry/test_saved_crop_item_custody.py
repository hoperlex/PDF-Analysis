"""One selected saved crop uses complete metadata without sibling PNG bytes."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from auditmanager.analysis.engine.serialization import canonical_bytes
from auditmanager.analysis.geometry.saved_crop_custody import (
    SavedCropCustodyRefused,
    check_saved_crop_item_bytes,
    prepare_saved_crop_item,
)
from auditmanager.analysis.ports.artifacts import ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS
from tests.integration.analysis.geometry.test_saved_crop_custody import RUN, VERSION, _fixture


def _metadata(stage, payloads):
    return {
        raw["blob_id"]: payloads[raw["blob_id"]]
        for raw in stage.artifacts
        if raw["role"] in {ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS}
    }


def _selected(stage, payloads, *, index=0):
    manifest_ref = next(raw for raw in stage.artifacts if raw["role"] == ROLE_PAGE_CROPS)
    manifest = json.loads(payloads[manifest_ref["blob_id"]])
    return manifest["crops"][index]["portal_block_id"]


def _prepare(stage, payloads, *, block=None):
    return prepare_saved_crop_item(
        run_id=RUN, version_uid=VERSION, stage=stage,
        supplied_metadata_bytes=_metadata(stage, payloads),
        portal_block_id=block or _selected(stage, payloads),
    )


def test_complete_metadata_selects_only_one_png_and_checks_its_bytes() -> None:
    stage, payloads = _fixture()
    before = copy.deepcopy((stage, payloads))
    prepared = _prepare(stage, payloads)
    assert len(prepared.cohort.crops) == 2
    assert prepared.crop.portal_block_id == _selected(stage, payloads)
    assert set(_metadata(stage, payloads)) != set(payloads)
    png = payloads[prepared.crop.blob.blob_id]
    checked = check_saved_crop_item_bytes(prepared=prepared, supplied_png_bytes=png)
    assert checked.checked_blob_sha256 == (
        prepared.crop.blob.blob_id, hashlib.sha256(png).hexdigest(),
    )
    assert checked == check_saved_crop_item_bytes(prepared=prepared, supplied_png_bytes=png)
    assert (stage, payloads) == before


def test_two_blocks_may_share_one_content_addressed_png_ref() -> None:
    stage, payloads = _fixture()
    stage = copy.deepcopy(stage)
    crops = [raw for raw in stage.artifacts if raw["role"] == "geometry.crop_image"]
    assert len(crops) == 2
    manifest_ref = next(raw for raw in stage.artifacts if raw["role"] == ROLE_PAGE_CROPS)
    manifest = json.loads(payloads[manifest_ref["blob_id"]])
    for field in ("blob_id", "sha256", "size_bytes"):
        manifest["crops"][1][field] = manifest["crops"][0][field]
    encoded = canonical_bytes(manifest)
    manifest_ref["sha256"] = hashlib.sha256(encoded).hexdigest()
    manifest_ref["size_bytes"] = len(encoded)
    payloads[manifest_ref["blob_id"]] = encoded
    stage = replace(stage, artifacts=tuple(
        raw for raw in stage.artifacts if raw is not crops[1]
    ))

    prepared = _prepare(stage, payloads, block=manifest["crops"][1]["portal_block_id"])
    assert len(prepared.cohort.crops) == 2
    assert len({crop.blob.blob_id for crop in prepared.cohort.crops}) == 1
    assert check_saved_crop_item_bytes(
        prepared=prepared, supplied_png_bytes=payloads[crops[0]["blob_id"]],
    ).prepared == prepared


@pytest.mark.parametrize("change", ["missing", "extra", "wrong_digest"])
def test_complete_saved_ref_set_is_required(change: str) -> None:
    stage, payloads = _fixture()
    stage = copy.deepcopy(stage)
    crop_refs = [raw for raw in stage.artifacts if raw["role"] == "geometry.crop_image"]
    if change == "missing":
        stage = replace(stage, artifacts=tuple(
            raw for raw in stage.artifacts if raw is not crop_refs[1]
        ))
    elif change == "extra":
        extra = {**crop_refs[0], "blob_id": "blob_" + "9" * 26}
        stage = replace(stage, artifacts=stage.artifacts + (extra,))
    else:
        crop_refs[0]["sha256"] = "f" * 64
    with pytest.raises(SavedCropCustodyRefused, match="saved_crop_reference_mismatch"):
        _prepare(stage, payloads)


def test_unknown_or_nonimage_block_and_corrupt_selected_png_refuse() -> None:
    stage, payloads = _fixture()
    with pytest.raises(SavedCropCustodyRefused, match="selected_crop_unavailable"):
        _prepare(stage, payloads, block="blk_" + "0" * 32)
    prepared = _prepare(stage, payloads)
    png = payloads[prepared.crop.blob.blob_id]
    with pytest.raises(SavedCropCustodyRefused, match="supplied_blob_bytes_mismatch"):
        check_saved_crop_item_bytes(
            prepared=prepared, supplied_png_bytes=png[:-1] + b"x",
        )


def test_metadata_bytes_and_cohort_must_match_saved_stage() -> None:
    stage, payloads = _fixture()
    metadata = _metadata(stage, payloads)
    metadata["blob_" + "9" * 26] = b"extra"
    with pytest.raises(SavedCropCustodyRefused, match="supplied_blob_set_invalid"):
        prepare_saved_crop_item(
            run_id=RUN, version_uid=VERSION, stage=stage,
            supplied_metadata_bytes=metadata, portal_block_id=_selected(stage, payloads),
        )
