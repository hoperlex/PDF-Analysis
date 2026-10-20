"""Work assignments: a project or one of its documents given to an expert, and its history.

Revision ID: 0025_work_assignments
Revises: 0024_version_classification

`W61-DISPATCHER-01` (roadmap Q-2, ``ROADMAP-TO-BETA.md`` §10.5: «Диспетчер» in beta).

What this revision adds
-----------------------
``work_assignment`` -- one row per assignment: its opaque identity (``asg_<ULID>``), the
project, optionally one document of that project, the expert it was **first** given to, the
administrator who created it, an optional note and when. Written once and never updated or
deleted (``am_immutable_row``, SQLSTATE ``AM003``).

``work_assignment_event`` -- the append-only history: ``assigned`` (always the first, and only
the first), ``started``, ``completed``, ``returned`` (with its reason), ``reassigned`` (with
the new assignee) and ``cancelled``, each with the acting account and the time. Its identity
is an ``audit_event_id`` (``evt_``), as ``norm_current_snapshot_event``'s is (``0020``): an
appended history row is an audit event, and the domain catalog already declares that
identity. ``seq`` orders the events of one assignment and, being unique per assignment, is
the backstop that two concurrent transitions cannot both append the same next event. It is
an order, never an identity, and is not exposed. UPDATE and DELETE are refused
(``am_immutable_row``).

``work_assignment_current`` -- a view, the derived current state: the latest event of each
assignment and the current assignee (the latest ``reassigned`` event's new assignee, else the
first assignee). There is **no status column**: the status is a function of the latest
event's kind, and that function, like every rule about which move is allowed and who may
make it, lives in ``auditmanager.dispatch``. Nothing here is a cache that could disagree with
the history.

``am_require_work_assignment_event`` -- a deferred constraint trigger: an assignment row is
refused at COMMIT unless its ``assigned`` event (``seq`` 1) exists, so the view never meets
an assignment without a history.

**Account references.** The first assignee, the creator, each event's actor and each
reassignment's new assignee are ``RESTRICT`` foreign keys to ``app_user`` and are registered
in ``auditmanager.access.references``: an account that was given or handed out work is
history the assignment points at, so purging it is refused (``conflict``,
``account_referenced``) -- archive stays available. ``test_accounts_migration.py`` holds the
register equal to the schema's foreign keys.

**The project and the document are RESTRICT references too.** "The document belongs to the
project" is checked by the dispatch context in the writing transaction (through the
documents boundary); the schema keeps a plain foreign key to ``document`` because a
composite key would need a new constraint on ``document``, which this revision does not
touch.

**No backfill.** Nothing existed before; the upgrade creates empty tables beside existing
rows and changes none of them.

Downgrade
---------
Drops the view, the two tables and the trigger function -- and nothing else. Every recorded
assignment and its history exist nowhere else; the downgrade names how many it drops.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0025_work_assignments"
down_revision: str | None = "0024_version_classification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.work_assignments")

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: The event vocabulary, restated rather than imported (a migration is history and must not
#: move when the application does); ``tests/unit/dispatch`` holds it equal to
#: ``auditmanager.dispatch.policy.EVENT_KINDS``.
EVENT_KINDS: tuple[str, ...] = (
    "assigned", "started", "completed", "returned", "reassigned", "cancelled",
)

#: The longest note and reason, in characters; restated as ``MAX_NOTE_LENGTH`` /
#: ``MAX_REASON_LENGTH`` in ``auditmanager.dispatch.policy`` and held equal by the same test.
MAX_NOTE_LENGTH = 2000
MAX_REASON_LENGTH = 2000


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE work_assignment (
            assignment_uid      text PRIMARY KEY,
            project_uid         text NOT NULL,
            document_uid        text NULL,
            assignee_user_uid   text NOT NULL,
            created_by_user_uid text NOT NULL,
            note                text NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_work_assignment_project
                FOREIGN KEY (project_uid) REFERENCES project (project_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_work_assignment_document
                FOREIGN KEY (document_uid) REFERENCES document (document_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_work_assignment_assignee
                FOREIGN KEY (assignee_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_work_assignment_created_by
                FOREIGN KEY (created_by_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT ck_work_assignment_assignment_uid_format
                CHECK (assignment_uid ~ '^asg_{ULID}$'),
            CONSTRAINT ck_work_assignment_project_uid_format
                CHECK (project_uid ~ '^prj_{ULID}$'),
            CONSTRAINT ck_work_assignment_document_uid_format
                CHECK (document_uid IS NULL OR document_uid ~ '^doc_{ULID}$'),
            CONSTRAINT ck_work_assignment_assignee_user_uid_format
                CHECK (assignee_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_work_assignment_created_by_user_uid_format
                CHECK (created_by_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_work_assignment_note_length
                CHECK (note IS NULL OR char_length(note) BETWEEN 1 AND {MAX_NOTE_LENGTH})
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_work_assignment_scope ON work_assignment (project_uid, document_uid);"
    )
    op.execute(
        "CREATE INDEX ix_work_assignment_created "
        "ON work_assignment (created_at DESC, assignment_uid DESC);"
    )
    op.execute(
        """
        CREATE TRIGGER trg_work_assignment_immutable
            BEFORE UPDATE OR DELETE ON work_assignment
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE work_assignment IS "
        "'W61-DISPATCHER-01. One assignment of a project, or of one document of it, to an "
        "expert. Written once and never updated or deleted (am_immutable_row). "
        "assignee_user_uid is the FIRST assignee; the current assignee and the status are "
        "derived from work_assignment_event (view work_assignment_current).';"
    )

    op.execute(
        f"""
        CREATE TABLE work_assignment_event (
            event_id              text PRIMARY KEY,
            assignment_uid        text NOT NULL,
            seq                   integer NOT NULL,
            kind                  text NOT NULL,
            actor_user_uid        text NOT NULL,
            reason                text NULL,
            new_assignee_user_uid text NULL,
            occurred_at           timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT fk_work_assignment_event_assignment
                FOREIGN KEY (assignment_uid) REFERENCES work_assignment (assignment_uid)
                ON DELETE RESTRICT,
            CONSTRAINT fk_work_assignment_event_actor
                FOREIGN KEY (actor_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_work_assignment_event_new_assignee
                FOREIGN KEY (new_assignee_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            CONSTRAINT uq_work_assignment_event_assignment_uid_seq
                UNIQUE (assignment_uid, seq),
            CONSTRAINT ck_work_assignment_event_event_id_format
                CHECK (event_id ~ '^evt_{ULID}$'),
            CONSTRAINT ck_work_assignment_event_assignment_uid_format
                CHECK (assignment_uid ~ '^asg_{ULID}$'),
            CONSTRAINT ck_work_assignment_event_actor_user_uid_format
                CHECK (actor_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_work_assignment_event_new_assignee_user_uid_format
                CHECK (new_assignee_user_uid IS NULL OR new_assignee_user_uid ~ '^usr_{ULID}$'),
            CONSTRAINT ck_work_assignment_event_seq CHECK (seq >= 1),
            CONSTRAINT ck_work_assignment_event_kind CHECK (kind IN ({_sql_list(EVENT_KINDS)})),
            CONSTRAINT ck_work_assignment_event_first_is_assigned
                CHECK ((kind = 'assigned') = (seq = 1)),
            CONSTRAINT ck_work_assignment_event_new_assignee_only_on_reassign
                CHECK ((new_assignee_user_uid IS NOT NULL) = (kind = 'reassigned')),
            CONSTRAINT ck_work_assignment_event_reason_shape
                CHECK (
                    (kind <> 'returned' OR reason IS NOT NULL)
                    AND (kind IN ('returned', 'reassigned', 'cancelled') OR reason IS NULL)
                ),
            CONSTRAINT ck_work_assignment_event_reason_length
                CHECK (reason IS NULL OR char_length(reason) BETWEEN 1 AND {MAX_REASON_LENGTH})
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_work_assignment_event_new_assignee "
        "ON work_assignment_event (new_assignee_user_uid) WHERE new_assignee_user_uid IS NOT NULL;"
    )
    op.execute(
        """
        CREATE TRIGGER trg_work_assignment_event_immutable
            BEFORE UPDATE OR DELETE ON work_assignment_event
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
    op.execute(
        "COMMENT ON TABLE work_assignment_event IS "
        "'W61-DISPATCHER-01. Append-only history of one assignment: assigned (seq 1), "
        "started, completed, returned (reason), reassigned (new assignee), cancelled; actor "
        "and time. Never updated or deleted (am_immutable_row). seq orders one assignment''s "
        "events and is never an identity; event_id is.';"
    )

    op.execute(
        """
        CREATE FUNCTION am_require_work_assignment_event() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM work_assignment_event
                WHERE assignment_uid = NEW.assignment_uid AND seq = 1 AND kind = 'assigned'
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: work_assignment % has no assigned event',
                    NEW.assignment_uid
                    USING ERRCODE = 'AM001',
                          HINT = 'An assignment is created together with its assigned '
                                 'event (seq 1) in one transaction.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_work_assignment_has_assigned_event
            AFTER INSERT ON work_assignment
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION am_require_work_assignment_event();
        """
    )

    op.execute(
        """
        CREATE VIEW work_assignment_current AS
        SELECT
            a.assignment_uid,
            a.project_uid,
            a.document_uid,
            a.assignee_user_uid AS first_assignee_user_uid,
            COALESCE(r.new_assignee_user_uid, a.assignee_user_uid) AS current_assignee_user_uid,
            a.created_by_user_uid,
            a.note,
            a.created_at,
            l.seq AS last_seq,
            l.kind AS last_kind,
            l.actor_user_uid AS last_actor_user_uid,
            l.reason AS last_reason,
            l.occurred_at AS last_occurred_at
        FROM work_assignment a
        CROSS JOIN LATERAL (
            SELECT e.seq, e.kind, e.actor_user_uid, e.reason, e.occurred_at
            FROM work_assignment_event e
            WHERE e.assignment_uid = a.assignment_uid
            ORDER BY e.seq DESC
            LIMIT 1
        ) l
        LEFT JOIN LATERAL (
            SELECT e.new_assignee_user_uid
            FROM work_assignment_event e
            WHERE e.assignment_uid = a.assignment_uid AND e.kind = 'reassigned'
            ORDER BY e.seq DESC
            LIMIT 1
        ) r ON TRUE;
        """
    )
    op.execute(
        "COMMENT ON VIEW work_assignment_current IS "
        "'W61-DISPATCHER-01. Derived current state of each assignment: its latest event and "
        "its current assignee. No status is stored: auditmanager.dispatch maps the latest "
        "event kind to the status.';"
    )


def downgrade() -> None:
    """Drop the view, both tables and the trigger function; nothing else is touched."""
    bind = op.get_bind()
    assignments = bind.execute(text("SELECT count(*) FROM work_assignment")).scalar_one()
    events = bind.execute(text("SELECT count(*) FROM work_assignment_event")).scalar_one()
    if assignments or events:
        _log.warning(
            "0025_work_assignments downgrade: %d assignment(s) and %d history event(s) "
            "exist nowhere else and are dropped with their tables.",
            int(assignments),
            int(events),
        )
    op.execute("DROP VIEW work_assignment_current;")
    op.execute("DROP TABLE work_assignment_event;")
    op.execute("DROP TABLE work_assignment;")
    op.execute("DROP FUNCTION am_require_work_assignment_event();")
