"""First-call binding of a comparison job admitted by a rule or a group (`EXEC2-GROUP-CMP-01`, ADR-0026 decisions 12 to 16).

A job made while the routing mode is ``rules`` is consented to **before** it has a connection: it stores the rule revision and the
group revision (``comparison_ai_job.binding_state = 'pending'``, ``connection_revision_id`` NULL) and the user consented to the group's
model, billing and rates. The job binds to one member of the group at its **first dispatched call**, in the transaction that prepares
that call, and its later calls stay on that member.

What the wrapper (:class:`~auditmanager.comparison.spend.caller.ComparisonModelCaller`) does when the route it is handed carries a
:class:`~auditmanager.comparison.spend.model.GroupDispatch`, in this order and in one transaction that also holds the item:

1. **Lock the group**, then **the members' connections in ascending ``connection_id``** (the advisory lock of a Run's claim), then --
   later, with the ceilings -- **the day**. The order is decision 14's; a Run's claim and an administrator's revision take the same
   locks in the same order, so none of them deadlocks with a call.
2. **Read the job under the group lock.** A job already ``bound`` (another item of it bound it first) stays on its member and is
   never chosen for again: it needs only that member's free unit. This is also what makes a retry, a resume after ``overrun`` and a
   call after ``spend_unknown`` stay on the bound member (decision 16): a bound job has exactly one member to ask, and the database
   refuses to write another.
3. **Choose** among the members that are eligible and have a free unit (``executors.public``: ``member_facts`` -- read host-aware for a system group by :func:`member_facts_of` --, ``member_issue``,
   ``choose``). No eligible member with a free unit is a **wait**: the job's ``wait_reason`` says why (``executor_at_capacity``, or
   ``runner_offline`` when no member is eligible at all) and the item is asked again later (the refusal is ``connection_busy``, which
   every handler already answers with a retry that spends no attempt). A wait for capacity has no end; a wait with no eligible member
   ends the job ``failed`` / ``no_executor_online`` after ``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`` (decision 15).
4. **Re-check the consent** against the chosen member (:func:`consent_problem`): the group revision the job froze, the model, the
   billing, the member's own revision, the figure the group's rate snapshot prices the stored estimate at and -- the rule a Run's
   dispatch holds (``runs.cost_policy.group_consent_holds``) -- the **rates**: the rates the consent was given on must be the rates
   the bound member's current revision is priced at now, the provider lock's for its pin, compared by the same digest
   (``model_rate_sha256``). A consent that does not hold calls nothing and **never re-prices**: the job records
   ``wait_reason = needs_reconsent`` and pauses ``route_changed`` -- the reconsent pause a changed route already has. (A new consent of a
   job admitted by a group is priced on that job's own group revision again, so while the lock and the revision's snapshot differ
   the job cannot go on: an administrator makes a new group revision and the work is started again on it.)
5. **Open the member's route**, apply the USD 10 job and USD 50 day ceilings, advance the group's rotation, write the binding
   (``pending -> bound``, the member's revision) with a journal event ``executor.comparison_job_bound``, and insert the ``prepared`` row
   of the call journal -- the unit the member now spends -- all or none (a savepoint), then commit. The model is called only after
   that commit. The ceilings, the journal's estimate and the cost the call settles at are **one price**: the member's own route must
   carry the rates of the route the estimate was priced on (:func:`same_rates`), or the call is refused ``consent_stale``.

Nothing here retries a call or sends one to another member: a ``spend_unknown`` item is never sent again by the queue (it ends
``spend_unknown``) and a job has one member for good.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, NoReturn

from sqlalchemy.orm import Session

from auditmanager.comparison.spend.errors import (
    REASON_CONNECTION_BUSY,
    REASON_CONSENT_STALE,
    REASON_EXECUTOR_ROUTE_MISSING,
    REASON_NO_EXECUTOR_ONLINE,
    CallRefused,
)
from auditmanager.comparison.spend.model import (
    BINDING_BOUND,
    BINDING_FROZEN,
    BINDING_PENDING,
    JOB_CEILING_MICROS,
    WAIT_AT_CAPACITY,
    WAIT_NEEDS_RECONSENT,
    WAIT_RUNNER_OFFLINE,
    CallRoute,
    GroupDispatch,
    JobBindings,
    estimate_micros_of,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "DEFAULT_GROUP_OFFLINE_WAIT_SECONDS",
    "EVENT_JOB_BOUND",
    "GROUP_OFFLINE_WAIT_ENV",
    "GroupRoutes",
    "MAX_GROUP_OFFLINE_WAIT_SECONDS",
    "Selection",
    "consent_problem",
    "group_aware",
    "group_offline_wait_seconds",
    "group_pin",
    "group_rates_hold",
    "group_wait_reason",
    "is_eligible",
    "lock_pin",
    "member_facts_of",
    "member_issues",
    "pending_route",
    "priced_as_consented",
    "same_rates",
    "select_member",
    "snapshot_pin",
    "write_binding",
]

#: ADR-0026 decision 15, ``R-149c``: how long a job whose group has **no eligible member** waits before it ends.
GROUP_OFFLINE_WAIT_ENV: Final[str] = "AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS"
DEFAULT_GROUP_OFFLINE_WAIT_SECONDS: Final[int] = 1800
MAX_GROUP_OFFLINE_WAIT_SECONDS: Final[int] = 7 * 24 * 3600
#: The journal event of a binding: ``executor.``-prefixed, identities and classifiers only (``jobs.events._SAFE_KEYS``).
EVENT_JOB_BOUND: Final[str] = "executor.comparison_job_bound"
_EVENT_AGGREGATE: Final[str] = "ComparisonAiJob"
#: ``executors.group_selection.ISSUE_AT_CAPACITY``: the one issue that leaves a member eligible (it waits for a free unit). A test
#: pins the word against the executors' own.
_AT_CAPACITY: Final[str] = "at_capacity"
_NOT_METERED: Final[str] = "not_metered"


def group_offline_wait_seconds(environ: Mapping[str, str] | None = None) -> int:
    """``AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS``: unset is :data:`DEFAULT_GROUP_OFFLINE_WAIT_SECONDS`; anything else must be a whole
    number of seconds, written plainly (blank included, no sign, no fraction, no exponent), from one second to a week. A bad value
    raises ``ValueError`` -- it is never clamped to the default, which would make the wait something nobody wrote. The same reading
    as the Run side's (``jobs.repository``), so a Run and a comparison job of one group give up after the same time."""
    source = os.environ if environ is None else environ
    if GROUP_OFFLINE_WAIT_ENV not in source:
        return DEFAULT_GROUP_OFFLINE_WAIT_SECONDS
    raw = source[GROUP_OFFLINE_WAIT_ENV].strip()
    if not raw.isascii() or not raw.isdigit():
        raise ValueError(f"{GROUP_OFFLINE_WAIT_ENV} is {raw!r}; it is a whole number of seconds, written plainly")
    value = int(raw)
    if not 1 <= value <= MAX_GROUP_OFFLINE_WAIT_SECONDS:
        raise ValueError(f"{GROUP_OFFLINE_WAIT_ENV} is {value}; it must be between 1 and {MAX_GROUP_OFFLINE_WAIT_SECONDS}")
    return value


