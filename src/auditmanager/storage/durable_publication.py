"""BlobStore decorator that journals verified analysis bytes before publication."""

from __future__ import annotations

from collections.abc import Callable

from .models import BlobId, BlobRole, PublishedBlob, TemporaryBlob, VerifiedBlob
from .port import BlobSource, BlobStore

BeforePublish = Callable[[VerifiedBlob], None]
AfterPublish = Callable[[PublishedBlob], None]


class DurablePublicationStore:
    """Delegate reads, but expand ``put_blob`` around a durable pre-publish callback.

    The callback commits both ``blob.verifying`` and the attempt-scoped publication
    intent. If canonical publication then succeeds but the caller's later binding
    transaction rolls back, reconciliation can still find the object by ``blob_id``.
    """

    __slots__ = ("_store", "_before_publish", "_after_publish")

    def __init__(
        self,
        store: BlobStore,
        *,
        before_publish: BeforePublish,
        after_publish: AfterPublish | None = None,
    ) -> None:
        self._store = store
        self._before_publish = before_publish
        self._after_publish = after_publish

    def check_access(self) -> None:
        self._store.check_access()

    def stage_temporary(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
    ) -> TemporaryBlob:
        return self._store.stage_temporary(
            source,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
        )

    def verify_temporary(self, temporary: TemporaryBlob) -> VerifiedBlob:
        return self._store.verify_temporary(temporary)

    def publish(self, verified: VerifiedBlob) -> PublishedBlob:
        return self._store.publish(verified)

    def discard_temporary(self, temporary: TemporaryBlob) -> None:
        self._store.discard_temporary(temporary)

    def put_blob(
        self,
        source: BlobSource,
        *,
        declared_sha256: str,
        declared_size: int,
        role: BlobRole,
        media_type: str,
    ) -> PublishedBlob:
        temporary = self.stage_temporary(
            source,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
        )
        try:
            verified = self.verify_temporary(temporary)
            self._before_publish(verified)
            published = self.publish(verified)
            if self._after_publish is not None:
                self._after_publish(published)
            return published
        except Exception:
            # A database refusal is not a StorageError, but it is equally important not
            # to leave the temporary object behind. Canonical bytes, if publication had
            # already completed, remain content-addressed and are intentionally not
            # deleted; their committed intent is the reconciliation breadcrumb.
            self.discard_temporary(temporary)
            raise

    def inspect(self, blob_id: BlobId) -> PublishedBlob:
        return self._store.inspect(blob_id)

    def read(self, blob_id: BlobId, *, verify: bool = True) -> bytes:
        return self._store.read(blob_id, verify=verify)


__all__ = ["AfterPublish", "BeforePublish", "DurablePublicationStore"]
