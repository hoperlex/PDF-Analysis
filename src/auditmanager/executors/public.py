"""The cross-context surface of the executors boundary (`EXEC-SEAL-01`).

What ``EXEC-HTTP-01`` relies on:

* :func:`resolve_route` and :func:`current_revision` -- which connection serves a kind of model
  work and the revision to freeze at run start;
* :func:`pinned_models` -- the models a revision may name, with their rates, from the provider
  lock (the same list validates a revision);
* :func:`record_probe_started` and :func:`record_probe_result` -- how the worker writes a probe;
* :func:`open_secret` -- **worker only**. The caller recomputes the destination from the
  revision it is about to call (:func:`destination_for`) and passes it; the associated data is
  built from that argument and never from the stored row. A revision that changed the address
  leaves the old secret :class:`SecretUnreadableError` for it.

The ``api`` never imports :func:`open_secret`'s ring: it loads public keys only
(:func:`load_public_ring`).
"""

from __future__ import annotations

from auditmanager.analysis.public import ModelPin, pinned_models
from auditmanager.executors.commands import (
    GeneratedKey,
    archive_connection,
    create_connection,
    generate_ssh_key,
    request_probe,
    revise_connection,
    set_route,
    set_secret,
)
from auditmanager.executors.model import (
    ConnectionRecord,
    ConnectionSummary,
    ProbeRecord,
    ResolvedRoute,
    RevisionRecord,
    RevisionSettings,
    RouteRecord,
    SecretRecord,
    destination_for,
    host_key_fingerprint,
)
from auditmanager.executors.pull import (
    PullAdapter,
    TaskWaiter,
    answer_window,
    build_pull_adapter,
    probe_pull,
)
from auditmanager.executors.queries import (
    ConnectionDetail,
    connection_detail,
    list_connection_summaries,
    list_routes,
    resolve_route,
    sweep,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.runner import (
    CLAIM_LEASE_SECONDS,
    ClaimedTask,
    IssuedToken,
    RunnerPrincipal,
    TaskAck,
    authenticate_runner,
    claim_task,
    extend_claim,
    fail_task,
    issue_runner_token,
    open_task_count,
    revoke_runner_token,
    runner_tokens_of,
    submit_answer,
)
from auditmanager.executors.runner_repository import RunnerTokenRecord
from auditmanager.executors.sealing import (
    PrivateRing,
    PublicRing,
    SealingConfigurationError,
    SecretUnreadable,
    associated_data,
    load_private_ring,
    load_public_ring,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from sqlalchemy.orm import Session

__all__ = [
    "CLAIM_LEASE_SECONDS",
    "ClaimedTask",
    "ConnectionDetail",
    "ConnectionRecord",
    "ConnectionSummary",
    "GeneratedKey",
    "IssuedToken",
    "ModelPin",
    "PrivateRing",
    "ProbeRecord",
    "PublicRing",
    "PullAdapter",
    "ResolvedRoute",
    "RevisionRecord",
    "RevisionSettings",
    "RouteRecord",
    "RunnerPrincipal",
    "RunnerTokenRecord",
    "SealingConfigurationError",
    "SecretRecord",
    "SecretUnreadableError",
    "TaskAck",
    "TaskWaiter",
    "answer_window",
    "archive_connection",
    "authenticate_runner",
    "build_pull_adapter",
    "claim_task",
    "connection_detail",
    "create_connection",
    "current_revision",
    "destination_for",
    "extend_claim",
    "fail_task",
    "generate_ssh_key",
    "host_key_fingerprint",
    "issue_runner_token",
    "list_connection_summaries",
    "list_routes",
    "load_private_ring",
    "load_public_ring",
    "open_secret",
    "open_task_count",
    "pinned_models",
    "probe_pull",
    "record_probe_result",
    "record_probe_started",
    "request_probe",
    "resolve_route",
    "revise_connection",
    "revoke_runner_token",
    "runner_tokens_of",
    "set_route",
    "set_secret",
    "submit_answer",
    "sweep",
]


class SecretUnreadableError(DomainError):
    """``dependency_unavailable``, ``dependency: secret_unreadable``: the secret cannot be opened
    here, for this destination. Carries no bytes and no key material."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.DEPENDENCY_UNAVAILABLE, message="the sealed secret cannot be opened",
            dependency="secret_unreadable",
        )


def current_revision(
    session: Session, connection_id: str, repository: ExecutorRepository | None = None
) -> RevisionRecord | None:
    """The highest-numbered revision of a connection, or ``None`` when it has none."""
    return (repository or ExecutorRepository()).current_revisions(
        session, [connection_id]
    ).get(connection_id)


def open_secret(
    session: Session, ring: PrivateRing | None, *, secret_id: str, destination: str,
    repository: ExecutorRepository | None = None,
) -> str:
    """Open one secret for ``destination``. Worker only: ``ring`` is the private ring.

    Raises :class:`SecretUnreadableError` for every reason it cannot: no ring, no such secret,
    a key id missing from the ring, a corrupt envelope, or a destination other than the one
    the secret was sealed for. The reason is not distinguished, and no byte is in the error.
    """
    sealed = (repository or ExecutorRepository()).sealed_secret(session, secret_id)
    if ring is None or sealed is None:
        raise SecretUnreadableError()
    connection_id, purpose, kid, ciphertext = sealed
    associated = associated_data(
        secret_id=secret_id, connection_id=connection_id, purpose=purpose, kid=kid,
        destination=destination,
    )
    try:
        return ring.open(kid, ciphertext, associated).decode("utf-8")
    except (SecretUnreadable, UnicodeDecodeError):
        raise SecretUnreadableError() from None


def record_probe_started(
    session: Session, probe_id: str, repository: ExecutorRepository | None = None
) -> bool:
    """``requested -> running``; ``False`` when the probe was no longer ``requested``."""
    return (repository or ExecutorRepository()).start_probe(session, probe_id)


def record_probe_result(
    session: Session, probe_id: str, *, outcome: str, reported_model: str | None = None,
    identity_basis: str | None = None, latency_ms: int | None = None,
    http_status: int | None = None, rate_check: str | None = None,
    observed_host_key: str | None = None, detail: str | None = None,
    repository: ExecutorRepository | None = None,
) -> bool:
    """Finish a probe. ``False`` when it had already finished (the api's sweep ended it first):
    a late worker never overwrites ``no_worker`` or ``timeout``. ``detail`` is cut to the 500
    characters the schema allows; the caller scrubs it first and never passes a body."""
    return (repository or ExecutorRepository()).finish_probe(
        session, probe_id, outcome=outcome, reported_model=reported_model,
        identity_basis=identity_basis, latency_ms=latency_ms, http_status=http_status,
        rate_check=rate_check, observed_host_key=observed_host_key,
        detail=None if detail is None else detail[:500],
    )
