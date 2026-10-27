"""Analysis presets: a named, saved choice of the executor a run starts on, and the run's record of it.

Revision ID: 0037_analysis_presets
Revises: 0036_cite_partition_v3

`ANALYSIS-PRESETS-01` (PW5 lane PR; owner's `R-146av`, «Строить пресеты»). The premise of the lane
(task file, P-02 to P-05) is that a run start selects exactly one setting per run: the executor
connection (``startRun.executor_connection_id``). The cost ceiling is one process-wide setting and no
threshold is an input of a start, so a preset is **a name plus an executor connection**; nothing else
is stored because nothing else is selectable.

What this revision adds
-----------------------
``analysis_preset_revision`` -- one **append-only** table; every row is one revision of one preset.
Changing a preset is a new row, archiving it is a new row (``state = 'archived'``), and no row is ever
updated or deleted (``am_immutable_row``, SQLSTATE ``AM003``). A preset is identified by ``preset_id``
for its whole life; its name is a label and never an identity, so a rename is a new revision under the
same ``preset_id``.

Identities are ``evt_<ULID>`` (``AuditEventId``): the registry of identifier prefixes lives in the domain
contract and in ``auditmanager.shared.identity``, which this lane does not own, and ``0035`` gave
``comparison_summary.summary_id`` the same identity. Here **every revision's id is the id of the audit
event that records it** (written in the same transaction), and a preset's identity is the id of its
first revision: ``CHECK ((revision_no = 1) = (preset_id = preset_revision_id))``. A dedicated prefix is a
mechanical change in those other places and a rewrite of an empty table.

``am_check_analysis_preset_chain`` -- BEFORE INSERT, ``AM001``. First it takes one fixed
``pg_advisory_xact_lock``: a preset write is rare and an administrator's, the application role holds no
UPDATE privilege and so no row lock to lean on, and one lock for the family is the simplest correct
serialisation. Then: revision 1 starts a chain and only while fewer than 100 presets exist; revision
n needs revision n - 1 of the same preset, and that one is ``active`` (nothing follows an archived
revision); an ``archived`` revision repeats the previous revision's name and connection (an archive
changes the state and nothing else); an ``active`` revision needs a connection that is not archived and
a name that the **latest** revision of no other preset holds while ``active`` (compared without regard
to case, so «Чертежи» and «чертежи» are one name). The command checks the same rules first and answers
with a typed conflict; the trigger is the backstop for any other writer.

The **current** revision of a preset is a query (its highest ``revision_no``), never stored state, so
nothing can disagree with the history.

``audit_run.preset_revision_id`` -- nullable, ``REFERENCES analysis_preset_revision (preset_revision_id)``:
the exact preset revision a run was started with, written once in the start's own INSERT.
``trg_audit_run_frozen_guard`` is recreated with the column in its list (the run cannot be given another
preset afterwards), and a BEFORE INSERT trigger ``am_check_audit_run_preset`` (``AM001``) says the run
also froze an executor revision and that this revision belongs to the connection the preset revision
names -- so a run can never claim a preset whose executor it did not use. A run with
no preset keeps the column null and nothing about it changes.

**No backfill.** Nothing existed before; the upgrade creates an empty table and a null column beside
existing rows and changes none of them. The bounds (100, 120) are restated, not imported: a migration is
history and must not move when the application does; ``tests/unit/executors`` holds them equal to
``auditmanager.executors.presets``.

Downgrade
---------
Refuses while a preset revision or a run that recorded a preset exists: both exist nowhere else, and an
unannounced downgrade would drop an administrator's configuration (the pattern of the refusals in
``0006``, ``0029``, ``0032``, ``0033``, ``0034`` and ``0035``). With none it restores the ``0030`` list of
the frozen guard, drops the column, the trigger, the table and its functions, and nothing else.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0037_analysis_presets"
down_revision: str | None = "0036_cite_partition_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

STATES: tuple[str, ...] = ("active", "archived")
#: ``auditmanager.executors.presets.MAX_PRESETS`` / ``MAX_NAME_LENGTH``.
MAX_PRESETS = 100
MAX_NAME_LENGTH = 120

#: ``audit_run``'s frozen list as ``0030`` left it.
_FROZEN_RUN_COLUMNS = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id'"
)


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _frozen_run_guard(*, with_preset: bool) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    columns = _FROZEN_RUN_COLUMNS + (", 'preset_revision_id'" if with_preset else "")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({columns})"
    )


_CHAIN_FUNCTION = f"""
        CREATE FUNCTION am_check_analysis_preset_chain() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no integer;
            previous analysis_preset_revision%ROWTYPE;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('analysis_preset_revision', 0));
            SELECT max(revision_no) INTO last_no
              FROM analysis_preset_revision WHERE preset_id = NEW.preset_id;
            IF last_no IS NULL THEN
                IF NEW.revision_no <> 1 THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: preset % starts at revision 1', NEW.preset_id
                        USING ERRCODE = 'AM001',
                              HINT = 'Revisions are numbered 1, 2, 3, ... without a gap.';
                END IF;
                IF (SELECT count(*) FROM analysis_preset_revision WHERE revision_no = 1)
                   >= {MAX_PRESETS} THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: {MAX_PRESETS} presets already exist'
                        USING ERRCODE = 'AM001',
                              HINT = 'Archive is not deletion; the bound counts every preset.';
                END IF;
            ELSE
                IF NEW.revision_no <> last_no + 1 THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: preset % has revision % and cannot take %',
                        NEW.preset_id, last_no, NEW.revision_no
                        USING ERRCODE = 'AM001',
                              HINT = 'Revisions are numbered 1, 2, 3, ... without a gap.';
                END IF;
                SELECT * INTO previous FROM analysis_preset_revision
                 WHERE preset_id = NEW.preset_id AND revision_no = last_no;
                IF previous.state = 'archived' THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: preset % is archived and takes no revision',
                        NEW.preset_id
                        USING ERRCODE = 'AM001',
                              HINT = 'Archiving is one-way; make a new preset instead.';
                END IF;
                IF NEW.state = 'archived'
                   AND (NEW.name <> previous.name
                        OR NEW.executor_connection_id <> previous.executor_connection_id) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: the archive of preset % changes only its state',
                        NEW.preset_id
                        USING ERRCODE = 'AM001',
                              HINT = 'An archived revision repeats the previous name and connection.';
                END IF;
            END IF;
            IF NEW.state = 'active' THEN
                IF EXISTS (
                    SELECT 1 FROM executor_connection c
                     WHERE c.connection_id = NEW.executor_connection_id
                       AND c.archived_at IS NOT NULL
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: preset % names an archived connection',
                        NEW.preset_id
                        USING ERRCODE = 'AM001',
                              HINT = 'An active revision names a connection that is not archived.';
                END IF;
                IF EXISTS (
                    SELECT 1 FROM analysis_preset_revision r
                     WHERE r.preset_id <> NEW.preset_id
                       AND r.state = 'active'
                       AND lower(r.name) = lower(NEW.name)
                       AND r.revision_no = (SELECT max(x.revision_no)
                                              FROM analysis_preset_revision x
                                             WHERE x.preset_id = r.preset_id)
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: preset name already held by another active preset'
                        USING ERRCODE = 'AM001',
                              HINT = 'Names of active presets are unique without regard to case.';
                END IF;
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_RUN_FUNCTION = """
        CREATE FUNCTION am_check_audit_run_preset() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.preset_revision_id IS NOT NULL AND NOT EXISTS (
                SELECT 1
                  FROM executor_connection_revision cr
                  JOIN analysis_preset_revision pr
                    ON pr.executor_connection_id = cr.connection_id
                 WHERE cr.revision_id = NEW.connection_revision_id
                   AND pr.preset_revision_id = NEW.preset_revision_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: run % froze an executor revision that is not '
                    'the connection of its preset revision', NEW.run_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A run records a preset only when it started on that preset''s '
                                 'executor connection.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE analysis_preset_revision (
            preset_revision_id     text NOT NULL,
            preset_id              text NOT NULL,
            revision_no            integer NOT NULL,
            state                  text NOT NULL,
            name                   text NOT NULL,
            executor_connection_id text NOT NULL,
            created_at             timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by             text NOT NULL,
            CONSTRAINT pk_analysis_preset_revision PRIMARY KEY (preset_revision_id),
            CONSTRAINT uq_analysis_preset_revision_number UNIQUE (preset_id, revision_no),
            CONSTRAINT fk_analysis_preset_revision_connection
                FOREIGN KEY (executor_connection_id) REFERENCES executor_connection (connection_id)
                ON DELETE RESTRICT,
            CONSTRAINT ck_analysis_preset_revision_id_format
                CHECK (preset_revision_id ~ '^evt_{ULID}$'),
            CONSTRAINT ck_analysis_preset_revision_preset_id_format
                CHECK (preset_id ~ '^evt_{ULID}$'),
            CONSTRAINT ck_analysis_preset_revision_connection_id_format
                CHECK (executor_connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_analysis_preset_revision_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_analysis_preset_revision_number CHECK (revision_no >= 1),
            CONSTRAINT ck_analysis_preset_revision_identity
                CHECK ((revision_no = 1) = (preset_id = preset_revision_id)),
            CONSTRAINT ck_analysis_preset_revision_state
                CHECK (state IN ({_sql_list(STATES)})),
            CONSTRAINT ck_analysis_preset_revision_opens_active
                CHECK (state = 'active' OR revision_no >= 2),
            CONSTRAINT ck_analysis_preset_revision_name
                CHECK (char_length(name) BETWEEN 1 AND {MAX_NAME_LENGTH}
                       AND name = btrim(name, E' \\t\\r\\n')
                       AND name !~ '[[:cntrl:]]')
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_analysis_preset_revision_connection "
        "ON analysis_preset_revision (executor_connection_id);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_analysis_preset_revision_immutable
            BEFORE UPDATE OR DELETE ON analysis_preset_revision
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(_CHAIN_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_analysis_preset_revision_chain
            BEFORE INSERT ON analysis_preset_revision
            FOR EACH ROW EXECUTE FUNCTION am_check_analysis_preset_chain();
        """
    )
    op.execute(
        "COMMENT ON TABLE analysis_preset_revision IS "
        "'ANALYSIS-PRESETS-01 (R-146av). A named, saved choice of the executor connection a run is "
        "started on, append-only: one row per revision, archive is a revision. Identity is evt_ (the "
        "id of the revision''s audit event); the preset is the id of its first revision. A name is a "
        "label, never an identity. Configuration, kept by the product purge like the executor "
        "tables. Never updated or deleted (am_immutable_row); chain, names and connection are "
        "checked by am_check_analysis_preset_chain.';"
    )

    op.execute(
        "ALTER TABLE audit_run ADD COLUMN preset_revision_id text NULL "
        "REFERENCES analysis_preset_revision (preset_revision_id)"
    )
    op.execute(
        f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_preset_revision_format "
        f"CHECK (preset_revision_id IS NULL OR preset_revision_id ~ '^evt_{ULID}$')"
    )
    op.execute(
        "CREATE INDEX ix_audit_run_preset_revision ON audit_run (preset_revision_id) "
        "WHERE preset_revision_id IS NOT NULL"
    )
    _frozen_run_guard(with_preset=True)
    op.execute(_RUN_FUNCTION)
    op.execute(
        """
        CREATE TRIGGER trg_audit_run_preset_executor
            BEFORE INSERT ON audit_run
            FOR EACH ROW EXECUTE FUNCTION am_check_audit_run_preset();
        """
    )


def downgrade() -> None:
    """Refuse while a row exists, otherwise drop this revision's own objects and nothing else."""
    bind = op.get_bind()
    presets = bind.execute(text("SELECT count(*) FROM analysis_preset_revision")).scalar_one()
    runs = bind.execute(
        text("SELECT count(*) FROM audit_run WHERE preset_revision_id IS NOT NULL")
    ).scalar_one()
    if presets or runs:
        raise RuntimeError(
            f"0037 downgrade refused: {presets} preset revision(s) and {runs} run(s) that recorded "
            "a preset exist nowhere else; restore a backup instead of downgrading"
        )
    op.execute("DROP TRIGGER trg_audit_run_preset_executor ON audit_run;")
    op.execute("DROP FUNCTION am_check_audit_run_preset();")
    _frozen_run_guard(with_preset=False)
    op.execute("DROP INDEX ix_audit_run_preset_revision;")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_preset_revision_format;")
    op.execute("ALTER TABLE audit_run DROP COLUMN preset_revision_id;")
    op.execute("DROP TABLE analysis_preset_revision;")
    op.execute("DROP FUNCTION am_check_analysis_preset_chain();")
