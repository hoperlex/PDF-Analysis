"""The stage layout, the catalogue and the readiness of a start, as a service (`HOSTS-LAYOUT-01`, ADR-0028 decisions 8, 12-14).

``StagePlanService`` is what ``bootstrap/stage_plan_adapter.py`` delegates to. It holds, over ``stage_layout*`` (migration ``0062``) and
``contracts/analysis/v1/model-catalogue.json``:

* the **layout** and its revisions -- a pair of the catalogue per cell, the closed list of block schemes, the sets « Только Claude » and
  « Только Codex » (``runs/stage_layout.py`` holds the tables, this module only applies them). Only an administrator revises it; the role
  set is re-read in the command's own transaction. An expert reads it through the router; the viewer is closed by ``api/security.py``.
  A revision also holds the **comparison cells** (`HOSTS-CMP-01`): the model, effort, limit and timeout of the four kinds of comparison
  work that call a model. They are optional on a request -- a revision saved without them follows its set's table;
* the **switch** and its journal: on, runs started from now on freeze a ``stage_plan``; off, they follow the legacy route. It needs a
  revision and ``AUDITMANAGER_PROVIDER_SOURCE=database``, is read only when a run starts (``runs/stage_plan.py``), and every change is an
  append-only event with its author;
* the **catalogue** read of ``listModelCatalogue``;
* the **readiness** the one button shows (``getRunStartReadiness``): what a start would freeze, the access of each cell, the cells no
  server can serve and the digest of the estimate to confirm.

The adapter parses nothing and decides nothing. Nothing here calls a model; no answer of a model chooses a model or an effort.
"""

from __future__ import annotations

import os
from typing import Any, Final, Iterable, Mapping

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import CellSettings, FORBIDDEN_EFFORTS, ModelCatalogue, model_catalogue
from auditmanager.ingest.public import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.jobs.public import append_execution_event
from auditmanager.runs.public import (
    KIT_CUSTOM, LayoutRevisionRow, ModelAvailabilityPort, PROVIDER_SOURCE_DATABASE, SqlStageLayoutStore, StageLayoutStore,
    StagePlanFreezer, SwitchEventRow, cells_to_wire, comparison_cells_to_wire, no_layout_revision, provider_source_not_database,
    require_valid_comparison_cells, require_valid_layout, start_readiness,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey

__all__ = ["COMMAND_TYPE_REVISE", "COMMAND_TYPE_SWITCH", "DEPENDENCY", "StagePlanService"]

DEPENDENCY: Final[str] = "stage_models"
COMMAND_TYPE_REVISE: Final[str] = "revise_stage_layout"
COMMAND_TYPE_SWITCH: Final[str] = "set_stage_layout_enabled"
_HISTORY_LIMIT: Final[int] = 50


def _admin(roles: Iterable[str]) -> None:
    if "admin" not in set(roles):
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")


def _roles(session: Session, user_uid: str) -> frozenset[str]:
    from auditmanager.access.public import AccountRepository

    return AccountRepository().roles_of(session, user_uid)


def _value(member: Any) -> Any:
    return getattr(member, "value", member)


def _revision_view(row: LayoutRevisionRow) -> dict[str, Any]:
    view: dict[str, Any] = {
        "layout_revision_id": row.layout_revision_id, "revision_no": row.revision_no, "kit": row.kit,
        "cells": cells_to_wire(row.cells), "created_at": row.created_at, "created_by": row.created_by,
    }
    comparison = row.comparison_cells_in_force
    if comparison is not None:  # « Свой набор » that stored none has none: the key is absent, not an empty list
        view["comparison_cells"] = comparison_cells_to_wire(comparison)
    return view


def _event_view(row: SwitchEventRow) -> dict[str, Any]:
    return {"enabled": row.enabled, "set_at": row.set_at, "set_by": row.set_by}


def _cells_of(body: Any) -> tuple[CellSettings, ...]:
    """The cells of a request as the domain reads them. A cell whose key is not its row and role is refused here: the wire carries the
    three and they must agree."""
    cells = []
    for item in body.cells:
        key, row, role = str(item.cell_key), str(_value(item.row)), str(_value(item.role))
        if key != f"{row}:{role}":
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="cells", constraint="cell_key_mismatch")
        cells.append(CellSettings(
            cell_key=key, model_id=str(item.model_id), effort=str(_value(item.effort)),
            max_output_tokens=int(item.max_output_tokens), timeout_seconds=int(item.timeout_seconds),
        ))
    return tuple(cells)


