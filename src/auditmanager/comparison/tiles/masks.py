"""The inflated masks of the results being viewed, read once and kept within a byte budget.

`CMP-VIEWER-01`. A mask blob is one object per result that has differences in its pixels. Reading it costs a download, an
inflation of up to 40 MB and the memory of both, so it is done once per mask at a time (single-flight), at most
:data:`DECODE_SLOTS` masks at once, and the inflated planes are kept for the next tile of the same pair. The decoder is
the engine's codec (``comparison/engine/mask_codec.py``, the owner of format 1): it refuses a wrong magic, format, layer
count or reserved word, a plane over 40 Mpx and a body whose length after a **bounded** inflation is not the declared
one, and a blob it refuses is ``storage_integrity_error`` and is not kept.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from auditmanager.comparison.engine.mask_codec import DecodedMask, MaskFormatError, decode_mask
from auditmanager.comparison.tiles import errors
from auditmanager.comparison.tiles.cache import ByteCache
from auditmanager.comparison.tiles.limits import DECODE_SLOTS, MASK_CACHE_BYTES
from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

__all__ = ["MaskStore"]


class MaskStore:
    def __init__(
        self,
        blob_store: Any,
        *,
        cache_bytes: int = MASK_CACHE_BYTES,
        decode_slots: int = DECODE_SLOTS,
        decoder: Callable[[bytes], DecodedMask] = decode_mask,
    ) -> None:
        self._store = blob_store
        self._cache: ByteCache[str, DecodedMask] = ByteCache(cache_bytes)
        self._slots = threading.BoundedSemaphore(decode_slots)
        self._decode = decoder

    @property
    def cache(self) -> "ByteCache[str, DecodedMask]":
        return self._cache

    def planes(self, blob_id: str) -> DecodedMask:
        def load() -> tuple[DecodedMask, int]:
            with self._slots:
                try:
                    data = self._store.read(parse_blob_id(blob_id), verify=True)
                except BlobNotFoundError:
                    raise errors.not_found("ComparisonMask") from None
                except StorageError as failure:
                    raise errors.storage_failure(failure, blob_id) from None
                try:
                    planes = self._decode(data)
                except MaskFormatError as refused:
                    raise errors.integrity(f"mask {refused}", blob_id) from None
                return planes, int(planes.packed.nbytes)

        return self._cache.get_or_load(blob_id, load)
