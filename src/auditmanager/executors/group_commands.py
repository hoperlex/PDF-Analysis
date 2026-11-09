"""The administrator's commands on executor groups and routing rules, and the reads that go with them (`EXEC2-GROUP-STORE-01`).

Each command follows ``commands.py``: (1) the role check, (2) the rules that need no row (the name, the pin, the
number of members, a duplicate), (3) ``CommandRepository.begin`` with an idempotency key and a payload fingerprint
that names the acting administrator (a key belongs to the actor who spent it), (4) the locks, in ADR-0026 decision
14's order -- the group's row, then the member connections in ascending ``connection_id`` -- (5) the preconditions
that read rows, each a typed refusal, (6) the write, (7) an ``executor.``-prefixed journal event whose payload holds
identities and classifiers only (the group and rule identities are the event's ``aggregate_id``; the payload keys
are the ones ``jobs.events`` allows), (8) ``ledger.succeed`` with the identities of what was made. A replay answers
the resource as it stands now. The caller owns the transaction, and a refusal ends it: a refused request leaves
nothing behind, not even its key.

**What a group snapshots.** Each member is a connection and the connection's *current* revision at the moment the
group revision is made. The members' revisions must pin the group revision's ``pin_id`` and ``gateway_model`` and
share its ``billing`` (:func:`~auditmanager.executors.groups.refuse_member`); a group is never mixed. The rates are
the provider lock's for ``pin_id``, copied once into the revision. A revision is immutable and referenced by rules
and (from stage 3) by work admitted on it: nothing here deletes or rewrites one, and archiving a group is one-way and
leaves every revision readable. The membership is closed with the revision: ``insert_revision`` declares
``member_count`` as the number of members of the request and writes them in the same transaction, and the database
refuses a member beyond that number and a commit that holds fewer.

**Reads.** The list, the detail, the capacity and the rules are for any role (``api/security.py``); they do not take
the role set. Dispatch (``EXEC2-GROUP-RUN-01`` and ``EXEC2-GROUP-CMP-01``) reaches these functions through
``executors.public`` and never reads the group tables.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ModelPin
from auditmanager.executors.group_repository import GroupRepository
from auditmanager.executors.group_selection import MemberFacts, member_issue
from auditmanager.executors.groups import (
    AGGREGATE_GROUP,
    AGGREGATE_RULE,
    GroupCapacity,
    GroupDetail,
    GroupRecord,
    GroupRevisionRecord,
    GroupSettings,
    GroupSummary,
    MemberRequest,
    MemberStatus,
    ModeState,
    RuleListing,
    RuleRecord,
    clean_display_name,
    group_archived,
    group_name_in_use,
    group_not_found,
    group_revision_not_found,
    group_routed,
    refuse_member,
    refuse_settings,
    refuse_work_kind,
)
from auditmanager.executors.model import refuse_system_object
from auditmanager.executors.queries import Occupancy, occupancies
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.usability import is_probed_ok, is_served
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
    "advance_group_rotation",
    "append_rule",
    "archive_group",
    "create_group",
    "group_capacity",
    "group_detail",
    "group_revision_of",
    "group_summary",
    "list_group_summaries",
    "list_routing_rules",
    "make_group",
    "member_facts",
    "resolve_rule",
    "revise_group",
    "routing_mode",
    "set_routing_rule",
]

_CREATE = "create_executor_group"
_REVISE = "revise_executor_group"
_ARCHIVE = "archive_executor_group"
_SET_RULE = "set_executor_routing_rule"

Journal = Callable[..., None]


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _begin(
    session: Session, ledger: CommandRepository, command_type: str, idempotency_key: str,
    payload: dict[str, object],
) -> CommandStarted | CommandReplay:
    return ledger.begin(
        session, command_type=command_type, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(payload),
    )


def _inconsistent(what: str) -> DomainError:
    """A state the schema forbids (a group with no revision, a member with no connection). Not a user error."""
    return DomainError(ErrorCode.INTERNAL_ERROR, message=what)


def _settings_payload(settings: GroupSettings) -> dict[str, object]:
    return {"pin_id": settings.pin_id, "gateway_model": settings.gateway_model, "billing": settings.billing,
            "strategy": settings.strategy}


def _members_payload(members: Sequence[MemberRequest]) -> list[list[object]]:
    """The members as the ledger compares them: by connection, so the order they were listed in is not a difference."""
    return [[member.connection_id, member.connection_revision_id, member.tie_break_order]
            for member in sorted(members, key=lambda item: item.connection_id)]


# --- reads ---------------------------------------------------------------------------------------------------------


def _summaries(
    session: Session, groups: GroupRepository, records: Sequence[GroupRecord]
) -> tuple[GroupSummary, ...]:
    currents = groups.current_revisions(session, [record.group_id for record in records])
    routed: dict[str, set[str]] = {}
    for rule in groups.current_rules(session):
        routed.setdefault(rule.group_id, set()).add(rule.work_kind)
    found = []
    for record in records:
        current = currents.get(record.group_id)
        if current is None:
            raise _inconsistent("an executor group has no revision")
        found.append(GroupSummary(
            group=record, current_revision=current,
            routed_work_kinds=tuple(sorted(routed.get(record.group_id, ()))),
        ))
    return tuple(found)


def list_group_summaries(
    session: Session, groups: GroupRepository | None = None
) -> tuple[GroupSummary, ...]:
    """Every group with its current revision and the work kinds whose current rule names it, archived ones last."""
    store = groups or GroupRepository()
    return _summaries(session, store, store.list_groups(session))


def group_summary(
    session: Session, group_id: str, groups: GroupRepository | None = None
) -> GroupSummary:
    """One group as it stands; ``not_found`` for one that does not exist. An archived group still answers."""
    store = groups or GroupRepository()
    record = store.get_group(session, group_id)
    if record is None:
        raise group_not_found()
    (summary,) = _summaries(session, store, [record])
    return summary


def group_detail(
    session: Session, group_id: str, groups: GroupRepository | None = None
) -> GroupDetail:
    """A group and every revision of it, newest first, members included."""
    store = groups or GroupRepository()
    summary = group_summary(session, group_id, store)
    return GroupDetail(summary=summary, revisions=tuple(store.list_revisions(session, group_id)))


def group_revision_of(
    session: Session, group_revision_id: str, groups: GroupRepository | None = None
) -> GroupRevisionRecord | None:
    """One immutable revision with its members, or ``None``. What a Run or a job admitted on it reads back."""
    return (groups or GroupRepository()).get_revision(session, group_revision_id)


def routing_mode(session: Session, groups: GroupRepository | None = None) -> ModeState:
    """The routing mode in force: the latest event of the journal, ``legacy`` while the journal is empty."""
    return (groups or GroupRepository()).current_mode(session)


def list_routing_rules(session: Session, groups: GroupRepository | None = None) -> RuleListing:
    """The current rule of each work kind that has one, and the mode. While the mode is ``legacy`` the rules exist
    and nothing reads them."""
    store = groups or GroupRepository()
    return RuleListing(routing_mode=store.current_mode(session), rules=tuple(store.current_rules(session)))


def resolve_rule(
    session: Session, work_kind: str, groups: GroupRepository | None = None
) -> RuleRecord | None:
    """The current rule of a work kind, or ``None`` when it has none. Admission (stage 3) resolves a rule here and
    freezes the rule revision and the group revision it names; it does not read the group tables itself."""
    return (groups or GroupRepository()).current_rule(session, work_kind)


def advance_group_rotation(
    session: Session, group_id: str, groups: GroupRepository | None = None
) -> int:
    """Advance the group's persisted tie-break rotation by one and return the new value. The dispatcher calls it under
    the group's row lock after it has chosen a member."""
    return (groups or GroupRepository()).advance_rotation(session, group_id)


