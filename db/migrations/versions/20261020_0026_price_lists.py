"""Project price lists and vendor lists: the storage of «Оптимизация проекта».

Revision ID: 0026_price_lists
Revises: 0025_work_assignments

`W60-PRICE-LIST-01` (``CODE-FIRST-SCOPE-W58-W63.md`` W60 PROJECT-OPT; ``ROADMAP-TO-BETA.md``
§10.1 A-3..A-5: a money figure only from an uploaded price list; a global vendor list per
section kept by an administrator, overridable by a project's own list, each change versioned).

What this revision adds
-----------------------
``price_list_revision`` -- one row per uploaded price list of one project: its opaque identity
(``prl_<ULID>``), the project, a per-project ``revision_number`` (a display order, never an
identity; the current price list is the highest one, found by query), the uploading expert and
when, the **binding to the uploaded file's Blob** (``blob_id`` with the file's SHA-256, size and
media type, which must equal the ``available`` Blob row at insert -- ``am_check_price_list_blob``),
the detected format, the uploaded file name (display only), the declared default currency, the
deterministic parse report and its three row counts. Written once and never updated or deleted
(``am_immutable_row``).

``price_list_position`` -- the parsed positions of one revision: ``prp_<ULID>``, the source row
number (as the spreadsheet shows it; unique per revision and never an identity), optional code
and mark, name, unit, the unit price (an exact ``numeric``: positive, below 10^14, at most six
decimals -- nothing is rounded on the way in), the ISO 4217 currency, optional vendor and
optional section (one of the fifteen codes). Immutable.

``am_require_price_list_positions`` -- a deferred constraint trigger: a revision is refused at
COMMIT unless exactly ``accepted_row_count`` positions name it, so no revision is ever visible
with a partial position set.

``vendor_list_revision`` -- one revision of a vendor list for one section: ``vnl_<ULID>``, the
scope (``global``, with no project; or ``project``), the section, the mode (``list``: these
entries apply, possibly none; ``inherit``: a project revision that removes the project's
override, with no entries), a ``revision_number`` per (scope, project, section) -- an order,
not an identity -- the entry count, the acting account and when. Immutable; the effective list
is a query (the latest project revision when its mode is ``list``, else the latest global one).

``vendor_list_entry`` -- the entries of one revision, in order: material or equipment group
(optional), vendor (required) and note (optional). Immutable.
``am_require_vendor_list_entries`` -- the same deferred count check as for positions.

**Account references.** ``uploaded_by_user_uid`` and ``set_by_user_uid`` are ``RESTRICT``
foreign keys to ``app_user`` and are registered in ``auditmanager.access.references``.

**No backfill.** Nothing existed before; the upgrade creates empty tables beside existing rows
and changes none of them.

Downgrade
---------
Drops the four tables and the three trigger functions -- and nothing else. The Blob rows and
objects the price lists were bound to stay (content-addressed and shared); the downgrade names
how many revisions, positions and vendor-list revisions it drops.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0026_price_lists"
down_revision: str | None = "0025_work_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.price_lists")

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: The current fifteen sections, restated rather than imported (a migration is history and
#: must not move when the application does); ``tests/unit/optimisation`` holds this tuple equal
#: to ``auditmanager.optimisation.policy.SECTION_ORDER`` and ``sections.public.SECTION_CODES``.
PROJECT_SECTIONS: tuple[str, ...] = (
    "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX", "POS", "PS",
)

#: The accepted source formats and their media types, restated as
#: ``auditmanager.optimisation.parsing.MEDIA_TYPES`` (held equal by the same test).
SOURCE_MEDIA_TYPES: dict[str, str] = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

#: Bounds restated from ``auditmanager.optimisation.parsing.limits`` and ``policy``.
MAX_DATA_ROWS = 20000
MAX_SOURCE_FILENAME = 255
MAX_NAME_LENGTH = 2000
MAX_CODE_LENGTH = 200
MAX_MARK_LENGTH = 500
MAX_UNIT_LENGTH = 50
MAX_VENDOR_LENGTH = 500
MAX_VENDOR_LIST_ENTRIES = 500
MAX_MATERIAL_LENGTH = 500
MAX_ENTRY_NOTE_LENGTH = 1000

VENDOR_LIST_SCOPES: tuple[str, ...] = ("global", "project")
VENDOR_LIST_MODES: tuple[str, ...] = ("list", "inherit")


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _length(column: str, maximum: int, *, nullable: bool) -> str:
    check = f"char_length({column}) BETWEEN 1 AND {maximum}"
    return f"{column} IS NULL OR {check}" if nullable else check


def upgrade() -> None:
    _create_price_list_revision()
    _create_price_list_position()
    _create_vendor_list_revision()
    _create_vendor_list_entry()


def _create_price_list_revision() -> None:
    media_types = _sql_list(tuple(SOURCE_MEDIA_TYPES.values()))
    format_media = " OR ".join(
        f"(source_format = '{fmt}' AND media_type = '{media}')"
        for fmt, media in SOURCE_MEDIA_TYPES.items()
    )
    op.execute(
        f"""
        CREATE TABLE price_list_revision (
            price_list_id         text PRIMARY KEY,
            project_uid           text NOT NULL,
            revision_number       integer NOT NULL,
            uploaded_by_user_uid  text NOT NULL,
            uploaded_at           timestamptz NOT NULL DEFAULT now(),
            blob_id               text NOT NULL,
            sha256                text NOT NULL,
            size_bytes            bigint NOT NULL,
            media_type            text NOT NULL,
            source_format         text NOT NULL,
            source_filename       text NOT NULL,
            default_currency      text NULL,
            parse_report          jsonb NOT NULL,
            data_row_count        integer NOT NULL,
            accepted_row_count    integer NOT NULL,
            skipped_row_count     integer NOT NULL,
            CONSTRAINT fk_price_list_revision_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_price_list_revision_uploaded_by
                FOREIGN KEY (uploaded_by_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_price_list_revision_blob
                FOREIGN KEY (blob_id) REFERENCES blob (blob_id) ON DELETE RESTRICT,
            CONSTRAINT uq_price_list_revision_project_uid_revision_number
                UNIQUE (project_uid, revision_number),
            CONSTRAINT ck_price_list_revision_price_list_id_format
                CHECK (price_list_id ~ '^prl_{ULID}$'),
            CONSTRAINT ck_price_list_revision_project_uid_format
                CHECK (project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_price_list_revision_uploaded_by_user_uid_format
                CHECK (uploaded_by_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_price_list_revision_blob_id_format
                CHECK (blob_id ~ '^blob_{ULID}$'),
            CONSTRAINT ck_price_list_revision_revision_number CHECK (revision_number >= 1),
            CONSTRAINT ck_price_list_revision_sha256 CHECK (sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_price_list_revision_size_bytes CHECK (size_bytes >= 1),
            CONSTRAINT ck_price_list_revision_media_type CHECK (media_type IN ({media_types})),
            CONSTRAINT ck_price_list_revision_source_format
                CHECK (source_format IN ({_sql_list(tuple(SOURCE_MEDIA_TYPES))})),
            CONSTRAINT ck_price_list_revision_format_media CHECK ({format_media}),
            CONSTRAINT ck_price_list_revision_source_filename
                CHECK (
                    {_length('source_filename', MAX_SOURCE_FILENAME, nullable=False)}
                    AND source_filename !~ '[\\x01-\\x1f/\\\\]'
                ),
            CONSTRAINT ck_price_list_revision_default_currency
                CHECK (default_currency IS NULL OR default_currency ~ '^[A-Z]{{3}}$'),
            CONSTRAINT ck_price_list_revision_parse_report
                CHECK (jsonb_typeof(parse_report) = 'object'),
            CONSTRAINT ck_price_list_revision_row_counts
                CHECK (
                    accepted_row_count >= 1
                    AND skipped_row_count >= 0
                    AND data_row_count = accepted_row_count + skipped_row_count
                    AND data_row_count <= {MAX_DATA_ROWS}
                )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_price_list_revision_blob ON price_list_revision (blob_id);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_price_list_revision_immutable
            BEFORE UPDATE OR DELETE ON price_list_revision
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_check_price_list_blob() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM blob
                WHERE blob_id = NEW.blob_id
                  AND state = 'available'
                  AND sha256 = NEW.sha256
                  AND size_bytes = NEW.size_bytes
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: price list % names blob % that is not '
                    'available with the recorded digest and size',
                    NEW.price_list_id, NEW.blob_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A price list is bound to its uploaded file only after the '
                                 'Blob is published and marked available, in the same '
                                 'transaction.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_price_list_revision_blob_available
            BEFORE INSERT ON price_list_revision
            FOR EACH ROW EXECUTE FUNCTION am_check_price_list_blob();
        """
    )
    op.execute(
        "COMMENT ON TABLE price_list_revision IS "
        "'W60-PRICE-LIST-01. One uploaded price list (CSV or XLSX) of one project, bound to "
        "its file''s available Blob. Written once and never updated or deleted "
        "(am_immutable_row). revision_number orders a project''s revisions and is never an "
        "identity; the current price list is the highest one. source_filename is display "
        "only.';"
    )


def _create_price_list_position() -> None:
    op.execute(
        f"""
        CREATE TABLE price_list_position (
            price_list_position_id  text PRIMARY KEY,
            price_list_id           text NOT NULL,
            row_number              integer NOT NULL,
            code                    text NULL,
            name                    text NOT NULL,
            mark                    text NULL,
            unit                    text NOT NULL,
            unit_price              numeric NOT NULL,
            currency                text NOT NULL,
            vendor                  text NULL,
            section_code            text NULL,
            CONSTRAINT fk_price_list_position_price_list
                FOREIGN KEY (price_list_id) REFERENCES price_list_revision (price_list_id)
                ON DELETE RESTRICT,
            CONSTRAINT uq_price_list_position_price_list_id_row_number
                UNIQUE (price_list_id, row_number),
            CONSTRAINT ck_price_list_position_price_list_position_id_format
                CHECK (price_list_position_id ~ '^prp_{ULID}$'),
            CONSTRAINT ck_price_list_position_price_list_id_format
                CHECK (price_list_id ~ '^prl_{ULID}$'),
            CONSTRAINT ck_price_list_position_row_number CHECK (row_number >= 1),
            CONSTRAINT ck_price_list_position_code
                CHECK ({_length('code', MAX_CODE_LENGTH, nullable=True)}),
            CONSTRAINT ck_price_list_position_name
                CHECK ({_length('name', MAX_NAME_LENGTH, nullable=False)}),
            CONSTRAINT ck_price_list_position_mark
                CHECK ({_length('mark', MAX_MARK_LENGTH, nullable=True)}),
            CONSTRAINT ck_price_list_position_unit
                CHECK ({_length('unit', MAX_UNIT_LENGTH, nullable=False)}),
            CONSTRAINT ck_price_list_position_unit_price
                CHECK (unit_price > 0 AND unit_price < 1e14 AND scale(unit_price) <= 6),
            CONSTRAINT ck_price_list_position_currency CHECK (currency ~ '^[A-Z]{{3}}$'),
            CONSTRAINT ck_price_list_position_vendor
                CHECK ({_length('vendor', MAX_VENDOR_LENGTH, nullable=True)}),
            CONSTRAINT ck_price_list_position_section_code
                CHECK (section_code IS NULL OR section_code IN ({_sql_list(PROJECT_SECTIONS)}))
        );
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_price_list_position_immutable
            BEFORE UPDATE OR DELETE ON price_list_position
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE price_list_position IS "
        "'W60-PRICE-LIST-01. One parsed position of one price-list revision. row_number is "
        "the source row as the spreadsheet shows it, unique per revision and never an "
        "identity. unit_price is exact (no rounding on the way in). Never updated or deleted "
        "(am_immutable_row).';"
    )
    op.execute(
        """
        CREATE FUNCTION am_require_price_list_positions() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            found integer;
        BEGIN
            SELECT count(*) INTO found FROM price_list_position
            WHERE price_list_id = NEW.price_list_id;
            IF found <> NEW.accepted_row_count THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: price list % has % position(s), '
                    'declares %', NEW.price_list_id, found, NEW.accepted_row_count
                    USING ERRCODE = 'AM001',
                          HINT = 'A price-list revision is written together with every '
                                 'accepted position in one transaction.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_price_list_revision_has_positions
            AFTER INSERT ON price_list_revision
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_require_price_list_positions();
        """
    )


def _create_vendor_list_revision() -> None:
    op.execute(
        f"""
        CREATE TABLE vendor_list_revision (
            vendor_list_id   text PRIMARY KEY,
            scope            text NOT NULL,
            project_uid      text NULL,
            section_code     text NOT NULL,
            mode             text NOT NULL,
            revision_number  integer NOT NULL,
            entry_count      integer NOT NULL,
            set_by_user_uid  text NOT NULL,
            set_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_vendor_list_revision_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_vendor_list_revision_set_by
                FOREIGN KEY (set_by_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT uq_vendor_list_revision_scope_revision_number
                UNIQUE NULLS NOT DISTINCT (project_uid, section_code, revision_number),
            CONSTRAINT ck_vendor_list_revision_vendor_list_id_format
                CHECK (vendor_list_id ~ '^vnl_{ULID}$'),
            CONSTRAINT ck_vendor_list_revision_project_uid_format
                CHECK (project_uid IS NULL OR project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_vendor_list_revision_set_by_user_uid_format
                CHECK (set_by_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_vendor_list_revision_scope
                CHECK (scope IN ({_sql_list(VENDOR_LIST_SCOPES)})),
            CONSTRAINT ck_vendor_list_revision_scope_project
                CHECK ((scope = 'global') = (project_uid IS NULL)),
            CONSTRAINT ck_vendor_list_revision_section_code
                CHECK (section_code IN ({_sql_list(PROJECT_SECTIONS)})),
            CONSTRAINT ck_vendor_list_revision_mode
                CHECK (mode IN ({_sql_list(VENDOR_LIST_MODES)})),
            CONSTRAINT ck_vendor_list_revision_inherit_shape
                CHECK (mode = 'list' OR (scope = 'project' AND entry_count = 0)),
            CONSTRAINT ck_vendor_list_revision_revision_number CHECK (revision_number >= 1),
            CONSTRAINT ck_vendor_list_revision_entry_count
                CHECK (entry_count BETWEEN 0 AND {MAX_VENDOR_LIST_ENTRIES})
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_vendor_list_revision_set_by ON vendor_list_revision (set_by_user_uid);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_vendor_list_revision_immutable
            BEFORE UPDATE OR DELETE ON vendor_list_revision
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE vendor_list_revision IS "
        "'W60-PRICE-LIST-01. One revision of a vendor list of one section: global (an "
        "administrator''s, no project) or a project override (an expert''s; mode inherit "
        "removes the override). revision_number orders one (project, section) history and is "
        "never an identity. The effective list is a query. Never updated or deleted "
        "(am_immutable_row).';"
    )


def _create_vendor_list_entry() -> None:
    op.execute(
        f"""
        CREATE TABLE vendor_list_entry (
            vendor_list_id  text NOT NULL,
            ordinal         integer NOT NULL,
            material        text NULL,
            vendor          text NOT NULL,
            note            text NULL,
            CONSTRAINT pk_vendor_list_entry PRIMARY KEY (vendor_list_id, ordinal),
            CONSTRAINT fk_vendor_list_entry_vendor_list
                FOREIGN KEY (vendor_list_id) REFERENCES vendor_list_revision (vendor_list_id)
                ON DELETE RESTRICT,
            CONSTRAINT ck_vendor_list_entry_vendor_list_id_format
                CHECK (vendor_list_id ~ '^vnl_{ULID}$'),
            CONSTRAINT ck_vendor_list_entry_ordinal
                CHECK (ordinal BETWEEN 1 AND {MAX_VENDOR_LIST_ENTRIES}),
            CONSTRAINT ck_vendor_list_entry_material
                CHECK ({_length('material', MAX_MATERIAL_LENGTH, nullable=True)}),
            CONSTRAINT ck_vendor_list_entry_vendor
                CHECK ({_length('vendor', MAX_VENDOR_LENGTH, nullable=False)}),
            CONSTRAINT ck_vendor_list_entry_note
                CHECK ({_length('note', MAX_ENTRY_NOTE_LENGTH, nullable=True)})
        );
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_vendor_list_entry_immutable
            BEFORE UPDATE OR DELETE ON vendor_list_entry
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE vendor_list_entry IS "
        "'W60-PRICE-LIST-01. One entry of one vendor-list revision, in order: material or "
        "equipment group (optional), vendor (required), note (optional). ordinal is an order "
        "inside the revision, never an identity. Never updated or deleted "
        "(am_immutable_row).';"
    )
    op.execute(
        """
        CREATE FUNCTION am_require_vendor_list_entries() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            found integer;
        BEGIN
            SELECT count(*) INTO found FROM vendor_list_entry
            WHERE vendor_list_id = NEW.vendor_list_id;
            IF found <> NEW.entry_count THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: vendor list % has % entr(ies), declares %',
                    NEW.vendor_list_id, found, NEW.entry_count
                    USING ERRCODE = 'AM001',
                          HINT = 'A vendor-list revision is written together with every '
                                 'entry in one transaction.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_vendor_list_revision_has_entries
            AFTER INSERT ON vendor_list_revision
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_require_vendor_list_entries();
        """
    )


def downgrade() -> None:
    """Drop the four tables and the three trigger functions; nothing else is touched."""
    bind = op.get_bind()
    counts = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
        for table in (
            "price_list_revision",
            "price_list_position",
            "vendor_list_revision",
            "vendor_list_entry",
        )
    }
    if any(counts.values()):
        _log.warning(
            "0026_price_lists downgrade: %d price-list revision(s) with %d position(s) and "
            "%d vendor-list revision(s) with %d entr(ies) exist nowhere else and are dropped "
            "with their tables; the bound Blob rows and objects are kept.",
            counts["price_list_revision"],
            counts["price_list_position"],
            counts["vendor_list_revision"],
            counts["vendor_list_entry"],
        )
    op.execute("DROP TABLE vendor_list_entry;")
    op.execute("DROP TABLE vendor_list_revision;")
    op.execute("DROP TABLE price_list_position;")
    op.execute("DROP TABLE price_list_revision;")
    op.execute("DROP FUNCTION am_require_vendor_list_entries();")
    op.execute("DROP FUNCTION am_require_price_list_positions();")
    op.execute("DROP FUNCTION am_check_price_list_blob();")
