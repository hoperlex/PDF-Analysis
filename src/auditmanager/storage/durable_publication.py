"""BlobStore decorator that journals analysis intent before any external write."""

from __future__ import annotations

from collections.abc import Callable

from .models import (
    BlobDeclaration,
    BlobId,
    BlobRole,
    PublishedBlob,
    TemporaryBlob,
    VerifiedBlob,
    declare_blob,
)
from .port import BlobSource, BlobStore

BeforeStage = Callable[[BlobDeclaration], str]
BeforePublish = Callable[[VerifiedBlob], None]
AfterPublish = Callable[[PublishedBlob], None]


class DurablePublicationStore:
    """Delegate reads, but expand ``put_blob`` around two durable callbacks.

    ``before_stage`` commits ``blob.temporary`` plus the Attempt publication intent
    before temporary upload. ``before_publish`` advances the same identity to
    ``verifying`` after checksum verification and before canonical publication. A kill
    at either external-effect seam is therefore enumerable by ``blob_id``.
    """

    __slots__ = ("_store", "_before_stage", "_before_publish", "_after_publish")

    def __init__(
        self,
        store: BlobStore,
        *,
        before_stage: BeforeStage,
        before_publish: BeforePublish,
        after_publish: AfterPublish | None = None,
    ) -> None:
        self._store = store
        self._before_stage = before_stage
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
        upload_token: str | None = None,
    ) -> TemporaryBlob:
        return self._store.stage_temporary(
            source,
            declared_sha256=declared_sha256,
            declared_size=declared_size,
            role=role,
            media_type=media_type,
            upload_token=upload_token,
        )

    def temporary_exists(self, temporary: TemporaryBlob) -> bool:
        return self._store.temporary_exists(temporary)

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
        declaration = declare_blob(
            sha256=declared_sha256,
            size=declared_size,
            role=role,
            media_type=media_type,
        )
        # This transaction commits the Attempt attribution and declared content
        # identity before stage_temporary performs the first external S3 write.
        upload_token = self._before_stage(declaration)
        temporary = self.stage_temporary(
            source,
            declared_sha256=declaration.sha256,
            declared_size=declaration.size,
            role=declaration.role,
            media_type=declaration.media_type,
            upload_token=upload_token,
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


__all__ = ["AfterPublish", "BeforePublish", "BeforeStage", "DurablePublicationStore"]