def _facts(
    session: Session, revision: GroupRevisionRecord, store: ExecutorRepository
) -> list[tuple[MemberFacts, Occupancy, str | None]]:
    """For each member of the revision: the facts (:class:`MemberFacts`), its occupancy and the connection's
    current revision id. Read from the rows now; nothing is stored. The probe of a member is read on the
    connection's *current* revision (a member whose revision changed is reported first for that)."""
    ids = [member.connection_id for member in revision.members]
    currents = store.current_revisions(session, ids)
    counts = occupancies(session, ids, store)
    found = []
    for member in revision.members:
        connection = store.get_connection(session, member.connection_id)
        occupancy = counts.get(member.connection_id)
        if connection is None or occupancy is None:
            raise _inconsistent("a group member has no connection")
        current = currents.get(member.connection_id)
        served = current is not None and is_served(connection, current)
        probed = current is not None and is_probed_ok(session, store, connection, current)
        online = connection.kind != "pull" or store.runner_online(session, member.connection_id)
        found.append((
            MemberFacts(
                connection_id=member.connection_id, tie_break_order=member.tie_break_order,
                revision_is_snapshot=(
                    current is not None and current.revision_id == member.connection_revision_id),
                archived=connection.archived_at is not None, served=served, probed_ok=probed,
                runner_online=online, capacity=occupancy.capacity, used=occupancy.used,
            ),
            occupancy,
            None if current is None else current.revision_id,
        ))
    return found


