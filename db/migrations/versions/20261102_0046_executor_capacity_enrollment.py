"""Executor capacity, universal-agent enrollment and agent install sessions.

Revision ID: 0046_executor_capacity_enroll
Revises: 0045_comparison_page_bounds

The revision id is 29 characters, not the file name's 33: ``alembic_version.version_num`` is
``varchar(32)`` (Alembic's default; ``0015_accounts_roles_registration``, at exactly 32, is the longest
id before this one), and a longer id fails the version update that closes the upgrade. The file name
keeps its full form; Alembic reads the id from the ``revision`` variable below.

`EXEC2-SEAL-1` (ADR-0026 decisions 1 to 9, owner rulings `R-149a` to `R-149f`;
``docs/program/dispatch/EXEC2-PLAN.md``). It creates the storage of the stage-1 surface of contract
1.15.0 and nothing that behaves: no statement writes any of it until a stage-1 lane implements the
operation that does. Every addition is nullable or a new table, so a database at ``0045`` upgrades with
no row touched, and capacity stays at its default of one.

What this revision adds
-----------------------
``executor_connection_revision.max_active_runs``
    the most units of a connection that may be in use at once (a Run in ``leased``, ``running`` or
    ``retry_wait``, a comparison model call in ``prepared`` or ``sent``), 1 to 16. ``NULL`` is a
    revision written before this column and reads as 1. The table stays immutable.
``executor_task.claimed_by_instance_id``
    the agent process that claimed a task, so a held claim is redelivered only to that instance
    (decision 3). It may be set only while a token holds the claim.
``executor_runner_token`` health columns
    ``agent_version``, ``cli_health``, ``concurrency``, ``execution_profile``, ``declared_features`` and
    ``health_reported_at`` (decision 5): the closed enumerations and bounded strings an agent reports,
    all set together or all absent. No secret, no path to a credential and no document text has a
    column. They are not frozen: a later report replaces them.
``executor_connection.integration_authorised_at`` and ``integration_authorised_by``
    the administrator's mark that the command-line clients behind a ``pull`` connection are authorised
    for this integration (`R-149b`, decision 8): the current mark; its history is the audit trail.
``executor_secret`` accepts the purpose ``agent_install_key``
    the sealed SSH key of an install session. ``public_material`` is allowed for it as for an SSH key.
    No connection kind holds this purpose (``executors.model.PURPOSES_BY_KIND``), and the contract's
    ``setExecutorSecret`` cannot name it.
``executor_enrollment`` (``exen``)
    a single-use grant by which a universal agent obtains a runner token for exactly one ``pull``
    connection (decision 4). **Only the SHA-256 of the secret is stored**, beside its non-secret
    prefix. At most one grant per connection is unredeemed and unrevoked at a time; redeeming and
    revoking are write-once and exclusive. Its state is derived (pending, redeemed, expired, revoked).
``executor_agent_install`` (``exai``)
    one install session of the agent over SSH (decision 7): host, port, user, the sealed key, the host
    key the worker observed, the fingerprint the administrator confirmed (write-once, so a changed key
    cannot be adopted silently), the package it installs and, when it fails, a sanitised reason from a
    closed set. At most one session per connection is unfinished at a time.

Two rows of ``executor_secret`` checks are redefined in place (same names, same count):
``ck_executor_secret_purpose`` and ``ck_executor_secret_public_material``.

The actor columns (``created_by``, ``revoked_by``, ``host_key_confirmed_by``,
``integration_authorised_by``) hold a ``usr`` identity and carry no foreign key to ``app_user``, as in
``0030``.

Downgrade
---------
Refused while any enrollment or install session exists, any revision names a capacity above one, any
connection carries an integration-authorisation mark or any ``agent_install_key`` secret exists; restore
a database backup instead. The health columns and ``claimed_by_instance_id`` are transient (an agent
reports again, a claim is renewed) and are dropped without ceremony, as are explicit capacities of one.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0046_executor_capacity_enroll"
down_revision: str | None = "0045_comparison_page_bounds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

_NEW_TABLES = ("executor_agent_install", "executor_enrollment")

_INSTALL_FAILURES = (
    "'host_unreachable', 'ssh_refused', 'host_key_changed', 'host_key_not_confirmed', "
    "'sudo_password_required', 'unsupported_platform', 'package_unavailable', 'install_failed', "
    "'enrollment_failed', 'secret_unreadable', 'no_worker', 'timed_out'"
)


def upgrade() -> None:
    # --- capacity of a connection (decision 1) --------------------------------------------------
    op.execute("ALTER TABLE executor_connection_revision ADD COLUMN max_active_runs integer NULL")
    op.execute(
        "ALTER TABLE executor_connection_revision ADD CONSTRAINT ck_executor_revision_max_active_runs "
        "CHECK (max_active_runs IS NULL OR max_active_runs BETWEEN 1 AND 16)"
    )

    # --- the instance that holds a claim (decision 3) -------------------------------------------
    op.execute("ALTER TABLE executor_task ADD COLUMN claimed_by_instance_id text NULL")
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_claimed_by_instance_format "
        "CHECK (claimed_by_instance_id IS NULL OR claimed_by_instance_id ~ '^[A-Za-z0-9_-]{8,64}$')"
    )
    op.execute(
        "ALTER TABLE executor_task ADD CONSTRAINT ck_executor_task_instance_with_token "
        "CHECK (claimed_by_instance_id IS NULL OR claimed_by_token_id IS NOT NULL)"
    )

    # --- the health an agent reports on its token (decision 5) ----------------------------------
    op.execute(
        "ALTER TABLE executor_runner_token "
        "ADD COLUMN agent_version text NULL, "
        "ADD COLUMN cli_health jsonb NULL, "
        "ADD COLUMN concurrency integer NULL, "
        "ADD COLUMN execution_profile text NULL, "
        "ADD COLUMN declared_features jsonb NULL, "
        "ADD COLUMN health_reported_at timestamptz NULL"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_agent_version "
        "CHECK (agent_version IS NULL OR agent_version ~ '^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$')"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_cli_health "
        "CHECK (cli_health IS NULL OR (CASE WHEN jsonb_typeof(cli_health) = 'array' "
        "THEN jsonb_array_length(cli_health) <= 8 ELSE false END))"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_concurrency "
        "CHECK (concurrency IS NULL OR concurrency BETWEEN 1 AND 16)"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_execution_profile "
        "CHECK (execution_profile IS NULL OR execution_profile IN ('command', 'endpoint'))"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_features "
        "CHECK (declared_features IS NULL OR (CASE WHEN jsonb_typeof(declared_features) = 'array' "
        "THEN jsonb_array_length(declared_features) <= 8 ELSE false END))"
    )
    op.execute(
        "ALTER TABLE executor_runner_token ADD CONSTRAINT ck_executor_runner_token_health_shape CHECK ("
        "(health_reported_at IS NULL AND agent_version IS NULL AND cli_health IS NULL "
        "AND concurrency IS NULL AND execution_profile IS NULL AND declared_features IS NULL) "
        "OR (health_reported_at IS NOT NULL AND agent_version IS NOT NULL AND cli_health IS NOT NULL "
        "AND concurrency IS NOT NULL AND execution_profile IS NOT NULL AND declared_features IS NOT NULL))"
    )

    # --- the administrator's integration-authorisation mark (decision 8, R-149b) ----------------
    op.execute(
        "ALTER TABLE executor_connection "
        "ADD COLUMN integration_authorised_at timestamptz NULL, "
        "ADD COLUMN integration_authorised_by text NULL"
    )
    op.execute(
        "ALTER TABLE executor_connection ADD CONSTRAINT "
        "ck_executor_connection_integration_authorised_by_format "
        f"CHECK (integration_authorised_by IS NULL OR integration_authorised_by ~ '^usr_{ULID}$')"
    )
    op.execute(
        "ALTER TABLE executor_connection ADD CONSTRAINT ck_executor_connection_integration_pair "
        "CHECK ((integration_authorised_at IS NULL) = (integration_authorised_by IS NULL))"
    )
    op.execute(
        "ALTER TABLE executor_connection ADD CONSTRAINT ck_executor_connection_integration_pull_only "
        "CHECK (integration_authorised_at IS NULL OR kind = 'pull')"
    )

    # --- the sealed key of an install session: one more secret purpose --------------------------
    op.execute("ALTER TABLE executor_secret DROP CONSTRAINT ck_executor_secret_purpose")
    op.execute(
        "ALTER TABLE executor_secret ADD CONSTRAINT ck_executor_secret_purpose "
        "CHECK (purpose IN ('api_key', 'ssh_private_key', 'agent_install_key'))"
    )
    op.execute("ALTER TABLE executor_secret DROP CONSTRAINT ck_executor_secret_public_material")
    op.execute(
        "ALTER TABLE executor_secret ADD CONSTRAINT ck_executor_secret_public_material "
        "CHECK (public_material IS NULL "
        "OR (purpose IN ('ssh_private_key', 'agent_install_key') "
        "AND char_length(public_material) BETWEEN 1 AND 2048))"
    )

    # --- the enrollment grant (decision 4) -------------------------------------------------------
    op.execute(
        f"""
        CREATE TABLE executor_enrollment (
            enrollment_id   text PRIMARY KEY,
            connection_id   text NOT NULL REFERENCES executor_connection (connection_id),
            secret_prefix   text NOT NULL,
            secret_hash     bytea NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by      text NOT NULL,
            expires_at      timestamptz NOT NULL,
            redeemed_at     timestamptz NULL,
            runner_token_id text NULL,
            revoked_at      timestamptz NULL,
            revoked_by      text NULL,
            CONSTRAINT fk_executor_enrollment_token FOREIGN KEY (runner_token_id, connection_id)
                REFERENCES executor_runner_token (token_id, connection_id),
            CONSTRAINT uq_executor_enrollment_prefix UNIQUE (secret_prefix),
            CONSTRAINT uq_executor_enrollment_hash UNIQUE (secret_hash),
            CONSTRAINT ck_executor_enrollment_id_format
                CHECK (enrollment_id ~ '^exen_{ULID}$'),
            CONSTRAINT ck_executor_enrollment_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_enrollment_prefix_format
                CHECK (secret_prefix ~ '^ame_[0-9a-z]{{8}}$'),
            CONSTRAINT ck_executor_enrollment_hash_length
                CHECK (octet_length(secret_hash) = 32),
            CONSTRAINT ck_executor_enrollment_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_enrollment_revoked_by_format
                CHECK (revoked_by IS NULL OR revoked_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_enrollment_runner_token_id_format
                CHECK (runner_token_id IS NULL OR runner_token_id ~ '^ern_{ULID}$'),
            CONSTRAINT ck_executor_enrollment_expiry CHECK (expires_at > created_at),
            CONSTRAINT ck_executor_enrollment_revoke_pair
                CHECK ((revoked_at IS NULL) = (revoked_by IS NULL)),
            CONSTRAINT ck_executor_enrollment_redeem_pair
                CHECK ((redeemed_at IS NULL) = (runner_token_id IS NULL)),
            CONSTRAINT ck_executor_enrollment_one_ending
                CHECK (redeemed_at IS NULL OR revoked_at IS NULL),
            CONSTRAINT ck_executor_enrollment_redeemed_in_window
                CHECK (redeemed_at IS NULL OR redeemed_at <= expires_at)
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_enrollment_pending ON executor_enrollment (connection_id) "
        "WHERE redeemed_at IS NULL AND revoked_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_executor_enrollment_connection ON executor_enrollment "
        "(connection_id, created_at DESC, enrollment_id DESC)"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_enrollment_frozen_guard BEFORE UPDATE ON executor_enrollment "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'enrollment_id', 'connection_id', 'secret_prefix', 'secret_hash', 'created_at', "
        "'created_by', 'expires_at')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_enrollment_write_once BEFORE UPDATE ON executor_enrollment "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns("
        "'redeemed_at', 'revoked_at', 'revoked_by')"
    )
    op.execute(
        "COMMENT ON TABLE executor_enrollment IS "
        "'ADR-0026 decision 4: the single-use grant of a universal agent. Only the SHA-256 of the "
        "secret is stored; the value is shown once when issued. Configuration, kept by the product "
        "purge like accounts.';"
    )

    # --- the install session over SSH (decision 7) -----------------------------------------------
    op.execute(
        f"""
        CREATE TABLE executor_agent_install (
            install_id                     text PRIMARY KEY,
            connection_id                  text NOT NULL REFERENCES executor_connection (connection_id),
            state                          text NOT NULL DEFAULT 'requested',
            access                         text NOT NULL,
            ssh_host                       text NOT NULL,
            ssh_port                       integer NOT NULL,
            ssh_user                       text NOT NULL,
            key_secret_id                  text NULL REFERENCES executor_secret (secret_id),
            observed_host_key              text NULL,
            confirmed_host_key_fingerprint text NULL,
            host_key_confirmed_at          timestamptz NULL,
            host_key_confirmed_by          text NULL,
            package_version                text NULL,
            package_sha256                 text NULL,
            failure_reason                 text NULL,
            key_removed_at                 timestamptz NULL,
            created_at                     timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by                     text NOT NULL,
            updated_at                     timestamptz NOT NULL DEFAULT clock_timestamp(),
            finished_at                    timestamptz NULL,
            CONSTRAINT ck_executor_agent_install_id_format
                CHECK (install_id ~ '^exai_{ULID}$'),
            CONSTRAINT ck_executor_agent_install_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_agent_install_key_secret_id_format
                CHECK (key_secret_id IS NULL OR key_secret_id ~ '^exs_{ULID}$'),
            CONSTRAINT ck_executor_agent_install_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_agent_install_confirmed_by_format
                CHECK (host_key_confirmed_by IS NULL OR host_key_confirmed_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_agent_install_state CHECK (
                state IN ('requested', 'scanning', 'awaiting_host_key', 'installing', 'succeeded',
                          'failed')),
            CONSTRAINT ck_executor_agent_install_access
                CHECK (access IN ('generated_key', 'pasted_key')),
            CONSTRAINT ck_executor_agent_install_ssh_host
                CHECK (char_length(ssh_host) BETWEEN 1 AND 253),
            CONSTRAINT ck_executor_agent_install_ssh_port CHECK (ssh_port BETWEEN 1 AND 65535),
            CONSTRAINT ck_executor_agent_install_ssh_user
                CHECK (char_length(ssh_user) BETWEEN 1 AND 64),
            CONSTRAINT ck_executor_agent_install_observed_host_key
                CHECK (observed_host_key IS NULL OR char_length(observed_host_key) BETWEEN 1 AND 2048),
            CONSTRAINT ck_executor_agent_install_confirmed_fingerprint
                CHECK (confirmed_host_key_fingerprint IS NULL
                       OR char_length(confirmed_host_key_fingerprint) BETWEEN 1 AND 128),
            CONSTRAINT ck_executor_agent_install_confirm_shape CHECK (
                (host_key_confirmed_at IS NULL) = (host_key_confirmed_by IS NULL)
                AND (host_key_confirmed_at IS NULL) = (confirmed_host_key_fingerprint IS NULL)),
            CONSTRAINT ck_executor_agent_install_package_version CHECK (
                package_version IS NULL
                OR package_version ~ '^[0-9]{{1,4}}\\.[0-9]{{1,4}}\\.[0-9]{{1,4}}$'),
            CONSTRAINT ck_executor_agent_install_package_sha256
                CHECK (package_sha256 IS NULL OR package_sha256 ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_executor_agent_install_package_pair
                CHECK ((package_version IS NULL) = (package_sha256 IS NULL)),
            CONSTRAINT ck_executor_agent_install_failure_reason
                CHECK (failure_reason IS NULL OR failure_reason IN ({_INSTALL_FAILURES})),
            CONSTRAINT ck_executor_agent_install_failure_shape
                CHECK ((state = 'failed') = (failure_reason IS NOT NULL)),
            CONSTRAINT ck_executor_agent_install_finished_shape
                CHECK ((state IN ('succeeded', 'failed')) = (finished_at IS NOT NULL)),
            CONSTRAINT ck_executor_agent_install_observed_before_confirm CHECK (
                state NOT IN ('awaiting_host_key', 'installing', 'succeeded')
                OR observed_host_key IS NOT NULL),
            CONSTRAINT ck_executor_agent_install_confirmed_before_install CHECK (
                state NOT IN ('installing', 'succeeded') OR host_key_confirmed_at IS NOT NULL),
            CONSTRAINT ck_executor_agent_install_updated_after_created
                CHECK (updated_at >= created_at),
            CONSTRAINT ck_executor_agent_install_key_removed_shape
                CHECK ((key_secret_id IS NULL) = (key_removed_at IS NOT NULL))
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_agent_install_open ON executor_agent_install (connection_id) "
        "WHERE state NOT IN ('succeeded', 'failed')"
    )
    op.execute(
        "CREATE INDEX ix_executor_agent_install_connection ON executor_agent_install "
        "(connection_id, created_at DESC, install_id DESC)"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_agent_install_frozen_guard BEFORE UPDATE ON executor_agent_install "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'install_id', 'connection_id', 'access', 'ssh_host', 'ssh_port', 'ssh_user', "
        "'created_at', 'created_by')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_agent_install_write_once BEFORE UPDATE ON executor_agent_install "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns("
        "'observed_host_key', 'confirmed_host_key_fingerprint', 'host_key_confirmed_at', "
        "'host_key_confirmed_by', 'finished_at')"
    )
    op.execute(
        "COMMENT ON TABLE executor_agent_install IS "
        "'ADR-0026 decision 7: one install session of the agent over SSH, executed by the worker. "
        "The sealed key is an executor_secret of purpose agent_install_key, destroyed when the install "
        "ends. Configuration, kept by the product purge like accounts.';"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in _NEW_TABLES:
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    if bind.execute(text(
        "SELECT EXISTS (SELECT 1 FROM executor_connection_revision WHERE max_active_runs > 1)"
    )).scalar_one():
        retained.append("executor_connection_revision.max_active_runs above one")
    if bind.execute(text(
        "SELECT EXISTS (SELECT 1 FROM executor_connection WHERE integration_authorised_at IS NOT NULL)"
    )).scalar_one():
        retained.append("executor_connection.integration_authorised_at")
    if bind.execute(text(
        "SELECT EXISTS (SELECT 1 FROM executor_secret WHERE purpose = 'agent_install_key')"
    )).scalar_one():
        retained.append("executor_secret purpose agent_install_key")
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0046_executor_capacity_enroll with retained enrollment, "
            f"install or capacity data ({', '.join(retained)}); restore a database backup instead"
        )

    for table in _NEW_TABLES:
        op.execute(f"DROP TABLE {table}")

    op.execute("ALTER TABLE executor_secret DROP CONSTRAINT ck_executor_secret_public_material")
    op.execute(
        "ALTER TABLE executor_secret ADD CONSTRAINT ck_executor_secret_public_material "
        "CHECK (public_material IS NULL "
        "OR (purpose = 'ssh_private_key' AND char_length(public_material) BETWEEN 1 AND 2048))"
    )
    op.execute("ALTER TABLE executor_secret DROP CONSTRAINT ck_executor_secret_purpose")
    op.execute(
        "ALTER TABLE executor_secret ADD CONSTRAINT ck_executor_secret_purpose "
        "CHECK (purpose IN ('api_key', 'ssh_private_key'))"
    )

    for constraint in (
        "ck_executor_connection_integration_pull_only", "ck_executor_connection_integration_pair",
        "ck_executor_connection_integration_authorised_by_format",
    ):
        op.execute(f"ALTER TABLE executor_connection DROP CONSTRAINT {constraint}")
    op.execute(
        "ALTER TABLE executor_connection DROP COLUMN integration_authorised_by, "
        "DROP COLUMN integration_authorised_at"
    )

    for constraint in (
        "ck_executor_runner_token_health_shape", "ck_executor_runner_token_features",
        "ck_executor_runner_token_execution_profile", "ck_executor_runner_token_concurrency",
        "ck_executor_runner_token_cli_health", "ck_executor_runner_token_agent_version",
    ):
        op.execute(f"ALTER TABLE executor_runner_token DROP CONSTRAINT {constraint}")
    op.execute(
        "ALTER TABLE executor_runner_token DROP COLUMN health_reported_at, "
        "DROP COLUMN declared_features, DROP COLUMN execution_profile, DROP COLUMN concurrency, "
        "DROP COLUMN cli_health, DROP COLUMN agent_version"
    )

    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_instance_with_token")
    op.execute("ALTER TABLE executor_task DROP CONSTRAINT ck_executor_task_claimed_by_instance_format")
    op.execute("ALTER TABLE executor_task DROP COLUMN claimed_by_instance_id")

    op.execute(
        "ALTER TABLE executor_connection_revision DROP CONSTRAINT ck_executor_revision_max_active_runs"
    )
    op.execute("ALTER TABLE executor_connection_revision DROP COLUMN max_active_runs")
