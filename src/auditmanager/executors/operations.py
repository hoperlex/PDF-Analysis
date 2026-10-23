"""The operator's commands: ``import-env``, ``rewrap`` and ``reach`` (plan section 6, `EXEC-HTTP-01`).

All three run **on the worker**, from its image and its environment, because they need what only the
worker holds: the private key ring, and the network path real calls take. None of them prints a key,
a header or an address; their output is identities, counts and outcome words.

``import_env``
    turns today's ``PROXY_LLM_*`` into the first connection, with its sealed key and a
    ``text_analysis`` route. It is **idempotent**: a second run changes nothing and names the existing
    connection. Because only a revision with an ``ok`` probe on its current key can be routed, it
    runs the probe itself, over this worker's network path, and routes only on ``ok``. A refused
    probe leaves the connection in place and un-routed, and says which outcome it was.
``rewrap``
    re-seals every current secret whose key id is not the active one, by inserting new rows
    (``executor_secret`` is immutable). Each new row keeps its destination, so the key still
    opens only for the address it was entered for. The latest ``ok`` probe of the old row is
    carried over to the new one as a recorded probe, so a rotation of the master key does not make
    every connection "unprobed" and stop run start.
``reach``
    says whether this container may send a key to an address and can open a TCP connection to
    it: the destination rule, the resolution and the connect, in that order.
"""

from __future__ import annotations

