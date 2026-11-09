"""0062 -- executor hosts, system connections, the stage layout and the cell-bound run (`HOSTS-SEAL-1`, ADR-0028).

Revision ID: 0062_hosts_stage_models
Revises: 0061_decision_memory_m2

`HOSTS-SEAL-1` (the owner-approved plan of 2026-11-09, sections 3.2, 3.3, 4.1, 4.5 and 10.2; contract 1.45.0). It creates the storage
of the surface of contract 1.45.0 and nothing that behaves: no statement writes any of it until a wave-1 lane implements the operation
that does. Every addition to an existing table is nullable or defaulted, so a database at ``0061`` upgrades with no row touched.

What this revision adds
-----------------------
``executor_host`` (``exh``) and its three journals
    A *server*: one agent process, one host token, every provider CLI and API key on that machine. ``executor_host_use_event`` (``exhu``)
    is the «Использовать» journal -- author, time, ``enabled``; the latest event is the switch (a new server is switched on by the
    administrator who connected it, so the first event is ``enabled``). ``executor_host_slot_event`` (``exhs``) holds the slots of a
    provider on the host (1 to 16), the latest event per provider being the number in force. Both are append-only and numbered 1, 2, 3
    without a gap per host (``am_check_gapless_number``). ``executor_host_report`` is the **latest** health and capability snapshot of
    the host's agent (providers, their models and their states, the slots the agent reports); a report that changes nothing is not
    written, so the row is the snapshot of the last change and the token's ``last_seen_at`` is the pulse.
``executor_model_cooldown``
    The passive check of plan section 5.5: after a real refusal (access, quota, no such model) the (host, provider, model) is taken out
    of availability until ``until``. One row per triple, replaced by the next refusal.
``host_id`` on ``executor_runner_token``, ``executor_enrollment`` and ``executor_agent_install``
    ``connection_id`` becomes nullable on all three, and ``ck_*_target`` says *exactly one of* ``connection_id`` and ``host_id``. Every
    row written before this revision names a connection. A host token claims the tasks of the system connections of its host: the
    composite key of ``executor_task`` to the token (``fk_executor_task_token``) cannot express that and is replaced by a plain key plus
    ``trg_executor_task_claimer``, which accepts the connection's own token or a token of the connection's host. The enrollment key
    ``(runner_token_id, host_id)`` and a second unique index per host mirror the connection forms.
``system_managed``, ``host_id`` and ``capacity_pool`` on ``executor_connection``; ``system_managed`` on ``executor_group``
    The connections the stand keeps for each found (host, provider, access, model) and the groups it keeps for each (model, access).
    A system connection is a ``pull`` connection of a host whose ``capacity_pool`` is ``<host_id>:<provider>`` (the unit of capacity is
    the pair run and pool, plan section 3.2). The user never sees or edits them; revise and archive of a system object is the
    application's refusal, and the columns are frozen. ``host_id`` is not in the brief's list: the pool text alone would be a host
    identity held as an unchecked string, so the key is explicit and ``ck_executor_connection_pool`` ties the two.
``stage_layout`` / ``stage_layout_revision`` (``slr``) / ``stage_layout_switch_event`` (``sls``)
    The models of the analysis stages, kept in the database: one layout (key ``default``), its append-only revisions (the kit, and one
    cell per row and role with the model, the effort, the output limit and the timeout) and the switch that puts the layout in force,
    with its journal. Enabling needs a revision (``trg_stage_layout_switch_enabled``).
``audit_run.stage_plan``
    The plan a run froze at its start: for every cell the model, the effort, the limits and the access. A run with a plan is bound **by
    cell** at dispatch: ``binding_state`` is still ``pending`` then ``bound``, but the run has no group, no connection revision, no
    preset and no rule of its own (``ck_audit_run_binding_shape`` gains that fourth shape). ``stage_plan`` joins the frozen columns of
    ``trg_audit_run_frozen_guard``, and ``am_guard_audit_run_frozen`` refuses ``pending`` -> ``bound`` of a planned run unless every
    cell of the plan has its binding row. ``ck_audit_run_wait_reason`` accepts ``model_unavailable``, and only a planned run may carry
    it (``ck_audit_run_wait_model_unavailable``). ``ck_audit_run_wait_pending`` (``0048``: a wait only while ``pending``) already admits
    a planned run and is left as it is.
``audit_run_cell_binding``
    One row per (run, cell): the group revision and the member's connection revision that cell was bound to, written once, in the
    transaction that binds the run. ``trg_audit_run_cell_binding_member`` accepts a row only for a ``pending`` planned run, for a cell
    of its plan, for a member of the named group revision that is a system connection and pins exactly the cell's model.
    ``trg_audit_run_cell_binding_immutable`` refuses every UPDATE and DELETE.
``stage_key``, ``host_id`` and ``access`` on ``model_call`` and ``provider_call_effect``
    Which row of the layout the call belongs to, which host served it (a bare identity, **not a foreign key**: a host is archived,
    never deleted, but a call outlives anything) and whether it ran on a subscription or an API key. All three are NULL for every call
    written before this revision and for every call of a connection-bound run.

Consent v2 and the new ``ExecutorGroupMemberIssue`` values (``host_disabled``, ``model_not_verified``, ``model_cooling_down``) have no
column: the consent is stored in the command's outcome and the issues are derived on read.

Downgrade
---------
Refused while any host, host-bound credential, system object, layout revision or switch event, planned run, cell binding, host report,
cooldown, or any call carrying ``stage_key``, ``host_id`` or ``access`` exists: dropping them would turn a fact into silence (AGENTS
section 4, no silent fallback). Otherwise it restores ``0061``'s schema, the frozen lists and the body of ``am_guard_audit_run_frozen``.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0062_hosts_stage_models"
down_revision: str | None = "0061_decision_memory_m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_PROVIDERS = "'claude_code', 'codex', 'anthropic_api', 'openai_api', 'openrouter_api'"
_ACCESS = "'subscription', 'api'"
_COOLDOWN_REASONS = "'access_denied', 'quota_exceeded', 'model_not_found'"
_KITS = "'claude_only', 'codex_only', 'custom'"
#: The roles of a cell (`StageCellRole`): the single answer, the two legs of an ensemble and its judge.
_CELL_ROLE_ALTERNATIVES = "main|leg1|leg2|judge"

#: ``RunQueueReason`` of contract 1.45.0 (``auditmanager.executors.model.WAIT_REASONS``).
_WAIT_REASONS_0048 = "'executor_at_capacity', 'runner_offline', 'needs_reconsent'"
_WAIT_REASONS_0062 = _WAIT_REASONS_0048 + ", 'model_unavailable'"

#: ``audit_run``'s frozen list as ``0060`` left it, restated: a migration never imports another.
_FROZEN_RUN_0060 = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id', 'executor_group_revision_id', 'routing_rule_revision_id', "
    "'started_by_user_uid', 'started_from_run_id', 'start_stage_id'"
)
_FROZEN_RUN_0062 = _FROZEN_RUN_0060 + ", 'stage_plan'"

#: The frozen lists of the executor tables as ``0030``, ``0031``, ``0046`` and ``0047`` left them.
_FROZEN_CONNECTION_0030 = "'connection_id', 'kind', 'display_name', 'created_at', 'created_by'"
_FROZEN_CONNECTION_0062 = _FROZEN_CONNECTION_0030 + ", 'system_managed', 'host_id', 'capacity_pool'"
_FROZEN_TOKEN_0031 = "'token_id', 'connection_id', 'token_prefix', 'token_hash', 'created_at', 'created_by', 'expires_at'"
_FROZEN_TOKEN_0062 = _FROZEN_TOKEN_0031 + ", 'host_id'"
_FROZEN_ENROLLMENT_0046 = (
    "'enrollment_id', 'connection_id', 'secret_prefix', 'secret_hash', 'created_at', 'created_by', 'expires_at'"
)
_FROZEN_ENROLLMENT_0062 = _FROZEN_ENROLLMENT_0046 + ", 'host_id'"
_FROZEN_INSTALL_0046 = (
    "'install_id', 'connection_id', 'access', 'ssh_host', 'ssh_port', 'ssh_user', 'created_at', 'created_by'"
)
_FROZEN_INSTALL_0062 = _FROZEN_INSTALL_0046 + ", 'host_id'"
_FROZEN_GROUP_0047 = "'group_id', 'display_name', 'created_at', 'created_by'"
_FROZEN_GROUP_0062 = _FROZEN_GROUP_0047 + ", 'system_managed'"

#: ``0048``'s body, verbatim, restored by the downgrade.
_RUN_FROZEN_FUNCTION_0048 = """
        CREATE OR REPLACE FUNCTION am_guard_audit_run_frozen() RETURNS trigger
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