def is_eligible(facts: Any) -> bool:
    """May dispatch choose this member once it has a free unit? Its first issue is none, or ``at_capacity`` alone
    (``executors.group_selection.member_issue``). One reading, shared by the first-call choice and the offline sweep, so the call that
    waits and the sweep that ends the wait cannot disagree about what «nobody can take it» means."""
    from auditmanager.executors.public import member_issue

    return member_issue(facts) in (None, _AT_CAPACITY)


def member_issues(session: Session, revision: Any) -> list[str | None]:
    """The first issue of each member of ``revision`` now (``executors.group_selection.member_issue``; ``None`` is a member with no
    issue at all). Read-only: no lock is taken."""
    from auditmanager.executors.public import member_issue

    return [member_issue(facts) for facts in member_facts_of(session, revision)]


def member_facts_of(session: Session, revision: Any) -> list[Any]:
    """``executors.public.member_facts`` made to read a **system** member (`HOSTS-CMP-01`, ADR-0028 decisions 3 and 16).

    The members of a system group are the system connections of the servers. They have no probe and no runner token of their own -- the server
    reports, and the server's facts say whether it can take a call -- so the generic facts, which ask for a probe and a runner, find none and
    would leave a group of servers with no eligible member for ever. For such a member the facts are the server's: ``probed_ok`` and
    ``runner_online`` are the absence of any reason the model is not available on it now (``executors.public.member_reasons``: the server is off,
    off line, signed out, has not verified the model or is cooling down), and its capacity and use are the server's slots of the provider -- the
    pool the Runs' cell binding counts and the spend mirror locks. A member that is not a system connection is read as it always was."""
    from auditmanager.executors.public import (
        ExecutorRepository, MemberFacts, access_of_billing, current_revision, member_facts, member_reasons, read_hosts, split_pool,
    )

    found = list(member_facts(session, revision))
    members = tuple(getattr(revision, "members", ()))
    store = ExecutorRepository()
    system = {}
    for member in members:
        connection = store.get_connection(session, member.connection_id)
        if connection is not None and connection.system_managed and connection.capacity_pool is not None:
            system[member.connection_id] = connection
    if not system:
        return found
    hosts = {item.record.host_id: item for item in read_hosts(
        session, sorted({split_pool(connection.capacity_pool)[0] for connection in system.values()}), include_archived=True)}
    access = access_of_billing(revision.billing)
    for index, member in enumerate(members):
        connection = system.get(member.connection_id)
        if connection is None:
            continue
        host_id, provider = split_pool(connection.capacity_pool)
        host, current = hosts.get(host_id), current_revision(session, member.connection_id)
        reasons, _full = (["host_offline"], False) if host is None else member_reasons(
            host, provider=provider, access=access, model_id=revision.pin_id)
        slot = None if host is None else host.slot_of(provider)
        found[index] = MemberFacts(
            connection_id=member.connection_id, tie_break_order=member.tie_break_order,
            revision_is_snapshot=current is not None and current.revision_id == member.connection_revision_id,
            archived=connection.archived_at is not None or host is None or host.record.archived_at is not None,
            served=True, probed_ok=not reasons, runner_online=not reasons,
            capacity=0 if slot is None else slot.slots, used=0 if slot is None else slot.in_use,
        )
    return found


