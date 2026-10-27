"""Synthetic crops for the several-image tests (`CMP-EXEC-IMAGES-01`): distinct, checked, small.

A crop here is a byte string that starts with the PNG signature and carries a label, so its digest,
size and blob id are real and two crops differ whenever their labels do. Nothing here decodes one.
"""

from __future__ import annotations

import hashlib
from typing import Any

from auditmanager.executors.image_input import CropImage
from auditmanager.storage.public import derive_blob_id

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png(label: str, *, pad: int = 0) -> bytes:
    return SIGNATURE + label.encode() + b"." * pad


def crop(label: str, *, pad: int = 0) -> CropImage:
    """A crop whose opaque reference is ``crop-<label>``."""
    return CropImage(crop_id=f"crop-{label}", data=png(label, pad=pad))


def descriptor(raw: bytes, **identity: str) -> dict[str, Any]:
    """A descriptor for ``raw`` with the given identity member (``crop_id`` or ``portal_block_id``)."""
    digest = hashlib.sha256(raw).hexdigest()
    return {"blob_id": str(derive_blob_id(sha256=digest, size=len(raw))), **identity,
            "sha256": digest, "size_bytes": len(raw), "media_type": "image/png"}


def fake_descriptor(index: int, size: int, **identity: str) -> dict[str, Any]:
    """A descriptor of an image of ``size`` bytes that need not exist: for limits, not for bytes."""
    digest = hashlib.sha256(f"fake-{index}".encode()).hexdigest()
    return {"blob_id": str(derive_blob_id(sha256=digest, size=size)),
            **(identity or {"crop_id": f"fake-{index}"}),
            "sha256": digest, "size_bytes": size, "media_type": "image/png"}