def member_facts(
    session: Session, revision: GroupRevisionRecord, repository: ExecutorRepository | None = None
) -> list[MemberFacts]:
    """What is true of each member of ``revision`` right now, in the revision's member order. The dispatcher takes the
    members whose :func:`~auditmanager.executors.group_selection.member_issue` is ``None`` or ``at_capacity`` and
    chooses among them with :func:`~auditmanager.executors.group_selection.choose`, under the locks of decision 14."""
    return [facts for facts, _, _ in _facts(session, revision, repository or ExecutorRepository())]


def group_capacity(
    session: Session, group_id: str, repository: ExecutorRepository | None = None,
    groups: GroupRepository | None = None,
) -> GroupCapacity:
    """The capacity of a group's current revision as dispatch would see it right now (decisions 1 and 14).

    Per member: the snapshot, the connection's current revision, its occupancy (``EXEC2-CAP-01``'s units) and the first
    reason dispatch would not choose it. ``capacity`` and ``used`` sum the members in service -- not archived, current
    revision equal to the snapshot -- and ``waiting`` counts the work admitted on any revision of the group that is
    still ``pending``. A write transaction: the read ends the probes nobody can still be running, as the connection
    detail does.
    """
    store, repo = repository or ExecutorRepository(), groups or GroupRepository()
    store.sweep_probes(session)
    record = repo.get_group(session, group_id)
    if record is None:
        raise group_not_found()
    revision = repo.current_revisions(session, [group_id]).get(group_id)
    if revision is None:
        raise _inconsistent("an executor group has no revision")
    if record.system_managed:
        return _system_group_capacity(session, record, revision, store, repo)
    rows = _facts(session, revision, store)
    in_service = [facts for facts, _, _ in rows if facts.in_service]
    return GroupCapacity(
        group_id=group_id, group_revision_id=revision.group_revision_id,
        members=tuple(
            MemberStatus(
                connection_id=facts.connection_id,
                snapshot_revision_id=member.connection_revision_id,
                current_revision_id=current_id, occupancy=occupancy, issue=member_issue(facts),
            )
            for member, (facts, occupancy, current_id) in zip(revision.members, rows, strict=True)
        ),
        capacity=sum(facts.capacity for facts in in_service),
        used=sum(facts.used for facts in in_service),
        waiting=repo.pending_count(session, group_id),
    )


