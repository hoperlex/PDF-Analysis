"""The route of a comparison kind under the stage layout (`HOSTS-CMP-01`, ADR-0028 decision 19, ADR-0026 decisions 12 and 13).

With the stage layout switched on and the provider source ``database``, the four kinds of comparison work that call a model --
``comparison_pair_check``, ``comparison_sheet_changes``, ``comparison_spec`` and ``comparison_report`` -- are served by the same system
groups as the analysis. This module is the third branch of :func:`~auditmanager.comparison.ai_jobs.estimate.read_route`:

1. the **cell** of the kind, read from the layout revision in force (``runs.public``: the layout is the runs context's, this module only reads
   it): model, effort, answer limit and timeout;
2. the **access**, chosen as the stage-plan freezer chooses it -- a subscription when a subscription server can serve the model, otherwise an API
   key. "Can serve" is what a run's binding asks (``executors.public.evaluate_wait``): a member of the pair's system group that is on line, signed in,
   verified for the model and not cooling down. A member whose pool is full still counts: the job is admitted and waits for the unit as every
   group job does (``executor_at_capacity``), it does not pay for an API key because a subscription is busy;
3. the **system group** ``pair_group_name(model, access)`` and its current revision, as a route (``route_of_group_revision``) that carries the
   cell. The job freezes that group revision and the cell with its estimate, so its consent names both and the existing group dispatch and the
   spend mirror (the pool lock) serve it unchanged.

A kind whose model has no available member is refused here, with the existing typed answer for an unavailable route
(``503 dependency_unavailable``, ``executor_route_missing``). It is never routed somewhere else (``AGENTS.md`` section 4): not to the legacy
connection, not to a rule, not to another model. The same answer is given for a layout that is on while the provider source is not
``database`` (the freezer's own refusal of a run) and for a revision that has no cell for the kind (« Свой набор » saved without them).

With the switch off, and for a kind the layout holds no cell for (``comparison_stage_review``), nothing here answers and the route is what it
always was: legacy, or the work kind's rule.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

from sqlalchemy.orm import Session

from auditmanager.comparison.ai_jobs.estimate import DEPENDENCY_ROUTE_MISSING, route_of_group_revision
from auditmanager.comparison.ai_jobs.model import AiRoute
from auditmanager.shared.errors import DomainError, ErrorCode

if TYPE_CHECKING:  # the type only: ``analysis`` is read through its public face, at run time none of it is needed here
    from auditmanager.analysis.public import CellSettings

__all__ = ["ACCESS_ORDER", "PROVIDER_SOURCE_ENV", "layout_serving", "read_layout_route"]

#: Which access is tried first: a subscription before an API key (ADR-0028 decision 2), as ``runs.stage_plan.ModelAvailability.access`` says.
ACCESS_ORDER: Final[tuple[str, ...]] = ("subscription", "api")
#: The process's provider source, read where ``bootstrap.stage_plan_service`` reads it.
PROVIDER_SOURCE_ENV: Final[str] = "AUDITMANAGER_PROVIDER_SOURCE"


def _refused(message: str) -> DomainError:
    """``503 dependency_unavailable`` naming ``executor_route_missing``: the one answer for a route that does not exist, whatever the reason."""
    return DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, message=message, dependency=DEPENDENCY_ROUTE_MISSING)


def layout_serving(session: Session, work_kind: str, cell: "CellSettings") -> tuple[str, str]:
    """``(access, group revision id)`` of the system group that serves ``cell`` now, subscription first, or ``executor_route_missing``.

    Reads only; takes no lock and binds nothing. The member is chosen later, at the job's first call, under the group's and the pool's locks."""
    from auditmanager.executors.public import (
        AT_CAPACITY, CellRequest, HostRepository, evaluate_wait, group_detail, pair_group_name,
    )

    for access in ACCESS_ORDER:
        outcome = evaluate_wait(
            session, run_id=f"layout:{work_kind}", cells=[CellRequest(cell.cell_key, cell.model_id, access)])
        if outcome.bound:  # a member is free this instant: the revision the binding read is the one to freeze
            return access, outcome.bound[0].group_revision_id
        if any(wait.cause == AT_CAPACITY for wait in outcome.waits):  # available, only the pool is full: the job waits for the unit
            group_id = HostRepository().system_group_for(session, pair_group_name(cell.model_id, access))
            revisions = () if group_id is None else group_detail(session, group_id).revisions
            if revisions:
                return access, revisions[0].group_revision_id
    raise _refused("no server serves the model of this kind of work")


def read_layout_route(
    session: Session, work_kind: str, provider_mode: str, *, provider_source: str | None = None,
) -> AiRoute | None:
    """The route of ``work_kind`` under the stage layout, or ``None`` when the layout does not serve this kind now (the switch is off, or the
    layout holds no cell of this kind at all). Raises ``executor_route_missing`` when it does and cannot (see the module note)."""
    from auditmanager.runs.public import COMPARISON_KINDS, PROVIDER_SOURCE_DATABASE, SqlStageLayoutStore

    if work_kind not in COMPARISON_KINDS:
        return None
    store = SqlStageLayoutStore()
    if not store.enabled(session):
        return None
    source = provider_source if provider_source is not None else os.environ.get(PROVIDER_SOURCE_ENV, "environment").strip() or "environment"
    if source != PROVIDER_SOURCE_DATABASE:
        raise _refused("the stage layout needs the database provider source")
    revision = store.current_revision(session)
    cell = None if revision is None else revision.comparison_cell(work_kind)
    if cell is None:
        raise _refused("the stage layout has no cell for this kind of work")
    _access, group_revision_id = layout_serving(session, work_kind, cell)
    route = route_of_group_revision(
        session, group_revision_id, work_kind=work_kind, provider_mode=provider_mode, rule_revision_id=None, cell=cell)
    if route.pinned_model != cell.model_id:  # the system group of a pair pins its model; anything else is not the cell's group
        raise _refused("the group that serves this kind of work does not pin the model of its cell")
    return route
