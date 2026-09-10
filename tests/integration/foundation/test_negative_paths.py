"""The refusals ``FF-01`` section 7 makes blocking.

Items 4 and 6 of the blocking acceptance list are refusals, not capabilities:
anonymous list, read and write must be *denied*, and a wrong checksum must
leave *nothing* canonical. A foundation that can only demonstrate its happy
path has demonstrated the half that does not matter when something goes wrong.

The third group here is the one that turns "it failed" into "it failed
explicitly": a missing or misconfigured ``DATABASE_URL`` or ``S3_*`` must raise
a typed error naming the variable. The failure mode this rules out is not a
crash -- it is a *silent substitution*, a client that quietly becomes anonymous
or a store that quietly becomes a local directory, which would leave the whole
suite above passing against nothing.

Refusals are verified out of band wherever a refusal could be faked by the
object that performed it: the absence of a canonical object is asserted with an
independently built client, not with the adapter that just declined to write it.
"""

from __future__ import annotations

import secrets
from dataclasses import replace
from typing import Any
from urllib.parse import urlparse

import psycopg
import pytest
from botocore.exceptions import ClientError
from sqlalchemy.engine import make_url

from auditmanager.shared.db.config import (
    DATABASE_URL_VAR,
    DatabaseSettings,
    load_settings,
)
from auditmanager.shared.db.engine import create_database_engine, verify_connectivity
from auditmanager.shared.db.errors import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
)
from auditmanager.storage import (
    ROLE_FOUNDATION_CHECK,
    BlobId,
    BlobNotFoundError,
    ChecksumMismatchError,
    S3BlobStore,
    S3StorageSettings,
    SizeMismatchError,
    StorageConfigurationError,
    StorageError,
    StorageUnavailableError,
    derive_blob_id,
    sha256_of,
)
from auditmanager.storage._object_layout import canonical_key, temporary_key
from auditmanager.storage.settings import REQUIRED_VARS

_MEDIA_TYPE = "application/octet-stream"


def _unique_payload(label: str) -> bytes:
    return f"P1-QA-00 {label} {secrets.token_hex(16)}\n".encode("utf-8")


def _object_is_absent(client: Any, bucket: str, key: str) -> bool:
    """True when an independently built client cannot see the object."""
    try:
        client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        return exc.response["ResponseMetadata"]["HTTPStatusCode"] in (403, 404)
    return False


# --------------------------------------------------------------------------
# FF-01 section 7 item 6: a wrong checksum publishes nothing
# --------------------------------------------------------------------------


