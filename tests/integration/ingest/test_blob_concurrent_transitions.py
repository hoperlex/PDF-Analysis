"""`D-146` -- two writers of one content-addressed blob row, past the INSERT.

``test_blob_metadata.py`` proves the declaration half: two declarers of equal bytes both succeed
(``ON CONFLICT (blob_id) DO NOTHING`` then a re-read). That half does not need the per-blob
advisory lock -- the INSERT itself waits on the first writer's row -- so removing the lock left
every test in that file green. The lock matters for the **transitions** after the row exists:
two runs of one version both reach ``record_verified`` and then ``mark_available`` for the same
``blob_id``, and a loser that read ``temporary`` (or ``verifying``) before the winner committed
would turn its ``UPDATE ... WHERE state = <what it read>`` into zero rows and fail its run with
``state_transition_not_allowed``.

With the lock the loser waits at the top of the repository call, reads the committed state and
returns it. Each test arranges that interleaving on a real PostgreSQL in two sessions and
observes the wait in ``pg_stat_activity`` rather than assuming it from timing.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

import pytest
from sqlalchemy import text

from auditmanager.shared.errors import DomainError
from auditmanager.storage import (
    BlobState,
    VerifiedBlob,
    declare_blob,
    derive_blob_id,
    parse_blob_role,
    sha256_of,
)
from auditmanager.storage.blob_repository import BlobMetadataRecord, BlobMetadataRepository


def verified_for(content: bytes) -> VerifiedBlob:
    digest = sha256_of(content)
    return VerifiedBlob(
        blob_id=derive_blob_id(sha256=digest, size=len(content)),
        upload_token="tok_" + digest[:16],
        sha256=digest,
        size=len(content),
        role="source_document",  # type: ignore[arg-type]
        media_type="application/pdf",
    )


def _wait_until_blocked(engine, pid: int, *, seconds: float = 15.0) -> None:
    deadline = time.monotonic() + seconds
    with engine.connect() as observer:
        while time.monotonic() < deadline:
            waiting = observer.execute(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                {"pid": pid},
            ).scalar()
            if waiting == "Lock":
                return
            observer.rollback()
            time.sleep(0.05)
    pytest.fail("the second writer never waited for the first; the race was not arranged")


def _declared_and_committed(session_factory, content: bytes):
    """The row exists as ``temporary`` and is committed: the state both runs read first."""
    verified = verified_for(content)
    declaration = declare_blob(
        sha256=verified.sha256,
        size=verified.size,
        role=parse_blob_role("source_document"),
        media_type=verified.media_type,
    )
    with session_factory() as session:
        BlobMetadataRepository().record_declared(session, declaration)
        session.commit()
    return verified


def _race(
    session_factory,
    engine,
    *,
    first: Callable[[Any], Any],
    second: Callable[[Any], BlobMetadataRecord],
) -> dict[str, object]:
    """Run ``first`` uncommitted in this thread; start ``second`` on another session and wait
    until it is blocked; commit ``first``; return what ``second`` produced."""
    one, two = session_factory(), session_factory()
    outcome: dict[str, object] = {}
    try:
        first(one)
        pid = two.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def run_second() -> None:
            try:
                outcome["record"] = second(two)
                two.commit()
            except BaseException as exc:  # noqa: BLE001 - reported by the assertions, verbatim
                outcome["error"] = exc
                two.rollback()

        worker = threading.Thread(target=run_second)
        worker.start()
        _wait_until_blocked(engine, pid)
        one.commit()
        worker.join(timeout=30)
        assert not worker.is_alive(), "the second writer never finished"
    finally:
        one.close()
        two.close()
    return outcome


def test_two_runs_verifying_equal_bytes_both_succeed(session_factory, engine) -> None:
    repository = BlobMetadataRepository()
    content = b"%PDF-1.7\nd-146 verify " + uuid.uuid4().hex.encode()
    verified = _declared_and_committed(session_factory, content)

    outcome = _race(
        session_factory,
        engine,
        first=lambda session: repository.record_verified(session, verified),
        second=lambda session: repository.record_verified(session, verified),
    )

    error = outcome.get("error")
    assert error is None, (
        f"the second run failed ({error!r}): "
        + (str(error.code) if isinstance(error, DomainError) else "not a domain error")
    )
    record = outcome["record"]
    assert isinstance(record, BlobMetadataRecord)
    assert (record.blob_id, record.state) == (verified.blob_id, BlobState.VERIFYING)


def test_two_runs_marking_equal_bytes_available_both_succeed(session_factory, engine) -> None:
    repository = BlobMetadataRepository()
    content = b"%PDF-1.7\nd-146 available " + uuid.uuid4().hex.encode()
    verified = _declared_and_committed(session_factory, content)
    with session_factory() as session:
        repository.record_verified(session, verified)
        session.commit()

    outcome = _race(
        session_factory,
        engine,
        first=lambda session: repository.mark_available(session, verified.blob_id),
        second=lambda session: repository.mark_available(session, verified.blob_id),
    )

    error = outcome.get("error")
    assert error is None, f"the second run failed: {error!r}"
    record = outcome["record"]
    assert isinstance(record, BlobMetadataRecord)
    assert (record.blob_id, record.state) == (verified.blob_id, BlobState.AVAILABLE)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM blob WHERE blob_id = :b"), {"b": str(verified.blob_id)}
        ).scalar_one() == 1
