"""Publish the bytes of a page profile to the object store, with the blob journal the store requires.

`CMP-PROFILE-01`. Every blob a profile row names goes through the same sequence the other publishers
use (``runs/executor.py``, ``optimisation/uploads.py``): the content is **declared in the database
before the first external write** (``blob`` row ``temporary``), verified, advanced to ``verifying``
before it is made canonical, published, and only then marked ``available``. A process killed anywhere
in between leaves a ``blob`` row that names exactly the content that was in flight, which
reconciliation can enumerate by ``blob_id``; this module adds no second journal and no delete.

The identity is derived from ``(sha256, size)``, so the same preview of the same page published twice
is one object, and a re-run of a half-finished build re-publishes the same ids.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.storage.public import (
    BlobDeclaration,
    BlobMetadataRepository,
    DurablePublicationStore,
    VerifiedBlob,
    parse_blob_role,
)

__all__ = [
    "PNG_MEDIA_TYPE",
    "ROLE_PAGE_PREVIEW",
    "ROLE_PAGE_PROFILE",
    "ROLE_PAGE_THUMBNAIL",
    "ProfileBlobPublisher",
]

PNG_MEDIA_TYPE: Final[str] = "image/png"
ROLE_PAGE_PROFILE: Final[str] = "comparison_page_profile"
ROLE_PAGE_PREVIEW: Final[str] = "comparison_page_preview"
ROLE_PAGE_THUMBNAIL: Final[str] = "comparison_page_thumbnail"


class ProfileBlobPublisher:
    """Publishes one byte string at a time and returns its blob identity."""

    def __init__(self, session_factory: sessionmaker[Session], store: Any) -> None:
        self._factory = session_factory
        self._store = store
        self._blobs = BlobMetadataRepository()

    def publish(self, payload: bytes, *, role: str, media_type: str) -> str:
        def before_stage(declaration: BlobDeclaration) -> str:
            with session_scope(self._factory) as session:
                self._blobs.record_declared(session, declaration)
            return secrets.token_hex(16)

        def before_publish(verified: VerifiedBlob) -> None:
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)

        store = DurablePublicationStore(
            self._store, before_stage=before_stage, before_publish=before_publish
        )
        published = store.put_blob(
            payload,
            declared_sha256=hashlib.sha256(payload).hexdigest(),
            declared_size=len(payload),
            role=parse_blob_role(role),
            media_type=media_type,
        )
        with session_scope(self._factory) as session:
            self._blobs.mark_available(session, published.blob_id)
        return str(published.blob_id)
