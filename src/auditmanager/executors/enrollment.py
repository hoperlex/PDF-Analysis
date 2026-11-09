"""The enrollment grant of the universal agent, the exchange for a runner token, and the agent's health
(`EXEC2-ENROLL-01`, ADR-0026 decisions 4, 5, 6 and 9, owner ruling `R-149b`).

An administrator issues a **grant** for one ``pull`` connection and copies the command it comes with to the
agent's host. Running it registers the agent: the secret in the command is exchanged, once, for a **runner
token** of that connection, and from then on the agent is a runner like any other (``runner.py``). The
connection then shows what the agent reports about itself and whether it is online.

The grant
---------
``ame_`` + eight characters + ``_`` + 43 characters of url-safe base64 (256 bits), 56 characters like a
runner token. **Only its SHA-256 is stored**; the value is returned once, by :func:`issue_executor_enrollment`,
and an identical repeat of the request answers ``conflict`` / ``enrollment_shown_once``. The first twelve
characters are the non-secret prefix the row is found by; the hash is then compared with
:func:`hmac.compare_digest`. A grant lives :data:`ENROLLMENT_LIFETIME_SECONDS` (15 minutes), is bound to one
connection, and is redeemed at most once. A new grant revokes the previous one that was neither redeemed nor
revoked, so at most one is pending per connection (a partial unique index backs it).

The exchange, and how a repeat by the same agent is told from anyone else
------------------------------------------------------------------------
:func:`authenticate_enrollment` is the authorization seam's port for ``redeemExecutorEnrollment`` (the only
operation that takes a grant): shape, prefix, constant-time hash comparison, expiry, revocation. A grant that
was **already redeemed** is still authenticated -- its holder proved the secret -- so that the exchange itself
can say ``enrollment_redeemed`` instead of the indistinguishable ``authentication_required``; an unknown,
wrong, revoked or expired secret is the one ``None``. The grant reaches no other operation.

:func:`redeem_enrollment` issues the runner token, **drawn at random exactly as ``issue_runner_token`` draws
one** (256 bits; only its SHA-256 is stored; the value is returned once). Nothing about the token can be
computed from the enrollment secret, so a secret that is later read from a shell history yields no token.

*Which agent process redeemed it* is recorded in the columns that exist, without a migration:

* the token's ``token_prefix`` (``amr_`` and eight characters, non-secret, shown to the administrator) is
  ``amr_`` + a seven-character **instance tag** + one character that tells apart the tokens minted for that
  instance. The tag is ``HMAC-SHA256(HMAC(secret, context), runner_instance_id)`` reduced to seven lower-case
  base-36 characters (:func:`instance_tag`); the secret it is keyed by is not stored, so the tag says nothing
  to anyone who has not seen the secret and the instance id;
* ``executor_enrollment.runner_token_id`` (deliberately **not** write-once) names the token most recently minted
  from the grant.

So a repeat is judged from the grant's current token alone:

1. the same ``runner_instance_id`` -- the current token's tag is this instance's tag -- inside the grant's window
   (its 15 minutes), on a connection that is not archived, whose current token is still usable: the stand
   **revokes that token and mints a fresh random one**, and points ``runner_token_id`` at it. An agent that lost
   the response is never locked out; the token it never saw (or saw and retried anyway) stops working;
2. a different instance id (another tag), a repeat after the window, a current token an administrator revoked
   (a retry does not undo a revocation), or no free slot left for the instance (at most 36 tokens per instance
   and grant) is ``409 enrollment_redeemed``;
3. an expired or revoked grant that was never redeemed is ``401``; an archived connection is
   ``409 connection_archived``.

A repeat is journaled as ``executor.runner_token_revoked`` (``reason: enrollment_repeat``; ``revoked_by`` on the
row is the administrator who issued the grant, the only user the grant stands for) and
``executor.enrollment_redeemed`` (``reason: repeat``).

Health
------
:func:`report_runner_health` stores what an agent says about itself on the token it presents: its version,
for each command-line client whether it is installed, its version and a sanitised authentication state, the
agent's concurrency, execution profile and declared features. Closed enumerations and bounded strings only
(:func:`normalise_health_report`); no secret, no path to a credential, no document text. Telemetry is not
journaled: it replaces itself, and a periodic report would fill the audit trail.

Moving an agent
---------------
Issuing a grant for a connection that already has an **online** agent (a token seen within
:data:`~auditmanager.executors.repository.RUNNER_ONLINE_SECONDS`) is allowed, and the move is
journaled (``executor.agent_move_requested``). The new agent redeems its grant on the other host; revoking
the old token stays ``revokeRunnerToken``'s act, once the new agent is online.

Nothing here puts a secret, a hash, a token or a derived key in an event, a log line, an error detail or a
repr. The functions run in the caller's transaction and never commit; a refusal raises before any write
that matters, and the caller's rollback drops the rest.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.executors.agent_package import (
    AgentPackage,
    install_command,
    latest_package,
    resolve_origin,
)
from auditmanager.executors.enrollment_repository import (
    EnrollmentRecord,
    EnrollmentRepository,
    TokenHealth,
)
from auditmanager.executors.host_repository import HostRepository
from auditmanager.executors.model import (
    CONFLICT_ENROLLMENT_REDEEMED,
    CONFLICT_ENROLLMENT_SHOWN_ONCE,
    CONSTRAINT_KIND_NOT_PULL,
    RUNNER_CLI_AUTH_STATES,
    RUNNER_CLI_NAMES,
    RUNNER_EXECUTION_PROFILES,
    RUNNER_FEATURES,
    refuse_system_object,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.runner import DEFAULT_TOKEN_DAYS, hash_token
from auditmanager.executors.runner_repository import RunnerRepository, RunnerTokenRecord
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = [
    "ENROLLMENT_LIFETIME_SECONDS",
    "EnrollmentPrincipal",
    "IssuedEnrollment",
    "RedeemedToken",
    "RunnerHealthReport",
    "SECRET_PREFIX_LENGTH",
    "TAG_LENGTH",
    "authenticate_enrollment",
    "enrollments_of",
    "exchange_key",
    "generate_enrollment_secret",
    "hash_enrollment_secret",
    "instance_tag",
    "issue_executor_enrollment",
    "mint_runner_token",
    "normalise_health_report",
    "redeem_enrollment",
    "report_runner_health",
    "token_health_of",
]

_AGGREGATE_CONNECTION = "ExecutorConnection"
_AGGREGATE_ENROLLMENT = "ExecutorEnrollment"
#: A grant is valid for fifteen minutes from the moment it is issued (ADR-0026 decision 4).
ENROLLMENT_LIFETIME_SECONDS: Final[int] = 15 * 60
#: ``ame_`` and eight lower-case characters: what an administrator reads and the row is found by.
SECRET_PREFIX_LENGTH: Final[int] = 12
_SECRET_SHAPE: Final[re.Pattern[str]] = re.compile(r"ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
_TOKEN_SHAPE: Final[re.Pattern[str]] = re.compile(r"amr_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
_INSTANCE_SHAPE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_-]{8,64}")
_VERSION_SHAPE: Final[re.Pattern[str]] = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}")
_CLI_VERSION_SHAPE: Final[re.Pattern[str]] = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")
_ALPHABET: Final[str] = string.ascii_lowercase + string.digits
_EXCHANGE_CONTEXT: Final[bytes] = b"auditmanager/enrollment/exchange-key/v1"
_TAG_CONTEXT: Final[bytes] = b"auditmanager/enrollment/instance-tag/v1\x00"
#: The characters of a token's prefix that name the agent process that redeemed the grant, and the one after
#: them that tells apart the tokens minted for it: ``amr_`` + tag + slot is 12 characters.
TAG_LENGTH: Final[int] = 7
_MAX_LIST: Final[int] = 8
#: The journal's writer, replaceable by a test that has no database.
Journal = Callable[..., None]


# -- values -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnrollmentPrincipal:
    """Who an exchange request is: one grant of one connection that proved its secret.

    ``exchange_key`` is derived from the secret (:func:`exchange_key`) and is as sensitive as the secret
    itself: it is the key the instance tag is computed under. It lives for one request and is in no repr."""

    enrollment_id: str
    #: Exactly one of ``connection_id`` and ``host_id`` is set (`HOSTS-BACKEND-01`): a grant of a ``pull`` connection, or of a host.
    connection_id: str | None
    exchange_key: bytes = field(repr=False)
    host_id: str | None = None


@dataclass(frozen=True, slots=True, repr=False)
class IssuedEnrollment:
    """The only moment a grant's secret and the command that carries it exist outside the agent's host."""

    record: EnrollmentRecord
    secret: str
    package: AgentPackage
    command: str

    def __repr__(self) -> str:  # a value must not reach a log through a stray repr
        return f"IssuedEnrollment(record={self.record!r}, secret=<shown once>, command=<shown once>)"


@dataclass(frozen=True, slots=True, repr=False)
class RedeemedToken:
    """A runner token as the exchange returns it: its metadata and its value, which exists only here."""

    record: RunnerTokenRecord
    value: str

    def __repr__(self) -> str:
        return f"RedeemedToken(record={self.record!r}, value=<shown once>)"


@dataclass(frozen=True, slots=True)
class RunnerHealthReport:
    """A validated health report: nothing in it is free text."""

    agent_version: str
    clis: tuple[Mapping[str, Any], ...]
    concurrency: int
    execution_profile: str
    features: tuple[str, ...]


# -- secrets and derived tokens ---------------------------------------------------------------


def generate_enrollment_secret() -> tuple[str, str]:
    """``(value, prefix)`` of a new grant's secret: 256 bits of entropy behind a recognisable prefix."""
    prefix = "ame_" + "".join(secrets.choice(_ALPHABET) for _ in range(8))
    value = f"{prefix}_{secrets.token_urlsafe(32)}"
    assert _SECRET_SHAPE.fullmatch(value) is not None
    return value, prefix


