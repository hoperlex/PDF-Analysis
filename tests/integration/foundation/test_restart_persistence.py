"""``FF-01`` section 7 item 7: stop and start without losing accepted state.

This is the property no authoring lane could test. Each ran against its own
throwaway instance and tore it down between runs, so "the migrated schema and a
published object are still there afterwards" was never a question any of them
could ask -- their instances were *supposed* to be disposable.

It is also the property with the most expensive failure mode. A compose file
that declared an anonymous volume, or a ``down`` that passed ``--volumes``,
would look perfect in every other test in this repository and would silently
destroy a database on the first restart.

The restart goes through the frozen ``make down`` and ``make up`` targets rather
than through ``docker`` directly, so what is proved is what an operator running
the accepted command sequence gets.
"""

from __future__ import annotations

import secrets
from typing import Any

import psycopg
import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from auditmanager.shared.db.migrations import read_state
from auditmanager.storage import (
    ROLE_FOUNDATION_CHECK,
    BlobId,
    S3BlobStore,
    S3StorageSettings,
    StorageUnavailableError,
    sha256_of,
)
from auditmanager.storage._object_layout import canonical_key

_MEDIA_TYPE = "application/octet-stream"


def test_the_migrated_schema_and_a_published_object_survive_a_restart(
    store: S3BlobStore,
    engine: Engine,
    database_url: URL,
    independent_s3: Any,
    storage_settings: S3StorageSettings,
    published_blobs: list[BlobId],
    record_available_blob: Any,
    psycopg_connector: Any,
    make_target: Any,
    describe_command: Any,
) -> None:
    """Accepted state on both providers outlives ``make down && make up``.

    The test has three parts and the middle one is the one that makes it
    evidence: after ``make down`` it proves both services are genuinely gone.
    Without that, a ``down`` that quietly did nothing would leave this test
    passing while proving no restart had happened at all.
    """
    payload = f"P1-QA-00 restart {secrets.token_hex(16)}\n".encode("utf-8")
    digest = sha256_of(payload)

    published = store.put_blob(
        payload,
        declared_sha256=digest,
        declared_size=len(payload),
        role=ROLE_FOUNDATION_CHECK,
        media_type=_MEDIA_TYPE,
    )
    published_blobs.append(published.blob_id)
    blob_id = record_available_blob(published)
    key = canonical_key(published.blob_id)

    head_before = independent_s3.head_object(Bucket=storage_settings.bucket, Key=key)
    revision_before = read_state(engine).current
    assert revision_before is not None, "the database is unmigrated before the restart"

    with psycopg_connector(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                "AND tgrelid = 'blob'::regclass"
            )
            (triggers_before,) = cursor.fetchone()
    assert triggers_before > 0, "the blob guards are absent before the restart"

    # --- stop ---------------------------------------------------------------
    down = make_target("down")
    assert down.returncode == 0, describe_command(down)

    # --- and prove the stop really happened ---------------------------------
    # A `down` that silently did nothing would leave every assertion after the
    # restart trivially true, so the outage itself is asserted.
    with pytest.raises(StorageUnavailableError):
        store.check_access()
    with pytest.raises(psycopg.OperationalError):
        psycopg_connector(database_url).close()

    # --- start --------------------------------------------------------------
    up = make_target("up")
    assert up.returncode == 0, describe_command(up)

    # --- the database kept its schema and its rows --------------------------
    # pool_pre_ping discards the connections the shutdown killed, so the same
    # engine is usable again without being rebuilt.
    state_after = read_state(engine)
    assert state_after.current == revision_before, (
        f"the migration revision changed across the restart: {revision_before} -> "
        f"{state_after.current}. The database volume did not survive."
    )
    assert state_after.is_at_head, (
        f"after the restart the database is {state_after.describe()}"
    )

    with psycopg_connector(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT state, sha256, size_bytes, media_type FROM blob "
                "WHERE blob_id = %s",
                (blob_id,),
            )
            row = cursor.fetchone()
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                "AND tgrelid = 'blob'::regclass"
            )
            (triggers_after,) = cursor.fetchone()

    assert row is not None, (
        "the blob row recorded before the restart is gone: PostgreSQL came back "
        "with an empty database, so `make down` destroyed accepted state"
    )
    assert row == ("available", digest, len(payload), _MEDIA_TYPE), (
        f"the recorded metadata changed across the restart: {row}"
    )
    assert triggers_after == triggers_before, (
        "the schema's trigger guards did not survive the restart"
    )

    # --- object storage kept the published bytes ----------------------------
    head_after = independent_s3.head_object(Bucket=storage_settings.bucket, Key=key)
    assert head_after["ETag"] == head_before["ETag"], (
        "the published object's ETag changed across the restart: these are not the "
        "bytes that were published"
    )
    # A restart takes seconds, far longer than the timestamp resolution, so an
    # object that was re-created rather than persisted would show a moved
    # LastModified. This comparison is safe here in a way it would not be for
    # two writes in quick succession.
    assert head_after["LastModified"] == head_before["LastModified"], (
        "the published object was rewritten across the restart rather than "
        "persisted: its LastModified moved"
    )
    assert store.read(published.blob_id) == payload, (
        "the published bytes did not come back byte-identical after the restart"
    )

    inspected = store.inspect(published.blob_id)
    assert inspected.sha256 == digest
    assert inspected.size == len(payload)
    assert inspected.role == ROLE_FOUNDATION_CHECK
    assert inspected.media_type == _MEDIA_TYPE


def test_the_accepted_check_sequence_passes_after_the_restart(
    make_target: Any, describe_command: Any
) -> None:
    """``check-services``, ``check-db`` and ``check-storage`` are green again.

    ``P1-QA-00`` requires ``make down && make up && make check-services &&
    make check-db && make check-storage`` to exit 0 without loss of accepted
    state. The test above proves the state; this proves the three checks
    themselves still pass on the restarted instance, so the required sequence is
    green end to end rather than only in its first two steps.

    Each target's success sentinel is asserted, not just its exit status: the
    Makefile refuses a zero exit without one, and so does this.
    """
    for target in ("check-services", "check-db", "check-storage"):
        result = make_target(target)
        assert result.returncode == 0, describe_command(result)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert lines and lines[-1] == f"FOUNDATION-CHECK OK {target}", (
            f"{target} did not end with its success sentinel:\n"
            + describe_command(result)
        )
