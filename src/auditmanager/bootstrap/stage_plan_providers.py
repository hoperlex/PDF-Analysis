"""Providers of a planned run: what `HOSTS-SEAL-1` stubbed and `HOSTS-LAYOUT-01` fills (ADR-0028 decisions 5, 6 and 17).

A run frozen with a ``stage_plan`` has no connection of its own. ``StagePlanProviders`` is what the database provider source resolves such a
run through. For each **cell** of the plan it returns the adapter of the member the cell was bound to at dispatch
(``audit_run_cell_binding``, written once) and **one** ``CallBinding`` whose ``expected_model`` is the cell's model, so the identity check
(`R-133`) holds per call and a call with no binding is refused, never skipped.

* ``resolve(session, run, context)`` is what ``DatabaseProviders.resolve`` returns for a planned run: the plan's **text** cell as the run's
  binding (so the text stage runs on it unchanged), with ``cells`` set so every other phase asks ``runs.stage_plan.cell_binding`` for its row;
* ``binding_for(session, run_id=..., cell_key=...)`` is the one cell's binding.

The adapter of a member is built by the composition root (it holds the key ring, the destination policy and the pull runtime), handed in as
``binder``: ``binder(session, connection_revision_id=..., cell=..., context=...)`` returns a :class:`BoundMember`. This module reads no
secret, opens no connection and sends nothing; a refusal is a typed ``DomainError`` before any call.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Final, Protocol

from sqlalchemy.orm import Session

from auditmanager.analysis.public import CellSettings, ProviderMode
from auditmanager.analysis.text import CallBinding
from auditmanager.runs.provider import ProviderBinding
from auditmanager.runs.public import FrozenStagePlan, RunRepository, parse_plan
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["BoundMember", "DEPENDENCY", "MemberBinder", "StagePlanProviders"]

DEPENDENCY: Final[str] = "stage_plan_providers"


@dataclass(frozen=True, slots=True)
class BoundMember:
    """What the composition root's binder returns for one cell: the member's adapter and how its calls are recorded."""

    adapter: Any
    provider_label: str
    identity_basis: str
    connection_revision_id: str
    #: ``True`` for a subscription member (``billing = not_metered``): the cell's calls are counted and never charged.
    unmetered: bool
    host_id: str | None = None


class MemberBinder(Protocol):
    def __call__(self, session: Session, *, connection_revision_id: str, cell: CellSettings, context: Any) -> BoundMember: ...


def _refuse(reason: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason=reason)


class StagePlanProviders:
    def __init__(self, *, binder: MemberBinder, base_config: Any, runs: RunRepository | None = None) -> None:
        self._binder = binder
        self._base = base_config
        self._runs = runs or RunRepository()

    def resolve(self, session: Session, run: Any, context: Any = None) -> ProviderBinding:
        """The binding of a planned run: its text cell, with ``cells`` for the others. Refused before any call when the run has no plan, a
        cell has no binding row, or a member does not match the cell."""
        document = getattr(run, "stage_plan", None)
        if document is None:
            raise _refuse("run_has_no_stage_plan")
        plan = parse_plan(document)
        bound = self._runs.cell_bindings(session, run.run_id)
        if any(cell.cell_key not in bound for cell in plan.cells):
            raise _refuse("cell_not_bound")
        built: dict[str, ProviderBinding] = {}

        def cell_binding(cell_key: str) -> ProviderBinding:
            if cell_key not in built:
                built[cell_key] = self._bind(session, plan, bound[cell_key].connection_revision_id if cell_key in bound else None,
                                             cell_key, context)
            return built[cell_key]

        text = cell_binding("text:main")
        return ProviderBinding(adapter=text.adapter, config=text.config, call=text.call, cells=cell_binding)

    def binding_for(self, session: Session, *, run_id: str, cell_key: str, context: Any = None) -> ProviderBinding:
        """The adapter of the member bound to the cell and the ``CallBinding`` of the cell's model (one per call)."""
        return self.resolve(session, self._runs.get(session, run_id), context).cells(cell_key)

    def _bind(self, session: Session, plan: FrozenStagePlan, revision_id: str | None, cell_key: str, context: Any) -> ProviderBinding:
        cell = plan.cell(cell_key)
        if revision_id is None:
            raise _refuse("cell_not_bound")
        member = self._binder(session, connection_revision_id=revision_id, cell=cell, context=context)
        if member.connection_revision_id != revision_id or member.unmetered != (cell.access == "subscription"):
            # The member serves a cell the way it was not bound and priced: the consent does not cover it.
            raise _refuse("cost_estimate_binding_changed")
        call = CallBinding(
            provider_label=member.provider_label, expected_model=cell.model_id, check_identity=True, unmetered=member.unmetered,
            identity_basis=member.identity_basis, connection_revision_id=member.connection_revision_id,
            cell_key=cell.cell_key, access=cell.access, host_id=member.host_id,
        )
        config = dataclasses.replace(
            self._base, mode=ProviderMode.LIVE, model_id=cell.model_id, api_key=None, cell_settings=cell,
        )
        return ProviderBinding(adapter=member.adapter, config=config, call=call)
