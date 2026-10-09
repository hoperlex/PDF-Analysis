"""Durable W53 queue controls and re-audit lineage.

The migration backfills missing Jobs and expires pre-existing unreleased leases in
one Alembic transaction. A populated 0017 cannot be downgraded: restoring a backup
is required to avoid losing queue authority or re-audit provenance.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

from auditmanager.shared.identity import JobId

revision: str = "0017_execution_queue"
down_revision: str | None = "0016_release_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FROZEN_RUN_COLUMNS = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id'"
)


def _replace_run_frozen_guard(*, with_lineage: bool) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    columns = _FROZEN_RUN_COLUMNS if with_lineage else _FROZEN_RUN_COLUMNS.replace(
        ", 'reaudit_of_run_id'", ""
    )
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(" + columns + ")"
    )


def _replace_effect_guard(*, with_not_processed: bool) -> None:
    next_states = (
        "'response_received', 'outcome_unknown', 'not_processed'"
        if with_not_processed else "'response_received', 'outcome_unknown'"
    )
    mutable = (
        "'state', 'response_sha256', 'input_tokens', 'output_tokens', "
        "'latency_ms', 'error_code', 'final_model_call_id', 'updated_at'"
    )
    if with_not_processed:
        mutable += ", 'dispatch_class'"
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION am_guard_durable_effect_transition() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF OLD.state IS NOT DISTINCT FROM NEW.state THEN
                IF OLD IS DISTINCT FROM NEW THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: durable effect rows are immutable within a state'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_TABLE_NAME = 'provider_call_effect' AND (
                (OLD.state = 'prepared' AND NEW.state IN ({next_states}))
                OR (OLD.state = 'response_received' AND NEW.state = 'completed')
                OR (OLD.state IN ('prepared', 'response_received')
                    AND NEW.state = 'abandoned')
            ) THEN
                IF (to_jsonb(OLD) - ARRAY[{mutable}]) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY[{mutable}]) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: provider effect identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_TABLE_NAME = 'analysis_artifact_publication'
               AND OLD.state = 'prepared' AND NEW.state = 'bound' THEN
                IF (to_jsonb(OLD) - ARRAY['state', 'artifact_role', 'bound_at']) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY['state', 'artifact_role', 'bound_at']) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: artifact publication identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'state_transition_not_allowed: invalid durable effect transition'
                USING ERRCODE = 'AM001';
        END
        $fn$;
        """
    )