def group_wait_reason(issues: Sequence[str | None]) -> str | None:
    """Why work admitted on a group cannot be dispatched now, from the first issue of each member (decision 15).

    The Run side's reading (``jobs.repository._group_wait_reason``, a test holds the two equal) and the first call's own
    (:func:`_wait`): ``None`` when some member has no issue at all (it can take the work); ``executor_at_capacity`` when none has but
    some member is only full (a wait for a place, which has no end); ``runner_offline`` otherwise -- every member is revised, archived,
    not served, not probed or without a runner, which for waiting work is no executor online."""
    if any(issue is None for issue in issues):
        return None
    if any(issue == _AT_CAPACITY for issue in issues):
        return WAIT_AT_CAPACITY
    return WAIT_RUNNER_OFFLINE


def _route_missing() -> DomainError:
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="no usable executor connection is routed for this kind of work",
        dependency=REASON_EXECUTOR_ROUTE_MISSING,
    )


def lock_pin(pin_id: str) -> Any | None:
    """The provider lock's pin for ``pin_id`` with the rates the lock publishes **now**, or ``None`` when the lock does not pin it.

    The rates a Run is priced at and re-checks at dispatch (``runs.cost_policy.group_consent_holds``) are these."""
    from auditmanager.executors.public import pinned_models

    return next((candidate for candidate in pinned_models() if candidate.model_id == pin_id), None)


def same_rates(left: Any | None, right: Any | None) -> bool:
    """Do two pins name one model at one price? The comparison is the Run side's own: the digest of the model and its exact
    published rates (``analysis.text.cost.model_rate_sha256``). A missing pin is never the same as a pin."""
    from auditmanager.analysis.public import model_rate_sha256

    return left is not None and right is not None and model_rate_sha256(left) == model_rate_sha256(right)


def snapshot_pin(revision: Any) -> Any | None:
    """The provider lock's pin of ``revision.pin_id`` with the **rate snapshot the revision copied** (the rates are a part of what the
    consent names, and a revision is immutable), or ``None`` when the lock does not pin the model."""
    base = lock_pin(revision.pin_id)
    if base is None:
        return None
    return dataclasses.replace(
        base, input_per_mtok_usd=float(revision.input_per_mtok_usd), output_per_mtok_usd=float(revision.output_per_mtok_usd),
    )


