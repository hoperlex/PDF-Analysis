"""The inflated masks of the results being viewed, read once and kept within a byte budget.

`CMP-VIEWER-01`. A mask blob is one object per non-``same`` result. Reading it costs a download, an inflation of up to
40 MB and the memory of both, so it is done once per mask at a time (single-flight), at most :data:`DECODE_SLOTS`
masks at once, and the inflated planes are kept for the next tile of the same pair. A blob that fails its format
checks is ``storage_integrity_error`` and is not kept.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from auditmanager.comparison.tiles import errors
from auditmanager.comparison.tiles.cache import ByteCache
from auditmanager.comparison.tiles.limits import DECODE_SLOTS, MASK_CACHE_BYTES
from auditmanager.comparison.tiles.mask import MaskPlanes, MaskRefused, read_mask
from auditmanager.storage.public import BlobNotFoundError, StorageError, parse_blob_id

__all__ = ["MaskStore"]


class MaskStore:
    def __init__(
        self,
        blob_store: Any,
        *,
        cache_bytes: int = MASK_CACHE_BYTES,
        decode_slots: int = DECODE_SLOTS,
        decoder: Callable[[bytes], MaskPlanes] = read_mask,
    ) -> None:
        self._store = blob_store
        self._cache: ByteCache[str, MaskPlanes] = ByteCache(cache_bytes)
        self._slots = threading.BoundedSemaphore(decode_slots)
        self._decode = decoder

    @property
    def cache(self) -> "ByteCache[str, MaskPlanes]":
        return self._cache

    def planes(self, blob_id: str) -> MaskPlanes:
        def load() -> tuple[MaskPlanes, int]:
            with self._slots:
                try:
                    data = self._store.read(parse_blob_id(blob_id), verify=True)
                except BlobNotFoundError:
                    raise errors.not_found("ComparisonMask") from None
                except StorageError as failure:
                    raise errors.storage_failure(failure, blob_id) from None
                try:
                    planes = self._decode(data)
                except MaskRefused as refused:
                    raise errors.integrity(f"mask {refused.reason}", blob_id) from None
                return planes, planes.nbytes

        return self._cache.get_or_load(blob_id, load)