def hash_enrollment_secret(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def exchange_key(secret: str) -> bytes:
    """The key an instance tag is computed under: ``HMAC-SHA256(secret, context)``.

    Whoever holds the stored hash alone cannot compute it; it needs the secret itself."""
    return hmac.new(secret.encode("utf-8"), _EXCHANGE_CONTEXT, hashlib.sha256).digest()


def instance_tag(key: bytes, runner_instance_id: str) -> str:
    """Seven lower-case base-36 characters that stand for one agent process within one grant.

    ``HMAC-SHA256(key, runner_instance_id)`` reduced byte by byte: deterministic in ``(key, instance)``, so a
    repeat by the same process has the tag of the token it was given, and a different instance id (or a
    different grant) another. It is a recognition mark, not a credential: it is a fragment of the token's
    non-secret prefix and reveals nothing of the token's 256 random bits."""
    digest = hmac.new(key, _TAG_CONTEXT + runner_instance_id.encode("ascii"), hashlib.sha256).digest()
    return "".join(_ALPHABET[byte % len(_ALPHABET)] for byte in digest[:TAG_LENGTH])


def mint_runner_token(tag: str, taken_prefixes: Collection[str]) -> tuple[str, str] | None:
    """``(value, prefix)`` of a new random runner token for the instance with this tag, or ``None``.

    The value is drawn exactly as ``runner.generate_token`` draws one -- ``secrets.token_urlsafe(32)``, 256
    bits, nothing derived from any secret -- and only the prefix carries the tag. The last prefix character
    is a free one of 36 (one not in ``taken_prefixes``), so every token an instance is given has a prefix of
    its own; ``None`` when the instance has used them all."""
    free = [c for c in _ALPHABET if f"amr_{tag}{c}" not in taken_prefixes]
    if not free:
        return None
    prefix = f"amr_{tag}{secrets.choice(free)}"
    value = f"{prefix}_{secrets.token_urlsafe(32)}"
    assert _TOKEN_SHAPE.fullmatch(value) is not None
    return value, prefix


# -- shared helpers ---------------------------------------------------------------------------


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _conflict(reason: str, message: str) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message=message, conflict_reason=reason)


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str,
    payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


