"""The cut-over from the legacy Primary/Standby routes to the routing rules, and the way back (`EXEC2-CUTOVER-01`, ADR-0026
decision 17).

Two administrator operations of contract 1.16.0 and the guard that makes the legacy routes read-only once the cut-over is
done.

**The preview** (``previewExecutorRouting``) writes nothing. For each of the six work kinds it reads the current legacy
route and proposes what the cut-over would make of it: a one-member group of the **current revision** of the route's
*primary* connection, named :attr:`PreviewItem.proposed_group_name`.

====================  ==========================================================================================
``ready``             the route has a primary that is not archived, has a current revision, and whose kind this
                      release serves; the item carries that revision, its pin, gateway model and billing and the
                      proposed name
``no_route``          the work kind has no legacy route, so the cut-over gives it no rule
``incompatible``      the route exists and cannot become a group; ``incompatible_reason`` is ``connection_archived``,
                      ``no_revision`` or ``kind_not_served`` (the first that applies, in that order)
====================  ==========================================================================================

A **standby is shown and never converted**: ``standby_connection_id`` is on the item whenever the route has one, and no
group is made from it. A standby is used only at a run start, with an event (``audit_run.standby_used``); rules never
use one. Whether the primary has passed a probe is not a preview status (the contract names no such issue) and is not
checked here: a member that has not is reported by the group's capacity as ``probe_not_ok`` and dispatch does not choose
it, so work for it waits visibly instead of going elsewhere.

``preview_digest`` is the SHA-256 of the canonical JSON (sorted keys, no whitespace, UTF-8) of the six items exactly as
they are shown, in the order of :data:`~auditmanager.executors.model.WORK_KINDS`, behind a fixed domain line
(:data:`DIGEST_DOMAIN`). It does not cover ``routing_mode``. A proposed name is a function of the names the active groups
hold, so making or archiving a group changes the digest of a preview that proposed it.

**The cut-over** (``setExecutorRoutingMode`` to ``rules``) takes the digest that was shown and the mapping the
administrator confirmed: for each work kind to convert, the name of the one-member group to make. It is one transaction:

1. the command ledger row for ``set_executor_routing_mode`` and the caller's key (a repeat replays; the same key with
   another payload is the ledger's ``idempotency_key_reuse``);
2. ``pg_advisory_xact_lock(hashtextextended('executor_routing_mode_event', 0))`` -- the journal's lock, which the insert
   trigger takes too and ``setExecutorRoute`` takes first, so a route change and a mode change are serialised and two
   cut-overs cannot interleave;
3. the mode is read; naming the mode it already is is ``conflict`` / ``routing_mode_unchanged``;
4. the six routes are read, the primaries' ``executor_connection`` rows are locked ``FOR SHARE`` in ascending
   ``connection_id`` (decision 14's order for connections), and the preview is **recomputed under those locks**; a digest
   that is not the recomputed one is ``conflict`` / ``preview_stale``, and a mapping entry for a work kind that is not
   ``ready`` is ``validation_failed`` / ``mapping_entry_not_ready``;
5. per mapped work kind, in the order of ``WORK_KINDS``: the group, its first revision (``member_count`` = 1) and its one
   member, by :func:`~auditmanager.executors.group_commands.make_group` -- the very code of ``createExecutorGroup``, with
   the same validation, the database checks and the ``executor.group_created`` event -- and the rule, by
   :func:`~auditmanager.executors.group_commands.append_rule`, with ``executor.routing_rule_set``;
6. the ``rules`` event of ``executor_routing_mode_event``, numbered the highest plus one under the lock of step 2, carrying
   the digest and one entry per converted work kind (the work kind, the group, the group revision and the rule revision
   the change created), and an ``executor.routing_mode_changed`` event;
7. the ledger is succeeded with the mode event and the groups made.

Any refusal ends the transaction and leaves nothing behind, the key included. A work kind **left out of the mapping gets no
group and no rule from this change**; if it has none it is refused under ``rules`` (``no_rule_for_work_kind``) and never
routed by the legacy primary, and if an administrator set a rule for it earlier that rule is what governs it.

**The rollback** (``setExecutorRoutingMode`` to ``legacy``) takes neither a digest nor a mapping. Steps 1 to 3, then one
``legacy`` event and its ``executor.routing_mode_changed`` event. It touches no group, no revision, no rule and no Run or
job: work admitted by a rule or a group keeps its group revision and its rule revision, binds from that revision at
dispatch, and is never read through a legacy route. The groups and rules stay readable and the rules keep being the
rules of the next cut-over (which appends new ones).

**Under ``rules`` the legacy routes are read-only.** :func:`ensure_legacy_routing` is called by ``set_route`` first: it
takes the journal's lock, reads the mode and refuses ``conflict`` / ``routing_mode_rules`` before a key is claimed or a
row is written. ``listExecutorRoutes`` is a read and stays available as history.

Refusals reuse the catalogue (ADR-0026 decision 18): ``validation_failed`` with a ``field`` and a ``constraint``,
``conflict`` with a ``conflict_reason``, ``permission_denied`` for a caller who is not an administrator. No value is
echoed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.analysis.public import ModelPin
from auditmanager.executors.group_commands import append_rule, group_summary, make_group
from auditmanager.executors.group_repository import GroupRepository
from auditmanager.executors.groups import (
    MAX_NAME_LENGTH,
    GroupSettings,
    GroupSummary,
    MemberRequest,
    ModeState,
    RuleRecord,
    clean_display_name,
    group_name_in_use,
    refuse_settings,
    refuse_work_kind,
)
from auditmanager.executors.model import (
    CONFLICT_PREVIEW_STALE,
    CONFLICT_ROUTING_MODE_RULES,
    CONFLICT_ROUTING_MODE_UNCHANGED,
    CONSTRAINT_MAPPING_ENTRY_NOT_READY,
    CONSTRAINT_MAPPING_NOT_ACCEPTED,
    CONSTRAINT_MAPPING_REQUIRED,
    CONSTRAINT_MAPPING_WORK_KIND_REPEATED,
    CONSTRAINT_PREVIEW_DIGEST_REQUIRED,
    GROUP_STRATEGY_LEAST_LOADED,
    ROUTING_MODE_LEGACY,
    ROUTING_MODE_RULES,
    ROUTING_MODES,
    ROUTING_PREVIEW_ISSUES,
    ROUTING_PREVIEW_STATUSES,
    WORK_KINDS,
    ConnectionRecord,
    RevisionRecord,
    RouteRecord,
)
from auditmanager.executors.repository import ExecutorRepository
from auditmanager.executors.usability import is_served
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
    "COMMAND_TYPE",
    "DIGEST_DOMAIN",
    "MappingEntry",
    "ModeChange",
    "PreviewItem",
    "RoutingPreview",
    "check_mapping",
    "classify_route",
    "ensure_legacy_routing",
    "preview_digest_of",
    "preview_routing",
    "propose_name",
    "refuse_mode_request",
    "set_routing_mode",
]

#: The command type the product purge keeps (``KEEP_COMMAND_TYPES``).
COMMAND_TYPE: Final[str] = "set_executor_routing_mode"
#: The first line of what the preview digest hashes. A change of the proposal's shape changes this line.
DIGEST_DOMAIN: Final[str] = "auditmanager/executor-routing-preview/v1\n"
#: The journal aggregates and events of this module. The payload keys are the ones ``jobs.events`` allows.
AGGREGATE_MODE_EVENT: Final[str] = "ExecutorRoutingModeEvent"
AGGREGATE_ROUTE_EVENT: Final[str] = "ExecutorRouteEvent"
EVENT_MODE_CHANGED: Final[str] = "executor.routing_mode_changed"

PREVIEW_READY, PREVIEW_NO_ROUTE, PREVIEW_INCOMPATIBLE = ROUTING_PREVIEW_STATUSES
ISSUE_CONNECTION_ARCHIVED, ISSUE_NO_REVISION, ISSUE_KIND_NOT_SERVED = ROUTING_PREVIEW_ISSUES

_DIGEST = re.compile(r"[0-9a-f]{64}")
_SEPARATOR = " / "

Journal = Callable[..., None]


# --- records ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreviewItem:
    """What the cut-over would do with one work kind (``ExecutorRoutingPreviewItem``). Every field but the work kind and
    the status is ``None`` when it does not apply, and absent from the wire."""

    work_kind: str
    status: str
    primary_connection_id: str | None = None
    connection_revision_id: str | None = None
    standby_connection_id: str | None = None
    pin_id: str | None = None
    gateway_model: str | None = None
    billing: str | None = None
    proposed_group_name: str | None = None
    incompatible_reason: str | None = None

    def as_wire(self) -> dict[str, str]:
        """The fields that have a value, by their contract names -- exactly what the preview shows and the digest binds."""
        return {
            name: value for name, value in (
                ("work_kind", self.work_kind), ("status", self.status),
                ("primary_connection_id", self.primary_connection_id),
                ("connection_revision_id", self.connection_revision_id),
                ("standby_connection_id", self.standby_connection_id), ("pin_id", self.pin_id),
                ("gateway_model", self.gateway_model), ("billing", self.billing),
                ("proposed_group_name", self.proposed_group_name),
                ("incompatible_reason", self.incompatible_reason),
            ) if value is not None
        }


@dataclass(frozen=True, slots=True)
class RoutingPreview:
    """The proposal: the mode in force, the digest that binds the six items, and the items in ``WORK_KINDS`` order."""

    routing_mode: ModeState
    preview_digest: str
    items: tuple[PreviewItem, ...]


@dataclass(frozen=True, slots=True)
class MappingEntry:
    """One confirmed line of a cut-over: the work kind and the name of the one-member group to make for it."""

    work_kind: str
    group_display_name: str


@dataclass(frozen=True, slots=True)
class ModeChange:
    """The mode after a change, the groups the change made (none for a rollback or a repeat of a rollback) and the rules
    now current."""

    routing_mode: ModeState
    groups: tuple[GroupSummary, ...]
    rules: tuple[RuleRecord, ...]


# --- refusals --------------------------------------------------------------------------------------------------------


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _invalid(field: str, constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the routing mode request is not acceptable",
        field=field, constraint=constraint,
    )


def _conflict(reason: str, aggregate_type: str = AGGREGATE_MODE_EVENT) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT, message="the routing mode is not in a state that allows this",
        conflict_reason=reason, aggregate_type=aggregate_type,
    )


def _inconsistent(what: str) -> DomainError:
    """A state the schema forbids (a legacy route to a connection that does not exist). Not a user error."""
    return DomainError(ErrorCode.INTERNAL_ERROR, message=what)


# --- the preview: pure --------------------------------------------------------------------------------------------------


def classify_route(
    work_kind: str, route: RouteRecord | None, connection: ConnectionRecord | None, revision: RevisionRecord | None,
    *, served: bool,
) -> PreviewItem:
    """What the cut-over would do with one work kind, from the facts about its legacy route. The proposed name is added
    by the caller (it depends on the other items).

    * no route: ``no_route``;
    * the primary's connection archived: ``incompatible`` / ``connection_archived``; else with no revision:
      ``no_revision``; else when this release does not serve it: ``kind_not_served``;
    * otherwise ``ready``, carrying the **current** revision and the pin, gateway model and billing it pins.

    The standby is carried whenever the route has one, in every status but ``no_route``, and is never read further."""
    if route is None:
        return PreviewItem(work_kind=work_kind, status=PREVIEW_NO_ROUTE)
    if connection is None:
        raise _inconsistent("a legacy route names a connection that does not exist")
    pinned = {} if revision is None else {
        "connection_revision_id": revision.revision_id, "pin_id": revision.settings.pin_id,
        "gateway_model": revision.settings.gateway_model, "billing": revision.settings.billing,
    }
    shown = {
        "work_kind": work_kind, "primary_connection_id": route.primary_connection_id,
        "standby_connection_id": route.standby_connection_id, **pinned,
    }
    if connection.archived_at is not None:
        return PreviewItem(status=PREVIEW_INCOMPATIBLE, incompatible_reason=ISSUE_CONNECTION_ARCHIVED, **shown)
    if revision is None:
        return PreviewItem(status=PREVIEW_INCOMPATIBLE, incompatible_reason=ISSUE_NO_REVISION, **shown)
    if not served:
        return PreviewItem(status=PREVIEW_INCOMPATIBLE, incompatible_reason=ISSUE_KIND_NOT_SERVED, **shown)
    return PreviewItem(status=PREVIEW_READY, **shown)


def propose_name(display_name: str, work_kind: str, taken: Collection[str]) -> str:
    """The name proposed for the one-member group of a work kind: ``<connection name> / <work kind>``, at most 120
    characters, and no name in ``taken`` (lower-cased names of the active groups and of the names already proposed). A
    name that is taken gets `` (2)``, `` (3)``, ... The result is a function of its arguments, so the digest that covers
    it is reproducible. A connection name that is not a label falls back to the work kind alone."""
    room = MAX_NAME_LENGTH - len(_SEPARATOR) - len(work_kind)
    try:
        base = clean_display_name(f"{display_name[:max(room, 0)]}{_SEPARATOR}{work_kind}")
    except DomainError:
        base = work_kind
    candidate, number = base, 1
    while candidate.lower() in taken:
        number += 1
        suffix = f" ({number})"
        candidate = base[: MAX_NAME_LENGTH - len(suffix)].rstrip() + suffix
    return candidate


def preview_digest_of(items: Sequence[PreviewItem]) -> str:
    """The digest that binds the items as shown: SHA-256 of :data:`DIGEST_DOMAIN` and the canonical JSON of each item's
    wire fields, in the order given."""
    body = json.dumps([item.as_wire() for item in items], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((DIGEST_DOMAIN + body).encode("utf-8")).hexdigest()


# --- the request: pure ----------------------------------------------------------------------------------------------------


def refuse_mode_request(
    mode: str, preview_digest: str | None, mapping: Sequence[MappingEntry] | None,
) -> tuple[MappingEntry, ...]:
    """Refuse what is wrong with a request before any row is read, and return the cleaned mapping (empty for ``legacy``).

    * ``mode`` / ``enum`` -- not ``legacy`` or ``rules``;
    * ``legacy`` takes neither field: ``mapping`` / ``mapping_not_accepted`` when either is present;
    * ``rules``: ``preview_digest`` / ``preview_digest_required`` when absent and ``preview_digest`` / ``format`` when it
      is not 64 lowercase hexadecimal digits; ``mapping`` / ``mapping_required`` when absent or empty;
      ``work_kind`` / ``enum`` for a work kind the enumeration does not name; ``mapping`` /
      ``mapping_work_kind_repeated`` for a work kind twice; ``display_name`` / ``type``, ``required``, ``printable`` or
      ``max_length`` for a name that is not a label; and ``409 conflict`` / ``group_name_in_use`` for one name twice
      (without regard to case)."""
    if mode not in ROUTING_MODES:
        raise _invalid("mode", "enum")
    if mode == ROUTING_MODE_LEGACY:
        if preview_digest is not None or mapping is not None:
            raise _invalid("mapping", CONSTRAINT_MAPPING_NOT_ACCEPTED)
        return ()
    if preview_digest is None:
        raise _invalid("preview_digest", CONSTRAINT_PREVIEW_DIGEST_REQUIRED)
    if _DIGEST.fullmatch(preview_digest) is None:
        raise _invalid("preview_digest", "format")
    if not mapping:
        raise _invalid("mapping", CONSTRAINT_MAPPING_REQUIRED)
    seen_kinds: set[str] = set()
    seen_names: set[str] = set()
    cleaned: list[MappingEntry] = []
    for entry in mapping:
        refuse_work_kind(entry.work_kind)
        if entry.work_kind in seen_kinds:
            raise _invalid("mapping", CONSTRAINT_MAPPING_WORK_KIND_REPEATED)
        seen_kinds.add(entry.work_kind)
        name = clean_display_name(entry.group_display_name)
        if name.lower() in seen_names:
            raise group_name_in_use()
        seen_names.add(name.lower())
        cleaned.append(MappingEntry(entry.work_kind, name))
    return tuple(cleaned)


def check_mapping(entries: Sequence[MappingEntry], items: Sequence[PreviewItem]) -> None:
    """``validation_failed`` / ``mapping_entry_not_ready`` for an entry whose work kind is not ``ready`` in the preview
    now computed. A work kind the mapping leaves out is not an error: it gets no group and no rule from this change."""
    by_kind = {item.work_kind: item for item in items}
    for entry in entries:
        if by_kind[entry.work_kind].status != PREVIEW_READY:
            raise _invalid("mapping", CONSTRAINT_MAPPING_ENTRY_NOT_READY)


# --- the preview: rows -------------------------------------------------------------------------------------------------------


def _build_items(
    session: Session, store: ExecutorRepository, repo: GroupRepository, *, lock: bool
) -> tuple[PreviewItem, ...]:
    """The six items from the rows now. With ``lock`` the primaries' connection rows are locked ``FOR SHARE`` in
    ascending order before their facts are read, so no revision, archive or key change can slip between this read and
    the groups that snapshot it (the cut-over); the preview read takes none."""
    routes = {route.work_kind: route for route in store.current_routes(session)}
    primaries = sorted({route.primary_connection_id for route in routes.values()})
    if lock:
        repo.lock_connections(session, primaries)
    connections = {connection_id: store.get_connection(session, connection_id) for connection_id in primaries}
    revisions = store.current_revisions(session, primaries)
    taken = set(repo.active_group_names(session))
    items: list[PreviewItem] = []
    for work_kind in WORK_KINDS:
        route = routes.get(work_kind)
        connection = None if route is None else connections.get(route.primary_connection_id)
        if connection is not None and connection.system_managed:
            # `HOSTS-BACKEND-01`: the stand's own system connections are never a cut-over candidate. No route can name one (``set_route`` refuses it);
            # this is the guard, and such a route is read as no route.
            route = connection = None
        revision = None if route is None else revisions.get(route.primary_connection_id)
        served = connection is not None and revision is not None and is_served(connection, revision)
        item = classify_route(work_kind, route, connection, revision, served=served)
        if item.status == PREVIEW_READY:
            assert connection is not None
            name = propose_name(connection.display_name, work_kind, taken)
            taken.add(name.lower())
            item = replace(item, proposed_group_name=name)
        items.append(item)
    return tuple(items)


def preview_routing(
    session: Session, *, roles: Iterable[str], repository: ExecutorRepository | None = None,
    groups: GroupRepository | None = None,
) -> RoutingPreview:
    """The cut-over proposal for an administrator, writing nothing. ``permission_denied`` for anybody else."""
    _admin(roles)
    store, repo = repository or ExecutorRepository(), groups or GroupRepository()
    items = _build_items(session, store, repo, lock=False)
    return RoutingPreview(routing_mode=repo.current_mode(session), preview_digest=preview_digest_of(items), items=items)


# --- the guard on the legacy routes ----------------------------------------------------------------------------------------


def ensure_legacy_routing(session: Session, groups: GroupRepository | None = None) -> None:
    """Refuse ``setExecutorRoute`` while the routing mode is ``rules``: ``conflict`` / ``routing_mode_rules``.

    Takes the journal's advisory lock first and holds it to the end of the caller's transaction, so a route change and a
    cut-over (which holds the same lock from its own start to its commit) cannot interleave: either the route is written
    before the cut-over computes its preview and the digest sees it, or the cut-over commits first and this refuses."""
    repo = groups or GroupRepository()
    repo.lock_mode_journal(session)
    if repo.current_mode(session).mode == ROUTING_MODE_RULES:
        raise _conflict(CONFLICT_ROUTING_MODE_RULES, AGGREGATE_ROUTE_EVENT)


# --- the command -------------------------------------------------------------------------------------------------------------


def _fingerprint(
    mode: str, preview_digest: str | None, entries: Sequence[MappingEntry], actor_uid: str
) -> dict[str, object]:
    """What the ledger compares: the mode, the digest and the mapping by work kind (the order listed is not a
    difference), and the administrator who spent the key."""
    return {
        "mode": mode, "preview_digest": preview_digest, "actor_uid": actor_uid,
        "mapping": [[entry.work_kind, entry.group_display_name]
                    for entry in sorted(entries, key=lambda item: item.work_kind)],
    }


def _answer(session: Session, repo: GroupRepository, group_ids: Iterable[Any]) -> ModeChange:
    """The result as it stands now: the mode in force, the groups the recorded change made, the rules now current."""
    return ModeChange(
        routing_mode=repo.current_mode(session),
        groups=tuple(group_summary(session, str(group_id), repo) for group_id in group_ids),
        rules=tuple(repo.current_rules(session)),
    )


def set_routing_mode(
    session: Session, *, mode: str, preview_digest: str | None, mapping: Sequence[MappingEntry] | None,
    pins: Iterable[ModelPin], roles: Iterable[str], idempotency_key: str, actor_uid: str,
    repository: ExecutorRepository | None = None, groups: GroupRepository | None = None,
    commands: CommandRepository | None = None, journal: Journal = append_execution_event,
) -> ModeChange:
    """Cut over to ``rules`` or roll back to ``legacy``, in one transaction (see the module docstring for the steps and
    their lock order). The caller owns the transaction, and a refusal ends it: a refused request leaves nothing behind,
    not even its key.

    Refusals, in this order: ``permission_denied``; the request itself (:func:`refuse_mode_request`); then, after the key
    is claimed and the journal's lock taken, ``409 conflict`` / ``routing_mode_unchanged``, ``409 conflict`` /
    ``preview_stale``, ``422`` / ``mapping_entry_not_ready``, the pin and the member refusals of a group made by hand
    (``pin_id`` / ``model_not_pinned``, ``members`` / ``member_kind_not_served``, ...) and ``409`` /
    ``group_name_in_use`` for a name an active group holds."""
    _admin(roles)
    entries = refuse_mode_request(mode, preview_digest, mapping)
    store, repo, ledger = repository or ExecutorRepository(), groups or GroupRepository(), commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type=COMMAND_TYPE, idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint(_fingerprint(mode, preview_digest, entries, actor_uid)),
    )
    if isinstance(claimed, CommandReplay):
        return _answer(session, repo, claimed.outcome.get("group_ids") or ())
    assert isinstance(claimed, CommandStarted)
    repo.lock_mode_journal(session)
    before = repo.current_mode(session)
    if before.mode == mode:
        raise _conflict(CONFLICT_ROUTING_MODE_UNCHANGED)
    group_ids: list[str] = []
    digest: str | None = None
    confirmed: list[dict[str, str]] = []
    if mode == ROUTING_MODE_RULES:
        assert preview_digest is not None
        digest = preview_digest
        group_ids, confirmed = _convert(
            session, store=store, repo=repo, entries=entries, preview_digest=preview_digest,
            pins=pins, actor_uid=actor_uid, journal=journal)
    state, number = repo.insert_mode_event(
        session, mode=mode, preview_digest=digest, mapping=confirmed, actor_uid=actor_uid)
    journal(
        session, event_type=EVENT_MODE_CHANGED, aggregate_type=AGGREGATE_MODE_EVENT,
        aggregate_id=str(state.mode_event_id),
        payload={"from_state": before.mode, "to_state": mode, "revision_no": number, "actor_uid": actor_uid},
    )
    ledger.succeed(session, claimed.command_id, {"mode_event_id": state.mode_event_id, "group_ids": group_ids})
    return ModeChange(
        routing_mode=state,
        groups=tuple(group_summary(session, group_id, repo) for group_id in group_ids),
        rules=tuple(repo.current_rules(session)),
    )


def _convert(
    session: Session, *, store: ExecutorRepository, repo: GroupRepository, entries: Sequence[MappingEntry],
    preview_digest: str, pins: Iterable[ModelPin], actor_uid: str, journal: Journal,
) -> tuple[list[str], list[dict[str, str]]]:
    """Steps 4 and 5 of the cut-over: recompute the preview under the connection locks, hold the confirmation against
    it, then make the one-member group and the rule of each mapped work kind. Returns the groups made and the entries of
    the ``rules`` event, both in ``WORK_KINDS`` order."""
    items = _build_items(session, store, repo, lock=True)
    if preview_digest_of(items) != preview_digest:
        raise _conflict(CONFLICT_PREVIEW_STALE)
    check_mapping(entries, items)
    by_kind = {item.work_kind: item for item in items}
    table = {pin.model_id: pin for pin in pins}
    plans: list[tuple[MappingEntry, GroupSettings, list[MemberRequest]]] = []
    for entry in sorted(entries, key=lambda item: WORK_KINDS.index(item.work_kind)):
        item = by_kind[entry.work_kind]
        assert item.pin_id and item.gateway_model and item.billing
        assert item.primary_connection_id and item.connection_revision_id
        settings = GroupSettings(
            pin_id=item.pin_id, gateway_model=item.gateway_model, billing=item.billing,
            strategy=GROUP_STRATEGY_LEAST_LOADED)
        members = [MemberRequest(item.primary_connection_id, item.connection_revision_id)]
        refuse_settings(settings, members, pinned_model_ids=table)
        plans.append((entry, settings, members))
    group_ids: list[str] = []
    confirmed: list[dict[str, str]] = []
    for entry, settings, members in plans:
        record, revision = make_group(
            session, name=entry.group_display_name, settings=settings, members=members, table=table, store=store,
            repo=repo, actor_uid=actor_uid, journal=journal)
        rule = append_rule(
            session, work_kind=entry.work_kind, group_revision_id=revision.group_revision_id, repo=repo,
            actor_uid=actor_uid, journal=journal)
        group_ids.append(record.group_id)
        confirmed.append({
            "work_kind": entry.work_kind, "group_id": record.group_id,
            "group_revision_id": revision.group_revision_id, "rule_revision_id": rule.rule_revision_id,
        })
    return group_ids, confirmed
