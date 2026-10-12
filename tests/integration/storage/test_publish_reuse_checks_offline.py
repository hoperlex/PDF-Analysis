"""``S3BlobStore.publish``'s reuse checks, without a container (`R-76`, `W54-CUSTODY-01`).

The real-service cases live in ``test_repeated_publication.py`` and run in the owner's
window. These drive the same adapter code through a small in-memory stand-in for the four
S3 calls ``publish`` makes, so the decision table -- reuse on equal size, SHA-256 and media
type whatever the role; refuse a missing digest, a different digest or size, and a different
media type -- is proved on every run. The stand-in stores what the adapter writes and
answers what S3 answers (a 404 ``ClientError`` for an absent key); it has no opinion.
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import Any

import pytest
from botocore.exceptions import ClientError

from auditmanager.storage import (
    ROLE_SOURCE_DOCUMENT,
    BlobAttributeConflictError,
    BlobMetadataInvalidError,
    ChecksumMismatchError,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    parse_blob_role,
)
from auditmanager.storage._object_layout import canonical_key

BUCKET = "offline-bucket"


class MemoryS3:
    """The handful of S3 calls the adapter makes, over a dict. Keys never leave it."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _missing() -> ClientError:
        return ClientError(
            {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject"
        )

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        self.objects[Key] = {
            "body": bytes(Body), "type": ContentType, "meta": {}, "at": datetime.now(UTC),
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise self._missing()
        item = self.objects[Key]
        return {
            "ContentLength": len(item["body"]),
            "ContentType": item["type"],
            "Metadata": dict(item["meta"]),
            "LastModified": item["at"],
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise self._missing()
        item = self.objects[Key]
        return {"Body": io.BytesIO(item["body"]), "Metadata": dict(item["meta"])}

    def copy_object(
        self, *, Bucket: str, Key: str, CopySource: dict[str, str], MetadataDirective: str,
        ContentType: str, Metadata: dict[str, str],
    ) -> None:
        source = self.objects.get(CopySource["Key"])
        if source is None:
            raise self._missing()
        self.objects[Key] = {
            "body": source["body"], "type": ContentType, "meta": dict(Metadata),
            "at": datetime.now(UTC),
        }

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)


def _store() -> tuple[S3BlobStore, MemoryS3]:
    client = MemoryS3()
    settings = S3StorageSettings(
        endpoint_url="http://127.0.0.1:1",
        region="us-east-1",
        bucket=BUCKET,
        access_key_id="offline",
        secret_access_key="offline",
    )
    return S3BlobStore(settings, client=client), client


def _put(store: S3BlobStore, data: bytes, *, role: str, media_type: str = "application/pdf"):
    return store.put_blob(
        data,
        declared_sha256=hashlib.sha256(data).hexdigest(),
        declared_size=len(data),
        role=parse_blob_role(role),
        media_type=media_type,
    )


DATA = b"%PDF-1.7\nequal bytes, two consumers\n"


def test_equal_bytes_under_another_role_reuse_the_first_record() -> None:
    store, client = _store()
    first = _put(store, DATA, role=ROLE_SOURCE_DOCUMENT)
    second = _put(store, DATA, role="norm_source")
    assert second == first
    assert second.role == ROLE_SOURCE_DOCUMENT
    assert list(client.objects) == [canonical_key(first.blob_id)]


def test_a_different_media_type_is_still_a_conflict() -> None:
    store, client = _store()
    _put(store, DATA, role=ROLE_SOURCE_DOCUMENT)
    with pytest.raises(BlobAttributeConflictError):
        _put(store, DATA, role="norm_source", media_type="image/png")
    assert len(client.objects) == 1, "the refused attempt left a staged object"


@pytest.mark.parametrize(
    ("tamper", "raised"),
    (
        (lambda meta: meta.pop("content-sha256"), BlobMetadataInvalidError),
        (lambda meta: meta.__setitem__("content-sha256", "0" * 64), ChecksumMismatchError),
    ),
    ids=("no-recorded-digest", "other-recorded-digest"),
)
def test_an_object_this_adapter_cannot_vouch_for_is_refused_not_reused(tamper, raised) -> None:
    store, client = _store()
    first = _put(store, DATA, role=ROLE_SOURCE_DOCUMENT)
    tamper(client.objects[canonical_key(first.blob_id)]["meta"])
    with pytest.raises(raised):
        _put(store, DATA, role="norm_source")
    assert list(client.objects) == [canonical_key(first.blob_id)]


def test_an_object_of_another_length_is_refused_not_reused() -> None:
    store, client = _store()
    first = _put(store, DATA, role=ROLE_SOURCE_DOCUMENT)
    key = canonical_key(first.blob_id)
    client.objects[key]["body"] = DATA + b"tail"
    client.objects[key]["meta"]["content-size"] = str(len(DATA) + 4)
    with pytest.raises(SizeMismatchError):
        _put(store, DATA, role=ROLE_SOURCE_DOCUMENT)
    assert list(client.objects) == [key]
