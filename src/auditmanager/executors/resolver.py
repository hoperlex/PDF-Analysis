"""From a route to an adapter: freeze at run start, bind per Attempt (plan sections 2, 3 and 6).

`EXEC-HTTP-01` (`R-143`). Two moments, kept apart on purpose:

**Freeze -- at run start.** :func:`freeze_connection` resolves the ``text_analysis`` route to one
*revision* and the run keeps its identity for the rest of its life. The primary is used when its
current revision is served and has an ``ok`` probe on its current key; only then, and only when an
administrator configured one, the standby. A standby is never a silent fallback: the caller
journals the use (:attr:`FrozenConnection.reason` says why), and a failure in the middle of a run
never switches connections. With neither usable the start is refused,
``dependency_unavailable`` with ``dependency: executor_route_missing``. Nothing falls back to
``provider.env``.

**Bind -- per Attempt.** :func:`bind_connection` reads the frozen revision (an archived one still
serves the run that froze it), opens the connection's *current* key **for the destination
recomputed from that revision** and asks the kind's factory for the adapter. A rotated key is
therefore picked up by the next Attempt, and a key that no longer opens for the revision's address
is ``secret_unreadable``, never a call.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from auditmanager.executors.destinations import DestinationPolicy
from auditmanager.executors.kinds import KindRuntime, adapter_for
from auditmanager.executors.model import (
    IDENTITY_BASIS_BY_KIND,
    ConnectionRecord,
    RevisionRecord,
    destination_for,
)
from auditmanager.executors.public import SecretUnreadableError, open_secret
from auditmanager.executors.queries import resolve_route
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PrivateRing
from auditmanager.executors.usability import current_secret, is_probed_ok, is_served
from auditmanager.jobs.public import AttemptContext
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "BoundConnection",
    "FrozenConnection",
    "bind_connection",
    "freeze_connection",
]


def route_missing() -> DomainError:
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="no usable executor connection is routed",
        dependency="executor_route_missing",
    )


@dataclass(frozen=True, slots=True)
class FrozenConnection:
    """The revision a run starts on, and the route it was chosen from."""

    revision_id: str
    connection_id: str
    pin_id: str
    work_kind: str
    primary_connection_id: str
    standby_connection_id: str | None
    #: ``None`` when the primary served; else why the standby did.
    reason: str | None = None

    @property
    def used_standby(self) -> bool:
        return self.reason is not None


@dataclass(frozen=True, slots=True)
class BoundConnection:
    adapter: object
    revision: RevisionRecord
    connection: ConnectionRecord
    #: ``reported`` for a kind whose answer names its model, ``declared`` for one that asserts it.
    identity_basis: str
    #: Recorded as the call row's ``provider``.
    provider_label: str


def _why_unusable(
    session: Session, store: ExecutorRepository, revision: RevisionRecord | None
) -> str | None:
    """``None`` when the side serves; else a controlled reason."""
    if revision is None:
        return "primary_archived"
    connection = store.get_connection(session, revision.connection_id)
    if connection is None or connection.archived_at is not None:
        return "primary_archived"
    if not is_served(connection, revision):
        return "primary_kind_not_served"
    if not is_probed_ok(session, store, connection, revision):
        return "primary_not_probed"
    return None


def freeze_connection(
    session: Session, work_kind: str, *, repository: ExecutorRepository | None = None,
) -> FrozenConnection:
    store = repository or ExecutorRepository()
    route = resolve_route(session, work_kind, store)
    if route is None:
        raise route_missing()
    reason = _why_unusable(session, store, route.primary)
    if reason is None:
        assert route.primary is not None
        chosen, why = route.primary, None
    else:
        if route.standby is None or _why_unusable(session, store, route.standby) is not None:
            raise route_missing()
        chosen, why = route.standby, reason
    return FrozenConnection(
        revision_id=chosen.revision_id, connection_id=chosen.connection_id,
        pin_id=chosen.settings.pin_id, work_kind=work_kind,
        primary_connection_id=route.route.primary_connection_id,
        standby_connection_id=route.route.standby_connection_id, reason=why,
    )


def bind_connection(
    session: Session, revision_id: str, *, ring: PrivateRing | None,
    policy: DestinationPolicy, context: AttemptContext | None,
    repository: ExecutorRepository | None = None, runtime: KindRuntime | None = None,
) -> BoundConnection:
    """The adapter of a frozen revision for this Attempt. Raises :class:`SecretUnreadableError`
    when the key cannot be opened for the revision's address, and ``dependency_unavailable``
    (``executor_route_missing``) when the revision or its kind's factory is gone.

    A **channel kind** (``pull``) has no key to open: its adapter is built from ``runtime`` (the
    worker's database access) and the Attempt's context, and the remote party calls the stand."""
    store = repository or ExecutorRepository()
    revision = store.get_revision(session, revision_id)
    connection = None if revision is None else store.get_connection(session, revision.connection_id)
    if revision is None or connection is None:
        raise route_missing()
    entry = adapter_for(connection.kind)
    if entry is None or not entry.serves(revision):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="this kind of connection is not served yet",
            field="kind", constraint="kind_not_served",
        )
    if entry.channel is not None:
        if runtime is None:
            raise route_missing()
        return BoundConnection(
            adapter=entry.channel(revision, context, runtime), revision=revision,
            connection=connection, identity_basis=IDENTITY_BASIS_BY_KIND[connection.kind],
            provider_label=entry.provider_label(revision),
        )
    assert entry.purpose is not None  # only a channel kind has none, and it returned above
    secret = current_secret(session, store, connection)
    if secret is None:
        raise SecretUnreadableError()
    value = open_secret(
        session, ring, secret_id=secret.secret_id,
        destination=destination_for(connection.kind, revision.settings, entry.purpose),
        repository=store,
    )
    return BoundConnection(
        adapter=entry.factory(revision, value, policy, context), revision=revision,
        connection=connection, identity_basis=IDENTITY_BASIS_BY_KIND[connection.kind],
        provider_label=entry.provider_label(revision),
    )
