"""The only writer and reader of ``executor_agent_install`` (migration ``0046``, `EXEC2-ENROLL-01`), and of
the one ``executor_secret`` row an install session keeps.

Statements only: the rules live in ``agent_install.py`` (the API's half: a session is created in ``requested``,
read, and has its host key confirmed) and in ``agent_install_runner.py`` (the worker's half, `EXEC2-ENROLL-SSH-01`:
it takes a ``requested`` session, records the host key it observed, and ends the session). The table's triggers
pin what neither may move (``trg_executor_agent_install_frozen_guard`` and ``_write_once``).

**The worker's statements move a session one step and say whether they did.** Each one names the state it moves
the session *from* in its ``WHERE``, so a session the API's lazy sweep (``expire_overdue_installs``) has already
ended is left as the sweep wrote it, and a second worker that reads the same row changes nothing.

**The sealed key is the session's current secret.** It is stored as any ``executor_secret`` is -- current, until
replaced -- and a new install session of the connection replaces the previous one's key
(``ux_executor_secret_current`` allows one current secret per connection and purpose), exactly as
``set_secret`` replaces an ``api_key``. It is not listed among the connection's secrets: the connection's
reads take only :data:`~auditmanager.executors.model.GENERIC_PURPOSES` (``ExecutorRepository.current_secrets``).
The session names it by ``key_secret_id`` and the worker opens it from there (``public.open_secret``, with the
destination :func:`~auditmanager.executors.agent_install.install_destination`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.identity import ExecutorAgentInstallId

__all__ = ["AgentInstallRepository", "InstallRecord", "STALE_SCAN_SECONDS", "UNFINISHED_STATES"]

#: The states of a session that has not ended (``ux_executor_agent_install_open`` allows one per connection).
UNFINISHED_STATES: Final[tuple[str, ...]] = ("requested", "scanning", "awaiting_host_key", "installing")
#: How long a session may stay ``scanning`` before another worker scans it again (`EXEC2-ENROLL-SSH-01`).
STALE_SCAN_SECONDS: Final[int] = 120

_COLUMNS: Final = (
    "i.install_id, i.connection_id, i.host_id, i.state, i.access, i.ssh_host, i.ssh_port, i.ssh_user, "
    "i.key_secret_id, s.public_material AS public_key, i.observed_host_key, "
    "i.confirmed_host_key_fingerprint, i.host_key_confirmed_at, i.host_key_confirmed_by, "
    "i.package_version, i.package_sha256, i.failure_reason, i.key_removed_at, i.created_at, "
    "i.created_by, i.updated_at, i.finished_at"
)
_FROM: Final = (
    "FROM executor_agent_install i LEFT JOIN executor_secret s ON s.secret_id = i.key_secret_id"
)


@dataclass(frozen=True, slots=True)
class InstallRecord:
    """One install session. The sealed key is not here, only its identity and, for a generated key, its
    public half."""

    install_id: str
    #: Exactly one of ``connection_id`` and ``host_id`` is set (`HOSTS-SEAL-1`, ``ck_executor_agent_install_target``; the host's is ``host_id``,
    #: below, last with a default so a record written for a connection reads as it always did).
    connection_id: str | None
    state: str
    access: str
    ssh_host: str
    ssh_port: int
    ssh_user: str
    key_secret_id: str | None
    public_key: str | None
    observed_host_key: str | None
    confirmed_host_key_fingerprint: str | None
    host_key_confirmed_at: datetime | None
    host_key_confirmed_by: str | None
    package_version: str | None
    package_sha256: str | None
    failure_reason: str | None
    key_removed_at: datetime | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    finished_at: datetime | None
    host_id: str | None = None


def _record(row: Mapping[str, Any]) -> InstallRecord:
    return InstallRecord(**{name: row[name] for name in InstallRecord.__slots__})


class AgentInstallRepository:
    """Stateless; every method takes the caller's session and never commits."""

    def unfinished_install(self, session: Session, connection_id: str) -> str | None:
        """The identity of the connection's session that has not ended, if there is one."""
        row = session.execute(text(
            "SELECT install_id FROM executor_agent_install WHERE connection_id = :c "
            "AND state IN ('requested', 'scanning', 'awaiting_host_key', 'installing') LIMIT 1"
        ), {"c": connection_id}).first()
        return None if row is None else str(row[0])

    def unfinished_install_of_host(self, session: Session, host_id: str) -> str | None:
        """The identity of the host's session that has not ended, if there is one (one per host: ``ux_executor_agent_install_open_host``)."""
        row = session.execute(text(
            "SELECT install_id FROM executor_agent_install WHERE host_id = :h "
            "AND state IN ('requested', 'scanning', 'awaiting_host_key', 'installing') LIMIT 1"
        ), {"h": host_id}).first()
        return None if row is None else str(row[0])

    def insert_key(
        self, session: Session, *, secret_id: str, connection_id: str | None = None, kid: str,
        destination: str, ciphertext: bytes, public_material: str | None, actor_uid: str,
        host_id: str | None = None,
    ) -> None:
        """Store the session's sealed key as the owner's current ``agent_install_key``, replacing the
        previous one. The owner is a connection or -- `HOSTS-BACKEND-01`, a host install, ``executor_secret.host_id`` -- a host;
        the caller holds its row lock, so there is exactly one current."""
        if (connection_id is None) == (host_id is None):
            raise ValueError("a secret names exactly one of a connection and a host")
        session.execute(text(
            "UPDATE executor_secret SET replaced_at = clock_timestamp() "
            "WHERE connection_id IS NOT DISTINCT FROM :c AND host_id IS NOT DISTINCT FROM :h "
            "AND purpose = 'agent_install_key' AND replaced_at IS NULL"
        ), {"c": connection_id, "h": host_id})
        session.execute(text(
            "INSERT INTO executor_secret (secret_id, connection_id, host_id, purpose, kid, destination, "
            "ciphertext, last4, public_material, set_by) VALUES (:id, :c, :h, 'agent_install_key', :kid, "
            ":dest, :cipher, '', :public, :actor)"
        ), {"id": secret_id, "c": connection_id, "h": host_id, "kid": kid, "dest": destination,
            "cipher": ciphertext, "public": public_material, "actor": actor_uid})

    def insert_install(
        self, session: Session, *, install_id: ExecutorAgentInstallId | str, connection_id: str | None = None,
        access: str, ssh_host: str, ssh_port: int, ssh_user: str, key_secret_id: str,
        package_version: str, package_sha256: str, actor_uid: str, host_id: str | None = None,
    ) -> InstallRecord:
        if (connection_id is None) == (host_id is None):
            raise ValueError("an install session names exactly one of a connection and a host")
        session.execute(text(
            "INSERT INTO executor_agent_install (install_id, connection_id, host_id, access, ssh_host, "
            "ssh_port, ssh_user, key_secret_id, package_version, package_sha256, created_by) "
            "VALUES (:id, :c, :h, :access, :host, :port, :user, :secret, :version, :sha, :actor)"
        ), {"id": str(install_id), "c": connection_id, "h": host_id, "access": access, "host": ssh_host,
            "port": ssh_port, "user": ssh_user, "secret": key_secret_id,
            "version": package_version, "sha": package_sha256, "actor": actor_uid})
        found = self.get_install(session, str(install_id))
        assert found is not None
        return found

    def get_install(
        self, session: Session, install_id: str, *, lock: bool = False
    ) -> InstallRecord | None:
        row = session.execute(text(
            f"SELECT {_COLUMNS} {_FROM} WHERE i.install_id = :id"
            + (" FOR UPDATE OF i" if lock else "")
        ), {"id": install_id}).mappings().first()
        return None if row is None else _record(row)

    def confirm_host_key(
        self, session: Session, install_id: str, *, fingerprint: str, actor_uid: str
    ) -> bool:
        """Record the confirmation and move ``awaiting_host_key`` to ``installing``; ``False`` when the
        session was not awaiting it (nothing changed)."""
        return bool(session.execute(text(
            "UPDATE executor_agent_install SET state = 'installing', "
            "confirmed_host_key_fingerprint = :fingerprint, "
            "host_key_confirmed_at = clock_timestamp(), host_key_confirmed_by = :actor, "
            "updated_at = clock_timestamp() WHERE install_id = :id "
            "AND state = 'awaiting_host_key' AND confirmed_host_key_fingerprint IS NULL"
        ), {"id": install_id, "fingerprint": fingerprint, "actor": actor_uid}).rowcount)

    # -- the worker's half (`EXEC2-ENROLL-SSH-01`) ---------------------------------------------

    def claim_requested(
        self, session: Session, *, seconds: int, stale_scan_seconds: int = STALE_SCAN_SECONDS
    ) -> InstallRecord | None:
        """Take the oldest session that needs a scan for this worker: ``requested -> scanning`` in one statement,
        skipping a row another worker has locked, so two workers never scan one session at once. ``scanning`` is
        the durable claim: it is stored, and a restart of the worker loses nothing.

        A session that is ``scanning`` with no key stored for more than ``stale_scan_seconds`` -- a scan takes at
        most a few tens of seconds, so its worker is gone -- is taken again (a scan only reads a public key; a
        second one is harmless, and the first writer of the write-once key wins). A session already older than
        ``seconds`` (the session's lifetime) is not taken: the API's sweep ends it. The clock is the database's."""
        row = session.execute(text(
            "UPDATE executor_agent_install SET state = 'scanning', updated_at = clock_timestamp() "
            "WHERE install_id = (SELECT install_id FROM executor_agent_install "
            "WHERE created_at > clock_timestamp() - make_interval(secs => :seconds) "
            "AND (state = 'requested' OR (state = 'scanning' AND observed_host_key IS NULL "
            "AND updated_at < clock_timestamp() - make_interval(secs => :stale))) "
            "ORDER BY created_at, install_id FOR UPDATE SKIP LOCKED LIMIT 1) "
            "AND state IN ('requested', 'scanning') RETURNING install_id"
        ), {"seconds": seconds, "stale": stale_scan_seconds}).first()
        return None if row is None else self.get_install(session, str(row[0]))

    def installing(self, session: Session, *, seconds: int, limit: int) -> list[InstallRecord]:
        """The sessions whose host key the administrator confirmed and that are younger than ``seconds``,
        oldest first. **Nothing is locked and nothing is claimed here**: ``installing`` has no second state, so
        which of them is already being installed is not in this table -- the claim of an install is the
        enrollment grant that the worker issues for it (``agent_install_runner``)."""
        rows = session.execute(text(
            f"SELECT {_COLUMNS} {_FROM} WHERE i.state = 'installing' "
            "AND i.created_at > clock_timestamp() - make_interval(secs => :seconds) "
            "ORDER BY i.created_at, i.install_id LIMIT :limit"
        ), {"seconds": seconds, "limit": limit}).mappings().all()
        return [_record(row) for row in rows]

    def record_observed_host_key(self, session: Session, install_id: str, *, host_key: str) -> bool:
        """Store the host key the worker saw and move ``scanning`` to ``awaiting_host_key``. The column is
        write-once, so a key can never be replaced after the administrator has read its fingerprint. ``False``
        when the session was no longer ``scanning`` (the sweep ended it)."""
        return bool(session.execute(text(
            "UPDATE executor_agent_install SET state = 'awaiting_host_key', observed_host_key = :key, "
            "updated_at = clock_timestamp() WHERE install_id = :id AND state = 'scanning' "
            "AND observed_host_key IS NULL"
        ), {"id": install_id, "key": host_key}).rowcount)

    def finish_install(
        self, session: Session, *, install_id: str, connection_id: str | None = None, from_state: str, state: str,
        reason: str | None, host_id: str | None = None,
    ) -> bool:
        """End the session -- ``succeeded`` (``reason`` is ``None``) or ``failed`` (a reason from
        ``ExecutorAgentInstallFailure``) -- drop its reference to the key and replace the connection's current
        ``agent_install_key``. ``False`` (nothing changed) when the session was no longer in ``from_state``.

        What the table demands is met in one statement: ``failed`` carries a reason and ``succeeded`` none
        (``ck_..._failure_shape``), both a ``finished_at`` (``ck_..._finished_shape``; write-once, still NULL
        here), and an absent ``key_secret_id`` a ``key_removed_at`` (``ck_..._key_removed_shape``). The sealed
        ciphertext itself is a frozen column of ``executor_secret``: the key is *replaced* (never opened again,
        because nothing names it), exactly as an expired session's is."""
        ended = session.execute(text(
            "UPDATE executor_agent_install SET state = :state, failure_reason = :reason, "
            "key_secret_id = NULL, key_removed_at = COALESCE(key_removed_at, clock_timestamp()), "
            "finished_at = clock_timestamp(), updated_at = clock_timestamp() "
            "WHERE install_id = :id AND state = :from_state"
        ), {"id": install_id, "from_state": from_state, "state": state, "reason": reason}).rowcount
        if not ended:
            return False
        session.execute(text(
            "UPDATE executor_secret SET replaced_at = clock_timestamp() "
            "WHERE connection_id IS NOT DISTINCT FROM :c AND host_id IS NOT DISTINCT FROM :h "
            "AND purpose = 'agent_install_key' AND replaced_at IS NULL"
        ), {"c": connection_id, "h": host_id})
        return True
