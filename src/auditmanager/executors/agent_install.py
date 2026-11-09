"""The API side of path A: an install session of the universal agent over SSH (`EXEC2-ENROLL-01`,
ADR-0026 decision 7, owner ruling `R-149b`).

An administrator gives the stand SSH access to a host -- a key the stand generates, whose public half the
administrator adds to the host, or a private key pasted here and sealed; **never a password** -- and a
session is recorded. What this module does, and what it leaves to the worker:

========================  ==================================================================================
this module (``api``)     :func:`create_agent_install` records the session in ``requested`` with the sealed
                          key and the package it will install; :func:`get_agent_install` reads it;
                          :func:`confirm_agent_install_host_key` records that the administrator read the
                          host-key fingerprint the worker observed, and moves ``awaiting_host_key`` to
                          ``installing``.
`EXEC2-ENROLL-SSH-01`     the worker (``agent_install_runner.py``) scans the host (``requested -> scanning
(``worker``)              -> awaiting_host_key``), runs the fixed install script with the package on stdin
                          and ``sudo -n`` once the fingerprint is confirmed, removes the stand's key line,
                          replaces the sealed key and ends the session (``succeeded`` or ``failed`` with a
                          sanitised reason). Only the worker opens a secret.
========================  ==================================================================================

A session stays visibly ``requested`` until a worker takes it; nothing here pretends otherwise.

**A session ends.** Nothing but the worker advances a session, and a worker can be down or can die half way, so a
session would stay unfinished for ever, block every later create with ``install_in_progress`` (one unfinished
session per connection) and keep a pasted key sealed indefinitely. A session therefore has a bounded life,
:data:`INSTALL_SESSION_SECONDS` from its creation. An unfinished session older than that is **finished as
``failed``** -- ``no_worker`` when it is still ``requested`` (nobody took it), ``timed_out`` in any other
unfinished state (somebody did, and went silent) -- and its key is replaced and its reference removed, so no
``agent_install_key`` stays current. This is done lazily and idempotently, in the transaction that is already
open, by :func:`create_agent_install` (for that connection, before the conflict check) and by
:func:`get_agent_install` (for that session); it needs no scheduler. The worker's own late write finds the
session finished and changes nothing, as for a probe.

Safety by construction
----------------------
* **No command text comes from the caller.** The host, port and user are validated as plain values -- a
  host name or address that starts with a letter, a digit or ``[``, a user name of the portable set -- so
  neither can become an option of ``ssh`` (``-oProxyCommand=...``). The script is the worker's.
* **No trust on first use.** The confirmation carries the fingerprint by value, and it must equal the one
  the worker observed; a different one is ``conflict`` / ``host_key_changed``.
* **A key is sealed, never returned.** It is sealed to the stand's public ring under associated data that
  binds it to the session's host, port and user (:func:`install_destination`), so the sealed bytes open for
  that endpoint and no other. A generated key returns its public half and the ``authorized_keys`` line
  (:func:`authorized_keys_line`) -- public by nature; a pasted key returns nothing.
* **The idempotency fingerprint holds no key material**: the connection, the access, the host, the port and
  the user. A repeat of the key answers the first session, as ``set_secret`` does for the same reason.

Nothing here puts a key, a fingerprint or a host output in an event, a log line or an error detail.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.agent_install_repository import (
    UNFINISHED_STATES,
    AgentInstallRepository,
    InstallRecord,
)
from auditmanager.executors.agent_package import AgentPackage, latest_package
from auditmanager.executors.model import (
    AGENT_INSTALL_ACCESSES,
    CONFLICT_HOST_KEY_CHANGED,
    CONFLICT_INSTALL_IN_PROGRESS,
    CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
    CONSTRAINT_KIND_NOT_PULL,
    CONSTRAINT_PRIVATE_KEY_NOT_ACCEPTED,
    CONSTRAINT_PRIVATE_KEY_REQUIRED,
    host_key_fingerprint,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PublicRing
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorAgentInstallId, ExecutorSecretId, IdempotencyKey

__all__ = [
    "FAILURE_NO_WORKER",
    "FAILURE_TIMED_OUT",
    "INSTALL_MARKER_PREFIX",
    "INSTALL_PURPOSE",
    "INSTALL_SESSION_SECONDS",
    "InstallLifetimeRepository",
    "OverdueInstall",
    "authorized_keys_line",
    "confirm_agent_install_host_key",
    "create_agent_install",
    "get_agent_install",
    "install_destination",
    "install_marker",
    "observed_fingerprint",
]

_AGGREGATE_CONNECTION: Final[str] = "ExecutorConnection"
_AGGREGATE_INSTALL: Final[str] = "ExecutorAgentInstall"
#: The ``executor_secret.purpose`` of a session's sealed key (``model.INSTALL_PURPOSES``).
INSTALL_PURPOSE: Final[str] = "agent_install_key"
#: How long an install session may stay unfinished, counted from its creation: 30 minutes. A longer one is
#: finished as ``failed`` (module docstring, "A session ends").
INSTALL_SESSION_SECONDS: Final[int] = 1800
#: The comment that names a session on the ``authorized_keys`` line of a generated key: how the worker finds
#: the line to remove when the install ends (`EXEC2-ENROLL-SSH-01`).
INSTALL_MARKER_PREFIX: Final[str] = "auditmanager-install:"
#: The two ``failure_reason`` values (``model.AGENT_INSTALL_FAILURES``) a session ends with when its time is
#: up: nobody took it, or somebody took it and went silent.
FAILURE_NO_WORKER: Final[str] = "no_worker"
FAILURE_TIMED_OUT: Final[str] = "timed_out"
#: What the contract's request allows is wider than what may reach a command line: a host, as the connection
#: settings validate one (``model.py``), and a user name of the portable set. Anything else is refused.
_HOST: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:.]{2,45}\]")
_USER: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
_FINGERPRINT: Final[re.Pattern[str]] = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")
_PRIVATE_KEY_LIMIT: Final[int] = 8192
Journal = Callable[..., None]


# -- values ---------------------------------------------------------------------------------


def install_destination(*, ssh_host: str, ssh_port: int, ssh_user: str) -> str:
    """The endpoint a session's sealed key is bound to: ``agent_install|user@host:port|``.

    The worker recomputes it from the session's frozen columns when it opens the key
    (``public.open_secret``); a key sealed for one endpoint opens for no other."""
    return f"agent_install|{ssh_user}@{ssh_host}:{ssh_port}|"


def install_marker(install_id: str) -> str:
    """The comment that names a session on its generated key's ``authorized_keys`` line: the last field of the
    line, and exactly what the worker matches when it removes the line."""
    return f"{INSTALL_MARKER_PREFIX}{install_id}"


def authorized_keys_line(public_key: str, install_id: str) -> str:
    """The line the administrator adds to the host's ``authorized_keys`` for a generated key.

    ``restrict`` turns off forwarding and a terminal; the comment (:func:`install_marker`) names the session,
    which is how the worker finds the line to remove when the install ends."""
    return f"restrict {public_key} {install_marker(install_id)}"


def observed_fingerprint(record: InstallRecord) -> str | None:
    """``SHA256:...`` of the host key the worker observed, derived from the stored line as the connection
    revisions derive theirs; ``None`` before the worker has observed one."""
    if record.observed_host_key is None:
        return None
    try:
        return host_key_fingerprint(record.observed_host_key)
    except DomainError:
        return None


# -- helpers ---------------------------------------------------------------------------------


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _conflict(reason: str, message: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message=message, conflict_reason=reason)


def _refused(field_name: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the agent install request is not acceptable",
        field=field_name, constraint=constraint,
    )


def _not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE_INSTALL)


def _check_target(ssh_host: str, ssh_port: int, ssh_user: str) -> None:
    if _HOST.fullmatch(ssh_host) is None:
        raise _refused("ssh_host", "format")
    if type(ssh_port) is not int or not 1 <= ssh_port <= 65535:
        raise _refused("ssh_port", "range")
    if _USER.fullmatch(ssh_user) is None:
        raise _refused("ssh_user", "format")


def _check_key_argument(access: str, private_key: str | None) -> None:
    """``pasted_key`` needs a key and ``generated_key`` takes none; a pasted value must look like an
    unencrypted private key (a password-protected one could never be used non-interactively)."""
    if access not in AGENT_INSTALL_ACCESSES:
        raise _refused("access", "enum")
    if access == "generated_key":
        if private_key is not None:
            raise _refused("private_key", CONSTRAINT_PRIVATE_KEY_NOT_ACCEPTED)
        return
    if private_key is None:
        raise _refused("private_key", CONSTRAINT_PRIVATE_KEY_REQUIRED)
    head = private_key.lstrip()[:200]
    if (len(private_key) > _PRIVATE_KEY_LIMIT or not head.startswith("-----BEGIN ")
            or "PRIVATE KEY-----" not in private_key or "ENCRYPTED" in head
            or "Proc-Type" in private_key):
        raise _refused("private_key", "format")


def _need_ring(ring: PublicRing | None) -> PublicRing:
    if ring is None:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="no public key is configured to seal secrets to",
            dependency="secrets_public_key_missing",
        )
    return ring


# -- the end of a session ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OverdueInstall:
    """An unfinished session whose time is up, as read under its row lock: the state it is in (which decides
    how it ends) and the key it still names."""

    install_id: str
    state: str
    key_secret_id: str | None


class InstallLifetimeRepository(AgentInstallRepository):
    """:class:`AgentInstallRepository` and the two statements of a session's end.

    They are kept beside the rule that uses them because the stage-1 review fix that added them was not
    granted ``agent_install_repository.py``. They belong in :class:`AgentInstallRepository`; moving them is a
    cut and paste, after which this class goes and the two defaults ``InstallLifetimeRepository()`` in
    :func:`create_agent_install` and :func:`get_agent_install` become ``AgentInstallRepository()``."""

    def overdue_installs(
        self, session: Session, *, connection_id: str | None = None, install_id: str | None = None,
        seconds: int = INSTALL_SESSION_SECONDS, host_id: str | None = None,
    ) -> list[OverdueInstall]:
        """The connection's (or, `HOSTS-BACKEND-01`, the host's) unfinished sessions (or just ``install_id``, when named) created at
        least ``seconds`` ago, **locked** so that the worker cannot move one between this read and the write that
        ends it. The clock is the database's."""
        rows = session.execute(text(
            "SELECT install_id, state, key_secret_id FROM executor_agent_install "
            "WHERE connection_id IS NOT DISTINCT FROM :c AND host_id IS NOT DISTINCT FROM :h AND state = ANY(:states) "
            "AND created_at <= clock_timestamp() - make_interval(secs => :seconds)"
            + ("" if install_id is None else " AND install_id = :id")
            + " ORDER BY created_at, install_id FOR UPDATE"
        ), {"c": connection_id, "h": host_id, "states": list(UNFINISHED_STATES), "seconds": seconds,
            **({} if install_id is None else {"id": install_id})}).all()
        return [OverdueInstall(install_id=str(row[0]), state=str(row[1]),
                               key_secret_id=None if row[2] is None else str(row[2])) for row in rows]

    def fail_install(
        self, session: Session, *, install_id: str, connection_id: str | None = None, from_state: str, reason: str,
        host_id: str | None = None,
    ) -> bool:
        """End the session as ``failed`` with ``reason``, drop its reference to the key and replace the
        connection's current ``agent_install_key``. ``False`` (nothing changed) when the session was no
        longer in ``from_state``.

        The shape the table demands is met in one statement: ``failed`` carries a reason
        (``ck_executor_agent_install_failure_shape``) and a ``finished_at``
        (``ck_..._finished_shape``, write-once and still NULL here), and an absent ``key_secret_id`` carries
        a ``key_removed_at`` (``ck_..._key_removed_shape``) -- kept as it is when the worker had already
        removed the key."""
        ended = session.execute(text(
            "UPDATE executor_agent_install SET state = 'failed', failure_reason = :reason, "
            "key_secret_id = NULL, key_removed_at = COALESCE(key_removed_at, clock_timestamp()), "
            "finished_at = clock_timestamp(), updated_at = clock_timestamp() "
            "WHERE install_id = :id AND state = :from_state"
        ), {"id": install_id, "from_state": from_state, "reason": reason}).rowcount
        if not ended:
            return False
        session.execute(text(
            "UPDATE executor_secret SET replaced_at = clock_timestamp() "
            "WHERE connection_id IS NOT DISTINCT FROM :c AND host_id IS NOT DISTINCT FROM :h "
            "AND purpose = 'agent_install_key' AND replaced_at IS NULL"
        ), {"c": connection_id, "h": host_id})
        return True