# -- issuing a grant --------------------------------------------------------------------------


def issue_executor_enrollment(
    session: Session, *, connection_id: str, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, configured_origin: str | None,
    executors: ExecutorRepository | None = None, repository: EnrollmentRepository | None = None,
    commands: CommandRepository | None = None,
    package_source: Callable[[], AgentPackage] = latest_package,
    journal: Journal = append_execution_event,
) -> IssuedEnrollment:
    """Issue a grant for a ``pull`` connection and return its secret and install command, once.

    Refusals, in this order and all before anything is written: ``permission_denied``;
    ``dependency_unavailable`` / ``public_origin`` (the configured ``AUDITMANAGER_PUBLIC_ORIGIN`` is the only
    source of the command's origin, and a stand without a valid one refuses before even the idempotency key
    is recorded); a repeat of the key (``conflict`` / ``enrollment_shown_once``: the secret was never stored);
    ``not_found``; ``conflict`` / ``connection_archived``; ``validation_failed`` on ``kind``
    (``kind_not_pull``); ``conflict`` / ``no_revision``; ``dependency_unavailable`` / ``agent_package``.

    The previous grant that was neither redeemed nor revoked is revoked, and when an agent of this
    connection is online the move is journaled."""
    _admin(roles)
    origin = resolve_origin(configured_origin)
    store, grants, ledger = (
        executors or ExecutorRepository(), repository or EnrollmentRepository(),
        commands or CommandRepository(),
    )
    claimed = _begin(session, ledger, "issue_executor_enrollment", idempotency_key,
                     {"connection_id": connection_id})
    if isinstance(claimed, CommandReplay):
        raise _conflict(CONFLICT_ENROLLMENT_SHOWN_ONCE,
                        "the secret was shown once and cannot be shown again")
    connection = store.get_connection(session, connection_id, lock=True)
    if connection is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=_AGGREGATE_CONNECTION)
    if connection.system_managed:
        raise refuse_system_object()
    if connection.archived_at is not None:
        raise _conflict("connection_archived", "the connection is archived")
    if connection.kind != "pull":
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="only a pull connection takes an agent",
            field="kind", constraint=CONSTRAINT_KIND_NOT_PULL,
        )
    current = store.current_revisions(session, [connection_id]).get(connection_id)
    if current is None:
        raise _conflict("no_revision", "the connection has no revision yet")
    package = package_source()

    online = grants.online_tokens(session, connection_id)
    for revoked_id, was_live in grants.revoke_unredeemed(session, connection_id, actor_uid=actor_uid):
        if was_live:
            journal(
                session, event_type="executor.enrollment_revoked",
                aggregate_type=_AGGREGATE_ENROLLMENT, aggregate_id=revoked_id,
                payload={"connection_id": connection_id, "actor_uid": actor_uid,
                         "reason": "superseded"},
            )
    value, prefix = generate_enrollment_secret()
    record = grants.insert_enrollment(
        session, connection_id=connection_id, secret_prefix=prefix,
        secret_hash=hash_enrollment_secret(value), lifetime_seconds=ENROLLMENT_LIFETIME_SECONDS,
        actor_uid=actor_uid,
    )
    journal(
        session, event_type="executor.enrollment_issued", aggregate_type=_AGGREGATE_ENROLLMENT,
        aggregate_id=record.enrollment_id,
        payload={"connection_id": connection_id, "actor_uid": actor_uid},
    )
    if online:
        journal(
            session, event_type="executor.agent_move_requested",
            aggregate_type=_AGGREGATE_CONNECTION, aggregate_id=connection_id,
            payload={"connection_id": connection_id, "token_id": online[0],
                     "actor_uid": actor_uid, "reason": "online_agent"},
        )
    ledger.succeed(session, claimed.command_id, {"enrollment_id": record.enrollment_id})
    return IssuedEnrollment(
        record=record, secret=value, package=package,
        command=install_command(origin=origin, package=package, secret=value,
                                model=current.settings.gateway_model),
    )