#: ``0048``'s body plus the rule of a planned run: it is bound when, and only when, every cell of its plan has its binding row.
_RUN_FROZEN_FUNCTION_0062 = _RUN_FROZEN_FUNCTION_0048.replace(
    """            FOREACH v_column IN ARRAY TG_ARGV LOOP""",
    """            IF NEW.stage_plan IS NOT NULL
               AND OLD.binding_state = 'pending' AND NEW.binding_state = 'bound' THEN
                -- A planned run is bound cell by cell, in the transaction that binds it: every cell of the frozen plan has its
                -- row of audit_run_cell_binding and no other row exists (the rows are written once, so a plain read is exact).
                IF (SELECT count(*) FROM audit_run_cell_binding b WHERE b.run_id = NEW.run_id)
                       IS DISTINCT FROM jsonb_array_length(NEW.stage_plan -> 'cells')
                   OR EXISTS (
                       SELECT 1 FROM jsonb_array_elements(NEW.stage_plan -> 'cells') AS cell
                        WHERE NOT EXISTS (
                            SELECT 1 FROM audit_run_cell_binding b
                             WHERE b.run_id = NEW.run_id AND b.cell_key = cell ->> 'cell_key')
                   ) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: run % is bound only when every cell of its stage plan has a binding',
                        OLD.run_id
                        USING ERRCODE = 'AM001',
                              HINT = 'Write audit_run_cell_binding for every cell of the plan, then move the run to bound.';
                END IF;
            END IF;
            FOREACH v_column IN ARRAY TG_ARGV LOOP""",
    1,
)