def expire_overdue_installs(
    session: Session, installs: InstallLifetimeRepository, *, connection_id: str | None = None,
    install_id: str | None = None, journal: Journal = append_execution_event, host_id: str | None = None,
) -> int:
    """Finish the connection's overdue sessions (or just ``install_id``) as ``failed`` and journal each.

    ``no_worker`` for a session still ``requested``, ``timed_out`` for one in any other unfinished state. The
    journal event, ``executor.agent_install_expired``, names the session, the connection, the key's identity
    and the two states and the reason (all controlled values): never the host, the user, a fingerprint or a
    key. Idempotent: once finished, a session is no longer overdue and nothing is written. The number of
    sessions it ended is returned."""
    ended = 0
    for overdue in installs.overdue_installs(
        session, connection_id=connection_id, host_id=host_id, install_id=install_id, seconds=INSTALL_SESSION_SECONDS,
    ):
        reason = FAILURE_NO_WORKER if overdue.state == "requested" else FAILURE_TIMED_OUT
        if not installs.fail_install(
            session, install_id=overdue.install_id, connection_id=connection_id, host_id=host_id,
            from_state=overdue.state, reason=reason,
        ):
            continue
        ended += 1
        journal(
            session, event_type="executor.agent_install_expired", aggregate_type=_AGGREGATE_INSTALL,
            aggregate_id=overdue.install_id,
            payload={**({"connection_id": connection_id} if connection_id is not None else {"host_id": host_id}),
                     "purpose": INSTALL_PURPOSE,
                     "from_state": overdue.state, "to_state": "failed", "reason": reason,
                     **({} if overdue.key_secret_id is None else {"secret_id": overdue.key_secret_id})},
        )
    return ended