def enrollments_of(
    session: Session, connection_id: str, repository: EnrollmentRepository | None = None,
    *, limit: int = 10,
) -> list[EnrollmentRecord]:
    """The connection's last grants, newest first, as metadata."""
    return (repository or EnrollmentRepository()).list_for_connection(
        session, connection_id, limit=limit)


# -- the exchange -----------------------------------------------------------------------------


def authenticate_enrollment(
    session: Session, presented: str, repository: EnrollmentRepository | None = None,
) -> EnrollmentPrincipal | None:
    """The principal of a presented enrollment secret, or ``None`` for every way it can fail.

    The shape is checked before any read, so a runner token, a user's credential or garbage costs no query.
    The stored hash is compared with :func:`hmac.compare_digest`; a missing secret takes the same path.
    A grant that is unknown, wrong, revoked, or expired without having been redeemed is the same ``None``.
    One that **was** redeemed is authenticated: the exchange answers it (``enrollment_redeemed``)."""
    if _SECRET_SHAPE.fullmatch(presented) is None:
        return None
    store = repository or EnrollmentRepository()
    found = store.by_prefix(session, presented[:SECRET_PREFIX_LENGTH])
    candidate = hash_enrollment_secret(presented)
    if found is None:
        hmac.compare_digest(candidate, hash_enrollment_secret(""))
        return None
    record, stored_hash = found
    if not hmac.compare_digest(candidate, stored_hash):
        return None
    if record.redeemed_at is None and not record.usable:
        return None
    return EnrollmentPrincipal(
        enrollment_id=record.enrollment_id, connection_id=record.connection_id,
        exchange_key=exchange_key(presented), host_id=record.host_id,
    )


