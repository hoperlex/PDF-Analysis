"""Add verified retrieval-set custody and certified observation citation partitions.

Revision ID: 0023_norm_citations
Revises: 0022_findings_v2

An empty citation SELECT is ambiguous on historical rows.  A nullable count is
therefore the partition certificate: NULL is legacy/unsealed, zero is an
explicitly checked empty partition, and 1..5 is checked against immutable rows
at transaction commit. This migration activates no v3 profile or served route.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0023_norm_citations"
down_revision: str | None = "0022_findings_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA = "~ '^[0-9a-f]{64}$'"
FROZEN_RUN_COLUMNS = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id'"
)
ROLE_SHAPE = (
    "(role = 'norm_source' AND target_kind = 'norm_document' "
    f"AND target_id ~ '^ndoc_{ULID}$' AND anchor_kind IN ('pdf', 'crop')) OR "
    "(role = 'norm_retrieval_set' AND target_kind = 'norm_retrieval_set' "
    f"AND target_id ~ '^nrs_{ULID}$' AND anchor_kind IN ('artifact')) OR "
    "(role = 'norm_catalogue' AND target_kind = 'norm_retrieval_set' "
    f"AND target_id ~ '^nrs_{ULID}$' AND anchor_kind IN ('artifact'))"
)
OLD_ROLE_SHAPE = (
    "(role = 'norm_source' AND target_kind = 'norm_document' "
    f"AND target_id ~ '^ndoc_{ULID}$' AND anchor_kind IN ('pdf', 'crop'))"
)
OLD_CATEGORIES = (
    "internal_contradiction", "explicit_placeholder", "dimensions", "layout",
    "facade", "roof", "documentation",
)
NORM_CATEGORIES = (
    "evacuation", "fire_safety", "accessibility", "insulation", "sound",
)
OLD_REASONS = (
    "quotation_absent", "quotation_on_different_page", "span_outside_page",
    "span_outside_block", "span_length_mismatch", "quote_in_recognised_text",
)
NEW_REASONS = (
    *OLD_REASONS, "norm_label_unknown", "norm_quote_too_short",
    "norm_quote_ambiguous", "norm_quote_absent", "norm_value_not_in_quote",
    "stated_value_not_in_evidence",
)


def _literals(values: tuple[str, ...]) -> str:
    return ", ".join("'" + value + "'" for value in values)


def _replace_check(table: str, name: str, expression: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})")


def _binding_guard(*, with_set: bool) -> None:
    target_arm = """
            ELSIF NEW.target_kind = 'norm_retrieval_set' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM norm_retrieval_set
                    WHERE norm_retrieval_set_id = NEW.target_id AND state = 'verified'
                ) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: retrieval-set target is not verified'
                        USING ERRCODE = 'AM001';
                END IF;
    """ if with_set else ""
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION am_guard_norm_custody_binding() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_admission norm_custody_admission%ROWTYPE;
            v_blob blob%ROWTYPE;
        BEGIN
            SELECT * INTO v_admission FROM norm_custody_admission
             WHERE norm_custody_admission_id = NEW.norm_custody_admission_id
             FOR KEY SHARE;
            IF NOT FOUND OR v_admission.state IS DISTINCT FROM 'confirmed' THEN
                RAISE EXCEPTION 'state_transition_not_allowed: a custody binding needs a confirmed admission'
                    USING ERRCODE = 'AM001';
            END IF;
            SELECT * INTO v_blob FROM blob WHERE blob_id = NEW.blob_id FOR KEY SHARE;
            IF NOT FOUND OR v_blob.state IS DISTINCT FROM 'available'
               OR v_blob.sha256 IS DISTINCT FROM v_admission.declared_sha256
               OR v_blob.size_bytes IS DISTINCT FROM v_admission.declared_size_bytes
               OR v_blob.media_type IS DISTINCT FROM v_admission.media_type THEN
                RAISE EXCEPTION 'state_transition_not_allowed: a custody binding needs its available, verified blob'
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.target_kind = 'norm_document' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM norm_document WHERE norm_document_id = NEW.target_id
                ) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: the custody binding target does not exist'
                        USING ERRCODE = 'AM001';
                END IF;
            {target_arm}
            ELSE
                RAISE EXCEPTION 'state_transition_not_allowed: unknown custody target kind %', NEW.target_kind
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END $fn$;
        """
    )


