"""``FF-01`` section 7 items 3 and 8: doing it twice changes nothing.

Three separate idempotency claims meet on this instance, and each is asserted
by comparing *state*, never by reading an exit status:

* running the migration again at head applies no DDL;
* initializing the bucket again creates nothing and reopens nothing;
* publishing identical verified content again returns the same ``blob_id`` and
  does not rewrite the canonical object.

The third one is where a suite is easiest to fool. "The object was not
rewritten" is usually asserted by comparing a timestamp, and a store whose
timestamp resolution is coarser than the gap between the two writes will look
idempotent while rewriting the bytes every time. So the claim is made a second
way that has no clock in it at all: the adapter is handed a pass-through proxy
around a real ``boto3`` client, and the number of ``copy_object`` calls is
counted. One copy across two publications is a fact no resolution can blur.
"""

from __future__ import annotations

import secrets
import subprocess
from collections import Counter
from typing import Any

import psycopg
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db.migrations import read_state
from auditmanager.shared.db.session import session_scope
from auditmanager.storage import (
    ROLE_FOUNDATION_CHECK,
    BlobId,
    S3BlobStore,
    S3StorageSettings,
    derive_blob_id,
    sha256_of,
)
from auditmanager.storage._object_layout import canonical_key

_MEDIA_TYPE = "application/octet-stream"

#: Everything the migration head creates, as one comparable string: columns,
#: triggers, indexes, functions and views. A second `alembic upgrade head` that
#: applied any DDL at all would move one of these lines.
_SCHEMA_FINGERPRINT = """
SELECT coalesce(string_agg(entry, chr(10) ORDER BY entry), '')
FROM (
    SELECT 'column:' || table_name || '.' || column_name || ':' || data_type AS entry
      FROM information_schema.columns WHERE table_schema = 'public'
    UNION ALL
    SELECT 'trigger:' || tgrelid::regclass::text || '.' || tgname
      FROM pg_trigger WHERE NOT tgisinternal
    UNION ALL
    SELECT 'index:' || indexname || ':' || indexdef
      FROM pg_indexes WHERE schemaname = 'public'
    UNION ALL
    SELECT 'function:' || p.proname
      FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'public'
    UNION ALL
    SELECT 'view:' || viewname FROM pg_views WHERE schemaname = 'public'
) AS parts
"""