def redeem_enrollment(
    session: Session, principal: EnrollmentPrincipal, *, runner_instance_id: str,
    executors: ExecutorRepository | None = None, repository: EnrollmentRepository | None = None,
    runner: RunnerRepository | None = None, journal: Journal = append_execution_event,
    hosts: HostRepository | None = None,
) -> RedeemedToken:
    """Exchange a proven grant for a runner token of its connection -- or, for the grant of a host (`HOSTS-BACKEND-01`), for the **host
    token**, which serves every system connection of that host. The host's row takes the place of the connection's in the lock order, and
    redeeming the grant of a host revokes the host's other usable tokens (one agent process per host: a move or an upgrade replaces the old one).

    The connection and then the grant are locked, in that order (the order :func:`issue_executor_enrollment`
    takes), so two exchanges of one grant, and an exchange against a new grant, serialise. A grant revoked
    or expired between authentication and here is ``authentication_required``; an archived connection and a
    grant already exchanged are ``conflict`` (``connection_archived``, ``enrollment_redeemed``) -- except a
    repeat by the same instance inside the grant's window, which revokes the token it was given and mints it
    a fresh one (see the module note)."""
    if _INSTANCE_SHAPE.fullmatch(runner_instance_id) is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the runner instance id is not of the declared form",
            field="runner_instance_id", constraint="pattern",
        )
    store, grants, tokens = (
        executors or ExecutorRepository(), repository or EnrollmentRepository(),
        runner or RunnerRepository(),
    )
    if principal.host_id is not None:
        owner = (hosts or HostRepository()).get_host(session, principal.host_id, lock=True)
        grant = grants.get_enrollment(session, principal.enrollment_id, lock=True)
        archived = owner is None or owner.archived_at is not None
        if owner is None or grant is None or grant.host_id != owner.host_id:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        archived_refusal = lambda: DomainError(  # noqa: E731
            ErrorCode.CONFLICT, message="the host is archived", conflict_reason="host_archived", aggregate_type="ExecutorHost")
    else:
        connection = store.get_connection(session, principal.connection_id, lock=True)
        grant = grants.get_enrollment(session, principal.enrollment_id, lock=True)
        if connection is None or grant is None or grant.connection_id != connection.connection_id:
            raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
        archived = connection.archived_at is not None
        archived_refusal = lambda: _conflict("connection_archived", "the connection is archived")  # noqa: E731
    tag = instance_tag(principal.exchange_key, runner_instance_id)
    if grant.redeemed_at is not None:
        if archived:
            raise archived_refusal()
        return _repeat(session, grant, tag, grants, tokens, journal)
    if not grant.usable:
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    if archived:
        raise archived_refusal()
    minted = _mint(session, grant, tag, grants, tokens)
    if minted is None:
        raise _conflict(CONFLICT_ENROLLMENT_REDEEMED, "the enrollment secret was already exchanged")
    if not grants.mark_redeemed(session, grant.enrollment_id, minted.record.token_id):
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    journal(
        session, event_type="executor.enrollment_redeemed", aggregate_type=_AGGREGATE_ENROLLMENT,
        aggregate_id=grant.enrollment_id,
        payload={**_target(grant), "token_id": minted.record.token_id},
    )
    if grant.host_id is not None:
        _replace_host_tokens(session, grant, minted.record.token_id, hosts or HostRepository(), journal)
    return minted


