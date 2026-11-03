"""Executor groups, routing rules and the routing mode.

Revision ID: 0047_executor_groups_rules
Revises: 0046_executor_capacity_enroll

The revision id is 25 characters, not the file name's 33: ``alembic_version.version_num`` is ``varchar(32)``.
The file name keeps its full form; Alembic reads the id from the ``revision`` variable below.

`EXEC2-SEAL-2` (ADR-0026 decisions 10, 11, 14 and 17, owner rulings `R-149a` to `R-149f`;
``docs/program/dispatch/EXEC2-PLAN.md``). It creates the storage of the group and rule surface of contract 1.16.0
and nothing that behaves: no statement writes any of it until a stage-2 lane implements the operation that does,
and before the cut-over nothing reads it. A database at ``0046`` upgrades with no row touched.

The name «group» was taken: ``ar_v3_run_group`` (``0032``) is the six-Run group of the AR v3 beta. These tables are
``executor_group*`` and their identities ``exg``, ``exgr``, ``exrr`` and ``exrm``.

What this revision adds
-----------------------
``executor_group`` (``exg``)
    a group of interchangeable executors and its name. Archiving is one-way and not deletion (``archived_at`` and
    ``archived_by`` are write-once, and a row cannot be deleted: ``trg_executor_group_no_delete``); an active group's
    name is unique without regard to case. ``rotation_cursor`` is the tie-break rotation of ``least_loaded`` dispatch,
    persisted in the database (decision 14): the only column of the table that changes freely.
``executor_group_revision`` (``exgr``)
    one immutable revision: ``pin_id``, ``gateway_model``, ``billing``, the rate snapshot (USD per million tokens,
    copied from the provider lock when the revision is made), ``strategy`` (``least_loaded`` is the only value) and
    ``member_count`` (1 to 16), the number of members the revision is made with. Numbered 1, 2, 3, ... per group
    without a gap, and an archived group takes none (``am_check_executor_group_revision``).
``executor_group_member``
    the members of a revision: a connection and the **revision** of it the group snapshots, with an optional tie-break
    order (1 to 16, unique inside the revision). Immutable. ``am_check_executor_group_member`` holds the homogeneity of
    decision 10 in the database: the member's revision pins exactly the group revision's ``pin_id`` and
    ``gateway_model`` and shares its ``billing``, and its connection is not archived. A connection appears once per
    revision.
    **The membership of a revision is closed when the revision is made.** Row immutability alone would let a later
    ``INSERT`` add a member to a revision that had already admitted work, or a seventeenth to a full one, so the
    revision declares ``member_count`` (frozen with the row) and the database holds both ends: a member is refused when
    the revision already has ``member_count`` members, and a deferred constraint trigger
    (``trg_executor_group_revision_has_members``) requires **exactly** ``member_count`` members when the transaction
    that made the revision commits. Together: a committed revision always has exactly its declared members, and none can
    be added afterwards. (The count is read from the rows, never from ``xmin`` or ``txid_current()``, which a savepoint
    breaks.)
``executor_routing_rule_revision`` (``exrr``)
    the rule of a work kind (decision 11): append-only, numbered per work kind, targeting an immutable group revision
    of a group that is not archived (``am_check_executor_routing_rule``). The current rule of a work kind is its highest
    ``rule_no``; there is no view, so the schema's view count does not move.
``executor_routing_mode_event`` (``exrm``)
    the routing mode (decision 17) as an **append-only journal with no singleton row**: the mode in force is the event
    with the highest ``event_no``, and an empty table means ``legacy``. A ``rules`` event carries the digest of the
    preview that was confirmed and the confirmed mapping (one entry per converted work kind: the group, the group
    revision and the rule revision the change created); a ``legacy`` event (the rollback) carries neither. The number is
    gap-free and increasing: ``am_check_executor_routing_mode_event`` takes the advisory lock
    ``executor_routing_mode_event`` and requires ``event_no`` to be the highest number plus one, as the rule numbering
    does, so two writers are serialised and the history is linear. (A writer that numbers its own event takes the same
    lock first.)

Archive races
-------------
Archiving takes ``FOR UPDATE`` on the group row (``group_repository.get_group(lock=True)``). The three insert triggers
read the ``archived_at`` they decide on with ``FOR SHARE`` -- the group's in the revision chain and the rule check, the
connection's in the member check -- so an archive and a concurrent revision, rule or member insert serialise instead of
both passing a plain read.

The actor columns (``created_by``, ``archived_by``, ``set_by``, ``changed_by``) hold a ``usr`` identity and carry no
foreign key to ``app_user``, as in ``0030``. The rate columns are ``numeric(12,6)``: the pinned rates are decimal USD per
million tokens and are compared for equality between members, which a binary float would make unreliable.

Configuration like the executor connections: the product purge keeps these tables.

Downgrade
---------
Refused while any row exists in any of the five tables; restore a database backup instead. ``0048`` must be downgraded
first (its columns reference two of these tables, and its binding guards read ``executor_group_member``).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0047_executor_groups_rules"
down_revision: str | None = "0046_executor_capacity_enroll"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: Dependency order of creation; the downgrade drops them in reverse.
_NEW_TABLES = (
    "executor_group", "executor_group_revision", "executor_group_member",
    "executor_routing_rule_revision", "executor_routing_mode_event",
)
_NEW_FUNCTIONS = (
    "am_check_executor_group_revision", "am_check_executor_group_member", "am_check_executor_routing_rule",
    "am_require_executor_group_members", "am_check_executor_routing_mode_event",
)

#: ``auditmanager.executors.model.WORK_KINDS`` as ``ck_executor_route_work_kind`` has them since ``0042``.
_WORK_KINDS = (
    "'text_analysis', 'comparison_pair_check', 'comparison_sheet_changes', 'comparison_spec', "
    "'comparison_report', 'comparison_stage_review'"
)

_REVISION_CHAIN_FUNCTION = """
        CREATE FUNCTION am_check_executor_group_revision() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no    integer;
            v_archived boolean;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('executor_group_revision:' || NEW.group_id, 0));
            -- FOR SHARE: archiving takes the group row FOR UPDATE, so it and this insert serialise.
            SELECT (g.archived_at IS NOT NULL) INTO v_archived
              FROM executor_group g WHERE g.group_id = NEW.group_id FOR SHARE;
            IF v_archived THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: group % is archived and takes no revision', NEW.group_id
                    USING ERRCODE = 'AM001',
                          HINT = 'Archiving is one-way; make a new group instead.';
            END IF;
            SELECT max(revision_no) INTO last_no FROM executor_group_revision WHERE group_id = NEW.group_id;
            IF NEW.revision_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: group % has revision % and cannot take %',
                    NEW.group_id, coalesce(last_no, 0), NEW.revision_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Revisions are numbered 1, 2, 3, ... without a gap.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: Decision 10: a group is homogeneous. The member's revision must pin exactly the group revision's model and share its
