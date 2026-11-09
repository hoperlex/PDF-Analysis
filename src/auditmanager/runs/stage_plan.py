"""From a stored layout to the plan a run freezes at its start (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 8, 14).

Three things live here, none of which touches a model:

* the **availability port** (:class:`ModelAvailabilityPort`): what the stand knows of whether a model can be served *now*, and how. The
  ``executors`` context (``HOSTS-BACKEND-01``) implements it over the host facts; this module sees only the typed answer, and a model
  the answer does not mention is *not on any server* (an explicit reason, never a guess that it is available);
* the **draft** (:class:`StagePlanDraft`): the layout revision read inside the start's transaction together with the availability of
  its models. It becomes a :class:`~auditmanager.runs.stage_layout.FrozenStagePlan` once the rows the run will call are known
  (:meth:`StagePlanDraft.freeze`): the access of each model is chosen **then** -- a subscription when a subscription server can serve it
  now, otherwise an API key -- and never again;
* the **freezer** (:class:`StagePlanFreezer`): the seam the three start commands call. It answers ``None`` while the layout is off (the
  legacy route, exactly as before) and refuses -- typed, never by falling back -- while it is on but cannot serve a run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Final, Iterable, Mapping, Protocol, Sequence

from sqlalchemy.orm import Session

from auditmanager.analysis.public import CellSettings
from auditmanager.runs.stage_layout import FrozenStagePlan
from auditmanager.runs.stage_layout_store import LayoutRevisionRow, StageLayoutStore
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AVAILABILITY_DEPENDENCY", "call_journal_columns", "cell_binding", "model_of", "settings_of", "ModelAvailability", "ModelAvailabilityPort", "NOT_ON_ANY_SERVER", "PROVIDER_SOURCE_DATABASE",
    "StagePlanDraft", "StagePlanFreezer", "StagePlanSource", "provider_source_not_database", "no_layout_revision",
]

#: The provider source the layout needs: a run is bound to a member of a system group, and only the ``database`` source binds.
PROVIDER_SOURCE_DATABASE: Final[str] = "database"
#: A model the availability answer does not name: no server serves it (``ModelUnavailableReason.not_on_any_server``).
NOT_ON_ANY_SERVER: Final[str] = "not_on_any_server"
AVAILABILITY_DEPENDENCY: Final[str] = "stage_model_availability"


@dataclass(frozen=True, slots=True)
class ModelAvailability:
    """Whether a model can be served now, by which kind of access, and -- when it cannot -- why (``ModelUnavailableReason`` values)."""

    subscription: bool = False
    api: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def access(self) -> str | None:
        """The access a run started now would use: a subscription when one can serve the model, otherwise an API key, else none."""
        return "subscription" if self.subscription else "api" if self.api else None


class ModelAvailabilityPort(Protocol):
    """Answered by the executors context. ``model_ids`` are catalogue model ids; the answer is read, never written, and a model the
    mapping leaves out is read as not served."""

    def availability(self, session: Session, model_ids: Sequence[str]) -> Mapping[str, ModelAvailability]: ...


def provider_source_not_database() -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message="the stage layout needs the database provider source",
                       conflict_reason="provider_source_not_database")


def no_layout_revision() -> DomainError:
    return DomainError(ErrorCode.CONFLICT, message="the stage layout has no revision yet", conflict_reason="no_layout_revision")


@dataclass(frozen=True, slots=True)
class StagePlanDraft:
    """The layout in force and what can serve it now, read in the start's own transaction. Not yet a plan: the access of a model is
    fixed by :meth:`freeze`, for the rows the run will call."""

    layout_revision_id: str
    kit: str
    cells: tuple[CellSettings, ...]
    availability: Mapping[str, ModelAvailability]

    def availability_of(self, model_id: str) -> ModelAvailability:
        return self.availability.get(model_id) or ModelAvailability(reasons=(NOT_ON_ANY_SERVER,))

    def cells_of(self, rows: Iterable[str]) -> tuple[CellSettings, ...]:
        wanted = set(rows)
        return tuple(cell for cell in self.cells if cell.row in wanted)

    def unavailable(self, rows: Iterable[str]) -> tuple[CellSettings, ...]:
        """The cells of ``rows`` whose model no server can serve now."""
        return tuple(cell for cell in self.cells_of(rows) if self.availability_of(cell.model_id).access is None)

    def freeze(self, rows: Iterable[str]) -> FrozenStagePlan:
        """The plan of the cells of ``rows``, each with the access of its model. A model nothing can serve refuses the start: no cell is
        dropped, no other model is substituted (``AGENTS.md`` section 4)."""
        missing = self.unavailable(rows)
        if missing:
            raise DomainError(
                ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=AVAILABILITY_DEPENDENCY,
                message="no server serves the model of: " + ", ".join(cell.cell_key for cell in missing),
            )
        return FrozenStagePlan(
            self.layout_revision_id, self.kit,
            tuple(replace(cell, access=self.availability_of(cell.model_id).access) for cell in self.cells_of(rows)),
        )


#: What the three start commands call: ``None`` while the layout is off, else the draft of this transaction.
StagePlanSource = Callable[[Session], "StagePlanDraft | None"]


class StagePlanFreezer:
    """The layout as the start commands read it: ``freezer(session)`` is ``None`` while the switch is off and the draft while it is on.

    The switch is read **here and only here**, when a run starts (ADR-0028 decision 14): switching it off breaks no run in progress,
    which froze its plan. With the layout on, a provider source other than ``database`` and a layout with no revision are refused, and the
    models are asked of the availability port. ``provider_source`` is what the process was started with
    (``AUDITMANAGER_PROVIDER_SOURCE``); it is a parameter, not a read of the environment, so a test needs no patching.
    """

    def __init__(self, *, store: StageLayoutStore, availability: ModelAvailabilityPort | None, provider_source: str) -> None:
        self._store = store
        self._availability = availability
        self._provider_source = provider_source

    def __call__(self, session: Session) -> StagePlanDraft | None:
        if not self._store.enabled(session):
            return None
        return self.draft(session)

    def draft(self, session: Session) -> StagePlanDraft:
        """The draft of the revision in force, whether or not the switch is on (the readiness read of an administrator who has not yet
        switched shows what a start would do)."""
        if self._provider_source != PROVIDER_SOURCE_DATABASE:
            raise provider_source_not_database()
        revision = self._store.current_revision(session)
        if revision is None:
            raise no_layout_revision()
        return self.draft_of(session, revision)

    def draft_of(self, session: Session, revision: LayoutRevisionRow) -> StagePlanDraft:
        if self._availability is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=AVAILABILITY_DEPENDENCY)
        models = tuple(dict.fromkeys(cell.model_id for cell in revision.cells))
        return StagePlanDraft(
            revision.layout_revision_id, revision.kit, revision.cells, dict(self._availability.availability(session, models)),
        )


# --- the binding of a call ------------------------------------------------------------------------------------------------------

#: The approvals of the run's consent, which a cell's binding carries from the run-level configuration: the ceiling, the window and
#: call limits, the models the consent v2 approved and the digest of the plan. A cell's own configuration names the cell's model.
_RUN_APPROVALS: Final[tuple[str, ...]] = (
    "run_cost_ceiling_usd", "approved_window_characters", "approved_max_windows", "approved_cost_ceiling", "approved_model_id",
    "approved_rate_sha256", "approved_native_page_pieces", "approved_models", "approved_stage_plan_digest",
)


def _refuse_cell(reason: str) -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason=reason)


def cell_binding(binding: Any, cell_key: str) -> Any:
    """The binding a call of the cell ``cell_key`` runs with (ADR-0028 decision 6, ``binding_for(cell)``).

    A run that is not frozen with a stage plan has no cells: its one binding serves every call, exactly as before. For a planned run the
    cell's own binding is resolved -- the adapter of the member the cell was bound to, the cell's model and settings, one ``CallBinding``
    that holds the reply to the cell's model -- and carries the run's consent approvals. **A cell that comes back without a call binding,
    or with one that is not the cell's, is refused** (`R-133`): a call is never made unbound, and never on another cell's model.
    """
    cells = getattr(binding, "cells", None)
    if cells is None:
        return binding
    resolved = cells(cell_key)
    call = getattr(resolved, "call", None)
    if (call is None or getattr(call, "cell_key", None) != cell_key or not call.check_identity or not call.expected_model
            or getattr(resolved.config, "cell_settings", None) is None):
        raise _refuse_cell("cell_call_binding_missing")
    approvals = {name: getattr(binding.config, name) for name in _RUN_APPROVALS}
    return replace(resolved, config=replace(resolved.config, **approvals), cells=None)


def model_of(binding: Any) -> str:
    """The model id a request of this binding is built for."""
    return binding.config.model_id


def settings_of(binding: Any) -> Any:
    """The cell settings of this binding (``None`` outside a planned run: the builders then keep their constants)."""
    return getattr(binding.config, "cell_settings", None)


def call_journal_columns(call: Any) -> dict[str, Any]:
    """The keywords ``prepare_provider_call`` takes for a planned call: the layout row (``stage_key``), the serving host and the access.
    Empty for every other call, which is then written exactly as before (``NULL`` in all three columns)."""
    if call is None or getattr(call, "cell_key", None) is None:
        return {}
    return {"stage_key": call.stage_key, "host_id": call.host_id, "access": call.access}
