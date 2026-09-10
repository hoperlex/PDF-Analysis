"""``make check-storage`` -- prove BlobStore access to the private bucket.

``FOUNDATION_LOCK.json`` forwards the frozen target here::

    PYTHONPATH=src .venv/bin/python -m auditmanager.storage.check

and refuses the result unless ``FOUNDATION-CHECK OK check-storage`` is the last
actual output line. A zero exit without the sentinel, or any output after it, is
not accepted as evidence -- so this module prints the sentinel once, last, and
returns immediately afterwards.

What it proves
--------------
1. The frozen ``FF-01`` section 3 environment names are all present.
2. The **configured application credentials** reach the bucket. This is the
   claim the target is named for.
3. The same bucket refuses an **unsigned** request. Without this, step 2 proves
   only that a bucket exists, not that reaching it required credentials --
   which is what makes the bucket private.
4. A full ``temporary -> verify -> publish`` round trip: published bytes come
   back byte-identical and carry role, media type, size and SHA-256.
5. A **corrupt upload publishes nothing**: content declared with the wrong
   checksum is refused, and the ``blob_id`` those bytes would have taken is
   absent from the store afterwards.

What it does not do
-------------------
It makes no claim about PostgreSQL, the migration head or container health --
those belong to ``check-db`` and ``check-services``. It never creates the
bucket. It removes the two objects it created, one key at a time, and never
performs a bulk deletion.

Nothing printed here names a bucket, an object key or a credential.
"""

from __future__ import annotations

import secrets
import sys
from typing import Any

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from .errors import BlobNotFoundError, ChecksumMismatchError, StorageError
from .models import ROLE_FOUNDATION_CHECK, derive_blob_id
from .s3 import S3BlobStore, sha256_of
from .settings import S3StorageSettings

SENTINEL = "FOUNDATION-CHECK OK check-storage"

_MEDIA_TYPE = "application/octet-stream"


def _say(message: str) -> None:
    print(message, flush=True)


def _probe_anonymous_access_is_denied(settings: S3StorageSettings) -> None:
    """Fail unless an unsigned client is refused list *and* read.

    Raises :class:`AssertionError` if either succeeds. A bucket an anonymous
    client can list is not private, whatever the credentialed path proves.
    """
    anonymous: Any = boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        config=Config(
            signature_version=UNSIGNED,
            s3={"addressing_style": "path"},
            connect_timeout=settings.connect_timeout_seconds,
            read_timeout=settings.read_timeout_seconds,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )
    for description, call in (
        ("list", lambda: anonymous.list_objects_v2(Bucket=settings.bucket, MaxKeys=1)),
        (
            "read",
            lambda: anonymous.get_object(
                Bucket=settings.bucket, Key="probe-anonymous-access"
            ),
        ),
    ):
        try:
            call()
        except ClientError:
            # Any refusal is a refusal. The specific code is not asserted:
            # "denied" and "the object you may not see does not exist" are both
            # correct answers from a private bucket, and which one an
            # implementation returns is not this task's contract.
            continue
        except BotoCoreError as exc:  # unreachable endpoint, not a denial
            raise AssertionError(
                f"anonymous {description} could not be probed: {type(exc).__name__}"
            ) from None
        raise AssertionError(
            f"anonymous {description} succeeded: the bucket is not private"
        )


def run_check() -> None:
    """Run every proof. Raises on the first failure."""
    settings = S3StorageSettings.from_env()
    _say(f"storage endpoint      : {settings.endpoint_url} (region {settings.region})")

    store = S3BlobStore(settings)
    store.check_access()
    _say("application credentials: private bucket reachable")

    _probe_anonymous_access_is_denied(settings)
    _say("anonymous access       : denied for list and read")

    nonce = secrets.token_hex(8)
    payload = f"auditmanager check-storage {nonce}\n".encode("utf-8")
    digest = sha256_of(payload)

    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    _say(f"publication            : {published.blob_id} ({published.state.value})")

    inspected = store.inspect(published.blob_id)
    assert inspected == published, "inspection disagreed with publication"
    assert inspected.role == ROLE_FOUNDATION_CHECK, "recorded role is wrong"
    assert inspected.media_type == _MEDIA_TYPE, "recorded media type is wrong"
    assert inspected.size == len(payload), "recorded size is wrong"
    assert inspected.sha256 == digest, "recorded SHA-256 is wrong"
    _say("inspection             : role, media type, size and SHA-256 recorded")

    assert store.read(published.blob_id) == payload, "published bytes read back wrong"
    _say("read                   : bytes identical to what was published")

    corrupt = f"auditmanager corrupt {nonce}\n".encode("utf-8")
    would_be = derive_blob_id(sha256=sha256_of(b"different bytes"), size=len(corrupt))
    try:
        store.put_blob(
            corrupt,
            declared_sha256=sha256_of(b"different bytes"),
            declared_size=len(corrupt),
            role=ROLE_FOUNDATION_CHECK,
            media_type=_MEDIA_TYPE,
        )
    except ChecksumMismatchError:
        pass
    else:  # pragma: no cover - a passing store here is the failure
        raise AssertionError("a corrupt upload was published")
    try:
        store.inspect(would_be)
    except BlobNotFoundError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a corrupt upload left a canonical object")
    _say("corrupt upload         : refused, nothing canonical")

    store._purge_published(published.blob_id)
    _say("cleanup                : the object this check created was removed")


def _redacted(text: str) -> str:
    """Remove the bucket name from diagnostic text.

    The typed errors cannot carry it, but this branch also catches exceptions
    raised outside this package -- a raw ``botocore`` error escaping a call this
    module makes directly, say. Redacting here means the privacy rule holds for
    text this module did not compose, not only for text it did.
    """
    bucket = _configured_bucket()
    if bucket:
        text = text.replace(bucket, "<bucket>")
    return text


def _configured_bucket() -> str:
    import os

    from .settings import BUCKET_VAR

    return os.environ.get(BUCKET_VAR, "").strip()


def _fail(message: str) -> int:
    print(f"check-storage failed: {_redacted(message)}", file=sys.stderr, flush=True)
    return 1


def main(argv: list[str] | None = None) -> int:
    try:
        run_check()
    except (StorageError, AssertionError) as exc:
        return _fail(str(exc))
    except Exception as exc:  # noqa: BLE001 - the check must never crash opaquely
        return _fail(f"unexpected {type(exc).__name__}: {exc}")
    print(SENTINEL, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
