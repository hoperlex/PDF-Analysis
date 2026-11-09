"""How a run gets its model adapter when the provider source is the database (`EXEC-HTTP-01`).

Two moments, each a small callable the composition root supplies and ``runs`` only calls:

* **freeze** (:data:`RouteFreezer`) -- at run start, in the transaction that creates the run:
  resolve the ``text_analysis`` route to a connection revision and return it as a
  :class:`FrozenRoute`. The revision is written to the run row, which freezes it; the input budget
  follows that revision's pinned model; a standby chosen instead of the primary is journaled.
  A refusal is raised here, before any row exists. With ``connection_id`` the freezer freezes
  *that* connection's current revision instead (`EXEC-PAR-START-01`) and reads neither the route
  nor the standby; a connection it cannot use is a refusal, never another connection.
* **bind** (:data:`ProviderResolver`) -- at each Attempt, just before the model stage: build the
  adapter of the run's frozen revision with the connection's *current* key, and say how the call
  must be recorded and held to its model (:class:`ProviderBinding`).

* **admit** (:data:`GroupAdmitter`, `EXEC2-GROUP-RUN-01`) -- at run start, for a start that names an executor
  group or that the routing rules route: read the group revision in the start's transaction and return what
  admission freezes (:class:`AdmittedGroup`). **No connection is chosen here**: the run is written
  ``binding_state = 'pending'`` and the claim binds a member, once, at dispatch (ADR-0026 decisions 12 to 14).

The ``environment`` source needs neither: its adapter is built once at start-up and passed to
``execute_run`` as before, and it has no admitter, so it refuses a group and never serves a pending run. ``runs`` imports nothing from ``executors``; the composition root
(``bootstrap/providers.py``) is where the two meet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.orm import Session

from auditmanager.jobs.public import AttemptContext

__all__ = [
    "AdmittedGroup", "ChosenPreset", "FrozenRoute", "GroupAdmitter", "PresetResolver", "ProviderBinding",
    "ProviderResolver", "RouteFreezer",
]


@dataclass(frozen=True, slots=True)
class FrozenRoute:
    """The connection revision a run starts on, and the budget that follows its model."""

    revision_id: str
    input_budget_characters: int
    #: Pinned model of this revision, used for stable raised-limit window sizing.
    model_id: str | None = None
    #: Set when the standby served instead of the primary: the two connections and why.
    primary_connection_id: str | None = None
    standby_connection_id: str | None = None
    standby_reason: str | None = None
    #: `EXEC-PAR-START-01`. Set (to the connection's id) exactly when the freezer was asked for a
    #: named connection; ``None`` when the route chose. The caller journals the choice from it.
    chosen_connection_id: str | None = None
    billing: str = "metered"


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    """What one Attempt calls: the adapter, the configuration it runs under (``model_id`` is the
    pin id) and the :class:`~auditmanager.analysis.text.binding.CallBinding` the stage reads."""

    adapter: Any
    config: Any
    call: Any = None
    #: `HOSTS-LAYOUT-01` (ADR-0028 decision 6). Set only for a run frozen with a stage plan: ``cells(cell_key)`` answers the
    #: :class:`ProviderBinding` of that cell -- the adapter of the member the cell was bound to, the cell's model and settings, and the
    #: ``CallBinding`` that holds the reply to the cell's model. The binding itself is then the plan's **text** cell, so the text stage
    #: runs on it unchanged; every other phase asks ``runs.stage_plan.cell_binding`` for its row's cell. ``None`` for every other run.
    cells: Any = None


class RouteFreezer(Protocol):
    """``freeze(session)`` follows the route; ``freeze(session, connection_id=...)`` freezes the
    named connection (`EXEC-PAR-START-01`). A freezer is called without the keyword when no
    connection was named, so one that predates the keyword is called exactly as before."""

    def __call__(self, session: Session, *, connection_id: str | None = None) -> FrozenRoute: ...


@dataclass(frozen=True, slots=True)
class ChosenPreset:
    """What a run start applies from a named preset (`ANALYSIS-PRESETS-01`): the preset's current
    revision, resolved in the start's own transaction, and the one setting a start can take."""

    preset_id: str
    revision_id: str
    revision_no: int
    executor_connection_id: str


class PresetResolver(Protocol):
    """``resolve(session, preset_id)`` is the preset's current revision, or the refusal that stops
    the start before anything is written (an unknown preset, an archived one). The ``runs`` context
    never reads the preset's tables: the composition root hands it this seam, as it hands it the
    route freezer."""

    def __call__(self, session: Session, preset_id: str) -> ChosenPreset: ...


@dataclass(frozen=True, slots=True)
class AdmittedGroup:
    """What admission freezes of a group (`EXEC2-GROUP-RUN-01`, ADR-0026 decision 13): the group and its immutable
    revision, the rule revision when a rule routed the start (``None`` when the group was named), and the planned
    model with its billing and the input budget that follows its pin. **Not a connection**: a member is chosen at
    dispatch, and every member of a homogeneous group serves this pin, model and billing.

    ``billing`` is spelled as the cost estimate spells it (``metered`` or ``unmetered``)."""

    group_id: str
    group_revision_id: str
    pin_id: str
    gateway_model: str
    billing: str
    input_budget_characters: int
    rule_revision_id: str | None = None


class GroupAdmitter(Protocol):
    """``admit(session, group_id=...)`` admits a start on the current revision of the named group; without a
    ``group_id`` it follows the routing rules: ``None`` while the mode is ``legacy`` (the start is what it always was),
    the rule of ``text_analysis`` while the mode is ``rules``.

    Refusals are typed and precede the idempotency key's claim, so nothing is written: ``validation_failed`` on
    ``executor_group_id`` for an unknown group, ``conflict`` (``group_archived``) for an archived one and
    ``dependency_unavailable`` (``no_rule_for_work_kind``) for a work kind with no rule. ``group_of`` is the group a
    group revision belongs to, for a repeat of a start that named a group. The ``runs`` context never reads the
    group tables: the composition root hands it this seam, as it hands it the route freezer."""

    def __call__(self, session: Session, *, group_id: str | None = None) -> AdmittedGroup | None: ...

    def group_of(self, session: Session, group_revision_id: str) -> str | None: ...


ProviderResolver = Callable[[Session, Any, AttemptContext], ProviderBinding]
