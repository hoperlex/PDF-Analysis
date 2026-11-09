"""The only writer and reader of the host tables (migration ``0062``, `HOSTS-BACKEND-01`, ADR-0028).

Statements only: the rules live in ``hosts.py`` (pure) and ``host_commands.py``. Every method takes the caller's session and never commits.
Every comparison with time uses the database clock (``clock_timestamp()``), so the ``api`` that serves an agent, the worker that
binds a run and a test that moves a pulse all agree on one clock.

What is written here, and what the database holds again:

* ``executor_host`` is inserted, archived once (write-once ``archived_at`` and ``archived_by``) and never deleted;
* ``executor_host_use_event`` and ``executor_host_slot_event`` are append-only and numbered without a gap per host by a trigger that
  takes its own advisory lock; the caller holds the host's row lock first (:meth:`HostRepository.get_host` with ``lock``), so the number
  read here is the number the trigger expects;
* ``executor_host_report`` is the latest snapshot (one row per host), replaced only by a report that changes it;
* ``executor_model_cooldown`` is one row per (host, provider, model), replaced by the next refusal and cleared by a changed report;
* the system connections of a host are ``executor_connection`` rows with ``system_managed``, ``host_id`` and ``capacity_pool`` set
  (``ck_executor_connection_pool``); their revisions are the ordinary immutable revisions.

**The pool's units** are one statement (:data:`POOL_UNITS`), copied word for word into the comparison call's mirror
(``comparison.spend.repository``) and held equal by ``tests/unit/comparison/spend``: a run holds one unit in each pool its cells are
bound in while its Job is active (``leased``, ``running``, ``retry_wait``), and an active comparison model call holds one in the pool
of its connection. :data:`POOL_SLOTS` is the number of units a pool has.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.hosts import HostReport
from auditmanager.shared.identity import (
    ExecutorConnectionId,
    ExecutorHostId,
    ExecutorHostSlotEventId,
    ExecutorHostUseEventId,
)

__all__ = [
    "ActiveTask",
    "HostRecord",
    "HostRepository",
    "POOL_SLOTS",
    "POOL_UNITS",
    "StoredReport",
    "SystemConnectionRow",
]

_HOST_COLUMNS: Final = "host_id, display_name, created_at, created_by, archived_at, archived_by"
_ACTIVE_RUN_JOB_STATES: Final = "('leased', 'running', 'retry_wait')"

#: The units in use of one pool: the active Runs bound in it (by cell, or by the revision a Run froze) and the active comparison model
#: calls of its connections, other than the Run ``:run_id`` (pass a value no Run has to count them all). Built from the few active
#: Jobs and never from the history of a pool's Runs (the shape ``jobs.repository._NEXT_JOB`` documents).
POOL_UNITS: Final = (
    "WITH active AS (SELECT j.run_id, r.connection_revision_id FROM job j JOIN audit_run r ON r.run_id = j.run_id "
    f"WHERE j.state IN {_ACTIVE_RUN_JOB_STATES} AND j.run_id <> :run_id) "
    "SELECT (SELECT count(*) FROM ("
    "SELECT a.run_id FROM active a JOIN audit_run_cell_binding b ON b.run_id = a.run_id "
    "JOIN executor_connection_revision rev ON rev.revision_id = b.connection_revision_id "
    "JOIN executor_connection c ON c.connection_id = rev.connection_id WHERE c.capacity_pool = :pool "
    "UNION "
    "SELECT a.run_id FROM active a JOIN executor_connection_revision rev ON rev.revision_id = a.connection_revision_id "
    "JOIN executor_connection c ON c.connection_id = rev.connection_id WHERE c.capacity_pool = :pool) units) "
    "+ (SELECT count(*) FROM comparison_model_call active_call "
    "JOIN comparison_work_attempt active_attempt "
    "ON active_attempt.comparison_work_attempt_id = active_call.comparison_work_attempt_id "
    "JOIN executor_connection_revision call_peer ON call_peer.revision_id = active_call.connection_revision_id "
    "JOIN executor_connection call_connection ON call_connection.connection_id = call_peer.connection_id "
    "WHERE call_connection.capacity_pool = :pool AND active_call.state IN ('prepared', 'sent') "
    "AND active_attempt.state IN ('created', 'leased', 'running')) AS units_in_use"
)


def pool_slots_sql(pool: str) -> str:
    """The SQL for the units a pool has, ``pool`` being a SQL expression for its text (``<host_id>:<provider>``): the latest slot event
    of the provider on the host, else the default of the access the host's current report gives the provider (2 for ``api``, 1 for a
    subscription and for a provider the report no longer names)."""
    host, provider = f"split_part({pool}, ':', 1)", f"split_part({pool}, ':', 2)"
    return (
        f"COALESCE((SELECT slot_event.slots FROM executor_host_slot_event slot_event WHERE slot_event.host_id = {host} "
        f"AND slot_event.provider = {provider} ORDER BY slot_event.event_no DESC LIMIT 1), "
        "(SELECT CASE reported.provider_item ->> 'access' WHEN 'api' THEN 2 ELSE 1 END "
        "FROM (SELECT jsonb_array_elements(host_report.providers) AS provider_item "
        f"FROM executor_host_report host_report WHERE host_report.host_id = {host}) reported "
        f"WHERE reported.provider_item ->> 'provider' = {provider} LIMIT 1), 1)"
    )


POOL_SLOTS: Final = "SELECT " + pool_slots_sql(":pool") + " AS slots"


@dataclass(frozen=True, slots=True)
class HostRecord:
    host_id: str
    display_name: str
    created_at: datetime
    created_by: str
    archived_at: datetime | None = None
    archived_by: str | None = None


@dataclass(frozen=True, slots=True)
class StoredReport:
    """The latest snapshot of a host and when it was written; ``pulse_age_seconds`` is not here (it is the token's)."""

    host_id: str
    token_id: str
    report: HostReport
    report_sha256: str
    reported_at: datetime


@dataclass(frozen=True, slots=True)
class SystemConnectionRow:
    """A system connection of a host with its current revision: what the system-object maintenance and the availability read."""

    connection_id: str
    host_id: str
    capacity_pool: str
    provider: str
    revision_id: str | None
    pin_id: str | None
    billing: str | None
    archived_at: datetime | None
    integration_authorised_at: datetime | None


@dataclass(frozen=True, slots=True)
class ActiveTask:
    """A call running on a host now."""

    task_id: str
    run_id: str
    provider: str
    model_id: str
    stage_key: str | None
    since: datetime


def _host(row: Mapping[str, Any]) -> HostRecord:
    return HostRecord(**{name: row[name] for name in (
        "host_id", "display_name", "created_at", "created_by", "archived_at", "archived_by")})


def _json(raw: Any) -> Any:
    return raw if isinstance(raw, (list, dict)) else json.loads(raw)


class HostRepository:
    """Stateless; every method takes the caller's session and never commits."""

    # -- the host ----------------------------------------------------------------------------------------

    def lock_name(self, session: Session, display_name: str) -> None:
        """Serialise two creations of one name (without regard to case) until the transaction ends."""
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {"key": f"executor_host_name:{display_name.lower()}"})

    def name_in_use(self, session: Session, display_name: str) -> bool:
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM executor_host WHERE lower(display_name) = lower(:name) AND archived_at IS NULL)"
        ), {"name": display_name}).scalar_one())

    def insert_host(self, session: Session, *, display_name: str, actor_uid: str) -> HostRecord:
        row = session.execute(text(
            f"INSERT INTO executor_host (host_id, display_name, created_by) VALUES (:id, :name, :actor) RETURNING {_HOST_COLUMNS}"
        ), {"id": str(ExecutorHostId.new()), "name": display_name, "actor": actor_uid}).mappings().one()
        return _host(row)

    def get_host(self, session: Session, host_id: str, *, lock: bool = False) -> HostRecord | None:
        row = session.execute(text(
            f"SELECT {_HOST_COLUMNS} FROM executor_host WHERE host_id = :id" + (" FOR UPDATE" if lock else "")
        ), {"id": host_id}).mappings().first()
        return None if row is None else _host(row)

    def list_hosts(self, session: Session, *, include_archived: bool = False, limit: int = 500) -> list[HostRecord]:
        rows = session.execute(text(
            f"SELECT {_HOST_COLUMNS} FROM executor_host "
            + ("" if include_archived else "WHERE archived_at IS NULL ")
            + "ORDER BY created_at DESC, host_id DESC LIMIT :limit"
        ), {"limit": limit}).mappings().all()
        return [_host(row) for row in rows]

    def archive_host(self, session: Session, host_id: str, *, actor_uid: str) -> HostRecord:
        row = session.execute(text(
            "UPDATE executor_host SET archived_at = clock_timestamp(), archived_by = :actor "
            f"WHERE host_id = :id AND archived_at IS NULL RETURNING {_HOST_COLUMNS}"
        ), {"id": host_id, "actor": actor_uid}).mappings().first()
        if row is None:
            found = self.get_host(session, host_id)
            assert found is not None
            return found
        return _host(row)

    # -- «Использовать» and the slots: append-only journals ------------------------------------------------

    def insert_use_event(self, session: Session, host_id: str, *, enabled: bool, actor_uid: str) -> int:
        """Append the host's next «Использовать» event and answer its number. The caller holds the host's row lock."""
        row = session.execute(text(
            "INSERT INTO executor_host_use_event (use_event_id, host_id, event_no, enabled, set_by) "
            "SELECT :id, :host, COALESCE(MAX(event_no), 0) + 1, :enabled, :actor FROM executor_host_use_event "
            "WHERE host_id = :host RETURNING event_no"
        ), {"id": str(ExecutorHostUseEventId.new()), "host": host_id, "enabled": enabled, "actor": actor_uid}).one()
        return int(row[0])

    def current_use(self, session: Session, host_ids: Sequence[str]) -> dict[str, tuple[bool, datetime, str]]:
        """``host_id -> (enabled, set_at, set_by)`` of the latest event; a host with no event is absent."""
        if not host_ids:
            return {}
        rows = session.execute(text(
            "SELECT DISTINCT ON (host_id) host_id, enabled, set_at, set_by FROM executor_host_use_event "
            "WHERE host_id = ANY(:ids) ORDER BY host_id, event_no DESC"
        ), {"ids": list(host_ids)}).all()
        return {str(row[0]): (bool(row[1]), row[2], str(row[3])) for row in rows}

    def insert_slot_event(
        self, session: Session, host_id: str, *, provider: str, slots: int, actor_uid: str
    ) -> int:
        row = session.execute(text(
            "INSERT INTO executor_host_slot_event (slot_event_id, host_id, event_no, provider, slots, set_by) "
            "SELECT :id, :host, COALESCE(MAX(event_no), 0) + 1, :provider, :slots, :actor FROM executor_host_slot_event "
            "WHERE host_id = :host RETURNING event_no"
        ), {"id": str(ExecutorHostSlotEventId.new()), "host": host_id, "provider": provider, "slots": slots,
            "actor": actor_uid}).one()
        return int(row[0])

    def slot_journal(self, session: Session, host_ids: Sequence[str]) -> dict[tuple[str, str], int]:
        """``(host_id, provider) -> slots`` of the latest slot event of each provider; a provider with no event is absent."""
        if not host_ids:
            return {}
        rows = session.execute(text(
            "SELECT DISTINCT ON (host_id, provider) host_id, provider, slots FROM executor_host_slot_event "
            "WHERE host_id = ANY(:ids) ORDER BY host_id, provider, event_no DESC"
        ), {"ids": list(host_ids)}).all()
        return {(str(row[0]), str(row[1])): int(row[2]) for row in rows}

    # -- the report snapshot --------------------------------------------------------------------------------

    def get_report(self, session: Session, host_id: str, *, lock: bool = False) -> StoredReport | None:
        row = session.execute(text(
            "SELECT host_id, token_id, agent_version, providers, slots, report_sha256, reported_at "
            "FROM executor_host_report WHERE host_id = :id" + (" FOR UPDATE" if lock else "")
        ), {"id": host_id}).mappings().first()
        return None if row is None else self._report(row)

    def get_reports(self, session: Session, host_ids: Sequence[str]) -> dict[str, StoredReport]:
        if not host_ids:
            return {}
        rows = session.execute(text(
            "SELECT host_id, token_id, agent_version, providers, slots, report_sha256, reported_at "
            "FROM executor_host_report WHERE host_id = ANY(:ids)"
        ), {"ids": list(host_ids)}).mappings().all()
        return {str(row["host_id"]): self._report(row) for row in rows}

    @staticmethod
    def _report(row: Mapping[str, Any]) -> StoredReport:
        return StoredReport(
            host_id=str(row["host_id"]), token_id=str(row["token_id"]),
            report=HostReport.from_stored(
                agent_version=str(row["agent_version"]), providers=_json(row["providers"]), slots=_json(row["slots"])),
            report_sha256=str(row["report_sha256"]), reported_at=row["reported_at"],
        )

    def write_report(
        self, session: Session, *, host_id: str, token_id: str, report: HostReport, report_sha256: str
    ) -> None:
        """Replace the host's snapshot with this report (the caller has found that it differs from the stored one)."""
        session.execute(text(
            "INSERT INTO executor_host_report (host_id, token_id, agent_version, providers, slots, report_sha256) "
            "VALUES (:host, :token, :version, CAST(:providers AS jsonb), CAST(:slots AS jsonb), :sha) "
            "ON CONFLICT (host_id) DO UPDATE SET token_id = EXCLUDED.token_id, agent_version = EXCLUDED.agent_version, "
            "providers = EXCLUDED.providers, slots = EXCLUDED.slots, report_sha256 = EXCLUDED.report_sha256, "
            "reported_at = clock_timestamp()"
        ), {"host": host_id, "token": token_id, "version": report.agent_version,
            "providers": json.dumps(report.providers_json(), separators=(",", ":")),
            "slots": json.dumps(dict(sorted(report.slots.items())), separators=(",", ":")), "sha": report_sha256})

    # -- the pulse ------------------------------------------------------------------------------------------

    def pulse_ages(self, session: Session, host_ids: Sequence[str]) -> dict[str, float]:
        """``host_id -> seconds since the latest sign of life`` of its usable tokens, by the database clock; a host whose token
        was never seen is absent (it never reported)."""
        if not host_ids:
            return {}
        rows = session.execute(text(
            "SELECT host_id, extract(epoch FROM (clock_timestamp() - max(last_seen_at))) FROM executor_runner_token "
            "WHERE host_id = ANY(:ids) AND revoked_at IS NULL AND expires_at > clock_timestamp() "
            "AND last_seen_at IS NOT NULL GROUP BY host_id"
        ), {"ids": list(host_ids)}).all()
        return {str(row[0]): float(row[1]) for row in rows}

    def usable_tokens(self, session: Session, host_id: str) -> list[str]:
        rows = session.execute(text(
            "SELECT token_id FROM executor_runner_token WHERE host_id = :h AND revoked_at IS NULL "
            "AND expires_at > clock_timestamp() ORDER BY created_at DESC, token_id DESC"
        ), {"h": host_id}).all()
        return [str(row[0]) for row in rows]

    def revoke_tokens_of(self, session: Session, host_id: str, *, actor_uid: str) -> list[str]:
        rows = session.execute(text(
            "UPDATE executor_runner_token SET revoked_at = clock_timestamp(), revoked_by = :actor "
            "WHERE host_id = :h AND revoked_at IS NULL RETURNING token_id"
        ), {"h": host_id, "actor": actor_uid}).all()
        return [str(row[0]) for row in rows]

    def revoke_pending_grants(self, session: Session, host_id: str, *, actor_uid: str) -> int:
        return int(session.execute(text(
            "UPDATE executor_enrollment SET revoked_at = clock_timestamp(), revoked_by = :actor "
            "WHERE host_id = :h AND redeemed_at IS NULL AND revoked_at IS NULL"
        ), {"h": host_id, "actor": actor_uid}).rowcount or 0)

    # -- the passive cooldown --------------------------------------------------------------------------------

    def set_cooldown(
        self, session: Session, *, host_id: str, provider: str, model_id: str, seconds: int, reason: str
    ) -> datetime:
        """One row per triple, replaced by the next refusal; answers ``until`` (database time)."""
        row = session.execute(text(
            "INSERT INTO executor_model_cooldown (host_id, provider, model_id, until, reason, set_at) "
            "VALUES (:host, :provider, :model, clock_timestamp() + make_interval(secs => :seconds), :reason, clock_timestamp()) "
            "ON CONFLICT (host_id, provider, model_id) DO UPDATE SET until = EXCLUDED.until, reason = EXCLUDED.reason, "
            "set_at = EXCLUDED.set_at RETURNING until"
        ), {"host": host_id, "provider": provider, "model": model_id, "seconds": seconds, "reason": reason}).one()
        return row[0]

    def cooldowns_of(self, session: Session, host_ids: Sequence[str]) -> dict[tuple[str, str, str], datetime]:
        """``(host_id, provider, model_id) -> until`` of the cooldowns still running by the database clock."""
        if not host_ids:
            return {}
        rows = session.execute(text(
            "SELECT host_id, provider, model_id, until FROM executor_model_cooldown "
            "WHERE host_id = ANY(:ids) AND until > clock_timestamp()"
        ), {"ids": list(host_ids)}).all()
        return {(str(row[0]), str(row[1]), str(row[2])): row[3] for row in rows}

    def clear_cooldowns(self, session: Session, host_id: str) -> int:
        """A changed report is the agent's own word on every model: the host's cooldowns end."""
        return int(session.execute(text(
            "DELETE FROM executor_model_cooldown WHERE host_id = :h"), {"h": host_id}).rowcount or 0)

    # -- system connections -----------------------------------------------------------------------------------

    def system_connections(self, session: Session, host_ids: Sequence[str]) -> list[SystemConnectionRow]:
        """Every system connection of the hosts with its current revision, archived ones included."""
        if not host_ids:
            return []
        rows = session.execute(text(
            "SELECT c.connection_id, c.host_id, c.capacity_pool, c.archived_at, c.integration_authorised_at, "
            "rev.revision_id, rev.pin_id, rev.billing FROM executor_connection c "
            "LEFT JOIN LATERAL (SELECT r.revision_id, r.pin_id, r.billing FROM executor_connection_revision r "
            "WHERE r.connection_id = c.connection_id ORDER BY r.revision_no DESC LIMIT 1) rev ON true "
            "WHERE c.system_managed AND c.host_id = ANY(:ids) ORDER BY c.created_at, c.connection_id"
        ), {"ids": list(host_ids)}).mappings().all()
        return [SystemConnectionRow(
            connection_id=str(row["connection_id"]), host_id=str(row["host_id"]), capacity_pool=str(row["capacity_pool"]),
            provider=str(row["capacity_pool"]).split(":", 1)[1], revision_id=row["revision_id"], pin_id=row["pin_id"],
            billing=row["billing"], archived_at=row["archived_at"],
            integration_authorised_at=row["integration_authorised_at"]) for row in rows]

    def insert_system_connection(
        self, session: Session, *, host_id: str, provider: str, display_name: str, actor_uid: str
    ) -> str:
        """A ``pull`` connection the stand keeps for one quadruple of a host (``ck_executor_connection_pool``)."""
        connection_id = str(ExecutorConnectionId.new())
        session.execute(text(
            "INSERT INTO executor_connection (connection_id, kind, display_name, created_by, system_managed, host_id, capacity_pool) "
            "VALUES (:id, 'pull', :name, :actor, true, :host, :pool)"
        ), {"id": connection_id, "name": display_name, "actor": actor_uid, "host": host_id,
            "pool": f"{host_id}:{provider}"})
        return connection_id

    def archive_system_connections(self, session: Session, host_id: str, *, actor_uid: str) -> list[str]:
        rows = session.execute(text(
            "UPDATE executor_connection SET archived_at = clock_timestamp(), archived_by = :actor "
            "WHERE host_id = :h AND system_managed AND archived_at IS NULL RETURNING connection_id"
        ), {"h": host_id, "actor": actor_uid}).all()
        return [str(row[0]) for row in rows]

    def set_integration_marks(
        self, session: Session, host_id: str, *, authorised: bool, actor_uid: str
    ) -> int:
        """Set or clear the integration mark of the host's live system connections («Использовать», ADR-0028 / ADR-0026 decision 8)."""
        if authorised:
            return int(session.execute(text(
                "UPDATE executor_connection SET integration_authorised_at = clock_timestamp(), integration_authorised_by = :actor "
                "WHERE host_id = :h AND system_managed AND archived_at IS NULL AND integration_authorised_at IS NULL"
            ), {"h": host_id, "actor": actor_uid}).rowcount or 0)
        return int(session.execute(text(
            "UPDATE executor_connection SET integration_authorised_at = NULL, integration_authorised_by = NULL "
            "WHERE host_id = :h AND system_managed AND archived_at IS NULL AND integration_authorised_at IS NOT NULL"
        ), {"h": host_id}).rowcount or 0)

    # -- the system groups -------------------------------------------------------------------------------------

    def system_group_for(self, session: Session, display_name: str) -> str | None:
        row = session.execute(text(
            "SELECT group_id FROM executor_group WHERE system_managed AND archived_at IS NULL AND display_name = :name"
        ), {"name": display_name}).first()
        return None if row is None else str(row[0])

    def insert_system_group(self, session: Session, *, display_name: str, actor_uid: str) -> str:
        from auditmanager.shared.identity import ExecutorGroupId

        group_id = str(ExecutorGroupId.new())
        session.execute(text(
            "INSERT INTO executor_group (group_id, display_name, created_by, system_managed) VALUES (:id, :name, :actor, true)"
        ), {"id": group_id, "name": display_name, "actor": actor_uid})
        return group_id

    def lock_group(self, session: Session, group_id: str) -> None:
        session.execute(text("SELECT 1 FROM executor_group WHERE group_id = :id FOR UPDATE"), {"id": group_id})

    def live_members_of_pair(
        self, session: Session, *, model_id: str, billing: str
    ) -> list[tuple[str, str]]:
        """``(connection_id, current revision id)`` of every live system connection of the pair (model, billing), oldest first."""
        rows = session.execute(text(
            "SELECT c.connection_id, rev.revision_id FROM executor_connection c "
            "JOIN LATERAL (SELECT r.revision_id, r.pin_id, r.billing FROM executor_connection_revision r "
            "WHERE r.connection_id = c.connection_id ORDER BY r.revision_no DESC LIMIT 1) rev ON true "
            "JOIN executor_host h ON h.host_id = c.host_id "
            "WHERE c.system_managed AND c.archived_at IS NULL AND h.archived_at IS NULL "
            "AND rev.pin_id = :model AND rev.billing = :billing ORDER BY c.created_at, c.connection_id"
        ), {"model": model_id, "billing": billing}).all()
        return [(str(row[0]), str(row[1])) for row in rows]

    def current_group_members(self, session: Session, group_id: str) -> list[tuple[str, str]] | None:
        """``(connection_id, connection_revision_id)`` of the group's current revision, or ``None`` when it has none."""
        row = session.execute(text(
            "SELECT group_revision_id FROM executor_group_revision WHERE group_id = :id ORDER BY revision_no DESC LIMIT 1"
        ), {"id": group_id}).first()
        if row is None:
            return None
        members = session.execute(text(
            "SELECT connection_id, connection_revision_id FROM executor_group_member WHERE group_revision_id = :rev "
            "ORDER BY connection_id"
        ), {"rev": row[0]}).all()
        return [(str(item[0]), str(item[1])) for item in members]

    # -- the pool ----------------------------------------------------------------------------------------------

    def lock_pool(self, session: Session, pool: str) -> None:
        """The pool's advisory lock to the end of the transaction: the lock every claim, hint, comparison call and cell binding of a
        pool takes (``jobs.repository._LOCK_POOL``; the same key as a system connection's ``_LOCK_CONNECTION``)."""
        session.execute(text(_LOCK_POOL), {"pool": pool})

    def pool_units(self, session: Session, pool: str, *, exclude_run_id: str = "") -> int:
        return int(session.execute(text(POOL_UNITS), {"pool": pool, "run_id": exclude_run_id}).scalar_one())

    def pool_slots(self, session: Session, pool: str) -> int:
        return int(session.execute(text(POOL_SLOTS), {"pool": pool}).scalar_one())

    def active_tasks(self, session: Session, host_id: str, *, limit: int = 64) -> list[ActiveTask]:
        rows = session.execute(text(
            "SELECT t.task_id, t.run_id, t.payload -> 'host' ->> 'provider' AS provider, t.expected_model, "
            "t.payload -> 'host' ->> 'cell_key' AS cell_key, t.first_claimed_at FROM executor_task t "
            "JOIN executor_connection c ON c.connection_id = t.connection_id "
            "WHERE c.host_id = :h AND t.state = 'claimed' AND t.run_id IS NOT NULL "
            "ORDER BY t.first_claimed_at, t.task_id LIMIT :limit"
        ), {"h": host_id, "limit": limit}).mappings().all()
        return [ActiveTask(
            task_id=str(row["task_id"]), run_id=str(row["run_id"]), provider=str(row["provider"] or ""),
            model_id=str(row["expected_model"]),
            stage_key=None if row["cell_key"] is None else str(row["cell_key"]).split(":", 1)[0],
            since=row["first_claimed_at"]) for row in rows]


#: The statement behind :meth:`HostRepository.lock_pool`, shared in spelling with ``jobs.repository._LOCK_POOL`` and
#: ``comparison.spend.repository._LOCK_POOL`` (a test holds the three equal, and equal in key to a system connection's lock).
_LOCK_POOL: Final = (
    "SELECT pg_advisory_xact_lock(hashtextextended('auditmanager.executor_connection|' || :pool, 0))"
)
