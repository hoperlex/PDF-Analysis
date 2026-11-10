"""The frozen cell of a comparison job, applied to its calls (`HOSTS-CMP-01`, ADR-0028 decision 19).

A comparison job admitted under the stage layout froze one cell with its estimate (``AiRoute.cell``): the effort, the answer limit and the
timeout the owner chose for that kind of work. This module says what the cell does to **one call**; the spend wrapper
(:meth:`~auditmanager.comparison.spend.caller.ComparisonModelCaller.call`) applies it to every call of the job, before the request is hashed, priced
and journalled, so a method builds its request as it always did and no method can forget the cell.

* **effort** -- the cell's effort replaces the module's (``ai_pairs`` ``EFFORT``, the literal ``"high"`` of ``ai_sheets`` and ``report``, and the
  absent one of ``specification``): ``output_config.effort`` of the body;
* **answer limit** -- a ceiling over the module's own, ``min(module limit, cell limit)``: ``max_tokens`` of the body, and the output tokens the call is
  priced at. A request that names no limit takes the cell's;
* **timeout** -- the host task window of the call: :func:`host_call_of` is what the route's binder hands the pull adapter (``executors.public.HostCall``),
  which takes the smaller of it and what the attempt's watchdog leaves;
* **the ceiling the host is told** (`D-677`) -- the answer limit of the *request* that is sent, not the cell's alone: ``host_call_of`` builds one call per
  route, but the limit differs per request (a module's own, cut by :func:`apply_cell`), so the host call reads it from the request being sent
  (:func:`answer_limit_of`, entered by ``PublishedPullAdapter.complete``) and tells the agent ``min(request limit, cell limit)``.

A job admitted by the legacy route or by a rule has no cell and nothing here changes a call of it.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from functools import cache
from typing import TYPE_CHECKING, Any

from auditmanager.comparison.spend.model import CallEstimate

if TYPE_CHECKING:
    from auditmanager.analysis.public import CellSettings, ModelRequest
    from auditmanager.executors.public import HostCall

__all__ = ["answer_limit_of", "apply_cell", "capped_output_tokens", "host_call_of"]


def capped_output_tokens(module_limit: int, cell: "CellSettings | None") -> int:
    """``min(module limit, the cell's)``; the module's own limit when there is no cell."""
    return module_limit if cell is None else min(module_limit, cell.max_output_tokens)


def apply_cell(
    cell: "CellSettings | None", request: "ModelRequest", estimate: CallEstimate,
) -> tuple["ModelRequest", CallEstimate]:
    """The request and the estimate of one call as the job's cell says. ``None`` returns both unchanged."""
    if cell is None:
        return request, estimate
    body: dict[str, Any] = dict(request.body)
    named = body.get("max_tokens")
    body["max_tokens"] = cell.max_output_tokens if type(named) is not int else capped_output_tokens(named, cell)
    output_config = dict(body.get("output_config") or {})
    output_config["effort"] = cell.effort
    body["output_config"] = output_config
    return (
        replace(request, body=body),
        CallEstimate(input_tokens=estimate.input_tokens, output_tokens=capped_output_tokens(estimate.output_tokens, cell)),
    )


#: The answer limit of the request being sent on this thread of control, or ``None`` outside :func:`answer_limit_of`. A ``ContextVar``, so a call
#: made in another thread (a heartbeat, a second worker slot) never sees it, and it is reset when the call ends however it ends.
_REQUEST_LIMIT: ContextVar[int | None] = ContextVar("comparison_request_answer_limit", default=None)


@contextmanager
def answer_limit_of(request: "ModelRequest") -> Iterator[None]:
    """Within the block, a host call of :func:`host_call_of` tells the agent the answer limit of ``request`` (``body.max_tokens``, which
    :func:`apply_cell` has already held to the cell's) instead of the cell's alone. A request that names no limit changes nothing."""
    named = request.body.get("max_tokens")
    token = _REQUEST_LIMIT.set(named if type(named) is int and named > 0 else None)
    try:
        yield
    finally:
        _REQUEST_LIMIT.reset(token)


@cache
def _cell_host_call() -> "type[HostCall]":
    """``HostCall`` whose ``members`` carry the smaller of the request's limit and the cell's. Built on first use: ``executors.public`` is
    imported inside functions in this package (see ``spend/dispatch.py``), never at import time."""
    from auditmanager.executors.public import HostCall

    class CellHostCall(HostCall):
        __slots__ = ()

        def members(self, window_seconds: float) -> dict[str, Any]:
            members = HostCall.members(self, window_seconds)
            limit = _REQUEST_LIMIT.get()
            if limit is not None:
                members["max_output_tokens"] = min(limit, self.max_output_tokens)
            return members

    return CellHostCall


def host_call_of(cell: "CellSettings", *, provider: str, access: str) -> "HostCall":
    """What a host agent is told beside the prompt (``payload.host``) for a call of this cell: the provider and access of the member the job is
    bound to, the cell's model, effort and limit, its timeout and its key (``comparison_pair_check:main``). The route's binder, which knows the
    member, builds it from ``job.cell``; ``timeout_seconds`` is what makes the cell's timeout the task's window. ``max_output_tokens`` is the cell's
    ceiling; within :func:`answer_limit_of` the task carries the smaller limit of the request that is sent (`D-677`)."""
    return _cell_host_call()(
        provider=provider, access=access, model_id=cell.model_id, effort=cell.effort, max_output_tokens=cell.max_output_tokens,
        timeout_seconds=cell.timeout_seconds, cell_key=cell.cell_key,
    )
