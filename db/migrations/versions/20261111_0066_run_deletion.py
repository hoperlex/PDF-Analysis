"""0066 -- the tombstone of a deleted run: ``audit_run_deletion`` (`RUN-DELETE-01`; contract 1.53.0).

Revision ID: 0066_run_deletion
Revises: 0065_norm_crop_render

Owner hotfix 2026-11-11: «Добавь возможность удалять частичные и непрошедшие прогоны в UI — они необъективны и их нужно удалять, чтобы
уменьшить шум.» A ``partial``, ``failed`` or ``cancelled`` run is noise in the lists of an expert; the order is that it leaves them.

It is **not** a deletion of data. The run's stage results, findings, expert decisions, cost rows and Blobs stay stored, and ``getRunStatus`` still
answers the run by its identity: a decision an expert took on a finding of that run, or a re-audit that names it as its source, must keep a
row to point at (AGENTS section 4: a path or a display number is never an identity, and nothing the expert decided is rewritten). What the order
removes is the run from every **list** of runs: the run list of a version, the dashboard's counts and picks, the exports and the selections that
read "the latest run".

What this revision adds
-----------------------
``audit_run_deletion`` (PRODUCT)
    One row per deleted run: the run (primary key, so a run is deleted at most once), the instant, the account that deleted it and the command
    record of the keyed ``deleteRun`` call. The row is immutable (``am_immutable_row``): there is no restore operation, and a tombstone that
    could be updated or removed would be a second, silent way to change what a list shows.

It is a table of its own, not a column of ``audit_run``, because ``trg_audit_run_frozen_guard`` refuses any update of a terminal run (a terminal
run is never reopened, PD-03) and a column written after the terminal state would need a hole in that guard.

The application role may ``SELECT`` and ``INSERT`` and nothing else (``scripts/recovery/grant_classification.py``, append-only).

Downgrade
---------
Drops the table. The only fact lost is that the owner's deleted runs show in the run lists again: no run, result, finding or decision is touched
by this revision in either direction.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0066_run_deletion"
down_revision: str | None = "0065_norm_crop_render"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE audit_run_deletion (
            run_id text NOT NULL
                CONSTRAINT ck_audit_run_deletion_run_id_format CHECK (run_id ~ '^run_{ULID}$')
                CONSTRAINT fk_audit_run_deletion_run REFERENCES audit_run (run_id) ON DELETE RESTRICT,
            deleted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            deleted_by_user_uid text NOT NULL
                CONSTRAINT ck_audit_run_deletion_deleted_by_format CHECK (deleted_by_user_uid ~ '^usr_{ULID}$')
                CONSTRAINT fk_audit_run_deletion_deleted_by REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            command_id text NOT NULL
                CONSTRAINT ck_audit_run_deletion_command_id_format CHECK (command_id ~ '^cmd_{ULID}$')
                CONSTRAINT uq_audit_run_deletion_command UNIQUE
                CONSTRAINT fk_audit_run_deletion_command REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT pk_audit_run_deletion PRIMARY KEY (run_id)
        )
    """)
    op.execute(
        "CREATE TRIGGER trg_audit_run_deletion_immutable BEFORE UPDATE OR DELETE ON audit_run_deletion "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "COMMENT ON TABLE audit_run_deletion IS "
        "'RUN-DELETE-01 (owner hotfix 2026-11-11): the tombstone of a run an expert deleted from the run lists. A partial, failed or cancelled run "
        "only. The run, its results, findings and decisions stay stored and getRunStatus still answers it; every list of runs leaves it out. "
        "Immutable; there is no restore.';"
    )


def downgrade() -> None:
    op.execute("DROP TABLE audit_run_deletion")