def group_pin(revision: Any) -> Any:
    """The pin a group revision prices at: :func:`snapshot_pin`. An unpinned model is ``executor_route_missing``."""
    pin = snapshot_pin(revision)
    if pin is None:
        raise _route_missing()
    return pin


def group_rates_hold(revision: Any, pin_id: str | None = None) -> bool:
    """Are the rates the group revision snapshotted -- the ones a consent is given on -- the rates the provider lock prices ``pin_id`` (by
    default the revision's own model) at **now**? The rule a Run's dispatch holds (``runs.cost_policy.group_consent_holds``), compared by
    the same digest. ``False`` when the lock has stopped pinning the model."""
    return same_rates(snapshot_pin(revision), lock_pin(revision.pin_id if pin_id is None else pin_id))


def priced_as_consented(session: Session, group_revision_id: str, pin: Any | None) -> bool:
    """Is a call priced at ``pin`` priced at the rates the consent of a job admitted on ``group_revision_id`` was given on? For the calls of a
    job that is **already bound**, whose route is opened from the lock as it is now: the same comparison :func:`consent_problem` makes at the
    first call, repeated at every call as a Run's call-time guard does (``analysis.text.cost.require_approved_model``). A group revision that
    cannot be read, or a missing pin, is not a consent that holds."""
    from auditmanager.executors.public import group_revision_of

    revision = group_revision_of(session, group_revision_id)
    return revision is not None and same_rates(snapshot_pin(revision), pin)


# -- the route of a pending job -----------------------------------------------------------------------------------------------


class _UnboundAdapter:
    """The adapter of a job that has no member yet: it names the mode (so the wrapper can read it) and refuses to be called -- the
    wrapper replaces the whole route by the chosen member's before anything is sent."""

    provider_mode = "live"

    def complete(self, request: Any) -> Any:
        raise RuntimeError("a job admitted by a group is bound to a member at its first call, before any model is called")


def pending_route(
    session: Session, job: Any, *, member_route: Callable[[Session, Any], CallRoute], jobs: JobBindings,
) -> CallRoute:
    """The route of a ``pending`` job: the group revision's model, rates and billing, and the means to bind a member at the first call.

    ``member_route(session, job)`` is the composition root's own binder; it is called with ``job`` as it will be once bound (the
    chosen member's revision in ``connection_revision_id``) and answers the route of that connection."""
    from auditmanager.executors.public import group_revision_of

    revision = None if job.executor_group_revision_id is None else group_revision_of(session, job.executor_group_revision_id)
    if revision is None:
        raise _route_missing()

    def open_member(member_session: Session, revision_id: str) -> CallRoute:
        return member_route(member_session, dataclasses.replace(job, binding_state=BINDING_BOUND, connection_revision_id=revision_id))

    return CallRoute(
        adapter=_UnboundAdapter(), model_identity=job.pinned_model, expected_model=revision.gateway_model, check_identity=True,
        unmetered=revision.billing == _NOT_METERED, pin=group_pin(revision),
        dispatch=GroupDispatch(
            job_id=job.job_id, group_id=revision.group_id, group_revision_id=revision.group_revision_id,
            work_kind=f"comparison_{job.method}", member_route=open_member, jobs=jobs,
            rule_revision_id=job.routing_rule_revision_id,
        ),
    )


class GroupRoutes:
    """The route source a handler is given: the composition root's binder for every job that has a connection, and a
    :class:`~auditmanager.comparison.spend.model.GroupDispatch` route for a ``pending`` live job.

    It implements both spellings the handlers use (``route`` and ``route_for``). A recorded job is passed to the inner source
    untouched: a replay binds no route and spends nothing, so it stays ``pending`` for good."""

    __slots__ = ("_inner", "_jobs")

    def __init__(self, inner: Any, *, jobs: JobBindings) -> None:
        self._inner = inner
        self._jobs = jobs

    def _open(self, session: Session, job: Any) -> CallRoute:
        opener = getattr(self._inner, "route", None) or self._inner.route_for
        return opener(session, job)

    def route(self, session: Session, job: Any) -> CallRoute:
        if getattr(job, "binding_state", BINDING_FROZEN) != BINDING_PENDING or getattr(job, "provider_mode", "live") != "live":
            return self._open(session, job)
        return pending_route(session, job, member_route=self._open, jobs=self._jobs)

    def route_for(self, session: Session, job: Any) -> CallRoute:
        return self.route(session, job)


