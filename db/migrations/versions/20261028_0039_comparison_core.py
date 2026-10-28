"""The version comparison core: matrix builds, manual edits, accepted AI links, series, transitions and sheet-pair results.

Revision ID: 0039_comparison_core
Revises: 0038_comparison_foundation

`CMP-SEAL-C1` (wave C1 of `COMPARE-MODULES-PLAN`, `ADR-0025`). It creates the tables the C1 lanes
(`CMP-MATRIX-01`, `CMP-ENGINE-01`, `CMP-VIEWER-01`, `CMP-SERIES-01`, `CMP-VC-OVERVIEW-01`) implement
against, and nothing that implements them: the only rows it writes are the manual matrix edits that
carry the active ``0035`` approvals (decision 13), and no code reads or writes any other table. Every
table is reachable from ``project`` by foreign keys, so the project erase keeps its closure
(decision 7).

Tables (seven)
--------------
``comparison_matrix`` (``cmx_``) -- one **algorithmic build** of the matrix of a document set: the rows
the algorithm produced for the versions in one order revision, with the digest of the page profiles it
read (``profile_signature``), the rule and algorithm versions and the counts. Append-only. The
*effective* matrix is a read model over the latest build, the accepted AI links and the manual edits
(decision 3); a build that does not match the current order revision or the current profiles is stale.
Builds are numbered 1, 2, 3, ... per document without a gap, and one input set is built once.

``comparison_matrix_edit`` (``cme_``) -- the append-only history of manual edits of a document set,
numbered ``edit_no`` 1, 2, 3, ... without a gap (the pattern of ``0035``). A kind is ``link``,
``unlink``, ``mark_absent`` or ``undo`` (which names the edit it reverses, once). A page is a version
and a coordinate inside that immutable version, never a display number. An edit binds the version
order revision in force (``order_id``, empty for the document's own order). ``source`` is ``expert`` for
an act of ``applyComparisonMatrixEdits`` (it carries a command receipt) or ``migrated_sheet_link`` for an
approval of ``0035`` (decision 13), whose ``comparison_id``, ``sheet_link_id`` and ``link_revision`` are
in ``provenance``. The effective matrix at a revision is a function of the build and of this history; the
revision a client names is the pair (build, ``edit_no`` of the latest event).

``comparison_ai_link`` (``cak_``) -- an accepted AI link (decisions 3 and 14): append-only, bound to the
build it answered and to the cell state (``unmatched`` or ``doubtful``) it answered. **This revision only
creates the table; wave C2 writes it.**

``comparison_series`` (``cser_``) -- the comparison of every adjacent pair of versions of a document set
for one order revision and one matrix revision; ``input_sha256`` is the stored digest that staleness
compares (decision 21). A «Заново» is a new series that names the one it replaced.
``comparison_transition`` (``ctn_``) -- one adjacent pair of versions of a series with its stored summary
counts and verdict codes. ``comparison_sheet_pair`` (``ctp_``) -- one sheet pair of a transition: the two
pages (as profile identities), the link confidence and flags, the status and the post-phase records (permit
reconciliation and parts coverage); it points at a content-keyed result. ``comparison_sheet_pair_result``
(``csp_``) -- the **content-keyed** result of comparing two pages (decision 15): a ULID id and a unique
content-key digest that includes ``project_uid``, so a result is reused within a project only. The
digest is never a foreign key. The mask blob, stored once per pair that is not ``same``, is write-once.

Other changes
-------------
``comparison_work.comparison_series_id`` (nullable, frozen once set) so that a series can pause, resume and
cancel its items the way an upload does (``comparison_upload_id``). ``comparison_upload.compare_after_preparation``
(``NOT NULL DEFAULT false``, frozen): «После подготовки сравнить все соседние версии». Nothing else of ``0038``
is touched. The ``0035`` tables stay as they are: immutable history.

Data migration (``Q-CMP-8``)
----------------------------
Every **active** approval of ``comparison_sheet_link`` (an ``approved`` row with no ``withdrawn`` row of the
same ``sheet_link_id``) becomes one ``link`` edit with its actor, label and time and the ``0035`` ids in
``provenance``, numbered in the order of the approvals (time, then comparison and revision). It never
deletes or edits a ``0035`` row. It is idempotent: an approval that already has its edit is skipped (a unique
index on the ``0035`` link id, and a check before the insert), so running it again changes nothing.

Downgrade
---------
Refuses while any row of the seven tables exists **other than** the migrated edits, and while any
``comparison_work`` carries a series or any upload asked for the comparison after preparation: they exist
nowhere else (the pattern of ``0035``, ``0037`` and ``0038``). With none it deletes the migrated edits (their
source is ``0035``, which is untouched), drops this revision's own objects and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

from auditmanager.shared.identity.ulid import new_ulid

revision: str = "0039_comparison_core"
down_revision: str | None = "0038_comparison_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"
SHA256 = "^[0-9a-f]{64}$"
MAX_LABEL_LENGTH = 128
#: ``version_reader.MAX_VERSION_PAGES`` (``0021``): pages of a published version.
MAX_PAGE_NUMBER = 500

EDIT_KINDS: tuple[str, ...] = ("link", "unlink", "mark_absent", "undo")
EDIT_SOURCES: tuple[str, ...] = ("expert", "migrated_sheet_link")
ANSWERED_STATES: tuple[str, ...] = ("unmatched", "doubtful")
SERIES_STATES: tuple[str, ...] = ("queued", "running", "paused", "completed", "failed", "cancelled")
TRANSITION_STATES: tuple[str, ...] = ("queued", "running", "completed", "failed", "cancelled")
PAIR_STATES: tuple[str, ...] = ("queued", "computing", "done", "failed")
PAIR_STATUSES: tuple[str, ...] = (
    "same", "same_zones_changed", "different", "needs_review", "added", "removed", "unmatched",
)
RESULT_STATUSES: tuple[str, ...] = ("same", "same_zones_changed", "different", "needs_review")
CONFIDENCES: tuple[str, ...] = ("high", "medium", "group", "manual", "ai")

#: ``(table, from_state, to_state)``: the only state changes the database allows for these tables.
#: A series, a transition and a pair can be queued again (a «Досчитать» or a retry); a finished
#: pair never is.
EDGES: tuple[tuple[str, str, str], ...] = (
    ("comparison_series", "queued", "running"),
    ("comparison_series", "queued", "paused"),
    ("comparison_series", "queued", "failed"),
    ("comparison_series", "queued", "cancelled"),
    ("comparison_series", "running", "paused"),
    ("comparison_series", "running", "completed"),
    ("comparison_series", "running", "failed"),
    ("comparison_series", "running", "cancelled"),
    ("comparison_series", "paused", "queued"),
    ("comparison_series", "paused", "running"),
    ("comparison_series", "paused", "cancelled"),
    ("comparison_series", "completed", "queued"),
    ("comparison_series", "failed", "queued"),
    ("comparison_series", "cancelled", "queued"),
    ("comparison_transition", "queued", "running"),
    ("comparison_transition", "queued", "failed"),
    ("comparison_transition", "queued", "cancelled"),
    ("comparison_transition", "running", "completed"),
    ("comparison_transition", "running", "failed"),
    ("comparison_transition", "running", "cancelled"),
    ("comparison_transition", "running", "queued"),
    ("comparison_transition", "completed", "queued"),
    ("comparison_transition", "failed", "queued"),
    ("comparison_transition", "cancelled", "queued"),
    ("comparison_sheet_pair", "queued", "computing"),
    ("comparison_sheet_pair", "queued", "failed"),
    ("comparison_sheet_pair", "computing", "done"),
    ("comparison_sheet_pair", "computing", "failed"),
    ("comparison_sheet_pair", "computing", "queued"),
    ("comparison_sheet_pair", "failed", "queued"),
)

TABLES: tuple[str, ...] = (
    "comparison_matrix", "comparison_matrix_edit", "comparison_ai_link", "comparison_series",
    "comparison_transition", "comparison_sheet_pair_result", "comparison_sheet_pair",
)


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _id(column: str, prefix: str, *, nullable: bool = False) -> str:
    check = f"{column} ~ '^{prefix}_{ULID}$'"
    return f"({column} IS NULL OR {check})" if nullable else check


def _edges_values() -> str:
    return ", ".join(f"('{t}', '{a}', '{b}')" for t, a, b in EDGES)


_EDGE_FUNCTION = f"""
        CREATE FUNCTION am_guard_comparison_core_state_edges() RETURNS trigger
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
                      HINT = 'A comparison row moves only along the edges of migration 0039.';
        END
        $fn$;
        """

#: One check for the three tables that name a project and a document: the document is the project's.
_DOCUMENT_PROJECT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_core_document() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM document d
                 WHERE d.document_uid = NEW.document_uid AND d.project_uid = NEW.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: document % is not a document of project %',
                    NEW.document_uid, NEW.project_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'A comparison row names the project its document belongs to.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_MATRIX_CHAIN_FUNCTION = """
        CREATE FUNCTION am_check_comparison_matrix_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no integer;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('comparison_matrix:' || NEW.document_uid, 0));
            SELECT max(build_no) INTO last_no FROM comparison_matrix WHERE document_uid = NEW.document_uid;
            IF NEW.build_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: document % has build % and cannot take %',
                    NEW.document_uid, coalesce(last_no, 0), NEW.build_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Builds are numbered 1, 2, 3, ... without a gap.';
            END IF;
            IF NEW.order_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_version_order o
                 WHERE o.comparison_version_order_id = NEW.order_id
                   AND o.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: order revision % is not of document %',
                    NEW.order_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_EDIT_CHAIN_FUNCTION = f"""
        CREATE FUNCTION am_check_comparison_matrix_edit_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no integer;
            target record;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('comparison_matrix_edit:' || NEW.document_uid, 0));
            SELECT max(edit_no) INTO last_no FROM comparison_matrix_edit WHERE document_uid = NEW.document_uid;
            IF NEW.edit_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: document % has edit % and cannot take %',
                    NEW.document_uid, coalesce(last_no, 0), NEW.edit_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Edits are numbered 1, 2, 3, ... without a gap.';
            END IF;
            IF NEW.order_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_version_order o
                 WHERE o.comparison_version_order_id = NEW.order_id
                   AND o.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: order revision % is not of document %',
                    NEW.order_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.kind <> 'undo' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM document_version v
                     WHERE v.version_uid = NEW.page_version_uid AND v.document_uid = NEW.document_uid
                       AND NEW.page_number <= v.page_count
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: version % is not a version of document % with page %',
                        NEW.page_version_uid, NEW.document_uid, NEW.page_number
                        USING ERRCODE = 'AM001';
                END IF;
                IF NEW.other_version_uid IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM document_version v
                     WHERE v.version_uid = NEW.other_version_uid AND v.document_uid = NEW.document_uid
                       AND NEW.other_page_number <= v.page_count
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: version % is not a version of document % with page %',
                        NEW.other_version_uid, NEW.document_uid, NEW.other_page_number
                        USING ERRCODE = 'AM001';
                END IF;
                IF NEW.absent_version_uid IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM document_version v
                     WHERE v.version_uid = NEW.absent_version_uid AND v.document_uid = NEW.document_uid
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: version % is not a version of document %',
                        NEW.absent_version_uid, NEW.document_uid
                        USING ERRCODE = 'AM001';
                END IF;
            ELSE
                SELECT * INTO target FROM comparison_matrix_edit WHERE comparison_matrix_edit_id = NEW.undoes_edit_id;
                IF target.comparison_matrix_edit_id IS NULL
                   OR target.document_uid <> NEW.document_uid
                   OR target.kind = 'undo'
                   OR target.edit_no >= NEW.edit_no THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: edit % is not an earlier edit of document % that can be undone',
                        NEW.undoes_edit_id, NEW.document_uid
                        USING ERRCODE = 'AM001',
                              HINT = 'An undo names one earlier edit of the same document, never another undo.';
                END IF;
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_AI_LINK_FUNCTION = """
        CREATE FUNCTION am_check_comparison_ai_link() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM document_version a, document_version b
                 WHERE a.version_uid = NEW.page_version_uid AND a.document_uid = NEW.document_uid
                   AND NEW.page_number <= a.page_count
                   AND b.version_uid = NEW.other_version_uid AND b.document_uid = NEW.document_uid
                   AND NEW.other_page_number <= b.page_count
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the two pages of an AI link are pages of versions of document %',
                    NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_SERIES_FUNCTION = """
        CREATE FUNCTION am_check_comparison_series() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM comparison_matrix m
                 WHERE m.comparison_matrix_id = NEW.comparison_matrix_id
                   AND m.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: build % is not a build of document %',
                    NEW.comparison_matrix_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.order_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_version_order o
                 WHERE o.comparison_version_order_id = NEW.order_id
                   AND o.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: order revision % is not of document %',
                    NEW.order_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.restarted_from_series_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_series s
                 WHERE s.comparison_series_id = NEW.restarted_from_series_id
                   AND s.document_uid = NEW.document_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: series % is not a series of document %',
                    NEW.restarted_from_series_id, NEW.document_uid
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_TRANSITION_FUNCTION = """
        CREATE FUNCTION am_check_comparison_transition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF (SELECT count(*) FROM comparison_series s
                 JOIN document_version a ON a.document_uid = s.document_uid
                 JOIN document_version b ON b.document_uid = s.document_uid
                WHERE s.comparison_series_id = NEW.comparison_series_id
                  AND a.version_uid = NEW.source_version_uid
                  AND b.version_uid = NEW.target_version_uid) <> 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the two versions of transition % are not versions of the document of series %',
                    NEW.comparison_transition_id, NEW.comparison_series_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_RESULT_FUNCTION = """
        CREATE FUNCTION am_check_comparison_sheet_pair_result() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF (SELECT count(*) FROM comparison_page_profile a
                 JOIN document_version va ON va.version_uid = a.version_uid
                 JOIN document da ON da.document_uid = va.document_uid
                 JOIN comparison_page_profile b ON b.comparison_page_profile_id = NEW.page_b_profile_id
                 JOIN document_version vb ON vb.version_uid = b.version_uid
                 JOIN document db ON db.document_uid = vb.document_uid
                WHERE a.comparison_page_profile_id = NEW.page_a_profile_id
                  AND da.project_uid = NEW.project_uid AND db.project_uid = NEW.project_uid) <> 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the pages of result % are not pages of project %',
                    NEW.comparison_sheet_pair_result_id, NEW.project_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'A result is reused within one project only (ADR-0025 decision 15).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_PAIR_FUNCTION = """
        CREATE FUNCTION am_check_comparison_sheet_pair() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            t record;
        BEGIN
            SELECT * INTO t FROM comparison_transition WHERE comparison_transition_id = NEW.comparison_transition_id;
            IF NEW.page_a_profile_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_page_profile p
                 WHERE p.comparison_page_profile_id = NEW.page_a_profile_id
                   AND p.version_uid = t.source_version_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: page A of pair % is not a page of the older version of its transition',
                    NEW.comparison_sheet_pair_id
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.page_b_profile_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_page_profile p
                 WHERE p.comparison_page_profile_id = NEW.page_b_profile_id
                   AND p.version_uid = t.target_version_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: page B of pair % is not a page of the newer version of its transition',
                    NEW.comparison_sheet_pair_id
                    USING ERRCODE = 'AM001';
            END IF;
            IF NEW.result_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM comparison_sheet_pair_result r
                  JOIN comparison_transition tt ON tt.comparison_transition_id = NEW.comparison_transition_id
                  JOIN comparison_series s ON s.comparison_series_id = tt.comparison_series_id
                 WHERE r.comparison_sheet_pair_result_id = NEW.result_id
                   AND r.project_uid = s.project_uid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: result % is not a result of the project of pair %',
                    NEW.result_id, NEW.comparison_sheet_pair_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A result is reused within one project only (ADR-0025 decision 15).';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_FUNCTIONS: tuple[str, ...] = (
    "am_check_comparison_sheet_pair", "am_check_comparison_sheet_pair_result",
    "am_check_comparison_transition", "am_check_comparison_series", "am_check_comparison_ai_link",
    "am_check_comparison_matrix_edit_chain", "am_check_comparison_matrix_chain",
    "am_check_comparison_core_document", "am_guard_comparison_core_state_edges",
)