class _CountingClient:
    """A pass-through proxy that records which S3 operations were called.

    Not a mock and not a substitute: every call is delegated to the real
    ``boto3`` client underneath, so the bytes really travel to the real MinIO
    service. The only thing added is a counter, which is what makes "the second
    publication did not rewrite the object" checkable without a clock.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.calls: Counter[str] = Counter()

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._inner, name)
        if not callable(attribute):
            return attribute

        def counted(*args: Any, **kwargs: Any) -> Any:
            self.calls[name] += 1
            return attribute(*args, **kwargs)

        return counted


def _fingerprint(connection: psycopg.Connection) -> str:
    with connection.cursor() as cursor:
        cursor.execute(_SCHEMA_FINGERPRINT)
        (value,) = cursor.fetchone()
    connection.rollback()
    return value


# --------------------------------------------------------------------------
# migrations
# --------------------------------------------------------------------------


def test_running_the_migration_again_at_head_applies_no_ddl(
    engine: Engine,
    independent_db: psycopg.Connection,
    make_target: Any,
    describe_command: Any,
) -> None:
    """``make migrate`` twice more on a database already at head changes nothing.

    Migrating an *empty* database is the database lane's own suite, which
    creates and drops its own throwaway databases for the purpose. This is the
    other half of ``FF-01`` section 7 item 3, and the half only the converged
    instance can show: the accepted, populated database this gate runs against
    is not disturbed by re-running the command.

    Exit status is not the evidence -- an ``upgrade head`` that dropped and
    recreated a table would also exit 0. The whole schema is fingerprinted
    before and after each run.
    """
    before = _fingerprint(independent_db)
    revision_before = read_state(engine).current
    assert revision_before is not None, "the database is unmigrated"

    for attempt in (1, 2):
        result = make_target("migrate")
        assert result.returncode == 0, (
            f"migrate attempt {attempt} failed:\n{describe_command(result)}"
        )
        assert _fingerprint(independent_db) == before, (
            f"migrate attempt {attempt} changed the schema. A rerun at head must "
            "apply no DDL at all."
        )
        assert read_state(engine).current == revision_before, (
            f"migrate attempt {attempt} moved the stamped revision"
        )

    assert read_state(engine).is_at_head


def test_the_migration_history_has_exactly_one_head(engine: Engine) -> None:
    """One head, so "upgrade head" is unambiguous on this converged tree.

    Two lanes merging into one branch is exactly how a second head appears, and
    a branched history would make every idempotency claim above conditional on
    which head Alembic happened to pick.
    """
    state = read_state(engine)
    assert state.expected_head, "no migration head is declared"
    assert state.is_at_head, f"the database is {state.describe()}"


# --------------------------------------------------------------------------
# bucket initialization
# --------------------------------------------------------------------------


def test_initializing_the_bucket_again_is_a_no_op(
    frozen_env: dict[str, str],
    storage_settings: S3StorageSettings,
    store: S3BlobStore,
    anonymous_s3: Any,
    independent_s3: Any,
    published_blobs: list[BlobId],
) -> None:
    """``FF-01`` section 7 item 8, run as the initializer's own documented rerun.

    ``bucket-init.sh`` documents this exact invocation for re-running it by
    hand, and it is what ``make up`` runs on every start. The assertion is not
    only "it exited 0": an object published beforehand must still be there
    afterwards, and the bucket must still refuse an anonymous caller. An
    initializer that recreated the bucket would pass an exit-status check while
    having destroyed everything in it.
    """
    payload = f"P1-QA-00 reinit {secrets.token_hex(16)}\n".encode("utf-8")
    published = store.put_blob(
        payload,
        declared_sha256=sha256_of(payload),
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    key = canonical_key(published.blob_id)
    before = independent_s3.head_object(Bucket=storage_settings.bucket, Key=key)

    result = _rerun_bucket_init(frozen_env)
    assert result.returncode == 0, (
        f"the documented bucket-init rerun failed:\n"
        f"exit {result.returncode}\n{result.stdout}\n{result.stderr}"
    )
    assert "no-op" in result.stdout, (
        "the second initialization did not report a no-op; it created something:\n"
        + result.stdout
    )
    assert "bucket-init: OK" in result.stdout

    after = independent_s3.head_object(Bucket=storage_settings.bucket, Key=key)
    assert after["ETag"] == before["ETag"], (
        "re-initializing the bucket changed an object that was already in it"
    )
    assert store.read(published.blob_id) == payload

    # Still private. `mc anonymous set none` is unconditional, so a second run
    # must leave the bucket closed rather than opening it.
    from botocore.exceptions import ClientError

    with pytest.raises(ClientError):
        anonymous_s3.list_objects_v2(Bucket=storage_settings.bucket, MaxKeys=1)


def _rerun_bucket_init(frozen_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """The rerun command ``infra/local/bucket-init.sh`` documents in its header.

    ``-T`` is added because pytest gives the child no TTY; without it compose
    would try to allocate one and the capture would fail for a reason that has
    nothing to do with idempotency.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            frozen_env["FOUNDATION_INSTANCE"],
            "--file",
            str(root / "infra" / "local" / "docker-compose.yml"),
            "exec",
            "-T",
            "s3-init",
            "/bin/sh",
            "/usr/local/lib/foundation/bucket-init.sh",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


# --------------------------------------------------------------------------
# republication
# --------------------------------------------------------------------------