def _target(grant: EnrollmentRecord) -> dict[str, str]:
    """The identity a grant is for, as a journal payload: a connection or a host."""
    return {"host_id": grant.host_id} if grant.host_id is not None else {"connection_id": str(grant.connection_id)}


def _replace_host_tokens(
    session: Session, grant: EnrollmentRecord, keep_token_id: str, hosts: HostRepository, journal: Journal,
) -> None:
    """One agent process per host: the token just minted replaces every other usable token of the host."""
    assert grant.host_id is not None
    for token_id in hosts.usable_tokens(session, grant.host_id):
        if token_id == keep_token_id:
            continue
        RunnerRepository().revoke_token(session, token_id, actor_uid=grant.created_by)
        journal(
            session, event_type="executor.runner_token_revoked", aggregate_type="ExecutorHost", aggregate_id=grant.host_id,
            payload={"host_id": grant.host_id, "token_id": token_id, "reason": "host_moved"})


def _mint(
    session: Session, grant: EnrollmentRecord, tag: str, grants: EnrollmentRepository,
    tokens: RunnerRepository,
) -> RedeemedToken | None:
    """Insert a new random token for ``tag`` on the grant's connection; ``None`` with no free slot."""
    pair = mint_runner_token(tag, grants.prefixes_starting(session, f"amr_{tag}"))
    if pair is None:
        return None
    value, prefix = pair
    record = tokens.insert_token(
        session, connection_id=grant.connection_id, token_prefix=prefix,
        token_hash=hash_token(value), expires_in_days=DEFAULT_TOKEN_DAYS, actor_uid=grant.created_by,
        **({} if grant.host_id is None else {"host_id": grant.host_id}),
    )
    return RedeemedToken(record=record, value=value)


def _repeat(
    session: Session, grant: EnrollmentRecord, tag: str, grants: EnrollmentRepository,
    tokens: RunnerRepository, journal: Journal,
) -> RedeemedToken:
    """A grant already exchanged. The same instance, inside the grant's window, whose current token is still
    in force, has that token revoked and a fresh one minted; everyone else is ``enrollment_redeemed``."""
    redeemed = _conflict(CONFLICT_ENROLLMENT_REDEEMED, "the enrollment secret was already exchanged")
    if grant.runner_token_id is None or grant.read_at > grant.expires_at:
        raise redeemed
    current = tokens.get_token(session, grant.runner_token_id, lock=True)
    if current is None:
        raise redeemed
    stored = tokens.token_by_prefix(session, current.token_prefix)
    if stored is None or stored.token_id != current.token_id or not stored.usable:
        raise redeemed
    held = current.token_prefix[len("amr_"):len("amr_") + TAG_LENGTH]
    if not hmac.compare_digest(held.encode("ascii"), tag.encode("ascii")):
        raise redeemed
    minted = _mint(session, grant, tag, grants, tokens)
    if minted is None:
        raise redeemed
    tokens.revoke_token(session, current.token_id, actor_uid=grant.created_by)
    if not grants.set_current_token(session, grant.enrollment_id, minted.record.token_id):
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    journal(
        session, event_type="executor.runner_token_revoked",
        aggregate_type=_AGGREGATE_CONNECTION if grant.host_id is None else "ExecutorHost",
        aggregate_id=str(grant.connection_id if grant.host_id is None else grant.host_id),
        payload={**_target(grant), "token_id": current.token_id, "reason": "enrollment_repeat"},
    )
    journal(
        session, event_type="executor.enrollment_redeemed", aggregate_type=_AGGREGATE_ENROLLMENT,
        aggregate_id=grant.enrollment_id,
        payload={**_target(grant), "token_id": minted.record.token_id, "reason": "repeat"},
    )
    return minted


