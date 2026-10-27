"""The BlobStore port.

Narrow on purpose. It expresses one sequence -- ``temporary -> verify ->
publish`` -- plus inspection, a whole or a streamed read and an access probe.
It does not expose delete, erase, overwrite, presign, list or any way to name
an object: those are either later-gate decisions or adapter internals, and a
port that offered them would make the invariants below unenforceable.

Chunked uploads are a second port, :class:`MultipartStaging` (`CMP-STORAGE-PARTS-01`), so this
one keeps its shape: its ``abort_multipart`` removes only what a token itself staged and never a
published blob, which is why it does not reopen the "no delete" rule above.

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

from collections.abc import Callable, Generator, Sequence
from typing import BinaryIO, Final, Protocol, runtime_checkable

from .models import BlobId, BlobRole, PublishedBlob, TemporaryBlob, VerifiedBlob
from .multipart import UploadedPart

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


@runtime_checkable
class MultipartStaging(Protocol):
    """Stage one object as a multipart upload that a database row owns, then publish it.

    `CMP-STORAGE-PARTS-01`, ADR-0025 decision 10. A **second** port beside :class:`BlobStore`, not a
    widening of it: the ``BlobStore`` member set is pinned by a test and implemented by test doubles
    that have no business with parts, and the two sequences are different (``temporary -> verify ->
    publish`` for bytes in hand; ``begin -> part ... -> complete`` for bytes that arrive in chunks).
    The S3 adapter satisfies both.

    The two invariants of :class:`BlobStore` hold here unchanged. **Nothing canonical without
    verification**: :meth:`complete_multipart` assembles the parts under a temporary key and then
    runs the existing ``verify_temporary`` and ``publish`` on it, so a digest or size mismatch leaves
    no object. **No silent degradation**: every failure is a typed
    :class:`~auditmanager.storage.errors.StorageError`.

    The token is minted by :func:`~auditmanager.storage.multipart.new_multipart_token` and **persisted
    by the caller before** :meth:`begin_multipart` is called (the first part's row is refused by the
    database until it is). The port persists nothing and enumerates nothing.
    """

    def begin_multipart(self, upload_token: str) -> None:
        """Open the upload this token names. Idempotent: an upload already open is kept.

        Raises :class:`~auditmanager.storage.errors.BlobMetadataInvalidError` for a string that is
        not a minted token. Call it only for a file the database still accepts parts for: a token
        whose upload was aborted would be opened again.
        """

    def upload_part(
        self, upload_token: str, part_number: int, source: BlobSource
    ) -> UploadedPart:
        """Send one part (1 byte to 16 MiB, number 1 to 10 000) and return its receipt.

        The size and SHA-256 in the receipt are computed here from the bytes sent. Sending the same
        number again replaces the part; identical bytes give the identical receipt. Raises
        :class:`~auditmanager.storage.errors.MultipartPartError` for a number or size outside the
        bounds, and :class:`~auditmanager.storage.errors.TemporaryBlobLostError` when no upload is open
        for the token (never begun, completed, or aborted).
        """

    def complete_multipart(
        self,
        upload_token: str,
        parts: Sequence[UploadedPart],
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
        before_publish: Callable[[VerifiedBlob], None] | None = None,
    ) -> PublishedBlob:
        """Assemble the recorded parts, verify the whole object and publish it.

        ``parts`` are the receipts the caller recorded, ascending from 1 with no gap. Refused before
        anything is assembled: a list that is not whole and ordered, or not what the store holds
        (:class:`~auditmanager.storage.errors.MultipartPartsError`), and sizes that do not add up to
        ``declared_size`` (:class:`~auditmanager.storage.errors.SizeMismatchError`). After assembly the
        object is read back: a SHA-256 or size that differs from the declaration raises
        :class:`~auditmanager.storage.errors.ChecksumMismatchError` or
        :class:`~auditmanager.storage.errors.SizeMismatchError` **and removes the assembled object**.

        ``before_publish`` is the seam :class:`~auditmanager.storage.durable_publication.DurablePublicationStore`
        has: called with the :class:`VerifiedBlob` after the verification and before the canonical copy,
        so the caller can commit ``verifying`` for that ``blob_id`` first. If it raises, nothing is
        published and the assembled object is kept, so a retry resumes at the verification.

        Retryable after a crash between assembly and verification: with no open upload and the
        assembled object present, it resumes at the verification. With neither,
        :class:`~auditmanager.storage.errors.TemporaryBlobLostError`.
        """

    def abort_multipart(self, upload_token: str) -> bool:
        """Remove everything the token holds in the store; idempotent.

        Aborts the open upload and deletes an assembled-but-unverified object. **Never touches a
        published blob.** Returns ``True`` when something was removed, ``False`` when the store held
        nothing for the token.
        """


__all__ = [
    "STREAM_CHUNK_BYTES",
    "BlobChunks",
    "BlobSource",
    "BlobStore",
    "MultipartStaging",
]
