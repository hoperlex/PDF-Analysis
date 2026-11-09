"""0059 -- the expert decision memory: the capture core (`DECISION-MEMORY-01` phases M0 and M1, `ADR-0027`).

When an expert decides a finding, the decision is copied -- in the ledger's own transaction -- into a **case** that holds what the
expert saw and said: the finding text, the evidence quotes with their page geometry, the normative references and a reference to each
portal crop image that belongs to the pages the evidence names. The ledger stays the authority while its source exists; the case is the
only remaining copy of the *context* once the project or the document is erased, so **no table here has a foreign key into a project,
a document, a finding or the ledger** (the project erase's foreign-key closure cannot reach the memory, and the purge classifies every
table `KEEP`). The only foreign keys are between memory tables, to `blob` (a crop is a binding to an existing Blob, never a byte copy
-- a Blob's identity is derived from its bytes) and, for the status events, to `command_record`.

``decision_memory_case``
    One row per reviewed observation (``UNIQUE (origin_observation_id)``, so capture is idempotent): where it came from (identities that
    resolve nowhere after an erase), its category, the section **as of capture**, ``data_class`` (``test`` or ``real``), whether any crop
    was available, and a SHA-256 over the observation's immutable content.
``decision_memory_decision``
    One row per captured ledger event (``UNIQUE (source_decision_id)``): ``accept`` or ``reject`` (a ``comment`` is not captured --
    `Q8`), the verdict, the optional severity of an accept, the author as an opaque ``user_uid`` **without a foreign key** (`Q7`:
    ``purgeUser`` stays possible), and ``origin_kind`` (``direct``, ``carried``, ``imported``).
``decision_memory_decision_text``
    The expert's comment, per decision (the expert's own words; may quote the document).
``decision_memory_status_event``
    Table only: ``withdraw``, ``restore`` and ``forget`` events with a closed ``reason_code``. No operation writes it before phase M2.
    The actor is an account identity with its format check and, deliberately for now, **no foreign key** to ``app_user``: the key and
    its entry in ``access/references.py`` arrive with the operations that write the table (`D-393`).
``decision_memory_content`` / ``_evidence`` / ``_norm_ref`` / ``_crop``
    The case content, keyed ``(case_id, revision)`` with ``revision`` 1 in v1: the finding and its provenance classifiers, the evidence
    items and their geometry, the normative references (ids and the quoted norm text) and the crop references (at most four per case,
    ``crop_ordinal`` 1..4, with the rule that selected them).

Every table is append-only (``am_immutable_row``, `ADR-0027` decision 5). Phase M2 replaces the guard of the four content tables with
the forget guard (`DECISION-MEMORY-01` section 4.5); phase M3 gives the crop table its state column and guard. Not here: embeddings,
probes, exports, renders (M3-M5).

The downgrade refuses while any memory row exists: a populated memory is restored from a backup, never dropped silently.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0059_decision_memory"
down_revision: str | None = "0058_finding_decision_origin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
_SEVERITIES = "'critical', 'economic', 'operational', 'recommendation', 'check_adjacent'"

#: Creation order; the downgrade drops in the reverse.
TABLES: tuple[str, ...] = (
    "decision_memory_case",
    "decision_memory_decision",
    "decision_memory_decision_text",
    "decision_memory_status_event",
    "decision_memory_content",
    "decision_memory_evidence",
    "decision_memory_norm_ref",
    "decision_memory_crop",
)


def _id(column: str, prefix: str, table: str, *, nullable: bool = False) -> str:
    """A column with its identity-format CHECK, named ``ck_<table>_<column>_format``."""
    check = f"{column} IS NULL OR {column} ~ '^{prefix}_{ULID}$'" if nullable else f"{column} ~ '^{prefix}_{ULID}$'"
    return (
        f"{column} text {'NULL' if nullable else 'NOT NULL'} "
        f"CONSTRAINT ck_{table}_{column}_format CHECK ({check})"
    )


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE decision_memory_case (
            case_id text PRIMARY KEY
                CONSTRAINT ck_decision_memory_case_case_id_format CHECK (case_id ~ '^dmc_{ULID}$'),
            {_id("origin_observation_id", "fobs", "decision_memory_case")}
                CONSTRAINT uq_decision_memory_case_origin_observation UNIQUE,
            {_id("origin_finding_uid", "fnd", "decision_memory_case")},
            {_id("origin_project_uid", "prj", "decision_memory_case")},
            {_id("origin_document_uid", "doc", "decision_memory_case")},
            {_id("origin_version_uid", "ver", "decision_memory_case")},
            {_id("origin_run_id", "run", "decision_memory_case")},
            category text NOT NULL
                CONSTRAINT ck_decision_memory_case_category CHECK (char_length(category) BETWEEN 1 AND 64),
            section_code text NULL
                CONSTRAINT ck_decision_memory_case_section_code
                    CHECK (section_code IS NULL OR char_length(section_code) BETWEEN 1 AND 64),
            data_class text NOT NULL
                CONSTRAINT ck_decision_memory_case_data_class CHECK (data_class IN ('test', 'real')),
            crop_state text NOT NULL
                CONSTRAINT ck_decision_memory_case_crop_state CHECK (crop_state IN ('referenced', 'none_available')),
            capture_version text NOT NULL
                CONSTRAINT ck_decision_memory_case_capture_version CHECK (char_length(capture_version) BETWEEN 1 AND 32),
            content_sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_case_content_sha256 CHECK (content_sha256 ~ '^[0-9a-f]{{64}}$'),
            captured_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_case_origin_project ON decision_memory_case (origin_project_uid)")
    op.execute("CREATE INDEX ix_decision_memory_case_section_category ON decision_memory_case (section_code, category)")

    op.execute(f"""
        CREATE TABLE decision_memory_decision (
            memory_decision_id text PRIMARY KEY
                CONSTRAINT ck_decision_memory_decision_memory_decision_id_format
                    CHECK (memory_decision_id ~ '^dmd_{ULID}$'),
            {_id("case_id", "dmc", "decision_memory_decision")}
                CONSTRAINT fk_decision_memory_decision_case
                    REFERENCES decision_memory_case (case_id) ON DELETE RESTRICT,
            {_id("source_decision_id", "dec", "decision_memory_decision")}
                CONSTRAINT uq_decision_memory_decision_source UNIQUE,
            event_type text NOT NULL
                CONSTRAINT ck_decision_memory_decision_event_type CHECK (event_type IN ('accept', 'reject')),
            verdict text NOT NULL
                CONSTRAINT ck_decision_memory_decision_verdict CHECK (verdict IN ('accepted', 'rejected')),
            severity text NULL
                CONSTRAINT ck_decision_memory_decision_severity
                    CHECK (severity IS NULL OR severity IN ({_SEVERITIES})),
            author_user_uid text NULL
                CONSTRAINT ck_decision_memory_decision_author_user_uid_format
                    CHECK (author_user_uid IS NULL OR author_user_uid ~ '^usr_{ULID}$'),
            origin_kind text NOT NULL
                CONSTRAINT ck_decision_memory_decision_origin_kind
                    CHECK (origin_kind IN ('direct', 'carried', 'imported')),
            decided_at timestamptz NOT NULL,
            captured_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_decision_memory_decision_verdict_matches_event
                CHECK (verdict = CASE event_type WHEN 'accept' THEN 'accepted' ELSE 'rejected' END),
            CONSTRAINT ck_decision_memory_decision_severity_accept_only
                CHECK (severity IS NULL OR event_type = 'accept')
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_decision_case ON decision_memory_decision (case_id, decided_at)")

    op.execute(f"""
        CREATE TABLE decision_memory_decision_text (
            memory_decision_id text PRIMARY KEY
                CONSTRAINT fk_decision_memory_decision_text_decision
                    REFERENCES decision_memory_decision (memory_decision_id) ON DELETE RESTRICT
                CONSTRAINT ck_decision_memory_decision_text_memory_decision_id_format
                    CHECK (memory_decision_id ~ '^dmd_{ULID}$'),
            comment text NULL
                CONSTRAINT ck_decision_memory_decision_text_comment
                    CHECK (comment IS NULL OR char_length(comment) BETWEEN 1 AND 4000)
        )
    """)

    op.execute(f"""
        CREATE TABLE decision_memory_status_event (
            status_event_id text PRIMARY KEY
                CONSTRAINT ck_decision_memory_status_event_status_event_id_format
                    CHECK (status_event_id ~ '^dmw_{ULID}$'),
            {_id("case_id", "dmc", "decision_memory_status_event")}
                CONSTRAINT fk_decision_memory_status_event_case
                    REFERENCES decision_memory_case (case_id) ON DELETE RESTRICT,
            kind text NOT NULL
                CONSTRAINT ck_decision_memory_status_event_kind CHECK (kind IN ('withdraw', 'restore', 'forget')),
            reason_code text NOT NULL
                CONSTRAINT ck_decision_memory_status_event_reason_code
                    CHECK (reason_code IN ('capture_defect', 'wrong_decision', 'client_request', 'test_data', 'other')),
            {_id("actor_user_uid", "usr", "decision_memory_status_event")},
            {_id("command_id", "cmd", "decision_memory_status_event", nullable=True)}
                CONSTRAINT fk_decision_memory_status_event_command
                    REFERENCES command_record (command_id) ON DELETE RESTRICT,
            owner_permission_ref text NULL
                CONSTRAINT ck_decision_memory_status_event_owner_permission_ref
                    CHECK (owner_permission_ref IS NULL OR char_length(owner_permission_ref) BETWEEN 1 AND 200),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_decision_memory_status_event_forget_permission
                CHECK ((kind = 'forget') = (owner_permission_ref IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_status_event_case ON decision_memory_status_event (case_id, created_at)")

    op.execute(f"""
        CREATE TABLE decision_memory_content (
            {_id("case_id", "dmc", "decision_memory_content")}
                CONSTRAINT fk_decision_memory_content_case
                    REFERENCES decision_memory_case (case_id) ON DELETE RESTRICT,
            revision integer NOT NULL
                CONSTRAINT ck_decision_memory_content_revision CHECK (revision >= 1),
            finding_text text NOT NULL
                CONSTRAINT ck_decision_memory_content_finding_text CHECK (char_length(finding_text) BETWEEN 1 AND 4000),
            recommendation_text text NOT NULL
                CONSTRAINT ck_decision_memory_content_recommendation_text
                    CHECK (char_length(recommendation_text) BETWEEN 1 AND 4000),
            proposed_severity text NULL
                CONSTRAINT ck_decision_memory_content_proposed_severity
                    CHECK (proposed_severity IS NULL OR proposed_severity IN ({_SEVERITIES})),
            required_value text NULL,
            stated_value text NULL,
            stage_id text NOT NULL
                CONSTRAINT ck_decision_memory_content_stage_id CHECK (char_length(stage_id) BETWEEN 1 AND 64),
            {_id("analysis_profile_id", "ap", "decision_memory_content")},
            {_id("prompt_bundle_id", "pb", "decision_memory_content")},
            provider_mode text NOT NULL
                CONSTRAINT ck_decision_memory_content_provider_mode CHECK (provider_mode IN ('live', 'recorded')),
            CONSTRAINT pk_decision_memory_content PRIMARY KEY (case_id, revision),
            CONSTRAINT ck_decision_memory_content_values
                CHECK ((required_value IS NULL) = (stated_value IS NULL)
                       AND (required_value IS NULL OR char_length(required_value) BETWEEN 1 AND 200)
                       AND (stated_value IS NULL OR char_length(stated_value) BETWEEN 1 AND 200))
        )
    """)

    op.execute("""
        CREATE TABLE decision_memory_evidence (
            case_id text NOT NULL,
            revision integer NOT NULL,
            ordinal integer NOT NULL
                CONSTRAINT ck_decision_memory_evidence_ordinal CHECK (ordinal >= 0),
            page_number integer NOT NULL
                CONSTRAINT ck_decision_memory_evidence_page_number CHECK (page_number >= 1),
            quote text NOT NULL
                CONSTRAINT ck_decision_memory_evidence_quote CHECK (char_length(quote) BETWEEN 1 AND 2000),
            char_start integer NOT NULL,
            char_end integer NOT NULL,
            block_ref text NULL
                CONSTRAINT ck_decision_memory_evidence_block_ref CHECK (block_ref IS NULL OR block_ref ~ '^b_[0-9]{6}$'),
            bbox_x0 double precision NULL,
            bbox_y0 double precision NULL,
            bbox_x1 double precision NULL,
            bbox_y1 double precision NULL,
            bbox_unit text NULL
                CONSTRAINT ck_decision_memory_evidence_bbox_unit
                    CHECK (bbox_unit IS NULL OR char_length(bbox_unit) BETWEEN 1 AND 32),
            bbox_origin text NULL
                CONSTRAINT ck_decision_memory_evidence_bbox_origin
                    CHECK (bbox_origin IS NULL OR char_length(bbox_origin) BETWEEN 1 AND 32),
            CONSTRAINT pk_decision_memory_evidence PRIMARY KEY (case_id, revision, ordinal),
            CONSTRAINT fk_decision_memory_evidence_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT,
            CONSTRAINT ck_decision_memory_evidence_span
                CHECK (char_start >= 0 AND char_end > char_start AND char_end - char_start = char_length(quote)),
            CONSTRAINT ck_decision_memory_evidence_bbox_whole
                CHECK ((bbox_x0 IS NULL) = (bbox_y0 IS NULL) AND (bbox_x0 IS NULL) = (bbox_x1 IS NULL)
                       AND (bbox_x0 IS NULL) = (bbox_y1 IS NULL) AND (bbox_x0 IS NULL) = (bbox_unit IS NULL)
                       AND (bbox_x0 IS NULL) = (bbox_origin IS NULL))
        )
    """)
    op.execute(f"""
        ALTER TABLE decision_memory_evidence
            ADD CONSTRAINT ck_decision_memory_evidence_case_id_format CHECK (case_id ~ '^dmc_{ULID}$')
    """)

    op.execute(f"""
        CREATE TABLE decision_memory_norm_ref (
            case_id text NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_case_id_format CHECK (case_id ~ '^dmc_{ULID}$'),
            revision integer NOT NULL,
            ordinal integer NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_ordinal CHECK (ordinal BETWEEN 1 AND 5),
            {_id("norms_snapshot_id", "ns", "decision_memory_norm_ref")},
            {_id("norm_document_id", "ndoc", "decision_memory_norm_ref")},
            {_id("norm_paragraph_id", "npar", "decision_memory_norm_ref")},
            designation text NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_designation CHECK (char_length(designation) BETWEEN 1 AND 512),
            clause_number text NULL
                CONSTRAINT ck_decision_memory_norm_ref_clause_number
                    CHECK (clause_number IS NULL OR char_length(clause_number) BETWEEN 1 AND 128),
            page_label integer NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_page_label CHECK (page_label >= 1),
            quote text NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_quote CHECK (char_length(quote) BETWEEN 20 AND 4000),
            citation_state text NOT NULL
                CONSTRAINT ck_decision_memory_norm_ref_citation_state CHECK (citation_state IN ('verified', 'rebound')),
            CONSTRAINT pk_decision_memory_norm_ref PRIMARY KEY (case_id, revision, ordinal),
            CONSTRAINT fk_decision_memory_norm_ref_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT
        )
    """)

    op.execute(f"""
        CREATE TABLE decision_memory_crop (
            crop_id text PRIMARY KEY
                CONSTRAINT ck_decision_memory_crop_crop_id_format CHECK (crop_id ~ '^dmx_{ULID}$'),
            case_id text NOT NULL
                CONSTRAINT ck_decision_memory_crop_case_id_format CHECK (case_id ~ '^dmc_{ULID}$'),
            revision integer NOT NULL,
            crop_ordinal integer NOT NULL
                CONSTRAINT ck_decision_memory_crop_crop_ordinal CHECK (crop_ordinal BETWEEN 1 AND 4),
            evidence_ordinal integer NULL
                CONSTRAINT ck_decision_memory_crop_evidence_ordinal CHECK (evidence_ordinal IS NULL OR evidence_ordinal >= 0),
            kind text NOT NULL
                CONSTRAINT ck_decision_memory_crop_kind CHECK (kind = 'portal_image_block'),
            selection_rule text NOT NULL
                CONSTRAINT ck_decision_memory_crop_selection_rule CHECK (char_length(selection_rule) BETWEEN 1 AND 64),
            page_number integer NOT NULL
                CONSTRAINT ck_decision_memory_crop_page_number CHECK (page_number >= 1),
            bbox_x0 double precision NOT NULL,
            bbox_y0 double precision NOT NULL,
            bbox_x1 double precision NOT NULL,
            bbox_y1 double precision NOT NULL,
            {_id("blob_id", "blob", "decision_memory_crop")}
                CONSTRAINT fk_decision_memory_crop_blob REFERENCES blob (blob_id) ON DELETE RESTRICT,
            sha256 text NOT NULL
                CONSTRAINT ck_decision_memory_crop_sha256 CHECK (sha256 ~ '^[0-9a-f]{{64}}$'),
            size_bytes bigint NOT NULL
                CONSTRAINT ck_decision_memory_crop_size_bytes CHECK (size_bytes >= 1),
            media_type text NOT NULL
                CONSTRAINT ck_decision_memory_crop_media_type CHECK (media_type = 'image/png'),
            width_px integer NOT NULL
                CONSTRAINT ck_decision_memory_crop_width_px CHECK (width_px >= 1),
            height_px integer NOT NULL
                CONSTRAINT ck_decision_memory_crop_height_px CHECK (height_px >= 1),
            source_ref text NOT NULL
                CONSTRAINT ck_decision_memory_crop_source_ref CHECK (source_ref ~ '^blk_[0-9a-f]{{32}}$'),
            portal_description text NULL
                CONSTRAINT ck_decision_memory_crop_portal_description
                    CHECK (portal_description IS NULL OR char_length(portal_description) BETWEEN 1 AND 4000),
            CONSTRAINT fk_decision_memory_crop_content FOREIGN KEY (case_id, revision)
                REFERENCES decision_memory_content (case_id, revision) ON DELETE RESTRICT,
            CONSTRAINT uq_decision_memory_crop_ordinal UNIQUE (case_id, revision, crop_ordinal),
            CONSTRAINT uq_decision_memory_crop_source UNIQUE (case_id, revision, source_ref),
            CONSTRAINT ck_decision_memory_crop_bbox
                CHECK (bbox_x0 >= 0 AND bbox_y0 >= 0 AND bbox_x1 <= 1 AND bbox_y1 <= 1
                       AND bbox_x1 > bbox_x0 AND bbox_y1 > bbox_y0)
        )
    """)
    op.execute("CREATE INDEX ix_decision_memory_crop_blob ON decision_memory_crop (blob_id)")

    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    op.execute(
        "COMMENT ON TABLE decision_memory_case IS "
        "'ADR-0027: one reviewed observation, captured in the transaction of the first decision on it. The case content is a "
        "primary record that outlives its project and document: no column here is a foreign key into a project, document, "
        "finding or the ledger, so an erase or a purge cannot reach it. Append-only.';"
    )
    op.execute(
        "COMMENT ON COLUMN decision_memory_case.data_class IS "
        "'test or real, fixed at capture. Every case captured before the installation setting of phase M2 is test.';"
    )
    op.execute(
        "COMMENT ON COLUMN decision_memory_decision.author_user_uid IS "
        "'Q7: an opaque account identity with no foreign key, so purgeUser stays possible. NULL: the ledger event had no account.';"
    )


def downgrade() -> None:
    populated = " OR ".join(f"EXISTS (SELECT 1 FROM {table})" for table in TABLES)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF {populated} THEN
                RAISE EXCEPTION
                    'the decision memory holds rows (ADR-0027: the case content is a primary record that outlives its '
                    'source); restore it from a backup instead of downgrading 0059';
            END IF;
        END
        $$;
        """
    )
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