import socket
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import pinned_models
from auditmanager.executors.destinations import (
    DestinationPolicy,
    DestinationRefused,
    DestinationUnresolvable,
    normalise_target,
)
from auditmanager.executors.identity import is_placeholder
from auditmanager.executors.model import RevisionSettings
from auditmanager.executors.probe_runner import ProbeRunner
from auditmanager.executors.public import (
    create_connection,
    request_probe,
    revise_connection,
    set_route,
    set_secret,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PrivateRing, SecretUnreadable, associated_data
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import ExecutorSecretId

__all__ = [
    "IMPORT_DISPLAY_NAME",
    "SYSTEM_ACTOR_UID",
    "ImportReport",
    "ReachReport",
    "RewrapReport",
    "import_env",
    "reach",
    "rewrap",
]

#: The display name that marks the connection ``import-env`` made; its presence is what makes a
#: second run a no-op.
IMPORT_DISPLAY_NAME: Final[str] = "OpenRouter (из окружения)"
_LEGACY_IMPORT_DISPLAY_NAME: Final[str] = "Шлюз моделей (импорт из окружения)"
#: The actor of an operator command run from a shell: a well-formed ``usr`` identity that names no
#: account. ``--actor`` names a real administrator instead.
SYSTEM_ACTOR_UID: Final[str] = "usr_0000000000000000000000EXEC"
_ADMIN: Final[tuple[str, ...]] = ("admin",)
_DEFAULT_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190 s


class OperationRefused(Exception):
    """An operator command that cannot proceed; the message is safe to print."""


@dataclass(frozen=True, slots=True)
class ImportReport:
    connection_id: str
    created: bool
    probe_outcome: str | None
    routed: bool


@dataclass(frozen=True, slots=True)
class RewrapReport:
    rewrapped: int
    already_active: int
    unreadable: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReachReport:
    outcome: str
    category: str | None = None


# -- import-env ---------------------------------------------------------------------------------


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise OperationRefused(f"{name} is unset; there is nothing to import")
    return value


def import_env(
    session_factory: sessionmaker[Session], environ: Mapping[str, str], *,
    ring: PrivateRing | None, policy: DestinationPolicy, actor_uid: str = SYSTEM_ACTOR_UID,
    repository: ExecutorRepository | None = None, queue_only: bool = False,
) -> ImportReport:
    store = repository or ExecutorRepository()
    with session_factory() as session:
        existing = next((item for item in store.list_connections(session)
                         if item.display_name in (IMPORT_DISPLAY_NAME, _LEGACY_IMPORT_DISPLAY_NAME)
                         and item.archived_at is None), None)
        if existing is not None:
            routed = any(route.primary_connection_id == existing.connection_id
                         for route in store.current_routes(session))
            return ImportReport(existing.connection_id, False, None, routed)
        if queue_only:
            archived = next((item for item in store.list_connections(session)
                             if item.display_name in (IMPORT_DISPLAY_NAME,
                                                      _LEGACY_IMPORT_DISPLAY_NAME)), None)
            if archived is not None:
                # Archiving is an administrator's explicit decision. A worker restart may
                # not resurrect it through the old create command's idempotency key.
                return ImportReport(archived.connection_id, False, None, False)
    if ring is None:
        raise OperationRefused(
            "AUDITMANAGER_SECRETS_KEYS is unset; the worker's private ring seals and opens the key")
    base_url = _required(environ, "PROXY_LLM_BASE_URL")
    token = _required(environ, "PROXY_LLM_TOKEN")
    gateway_model = _required(environ, "PROXY_LLM_MODEL")
    if is_placeholder(gateway_model):
        raise OperationRefused(
            "PROXY_LLM_MODEL names no model (a gateway stub); set the explicit model the "
            "gateway reports, as R-133 requires, before importing")
    pins = {pin.model_id for pin in pinned_models()}
    pin_id = environ.get("AUDITMANAGER_MODEL_ID", "").strip() or next(iter(sorted(pins)))
    if pin_id not in pins:
        raise OperationRefused("AUDITMANAGER_MODEL_ID is not a pinned model")
    sealing = ring.public_ring()
    settings = RevisionSettings(
        pin_id=pin_id, gateway_model=gateway_model, billing="metered",
        allow_client_documents=False, timeout_seconds=_DEFAULT_TIMEOUT_SECONDS,
        api_flavour="openai_chat", base_url=base_url, transport="direct",
    )
    try:
        with session_factory() as session:
            connection = create_connection(
                session, kind="http_api", display_name=IMPORT_DISPLAY_NAME, roles=_ADMIN,
                idempotency_key="import-env:connection", actor_uid=actor_uid,
            )
            revise_connection(
                session, connection_id=connection.connection_id, settings=settings,
                pinned_model_ids=pins, roles=_ADMIN, idempotency_key="import-env:revision",
                actor_uid=actor_uid,
            )
            set_secret(
                session, connection_id=connection.connection_id, purpose="api_key", value=token,
                ring=sealing, roles=_ADMIN, idempotency_key="import-env:secret",
                actor_uid=actor_uid,
            )
            probe = request_probe(
                session, connection_id=connection.connection_id, roles=_ADMIN,
                idempotency_key="import-env:probe", actor_uid=actor_uid,
            )
            session.commit()
    except DomainError as refusal:
        raise OperationRefused(f"the connection could not be created ({refusal.code.value})") from None
    if queue_only:
        # Worker startup only registers the option. Its normal probe loop will verify the
        # current revision and key; an administrator alone changes the route.
        return ImportReport(connection.connection_id, True, None, False)
    # The probe runs here, on this worker's own network path, exactly as the worker's loop would.
    ProbeRunner(session_factory, ring=ring, policy=policy, repository=store).run_pending()
    with session_factory() as session:
        finished = store.get_probe(session, probe.probe_id)
        outcome = None if finished is None else finished.outcome
        routed = False
        if outcome == "ok":
            set_route(
                session, work_kind="text_analysis",
                primary_connection_id=connection.connection_id, standby_connection_id=None,
                roles=_ADMIN, idempotency_key="import-env:route", actor_uid=actor_uid,
            )
            session.commit()
            routed = True
    return ImportReport(connection.connection_id, True, outcome, routed)


# -- rewrap -------------------------------------------------------------------------------------


def rewrap(
    session_factory: sessionmaker[Session], *, ring: PrivateRing | None,
    actor_uid: str = SYSTEM_ACTOR_UID, repository: ExecutorRepository | None = None,
) -> RewrapReport:
    """Re-seal every current secret not sealed to the active key id."""
    store = repository or ExecutorRepository()
    if ring is None or ring.active_kid is None:
        raise OperationRefused(
            "AUDITMANAGER_SECRETS_KEYS and AUDITMANAGER_SECRETS_ACTIVE_KID must both be set")
    sealing = ring.public_ring()
    rewrapped = already = 0
    unreadable: list[str] = []
    with session_factory() as listing:
        connections = [item.connection_id for item in store.list_connections(listing, limit=10_000)]
    for connection_id in connections:
        with session_factory() as session:
            connection = store.get_connection(session, connection_id, lock=True)
            if connection is None:
                continue
            for secret in store.current_secrets(session, [connection_id]).get(connection_id, []):
                if secret.kid == sealing.active_kid:
                    already += 1
                    continue
                sealed = store.sealed_secret(session, secret.secret_id)
                try:
                    if sealed is None:
                        raise SecretUnreadable()
                    plain = ring.open(secret.kid, sealed[3], associated_data(
                        secret_id=secret.secret_id, connection_id=connection_id,
                        purpose=secret.purpose, kid=secret.kid, destination=secret.destination,
                    ))
                except SecretUnreadable:
                    unreadable.append(secret.secret_id)
                    continue
                new_id = str(ExecutorSecretId.new())
                kid, envelope = sealing.seal(plain, {
                    "secret_id": new_id, "connection_id": connection_id,
                    "purpose": secret.purpose, "destination": secret.destination,
                })
                replacement = store.replace_secret(
                    session, secret_id=new_id, connection_id=connection_id,
                    purpose=secret.purpose, kid=kid, destination=secret.destination,
                    ciphertext=envelope, last4=secret.last4,
                    public_material=secret.public_material, actor_uid=actor_uid,
                )
                _carry_probe_over(session, store, secret.secret_id, replacement.secret_id,
                                  connection_id, actor_uid)
                append_execution_event(
                    session, event_type="executor.secret_rewrapped", aggregate_type="ExecutorConnection",
                    aggregate_id=connection_id,
                    payload={"connection_id": connection_id, "secret_id": replacement.secret_id,
                             "purpose": secret.purpose, "actor_uid": actor_uid},
                )
                rewrapped += 1
            session.commit()
    return RewrapReport(rewrapped, already, tuple(unreadable))


def _carry_probe_over(
    session: Session, store: ExecutorRepository, old_secret_id: str, new_secret_id: str,
    connection_id: str, actor_uid: str,
) -> None:
    """The same key under a new envelope is the same key: the latest ``ok`` probe of the current
    revision on the old secret is recorded again on the new one, so the connection stays usable."""
    revisions = store.current_revisions(session, [connection_id])
    revision = revisions.get(connection_id)
    if revision is None:
        return
    earlier = store.latest_finished_probe(session, revision.revision_id, old_secret_id)
    if earlier is None or earlier.outcome != "ok":
        return
    carried = store.insert_probe(
        session, connection_id=connection_id, revision_id=revision.revision_id,
        secret_id=new_secret_id, actor_uid=actor_uid,
    )
    store.finish_probe(
        session, carried.probe_id, outcome="ok", reported_model=earlier.reported_model,
        identity_basis=earlier.identity_basis, latency_ms=earlier.latency_ms,
        http_status=earlier.http_status, rate_check=earlier.rate_check, observed_host_key=None,
        detail="carried over by a rewrap of the same key",
    )


# -- reach --------------------------------------------------------------------------------------


def reach(
    url: str, *, transport: str, policy: DestinationPolicy, timeout: float = 5.0,
) -> ReachReport:
    """Whether this container may send a key to ``url`` and can open a TCP connection to it."""
    host, port = normalise_target(url)
    try:
        addresses = policy.check(host, port, transport=transport)
    except DestinationRefused as refused:
        return ReachReport("refused", refused.category)
    except DestinationUnresolvable:
        return ReachReport("unresolvable")
    for address in addresses:
        target = policy.dial(address, port)
        try:
            socket.create_connection(target, timeout=timeout).close()
            return ReachReport("reachable")
        except OSError:
            continue
    return ReachReport("unreachable")