def _system_group_capacity(
    session: Session, record: GroupRecord, revision: GroupRevisionRecord, store: ExecutorRepository, repo: GroupRepository,
) -> GroupCapacity:
    """The capacity of a **system** group (`HOSTS-BACKEND-01`, ADR-0028 decisions 3 and 16): each member is a system connection of a host, its
    occupancy is that of its capacity **pool** (the units the pool's runs and calls hold against the host's slots of the provider), and the issue
    that keeps it from being chosen is read from the host's facts -- the unavailability reasons, then ``at_capacity``.

    The reasons come **before** ``at_capacity`` here, whatever the enumeration's order, so that a member whose only issue is ``at_capacity`` is one
    that is available and busy (``MemberStatus.eligible`` is the absence of any issue). ``host_offline`` is reported as ``runner_offline`` and
    ``login_required`` as ``model_not_verified``: the contract has no words of its own for them."""
    from auditmanager.executors.group_selection import ISSUE_AT_CAPACITY, ISSUE_CONNECTION_ARCHIVED, ISSUE_REVISION_CHANGED
    from auditmanager.executors.host_commands import member_reasons, read_hosts
    from auditmanager.executors.hosts import (
        REASON_HOST_DISABLED, REASON_HOST_OFFLINE, REASON_LOGIN_REQUIRED, REASON_MODEL_COOLING_DOWN,
        REASON_MODEL_NOT_VERIFIED, access_of_billing, split_pool,
    )

    ids = [member.connection_id for member in revision.members]
    currents = store.current_revisions(session, ids)
    connections = {cid: store.get_connection(session, cid) for cid in ids}
    host_ids = sorted({split_pool(conn.capacity_pool)[0] for conn in connections.values()
                       if conn is not None and conn.capacity_pool is not None})
    hosts = {item.record.host_id: item for item in read_hosts(session, host_ids, include_archived=True)}
    statuses: list[MemberStatus] = []
    capacity = used = 0
    for member in revision.members:
        connection = connections.get(member.connection_id)
        if connection is None or connection.capacity_pool is None:
            raise _inconsistent("a system group member has no connection")
        host_id, provider = split_pool(connection.capacity_pool)
        host = hosts[host_id]
        current = currents.get(member.connection_id)
        slot = host.slot_of(provider)
        occupancy = Occupancy(capacity=0 if slot is None else slot.slots, active_runs=0 if slot is None else slot.in_use, active_calls=0)
        issue: str | None = None
        if current is None or current.revision_id != member.connection_revision_id:
            issue = ISSUE_REVISION_CHANGED
        elif connection.archived_at is not None or host.record.archived_at is not None:
            issue = ISSUE_CONNECTION_ARCHIVED
        else:
            reasons, _full = member_reasons(
                host, provider=provider, access=access_of_billing(current.settings.billing), model_id=revision.pin_id)
            issue = next((word for reason, word in (
                (REASON_HOST_OFFLINE, "runner_offline"), (REASON_HOST_DISABLED, "host_disabled"),
                (REASON_LOGIN_REQUIRED, "model_not_verified"), (REASON_MODEL_NOT_VERIFIED, "model_not_verified"),
                (REASON_MODEL_COOLING_DOWN, "model_cooling_down")) if reason in reasons), None)
            if issue is None and not occupancy.has_free_unit:
                issue = ISSUE_AT_CAPACITY
            if current.revision_id == member.connection_revision_id:
                capacity += occupancy.capacity
                used += occupancy.used
        statuses.append(MemberStatus(
            connection_id=member.connection_id, snapshot_revision_id=member.connection_revision_id,
            current_revision_id=None if current is None else current.revision_id, occupancy=occupancy, issue=issue))
    return GroupCapacity(
        group_id=record.group_id, group_revision_id=revision.group_revision_id, members=tuple(statuses),
        capacity=capacity, used=used, waiting=repo.pending_count(session, record.group_id))


# --- commands --------------------------------------------------------------------------------------------------------


def _rates(pins: dict[str, ModelPin], pin_id: str) -> tuple[Decimal, Decimal]:
    pin = pins[pin_id]
    return Decimal(str(pin.input_per_mtok_usd)), Decimal(str(pin.output_per_mtok_usd))


