"""Install pgvector and add the rebuildable normative embedding projection.

Revision ID: 0013_norm_embeddings
Revises: 0012_norms_corpus

The one seeded profile is immutable reference data. Embedding rows remain a private,
replace-only retrieval projection: the canonical authority is still ``norm_paragraph`` and
public search results must resolve through its opaque identity rather than cite a vector row.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0013_norm_embeddings"
down_revision: str | None = "0012_norms_corpus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PGVECTOR_VERSION = "0.8.6"
PROFILE = "bge-m3-dense-v1"
DIMENSIONS = 1024
SHA256 = "~ '^[0-9a-f]{64}$'"


def upgrade() -> None:
    # The repository-owned image carries the extension files. Database installation remains a
    # migration so an image restart can never mutate schema behind Alembic's back.
    op.execute(f"CREATE EXTENSION vector WITH VERSION '{PGVECTOR_VERSION}';")

    op.execute(
        """
        CREATE TABLE norm_embedding_profile (
            embedding_profile text PRIMARY KEY,
            model_repository text NOT NULL,
            model_revision text NOT NULL,
            tokenizer_revision text NOT NULL,
            transformers_version text NOT NULL,
            sentence_transformers_version text NOT NULL,
            pooling text NOT NULL,
            dimensions integer NOT NULL,
            normalized boolean NOT NULL,
            distance_metric text NOT NULL,
            max_tokens integer NOT NULL,
            overlap_tokens integer NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norm_embedding_profile_key
                CHECK (char_length(embedding_profile) BETWEEN 1 AND 100),
            CONSTRAINT ck_norm_embedding_profile_model
                CHECK (char_length(model_repository) BETWEEN 1 AND 200),
            CONSTRAINT ck_norm_embedding_profile_revision
                CHECK (model_revision ~ '^[0-9a-f]{40}$'
                       AND tokenizer_revision ~ '^[0-9a-f]{40}$'),
            CONSTRAINT ck_norm_embedding_profile_pooling CHECK (pooling = 'cls'),
            CONSTRAINT ck_norm_embedding_profile_dimensions CHECK (dimensions = 1024),
            CONSTRAINT ck_norm_embedding_profile_normalized CHECK (normalized),
            CONSTRAINT ck_norm_embedding_profile_distance
                CHECK (distance_metric = 'inner_product'),
            CONSTRAINT ck_norm_embedding_profile_tokens
                CHECK (max_tokens = 512 AND overlap_tokens = 64)
        );
        """
    )
    op.execute(
        """
        INSERT INTO norm_embedding_profile (
            embedding_profile, model_repository, model_revision, tokenizer_revision,
            transformers_version, sentence_transformers_version, pooling, dimensions,
            normalized, distance_metric, max_tokens, overlap_tokens
        ) VALUES (
            'bge-m3-dense-v1', 'BAAI/bge-m3',
            '5617a9f61b028005a4858fdac845db406aefb181',
            '5617a9f61b028005a4858fdac845db406aefb181',
            '4.53.3', '5.0.0', 'cls', 1024, true, 'inner_product', 512, 64
        );
        """
    )

    # A composite reference prevents a vector row from naming a chunk under another snapshot or
    # chunking profile, without treating the chunk's private relational key as public identity.
    op.execute(
        """
        ALTER TABLE norm_chunk
            ADD CONSTRAINT uq_norm_chunk_pk_snapshot_profile
            UNIQUE (norm_chunk_pk, norms_snapshot_id, chunking_profile);
        """
    )
    op.execute(
        """
        CREATE TABLE norm_embedding_build (
            norms_snapshot_id text NOT NULL,
            chunking_profile text NOT NULL,
            embedding_profile text NOT NULL,
            chunk_count integer NOT NULL,
            window_count integer NOT NULL,
            embedding_set_sha256 text NOT NULL,
            built_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_norm_embedding_build_chunks
                FOREIGN KEY (norms_snapshot_id, chunking_profile)
                REFERENCES norm_chunk_build (norms_snapshot_id, chunking_profile)
                ON DELETE CASCADE,
            CONSTRAINT fk_norm_embedding_build_profile
                FOREIGN KEY (embedding_profile)
                REFERENCES norm_embedding_profile (embedding_profile),
            CONSTRAINT ck_norm_embedding_build_snapshot_id
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{26}$'),
            CONSTRAINT ck_norm_embedding_build_counts
                CHECK (chunk_count >= 0 AND window_count >= chunk_count),
            CONSTRAINT ck_norm_embedding_build_sha256
                CHECK (embedding_set_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT pk_norm_embedding_build
                PRIMARY KEY (norms_snapshot_id, chunking_profile, embedding_profile)
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE norm_embedding (
            norm_embedding_pk bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            norms_snapshot_id text NOT NULL,
            norm_chunk_pk bigint NOT NULL,
            chunking_profile text NOT NULL,
            embedding_profile text NOT NULL,
            window_ordinal integer NOT NULL,
            token_count integer NOT NULL,
            char_offset integer NOT NULL,
            char_length integer NOT NULL,
            paragraph_ordinal_first integer NOT NULL,
            paragraph_ordinal_last integer NOT NULL,
            input_sha256 text NOT NULL,
            embedding_sha256 text NOT NULL,
            embedding vector({DIMENSIONS}) NOT NULL,
            CONSTRAINT fk_norm_embedding_chunk
                FOREIGN KEY (norm_chunk_pk, norms_snapshot_id, chunking_profile)
                REFERENCES norm_chunk (norm_chunk_pk, norms_snapshot_id, chunking_profile)
                ON DELETE CASCADE,
            CONSTRAINT fk_norm_embedding_build
                FOREIGN KEY (norms_snapshot_id, chunking_profile, embedding_profile)
                REFERENCES norm_embedding_build (
                    norms_snapshot_id, chunking_profile, embedding_profile
                )
                ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT ck_norm_embedding_snapshot_id
                CHECK (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{{26}}$'),
            CONSTRAINT ck_norm_embedding_window_ordinal CHECK (window_ordinal >= 0),
            CONSTRAINT ck_norm_embedding_token_count CHECK (token_count BETWEEN 1 AND 512),
            CONSTRAINT ck_norm_embedding_char_span CHECK (char_offset >= 0 AND char_length > 0),
            CONSTRAINT ck_norm_embedding_paragraph_span CHECK (
                paragraph_ordinal_first >= 0
                AND paragraph_ordinal_last >= paragraph_ordinal_first
            ),
            CONSTRAINT ck_norm_embedding_input_sha256 CHECK (input_sha256 {SHA256}),
            CONSTRAINT ck_norm_embedding_vector_sha256 CHECK (embedding_sha256 {SHA256}),
            CONSTRAINT ck_norm_embedding_unit_norm
                CHECK (abs(vector_norm(embedding) - 1.0) <= 0.0001),
            CONSTRAINT uq_norm_embedding_chunk_profile_window
                UNIQUE (norm_chunk_pk, embedding_profile, window_ordinal)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX ix_norm_embedding_build_members
            ON norm_embedding (norms_snapshot_id, chunking_profile, embedding_profile);
        """
    )
    op.execute(
        """
        CREATE INDEX ix_norm_embedding_hnsw_ip
            ON norm_embedding USING hnsw (embedding vector_ip_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )
    op.execute(
        """
        COMMENT ON TABLE norm_embedding IS
        'Private rebuildable retrieval windows. Canonical evidence remains norm_paragraph; '
        'norm_embedding_pk is never a public identity.';
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_norm_embedding_profile_immutable
            BEFORE UPDATE OR DELETE ON norm_embedding_profile
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        CREATE TRIGGER trg_norm_embedding_build_no_update
            BEFORE UPDATE ON norm_embedding_build
            FOR EACH ROW EXECUTE FUNCTION am_norm_chunk_no_update();
        CREATE TRIGGER trg_norm_embedding_no_update
            BEFORE UPDATE ON norm_embedding
            FOR EACH ROW EXECUTE FUNCTION am_norm_chunk_no_update();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    builds = bind.execute(text("SELECT count(*) FROM norm_embedding_build")).scalar_one()
    if builds:
        raise RuntimeError(
            f"0013_norm_embeddings downgrade refused: {builds} complete embedding build(s) "
            "would be discarded. Export them or use a forward repair; retained projections "
            "are never dropped implicitly."
        )
    op.execute("DROP TABLE norm_embedding;")
    op.execute("DROP TABLE norm_embedding_build;")
    op.execute("DROP TABLE norm_embedding_profile;")
    op.execute(
        "ALTER TABLE norm_chunk DROP CONSTRAINT uq_norm_chunk_pk_snapshot_profile;"
    )
    op.execute("DROP EXTENSION vector;")
