"""Dispatch-time binding: ``binding_state`` on ``audit_run`` and ``comparison_ai_job``.

Revision ID: 0048_dispatch_time_binding
Revises: 0047_executor_groups_rules

The revision id is 26 characters, not the file name's 33: ``alembic_version.version_num`` is ``varchar(32)``.

`EXEC2-SEAL-2` (ADR-0026 decisions 12 to 15, owner rulings `R-149a` to `R-149f`;
``docs/program/dispatch/EXEC2-PLAN.md``). Work admitted by a rule or a group is not given a connection until dispatch.
This revision adds the columns that say so, and re-creates the two guards that freeze a connection revision so that it
may be written exactly once, at binding. It creates nothing that behaves: every existing row becomes
``frozen_at_start``, no statement writes another state until a stage-3 lane implements admission, and nothing reads the
new columns before the cut-over.

What this revision adds, on exactly two tables
----------------------------------------------
The two aggregates that freeze an executor are ``audit_run`` (the run-level freeze) and ``comparison_ai_job`` (the
consent-level freeze). The per-call provenance columns of ``model_call``, ``provider_call_effect`` and
``comparison_model_call`` are written at call time and are not touched.

``binding_state`` (``frozen_at_start`` | ``pending`` | ``bound``, ``NOT NULL``, default ``frozen_at_start``)
    ``frozen_at_start``: the connection revision was frozen at start (the existing behaviour: an explicit connection, a
    preset, the global route) -- every existing row. ``pending``: admitted by a rule or a group, no connection yet.
    ``bound``: dispatch wrote the connection revision. The ``environment`` provider source has a ``NULL`` connection
    revision on a ``frozen_at_start`` run; ``binding_state`` is what tells it apart from a ``pending`` one.
``executor_group_revision_id`` and ``routing_rule_revision_id`` (nullable, frozen once the row exists)
    what admission froze: the immutable group revision and, when a rule routed the work, the rule revision (``NULL``
    when the group was named explicitly). Both ``NULL`` on ``frozen_at_start``; the group revision is set on ``pending``
    and ``bound``. A pending or bound Run carries no preset (a group is exclusive with a preset and a connection).
``wait_reason`` and ``waiting_since`` (nullable, set together, only while ``pending``)
    why pending work is not dispatched and since when (decision 15): ``executor_at_capacity`` and ``runner_offline`` as
    ``RunQueueReason`` spells them, and ``needs_reconsent``. They change freely and are cleared at binding.
``comparison_ai_job.connection_revision_id`` becomes nullable
    ``NULL`` exactly when ``binding_state`` is ``pending`` (``ck_comparison_ai_job_pending_has_no_revision``). A job
    binds at its first dispatched call; its later calls stay on that connection.

The write-once rule (ADR-0026 decision 12)
------------------------------------------
``connection_revision_id`` may go ``NULL`` -> value **exactly once, in the same statement that moves ``binding_state``
``pending`` -> ``bound``**. Every other change is refused by the database, the same way as before:

* ``audit_run``. ``trg_audit_run_frozen_guard`` is re-created on a function of its own, ``am_guard_audit_run_frozen``,
  because the generic ``am_guard_frozen_columns`` cannot express an exception. The trigger keeps its full column list
  (``connection_revision_id`` still in it, ``executor_group_revision_id`` and ``routing_rule_revision_id`` added) and the
  function keeps the generic loop and message; it adds two rules. ``binding_state`` moves only ``pending`` -> ``bound``.
  A change of a listed column is refused, except ``connection_revision_id`` going from ``NULL`` to a value in a statement
  that also moves ``binding_state`` from ``pending`` to ``bound`` **and names a member of the run's group revision** (the
  value is the ``connection_revision_id`` of a row of ``executor_group_member`` of ``executor_group_revision_id``; any
  other revision is refused with ``AM001``). A second ``NULL`` -> value write (the state is no longer ``pending``), a
  value -> value write, a value -> ``NULL`` write and a ``NULL`` -> value write that leaves the state at ``pending`` are
  all refused (``ck_audit_run_binding_shape`` additionally refuses a ``bound`` row with no revision). For a
  ``frozen_at_start`` row this is exactly the freeze it had.
* ``comparison_ai_job``. ``am_guard_comparison_ai_job_consent`` (``0040``) is replaced, keeping its two original rules
  verbatim for a ``frozen_at_start`` job. A move ``pending`` -> ``bound`` must write the connection revision from
  ``NULL``, to the connection revision of a member of the job's group revision (``AM001`` otherwise), and change nothing
  of the consent (the estimate, its digest and amounts, the ceiling, the model, the provider mode, the consenting user and
  ``consent_no``). A ``pending`` or ``bound`` job never changes its connection revision or
  its pinned model, with or without a new consent number: the group is homogeneous and there is no re-routing after
  binding (decision 16). ``trg_comparison_ai_job_binding_pin`` freezes the two admission columns.

``bound`` and ``frozen_at_start`` are terminal for the machine (``binding_state`` in ``state-machines.json``); a
``pending`` -> ``frozen_at_start`` move, a ``bound`` -> ``pending`` move and the like are refused.

Downgrade
---------
Refused while any row is ``pending`` or ``bound`` or carries a group or rule revision or a wait; those rows exist
nowhere else. Otherwise it restores the ``0037`` trigger of ``audit_run`` (generic function, original column list) and the
``0040`` body of the consent guard, drops its own objects and makes ``comparison_ai_job.connection_revision_id``
``NOT NULL`` again.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0048_dispatch_time_binding"
down_revision: str | None = "0047_executor_groups_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_BINDING_STATES = "'frozen_at_start', 'pending', 'bound'"
#: ``RunQueueReason`` of contract 1.16.0 (``auditmanager.executors.model.WAIT_REASONS``).
_WAIT_REASONS = "'executor_at_capacity', 'runner_offline', 'needs_reconsent'"

#: ``audit_run``'s frozen list as ``0037`` left it.
_FROZEN_RUN_BEFORE = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id'"
)
#: The same list with what admission freezes added. ``connection_revision_id`` stays in it: its one exception is the
#: function's, not the list's.
_FROZEN_RUN_AFTER = _FROZEN_RUN_BEFORE + ", 'executor_group_revision_id', 'routing_rule_revision_id'"

#: ``am_guard_frozen_columns`` (``0002``) with the binding rules of ADR-0026 decision 12. The loop, the message and the
#: SQLSTATE of a frozen column are the generic function's, so every earlier refusal reads the same.
_RUN_FROZEN_FUNCTION = """
        CREATE FUNCTION am_guard_audit_run_frozen() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_column text;
            v_old    text;
            v_new    text;
        BEGIN
            IF NEW.binding_state IS DISTINCT FROM OLD.binding_state
               AND NOT (OLD.binding_state = 'pending' AND NEW.binding_state = 'bound') THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: binding_state of run % moves from pending to bound only, not % -> %',
                    OLD.run_id, OLD.binding_state, NEW.binding_state
                    USING ERRCODE = 'AM001',
                          HINT = 'frozen_at_start and bound are terminal; a pending run is bound once.';
            END IF;
            FOREACH v_column IN ARRAY TG_ARGV LOOP
                EXECUTE format('SELECT ($1).%I::text', v_column) INTO v_old USING OLD;
                EXECUTE format('SELECT ($1).%I::text', v_column) INTO v_new USING NEW;
                IF v_old IS DISTINCT FROM v_new THEN
                    IF v_column = 'connection_revision_id'
                       AND v_old IS NULL AND v_new IS NOT NULL
                       AND OLD.binding_state = 'pending' AND NEW.binding_state = 'bound' THEN
                        -- Dispatch binds a run to a member of the group revision it was admitted on, and to no other
                        -- connection (members are immutable, so a plain read is exact).
                        IF NOT EXISTS (
                            SELECT 1 FROM executor_group_member m
                             WHERE m.group_revision_id = NEW.executor_group_revision_id
                               AND m.connection_revision_id = NEW.connection_revision_id
                        ) THEN
                            RAISE EXCEPTION
                                'state_transition_not_allowed: connection revision % is not a member of group revision % that run % was admitted on',
                                NEW.connection_revision_id, NEW.executor_group_revision_id, OLD.run_id
                                USING ERRCODE = 'AM001',
                                      HINT = 'A pending run is bound to a member of its group revision, and to no other connection.';
                        END IF;
                        CONTINUE;
                    END IF;
                    RAISE EXCEPTION
                        'state_transition_not_allowed: %.% is frozen at creation and '
                        'may not be changed', TG_TABLE_NAME, v_column
                        USING ERRCODE = 'AM003',
                              HINT = 'A different value is a different entity. '
                                     'Create a new one with a new identifier.';
                END IF;
            END LOOP;
            RETURN NEW;
        END
        $fn$;
        """

#: ``0040``'s body, verbatim, for the downgrade.
_JOB_CONSENT_FUNCTION_BEFORE = """
        CREATE OR REPLACE FUNCTION am_guard_comparison_ai_job_consent() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF (NEW.estimate, NEW.estimate_digest, NEW.estimate_micros, NEW.ceiling_micros,
                NEW.connection_revision_id, NEW.pinned_model, NEW.provider_mode, NEW.consented_by_user_uid)
               IS DISTINCT FROM
               (OLD.estimate, OLD.estimate_digest, OLD.estimate_micros, OLD.ceiling_micros,
                OLD.connection_revision_id, OLD.pinned_model, OLD.provider_mode, OLD.consented_by_user_uid)
               AND NEW.consent_no <> OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the consented estimate of job % changes only with a new consent',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A new consent raises consent_no by one and carries the new estimate with it.';
            END IF;
            IF NEW.consent_no < OLD.consent_no OR NEW.consent_no > OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: consent_no of job % moves by one at most, upwards',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_JOB_CONSENT_FUNCTION_AFTER = """
        CREATE OR REPLACE FUNCTION am_guard_comparison_ai_job_consent() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.binding_state IS DISTINCT FROM OLD.binding_state THEN
                IF NOT (OLD.binding_state = 'pending' AND NEW.binding_state = 'bound') THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: binding_state of job % moves from pending to bound only, not % -> %',
                        OLD.comparison_ai_job_id, OLD.binding_state, NEW.binding_state
                        USING ERRCODE = 'AM001',
                              HINT = 'frozen_at_start and bound are terminal; a pending job is bound once.';
                END IF;
                IF OLD.connection_revision_id IS NOT NULL OR NEW.connection_revision_id IS NULL THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: job % is bound by writing its connection revision once, from NULL',
                        OLD.comparison_ai_job_id
                        USING ERRCODE = 'AM003',
                              HINT = 'The connection revision of a pending job goes from NULL to a value in the statement that binds it.';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM executor_group_member m
                     WHERE m.group_revision_id = NEW.executor_group_revision_id
                       AND m.connection_revision_id = NEW.connection_revision_id
                ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: connection revision % is not a member of group revision % that job % was admitted on',
                        NEW.connection_revision_id, NEW.executor_group_revision_id, OLD.comparison_ai_job_id
                        USING ERRCODE = 'AM001',
                              HINT = 'A pending job is bound to a member of its group revision, and to no other connection.';
                END IF;
                IF (NEW.estimate, NEW.estimate_digest, NEW.estimate_micros, NEW.ceiling_micros,
                    NEW.pinned_model, NEW.provider_mode, NEW.consented_by_user_uid, NEW.consent_no)
                   IS DISTINCT FROM
                   (OLD.estimate, OLD.estimate_digest, OLD.estimate_micros, OLD.ceiling_micros,
                    OLD.pinned_model, OLD.provider_mode, OLD.consented_by_user_uid, OLD.consent_no) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: binding job % writes its connection revision and nothing of its consent',
                        OLD.comparison_ai_job_id
                        USING ERRCODE = 'AM001',
                              HINT = 'A changed consent is a new consent of a job that is already bound or still pending.';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.binding_state <> 'frozen_at_start'
               AND (NEW.connection_revision_id IS DISTINCT FROM OLD.connection_revision_id
                    OR NEW.pinned_model IS DISTINCT FROM OLD.pinned_model) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: job % keeps its connection revision and its model once it is admitted by a group',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM003',
                          HINT = 'There is no re-routing after binding; a pending job is bound once.';
            END IF;
            IF (NEW.estimate, NEW.estimate_digest, NEW.estimate_micros, NEW.ceiling_micros,
                NEW.connection_revision_id, NEW.pinned_model, NEW.provider_mode, NEW.consented_by_user_uid)
               IS DISTINCT FROM
               (OLD.estimate, OLD.estimate_digest, OLD.estimate_micros, OLD.ceiling_micros,
                OLD.connection_revision_id, OLD.pinned_model, OLD.provider_mode, OLD.consented_by_user_uid)
               AND NEW.consent_no <> OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the consented estimate of job % changes only with a new consent',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A new consent raises consent_no by one and carries the new estimate with it.';
            END IF;
            IF NEW.consent_no < OLD.consent_no OR NEW.consent_no > OLD.consent_no + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: consent_no of job % moves by one at most, upwards',
                    OLD.comparison_ai_job_id
                    USING ERRCODE = 'AM001';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def _frozen_run_guard(function: str, columns: str) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION {function}({columns})"
    )


