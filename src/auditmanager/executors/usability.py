"""Whether a connection may be routed or used: served by this release, and probed ``ok``.

`EXEC-HTTP-01` (`R-143`, plan section 3). Two conditions, both read from rows and neither
cached:

* **served** -- this release has an adapter factory for the kind (:mod:`.kinds`). Today that is
  ``http_api`` over ``direct`` or ``vpn``, ``pull`` and ``ssh_command``; the
  ``ssh_tunnel`` transport with both secrets and a current probe;
* **probed** -- the *latest finished probe of the current revision on the current primary
  secret* is ``ok``. For a tunnel, that probe must have been requested after both current
  secrets were issued. A new revision, a changed key and a failed re-probe each make the
  connection unusable until a probe passes again (T-1).

A run that already froze a revision is not asked again: it uses that revision with whatever key is
current (a rotation is picked up at the next Attempt). These checks guard *routing* and *run start*.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from auditmanager.executors.kinds import adapter_for
from auditmanager.executors.model import ConnectionRecord, RevisionRecord, SecretRecord
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "current_secret",
    "ensure_routable",
    "is_probed_ok",
    "is_served",
    "refuse_if_not_served",
]

def is_served(connection: ConnectionRecord, revision: RevisionRecord) -> bool:
    entry = adapter_for(connection.kind)
    return entry is not None and entry.serves(revision)


def refuse_if_not_served(connection: ConnectionRecord, revision: RevisionRecord) -> None:
    if not is_served(connection, revision):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="this kind of connection is not served yet",
            field="kind", constraint="kind_not_served",
        )


def current_secret(
    session: Session, store: ExecutorRepository, connection: ConnectionRecord
) -> SecretRecord | None:
    """The connection's current secret of the purpose its kind's adapter is handed."""
    entry = adapter_for(connection.kind)
    purpose = "api_key" if entry is None else entry.purpose
    return next((secret for secret in
                 store.current_secrets(session, [connection.connection_id])
                 .get(connection.connection_id, [])
                 if secret.purpose == purpose), None)


def is_probed_ok(
    session: Session, store: ExecutorRepository, connection: ConnectionRecord,
    revision: RevisionRecord,
) -> bool:
    entry = adapter_for(connection.kind)
    if entry is not None and entry.purpose is None:
        # A channel kind (``pull``) keeps no sealed secret: its probe is taken on no secret, and
        # a runner token is a credential of the runner, not a condition of the revision.
        secret_id = None
    else:
        secret = current_secret(session, store, connection)
        if secret is None:
            return False
        secret_id = secret.secret_id
    probe = store.latest_finished_probe(session, revision.revision_id, secret_id)
    if probe is None or probe.outcome != "ok":
        return False
    if connection.kind == "http_api" and revision.settings.transport == "ssh_tunnel":
        # The probe row names the API key. Its request time binds the successful
        # check to the SSH key too: after either rotation, an earlier `ok` is stale.
        current = {item.purpose: item for item in
                   store.current_secrets(session, [connection.connection_id])
                   .get(connection.connection_id, ())}
        ssh = current.get("ssh_private_key")
        api = current.get("api_key")
        if ssh is None or api is None or probe.requested_at < max(ssh.set_at, api.set_at):
            return False
    return True


def ensure_routable(
    session: Session, store: ExecutorRepository, connection: ConnectionRecord,
    revision: RevisionRecord,
) -> None:
    """Refuse a route to a connection this release does not serve, or whose current revision
    has no ``ok`` probe on its current key (``conflict``, ``connection_not_probed``)."""
    refuse_if_not_served(connection, revision)
    if not is_probed_ok(session, store, connection, revision):
        raise DomainError(
            ErrorCode.CONFLICT, message="the connection has not passed a probe",
            conflict_reason="connection_not_probed",
        )
