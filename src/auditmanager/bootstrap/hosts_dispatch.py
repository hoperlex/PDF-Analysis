"""Dispatch of a planned run and the claim of a host token (`HOSTS-BACKEND-01`, ADR-0028): the two seams `HOSTS-SEAL-1` shipped as stubs.

``bind_planned_run``
    A run frozen with a ``stage_plan`` is ``pending``. At dispatch **every cell** of its plan is bound, in one transaction, each to a member of
    the system group of its (model, access): rows of ``audit_run_cell_binding`` (written once; the trigger accepts only a system member that
    pins the cell's model), then ``binding_state`` ``pending`` -> ``bound``, which the database allows only when every cell has its row. If one
    cell has no available member -- or the pools of the ones that are available are full -- the run stays ``pending`` with ``wait_reason``
    ``model_unavailable`` (or ``executor_at_capacity``) and the cells named; nothing has run, nothing is lost. The unit of capacity is the pair (run,
    ``capacity_pool`` = host and provider); the advisory lock is taken by pool, in ascending order, in the four places the plan names (claim, hint,
    comparison mirror, binding). **The worker's claim does exactly this inside its own transaction** (``jobs.repository.JobRepository._claim``), so
    no model I/O can precede the binding; this function is the same step for a caller that owns the run's transaction.
``claim_for_host_token``
    A host token claims the tasks of the system connections of its host: the task carries provider, access, model, effort, limits and cell key (all
    seven or none); the agent refuses a model it does not report as verified. It is ``executors.runner.claim_task`` for a principal that names a host.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.runs.public import ModelAvailability
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["DEPENDENCY", "HostModelAvailability", "bind_planned_run", "claim_for_host_token"]

DEPENDENCY: Final[str] = "executor_host_dispatch"


def bind_planned_run(session: Session, *, run_id: str) -> Any:
    """Bind every cell of the run's frozen stage plan, or leave it ``pending`` naming the cells that wait.

    Answers the :class:`~auditmanager.executors.public.BoundCell` tuple that was bound, or the
    :class:`~auditmanager.executors.public.BindOutcome` that says why not (``bound`` is ``None``; ``reason`` and ``waits`` name it) after storing the
    wait. The caller owns the transaction. ``conflict`` for a run that is not ``pending`` with a plan."""
    from auditmanager.jobs.repository import GroupDispatchWaiting, JobRepository

    jobs = JobRepository()
    row = session.execute(text(
        "SELECT binding_state, stage_plan FROM audit_run WHERE run_id = :run FOR UPDATE"), {"run": run_id}).first()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    if row[0] != "pending" or row[1] is None:
        raise DomainError(ErrorCode.CONFLICT, message="the run is not a pending planned run", aggregate_type="AuditRun")
    try:
        bound = JobRepository._select_cells(session, run_id=run_id, stage_plan=row[1])
    except GroupDispatchWaiting as waiting:
        from auditmanager.executors.public import cell_requests, evaluate_wait

        jobs.record_group_wait(session, run_id=run_id, reason=waiting.wait_reason)
        return evaluate_wait(session, run_id=run_id, cells=cell_requests(row[1]))
    jobs._bind_planned(session, run_id=run_id, bound=bound)
    return bound


class _Borrowed:
    """A session factory that lends one session and leaves its closing to its owner."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @contextmanager
    def __call__(self) -> Iterator[Session]:
        yield self._session


def claim_for_host_token(session: Session, *, token_id: str, runner_instance_id: str | None, wait_seconds: int) -> Any:
    """Hand a host token the next task of any system connection of its host that it may run, or none.

    ``DomainError`` ``authentication_required`` for a token that is not a usable host token. Each poll commits the borrowed session (a claim is a
    short transaction of its own); the long poll's bounds are ``claim_task``'s."""
    from auditmanager.executors.public import RunnerPrincipal, claim_task

    host_id = session.execute(text(
        "SELECT host_id FROM executor_runner_token WHERE token_id = :t"), {"t": token_id}).scalar_one_or_none()
    if host_id is None:
        raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)
    return claim_task(
        _Borrowed(session), RunnerPrincipal(token_id=token_id, connection_id=None, host_id=str(host_id)),
        wait_seconds=wait_seconds, runner_instance_id=runner_instance_id)


class HostModelAvailability:
    """``runs.ModelAvailabilityPort`` over the servers (`HOSTS-INT-WIRE-01`, ADR-0028 decisions 3 and 16): can a catalogue model be served **now**,
    and by which kind of access?

    Answered from the facts of every live host, computed on read (``executors.public.read_hosts`` and ``model_availability``): a model is
    served by *subscription* (or *api*) when some host has it ``available`` -- or ``busy``, which is available with every slot taken: a run then
    waits for the unit, it is not refused (``executor_at_capacity``). A model no host can serve now carries the **one** reason of the host closest
    to serving it (the fewest reasons, then the most actionable one), the order ``REASON_ORDER`` gives, the same choice the binding's wait makes
    (``cell_binding._cause_of``). A model no live host reports is left out of the answer, which the port reads as ``not_on_any_server``.
    Read-only; it writes nothing and calls no model."""

    def availability(self, session: Session, model_ids: Sequence[str]) -> Mapping[str, ModelAvailability]:
        from auditmanager.executors.public import REASON_ORDER, model_availability, read_hosts

        wanted = set(model_ids)
        served: dict[str, set[str]] = {}
        closest: dict[str, tuple[str, ...]] = {}
        for facts in read_hosts(session):
            for item in model_availability(facts):
                if item.model_id not in wanted:
                    continue
                if item.state in ("available", "busy"):
                    served.setdefault(item.model_id, set()).add(item.access)
                    continue
                current = closest.get(item.model_id)
                if item.reasons and (current is None or len(item.reasons) < len(current)):
                    closest[item.model_id] = item.reasons
        answer: dict[str, ModelAvailability] = {}
        for model_id in wanted:
            accesses = served.get(model_id, set())
            if accesses:
                answer[model_id] = ModelAvailability(subscription="subscription" in accesses, api="api" in accesses)
            elif model_id in closest:
                answer[model_id] = ModelAvailability(reasons=(min(closest[model_id], key=REASON_ORDER.index),))
            # a model no live host reports stays out of the answer: the port reads that as ``not_on_any_server``
        return answer