def test_a_wrong_checksum_leaves_nothing_canonical_and_no_temporary_residue(
    store: S3BlobStore,
    independent_s3: Any,
    independent_db: psycopg.Connection,
    storage_settings: S3StorageSettings,
) -> None:
    """The refusal is verified from outside the adapter, at both prefixes.

    ``stage_temporary`` is called directly rather than through ``put_blob`` so
    the upload token is in hand: without it, "the temporary bytes were removed"
    could only be taken on trust. Both the canonical key and the temporary key
    are then checked with a client this suite built, so the adapter is not the
    witness to its own cleanup.
    """
    payload = _unique_payload("wrong-checksum")
    wrong_digest = sha256_of(b"bytes that were never uploaded")
    would_be = derive_blob_id(sha256=wrong_digest, size=len(payload))

    temporary = store.stage_temporary(
        payload,
        declared_sha256=wrong_digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    staged_key = temporary_key(temporary.upload_token)
    # The staged bytes are really there before verification refuses them --
    # otherwise the cleanup assertion below would pass against an upload that
    # never happened.
    independent_s3.head_object(Bucket=storage_settings.bucket, Key=staged_key)

    with pytest.raises(ChecksumMismatchError):
        store.verify_temporary(temporary)

    assert _object_is_absent(independent_s3, storage_settings.bucket, staged_key), (
        "the refused upload's temporary bytes are still in the bucket: a rejected "
        "publication left residue that a later sweep would have to guess about"
    )
    assert _object_is_absent(
        independent_s3, storage_settings.bucket, canonical_key(would_be)
    ), "a wrong checksum produced a canonical object"

    with pytest.raises(BlobNotFoundError):
        store.inspect(would_be)

    with independent_db.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM blob WHERE blob_id = %s", (str(would_be),))
        (count,) = cursor.fetchone()
    independent_db.rollback()
    assert count == 0, "a refused upload was recorded in the database"


def test_the_whole_sequence_refuses_a_wrong_checksum_in_one_call(
    store: S3BlobStore, independent_s3: Any, storage_settings: S3StorageSettings
) -> None:
    """``put_blob`` -- the business-facing entry point -- refuses it too.

    The staged-and-verified path above proves the mechanism. This proves the
    call an application actually makes has the same outcome, which is what
    ``FF-01`` section 7 item 6 is about.
    """
    payload = _unique_payload("wrong-checksum-put")
    wrong_digest = sha256_of(b"a different buffer entirely")
    would_be = derive_blob_id(sha256=wrong_digest, size=len(payload))

    with pytest.raises(ChecksumMismatchError):
        store.put_blob(
            payload,
            declared_sha256=wrong_digest,
            declared_size=len(payload),
            role=ROLE_FOUNDATION_CHECK,
            media_type=_MEDIA_TYPE,
        )

    assert _object_is_absent(
        independent_s3, storage_settings.bucket, canonical_key(would_be)
    ), "put_blob published content whose checksum did not match"


def test_a_wrong_size_leaves_nothing_canonical(
    store: S3BlobStore, independent_s3: Any, storage_settings: S3StorageSettings
) -> None:
    """A size mismatch is refused before the checksum is even computed."""
    payload = _unique_payload("wrong-size")
    digest = sha256_of(payload)
    declared = len(payload) + 1
    would_be = derive_blob_id(sha256=digest, size=declared)

    with pytest.raises(SizeMismatchError):
        store.put_blob(
            payload,
            declared_sha256=digest,
            declared_size=declared,
            role=ROLE_FOUNDATION_CHECK,
            media_type=_MEDIA_TYPE,
        )

    assert _object_is_absent(
        independent_s3, storage_settings.bucket, canonical_key(would_be)
    ), "a size mismatch produced a canonical object"


# --------------------------------------------------------------------------
# FF-01 section 7 item 4: anonymous list, read and write are denied
# --------------------------------------------------------------------------


def test_anonymous_list_is_denied(
    anonymous_s3: Any, storage_settings: S3StorageSettings
) -> None:
    """An unsigned client may not enumerate the bucket.

    A bucket an anonymous caller can list is not private, whatever the
    credentialed path proves about it.
    """
    with pytest.raises(ClientError) as refused:
        anonymous_s3.list_objects_v2(Bucket=storage_settings.bucket, MaxKeys=1)
    status = refused.value.response["ResponseMetadata"]["HTTPStatusCode"]
    assert status in (403, 404), f"anonymous list was answered with HTTP {status}"


def test_anonymous_read_of_an_existing_object_is_denied(
    store: S3BlobStore,
    anonymous_s3: Any,
    storage_settings: S3StorageSettings,
    published_blobs: list[BlobId],
) -> None:
    """The denial is proved against a key that really exists.

    Refusing to read an absent object proves nothing -- "not found" and "not
    allowed" look alike. This publishes real bytes first, so the anonymous
    client is being denied something that is genuinely there.
    """
    payload = _unique_payload("anonymous-read")
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    key = canonical_key(published.blob_id)

    # The credentialed adapter can read it; that is what makes the next
    # assertion a statement about privacy rather than about absence.
    assert store.read(published.blob_id) == payload

    with pytest.raises(ClientError) as refused:
        body = anonymous_s3.get_object(Bucket=storage_settings.bucket, Key=key)["Body"]
        body.read()
        body.close()
    status = refused.value.response["ResponseMetadata"]["HTTPStatusCode"]
    assert status in (403, 404), f"anonymous read was answered with HTTP {status}"


def test_anonymous_write_is_denied_and_creates_nothing(
    anonymous_s3: Any, independent_s3: Any, storage_settings: S3StorageSettings
) -> None:
    """An unsigned PUT is refused *and* leaves no object behind.

    The second half matters as much as the first: a store that answered with an
    error after writing the object would still be a store an anonymous caller
    can write to.
    """
    key = f"temporary/p1-qa-00-anonymous-write-{secrets.token_hex(8)}"
    with pytest.raises(ClientError) as refused:
        anonymous_s3.put_object(
            Bucket=storage_settings.bucket, Key=key, Body=b"anonymous"
        )
    status = refused.value.response["ResponseMetadata"]["HTTPStatusCode"]
    assert status in (403, 404), f"anonymous write was answered with HTTP {status}"

    assert _object_is_absent(independent_s3, storage_settings.bucket, key), (
        "the refused anonymous write created an object anyway"
    )


def test_anonymous_access_is_denied_over_plain_http_too(
    store: S3BlobStore,
    storage_settings: S3StorageSettings,
    published_blobs: list[BlobId],
    http_get: Any,
) -> None:
    """The denial does not depend on using an SDK.

    boto3 could in principle be configured into signing something; a bare HTTP
    GET cannot be. This is the same claim made with no client library between
    the request and the server.
    """
    payload = _unique_payload("anonymous-http")
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)

    base = storage_settings.endpoint_url.rstrip("/")
    listing_status, _ = http_get(f"{base}/{storage_settings.bucket}/")
    assert listing_status in (403, 404), (
        f"an unauthenticated HTTP bucket listing returned {listing_status}"
    )
    object_status, _ = http_get(
        f"{base}/{storage_settings.bucket}/{canonical_key(published.blob_id)}"
    )
    assert object_status in (403, 404), (
        f"an unauthenticated HTTP object read returned {object_status}; the bytes "
        "are reachable without credentials"
    )