#: ``comparison_work``'s frozen list as ``0038`` left it, and with this revision's column.
_WORK_FROZEN = (
    "comparison_work_id", "project_uid", "module", "kind", "dedupe_key", "comparison_upload_id",
    "created_by_user_uid", "created_at",
)
_UPLOAD_FROZEN = (
    "comparison_upload_id", "project_uid", "declared_files", "declared_bytes", "declared_pages",
    "part_size_bytes", "actor_user_uid", "actor_label", "command_id", "created_at",
)


def upgrade() -> None:
    _functions()
    _tables()
    _alter_existing()
    _guards()
    _comments()
    _migrate_sheet_links()


def _functions() -> None:
    for function in (
        _EDGE_FUNCTION, _DOCUMENT_PROJECT_FUNCTION, _MATRIX_CHAIN_FUNCTION, _EDIT_CHAIN_FUNCTION,
        _AI_LINK_FUNCTION, _SERIES_FUNCTION, _TRANSITION_FUNCTION, _RESULT_FUNCTION, _PAIR_FUNCTION,
    ):
        op.execute(function)


def _tables() -> None:
    op.execute(
        f"""
        CREATE TABLE comparison_matrix (
            comparison_matrix_id text PRIMARY KEY,
            project_uid          text NOT NULL,
            document_uid         text NOT NULL,
            build_no             integer NOT NULL,
            order_id             text NULL,
            profile_signature    text NOT NULL,
            rules_version        text NOT NULL,
            algo_version         text NOT NULL,
            rows                 jsonb NOT NULL,
            unassigned           jsonb NOT NULL DEFAULT '[]'::jsonb,
            summary              jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            created_at           timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_matrix_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_order
                FOREIGN KEY (order_id) REFERENCES comparison_version_order (comparison_version_order_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_matrix_build UNIQUE (document_uid, build_no),
            CONSTRAINT uq_comparison_matrix_document UNIQUE (comparison_matrix_id, document_uid),
            CONSTRAINT ck_comparison_matrix_id_format CHECK ({_id('comparison_matrix_id', 'cmx')}),
            CONSTRAINT ck_comparison_matrix_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_matrix_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_matrix_order_id_format
                CHECK ({_id('order_id', 'cvo', nullable=True)}),
            CONSTRAINT ck_comparison_matrix_build_no CHECK (build_no >= 1),
            CONSTRAINT ck_comparison_matrix_profile_signature CHECK (profile_signature ~ '{SHA256}'),
            CONSTRAINT ck_comparison_matrix_rules_version
                CHECK (char_length(rules_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_matrix_algo_version
                CHECK (char_length(algo_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_matrix_rows_is_array CHECK (jsonb_typeof(rows) = 'array'),
            CONSTRAINT ck_comparison_matrix_unassigned_is_array
                CHECK (jsonb_typeof(unassigned) = 'array'),
            CONSTRAINT ck_comparison_matrix_summary_is_object CHECK (jsonb_typeof(summary) = 'object')
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_matrix_inputs ON comparison_matrix "
        "(document_uid, coalesce(order_id, ''), profile_signature, rules_version, algo_version);"
    )
    op.execute("CREATE INDEX ix_comparison_matrix_project ON comparison_matrix (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_matrix_order ON comparison_matrix (order_id) WHERE order_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_matrix_edit (
            comparison_matrix_edit_id text PRIMARY KEY,
            project_uid               text NOT NULL,
            document_uid              text NOT NULL,
            edit_no                   integer NOT NULL,
            batch_position            smallint NOT NULL DEFAULT 1,
            kind                      text NOT NULL,
            source                    text NOT NULL DEFAULT 'expert',
            page_version_uid          text NULL,
            page_number               integer NULL,
            other_version_uid         text NULL,
            other_page_number         integer NULL,
            absent_version_uid        text NULL,
            undoes_edit_id            text NULL,
            order_id                  text NULL,
            provenance                jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            actor_user_uid            text NOT NULL,
            actor_label               text NOT NULL,
            command_id                text NULL,
            decided_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_matrix_edit_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_page_version
                FOREIGN KEY (page_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_other_version
                FOREIGN KEY (other_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_absent_version
                FOREIGN KEY (absent_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_undoes
                FOREIGN KEY (undoes_edit_id) REFERENCES comparison_matrix_edit (comparison_matrix_edit_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_order
                FOREIGN KEY (order_id) REFERENCES comparison_version_order (comparison_version_order_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_matrix_edit_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_matrix_edit_no UNIQUE (document_uid, edit_no),
            CONSTRAINT uq_comparison_matrix_edit_undoes UNIQUE (undoes_edit_id),
            CONSTRAINT uq_comparison_matrix_edit_command_position UNIQUE (command_id, batch_position),
            CONSTRAINT ck_comparison_matrix_edit_id_format
                CHECK ({_id('comparison_matrix_edit_id', 'cme')}),
            CONSTRAINT ck_comparison_matrix_edit_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_matrix_edit_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_matrix_edit_version_uids_format CHECK (
                {_id('page_version_uid', 'ver', nullable=True)}
                AND {_id('other_version_uid', 'ver', nullable=True)}
                AND {_id('absent_version_uid', 'ver', nullable=True)}),
            CONSTRAINT ck_comparison_matrix_edit_undoes_edit_id_format
                CHECK ({_id('undoes_edit_id', 'cme', nullable=True)}),
            CONSTRAINT ck_comparison_matrix_edit_order_id_format
                CHECK ({_id('order_id', 'cvo', nullable=True)}),
            CONSTRAINT ck_comparison_matrix_edit_actor_user_uid_format
                CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_matrix_edit_command_id_format
                CHECK ({_id('command_id', 'cmd', nullable=True)}),
            CONSTRAINT ck_comparison_matrix_edit_edit_no CHECK (edit_no >= 1),
            CONSTRAINT ck_comparison_matrix_edit_batch_position CHECK (batch_position >= 1),
            CONSTRAINT ck_comparison_matrix_edit_kind CHECK (kind IN ({_sql_list(EDIT_KINDS)})),
            CONSTRAINT ck_comparison_matrix_edit_source CHECK (source IN ({_sql_list(EDIT_SOURCES)})),
            CONSTRAINT ck_comparison_matrix_edit_page_numbers CHECK (
                (page_number IS NULL OR page_number BETWEEN 1 AND {MAX_PAGE_NUMBER})
                AND (other_page_number IS NULL OR other_page_number BETWEEN 1 AND {MAX_PAGE_NUMBER})),
            CONSTRAINT ck_comparison_matrix_edit_shape CHECK (
                (kind = 'link'
                    AND page_version_uid IS NOT NULL AND page_number IS NOT NULL
                    AND other_version_uid IS NOT NULL AND other_page_number IS NOT NULL
                    AND absent_version_uid IS NULL AND undoes_edit_id IS NULL
                    AND page_version_uid <> other_version_uid)
                OR (kind = 'unlink'
                    AND page_version_uid IS NOT NULL AND page_number IS NOT NULL
                    AND other_version_uid IS NULL AND other_page_number IS NULL
                    AND absent_version_uid IS NULL AND undoes_edit_id IS NULL)
                OR (kind = 'mark_absent'
                    AND page_version_uid IS NOT NULL AND page_number IS NOT NULL
                    AND other_version_uid IS NULL AND other_page_number IS NULL
                    AND absent_version_uid IS NOT NULL AND undoes_edit_id IS NULL
                    AND page_version_uid <> absent_version_uid)
                OR (kind = 'undo'
                    AND page_version_uid IS NULL AND page_number IS NULL
                    AND other_version_uid IS NULL AND other_page_number IS NULL
                    AND absent_version_uid IS NULL AND undoes_edit_id IS NOT NULL)),
            CONSTRAINT ck_comparison_matrix_edit_provenance_is_object
                CHECK (jsonb_typeof(provenance) = 'object'),
            CONSTRAINT ck_comparison_matrix_edit_source_shape CHECK (
                (source = 'expert' AND command_id IS NOT NULL AND provenance = '{{}}'::jsonb)
                OR (source = 'migrated_sheet_link' AND kind = 'link' AND command_id IS NULL
                    AND provenance ?& ARRAY['comparison_id', 'sheet_link_id', 'link_revision'])),
            CONSTRAINT ck_comparison_matrix_edit_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n'))
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_matrix_edit_migrated ON comparison_matrix_edit "
        "(document_uid, (provenance ->> 'sheet_link_id')) WHERE source = 'migrated_sheet_link';"
    )
    op.execute("CREATE INDEX ix_comparison_matrix_edit_project ON comparison_matrix_edit (project_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_matrix_edit_order ON comparison_matrix_edit (order_id) "
        "WHERE order_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_ai_link (
            comparison_ai_link_id   text PRIMARY KEY,
            document_uid            text NOT NULL,
            comparison_matrix_id    text NOT NULL,
            page_version_uid        text NOT NULL,
            page_number             integer NOT NULL,
            other_version_uid       text NOT NULL,
            other_page_number       integer NOT NULL,
            answered_state          text NOT NULL,
            confidence              text NOT NULL DEFAULT 'high',
            comparison_model_call_id text NULL,
            details                 jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            created_at              timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_ai_link_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_link_matrix
                FOREIGN KEY (comparison_matrix_id, document_uid)
                REFERENCES comparison_matrix (comparison_matrix_id, document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_link_page_version
                FOREIGN KEY (page_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_link_other_version
                FOREIGN KEY (other_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_ai_link_model_call
                FOREIGN KEY (comparison_model_call_id)
                REFERENCES comparison_model_call (comparison_model_call_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_ai_link_pages UNIQUE
                (comparison_matrix_id, page_version_uid, page_number, other_version_uid, other_page_number),
            CONSTRAINT ck_comparison_ai_link_id_format CHECK ({_id('comparison_ai_link_id', 'cak')}),
            CONSTRAINT ck_comparison_ai_link_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_ai_link_matrix_id_format CHECK ({_id('comparison_matrix_id', 'cmx')}),
            CONSTRAINT ck_comparison_ai_link_version_uids_format
                CHECK ({_id('page_version_uid', 'ver')} AND {_id('other_version_uid', 'ver')}),
            CONSTRAINT ck_comparison_ai_link_model_call_id_format
                CHECK ({_id('comparison_model_call_id', 'cmc', nullable=True)}),
            CONSTRAINT ck_comparison_ai_link_page_numbers CHECK (
                page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}
                AND other_page_number BETWEEN 1 AND {MAX_PAGE_NUMBER}),
            CONSTRAINT ck_comparison_ai_link_versions_differ CHECK (page_version_uid <> other_version_uid),
            CONSTRAINT ck_comparison_ai_link_answered_state
                CHECK (answered_state IN ({_sql_list(ANSWERED_STATES)})),
            CONSTRAINT ck_comparison_ai_link_confidence CHECK (confidence = 'high'),
            CONSTRAINT ck_comparison_ai_link_details_is_object CHECK (jsonb_typeof(details) = 'object')
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_ai_link_document ON comparison_ai_link (document_uid);")
    op.execute(
        "CREATE INDEX ix_comparison_ai_link_model_call ON comparison_ai_link (comparison_model_call_id) "
        "WHERE comparison_model_call_id IS NOT NULL;"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_series (
            comparison_series_id     text PRIMARY KEY,
            project_uid              text NOT NULL,
            document_uid             text NOT NULL,
            state                    text NOT NULL DEFAULT 'queued',
            order_id                 text NULL,
            comparison_matrix_id     text NOT NULL,
            matrix_edit_no           integer NOT NULL,
            input_sha256             text NOT NULL,
            restarted_from_series_id text NULL,
            failure_reason           text NULL,
            actor_user_uid           text NOT NULL,
            actor_label              text NOT NULL,
            command_id               text NOT NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_series_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_series_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_series_order
                FOREIGN KEY (order_id) REFERENCES comparison_version_order (comparison_version_order_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_series_matrix
                FOREIGN KEY (comparison_matrix_id) REFERENCES comparison_matrix (comparison_matrix_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_series_restarted_from
                FOREIGN KEY (restarted_from_series_id) REFERENCES comparison_series (comparison_series_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_series_command
                FOREIGN KEY (command_id) REFERENCES command_record (command_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_series_command UNIQUE (command_id),
            CONSTRAINT ck_comparison_series_id_format CHECK ({_id('comparison_series_id', 'cser')}),
            CONSTRAINT ck_comparison_series_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_series_document_uid_format CHECK ({_id('document_uid', 'doc')}),
            CONSTRAINT ck_comparison_series_order_id_format
                CHECK ({_id('order_id', 'cvo', nullable=True)}),
            CONSTRAINT ck_comparison_series_matrix_id_format CHECK ({_id('comparison_matrix_id', 'cmx')}),
            CONSTRAINT ck_comparison_series_restarted_from_format
                CHECK ({_id('restarted_from_series_id', 'cser', nullable=True)}),
            CONSTRAINT ck_comparison_series_actor_user_uid_format CHECK ({_id('actor_user_uid', 'usr')}),
            CONSTRAINT ck_comparison_series_command_id_format CHECK ({_id('command_id', 'cmd')}),
            CONSTRAINT ck_comparison_series_state CHECK (state IN ({_sql_list(SERIES_STATES)})),
            CONSTRAINT ck_comparison_series_matrix_edit_no CHECK (matrix_edit_no >= 0),
            CONSTRAINT ck_comparison_series_input_sha256 CHECK (input_sha256 ~ '{SHA256}'),
            CONSTRAINT ck_comparison_series_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128)),
            CONSTRAINT ck_comparison_series_actor_label
                CHECK (char_length(actor_label) BETWEEN 1 AND {MAX_LABEL_LENGTH}
                       AND actor_label = btrim(actor_label, E' \\t\\r\\n'))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_series_document ON comparison_series (document_uid, created_at);"
    )
    op.execute("CREATE INDEX ix_comparison_series_project ON comparison_series (project_uid);")
    op.execute("CREATE INDEX ix_comparison_series_matrix ON comparison_series (comparison_matrix_id);")
    op.execute(
        "CREATE UNIQUE INDEX uq_comparison_series_live ON comparison_series (document_uid) "
        "WHERE state IN ('queued', 'running', 'paused');"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_transition (
            comparison_transition_id text PRIMARY KEY,
            comparison_series_id     text NOT NULL,
            transition_no            integer NOT NULL,
            source_version_uid       text NOT NULL,
            target_version_uid       text NOT NULL,
            state                    text NOT NULL DEFAULT 'queued',
            summary                  jsonb NULL,
            verdict                  jsonb NULL,
            failure_reason           text NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_transition_series
                FOREIGN KEY (comparison_series_id) REFERENCES comparison_series (comparison_series_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_transition_source_version
                FOREIGN KEY (source_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_transition_target_version
                FOREIGN KEY (target_version_uid) REFERENCES document_version (version_uid)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_transition_no UNIQUE (comparison_series_id, transition_no),
            CONSTRAINT uq_comparison_transition_pair
                UNIQUE (comparison_series_id, source_version_uid, target_version_uid),
            CONSTRAINT ck_comparison_transition_id_format
                CHECK ({_id('comparison_transition_id', 'ctn')}),
            CONSTRAINT ck_comparison_transition_series_id_format
                CHECK ({_id('comparison_series_id', 'cser')}),
            CONSTRAINT ck_comparison_transition_version_uids_format
                CHECK ({_id('source_version_uid', 'ver')} AND {_id('target_version_uid', 'ver')}),
            CONSTRAINT ck_comparison_transition_no CHECK (transition_no >= 1),
            CONSTRAINT ck_comparison_transition_versions_differ
                CHECK (source_version_uid <> target_version_uid),
            CONSTRAINT ck_comparison_transition_state
                CHECK (state IN ({_sql_list(TRANSITION_STATES)})),
            CONSTRAINT ck_comparison_transition_summary_is_object
                CHECK (summary IS NULL OR jsonb_typeof(summary) = 'object'),
            CONSTRAINT ck_comparison_transition_verdict_is_array
                CHECK (verdict IS NULL OR jsonb_typeof(verdict) = 'array'),
            CONSTRAINT ck_comparison_transition_completed_has_verdict
                CHECK (state <> 'completed' OR (summary IS NOT NULL AND verdict IS NOT NULL)),
            CONSTRAINT ck_comparison_transition_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128))
        );
        """
    )
    op.execute("CREATE INDEX ix_comparison_transition_series ON comparison_transition (comparison_series_id);")
    op.execute(
        "CREATE INDEX ix_comparison_transition_source_version ON comparison_transition (source_version_uid);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_transition_target_version ON comparison_transition (target_version_uid);"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_sheet_pair_result (
            comparison_sheet_pair_result_id text PRIMARY KEY,
            project_uid                     text NOT NULL,
            content_key                     text NOT NULL,
            algo_version                    text NOT NULL,
            status                          text NOT NULL,
            reasons                         jsonb NOT NULL DEFAULT '[]'::jsonb,
            channels                        jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            result                          jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            page_a_profile_id               text NOT NULL,
            page_b_profile_id               text NOT NULL,
            mask_blob_id                    text NULL,
            created_at                      timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_sheet_pair_result_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_result_page_a
                FOREIGN KEY (page_a_profile_id) REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_result_page_b
                FOREIGN KEY (page_b_profile_id) REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_result_mask_blob
                FOREIGN KEY (mask_blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_sheet_pair_result_content_key UNIQUE (project_uid, content_key),
            CONSTRAINT ck_comparison_sheet_pair_result_id_format
                CHECK ({_id('comparison_sheet_pair_result_id', 'csp')}),
            CONSTRAINT ck_comparison_sheet_pair_result_project_uid_format CHECK ({_id('project_uid', 'prj')}),
            CONSTRAINT ck_comparison_sheet_pair_result_page_ids_format CHECK (
                {_id('page_a_profile_id', 'cpr')} AND {_id('page_b_profile_id', 'cpr')}),
            CONSTRAINT ck_comparison_sheet_pair_result_mask_blob_id_format
                CHECK ({_id('mask_blob_id', 'blob', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_pair_result_content_key CHECK (content_key ~ '{SHA256}'),
            CONSTRAINT ck_comparison_sheet_pair_result_algo_version
                CHECK (char_length(algo_version) BETWEEN 1 AND 64),
            CONSTRAINT ck_comparison_sheet_pair_result_status
                CHECK (status IN ({_sql_list(RESULT_STATUSES)})),
            CONSTRAINT ck_comparison_sheet_pair_result_reasons_is_array
                CHECK (jsonb_typeof(reasons) = 'array'),
            CONSTRAINT ck_comparison_sheet_pair_result_channels_is_object
                CHECK (jsonb_typeof(channels) = 'object'),
            CONSTRAINT ck_comparison_sheet_pair_result_result_is_object
                CHECK (jsonb_typeof(result) = 'object'),
            CONSTRAINT ck_comparison_sheet_pair_result_same_has_no_mask
                CHECK (status <> 'same' OR mask_blob_id IS NULL)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_result_mask_blob ON comparison_sheet_pair_result "
        "(mask_blob_id) WHERE mask_blob_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_result_page_a ON comparison_sheet_pair_result (page_a_profile_id);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_result_page_b ON comparison_sheet_pair_result (page_b_profile_id);"
    )
    op.execute(
        f"""
        CREATE TABLE comparison_sheet_pair (
            comparison_sheet_pair_id text PRIMARY KEY,
            comparison_transition_id text NOT NULL,
            pair_no                  integer NOT NULL,
            state                    text NOT NULL DEFAULT 'queued',
            status                   text NULL,
            page_a_profile_id        text NULL,
            page_b_profile_id        text NULL,
            confidence               text NULL,
            flags                    jsonb NOT NULL DEFAULT '[]'::jsonb,
            result_id                text NULL,
            ai_dependent             boolean NOT NULL DEFAULT false,
            permit                   jsonb NULL,
            parts                    jsonb NULL,
            failure_reason           text NULL,
            created_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_comparison_sheet_pair_transition
                FOREIGN KEY (comparison_transition_id) REFERENCES comparison_transition (comparison_transition_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_page_a
                FOREIGN KEY (page_a_profile_id) REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_page_b
                FOREIGN KEY (page_b_profile_id) REFERENCES comparison_page_profile (comparison_page_profile_id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_comparison_sheet_pair_result
                FOREIGN KEY (result_id) REFERENCES comparison_sheet_pair_result (comparison_sheet_pair_result_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_comparison_sheet_pair_no UNIQUE (comparison_transition_id, pair_no),
            CONSTRAINT ck_comparison_sheet_pair_id_format
                CHECK ({_id('comparison_sheet_pair_id', 'ctp')}),
            CONSTRAINT ck_comparison_sheet_pair_transition_id_format
                CHECK ({_id('comparison_transition_id', 'ctn')}),
            CONSTRAINT ck_comparison_sheet_pair_page_ids_format CHECK (
                {_id('page_a_profile_id', 'cpr', nullable=True)}
                AND {_id('page_b_profile_id', 'cpr', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_pair_result_id_format
                CHECK ({_id('result_id', 'csp', nullable=True)}),
            CONSTRAINT ck_comparison_sheet_pair_no CHECK (pair_no >= 1),
            CONSTRAINT ck_comparison_sheet_pair_state CHECK (state IN ({_sql_list(PAIR_STATES)})),
            CONSTRAINT ck_comparison_sheet_pair_status
                CHECK (status IS NULL OR status IN ({_sql_list(PAIR_STATUSES)})),
            CONSTRAINT ck_comparison_sheet_pair_confidence
                CHECK (confidence IS NULL OR confidence IN ({_sql_list(CONFIDENCES)})),
            CONSTRAINT ck_comparison_sheet_pair_has_a_page
                CHECK (page_a_profile_id IS NOT NULL OR page_b_profile_id IS NOT NULL),
            CONSTRAINT ck_comparison_sheet_pair_status_when_done
                CHECK ((state = 'done') = (status IS NOT NULL)),
            CONSTRAINT ck_comparison_sheet_pair_result_when_compared CHECK (
                coalesce(status IN ('same', 'same_zones_changed', 'different', 'needs_review'), false)
                = (result_id IS NOT NULL)),
            CONSTRAINT ck_comparison_sheet_pair_compared_has_both_pages CHECK (
                status IS NULL OR status NOT IN ('same', 'same_zones_changed', 'different')
                OR (page_a_profile_id IS NOT NULL AND page_b_profile_id IS NOT NULL)),
            CONSTRAINT ck_comparison_sheet_pair_one_sided CHECK (
                status IS NULL
                OR status NOT IN ('added', 'removed')
                OR ((status = 'added') = (page_a_profile_id IS NULL)
                    AND (status = 'removed') = (page_b_profile_id IS NULL))),
            CONSTRAINT ck_comparison_sheet_pair_flags_is_array CHECK (jsonb_typeof(flags) = 'array'),
            CONSTRAINT ck_comparison_sheet_pair_permit_is_object
                CHECK (permit IS NULL OR jsonb_typeof(permit) = 'object'),
            CONSTRAINT ck_comparison_sheet_pair_parts_is_object
                CHECK (parts IS NULL OR jsonb_typeof(parts) = 'object'),
            CONSTRAINT ck_comparison_sheet_pair_failure_reason CHECK (
                (state = 'failed') = (failure_reason IS NOT NULL)
                AND (failure_reason IS NULL OR char_length(failure_reason) BETWEEN 1 AND 128))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_transition ON comparison_sheet_pair "
        "(comparison_transition_id, pair_no);"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_result ON comparison_sheet_pair (result_id) "
        "WHERE result_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_page_a ON comparison_sheet_pair (page_a_profile_id) "
        "WHERE page_a_profile_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_comparison_sheet_pair_page_b ON comparison_sheet_pair (page_b_profile_id) "
        "WHERE page_b_profile_id IS NOT NULL;"
    )


def _alter_existing() -> None:
    op.execute("ALTER TABLE comparison_work ADD COLUMN comparison_series_id text NULL")
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT fk_comparison_work_series "
        "FOREIGN KEY (comparison_series_id) REFERENCES comparison_series (comparison_series_id) "
        "ON DELETE RESTRICT"
    )
    op.execute(
        "ALTER TABLE comparison_work ADD CONSTRAINT ck_comparison_work_series_id_format "
        f"CHECK ({_id('comparison_series_id', 'cser', nullable=True)})"
    )
    op.execute(
        "CREATE INDEX ix_comparison_work_series ON comparison_work (comparison_series_id) "
        "WHERE comparison_series_id IS NOT NULL;"
    )
    op.execute(
        "ALTER TABLE comparison_upload "
        "ADD COLUMN compare_after_preparation boolean NOT NULL DEFAULT false"
    )
    _frozen("comparison_work", _WORK_FROZEN + ("comparison_series_id",))
    _frozen("comparison_upload", _UPLOAD_FROZEN + ("compare_after_preparation",))


def _frozen(table: str, columns: Sequence[str]) -> None:
    op.execute(f"DROP TRIGGER trg_{table}_frozen_guard ON {table}")
    op.execute(
        f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_sql_list(columns)})"
    )


def _guards() -> None:
    for table in ("comparison_series", "comparison_transition", "comparison_sheet_pair"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_state_edges BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_comparison_core_state_edges()"
        )
    frozen = {
        "comparison_series": (
            "comparison_series_id", "project_uid", "document_uid", "order_id", "comparison_matrix_id",
            "matrix_edit_no", "input_sha256", "restarted_from_series_id", "actor_user_uid",
            "actor_label", "command_id", "created_at",
        ),
        "comparison_transition": (
            "comparison_transition_id", "comparison_series_id", "transition_no", "source_version_uid",
            "target_version_uid", "created_at",
        ),
        "comparison_sheet_pair": (
            "comparison_sheet_pair_id", "comparison_transition_id", "pair_no", "page_a_profile_id",
            "page_b_profile_id", "created_at",
        ),
        "comparison_sheet_pair_result": (
            "comparison_sheet_pair_result_id", "project_uid", "content_key", "algo_version", "status",
            "reasons", "channels", "result", "page_a_profile_id", "page_b_profile_id", "created_at",
        ),
    }
    for table, columns in frozen.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_frozen_guard BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({_sql_list(columns)})"
        )
    op.execute(
        "CREATE TRIGGER trg_comparison_sheet_pair_result_write_once BEFORE UPDATE ON "
        "comparison_sheet_pair_result FOR EACH ROW EXECUTE FUNCTION "
        "am_guard_write_once_columns('mask_blob_id')"
    )
    for table in ("comparison_matrix", "comparison_matrix_edit", "comparison_ai_link"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    for table in ("comparison_matrix", "comparison_matrix_edit", "comparison_series"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_document BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_check_comparison_core_document()"
        )
    inserts = {
        "comparison_matrix": ("chain", "am_check_comparison_matrix_chain"),
        "comparison_matrix_edit": ("chain", "am_check_comparison_matrix_edit_chain"),
        "comparison_ai_link": ("pages", "am_check_comparison_ai_link"),
        "comparison_series": ("inputs", "am_check_comparison_series"),
        "comparison_transition": ("versions", "am_check_comparison_transition"),
        "comparison_sheet_pair_result": ("pages", "am_check_comparison_sheet_pair_result"),
        "comparison_sheet_pair": ("pages", "am_check_comparison_sheet_pair"),
    }
    for table, (suffix, function) in inserts.items():
        op.execute(
            f"CREATE TRIGGER trg_{table}_{suffix} BEFORE INSERT ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {function}()"
        )


def _comments() -> None:
    comments = {
        "comparison_matrix": (
            "CMP-SEAL-C1. One algorithmic build of the matrix of a document set (ADR-0025 decisions 3 "
            "and 14), append-only (am_immutable_row), numbered without a gap per document "
            "(am_check_comparison_matrix_chain). The effective matrix is a read model over the latest "
            "build, the accepted AI links and the manual edits."
        ),
        "comparison_matrix_edit": (
            "CMP-SEAL-C1. The append-only history of manual matrix edits of a document set, numbered "
            "without a gap (am_check_comparison_matrix_edit_chain): link, unlink, mark_absent and undo. "
            "A page is a version and a coordinate in it. A migrated row carries the 0035 ids of the "
            "approval it came from in provenance (ADR-0025 decision 13)."
        ),
        "comparison_ai_link": (
            "CMP-SEAL-C1. An accepted AI link (ADR-0025 decisions 3 and 14), append-only, bound to the "
            "build and the cell state it answered. Created empty; wave C2 writes it."
        ),
        "comparison_series": (
            "CMP-SEAL-C1. The comparison of every adjacent pair of versions of a document set for one "
            "order revision and one matrix revision (ADR-0025 decision 21); input_sha256 is the stored "
            "digest that staleness compares. At most one live series per document."
        ),
        "comparison_transition": (
            "CMP-SEAL-C1. One adjacent pair of versions of a series, with its stored summary counts and "
            "deterministic verdict codes once completed."
        ),
        "comparison_sheet_pair": (
            "CMP-SEAL-C1. One sheet pair of a transition: the two pages as profile identities, the link "
            "confidence and flags, the status and the post-phase records. It points at a content-keyed "
            "result; two pairs of equal content share one."
        ),
        "comparison_sheet_pair_result": (
            "CMP-SEAL-C1. The content-keyed result of comparing two pages (ADR-0025 decision 15): a ULID "
            "id and a unique digest that includes project_uid, so a result is reused within a project "
            "only. Frozen apart from the write-once mask blob, which is stored once per pair that is not "
            "same."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")
    op.execute(
        "COMMENT ON COLUMN comparison_matrix_edit.actor_user_uid IS "
        "'The account that made the edit (the approver, for a migrated row). Deliberately not a foreign "
        "key: the register of account references belongs to the access context.';"
    )
    op.execute(
        "COMMENT ON COLUMN comparison_series.actor_user_uid IS "
        "'The account that started the series. Deliberately not a foreign key: the register of "
        "account references belongs to the access context.';"
    )


def _migrate_sheet_links() -> None:
    """Every active approval of ``comparison_sheet_link`` becomes one ``link`` edit (Q-CMP-8)."""
    bind = op.get_bind()
    rows = bind.execute(
        text(
            """
            SELECT a.project_uid, a.document_uid, a.comparison_id, a.link_revision, a.sheet_link_id,
                   a.source_version_uid, a.source_page_number, a.target_version_uid,
                   a.target_page_number, a.source_page_text_sha256, a.target_page_text_sha256,
                   a.suggestion_sha256, a.actor_user_uid, a.actor_label, a.decided_at
              FROM comparison_sheet_link a
             WHERE a.event_kind = 'approved'
               AND NOT EXISTS (
                   SELECT 1 FROM comparison_sheet_link w
                    WHERE w.comparison_id = a.comparison_id
                      AND w.sheet_link_id = a.sheet_link_id
                      AND w.event_kind = 'withdrawn')
               AND NOT EXISTS (
                   SELECT 1 FROM comparison_matrix_edit e
                    WHERE e.document_uid = a.document_uid
                      AND e.source = 'migrated_sheet_link'
                      AND e.provenance ->> 'sheet_link_id' = a.sheet_link_id)
             ORDER BY a.decided_at, a.comparison_id, a.link_revision
            """
        )
    ).mappings().all()
    next_no: dict[str, int] = {}
    for row in rows:
        document = row["document_uid"]
        if document not in next_no:
            next_no[document] = int(
                bind.execute(
                    text("SELECT coalesce(max(edit_no), 0) FROM comparison_matrix_edit WHERE document_uid = :d"),
                    {"d": document},
                ).scalar_one()
            )
        next_no[document] += 1
        bind.execute(
            text(
                """
                INSERT INTO comparison_matrix_edit (
                    comparison_matrix_edit_id, project_uid, document_uid, edit_no, batch_position, kind, source,
                    page_version_uid, page_number, other_version_uid, other_page_number, provenance,
                    actor_user_uid, actor_label, command_id, decided_at)
                VALUES (
                    :edit_id, :project_uid, :document_uid, :edit_no, 1, 'link', 'migrated_sheet_link',
                    :source_version_uid, :source_page_number, :target_version_uid, :target_page_number,
                    CAST(:provenance AS jsonb), :actor_user_uid, :actor_label, NULL, :decided_at)
                """
            ),
            {
                "edit_id": f"cme_{new_ulid()}",
                "project_uid": row["project_uid"],
                "document_uid": document,
                "edit_no": next_no[document],
                "source_version_uid": row["source_version_uid"],
                "source_page_number": row["source_page_number"],
                "target_version_uid": row["target_version_uid"],
                "target_page_number": row["target_page_number"],
                "provenance": _provenance(row),
                "actor_user_uid": row["actor_user_uid"],
                "actor_label": row["actor_label"],
                "decided_at": row["decided_at"],
            },
        )


def _provenance(row: dict) -> str:
    import json

    return json.dumps(
        {
            "comparison_id": row["comparison_id"],
            "sheet_link_id": row["sheet_link_id"],
            "link_revision": int(row["link_revision"]),
            "source_page_text_sha256": row["source_page_text_sha256"],
            "target_page_text_sha256": row["target_page_text_sha256"],
            "suggestion_sha256": row["suggestion_sha256"],
        },
        sort_keys=True,
    )


def downgrade() -> None:
    """Refuse while data exists that is not a migrated edit, otherwise drop this revision's own objects."""
    bind = op.get_bind()
    occupied = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
        for table in TABLES
        if table != "comparison_matrix_edit"
    }
    occupied["comparison_matrix_edit (expert)"] = int(
        bind.execute(
            text("SELECT count(*) FROM comparison_matrix_edit WHERE source <> 'migrated_sheet_link'")
        ).scalar_one()
    )
    occupied["comparison_work (series)"] = int(
        bind.execute(
            text("SELECT count(*) FROM comparison_work WHERE comparison_series_id IS NOT NULL")
        ).scalar_one()
    )
    occupied["comparison_upload (compare_after_preparation)"] = int(
        bind.execute(
            text("SELECT count(*) FROM comparison_upload WHERE compare_after_preparation")
        ).scalar_one()
    )
    if any(occupied.values()):
        rendered = ", ".join(f"{name}={count}" for name, count in occupied.items() if count)
        raise RuntimeError(
            f"0039 downgrade refused: comparison data exists nowhere else ({rendered}); "
            "restore a backup instead of downgrading"
        )
    # The migrated edits are copies of 0035 rows, which this revision never touched: they go with
    # their table. The table is append-only, so its trigger is dropped before the rows are.
    op.execute("DROP TRIGGER trg_comparison_matrix_edit_immutable ON comparison_matrix_edit")
    op.execute("DELETE FROM comparison_matrix_edit")
    op.execute("DROP INDEX ix_comparison_work_series")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT ck_comparison_work_series_id_format")
    op.execute("ALTER TABLE comparison_work DROP CONSTRAINT fk_comparison_work_series")
    _frozen("comparison_work", _WORK_FROZEN)
    op.execute("ALTER TABLE comparison_work DROP COLUMN comparison_series_id")
    _frozen("comparison_upload", _UPLOAD_FROZEN)
    op.execute("ALTER TABLE comparison_upload DROP COLUMN compare_after_preparation")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in _FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