_GAPLESS_FUNCTION = """
        CREATE FUNCTION am_check_gapless_number() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_key_column    text := TG_ARGV[0];
            v_number_column text := TG_ARGV[1];
            v_key           text := to_jsonb(NEW) ->> TG_ARGV[0];
            v_new           integer := (to_jsonb(NEW) ->> TG_ARGV[1])::integer;
            v_last          integer;
        BEGIN
            -- One writer per (table, key) at a time: the rule reads the highest number, so two writers must queue.
            PERFORM pg_advisory_xact_lock(hashtextextended(TG_TABLE_NAME || ':' || v_key, 0));
            EXECUTE format('SELECT max(%I) FROM %I WHERE %I = $1', v_number_column, TG_TABLE_NAME, v_key_column)
                INTO v_last USING v_key;
            IF v_new <> coalesce(v_last, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: % of % has number % and cannot take %',
                    TG_TABLE_NAME, v_key, coalesce(v_last, 0), v_new
                    USING ERRCODE = 'AM001',
                          HINT = 'Numbers are 1, 2, 3, ... per key without a gap.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: A task is claimed by the connection's own token or by a token of the host that owns the connection.
_TASK_CLAIMER_FUNCTION = """
        CREATE FUNCTION am_check_executor_task_claimer() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.claimed_by_token_id IS NULL THEN
                RETURN NEW;
            END IF;
            IF NOT EXISTS (
                SELECT 1
                  FROM executor_runner_token t
                  JOIN executor_connection c ON c.connection_id = NEW.connection_id
                 WHERE t.token_id = NEW.claimed_by_token_id
                   AND (t.connection_id = NEW.connection_id
                        OR (t.host_id IS NOT NULL AND t.host_id = c.host_id))
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: token % does not serve connection % of task %',
                    NEW.claimed_by_token_id, NEW.connection_id, NEW.task_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A task is claimed by a token of its connection or by a token of the host that owns the connection.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

_SWITCH_FUNCTION = """
        CREATE FUNCTION am_check_stage_layout_switch() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NEW.enabled AND NOT EXISTS (
                SELECT 1 FROM stage_layout_revision r WHERE r.layout_key = NEW.layout_key
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: stage layout % has no revision and cannot be switched on', NEW.layout_key
                    USING ERRCODE = 'AM001',
                          HINT = 'Save a revision of the layout first; the switch puts a revision in force.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: A row of ``audit_run_cell_binding`` is accepted for a pending planned run only, for a cell of its plan, for a member of the group
#: revision that is a system connection and pins exactly the cell's model.
_CELL_BINDING_FUNCTION = """
        CREATE FUNCTION am_check_audit_run_cell_binding() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_state text;
            v_plan  jsonb;
            v_model text;
        BEGIN
            SELECT r.binding_state, r.stage_plan INTO v_state, v_plan
              FROM audit_run r WHERE r.run_id = NEW.run_id FOR SHARE;
            IF v_plan IS NULL OR v_state IS DISTINCT FROM 'pending' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: run % takes a cell binding only while it is pending with a stage plan', NEW.run_id
                    USING ERRCODE = 'AM001',
                          HINT = 'Cells are bound together, once, in the transaction that binds the run.';
            END IF;
            SELECT cell ->> 'model_id' INTO v_model
              FROM jsonb_array_elements(v_plan -> 'cells') AS cell
             WHERE cell ->> 'cell_key' = NEW.cell_key;
            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: run % has no cell % in its stage plan', NEW.run_id, NEW.cell_key
                    USING ERRCODE = 'AM001';
            END IF;
            IF NOT EXISTS (
                SELECT 1
                  FROM executor_group_member m
                  JOIN executor_connection_revision cr ON cr.revision_id = m.connection_revision_id
                  JOIN executor_connection c ON c.connection_id = cr.connection_id
                 WHERE m.group_revision_id = NEW.group_revision_id
                   AND m.connection_revision_id = NEW.connection_revision_id
                   AND c.system_managed
                   AND cr.pin_id = v_model
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: connection revision % is not a system member of group revision % pinning the model of cell % of run %',
                    NEW.connection_revision_id, NEW.group_revision_id, NEW.cell_key, NEW.run_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A cell is bound to a member of a system group for exactly its model.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def _guard(table: str, trigger: str, function: str, columns: str) -> None:
    op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute(
        f"CREATE TRIGGER {trigger} BEFORE UPDATE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION {function}({columns})"
    )


def upgrade() -> None:
    op.execute(_GAPLESS_FUNCTION)

    # --- the host ----------------------------------------------------------------------------------
    op.execute(
        f"""
        CREATE TABLE executor_host (
            host_id      text PRIMARY KEY,
            display_name text NOT NULL,
            created_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by   text NOT NULL,
            archived_at  timestamptz NULL,
            archived_by  text NULL,
            CONSTRAINT ck_executor_host_id_format CHECK (host_id ~ '^exh_{ULID}$'),
            CONSTRAINT ck_executor_host_display_name CHECK (char_length(display_name) BETWEEN 1 AND 120),
            CONSTRAINT ck_executor_host_created_by_format CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_host_archived_by_format CHECK (archived_by IS NULL OR archived_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_host_archive_pair CHECK ((archived_at IS NULL) = (archived_by IS NULL))
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_host_name_active ON executor_host (lower(display_name)) "
        "WHERE archived_at IS NULL"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_frozen_guard BEFORE UPDATE ON executor_host "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('host_id', 'display_name', 'created_at', 'created_by')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_write_once BEFORE UPDATE ON executor_host "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns('archived_at', 'archived_by')"
    )
    # Archive is not deletion: a host is never removed, because its identity stays in the call journal.
    op.execute(
        "CREATE TRIGGER trg_executor_host_no_delete BEFORE DELETE ON executor_host "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    op.execute(
        f"""
        CREATE TABLE executor_host_use_event (
            use_event_id text PRIMARY KEY,
            host_id      text NOT NULL REFERENCES executor_host (host_id),
            event_no     integer NOT NULL,
            enabled      boolean NOT NULL,
            set_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by       text NOT NULL,
            CONSTRAINT uq_executor_host_use_event_number UNIQUE (host_id, event_no),
            CONSTRAINT ck_executor_host_use_event_id_format CHECK (use_event_id ~ '^exhu_{ULID}$'),
            CONSTRAINT ck_executor_host_use_event_host_id_format CHECK (host_id ~ '^exh_{ULID}$'),
            CONSTRAINT ck_executor_host_use_event_number CHECK (event_no >= 1),
            CONSTRAINT ck_executor_host_use_event_set_by_format CHECK (set_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_use_event_append_only BEFORE UPDATE OR DELETE ON executor_host_use_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_use_event_number BEFORE INSERT ON executor_host_use_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('host_id', 'event_no')"
    )

    op.execute(
        f"""
        CREATE TABLE executor_host_slot_event (
            slot_event_id text PRIMARY KEY,
            host_id       text NOT NULL REFERENCES executor_host (host_id),
            event_no      integer NOT NULL,
            provider      text NOT NULL,
            slots         smallint NOT NULL,
            set_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by        text NOT NULL,
            CONSTRAINT uq_executor_host_slot_event_number UNIQUE (host_id, event_no),
            CONSTRAINT ck_executor_host_slot_event_id_format CHECK (slot_event_id ~ '^exhs_{ULID}$'),
            CONSTRAINT ck_executor_host_slot_event_host_id_format CHECK (host_id ~ '^exh_{ULID}$'),
            CONSTRAINT ck_executor_host_slot_event_number CHECK (event_no >= 1),
            CONSTRAINT ck_executor_host_slot_event_provider CHECK (provider IN ({_PROVIDERS})),
            CONSTRAINT ck_executor_host_slot_event_slots CHECK (slots BETWEEN 1 AND 16),
            CONSTRAINT ck_executor_host_slot_event_set_by_format CHECK (set_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_slot_event_append_only BEFORE UPDATE OR DELETE ON executor_host_slot_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_host_slot_event_number BEFORE INSERT ON executor_host_slot_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('host_id', 'event_no')"
    )

    # --- the host token, the grant and the install session: exactly one of a connection and a host -------
    op.execute("ALTER TABLE executor_runner_token ALTER COLUMN connection_id DROP NOT NULL")
    op.execute("ALTER TABLE executor_runner_token ADD COLUMN host_id text NULL REFERENCES executor_host (host_id)")
    op.execute(
        f"ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_host_id_format "
        f"CHECK (host_id IS NULL OR host_id ~ '^exh_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_target "
        "CHECK ((connection_id IS NULL) <> (host_id IS NULL))"
    )
    op.execute("ALTER TABLE executor_runner_token ADD CONSTRAINT uq_executor_runner_token_host UNIQUE (token_id, host_id)")
    op.execute(
        "CREATE INDEX ix_executor_runner_token_host ON executor_runner_token (host_id, created_at DESC, token_id DESC) "
        "WHERE host_id IS NOT NULL"
    )
    _guard("executor_runner_token", "trg_executor_runner_token_frozen_guard", "am_guard_frozen_columns", _FROZEN_TOKEN_0062)

    op.execute("ALTER TABLE executor_enrollment ALTER COLUMN connection_id DROP NOT NULL")
    op.execute("ALTER TABLE executor_enrollment ADD COLUMN host_id text NULL REFERENCES executor_host (host_id)")
    op.execute(
        f"ALTER TABLE executor_enrollment ADD CONSTRAINT ck_executor_enrollment_host_id_format "
        f"CHECK (host_id IS NULL OR host_id ~ '^exh_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE executor_enrollment ADD CONSTRAINT ck_executor_enrollment_target "
        "CHECK ((connection_id IS NULL) <> (host_id IS NULL))"
    )
    op.execute(
        "ALTER TABLE executor_enrollment ADD CONSTRAINT fk_executor_enrollment_host_token "
        "FOREIGN KEY (runner_token_id, host_id) REFERENCES executor_runner_token (token_id, host_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_enrollment_pending_host ON executor_enrollment (host_id) "
        "WHERE host_id IS NOT NULL AND redeemed_at IS NULL AND revoked_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_executor_enrollment_host ON executor_enrollment (host_id, created_at DESC, enrollment_id DESC) "
        "WHERE host_id IS NOT NULL"
    )
    _guard("executor_enrollment", "trg_executor_enrollment_frozen_guard", "am_guard_frozen_columns", _FROZEN_ENROLLMENT_0062)

    op.execute("ALTER TABLE executor_agent_install ALTER COLUMN connection_id DROP NOT NULL")
    op.execute("ALTER TABLE executor_agent_install ADD COLUMN host_id text NULL REFERENCES executor_host (host_id)")
    op.execute(
        f"ALTER TABLE executor_agent_install ADD CONSTRAINT ck_executor_agent_install_host_id_format "
        f"CHECK (host_id IS NULL OR host_id ~ '^exh_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE executor_agent_install ADD CONSTRAINT ck_executor_agent_install_target "
        "CHECK ((connection_id IS NULL) <> (host_id IS NULL))"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_agent_install_open_host ON executor_agent_install (host_id) "
        "WHERE host_id IS NOT NULL AND state NOT IN ('succeeded', 'failed')"
    )
    op.execute(
        "CREATE INDEX ix_executor_agent_install_host ON executor_agent_install (host_id, created_at DESC, install_id DESC) "
        "WHERE host_id IS NOT NULL"
    )
    _guard("executor_agent_install", "trg_executor_agent_install_frozen_guard", "am_guard_frozen_columns", _FROZEN_INSTALL_0062)

    # The task's key to its claiming token named (token, connection); a host token has no connection. A plain key and the trigger.
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT fk_executor_task_token")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT fk_executor_task_token "
        "FOREIGN KEY (claimed_by_token_id) REFERENCES executor_runner_token (token_id)"
    )
    op.execute(_TASK_CLAIMER_FUNCTION)
    op.execute(
        "CREATE TRIGGER trg_executor_task_claimer BEFORE INSERT OR UPDATE OF claimed_by_token_id ON executor_task "
        "FOR EACH ROW EXECUTE FUNCTION am_check_executor_task_claimer()"
    )

    # --- system connections and groups -------------------------------------------------------------
    op.execute(
        "ALTER TABLE executor_connection "
        "ADD COLUMN system_managed boolean NOT NULL DEFAULT false, "
        "ADD COLUMN host_id text NULL REFERENCES executor_host (host_id), "
        "ADD COLUMN capacity_pool text NULL"
    )
    op.execute(
        f"ALTER TABLE executor_connection ADD CONSTRAINT ck_executor_connection_host_id_format "
        f"CHECK (host_id IS NULL OR host_id ~ '^exh_{ULID}$')"
    )
    # A system connection belongs to one host and one provider of it: the pool is `<host_id>:<provider>`. Neither is ever set on a
    # connection a user made.
    op.execute(
        "ALTER TABLE executor_connection ADD CONSTRAINT ck_executor_connection_pool CHECK ("
        "(system_managed AND kind = 'pull' AND host_id IS NOT NULL AND capacity_pool IS NOT NULL "
        "AND left(capacity_pool, char_length(host_id) + 1) = host_id || ':' "
        f"AND substr(capacity_pool, char_length(host_id) + 2) IN ({_PROVIDERS})) "
        "OR (NOT system_managed AND host_id IS NULL AND capacity_pool IS NULL))"
    )
    op.execute(
        "CREATE INDEX ix_executor_connection_pool ON executor_connection (capacity_pool, connection_id) "
        "WHERE capacity_pool IS NOT NULL"
    )
    _guard("executor_connection", "trg_executor_connection_frozen_guard", "am_guard_frozen_columns", _FROZEN_CONNECTION_0062)

    op.execute("ALTER TABLE executor_group ADD COLUMN system_managed boolean NOT NULL DEFAULT false")
    _guard("executor_group", "trg_executor_group_frozen_guard", "am_guard_frozen_columns", _FROZEN_GROUP_0062)

    # --- the latest report and the passive refusal -------------------------------------------------
    op.execute(
        f"""
        CREATE TABLE executor_host_report (
            host_id        text PRIMARY KEY,
            token_id       text NOT NULL,
            agent_version  text NOT NULL,
            providers      jsonb NOT NULL,
            slots          jsonb NOT NULL,
            report_sha256  text NOT NULL,
            reported_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_executor_host_report_host FOREIGN KEY (host_id) REFERENCES executor_host (host_id),
            CONSTRAINT fk_executor_host_report_token FOREIGN KEY (token_id, host_id)
                REFERENCES executor_runner_token (token_id, host_id),
            CONSTRAINT ck_executor_host_report_host_id_format CHECK (host_id ~ '^exh_{ULID}$'),
            CONSTRAINT ck_executor_host_report_token_id_format CHECK (token_id ~ '^ern_{ULID}$'),
            CONSTRAINT ck_executor_host_report_agent_version
                CHECK (agent_version ~ '^[0-9A-Za-z][0-9A-Za-z.+_-]{{0,63}}$'),
            CONSTRAINT ck_executor_host_report_providers
                CHECK (CASE WHEN jsonb_typeof(providers) = 'array' THEN jsonb_array_length(providers) <= 8 ELSE false END),
            CONSTRAINT ck_executor_host_report_slots CHECK (jsonb_typeof(slots) = 'object'),
            CONSTRAINT ck_executor_host_report_sha256 CHECK (report_sha256 ~ '^[0-9a-f]{{64}}$')
        );
        """
    )

    op.execute(
        f"""
        CREATE TABLE executor_model_cooldown (
            host_id  text NOT NULL REFERENCES executor_host (host_id),
            provider text NOT NULL,
            model_id text NOT NULL,
            until    timestamptz NOT NULL,
            reason   text NOT NULL,
            set_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (host_id, provider, model_id),
            CONSTRAINT ck_executor_model_cooldown_host_id_format CHECK (host_id ~ '^exh_{ULID}$'),
            CONSTRAINT ck_executor_model_cooldown_provider CHECK (provider IN ({_PROVIDERS})),
            CONSTRAINT ck_executor_model_cooldown_model CHECK (char_length(model_id) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_model_cooldown_reason CHECK (reason IN ({_COOLDOWN_REASONS})),
            CONSTRAINT ck_executor_model_cooldown_window CHECK (until > set_at)
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_model_cooldown_frozen_guard BEFORE UPDATE ON executor_model_cooldown "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns('host_id', 'provider', 'model_id')"
    )

    # --- the stage layout --------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE stage_layout (
            layout_key text PRIMARY KEY,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_stage_layout_key CHECK (layout_key = 'default')
        );
        """
    )
    op.execute("INSERT INTO stage_layout (layout_key) VALUES ('default')")
    op.execute(
        "CREATE TRIGGER trg_stage_layout_immutable BEFORE UPDATE OR DELETE ON stage_layout "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        f"""
        CREATE TABLE stage_layout_revision (
            layout_revision_id text PRIMARY KEY,
            layout_key         text NOT NULL REFERENCES stage_layout (layout_key),
            revision_no        integer NOT NULL,
            kit                text NOT NULL,
            cells              jsonb NOT NULL,
            created_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by         text NOT NULL,
            CONSTRAINT uq_stage_layout_revision_number UNIQUE (layout_key, revision_no),
            CONSTRAINT ck_stage_layout_revision_id_format CHECK (layout_revision_id ~ '^slr_{ULID}$'),
            CONSTRAINT ck_stage_layout_revision_number CHECK (revision_no >= 1),
            CONSTRAINT ck_stage_layout_revision_kit CHECK (kit IN ({_KITS})),
            CONSTRAINT ck_stage_layout_revision_cells
                CHECK (CASE WHEN jsonb_typeof(cells) = 'array' THEN jsonb_array_length(cells) BETWEEN 1 AND 32 ELSE false END),
            CONSTRAINT ck_stage_layout_revision_created_by_format CHECK (created_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_stage_layout_revision_append_only BEFORE UPDATE OR DELETE ON stage_layout_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_stage_layout_revision_number BEFORE INSERT ON stage_layout_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('layout_key', 'revision_no')"
    )
    op.execute(
        f"""
        CREATE TABLE stage_layout_switch_event (
            switch_event_id text PRIMARY KEY,
            layout_key      text NOT NULL REFERENCES stage_layout (layout_key),
            event_no        integer NOT NULL,
            enabled         boolean NOT NULL,
            set_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by          text NOT NULL,
            CONSTRAINT uq_stage_layout_switch_event_number UNIQUE (layout_key, event_no),
            CONSTRAINT ck_stage_layout_switch_event_id_format CHECK (switch_event_id ~ '^sls_{ULID}$'),
            CONSTRAINT ck_stage_layout_switch_event_number CHECK (event_no >= 1),
            CONSTRAINT ck_stage_layout_switch_event_set_by_format CHECK (set_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_stage_layout_switch_event_append_only BEFORE UPDATE OR DELETE ON stage_layout_switch_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_stage_layout_switch_event_number BEFORE INSERT ON stage_layout_switch_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_gapless_number('layout_key', 'event_no')"
    )
    op.execute(_SWITCH_FUNCTION)
    op.execute(
        "CREATE TRIGGER trg_stage_layout_switch_enabled BEFORE INSERT ON stage_layout_switch_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_stage_layout_switch()"
    )

    # --- the run: the plan, the shapes, the wait reason, the guard ---------------------------------
    op.execute("ALTER TABLE audit_run ADD COLUMN stage_plan jsonb NULL")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_stage_plan_shape CHECK (stage_plan IS NULL OR ("
        "jsonb_typeof(stage_plan) = 'object' AND jsonb_typeof(stage_plan -> 'cells') = 'array' "
        "AND jsonb_array_length(stage_plan -> 'cells') BETWEEN 1 AND 32))"
    )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_binding_shape")
    # The three shapes of 0048 gain `stage_plan IS NULL`; a fourth, planned shape has no group, no connection revision, no preset and
    # no rule -- its cells carry them (audit_run_cell_binding).
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_binding_shape CHECK ("
        "(binding_state = 'frozen_at_start' AND stage_plan IS NULL AND executor_group_revision_id IS NULL "
        "AND routing_rule_revision_id IS NULL) "
        "OR (binding_state = 'pending' AND stage_plan IS NULL AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NULL AND preset_revision_id IS NULL) "
        "OR (binding_state = 'bound' AND stage_plan IS NULL AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NOT NULL AND preset_revision_id IS NULL) "
        "OR (binding_state IN ('pending', 'bound') AND stage_plan IS NOT NULL AND executor_group_revision_id IS NULL "
        "AND routing_rule_revision_id IS NULL AND connection_revision_id IS NULL AND preset_revision_id IS NULL))"
    )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_wait_reason")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_reason "
        f"CHECK (wait_reason IS NULL OR wait_reason IN ({_WAIT_REASONS_0062}))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_model_unavailable "
        "CHECK (wait_reason IS DISTINCT FROM 'model_unavailable' OR stage_plan IS NOT NULL)"
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.stage_plan IS "
        "'HOSTS-SEAL-1 (plan 2026-11-09 section 4.5): the plan the run froze at its start, one cell per row and role of the stage "
        "layout with the model, the effort, the limits and the access. A planned run is bound by cell (audit_run_cell_binding).';"
    )

    op.execute(
        f"""
        CREATE TABLE audit_run_cell_binding (
            run_id                 text NOT NULL REFERENCES audit_run (run_id),
            cell_key               text NOT NULL,
            group_revision_id      text NOT NULL REFERENCES executor_group_revision (group_revision_id),
            connection_revision_id text NOT NULL REFERENCES executor_connection_revision (revision_id),
            bound_at               timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (run_id, cell_key),
            CONSTRAINT ck_audit_run_cell_binding_run_id_format CHECK (run_id ~ '^run_{ULID}$'),
            CONSTRAINT ck_audit_run_cell_binding_cell_key
                CHECK (cell_key ~ '^[a-z][a-z0-9_]{{0,63}}:({_CELL_ROLE_ALTERNATIVES})$'),
            CONSTRAINT ck_audit_run_cell_binding_group_revision_id_format CHECK (group_revision_id ~ '^exgr_{ULID}$'),
            CONSTRAINT ck_audit_run_cell_binding_connection_revision_id_format
                CHECK (connection_revision_id ~ '^excr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_audit_run_cell_binding_connection ON audit_run_cell_binding (connection_revision_id)"
    )
    op.execute(_CELL_BINDING_FUNCTION)
    op.execute(
        "CREATE TRIGGER trg_audit_run_cell_binding_member BEFORE INSERT ON audit_run_cell_binding "
        "FOR EACH ROW EXECUTE FUNCTION am_check_audit_run_cell_binding()"
    )
    # Write-once: a cell is bound to one member for the life of the run, with no re-routing after binding (ADR-0026 decision 16).
    op.execute(
        "CREATE TRIGGER trg_audit_run_cell_binding_immutable BEFORE UPDATE OR DELETE ON audit_run_cell_binding "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    op.execute(_RUN_FROZEN_FUNCTION_0062)
    _guard("audit_run", "trg_audit_run_frozen_guard", "am_guard_audit_run_frozen", _FROZEN_RUN_0062)

    # --- the call journal --------------------------------------------------------------------------
    for table in ("model_call", "provider_call_effect"):
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN stage_key text NULL, ADD COLUMN host_id text NULL, ADD COLUMN access text NULL"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_stage_key "
            "CHECK (stage_key IS NULL OR stage_key ~ '^[a-z][a-z0-9_]{0,63}$')"
        )
        # A bare identity, not a foreign key: the journal outlives anything it names.
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_host_id_format "
            f"CHECK (host_id IS NULL OR host_id ~ '^exh_{ULID}$')"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_access CHECK (access IS NULL OR access IN ({_ACCESS}))"
        )

    comments = {
        "executor_host": (
            "HOSTS-SEAL-1 (plan 2026-11-09 section 3.2): a server -- one agent process, one host token. Configuration, kept by the "
            "product purge like the executor connections. Archive is one-way and is not deletion."
        ),
        "executor_host_use_event": (
            "HOSTS-SEAL-1: the Use journal of a host -- author, time, enabled. Append-only, numbered without a gap per host; the "
            "latest event is the switch."
        ),
        "executor_host_slot_event": (
            "HOSTS-SEAL-1: the slots of a provider on a host. Append-only, numbered without a gap per host; the latest event of a "
            "provider is the number in force."
        ),
        "executor_host_report": (
            "HOSTS-SEAL-1: the latest health and capability snapshot a host agent reported (providers, models and their states, "
            "slots). Written only when the report changes; the pulse is the last_seen_at of the token."
        ),
        "executor_model_cooldown": (
            "HOSTS-SEAL-1 (plan section 5.5): a (host, provider, model) taken out of availability until a time after a real "
            "refusal. One row per triple, replaced by the next refusal."
        ),
        "stage_layout": "HOSTS-SEAL-1: the layout of models over the analysis stages for this installation (one: key default).",
        "stage_layout_revision": (
            "HOSTS-SEAL-1: an append-only revision of the stage layout, numbered without a gap: the kit and one cell per row and role."
        ),
        "stage_layout_switch_event": (
            "HOSTS-SEAL-1: the switch that puts the stage layout in force, as an append-only journal; the latest event is the "
            "switch and an empty table means off."
        ),
        "audit_run_cell_binding": (
            "HOSTS-SEAL-1: one row per cell of a planned run -- the group revision and the member connection revision it was bound "
            "to at dispatch. Written once, in the transaction that binds the run; never updated or deleted."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in (
        "executor_host", "stage_layout_revision", "stage_layout_switch_event", "audit_run_cell_binding",
        "executor_host_report", "executor_model_cooldown",
    ):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    for label, query in (
        ("audit_run.stage_plan", "SELECT EXISTS (SELECT 1 FROM audit_run WHERE stage_plan IS NOT NULL)"),
        ("executor_connection system objects",
         "SELECT EXISTS (SELECT 1 FROM executor_connection WHERE system_managed OR host_id IS NOT NULL)"),
        ("executor_group system objects", "SELECT EXISTS (SELECT 1 FROM executor_group WHERE system_managed)"),
        ("host-bound credentials",
         "SELECT EXISTS (SELECT 1 FROM executor_runner_token WHERE host_id IS NOT NULL) "
         "OR EXISTS (SELECT 1 FROM executor_enrollment WHERE host_id IS NOT NULL) "
         "OR EXISTS (SELECT 1 FROM executor_agent_install WHERE host_id IS NOT NULL)"),
        ("model_call / provider_call_effect stage_key, host_id or access",
         "SELECT EXISTS (SELECT 1 FROM model_call WHERE stage_key IS NOT NULL OR host_id IS NOT NULL OR access IS NOT NULL) "
         "OR EXISTS (SELECT 1 FROM provider_call_effect "
         "WHERE stage_key IS NOT NULL OR host_id IS NOT NULL OR access IS NOT NULL)"),
    ):
        if bind.execute(text(query)).scalar_one():
            retained.append(label)
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0062_hosts_stage_models with retained host, layout or planned-run data "
            f"({', '.join(retained)}); restore a database backup instead"
        )

    for table in ("model_call", "provider_call_effect"):
        for constraint in (f"ck_{table}_access", f"ck_{table}_host_id_format", f"ck_{table}_stage_key"):
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
        op.execute(f"ALTER TABLE {table} DROP COLUMN access, DROP COLUMN host_id, DROP COLUMN stage_key")

    _guard("audit_run", "trg_audit_run_frozen_guard", "am_guard_audit_run_frozen", _FROZEN_RUN_0060)
    op.execute(_RUN_FROZEN_FUNCTION_0048)
    op.execute("DROP TABLE audit_run_cell_binding")
    op.execute("DROP FUNCTION am_check_audit_run_cell_binding()")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_wait_model_unavailable")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_wait_reason")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_wait_reason "
        f"CHECK (wait_reason IS NULL OR wait_reason IN ({_WAIT_REASONS_0048}))"
    )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_binding_shape")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_binding_shape CHECK ("
        "(binding_state = 'frozen_at_start' AND executor_group_revision_id IS NULL "
        "AND routing_rule_revision_id IS NULL) "
        "OR (binding_state = 'pending' AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NULL AND preset_revision_id IS NULL) "
        "OR (binding_state = 'bound' AND executor_group_revision_id IS NOT NULL "
        "AND connection_revision_id IS NOT NULL AND preset_revision_id IS NULL))"
    )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_stage_plan_shape")
    op.execute("ALTER TABLE audit_run DROP COLUMN stage_plan")

    for table in ("stage_layout_switch_event", "stage_layout_revision", "stage_layout"):
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION am_check_stage_layout_switch()")
    op.execute("DROP TABLE executor_model_cooldown")
    op.execute("DROP TABLE executor_host_report")

    _guard("executor_group", "trg_executor_group_frozen_guard", "am_guard_frozen_columns", _FROZEN_GROUP_0047)
    op.execute("ALTER TABLE executor_group DROP COLUMN system_managed")
    _guard("executor_connection", "trg_executor_connection_frozen_guard", "am_guard_frozen_columns", _FROZEN_CONNECTION_0030)
    op.execute("DROP INDEX ix_executor_connection_pool")
    op.execute("ALTER TABLE executor_connection DROP CONSTRAINT ck_executor_connection_pool")
    op.execute("ALTER TABLE executor_connection DROP CONSTRAINT ck_executor_connection_host_id_format")
    op.execute("ALTER TABLE executor_connection DROP COLUMN capacity_pool, DROP COLUMN host_id, DROP COLUMN system_managed")

    op.execute("DROP TRIGGER trg_executor_task_claimer ON executor_task")
    op.execute("DROP FUNCTION am_check_executor_task_claimer()")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT fk_executor_task_token")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT fk_executor_task_token "
        "FOREIGN KEY (claimed_by_token_id, connection_id) REFERENCES executor_runner_token (token_id, connection_id)"
    )

    _guard("executor_agent_install", "trg_executor_agent_install_frozen_guard", "am_guard_frozen_columns", _FROZEN_INSTALL_0046)
    op.execute("DROP INDEX ix_executor_agent_install_host")
    op.execute("DROP INDEX ux_executor_agent_install_open_host")
    op.execute("ALTER TABLE executor_agent_install DROP CONSTRAINT ck_executor_agent_install_target")
    op.execute("ALTER TABLE executor_agent_install DROP CONSTRAINT ck_executor_agent_install_host_id_format")
    op.execute("ALTER TABLE executor_agent_install DROP COLUMN host_id")
    op.execute("ALTER TABLE executor_agent_install ALTER COLUMN connection_id SET NOT NULL")

    _guard("executor_enrollment", "trg_executor_enrollment_frozen_guard", "am_guard_frozen_columns", _FROZEN_ENROLLMENT_0046)
    op.execute("DROP INDEX ix_executor_enrollment_host")
    op.execute("DROP INDEX ux_executor_enrollment_pending_host")
    op.execute("ALTER TABLE executor_enrollment DROP CONSTRAINT fk_executor_enrollment_host_token")
    op.execute("ALTER TABLE executor_enrollment DROP CONSTRAINT ck_executor_enrollment_target")
    op.execute("ALTER TABLE executor_enrollment DROP CONSTRAINT ck_executor_enrollment_host_id_format")
    op.execute("ALTER TABLE executor_enrollment DROP COLUMN host_id")
    op.execute("ALTER TABLE executor_enrollment ALTER COLUMN connection_id SET NOT NULL")

    _guard("executor_runner_token", "trg_executor_runner_token_frozen_guard", "am_guard_frozen_columns", _FROZEN_TOKEN_0031)
    op.execute("DROP INDEX ix_executor_runner_token_host")
    op.execute("ALTER TABLE executor_runner_token DROP CONSTRAINT uq_executor_runner_token_host")
    op.execute("ALTER TABLE executor_runner_token DROP CONSTRAINT ck_executor_runner_token_target")
    op.execute("ALTER TABLE executor_runner_token DROP CONSTRAINT ck_executor_runner_token_host_id_format")
    op.execute("ALTER TABLE executor_runner_token DROP COLUMN host_id")
    op.execute("ALTER TABLE executor_runner_token ALTER COLUMN connection_id SET NOT NULL")

    op.execute("DROP TABLE executor_host_slot_event")
    op.execute("DROP TABLE executor_host_use_event")
    op.execute("DROP TABLE executor_host")
    op.execute("DROP FUNCTION am_check_gapless_number()")
