"""Executor connections, sealed secrets, probes, routes and the frozen revision of a run.

Revision ID: 0030_executor_connections
Revises: 0029_routing_refusal_codes

`EXEC-SEAL-01` (owner rulings R-143 and R-144; ``docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md``
sections 2 to 5). A *connection* is where a process sends model work; a *revision* is one
immutable set of its non-secret settings; a *secret* is held only as ciphertext, sealed by the
``api`` to the stand's public key and opened by the worker alone; a *probe* records one check
of a revision; a *route* names which connection serves a kind of model work.

What this revision adds
-----------------------
``executor_connection`` (``exc``)
    the connection: its kind (``http_api``, ``ssh_command``, ``pull``), its display name and,
    once, when it was archived. Everything but the archive stamp is frozen.
``executor_connection_revision`` (``excr``)
    immutable settings, numbered per connection. The pin id (tariffs and the input budget) and
    the gateway model name (sent to the provider and compared with the reported model) are two
    fields, neither derived from the other (plan section 3). ``host_key`` is the full public key
    line for ``UserKnownHostsFile``; the fingerprint is derived on read.
``executor_secret`` (``exs``)
    the ciphertext (``bytea``) with the key id it was sealed under, the destination it was
    sealed for (informational: the worker recomputes it and never trusts this column), the last
    four characters, and for a generated SSH key the public half. Only ``replaced_at`` may move,
    once. A rotation writes a new row; at most one row per connection and purpose is current.
``executor_probe`` (``epb``)
    ``requested``, ``running`` or ``finished`` with the outcome vocabulary of the plan. The
    worker that executes probes arrives in ``EXEC-HTTP-01``; the ``api`` ends a probe nobody took
    in 120 seconds as ``no_worker``.
``executor_route_event`` (``ert``) and the view ``executor_route_current``
    append-only changes of the route per kind of model work; the view is the latest of each.

and, on existing tables, all nullable and writable at insert:

* ``audit_run.connection_revision_id`` -- the revision a run froze at start. ``trg_audit_run_frozen_guard``
  is BEFORE UPDATE only, so a column set at insert passes it unless it is listed; it is added to
  the frozen list the way ``0017`` and ``0023`` did, so it actually freezes.
* ``model_call.connection_revision_id`` and ``model_call.identity_basis`` (``reported`` or
  ``declared``), and the same two columns on ``provider_call_effect``. A revision and a basis go
  together or are both absent (the ``environment`` source sets neither). The effect's state guard
  already refuses any change of a column it does not list as mutable, so both are immutable there
  too.
* ``ck_model_call_cost_basis`` (``0004``) gains ``unmetered``: a call on a connection that has no
  per-call cost is recorded as such, never as a zero.

No behaviour changes: the provider source stays ``environment`` and nothing writes these
columns yet.

The actor columns (``created_by``, ``set_by``, ``requested_by``) hold an ``usr`` identity and
carry no foreign key to ``app_user``: a key would have to be registered in
``auditmanager.access.references``, outside this task's grant. The identity stays in the history
of an account that is later purged.

Downgrade
---------
Refused once any executor row, any run, call or effect naming a revision, or any ``unmetered``
call exists, as ``0019`` refuses a populated worker registry; restore a database backup instead.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0030_executor_connections"
down_revision: str | None = "0029_routing_refusal_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

#: ``audit_run``'s frozen list as ``0023`` left it (``0017`` plus ``norm_retrieval_set_id``).
_FROZEN_RUN_COLUMNS = (
    "'run_id', 'project_uid', 'version_uid', 'analysis_profile_id', "
    "'prompt_bundle_id', 'norms_snapshot_id', 'provider_mode', "
    "'frozen_input_digest', 'created_at', 'reaudit_of_run_id', 'norm_retrieval_set_id'"
)

_TABLES = (
    "executor_route_event", "executor_probe", "executor_secret",
    "executor_connection_revision", "executor_connection",
)


def _frozen_run_guard(*, with_revision: bool) -> None:
    op.execute("DROP TRIGGER trg_audit_run_frozen_guard ON audit_run")
    columns = _FROZEN_RUN_COLUMNS + (", 'connection_revision_id'" if with_revision else "")
    op.execute(
        "CREATE TRIGGER trg_audit_run_frozen_guard BEFORE UPDATE ON audit_run "
        f"FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns({columns})"
    )


def upgrade() -> None:
    op.execute(
        f"""
        CREATE TABLE executor_connection (
            connection_id text PRIMARY KEY,
            kind          text NOT NULL,
            display_name  text NOT NULL,
            created_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by    text NOT NULL,
            archived_at   timestamptz NULL,
            archived_by   text NULL,
            CONSTRAINT ck_executor_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_connection_kind
                CHECK (kind IN ('http_api', 'ssh_command', 'pull')),
            CONSTRAINT ck_executor_connection_display_name
                CHECK (char_length(display_name) BETWEEN 1 AND 120),
            CONSTRAINT ck_executor_connection_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_connection_archived_by_format
                CHECK (archived_by IS NULL OR archived_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_connection_archive_pair
                CHECK ((archived_at IS NULL) = (archived_by IS NULL))
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_connection_frozen_guard BEFORE UPDATE ON executor_connection "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'connection_id', 'kind', 'display_name', 'created_at', 'created_by')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_connection_write_once BEFORE UPDATE ON executor_connection "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns('archived_at', 'archived_by')"
    )

    op.execute(
        f"""
        CREATE TABLE executor_connection_revision (
            revision_id            text PRIMARY KEY,
            connection_id          text NOT NULL REFERENCES executor_connection (connection_id),
            revision_no            integer NOT NULL,
            created_at             timestamptz NOT NULL DEFAULT clock_timestamp(),
            created_by             text NOT NULL,
            pin_id                 text NOT NULL,
            gateway_model          text NOT NULL,
            billing                text NOT NULL,
            allow_client_documents boolean NOT NULL,
            timeout_seconds        integer NOT NULL,
            api_flavour            text NULL,
            base_url               text NULL,
            transport              text NULL,
            max_parallel_calls     integer NULL,
            ssh_host               text NULL,
            ssh_port               integer NULL,
            ssh_user               text NULL,
            host_key               text NULL,
            ssh_profile            text NULL,
            pull_client            text NULL,
            answer_deadline_seconds integer NULL,
            max_claimed_tasks      integer NULL,
            CONSTRAINT uq_executor_revision_number UNIQUE (connection_id, revision_no),
            CONSTRAINT uq_executor_revision_connection UNIQUE (revision_id, connection_id),
            CONSTRAINT ck_executor_revision_id_format
                CHECK (revision_id ~ '^excr_{ULID}$'),
            CONSTRAINT ck_executor_revision_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_revision_number CHECK (revision_no >= 1),
            CONSTRAINT ck_executor_revision_created_by_format
                CHECK (created_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_revision_pin CHECK (char_length(pin_id) BETWEEN 1 AND 128),
            CONSTRAINT ck_executor_revision_gateway_model
                CHECK (char_length(gateway_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_revision_billing
                CHECK (billing IN ('metered', 'not_metered')),
            CONSTRAINT ck_executor_revision_timeout
                CHECK (timeout_seconds BETWEEN 1 AND 3600),
            CONSTRAINT ck_executor_revision_api_flavour
                CHECK (api_flavour IS NULL OR api_flavour IN ('openai_chat', 'anthropic_messages')),
            CONSTRAINT ck_executor_revision_base_url
                CHECK (base_url IS NULL
                       OR (char_length(base_url) BETWEEN 1 AND 2048 AND base_url !~ '[?#]')),
            CONSTRAINT ck_executor_revision_transport
                CHECK (transport IS NULL OR transport IN ('direct', 'vpn', 'ssh_tunnel')),
            CONSTRAINT ck_executor_revision_parallel
                CHECK (max_parallel_calls IS NULL OR max_parallel_calls BETWEEN 1 AND 16),
            CONSTRAINT ck_executor_revision_ssh_host
                CHECK (ssh_host IS NULL OR char_length(ssh_host) BETWEEN 1 AND 253),
            CONSTRAINT ck_executor_revision_ssh_port
                CHECK (ssh_port IS NULL OR ssh_port BETWEEN 1 AND 65535),
            CONSTRAINT ck_executor_revision_ssh_user
                CHECK (ssh_user IS NULL OR char_length(ssh_user) BETWEEN 1 AND 64),
            CONSTRAINT ck_executor_revision_host_key
                CHECK (host_key IS NULL OR char_length(host_key) BETWEEN 1 AND 2048),
            CONSTRAINT ck_executor_revision_ssh_profile
                CHECK (ssh_profile IS NULL
                       OR ssh_profile IN ('claude_code_headless', 'custom_command')),
            CONSTRAINT ck_executor_revision_pull_client
                CHECK (pull_client IS NULL
                       OR pull_client IN ('claude_code_session', 'agent')),
            CONSTRAINT ck_executor_revision_answer_deadline
                CHECK (answer_deadline_seconds IS NULL
                       OR answer_deadline_seconds BETWEEN 10 AND 3600),
            CONSTRAINT ck_executor_revision_max_claimed
                CHECK (max_claimed_tasks IS NULL OR max_claimed_tasks BETWEEN 1 AND 16)
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_connection_revision_immutable "
        "BEFORE UPDATE OR DELETE ON executor_connection_revision "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )

    op.execute(
        f"""
        CREATE TABLE executor_secret (
            secret_id       text PRIMARY KEY,
            connection_id   text NOT NULL REFERENCES executor_connection (connection_id),
            purpose         text NOT NULL,
            kid             text NOT NULL,
            destination     text NOT NULL,
            ciphertext      bytea NOT NULL,
            last4           text NOT NULL,
            public_material text NULL,
            set_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by          text NOT NULL,
            replaced_at     timestamptz NULL,
            CONSTRAINT ck_executor_secret_id_format CHECK (secret_id ~ '^exs_{ULID}$'),
            CONSTRAINT ck_executor_secret_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_secret_purpose
                CHECK (purpose IN ('api_key', 'ssh_private_key')),
            CONSTRAINT ck_executor_secret_kid CHECK (kid ~ '^[A-Za-z0-9._-]{{1,64}}$'),
            CONSTRAINT ck_executor_secret_destination
                CHECK (char_length(destination) BETWEEN 1 AND 2200),
            CONSTRAINT ck_executor_secret_ciphertext
                CHECK (octet_length(ciphertext) BETWEEN 1 AND 20000),
            CONSTRAINT ck_executor_secret_last4 CHECK (char_length(last4) <= 4),
            CONSTRAINT ck_executor_secret_public_material
                CHECK (public_material IS NULL
                       OR (purpose = 'ssh_private_key'
                           AND char_length(public_material) BETWEEN 1 AND 2048)),
            CONSTRAINT ck_executor_secret_set_by_format CHECK (set_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_secret_replaced_after_set
                CHECK (replaced_at IS NULL OR replaced_at >= set_at)
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_executor_secret_current ON executor_secret "
        "(connection_id, purpose) WHERE replaced_at IS NULL"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_secret_frozen_guard BEFORE UPDATE ON executor_secret "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'secret_id', 'connection_id', 'purpose', 'kid', 'destination', 'ciphertext', "
        "'last4', 'public_material', 'set_at', 'set_by')"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_secret_write_once BEFORE UPDATE ON executor_secret "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_write_once_columns('replaced_at')"
    )

    op.execute(
        f"""
        CREATE TABLE executor_probe (
            probe_id          text PRIMARY KEY,
            connection_id     text NOT NULL,
            revision_id       text NOT NULL,
            secret_id         text NULL REFERENCES executor_secret (secret_id),
            state             text NOT NULL,
            outcome           text NULL,
            reported_model    text NULL,
            identity_basis    text NULL,
            latency_ms        integer NULL,
            http_status       integer NULL,
            rate_check        text NULL,
            observed_host_key text NULL,
            detail            text NULL,
            requested_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
            requested_by      text NOT NULL,
            started_at        timestamptz NULL,
            finished_at       timestamptz NULL,
            CONSTRAINT fk_executor_probe_revision FOREIGN KEY (revision_id, connection_id)
                REFERENCES executor_connection_revision (revision_id, connection_id),
            CONSTRAINT ck_executor_probe_id_format CHECK (probe_id ~ '^epb_{ULID}$'),
            CONSTRAINT ck_executor_probe_connection_id_format
                CHECK (connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_probe_revision_id_format
                CHECK (revision_id ~ '^excr_{ULID}$'),
            CONSTRAINT ck_executor_probe_secret_id_format
                CHECK (secret_id IS NULL OR secret_id ~ '^exs_{ULID}$'),
            CONSTRAINT ck_executor_probe_state
                CHECK (state IN ('requested', 'running', 'finished')),
            CONSTRAINT ck_executor_probe_outcome
                CHECK (outcome IS NULL OR outcome IN (
                    'ok', 'ip_refused', 'credential_refused', 'model_mismatch', 'rate_mismatch',
                    'timeout', 'unreachable', 'protocol_error', 'secret_unreadable',
                    'host_key_unpinned', 'host_key_changed', 'no_runner_online',
                    'destination_refused', 'kind_not_served', 'no_worker')),
            CONSTRAINT ck_executor_probe_identity_basis
                CHECK (identity_basis IS NULL OR identity_basis IN ('reported', 'declared')),
            CONSTRAINT ck_executor_probe_rate_check
                CHECK (rate_check IS NULL
                       OR rate_check IN ('checked', 'not_reported', 'mismatch', 'not_metered')),
            CONSTRAINT ck_executor_probe_latency CHECK (latency_ms IS NULL OR latency_ms >= 0),
            CONSTRAINT ck_executor_probe_http_status
                CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
            CONSTRAINT ck_executor_probe_reported_model
                CHECK (reported_model IS NULL OR char_length(reported_model) BETWEEN 1 AND 200),
            CONSTRAINT ck_executor_probe_host_key
                CHECK (observed_host_key IS NULL
                       OR char_length(observed_host_key) BETWEEN 1 AND 2048),
            CONSTRAINT ck_executor_probe_detail
                CHECK (detail IS NULL OR char_length(detail) <= 500),
            CONSTRAINT ck_executor_probe_requested_by_format
                CHECK (requested_by ~ '^usr_{ULID}$'),
            CONSTRAINT ck_executor_probe_state_shape CHECK (
                (state = 'requested'
                    AND outcome IS NULL AND started_at IS NULL AND finished_at IS NULL)
                OR (state = 'running'
                    AND outcome IS NULL AND started_at IS NOT NULL AND finished_at IS NULL)
                OR (state = 'finished' AND outcome IS NOT NULL AND finished_at IS NOT NULL)
            )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_executor_probe_connection ON executor_probe "
        "(connection_id, requested_at DESC, probe_id DESC)"
    )
    op.execute(
        "CREATE INDEX ix_executor_probe_revision ON executor_probe "
        "(revision_id, requested_at DESC, probe_id DESC)"
    )
    op.execute(
        "CREATE INDEX ix_executor_probe_open ON executor_probe (requested_at) "
        "WHERE state <> 'finished'"
    )
    op.execute(
        "CREATE TRIGGER trg_executor_probe_frozen_guard BEFORE UPDATE ON executor_probe "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_frozen_columns("
        "'probe_id', 'connection_id', 'revision_id', 'secret_id', 'requested_at', 'requested_by')"
    )

    op.execute(
        f"""
        CREATE TABLE executor_route_event (
            route_event_id        text PRIMARY KEY,
            work_kind             text NOT NULL,
            route_no              integer NOT NULL,
            primary_connection_id text NOT NULL REFERENCES executor_connection (connection_id),
            standby_connection_id text NULL REFERENCES executor_connection (connection_id),
            set_at                timestamptz NOT NULL DEFAULT clock_timestamp(),
            set_by                text NOT NULL,
            CONSTRAINT uq_executor_route_number UNIQUE (work_kind, route_no),
            CONSTRAINT ck_executor_route_event_id_format
                CHECK (route_event_id ~ '^ert_{ULID}$'),
            CONSTRAINT ck_executor_route_primary_format
                CHECK (primary_connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_route_standby_format
                CHECK (standby_connection_id IS NULL OR standby_connection_id ~ '^exc_{ULID}$'),
            CONSTRAINT ck_executor_route_work_kind CHECK (work_kind IN ('text_analysis')),
            CONSTRAINT ck_executor_route_number CHECK (route_no >= 1),
            CONSTRAINT ck_executor_route_standby_differs
                CHECK (standby_connection_id IS NULL
                       OR standby_connection_id <> primary_connection_id),
            CONSTRAINT ck_executor_route_set_by_format CHECK (set_by ~ '^usr_{ULID}$')
        );
        """
    )
    op.execute(
        "CREATE TRIGGER trg_executor_route_event_append_only "
        "BEFORE UPDATE OR DELETE ON executor_route_event "
        "FOR EACH ROW EXECUTE FUNCTION am_append_only()"
    )
    op.execute(
        """
        CREATE VIEW executor_route_current AS
        SELECT DISTINCT ON (work_kind)
               route_event_id, work_kind, route_no, primary_connection_id,
               standby_connection_id, set_at, set_by
          FROM executor_route_event
         ORDER BY work_kind, route_no DESC;
        """
    )
    op.execute(
        "COMMENT ON TABLE executor_secret IS "
        "'R-143b sealed secrets. Ciphertext only; the key ring is in the worker environment and "
        "never in PostgreSQL. Only replaced_at moves, once. destination is informational: the "
        "worker rebuilds the associated data from the revision it is about to call.';"
    )
    op.execute(
        "COMMENT ON TABLE executor_connection IS "
        "'R-143 where a process sends model work. Configuration, kept by the product purge "
        "like accounts.';"
    )

    # The frozen revision and the call provenance, on existing tables; all nullable.
    for table in ("audit_run", "model_call", "provider_call_effect"):
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN connection_revision_id text NULL "
            "REFERENCES executor_connection_revision (revision_id)"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_connection_revision_format "
            f"CHECK (connection_revision_id IS NULL OR connection_revision_id ~ '^excr_{ULID}$')"
        )
    for table in ("model_call", "provider_call_effect"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN identity_basis text NULL")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_identity_basis "
            "CHECK (identity_basis IS NULL OR identity_basis IN ('reported', 'declared'))"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT ck_{table}_basis_with_revision "
            "CHECK ((connection_revision_id IS NULL) = (identity_basis IS NULL))"
        )
        op.execute(
            f"CREATE INDEX ix_{table}_connection_revision ON {table} (connection_revision_id) "
            "WHERE connection_revision_id IS NOT NULL"
        )
    op.execute(
        "CREATE INDEX ix_audit_run_connection_revision ON audit_run (connection_revision_id) "
        "WHERE connection_revision_id IS NOT NULL"
    )
    _frozen_run_guard(with_revision=True)

    op.execute("ALTER TABLE model_call DROP CONSTRAINT ck_model_call_cost_basis")
    op.execute(
        "ALTER TABLE model_call ADD CONSTRAINT ck_model_call_cost_basis "
        "CHECK (cost_basis IN ('measured', 'estimated', 'unmetered'))"
    )


def downgrade() -> None:
    bind = op.get_bind()
    retained: list[str] = []
    for table in reversed(_TABLES):
        if bind.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar_one():
            retained.append(table)
    for table in ("audit_run", "model_call", "provider_call_effect"):
        if bind.execute(text(
            f"SELECT EXISTS (SELECT 1 FROM {table} WHERE connection_revision_id IS NOT NULL)"
        )).scalar_one():
            retained.append(f"{table}.connection_revision_id")
    if bind.execute(text(
        "SELECT EXISTS (SELECT 1 FROM model_call WHERE cost_basis = 'unmetered')"
    )).scalar_one():
        retained.append("model_call.cost_basis unmetered")
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0030_executor_connections with retained executor data "
            f"({', '.join(retained)}); restore a database backup instead"
        )

    op.execute("ALTER TABLE model_call DROP CONSTRAINT ck_model_call_cost_basis")
    op.execute(
        "ALTER TABLE model_call ADD CONSTRAINT ck_model_call_cost_basis "
        "CHECK (cost_basis IN ('measured', 'estimated'))"
    )
    _frozen_run_guard(with_revision=False)
    op.execute("DROP INDEX ix_audit_run_connection_revision")
    for table in ("provider_call_effect", "model_call"):
        op.execute(f"DROP INDEX ix_{table}_connection_revision")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT ck_{table}_basis_with_revision")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT ck_{table}_identity_basis")
        op.execute(f"ALTER TABLE {table} DROP COLUMN identity_basis")
    for table in ("provider_call_effect", "model_call", "audit_run"):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT ck_{table}_connection_revision_format")
        op.execute(f"ALTER TABLE {table} DROP COLUMN connection_revision_id")

    op.execute("DROP VIEW executor_route_current")
    for table in _TABLES:
        op.execute(f"DROP TABLE {table}")
