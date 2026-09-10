"""The BlobStore port.

Narrow on purpose. It expresses one sequence -- ``temporary -> verify ->
publish`` -- plus inspection, read and an access probe. It does not expose
delete, erase, overwrite, presign, list or any way to name an object: those are
either later-gate decisions or adapter internals, and a port that offered them
would make the invariants below unenforceable.

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

from typing import BinaryIO, Protocol, runtime_checkable

from .models import BlobId, BlobRole, PublishedBlob, TemporaryBlob, VerifiedBlob

#: Anything the port accepts as content. Bytes for small artifacts, a binary
#: file object for anything large enough that holding it in memory is wrong.
BlobSource = bytes | bytearray | BinaryIO


@runtime_checkable
class BlobStore(Protocol):
    """Publish and read checksum-verified bytes, addressed only by ``blob_id``."""

    def check_access(self) -> None:
        """Prove the configured credentials can reach the private bucket.

        Returns ``None`` on success and raises otherwise:
        :class:`StoragePermissionDeniedError` when the credentials are refused,
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
    ) -> TemporaryBlob:
        """Upload bytes to a temporary location. Verifies nothing yet."""

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


__all__ = ["BlobSource", "BlobStore"]
