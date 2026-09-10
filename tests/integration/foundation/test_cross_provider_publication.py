"""The positive path no single lane could prove: both providers, one run.

The storage lane proved publication against its own MinIO. The database lane
proved sessions and the migration head against its own PostgreSQL. Neither ran
both at once, so neither could show that the identity the S3 adapter derives is
the identity the database records, that the four recorded facts survive the
crossing intact, and that no bucket or object key crosses with them.

Every assertion here is made twice over: once through the boundary under test,
and once through an **independent** reader -- a raw ``psycopg`` connection and a
separately constructed ``boto3`` client. A record that only the writing object
can see is not evidence that anything reached a server.
"""

from __future__ import annotations

import secrets
from typing import Any

import psycopg
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.migrations import read_state
from auditmanager.shared.db.session import session_scope
from auditmanager.storage import (
    BLOB_ID_PATTERN,
    ROLE_FOUNDATION_CHECK,
    BlobId,
    PublishedBlob,
    S3BlobStore,
    S3StorageSettings,
    derive_blob_id,
    sha256_of,
)

# The adapter-private key layout. Business code never imports this and the
# public surface has no accessor for a key -- which is exactly why an
# out-of-band check needs it: verifying that bytes are really in the bucket
# means naming the object, and the adapter is the only thing that can.
from auditmanager.storage._object_layout import canonical_key

_MEDIA_TYPE = "application/octet-stream"


def _unique_payload(label: str) -> bytes:
    """Content no other test or run shares.

    Canonical keys are content-addressed, so two tests publishing identical
    bytes would publish the *same* object and the first teardown would delete
    the second test's evidence. A nonce keeps every test's cleanup its own.
    """
    return f"P1-QA-00 {label} {secrets.token_hex(16)}\n".encode("utf-8")


def test_a_blob_published_to_s3_is_reachable_through_the_db_session_boundary(
    store: S3BlobStore,
    session_factory: sessionmaker[Session],
    independent_db: psycopg.Connection,
    independent_s3: Any,
    storage_settings: S3StorageSettings,
    published_blobs: list[BlobId],
    recorded_blob_rows: list[str],
    record_available_blob: Any,
) -> None:
    """One blob, published through S3 and recorded through PostgreSQL, in one run.

    This is the cross-provider claim in full: the same ``blob_id`` addresses
    real bytes in the real bucket and a real row in the real migrated schema,
    and the role, media type, size and SHA-256 agree on both sides.
    """
    payload = _unique_payload("cross-provider")
    digest = sha256_of(payload)

    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)

    # --- the storage side, verified out of band -----------------------------
    assert BLOB_ID_PATTERN.match(published.blob_id), (
        f"{published.blob_id!r} is not the frozen wire pattern"
    )
    assert published.blob_id == derive_blob_id(sha256=digest, size=len(payload)), (
        "the published identity is not the one (sha256, size) derives, so it is "
        "allocated somewhere rather than derived and idempotency cannot hold"
    )
    head = independent_s3.head_object(
        Bucket=storage_settings.bucket, Key=canonical_key(published.blob_id)
    )
    assert int(head["ContentLength"]) == len(payload), (
        "a client this suite built itself does not see the published bytes at the "
        "canonical key: the adapter did not write to the configured S3 service"
    )
    assert store.read(published.blob_id) == payload

    # --- the database side, written through session_scope --------------------
    record_available_blob(published)

    # --- the database side, verified out of band -----------------------------
    with independent_db.cursor() as cursor:
        cursor.execute(
            "SELECT state, sha256, size_bytes, media_type FROM blob WHERE blob_id = %s",
            (str(published.blob_id),),
        )
        row = cursor.fetchone()
    independent_db.rollback()

    assert row is not None, (
        "the row written through session_scope is not visible to an independent "
        "connection: the unit of work did not commit to the real server"
    )
    state, sha256, size_bytes, media_type = row
    assert state == "available"
    assert sha256 == published.sha256 == digest
    assert size_bytes == published.size == len(payload)
    assert media_type == published.media_type == _MEDIA_TYPE

    # --- and the storage side still agrees, after the database write ---------
    inspected = store.inspect(published.blob_id)
    assert inspected == published, "inspection disagreed with publication"
    assert store.read(published.blob_id) == payload


