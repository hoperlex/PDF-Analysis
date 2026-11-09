"""0061 -- the decision memory, phase M2: withdraw, restore, forget and the installation settings (`DECISION-MEMORY-01` section 8, `ADR-0027`).

``0059`` made eight append-only tables; this revision gives the status events a writer and the content tables their one way out.

``decision_memory_status_event``
    * the actor gets its **RESTRICT foreign key** to ``app_user`` (``D-393``) -- the account that withdrew, restored or forgot a case
      cannot be purged while the event names it; the key is also an entry of ``access/references.py``;
    * the forgotten content's digest (``forgotten_content_sha256``, exactly on a ``forget`` event) is the tombstone's proof of what is
      gone, without holding it;
    * ``trg_decision_memory_status_event_transition`` (``am_guard_decision_memory_status``) is the database's own transition rule:
      a ``withdraw`` needs an active case, a ``restore`` a withdrawn one, nothing follows a ``forget``. It takes an advisory lock per
      case, so two concurrent writers cannot both win; the application checks first and answers ``state_transition_not_allowed``, this
      is what holds when it is bypassed. Refusals carry ``AM003`` like every other immutable-row refusal.

The five content tables (``decision_memory_content``, ``_decision_text``, ``_evidence``, ``_norm_ref``, ``_crop``)
    ``am_immutable_row`` is replaced by ``am_guard_decision_memory_forget`` (``D-394``): ``UPDATE`` is still refused, and ``DELETE`` is
    permitted **only** when a ``forget`` status event of the same case was inserted by the *same transaction* (its ``xmin`` is the
    current top-level transaction id). The application role holds no ``DELETE`` privilege on them either; the guard is what lets the
    operator's forget tool delete content without switching a trigger off. The identity tables (case, decision, status event) stay
    ``am_immutable_row``.

``decision_memory_setting_event``
    The installation settings (``D-390``) as an append-only journal, the shape of ``schedule_setting_event``: ``data_class``
    (``test`` or ``real``; the default, when nothing is journalled, is ``test``) and ``training_use`` (``off`` or ``on``; the default
    is ``off``, `Q3c`). The application only reads it; an operator tool (``scripts/recovery/memory_setting.py``) writes it as the
    owner, naming an admin account, and ``training_use = on`` names the owner's permission (``owner_permission_ref``).

``decision_memory_case_current``
    The read model of a case: its status (``active``, ``withdrawn``, ``forgotten``) from the latest status event and its current
    verdict from the latest decision -- the memory's counterpart of ``finding_current_verdict``.

The downgrade refuses while a status event or a setting event exists: they are history that nothing can rebuild.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0061_decision_memory_m2"
down_revision: str | None = "0060_run_from_stage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: The content side: deletable only by a forget of the case (`DECISION-MEMORY-01` section 3.4).
CONTENT_TABLES: tuple[str, ...] = (
    "decision_memory_content",
    "decision_memory_decision_text",
    "decision_memory_evidence",
    "decision_memory_norm_ref",
    "decision_memory_crop",
)


def upgrade() -> None:
    # --- the status event ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE decision_memory_status_event
            ADD CONSTRAINT fk_decision_memory_status_event_actor
                FOREIGN KEY (actor_user_uid) REFERENCES app_user (user_uid) ON DELETE RESTRICT
    """)
    op.execute("ALTER TABLE decision_memory_status_event ADD COLUMN forgotten_content_sha256 text NULL")
    op.execute("""
        ALTER TABLE decision_memory_status_event
            ADD CONSTRAINT ck_decision_memory_status_event_forgotten_content_sha256
                CHECK (forgotten_content_sha256 IS NULL OR forgotten_content_sha256 ~ '^[0-9a-f]{64}$'),
            ADD CONSTRAINT ck_decision_memory_status_event_forget_digest
                CHECK ((kind = 'forget') = (forgotten_content_sha256 IS NOT NULL))
    """)

    op.execute("""
        CREATE FUNCTION am_guard_decision_memory_status() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            latest text;
        BEGIN
            -- One writer per case at a time: the rule below reads the latest event, so two concurrent writers must queue.
            PERFORM pg_advisory_xact_lock(hashtextextended('decision_memory_status:' || NEW.case_id, 0));
            SELECT e.kind INTO latest
              FROM decision_memory_status_event e
             WHERE e.case_id = NEW.case_id
             ORDER BY e.created_at DESC, e.status_event_id DESC
             LIMIT 1;
            IF latest = 'forget' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory case % was forgotten; a % event is refused', NEW.case_id, NEW.kind
                    USING ERRCODE = 'AM003',
                          HINT = 'A forgotten case is terminal: it keeps its tombstone and accepts no further status event.';
            ELSIF NEW.kind = 'withdraw' AND latest = 'withdraw' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory case % is already withdrawn', NEW.case_id
                    USING ERRCODE = 'AM003';
            ELSIF NEW.kind = 'restore' AND (latest IS NULL OR latest = 'restore') THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: decision memory case % is not withdrawn, so it cannot be restored', NEW.case_id
                    USING ERRCODE = 'AM003';
            END IF;
            RETURN NEW;
        END
        $fn$;
    """)
    op.execute("""
        CREATE TRIGGER trg_decision_memory_status_event_transition
            BEFORE INSERT ON decision_memory_status_event
            FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_status()
    """)

    # --- the forget guard on the content side -----------------------------------------------
    op.execute("""
        CREATE FUNCTION am_guard_decision_memory_forget() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            owner_case text;
        BEGIN
            IF TG_OP <> 'DELETE' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: % is immutable once written; % is refused', TG_TABLE_NAME, TG_OP
                    USING ERRCODE = 'AM003',
                          HINT = 'Correcting data creates a new entity with a new identifier; it never rewrites an existing one.';
            END IF;
            IF TG_TABLE_NAME = 'decision_memory_decision_text' THEN
                SELECT d.case_id INTO owner_case
                  FROM decision_memory_decision d WHERE d.memory_decision_id = OLD.memory_decision_id;
            ELSE
                owner_case := OLD.case_id;
            END IF;
            -- The forget event must have been inserted by THIS transaction: its xmin is the current top-level transaction id.
            IF NOT EXISTS (
                SELECT 1 FROM decision_memory_status_event e
                 WHERE e.case_id = owner_case AND e.kind = 'forget' AND e.xmin = pg_current_xact_id()::xid
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: % is immutable once written; DELETE is permitted only beside a forget event of its case in the same transaction', TG_TABLE_NAME
                    USING ERRCODE = 'AM003',
                          HINT = 'Content is removed by the operator tool scripts/recovery/memory_forget.py and by nothing else.';
            END IF;
            RETURN OLD;
        END
        $fn$;
    """)
    for table in CONTENT_TABLES:
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(
            f"CREATE TRIGGER trg_{table}_forget_guard BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_guard_decision_memory_forget()"
        )

    # --- the installation settings ----------------------------------------------------------
    op.execute(f"""
        CREATE TABLE decision_memory_setting_event (
            setting_name text NOT NULL
                CONSTRAINT ck_decision_memory_setting_event_setting_name CHECK (setting_name IN ('data_class', 'training_use')),
            revision integer NOT NULL
                CONSTRAINT ck_decision_memory_setting_event_revision CHECK (revision >= 1),
            value text NOT NULL
                CONSTRAINT ck_decision_memory_setting_event_value CHECK (value IN ('test', 'real', 'off', 'on')),
            actor_user_uid text NOT NULL
                CONSTRAINT ck_decision_memory_setting_event_actor_user_uid_format CHECK (actor_user_uid ~ '^usr_{ULID}$')
                CONSTRAINT fk_decision_memory_setting_event_actor
                    REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            owner_permission_ref text NULL
                CONSTRAINT ck_decision_memory_setting_event_owner_permission_ref
                    CHECK (owner_permission_ref IS NULL OR char_length(owner_permission_ref) BETWEEN 1 AND 200),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT pk_decision_memory_setting_event PRIMARY KEY (setting_name, revision),
            CONSTRAINT ck_decision_memory_setting_event_value_for_name
                CHECK ((setting_name = 'data_class' AND value IN ('test', 'real'))
                       OR (setting_name = 'training_use' AND value IN ('off', 'on'))),
            CONSTRAINT ck_decision_memory_setting_event_on_needs_permission
                CHECK (value <> 'on' OR owner_permission_ref IS NOT NULL)
        )
    """)
    op.execute(
        "CREATE TRIGGER trg_decision_memory_setting_event_immutable BEFORE UPDATE OR DELETE ON decision_memory_setting_event "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "COMMENT ON TABLE decision_memory_setting_event IS "
        "'ADR-0027 / DECISION-MEMORY-01 phase M2: the installation settings of the decision memory, an append-only journal. "
        "data_class (test, real) is read at every capture and defaults to test; training_use (off, on) defaults to off and gates "
        "the training export. Written by the operator tool scripts/recovery/memory_setting.py as the owner; the application only reads.';"
    )

    # --- the read model ---------------------------------------------------------------------
    op.execute("""
        CREATE VIEW decision_memory_case_current AS
        SELECT c.case_id,
               c.category,
               c.section_code,
               c.data_class,
               c.crop_state,
               c.origin_project_uid,
               c.captured_at,
               CASE s.kind WHEN 'withdraw' THEN 'withdrawn' WHEN 'forget' THEN 'forgotten' ELSE 'active' END AS status,
               s.status_event_id AS status_event_id,
               s.reason_code AS status_reason_code,
               s.created_at AS status_changed_at,
               v.memory_decision_id AS current_decision_id,
               v.verdict AS current_verdict,
               v.severity AS current_severity,
               v.origin_kind AS current_origin_kind,
               v.decided_at AS current_decided_at,
               (SELECT count(*) FROM decision_memory_decision d WHERE d.case_id = c.case_id) AS decision_count
          FROM decision_memory_case c
          LEFT JOIN (
                SELECT DISTINCT ON (e.case_id) e.case_id, e.kind, e.status_event_id, e.reason_code, e.created_at
                  FROM decision_memory_status_event e
                 ORDER BY e.case_id, e.created_at DESC, e.status_event_id DESC
          ) s ON s.case_id = c.case_id
          LEFT JOIN (
                SELECT DISTINCT ON (d.case_id) d.case_id, d.memory_decision_id, d.verdict, d.severity, d.origin_kind, d.decided_at
                  FROM decision_memory_decision d
                 ORDER BY d.case_id, d.decided_at DESC, d.memory_decision_id DESC
          ) v ON v.case_id = c.case_id
    """)
    op.execute(
        "COMMENT ON VIEW decision_memory_case_current IS "
        "'DECISION-MEMORY-01 phase M2: a case with its status (active, withdrawn, forgotten) from the latest status event and its "
        "current verdict from the latest decision. The memory is never a decision authority while the source finding exists.';"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM decision_memory_status_event) OR EXISTS (SELECT 1 FROM decision_memory_setting_event) THEN
                RAISE EXCEPTION
                    'the decision memory holds status events or settings (withdraw, restore, forget, data_class, training_use); '
                    'they are history nothing can rebuild, so restore from a backup instead of downgrading 0061';
            END IF;
        END
        $$;
        """
    )
    op.execute("DROP VIEW decision_memory_case_current")
    op.execute("DROP TABLE decision_memory_setting_event")
    for table in CONTENT_TABLES:
        op.execute(f"DROP TRIGGER trg_{table}_forget_guard ON {table}")
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
        )
    op.execute("DROP FUNCTION am_guard_decision_memory_forget()")
    op.execute("DROP TRIGGER trg_decision_memory_status_event_transition ON decision_memory_status_event")
    op.execute("DROP FUNCTION am_guard_decision_memory_status()")
    op.execute("""
        ALTER TABLE decision_memory_status_event
            DROP CONSTRAINT ck_decision_memory_status_event_forget_digest,
            DROP CONSTRAINT ck_decision_memory_status_event_forgotten_content_sha256
    """)
    op.execute("ALTER TABLE decision_memory_status_event DROP COLUMN forgotten_content_sha256")
    op.execute("ALTER TABLE decision_memory_status_event DROP CONSTRAINT fk_decision_memory_status_event_actor")
