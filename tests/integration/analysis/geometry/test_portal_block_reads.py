"""``BlockAdapter``'s two portal reads over a real run, on the lane's PostgreSQL and S3.

`W55B-GEOMETRY-01`. ``start_audit_run`` and ``execute_run`` (the recorded adapter, offline)
carry a portal-bundle version through the real chain; the shipped adapter then answers
``listVersionPortalBlocks`` and ``streamVersionPortalBlockCrop``:

* ``not_produced`` before a run, ``produced`` after, from the run that produced it;
* the join on ``portal_block_id``: TEXT blocks carry the recognised text and its flags, IMAGE
  blocks the portal's description and their crop, stamps neither; an empty body is left out;
* an unknown version is ``not_found`` for both reads, and so is a block without a crop;
* the crop's bytes are the manifest's (SHA-256); a blob that is missing or not the recorded
  one is ``storage_integrity_error`` (``test_portal_block_integrity.py``, which says why it is
  a module of its own);
* the executor hands the block list to the geometry stage, and every crop blob it published
  is bound to the run;
* a version without a bundle publishes no portal geometry and answers ``not_produced``, while
  ``getVersionBlocks`` answers ``produced`` exactly as before.

The run harness of ``tests/integration/runs`` is loaded by path (``reads_support``).
"""

from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import text

from auditmanager.analysis.public import ROLE_CROP_IMAGE, ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import parse_blob_id
from tests.integration.analysis.geometry.reads_support import (
    ABSENT_VERSION,
    IMAGE_ID,
    POLYGON_ID,
    STAMP_ID,
    TEXT_ID,
    harness,
    produced,
)
from tests.integration.analysis.geometry.reads_support import block_adapter as _adapter
from tests.integration.analysis.geometry.reads_support import crop_blobs as _crop_blobs
from tests.integration.analysis.geometry.reads_support import run_published as _run
from tests.integration.analysis.geometry.reads_support import seed_bundle_version as _seed_bundle_version
from tests.integration.analysis.geometry.reads_support import stage_result as _stage
from tests.integration.analysis.recognised.recognised_support import members

_no_network = harness._no_network
engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
seeded = harness.seeded
new_key = harness.new_key


# -- the listing ---------------------------------------------------------------------------


def test_not_produced_before_a_run_and_produced_by_that_run_after(produced) -> None:
    before = produced["before"]
    assert (before.status, before.produced_by_run_id, before.blocks) == ("not_produced", None, ())
    after = produced["adapter"].list_portal_blocks(version_uid=produced["version_uid"])
    assert after.status == "produced"
    assert after.produced_by_run_id == produced["run_id"]
    assert after.version_uid == produced["version_uid"]
    assert len(after.blocks) == 12


def test_the_join_puts_each_artifact_on_its_block(session, blob_store, produced) -> None:
    view = produced["adapter"].list_portal_blocks(version_uid=produced["version_uid"])
    blocks = {block.portal_block_id: block for block in view.blocks}
    recognised = json.loads(blob_store.read(parse_blob_id(next(
        a["blob_id"] for a in _stage(session, produced["run_id"], "source_preparation").artifacts
        if a["role"] == "prepared.recognised_text"
    ))))
    entries = {entry["portal_block_id"]: entry for entry in recognised["entries"]}
    manifest = json.loads(blob_store.read(parse_blob_id(next(
        a["blob_id"] for a in _stage(session, produced["run_id"], "page_geometry_extraction").artifacts
        if a["role"] == ROLE_PAGE_CROPS
    ))))
    crops = {record["portal_block_id"]: record for record in manifest["crops"]}
    for identifier, block in blocks.items():
        assert block.geometry == "ok"
        if block.block_type == "text":
            assert block.recognised_text is not None
            assert block.recognised_text.text == entries[identifier]["text"]
            assert list(block.recognised_text.flags) == entries[identifier]["flags"]
            assert block.portal_description is None and block.crop is None
        elif block.block_type == "image":
            assert block.portal_description == entries[identifier]["text"]
            assert block.recognised_text is None
            record = crops[identifier]
            assert (block.crop.media_type, block.crop.width_px, block.crop.height_px, block.crop.sha256) == (
                "image/png", record["width_px"], record["height_px"], record["sha256"]
            )
        else:
            assert block.block_type == "stamp" and block.ordinal is None
            assert (block.recognised_text, block.portal_description, block.crop) == (None, None, None)
    assert blocks[POLYGON_ID].polygon_points is not None and len(blocks[POLYGON_ID].polygon_points) == 6
    assert blocks[IMAGE_ID].polygon_points is None
    assert blocks[TEXT_ID].bbox_norm == (0.0952, 0.0831, 0.9048, 0.9691)


def test_the_blocks_arrive_in_the_ports_order(produced) -> None:
    view = produced["adapter"].list_portal_blocks(version_uid=produced["version_uid"])
    keys = [(b.page_number, b.ordinal is None, b.ordinal or 0, b.portal_block_id) for b in view.blocks]
    assert keys == sorted(keys)
    assert [b.portal_block_id for b in view.blocks[:2]] == [TEXT_ID, STAMP_ID]