def test_the_crossing_carries_no_bucket_and_no_object_key(
    store: S3BlobStore,
    independent_db: psycopg.Connection,
    storage_settings: S3StorageSettings,
    published_blobs: list[BlobId],
    record_available_blob: Any,
) -> None:
    """``FF-01`` section 7 item 9: public values carry ``blob_id``, not location.

    Asserted at the crossing rather than inside either provider, because the
    crossing is where a location would leak if the two sides had to agree on
    one. They do not: the ``blob`` table has no bucket and no key column, and
    the derived identity means the database never has to resolve a location.
    """
    payload = _unique_payload("no-location")
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    record_available_blob(published)

    public_fields = {
        field: getattr(published, field) for field in PublishedBlob.__slots__
    }
    assert set(public_fields) == {
        "blob_id",
        "role",
        "media_type",
        "size",
        "sha256",
        "published_at",
        "state",
    }, f"PublishedBlob grew or lost a public field: {sorted(public_fields)}"

    rendered = repr(published) + repr(public_fields)
    for secret in (
        storage_settings.bucket,
        storage_settings.access_key_id,
        storage_settings.secret_access_key,
        canonical_key(published.blob_id),
    ):
        assert secret not in rendered, (
            "a public return value carries adapter-internal location or credential "
            "material; FF-01 section 2 item 4 keeps bucket and key inside the adapter"
        )

    with independent_db.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'blob'"
        )
        columns = {name for (name,) in cursor.fetchall()}
    independent_db.rollback()

    assert not columns & {"bucket", "key", "object_key", "uri", "url", "path"}, (
        f"the blob table carries a location column: {sorted(columns)}. A blob is "
        "addressed by opaque blob_id; bucket and key remain adapter details."
    )


def test_the_database_is_at_the_migration_head_while_storage_is_serving(
    engine: Any, store: S3BlobStore
) -> None:
    """Both providers are simultaneously in their accepted state.

    Each half is a lane's own claim. Asserting them in one process is what makes
    ``make foundation`` a statement about a single working instance rather than
    two statements about two instances that were never up at the same time.
    """
    state = read_state(engine)
    assert state.is_at_head, (
        f"the database is {state.describe()}; the cross-provider claims below are "
        "about the migrated schema, so a database off head makes them meaningless"
    )
    store.check_access()


def test_the_session_boundary_rolls_back_a_failed_unit_of_work(
    session_factory: sessionmaker[Session],
    independent_db: psycopg.Connection,
    store: S3BlobStore,
    published_blobs: list[BlobId],
    recorded_blob_rows: list[str],
) -> None:
    """A published blob whose metadata write fails leaves no half-recorded row.

    The interesting cross-provider failure is the asymmetric one: bytes are
    canonical, and then the database write raises. ``session_scope`` must roll
    the whole unit of work back, so the row is absent rather than stuck in
    ``temporary`` where a later reader would treat it as an upload in progress.
    """
    payload = _unique_payload("rollback")
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    blob_id = str(published.blob_id)
    # Registered even though the rollback must leave nothing: if this test's own
    # claim is false, the row it proves absent is still removed by exact key.
    recorded_blob_rows.append(blob_id)

    boom = RuntimeError("the caller's own failure, after the insert")
    try:
        with session_scope(session_factory) as session:
            session.execute(
                text("INSERT INTO blob (blob_id, state) VALUES (:blob_id, 'temporary')"),
                {"blob_id": blob_id},
            )
            raise boom
    except RuntimeError as raised:
        assert raised is boom, "session_scope replaced the caller's exception"
    else:  # pragma: no cover - reaching here means the raise did not propagate
        raise AssertionError("session_scope swallowed the caller's exception")

    with independent_db.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM blob WHERE blob_id = %s", (blob_id,))
        (count,) = cursor.fetchone()
    independent_db.rollback()

    assert count == 0, (
        "a unit of work that raised left a row behind: the rollback in "
        "session_scope is not unconditional, so a half-applied command is visible"
    )
    # The bytes are still canonical and still readable. A failed metadata write
    # does not un-publish verified content; it leaves it unrecorded.
    assert store.read(published.blob_id) == payload
