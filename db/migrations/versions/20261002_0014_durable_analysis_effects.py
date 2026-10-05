"""Instantiate durable execution authority and external-effect journals.

Revision ID: 0014_durable_analysis_effects
Revises: 0013_norm_embeddings

The domain and analysis contracts already define Job, Attempt, Lease and the opaque
``execution_token``.  This migration does not widen those contracts; it makes their
publication-authority rule executable for the local alpha runner and gives both kinds
of external effect a database breadcrumb before they happen.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0014_durable_analysis_effects"
down_revision: str | None = "0013_norm_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"
ERROR_CODES: tuple[str, ...] = (
    "validation_failed",
    "not_found",
    "authentication_required",
    "permission_denied",
    "conflict",
    "state_transition_not_allowed",
    "idempotency_key_reuse",
    "idempotency_key_in_progress",
    "idempotency_key_stale",
    "unsupported_contract_version",
    "storage_integrity_error",
    "dependency_unavailable",
    "dependency_credential_refused",
    "staged_upload_lost",
    "required_norm_unavailable",
    "analysis_input_invalid",
    "analysis_failed",
    "partial_result_not_publishable",
    "cost_budget_exceeded",
    "stale_attempt",
    "execution_token_invalid",
    "internal_error",
)
ERROR_CODES_SQL = ", ".join(f"'{code}'" for code in ERROR_CODES)


def _id_check(column: str, prefix: str) -> str:
    return f"{column} ~ '^{prefix}_{ULID_BODY}$'"


JOB_TOPOLOGY: tuple[tuple[str | None, str], ...] = (
    (None, "queued"),
    ("queued", "leased"),
    ("queued", "cancelled"),
    ("leased", "running"),
    ("leased", "queued"),
    ("leased", "failed"),
    ("leased", "cancelled"),
    ("running", "succeeded"),
    ("running", "retry_wait"),
    ("running", "failed"),
    ("running", "cancelled"),
    ("retry_wait", "queued"),
    ("retry_wait", "dead_letter"),
    ("retry_wait", "cancelled"),
)

ATTEMPT_TOPOLOGY: tuple[tuple[str | None, str], ...] = (
    (None, "created"),
    ("created", "leased"),
    ("created", "cancelled"),
    ("leased", "running"),
    ("leased", "superseded"),
    ("leased", "lost"),
    ("leased", "failed"),
    ("leased", "cancelled"),
    ("running", "succeeded"),
    ("running", "failed"),
    ("running", "superseded"),
    ("running", "lost"),
    ("running", "cancelled"),
)


def upgrade() -> None:
    _extend_state_topology()
    _create_execution_authority()
    _create_effect_journals()
    _attach_guards()


def _extend_state_topology() -> None:
    # The topology table is immutable to application SQL. A migration is its one owner,
    # so it temporarily removes the guard, widens the closed machine vocabulary, appends
    # the already-contracted edges, and restores the guard before returning.
    op.execute("DROP TRIGGER trg_contract_state_transition_immutable ON contract_state_transition;")
    op.execute(
        "ALTER TABLE contract_state_transition "
        "DROP CONSTRAINT ck_contract_state_transition_machine;"
    )
    op.execute(
        "ALTER TABLE contract_state_transition ADD CONSTRAINT "
        "ck_contract_state_transition_machine "
        "CHECK (machine IN ('audit_run', 'blob', 'command_idempotency', 'job', 'attempt'));"
    )
    values = []
    for machine, topology in (("job", JOB_TOPOLOGY), ("attempt", ATTEMPT_TOPOLOGY)):
        values.extend(
            "('{machine}', {origin}, '{target}')".format(
                machine=machine,
                origin="NULL" if origin is None else f"'{origin}'",
                target=target,
            )
            for origin, target in topology
        )
    op.execute(
        "INSERT INTO contract_state_transition (machine, from_state, to_state) VALUES "
        + ", ".join(values)
        + ";"
    )
    op.execute(
        """
        CREATE TRIGGER trg_contract_state_transition_immutable
            BEFORE INSERT OR UPDATE OR DELETE ON contract_state_transition
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )


def _create_execution_authority() -> None:
    op.execute(
        f"""
        CREATE TABLE job (
            job_id             text PRIMARY KEY,
            run_id             text NOT NULL REFERENCES audit_run (run_id),
            state              text NOT NULL DEFAULT 'queued',
            current_attempt_id text NULL,
            created_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at        timestamptz NULL,
            CONSTRAINT ck_job_job_id_format CHECK ({_id_check('job_id', 'job')}),
            CONSTRAINT ck_job_run_id_format CHECK ({_id_check('run_id', 'run')}),
            CONSTRAINT ck_job_current_attempt_id_format CHECK (
                current_attempt_id IS NULL OR {_id_check('current_attempt_id', 'att')}
            ),
            CONSTRAINT ck_job_state CHECK (
                state IN ('queued', 'leased', 'running', 'succeeded', 'retry_wait',
                          'failed', 'cancelled', 'dead_letter')
            ),
            CONSTRAINT ck_job_terminal_at CHECK (
                (state IN ('succeeded', 'failed', 'cancelled', 'dead_letter'))
                = (terminal_at IS NOT NULL)
            ),
            CONSTRAINT uq_job_run_id UNIQUE (run_id),
            CONSTRAINT uq_job_run_job UNIQUE (run_id, job_id),
            CONSTRAINT uq_job_current_attempt UNIQUE (current_attempt_id)
        );
        """
    )
    op.execute(
        f"""
        CREATE TABLE attempt (
            attempt_id      text PRIMARY KEY,
            job_id          text NOT NULL REFERENCES job (job_id),
            state           text NOT NULL DEFAULT 'created',
            execution_token text NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            terminal_at     timestamptz NULL,
            CONSTRAINT ck_attempt_attempt_id_format
                CHECK ({_id_check('attempt_id', 'att')}),
            CONSTRAINT ck_attempt_job_id_format CHECK ({_id_check('job_id', 'job')}),
            CONSTRAINT ck_attempt_execution_token CHECK (
                char_length(execution_token) BETWEEN 1 AND 256
                AND execution_token ~ '^[A-Za-z0-9._~-]+$'
            ),
            CONSTRAINT ck_attempt_state CHECK (
                state IN ('created', 'leased', 'running', 'succeeded', 'failed',
                          'superseded', 'lost', 'cancelled')
            ),
            CONSTRAINT ck_attempt_terminal_at CHECK (
                (state IN ('succeeded', 'failed', 'superseded', 'lost', 'cancelled'))
                = (terminal_at IS NOT NULL)
            ),
            CONSTRAINT uq_attempt_execution_token UNIQUE (execution_token),
            CONSTRAINT uq_attempt_job_attempt UNIQUE (job_id, attempt_id)
        );
        """
    )
    op.execute(
        "ALTER TABLE job ADD CONSTRAINT fk_job_current_attempt "
        "FOREIGN KEY (current_attempt_id) REFERENCES attempt (attempt_id);"
    )
    op.execute(
        "ALTER TABLE job ADD CONSTRAINT fk_job_current_attempt_belongs_to_job "
        "FOREIGN KEY (job_id, current_attempt_id) "
        "REFERENCES attempt (job_id, attempt_id);"
    )
    op.execute("CREATE INDEX ix_attempt_job_id ON attempt (job_id);")

    op.execute(
        f"""
        CREATE TABLE lease (
            lease_id    text PRIMARY KEY,
            job_id      text NOT NULL REFERENCES job (job_id),
            attempt_id  text NOT NULL REFERENCES attempt (attempt_id),
            acquired_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            released_at timestamptz NULL,
            CONSTRAINT ck_lease_lease_id_format CHECK ({_id_check('lease_id', 'lse')}),
            CONSTRAINT ck_lease_job_id_format CHECK ({_id_check('job_id', 'job')}),
            CONSTRAINT ck_lease_attempt_id_format CHECK ({_id_check('attempt_id', 'att')}),
            CONSTRAINT uq_lease_attempt_id UNIQUE (attempt_id),
            CONSTRAINT fk_lease_attempt_belongs_to_job FOREIGN KEY (job_id, attempt_id)
                REFERENCES attempt (job_id, attempt_id)
        );
        """
    )
    op.execute("CREATE INDEX ix_lease_job_id ON lease (job_id);")
    op.execute(
        "COMMENT ON COLUMN attempt.execution_token IS "
        "'Secret-class opaque equality-only capability. It is never logged, returned "
        "through the API, parsed, ordered or used as entity identity.';"
    )