# -- health -----------------------------------------------------------------------------------


def _refused(field_name: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the health report is not acceptable",
        field=field_name, constraint=constraint,
    )


def normalise_health_report(
    *, agent_version: Any, clis: Any, concurrency: Any, execution_profile: Any, features: Any,
) -> RunnerHealthReport:
    """The report as the stand will store it, or ``validation_failed`` naming the field.

    Only closed enumerations and bounded strings survive, rebuilt from the accepted fields -- an extra key
    is dropped by construction. Beyond the schema: a client is named once, and a client that is not
    installed has no version and an ``unknown`` state (the enumeration's own meaning of ``unknown``)."""
    if not isinstance(agent_version, str) or _VERSION_SHAPE.fullmatch(agent_version) is None:
        raise _refused("agent_version", "pattern")
    if not isinstance(clis, Sequence) or isinstance(clis, (str, bytes)) or len(clis) > _MAX_LIST:
        raise _refused("clis", "length")
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in clis:
        if not isinstance(item, Mapping):
            raise _refused("clis", "type")
        name, installed = item.get("cli"), item.get("installed")
        version, state = item.get("version"), item.get("auth_state")
        if name not in RUNNER_CLI_NAMES:
            raise _refused("clis", "enum")
        if name in seen:
            raise _refused("clis", "unique")
        if not isinstance(installed, bool) or state not in RUNNER_CLI_AUTH_STATES:
            raise _refused("clis", "type")
        if version is not None and (
            not isinstance(version, str) or _CLI_VERSION_SHAPE.fullmatch(version) is None
        ):
            raise _refused("clis", "pattern")
        if not installed and (version is not None or state != "unknown"):
            raise _refused("clis", "not_installed")
        seen.add(name)
        cleaned.append({"cli": name, "installed": installed, "auth_state": state,
                        **({} if version is None else {"version": version})})
    if type(concurrency) is not int or not 1 <= concurrency <= 16:
        raise _refused("concurrency", "range")
    if execution_profile not in RUNNER_EXECUTION_PROFILES:
        raise _refused("execution_profile", "enum")
    if (not isinstance(features, Sequence) or isinstance(features, (str, bytes))
            or len(features) > _MAX_LIST):
        raise _refused("features", "length")
    if any(feature not in RUNNER_FEATURES for feature in features):
        raise _refused("features", "enum")
    if len(set(features)) != len(features):
        raise _refused("features", "unique")
    return RunnerHealthReport(
        agent_version=agent_version, clis=tuple(cleaned), concurrency=concurrency,
        execution_profile=execution_profile, features=tuple(sorted(features)),
    )


def report_runner_health(
    session: Session, token_id: str, *, agent_version: Any, clis: Any, concurrency: Any,
    execution_profile: Any, features: Any, repository: EnrollmentRepository | None = None,
) -> datetime:
    """Store the report on the token that presented it and return when it was recorded.

    The caller is an authenticated runner, so the token is there; a token that is gone between the
    authentication and here is ``authentication_required``, as everywhere on the runner channel."""
    report = normalise_health_report(
        agent_version=agent_version, clis=clis, concurrency=concurrency,
        execution_profile=execution_profile, features=features)
    recorded = (repository or EnrollmentRepository()).store_health(
        session, token_id, agent_version=report.agent_version, clis=report.clis,
        concurrency=report.concurrency, execution_profile=report.execution_profile,
        features=report.features)
    if recorded is None:
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    return recorded


def token_health_of(
    session: Session, token_ids: Sequence[str], repository: EnrollmentRepository | None = None,
) -> dict[str, TokenHealth]:
    """What the tokens last reported, with «online» as of now. A token that never reported is absent."""
    return (repository or EnrollmentRepository()).health_of_tokens(session, token_ids)
