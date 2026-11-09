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
  which takes the smaller of it and what the attempt's watchdog leaves.

A job admitted by the legacy route or by a rule has no cell and nothing here changes a call of it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from auditmanager.comparison.spend.model import CallEstimate

if TYPE_CHECKING:
    from auditmanager.analysis.public import CellSettings, ModelRequest
    from auditmanager.executors.public import HostCall

__all__ = ["apply_cell", "capped_output_tokens", "host_call_of"]


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


def host_call_of(cell: "CellSettings", *, provider: str, access: str) -> "HostCall":
    """What a host agent is told beside the prompt (``payload.host``) for a call of this cell: the provider and access of the member the job is
    bound to, the cell's model, effort and limit, its timeout and its key (``comparison_pair_check:main``). The route's binder, which knows the
    member, builds it from ``job.cell``; ``timeout_seconds`` is what makes the cell's timeout the task's window."""
    from auditmanager.executors.public import HostCall

    return HostCall(
        provider=provider, access=access, model_id=cell.model_id, effort=cell.effort, max_output_tokens=cell.max_output_tokens,
        timeout_seconds=cell.timeout_seconds, cell_key=cell.cell_key,
    )