def _refuse_members(
    session: Session, store: ExecutorRepository, groups: GroupRepository, settings: GroupSettings,
    members: Sequence[MemberRequest],
) -> None:
    """Hold decision 10 against the rows, before anything is written: lock the member connections (ascending, shared),
    read their current revisions and refuse the first member that does not fit."""
    existing = groups.lock_connections(session, [member.connection_id for member in members])
    currents = store.current_revisions(session, sorted(existing))
    for member in members:
        connection = (
            store.get_connection(session, member.connection_id) if member.connection_id in existing else None)
        if connection is not None and connection.system_managed:
            raise refuse_system_object()
        current = currents.get(member.connection_id)
        refuse_member(
            settings, member, connection=connection,
            named=store.get_revision(session, member.connection_revision_id),
            current=current,
            served=connection is not None and current is not None and is_served(connection, current),
        )


def make_group(
    session: Session, *, name: str, settings: GroupSettings, members: Sequence[MemberRequest],
    table: dict[str, ModelPin], store: ExecutorRepository, repo: GroupRepository, actor_uid: str,
    journal: Journal,
) -> tuple[GroupRecord, GroupRevisionRecord]:
    """The writes of :func:`create_group` after its key is claimed: hold decision 10 against the rows (the member
    connections locked ascending, their current revisions read, the first member that does not fit refused), take the
    name, insert the group and its first revision with its members (``member_count`` is the number of members of the
    request) and journal ``executor.group_created``.

    ``table`` maps each pinned ``model_id`` to its pin, as :func:`create_group` builds it; the caller has already held the
    settings and the members against it (:func:`~auditmanager.executors.groups.refuse_settings`). The routing-mode
    cut-over (`EXEC2-CUTOVER-01`) calls this once per work kind inside its own transaction and its own key, so it has
    the validation, the database checks and the event of a group made by hand, and no second path that could drift. It
    claims no key and succeeds no command: that is the caller's."""
    _refuse_members(session, store, repo, settings, members)
    repo.lock_name(session, name)
    if repo.name_in_use(session, name):
        raise group_name_in_use()
    record = repo.insert_group(session, display_name=name, actor_uid=actor_uid)
    rate_in, rate_out = _rates(table, settings.pin_id)
    revision = repo.insert_revision(
        session, group_id=record.group_id, revision_no=repo.next_revision_no(session, record.group_id),
        settings=settings, input_per_mtok_usd=rate_in, output_per_mtok_usd=rate_out, members=members,
        actor_uid=actor_uid,
    )
    journal(
        session, event_type="executor.group_created", aggregate_type=AGGREGATE_GROUP,
        aggregate_id=record.group_id,
        payload={"revision_id": revision.group_revision_id, "revision_no": revision.revision_no,
                 "actor_uid": actor_uid},
    )
    return record, revision


def create_group(
    session: Session, *, display_name: str, settings: GroupSettings, members: Sequence[MemberRequest],
    pins: Iterable[ModelPin], roles: Iterable[str], idempotency_key: str, actor_uid: str,
    repository: ExecutorRepository | None = None, groups: GroupRepository | None = None,
    commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> GroupSummary:
    """Create a group and its first revision, or refuse before anything is written.

    Refusals, in this order: ``permission_denied``; ``validation_failed`` for the name, the pin
    (``model_not_pinned``), the billing, the strategy, the number of members (``range``), a duplicate member
    (``member_repeated``) and a repeated or out-of-range tie-break order; then, per member in the order listed,
    ``members`` / ``unknown_executor_connection``, ``409 connection_archived``, ``member_revision_not_of_connection``
    (the revision named is not the connection's current one), ``member_kind_not_served``, and ``member_pin_mismatch``,
    ``member_model_mismatch`` or ``member_billing_mismatch``; ``409 group_name_in_use`` for a name an active group
    holds. Every one leaves no row."""
    _admin(roles)
    name = clean_display_name(display_name)
    table = {pin.model_id: pin for pin in pins}
    refuse_settings(settings, members, pinned_model_ids=table)
    store, repo, ledger = repository or ExecutorRepository(), groups or GroupRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, _CREATE, idempotency_key, {
        "display_name": name, "settings": _settings_payload(settings), "members": _members_payload(members),
        "actor_uid": actor_uid})
    if isinstance(claimed, CommandReplay):
        return group_summary(session, str(claimed.outcome["group_id"]), repo)
    record, revision = make_group(
        session, name=name, settings=settings, members=members, table=table, store=store, repo=repo,
        actor_uid=actor_uid, journal=journal)
    ledger.succeed(session, claimed.command_id, {
        "group_id": record.group_id, "group_revision_id": revision.group_revision_id})
    return group_summary(session, record.group_id, repo)