def _frozen_run_guard(*, with_set: bool) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    cols = FROZEN_RUN_COLUMNS + (", 'norm_retrieval_set_id'" if with_set else "")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({cols})"
    )


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE norm_retrieval_set (
            norm_retrieval_set_id text PRIMARY KEY,
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            map_sha256 text NOT NULL,
            reviewed_content_key text NOT NULL,
            chunking_profile text NOT NULL,
            embedding_profile text NOT NULL,
            builder_version text NOT NULL,
            state text NOT NULL,
            expected_set_sha256 text NOT NULL,
            observed_set_sha256 text NOT NULL,
            expected_catalogue_sha256 text NOT NULL,
            observed_catalogue_sha256 text NOT NULL,
            set_blob_id text NULL REFERENCES blob (blob_id),
            set_size_bytes bigint NULL,
            catalogue_blob_id text NULL REFERENCES blob (blob_id),
            catalogue_size_bytes bigint NULL,
            prompt_part_characters integer NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norm_retrieval_set_id CHECK
                (norm_retrieval_set_id ~ '^nrs_{ULID}$'),
            CONSTRAINT ck_norm_retrieval_set_snapshot_id CHECK
                (norms_snapshot_id ~ '^ns_{ULID}$'),
            CONSTRAINT ck_norm_retrieval_set_set_blob_id CHECK
                (set_blob_id IS NULL OR set_blob_id ~ '^blob_{ULID}$'),
            CONSTRAINT ck_norm_retrieval_set_catalogue_blob_id CHECK
                (catalogue_blob_id IS NULL OR catalogue_blob_id ~ '^blob_{ULID}$'),
            CONSTRAINT ck_norm_retrieval_set_digest CHECK
                (map_sha256 {SHA} AND expected_set_sha256 {SHA}
                 AND observed_set_sha256 {SHA} AND expected_catalogue_sha256 {SHA}
                 AND observed_catalogue_sha256 {SHA}),
            CONSTRAINT ck_norm_retrieval_set_strings CHECK
                (char_length(reviewed_content_key) BETWEEN 1 AND 240
                 AND char_length(chunking_profile) BETWEEN 1 AND 100
                 AND char_length(embedding_profile) BETWEEN 1 AND 100
                 AND char_length(builder_version) BETWEEN 1 AND 100),
            CONSTRAINT ck_norm_retrieval_set_state CHECK (state IN ('verified', 'rejected')),
            CONSTRAINT ck_norm_retrieval_set_state_shape CHECK (
                (state = 'rejected'
                 AND (expected_set_sha256 <> observed_set_sha256
                      OR expected_catalogue_sha256 <> observed_catalogue_sha256)
                 AND set_blob_id IS NULL AND set_size_bytes IS NULL
                 AND catalogue_blob_id IS NULL AND catalogue_size_bytes IS NULL)
                OR (state = 'verified' AND
                    expected_set_sha256 = observed_set_sha256
                    AND expected_catalogue_sha256 = observed_catalogue_sha256
                    AND set_blob_id IS NOT NULL AND set_size_bytes IS NOT NULL
                    AND set_size_bytes > 0
                    AND catalogue_blob_id IS NOT NULL
                    AND catalogue_size_bytes IS NOT NULL AND catalogue_size_bytes > 0
                    AND prompt_part_characters IS NOT NULL
                    AND prompt_part_characters BETWEEN 1 AND 22000
                )
            ),
            CONSTRAINT fk_norm_retrieval_set_embedding_build
                FOREIGN KEY (norms_snapshot_id, chunking_profile, embedding_profile)
                REFERENCES norm_embedding_build
                    (norms_snapshot_id, chunking_profile, embedding_profile)
        );
        CREATE UNIQUE INDEX uq_norm_retrieval_set_verified_identity
            ON norm_retrieval_set (map_sha256, norms_snapshot_id, chunking_profile,
                                   embedding_profile, builder_version)
            WHERE state = 'verified';
        CREATE TRIGGER trg_norm_retrieval_set_immutable
            BEFORE UPDATE OR DELETE ON norm_retrieval_set
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    for table in ("norm_custody_admission", "norm_custody_binding"):
        _replace_check(table, "ck_norm_custody_role_shape", ROLE_SHAPE)
    _binding_guard(with_set=True)
    op.execute(
        """
        CREATE FUNCTION am_verify_norm_retrieval_set() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            set_role_count integer;
            catalogue_role_count integer;
            source_key text;
            complete_build boolean;
        BEGIN
            IF NEW.state <> 'verified' THEN RETURN NULL; END IF;
            SELECT content_key INTO source_key FROM norms_snapshot
                WHERE norms_snapshot_id = NEW.norms_snapshot_id;
            IF source_key IS DISTINCT FROM NEW.reviewed_content_key THEN
                RAISE EXCEPTION 'state_transition_not_allowed: reviewed snapshot content key differs'
                    USING ERRCODE = 'AM001';
            END IF;
            SELECT EXISTS (
                SELECT 1 FROM norm_chunk_build cb
                JOIN norm_embedding_build eb
                  ON eb.norms_snapshot_id = cb.norms_snapshot_id
                 AND eb.chunking_profile = cb.chunking_profile
                 AND eb.embedding_profile = NEW.embedding_profile
               WHERE cb.norms_snapshot_id = NEW.norms_snapshot_id
                 AND cb.chunking_profile = NEW.chunking_profile
                 AND cb.chunk_count > 0
                 AND eb.chunk_count = cb.chunk_count
                 AND eb.window_count >= eb.chunk_count
                 AND (SELECT count(*) FROM norm_chunk c
                       WHERE c.norms_snapshot_id = cb.norms_snapshot_id
                         AND c.chunking_profile = cb.chunking_profile) = cb.chunk_count
                 AND (SELECT count(*) FROM norm_embedding e
                       WHERE e.norms_snapshot_id = cb.norms_snapshot_id
                         AND e.chunking_profile = cb.chunking_profile
                         AND e.embedding_profile = eb.embedding_profile) = eb.window_count
                 AND (SELECT count(DISTINCT e.norm_chunk_pk) FROM norm_embedding e
                       WHERE e.norms_snapshot_id = cb.norms_snapshot_id
                         AND e.chunking_profile = cb.chunking_profile
                         AND e.embedding_profile = eb.embedding_profile) = cb.chunk_count
            ) INTO complete_build;
            IF NOT complete_build THEN
                RAISE EXCEPTION 'state_transition_not_allowed: verified set needs a complete vector build'
                    USING ERRCODE = 'AM001';
            END IF;
            SELECT count(*) FILTER (
                       WHERE b.role = 'norm_retrieval_set'
                         AND b.blob_id = NEW.set_blob_id
                         AND x.sha256 = NEW.observed_set_sha256
                         AND x.size_bytes = NEW.set_size_bytes),
                   count(*) FILTER (
                       WHERE b.role = 'norm_catalogue'
                         AND b.blob_id = NEW.catalogue_blob_id
                         AND x.sha256 = NEW.observed_catalogue_sha256
                         AND x.size_bytes = NEW.catalogue_size_bytes)
              INTO set_role_count, catalogue_role_count
              FROM norm_custody_binding b JOIN blob x ON x.blob_id = b.blob_id
             WHERE b.target_kind = 'norm_retrieval_set'
               AND b.target_id = NEW.norm_retrieval_set_id;
            IF set_role_count <> 1 OR catalogue_role_count <> 1 OR
               (SELECT count(*) FROM norm_custody_binding b
                 WHERE b.target_kind = 'norm_retrieval_set'
                   AND b.target_id = NEW.norm_retrieval_set_id) <> 2 THEN
                RAISE EXCEPTION 'state_transition_not_allowed: verified set needs both exact confirmed custody bindings'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NULL;
        END $fn$;
        CREATE CONSTRAINT TRIGGER trg_norm_retrieval_set_verified
            AFTER INSERT ON norm_retrieval_set DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_verify_norm_retrieval_set();
        """
    )

    op.execute(
        "ALTER TABLE audit_run ADD COLUMN norm_retrieval_set_id text NULL "
        "REFERENCES norm_retrieval_set (norm_retrieval_set_id)"
    )
    op.execute(
        f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_norm_retrieval_set_id "
        f"CHECK (norm_retrieval_set_id IS NULL OR norm_retrieval_set_id ~ '^nrs_{ULID}$')"
    )
    # 0022 introduced this frozen identity reference without its direct format
    # CHECK. Add the forward guard here; do not rewrite the published migration.
    op.execute(
        f"ALTER TABLE finding ADD CONSTRAINT ck_finding_canonical_observation_id "
        f"CHECK (canonical_observation_id IS NULL OR "
        f"canonical_observation_id ~ '^fobs_{ULID}$')"
    )
    _frozen_run_guard(with_set=True)
    op.execute(
        """
        CREATE FUNCTION am_verify_run_norm_set() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.norm_retrieval_set_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM norm_retrieval_set s
                WHERE s.norm_retrieval_set_id = NEW.norm_retrieval_set_id
                  AND s.norms_snapshot_id = NEW.norms_snapshot_id
                  AND s.state = 'verified'
            ) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: run needs a verified set of its pinned snapshot'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END $fn$;
        CREATE TRIGGER trg_audit_run_norm_set
            BEFORE INSERT OR UPDATE OF norm_retrieval_set_id, norms_snapshot_id ON audit_run
            FOR EACH ROW EXECUTE FUNCTION am_verify_run_norm_set();
        """
    )

    categories = _literals((*OLD_CATEGORIES, *NORM_CATEGORIES))
    for table in ("finding", "finding_observation"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({categories})")
    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_literals(NEW_REASONS)})",
    )
    op.execute(
        """
        ALTER TABLE finding_observation
            ADD COLUMN required_value text NULL,
            ADD COLUMN stated_value text NULL,
            ADD COLUMN norm_citation_count integer NULL;
        ALTER TABLE finding_observation
            ADD CONSTRAINT ck_finding_observation_norm_values CHECK (
                (required_value IS NULL) = (stated_value IS NULL)
                AND (required_value IS NULL OR char_length(required_value) BETWEEN 1 AND 200)
                AND (stated_value IS NULL OR char_length(stated_value) BETWEEN 1 AND 200)
            ),
            ADD CONSTRAINT ck_finding_observation_norm_partition CHECK (
                norm_citation_count IS NULL OR
                (grounded AND finding_uid IS NOT NULL AND norm_citation_count BETWEEN 0 AND 5)
            );
        """
    )
    op.execute(
        f"""
        ALTER TABLE finding_observation
            ADD CONSTRAINT ck_finding_observation_norm_category_shape CHECK (
                (category IN ({_literals(NORM_CATEGORIES)}) AND
                    (NOT grounded OR
                     (norm_citation_count IS NOT NULL
                      AND norm_citation_count BETWEEN 1 AND 5
                      AND required_value IS NOT NULL)))
                OR
                (category NOT IN ({_literals(NORM_CATEGORIES)}) AND
                    (norm_citation_count IS NULL OR norm_citation_count = 0) AND
                    required_value IS NULL AND stated_value IS NULL)
            );
        CREATE TABLE finding_observation_norm_citation (
            finding_observation_id text NOT NULL
                REFERENCES finding_observation (finding_observation_id),
            citation_ordinal integer NOT NULL,
            run_id text NOT NULL REFERENCES audit_run (run_id),
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            norm_retrieval_set_id text NOT NULL
                REFERENCES norm_retrieval_set (norm_retrieval_set_id),
            norm_document_id text NOT NULL REFERENCES norm_document (norm_document_id),
            norm_paragraph_id text NOT NULL REFERENCES norm_paragraph (norm_paragraph_id),
            quote text NOT NULL,
            char_start integer NOT NULL,
            char_length integer NOT NULL,
            state text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_finding_observation_norm_citation
                PRIMARY KEY (finding_observation_id, citation_ordinal),
            CONSTRAINT ck_finding_observation_norm_citation_ids CHECK (
                finding_observation_id ~ '^fobs_{ULID}$'
                AND run_id ~ '^run_{ULID}$'
                AND norms_snapshot_id ~ '^ns_{ULID}$'
                AND norm_retrieval_set_id ~ '^nrs_{ULID}$'
                AND norm_document_id ~ '^ndoc_{ULID}$'
                AND norm_paragraph_id ~ '^npar_{ULID}$'
            ),
            CONSTRAINT ck_finding_observation_norm_citation_ordinal
                CHECK (citation_ordinal BETWEEN 1 AND 5),
            CONSTRAINT ck_finding_observation_norm_citation_quote
                CHECK (char_length(quote) BETWEEN 20 AND 4000
                       AND char_length = char_length(quote) AND char_start >= 0),
            CONSTRAINT ck_finding_observation_norm_citation_state
                CHECK (state IN ('verified', 'rebound'))
        );
        CREATE TRIGGER trg_finding_observation_norm_citation_immutable
            BEFORE UPDATE OR DELETE ON finding_observation_norm_citation
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_verify_norm_citation() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            observed_run text;
            observed_count integer;
            pinned_snapshot text;
            pinned_set text;
            paragraph_snapshot text;
            paragraph_document text;
            paragraph_text text;
            paragraph_reliability text;
        BEGIN
            SELECT run_id, norm_citation_count INTO observed_run, observed_count
              FROM finding_observation
             WHERE finding_observation_id = NEW.finding_observation_id;
            SELECT norms_snapshot_id, norm_retrieval_set_id
              INTO pinned_snapshot, pinned_set FROM audit_run WHERE run_id = NEW.run_id;
            SELECT p.norms_snapshot_id, d.norm_document_id, p.text, p.text_reliability
              INTO paragraph_snapshot, paragraph_document, paragraph_text, paragraph_reliability
              FROM norm_paragraph p
              JOIN norm_document d ON d.norm_document_pk = p.norm_document_pk
             WHERE p.norm_paragraph_id = NEW.norm_paragraph_id;
            IF observed_run IS DISTINCT FROM NEW.run_id OR observed_count IS NULL
               OR pinned_snapshot IS DISTINCT FROM NEW.norms_snapshot_id
               OR pinned_set IS DISTINCT FROM NEW.norm_retrieval_set_id
               OR paragraph_snapshot IS DISTINCT FROM NEW.norms_snapshot_id
               OR paragraph_document IS DISTINCT FROM NEW.norm_document_id
               OR paragraph_reliability IS DISTINCT FROM 'reliable'
               OR substr(paragraph_text, NEW.char_start + 1, NEW.char_length)
                    IS DISTINCT FROM NEW.quote THEN
                RAISE EXCEPTION 'state_transition_not_allowed: citation is outside the verified run/paragraph/quote'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END $fn$;
        CREATE TRIGGER trg_finding_observation_norm_citation_guard
            BEFORE INSERT ON finding_observation_norm_citation
            FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation();

        CREATE FUNCTION am_verify_norm_citation_partition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            observation_id text;
            observation_run text;
            certified_count integer;
            actual_count integer;
        BEGIN
            observation_id := NEW.finding_observation_id;
            SELECT run_id, norm_citation_count INTO observation_run, certified_count
              FROM finding_observation
             WHERE finding_observation_id = observation_id;
            SELECT count(*) INTO actual_count FROM finding_observation_norm_citation
             WHERE finding_observation_id = observation_id;
            IF (certified_count IS NULL AND actual_count <> 0)
               OR (certified_count IS NOT NULL AND certified_count <> actual_count) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: citation partition count mismatch'
                    USING ERRCODE = 'AM001';
            END IF;
            IF certified_count IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM audit_run r
                JOIN norm_retrieval_set s
                  ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
                 AND s.norms_snapshot_id = r.norms_snapshot_id
                 AND s.state = 'verified'
                JOIN stage_result st ON st.run_id = r.run_id
                 AND st.stage_id = 'norm_verification' AND st.status = 'succeeded'
                WHERE r.run_id = observation_run
            ) THEN
                RAISE EXCEPTION 'state_transition_not_allowed: certified citation partition needs succeeded CITE stage and pinned verified set'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NULL;
        END $fn$;
        CREATE CONSTRAINT TRIGGER trg_finding_observation_partition
            AFTER INSERT ON finding_observation DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation_partition();
        CREATE CONSTRAINT TRIGGER trg_norm_citation_partition
            AFTER INSERT ON finding_observation_norm_citation DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation_partition();
        """
    )


