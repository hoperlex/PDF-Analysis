"""The pull channel: runner tokens and the tasks a runner takes.

Revision ID: 0031_executor_pull_channel
Revises: 0030_executor_connections

`EXEC-PULL-01` (owner rulings R-143 and R-144; ``docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md``
sections 2 to 4). A ``pull`` connection is served by a *runner* -- a Claude Code session or an
unattended agent -- that calls the stand over HTTPS, takes a task, and submits the model's
answer. The runner never reaches PostgreSQL or S3 (R-143c): the ``api`` writes these rows on its
behalf, and the worker waits on them inside the Attempt that needs the answer.

What this revision adds
-----------------------
``executor_runner_token`` (``ern``)
    one credential of exactly one connection. **Only the SHA-256 of the value is stored**; the
    value is shown once when it is issued. ``token_prefix`` is the recognisable, non-secret
    start (``amr_`` and eight characters) that an administrator reads on the screen and the
    ``api`` looks the row up by; the hash is then compared in constant time. A token expires
    (default 30 days, set at issue), can be revoked once, and records when and from where it
    was last seen. Only ``revoked_at``/``revoked_by`` (write-once) and the last-seen pair move.
``executor_task`` (``ext``)
    one unit of model work: the request payload (system prompt, user text, output JSON
    schema), the Attempt and model call that wait for it (or, for «Проверить», the probe), its
    ``deadline_at``, its claim lease and, once, its answer with the model the runner *declared*.
    States: ``open -> claimed -> answered | failed``, and ``expired`` or ``cancelled`` from
    ``open`` or ``claimed``. A claim whose lease lapses returns to ``open``. The payload and the
    answer are the stand's documents: both are cleared seven days after the task became
    terminal (``payload_cleared_at``), and the row stays as the trail.

No behaviour changes until a ``pull`` connection is routed: nothing writes either table before
that.

Downgrade
---------
Refused once any token or any task exists, as ``0030`` refuses a populated connection table;
restore a database backup instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0031_executor_pull_channel"
down_revision: str | None = "0030_executor_connections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_TABLES = ("executor_task", "executor_runner_token")


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE executor_runner_token (
            token_id          text PRIMARY KEY,
            connection_id     text NOT NULL REFERENCES executor_connection (connection_id),
            token_prefix      text NOT NULL,
            token_hash        bytea NOT NULL,
            created_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by        text NOT NULL,
            expires_at        timestamptz NOT NULL,
            revoked_at        timestamptz NULL,
            revoked_by        text NULL,
            last_seen_at      timestamptz NULL,
            last_seen_address text NULL,
            CONSTRAINT uq_executor_runner_token_prefix UNIQUE (token_prefix),
            CONSTRAINT uq_executor_runner_token_hash UNIQUE (token_hash),
            CONSTRAINT uq_executor_runner_token_connection UNIQUE (token_id, connection_id),
            CONSTRAINT ck_executor_runner_token_id_format
                CHECK (token_id ~ '^ern_{ULID}$'),
            CONSTRAINT ck_executor_runner_token_prefix_format
                CHECK (token_prefix ~ '^amr_[0-9a-z]{{8}}$'),
            CONSTRAINT ck_executor_runner_token_hash_length
                CHECK (octet_length(token_hash) = 32),
            CONSTRAINT ck_executor_runner_token_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_runner_token_revoked_by_format
                CHECK (revoked_by IS NULL OR revoked_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_runner_token_revoke_pair
                CHECK ((revoked_at IS NULL) = (revoked_by IS NULL)),
            CONSTRAINT ck_executor_runner_token_expiry CHECK (expires_at > created_at),
            CONSTRAINT ck_executor_runner_token_address
                CHECK (last_seen_address IS NULL OR char_length(last_seen_address) <= 64),
            CONSTRAINT ck_executor_runner_token_seen_pair
                CHECK (last_seen_address IS NULL OR last_seen_at IS NOT NULL)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_executor_runner_token_connection ON executor_runner_token "
        "(connection_id, created_at DESC, token_id DESC)"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_runner_token_frozen_guard BEFORE UPDATE ON "
        "executor_runner_token FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'token_id', 'connection_id', 'token_prefix', 'token_hash', 'created_at', "
        "'created_by', 'expires_at')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_runner_token_write_once BEFORE UPDATE ON "
        "executor_runner_token FOR EACH ROW EXECUTE FUNCTION "
        "am_guard_write_once_columns('revoked_at', 'revoked_by')"
    )
    op.execute(
        "COMMENT ON TABLE executor_runner_token IS "
        "'R-143 runner credentials. Only the SHA-256 of the value is stored; the value is "
        "shown once when issued. Configuration, kept by the product purge like accounts.';"
    )

    op.execute(
        f"""
        CREATE TABLE executor_task (
            task_id                text PRIMARY KEY,
            connection_id          text NOT NULL,
            revision_id            text NOT NULL,
            origin                 text NOT NULL,
            run_id                 text NULL REFERENCES audit_run (run_id),
            attempt_id             text NULL REFERENCES attempt (attempt_id),
            model_call_id          text NULL REFERENCES provider_call_effect (model_call_id),
            probe_id               text NULL REFERENCES executor_probe (probe_id),
            state                  text NOT NULL DEFAULT 'open',
            expected_model         text NOT NULL,
            payload                jsonb NULL,
            created_at             timestamptz NOT NULL DEFAULT clock_timestamp(),
            deadline_at            timestamptz NOT NULL,
            claimed_by_token_id    text NULL,
            claim_expires_at       timestamptz NULL,
            first_claimed_at       timestamptz NULL,
            claim_count            integer NOT NULL DEFAULT 0,
            answer_text            text NULL,
            declared_model         text NULL,
            declared_input_tokens  integer NULL,
            declared_output_tokens integer NULL,
            fail_reason            text NULL,
            terminal_at            timestamptz NULL,
            payload_cleared_at     timestamptz NULL,
            CONSTRAINT fk_executor_task_revision FOREIGN KEY (revision_id, connection_id)
                REFERENCES executor_connection_revision (revision_id, connection_id),
            CONSTRAINT fk_executor_task_token FOREIGN KEY (claimed_by_token_id, connection_id)
                REFERENCES executor_runner_token (token_id, connection_id),
            CONSTRAINT ck_executor_task_id_format CHECK (task_id ~ '^ext_{ULID}$'),
            CONSTRAINT ck_executor_task_origin CHECK (origin IN ('run_call', 'probe')),
            CONSTRAINT ck_executor_task_origin_shape CHECK (
                (origin = 'run_call' AND run_id IS NOT NULL AND attempt_id IS NOT NULL
                    AND probe_id IS NULL)
                OR (origin = 'probe' AND probe_id IS NOT NULL AND run_id IS NULL
                    AND attempt_id IS NULL AND model_call_id IS NULL)
            ),
            CONSTRAINT ck_executor_task_state CHECK (
                state IN ('open', 'claimed', 'answered', 'failed', 'expired', 'cancelled')
            ),
            CONSTRAINT ck_executor_task_expected_model
                CHECK (char_length(expected_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_task_deadline CHECK (deadline_at > created_at),
            CONSTRAINT ck_executor_task_claim_count CHECK (claim_count >= 0),
            CONSTRAINT ck_executor_task_declared_model
                CHECK (declared_model IS NULL OR char_length(declared_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_task_declared_tokens CHECK (
                (declared_input_tokens IS NULL OR declared_input_tokens >= 0)
                AND (declared_output_tokens IS NULL OR declared_output_tokens >= 0)
            ),
            CONSTRAINT ck_executor_task_fail_reason
                CHECK (fail_reason IS NULL OR char_length(fail_reason) BETWEEN 1 AND 512),
            CONSTRAINT ck_executor_task_claim_shape CHECK (
                (state = 'open' AND claimed_by_token_id IS NULL AND claim_expires_at IS NULL)
                OR (state = 'claimed' AND claimed_by_token_id IS NOT NULL
                    AND claim_expires_at IS NOT NULL AND claim_count >= 1
                    AND first_claimed_at IS NOT NULL)
                OR state IN ('answered', 'failed', 'expired', 'cancelled')
            ),
            CONSTRAINT ck_executor_task_terminal_shape CHECK (
                (state IN ('open', 'claimed')) = (terminal_at IS NULL)
            ),
            CONSTRAINT ck_executor_task_answer_shape CHECK (
                (state = 'answered' AND declared_model IS NOT NULL
                    AND (answer_text IS NOT NULL OR payload_cleared_at IS NOT NULL))
                OR (state <> 'answered' AND answer_text IS NULL AND declared_model IS NULL)
            ),
            CONSTRAINT ck_executor_task_fail_shape
                CHECK ((state = 'failed') = (fail_reason IS NOT NULL)),
            CONSTRAINT ck_executor_task_payload_shape CHECK (
                (payload IS NOT NULL OR payload_cleared_at IS NOT NULL)
                AND (payload_cleared_at IS NULL OR terminal_at IS NOT NULL)
            )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_executor_task_live ON executor_task "
        "(connection_id, created_at, task_id) WHERE state IN ('open', 'claimed')"
    )
    op.execute(
        "CREATE INDEX ix_executor_task_attempt ON executor_task (attempt_id) "
        "WHERE attempt_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_executor_task_run ON executor_task (run_id) WHERE run_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_executor_task_clearing ON executor_task (terminal_at) "
        "WHERE terminal_at IS NOT NULL AND payload_cleared_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_executor_task_token ON executor_task (claimed_by_token_id) "
        "WHERE claimed_by_token_id IS NOT NULL"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_task_frozen_guard BEFORE UPDATE ON executor_task "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'task_id', 'connection_id', 'revision_id', 'origin', 'run_id', 'attempt_id', "
        "'model_call_id', 'probe_id', 'expected_model', 'created_at', 'deadline_at')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_task_write_once BEFORE UPDATE ON executor_task "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns("
        "'terminal_at', 'first_claimed_at', 'payload_cleared_at')"
    )
    op.execute(
        "COMMENT ON TABLE executor_task IS "
        "'R-143 a unit of model work handed to a runner. payload and answer_text hold the "
        "stand''s documents and are cleared seven days after the task is terminal; the row "
        "stays as the trail. The api writes it on behalf of the runner, the worker waits on it.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained = [
        table for table in _TABLES
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one()
    ]
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0031_executor_pull_channel with retained pull-channel data "
            f"({', '.join(retained)}); restore a database backup instead"
        )
    for table in _TABLES:
        op.execute(f"DROP TABLE {table}")