# --------------------------------------------------------------------------
# Missing or misconfigured configuration fails explicitly, never degrades
# --------------------------------------------------------------------------


def test_every_missing_s3_variable_is_named_explicitly() -> None:
    """Each of the five ``S3_*`` names, removed one at a time, is refused by name.

    Asserted per variable rather than in bulk: a loader that happened to check
    only the first would pass a single "everything missing" case while silently
    defaulting the rest.
    """
    complete = {name: "placeholder-value" for name in REQUIRED_VARS}
    with pytest.raises(StorageConfigurationError):
        S3StorageSettings.from_env({})

    for missing in REQUIRED_VARS:
        partial = dict(complete)
        del partial[missing]
        with pytest.raises(StorageConfigurationError) as refused:
            S3StorageSettings.from_env(partial)
        assert missing in str(refused.value), (
            f"the error for a missing {missing} does not name it: {refused.value}"
        )

        blank = dict(complete)
        blank[missing] = "   "
        with pytest.raises(StorageConfigurationError):
            S3StorageSettings.from_env(blank)


def test_a_missing_database_url_is_refused_rather_than_defaulted() -> None:
    """No default connection is assumed when ``DATABASE_URL`` is absent or empty."""
    with pytest.raises(DatabaseConfigurationError) as refused:
        load_settings({})
    assert DATABASE_URL_VAR in str(refused.value)

    for bad in ("", "   ", "not-a-url", "postgresql+psycopg://user@host:5432/"):
        with pytest.raises(DatabaseConfigurationError):
            load_settings({DATABASE_URL_VAR: bad})


def test_a_misconfigured_database_url_does_not_leak_its_password() -> None:
    """The refusal names the fault, not the value that carried the credential."""
    secret = "s3cret-p1-qa-00-password"
    with pytest.raises(DatabaseConfigurationError) as refused:
        load_settings({DATABASE_URL_VAR: f"postgresql+psycopg://u:{secret}@h:notaport/d"})
    assert secret not in str(refused.value), (
        "the configuration error echoed the password out of DATABASE_URL"
    )


def test_an_unreachable_database_raises_instead_of_degrading(
    database_url: Any, closed_port: int
) -> None:
    """A database that is not there is a typed failure, not a silent fallback.

    This is the shape of the degradation the freeze rules out: an unreachable
    PostgreSQL must never become an on-disk SQLite file or an in-memory
    substitute. The engine is built successfully -- construction is lazy -- and
    the failure arrives on first use, typed.
    """
    unreachable = make_url(
        database_url.render_as_string(hide_password=False)
    ).set(port=closed_port)
    engine = create_database_engine(DatabaseSettings(url=unreachable))
    try:
        with pytest.raises(DatabaseUnavailableError):
            verify_connectivity(engine)
    finally:
        engine.dispose()


def test_an_unreachable_object_store_raises_instead_of_degrading(
    storage_settings: S3StorageSettings, closed_port: int
) -> None:
    """An unreachable endpoint raises a typed ``StorageError``.

    ``FF-01`` section 4 does not approve filesystem canonical storage, and the
    port's contract says an unreachable store "raises; it never falls back to a
    filesystem, a cache or a local directory". Both the access probe and a
    publication attempt are checked, because a fallback would most plausibly
    appear on the write path.
    """
    endpoint = urlparse(storage_settings.endpoint_url)
    dead = replace(
        storage_settings,
        endpoint_url=f"{endpoint.scheme}://{endpoint.hostname}:{closed_port}",
    )
    store = S3BlobStore(dead)

    with pytest.raises(StorageUnavailableError):
        store.check_access()

    payload = _unique_payload("unreachable")
    with pytest.raises(StorageError):
        store.put_blob(
            payload,
            declared_sha256=sha256_of(payload),
            declared_size=len(payload),
            role=ROLE_FOUNDATION_CHECK,
            media_type=_MEDIA_TYPE,
        )


def test_refused_credentials_are_a_typed_failure_not_an_anonymous_client(
    storage_settings: S3StorageSettings,
) -> None:
    """Wrong credentials are refused; the adapter does not retry unsigned.

    A client that fell back to an unsigned request when its credentials were
    rejected would make every privacy assertion in this file meaningless, so
    the absence of that fallback is asserted directly.
    """
    wrong = replace(
        storage_settings,
        access_key_id="p1-qa-00-not-a-real-key",
        secret_access_key="p1-qa-00-not-a-real-secret",
    )
    store = S3BlobStore(wrong)
    with pytest.raises(StorageError) as refused:
        store.check_access()
    assert not isinstance(refused.value, StorageUnavailableError), (
        "a refused credential was reported as an unreachable endpoint, which hides "
        "an authorization fault behind a transport one"
    )