def downgrade() -> None:
    retained = op.get_bind().execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM norm_retrieval_set UNION ALL "
            "SELECT 1 FROM finding_observation_norm_citation UNION ALL "
            "SELECT 1 FROM audit_run WHERE norm_retrieval_set_id IS NOT NULL UNION ALL "
            "SELECT 1 FROM finding_observation WHERE norm_citation_count IS NOT NULL "
            "OR required_value IS NOT NULL OR stated_value IS NOT NULL UNION ALL "
            "SELECT 1 FROM finding WHERE category IN ('evacuation','fire_safety',"
            "'accessibility','insulation','sound') UNION ALL "
            "SELECT 1 FROM finding_observation WHERE category IN ('evacuation','fire_safety',"
            "'accessibility','insulation','sound') UNION ALL "
            "SELECT 1 FROM finding_observation WHERE ungrounded_reason IN "
            "('norm_label_unknown','norm_quote_too_short','norm_quote_ambiguous',"
            "'norm_quote_absent','norm_value_not_in_quote','stated_value_not_in_evidence') "
            "UNION ALL SELECT 1 FROM norm_custody_admission "
            "WHERE role IN ('norm_retrieval_set','norm_catalogue'))"
        )
    ).scalar_one()
    if retained:
        raise RuntimeError("0023 downgrade refused: retained retrieval set, citation or v3 data")
    op.execute("DROP TRIGGER trg_finding_observation_partition ON finding_observation")
    op.execute("DROP TABLE finding_observation_norm_citation")
    op.execute("DROP FUNCTION am_verify_norm_citation_partition()")
    op.execute("DROP FUNCTION am_verify_norm_citation()")
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_norm_category_shape")
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_norm_partition")
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_norm_values")
    op.execute("ALTER TABLE finding_observation DROP COLUMN norm_citation_count")
    op.execute("ALTER TABLE finding_observation DROP COLUMN required_value")
    op.execute("ALTER TABLE finding_observation DROP COLUMN stated_value")
    for table in ("finding", "finding_observation"):
        _replace_check(table, f"ck_{table}_category", f"category IN ({_literals(OLD_CATEGORIES)})")
    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_literals(OLD_REASONS)})",
    )
    op.execute("DROP TRIGGER trg_audit_run_norm_set ON audit_run")
    op.execute("DROP FUNCTION am_verify_run_norm_set()")
    op.execute("ALTER TABLE finding DROP CONSTRAINT ck_finding_canonical_observation_id")
    _frozen_run_guard(with_set=False)
    op.execute("ALTER TABLE audit_run DROP COLUMN norm_retrieval_set_id")
    _binding_guard(with_set=False)
    for table in ("norm_custody_admission", "norm_custody_binding"):
        _replace_check(table, "ck_norm_custody_role_shape", OLD_ROLE_SHAPE)
    op.execute("DROP TABLE norm_retrieval_set")
    op.execute("DROP FUNCTION am_verify_norm_retrieval_set()")