def group_aware(routes: Any, *, jobs: JobBindings) -> Any:
    """``routes`` with the first-call binding of a ``pending`` job; ``None`` stays ``None`` (a bundle with no route source)."""
    if routes is None or isinstance(routes, GroupRoutes):
        return routes
    return GroupRoutes(routes, jobs=jobs)


# -- the consent, re-checked against the member -------------------------------------------------------------------------------


def consent_problem(job: Any, revision: Any, member: Any, snapshot_revision_id: str) -> str | None:
    """Why the consent of ``job`` does not hold for ``member`` at dispatch, or ``None`` when it does (decision 14).

    The consent envelope is the group revision the job froze, its model, its billing, the figure the estimate prices at and the
    ceiling. At dispatch each is read again from rows, never trusted from the route in hand: the job still names the group revision
    it was consented on and the estimate it stored names the same; the model and the billing are the group revision's and the member's
    own current revision still pins that model, serves that gateway model and bills that way and is the revision the group
    snapshotted; **the rates the consent was given on** (the group revision's snapshot) **are the rates that member's pin is priced at
    now** -- the provider lock's, the rule a Run's dispatch holds -- so nothing is silently re-priced; and the stored estimate priced at
    the group's rate snapshot is the stored ``estimate_micros`` (a not-metered group: zero, with no money ceiling). The word returned
    names the first check that failed; it is for a log line, never for a user."""
    estimate = job.estimate if isinstance(job.estimate, Mapping) else {}
    document = estimate.get("route") if isinstance(estimate.get("route"), Mapping) else {}
    if job.executor_group_revision_id != revision.group_revision_id:
        return "group_revision"
    if document.get("executor_group_revision_id") != revision.group_revision_id:
        return "estimate_group_revision"
    if job.pinned_model != revision.pin_id or document.get("pinned_model") != revision.pin_id:
        return "pinned_model"
    if document.get("billing") != revision.billing:
        return "billing"
    if member is None or member.revision_id != snapshot_revision_id:
        return "member_revision"
    settings = member.settings
    if (settings.pin_id, settings.gateway_model, settings.billing) != (revision.pin_id, revision.gateway_model, revision.billing):
        return "member_settings"
    if not group_rates_hold(revision, settings.pin_id):
        return "rates"
    if revision.billing == _NOT_METERED:
        return None if job.estimate_micros == 0 else "estimate"
    if not 0 < job.ceiling_micros <= JOB_CEILING_MICROS:
        return "ceiling"
    try:
        priced = estimate_micros_of(group_pin(revision).cost_usd(
            input_tokens=int(estimate["input_tokens"]), output_tokens=int(estimate["output_tokens"]),
        ))
    except (KeyError, TypeError, ValueError):
        return "estimate"
    return None if priced == job.estimate_micros else "estimate"


# -- the first-call binding -----------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Selection:
    """The member a call goes to: its open route, its connection and revision, and whether this call binds the job."""

    route: CallRoute
    connection_id: str
    revision_id: str
    binds: bool


def _open_member(session: Session, dispatch: GroupDispatch, revision_id: str) -> CallRoute:
    try:
        route = dispatch.member_route(session, revision_id)
    except DomainError:
        # The revision, its kind's factory or its key is gone. Nothing is written yet and nothing is sent.
        raise CallRefused(REASON_EXECUTOR_ROUTE_MISSING, pauses_job=False) from None
    if route.dispatch is not None or route.connection_revision_id != revision_id:
        raise ValueError("the route opened for a member is the route of that member's revision")
    return route


def _wait(session: Session, dispatch: GroupDispatch, *, any_eligible: bool, offline_wait_seconds: int) -> NoReturn:
    """No member can take the call: record why, commit that (and nothing else), and refuse. Always raises."""
    reason = WAIT_AT_CAPACITY if any_eligible else WAIT_RUNNER_OFFLINE
    waited = dispatch.jobs.set_wait(session, dispatch.job_id, reason)
    session.commit()
    if reason == WAIT_RUNNER_OFFLINE and waited is not None and waited > offline_wait_seconds:
        raise CallRefused(REASON_NO_EXECUTOR_ONLINE, pauses_job=True)
    raise CallRefused(REASON_CONNECTION_BUSY, pauses_job=False)