# -- the three operations --------------------------------------------------------------------


def create_agent_install(
    session: Session, *, connection_id: str, access: str, ssh_host: str, ssh_port: int,
    ssh_user: str, private_key: str | None, ring: PublicRing | None, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, executors: ExecutorRepository | None = None,
    repository: InstallLifetimeRepository | None = None, commands: CommandRepository | None = None,
    package_source: Callable[[], AgentPackage] = latest_package,
    journal: Journal = append_execution_event,
) -> InstallRecord:
    """Record an install session in ``requested`` and return it.

    Refusals, all before anything is written: ``permission_denied``; ``validation_failed`` for a request that
    is not acceptable (the host, the port, the user, and ``private_key`` as the contract states);
    ``not_found``; ``conflict`` (``connection_archived``, ``no_revision``, ``install_in_progress``);
    ``validation_failed`` on ``kind`` (``kind_not_pull``); ``dependency_unavailable``
    (``secrets_public_key_missing``, ``agent_package``).

    Under the connection's row lock and **before** the ``install_in_progress`` check, the connection's session
    that has outlived :data:`INSTALL_SESSION_SECONDS` is finished as ``failed`` (module docstring, "A session
    ends"), so an abandoned session never blocks the next one for ever."""
    _admin(roles)
    store, installs, ledger = (
        executors or ExecutorRepository(), repository or InstallLifetimeRepository(),
        commands or CommandRepository(),
    )
    _check_key_argument(access, private_key)
    _check_target(ssh_host, ssh_port, ssh_user)
    claimed = ledger.begin(
        session, command_type="create_executor_agent_install",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "connection_id": connection_id, "access": access, "ssh_host": ssh_host,
            "ssh_port": ssh_port, "ssh_user": ssh_user}),
    )
    if isinstance(claimed, CommandReplay):
        found = installs.get_install(session, str(claimed.outcome["install_id"]))
        if found is None:
            raise _not_found()
        return found
    connection = store.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE_CONNECTION)
    if connection.archived_at is not None:
        raise _conflict("connection_archived", "the connection is archived")
    if connection.kind != "pull":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="only a pull connection takes an agent",
            field="kind", constraint=CONSTRAINT_KIND_NOT_PULL,
        )
    if store.current_revisions(session, [connection_id]).get(connection_id) is None:
        raise _conflict("no_revision", "the connection has no revision yet")
    expire_overdue_installs(session, installs, connection_id=connection_id, journal=journal)
    if installs.unfinished_install(session, connection_id) is not None:
        raise _conflict(CONFLICT_INSTALL_IN_PROGRESS, "an install of this connection has not finished")
    sealing = _need_ring(ring)
    package = package_source()

    install_id = ExecutorAgentInstallId.new()
    secret_id = str(ExecutorSecretId.new())
    public_material: str | None = None
    if access == "generated_key":
        generated = Ed25519PrivateKey.generate()
        public_material = generated.public_key().public_bytes(
            Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")
        plaintext = generated.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
    else:
        assert private_key is not None
        plaintext = private_key.encode("utf-8")
    destination = install_destination(ssh_host=ssh_host, ssh_port=ssh_port, ssh_user=ssh_user)
    kid, envelope = sealing.seal(plaintext, {
        "secret_id": secret_id, "connection_id": connection_id, "purpose": INSTALL_PURPOSE,
        "destination": destination,
    })
    installs.insert_key(
        session, secret_id=secret_id, connection_id=connection_id, kid=kid,
        destination=destination, ciphertext=envelope, public_material=public_material,
        actor_uid=actor_uid)
    record = installs.insert_install(
        session, install_id=install_id, connection_id=connection_id, access=access,
        ssh_host=ssh_host, ssh_port=ssh_port, ssh_user=ssh_user, key_secret_id=secret_id,
        package_version=package.version, package_sha256=package.sha256, actor_uid=actor_uid)
    journal(
        session, event_type="executor.agent_install_requested", aggregate_type=_AGGREGATE_INSTALL,
        aggregate_id=record.install_id,
        payload={"connection_id": connection_id, "secret_id": secret_id, "purpose": INSTALL_PURPOSE,
                 "state": record.state, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"install_id": record.install_id})
    return record


def get_agent_install(
    session: Session, *, connection_id: str, install_id: str,
    repository: InstallLifetimeRepository | None = None, journal: Journal = append_execution_event,
) -> InstallRecord:
    """The session, or ``not_found`` for an unknown one and for one that is another connection's.

    A session that has outlived :data:`INSTALL_SESSION_SECONDS` is finished as ``failed`` first, in this
    transaction, and the answer is the session as it then stands (module docstring, "A session ends"). This
    is a write on a read: the caller must commit it, or the next create does it again (it is idempotent)."""
    installs = repository or InstallLifetimeRepository()
    found = installs.get_install(session, install_id)
    if found is None or found.connection_id != connection_id:
        raise _not_found()
    if found.state in UNFINISHED_STATES and expire_overdue_installs(
        session, installs, connection_id=connection_id, install_id=install_id, journal=journal,
    ):
        found = installs.get_install(session, install_id)
        assert found is not None
    return found


def confirm_agent_install_host_key(
    session: Session, *, connection_id: str, install_id: str, fingerprint: str,
    roles: Iterable[str], idempotency_key: str, actor_uid: str,
    repository: AgentInstallRepository | None = None, commands: CommandRepository | None = None,
    journal: Journal = append_execution_event,
) -> InstallRecord:
    """Record that the administrator read exactly the fingerprint the worker observed.

    Answers, in order: ``permission_denied``; ``not_found``; the session as it stands when this fingerprint
    was already confirmed (an identical repeat); ``conflict`` / ``host_key_changed`` for another fingerprint
    than the confirmed one, or than the observed one; ``conflict`` / ``install_not_awaiting_host_key`` for a
    session that has no observed key to confirm yet or has ended; otherwise the confirmation, which moves
    the session to ``installing`` for the worker."""
    _admin(roles)
    installs, ledger = repository or AgentInstallRepository(), commands or CommandRepository()
    if _FINGERPRINT.fullmatch(fingerprint) is None:
        raise _refused("host_key_fingerprint", "pattern")
    claimed = ledger.begin(
        session, command_type="confirm_executor_agent_install_host_key",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "connection_id": connection_id, "install_id": install_id,
            "host_key_fingerprint": fingerprint}),
    )
    found = installs.get_install(session, install_id, lock=True)
    if found is None or found.connection_id != connection_id:
        raise _not_found()
    if isinstance(claimed, CommandReplay):
        return found
    if found.confirmed_host_key_fingerprint is not None:
        if found.confirmed_host_key_fingerprint != fingerprint:
            raise _conflict(CONFLICT_HOST_KEY_CHANGED, "the fingerprint is not the one confirmed")
        ledger.succeed(session, claimed.command_id, {"install_id": install_id})
        return found
    if found.state != "awaiting_host_key":
        raise _conflict(CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
                        "the install is not waiting for a host key to be confirmed")
    if observed_fingerprint(found) != fingerprint:
        raise _conflict(CONFLICT_HOST_KEY_CHANGED, "the fingerprint is not the one observed")
    if not installs.confirm_host_key(
        session, install_id, fingerprint=fingerprint, actor_uid=actor_uid
    ):
        raise _conflict(CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
                        "the install is not waiting for a host key to be confirmed")
    confirmed = installs.get_install(session, install_id)
    assert confirmed is not None
    journal(
        session, event_type="executor.agent_install_host_key_confirmed",
        aggregate_type=_AGGREGATE_INSTALL, aggregate_id=install_id,
        payload={"connection_id": connection_id, "state": confirmed.state, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"install_id": install_id})
    return confirmed
