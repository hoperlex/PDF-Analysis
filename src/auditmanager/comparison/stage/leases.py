"""Process leases for stage uploads with external multipart effects."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.errors import DomainError, ErrorCode


@contextmanager
def upload_process_lease(
    session_factory: sessionmaker[Session], upload_id: str,
) -> Iterator[None]:
    """Serialize part writes with pause/cancel across processes.

    The connection holds a PostgreSQL session lock while bytes move. A killed
    process releases it even if its short DB transaction already committed.
    """
    bind = session_factory.kw.get("bind")
    if bind is None:
        raise ValueError("stage upload needs a database bind for its process lease")
    lock = f"stage_upload:batch_process:{upload_id}"
    with bind.engine.connect() as lease:
        held = bool(lease.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:lock))"), {"lock": lock},
        ).scalar_one())
        lease.commit()
        if not held:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_upload_busy")
        try:
            yield
        finally:
            released = bool(lease.execute(
                text("SELECT pg_advisory_unlock(hashtext(:lock))"), {"lock": lock},
            ).scalar_one())
            lease.commit()
            if not released:
                raise RuntimeError("the stage upload process lease was lost")