def _create_effect_journals() -> None:
    op.execute(
        "ALTER TABLE model_call ADD CONSTRAINT uq_model_call_run_call "
        "UNIQUE (run_id, model_call_id);"
    )
    op.execute(
        f"""
        CREATE TABLE provider_call_effect (
            model_call_id       text PRIMARY KEY,
            run_id              text NOT NULL REFERENCES audit_run (run_id),
            job_id              text NOT NULL REFERENCES job (job_id),
            attempt_id          text NOT NULL REFERENCES attempt (attempt_id),
            stage_id            text NOT NULL,
            provider            text NOT NULL,
            model_identity      text NOT NULL,
            provider_mode       text NOT NULL,
            parameters          jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            request_sha256      text NOT NULL,
            state               text NOT NULL DEFAULT 'prepared',
            response_sha256     text NULL,
            input_tokens        integer NULL,
            output_tokens       integer NULL,
            latency_ms          integer NULL,
            error_code          text NULL,
            final_model_call_id text NULL,
            prepared_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
            updated_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_provider_effect_model_call_id_format
                CHECK ({_id_check('model_call_id', 'mc')}),
            CONSTRAINT ck_provider_effect_run_id_format CHECK ({_id_check('run_id', 'run')}),
            CONSTRAINT ck_provider_effect_job_id_format CHECK ({_id_check('job_id', 'job')}),
            CONSTRAINT ck_provider_effect_attempt_id_format
                CHECK ({_id_check('attempt_id', 'att')}),
            CONSTRAINT ck_provider_effect_final_model_call_id_format CHECK (
                final_model_call_id IS NULL OR {_id_check('final_model_call_id', 'mc')}
            ),
            CONSTRAINT ck_provider_effect_stage_id CHECK (stage_id = 'text_analysis'),
            CONSTRAINT ck_provider_effect_mode CHECK (provider_mode IN ('live', 'recorded')),
            CONSTRAINT ck_provider_effect_request_sha256
                CHECK (request_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_provider_effect_response_sha256 CHECK (
                response_sha256 IS NULL OR response_sha256 ~ '^[0-9a-f]{{64}}$'
            ),
            CONSTRAINT ck_provider_effect_state CHECK (
                state IN (
                    'prepared', 'response_received', 'completed', 'outcome_unknown',
                    'abandoned'
                )
            ),
            CONSTRAINT ck_provider_effect_error_code CHECK (
                error_code IS NULL OR error_code IN ({ERROR_CODES_SQL})
            ),
            CONSTRAINT ck_provider_effect_tokens CHECK (
                (input_tokens IS NULL OR input_tokens >= 0)
                AND (output_tokens IS NULL OR output_tokens >= 0)
                AND (latency_ms IS NULL OR latency_ms >= 0)
            ),
            CONSTRAINT ck_provider_effect_response_shape CHECK (
                state NOT IN ('response_received', 'completed')
                OR (response_sha256 IS NOT NULL AND input_tokens IS NOT NULL
                    AND output_tokens IS NOT NULL AND latency_ms IS NOT NULL)
            ),
            CONSTRAINT ck_provider_effect_completion CHECK (
                (state = 'completed') = (final_model_call_id IS NOT NULL)
                AND (final_model_call_id IS NULL OR final_model_call_id = model_call_id)
            ),
            CONSTRAINT ck_provider_effect_outcome_shape CHECK (
                (state = 'prepared' AND response_sha256 IS NULL
                    AND input_tokens IS NULL AND output_tokens IS NULL
                    AND latency_ms IS NULL AND error_code IS NULL)
                OR (state IN ('response_received', 'completed')
                    AND response_sha256 IS NOT NULL AND input_tokens IS NOT NULL
                    AND output_tokens IS NOT NULL AND latency_ms IS NOT NULL
                    AND error_code IS NULL)
                OR (state = 'outcome_unknown' AND response_sha256 IS NULL
                    AND input_tokens IS NULL AND output_tokens IS NULL
                    AND latency_ms IS NULL AND error_code IS NOT NULL)
                OR (state = 'abandoned' AND error_code IS NOT NULL AND (
                    (response_sha256 IS NULL AND input_tokens IS NULL
                        AND output_tokens IS NULL AND latency_ms IS NULL)
                    OR (response_sha256 IS NOT NULL AND input_tokens IS NOT NULL
                        AND output_tokens IS NOT NULL AND latency_ms IS NOT NULL)
                ))
            ),
            CONSTRAINT fk_provider_effect_job_belongs_to_run FOREIGN KEY (run_id, job_id)
                REFERENCES job (run_id, job_id),
            CONSTRAINT fk_provider_effect_attempt_belongs_to_job
                FOREIGN KEY (job_id, attempt_id)
                REFERENCES attempt (job_id, attempt_id),
            CONSTRAINT fk_provider_effect_final_call_belongs_to_run
                FOREIGN KEY (run_id, final_model_call_id)
                REFERENCES model_call (run_id, model_call_id)
        );
        """
    )
    op.execute("CREATE INDEX ix_provider_call_effect_run_id ON provider_call_effect (run_id);")
    op.execute(
        "CREATE INDEX ix_provider_call_effect_unsettled "
        "ON provider_call_effect (state, prepared_at) "
        "WHERE state IN ('prepared', 'response_received');"
    )

    op.execute(
        f"""
        CREATE TABLE analysis_artifact_publication (
            run_id        text NOT NULL REFERENCES audit_run (run_id),
            job_id        text NOT NULL REFERENCES job (job_id),
            attempt_id    text NOT NULL REFERENCES attempt (attempt_id),
            stage_id      text NOT NULL,
            blob_id       text NOT NULL REFERENCES blob (blob_id),
            blob_role     text NOT NULL,
            upload_token  text NOT NULL DEFAULT gen_random_uuid()::text,
            artifact_role text NULL,
            state         text NOT NULL DEFAULT 'prepared',
            created_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
            bound_at      timestamptz NULL,
            CONSTRAINT pk_analysis_artifact_publication
                PRIMARY KEY (attempt_id, stage_id, blob_id, blob_role),
            CONSTRAINT ck_analysis_artifact_run_id_format CHECK ({_id_check('run_id', 'run')}),
            CONSTRAINT ck_analysis_artifact_job_id_format CHECK ({_id_check('job_id', 'job')}),
            CONSTRAINT ck_analysis_artifact_attempt_id_format
                CHECK ({_id_check('attempt_id', 'att')}),
            CONSTRAINT ck_analysis_artifact_stage_id
                CHECK (stage_id ~ '^[a-z][a-z0-9_]{{2,63}}$'),
            CONSTRAINT ck_analysis_artifact_blob_id_format CHECK ({_id_check('blob_id', 'blob')}),
            CONSTRAINT ck_analysis_artifact_blob_role
                CHECK (blob_role ~ '^[a-z][a-z0-9_]{{2,63}}$'),
            CONSTRAINT ck_analysis_artifact_upload_token
                CHECK (upload_token ~ '^[A-Za-z0-9._~-]{{1,128}}$'),
            CONSTRAINT ck_analysis_artifact_role CHECK (
                artifact_role IS NULL
                OR artifact_role ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$'
            ),
            CONSTRAINT ck_analysis_artifact_state CHECK (state IN ('prepared', 'bound')),
            CONSTRAINT ck_analysis_artifact_bound_shape CHECK (
                (state = 'bound') = (artifact_role IS NOT NULL AND bound_at IS NOT NULL)
            ),
            CONSTRAINT uq_analysis_artifact_upload_token UNIQUE (upload_token),
            CONSTRAINT fk_analysis_artifact_job_belongs_to_run FOREIGN KEY (run_id, job_id)
                REFERENCES job (run_id, job_id),
            CONSTRAINT fk_analysis_artifact_attempt_belongs_to_job
                FOREIGN KEY (job_id, attempt_id)
                REFERENCES attempt (job_id, attempt_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_analysis_artifact_publication_blob_id "
        "ON analysis_artifact_publication (blob_id);"
    )
    op.execute(
        "CREATE INDEX ix_analysis_artifact_publication_unbound "
        "ON analysis_artifact_publication (state, created_at) WHERE state = 'prepared';"
    )

    op.execute(
        """
        CREATE FUNCTION am_guard_durable_effect_transition() RETURNS trigger
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
                (OLD.state = 'prepared' AND NEW.state IN ('response_received', 'outcome_unknown'))
                OR (OLD.state = 'response_received' AND NEW.state = 'completed')
                OR (OLD.state IN ('prepared', 'response_received')
                    AND NEW.state = 'abandoned')
            ) THEN
                IF (to_jsonb(OLD) - ARRAY[
                        'state', 'response_sha256', 'input_tokens', 'output_tokens',
                        'latency_ms', 'error_code', 'final_model_call_id', 'updated_at'
                    ]) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY[
                        'state', 'response_sha256', 'input_tokens', 'output_tokens',
                        'latency_ms', 'error_code', 'final_model_call_id', 'updated_at'
                    ]) THEN
                    RAISE EXCEPTION 'state_transition_not_allowed: provider effect identity is immutable'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;
            IF TG_TABLE_NAME = 'analysis_artifact_publication'
               AND OLD.state = 'prepared' AND NEW.state = 'bound' THEN
                IF (to_jsonb(OLD) - ARRAY[
                        'state', 'artifact_role', 'bound_at'
                    ]) IS DISTINCT FROM
                   (to_jsonb(NEW) - ARRAY[
                        'state', 'artifact_role', 'bound_at'
                    ]) THEN
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


