"""The source PDF in a temporary file, for the length of a ``with`` block.

`W55B-GEOMETRY-01` (plan section B3.3): ``page_geometry_extraction`` opens the PDF from a
file, never from bytes in memory, exactly as ``source_preparation`` has since
`W55B-RECOGNISED-01`. That stage's helper is private to it and names ``source_preparation`` in
its refusal, so this is the same pattern written once more with the caller's ``stage_id``
rather than a private import across two stage modules.

The blob is streamed with its digest checked as it streams (:meth:`BlobStore.open_stream`, a
whole read: the last chunk is withheld unless the SHA-256 is the one the store recorded --
the comparison ``read(verify=True)`` made). The file is created with ``mkstemp`` in the
process's temporary directory and removed on the way out, whether the block succeeded or
raised.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobId, BlobStore

#: The temporary file's name prefix (``am-geometry-<random>.pdf``).
TEMPORARY_PREFIX: Final[str] = "am-geometry-"


@contextmanager
def source_file(store: BlobStore, blob_id: BlobId, *, stage_id: str) -> Iterator[str]:
    """The path of a temporary file holding the blob's exact bytes; removed afterwards."""
    descriptor, name = tempfile.mkstemp(prefix=TEMPORARY_PREFIX, suffix=".pdf")
    try:
        try:
            recorded = store.inspect(blob_id)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                for chunk in store.open_stream(
                    blob_id,
                    expected_sha256=recorded.sha256,
                    expected_size=recorded.size,
                ):
                    handle.write(chunk)
        except DomainError:
            raise
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed refusal
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="the source document referenced by the page inventory is unreadable",
                stage_id=stage_id,
                reason="source_unreadable",
            ) from exc
        yield name
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        Path(name).unlink(missing_ok=True)


__all__ = ["TEMPORARY_PREFIX", "source_file"]