def revise_group(
    session: Session, *, group_id: str, settings: GroupSettings, members: Sequence[MemberRequest],
    pins: Iterable[ModelPin], roles: Iterable[str], idempotency_key: str, actor_uid: str,
    repository: ExecutorRepository | None = None, groups: GroupRepository | None = None,
    commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> GroupSummary:
    """Add an immutable revision with the full settings, never a patch. Work already admitted on an earlier
    revision finishes on it, and a rule that names it is not moved.

    The refusals of :func:`create_group` for the settings and the members, and ``404 not_found`` for a group that
    does not exist and ``409 group_archived`` for an archived one. A revision may keep the settings and the members
    of the previous one: an unchanged revision is still a revision."""
    _admin(roles)
    table = {pin.model_id: pin for pin in pins}
    refuse_settings(settings, members, pinned_model_ids=table)
    store, repo, ledger = repository or ExecutorRepository(), groups or GroupRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, _REVISE, idempotency_key, {
        "group_id": group_id, "settings": _settings_payload(settings), "members": _members_payload(members),
        "actor_uid": actor_uid})
    if isinstance(claimed, CommandReplay):
        return group_summary(session, str(claimed.outcome["group_id"]), repo)
    record = repo.get_group(session, group_id, lock=True)
    if record is None:
        raise group_not_found()
    if record.system_managed:
        raise refuse_system_object("ExecutorGroup")
    if record.archived_at is not None:
        raise group_archived()
    _refuse_members(session, store, repo, settings, members)
    rate_in, rate_out = _rates(table, settings.pin_id)
    revision = repo.insert_revision(
        session, group_id=group_id, revision_no=repo.next_revision_no(session, group_id), settings=settings,
        input_per_mtok_usd=rate_in, output_per_mtok_usd=rate_out, members=members, actor_uid=actor_uid,
    )
    journal(
        session, event_type="executor.group_revised", aggregate_type=AGGREGATE_GROUP, aggregate_id=group_id,
        payload={"revision_id": revision.group_revision_id, "revision_no": revision.revision_no,
                 "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {
        "group_id": group_id, "group_revision_id": revision.group_revision_id})
    return group_summary(session, group_id, repo)


def archive_group(
    session: Session, *, group_id: str, roles: Iterable[str], idempotency_key: str, actor_uid: str,
    groups: GroupRepository | None = None, commands: CommandRepository | None = None,
    journal: Journal = append_execution_event,
) -> GroupSummary:
    """Archive a group: one-way, a soft archive. Every revision and member stays readable and referenced; the group
    takes no further revision or rule, and its name is free again.

    ``404 not_found``; ``409 group_routed`` while a rule still names the group (change the rule first); archiving an
    archived group answers it as it stands and writes nothing."""
    _admin(roles)
    repo, ledger = groups or GroupRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, _ARCHIVE, idempotency_key, {"group_id": group_id, "actor_uid": actor_uid})
    if isinstance(claimed, CommandReplay):
        return group_summary(session, str(claimed.outcome["group_id"]), repo)
    record = repo.get_group(session, group_id, lock=True)
    if record is None:
        raise group_not_found()
    if record.system_managed:
        raise refuse_system_object("ExecutorGroup")
    if record.archived_at is None:
        if any(rule.group_id == group_id for rule in repo.current_rules(session)):
            raise group_routed()
        repo.archive_group(session, group_id, actor_uid=actor_uid)
        journal(
            session, event_type="executor.group_archived", aggregate_type=AGGREGATE_GROUP,
            aggregate_id=group_id, payload={"actor_uid": actor_uid},
        )
    ledger.succeed(session, claimed.command_id, {"group_id": group_id})
    return group_summary(session, group_id, repo)