#: billing, and the member's connection must not be archived. (The pinned rates follow from the pin.)
_MEMBER_FUNCTION = """
        CREATE FUNCTION am_check_executor_group_member() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_declared smallint;
            v_held     bigint;
            v_archived boolean;
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM executor_group_revision gr
                  JOIN executor_connection_revision cr ON cr.revision_id = NEW.connection_revision_id
                 WHERE gr.group_revision_id = NEW.group_revision_id
                   AND cr.pin_id = gr.pin_id
                   AND cr.gateway_model = gr.gateway_model
                   AND cr.billing = gr.billing
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: revision % of connection % is not the pin, model and billing of group revision %',
                    NEW.connection_revision_id, NEW.connection_id, NEW.group_revision_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A group is homogeneous: every member pins exactly the same model and is billed the same way.';
            END IF;
            -- The membership is closed when the revision is made: a committed revision holds exactly member_count
            -- members (trg_executor_group_revision_has_members), so any later insert finds the count reached.
            SELECT gr.member_count INTO v_declared
              FROM executor_group_revision gr WHERE gr.group_revision_id = NEW.group_revision_id;
            SELECT count(*) INTO v_held
              FROM executor_group_member m WHERE m.group_revision_id = NEW.group_revision_id;
            IF v_held >= v_declared THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: group revision % already has its % declared members and takes no other',
                    NEW.group_revision_id, v_declared
                    USING ERRCODE = 'AM001',
                          HINT = 'The membership of a group revision is closed when the revision is made; make a new revision.';
            END IF;
            -- FOR SHARE: archiving a connection updates its row, so it and this insert serialise.
            SELECT (c.archived_at IS NOT NULL) INTO v_archived
              FROM executor_connection c WHERE c.connection_id = NEW.connection_id FOR SHARE;
            IF v_archived THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: connection % is archived and cannot become a member', NEW.connection_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A member is a connection that is not archived.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """

