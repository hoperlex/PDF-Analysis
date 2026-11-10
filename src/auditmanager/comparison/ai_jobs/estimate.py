"""The estimate protocol (`CMP-AI-JOBS-01`, ADR-0025 decisions 10 and 19, `Q-CMP-7`).

A method supplies the **counts** of what it would send (:class:`~.model.AiCounts`); this module turns them into the contract's
estimate without a model call:

1. the **route** -- while the routing mode is ``legacy``, the current revision of the connection routed for the method's work
   kind in «Назначения» (``executors.public.resolve_route``) and the model that revision pins (``pinned_models``). No route, no
   revision or an unpinned model is ``dependency_unavailable`` / ``executor_route_missing``: nothing falls back, and the
   standby is not priced -- it serves only when the primary cannot, and a job that meets it pauses ``route_changed``.
   `EXEC2-GROUP-CMP-01` (ADR-0026 decisions 13 and 17): while the mode is ``rules``, the route is the group revision the
   work kind's **current rule** names -- its ``pin_id``, its rate snapshot and its billing -- with no connection (the job's
   first dispatched call chooses a member); a work kind with no rule is ``dependency_unavailable`` /
   ``no_rule_for_work_kind``. `HOSTS-CMP-01` (ADR-0028 decision 19): while the stage layout is on, it comes first -- the route is the current
   revision of the system group that serves the **cell** of the work kind (:mod:`~auditmanager.comparison.ai_jobs.layout_route`), and carries
   that cell; a kind whose model no server serves is ``executor_route_missing``, never read from the legacy route or a rule. A job that was admitted by a group is re-estimated (a resume, a retry) on **its own** group
   revision, never on the rule as it is now, and a job made before the cut-over is re-estimated through the legacy route;
2. the **price** -- the pinned rates over the summed input and output tokens, in integer micro-USD rounded **up** (the
   spend wrapper prices a call the same way); a connection that is ``not_metered`` has ``estimate_micros`` 0, no ceiling and
   no ``blocked_by``;
3. the **ceilings** -- ``blocked_by`` is ``job`` when what the job has already spent plus this estimate passes USD 10, ``day``
   when what the installation has spent or reserved today plus this estimate passes USD 50 (both by ``>``: reaching a ceiling
   exactly is allowed, as in :mod:`auditmanager.comparison.spend.ceilings`);
4. the **digest** -- :func:`~.model.digest_of`.

An estimate is always computed at the snapshot of the route it reads. Whether a group revision's rate snapshot is still the provider
lock's (`EXEC2-FOLLOWUP-01`) is a separate question, :func:`require_group_rates_hold`, which the services behind the operations that declare
``422`` ask before a consent is taken or renewed.

:func:`build_estimate` is pure: the route, the counts and the two spend figures are its inputs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import (
    AiCounts,
    AiEstimate,
    AiScope,
    AiMode,
    AiRoute,
    digest_of,
    work_kind_of,
)
from auditmanager.comparison.spend.dispatch import group_pin, group_rates_hold, lock_pin
from auditmanager.comparison.spend.model import (
    DAY_CEILING_MICROS,
    JOB_CEILING_MICROS,
    estimate_micros_of,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "JOB_ROUTE_KEY",
    "REASON_RATES_STALE",
    "RouteReader",
    "build_estimate",
    "group_rates_stale",
    "no_rule_for_work_kind",
    "read_job_route",
    "read_legacy_route",
    "read_route",
    "read_rule_route",
    "require_group_rates_hold",
    "route_missing",
    "route_of_group_revision",
]

#: ``(session, work_kind, provider_mode) -> AiRoute``; the default reads the route in force (the legacy «Назначения» or the
#: work kind's rule, by the routing mode), a test may inject another.
RouteReader = Callable[[Session, str, str], AiRoute]

DEPENDENCY_ROUTE_MISSING = "executor_route_missing"
#: `EXEC2-FOLLOWUP-01`. The registered ``analysis_input_invalid`` reason of an accepted model, rate or revision authority that no longer holds
#: (``error-codes.json``, «cost preflight reasons»); ``runs.cost_policy`` raises the same word for a Run.
REASON_RATES_STALE: Final[str] = "cost_estimate_binding_changed"
#: `EXEC2-GROUP-CMP-01` (ADR-0026 decisions 17 and 18). The ``dependency`` of the refusal of a work kind that has no rule while the
#: routing mode is ``rules`` (``auditmanager.executors.model.DEPENDENCY_NO_RULE_FOR_WORK_KIND`` is the same word; a test pins the two).
DEPENDENCY_NO_RULE_FOR_WORK_KIND: Final[str] = "no_rule_for_work_kind"
#: ``routing_mode(session).mode`` while the cut-over has been confirmed (``auditmanager.executors.model.ROUTING_MODE_RULES``).
ROUTING_MODE_RULES: Final[str] = "rules"
#: The ``Session.info`` key under which :meth:`~auditmanager.comparison.ai_jobs.service.ComparisonAiJobService.estimate_in` puts the route of
#: the job it is re-estimating while a method counts: the methods price their stored answers by the model they read from
#: :func:`read_route`, and the model of a job that is already admitted is its own, not the one of the rule now.
JOB_ROUTE_KEY: Final[str] = "auditmanager.comparison.job_route"


def route_missing() -> DomainError:
    """``503 dependency_unavailable`` naming the stable class ``executor_route_missing`` (no route for a work kind)."""
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="no usable executor connection is routed for this kind of work",
        dependency=DEPENDENCY_ROUTE_MISSING,
    )


def group_rates_stale(work_kind: str) -> DomainError:
    """``422 analysis_input_invalid`` with ``reason: cost_estimate_binding_changed`` (`EXEC2-FOLLOWUP-01`): the rates the group revision
    snapshotted are not the rates the provider lock prices its model at now, so no consent on this group can be honoured -- the first
    call would refuse it, and a new consent would be priced on the same snapshot and refused again. The group must be rebuilt (a new
    revision copies the lock's rates).

    An existing registered refusal, not a new one: the catalogue's «cost preflight reasons» name ``cost_estimate_binding_changed`` for an
    accepted model, rate or revision authority that no longer holds, and the Run path raises it for the same fact
    (``analysis.text.cost.require_approved_model``, ``runs.cost_policy``). ``stage_id`` names the kind of work, as the summary's refusal
    names its own (``comparison_summary``).

    **Only operations that declare 422 may raise it** (:func:`require_group_rates_hold` says which, and a contract-driven test holds the
    list): the contract's 422 is part of an operation's declared answers, and an operation that declares none answers what it declares."""
    return DomainError(
        ErrorCode.ANALYSIS_INPUT_INVALID,
        message="the rates this group was made on are not the rates its model is priced at now; the group must be rebuilt",
        stage_id=work_kind, reason=REASON_RATES_STALE,
    )


def require_group_rates_hold(session: Session, route: AiRoute) -> None:
    """Refuse, before a consent is taken or renewed, a group route whose rate snapshot is not the provider lock's now (`EXEC2-FOLLOWUP-01`).

    An **explicit seam**, called by the services behind the operations that declare ``422`` and by nothing else: a start
    (``ComparisonAiJobService.start_in_session``, which every ``start*`` operation and the stage chain go through), a resume or a retry
    (``ComparisonAiJobService._renew_consent``), and the estimate of the sheet-changes series (``ComparisonAiSheetService.estimate_series``).
    ``read_route`` and the estimate itself do **not** refuse: the estimate operations that declare no ``422`` (a pair check's, a sheet
    description's, a specification's) are computed at the group's snapshot, as they always were, and the start that follows refuses with the
    clear message; ``finish`` (also without a ``422``) proceeds, and the first call of the job refuses it instead (``consent_stale``, the job
    pauses). ``tests/unit/comparison/ai_jobs/test_group_rates_seam.py`` reads the contract and holds each of these to its declared answers.

    The pin comes first: a lock that no longer pins the group's model makes the route unusable, ``executor_route_missing``, before any rates
    are compared. A route that names a connection (every job made before the cut-over) has no snapshot and is not asked."""
    if route.executor_group_revision_id is None:
        return
    from auditmanager.executors.public import group_revision_of

    revision = group_revision_of(session, route.executor_group_revision_id)
    if revision is None or lock_pin(revision.pin_id) is None:
        raise route_missing()
    if not group_rates_hold(revision):
        raise group_rates_stale(route.work_kind)


def no_rule_for_work_kind() -> DomainError:
    """``503 dependency_unavailable`` naming ``no_rule_for_work_kind``: the routing mode is ``rules`` and this kind of work has
    no rule. Nothing is created and nothing falls back to the legacy route."""
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="no routing rule is set for this kind of work",
        dependency=DEPENDENCY_NO_RULE_FOR_WORK_KIND,
    )


def read_route(session: Session, work_kind: str, provider_mode: str) -> AiRoute:
    """The route a start would use: the stage layout's when it is on, else by the routing mode in force.

    The stage layout on (`HOSTS-CMP-01`): the system group that serves the cell of ``work_kind``
    (:func:`~auditmanager.comparison.ai_jobs.layout_route.read_layout_route`). It does not answer while the switch is off, nor for a kind the
    layout holds no cell of; the route is then what it always was.
    ``legacy`` (the default): the primary of ``work_kind``'s current route, at its current revision (:func:`read_legacy_route`).
    ``rules``: the group revision the work kind's current rule names (:func:`read_rule_route`). While a job is being re-estimated the
    route of **that job** answers (:data:`JOB_ROUTE_KEY`)."""
    from auditmanager.comparison.ai_jobs.layout_route import read_layout_route
    from auditmanager.executors.public import routing_mode

    override = session.info.get(JOB_ROUTE_KEY)
    if override is not None and override.work_kind == work_kind:
        return override
    layout = read_layout_route(session, work_kind, provider_mode)
    if layout is not None:
        return layout
    if routing_mode(session).mode == ROUTING_MODE_RULES:
        return read_rule_route(session, work_kind, provider_mode)
    return read_legacy_route(session, work_kind, provider_mode)


def read_legacy_route(session: Session, work_kind: str, provider_mode: str) -> AiRoute:
    """The primary of ``work_kind``'s current route, at its current revision, whatever the routing mode. A job made before the
    cut-over is re-estimated through it: the legacy route is read-only under ``rules`` and is not re-read for work admitted by a
    rule."""
    from auditmanager.executors.public import pinned_models, resolve_route

    resolved = resolve_route(session, work_kind)
    if resolved is None or resolved.primary is None:
        raise route_missing()
    revision = resolved.primary
    settings = revision.settings
    pin = next((candidate for candidate in pinned_models() if candidate.model_id == settings.pin_id), None)
    if pin is None:
        raise route_missing()
    return AiRoute(
        work_kind=work_kind, connection_id=revision.connection_id, revision_id=revision.revision_id,
        pinned_model=pin.model_id, gateway_model=settings.gateway_model, billing=settings.billing,
        provider_mode=provider_mode, pin=pin,
    )


def route_of_group_revision(
    session: Session, group_revision_id: str, *, work_kind: str, provider_mode: str, rule_revision_id: str | None,
    cell: Any = None,
) -> AiRoute:
    """The route of one immutable group revision: its model, its billing and its rate snapshot, with no connection. ``cell`` is the
    stage layout's cell of the work kind (`HOSTS-CMP-01`) when the layout chose the group, or the one a job froze.

    It **reads** and refuses nothing about the rates: an estimate is computed at the snapshot the group revision holds. Whether that snapshot
    is still the provider lock's is asked by :func:`require_group_rates_hold`, and only where the operation declares ``422``."""
    from auditmanager.executors.public import group_revision_of

    revision = group_revision_of(session, group_revision_id)
    if revision is None:
        raise route_missing()
    return AiRoute(
        work_kind=work_kind, connection_id=None, revision_id=None, pinned_model=revision.pin_id,
        gateway_model=revision.gateway_model, billing=revision.billing, provider_mode=provider_mode,
        pin=group_pin(revision), executor_group_id=revision.group_id,
        executor_group_revision_id=revision.group_revision_id, routing_rule_revision_id=rule_revision_id, cell=cell,
    )


def read_rule_route(session: Session, work_kind: str, provider_mode: str) -> AiRoute:
    """The route a start would use under mode ``rules``: the group revision the work kind's current rule names. A kind with no rule is
    ``dependency_unavailable`` / ``no_rule_for_work_kind``; the legacy route is not consulted."""
    from auditmanager.executors.public import resolve_rule

    rule = resolve_rule(session, work_kind)
    if rule is None:
        raise no_rule_for_work_kind()
    return route_of_group_revision(
        session, rule.group_revision_id, work_kind=work_kind, provider_mode=provider_mode,
        rule_revision_id=rule.rule_revision_id,
    )


def read_job_route(session: Session, job: Any, provider_mode: str) -> AiRoute:
    """The route of a job that was admitted by a rule or a group: the group revision it froze, whatever the rule says now
    (ADR-0026 decision 17: work already admitted finishes on its own group revision). A job the stage layout admitted keeps its own **cell** the
    same way (`HOSTS-CMP-01`): the layout is not read again."""
    if job.executor_group_revision_id is None:
        raise ValueError("only a job admitted by a group has a group route")
    return route_of_group_revision(
        session, job.executor_group_revision_id, work_kind=work_kind_of(job.method), provider_mode=provider_mode,
        rule_revision_id=job.routing_rule_revision_id, cell=job.cell,
    )


def build_estimate(
    *, scope: AiScope, mode: AiMode, prompt_version: str, counts: AiCounts, route: AiRoute,
    job_spent_micros: int = 0, day_committed_micros: int = 0,
) -> AiEstimate:
    """The estimate of ``counts`` over ``route``. ``job_spent_micros`` is what the job has already spent or reserved (0 for a
    new job); ``day_committed_micros`` is what the installation has spent or reserved today. Neither is in the digest."""
    if route.work_kind != scope.work_kind:
        raise ValueError("the route is the route of another kind of work")
    # `LIMITS-01`: a frozen cell has no answer limit, so nothing caps the counts: the estimate prices each call at the output figure of the
    # module that makes it (``AiCallGroup.output_tokens``) -- an estimate, not a cap on what the model answers.
    totals = counts.totals()
    if route.metered:
        if route.pin is None:
            raise route_missing()
        estimate_micros = estimate_micros_of(route.pin.cost_usd(
            input_tokens=totals.input_tokens, output_tokens=totals.output_tokens,
        ))
        ceiling_micros = JOB_CEILING_MICROS
        day_remaining = max(0, DAY_CEILING_MICROS - day_committed_micros)
        if job_spent_micros + estimate_micros > JOB_CEILING_MICROS:
            blocked: str | None = "job"
        elif day_committed_micros + estimate_micros > DAY_CEILING_MICROS:
            blocked = "day"
        else:
            blocked = None
    else:
        estimate_micros, ceiling_micros, day_remaining, blocked = 0, 0, None, None
    digest = digest_of(
        scope=scope, mode=mode, route=route, prompt_version=prompt_version, counts=counts, totals=totals,
        estimate_micros=estimate_micros, ceiling_micros=ceiling_micros,
    )
    return AiEstimate(
        scope=scope, mode=mode, route=route, prompt_version=prompt_version, counts=counts, totals=totals,
        estimate_micros=estimate_micros, ceiling_micros=ceiling_micros, estimate_digest=digest,
        day_remaining_micros=day_remaining, blocked_by=blocked,
    )
