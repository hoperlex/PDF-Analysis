"""Durable, immutable six-scope AR v3 beta group.

Revision ID: 0032_ar_v3_run_group
Revises: 0031_executor_pull_channel
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0032_ar_v3_run_group"
down_revision: str | None = "0031_executor_pull_channel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE ar_v3_run_group (
            group_id text PRIMARY KEY CHECK (group_id ~ '^arg_{ULID}$'),
            project_uid text NOT NULL REFERENCES project(project_uid)
                CHECK (project_uid ~ '^prj_{ULID}$'),
            version_uid text NOT NULL REFERENCES document_version(version_uid)
                CHECK (version_uid ~ '^ver_{ULID}$'),
            command_id text NOT NULL UNIQUE REFERENCES command_record(command_id)
                CHECK (command_id ~ '^cmd_{ULID}$'),
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot(norms_snapshot_id)
                CHECK (norms_snapshot_id ~ '^ns_{ULID}$'),
            analysis_profile_id text NOT NULL CHECK (analysis_profile_id ~ '^ap_{ULID}$'),
            prompt_bundle_id text NOT NULL CHECK (prompt_bundle_id ~ '^pb_{ULID}$'),
            pack_sha256 text NOT NULL CHECK (pack_sha256 ~ '^[0-9a-f]{{64}}$'),
            composition_sha256 text NOT NULL CHECK (composition_sha256 ~ '^[0-9a-f]{{64}}$'),
            policy_sha256 text NOT NULL CHECK (policy_sha256 ~ '^[0-9a-f]{{64}}$'),
            provider_mode text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute(f"""
        CREATE TABLE ar_v3_run_group_member (
            group_id text NOT NULL REFERENCES ar_v3_run_group(group_id)
                CHECK (group_id ~ '^arg_{ULID}$'),
            ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 6),
            scope_id text NOT NULL CHECK (scope_id IN ('F1','F2','A1','A2','S1','S2')),
            run_id text NOT NULL UNIQUE REFERENCES audit_run(run_id)
                CHECK (run_id ~ '^run_{ULID}$'),
            map_sha256 text NOT NULL CHECK (map_sha256 ~ '^[0-9a-f]{{64}}$'),
            norm_retrieval_set_id text NOT NULL REFERENCES norm_retrieval_set(norm_retrieval_set_id)
                CHECK (norm_retrieval_set_id ~ '^nrs_{ULID}$'),
            frozen_input_digest text NOT NULL CHECK (frozen_input_digest ~ '^[0-9a-f]{{64}}$'),
            PRIMARY KEY (group_id, ordinal),
            UNIQUE (group_id, scope_id),
            CHECK ((ordinal, scope_id) IN ((1,'F1'),(2,'F2'),(3,'A1'),(4,'A2'),(5,'S1'),(6,'S2')))
        )
    """)
    for table in ("ar_v3_run_group", "ar_v3_run_group_member"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    op.execute("""
        CREATE FUNCTION am_ar_v3_group_complete() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (SELECT count(*) FROM ar_v3_run_group_member WHERE group_id = NEW.group_id) <> 6 THEN
                RAISE EXCEPTION 'AR v3 group requires six members' USING ERRCODE = '23514';
            END IF;
            IF EXISTS (
                SELECT 1 FROM ar_v3_run_group_member m
                JOIN audit_run r ON r.run_id = m.run_id
                JOIN norm_retrieval_set s ON s.norm_retrieval_set_id = m.norm_retrieval_set_id
                WHERE m.group_id = NEW.group_id AND (
                    r.project_uid IS DISTINCT FROM NEW.project_uid
                    OR r.version_uid IS DISTINCT FROM NEW.version_uid
                    OR r.norms_snapshot_id IS DISTINCT FROM NEW.norms_snapshot_id
                    OR r.analysis_profile_id IS DISTINCT FROM NEW.analysis_profile_id
                    OR r.prompt_bundle_id IS DISTINCT FROM NEW.prompt_bundle_id
                    OR r.provider_mode IS DISTINCT FROM NEW.provider_mode
                    OR r.norm_retrieval_set_id IS DISTINCT FROM m.norm_retrieval_set_id
                    OR r.frozen_input_digest IS DISTINCT FROM m.frozen_input_digest
                    OR r.command_id IS DISTINCT FROM NEW.command_id
                    OR s.map_sha256 IS DISTINCT FROM m.map_sha256
                    OR s.norms_snapshot_id IS DISTINCT FROM NEW.norms_snapshot_id
                    OR s.state IS DISTINCT FROM 'verified'
                )
            ) THEN
                RAISE EXCEPTION 'AR v3 member pin mismatch' USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_ar_v3_group_complete
        AFTER INSERT ON ar_v3_run_group DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION am_ar_v3_group_complete()
    """)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(text("SELECT EXISTS (SELECT 1 FROM ar_v3_run_group)")).scalar_one():
        raise RuntimeError("AR v3 group history exists; restore a backup instead of downgrading")
    op.execute("DROP TABLE ar_v3_run_group_member")
    op.execute("DROP TABLE ar_v3_run_group")
    op.execute("DROP FUNCTION am_ar_v3_group_complete()")
