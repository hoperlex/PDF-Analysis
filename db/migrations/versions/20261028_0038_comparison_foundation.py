"""The comparison foundation: upload batches, version orders, page profiles, the comparison queue and its spend journal.

Revision ID: 0038_comparison_foundation
Revises: 0037_analysis_presets

`CMP-SEAL-C0` (wave C0 of `COMPARE-MODULES-PLAN`, `ADR-0025`). It creates the tables the C0 lanes
(`CMP-WORK-01`, `CMP-SPEND-01`, `CMP-STORAGE-PARTS-01`, `CMP-EXEC-IMAGES-01`, `CMP-INGEST-ZIP-01`,
`CMP-INGEST-01`, `CMP-INGEST-02`, `CMP-PROFILE-01`, `CMP-VERSION-MARK-01`) implement against, and
nothing that implements them: no row is written and no behaviour changes. Every table is reachable
from ``project`` by foreign keys, so the project erase keeps its closure (decision 7).

Tables (nine; the plan names eight, and the ninth is the upload *set*, see below)
---------------------------------------------------------------------------------
``comparison_upload`` (``cbt_``) -- one upload batch of plain PDFs for comparison. The files are
declared before the first byte (count, bytes, pages); the limits of decision 9 are refused by the
application before the first part, and are not restated here because the owner may revise them
(`CMP-MEASURE-01`).

``comparison_upload_set`` (``cus_``) -- one proposed document set of a batch (the original's batch
*item*): its designation (the «шифр», metadata an expert confirms, never an identity), the proposal,
the stage and section, and its own state (``uploading`` ... ``done``). The plan's task list names
eight tables; a set needs a durable opaque identity and a state of its own for «confirm / exclude /
retry a set» and «pause after the current set», and ADR-0025 decision 10 names "the item id" as a
resume and grouping identity, so it is a table and not a column of the files.

``comparison_upload_file`` (``cuf_``) -- one declared file: a display name (a hint, never an
identity), the declared size and SHA-256 (checked at completion), the opaque multipart token
(persisted before the first part and write-once) and the published blob once verified.

``comparison_upload_part`` -- one chunk of one file, keyed by ``(file, part_number)`` (a part is
never referenced from elsewhere, so it has no identity of its own). A part row exists before its bytes
are staged ("a chunk has a database owner before its bytes are staged", decision 10), and a trigger
refuses a part for a file whose multipart token has not been persisted.

``comparison_version_order`` (``cvo_``) -- the append-only revisions of the order in which the
versions of a document set are compared (decisions 14 and 16). It never changes the documents'
``version_ordinal`` (`D-5`). A chain trigger numbers the revisions without a gap and checks that every
listed version belongs to the document.

``comparison_page_profile`` (``cpr_``) -- the raw deterministic profile of one page of one version, a
content-keyed row (a ULID id *and* a unique content-key digest, decision 2): the same digest is never a
foreign key. It holds the small summary and references the stored profile, preview and thumbnail blobs;
a blob reference is write-once.

``comparison_work`` (``cq_``) and ``comparison_work_attempt`` (``cqa_``) -- the durable comparison-local
queue (decision 4): the Lease pattern of ``job`` and ``attempt`` (expiry, heartbeat, attempt count,
pause, cancel, reclaim) without ``run_id``. They have **no foreign key to** ``job``, ``attempt`` **or**
``audit_run`` (a Job is a Run in the schema), and their non-terminal states are the ones the project
erase refuses on (decision 7).

``comparison_model_call`` (``cmc_``) -- the comparison spend journal (decision 5): ``prepared -> sent ->
completed | failed | unknown``. A row can only be **inserted** ``prepared`` (a trigger), so the pre-call
breadcrumb exists before any provider call; a row that is ``prepared`` or ``sent`` at reclaim is never
sent again and ends ``unknown``. Its cost columns are those of ``comparison_summary`` (``0035``).

Other changes
-------------
``document_version.upload_kind`` (``portal_bundle`` | ``comparison_pdf``, default ``portal_bundle``), and a
comparison-only version holds no portal bundle counts. ``executor_task`` gains the origin
``comparison_call`` and a nullable ``comparison_attempt_id``; its shape CHECK and its frozen-column guard
are rebuilt. Nothing else is touched.

State changes are guarded by one function, ``am_guard_comparison_state_edges``, over the explicit edge
list below; the same constants build the non-terminal sets that the erase derives from the CHECKs.

Downgrade
---------
Refuses while any row of any of the nine tables exists, or an ``executor_task`` of origin
``comparison_call``, or a ``comparison_pdf`` version: they exist nowhere else (the pattern of ``0035``
and ``0037``). With none it restores ``0037``'s ``executor_task`` CHECK and guard, drops the column and
this revision's own objects, and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0038_comparison_foundation"
down_revision: str | None = "0037_analysis_presets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "^[0-9a-f]{64}$"
MAX_LABEL_LENGTH = 128
#: ``version_reader.MAX_VERSION_PAGES`` (``0021``): pages of a published version.
MAX_PAGE_NUMBER = 500
#: S3 multipart: parts are numbered 1..10000.
MAX_PART_NUMBER = 10_000
#: ADR-0025 decision 10: 16 MiB per chunk.
PART_SIZE_BYTES = 16 * 1024 * 1024

UPLOAD_KINDS: tuple[str, ...] = ("portal_bundle", "comparison_pdf")
MODULES: tuple[str, ...] = ("versions", "stages")
PROVIDER_MODES: tuple[str, ...] = ("recorded", "live")
COST_BASES: tuple[str, ...] = ("unmetered", "measured", "estimated")
ORDER_SOURCES: tuple[str, ...] = ("proposal", "expert")
PROFILE_STATUSES: tuple[str, ...] = ("ready", "needs_review", "refused")

UPLOAD_STATES: tuple[str, ...] = (
    "uploading", "proposed", "processing", "paused", "completed", "cancelled",
)
UPLOAD_TERMINAL: tuple[str, ...] = ("completed", "cancelled")
SET_STATES: tuple[str, ...] = (
    "uploading", "reading", "review", "ready", "admitting", "done", "failed", "excluded",
)
SET_TERMINAL: tuple[str, ...] = ("done", "excluded")
FILE_STATES: tuple[str, ...] = ("declared", "uploading", "verified", "failed")
PART_STATES: tuple[str, ...] = ("declared", "staged", "completed", "aborted")
PART_TERMINAL: tuple[str, ...] = ("completed", "aborted")
WORK_STATES: tuple[str, ...] = (
    "queued", "leased", "running", "retry_wait", "paused", "spend_unknown",
    "succeeded", "failed", "cancelled",
)
WORK_TERMINAL: tuple[str, ...] = ("succeeded", "failed", "cancelled")
ATTEMPT_STATES: tuple[str, ...] = (
    "created", "leased", "running", "succeeded", "failed", "superseded", "lost", "cancelled",
)
ATTEMPT_TERMINAL: tuple[str, ...] = ("succeeded", "failed", "superseded", "lost", "cancelled")
CALL_STATES: tuple[str, ...] = ("prepared", "sent", "completed", "failed", "unknown")
CALL_TERMINAL: tuple[str, ...] = ("completed", "failed", "unknown")

#: ``(table, from_state, to_state)``: the only state changes the database allows. Insertion states
#: are the column defaults (and, for ``comparison_model_call``, enforced by a trigger).
EDGES: tuple[tuple[str, str, str], ...] = (
    ("comparison_upload", "uploading", "proposed"),
    ("comparison_upload", "uploading", "cancelled"),
    ("comparison_upload", "proposed", "processing"),
    ("comparison_upload", "proposed", "completed"),
    ("comparison_upload", "proposed", "cancelled"),
    ("comparison_upload", "processing", "paused"),
    ("comparison_upload", "processing", "completed"),
    ("comparison_upload", "processing", "cancelled"),
    ("comparison_upload", "paused", "processing"),
    ("comparison_upload", "paused", "cancelled"),
    ("comparison_upload_set", "uploading", "reading"),
    ("comparison_upload_set", "uploading", "failed"),
    ("comparison_upload_set", "uploading", "excluded"),
    ("comparison_upload_set", "reading", "review"),
    ("comparison_upload_set", "reading", "failed"),
    ("comparison_upload_set", "reading", "excluded"),
    ("comparison_upload_set", "review", "ready"),
    ("comparison_upload_set", "review", "failed"),
    ("comparison_upload_set", "review", "excluded"),
    ("comparison_upload_set", "ready", "admitting"),
    ("comparison_upload_set", "ready", "excluded"),
    ("comparison_upload_set", "admitting", "done"),
    ("comparison_upload_set", "admitting", "failed"),
    ("comparison_upload_set", "failed", "reading"),
    ("comparison_upload_set", "failed", "ready"),
    ("comparison_upload_set", "failed", "excluded"),
    ("comparison_upload_file", "declared", "uploading"),
    ("comparison_upload_file", "declared", "failed"),
    ("comparison_upload_file", "uploading", "verified"),
    ("comparison_upload_file", "uploading", "failed"),
    ("comparison_upload_file", "failed", "declared"),
    ("comparison_upload_file", "failed", "uploading"),
    ("comparison_upload_part", "declared", "staged"),
    ("comparison_upload_part", "declared", "aborted"),
    ("comparison_upload_part", "staged", "completed"),
    ("comparison_upload_part", "staged", "aborted"),
    ("comparison_work", "queued", "leased"),
    ("comparison_work", "queued", "paused"),
    ("comparison_work", "queued", "cancelled"),
    ("comparison_work", "leased", "running"),
    ("comparison_work", "leased", "queued"),
    ("comparison_work", "leased", "paused"),
    ("comparison_work", "leased", "failed"),
    ("comparison_work", "leased", "cancelled"),
    ("comparison_work", "leased", "spend_unknown"),
    ("comparison_work", "running", "succeeded"),
    ("comparison_work", "running", "queued"),
    ("comparison_work", "running", "retry_wait"),
    ("comparison_work", "running", "paused"),
    ("comparison_work", "running", "failed"),
    ("comparison_work", "running", "cancelled"),
    ("comparison_work", "running", "spend_unknown"),
    ("comparison_work", "retry_wait", "queued"),
    ("comparison_work", "retry_wait", "paused"),
    ("comparison_work", "retry_wait", "failed"),
    ("comparison_work", "retry_wait", "cancelled"),
    ("comparison_work", "paused", "queued"),
    ("comparison_work", "paused", "cancelled"),
    ("comparison_work", "spend_unknown", "queued"),
    ("comparison_work", "spend_unknown", "failed"),
    ("comparison_work", "spend_unknown", "cancelled"),
    ("comparison_work_attempt", "created", "leased"),
    ("comparison_work_attempt", "created", "cancelled"),
    ("comparison_work_attempt", "leased", "running"),
    ("comparison_work_attempt", "leased", "superseded"),
    ("comparison_work_attempt", "leased", "lost"),
    ("comparison_work_attempt", "leased", "failed"),
    ("comparison_work_attempt", "leased", "cancelled"),
    ("comparison_work_attempt", "running", "succeeded"),
    ("comparison_work_attempt", "running", "failed"),
    ("comparison_work_attempt", "running", "superseded"),
    ("comparison_work_attempt", "running", "lost"),
    ("comparison_work_attempt", "running", "cancelled"),
    ("comparison_model_call", "prepared", "sent"),
    ("comparison_model_call", "prepared", "failed"),
    ("comparison_model_call", "prepared", "unknown"),
    ("comparison_model_call", "sent", "completed"),
    ("comparison_model_call", "sent", "failed"),
    ("comparison_model_call", "sent", "unknown"),
)

TABLES: tuple[str, ...] = (
    "comparison_upload", "comparison_upload_set", "comparison_upload_file",
    "comparison_upload_part", "comparison_version_order", "comparison_page_profile",
    "comparison_work", "comparison_work_attempt", "comparison_model_call",
)

#: ``executor_task``'s frozen list as ``0031`` left it, and with this revision's column.
_TASK_FROZEN = (
    "'task_id', 'connection_id', 'revision_id', 'origin', 'run_id', 'attempt_id', "
    "'model_call_id', 'probe_id', 'expected_model', 'created_at', 'deadline_at'"
)


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _id(column: str, prefix: str, *, nullable: bool = False) -> str:
    check = f"{column} ~ '^{prefix}_{ULID}$'"
    return f"({column} IS NULL OR {check})" if nullable else check


def _edges_values() -> str:
    return ", ".join(f"('{t}', '{a}', '{b}')" for t, a, b in EDGES)


_EDGE_FUNCTION = f"""
        CREATE FUNCTION am_guard_comparison_state_edges() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                RETURN NEW;
            END IF;
            IF EXISTS (
                SELECT 1 FROM (VALUES {_edges_values()}) AS e (tbl, from_state, to_state)
                 WHERE e.tbl = TG_TABLE_NAME
                   AND e.from_state = OLD.state AND e.to_state = NEW.state
            ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'state_transition_not_allowed: % has no declared transition % -> %',
                TG_TABLE_NAME, OLD.state, NEW.state
                USING ERRCODE = 'AM001',
                      HINT = 'A comparison row moves only along the edges of migration 0038.';
        END
        $fn$;
        """

_CALL_INSERT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_model_call_insert() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.state <> 'prepared' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: a comparison model call is inserted prepared, not %',
                    NEW.state
                    USING ERRCODE = 'AM001',
                          HINT = 'The prepared row is committed before any provider call (ADR-0025 decision 5).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_PART_INSERT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_upload_part_insert() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.state <> 'declared' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: a part is inserted declared, not %', NEW.state
                    USING ERRCODE = 'AM001';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM comparison_upload_file f
                 WHERE f.comparison_upload_file_id = NEW.comparison_upload_file_id
                   AND f.multipart_token IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: file % has no multipart token yet',
                    NEW.comparison_upload_file_id
                    USING ERRCODE = 'AM001',
                          HINT = 'The multipart token is persisted before the first part (ADR-0025 decision 10).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_ORDER_CHAIN_FUNCTION = f"""
        CREATE FUNCTION am_check_comparison_version_order_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no integer;
            listed integer;
            distinct_listed integer;
            belonging integer;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended(
                'comparison_version_order:' || NEW.document_uid, 0));
            IF NOT EXISTS (
                SELECT 1 FROM document d
                 WHERE d.document_uid = NEW.document_uid AND d.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: document % is not a document of project %',
                    NEW.document_uid, NEW.project_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF jsonb_typeof(NEW.version_uids) IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: an order is a JSON array of version identities'
                    USING ERRCODE = 'AM001';
            END IF;
            SELECT max(revision_no) INTO last_no
              FROM comparison_version_order WHERE document_uid = NEW.document_uid;
            IF NEW.revision_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: document % has revision % and cannot take %',
                    NEW.document_uid, coalesce(last_no, 0), NEW.revision_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Revisions are numbered 1, 2, 3, ... without a gap.';
            END IF;
            SELECT count(*), count(DISTINCT v), count(dv.version_uid)
              INTO listed, distinct_listed, belonging
              FROM jsonb_array_elements_text(NEW.version_uids) AS v
              LEFT JOIN document_version dv
                ON dv.version_uid = v AND dv.document_uid = NEW.document_uid;
            IF listed <> distinct_listed OR listed <> belonging THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: an order lists a version twice or a version of another document'
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_PROFILE_INSERT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_page_profile() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM document_version v
                 WHERE v.version_uid = NEW.version_uid AND NEW.page_number <= v.page_count
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: version % has no page %',
                    NEW.version_uid, NEW.page_number
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def upgrade() -> None:
    _alter_document_version()
    _create_functions()
    _create_upload_tables()
    _create_order_and_profile_tables()
    _create_queue_tables()
    _create_model_call_table()
    _alter_executor_task()
    _attach_guards()
    _comments()


def _alter_document_version() -> None:
    op.execute(
        "ALTER TABLE document_version "
        "ADD COLUMN upload_kind text NOT NULL DEFAULT 'portal_bundle'"
    )
    op.execute(
        "ALTER TABLE document_version ADD CONSTRAINT ck_document_version_upload_kind "
        f"CHECK (upload_kind IN ({_sql_list(UPLOAD_KINDS)}))"
    )
    op.execute(
        "ALTER TABLE document_version ADD CONSTRAINT ck_document_version_comparison_pdf_no_bundle "
        "CHECK (upload_kind <> 'comparison_pdf' OR text_character_count IS NULL)"
    )
    op.execute(
        "COMMENT ON COLUMN document_version.upload_kind IS "
        "'CMP-SEAL-C0. How the version reached the product: a portal bundle (every version before "
        "0038) or a plain PDF admitted for comparison only (comparison_pdf, Q-CMP-5). A "
        "comparison-only version never starts a section analysis and never becomes the current "
        "version of a document that has a portal version (ADR-0025 decision 11).';"
    )


def _create_functions() -> None:
    op.execute(_EDGE_FUNCTION)
    op.execute(_CALL_INSERT_FUNCTION)
    op.execute(_PART_INSERT_FUNCTION)
    op.execute(_ORDER_CHAIN_FUNCTION)
    op.execute(_PROFILE_INSERT_FUNCTION)


def _create_upload_tables() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_upload (
            comparison_upload_id text PRIMARY KEY,
            project_uid          text NOT NULL,
            state                text NOT NULL DEFAULT 'uploading',
            declared_files       integer NOT NULL,
            declared_bytes       bigint NOT NULL,
            declared_pages       integer NOT NULL DEFAULT 0,
            part_size_bytes      integer NOT NULL DEFAULT {PART_SIZE_BYTES},
            pause_requested      boolean NOT NULL DEFAULT false,
            actor_user_uid       text NOT NULL,
            actor_label          text NOT NULL,
            command_id           text NOT NULL,
            created_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at          timestamptz NULL,
            CONSTRAINT fk_comparison_upload_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_upload_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_upload_command UNIQUE (command_id),
            CONSTRAINT uq_comparison_upload_project UNIQUE (comparison_upload_id, project_uid),
            CONSTRAINT ck_comparison_upload_id_format
                CHECK ({_id('comparison_upload_id', 'cbt')}),
            CONSTRAINT ck_comparison_upload_project_uid_format
                CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_upload_actor_user_uid_format
                CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_upload_command_id_format
                CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_upload_state CHECK (state IN ({_sql_list(UPLOAD_STATES)})),
            CONSTRAINT ck_comparison_upload_declared_files CHECK (declared_files >= 1),
            CONSTRAINT ck_comparison_upload_declared_bytes CHECK (declared_bytes >= 1),
            CONSTRAINT ck_comparison_upload_declared_pages CHECK (declared_pages >= 0),
            CONSTRAINT ck_comparison_upload_part_size
                CHECK (part_size_bytes BETWEEN 1 AND {PART_SIZE_BYTES}),
            CONSTRAINT ck_comparison_upload_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n')),
            CONSTRAINT ck_comparison_upload_terminal_at CHECK (
                (state IN ({_sql_list(UPLOAD_TERMINAL)})) = (terminal_at IS NOT NULL))
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_upload_project ON comparison_upload (project_uid, created_at);")
    op.execute(
        f"""
        CREATE TABLE comparison_upload_set (
            comparison_upload_set_id text PRIMARY KEY,
            comparison_upload_id     text NOT NULL,
            state                    text NOT NULL DEFAULT 'uploading',
            designation              text NULL,
            existing_document_uid    text NULL,
            document_uid             text NULL,
            project_stage            text NULL,
            section_code             text NULL,
            proposal                 jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            failure_reason           text NULL,
            confirmed_by_user_uid    text NULL,
            confirmed_at             timestamptz NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at              timestamptz NULL,
            CONSTRAINT fk_comparison_upload_set_upload
                FOREIGN KEY (comparison_upload_id) REFERENCES comparison_upload (comparison_upload_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_upload_set_existing_document
                FOREIGN KEY (existing_document_uid) REFERENCES document (document_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_upload_set_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_upload_set_upload
                UNIQUE (comparison_upload_set_id, comparison_upload_id),
            CONSTRAINT ck_comparison_upload_set_id_format
                CHECK ({_id('comparison_upload_set_id', 'cus')}),
            CONSTRAINT ck_comparison_upload_set_upload_id_format
                CHECK ({_id('comparison_upload_id', 'cbt')}),
            CONSTRAINT ck_comparison_upload_set_existing_document_uid_format
                CHECK ({_id('existing_document_uid', 'doc', nullable=True)}),
            CONSTRAINT ck_comparison_upload_set_document_uid_format
                CHECK ({_id('document_uid', 'doc', nullable=True)}),
            CONSTRAINT ck_comparison_upload_set_confirmed_by_format
                CHECK ({_id('confirmed_by_user_uid', 'usr', nullable=True)}),
            CONSTRAINT ck_comparison_upload_set_state CHECK (state IN ({_sql_list(SET_STATES)})),
            CONSTRAINT ck_comparison_upload_set_designation
                CHECK (designation IS NULL OR char_length(designation) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_upload_set_project_stage
                CHECK (project_stage IS NULL OR project_stage IN ('P', 'R')),
            CONSTRAINT ck_comparison_upload_set_section_code
                CHECK (section_code IS NULL OR section_code ~ '^[A-Z]{{2,3}}$'),
            CONSTRAINT ck_comparison_upload_set_proposal_is_object
                CHECK (jsonb_typeof(proposal) = 'object'),
            CONSTRAINT ck_comparison_upload_set_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128)),
            CONSTRAINT ck_comparison_upload_set_confirmed CHECK (
                state NOT IN ('ready', 'admitting', 'done')
                OR (confirmed_at IS NOT NULL AND confirmed_by_user_uid IS NOT NULL)),
            CONSTRAINT ck_comparison_upload_set_done_has_document
                CHECK (state <> 'done' OR document_uid IS NOT NULL),
            CONSTRAINT ck_comparison_upload_set_terminal_at CHECK (
                (state IN ({_sql_list(SET_TERMINAL)})) = (terminal_at IS NOT NULL))
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_upload_set_upload ON comparison_upload_set (comparison_upload_id);")
    op.execute(
        f"""
        CREATE TABLE comparison_upload_file (
            comparison_upload_file_id text PRIMARY KEY,
            comparison_upload_id      text NOT NULL,
            set_id                    text NULL,
            display_name              text NOT NULL,
            declared_size_bytes       bigint NOT NULL,
            declared_sha256           text NOT NULL,
            declared_page_count       integer NULL,
            state                     text NOT NULL DEFAULT 'declared',
            multipart_token           text NULL,
            blob_id                   text NULL,
            failure_reason            text NULL,
            created_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_upload_file_upload
                FOREIGN KEY (comparison_upload_id) REFERENCES comparison_upload (comparison_upload_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_upload_file_set
                FOREIGN KEY (set_id, comparison_upload_id)
                REFERENCES comparison_upload_set (comparison_upload_set_id, comparison_upload_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_upload_file_blob
                FOREIGN KEY (blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_upload_file_id_format
                CHECK ({_id('comparison_upload_file_id', 'cuf')}),
            CONSTRAINT ck_comparison_upload_file_upload_id_format
                CHECK ({_id('comparison_upload_id', 'cbt')}),
            CONSTRAINT ck_comparison_upload_file_set_id_format
                CHECK ({_id('set_id', 'cus', nullable=True)}),
            CONSTRAINT ck_comparison_upload_file_blob_id_format
                CHECK ({_id('blob_id', 'blob', nullable=True)}),
            CONSTRAINT ck_comparison_upload_file_state CHECK (state IN ({_sql_list(FILE_STATES)})),
            CONSTRAINT ck_comparison_upload_file_display_name
                CHECK (char_length(display_name) BETWEEN 1 AND 255),
            CONSTRAINT ck_comparison_upload_file_declared_size CHECK (declared_size_bytes >= 1),
            CONSTRAINT ck_comparison_upload_file_declared_sha256
                CHECK (declared_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_upload_file_declared_page_count
                CHECK (declared_page_count IS NULL OR declared_page_count BETWEEN 1 AND {MAX_PAGE_NUMBER}),
            CONSTRAINT ck_comparison_upload_file_multipart_token
                CHECK (multipart_token IS NULL OR char_length(multipart_token) BETWEEN 1 AND 1024),
            CONSTRAINT ck_comparison_upload_file_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128)),
            CONSTRAINT ck_comparison_upload_file_verified_has_blob
                CHECK (state <> 'verified' OR blob_id IS NOT NULL)
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_upload_file_upload ON comparison_upload_file (comparison_upload_id);")
    op.execute(
        "CREATE INDEX ix_comparison_upload_file_set ON comparison_upload_file (set_id) "
        "WHERE set_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_upload_file_blob ON comparison_upload_file (blob_id) "
        "WHERE blob_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_upload_part (
            comparison_upload_file_id text NOT NULL,
            part_number               integer NOT NULL,
            state                     text NOT NULL DEFAULT 'declared',
            size_bytes                bigint NULL,
            sha256                    text NULL,
            etag                      text NULL,
            created_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_comparison_upload_part PRIMARY KEY (comparison_upload_file_id, part_number),
            CONSTRAINT fk_comparison_upload_part_file
                FOREIGN KEY (comparison_upload_file_id)
                REFERENCES comparison_upload_file (comparison_upload_file_id) ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_upload_part_file_id_format
                CHECK ({_id('comparison_upload_file_id', 'cuf')}),
            CONSTRAINT ck_comparison_upload_part_number
                CHECK (part_number BETWEEN 1 AND {MAX_PART_NUMBER}),
            CONSTRAINT ck_comparison_upload_part_state CHECK (state IN ({_sql_list(PART_STATES)})),
            CONSTRAINT ck_comparison_upload_part_size
                CHECK (size_bytes IS NULL OR size_bytes BETWEEN 1 AND {PART_SIZE_BYTES}),
            CONSTRAINT ck_comparison_upload_part_sha256
                CHECK (sha256 IS NULL OR sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_upload_part_etag
                CHECK (etag IS NULL OR char_length(etag) BETWEEN 1 AND 256),
            CONSTRAINT ck_comparison_upload_part_staged_facts CHECK (
                state NOT IN ('staged', 'completed')
                OR (size_bytes IS NOT NULL AND sha256 IS NOT NULL AND etag IS NOT NULL))
        );
        """
    )


def _create_order_and_profile_tables() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_version_order (
            comparison_version_order_id text PRIMARY KEY,
            project_uid                 text NOT NULL,
            document_uid                text NOT NULL,
            revision_no                 integer NOT NULL,
            version_uids                jsonb NOT NULL,
            source                      text NOT NULL,
            actor_user_uid              text NOT NULL,
            actor_label                 text NOT NULL,
            command_id                  text NOT NULL,
            created_at                  timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_version_order_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_version_order_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_version_order_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_version_order_command UNIQUE (command_id),
            CONSTRAINT uq_comparison_version_order_revision UNIQUE (document_uid, revision_no),
            CONSTRAINT ck_comparison_version_order_id_format
                CHECK ({_id('comparison_version_order_id', 'cvo')}),
            CONSTRAINT ck_comparison_version_order_project_uid_format
                CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_version_order_document_uid_format
                CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_version_order_actor_format
                CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_version_order_command_id_format
                CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_version_order_revision_no CHECK (revision_no >= 1),
            CONSTRAINT ck_comparison_version_order_source
                CHECK (source IN ({_sql_list(ORDER_SOURCES)})),
            CONSTRAINT ck_comparison_version_order_versions_is_array CHECK (
                jsonb_typeof(version_uids) = 'array'
                AND CASE WHEN jsonb_typeof(version_uids) = 'array'
                         THEN jsonb_array_length(version_uids) BETWEEN 1 AND {MAX_PAGE_NUMBER}
                         ELSE false END),
            CONSTRAINT ck_comparison_version_order_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n'))
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE comparison_page_profile (
            comparison_page_profile_id text PRIMARY KEY,
            version_uid                text NOT NULL,
            page_number                integer NOT NULL,
            content_key                text NOT NULL,
            algo_version               text NOT NULL,
            status                     text NOT NULL,
            reason                     text NULL,
            profile                    jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            profile_blob_id            text NULL,
            preview_blob_id            text NULL,
            thumbnail_blob_id          text NULL,
            created_at                 timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_page_profile_version
                FOREIGN KEY (version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_page_profile_profile_blob
                FOREIGN KEY (profile_blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_page_profile_preview_blob
                FOREIGN KEY (preview_blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_page_profile_thumbnail_blob
                FOREIGN KEY (thumbnail_blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_page_profile_content_key UNIQUE (version_uid, content_key),
            CONSTRAINT uq_comparison_page_profile_page
                UNIQUE (version_uid, page_number, algo_version),
            CONSTRAINT ck_comparison_page_profile_id_format
                CHECK ({_id('comparison_page_profile_id', 'cpr')}),
            CONSTRAINT ck_comparison_page_profile_version_uid_format
                CHECK ({_id('version_uid', 'ver')}),
            CONSTRAINT ck_comparison_page_profile_blob_id_formats CHECK (
                {_id('profile_blob_id', 'blob', nullable=True)}
                AND {_id('preview_blob_id', 'blob', nullable=True)}
                AND {_id('thumbnail_blob_id', 'blob', nullable=True)}),
            CONSTRAINT ck_comparison_page_profile_page_number
                CHECK (page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}),
            CONSTRAINT ck_comparison_page_profile_content_key
                CHECK (content_key ~ '{SHA256}'),
            CONSTRAINT ck_comparison_page_profile_algo_version
                CHECK (char_length(algo_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_page_profile_status
                CHECK (status IN ({_sql_list(PROFILE_STATUSES)})),
            CONSTRAINT ck_comparison_page_profile_reason CHECK (
                (status = 'ready') = (reason IS NULL)
                AND (reason IS NULL OR char_length(reason) BETWEEN 1 AND 128)),
            CONSTRAINT ck_comparison_page_profile_profile_is_object
                CHECK (jsonb_typeof(profile) = 'object')
        );
        """
    )
    for column in ("profile_blob_id", "preview_blob_id", "thumbnail_blob_id"):
        op.execute(
            f"CREATE INDEX ix_comparison_page_profile_{column} ON comparison_page_profile "
            f"({column}) WHERE {column} IS NOT NULL;"
        )


def _create_queue_tables() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_work (
            comparison_work_id  text PRIMARY KEY,
            project_uid         text NOT NULL,
            module              text NOT NULL,
            kind                text NOT NULL,
            state               text NOT NULL DEFAULT 'queued',
            payload             jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            dedupe_key          text NULL,
            priority            smallint NOT NULL DEFAULT 0,
            not_before          timestamptz NOT NULL DEFAULT clock_timestamp(),
            attempt_count       integer NOT NULL DEFAULT 0,
            max_attempts        integer NOT NULL DEFAULT 3,
            current_attempt_id  text NULL,
            comparison_upload_id text NULL,
            cancel_requested_at timestamptz NULL,
            failure_reason      text NULL,
            created_by_user_uid text NULL,
            created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at         timestamptz NULL,
            CONSTRAINT fk_comparison_work_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_work_upload
                FOREIGN KEY (comparison_upload_id) REFERENCES comparison_upload (comparison_upload_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_work_current_attempt UNIQUE (current_attempt_id),
            CONSTRAINT ck_comparison_work_id_format CHECK ({_id('comparison_work_id', 'cq')}),
            CONSTRAINT ck_comparison_work_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_work_current_attempt_id_format
                CHECK ({_id('current_attempt_id', 'cqa', nullable=True)}),
            CONSTRAINT ck_comparison_work_upload_id_format
                CHECK ({_id('comparison_upload_id', 'cbt', nullable=True)}),
            CONSTRAINT ck_comparison_work_created_by_format
                CHECK ({_id('created_by_user_uid', 'usr', nullable=True)}),
            CONSTRAINT ck_comparison_work_module CHECK (module IN ({_sql_list(MODULES)})),
            CONSTRAINT ck_comparison_work_kind CHECK (kind ~ '^[a-z][a-z0-9_]{{2,63}}$'),
            CONSTRAINT ck_comparison_work_state CHECK (state IN ({_sql_list(WORK_STATES)})),
            CONSTRAINT ck_comparison_work_payload_is_object CHECK (jsonb_typeof(payload) = 'object'),
            CONSTRAINT ck_comparison_work_dedupe_key
                CHECK (dedupe_key IS NULL OR char_length(dedupe_key) BETWEEN 1 AND 256),
            CONSTRAINT ck_comparison_work_attempts CHECK (
                attempt_count >= 0 AND max_attempts BETWEEN 1 AND 10),
            CONSTRAINT ck_comparison_work_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128)),
            CONSTRAINT ck_comparison_work_terminal_at CHECK (
                (state IN ({_sql_list(WORK_TERMINAL)})) = (terminal_at IS NOT NULL))
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE comparison_work_attempt (
            comparison_work_attempt_id text PRIMARY KEY,
            comparison_work_id         text NOT NULL,
            attempt_no                 integer NOT NULL,
            state                      text NOT NULL DEFAULT 'created',
            execution_token            text NOT NULL,
            worker_id                  text NULL,
            lease_expires_at           timestamptz NULL,
            heartbeat_at               timestamptz NULL,
            failure_reason             text NULL,
            created_at                 timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at                 timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at                timestamptz NULL,
            CONSTRAINT fk_comparison_work_attempt_work
                FOREIGN KEY (comparison_work_id) REFERENCES comparison_work (comparison_work_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_work_attempt_worker
                FOREIGN KEY (worker_id) REFERENCES worker (worker_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_work_attempt_token UNIQUE (execution_token),
            CONSTRAINT uq_comparison_work_attempt_no UNIQUE (comparison_work_id, attempt_no),
            CONSTRAINT uq_comparison_work_attempt_work
                UNIQUE (comparison_work_id, comparison_work_attempt_id),
            CONSTRAINT ck_comparison_work_attempt_id_format
                CHECK ({_id('comparison_work_attempt_id', 'cqa')}),
            CONSTRAINT ck_comparison_work_attempt_work_id_format
                CHECK ({_id('comparison_work_id', 'cq')}),
            CONSTRAINT ck_comparison_work_attempt_worker_id_format
                CHECK ({_id('worker_id', 'wrk', nullable=True)}),
            CONSTRAINT ck_comparison_work_attempt_no CHECK (attempt_no >= 1),
            CONSTRAINT ck_comparison_work_attempt_state
                CHECK (state IN ({_sql_list(ATTEMPT_STATES)})),
            CONSTRAINT ck_comparison_work_attempt_execution_token CHECK (
                char_length(execution_token) BETWEEN 1 AND 256
                AND execution_token ~ '^[A-Za-z0-9._~-]+$'),
            CONSTRAINT ck_comparison_work_attempt_lease CHECK (
                state NOT IN ('leased', 'running')
                OR (lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL)),
            CONSTRAINT ck_comparison_work_attempt_failure_reason
                CHECK (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128),
            CONSTRAINT ck_comparison_work_attempt_terminal_at CHECK (
                (state IN ({_sql_list(ATTEMPT_TERMINAL)})) = (terminal_at IS NOT NULL))
        );
        """
    )
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT fk_comparison_work_current_attempt "
        "FOREIGN KEY (comparison_work_id, current_attempt_id) "
        "REFERENCES comparison_work_attempt (comparison_work_id, comparison_work_attempt_id) "
        "DEFERRABLE INITIALLY DEFERRED;"
    )
    op.execute("CREATE INDEX ix_comparison_work_attempt_work ON comparison_work_attempt (comparison_work_id);")
    op.execute(
        "CREATE INDEX ix_comparison_work_claimable ON comparison_work "
        "(priority DESC, not_before, created_at) WHERE state = 'queued';"
    )
    op.execute("CREATE INDEX ix_comparison_work_project ON comparison_work (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_work_upload ON comparison_work (comparison_upload_id) "
        "WHERE comparison_upload_id IS NOT NULL;"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_work_live_dedupe "
        "ON comparison_work (project_uid, kind, dedupe_key) "
        "WHERE dedupe_key IS NOT NULL AND terminal_at IS NULL;"
    )


def _create_model_call_table() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_model_call (
            comparison_model_call_id   text PRIMARY KEY,
            comparison_work_id         text NOT NULL,
            comparison_work_attempt_id text NOT NULL,
            work_kind                  text NOT NULL,
            state                      text NOT NULL DEFAULT 'prepared',
            provider_mode              text NOT NULL,
            model_identity             text NOT NULL,
            connection_revision_id     text NULL,
            request_sha256             text NOT NULL,
            estimate_micros            bigint NOT NULL,
            executor_task_id           text NULL,
            response_sha256            text NULL,
            input_tokens               integer NULL,
            output_tokens              integer NULL,
            latency_ms                 integer NULL,
            cost_basis                 text NULL,
            cost_micros                bigint NULL,
            error_code                 text NULL,
            prepared_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            sent_at                    timestamptz NULL,
            terminal_at                timestamptz NULL,
            CONSTRAINT fk_comparison_model_call_attempt
                FOREIGN KEY (comparison_work_id, comparison_work_attempt_id)
                REFERENCES comparison_work_attempt (comparison_work_id, comparison_work_attempt_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_model_call_revision
                FOREIGN KEY (connection_revision_id)
                REFERENCES executor_connection_revision (revision_id) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_model_call_task
                FOREIGN KEY (executor_task_id) REFERENCES executor_task (task_id)
                ON DELETE RESTRICT,
            CONSTRAINT ck_comparison_model_call_id_format
                CHECK ({_id('comparison_model_call_id', 'cmc')}),
            CONSTRAINT ck_comparison_model_call_work_id_format
                CHECK ({_id('comparison_work_id', 'cq')}),
            CONSTRAINT ck_comparison_model_call_attempt_id_format
                CHECK ({_id('comparison_work_attempt_id', 'cqa')}),
            CONSTRAINT ck_comparison_model_call_revision_id_format
                CHECK ({_id('connection_revision_id', 'excr', nullable=True)}),
            CONSTRAINT ck_comparison_model_call_task_id_format
                CHECK ({_id('executor_task_id', 'ext', nullable=True)}),
            CONSTRAINT ck_comparison_model_call_work_kind
                CHECK (work_kind ~ '^[a-z][a-z0-9_]{{2,63}}$'),
            CONSTRAINT ck_comparison_model_call_state CHECK (state IN ({_sql_list(CALL_STATES)})),
            CONSTRAINT ck_comparison_model_call_provider_mode
                CHECK (provider_mode IN ({_sql_list(PROVIDER_MODES)})),
            CONSTRAINT ck_comparison_model_call_model_identity
                CHECK (char_length(model_identity) BETWEEN 1 AND 200),
            CONSTRAINT ck_comparison_model_call_request_sha256
                CHECK (request_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_model_call_response_sha256
                CHECK (response_sha256 IS NULL OR response_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_model_call_estimate CHECK (estimate_micros >= 0),
            CONSTRAINT ck_comparison_model_call_tokens CHECK (
                (input_tokens IS NULL OR input_tokens >= 0)
                AND (output_tokens IS NULL OR output_tokens >= 0)
                AND (latency_ms IS NULL OR latency_ms >= 0)),
            CONSTRAINT ck_comparison_model_call_cost_basis
                CHECK (cost_basis IS NULL OR cost_basis IN ({_sql_list(COST_BASES)})),
            CONSTRAINT ck_comparison_model_call_cost_micros
                CHECK (cost_micros IS NULL OR cost_micros >= 0),
            CONSTRAINT ck_comparison_model_call_error_code
                CHECK (error_code IS NULL OR error_code ~ '^[a-z][a-z_]{{2,63}}$'),
            CONSTRAINT ck_comparison_model_call_unmetered_costs_nothing
                CHECK (cost_basis IS DISTINCT FROM 'unmetered' OR cost_micros = 0),
            CONSTRAINT ck_comparison_model_call_recorded_is_unmetered
                CHECK (provider_mode <> 'recorded' OR state <> 'completed'
                       OR (model_identity = 'recorded' AND cost_basis = 'unmetered')),
            CONSTRAINT ck_comparison_model_call_prepared_shape CHECK (
                state <> 'prepared'
                OR (sent_at IS NULL AND terminal_at IS NULL AND response_sha256 IS NULL
                    AND cost_basis IS NULL AND cost_micros IS NULL AND error_code IS NULL)),
            CONSTRAINT ck_comparison_model_call_sent_shape CHECK (
                state <> 'sent'
                OR (sent_at IS NOT NULL AND terminal_at IS NULL AND response_sha256 IS NULL
                    AND cost_basis IS NULL AND cost_micros IS NULL AND error_code IS NULL)),
            CONSTRAINT ck_comparison_model_call_completed_shape CHECK (
                state <> 'completed'
                OR (sent_at IS NOT NULL AND terminal_at IS NOT NULL AND response_sha256 IS NOT NULL
                    AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL
                    AND latency_ms IS NOT NULL AND cost_basis IS NOT NULL
                    AND cost_micros IS NOT NULL AND error_code IS NULL)),
            CONSTRAINT ck_comparison_model_call_failed_shape CHECK (
                state <> 'failed' OR (terminal_at IS NOT NULL AND error_code IS NOT NULL)),
            CONSTRAINT ck_comparison_model_call_unknown_shape CHECK (
                state <> 'unknown'
                OR (terminal_at IS NOT NULL AND response_sha256 IS NULL AND cost_micros IS NULL)),
            CONSTRAINT ck_comparison_model_call_terminal_at CHECK (
                (state IN ({_sql_list(CALL_TERMINAL)})) = (terminal_at IS NOT NULL))
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_model_call_attempt ON comparison_model_call (comparison_work_attempt_id);")
    op.execute("CREATE INDEX ix_comparison_model_call_work ON comparison_model_call (comparison_work_id);")
    op.execute(
        "CREATE INDEX ix_comparison_model_call_open ON comparison_model_call (prepared_at) "
        "WHERE state IN ('prepared', 'sent');"
    )
    op.execute(
        "CREATE INDEX ix_comparison_model_call_task ON comparison_model_call (executor_task_id) "
        "WHERE executor_task_id IS NOT NULL;"
    )


def _alter_executor_task() -> None:
    op.execute("ALTER TABLE executor_task ADD COLUMN comparison_attempt_id text NULL")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT fk_executor_task_comparison_attempt "
        "FOREIGN KEY (comparison_attempt_id) "
        "REFERENCES comparison_work_attempt (comparison_work_attempt_id)"
    )
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_comparison_attempt_id_format "
        f"CHECK ({_id('comparison_attempt_id', 'cqa', nullable=True)})"
    )
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_origin")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_origin_shape")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_origin "
        "CHECK (origin IN ('run_call', 'probe', 'comparison_call'))"
    )
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_origin_shape CHECK ("
        "(origin = 'run_call' AND run_id IS NOT NULL AND attempt_id IS NOT NULL "
        "AND probe_id IS NULL AND comparison_attempt_id IS NULL) "
        "OR (origin = 'probe' AND probe_id IS NOT NULL AND run_id IS NULL "
        "AND attempt_id IS NULL AND model_call_id IS NULL AND comparison_attempt_id IS NULL) "
        "OR (origin = 'comparison_call' AND comparison_attempt_id IS NOT NULL AND run_id IS NULL "
        "AND attempt_id IS NULL AND probe_id IS NULL AND model_call_id IS NULL))"
    )
    op.execute(
        "CREATE INDEX ix_executor_task_comparison_attempt ON executor_task (comparison_attempt_id) "
        "WHERE comparison_attempt_id IS NOT NULL"
    )
    _task_frozen_guard(with_comparison=True)


def _task_frozen_guard(*, with_comparison: bool) -> None:
    op.execute("DROP TRIGGER trg_executor_task_frozen_guard ON executor_task")
    columns = _TASK_FROZEN + (", 'comparison_attempt_id'" if with_comparison else "")
    op.execute(
        "CREATE TRIGGER trg_executor_task_frozen_guard BEFORE UPDATE ON executor_task "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({columns})"
    )


def _attach_guards() -> None:
    for table in (
        "comparison_upload", "comparison_upload_set", "comparison_upload_file",
        "comparison_upload_part", "comparison_work", "comparison_work_attempt",
        "comparison_model_call",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_state_edges BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_comparison_state_edges()"
        )
    frozen = {
        "comparison_upload": (
            "comparison_upload_id", "project_uid", "declared_files", "declared_bytes",
            "declared_pages", "part_size_bytes", "actor_user_uid", "actor_label", "command_id",
            "created_at",
        ),
        "comparison_upload_set": ("comparison_upload_set_id", "comparison_upload_id", "created_at"),
        "comparison_upload_file": (
            "comparison_upload_file_id", "comparison_upload_id", "display_name",
            "declared_size_bytes", "declared_sha256", "declared_page_count", "created_at",
        ),
        "comparison_upload_part": ("comparison_upload_file_id", "part_number", "created_at"),
        "comparison_work": (
            "comparison_work_id", "project_uid", "module", "kind", "dedupe_key",
            "comparison_upload_id", "created_by_user_uid", "created_at",
        ),
        "comparison_work_attempt": (
            "comparison_work_attempt_id", "comparison_work_id", "attempt_no", "execution_token",
            "created_at",
        ),
        "comparison_model_call": (
            "comparison_model_call_id", "comparison_work_id", "comparison_work_attempt_id",
            "work_kind", "provider_mode", "model_identity", "connection_revision_id",
            "request_sha256", "estimate_micros", "prepared_at",
        ),
        "comparison_page_profile": (
            "comparison_page_profile_id", "version_uid", "page_number", "content_key",
            "algo_version", "status", "reason", "profile", "created_at",
        ),
    }
    for table, columns in frozen.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_sql_list(columns)})"
        )
    write_once = {
        "comparison_upload_file": ("multipart_token", "blob_id"),
        "comparison_page_profile": ("profile_blob_id", "preview_blob_id", "thumbnail_blob_id"),
        "comparison_work": ("terminal_at",),
        "comparison_work_attempt": ("terminal_at",),
        "comparison_model_call": ("sent_at", "terminal_at"),
    }
    for table, columns in write_once.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_write_once BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns({_sql_list(columns)})"
        )
    op.execute(
        "CREATE TRIGGER trg_comparison_model_call_prepared_first BEFORE INSERT ON "
        "comparison_model_call FOR EACH ROW EXECUTE FUNCTION "
        "am_check_comparison_model_call_insert()"
    )
    op.execute(
        "CREATE TRIGGER trg_comparison_upload_part_token_first BEFORE INSERT ON "
        "comparison_upload_part FOR EACH ROW EXECUTE FUNCTION "
        "am_check_comparison_upload_part_insert()"
    )
    op.execute(
        "CREATE TRIGGER trg_comparison_version_order_chain BEFORE INSERT ON "
        "comparison_version_order FOR EACH ROW EXECUTE FUNCTION "
        "am_check_comparison_version_order_chain()"
    )
    op.execute(
        "CREATE TRIGGER trg_comparison_version_order_immutable BEFORE UPDATE OR DELETE ON "
        "comparison_version_order FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_comparison_page_profile_page BEFORE INSERT ON "
        "comparison_page_profile FOR EACH ROW EXECUTE FUNCTION am_check_comparison_page_profile()"
    )


def _comments() -> None:
    comments = {
        "comparison_upload": (
            "CMP-SEAL-C0. One upload batch of plain PDFs for comparison (ADR-0025 decisions 9-11): "
            "the declared files, bytes and pages, the actor and the idempotency receipt. The "
            "limits are refused by the application before the first part."
        ),
        "comparison_upload_set": (
            "CMP-SEAL-C0. One proposed document set of a batch (the original''s batch item): the "
            "designation (metadata, never an identity), the proposal, the stage and section and "
            "its state. Confirm, exclude and retry act on a set."
        ),
        "comparison_upload_file": (
            "CMP-SEAL-C0. One declared file: a display name (a hint, never an identity), the "
            "declared size and SHA-256 checked at completion, the opaque multipart token "
            "(write-once, persisted before the first part) and the published blob once verified."
        ),
        "comparison_upload_part": (
            "CMP-SEAL-C0. One chunk of one file, keyed by (file, part number). The row exists "
            "before its bytes are staged, and only for a file that holds a multipart token."
        ),
        "comparison_version_order": (
            "CMP-SEAL-C0. The append-only revisions of the order in which the versions of one "
            "document set are compared. Never updated or deleted (am_immutable_row); numbered "
            "without a gap and listing only versions of the document "
            "(am_check_comparison_version_order_chain). It does not change version_ordinal (D-5)."
        ),
        "comparison_page_profile": (
            "CMP-SEAL-C0. The raw deterministic profile of one page of one version, content-keyed "
            "(a ULID id and a unique digest; the digest is never a foreign key). Frozen apart from "
            "the write-once blob references."
        ),
        "comparison_work": (
            "CMP-SEAL-C0. The comparison-local durable queue (ADR-0025 decision 4): the Lease "
            "pattern of job without run_id, and no foreign key to job, attempt or audit_run. A "
            "project with a non-terminal row is not erased (decision 7)."
        ),
        "comparison_work_attempt": (
            "CMP-SEAL-C0. One leased execution of a comparison work item, with its heartbeat and "
            "lease expiry. execution_token is secret-class and never returned."
        ),
        "comparison_model_call": (
            "CMP-SEAL-C0. The comparison spend journal (ADR-0025 decision 5): inserted prepared "
            "before any provider call, then sent, then completed, failed or unknown. A prepared or "
            "sent row at reclaim is never sent again."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")
    op.execute(
        "COMMENT ON COLUMN comparison_work_attempt.execution_token IS "
        "'Secret-class opaque equality-only capability. It is never logged, returned through the "
        "API, parsed, ordered or used as entity identity.';"
    )
    op.execute(
        "COMMENT ON COLUMN comparison_upload.actor_user_uid IS "
        "'The account that declared the batch. Deliberately not a foreign key: the register of "
        "account references belongs to the access context.';"
    )


def downgrade() -> None:
    """Refuse while a row exists, otherwise drop this revision's own objects and nothing else."""
    bind = op.get_bind()
    occupied = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
        for table in TABLES
    }
    occupied["executor_task (comparison_call)"] = int(
        bind.execute(
            text("SELECT count(*) FROM executor_task WHERE origin = 'comparison_call'")
        ).scalar_one()
    )
    occupied["document_version (comparison_pdf)"] = int(
        bind.execute(
            text("SELECT count(*) FROM document_version WHERE upload_kind = 'comparison_pdf'")
        ).scalar_one()
    )
    if any(occupied.values()):
        rendered = ", ".join(f"{name}={count}" for name, count in occupied.items() if count)
        raise RuntimeError(
            f"0038 downgrade refused: comparison data exists nowhere else ({rendered}); "
            "restore a backup instead of downgrading"
        )
    op.execute("DROP INDEX ix_executor_task_comparison_attempt")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_origin_shape")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_origin")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_origin "
        "CHECK (origin IN ('run_call', 'probe'))"
    )
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_origin_shape CHECK ("
        "(origin = 'run_call' AND run_id IS NOT NULL AND attempt_id IS NOT NULL "
        "AND probe_id IS NULL) "
        "OR (origin = 'probe' AND probe_id IS NOT NULL AND run_id IS NULL "
        "AND attempt_id IS NULL AND model_call_id IS NULL))"
    )
    _task_frozen_guard(with_comparison=False)
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_comparison_attempt_id_format")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT fk_executor_task_comparison_attempt")
    op.execute("ALTER TABLE executor_task DROP COLUMN comparison_attempt_id")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT fk_comparison_work_current_attempt")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in (
        "am_check_comparison_page_profile", "am_check_comparison_version_order_chain",
        "am_check_comparison_upload_part_insert", "am_check_comparison_model_call_insert",
        "am_guard_comparison_state_edges",
    ):
        op.execute(f"DROP FUNCTION {function}()")
    op.execute("ALTER TABLE document_version DROP CONSTRAINT ck_document_version_comparison_pdf_no_bundle")
    op.execute("ALTER TABLE document_version DROP CONSTRAINT ck_document_version_upload_kind")
    op.execute("ALTER TABLE document_version DROP COLUMN upload_kind")