def select_member(
    session: Session, repository: Any, dispatch: GroupDispatch, *, offline_wait_seconds: int,
) -> Selection:
    """Take the group's and the members' locks, read the job under them and answer the member the call goes to (steps 1 to 4 of the
    module). Writes nothing but the job's wait (committed on its way out through a refusal); the caller applies the ceilings and
    writes the binding. Raises ``CallRefused``: ``connection_busy`` (a wait), ``no_executor_online`` (the wait is over),
    ``consent_stale`` (the consent does not hold; the job pauses for a new one) or ``executor_route_missing``."""
    from auditmanager.executors.public import choose, current_revision, group_revision_of

    jobs = dispatch.jobs
    rotation = repository.lock_group(session, dispatch.group_id)
    revision = None if rotation is None else group_revision_of(session, dispatch.group_revision_id)
    if rotation is None or revision is None or revision.group_id != dispatch.group_id:
        raise CallRefused(REASON_EXECUTOR_ROUTE_MISSING, pauses_job=False)
    for connection_id in sorted({member.connection_id for member in revision.members}):
        repository.lock_connection(session, connection_id)
    job = jobs.get(session, dispatch.job_id)
    if (job is None or job.executor_group_revision_id != dispatch.group_revision_id
            or job.binding_state not in (BINDING_PENDING, BINDING_BOUND)):
        raise CallRefused(REASON_CONSENT_STALE, pauses_job=True)

    if job.binding_state == BINDING_BOUND:
        # Another item of the job bound it first. Decision 16: it stays on that member, whatever the group looks like now.
        connection_id = repository.connection_of(session, job.connection_revision_id)
        if connection_id is None:
            raise CallRefused(REASON_EXECUTOR_ROUTE_MISSING, pauses_job=False)
        if not repository.connection_has_free_unit(session, connection_id):
            raise CallRefused(REASON_CONNECTION_BUSY, pauses_job=False)
        return Selection(
            _open_member(session, dispatch, job.connection_revision_id), connection_id, job.connection_revision_id, binds=False,
        )

    eligible = [facts for facts in member_facts_of(session, revision) if is_eligible(facts)]
    chosen = choose(
        [facts.as_member() for facts in eligible], {facts.connection_id: facts.used for facts in eligible},
        {facts.connection_id: facts.capacity for facts in eligible}, rotation,
    )
    if chosen is None:
        _wait(session, dispatch, any_eligible=bool(eligible), offline_wait_seconds=offline_wait_seconds)
    snapshot = next(member.connection_revision_id for member in revision.members if member.connection_id == chosen)
    problem = consent_problem(job, revision, current_revision(session, chosen), snapshot)
    if problem is not None:
        jobs.set_wait(session, dispatch.job_id, WAIT_NEEDS_RECONSENT)
        session.commit()
        raise CallRefused(REASON_CONSENT_STALE, pauses_job=True)
    return Selection(_open_member(session, dispatch, snapshot), chosen, snapshot, binds=True)


def write_binding(session: Session, dispatch: GroupDispatch, selection: Selection) -> None:
    """``pending -> bound`` with the member's revision, and the journal event of it. In the caller's transaction, once: the database
    refuses a second write of the revision and a revision that is not a member of the job's group revision."""
    from auditmanager.jobs.public import append_execution_event

    if not dispatch.jobs.bind(session, dispatch.job_id, connection_revision_id=selection.revision_id):
        raise CallRefused(REASON_CONSENT_STALE, pauses_job=True)
    append_execution_event(
        session, event_type=EVENT_JOB_BOUND, aggregate_type=_EVENT_AGGREGATE, aggregate_id=dispatch.job_id,
        payload={
            "job_id": dispatch.job_id, "connection_id": selection.connection_id, "revision_id": selection.revision_id,
            "work_kind": dispatch.work_kind, "from_state": BINDING_PENDING, "to_state": BINDING_BOUND,
        },
    )