def _attach_guards() -> None:
    op.execute(
        """
        CREATE TRIGGER trg_job_state_guard
            BEFORE INSERT OR UPDATE ON job
            FOR EACH ROW EXECUTE FUNCTION am_guard_state_transition('job', 'state');
        CREATE TRIGGER trg_job_frozen_guard
            BEFORE UPDATE ON job
            FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(
                'job_id', 'run_id', 'created_at');
        CREATE TRIGGER trg_attempt_state_guard
            BEFORE INSERT OR UPDATE ON attempt
            FOR EACH ROW EXECUTE FUNCTION am_guard_state_transition('attempt', 'state');
        CREATE TRIGGER trg_attempt_frozen_guard
            BEFORE UPDATE ON attempt
            FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(
                'attempt_id', 'job_id', 'execution_token', 'created_at');
        CREATE TRIGGER trg_lease_frozen_guard
            BEFORE UPDATE ON lease
            FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(
                'lease_id', 'job_id', 'attempt_id', 'acquired_at');
        CREATE TRIGGER trg_provider_call_effect_state_guard
            BEFORE UPDATE ON provider_call_effect
            FOR EACH ROW EXECUTE FUNCTION am_guard_durable_effect_transition();
        CREATE TRIGGER trg_provider_call_effect_frozen_guard
            BEFORE UPDATE ON provider_call_effect
            FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(
                'model_call_id', 'run_id', 'job_id', 'attempt_id', 'stage_id',
                'provider', 'model_identity', 'provider_mode', 'parameters',
                'request_sha256', 'prepared_at');
        CREATE TRIGGER trg_analysis_artifact_state_guard
            BEFORE UPDATE ON analysis_artifact_publication
            FOR EACH ROW EXECUTE FUNCTION am_guard_durable_effect_transition();
        CREATE TRIGGER trg_analysis_artifact_frozen_guard
            BEFORE UPDATE ON analysis_artifact_publication
            FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns(
                'run_id', 'job_id', 'attempt_id', 'stage_id', 'blob_id',
                'blob_role', 'upload_token', 'created_at');
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    occupied = {
        table: int(bind.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
        for table in (
            "provider_call_effect",
            "analysis_artifact_publication",
            "lease",
            "attempt",
            "job",
        )
    }
    if any(occupied.values()):
        rendered = ", ".join(f"{name}={count}" for name, count in occupied.items())
        raise RuntimeError(
            "0014_durable_analysis_effects downgrade refused: durable execution evidence "
            f"would be discarded ({rendered}). Use a forward repair or a disposable database."
        )

    op.execute("DROP TABLE analysis_artifact_publication;")
    op.execute("DROP TABLE provider_call_effect;")
    op.execute("ALTER TABLE model_call DROP CONSTRAINT uq_model_call_run_call;")
    op.execute("DROP TABLE lease;")
    op.execute(
        "ALTER TABLE job DROP CONSTRAINT IF EXISTS "
        "fk_job_current_attempt_belongs_to_job;"
    )
    op.execute("ALTER TABLE job DROP CONSTRAINT IF EXISTS fk_job_current_attempt;")
    op.execute("DROP TABLE attempt;")
    op.execute("DROP TABLE job;")
    op.execute("DROP FUNCTION am_guard_durable_effect_transition();")

    op.execute("DROP TRIGGER trg_contract_state_transition_immutable ON contract_state_transition;")
    op.execute("DELETE FROM contract_state_transition WHERE machine IN ('job', 'attempt');")
    op.execute(
        "ALTER TABLE contract_state_transition "
        "DROP CONSTRAINT ck_contract_state_transition_machine;"
    )
    op.execute(
        "ALTER TABLE contract_state_transition ADD CONSTRAINT "
        "ck_contract_state_transition_machine "
        "CHECK (machine IN ('audit_run', 'blob', 'command_idempotency'));"
    )
    op.execute(
        """
        CREATE TRIGGER trg_contract_state_transition_immutable
            BEFORE INSERT OR UPDATE OR DELETE ON contract_state_transition
            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
        """
    )
