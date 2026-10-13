"""The crops: PNG bytes, their content-addressed blobs, and the manifest that names them.

`W55B-GEOMETRY-01` (``P02_SEAMS`` sections 4.5 and 4.10). A crop is encoded once with Pillow
and published as a blob of role ``geometry.crop_image`` (``image/png``). Blobs are
content-addressed -- ``blob_id`` is derived from ``(sha256, size)`` -- and
:class:`CropPublisher` publishes each distinct PNG **once**: a second crop with the same bytes
reuses the first one's reference, so the stage result names every blob exactly once (the
stage-result schema's ``uniqueItems``, and the executor binds each reference once).

The manifest names a crop by ``portal_block_id`` and ``blob_id`` and records its digest, size,
pixels and render profile; it never holds an object key or a URL. Pixel bytes are stable
within one environment only (the renderer and Pillow are part of them), so nothing here or in
the tests records crop bytes.
"""

from __future__ import annotations

import io
from typing import Any, Final

from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.analysis.engine.serialization import sha256_hex
from auditmanager.analysis.geometry.maths import MAX_PIXELS, MIN_LONG_SIDE_PX, CropPlan
from auditmanager.analysis.geometry.portal import PortalBlockGeometry
from auditmanager.analysis.ports.artifacts import ROLE_CROP_IMAGE, blob_role_for
from auditmanager.storage.public import BlobStore

#: The crop's media type and its ``render_profile.format``.
PNG_MEDIA_TYPE: Final[str] = "image/png"
PNG_FORMAT: Final[str] = "png"
#: zlib's default level: an explicit argument, so a Pillow default moving cannot move a byte.
PNG_COMPRESS_LEVEL: Final[int] = 6
#: Every PNG begins with these eight bytes.
PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"


def encode_png(image: Any) -> bytes:
    """The image as PNG bytes: no metadata chunk, no timestamp, a pinned compression level."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False)
    return buffer.getvalue()


class CropPublisher:
    """Publishes each distinct PNG once and remembers its reference by digest."""

    def __init__(self, store: BlobStore) -> None:
        self._store = store
        self._published: dict[str, ArtifactRef] = {}

    def publish(self, png: bytes) -> ArtifactRef:
        digest = sha256_hex(png)
        known = self._published.get(digest)
        if known is not None:
            return known
        published = self._store.put_blob(
            png,
            declared_sha256=digest,
            declared_size=len(png),
            role=blob_role_for(ROLE_CROP_IMAGE),
            media_type=PNG_MEDIA_TYPE,
        )
        reference = ArtifactRef(
            role=ROLE_CROP_IMAGE,
            blob_id=str(published.blob_id),
            sha256=published.sha256,
            size_bytes=published.size,
            media_type=published.media_type,
        )
        self._published[digest] = reference
        return reference

    @property
    def references(self) -> tuple[ArtifactRef, ...]:
        """Every distinct crop blob, in the order it was first published."""
        return tuple(self._published.values())


def render_profile(renderer: str, plan: CropPlan) -> dict[str, Any]:
    """``render_profile`` of one manifest record (the crop manifest schema's five members)."""
    return {
        "renderer": renderer,
        "scale": plan.scale,
        "min_long_side_px": MIN_LONG_SIDE_PX,
        "max_pixels": MAX_PIXELS,
        "format": PNG_FORMAT,
    }


def crop_record(
    block: PortalBlockGeometry, plan: CropPlan, reference: ArtifactRef, renderer: str
) -> dict[str, Any]:
    """One ``crops`` entry of ``geometry.page_crops``. ``width_px`` x ``height_px`` is the clip."""
    return {
        "portal_block_id": block.portal_block_id,
        "page_number": block.page_number,
        "bbox_norm": list(block.bbox_norm),
        "render_profile": render_profile(renderer, plan),
        "blob_id": reference.blob_id,
        "sha256": reference.sha256,
        "size_bytes": reference.size_bytes,
        "width_px": plan.width,
        "height_px": plan.height,
    }


__all__ = [
    "PNG_COMPRESS_LEVEL",
    "PNG_FORMAT",
    "PNG_MEDIA_TYPE",
    "PNG_SIGNATURE",
    "CropPublisher",
    "crop_record",
    "encode_png",
    "render_profile",
]
