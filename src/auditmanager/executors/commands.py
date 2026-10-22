"""The administrator's commands on executor connections, following ``workers/commands.py``.

Each command: (1) the role check, (2) ``CommandRepository.begin`` with an idempotency key and a
payload fingerprint, (3) the mutation, (4) ``append_execution_event`` with identities and
controlled classifiers only, (5) ``ledger.succeed`` with the identities of what was made.
A replay answers the same resource as it stands now. The caller owns the transaction.

**No secret reaches the ledger, an event or a refusal.** ``set_secret``'s fingerprint is made
of the connection and the purpose only: a hash of the value would be an unkeyed digest of a
secret, which the plan refuses (section 4.1). The cost is the semantics of a repeat: the same
key replays the first answer even if the value differs, so the UI sends a fresh key for each
submission. The value is sealed and dropped; it is never stored, logged or echoed.

An unpinned model, a setting that does not fit the kind, a destination-less secret and the
rest are refused with the catalogue's existing codes and detail keys (``model.py``).
"""

from __future__ import annotations

import base64
from collections.abc import Collection, Iterable
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sqlalchemy.orm import Session

from auditmanager.executors.model import (
    SERVES,
    ConnectionRecord,
    ProbeRecord,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
    SecretRecord,
    destination_for,
    refuse_purpose,
    validate_settings,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PublicRing
from auditmanager.executors.usability import ensure_routable
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorSecretId, IdempotencyKey

__all__ = [
    "GeneratedKey",
    "archive_connection",
    "create_connection",
    "generate_ssh_key",
    "request_probe",
    "revise_connection",
    "set_route",
    "set_secret",
]

_AGGREGATE = "ExecutorConnection"
#: A secret whose last four characters are shown must be long enough that four are a small
#: part of it. A shorter value shows none.
_LAST4_MINIMUM_LENGTH = 16


@dataclass(frozen=True, slots=True)
class GeneratedKey:
    """The public half of a generated SSH key, and the sealed secret's metadata."""

    secret: SecretRecord
    public_key: str
    authorized_keys_line: str


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE)


def _conflict(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT, message="the connection is not in a state that allows this",
        conflict_reason=reason,
    )


def _need_ring(ring: PublicRing | None) -> PublicRing:
    if ring is None:
        raise DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="no public key is configured to seal secrets to",
            dependency="secrets_public_key_missing",
        )
    return ring


def _locked(
    session: Session, repository: ExecutorRepository, connection_id: str
) -> ConnectionRecord:
    connection = repository.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise _not_found()
    return connection


def _live(connection: ConnectionRecord) -> ConnectionRecord:
    if connection.archived_at is not None:
        raise _conflict("connection_archived")
    return connection


def _current(
    session: Session, repository: ExecutorRepository, connection_id: str
) -> RevisionRecord:
    revision = repository.current_revisions(session, [connection_id]).get(connection_id)
    if revision is None:
        raise _conflict("no_revision")
    return revision


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str,
    payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


