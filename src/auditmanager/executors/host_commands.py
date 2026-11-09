"""The servers: their lifecycle, the system objects kept for them, and the availability read from stored facts (`HOSTS-BACKEND-01`, ADR-0028).

A *host* is one machine, one agent process and one **host token**. An administrator enrolls it with one grant (:func:`issue_host_enrollment`)
or by an install session over SSH (:func:`create_host_agent_install`); no model is asked for. The agent then reports, with every heartbeat,
which providers and models it found and verified (:func:`report_host_health`). The stand keeps what follows from that:

* **the snapshot** -- the latest report, written only when its content changes (``HostReport.change_key``); the change goes to the executor
  journal (``executor.host_report_changed``);
* **the system objects** (:func:`sync_system_objects`) -- for every found quadruple host, provider, access, model that the catalogue serves, one
  system-managed ``pull`` connection (``not_metered`` for a subscription, ``metered`` for an API key) with one revision, and for every pair
  (model, access) one system group whose members are those connections. A group revises only when a host is connected or archived, never because
  a host went off line; at most ``GROUP_MEMBERS_MAX`` hosts take part in a pair (the oldest sixteen; a later one keeps its connections and is
  journaled ``executor.host_over_group_limit``). A system object cannot be revised or archived by hand and is not listed (``commands.py``,
  ``group_commands.py``, ``routing_mode.py``);
* **availability**, computed on read (:func:`read_hosts`, :func:`model_availability`): host enabled, pulse at most 120 s old, login present, model
  verified, the pair not cooling down (``hosts.model_reasons``). Nothing about it is stored except its facts. ``at_capacity`` is «Занято», not a reason;
* **«Использовать»** (:func:`set_host_enabled`) -- an append-only event with its author; it sets or clears the integration mark of the host's
  system connections. A host that is off takes no new run; the runs bound to it finish (the claims of its token go on);
* **slots** (:func:`set_host_slots`) -- an append-only event per provider; the pool of a provider (``<host_id>:<provider>``) has that many units;
* **the passive cooldown** (:func:`record_task_failure`) -- a real refusal of access, quota or model takes the pair out of availability for 15
  minutes or until a changed report.

Every function runs in the caller's transaction and never commits. A refusal raises before any write that matters.

Typed details this module adds to existing error codes (no new code): ``conflict`` with ``conflict_reason`` ``host_name_in_use`` (a live host holds
the name), ``host_archived``, ``host_in_use`` (a pool still holds a run's unit), ``upgrade_blocked_by_use`` (the name of a single-model pull
connection that rules or comparisons still use, until `HOSTS-CMP-01`) and ``system_managed`` (``commands.py``); ``validation_failed`` with ``field`` ``slots``
and ``constraint`` ``provider_not_reported`` or ``range``, ``field`` ``providers`` and a ``constraint`` naming what the report got wrong.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.agent_install import (
    INSTALL_PURPOSE,
    InstallLifetimeRepository,
    authorized_keys_line,
    expire_overdue_installs,
    install_destination,
    observed_fingerprint,
)
from auditmanager.executors.agent_install import (
    _check_key_argument,
    _check_target,
    _need_ring,
)
from auditmanager.executors.agent_install_repository import (
    UNFINISHED_STATES,
    AgentInstallRepository,
    InstallRecord,
)
from auditmanager.executors.agent_package import AgentPackage, install_command, latest_package, resolve_origin
from auditmanager.executors.catalogue import Catalogue, catalogue as default_catalogue
from auditmanager.executors.enrollment import (
    ENROLLMENT_LIFETIME_SECONDS,
    IssuedEnrollment,
    generate_enrollment_secret,
    hash_enrollment_secret,
)
from auditmanager.executors.enrollment_repository import EnrollmentRepository
from auditmanager.executors.group_repository import GroupRepository
from auditmanager.executors.groups import GroupSettings, MemberRequest, clean_display_name
from auditmanager.executors.host_repository import ActiveTask, HostRecord, HostRepository, StoredReport, SystemConnectionRow
from auditmanager.executors.hosts import (
    ACCESS_SUBSCRIPTION,
    COOLDOWN_SECONDS,
    HostReport,
    Quadruple,
    access_of_billing,
    billing_of_access,
    cooldown_reason_of,
    desired_quadruples,
    host_state,
    model_reasons,
    model_state,
    normalise_host_report,
    pair_group_name,
    pool_of,
    slots_in_force,
)
from auditmanager.executors.model import (
    CONFLICT_HOST_KEY_CHANGED,
    CONFLICT_INSTALL_IN_PROGRESS,
    CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
    CONFLICT_ENROLLMENT_SHOWN_ONCE,
    GROUP_MEMBERS_MAX,
    GROUP_STRATEGY_LEAST_LOADED,
    RevisionSettings,
    validate_settings,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.sealing import PublicRing
from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.jobs.public import append_execution_event
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import ExecutorAgentInstallId, ExecutorSecretId, IdempotencyKey

__all__ = [
    "HostDetails",
    "HostFacts",
    "HostHealthAck",
    "ModelAvailability",
    "SlotUse",
    "archive_host",
    "confirm_host_agent_install_host_key",
    "create_host_agent_install",
    "ensure_upgrade_allowed",
    "get_host_agent_install",
    "host_claim_limit",
    "host_details",
    "issue_host_enrollment",
    "model_availability",
    "read_hosts",
    "record_task_failure",
    "refuse_host_members_for_connection_token",
    "report_host_health",
    "report_host_runner_health",
    "set_host_enabled",
    "set_host_slots",
    "sync_system_objects",
]

_AGGREGATE_HOST: Final[str] = "ExecutorHost"
_AGGREGATE_INSTALL: Final[str] = "ExecutorAgentInstall"
_AGGREGATE_ENROLLMENT: Final[str] = "ExecutorEnrollment"
_AGGREGATE_CONNECTION: Final[str] = "ExecutorConnection"
Journal = Callable[..., None]

#: What a system connection's revision says besides the model and the billing (everything a ``pull`` revision needs, nothing a host varies):
#: no client documents, the agent client, the longest answer window the schema allows (the call's own limit is the cell's timeout) and one
#: claim at a time (a host token's own limit is the sum of its slots, ``host_claim_limit``).
_SYSTEM_TIMEOUT_SECONDS: Final[int] = 600
_SYSTEM_ANSWER_DEADLINE_SECONDS: Final[int] = 3600


# --- shared helpers -------------------------------------------------------------------------------------------------


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _conflict(reason: str, message: str, *, aggregate: str = _AGGREGATE_HOST) -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message=message, conflict_reason=reason, aggregate_type=aggregate)


def _not_found(aggregate: str = _AGGREGATE_HOST) -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=aggregate)


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str, payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


def _live_host(session: Session, repo: HostRepository, host_id: str, *, lock: bool = False) -> HostRecord:
    host = repo.get_host(session, host_id, lock=lock)
    if host is None:
        raise _not_found()
    if host.archived_at is not None:
        raise _conflict("host_archived", "the host is archived")
    return host


# --- facts and availability, read at the moment they are asked for ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotUse:
    provider: str
    access: str | None
    slots: int
    in_use: int


@dataclass(frozen=True, slots=True)
class ModelAvailability:
    """One catalogue model on one host, with every reason it cannot be used (empty when it can). ``state`` is ``available``, ``busy``
    (no reason, every slot of its pool taken) or ``unavailable``."""

    provider: str
    access: str
    model_id: str
    state: str
    reasons: tuple[str, ...]
    cooldown_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class HostFacts:
    """Everything the availability of a host is computed from, read together at one database instant."""

    record: HostRecord
    enabled: bool
    pulse_age_seconds: float | None
    report: StoredReport | None
    slots: tuple[SlotUse, ...]
    cooldowns: Mapping[tuple[str, str], datetime]
    connections: tuple[SystemConnectionRow, ...]
    now: datetime

    @property
    def state(self) -> str:
        return host_state(
            pulse_age_seconds=self.pulse_age_seconds, slots_total=sum(item.slots for item in self.slots),
            slots_in_use=sum(item.in_use for item in self.slots))

    @property
    def slots_total(self) -> int:
        return sum(item.slots for item in self.slots)

    @property
    def slots_in_use(self) -> int:
        return sum(item.in_use for item in self.slots)

    def slot_of(self, provider: str) -> SlotUse | None:
        return next((item for item in self.slots if item.provider == provider), None)


@dataclass(frozen=True, slots=True)
class HostDetails:
    facts: HostFacts
    models: tuple[ModelAvailability, ...]
    tasks: tuple[ActiveTask, ...]


def read_hosts(
    session: Session, host_ids: Sequence[str] | None = None, *, repo: HostRepository | None = None,
    include_archived: bool = False,
) -> list[HostFacts]:
    """The facts of the named hosts (every live host when none are named), newest first, read now. A named host that does not exist is
    absent from the answer."""
    store = repo or HostRepository()
    if host_ids is None:
        records = store.list_hosts(session, include_archived=include_archived)
    else:
        records = [found for host_id in host_ids if (found := store.get_host(session, host_id)) is not None]
    ids = [record.host_id for record in records]
    uses, ages, reports = store.current_use(session, ids), store.pulse_ages(session, ids), store.get_reports(session, ids)
    journal, cooldowns = store.slot_journal(session, ids), store.cooldowns_of(session, ids)
    connections = store.system_connections(session, ids)
    now = session.execute(text("SELECT clock_timestamp()")).scalar_one()
    facts: list[HostFacts] = []
    for record in records:
        report = reports.get(record.host_id)
        slots: list[SlotUse] = []
        for provider in () if report is None else report.report.providers:
            pool = pool_of(record.host_id, provider.provider)
            slots.append(SlotUse(
                provider=provider.provider, access=provider.access,
                slots=slots_in_force(provider.access, journal.get((record.host_id, provider.provider))),
                in_use=store.pool_units(session, pool)))
        use = uses.get(record.host_id)
        facts.append(HostFacts(
            record=record, enabled=bool(use and use[0]), pulse_age_seconds=ages.get(record.host_id), report=report,
            slots=tuple(slots),
            cooldowns={(p, m): until for (h, p, m), until in cooldowns.items() if h == record.host_id},
            connections=tuple(row for row in connections if row.host_id == record.host_id), now=now))
    return facts


def model_availability(facts: HostFacts, catalogue: Catalogue | None = None) -> list[ModelAvailability]:
    """Every catalogue model the host's report names, with the reasons it cannot be used now. Computed from the facts alone: a model the
    report does not name is not listed here (its system connection, if any, is ``model_not_verified`` to anyone who asks about it:
    :func:`member_reasons`)."""
    book = catalogue or default_catalogue()
    found: list[ModelAvailability] = []
    if facts.report is None:
        return found
    for provider in facts.report.report.providers:
        slot = facts.slot_of(provider.provider)
        full = slot is not None and slot.in_use >= slot.slots
        for model in provider.models:
            if not book.serves(provider.provider, model.model_id, provider.access):
                continue
            until = facts.cooldowns.get((provider.provider, model.model_id))
            reasons = model_reasons(
                enabled=facts.enabled, pulse_age_seconds=facts.pulse_age_seconds, provider=provider, model=model,
                cooldown_until=until, now=facts.now)
            found.append(ModelAvailability(
                provider=provider.provider, access=provider.access, model_id=model.model_id,
                state=model_state(reasons, pool_full=full), reasons=tuple(reasons),
                cooldown_until=until if until is not None and until > facts.now else None))
    return found


def member_reasons(
    facts: HostFacts, *, provider: str, access: str, model_id: str
) -> tuple[list[str], bool]:
    """``(reasons, pool_full)`` for one system member -- a (provider, access, model) of this host, named by its connection. A provider,
    access or model the current report does not name is ``model_not_verified``: nothing is assumed."""
    report = None if facts.report is None else facts.report.report
    fact = None if report is None else report.provider(provider, access)
    model = None if fact is None else fact.model(model_id)
    reasons = model_reasons(
        enabled=facts.enabled, pulse_age_seconds=facts.pulse_age_seconds, provider=fact, model=model,
        cooldown_until=facts.cooldowns.get((provider, model_id)), now=facts.now)
    slot = facts.slot_of(provider)
    return reasons, slot is not None and slot.in_use >= slot.slots


def host_details(session: Session, host_id: str, *, repo: HostRepository | None = None) -> HostDetails:
    store = repo or HostRepository()
    found = read_hosts(session, [host_id], repo=store, include_archived=True)
    if not found:
        raise _not_found()
    facts = found[0]
    return HostDetails(
        facts=facts, models=tuple(model_availability(facts)), tasks=tuple(store.active_tasks(session, host_id)))


def host_claim_limit(session: Session, host_id: str, *, repo: HostRepository | None = None) -> int:
    """How many claims a host token may hold at once: the sum of the host's slots in force (at least one). This is the validation of
    ADR-0028 decision 4 -- «``max_claimed_tasks`` ≥ the sum of the slots» -- by construction: a host token has no revision to carry the figure,
    so the figure is never smaller than the sum."""
    found = read_hosts(session, [host_id], repo=repo or HostRepository(), include_archived=True)
    return max(1, found[0].slots_total) if found else 1


# --- the guard on --upgrade -------------------------------------------------------------------------------------------


_CONNECTION_USED = text(
    "SELECT EXISTS (SELECT 1 FROM executor_route_current r WHERE r.primary_connection_id = :c OR r.standby_connection_id = :c) "
    "OR EXISTS (SELECT 1 FROM executor_group g JOIN LATERAL (SELECT v.group_revision_id FROM executor_group_revision v "
    "WHERE v.group_id = g.group_id ORDER BY v.revision_no DESC LIMIT 1) cur ON true "
    "JOIN executor_group_member m ON m.group_revision_id = cur.group_revision_id "
    "WHERE g.archived_at IS NULL AND NOT g.system_managed AND m.connection_id = :c)"
)


def ensure_upgrade_allowed(session: Session, display_name: str) -> None:
    """The stand's half of the refusal of ``--upgrade`` (ADR-0028 decision 19, plan 5.7): a host enrollment under the name of a live
    single-model ``pull`` connection that a route, a rule or a comparison still uses would replace it, and the five ``comparison_*`` kinds
    still run on it until `HOSTS-CMP-01`. ``conflict`` / ``upgrade_blocked_by_use``, before anything is written; the connection is not named.

    The enrollment request carries a name and nothing else, so the name is the only handle there is: a host enrolled under another name
    is a new host, and the old agent stays as it is."""
    rows = session.execute(text(
        "SELECT connection_id FROM executor_connection WHERE NOT system_managed AND kind = 'pull' AND archived_at IS NULL "
        "AND lower(display_name) = lower(:name)"), {"name": display_name}).all()
    for row in rows:
        if session.execute(_CONNECTION_USED, {"c": str(row[0])}).scalar_one():
            raise DomainError(
                ErrorCode.CONFLICT, message="the single-model agent of this name is still used by a route or a rule",
                conflict_reason="upgrade_blocked_by_use", aggregate_type=_AGGREGATE_CONNECTION)


# --- enrollment: one grant, one host -------------------------------------------------------------------------------------


def _enroll_host(
    session: Session, *, name: str, actor_uid: str, hosts: HostRepository, journal: Journal,
) -> tuple[HostRecord, bool]:
    """The live host of this name, or a new one with its first «Использовать» event (a new host is on: the administrator who connected it
    made the mark). ``True`` when it is new. A host that exists gets a new grant (a move, or the upgrade of its agent)."""
    hosts.lock_name(session, name)
    existing = next((item for item in hosts.list_hosts(session) if item.display_name.lower() == name.lower()), None)
    if existing is not None:
        return _live_host(session, hosts, existing.host_id, lock=True), False
    host = hosts.insert_host(session, display_name=name, actor_uid=actor_uid)
    hosts.insert_use_event(session, host.host_id, enabled=True, actor_uid=actor_uid)
    journal(
        session, event_type="executor.host_created", aggregate_type=_AGGREGATE_HOST, aggregate_id=host.host_id,
        payload={"host_id": host.host_id, "enabled": True, "actor_uid": actor_uid})
    return host, True


def issue_host_enrollment(
    session: Session, *, display_name: str, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    configured_origin: str | None, hosts: HostRepository | None = None, grants: EnrollmentRepository | None = None,
    commands: CommandRepository | None = None, package_source: Callable[[], AgentPackage] = latest_package,
    journal: Journal = append_execution_event,
) -> IssuedEnrollment:
    """Make a host and issue its one-time grant, returning the secret and the install command **once** (no model in the command).

    A name a live host holds issues a *new* grant for that host and revokes the earlier unredeemed one (a move); a repeat of the same key
    answers ``conflict`` / ``enrollment_shown_once`` (the secret was never stored). Refusals, before anything is written: ``permission_denied``;
    ``dependency_unavailable`` / ``public_origin``; ``validation_failed`` on ``display_name``; ``conflict`` / ``upgrade_blocked_by_use``;
    ``dependency_unavailable`` / ``agent_package``."""
    _admin(roles)
    name = clean_display_name(display_name)
    origin = resolve_origin(configured_origin)
    store, grant_store, ledger = hosts or HostRepository(), grants or EnrollmentRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "issue_executor_host_enrollment", idempotency_key,
                     {"display_name": name, "actor_uid": actor_uid})
    if isinstance(claimed, CommandReplay):
        raise _conflict(CONFLICT_ENROLLMENT_SHOWN_ONCE, "the secret was shown once and cannot be shown again")
    ensure_upgrade_allowed(session, name)
    package = package_source()
    host, is_new = _enroll_host(session, name=name, actor_uid=actor_uid, hosts=store, journal=journal)
    online = store.pulse_ages(session, [host.host_id]).get(host.host_id)
    for revoked_id, was_live in grant_store.revoke_unredeemed_for_host(session, host.host_id, actor_uid=actor_uid):
        if was_live:
            journal(
                session, event_type="executor.enrollment_revoked", aggregate_type=_AGGREGATE_ENROLLMENT,
                aggregate_id=revoked_id, payload={"host_id": host.host_id, "actor_uid": actor_uid, "reason": "superseded"})
    value, prefix = generate_enrollment_secret()
    record = grant_store.insert_enrollment(
        session, host_id=host.host_id, secret_prefix=prefix, secret_hash=hash_enrollment_secret(value),
        lifetime_seconds=ENROLLMENT_LIFETIME_SECONDS, actor_uid=actor_uid)
    journal(
        session, event_type="executor.enrollment_issued", aggregate_type=_AGGREGATE_ENROLLMENT,
        aggregate_id=record.enrollment_id, payload={"host_id": host.host_id, "actor_uid": actor_uid})
    if online is not None and online <= 120 and not is_new:
        journal(
            session, event_type="executor.agent_move_requested", aggregate_type=_AGGREGATE_HOST, aggregate_id=host.host_id,
            payload={"host_id": host.host_id, "actor_uid": actor_uid, "reason": "online_agent"})
    ledger.succeed(session, claimed.command_id, {"enrollment_id": record.enrollment_id, "host_id": host.host_id})
    return IssuedEnrollment(
        record=record, secret=value, package=package,
        command=install_command(origin=origin, package=package, secret=value))


# --- the install session over SSH (path A), for a host ---------------------------------------------------------------


def create_host_agent_install(
    session: Session, *, display_name: str, access: str, ssh_host: str, ssh_port: int, ssh_user: str,
    private_key: str | None, ring: PublicRing | None, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    hosts: HostRepository | None = None, installs: InstallLifetimeRepository | None = None,
    commands: CommandRepository | None = None, package_source: Callable[[], AgentPackage] = latest_package,
    journal: Journal = append_execution_event,
) -> InstallRecord:
    """Make a host (or find the live one of this name) and record an install session of its agent in ``requested``.

    As ``agent_install.create_agent_install`` -- a key the stand generates or one pasted and sealed, never a password, the host key never trusted on
    first use -- but the target is a host and **no model is asked for**. The sealed key is an ``executor_secret`` of the host
    (``host_id`` set, no connection). Refusals, before anything is written: ``permission_denied``; ``validation_failed`` for the name, the
    target and the key as the contract states; ``conflict`` (``host_archived``, ``install_in_progress``, ``upgrade_blocked_by_use``);
    ``dependency_unavailable`` (``secrets_public_key_missing``, ``agent_package``)."""
    _admin(roles)
    name = clean_display_name(display_name)
    store, install_store, ledger = hosts or HostRepository(), installs or InstallLifetimeRepository(), commands or CommandRepository()
    _check_key_argument(access, private_key)
    _check_target(ssh_host, ssh_port, ssh_user)
    claimed = ledger.begin(
        session, command_type="create_executor_host_agent_install", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "display_name": name, "access": access, "ssh_host": ssh_host, "ssh_port": ssh_port, "ssh_user": ssh_user,
            "actor_uid": actor_uid}))
    if isinstance(claimed, CommandReplay):
        found = install_store.get_install(session, str(claimed.outcome["install_id"]))
        if found is None:
            raise _not_found(_AGGREGATE_INSTALL)
        return found
    ensure_upgrade_allowed(session, name)
    sealing = _need_ring(ring)
    package = package_source()
    host, _ = _enroll_host(session, name=name, actor_uid=actor_uid, hosts=store, journal=journal)
    expire_overdue_installs(session, install_store, host_id=host.host_id, journal=journal)
    if install_store.unfinished_install_of_host(session, host.host_id) is not None:
        raise _conflict(CONFLICT_INSTALL_IN_PROGRESS, "an install of this host has not finished", aggregate=_AGGREGATE_INSTALL)

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

    install_id = ExecutorAgentInstallId.new()
    secret_id = str(ExecutorSecretId.new())
    public_material: str | None = None
    if access == "generated_key":
        generated = Ed25519PrivateKey.generate()
        public_material = generated.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode("ascii")
        plaintext = generated.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
    else:
        assert private_key is not None
        plaintext = private_key.encode("utf-8")
    destination = install_destination(ssh_host=ssh_host, ssh_port=ssh_port, ssh_user=ssh_user)
    # The associated data names the owner of the secret: for a host, the host (`ExecutorRepository.sealed_secret` answers the same).
    kid, envelope = sealing.seal(plaintext, {
        "secret_id": secret_id, "connection_id": host.host_id, "purpose": INSTALL_PURPOSE, "destination": destination})
    install_store.insert_key(
        session, secret_id=secret_id, host_id=host.host_id, kid=kid, destination=destination, ciphertext=envelope,
        public_material=public_material, actor_uid=actor_uid)
    record = install_store.insert_install(
        session, install_id=install_id, host_id=host.host_id, access=access, ssh_host=ssh_host, ssh_port=ssh_port,
        ssh_user=ssh_user, key_secret_id=secret_id, package_version=package.version, package_sha256=package.sha256,
        actor_uid=actor_uid)
    journal(
        session, event_type="executor.agent_install_requested", aggregate_type=_AGGREGATE_INSTALL,
        aggregate_id=record.install_id,
        payload={"host_id": host.host_id, "secret_id": secret_id, "purpose": INSTALL_PURPOSE, "state": record.state,
                 "actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"install_id": record.install_id, "host_id": host.host_id})
    return record


def get_host_agent_install(
    session: Session, *, host_id: str, install_id: str, repository: InstallLifetimeRepository | None = None,
    journal: Journal = append_execution_event,
) -> InstallRecord:
    """The session, or ``not_found`` for an unknown one and for one of another host. An overdue session is finished as ``failed`` first (a write on a
    read: the caller commits it), exactly as for a connection."""
    installs = repository or InstallLifetimeRepository()
    found = installs.get_install(session, install_id)
    if found is None or found.host_id != host_id:
        raise _not_found(_AGGREGATE_INSTALL)
    if found.state in UNFINISHED_STATES and expire_overdue_installs(
        session, installs, host_id=host_id, install_id=install_id, journal=journal,
    ):
        found = installs.get_install(session, install_id)
        assert found is not None
    return found


def confirm_host_agent_install_host_key(
    session: Session, *, host_id: str, install_id: str, fingerprint: str, roles: Iterable[str], idempotency_key: str,
    actor_uid: str, repository: AgentInstallRepository | None = None, commands: CommandRepository | None = None,
    journal: Journal = append_execution_event,
) -> InstallRecord:
    """Record that the administrator read exactly the fingerprint the worker observed (as for a connection; no trust on first use)."""
    import re

    _admin(roles)
    installs, ledger = repository or AgentInstallRepository(), commands or CommandRepository()
    if re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", fingerprint) is None:
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="the fingerprint is not acceptable",
                          field="host_key_fingerprint", constraint="pattern")
    claimed = ledger.begin(
        session, command_type="confirm_executor_host_agent_install_host_key", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"host_id": host_id, "install_id": install_id, "host_key_fingerprint": fingerprint}))
    found = installs.get_install(session, install_id, lock=True)
    if found is None or found.host_id != host_id:
        raise _not_found(_AGGREGATE_INSTALL)
    if isinstance(claimed, CommandReplay):
        return found
    if found.confirmed_host_key_fingerprint is not None:
        if found.confirmed_host_key_fingerprint != fingerprint:
            raise _conflict(CONFLICT_HOST_KEY_CHANGED, "the fingerprint is not the one confirmed", aggregate=_AGGREGATE_INSTALL)
        ledger.succeed(session, claimed.command_id, {"install_id": install_id})
        return found
    if found.state != "awaiting_host_key":
        raise _conflict(CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
                        "the install is not waiting for a host key to be confirmed", aggregate=_AGGREGATE_INSTALL)
    if observed_fingerprint(found) != fingerprint:
        raise _conflict(CONFLICT_HOST_KEY_CHANGED, "the fingerprint is not the one observed", aggregate=_AGGREGATE_INSTALL)
    if not installs.confirm_host_key(session, install_id, fingerprint=fingerprint, actor_uid=actor_uid):
        raise _conflict(CONFLICT_INSTALL_NOT_AWAITING_HOST_KEY,
                        "the install is not waiting for a host key to be confirmed", aggregate=_AGGREGATE_INSTALL)
    confirmed = installs.get_install(session, install_id)
    assert confirmed is not None
    journal(
        session, event_type="executor.agent_install_host_key_confirmed", aggregate_type=_AGGREGATE_INSTALL,
        aggregate_id=install_id, payload={"host_id": host_id, "state": confirmed.state, "actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"install_id": install_id})
    return confirmed


# --- the system objects ------------------------------------------------------------------------------------------------


def _system_settings(model_id: str, access: str) -> RevisionSettings:
    return RevisionSettings(
        pin_id=model_id, gateway_model=model_id, billing=billing_of_access(access), allow_client_documents=False,
        timeout_seconds=_SYSTEM_TIMEOUT_SECONDS, pull_client="agent",
        answer_deadline_seconds=_SYSTEM_ANSWER_DEADLINE_SECONDS, max_claimed_tasks=1)


def _refresh_pair_group(
    session: Session, *, model_id: str, access: str, pins: Mapping[str, Any], hosts: HostRepository, groups: GroupRepository,
    actor_uid: str, journal: Journal,
) -> None:
    """Make the current revision of the pair's group hold exactly the live system connections of the pair (the oldest sixteen), writing a
    revision only when the membership differs, and archiving the group when no connection is left."""
    name = pair_group_name(model_id, access)
    billing = billing_of_access(access)
    groups.lock_name(session, name)
    group_id = hosts.system_group_for(session, name)
    live = hosts.live_members_of_pair(session, model_id=model_id, billing=billing)
    desired = live[:GROUP_MEMBERS_MAX]
    if len(live) > GROUP_MEMBERS_MAX:
        for connection_id, _revision in live[GROUP_MEMBERS_MAX:]:
            journal(
                session, event_type="executor.host_over_group_limit", aggregate_type=_AGGREGATE_CONNECTION,
                aggregate_id=connection_id, payload={"connection_id": connection_id, "model_id": model_id, "access": access})
    if group_id is None:
        if not desired:
            return
        group_id = hosts.insert_system_group(session, display_name=name, actor_uid=actor_uid)
    hosts.lock_group(session, group_id)
    current = hosts.current_group_members(session, group_id)
    if not desired:
        if current is not None:
            groups.archive_group(session, group_id, actor_uid=actor_uid)
            journal(session, event_type="executor.group_archived", aggregate_type="ExecutorGroup", aggregate_id=group_id,
                    payload={"actor_uid": actor_uid, "reason": "host_removed"})
        return
    if current is not None and sorted(current) == sorted(desired):
        return
    pin = pins[model_id]
    revision = groups.insert_revision(
        session, group_id=group_id, revision_no=groups.next_revision_no(session, group_id),
        settings=GroupSettings(pin_id=model_id, gateway_model=model_id, billing=billing, strategy=GROUP_STRATEGY_LEAST_LOADED),
        input_per_mtok_usd=Decimal(str(pin.input_per_mtok_usd)), output_per_mtok_usd=Decimal(str(pin.output_per_mtok_usd)),
        members=[MemberRequest(connection_id=cid, connection_revision_id=rid) for cid, rid in desired], actor_uid=actor_uid)
    journal(
        session, event_type="executor.group_revised" if current is not None else "executor.group_created",
        aggregate_type="ExecutorGroup", aggregate_id=group_id,
        payload={"revision_id": revision.group_revision_id, "revision_no": revision.revision_no, "actor_uid": actor_uid})


def sync_system_objects(
    session: Session, *, host: HostRecord, report: HostReport, enabled: bool, actor_uid: str,
    book: Catalogue | None = None, hosts: HostRepository | None = None, executors: ExecutorRepository | None = None,
    groups: GroupRepository | None = None, pins: Iterable[Any] | None = None, journal: Journal = append_execution_event,
) -> list[Quadruple]:
    """Make the host's system connections and the groups of their pairs follow its report. The caller holds the host's row lock.

    For every wanted quadruple with no live connection, one ``pull`` connection and its one revision; the connection gets the integration mark when
    the host is on. Then, for every affected pair, the group is brought up to date (:func:`_refresh_pair_group`) in ascending order of the pair, so
    two hosts connecting at once take the group locks in one order. A connection is never revised or removed here: what leaves the report is
    ``model_not_verified`` at read time, and only archiving the host removes its connections. Answers the quadruples created."""
    from auditmanager.analysis.public import pinned_models

    store, execs, group_store = hosts or HostRepository(), executors or ExecutorRepository(), groups or GroupRepository()
    wanted = desired_quadruples(report, book or default_catalogue())
    table = {pin.model_id: pin for pin in (pinned_models() if pins is None else pins)}
    live = {
        (row.provider, access_of_billing(row.billing), row.pin_id)
        for row in store.system_connections(session, [host.host_id]) if row.archived_at is None and row.revision_id is not None
    }
    created: list[Quadruple] = []
    for quad in wanted:
        if (quad.provider, quad.access, quad.model_id) in live or quad.model_id not in table:
            continue
        settings = validate_settings("pull", _system_settings(quad.model_id, quad.access), pinned_model_ids=table)
        connection_id = store.insert_system_connection(
            session, host_id=host.host_id, provider=quad.provider,
            display_name=f"{host.display_name} · {quad.provider} · {quad.access} · {quad.model_id}"[:120], actor_uid=actor_uid)
        execs.insert_revision(session, connection_id, settings, actor_uid=actor_uid)
        created.append(quad)
        journal(
            session, event_type="executor.host_model_found", aggregate_type=_AGGREGATE_CONNECTION, aggregate_id=connection_id,
            payload={"host_id": host.host_id, "connection_id": connection_id, "provider": quad.provider,
                     "access": quad.access, "model_id": quad.model_id})
    if created and enabled:
        store.set_integration_marks(session, host.host_id, authorised=True, actor_uid=actor_uid)
    for model_id, access in sorted({(quad.model_id, quad.access) for quad in created}):
        _refresh_pair_group(
            session, model_id=model_id, access=access, pins=table, hosts=store, groups=group_store, actor_uid=actor_uid,
            journal=journal)
    return created


# --- the report ------------------------------------------------------------------------------------------------------


def report_host_health(
    session: Session, *, host_id: str, token_id: str, agent_version: Any, providers: Any, slots: Any, key_file: Any = None,
    actor_uid: str | None = None, hosts: HostRepository | None = None, book: Catalogue | None = None,
    journal: Journal = append_execution_event, **maintenance: Any,
) -> tuple[bool, bool]:
    """Store what a host agent says about itself, **only when it changed**, and keep the system objects in step. Answers
    ``(changed, enabled)``.

    The snapshot is replaced only by a report whose :meth:`~auditmanager.executors.hosts.HostReport.change_key` differs from the stored one: a
    heartbeat that changes nothing writes nothing here (the pulse is the token's ``last_seen_at``, written by the runner authentication). A
    change clears the host's cooldowns (the agent has said what is true of every model), brings the system connections and groups up to date and goes
    to the executor journal. ``actor_uid`` is who the new rows are made on behalf of: the administrator who enrolled the host (the token's creator)."""
    store = hosts or HostRepository()
    report = normalise_host_report(agent_version=agent_version, providers=providers, slots=slots, key_file=key_file)
    host = store.get_host(session, host_id, lock=True)
    if host is None or host.archived_at is not None:
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    use = store.current_use(session, [host_id]).get(host_id)
    enabled = bool(use and use[0])
    key = report.change_key()
    stored = store.get_report(session, host_id)
    if stored is not None and stored.report_sha256 == key:
        return False, enabled
    store.write_report(session, host_id=host_id, token_id=token_id, report=report, report_sha256=key)
    store.clear_cooldowns(session, host_id)
    maker = actor_uid or host.created_by
    sync_system_objects(session, host=host, report=report, enabled=enabled, actor_uid=maker, book=book, hosts=store,
                        journal=journal, **maintenance)
    journal(
        session, event_type="executor.host_report_changed", aggregate_type=_AGGREGATE_HOST, aggregate_id=host_id,
        payload={"host_id": host_id, "state": "first" if stored is None else "changed"})
    return True, enabled


# --- «Использовать», slots, archive ----------------------------------------------------------------------------------


def set_host_enabled(
    session: Session, *, host_id: str, enabled: bool, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    hosts: HostRepository | None = None, commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> HostRecord:
    """Switch the server on or off. Append-only, with the author; the integration mark of its system connections follows the switch.

    ``permission_denied`` for anybody but an administrator; ``not_found``; ``conflict`` / ``host_archived``. Switching to the state the host is in
    appends nothing. A host that is off takes no new run; the runs already bound to it finish, and its token's claims go on."""
    _admin(roles)
    store, ledger = hosts or HostRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "set_executor_host_enabled", idempotency_key,
                     {"host_id": host_id, "enabled": enabled, "actor_uid": actor_uid})
    host = store.get_host(session, host_id, lock=True)
    if host is None:
        raise _not_found()
    if isinstance(claimed, CommandReplay):
        return host
    if host.archived_at is not None:
        raise _conflict("host_archived", "the host is archived")
    use = store.current_use(session, [host_id]).get(host_id)
    if use is None or use[0] != enabled:
        store.insert_use_event(session, host_id, enabled=enabled, actor_uid=actor_uid)
        store.set_integration_marks(session, host_id, authorised=enabled, actor_uid=actor_uid)
        journal(
            session, event_type="executor.host_use_changed", aggregate_type=_AGGREGATE_HOST, aggregate_id=host_id,
            payload={"host_id": host_id, "enabled": enabled, "actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"host_id": host_id})
    return host


def set_host_slots(
    session: Session, *, host_id: str, slots: Mapping[str, int], roles: Iterable[str], idempotency_key: str, actor_uid: str,
    hosts: HostRepository | None = None, commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> HostRecord:
    """Change the slots of the named providers, each a journalled event with its author (1 to 16).

    ``validation_failed`` on ``slots``: ``range``, or ``provider_not_reported`` for a provider the host's report does not name (nothing is assumed
    of a provider nobody has seen). A change to the number already in force appends nothing. A lowered number governs new binds only: a run that
    holds a unit keeps it."""
    _admin(roles)
    store, ledger = hosts or HostRepository(), commands or CommandRepository()
    if not slots:
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="no slots were named", field="slots", constraint="required")
    for count in slots.values():
        if type(count) is not int or not 1 <= count <= 16:
            raise DomainError(ErrorCode.VALIDATION_FAILED, message="slots are 1 to 16", field="slots", constraint="range")
    claimed = _begin(session, ledger, "set_executor_host_slots", idempotency_key,
                     {"host_id": host_id, "slots": dict(sorted(slots.items())), "actor_uid": actor_uid})
    host = store.get_host(session, host_id, lock=True)
    if host is None:
        raise _not_found()
    if isinstance(claimed, CommandReplay):
        return host
    if host.archived_at is not None:
        raise _conflict("host_archived", "the host is archived")
    stored = store.get_report(session, host_id)
    reported = {item.provider: item for item in (() if stored is None else stored.report.providers)}
    journal_now = store.slot_journal(session, [host_id])
    for provider, count in sorted(slots.items()):
        fact = reported.get(provider)
        if fact is None:
            raise DomainError(ErrorCode.VALIDATION_FAILED, message="the host does not report this provider",
                              field="slots", constraint="provider_not_reported")
        if slots_in_force(fact.access, journal_now.get((host_id, provider))) == count:
            continue
        store.insert_slot_event(session, host_id, provider=provider, slots=count, actor_uid=actor_uid)
        journal(
            session, event_type="executor.host_slots_changed", aggregate_type=_AGGREGATE_HOST, aggregate_id=host_id,
            payload={"host_id": host_id, "provider": provider, "slots": count, "actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"host_id": host_id})
    return host


def archive_host(
    session: Session, *, host_id: str, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    hosts: HostRepository | None = None, groups: GroupRepository | None = None, commands: CommandRepository | None = None,
    journal: Journal = append_execution_event, pins: Iterable[Any] | None = None,
) -> HostRecord:
    """Remove a server: archive it (one-way, never deleted: its identity stays in the call journal), revoke its tokens and pending grant, archive
    its system connections and bring the groups of its pairs up to date.

    ``conflict`` / ``host_in_use`` while a pool of the host still holds the unit of a run (a bound run finishes first). Archiving an archived host
    answers it as it stands and writes nothing."""
    from auditmanager.analysis.public import pinned_models

    _admin(roles)
    store, group_store, ledger = hosts or HostRepository(), groups or GroupRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, "archive_executor_host", idempotency_key, {"host_id": host_id, "actor_uid": actor_uid})
    host = store.get_host(session, host_id, lock=True)
    if host is None:
        raise _not_found()
    if isinstance(claimed, CommandReplay) or host.archived_at is not None:
        if not isinstance(claimed, CommandReplay):
            ledger.succeed(session, claimed.command_id, {"host_id": host_id})
        return host
    rows = store.system_connections(session, [host_id])
    pools = sorted({row.capacity_pool for row in rows})
    for pool in pools:  # the pool locks, ascending (ADR-0028 decision 15)
        store.lock_pool(session, pool)
    if any(store.pool_units(session, pool) > 0 for pool in pools):
        raise _conflict("host_in_use", "a bound run still holds a unit of this host")
    store.revoke_tokens_of(session, host_id, actor_uid=actor_uid)
    store.revoke_pending_grants(session, host_id, actor_uid=actor_uid)
    pairs = sorted({(row.pin_id, access_of_billing(row.billing)) for row in rows
                    if row.archived_at is None and row.pin_id is not None and row.billing is not None})
    store.archive_system_connections(session, host_id, actor_uid=actor_uid)
    archived = store.archive_host(session, host_id, actor_uid=actor_uid)
    table = {pin.model_id: pin for pin in (pinned_models() if pins is None else pins)}
    for model_id, access in pairs:
        if model_id in table:
            _refresh_pair_group(session, model_id=model_id, access=access, pins=table, hosts=store, groups=group_store,
                                actor_uid=actor_uid, journal=journal)
    journal(session, event_type="executor.host_archived", aggregate_type=_AGGREGATE_HOST, aggregate_id=host_id,
            payload={"host_id": host_id, "actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"host_id": host_id})
    return archived


# --- the passive cooldown --------------------------------------------------------------------------------------------


def record_task_failure(
    session: Session, *, host_id: str, provider: str | None, model_id: str | None, reason: str,
    hosts: HostRepository | None = None, journal: Journal = append_execution_event,
) -> datetime | None:
    """A host agent failed a task. When the failure is about the host's access -- a refusal, a quota, no such model (the first word of
    ``<code>: <detail>``) -- the (host, provider, model) leaves availability for :data:`~auditmanager.executors.hosts.COOLDOWN_SECONDS`
    (15 minutes), or until a changed report. Any other failure (a timeout, a bad answer, a lost claim) takes nothing out of service. Answers
    ``until`` when a cooldown was written."""
    code = cooldown_reason_of(reason)
    if code is None or provider is None or model_id is None:
        return None
    store = hosts or HostRepository()
    until = store.set_cooldown(session, host_id=host_id, provider=provider, model_id=model_id, seconds=COOLDOWN_SECONDS, reason=code)
    journal(
        session, event_type="executor.host_model_cooling_down", aggregate_type=_AGGREGATE_HOST, aggregate_id=host_id,
        payload={"host_id": host_id, "provider": provider, "model_id": model_id, "reason": code})
    return until


# --- the health report of a token, host or connection -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HostHealthAck:
    """What ``reportRunnerHealth`` answers a host token: when it was recorded, the catalogue it should check and the «Использовать» switch."""

    recorded_at: datetime
    catalogue: list[dict[str, Any]]
    enabled: bool
    changed: bool


def refuse_host_members_for_connection_token(*, providers: Any, slots: Any, key_file: Any) -> None:
    """``providers``, ``slots`` and ``key_file`` are required of a host token and **refused** of a connection token (RUNNER_API 10.9): a
    single-model agent speaks the earlier wire and nothing of the host's. ``validation_failed`` on the member."""
    for name, value in (("providers", providers), ("slots", slots), ("key_file", key_file)):
        if value is not None:
            raise DomainError(ErrorCode.VALIDATION_FAILED, message="a connection token takes no host report",
                              field=name, constraint="host_token_only")


def report_host_runner_health(
    session: Session, *, token_id: str, host_id: str, agent_version: Any, clis: Any, concurrency: Any,
    execution_profile: Any, features: Any, providers: Any, slots: Any, key_file: Any = None,
    book: Catalogue | None = None, hosts: HostRepository | None = None, journal: Journal = append_execution_event,
    **maintenance: Any,
) -> HostHealthAck:
    """The report of a host token: the token's health as for any runner (``enrollment.report_runner_health``, which replaces itself and is not
    journaled), then the host's snapshot **only when it changed** (:func:`report_host_health`). ``validation_failed`` on ``providers`` when a host
    token sends none. The answer carries the catalogue and the switch."""
    from auditmanager.executors.enrollment import report_runner_health

    if providers is None:
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="a host token reports its providers",
                          field="providers", constraint="required")
    recorded = report_runner_health(
        session, token_id, agent_version=agent_version, clis=clis, concurrency=concurrency,
        execution_profile=execution_profile, features=features)
    token_creator = session.execute(text(
        "SELECT created_by FROM executor_runner_token WHERE token_id = :t"), {"t": token_id}).scalar_one_or_none()
    changed, enabled = report_host_health(
        session, host_id=host_id, token_id=token_id, agent_version=agent_version, providers=providers, slots=slots,
        key_file=key_file, actor_uid=token_creator, hosts=hosts, book=book, journal=journal, **maintenance)
    return HostHealthAck(recorded_at=recorded, catalogue=(book or default_catalogue()).for_agent(), enabled=enabled, changed=changed)
