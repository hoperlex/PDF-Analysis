"""Durable deterministic stage-comparison boundary (CMP-SEAL-C3).

Revision ID: 0041_comparison_stage_core
Revises: 0040_comparison_ai_reports

The seal creates storage for resumable stage uploads, confirmed document pairs and
assemblies, full sheet-map revisions, immutable text evidence and pinned chain runs.
It does not read a ZIP or start a stage comparison. Every row reaches ``project``
through a foreign-key chain; names, display numbers and digests are never identities.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0041_comparison_stage_core"
down_revision: str | None = "0040_comparison_ai_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "^[0-9a-f]{64}$"
PART_SIZE_BYTES = 16 * 1024 * 1024

TABLES: tuple[str, ...] = (
    "stage_upload", "stage_upload_file", "stage_upload_part", "stage_upload_candidate",
    "stage_assembly", "stage_assembly_member", "stage_pair", "stage_link_revision",
    "stage_link_item", "stage_text_fragment", "stage_text_exclusion",
    "stage_text_difference", "stage_text_hint", "stage_chain_run", "stage_chain_step",
)


def _id(column: str, prefix: str, *, nullable: bool = False) -> str:
    check = f"{column} ~ '^{prefix}_{ULID}$'"
    return f"({column} IS NULL OR {check})" if nullable else check


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE stage_upload (
            stage_upload_id text PRIMARY KEY,
            project_uid text NOT NULL REFERENCES project (project_uid) ON DELETE RESTRICT,
            state text NOT NULL DEFAULT 'uploading',
            declared_files integer NOT NULL,
            declared_bytes bigint NOT NULL,
            part_size_bytes integer NOT NULL DEFAULT {PART_SIZE_BYTES},
            actor_user_uid text NOT NULL,
            command_id text NOT NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_stage_upload_id CHECK ({_id('stage_upload_id', 'stu')}),
            CONSTRAINT ck_stage_upload_project CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_stage_upload_actor CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_stage_upload_command CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_stage_upload_state CHECK (state IN
                ('uploading', 'paused', 'admitting', 'completed', 'failed', 'cancelled')),
            CONSTRAINT ck_stage_upload_files CHECK (declared_files BETWEEN 1 AND 1000),
            CONSTRAINT ck_stage_upload_bytes CHECK (declared_bytes BETWEEN 1 AND 2147483648),
            CONSTRAINT ck_stage_upload_part_size CHECK (part_size_bytes = {PART_SIZE_BYTES})
        );
    """)
    op.execute("CREATE INDEX ix_stage_upload_project ON stage_upload (project_uid, created_at)")

    op.execute(f"""
        CREATE TABLE stage_upload_file (
            stage_upload_file_id text PRIMARY KEY,
            stage_upload_id text NOT NULL REFERENCES stage_upload (stage_upload_id) ON DELETE RESTRICT,
            media_kind text NOT NULL,
            display_name text NOT NULL,
            declared_size_bytes bigint NOT NULL,
            declared_sha256 text NOT NULL,
            state text NOT NULL DEFAULT 'declared',
            multipart_token text NULL,
            source_blob_id text NULL REFERENCES blob (blob_id) ON DELETE RESTRICT,
            failure_reason text NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_stage_upload_file_id CHECK ({_id('stage_upload_file_id', 'suf')}),
            CONSTRAINT ck_stage_upload_file_upload CHECK ({_id('stage_upload_id', 'stu')}),
            CONSTRAINT ck_stage_upload_file_blob CHECK ({_id('source_blob_id', 'blob', nullable=True)}),
            CONSTRAINT ck_stage_upload_file_kind CHECK (media_kind IN ('pdf', 'zip')),
            CONSTRAINT ck_stage_upload_file_name CHECK (char_length(display_name) BETWEEN 1 AND 255),
            CONSTRAINT ck_stage_upload_file_size CHECK (declared_size_bytes BETWEEN 1 AND 2147483648),
            CONSTRAINT ck_stage_upload_file_sha CHECK (declared_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_stage_upload_file_state CHECK (state IN
                ('declared', 'receiving', 'received', 'admitting', 'ready', 'failed', 'cancelled')),
            CONSTRAINT ck_stage_upload_file_ready CHECK
                (state <> 'ready' OR source_blob_id IS NOT NULL)
        );
    """)
    op.execute("CREATE INDEX ix_stage_upload_file_upload ON stage_upload_file (stage_upload_id)")

    op.execute(f"""
        CREATE TABLE stage_upload_part (
            stage_upload_file_id text NOT NULL REFERENCES stage_upload_file (stage_upload_file_id)
                ON DELETE RESTRICT,
            part_number integer NOT NULL,
            state text NOT NULL DEFAULT 'declared',
            size_bytes integer NULL,
            sha256 text NULL,
            etag text NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (stage_upload_file_id, part_number),
            CONSTRAINT ck_stage_upload_part_file CHECK ({_id('stage_upload_file_id', 'suf')}),
            CONSTRAINT ck_stage_upload_part_number CHECK (part_number BETWEEN 1 AND 128),
            CONSTRAINT ck_stage_upload_part_state CHECK (state IN ('declared', 'staged', 'completed')),
            CONSTRAINT ck_stage_upload_part_size CHECK
                (size_bytes IS NULL OR size_bytes BETWEEN 1 AND {PART_SIZE_BYTES}),
            CONSTRAINT ck_stage_upload_part_sha CHECK (sha256 IS NULL OR sha256 ~ '{SHA256}'),
            CONSTRAINT ck_stage_upload_part_receipt CHECK
                (state = 'declared' OR (size_bytes IS NOT NULL AND sha256 IS NOT NULL AND etag IS NOT NULL))
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_upload_candidate (
            stage_upload_candidate_id text PRIMARY KEY,
            stage_upload_file_id text NOT NULL REFERENCES stage_upload_file (stage_upload_file_id)
                ON DELETE RESTRICT,
            member_number integer NOT NULL,
            state text NOT NULL DEFAULT 'proposed',
            display_name text NOT NULL,
            proposed_stage text NULL,
            proposed_section text NULL,
            designation text NULL,
            confirmed_stage text NULL,
            confirmed_section text NULL,
            document_uid text NULL REFERENCES document (document_uid) ON DELETE RESTRICT,
            version_uid text NULL REFERENCES document_version (version_uid) ON DELETE RESTRICT,
            pdf_blob_id text NULL REFERENCES blob (blob_id) ON DELETE RESTRICT,
            pdf_facts jsonb NULL,
            confirmed_by_user_uid text NULL,
            confirmed_at timestamptz NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_upload_file_id, member_number),
            CONSTRAINT ck_stage_upload_candidate_id CHECK ({_id('stage_upload_candidate_id', 'suc')}),
            CONSTRAINT ck_stage_upload_candidate_file CHECK ({_id('stage_upload_file_id', 'suf')}),
            CONSTRAINT ck_stage_upload_candidate_document CHECK ({_id('document_uid', 'doc', nullable=True)}),
            CONSTRAINT ck_stage_upload_candidate_version CHECK ({_id('version_uid', 'ver', nullable=True)}),
            CONSTRAINT ck_stage_upload_candidate_blob CHECK ({_id('pdf_blob_id', 'blob', nullable=True)}),
            CONSTRAINT ck_stage_upload_candidate_actor CHECK
                ({_id('confirmed_by_user_uid', 'usr', nullable=True)}),
            CONSTRAINT ck_stage_upload_candidate_member CHECK (member_number BETWEEN 1 AND 1000),
            CONSTRAINT ck_stage_upload_candidate_state CHECK
                (state IN ('proposed', 'confirmed', 'admitting', 'published', 'rejected', 'failed')),
            CONSTRAINT ck_stage_upload_candidate_display CHECK
                (char_length(display_name) BETWEEN 1 AND 255),
            CONSTRAINT ck_stage_upload_candidate_stage CHECK
                ((proposed_stage IS NULL OR proposed_stage IN ('P', 'R')) AND
                 (confirmed_stage IS NULL OR confirmed_stage IN ('P', 'R'))),
            CONSTRAINT ck_stage_upload_candidate_pdf_facts CHECK
                (pdf_facts IS NULL OR jsonb_typeof(pdf_facts) = 'object'),
            CONSTRAINT ck_stage_upload_candidate_confirmed CHECK
                (state NOT IN ('confirmed', 'admitting', 'published') OR
                 (confirmed_stage IS NOT NULL AND confirmed_section IS NOT NULL AND
                  confirmed_by_user_uid IS NOT NULL AND confirmed_at IS NOT NULL)),
            CONSTRAINT ck_stage_upload_candidate_published CHECK
                (state <> 'published' OR
                 (document_uid IS NOT NULL AND version_uid IS NOT NULL AND
                  pdf_blob_id IS NOT NULL AND pdf_facts IS NOT NULL))
        );
    """)
    op.execute("CREATE INDEX ix_stage_upload_candidate_file ON stage_upload_candidate (stage_upload_file_id)")

    op.execute(f"""
        CREATE TABLE stage_assembly (
            stage_assembly_id text PRIMARY KEY,
            project_uid text NOT NULL REFERENCES project (project_uid) ON DELETE RESTRICT,
            label text NOT NULL,
            actor_user_uid text NOT NULL,
            command_id text NOT NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_stage_assembly_id CHECK ({_id('stage_assembly_id', 'sas')}),
            CONSTRAINT ck_stage_assembly_project CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_stage_assembly_actor CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_stage_assembly_command CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_stage_assembly_label CHECK (char_length(label) BETWEEN 1 AND 200)
        );
    """)
    op.execute("CREATE INDEX ix_stage_assembly_project ON stage_assembly (project_uid)")

    op.execute(f"""
        CREATE TABLE stage_assembly_member (
            stage_assembly_member_id text PRIMARY KEY,
            stage_assembly_id text NOT NULL REFERENCES stage_assembly (stage_assembly_id)
                ON DELETE RESTRICT,
            member_no integer NOT NULL,
            document_uid text NOT NULL REFERENCES document (document_uid) ON DELETE RESTRICT,
            action text NOT NULL,
            reverses_member_id text NULL REFERENCES stage_assembly_member (stage_assembly_member_id)
                ON DELETE RESTRICT,
            actor_user_uid text NOT NULL,
            command_id text NOT NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_assembly_id, member_no),
            CONSTRAINT ck_stage_assembly_member_id CHECK ({_id('stage_assembly_member_id', 'sam')}),
            CONSTRAINT ck_stage_assembly_member_assembly CHECK ({_id('stage_assembly_id', 'sas')}),
            CONSTRAINT ck_stage_assembly_member_document CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_stage_assembly_member_reverses CHECK
                ({_id('reverses_member_id', 'sam', nullable=True)}),
            CONSTRAINT ck_stage_assembly_member_actor CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_stage_assembly_member_command CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_stage_assembly_member_no CHECK (member_no >= 1),
            CONSTRAINT ck_stage_assembly_member_action CHECK (action IN ('add', 'remove')),
            CONSTRAINT ck_stage_assembly_member_remove CHECK
                ((action = 'remove') = (reverses_member_id IS NOT NULL))
        );
    """)
    op.execute(
        "CREATE UNIQUE INDEX ux_stage_assembly_member_one_remove "
        "ON stage_assembly_member (reverses_member_id) WHERE reverses_member_id IS NOT NULL"
    )

    op.execute(f"""
        CREATE TABLE stage_pair (
            stage_pair_id text PRIMARY KEY,
            project_uid text NOT NULL REFERENCES project (project_uid) ON DELETE RESTRICT,
            left_document_uid text NOT NULL REFERENCES document (document_uid) ON DELETE RESTRICT,
            right_document_uid text NULL REFERENCES document (document_uid) ON DELETE RESTRICT,
            stage_assembly_id text NULL REFERENCES stage_assembly (stage_assembly_id)
                ON DELETE RESTRICT,
            state text NOT NULL DEFAULT 'suggested',
            completeness text NOT NULL DEFAULT 'unknown',
            confirmed_by_user_uid text NULL,
            command_id text NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            confirmed_at timestamptz NULL,
            archived_at timestamptz NULL,
            CONSTRAINT ck_stage_pair_id CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_pair_project CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_stage_pair_left CHECK ({_id('left_document_uid', 'doc')}),
            CONSTRAINT ck_stage_pair_right CHECK ({_id('right_document_uid', 'doc', nullable=True)}),
            CONSTRAINT ck_stage_pair_assembly CHECK ({_id('stage_assembly_id', 'sas', nullable=True)}),
            CONSTRAINT ck_stage_pair_command CHECK ({_id('command_id', 'cmd', nullable=True)}),
            CONSTRAINT ck_stage_pair_actor CHECK
                ({_id('confirmed_by_user_uid', 'usr', nullable=True)}),
            CONSTRAINT ck_stage_pair_one_right CHECK
                ((right_document_uid IS NULL) <> (stage_assembly_id IS NULL)),
            CONSTRAINT ck_stage_pair_distinct CHECK
                (right_document_uid IS NULL OR right_document_uid <> left_document_uid),
            CONSTRAINT ck_stage_pair_state CHECK (state IN ('suggested', 'confirmed', 'archived')),
            CONSTRAINT ck_stage_pair_completeness CHECK
                (completeness IN ('unknown', 'full', 'partial')),
            CONSTRAINT ck_stage_pair_confirmed CHECK
                (state <> 'confirmed' OR
                 (confirmed_by_user_uid IS NOT NULL AND confirmed_at IS NOT NULL AND command_id IS NOT NULL))
        );
    """)
    op.execute("CREATE INDEX ix_stage_pair_project ON stage_pair (project_uid, created_at)")

    op.execute(f"""
        CREATE TABLE stage_link_revision (
            stage_link_revision_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            revision_no integer NOT NULL,
            base_revision_id text NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            source text NOT NULL,
            input_sha256 text NOT NULL,
            actor_user_uid text NOT NULL,
            command_id text NOT NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_pair_id, revision_no),
            CONSTRAINT ck_stage_link_revision_id CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_link_revision_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_link_revision_base CHECK
                ({_id('base_revision_id', 'slk', nullable=True)}),
            CONSTRAINT ck_stage_link_revision_actor CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_stage_link_revision_command CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_stage_link_revision_no CHECK (revision_no >= 1),
            CONSTRAINT ck_stage_link_revision_source CHECK (source IN ('expert', 'automatic')),
            CONSTRAINT ck_stage_link_revision_sha CHECK (input_sha256 ~ '{SHA256}')
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_link_item (
            stage_link_item_id text PRIMARY KEY,
            stage_link_revision_id text NOT NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            row_no integer NOT NULL,
            left_profile_id text NULL REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            right_profile_id text NULL REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            relation text NOT NULL,
            confidence text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_link_revision_id, row_no),
            CONSTRAINT ck_stage_link_item_id CHECK ({_id('stage_link_item_id', 'sli')}),
            CONSTRAINT ck_stage_link_item_revision CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_link_item_left CHECK ({_id('left_profile_id', 'cpr', nullable=True)}),
            CONSTRAINT ck_stage_link_item_right CHECK ({_id('right_profile_id', 'cpr', nullable=True)}),
            CONSTRAINT ck_stage_link_item_row CHECK (row_no >= 1),
            CONSTRAINT ck_stage_link_item_relation CHECK
                ((relation = 'paired' AND left_profile_id IS NOT NULL AND right_profile_id IS NOT NULL)
                 OR (relation = 'only_left' AND left_profile_id IS NOT NULL AND right_profile_id IS NULL)
                 OR (relation = 'only_right' AND left_profile_id IS NULL AND right_profile_id IS NOT NULL)),
            CONSTRAINT ck_stage_link_item_confidence CHECK
                (confidence IN ('high', 'manual', 'review', 'automatic_repair', 'unpaired'))
        );
    """)
    op.execute("CREATE INDEX ix_stage_link_item_left ON stage_link_item (left_profile_id)")
    op.execute("CREATE INDEX ix_stage_link_item_right ON stage_link_item (right_profile_id)")

    op.execute(f"""
        CREATE TABLE stage_text_fragment (
            stage_text_fragment_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            page_profile_id text NOT NULL REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            side text NOT NULL,
            content_key text NOT NULL,
            normalised_text text NOT NULL,
            box_anchor jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_pair_id, content_key),
            CONSTRAINT ck_stage_text_fragment_id CHECK ({_id('stage_text_fragment_id', 'stf')}),
            CONSTRAINT ck_stage_text_fragment_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_text_fragment_profile CHECK ({_id('page_profile_id', 'cpr')}),
            CONSTRAINT ck_stage_text_fragment_side CHECK (side IN ('left', 'right')),
            CONSTRAINT ck_stage_text_fragment_key CHECK (content_key ~ '{SHA256}'),
            CONSTRAINT ck_stage_text_fragment_text CHECK
                (char_length(normalised_text) BETWEEN 1 AND 20000),
            CONSTRAINT ck_stage_text_fragment_box CHECK (jsonb_typeof(box_anchor) = 'object')
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_text_exclusion (
            stage_text_exclusion_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            stage_link_revision_id text NOT NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            left_fragment_id text NOT NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            right_fragment_id text NOT NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            proof_kind text NOT NULL,
            content_key text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_pair_id, stage_link_revision_id, content_key),
            CONSTRAINT ck_stage_text_exclusion_id CHECK ({_id('stage_text_exclusion_id', 'ste')}),
            CONSTRAINT ck_stage_text_exclusion_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_text_exclusion_revision CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_text_exclusion_left CHECK ({_id('left_fragment_id', 'stf')}),
            CONSTRAINT ck_stage_text_exclusion_right CHECK ({_id('right_fragment_id', 'stf')}),
            CONSTRAINT ck_stage_text_exclusion_kind CHECK (proof_kind IN ('same', 'moved')),
            CONSTRAINT ck_stage_text_exclusion_key CHECK (content_key ~ '{SHA256}')
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_text_difference (
            stage_text_difference_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            stage_link_revision_id text NOT NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            left_fragment_id text NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            right_fragment_id text NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            status text NOT NULL,
            content_key text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_pair_id, stage_link_revision_id, content_key),
            CONSTRAINT ck_stage_text_difference_id CHECK ({_id('stage_text_difference_id', 'std')}),
            CONSTRAINT ck_stage_text_difference_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_text_difference_revision CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_text_difference_left CHECK
                ({_id('left_fragment_id', 'stf', nullable=True)}),
            CONSTRAINT ck_stage_text_difference_right CHECK
                ({_id('right_fragment_id', 'stf', nullable=True)}),
            CONSTRAINT ck_stage_text_difference_status CHECK
                ((status = 'changed' AND left_fragment_id IS NOT NULL AND right_fragment_id IS NOT NULL)
                 OR (status = 'removed' AND left_fragment_id IS NOT NULL AND right_fragment_id IS NULL)
                 OR (status = 'added' AND left_fragment_id IS NULL AND right_fragment_id IS NOT NULL)),
            CONSTRAINT ck_stage_text_difference_key CHECK (content_key ~ '{SHA256}')
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_text_hint (
            stage_text_hint_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            stage_link_revision_id text NOT NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            source_fragment_id text NOT NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            target_fragment_id text NOT NULL REFERENCES stage_text_fragment (stage_text_fragment_id)
                ON DELETE RESTRICT,
            content_key text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_pair_id, stage_link_revision_id, content_key),
            CONSTRAINT ck_stage_text_hint_id CHECK ({_id('stage_text_hint_id', 'sth')}),
            CONSTRAINT ck_stage_text_hint_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_text_hint_revision CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_text_hint_source CHECK ({_id('source_fragment_id', 'stf')}),
            CONSTRAINT ck_stage_text_hint_target CHECK ({_id('target_fragment_id', 'stf')}),
            CONSTRAINT ck_stage_text_hint_distinct CHECK (source_fragment_id <> target_fragment_id),
            CONSTRAINT ck_stage_text_hint_key CHECK (content_key ~ '{SHA256}')
        );
    """)

    op.execute(f"""
        CREATE TABLE stage_chain_run (
            stage_chain_run_id text PRIMARY KEY,
            stage_pair_id text NOT NULL REFERENCES stage_pair (stage_pair_id) ON DELETE RESTRICT,
            stage_link_revision_id text NOT NULL REFERENCES stage_link_revision (stage_link_revision_id)
                ON DELETE RESTRICT,
            input_sha256 text NOT NULL,
            pinned_version_uids jsonb NOT NULL,
            state text NOT NULL DEFAULT 'queued',
            failure_reason text NULL,
            actor_user_uid text NOT NULL,
            command_id text NOT NULL UNIQUE REFERENCES command_record (command_id) ON DELETE RESTRICT,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_stage_chain_run_id CHECK ({_id('stage_chain_run_id', 'crn')}),
            CONSTRAINT ck_stage_chain_run_pair CHECK ({_id('stage_pair_id', 'stp')}),
            CONSTRAINT ck_stage_chain_run_revision CHECK ({_id('stage_link_revision_id', 'slk')}),
            CONSTRAINT ck_stage_chain_run_actor CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_stage_chain_run_command CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_stage_chain_run_input CHECK (input_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_stage_chain_run_versions CHECK
                (jsonb_typeof(pinned_version_uids) = 'array' AND
                 jsonb_array_length(pinned_version_uids) BETWEEN 2 AND 100),
            CONSTRAINT ck_stage_chain_run_state CHECK
                (state IN ('queued', 'running', 'paused', 'completed', 'failed', 'cancelled'))
        );
    """)
    op.execute("CREATE INDEX ix_stage_chain_run_pair ON stage_chain_run (stage_pair_id, created_at)")

    op.execute(f"""
        CREATE TABLE stage_chain_step (
            stage_chain_step_id text PRIMARY KEY,
            stage_chain_run_id text NOT NULL REFERENCES stage_chain_run (stage_chain_run_id)
                ON DELETE RESTRICT,
            step_no integer NOT NULL,
            state text NOT NULL DEFAULT 'queued',
            counts jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            failure_reason text NULL,
            started_at timestamptz NULL,
            finished_at timestamptz NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (stage_chain_run_id, step_no),
            CONSTRAINT ck_stage_chain_step_id CHECK ({_id('stage_chain_step_id', 'cst')}),
            CONSTRAINT ck_stage_chain_step_run CHECK ({_id('stage_chain_run_id', 'crn')}),
            CONSTRAINT ck_stage_chain_step_no CHECK (step_no BETWEEN 1 AND 7),
            CONSTRAINT ck_stage_chain_step_state CHECK
                (state IN ('queued', 'running', 'paused', 'completed', 'failed', 'cancelled')),
            CONSTRAINT ck_stage_chain_step_counts CHECK (jsonb_typeof(counts) = 'object')
        );
    """)

    op.execute("""
        CREATE FUNCTION am_check_stage_pair_project() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM document d
                 WHERE d.document_uid = NEW.left_document_uid AND d.project_uid = NEW.project_uid
            ) OR (NEW.right_document_uid IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM document d
                 WHERE d.document_uid = NEW.right_document_uid AND d.project_uid = NEW.project_uid
            )) OR (NEW.stage_assembly_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM stage_assembly a
                 WHERE a.stage_assembly_id = NEW.stage_assembly_id AND a.project_uid = NEW.project_uid
            )) THEN
                RAISE EXCEPTION 'stage_pair_project_mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_pair_project BEFORE INSERT OR UPDATE OF
            project_uid, left_document_uid, right_document_uid, stage_assembly_id
        ON stage_pair FOR EACH ROW EXECUTE FUNCTION am_check_stage_pair_project()
    """)

    op.execute("""
        CREATE FUNCTION am_check_stage_assembly_member() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM stage_assembly a JOIN document d
                  ON d.project_uid = a.project_uid
                 WHERE a.stage_assembly_id = NEW.stage_assembly_id
                   AND d.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION 'stage_assembly_document_project_mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.reverses_member_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM stage_assembly_member m
                 WHERE m.stage_assembly_member_id = NEW.reverses_member_id
                   AND m.stage_assembly_id = NEW.stage_assembly_id
                   AND m.document_uid = NEW.document_uid AND m.action = 'add'
            ) THEN
                RAISE EXCEPTION 'stage_assembly_remove_mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_assembly_member_scope BEFORE INSERT ON stage_assembly_member
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_assembly_member()
    """)

    op.execute("""
        CREATE FUNCTION am_check_stage_upload_candidate_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE upload_project text;
        BEGIN
            SELECT u.project_uid INTO upload_project
              FROM stage_upload_file f JOIN stage_upload u
                ON u.stage_upload_id = f.stage_upload_id
             WHERE f.stage_upload_file_id = NEW.stage_upload_file_id;
            IF NEW.document_uid IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM document d WHERE d.document_uid = NEW.document_uid
                   AND d.project_uid = upload_project
            ) THEN
                RAISE EXCEPTION 'stage_upload_candidate_document_scope_mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.version_uid IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM document_version v JOIN document d
                  ON d.document_uid = v.document_uid
                 WHERE v.version_uid = NEW.version_uid
                   AND v.document_uid = NEW.document_uid
                   AND d.project_uid = upload_project
            ) THEN
                RAISE EXCEPTION 'stage_upload_candidate_version_scope_mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_upload_candidate_scope BEFORE INSERT OR UPDATE OF
            stage_upload_file_id, document_uid, version_uid ON stage_upload_candidate
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_upload_candidate_scope()
    """)

    op.execute("""
        CREATE FUNCTION am_check_stage_link_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            latest_id text;
            latest_no integer;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('stage_link:' || NEW.stage_pair_id, 0));
            IF NOT EXISTS (SELECT 1 FROM stage_pair p WHERE p.stage_pair_id = NEW.stage_pair_id
                           AND p.state = 'confirmed') THEN
                RAISE EXCEPTION 'stage_pair_not_confirmed' USING ERRCODE = 'AM001';
            END IF;
            SELECT r.stage_link_revision_id, r.revision_no INTO latest_id, latest_no
              FROM stage_link_revision r WHERE r.stage_pair_id = NEW.stage_pair_id
             ORDER BY r.revision_no DESC LIMIT 1;
            IF NEW.revision_no <> coalesce(latest_no, 0) + 1
               OR NEW.base_revision_id IS DISTINCT FROM latest_id THEN
                RAISE EXCEPTION 'stage_link_revision_stale' USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_link_revision_chain BEFORE INSERT ON stage_link_revision
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_link_chain()
    """)

    op.execute("""
        CREATE FUNCTION am_stage_profile_in_pair(pair_id text, profile_id text, side_name text)
        RETURNS boolean LANGUAGE sql STABLE AS $fn$
            SELECT EXISTS (
                SELECT 1 FROM stage_pair p
                  JOIN comparison_page_profile pp ON pp.comparison_page_profile_id = profile_id
                  JOIN document_version v ON v.version_uid = pp.version_uid
                  JOIN document d ON d.document_uid = v.document_uid
                 WHERE p.stage_pair_id = pair_id AND d.project_uid = p.project_uid
                   AND ((side_name = 'left' AND d.document_uid = p.left_document_uid)
                        OR (side_name = 'right' AND
                            (d.document_uid = p.right_document_uid OR
                             (p.stage_assembly_id IS NOT NULL AND
                              (SELECT m.action FROM stage_assembly_member m
                                WHERE m.stage_assembly_id = p.stage_assembly_id
                                  AND m.document_uid = d.document_uid
                                ORDER BY m.member_no DESC LIMIT 1) = 'add'))))
            )
        $fn$;
    """)
    op.execute("""
        CREATE FUNCTION am_check_stage_link_item_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE pair_id text;
        BEGIN
            SELECT r.stage_pair_id INTO pair_id FROM stage_link_revision r
             WHERE r.stage_link_revision_id = NEW.stage_link_revision_id;
            IF (NEW.left_profile_id IS NOT NULL AND
                NOT am_stage_profile_in_pair(pair_id, NEW.left_profile_id, 'left'))
               OR (NEW.right_profile_id IS NOT NULL AND
                   NOT am_stage_profile_in_pair(pair_id, NEW.right_profile_id, 'right')) THEN
                RAISE EXCEPTION 'stage_link_profile_scope_mismatch' USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_link_item_scope BEFORE INSERT ON stage_link_item
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_link_item_scope()
    """)
    op.execute("""
        CREATE FUNCTION am_check_stage_text_fragment_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT am_stage_profile_in_pair(NEW.stage_pair_id, NEW.page_profile_id, NEW.side) THEN
                RAISE EXCEPTION 'stage_text_fragment_scope_mismatch' USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_text_fragment_scope BEFORE INSERT ON stage_text_fragment
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_text_fragment_scope()
    """)

    op.execute("""
        CREATE FUNCTION am_check_stage_text_evidence_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            left_id text;
            right_id text;
            left_side text;
            right_side text;
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM stage_link_revision r
                 WHERE r.stage_link_revision_id = NEW.stage_link_revision_id
                   AND r.stage_pair_id = NEW.stage_pair_id
            ) THEN
                RAISE EXCEPTION 'stage_text_revision_scope_mismatch' USING ERRCODE = 'AM001';
            END IF;
            left_id := coalesce(to_jsonb(NEW)->>'left_fragment_id',
                                to_jsonb(NEW)->>'source_fragment_id');
            right_id := coalesce(to_jsonb(NEW)->>'right_fragment_id',
                                 to_jsonb(NEW)->>'target_fragment_id');
            IF left_id IS NOT NULL THEN
                SELECT f.side INTO left_side FROM stage_text_fragment f
                 WHERE f.stage_text_fragment_id = left_id AND f.stage_pair_id = NEW.stage_pair_id;
                IF left_side IS DISTINCT FROM 'left' THEN
                    RAISE EXCEPTION 'stage_text_left_fragment_scope_mismatch' USING ERRCODE = 'AM001';
                END IF;
            END IF;
            IF right_id IS NOT NULL THEN
                SELECT f.side INTO right_side FROM stage_text_fragment f
                 WHERE f.stage_text_fragment_id = right_id AND f.stage_pair_id = NEW.stage_pair_id;
                IF right_side IS DISTINCT FROM 'right' THEN
                    RAISE EXCEPTION 'stage_text_right_fragment_scope_mismatch' USING ERRCODE = 'AM001';
                END IF;
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    for table in ("stage_text_exclusion", "stage_text_difference", "stage_text_hint"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_scope BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_check_stage_text_evidence_scope()"
        )

    op.execute("""
        CREATE FUNCTION am_check_stage_chain_scope() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE pair_row stage_pair%ROWTYPE;
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM stage_pair p JOIN stage_link_revision r
                  ON r.stage_pair_id = p.stage_pair_id
                 WHERE p.stage_pair_id = NEW.stage_pair_id
                   AND p.state = 'confirmed'
                   AND r.stage_link_revision_id = NEW.stage_link_revision_id
            ) THEN
                RAISE EXCEPTION 'stage_chain_link_scope_mismatch' USING ERRCODE = 'AM001';
            END IF;
            SELECT * INTO pair_row FROM stage_pair WHERE stage_pair_id = NEW.stage_pair_id;
            IF EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(NEW.pinned_version_uids) AS pin(version_uid)
                 WHERE pin.version_uid !~ '^ver_[0-9A-HJKMNP-TV-Z]{26}$'
                    OR NOT EXISTS (
                        SELECT 1 FROM document_version v JOIN document d
                          ON d.document_uid = v.document_uid
                         WHERE v.version_uid = pin.version_uid
                           AND d.project_uid = pair_row.project_uid
                           AND (d.document_uid = pair_row.left_document_uid
                             OR d.document_uid = pair_row.right_document_uid
                             OR (pair_row.stage_assembly_id IS NOT NULL AND
                                 (SELECT m.action FROM stage_assembly_member m
                                   WHERE m.stage_assembly_id = pair_row.stage_assembly_id
                                     AND m.document_uid = d.document_uid
                                   ORDER BY m.member_no DESC LIMIT 1) = 'add'))
                    )
            ) THEN
                RAISE EXCEPTION 'stage_chain_version_scope_mismatch' USING ERRCODE = 'AM001';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(NEW.pinned_version_uids) AS pin(version_uid)
                  JOIN document_version v ON v.version_uid = pin.version_uid
                 WHERE v.document_uid = pair_row.left_document_uid
            ) OR NOT EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(NEW.pinned_version_uids) AS pin(version_uid)
                  JOIN document_version v ON v.version_uid = pin.version_uid
                 WHERE v.document_uid = pair_row.right_document_uid
                    OR (pair_row.stage_assembly_id IS NOT NULL AND EXISTS (
                        SELECT 1 FROM stage_assembly_member m
                         WHERE m.stage_assembly_id = pair_row.stage_assembly_id
                           AND m.document_uid = v.document_uid AND m.action = 'add'
                           AND m.member_no = (SELECT max(mm.member_no) FROM stage_assembly_member mm
                                               WHERE mm.stage_assembly_id = m.stage_assembly_id
                                                 AND mm.document_uid = m.document_uid)
                    ))
            ) THEN
                RAISE EXCEPTION 'stage_chain_missing_side_version' USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_stage_chain_scope BEFORE INSERT OR UPDATE OF
            stage_pair_id, stage_link_revision_id ON stage_chain_run
        FOR EACH ROW EXECUTE FUNCTION am_check_stage_chain_scope()
    """)

    for table in (
        "stage_assembly", "stage_assembly_member", "stage_link_revision", "stage_link_item", "stage_text_fragment",
        "stage_text_exclusion", "stage_text_difference", "stage_text_hint",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )

    frozen = {
        "stage_upload": ("stage_upload_id", "project_uid", "declared_files", "declared_bytes",
                         "part_size_bytes", "actor_user_uid", "command_id", "created_at"),
        "stage_upload_file": ("stage_upload_file_id", "stage_upload_id", "media_kind",
                              "display_name", "declared_size_bytes", "declared_sha256", "created_at"),
        "stage_upload_part": ("stage_upload_file_id", "part_number", "created_at"),
        "stage_upload_candidate": ("stage_upload_candidate_id", "stage_upload_file_id",
                                   "member_number", "display_name", "created_at"),
        "stage_pair": ("stage_pair_id", "project_uid", "left_document_uid",
                       "right_document_uid", "stage_assembly_id", "created_at"),
        "stage_chain_run": ("stage_chain_run_id", "stage_pair_id", "stage_link_revision_id",
                            "input_sha256", "pinned_version_uids", "actor_user_uid",
                            "command_id", "created_at"),
        "stage_chain_step": ("stage_chain_step_id", "stage_chain_run_id", "step_no", "created_at"),
    }
    for table, columns in frozen.items():
        args = ", ".join(f"'{column}'" for column in columns)
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({args})"
        )
    write_once = {
        "stage_upload_file": ("multipart_token", "source_blob_id"),
        "stage_upload_candidate": (
            "confirmed_stage", "confirmed_section", "document_uid", "version_uid",
            "pdf_blob_id", "pdf_facts", "confirmed_by_user_uid", "confirmed_at",
        ),
        "stage_pair": ("confirmed_by_user_uid", "confirmed_at", "command_id", "archived_at"),
    }
    for table, columns in write_once.items():
        args = ", ".join(f"'{column}'" for column in columns)
        op.execute(
            f"CREATE TRIGGER trg_{table}_write_once BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns({args})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    occupied = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in TABLES
    }
    if any(occupied.values()):
        rendered = ", ".join(f"{table}={count}" for table, count in occupied.items() if count)
        raise RuntimeError(
            f"0041 downgrade refused: stage-comparison data exists nowhere else ({rendered}); "
            "restore a backup instead of downgrading"
        )
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for name in (
        "am_check_stage_chain_scope", "am_check_stage_text_evidence_scope",
        "am_check_stage_text_fragment_scope", "am_check_stage_upload_candidate_scope",
        "am_check_stage_link_item_scope",
        "am_check_stage_link_chain",
        "am_check_stage_assembly_member", "am_check_stage_pair_project",
    ):
        op.execute(f"DROP FUNCTION {name}()")
    op.execute("DROP FUNCTION am_stage_profile_in_pair(text, text, text)")