def _comparison_cells_of(body: Any) -> tuple[CellSettings, ...] | None:
    """The comparison cells of a request, or ``None`` when it carries none (the revision then follows its set's table). The cell's key is
    the kind and ``main``: the wire names the kind, never a key."""
    items = getattr(body, "comparison_cells", None)
    if items is None:
        return None
    return tuple(
        CellSettings(
            cell_key=f"{_value(item.work_kind)}:main", model_id=str(item.model_id), effort=str(_value(item.effort)),
            max_output_tokens=int(item.max_output_tokens), timeout_seconds=int(item.timeout_seconds),
        )
        for item in items
    )


class StagePlanService:
    def __init__(
        self, *, session_factory: sessionmaker[Session], store: StageLayoutStore | None = None,
        availability: ModelAvailabilityPort | None = None, provider_source: str | None = None,
        cost_preflight: Any = None, catalogue: ModelCatalogue | None = None, commands: CommandRepository | None = None,
    ) -> None:
        self._sessions = session_factory
        self._store: StageLayoutStore = store or SqlStageLayoutStore()
        self._catalogue = catalogue
        self._commands = commands or CommandRepository()
        self._provider_source = (
            provider_source if provider_source is not None
            else os.environ.get("AUDITMANAGER_PROVIDER_SOURCE", "environment").strip() or "environment"
        )
        self._cost_preflight = cost_preflight
        self._availability = availability
        #: The seam the start commands call; the integrator hands this same object to ``start_audit_run``, ``reaudit_run`` and
        #: ``start_run_from_stage`` (``stage_plans=service.freezer``) and to ``RunCostPreflight``.
        self.freezer = StagePlanFreezer(store=self._store, availability=availability, provider_source=self._provider_source)

    def attach_cost_preflight(self, cost_preflight: Any) -> None:
        """`HOSTS-INT-WIRE-01`: the cost preflight is built by the run adapter, which needs ``freezer`` first -- so the root hands the service its
        preflight once, after the adapter exists. A second, different object is refused: the readiness a user reads and the estimate a start
        binds must be one policy."""
        if self._cost_preflight is not None and self._cost_preflight is not cost_preflight:
            raise ValueError("the stage plan service already holds a cost preflight")
        self._cost_preflight = cost_preflight

    # -- reads -----------------------------------------------------------------------------------------------------------------

    def get_layout(self) -> dict[str, Any]:
        with self._sessions() as session:
            return self._layout(session)

    def _layout(self, session: Session) -> dict[str, Any]:
        history = list(self._store.history(session, limit=_HISTORY_LIMIT))
        result: dict[str, Any] = {
            "enabled": self._store.enabled(session),
            "history": [_revision_view(row) for row in history],
            "switch_journal": [_event_view(row) for row in self._store.switch_journal(session, limit=_HISTORY_LIMIT)],
            "unavailable_cell_keys": [],
        }
        if history:
            result["current"] = _revision_view(history[0])
            draft = self.freezer.draft_of(session, history[0])
            result["unavailable_cell_keys"] = [cell.cell_key for cell in draft.unavailable({cell.row for cell in draft.cells})]
            comparison = history[0].comparison_cells_in_force
            if comparison:
                # The comparison cells are served by the same system groups: a model no server serves is « нет на серверах » there too.
                served = self._availability.availability(session, tuple(dict.fromkeys(cell.model_id for cell in comparison)))
                result["unavailable_cell_keys"] += [
                    cell.cell_key for cell in comparison if cell.model_id not in served or served[cell.model_id].access is None]
        return result

    def list_catalogue(self) -> dict[str, Any]:
        catalogue = self._catalogue or model_catalogue()
        return {
            "contract_version": catalogue.contract_version,
            "items": [
                {"provider": entry.provider, "model_id": entry.model_id, "access": list(entry.access),
                 "efforts": [effort for effort in entry.efforts if effort not in FORBIDDEN_EFFORTS],
                 "accepted_reported": list(entry.accepted_reported)}
                for entry in catalogue.entries
            ],
        }

    # -- writes ----------------------------------------------------------------------------------------------------------------

    def revise_layout(self, *, body: Any, user_uid: str, idempotency_key: str) -> dict[str, Any]:
        """A new immutable revision. Refusals precede the key's claim and write nothing: ``permission_denied``, then
        ``validation_failed`` (a cell outside the catalogue, a block scheme not on the list, a set named for cells that are not its)."""
        kit = str(_value(body.kit))
        cells = _cells_of(body)
        comparison = _comparison_cells_of(body)
        with self._sessions() as session:
            _admin(_roles(session, user_uid))
            ordered = require_valid_layout(kit, cells, catalogue=self._catalogue)
            ordered_comparison = (
                None if comparison is None else require_valid_comparison_cells(kit, comparison, catalogue=self._catalogue))
            # The list is part of the request only when it was sent: a request without it keeps the fingerprint it always had.
            sent = {} if ordered_comparison is None else {"comparison_cells": comparison_cells_to_wire(ordered_comparison)}
            claimed = self._commands.begin(
                session, command_type=COMMAND_TYPE_REVISE, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"actor_uid": user_uid, "kit": kit, "cells": cells_to_wire(ordered), **sent}),
            )
            if isinstance(claimed, CommandReplay):
                return self._layout(session)
            assert isinstance(claimed, CommandStarted)
            self._store.lock(session)
            row = self._store.append_revision(
                session, kit=kit, cells=ordered, created_by=user_uid,
                **({} if ordered_comparison is None else {"comparison_cells": ordered_comparison}))
            append_execution_event(
                session, event_type="stage_layout.revised", aggregate_type="StageLayoutRevision",
                aggregate_id=row.layout_revision_id,
                payload={"revision_id": row.layout_revision_id, "revision_no": row.revision_no, "actor_uid": user_uid,
                         "state": "custom" if kit == KIT_CUSTOM else kit},
            )
            self._commands.succeed(session, claimed.command_id, {"layout_revision_id": row.layout_revision_id})
            view = self._layout(session)
            session.commit()
            return view

    def set_layout_enabled(self, *, enabled: bool, user_uid: str, idempotency_key: str) -> dict[str, Any]:
        """Put the layout in force for runs started from now on, or take it out. Switching on needs a revision and the database provider
        source (``409 conflict``: ``no_layout_revision``, ``provider_source_not_database``); switching off needs nothing and breaks no run in
        progress, which froze its plan. A request for the state already in force records nothing."""
        with self._sessions() as session:
            _admin(_roles(session, user_uid))
            claimed = self._commands.begin(
                session, command_type=COMMAND_TYPE_SWITCH, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"actor_uid": user_uid, "enabled": enabled}),
            )
            if isinstance(claimed, CommandReplay):
                return self._layout(session)
            assert isinstance(claimed, CommandStarted)
            self._store.lock(session)
            if enabled:
                if self._provider_source != PROVIDER_SOURCE_DATABASE:
                    raise provider_source_not_database()
                if self._store.current_revision(session) is None:
                    raise no_layout_revision()
            if self._store.enabled(session) != enabled:
                self._store.append_switch(session, enabled=enabled, set_by=user_uid)
                # The journal names an aggregate by an identity (``ck_audit_event_aggregate_id``): the switch concerns the layout revision in
                # force. (`HOSTS-INT-WIRE-01`: the literal ``default`` this line used to carry is no identity and the database refused every
                # change of the switch.) A switch that is on has a revision, and one that goes off was on.
                revision = self._store.current_revision(session)
                assert revision is not None
                append_execution_event(
                    session, event_type="stage_layout.switched", aggregate_type="StageLayoutRevision",
                    aggregate_id=revision.layout_revision_id,
                    payload={"actor_uid": user_uid, "state": "on" if enabled else "off"},
                )
            self._commands.succeed(session, claimed.command_id, {"enabled": enabled})
            view = self._layout(session)
            session.commit()
            return view

    # -- the one button --------------------------------------------------------------------------------------------------------

    def get_start_readiness(self, *, body: Any) -> dict[str, Any]:
        """``getRunStartReadiness``: the route, the access of each cell, the cells no server serves, the digest to confirm and the total.
        Reads the layout and the availability and prices the plan; writes nothing and calls no model."""
        if self._cost_preflight is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
        request = {name: getattr(body, name, None) for name in (
            "reaudit_of_run_id", "executor_connection_id", "preset_id", "executor_group_id", "start_from_run_id", "start_stage_id")}
        with self._sessions() as session:
            return start_readiness(
                self._cost_preflight, session, self.freezer(session), version_uid=str(body.version_uid),
                relaxed_limits=bool(getattr(body, "relaxed_limits", None)), **request)