#: The other half of the closed membership: at commit, the revision has exactly the members it declared. A deferred
#: constraint trigger on the revision's INSERT, as the AR v3 group's and the optimisation pass's are.
_MEMBERS_COMPLETE_FUNCTION = """
        CREATE FUNCTION am_require_executor_group_members() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            v_held bigint;
        BEGIN
            SELECT count(*) INTO v_held
              FROM executor_group_member m WHERE m.group_revision_id = NEW.group_revision_id;
            IF v_held <> NEW.member_count THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: group revision % declares % members and holds %',
                    NEW.group_revision_id, NEW.member_count, v_held
                    USING ERRCODE = 'AM001',
                          HINT = 'A group revision commits together with exactly the members it declares.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """

_RULE_FUNCTION = """
        CREATE FUNCTION am_check_executor_routing_rule() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no    integer;
            v_archived boolean;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('executor_routing_rule:' || NEW.work_kind, 0));
            -- FOR SHARE OF g: archiving takes the group row FOR UPDATE, so it and this insert serialise.
            SELECT (g.archived_at IS NOT NULL) INTO v_archived
              FROM executor_group_revision gr
              JOIN executor_group g ON g.group_id = gr.group_id
             WHERE gr.group_revision_id = NEW.group_revision_id
               FOR SHARE OF g;
            IF v_archived THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: group revision % belongs to an archived group and takes no rule',
                    NEW.group_revision_id
                    USING ERRCODE = 'AM001',
                          HINT = 'A rule names a group that is not archived.';
            END IF;
            SELECT max(rule_no) INTO last_no FROM executor_routing_rule_revision WHERE work_kind = NEW.work_kind;
            IF NEW.rule_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: work kind % has rule % and cannot take %',
                    NEW.work_kind, coalesce(last_no, 0), NEW.rule_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Rules are numbered 1, 2, 3, ... per work kind without a gap.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


#: The routing-mode journal is numbered 1, 2, 3, ... without a gap, under one advisory lock, as the rules are.
_MODE_EVENT_FUNCTION = """
        CREATE FUNCTION am_check_executor_routing_mode_event() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            last_no integer;
        BEGIN
            PERFORM pg_advisory_xact_lock(hashtextextended('executor_routing_mode_event', 0));
            SELECT max(event_no) INTO last_no FROM executor_routing_mode_event;
            IF NEW.event_no <> coalesce(last_no, 0) + 1 THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the routing mode journal has event % and cannot take %',
                    coalesce(last_no, 0), NEW.event_no
                    USING ERRCODE = 'AM001',
                          HINT = 'Events are numbered 1, 2, 3, ... without a gap.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """


