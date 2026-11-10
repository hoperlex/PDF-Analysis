"""The frozen cell of a comparison job, applied to its calls (`HOSTS-CMP-01`, ADR-0028 decision 19; `LIMITS-01`).

A comparison job admitted under the stage layout froze one cell with its estimate (``AiRoute.cell``): the model and the effort the owner chose
for that kind of work. This module says what the cell does to **one call**; the spend wrapper
(:meth:`~auditmanager.comparison.spend.caller.ComparisonModelCaller.call`) applies it to every call of the job, before the request is hashed, priced
and journalled, so a method builds its request as it always did and no method can forget the cell.

* **effort** -- the cell's effort replaces the module's (``ai_pairs`` ``EFFORT``, the literal ``"high"`` of ``ai_sheets`` and ``report``, and the
  absent one of ``specification``): ``output_config.effort`` of the body;
* **timeout** -- the host task window of the call: :func:`host_call_of` is what the route's binder hands the pull adapter (``executors.public.HostCall``),
  which takes the smaller of it and what the attempt's watchdog leaves. It is the constant of the cell's kind
  (``analysis.text.cell_settings.COMPARISON_TIMEOUT_SECONDS``, the original's values), never a stored number (`R-153o`).

**No answer cap** (`R-153n`). A cell has no answer limit, so nothing here caps a request: the body keeps the ``max_tokens`` the module wrote, which
is the figure the call is hashed and priced at -- an estimate -- and the host task carries no ``max_output_tokens`` at all. (Until `LIMITS-01` the cell
held ``min(module limit, cell limit)`` and `D-677` told the agent that smaller number; both are gone.)

A job admitted by the legacy route or by a rule has no cell and nothing here changes a call of it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from auditmanager.comparison.spend.model import CallEstimate

if TYPE_CHECKING:
    from auditmanager.analysis.public import CellSettings, ModelRequest
    from auditmanager.executors.public import HostCall

__all__ = ["apply_cell", "host_call_of"]


def apply_cell(
    cell: "CellSettings | None", request: "ModelRequest", estimate: CallEstimate,
) -> tuple["ModelRequest", CallEstimate]:
    """The request and the estimate of one call as the job's cell says: the cell's effort in the body; the estimate unchanged (the module's own
    output figure -- the cell adds no cap). ``None`` returns both unchanged."""
    if cell is None:
        return request, estimate
    body: dict[str, Any] = dict(request.body)
    output_config = dict(body.get("output_config") or {})
    output_config["effort"] = cell.effort
    body["output_config"] = output_config
    return replace(request, body=body), estimate


def host_call_of(cell: "CellSettings", *, provider: str, access: str) -> "HostCall":
    """What a host agent is told beside the prompt (``payload.host``) for a call of this cell: the provider and access of the member the job is
    bound to, the cell's model and effort, its timeout and its key (``comparison_pair_check:main``). The route's binder, which knows the member,
    builds it from ``job.cell``; ``timeout_seconds`` is what makes the kind's constant the task's window. There is no answer cap among the members."""
    from auditmanager.executors.public import HostCall

    return HostCall(
        provider=provider, access=access, model_id=cell.model_id, effort=cell.effort, timeout_seconds=cell.timeout_seconds,
        cell_key=cell.cell_key,
    )
