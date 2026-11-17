"""0071 -- a run restarted from a stage chip: ``audit_run.restart_point`` and the link of the tombstone to the run that replaced it
(`RUN-RESTART-01`, owner rulings `R-155a`..`R-155i`; contract 1.59.0).

Revision ID: 0071_run_restart
Revises: 0070_document_group

«Перезапустить с этапа» (``restartRun``) is a **new run** that replaces a ``partial``, ``failed`` or ``cancelled`` source: everything before the
chosen stage chip is taken from the source chain, the chip and the later ones are computed, and when the new run publishes the source is
tombstoned with the ``deleteRun`` row of ``0066`` (`R-155a`, `R-155g`). The earlier run is never reopened (PD-03).

What this revision adds
-----------------------
``audit_run.restart_point`` -- one of the eight stage chips of the run screen (``preparation``, ``text``, ``blocks``, ``cross_check``, ``merge``,
``norms``, ``review``, ``correction``), written once at INSERT and ``NULL`` for every run that was not made by a restart. It is a column of its
own and **not** a widening of ``start_stage_id`` (``0060``): that column names a PC-01 *stage id* -- three values the executor, the cost
estimate and ``startRunFromStage`` read as such -- and a chip is a reader's grouping of the stage ids and of the extended review's procedures
(``cross_check`` is no stage id at all, and «Подготовка» covers three of them). One column holding two vocabularies would make every reader of
``start_stage_id`` choose between them; two columns that exclude each other make the choice a fact of the row.

The source of a restart is the existing ``started_from_run_id`` (the run whose stage outputs the new run takes, ``0060``). So the pair rule
``ck_audit_run_started_from_pair`` is redefined, same name: a source is named **exactly when** the run has a start stage *or* a restart point,
never both, and still never together with ``reaudit_of_run_id``. Every row written before this revision (a start stage with no restart point,
or neither) satisfies it unchanged. «Подготовка» takes nothing from the source but its settings and its link: it is a full rerun with the
source's settings, and it still names the source.

A restart row must say who made it and by which command: ``ck_audit_run_restart_has_starter_and_command`` (the tombstone's ``deleted_by_user_uid``
is NOT NULL, and the command is the link below).

Two partial unique indexes make the two rules of the command a fact of the database:

* ``ux_audit_run_active_restart`` -- **one active restart per source**: a second restart of the same source while the first has not ended is
  refused (``23505``; the command answers ``conflict``). It is released by any terminal state of the first, so «Остановить» (``cancelRun``) and a
  new restart follow each other;
* ``ux_audit_run_restart_command`` -- a restart command makes **one** run, so the command is a key to it.

The link of the source to the run that replaced it
--------------------------------------------------
No column is added to the frozen ``audit_run`` for it. The tombstone of ``0066`` already carries ``command_id`` (NOT NULL, UNIQUE, a foreign
key to ``command_record``) and ``audit_run`` carries the ``command_id`` of the command that created it. A restart's command record is the
**command of the new run**, and the tombstone of the source, written in the terminal transaction of that run, names the **same command**:

    new run :  audit_run.command_id            = <the restart command>, started_from_run_id = <source>, restart_point <> NULL
    source  :  audit_run_deletion.run_id = <source>, audit_run_deletion.command_id = <the restart command>

So «the run that replaced a tombstoned source» is the run whose ``command_id`` equals the tombstone's (``ux_audit_run_restart_command`` makes it
one run). Before that moment there is no tombstone and the source is listed as it was: the only forward pointer is the new run's own
``started_from_run_id``. A plain ``deleteRun`` tombstone names the ``delete_audit_run`` command, which no run was created by, so it replaces
nothing. ``restart_point`` joins ``trg_audit_run_frozen_guard``'s list, and the ``command_id`` of a **restart** row is frozen by a trigger of its
own (``trg_audit_run_restart_command_frozen``: the generic ``am_guard_frozen_columns`` under a ``WHEN`` of the row's restart point), so the link
cannot be moved after the fact. The column is not added to the general list on purpose: the recovery drills rewrite the receipts of ordinary runs,
and nothing about a run that is no restart depends on its command.

``trg_audit_run_deletion_by_restart`` makes the rule of ``R-155g`` a fact of the database too: a tombstone that names a restart's command is
refused unless that run is ``published`` **or** ``partial`` **and** names the tombstoned run as its source -- the tombstone is written in the
transaction that publishes the new run, after its state moved, and never before, never for another run, never by a restart that ``failed`` or was
``cancelled``. ``partial`` is admitted because the owner ruled the source is deleted «при публикации нового» (``R-155g``) and a ``partial`` run
has published findings too (the gate publishes the grounded ones; only a procedure of the extended review fell short): a restart that ends
``partial`` replaces its source, as one that ends ``published`` does. A tombstone of any other command (``deleteRun``) is unaffected.

What it does not change
-----------------------
The carried decisions of a restart need no schema change: ``expert_decision_event.carried_from_decision_id`` (``0058``) names the source decision
by identity and its four constraints (the shape, not-self, the verdict arm, the foreign key) say nothing about versions -- that the source finding
belongs to an *earlier* version is a rule of the command (``decisions.carryover``), not of the database -- so a carry between two findings of the
same version, made by a restart, is admitted as it stands. A comment is carried as a comment event with provenance text and no link (the verdict arm
of ``0058`` only admits ``accept``/``reject`` to carry one).

Downgrade
---------
Refuses while any run carries a restart point: dropping the column would turn «restarted from chip X of run Y» into «computed from scratch», and a
tombstone written by a restart into a plain deletion -- false statements about what produced the run's findings (AGENTS section 4, no silent
fallback; the pattern of ``0060``). With none, it restores the pair rule, the frozen list of ``0064``, and drops the column, the indexes, the
triggers and the function.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0071_run_restart"
down_revision: str | None = "0070_document_group"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: ``audit_run``'s frozen list as ``0064`` left it, restated: a migration never imports another.
_FROZEN_RUN_0064 = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id', 'executor_group_revision_id', 'routing_rule_revision_id', "
    "'started_by_user_uid', 'started_from_run_id', 'start_stage_id', 'stage_plan', 'publication_mode'"
)
_FROZEN_RUN_0071 = _FROZEN_RUN_0064 + ", 'restart_point'"

_POINTS = ("preparation", "text", "blocks", "cross_check", "merge", "norms", "review", "correction")
_POINT_LIST = ", ".join(f"'{point}'" for point in _POINTS)

_PAIR_0060 = (
    "(started_from_run_id IS NULL) = (start_stage_id IS NULL) "
    "AND (started_from_run_id IS NULL OR reaudit_of_run_id IS NULL)"
)
_PAIR_0071 = (
    "(started_from_run_id IS NULL) = (start_stage_id IS NULL AND restart_point IS NULL) "
    "AND (start_stage_id IS NULL OR restart_point IS NULL) "
    "AND (started_from_run_id IS NULL OR reaudit_of_run_id IS NULL)"
)

_ACTIVE_RESTART = "ux_audit_run_active_restart"
_RESTART_COMMAND = "ux_audit_run_restart_command"
_COMMAND_TRIGGER = "trg_audit_run_restart_command_frozen"
_DELETION_TRIGGER = "trg_audit_run_deletion_by_restart"
_DELETION_FUNCTION = "am_guard_run_deletion_by_restart"

_DELETION_BY_RESTART = f"""
    CREATE FUNCTION {_DELETION_FUNCTION}() RETURNS trigger
    LANGUAGE plpgsql AS $fn$
    DECLARE
        v_run   text;
        v_state text;
        v_from  text;
    BEGIN
        SELECT r.run_id, r.state, r.started_from_run_id INTO v_run, v_state, v_from
          FROM audit_run r
         WHERE r.command_id = NEW.command_id AND r.restart_point IS NOT NULL;
        IF NOT FOUND THEN
            RETURN NEW;  -- an ordinary deleteRun: the command made no run
        END IF;
        IF v_from IS DISTINCT FROM NEW.run_id THEN
            RAISE EXCEPTION
                'state_transition_not_allowed: the command of restart run % replaces run %, not run %',
                v_run, v_from, NEW.run_id
                USING ERRCODE = 'AM001',
                      HINT = 'A restart tombstones its own source and no other run.';
        END IF;
        IF v_state NOT IN ('published', 'partial') THEN
            RAISE EXCEPTION
                'state_transition_not_allowed: restart run % is % and has not published, so it does not replace run %',
                v_run, v_state, NEW.run_id
                USING ERRCODE = 'AM001',
                      HINT = 'The source is tombstoned in the transaction that publishes the new run (R-155g: published or partial), after its state moved.';
        END IF;
        RETURN NEW;
    END
    $fn$
