"""Durable normative-corpus snapshots, canonical paragraphs and rebuildable chunks.

Revision ID: 0012_norms_corpus
Revises: 0011_document_section

The domain contract owns opaque identities for the snapshot (``ns_<ULID>``), each normative
document (``ndoc_<ULID>``) and each canonical paragraph (``npar_<ULID>``). W33's
human-readable, content-derived value is stored as ``content_key`` instead: it is an
idempotency/comparison value and never substitutes for an entity identity.

Documents and paragraphs are immutable members of a snapshot. Chunks are a retrieval
projection over consecutive canonical paragraphs: UPDATE is refused, while DELETE remains
available so one complete chunking profile can be rebuilt and inserted again.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0012_norms_corpus"
down_revision: str | None = "0011_document_section"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.norms_corpus")

ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "~ '^[0-9a-f]{64}$'"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE norms_snapshot (
            norms_snapshot_id text PRIMARY KEY,
            content_key text NOT NULL,
            base_content_key text NOT NULL,
            content_digest text NOT NULL,
            drawn_from date NULL,
            drawn_to date NULL,
            undated_documents integer NOT NULL,
            document_count integer NOT NULL,
            repair_count integer NOT NULL DEFAULT 0,
            segmentation_profile text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norms_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_{ULID_BODY}$'),
            CONSTRAINT ck_norms_snapshot_content_key
                CHECK (char_length(content_key) BETWEEN 1 AND 240),
            CONSTRAINT ck_norms_snapshot_base_content_key
                CHECK (char_length(base_content_key) BETWEEN 1 AND 240),
            CONSTRAINT ck_norms_snapshot_content_digest
                CHECK (content_digest {SHA256}),
            CONSTRAINT ck_norms_snapshot_document_count CHECK (document_count > 0),
            CONSTRAINT ck_norms_snapshot_undated_documents
                CHECK (undated_documents BETWEEN 0 AND document_count),
            CONSTRAINT ck_norms_snapshot_repair_count CHECK (repair_count >= 0),
            CONSTRAINT ck_norms_snapshot_segmentation_profile
                CHECK (char_length(segmentation_profile) BETWEEN 1 AND 100),
            CONSTRAINT ck_norms_snapshot_draw_window CHECK (
                (drawn_from IS NULL AND drawn_to IS NULL)
                OR (drawn_from IS NOT NULL AND drawn_to IS NOT NULL AND drawn_from <= drawn_to)
            ),
            CONSTRAINT ck_norms_snapshot_raw_key CHECK (
                (repair_count = 0 AND base_content_key = content_key)
                OR (repair_count > 0 AND base_content_key <> content_key)
            ),
            CONSTRAINT uq_norms_snapshot_content_key UNIQUE (content_key)
        );
        """
    )
    op.execute(
        "COMMENT ON COLUMN norms_snapshot.content_key IS "
        "'Deterministic equality/idempotency key derived from effective corpus text. It is "
        "not an entity identity and never substitutes for norms_snapshot_id.';"
    )

    op.execute(
        """
        CREATE TABLE norm_document (
            norm_document_pk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            norm_document_id text NOT NULL,
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            source_document_ref text NOT NULL,
            slug text NOT NULL,
            title text NOT NULL,
            doc_type text NOT NULL,
            drawn_on date NULL,
            source_attribution text NOT NULL,
            pdf_page_count integer NOT NULL,
            block_count integer NOT NULL,
            page_heading_count integer NOT NULL,
            recognised_characters bigint NOT NULL,
            paragraph_count integer NOT NULL,
            CONSTRAINT ck_norm_document_id_format
                CHECK (norm_document_id ~ '^ndoc_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_document_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_document_source_ref
                CHECK (char_length(source_document_ref) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_document_slug CHECK (char_length(slug) BETWEEN 1 AND 500),
            CONSTRAINT ck_norm_document_title CHECK (char_length(title) BETWEEN 1 AND 1000),
            CONSTRAINT ck_norm_document_doc_type CHECK (char_length(doc_type) BETWEEN 1 AND 100),
            CONSTRAINT ck_norm_document_source_attribution
                CHECK (source_attribution IN ('consultant_plus', 'unattributed')),
            CONSTRAINT ck_norm_document_pdf_page_count CHECK (pdf_page_count > 0),
            CONSTRAINT ck_norm_document_block_count CHECK (block_count >= 0),
            CONSTRAINT ck_norm_document_page_heading_count CHECK (page_heading_count >= 0),
            CONSTRAINT ck_norm_document_recognised_characters
                CHECK (recognised_characters >= 0),
            CONSTRAINT ck_norm_document_paragraph_count CHECK (paragraph_count >= 0),
            CONSTRAINT uq_norm_document_id UNIQUE (norm_document_id),
            CONSTRAINT uq_norm_document_snapshot_source_ref
                UNIQUE (norms_snapshot_id, source_document_ref),
            CONSTRAINT uq_norm_document_snapshot_slug UNIQUE (norms_snapshot_id, slug),
            CONSTRAINT uq_norm_document_snapshot_pk
                UNIQUE (norms_snapshot_id, norm_document_pk)
        );
        """
    )
    op.execute(
        "COMMENT ON COLUMN norm_document.norm_document_pk IS "
        "'Private relational key. It is never returned by an API and is not a domain "
        "identity; source_document_ref, slug and names are also never foreign keys.';"
    )
    op.execute(
        "COMMENT ON COLUMN norm_document.norm_document_id IS "
        "'Opaque public identity. It is generated once and never derived from source names, "
        "content, ordinals or the private relational key.';"
    )

    op.execute(
        """
        CREATE TABLE norm_paragraph (
            norm_paragraph_pk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            norm_paragraph_id text NOT NULL,
            norms_snapshot_id text NOT NULL,
            norm_document_pk bigint NOT NULL,
            ordinal integer NOT NULL,
            page_label integer NOT NULL,
            block_ref text NOT NULL,
            char_offset bigint NOT NULL,
            char_length integer NOT NULL,
            kind text NOT NULL,
            clause_number text NULL,
            text text NOT NULL,
            CONSTRAINT fk_norm_paragraph_document
                FOREIGN KEY (norms_snapshot_id, norm_document_pk)
                REFERENCES norm_document (norms_snapshot_id, norm_document_pk),
            CONSTRAINT ck_norm_paragraph_id_format
                CHECK (norm_paragraph_id ~ '^npar_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_paragraph_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_paragraph_ordinal CHECK (ordinal >= 0),
            CONSTRAINT ck_norm_paragraph_page_label CHECK (page_label > 0),
            CONSTRAINT ck_norm_paragraph_block_ref
                CHECK (char_length(block_ref) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_paragraph_char_offset CHECK (char_offset >= 0),
            CONSTRAINT ck_norm_paragraph_char_length
                CHECK (char_length > 0 AND char_length = char_length(text)),
            CONSTRAINT ck_norm_paragraph_kind
                CHECK (kind IN ('body', 'heading', 'table_row')),
            CONSTRAINT ck_norm_paragraph_clause_number
                CHECK (clause_number IS NULL OR char_length(clause_number) BETWEEN 1 AND 100),
            CONSTRAINT uq_norm_paragraph_id UNIQUE (norm_paragraph_id),
            CONSTRAINT uq_norm_paragraph_snapshot_document_ordinal
                UNIQUE (norms_snapshot_id, norm_document_pk, ordinal)
        );
        """
    )
    op.execute(
        "COMMENT ON COLUMN norm_paragraph.norm_paragraph_id IS "
        "'Opaque public identity of immutable canonical normative text; never a content hash "
        "or paragraph ordinal.';"
    )

    op.execute(
        """
        CREATE TABLE norm_chunk_build (
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            chunking_profile text NOT NULL,
            target_characters integer NOT NULL,
            chunk_count integer NOT NULL,
            built_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norm_chunk_build_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_chunk_build_profile
                CHECK (char_length(chunking_profile) BETWEEN 1 AND 100),
            CONSTRAINT ck_norm_chunk_build_target CHECK (target_characters > 0),
            CONSTRAINT ck_norm_chunk_build_count CHECK (chunk_count >= 0),
            CONSTRAINT pk_norm_chunk_build
                PRIMARY KEY (norms_snapshot_id, chunking_profile)
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE norm_chunk (
            norm_chunk_pk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            norms_snapshot_id text NOT NULL,
            norm_document_pk bigint NOT NULL,
            chunking_profile text NOT NULL,
            ordinal integer NOT NULL,
            page_first integer NOT NULL,
            page_last integer NOT NULL,
            char_offset bigint NOT NULL,
            char_length integer NOT NULL,
            paragraph_ordinal_first integer NOT NULL,
            paragraph_ordinal_last integer NOT NULL,
            paragraph_count integer NOT NULL,
            clause_numbers text[] NOT NULL DEFAULT '{{}}'::text[],
            contains_clause boolean NOT NULL,
            text text NOT NULL,
            content_sha256 text NOT NULL,
            CONSTRAINT fk_norm_chunk_build
                FOREIGN KEY (norms_snapshot_id, chunking_profile)
                REFERENCES norm_chunk_build (norms_snapshot_id, chunking_profile)
                ON DELETE CASCADE
                DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT fk_norm_chunk_document
                FOREIGN KEY (norms_snapshot_id, norm_document_pk)
                REFERENCES norm_document (norms_snapshot_id, norm_document_pk),
            CONSTRAINT fk_norm_chunk_first_paragraph
                FOREIGN KEY (norms_snapshot_id, norm_document_pk, paragraph_ordinal_first)
                REFERENCES norm_paragraph (norms_snapshot_id, norm_document_pk, ordinal),
            CONSTRAINT fk_norm_chunk_last_paragraph
                FOREIGN KEY (norms_snapshot_id, norm_document_pk, paragraph_ordinal_last)
                REFERENCES norm_paragraph (norms_snapshot_id, norm_document_pk, ordinal),
            CONSTRAINT ck_norm_chunk_profile
                CHECK (char_length(chunking_profile) BETWEEN 1 AND 100),
            CONSTRAINT ck_norm_chunk_ordinal CHECK (ordinal >= 0),
            CONSTRAINT ck_norm_chunk_page_span
                CHECK (page_first > 0 AND page_last >= page_first),
            CONSTRAINT ck_norm_chunk_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{{26}}$'),
            CONSTRAINT ck_norm_chunk_char_span CHECK (char_offset >= 0 AND char_length > 0),
            CONSTRAINT ck_norm_chunk_paragraph_span CHECK (
                paragraph_ordinal_first >= 0
                AND paragraph_ordinal_last >= paragraph_ordinal_first
                AND paragraph_count = paragraph_ordinal_last - paragraph_ordinal_first + 1
            ),
            CONSTRAINT ck_norm_chunk_contains_clause
                CHECK (contains_clause = (cardinality(clause_numbers) > 0)),
            CONSTRAINT ck_norm_chunk_text CHECK (char_length(text) > 0),
            CONSTRAINT ck_norm_chunk_content_sha256 CHECK (content_sha256 {SHA256}),
            CONSTRAINT uq_norm_chunk_document_profile_ordinal
                UNIQUE (norm_document_pk, chunking_profile, ordinal)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_norm_chunk_snapshot_profile "
        "ON norm_chunk (norms_snapshot_id, chunking_profile);"
    )
    op.execute(
        "CREATE INDEX ix_norm_chunk_clause_numbers ON norm_chunk USING gin (clause_numbers);"
    )
    op.execute(
        "COMMENT ON TABLE norm_chunk IS "
        "'Rebuildable retrieval projection over consecutive canonical norm_paragraph rows. "
        "Rows may be deleted and reinserted by complete chunking profile; they are not "
        "canonical normative evidence.';"
    )

    for table in ("norms_snapshot", "norm_document", "norm_paragraph"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
            """
        )

    op.execute(
        """
        CREATE FUNCTION am_norm_chunk_no_update() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION
                'state_transition_not_allowed: % is replace-only; UPDATE is refused', TG_TABLE_NAME
                USING ERRCODE = 'AM003',
                      HINT = 'Delete and rebuild one complete chunking profile from canonical paragraphs.';
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_norm_chunk_no_update
            BEFORE UPDATE ON norm_chunk
            FOR EACH ROW EXECUTE FUNCTION am_norm_chunk_no_update();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_norm_chunk_build_no_update
            BEFORE UPDATE ON norm_chunk_build
            FOR EACH ROW EXECUTE FUNCTION am_norm_chunk_no_update();
        """
    )
    op.execute(
        """
        ALTER TABLE audit_run
            ADD CONSTRAINT fk_audit_run_norms_snapshot
            FOREIGN KEY (norms_snapshot_id)
            REFERENCES norms_snapshot (norms_snapshot_id);
        """
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.norms_snapshot_id IS "
        "'Optional opaque identity of the immutable normative-corpus snapshot pinned by "
        "this run. NULL continues to mean that no norms snapshot was admitted.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    snapshot_count = bind.execute(text("SELECT count(*) FROM norms_snapshot")).scalar_one()
    if snapshot_count:
        _log.warning(
            "0012_norms_corpus downgrade: dropping %d immutable snapshot(s) and their "
            "canonical paragraphs. Use only before consumers exist or restore afterwards.",
            snapshot_count,
        )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT fk_audit_run_norms_snapshot;")
    op.execute("DROP TABLE norm_chunk;")
    op.execute("DROP TABLE norm_chunk_build;")
    op.execute("DROP FUNCTION am_norm_chunk_no_update();")
    op.execute("DROP TABLE norm_paragraph;")
    op.execute("DROP TABLE norm_document;")
    op.execute("DROP TABLE norms_snapshot;")
    op.execute(
        "COMMENT ON COLUMN audit_run.norms_snapshot_id IS "
        "'Always NULL in the pre-0012 schema: no durable norms snapshot table exists.';"
    )
