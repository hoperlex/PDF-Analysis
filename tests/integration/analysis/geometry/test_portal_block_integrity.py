"""``BlockAdapter`` refuses a blob that is missing or is not the one its run recorded.

`W55B-GEOMETRY-01`, on the lane's PostgreSQL and S3. A crop's PNG is read with the SHA-256 and
size its manifest recorded as the declaration, and each JSON artifact of the join with the
digest and size its ``stage_result`` recorded; a blob that is missing, or another object in
its place, is ``storage_integrity_error`` -- never an empty page, never a shorter image.

**Why this module is separate, and binds no socket guard.** The store refuses a mismatched
object by closing the response it was reading, which closes that connection; the client's
next request opens a new one to the lane's S3. The runs harness's ``_no_network`` guard
forbids every new socket, so after the first refusal every later S3 call of a guarded module
would fail. Nothing here can reach a model: the run is driven by the recorded adapter, offline
by construction.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.public import ROLE_PAGE_CROPS, ROLE_PORTAL_BLOCKS
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobNotFoundError, parse_blob_id
from tests.integration.analysis.geometry.reads_support import IMAGE_ID, TEXT_ID, harness, produced
from tests.integration.analysis.geometry.reads_support import crop_blobs as _crop_blobs
from tests.integration.analysis.geometry.reads_support import block_adapter as _adapter
from tests.integration.analysis.geometry.reads_support import stage_result as _stage

# Deliberately not `harness._no_network`: see the module docstring.
engine = harness.engine
blob_store = harness.blob_store
session = harness.session
provider_config = harness.provider_config
recorded_adapter = harness.recorded_adapter
new_key = harness.new_key


class _SwappingStore:
    """The real store, except that one blob has been replaced by another, or is gone.

    Every way of reaching the blob -- its recorded facts, a whole read, a stream -- answers
    for the replacement, so only a reader that holds the bytes to the digest **its own
    record** names can tell.
    """

    def __init__(self, inner: Any, swap: dict[str, str | None]) -> None:
        self._inner = inner
        self._swap = swap

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def _target(self, blob_id: Any) -> Any:
        if str(blob_id) in self._swap:
            other = self._swap[str(blob_id)]
            if other is None:
                raise BlobNotFoundError(blob_id=str(blob_id))
            return parse_blob_id(other)
        return blob_id

    def inspect(self, blob_id: Any) -> Any:
        return self._inner.inspect(self._target(blob_id))

    def read(self, blob_id: Any, **kwargs: Any) -> bytes:
        return self._inner.read(self._target(blob_id), **kwargs)

    def open_stream(self, blob_id: Any, **kwargs: Any) -> Any:
        return self._inner.open_stream(self._target(blob_id), **kwargs)


@pytest.mark.parametrize("fault", ["missing", "other bytes"])
def test_a_crop_blob_that_is_missing_or_not_the_recorded_one_is_an_integrity_error(
    session, blob_store, produced, fault
) -> None:
    first, second = _crop_blobs(session, produced["run_id"])
    store = _SwappingStore(blob_store, {first: None if fault == "missing" else second})
    adapter = _adapter(session, store)
    view = produced["adapter"].list_portal_blocks(version_uid=produced["version_uid"])
    target = next(b.portal_block_id for b in view.blocks if b.crop is not None and b.portal_block_id == IMAGE_ID)
    with pytest.raises(DomainError) as refused:
        adapter.read_portal_block_crop(version_uid=produced["version_uid"], portal_block_id=target)
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR


@pytest.mark.parametrize("role", [ROLE_PORTAL_BLOCKS, ROLE_PAGE_CROPS, "prepared.recognised_text"])
def test_a_joined_artifact_that_is_missing_or_altered_is_an_integrity_error(
    session, blob_store, produced, role
) -> None:
    run_id = produced["run_id"]
    stage = "source_preparation" if role.startswith("prepared.") else "page_geometry_extraction"
    blob = next(a["blob_id"] for a in _stage(session, run_id, stage).artifacts if a["role"] == role)
    other = next(a["blob_id"] for a in _stage(session, run_id, "page_geometry_extraction").artifacts
                 if a["role"] == "geometry.block_index")
    for swap in (None, other):
        with pytest.raises(DomainError) as refused:
            _adapter(session, _SwappingStore(blob_store, {blob: swap})).list_portal_blocks(
                version_uid=produced["version_uid"]
            )
        assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR, (role, swap)


@pytest.mark.parametrize("fault", ["crop of a text block", "crop on a mismatch page"])
def test_a_crop_recorded_for_a_block_that_cannot_have_one_is_an_integrity_error(
    produced, monkeypatch, fault
) -> None:
    """The stage never cuts a crop for a block that is not an IMAGE block or for a block on a
    page marked ``geometry_mismatch``; the reader, which joins three artifacts by identifier,
    refuses a manifest that says otherwise instead of serving a crop for the wrong thing.

    The manifest and the block list are doctored **after** their digests were checked, because
    the digest check is a different guard (the two tests above); this one is the join's own."""
    adapter = produced["adapter"]
    read = adapter._portal_document

    def doctored(reference, role, version_uid):
        document = read(reference, role, version_uid)
        if fault == "crop of a text block" and role == ROLE_PAGE_CROPS:
            record = dict(document["crops"][0])
            record["portal_block_id"] = TEXT_ID
            return {**document, "crops": [*document["crops"], record]}
        if fault == "crop on a mismatch page" and role == ROLE_PORTAL_BLOCKS:
            return {
                **document,
                "blocks": [
                    {**block, "geometry": "geometry_mismatch"} if block["portal_block_id"] == IMAGE_ID else block
                    for block in document["blocks"]
                ],
            }
        return document

    monkeypatch.setattr(adapter, "_portal_document", doctored)
    with pytest.raises(DomainError) as refused:
        adapter.list_portal_blocks(version_uid=produced["version_uid"])
    assert refused.value.code is ErrorCode.STORAGE_INTEGRITY_ERROR
    assert dict(refused.value.detail_fields) == {"role": ROLE_PAGE_CROPS}
