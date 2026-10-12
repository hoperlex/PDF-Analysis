"""The worker registry and the lease's worker.

Revision ID: 0019_execution_workers
Revises: 0018_norm_custody

`W54-SEAL-01` (`W54-PLAN.md` section 3.6; owner ruling R-105). ``worker`` is the registry a
``python -m auditmanager.workers serve`` process writes: its ``wrk`` identity (kept on tmpfs,
so a restarted process is a new worker), its version, when it started, its heartbeat (every
20 s; stale after 90 s and offline after 600 s, derived on read), its ``slots`` and whether
it takes new runs (``intake_enabled``). ``lease.worker_id`` names the worker holding a lease;
it is NULL for a lease taken in-process (``EXECUTION_ROLE=all``) and for every lease written
before this migration, and it joins ``trg_lease_frozen_guard``: a lease never changes hands.

A populated 0019 is not downgraded: a registered worker or a lease naming one refuses it.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0019_execution_workers"
down_revision: str | None = "0018_norm_custody"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"

_LEASE_FROZEN = ("'lease_id'", "'job_id'", "'attempt_id'", "'acquired_at'")


def _lease_frozen_guard(*, with_worker: bool) -> None:
    columns = _LEASE_FROZEN + (("'worker_id'",) if with_worker else ())
    op.execute("DROP TRIGGER trg_lease_frozen_guard ON lease")
    op.execute(
        "CREATE TRIGGER trg_lease_frozen_guard BEFORE UPDATE ON lease "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(" + ", ".join(columns) + ")"
    )


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE worker (
            worker_id      text PRIMARY KEY,
            version        text NOT NULL,
            started_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
            heartbeat_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
            slots          integer NOT NULL,
            intake_enabled boolean NOT NULL DEFAULT true,
            CONSTRAINT ck_worker_worker_id_format
                CHECK (worker_id ~ '^wrk_{ULID_BODY}$'),
            CONSTRAINT ck_worker_version CHECK (char_length(version) BETWEEN 1 AND 128),
            CONSTRAINT ck_worker_slots CHECK (slots >= 1),
            CONSTRAINT ck_worker_heartbeat_after_start CHECK (heartbeat_at >= started_at)
        );
        """
    )
    op.execute("CREATE INDEX ix_worker_heartbeat ON worker (heartbeat_at DESC, worker_id)")
    op.execute(
        "CREATE TRIGGER trg_worker_frozen_guard BEFORE UPDATE ON worker "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'worker_id', 'version', 'started_at', 'slots')"
    )
    op.execute(
        "COMMENT ON TABLE worker IS "
        "'R-105 worker registry. Only heartbeat_at and intake_enabled change; a restarted "
        "process registers a new wrk identity. State (online, stale, offline) is derived "
        "from heartbeat_at on read and never stored.';"
    )

    op.execute("ALTER TABLE lease ADD COLUMN worker_id text NULL REFERENCES worker (worker_id)")
    op.execute(
        "ALTER TABLE lease ADD CONSTRAINT ck_lease_worker_id_format "
        f"CHECK (worker_id IS NULL OR worker_id ~ '^wrk_{ULID_BODY}$')"
    )
    op.execute("CREATE INDEX ix_lease_worker_id ON lease (worker_id) WHERE worker_id IS NOT NULL")
    _lease_frozen_guard(with_worker=True)


def downgrade() -> None:
    bind = op.get_bind()
    retained = []
    if bind.execute(text("SELECT EXISTS (SELECT 1 FROM worker)")).scalar_one():
        retained.append("worker")
    if bind.execute(text("SELECT EXISTS (SELECT 1 FROM lease WHERE worker_id IS NOT NULL)")).scalar_one():
        retained.append("lease.worker_id")
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0019_execution_workers with retained worker data "
            f"({', '.join(retained)}); restore a database backup instead"
        )
    _lease_frozen_guard(with_worker=False)
    op.execute("DROP INDEX ix_lease_worker_id")
    op.execute("ALTER TABLE lease DROP CONSTRAINT ck_lease_worker_id_format")
    op.execute("ALTER TABLE lease DROP COLUMN worker_id")
    op.execute("DROP TABLE worker")
