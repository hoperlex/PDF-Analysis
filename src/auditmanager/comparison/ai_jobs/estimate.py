"""The estimate protocol (`CMP-AI-JOBS-01`, ADR-0025 decisions 10 and 19, `Q-CMP-7`).

A method supplies the **counts** of what it would send (:class:`~.model.AiCounts`); this module turns them into the contract's
estimate without a model call:

1. the **route** -- the current revision of the connection routed for the method's work kind in «Назначения»
   (``executors.public.resolve_route``) and the model that revision pins (``pinned_models``). No route, no revision or an
   unpinned model is ``dependency_unavailable`` / ``executor_route_missing``: nothing falls back, and the standby is not
   priced -- it serves only when the primary cannot, and a job that meets it pauses ``route_changed``;
2. the **price** -- the pinned rates over the summed input and output tokens, in integer micro-USD rounded **up** (the
   spend wrapper prices a call the same way); a connection that is ``not_metered`` has ``estimate_micros`` 0, no ceiling and
   no ``blocked_by``;
3. the **ceilings** -- ``blocked_by`` is ``job`` when what the job has already spent plus this estimate passes USD 10, ``day``
   when what the installation has spent or reserved today plus this estimate passes USD 50 (both by ``>``: reaching a ceiling
   exactly is allowed, as in :mod:`auditmanager.comparison.spend.ceilings`);
4. the **digest** -- :func:`~.model.digest_of`.

:func:`build_estimate` is pure: the route, the counts and the two spend figures are its inputs.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.model import (
    AiCounts,
    AiEstimate,
    AiScope,
    AiMode,
    AiRoute,
    digest_of,
)
from auditmanager.comparison.spend.model import (
    DAY_CEILING_MICROS,
    JOB_CEILING_MICROS,
    estimate_micros_of,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["RouteReader", "build_estimate", "read_route", "route_missing"]

#: ``(session, work_kind, provider_mode) -> AiRoute``; the default reads «Назначения», a test may inject another.
RouteReader = Callable[[Session, str, str], AiRoute]

DEPENDENCY_ROUTE_MISSING = "executor_route_missing"


def route_missing() -> DomainError:
    """``503 dependency_unavailable`` naming the stable class ``executor_route_missing`` (no route for a work kind)."""
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="no usable executor connection is routed for this kind of work",
        dependency=DEPENDENCY_ROUTE_MISSING,
    )


def read_route(session: Session, work_kind: str, provider_mode: str) -> AiRoute:
    """The route a start would use: the primary of ``work_kind``'s current route, at its current revision."""
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


def build_estimate(
    *, scope: AiScope, mode: AiMode, prompt_version: str, counts: AiCounts, route: AiRoute,
    job_spent_micros: int = 0, day_committed_micros: int = 0,
) -> AiEstimate:
    """The estimate of ``counts`` over ``route``. ``job_spent_micros`` is what the job has already spent or reserved (0 for a
    new job); ``day_committed_micros`` is what the installation has spent or reserved today. Neither is in the digest."""
    if route.work_kind != scope.work_kind:
        raise ValueError("the route is the route of another kind of work")
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