def upgrade() -> None:
    op.execute("ALTER TABLE job ADD COLUMN priority integer NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE job ADD COLUMN available_at timestamptz NOT NULL DEFAULT clock_timestamp()")
    op.execute("CREATE INDEX ix_job_dispatch ON job (state, priority DESC, available_at, created_at)")
    op.execute("ALTER TABLE lease ADD COLUMN expires_at timestamptz")
    op.execute("ALTER TABLE lease ADD COLUMN heartbeat_at timestamptz")
    op.execute("UPDATE lease SET expires_at = statement_timestamp(), heartbeat_at = acquired_at WHERE released_at IS NULL")
    # Stage-A's existing Job writer inserts only the three identity columns. Its
    # leases must remain insertable until Stage B supplies explicit deadlines.
    op.execute("ALTER TABLE lease ALTER COLUMN expires_at SET DEFAULT (statement_timestamp() + interval '60 seconds')")
    op.execute("ALTER TABLE lease ALTER COLUMN heartbeat_at SET DEFAULT statement_timestamp()")
    op.execute("ALTER TABLE lease ADD CONSTRAINT ck_lease_active_expiry CHECK (released_at IS NOT NULL OR expires_at IS NOT NULL)")
    op.execute(
        "CREATE TABLE execution_control (singleton boolean PRIMARY KEY DEFAULT true "
        "CHECK (singleton), paused boolean NOT NULL, "
        "changed_at timestamptz NOT NULL DEFAULT clock_timestamp())"
    )
    op.execute("ALTER TABLE audit_run ADD COLUMN reaudit_of_run_id text REFERENCES audit_run(run_id)")
    op.execute("ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_reaudit_distinct CHECK (reaudit_of_run_id IS NULL OR reaudit_of_run_id <> run_id)")
    op.execute("ALTER TABLE audit_run ADD CONSTRAINT ck_audit_run_reaudit_id_format CHECK (reaudit_of_run_id IS NULL OR reaudit_of_run_id ~ '^run_[0-9A-HJKMNP-TV-Z]{26}$')")
    op.execute("CREATE INDEX ix_audit_run_reaudit_of ON audit_run (reaudit_of_run_id) WHERE reaudit_of_run_id IS NOT NULL")
    _replace_run_frozen_guard(with_lineage=True)

    op.execute("ALTER TABLE provider_call_effect ADD COLUMN dispatch_class text")
    op.execute(
        "ALTER TABLE provider_call_effect ADD CONSTRAINT ck_provider_effect_dispatch_class "
        "CHECK (dispatch_class IS NULL OR dispatch_class IN "
        "('not_sent', 'rate_limited', 'proxy_unavailable', 'definite_refusal', 'outcome_unknown'))"
    )
    op.execute("ALTER TABLE provider_call_effect DROP CONSTRAINT ck_provider_effect_state")
    op.execute(
        "ALTER TABLE provider_call_effect ADD CONSTRAINT ck_provider_effect_state CHECK "
        "(state IN ('prepared', 'response_received', 'completed', 'outcome_unknown', "
        "'not_processed', 'abandoned'))"
    )
    op.execute("ALTER TABLE provider_call_effect DROP CONSTRAINT ck_provider_effect_outcome_shape")
    op.execute(
        """ALTER TABLE provider_call_effect ADD CONSTRAINT ck_provider_effect_outcome_shape CHECK (
            (state = 'prepared' AND response_sha256 IS NULL AND input_tokens IS NULL
                AND output_tokens IS NULL AND latency_ms IS NULL AND error_code IS NULL)
            OR (state IN ('response_received', 'completed') AND response_sha256 IS NOT NULL
                AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL
                AND latency_ms IS NOT NULL AND error_code IS NULL)
            OR (state IN ('outcome_unknown', 'not_processed') AND response_sha256 IS NULL
                AND input_tokens IS NULL AND output_tokens IS NULL AND latency_ms IS NULL
                AND error_code IS NOT NULL)
            OR (state = 'abandoned' AND error_code IS NOT NULL AND (
                (response_sha256 IS NULL AND input_tokens IS NULL AND output_tokens IS NULL
                    AND latency_ms IS NULL)
                OR (response_sha256 IS NOT NULL AND input_tokens IS NOT NULL
                    AND output_tokens IS NOT NULL AND latency_ms IS NOT NULL)
            ))
        )"""
    )
    _replace_effect_guard(with_not_processed=True)
    op.execute("CREATE INDEX ix_audit_event_run_journal ON audit_event (aggregate_id, occurred_at DESC, sequence_no DESC) WHERE aggregate_type IN ('AuditRun', 'Job', 'Attempt')")

    # Existing queued runs may predate W48's Job-at-acceptance rule. Each gets a
    # newly minted independent Job identity, inside this migration's transaction.
    bind = op.get_bind()
    run_ids = bind.execute(text(
        "SELECT r.run_id FROM audit_run r LEFT JOIN job j ON j.run_id = r.run_id "
        "WHERE r.state = 'queued' AND j.job_id IS NULL ORDER BY r.created_at, r.run_id"
    )).scalars().all()
    for run_id in run_ids:
        bind.execute(text(
            "INSERT INTO job (job_id, run_id, state) VALUES (:job_id, :run_id, 'queued')"
        ), {"job_id": str(JobId.new()), "run_id": run_id})


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("audit_run", "job", "attempt", "lease", "provider_call_effect", "execution_control"):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            raise RuntimeError(
                "refusing to downgrade 0017_execution_queue with retained execution data; "
                "restore a database backup instead"
            )
    op.execute("DROP INDEX ix_audit_event_run_journal")
    _replace_effect_guard(with_not_processed=False)
    op.execute("ALTER TABLE provider_call_effect DROP CONSTRAINT ck_provider_effect_outcome_shape")
    op.execute(
        """ALTER TABLE provider_call_effect ADD CONSTRAINT ck_provider_effect_outcome_shape CHECK (
            (state = 'prepared' AND response_sha256 IS NULL AND input_tokens IS NULL
                AND output_tokens IS NULL AND latency_ms IS NULL AND error_code IS NULL)
            OR (state IN ('response_received', 'completed') AND response_sha256 IS NOT NULL
                AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL
                AND latency_ms IS NOT NULL AND error_code IS NULL)
            OR (state = 'outcome_unknown' AND response_sha256 IS NULL
                AND input_tokens IS NULL AND output_tokens IS NULL AND latency_ms IS NULL
                AND error_code IS NOT NULL)
            OR (state = 'abandoned' AND error_code IS NOT NULL AND (
                (response_sha256 IS NULL AND input_tokens IS NULL AND output_tokens IS NULL
                    AND latency_ms IS NULL)
                OR (response_sha256 IS NOT NULL AND input_tokens IS NOT NULL
                    AND output_tokens IS NOT NULL AND latency_ms IS NOT NULL)
            ))
        )"""
    )
    op.execute("ALTER TABLE provider_call_effect DROP CONSTRAINT ck_provider_effect_state")
    op.execute("ALTER TABLE provider_call_effect ADD CONSTRAINT ck_provider_effect_state CHECK (state IN ('prepared', 'response_received', 'completed', 'outcome_unknown', 'abandoned'))")
    op.execute("ALTER TABLE provider_call_effect DROP CONSTRAINT ck_provider_effect_dispatch_class")
    op.execute("ALTER TABLE provider_call_effect DROP COLUMN dispatch_class")
    _replace_run_frozen_guard(with_lineage=False)
    op.execute("DROP INDEX ix_audit_run_reaudit_of")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_reaudit_distinct")
    op.execute("ALTER TABLE audit_run DROP CONSTRAINT ck_audit_run_reaudit_id_format")
    op.execute("ALTER TABLE audit_run DROP COLUMN reaudit_of_run_id")
    op.execute("DROP TABLE execution_control")
    op.execute("ALTER TABLE lease DROP CONSTRAINT ck_lease_active_expiry")
    op.execute("ALTER TABLE lease DROP COLUMN heartbeat_at")
    op.execute("ALTER TABLE lease DROP COLUMN expires_at")
    op.execute("DROP INDEX ix_job_dispatch")
    op.execute("ALTER TABLE job DROP COLUMN available_at")
    op.execute("ALTER TABLE job DROP COLUMN priority")