def set_routing_rule(
    session: Session, *, work_kind: str, group_revision_id: str, roles: Iterable[str],
    idempotency_key: str, actor_uid: str, groups: GroupRepository | None = None,
    commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> RuleRecord:
    """Point the rule of ``work_kind`` at an immutable group revision. Append-only: a change adds a rule revision, and
    naming the revision that is already current answers the rule as it stands and appends nothing. Work already
    admitted keeps the rule revision it was admitted on.

    ``validation_failed`` on ``work_kind`` for a value the enumeration does not name; ``404 not_found`` for a group
    revision that does not exist; ``409 group_archived`` for the revision of an archived group. The group's row is
    locked before the check, and archiving locks it before looking for a rule, so a group cannot be archived and
    named at the same moment."""
    _admin(roles)
    refuse_work_kind(work_kind)
    repo, ledger = groups or GroupRepository(), commands or CommandRepository()
    claimed = _begin(session, ledger, _SET_RULE, idempotency_key, {
        "work_kind": work_kind, "group_revision_id": group_revision_id, "actor_uid": actor_uid})
    if isinstance(claimed, CommandReplay):
        found = repo.get_rule(session, str(claimed.outcome["rule_revision_id"]))
        if found is None:
            raise group_revision_not_found()
        return found
    revision = repo.get_revision(session, group_revision_id)
    if revision is None:
        raise group_revision_not_found()
    record = repo.get_group(session, revision.group_id, lock=True)
    if record is None:
        raise group_not_found()
    if record.system_managed:
        raise refuse_system_object("ExecutorGroup")
    if record.archived_at is not None:
        raise group_archived()
    rule = append_rule(
        session, work_kind=work_kind, group_revision_id=group_revision_id, repo=repo, actor_uid=actor_uid,
        journal=journal)
    ledger.succeed(session, claimed.command_id, {"rule_revision_id": rule.rule_revision_id})
    return rule


def append_rule(
    session: Session, *, work_kind: str, group_revision_id: str, repo: GroupRepository, actor_uid: str,
    journal: Journal,
) -> RuleRecord:
    """The write of :func:`set_routing_rule` after its checks: take the work kind's rule lock, answer the rule as it
    stands when it already names ``group_revision_id`` (nothing is appended and nothing journaled), else append the next
    rule and journal ``executor.routing_rule_set``.

    The caller holds the row of the group the revision belongs to -- ``FOR UPDATE`` (:func:`set_routing_rule`) or, for a
    group made in the same transaction (`EXEC2-CUTOVER-01`), the insert itself -- so the group is not being archived,
    and has checked that the revision exists. A key is claimed and succeeded by the caller."""
    repo.lock_rule(session, work_kind)
    current = repo.current_rule(session, work_kind)
    if current is not None and current.group_revision_id == group_revision_id:
        return current
    rule = repo.insert_rule(
        session, work_kind=work_kind, group_revision_id=group_revision_id, actor_uid=actor_uid)
    journal(
        session, event_type="executor.routing_rule_set", aggregate_type=AGGREGATE_RULE,
        aggregate_id=rule.rule_revision_id,
        payload={"work_kind": work_kind, "revision_id": group_revision_id, "revision_no": rule.rule_no,
                 "actor_uid": actor_uid},
    )
    return rule