def create_connection(
    session: Session, *, kind: str, display_name: str, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> ConnectionRecord:
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "create_executor_connection", idempotency_key,
                     {"kind": kind, "display_name": display_name})
    if isinstance(claimed, CommandReplay):
        found = store.get_connection(session, str(claimed.outcome["connection_id"]))
        if found is None:
            raise _not_found()
        return found
    connection = store.insert_connection(
        session, kind=kind, display_name=display_name, actor_uid=actor_uid
    )
    append_execution_event(
        session, event_type="executor.connection_created", aggregate_type=_AGGREGATE,
        aggregate_id=connection.connection_id,
        payload={"connection_id": connection.connection_id, "connection_kind": kind,
                 "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"connection_id": connection.connection_id})
    return connection


def revise_connection(
    session: Session, *, connection_id: str, settings: RevisionSettings,
    pinned_model_ids: Collection[str], roles: Iterable[str], idempotency_key: str,
    actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> RevisionRecord:
    """Add an immutable revision. The full settings, never a patch; a changed address leaves
    the connection's secrets unreadable for it until the key is entered again."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "revise_executor_connection", idempotency_key,
                     {"connection_id": connection_id,
                      "settings": {name: getattr(settings, name) for name in settings.__slots__}})
    if isinstance(claimed, CommandReplay):
        found = store.get_revision(session, str(claimed.outcome["revision_id"]))
        if found is None:
            raise _not_found()
        return found
    connection = _live(_locked(session, store, connection_id))
    checked = validate_settings(connection.kind, settings, pinned_model_ids=pinned_model_ids)
    revision = store.insert_revision(session, connection_id, checked, actor_uid=actor_uid)
    append_execution_event(
        session, event_type="executor.revision_added", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "revision_id": revision.revision_id,
                 "revision_no": revision.revision_no, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"revision_id": revision.revision_id})
    return revision


def archive_connection(
    session: Session, *, connection_id: str, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> ConnectionRecord:
    """Archive a connection no route names. Archiving is one-way; a route is changed first."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "archive_executor_connection", idempotency_key,
                     {"connection_id": connection_id})
    if isinstance(claimed, CommandReplay):
        found = store.get_connection(session, connection_id)
        if found is None:
            raise _not_found()
        return found
    connection = _live(_locked(session, store, connection_id))
    for route in store.current_routes(session):
        if connection_id in (route.primary_connection_id, route.standby_connection_id):
            raise _conflict("connection_routed")
    archived = store.archive_connection(session, connection.connection_id, actor_uid=actor_uid)
    append_execution_event(
        session, event_type="executor.connection_archived", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"connection_id": connection_id})
    return archived


def set_secret(
    session: Session, *, connection_id: str, purpose: str, value: str,
    ring: PublicRing | None, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    repository: ExecutorRepository | None = None, commands: CommandRepository | None = None,
) -> SecretRecord:
    """Seal ``value`` to the stand's public key, bound to the destination of the connection's
    current revision, and keep only the ciphertext. Write-only: the value is not returned."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "set_executor_secret", idempotency_key,
                     {"connection_id": connection_id, "purpose": purpose})
    if isinstance(claimed, CommandReplay):
        found = store.get_secret(session, str(claimed.outcome["secret_id"]))
        if found is None:
            raise _not_found()
        return found
    connection = _live(_locked(session, store, connection_id))
    refuse_purpose(connection.kind, purpose)
    sealing = _need_ring(ring)
    revision = _current(session, store, connection_id)
    destination = destination_for(connection.kind, revision.settings, purpose)
    secret_id = str(ExecutorSecretId.new())
    kid, envelope = sealing.seal(value.encode("utf-8"), {
        "secret_id": secret_id, "connection_id": connection_id, "purpose": purpose,
        "destination": destination,
    })
    last4 = value[-4:] if purpose == "api_key" and len(value) >= _LAST4_MINIMUM_LENGTH else ""
    secret = store.replace_secret(
        session, secret_id=secret_id, connection_id=connection_id, purpose=purpose, kid=kid,
        destination=destination, ciphertext=envelope, last4=last4, public_material=None,
        actor_uid=actor_uid,
    )
    append_execution_event(
        session, event_type="executor.secret_set", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "secret_id": secret_id, "purpose": purpose,
                 "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"secret_id": secret_id})
    return secret


def generate_ssh_key(
    session: Session, *, connection_id: str, ring: PublicRing | None, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> GeneratedKey:
    """Generate an ed25519 pair, seal the private half to the connection's SSH endpoint and
    keep the public half as the secret's public material. Only the public half is returned."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "generate_executor_ssh_key", idempotency_key,
                     {"connection_id": connection_id})
    if isinstance(claimed, CommandReplay):
        found = store.get_secret(session, str(claimed.outcome["secret_id"]))
        if found is None or found.public_material is None:
            raise _not_found()
        return _generated(found)
    connection = _live(_locked(session, store, connection_id))
    refuse_purpose(connection.kind, "ssh_private_key")
    sealing = _need_ring(ring)
    revision = _current(session, store, connection_id)
    destination = destination_for(connection.kind, revision.settings, "ssh_private_key")
    private = Ed25519PrivateKey.generate()
    public_line = private.public_key().public_bytes(
        Encoding.OpenSSH, PublicFormat.OpenSSH
    ).decode("ascii")
    secret_id = str(ExecutorSecretId.new())
    kid, envelope = sealing.seal(
        private.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()),
        {"secret_id": secret_id, "connection_id": connection_id, "purpose": "ssh_private_key",
         "destination": destination},
    )
    blob = base64.b64decode(public_line.split(" ", 2)[1])
    secret = store.replace_secret(
        session, secret_id=secret_id, connection_id=connection_id, purpose="ssh_private_key",
        kid=kid, destination=destination, ciphertext=envelope,
        last4=base64.b64encode(blob).decode("ascii")[-4:], public_material=public_line,
        actor_uid=actor_uid,
    )
    append_execution_event(
        session, event_type="executor.ssh_key_generated", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "secret_id": secret_id,
                 "purpose": "ssh_private_key", "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"secret_id": secret_id})
    return _generated(secret)


def _generated(secret: SecretRecord) -> GeneratedKey:
    assert secret.public_material is not None
    return GeneratedKey(
        secret=secret, public_key=secret.public_material,
        authorized_keys_line=f"restrict {secret.public_material} auditmanager:{secret.connection_id}",
    )


def request_probe(
    session: Session, *, connection_id: str, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> ProbeRecord:
    """Record a probe of the connection's current revision as ``requested``. The worker that
    executes it arrives in ``EXEC-HTTP-01``; until then the ``api``'s sweep ends it as
    ``no_worker`` after 120 seconds, whether or not any worker is up."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "request_executor_probe", idempotency_key,
                     {"connection_id": connection_id})
    store.sweep_probes(session)
    if isinstance(claimed, CommandReplay):
        found = store.get_probe(session, str(claimed.outcome["probe_id"]))
        if found is None:
            raise _not_found()
        return found
    connection = _live(_locked(session, store, connection_id))
    revision = _current(session, store, connection_id)
    secrets = {secret.purpose: secret for secret in
               store.current_secrets(session, [connection_id]).get(connection_id, [])}
    wanted = "api_key" if connection.kind == "http_api" else "ssh_private_key"
    secret = secrets.get(wanted)
    probe = store.insert_probe(
        session, connection_id=connection_id, revision_id=revision.revision_id,
        secret_id=None if secret is None else secret.secret_id, actor_uid=actor_uid,
    )
    append_execution_event(
        session, event_type="executor.probe_requested", aggregate_type=_AGGREGATE,
        aggregate_id=connection_id,
        payload={"connection_id": connection_id, "revision_id": revision.revision_id,
                 "probe_id": probe.probe_id, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"probe_id": probe.probe_id})
    return probe


def set_route(
    session: Session, *, work_kind: str, primary_connection_id: str,
    standby_connection_id: str | None, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, repository: ExecutorRepository | None = None,
    commands: CommandRepository | None = None,
) -> RouteRecord:
    """Name the connection that serves a kind of model work, with an optional standby that
    only an administrator configures. Every change is an appended, journaled event; nothing
    ever falls back implicitly."""
    _admin(roles)
    store, ledger = repository or ExecutorRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "set_executor_route", idempotency_key,
                     {"work_kind": work_kind, "primary_connection_id": primary_connection_id,
                      "standby_connection_id": standby_connection_id})
    if isinstance(claimed, CommandReplay):
        found = store.get_route_event(session, str(claimed.outcome["route_event_id"]))
        if found is None:
            raise _not_found()
        return found
    if standby_connection_id is not None and standby_connection_id == primary_connection_id:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="a standby is another connection",
            field="standby_connection_id", constraint="standby_equals_primary",
        )
    store.lock_route(session, work_kind)
    for name, connection_id in (("primary_connection_id", primary_connection_id),
                                ("standby_connection_id", standby_connection_id)):
        if connection_id is None:
            continue
        connection = store.get_connection(session, connection_id)
        if connection is None:
            raise _not_found()
        _live(connection)
        if connection.kind not in SERVES[work_kind]:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, message="this connection kind cannot serve the work",
                field=name, constraint="kind_not_routable",
            )
        # `EXEC-HTTP-01`: served by this release, and probed ok on its current key.
        ensure_routable(session, store, connection, _current(session, store, connection_id))
    route = store.append_route(
        session, work_kind=work_kind, primary_connection_id=primary_connection_id,
        standby_connection_id=standby_connection_id, actor_uid=actor_uid,
    )
    append_execution_event(
        session, event_type="executor.route_set", aggregate_type="ExecutorRoute",
        aggregate_id=route.route_event_id,
        payload={"work_kind": work_kind, "primary_connection_id": primary_connection_id,
                 "standby_connection_id": standby_connection_id, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"route_event_id": route.route_event_id})
    return route