def upgrade() -> None:
    # --- the group ------------------------------------------------------------------------------
    op.execute(
        f"""
        CREATE TABLE executor_group (
            group_id        text PRIMARY KEY,
            display_name    text NOT NULL,
            rotation_cursor bigint NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by      text NOT NULL,
            archived_at     timestamptz NULL,
            archived_by     text NULL,
            CONSTRAINT ck_executor_group_id_format
                CHECK (group_id ~ '^exg_{ULID}$'),
            CONSTRAINT ck_executor_group_display_name
                CHECK (char_length(display_name) BETWEEN 1 AND 120),
            CONSTRAINT ck_executor_group_rotation_cursor CHECK (rotation_cursor >= 0),
            CONSTRAINT ck_executor_group_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_group_archived_by_format
                CHECK (archived_by IS NULL OR archived_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_group_archive_pair
                CHECK ((archived_at IS NULL) = (archived_by IS NULL))
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_group_name_active ON executor_group (lower(display_name)) "
        "WHERE archived_at IS NULL"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_group_frozen_guard BEFORE UPDATE ON executor_group "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'group_id', 'display_name', 'created_at', 'created_by')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_group_write_once BEFORE UPDATE ON executor_group "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns('archived_at', 'archived_by')"
    )
    # Archive is not deletion: the row can change (the rotation cursor, the one-way archive) but is never removed.
    op.execute(
        "CREATE TRIGGER trg_executor_group_no_delete BEFORE DELETE ON executor_group "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    # --- the group revision ----------------------------------------------------------------------
    op.execute(_REVISION_CHAIN_FUNCTION)
    op.execute(
        f"""
        CREATE TABLE executor_group_revision (
            group_revision_id   text PRIMARY KEY,
            group_id            text NOT NULL REFERENCES executor_group (group_id),
            revision_no         integer NOT NULL,
            pin_id              text NOT NULL,
            gateway_model       text NOT NULL,
            billing             text NOT NULL,
            input_per_mtok_usd  numeric(12,6) NOT NULL,
            output_per_mtok_usd numeric(12,6) NOT NULL,
            strategy            text NOT NULL DEFAULT 'least_loaded',
            member_count        smallint NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by          text NOT NULL,
            CONSTRAINT uq_executor_group_revision_number UNIQUE (group_id, revision_no),
            CONSTRAINT ck_executor_group_revision_id_format
                CHECK (group_revision_id ~ '^exgr_{ULID}$'),
            CONSTRAINT ck_executor_group_revision_group_id_format
                CHECK (group_id ~ '^exg_{ULID}$'),
            CONSTRAINT ck_executor_group_revision_number CHECK (revision_no >= 1),
            CONSTRAINT ck_executor_group_revision_pin CHECK (char_length(pin_id) BETWEEN 1 AND 128),
            CONSTRAINT ck_executor_group_revision_gateway_model
                CHECK (char_length(gateway_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_group_revision_billing
                CHECK (billing IN ('metered', 'not_metered')),
            CONSTRAINT ck_executor_group_revision_input_rate CHECK (input_per_mtok_usd >= 0),
            CONSTRAINT ck_executor_group_revision_output_rate CHECK (output_per_mtok_usd >= 0),
            CONSTRAINT ck_executor_group_revision_strategy CHECK (strategy IN ('least_loaded')),
            CONSTRAINT ck_executor_group_revision_member_count CHECK (member_count BETWEEN 1 AND 16),
            CONSTRAINT ck_executor_group_revision_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_group_revision_immutable BEFORE UPDATE OR DELETE ON executor_group_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_group_revision_chain BEFORE INSERT ON executor_group_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_check_executor_group_revision()"
    )

    # --- the members of a revision ---------------------------------------------------------------
    op.execute(_MEMBER_FUNCTION)
    op.execute(
        f"""
        CREATE TABLE executor_group_member (
            group_revision_id      text NOT NULL,
            connection_id          text NOT NULL,
            connection_revision_id text NOT NULL,
            tie_break_order        integer NULL,
            CONSTRAINT pk_executor_group_member PRIMARY KEY (group_revision_id, connection_id),
            CONSTRAINT fk_executor_group_member_group_revision FOREIGN KEY (group_revision_id)
                REFERENCES executor_group_revision (group_revision_id),
            CONSTRAINT fk_executor_group_member_connection_revision
                FOREIGN KEY (connection_revision_id, connection_id)
                REFERENCES executor_connection_revision (revision_id, connection_id),
            CONSTRAINT uq_executor_group_member_order UNIQUE (group_revision_id, tie_break_order),
            CONSTRAINT ck_executor_group_member_group_revision_id_format
                CHECK (group_revision_id ~ '^exgr_{ULID}$'),
            CONSTRAINT ck_executor_group_member_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_group_member_connection_revision_id_format
                CHECK (connection_revision_id ~ '^excr_{ULID}$'),
            CONSTRAINT ck_executor_group_member_tie_break_order
                CHECK (tie_break_order IS NULL OR tie_break_order BETWEEN 1 AND 16)
        );
        """
    )
    op.execute("CREATE INDEX ix_executor_group_member_connection ON executor_group_member (connection_id)")
    op.execute(
        "CREATE TRIGGER trg_executor_group_member_immutable BEFORE UPDATE OR DELETE ON executor_group_member "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_group_member_homogeneous BEFORE INSERT ON executor_group_member "
        "FOR EACH ROW EXECUTE FUNCTION am_check_executor_group_member()"
    )
    # The revision commits together with exactly the members it declared (deferred to commit, so the members can be
    # inserted after the revision in the same transaction).
    op.execute(_MEMBERS_COMPLETE_FUNCTION)
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_executor_group_revision_has_members "
        "AFTER INSERT ON executor_group_revision DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION am_require_executor_group_members()"
    )

    # --- the routing rule of a work kind ----------------------------------------------------------
    op.execute(_RULE_FUNCTION)
    op.execute(
        f"""
        CREATE TABLE executor_routing_rule_revision (
            rule_revision_id  text PRIMARY KEY,
            work_kind         text NOT NULL,
            rule_no           integer NOT NULL,
            group_revision_id text NOT NULL REFERENCES executor_group_revision (group_revision_id),
            set_at            timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by            text NOT NULL,
            CONSTRAINT uq_executor_routing_rule_number UNIQUE (work_kind, rule_no),
            CONSTRAINT ck_executor_routing_rule_id_format
                CHECK (rule_revision_id ~ '^exrr_{ULID}$'),
            CONSTRAINT ck_executor_routing_rule_work_kind CHECK (work_kind IN ({_WORK_KINDS})),
            CONSTRAINT ck_executor_routing_rule_number CHECK (rule_no >= 1),
            CONSTRAINT ck_executor_routing_rule_group_revision_id_format
                CHECK (group_revision_id ~ '^exgr_{ULID}$'),
            CONSTRAINT ck_executor_routing_rule_set_by_format CHECK (set_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_executor_routing_rule_group_revision ON executor_routing_rule_revision (group_revision_id)"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_routing_rule_revision_append_only "
        "BEFORE UPDATE OR DELETE ON executor_routing_rule_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_routing_rule_revision_group BEFORE INSERT ON executor_routing_rule_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_check_executor_routing_rule()"
    )

    # --- the routing mode: an append-only journal, the latest event is the mode ------------------
    op.execute(
        f"""
        CREATE TABLE executor_routing_mode_event (
            mode_event_id  text PRIMARY KEY,
            event_no       integer NOT NULL,
            mode           text NOT NULL,
            preview_digest text NULL,
            mapping        jsonb NOT NULL DEFAULT '[]'::jsonb,
            changed_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
            changed_by     text NOT NULL,
            CONSTRAINT uq_executor_routing_mode_event_number UNIQUE (event_no),
            CONSTRAINT ck_executor_routing_mode_event_id_format
                CHECK (mode_event_id ~ '^exrm_{ULID}$'),
            CONSTRAINT ck_executor_routing_mode_event_number CHECK (event_no >= 1),
            CONSTRAINT ck_executor_routing_mode_event_mode CHECK (mode IN ('legacy', 'rules')),
            CONSTRAINT ck_executor_routing_mode_event_digest_format
                CHECK (preview_digest IS NULL OR preview_digest ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_executor_routing_mode_event_digest_shape
                CHECK ((mode = 'rules') = (preview_digest IS NOT NULL)),
            CONSTRAINT ck_executor_routing_mode_event_mapping_shape CHECK (
                CASE WHEN jsonb_typeof(mapping) = 'array'
                     THEN (mode = 'rules' AND jsonb_array_length(mapping) BETWEEN 1 AND 6)
                          OR (mode = 'legacy' AND jsonb_array_length(mapping) = 0)
                     ELSE false END),
            CONSTRAINT ck_executor_routing_mode_event_changed_by_format
                CHECK (changed_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_routing_mode_event_append_only "
        "BEFORE UPDATE OR DELETE ON executor_routing_mode_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(_MODE_EVENT_FUNCTION)
    op.execute(
        "CREATE TRIGGER trg_executor_routing_mode_event_number BEFORE INSERT ON executor_routing_mode_event "
        "FOR EACH ROW EXECUTE FUNCTION am_check_executor_routing_mode_event()"
    )

    comments = {
        "executor_group": (
            "ADR-0026 decision 10: a group of interchangeable executors. Configuration, kept by the product "
            "purge like the executor connections. Archive is one-way and is not deletion (a row cannot be deleted)."
        ),
        "executor_group_revision": (
            "ADR-0026 decision 10: an immutable revision of a group: pin, model, billing, the rate snapshot, "
            "the strategy and the number of members it is made with. Never updated or deleted (am_immutable_row)."
        ),
        "executor_group_member": (
            "ADR-0026 decision 10: the members of a group revision, each a connection and the connection "
            "revision snapshotted into the group. Immutable; homogeneity is checked on insert and the "
            "membership is closed when the revision is made (member_count)."
        ),
        "executor_routing_rule_revision": (
            "ADR-0026 decision 11: the routing rule of a work kind, append-only; the current rule is the "
            "highest rule_no of the work kind."
        ),
        "executor_routing_mode_event": (
            "ADR-0026 decision 17: the routing mode as an append-only journal, numbered without a gap; the "
            "latest event is the mode and an empty table means legacy."
        ),
    }
    for table, comment in comments.items():
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}';")


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in _NEW_TABLES:
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0047_executor_groups_rules with retained group, rule or routing-mode "
            f"data ({', '.join(retained)}); restore a database backup instead"
        )
    for table in reversed(_NEW_TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in _NEW_FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}()")