def test_an_empty_body_is_left_out_never_sent_empty(
    session, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    markdown = members("ar_baseline.zip").markdown.decode("utf-8")
    lines = markdown.split("\n")
    emptied: list[str] = []
    skip = False
    for line in lines:
        if line.startswith("### BLOCK #") and (TEXT_ID in line or IMAGE_ID in line):
            emptied += [line, ""]
            skip = True
            continue
        if skip and (line.startswith("### BLOCK #") or line.startswith("## Page")):
            skip = False
        if not skip:
            emptied.append(line)
    version_uid = _seed_bundle_version(session, blob_store, markdown="\n".join(emptied).encode("utf-8"))
    _run(session, version_uid, new_key("geometry-empty-bodies"), blob_store, recorded_adapter, provider_config)
    blocks = {b.portal_block_id: b for b in _adapter(session, blob_store).list_portal_blocks(version_uid=version_uid).blocks}
    assert blocks[TEXT_ID].recognised_text is None
    assert blocks[IMAGE_ID].portal_description is None
    assert blocks[IMAGE_ID].crop is not None, "the crop does not depend on the description"
    assert blocks[POLYGON_ID].portal_description, "the other IMAGE body is untouched"


def test_an_unknown_version_is_not_found_for_both_reads(session, blob_store) -> None:
    adapter = _adapter(session, blob_store)
    for call in (
        lambda: adapter.list_portal_blocks(version_uid=ABSENT_VERSION),
        lambda: adapter.read_portal_block_crop(version_uid=ABSENT_VERSION, portal_block_id=IMAGE_ID),
    ):
        with pytest.raises(DomainError) as refused:
            call()
        assert refused.value.code is ErrorCode.NOT_FOUND


# -- the crop ------------------------------------------------------------------------------


def test_the_crop_is_the_manifests_bytes(produced) -> None:
    view = produced["adapter"].list_portal_blocks(version_uid=produced["version_uid"])
    for identifier in (IMAGE_ID, POLYGON_ID):
        crop = produced["adapter"].read_portal_block_crop(
            version_uid=produced["version_uid"], portal_block_id=identifier
        )
        listed = next(b for b in view.blocks if b.portal_block_id == identifier).crop
        assert crop.media_type == "image/png"
        assert hashlib.sha256(crop.content).hexdigest() == crop.sha256 == listed.sha256
        assert crop.content.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("identifier", [TEXT_ID, STAMP_ID, "blk_" + "0" * 32])
def test_a_block_without_a_crop_is_not_found(produced, identifier) -> None:
    with pytest.raises(DomainError) as refused:
        produced["adapter"].read_portal_block_crop(version_uid=produced["version_uid"], portal_block_id=identifier)
    assert refused.value.code is ErrorCode.NOT_FOUND


def test_a_crop_before_any_run_is_not_found(session, blob_store) -> None:
    version_uid = _seed_bundle_version(session, blob_store)
    with pytest.raises(DomainError) as refused:
        _adapter(session, blob_store).read_portal_block_crop(version_uid=version_uid, portal_block_id=IMAGE_ID)
    assert refused.value.code is ErrorCode.NOT_FOUND


# -- the run that produced it --------------------------------------------------------------


def test_the_executor_hands_the_block_list_to_the_geometry_stage_and_binds_every_crop(session, produced) -> None:
    geometry = _stage(session, produced["run_id"], "page_geometry_extraction")
    assert geometry.status == "succeeded"
    roles = [a["role"] for a in geometry.artifacts]
    assert roles.count(ROLE_PORTAL_BLOCKS) == 1 and roles.count(ROLE_CROP_IMAGE) == 2
    assert geometry.metrics["crop_policy"] == "portal_image_blocks"
    rows = session.execute(
        text(
            "SELECT blob_id, state, artifact_role FROM analysis_artifact_publication "
            "WHERE run_id = :run AND stage_id = 'page_geometry_extraction'"
        ),
        {"run": produced["run_id"]},
    ).mappings().all()
    bound = {row["blob_id"]: (row["state"], row["artifact_role"]) for row in rows}
    for blob_id in _crop_blobs(session, produced["run_id"]):
        assert bound[blob_id] == ("bound", ROLE_CROP_IMAGE)
    assert {state for state, _role in bound.values()} == {"bound"}


def test_a_version_without_a_bundle_produces_no_portal_geometry(
    session, seeded, blob_store, recorded_adapter, provider_config, new_key
) -> None:
    run_id = _run(session, seeded.version_uid, new_key("geometry-bare"), blob_store, recorded_adapter, provider_config)
    geometry = _stage(session, run_id, "page_geometry_extraction")
    assert [a["role"] for a in geometry.artifacts] == ["geometry.block_index", "geometry.page_crops"]
    assert geometry.metrics["crop_policy"] == "none"
    adapter = _adapter(session, blob_store)
    portal = adapter.list_portal_blocks(version_uid=seeded.version_uid)
    assert (portal.status, portal.produced_by_run_id, portal.blocks) == ("not_produced", None, ())
    assert adapter.get_block_index(version_uid=seeded.version_uid).status == "produced"
