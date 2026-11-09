"""0060 -- a run started from a stage of an earlier run (`UI-A-60`, ruling `R-151i`, debt `D-301`).

«Запустить с этапа» is a **new run** that reuses the completed stage outputs of an earlier terminal run before the chosen
stage and computes the rest (`docs/program/RUN-FROM-STAGE-01.md`). The earlier run is immutable history and is never
touched. ``audit_run`` therefore gains two columns, written once at INSERT:

* ``started_from_run_id`` -- the run whose outputs are reused, by its opaque identity (never a number or a position).
  It is **not** ``reaudit_of_run_id``: a re-audit recomputes everything, and the two lineages answer different questions
  («повтор» against «продолжение»), so one column must never stand in for the other.
* ``start_stage_id`` -- the first stage the new run computes; every PC-01 stage before it is reused.

Both are NULL for every run written before this migration and for every run started from a version or as a re-audit.
Five constraints keep the pair honest:

* ``fk_audit_run_started_from`` -- the named run exists and can never be deleted from under the run that reuses it (the
  project erase tool, which deletes a whole project's runs in one scope, is the deliberate exception, as for
  ``reaudit_of_run_id``);
* ``ck_audit_run_started_from_run_id_format`` -- the usual ``run_<ULID>`` shape;
* ``ck_audit_run_started_from_not_self`` -- a run is not its own source;
* ``ck_audit_run_start_stage_id`` -- one of the stages after the first that PC-01 schedules (a start at the first stage
  reuses nothing and is a re-audit; a stage PC-01 does not schedule has nothing to start);
* ``ck_audit_run_started_from_pair`` -- both or neither, and not together with ``reaudit_of_run_id``.

The pair joins ``trg_audit_run_frozen_guard``'s column list (the function ``am_guard_audit_run_frozen`` of ``0048`` is
unchanged): what a run reuses is a fact of its creation and is never rewritten. A partial index serves the one question
asked of it, «is a run from this source and stage already in progress».

Downgrade refuses while any run carries the pair: dropping the columns would turn «continued from run X at stage S» into
«computed from scratch», a false statement about what produced the run's findings (AGENTS section 4, no silent fallback).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0060_run_from_stage"
down_revision: str | None = "0059_decision_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: ``0051``'s list, restated: a migration never imports another.
_FROZEN_0051 = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id', "
    "'connection_revision_id', 'preset_revision_id', 'executor_group_revision_id', 'routing_rule_revision_id', "
    "'started_by_user_uid'"
)
_FROZEN_0060 = _FROZEN_0051 + ", 'started_from_run_id', 'start_stage_id'"

_INDEX = "ix_audit_run_started_from"


def _frozen_run_guard(columns: str) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_audit_run_frozen({columns})"
    )


def upgrade() -> None:
    op.execute("ALTER TABLE audit_run ADD COLUMN started_from_run_id text NULL")
    op.execute("ALTER TABLE audit_run ADD COLUMN start_stage_id text NULL")
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT fk_audit_run_started_from "
        "FOREIGN KEY (started_from_run_id) REFERENCES audit_run (run_id) ON DELETE RESTRICT"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_from_run_id_format "
        f"CHECK (started_from_run_id IS NULL OR started_from_run_id ~ '^run_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_from_not_self "
        "CHECK (started_from_run_id IS NULL OR started_from_run_id <> run_id)"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_start_stage_id "
        "CHECK (start_stage_id IS NULL OR start_stage_id IN "
        "('page_geometry_extraction', 'document_context_build', 'text_analysis'))"
    )
    op.execute(
        "ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_started_from_pair "
        "CHECK ((started_from_run_id IS NULL) = (start_stage_id IS NULL) "
        "AND (started_from_run_id IS NULL OR reaudit_of_run_id IS NULL))"
    )
    op.execute(
        f"CREATE INDEX {_INDEX} ON audit_run (started_from_run_id, start_stage_id) "
        "WHERE started_from_run_id IS NOT NULL"
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.started_from_run_id IS "
        "'The terminal run whose completed stage outputs this run reuses (R-151i, UI-A-60); NULL for a run started from a "
        "version or as a re-audit.'"
    )
    op.execute(
        "COMMENT ON COLUMN audit_run.start_stage_id IS "
        "'The first stage this run computes; every PC-01 stage before it is reused from started_from_run_id (R-151i).'"
    )
    _frozen_run_guard(_FROZEN_0060)


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM audit_run WHERE started_from_run_id IS NOT NULL) THEN
                RAISE EXCEPTION
                    'runs were started from a stage of an earlier run (started_from_run_id); decide what to do with '
                    'that history before downgrading 0060';
            END IF;
        END
        $$;
        """
    )
    _frozen_run_guard(_FROZEN_0051)
    op.execute(f"DROP INDEX {_INDEX}")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_from_pair")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_start_stage_id")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_from_not_self")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_started_from_run_id_format")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT fk_audit_run_started_from")
    op.execute("ALTER TABLE audit_run DROP COLUMN start_stage_id")
    op.execute("ALTER TABLE audit_run DROP COLUMN started_from_run_id")
