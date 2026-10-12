"""The BlobStore port.

Narrow on purpose. It expresses one sequence -- ``temporary -> verify ->
publish`` -- plus inspection, a whole or a streamed read and an access probe.
It does not expose delete, erase, overwrite, presign, list or any way to name
an object: those are either later-gate decisions or adapter internals, and a
port that offered them would make the invariants below unenforceable.

The two invariants a conforming adapter must hold
-------------------------------------------------
1. **Nothing canonical without verification.** A checksum or size mismatch
   leaves no canonical object and no reachable ``blob_id``. The temporary bytes
   are removed by the same call that refuses them.
2. **No silent degradation.** Every failure is a typed
   :class:`~auditmanager.storage.errors.StorageError`. An unreachable store
   raises; it never falls back to a filesystem, a cache or a local directory.
   This package contains no filesystem canonical adapter and must never gain
   one -- ``FF-01`` section 4 lists "direct filesystem or JSON canonical
   storage" as not approved.

Extension point for P02
-----------------------
``B1`` adds the blob-metadata repository. It is an *addition*: it persists the
:class:`~auditmanager.storage.models.PublishedBlob` records this port already
returns and the ``machines.blob`` state each record already carries. Because
``blob_id`` is derived from ``(sha256, size)`` rather than allocated, the
repository does not become the identity authority and this port does not change
shape when it arrives.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import BinaryIO, Final, Protocol, runtime_checkable

from .models import BlobId, BlobRole, PublishedBlob, TemporaryBlob, VerifiedBlob

#: Anything the port accepts as content. Bytes for small artifacts, a binary
#: file object for anything large enough that holding it in memory is wrong.
BlobSource = bytes | bytearray | BinaryIO

#: The largest chunk :meth:`BlobStore.open_stream` yields unless told otherwise.
#: `W55A-CONTENT-01` (plan section A3.5): equal to the API's ``CONTENT_CHUNK_BYTES``,
#: which the content adapters pass explicitly; this package does not import the API.
STREAM_CHUNK_BYTES: Final[int] = 256 * 1024

#: What :meth:`BlobStore.open_stream` returns: an opened read, consumed chunk by
#: chunk. ``close()`` releases the connection when a consumer stops early.
BlobChunks = Generator[bytes, None, None]


@runtime_checkable
class BlobStore(Protocol):
    """Publish and read checksum-verified bytes, addressed only by ``blob_id``."""

    def check_access(self) -> None:
        """Prove the configured credentials can reach the private bucket.

        Returns ``None`` on success and raises otherwise:
        :class:`StorageCredentialRefusedError` when the credentials are refused,
        :class:`StorageBucketMissingError` when the configured bucket does not
        exist, :class:`StorageUnavailableError` when the endpoint cannot be
        reached at all.
        """

    def stage_temporary(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
        upload_token: str | None = None,
    ) -> TemporaryBlob:
        """Upload bytes to a temporary location. Verifies nothing yet.

        ``upload_token`` is an optional opaque pre-reserved handle. Durable analysis
        publication persists one before this call; ordinary ingest lets the adapter
        allocate it. It is never a business identity or object key.
        """

    def temporary_exists(self, temporary: TemporaryBlob) -> bool:
        """Point-inspect one exact temporary handle without listing the store."""

    def verify_temporary(self, temporary: TemporaryBlob) -> VerifiedBlob:
        """Read the staged bytes back and prove they match what was declared.

        Raises :class:`SizeMismatchError` or :class:`ChecksumMismatchError` --
        and removes the temporary bytes -- when they do not.
        """

    def publish(self, verified: VerifiedBlob) -> PublishedBlob:
        """Move verified bytes to their canonical location.

        Idempotent by ``(sha256, size)``: publishing content that is already
        available returns the existing record and does not rewrite the object.
        """

    def discard_temporary(self, temporary: TemporaryBlob) -> None:
        """Remove a staged upload that will not be published. Idempotent."""

    def put_blob(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
    ) -> PublishedBlob:
        """Run the whole ``temporary -> verify -> publish`` sequence.

        The business-facing entry point. Any failure at any step leaves nothing
        canonical and no temporary residue.
        """

    def inspect(self, blob_id: BlobId) -> PublishedBlob:
        """Return the recorded facts about published bytes without reading them."""

    def read(self, blob_id: BlobId, *, verify: bool = True) -> bytes:
        """Return published bytes, re-verifying their SHA-256 by default."""

    def open_stream(
        self,
        blob_id: BlobId,
        *,
        expected_sha256: str,
        expected_size: int,
        window: tuple[int, int] | None = None,
        chunk_size: int = STREAM_CHUNK_BYTES,
    ) -> BlobChunks:
        """Open published bytes for a chunked read; never hold the object whole.

        `W55A-CONTENT-01`, owner ruling ``R-115``. ``expected_sha256`` and
        ``expected_size`` are the caller's own declaration -- a manifest entry, a
        custody binding -- never the object's metadata, which only proves the
        object agrees with itself.

        **Everything that can refuse refuses before this returns**, so a caller
        that has not yet sent a status line can still answer with a typed
        failure: an absent object (:class:`BlobNotFoundError`), an unreachable or
        refusing store, a recorded digest that is absent
        (:class:`BlobMetadataInvalidError`) or differs from ``expected_sha256``,
        and a stored size that differs from ``expected_size`` (both
        :class:`BlobIntegrityError`).

        ``window`` is an inclusive ``(first, last)`` already resolved against
        ``expected_size``; only those bytes are requested from the store. A
        windowed read relies on the recorded verification (publication and
        reconciliation): it cannot hash an object it does not read.

        A whole read (``window is None``) hashes while it streams and **holds
        back its last chunk** until the digest equals ``expected_sha256``. On a
        mismatch it logs ``storage_integrity_error`` and raises
        :class:`ChecksumMismatchError` instead of yielding that chunk, so a
        consumer that has already declared the length delivers fewer bytes than
        it declared. A stream that ends short or runs long raises
        :class:`SizeMismatchError` the same way, on both kinds of read.
        """


__all__ = ["STREAM_CHUNK_BYTES", "BlobChunks", "BlobSource", "BlobStore"]