"""


def _frozen_run_guard(columns: str) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_audit_run_frozen({columns})"
    )


def upgrade() -> None:
    op.execute("ALTER TABLE audit_run ADD COLUMN restart_point text NULL")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_restart_point "
        f"CHECK (restart_point IS NULL OR restart_point IN ({_POINT_LIST}))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_restart_has_starter_and_command "
        "CHECK (restart_point IS NULL OR (started_by_user_uid IS NOT NULL AND command_id IS NOT NULL))"
    )
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_from_pair")
    op.execute(f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_from_pair CHECK ({_PAIR_0071})")
    op.execute(
        f"CREATE UNIQUE INDEX {_ACTIVE_RESTART} ON audit_run (started_from_run_id) "
        "WHERE restart_point IS NOT NULL AND state IN ('created', 'queued', 'running', 'validating')"
    )
    op.execute(f"CREATE UNIQUE INDEX {_RESTART_COMMAND} ON audit_run (command_id) WHERE restart_point IS NOT NULL")
    op.execute(
        "COMMENT ON COLUMN audit_run.restart_point IS "
        "'The stage chip a restarted run was started from (RUN-RESTART-01, R-155a): preparation, text, blocks, cross_check, merge, norms, "
        "review or correction; NULL for a run that is not a restart. The source is started_from_run_id; start_stage_id stays NULL.'"
    )
    op.execute(_DELETION_BY_RESTART)
    op.execute(
        f"CREATE TRIGGER {_DELETION_TRIGGER} BEFORE INSERT ON audit_run_deletion "
        f"FOR EACH ROW EXECUTE FUNCTION {_DELETION_FUNCTION}()"
    )
    op.execute(
        f"CREATE TRIGGER {_COMMAND_TRIGGER} BEFORE UPDATE ON audit_run FOR EACH ROW WHEN (OLD.restart_point IS NOT NULL) "
        "EXECUTE FUNCTION am_guard_frozen_columns('command_id')"
    )
    _frozen_run_guard(_FROZEN_RUN_0071)


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM audit_run WHERE restart_point IS NOT NULL) THEN
                RAISE EXCEPTION
                    'runs were restarted from a stage chip of an earlier run (restart_point), and the source of each is tombstoned by '
                    'the restart command; decide what to do with that history before downgrading 0071';
            END IF;
        END
        $$;
        """
    )
    _frozen_run_guard(_FROZEN_RUN_0064)
    op.execute(f"DROP TRIGGER {_COMMAND_TRIGGER} ON audit_run")
    op.execute(f"DROP TRIGGER {_DELETION_TRIGGER} ON audit_run_deletion")
    op.execute(f"DROP FUNCTION {_DELETION_FUNCTION}()")
    op.execute(f"DROP INDEX {_RESTART_COMMAND}")
    op.execute(f"DROP INDEX {_ACTIVE_RESTART}")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_from_pair")
    op.execute(f"ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_from_pair CHECK ({_PAIR_0060})")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_restart_has_starter_and_command")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_restart_point")
    op.execute("ALTER TABLE audit_run DROP COLUMN restart_point")