def test_publishing_identical_content_twice_does_not_rewrite_the_object(
    storage_settings: S3StorageSettings,
    independent_s3: Any,
    published_blobs: list[BlobId],
) -> None:
    """The same bytes twice: one identity, one object, one copy operation.

    The counted proxy is the point. Comparing ``LastModified`` alone would let
    an adapter that rewrites the object every time pass whenever the store's
    timestamp resolution is coarser than the gap between the two calls -- a
    trap this programme has already been caught by once. Counting
    ``copy_object`` has no clock in it: two publications that performed two
    copies cannot report one.
    """
    inner = independent_s3
    counting = _CountingClient(inner)
    store = S3BlobStore(storage_settings, client=counting)
    assert type(inner).__module__.startswith("botocore."), (
        "the proxied client is not a real botocore client, so this test would be "
        "asserting against a substitute"
    )

    payload = f"P1-QA-00 idempotent {secrets.token_hex(16)}\n".encode("utf-8")
    digest = sha256_of(payload)

    first = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(first.blob_id)
    key = canonical_key(first.blob_id)
    head_after_first = independent_s3.head_object(
        Bucket=storage_settings.bucket, Key=key
    )
    copies_after_first = counting.calls["copy_object"]
    assert copies_after_first == 1, (
        f"the first publication performed {copies_after_first} copies, expected 1"
    )

    second = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )

    assert second.blob_id == first.blob_id == derive_blob_id(
        sha256=digest, size=len(payload)
    ), "identical content resolved to two different identities"
    assert counting.calls["copy_object"] == 1, (
        f"the second publication performed another copy_object "
        f"({counting.calls['copy_object']} total): identical content was rewritten "
        "rather than recognised as already available"
    )

    # Corroborating only, and deliberately labelled as such. MinIO records
    # LastModified to one-second resolution, so two publications in the same
    # second carry the same timestamp whether or not the object was rewritten:
    # measured against an adapter mutated to copy unconditionally, this pair of
    # assertions PASSED while copy_object had run twice. They are kept because
    # a moved timestamp would still be a real signal, but the copy_object count
    # above is the assertion that can actually fail.
    head_after_second = independent_s3.head_object(
        Bucket=storage_settings.bucket, Key=key
    )
    assert head_after_second["ETag"] == head_after_first["ETag"]
    assert head_after_second["LastModified"] == head_after_first["LastModified"], (
        "the canonical object's LastModified moved on the second publication"
    )
    assert second.published_at == first.published_at

    # Two publications staged twice and removed both stagings. The second
    # attempt's bytes are dropped by the same call that recognises the content
    # as already available, so republication accumulates no temporary residue.
    assert counting.calls["put_object"] == 2, "each attempt should stage exactly once"
    assert counting.calls["delete_object"] == 2, (
        f"{counting.calls['delete_object']} temporary deletions for 2 stagings: a "
        "republication left staged bytes behind"
    )


def test_the_database_refuses_a_second_available_row_for_the_same_content(
    store: S3BlobStore,
    session_factory: sessionmaker[Session],
    independent_db: psycopg.Connection,
    published_blobs: list[BlobId],
    recorded_blob_rows: list[str],
    record_available_blob: Any,
) -> None:
    """The other half of idempotency: the database will not record a duplicate.

    The adapter makes republication a no-op by deriving identity from
    ``(sha256, size)``. The schema backs that with a partial unique index over
    available content. Asserting both in one run is what shows the two agree --
    a store that deduplicated and a database that did not would produce exactly
    the divergence this gate exists to catch.
    """
    payload = f"P1-QA-00 db-dupe {secrets.token_hex(16)}\n".encode("utf-8")
    digest = sha256_of(payload)
    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    record_available_blob(published)

    # A well-formed identity that is NOT this content's, used to claim this
    # content. derive_blob_id is deterministic, so a genuine second identity for
    # the same bytes cannot exist -- which is itself the first line of defence.
    impostor = derive_blob_id(sha256=sha256_of(payload + b"different"), size=len(payload))
    assert impostor != published.blob_id
    recorded_blob_rows.append(str(impostor))

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            session.execute(
                text("INSERT INTO blob (blob_id, state) VALUES (:blob_id, 'temporary')"),
                {"blob_id": str(impostor)},
            )
            session.execute(
                text("UPDATE blob SET state = 'verifying' WHERE blob_id = :blob_id"),
                {"blob_id": str(impostor)},
            )
            session.execute(
                text(
                    "UPDATE blob SET state = 'available', sha256 = :sha256, "
                    "size_bytes = :size, media_type = :media_type "
                    "WHERE blob_id = :blob_id"
                ),
                {
                    "blob_id": str(impostor),
                    "sha256": digest,
                    "size": len(payload),
                    "media_type": _MEDIA_TYPE,
                },
            )

    with independent_db.cursor() as cursor:
        cursor.execute(
            "SELECT blob_id FROM blob WHERE sha256 = %s AND state = 'available'",
            (digest,),
        )
        rows = [blob_id for (blob_id,) in cursor.fetchall()]
    independent_db.rollback()

    assert rows == [str(published.blob_id)], (
        f"available content is recorded under more than one identity: {rows}"
    )
