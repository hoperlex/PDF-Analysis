"""The only writer and reader of the ``executor_*`` tables (migration ``0030``).

Statements only: no rule lives here (``model.py`` and ``commands.py`` own them), and no secret
is ever returned except through :meth:`ExecutorRepository.sealed_secret`, which hands the
ciphertext to the one caller that may open it (``public.open_secret``, the worker).

Every writer that numbers something (a connection's revisions, a kind of work's routes) takes a
lock first, so two administrators cannot take the same number; the unique keys in the schema
are the backstop.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.model import (
    PROBE_RUNNING_MARGIN_SECONDS,
    PROBE_UNTAKEN_SECONDS,
    PULL_PROBE_WINDOW_SECONDS,
    ConnectionRecord,
    ProbeRecord,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
    SecretRecord,
)
from auditmanager.shared.identity import (
    ExecutorConnectionId,
    ExecutorConnectionRevisionId,
    ExecutorProbeId,
    ExecutorRouteEventId,
)

__all__ = ["ExecutorRepository"]

_CONNECTION_COLUMNS: Final = (
    "connection_id, kind, display_name, created_at, created_by, archived_at, archived_by"
)
_REVISION_COLUMNS: Final = (
    "revision_id, connection_id, revision_no, created_at, created_by, pin_id, gateway_model, "
    "billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport, "
    "max_parallel_calls, ssh_host, ssh_port, ssh_user, host_key, ssh_profile, pull_client, "
    "answer_deadline_seconds, max_claimed_tasks"
)
_SECRET_COLUMNS: Final = (
    "secret_id, connection_id, purpose, kid, destination, last4, public_material, set_at, "
    "set_by, replaced_at"
)
_PROBE_COLUMNS: Final = (
    "probe_id, connection_id, revision_id, secret_id, state, outcome, reported_model, "
    "identity_basis, latency_ms, http_status, rate_check, observed_host_key, detail, "
    "requested_at, requested_by, started_at, finished_at"
)
_ROUTE_COLUMNS: Final = (
    "route_event_id, work_kind, route_no, primary_connection_id, standby_connection_id, "
    "set_at, set_by"
)
_SETTING_NAMES: Final = (
    "pin_id", "gateway_model", "billing", "allow_client_documents", "timeout_seconds",
    "api_flavour", "base_url", "transport", "max_parallel_calls", "ssh_host", "ssh_port",
    "ssh_user", "host_key", "ssh_profile", "pull_client", "answer_deadline_seconds",
    "max_claimed_tasks",
)

_INTEGER_SETTINGS: Final = frozenset((
    "timeout_seconds", "max_parallel_calls", "ssh_port", "answer_deadline_seconds",
    "max_claimed_tasks",
))

def _typed_parameter(name: str) -> str:
    """A cast for each setting, so a NULL in an ``INSERT ... SELECT`` has a type."""
    if name in _INTEGER_SETTINGS:
        return f"CAST(:{name} AS integer)"
    if name == "allow_client_documents":
        return f"CAST(:{name} AS boolean)"
    return f"CAST(:{name} AS text)"


#: A probe row may be listed for a connection at most this many times.
PROBE_HISTORY: Final[int] = 10


def _connection(row: Mapping[str, Any]) -> ConnectionRecord:
    return ConnectionRecord(**{name: row[name] for name in (
        "connection_id", "kind", "display_name", "created_at", "created_by", "archived_at",
        "archived_by")})


def _revision(row: Mapping[str, Any]) -> RevisionRecord:
    return RevisionRecord(
        revision_id=row["revision_id"], connection_id=row["connection_id"],
        revision_no=row["revision_no"], created_at=row["created_at"],
        created_by=row["created_by"],
        settings=RevisionSettings(**{name: row[name] for name in _SETTING_NAMES}),
    )


def _secret(row: Mapping[str, Any]) -> SecretRecord:
    return SecretRecord(**{name: row[name] for name in (
        "secret_id", "connection_id", "purpose", "kid", "destination", "last4",
        "public_material", "set_at", "set_by", "replaced_at")})


def _probe(row: Mapping[str, Any]) -> ProbeRecord:
    return ProbeRecord(**{name: row[name] for name in (
        "probe_id", "connection_id", "revision_id", "secret_id", "state", "outcome",
        "reported_model", "identity_basis", "latency_ms", "http_status", "rate_check",
        "observed_host_key", "detail", "requested_at", "requested_by", "started_at",
        "finished_at")})


def _route(row: Mapping[str, Any]) -> RouteRecord:
    return RouteRecord(**{name: row[name] for name in (
        "route_event_id", "work_kind", "route_no", "primary_connection_id",
        "standby_connection_id", "set_at", "set_by")})


class ExecutorRepository:
    """Stateless; every method takes the caller's session and never commits."""

    # -- connections -----------------------------------------------------------------------

    def insert_connection(
        self, session: Session, *, kind: str, display_name: str, actor_uid: str
    ) -> ConnectionRecord:
        row = session.execute(text(
            "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
            f"VALUES (:id, :kind, :name, :actor) RETURNING {_CONNECTION_COLUMNS}"
        ), {"id": str(ExecutorConnectionId.new()), "kind": kind, "name": display_name,
            "actor": actor_uid}).mappings().one()
        return _connection(row)

    def get_connection(
        self, session: Session, connection_id: str, *, lock: bool = False
    ) -> ConnectionRecord | None:
        row = session.execute(text(
            f"SELECT {_CONNECTION_COLUMNS} FROM executor_connection WHERE connection_id = :id"
            + (" FOR UPDATE" if lock else "")
        ), {"id": connection_id}).mappings().first()
        return None if row is None else _connection(row)

    def list_connections(self, session: Session, *, limit: int = 500) -> list[ConnectionRecord]:
        rows = session.execute(text(
            f"SELECT {_CONNECTION_COLUMNS} FROM executor_connection "
            "ORDER BY archived_at IS NOT NULL, created_at DESC, connection_id DESC LIMIT :limit"
        ), {"limit": limit}).mappings().all()
        return [_connection(row) for row in rows]

    def archive_connection(
        self, session: Session, connection_id: str, *, actor_uid: str
    ) -> ConnectionRecord:
        row = session.execute(text(
            "UPDATE executor_connection SET archived_at = clock_timestamp(), "
            "archived_by = :actor WHERE connection_id = :id AND archived_at IS NULL "
            f"RETURNING {_CONNECTION_COLUMNS}"
        ), {"id": connection_id, "actor": actor_uid}).mappings().one()
        return _connection(row)

    # -- revisions -------------------------------------------------------------------------

    def insert_revision(
        self, session: Session, connection_id: str, settings: RevisionSettings, *,
        actor_uid: str,
    ) -> RevisionRecord:
        """Number the next revision. The caller holds the connection's row lock."""
        columns = ", ".join(_SETTING_NAMES)
        values = ", ".join(_typed_parameter(name) for name in _SETTING_NAMES)
        row = session.execute(text(
            "INSERT INTO executor_connection_revision "
            f"(revision_id, connection_id, revision_no, created_by, {columns}) "
            "SELECT :revision_id, :connection_id, COALESCE(MAX(revision_no), 0) + 1, "
            f":actor, {values} FROM executor_connection_revision WHERE connection_id = :connection_id "
            f"RETURNING {_REVISION_COLUMNS}"
        ), {"revision_id": str(ExecutorConnectionRevisionId.new()),
            "connection_id": connection_id, "actor": actor_uid,
            **{name: getattr(settings, name) for name in _SETTING_NAMES}}).mappings().one()
        return _revision(row)

    def list_revisions(self, session: Session, connection_id: str) -> list[RevisionRecord]:
        rows = session.execute(text(
            f"SELECT {_REVISION_COLUMNS} FROM executor_connection_revision "
            "WHERE connection_id = :id ORDER BY revision_no DESC"
        ), {"id": connection_id}).mappings().all()
        return [_revision(row) for row in rows]

    def get_revision(self, session: Session, revision_id: str) -> RevisionRecord | None:
        row = session.execute(text(
            f"SELECT {_REVISION_COLUMNS} FROM executor_connection_revision "
            "WHERE revision_id = :id"
        ), {"id": revision_id}).mappings().first()
        return None if row is None else _revision(row)

    def current_revisions(
        self, session: Session, connection_ids: Sequence[str]
    ) -> dict[str, RevisionRecord]:
        """The highest-numbered revision of each connection that has one."""
        if not connection_ids:
            return {}
        rows = session.execute(text(
            f"SELECT DISTINCT ON (connection_id) {_REVISION_COLUMNS} "
            "FROM executor_connection_revision WHERE connection_id = ANY(:ids) "
            "ORDER BY connection_id, revision_no DESC"
        ), {"ids": list(connection_ids)}).mappings().all()
        return {row["connection_id"]: _revision(row) for row in rows}

    # -- secrets ---------------------------------------------------------------------------

    def replace_secret(
        self, session: Session, *, secret_id: str, connection_id: str, purpose: str, kid: str,
        destination: str, ciphertext: bytes, last4: str, public_material: str | None,
        actor_uid: str,
    ) -> SecretRecord:
        """Mark the connection's current secret of this purpose replaced and insert the new
        row. The caller holds the connection's row lock, so there is exactly one current."""
        session.execute(text(
            "UPDATE executor_secret SET replaced_at = clock_timestamp() "
            "WHERE connection_id = :c AND purpose = :p AND replaced_at IS NULL"
        ), {"c": connection_id, "p": purpose})
        row = session.execute(text(
            "INSERT INTO executor_secret (secret_id, connection_id, purpose, kid, destination, "
            "ciphertext, last4, public_material, set_by) VALUES (:id, :c, :p, :kid, :dest, "
            f":cipher, :last4, :public, :actor) RETURNING {_SECRET_COLUMNS}"
        ), {"id": secret_id, "c": connection_id, "p": purpose, "kid": kid, "dest": destination,
            "cipher": ciphertext, "last4": last4, "public": public_material,
            "actor": actor_uid}).mappings().one()
        return _secret(row)

    def current_secrets(
        self, session: Session, connection_ids: Sequence[str]
    ) -> dict[str, list[SecretRecord]]:
        if not connection_ids:
            return {}
        rows = session.execute(text(
            f"SELECT {_SECRET_COLUMNS} FROM executor_secret "
            "WHERE connection_id = ANY(:ids) AND replaced_at IS NULL "
            "ORDER BY connection_id, purpose"
        ), {"ids": list(connection_ids)}).mappings().all()
        found: dict[str, list[SecretRecord]] = {}
        for row in rows:
            found.setdefault(row["connection_id"], []).append(_secret(row))
        return found

    def get_secret(self, session: Session, secret_id: str) -> SecretRecord | None:
        row = session.execute(text(
            f"SELECT {_SECRET_COLUMNS} FROM executor_secret WHERE secret_id = :id"
        ), {"id": secret_id}).mappings().first()
        return None if row is None else _secret(row)

    def sealed_secret(
        self, session: Session, secret_id: str
    ) -> tuple[str, str, str, bytes] | None:
        """``(connection_id, purpose, kid, ciphertext)`` for the worker's ``open_secret`` only."""
        row = session.execute(text(
            "SELECT connection_id, purpose, kid, ciphertext FROM executor_secret "
            "WHERE secret_id = :id"
        ), {"id": secret_id}).first()
        if row is None:
            return None
        return row[0], row[1], row[2], bytes(row[3])

    # -- probes ----------------------------------------------------------------------------

    def insert_probe(
        self, session: Session, *, connection_id: str, revision_id: str, secret_id: str | None,
        actor_uid: str,
    ) -> ProbeRecord:
        row = session.execute(text(
            "INSERT INTO executor_probe (probe_id, connection_id, revision_id, secret_id, "
            f"state, requested_by) VALUES (:id, :c, :r, :s, 'requested', :actor) "
            f"RETURNING {_PROBE_COLUMNS}"
        ), {"id": str(ExecutorProbeId.new()), "c": connection_id, "r": revision_id,
            "s": secret_id, "actor": actor_uid}).mappings().one()
        return _probe(row)

    def get_probe(self, session: Session, probe_id: str) -> ProbeRecord | None:
        row = session.execute(text(
            f"SELECT {_PROBE_COLUMNS} FROM executor_probe WHERE probe_id = :id"
        ), {"id": probe_id}).mappings().first()
        return None if row is None else _probe(row)

    def list_probes(
        self, session: Session, connection_id: str, *, limit: int = PROBE_HISTORY
    ) -> list[ProbeRecord]:
        rows = session.execute(text(
            f"SELECT {_PROBE_COLUMNS} FROM executor_probe WHERE connection_id = :id "
            "ORDER BY requested_at DESC, probe_id DESC LIMIT :limit"
        ), {"id": connection_id, "limit": limit}).mappings().all()
        return [_probe(row) for row in rows]

    def latest_probe_by_revision(
        self, session: Session, connection_id: str
    ) -> dict[str, ProbeRecord]:
        rows = session.execute(text(
            f"SELECT DISTINCT ON (revision_id) {_PROBE_COLUMNS} FROM executor_probe "
            "WHERE connection_id = :id ORDER BY revision_id, requested_at DESC, probe_id DESC"
        ), {"id": connection_id}).mappings().all()
        return {row["revision_id"]: _probe(row) for row in rows}

    def claim_requested_probe(self, session: Session) -> ProbeRecord | None:
        """Take the oldest ``requested`` probe for this worker: ``requested -> running`` in one
        statement, skipping rows another worker has locked, so two workers never run one probe."""
        row = session.execute(text(
            "UPDATE executor_probe SET state = 'running', started_at = clock_timestamp() "
            "WHERE probe_id = (SELECT probe_id FROM executor_probe WHERE state = 'requested' "
            "ORDER BY requested_at, probe_id FOR UPDATE SKIP LOCKED LIMIT 1) "
            f"RETURNING {_PROBE_COLUMNS}"
        )).mappings().first()
        return None if row is None else _probe(row)

    def latest_finished_probe(
        self, session: Session, revision_id: str, secret_id: str | None
    ) -> ProbeRecord | None:
        """The most recent *finished* probe of this revision on this secret (or on no secret)."""
        row = session.execute(text(
            f"SELECT {_PROBE_COLUMNS} FROM executor_probe WHERE revision_id = :r "
            "AND state = 'finished' AND secret_id IS NOT DISTINCT FROM CAST(:s AS text) "
            "ORDER BY finished_at DESC, probe_id DESC LIMIT 1"
        ), {"r": revision_id, "s": secret_id}).mappings().first()
        return None if row is None else _probe(row)

    def sweep_probes(self, session: Session) -> int:
        """End the probes nobody can still be running.

        A probe still ``requested`` (never ``running``) after 120 s becomes ``no_worker``: it
        fires in the ``api``'s request and read path, so it needs no worker to be up. A
        ``running`` probe whose worker vanished ends as ``timeout`` once its revision's timeout
        and a margin have passed. A worker's own late write then finds the row finished and
        changes nothing (:meth:`finish_probe`).
        """
        untaken = session.execute(text(
            "UPDATE executor_probe SET state = 'finished', outcome = 'no_worker', "
            "detail = 'no worker took the probe', finished_at = clock_timestamp() "
            "WHERE state = 'requested' "
            "AND requested_at < clock_timestamp() - make_interval(secs => :seconds)"
        ), {"seconds": PROBE_UNTAKEN_SECONDS}).rowcount or 0
        vanished = session.execute(text(
            "UPDATE executor_probe p SET state = 'finished', outcome = 'timeout', "
            "detail = 'the worker did not finish the probe', finished_at = clock_timestamp() "
            "FROM executor_connection_revision r JOIN executor_connection c "
            "ON c.connection_id = r.connection_id WHERE p.revision_id = r.revision_id "
            "AND p.state = 'running' AND p.started_at < clock_timestamp() "
            "- make_interval(secs => GREATEST(r.timeout_seconds, "
            "CASE WHEN c.kind = 'pull' THEN CAST(:pull_window AS integer) ELSE 0 END) + :margin)"
        ), {"margin": PROBE_RUNNING_MARGIN_SECONDS,
            "pull_window": PULL_PROBE_WINDOW_SECONDS}).rowcount or 0
        return int(untaken) + int(vanished)

    def start_probe(self, session: Session, probe_id: str) -> bool:
        """``requested -> running``; ``False`` when it was no longer ``requested``."""
        return bool(session.execute(text(
            "UPDATE executor_probe SET state = 'running', started_at = clock_timestamp() "
            "WHERE probe_id = :id AND state = 'requested'"
        ), {"id": probe_id}).rowcount)

    def finish_probe(
        self, session: Session, probe_id: str, *, outcome: str, reported_model: str | None,
        identity_basis: str | None, latency_ms: int | None, http_status: int | None,
        rate_check: str | None, observed_host_key: str | None, detail: str | None,
    ) -> bool:
        """``requested`` or ``running`` ``-> finished``; ``False`` when it already finished."""
        return bool(session.execute(text(
            "UPDATE executor_probe SET state = 'finished', outcome = :outcome, "
            "reported_model = :model, identity_basis = :basis, latency_ms = :latency, "
            "http_status = :status, rate_check = :rate, observed_host_key = :host_key, "
            "detail = :detail, finished_at = clock_timestamp() "
            "WHERE probe_id = :id AND state IN ('requested', 'running')"
        ), {"id": probe_id, "outcome": outcome, "model": reported_model,
            "basis": identity_basis, "latency": latency_ms, "status": http_status,
            "rate": rate_check, "host_key": observed_host_key, "detail": detail}).rowcount)

    # -- routes ----------------------------------------------------------------------------

    def lock_route(self, session: Session, work_kind: str) -> None:
        session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                        {"key": f"executor_route:{work_kind}"})

    def append_route(
        self, session: Session, *, work_kind: str, primary_connection_id: str,
        standby_connection_id: str | None, actor_uid: str,
    ) -> RouteRecord:
        row = session.execute(text(
            "INSERT INTO executor_route_event (route_event_id, work_kind, route_no, "
            "primary_connection_id, standby_connection_id, set_by) "
            "SELECT :id, :kind, COALESCE(MAX(route_no), 0) + 1, :primary, CAST(:standby AS text), :actor "
            f"FROM executor_route_event WHERE work_kind = :kind RETURNING {_ROUTE_COLUMNS}"
        ), {"id": str(ExecutorRouteEventId.new()), "kind": work_kind,
            "primary": primary_connection_id, "standby": standby_connection_id,
            "actor": actor_uid}).mappings().one()
        return _route(row)

    def get_route_event(self, session: Session, route_event_id: str) -> RouteRecord | None:
        row = session.execute(text(
            f"SELECT {_ROUTE_COLUMNS} FROM executor_route_event WHERE route_event_id = :id"
        ), {"id": route_event_id}).mappings().first()
        return None if row is None else _route(row)

    def current_routes(self, session: Session) -> list[RouteRecord]:
        rows = session.execute(text(
            f"SELECT {_ROUTE_COLUMNS} FROM executor_route_current ORDER BY work_kind"
        )).mappings().all()
        return [_route(row) for row in rows]

    def current_route(self, session: Session, work_kind: str) -> RouteRecord | None:
        row = session.execute(text(
            f"SELECT {_ROUTE_COLUMNS} FROM executor_route_current WHERE work_kind = :kind"
        ), {"kind": work_kind}).mappings().first()
        return None if row is None else _route(row)