def upgrade() -> None:
    # --- audit_run -------------------------------------------------------------------------------
    op.execute(
        "ALTER TABLE audit_run "
        "ADD COLUMN binding_state text NOT NULL DEFAULT 'frozen_at_start', "
        "ADD COLUMN executor_group_revision_id text NULL REFERENCES executor_group_revision (group_revision_id), "
        "ADD COLUMN routing_rule_revision_id text NULL REFERENCES executor_routing_rule_revision (rule_revision_id), "
        "ADD COLUMN wait_reason text NULL, "
        "ADD COLUMN waiting_since timestamptz NULL"
    )
    op.execute(
        f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_binding_state CHECK (binding_state IN ({_BINDING_STATES}))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_group_revision_format CHECK "
        f"(executor_group_revision_id IS NULL OR executor_group_revision_id ~ '^exgr_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_rule_revision_format CHECK "
        f"(routing_rule_revision_id IS NULL OR routing_rule_revision_id ~ '^exrr_{ULID}$')"
    )
    # frozen_at_start: no group, no rule; pending: a group, no connection, no preset; bound: a group and a connection, no
    # preset. A NULL connection revision on a frozen_at_start run is the environment provider source.
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_binding_shape CHECK ("
        "(binding_state = 'frozen_at_start' AND executor_group_revision_id IS NULL "
        "AND routing_rule_revision_id IS NULL) "
        "OR (binding_state = 'pending' AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NULL AND preset_revision_id IS NULL) "
        "OR (binding_state = 'bound' AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NOT NULL AND preset_revision_id IS NULL))"
    )
    op.execute(
        f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_reason CHECK "
        f"(wait_reason IS NULL OR wait_reason IN ({_WAIT_REASONS}))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_pair CHECK "
        "((wait_reason IS NULL) = (waiting_since IS NULL))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_pending CHECK "
        "(wait_reason IS NULL OR binding_state = 'pending')"
    )
    op.execute(
        "CREATE INDEX ix_audit_run_group_revision ON audit_run (executor_group_revision_id) "
        "WHERE executor_group_revision_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_audit_run_pending ON audit_run (created_at, run_id) WHERE binding_state = 'pending'"
    )

    # --- comparison_ai_job -----------------------------------------------------------------------
    op.execute("ALTER TABLE comparison_ai_job ALTER COLUMN connection_revision_id DROP NOT NULL")
    op.execute(
        "ALTER TABLE comparison_ai_job "
        "ADD COLUMN binding_state text NOT NULL DEFAULT 'frozen_at_start', "
        "ADD COLUMN executor_group_revision_id text NULL REFERENCES executor_group_revision (group_revision_id), "
        "ADD COLUMN routing_rule_revision_id text NULL REFERENCES executor_routing_rule_revision (rule_revision_id), "
        "ADD COLUMN wait_reason text NULL, "
        "ADD COLUMN waiting_since timestamptz NULL"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_binding_state "
        f"CHECK (binding_state IN ({_BINDING_STATES}))"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_group_revision_format CHECK "
        f"(executor_group_revision_id IS NULL OR executor_group_revision_id ~ '^exgr_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_rule_revision_format CHECK "
        f"(routing_rule_revision_id IS NULL OR routing_rule_revision_id ~ '^exrr_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_pending_has_no_revision CHECK "
        "((connection_revision_id IS NULL) = (binding_state = 'pending'))"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_binding_shape CHECK ("
        "(binding_state = 'frozen_at_start' AND executor_group_revision_id IS NULL "
        "AND routing_rule_revision_id IS NULL) "
        "OR (binding_state IN ('pending', 'bound') AND executor_group_revision_id IS NOT NULL))"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_wait_reason CHECK "
        f"(wait_reason IS NULL OR wait_reason IN ({_WAIT_REASONS}))"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_wait_pair CHECK "
        "((wait_reason IS NULL) = (waiting_since IS NULL))"
    )
    op.execute(
        "ALTER TABLE comparison_ai_job ADD CONSTRAINT ck_comparison_ai_job_wait_pending CHECK "
        "(wait_reason IS NULL OR binding_state = 'pending')"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_job_group_revision ON comparison_ai_job (executor_group_revision_id) "
        "WHERE executor_group_revision_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_comparison_ai_job_pending ON comparison_ai_job (created_at, comparison_ai_job_id) "
        "WHERE binding_state = 'pending'"
    )

    # --- the guards ------------------------------------------------------------------------------
    op.execute(_RUN_FROZEN_FUNCTION)
    _frozen_run_guard("am_guard_audit_run_frozen", _FROZEN_RUN_AFTER)
    op.execute(_JOB_CONSENT_FUNCTION_AFTER)
    op.execute(
        "CREATE TRIGGER trg_comparison_ai_job_binding_pin BEFORE UPDATE ON comparison_ai_job "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'executor_group_revision_id', 'routing_rule_revision_id')"
    )

    op.execute(
        "COMMENT ON COLUMN audit_run.binding_state IS "
        "'ADR-0026 decision 12: frozen_at_start (connection revision frozen at start), pending (admitted by a rule "
        "or a group, no connection yet) or bound. The connection revision goes NULL to a value once, with "
        "pending to bound (am_guard_audit_run_frozen).';"
    )
    op.execute(
        "COMMENT ON COLUMN comparison_ai_job.binding_state IS "
        "'ADR-0026 decision 12: as audit_run.binding_state. connection_revision_id is NULL exactly while pending and "
        "is written once, with pending to bound (am_guard_comparison_ai_job_consent).';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in ("audit_run", "comparison_ai_job"):
        if bind.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM {table} WHERE binding_state <> 'frozen_at_start' "
            "OR executor_group_revision_id IS NOT NULL OR routing_rule_revision_id IS NOT NULL "
            "OR wait_reason IS NOT NULL)"
        )).scalar_one():
            retained.append(f"{table} rows admitted by a rule or a group")
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0048_dispatch_time_binding with retained pending or bound work "
            f"({', '.join(retained)}); restore a database backup instead"
        )

    op.execute("DROP TRIGGER trg_comparison_ai_job_binding_pin ON comparison_ai_job")
    op.execute(_JOB_CONSENT_FUNCTION_BEFORE)
    _frozen_run_guard("am_guard_frozen_columns", _FROZEN_RUN_BEFORE)
    op.execute("DROP FUNCTION am_guard_audit_run_frozen()")

    op.execute("DROP INDEX ix_comparison_ai_job_pending")
    op.execute("DROP INDEX ix_comparison_ai_job_group_revision")
    for constraint in (
        "ck_comparison_ai_job_wait_pending", "ck_comparison_ai_job_wait_pair", "ck_comparison_ai_job_wait_reason",
        "ck_comparison_ai_job_binding_shape", "ck_comparison_ai_job_pending_has_no_revision",
        "ck_comparison_ai_job_rule_revision_format", "ck_comparison_ai_job_group_revision_format",
        "ck_comparison_ai_job_binding_state",
    ):
        op.execute(f"ALTER TABLE comparison_ai_job DROP CONSTRAINT {constraint}")
    op.execute(
        "ALTER TABLE comparison_ai_job DROP COLUMN waiting_since, DROP COLUMN wait_reason, "
        "DROP COLUMN routing_rule_revision_id, DROP COLUMN executor_group_revision_id, DROP COLUMN binding_state"
    )
    op.execute("ALTER TABLE comparison_ai_job ALTER COLUMN connection_revision_id SET NOT NULL")

    op.execute("DROP INDEX ix_audit_run_pending")
    op.execute("DROP INDEX ix_audit_run_group_revision")
    for constraint in (
        "ck_audit_run_wait_pending", "ck_audit_run_wait_pair", "ck_audit_run_wait_reason",
        "ck_audit_run_binding_shape", "ck_audit_run_rule_revision_format", "ck_audit_run_group_revision_format",
        "ck_audit_run_binding_state",
    ):
        op.execute(f"ALTER TABLE audit_run DROP CONSTRAINT {constraint}")
    op.execute(
        "ALTER TABLE audit_run DROP COLUMN waiting_since, DROP COLUMN wait_reason, "
        "DROP COLUMN routing_rule_revision_id, DROP COLUMN executor_group_revision_id, DROP COLUMN binding_state"
    )
