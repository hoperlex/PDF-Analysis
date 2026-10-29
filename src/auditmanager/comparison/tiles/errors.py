"""The typed failures of the pair tile, as :class:`~auditmanager.shared.errors.DomainError` values.

`CMP-VIEWER-01`. A tile that does not exist is ``not_found`` (the contract: a pair, a mask or a tile that does not
exist is ``404``). Stored bytes that are not what they say they are -- a mask that fails its format checks, a tile that
is not a PNG of its size, a result whose transform is not an affine -- are ``storage_integrity_error`` (the catalogue's
"the bytes do not match what they claim"): the viewer shows the sheet as unreadable and an operator sees the log line.
A request that cannot be served *now* -- no compose slot, a transform that needs more of page B than one request may
read -- is ``dependency_unavailable`` with the stable class name ``comparison_pair_tiles``, which the viewer retries a
bounded number of times.
"""

from __future__ import annotations

import logging
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode, from_internal
from auditmanager.storage.public import StorageError

__all__ = ["DEPENDENCY", "integrity", "not_found", "storage_failure", "unavailable"]

DEPENDENCY: Final[str] = "comparison_pair_tiles"
_LOG = logging.getLogger("auditmanager.comparison.tiles")


def not_found(what: str) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=what)


def unavailable(why: str) -> DomainError:
    _LOG.warning("comparison_pair_tile_unavailable why=%s", why)
    return DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=DEPENDENCY)


def integrity(why: str, blob_id: str | None = None) -> DomainError:
    """Stored bytes that are not what they claim. ``why`` goes to the log, never to the caller."""
    _LOG.error("comparison_pair_tile_integrity why=%s blob=%s", why, blob_id)
    details = {"blob_id": blob_id} if blob_id else {}
    return DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, **details)


def storage_failure(failure: StorageError, blob_id: str) -> DomainError:
    """The error one storage failure maps to: the code it carries, with only the details that code declares safe."""
    code = from_internal(getattr(failure, "code", "") or "")
    allowed = code.safe_detail_keys
    details = {
        key: value
        for key, value in {**dict(failure.details), "blob_id": blob_id}.items()
        if key in allowed and isinstance(value, (str, int, float, bool))
    }
    return DomainError(code, **details)
