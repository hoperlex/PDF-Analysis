"""The facts of a run's stages: plan and fact, read from three places (`RUN-STAGES-01`, contract 1.46.0, ADR-0028).

``getRunStages`` (`HOSTS-SEAL-2`) answers the window «Этапы анализа раздела»: for each *chip* the run has, in the order the rail draws
them, what the chip was planned to run on and what happened. A chip is a reader's name for the phase or phases of code that do one
kind of work; ``web/src/entities/audit-run/model/stage-dictionary.ts`` is the application's one dictionary of them, and :data:`CHIPS`
below is its server-side mirror (a unit test holds the two to the same ids and order).

The facts come from three places and from nowhere else:

* ``stage_result`` -- the PC-01 stages (the three preparation stages and ``text_analysis``) and, where the run wrote them, the other
  stage ids; the state of a chip and the times of a chip that calls no model;
* the extended review artifact, read through :func:`~auditmanager.runs.extended_review.read_extended_review` (its custody-checked reader):
  the ``procedures`` -- the state of the chips the stage results say nothing about -- and the ``phase_coverage`` batches planned and done;
* the call journal, ``model_call`` and ``provider_call_effect``: calls, tokens, cost, the times of a chip that calls a model, the last
  error. A call is placed on its chip by ``stage_key`` (written since migration ``0062``) or, for an older row that has none, **derived at
  read time** from ``parameters ->> 'extended_phase'`` by the map below; a row with neither is a call of the text stage. A row whose
  phase or key the map does not know is a typed ``storage_integrity_error``, never a guess (AGENTS section 4).

The plan is the run's frozen ``audit_run.stage_plan`` (one cell per row and role) with the server each cell was bound to
(``audit_run_cell_binding``, the host's display name). A run that froze none has, for each chip that calls a model, one line «модель прогона»
from its binding (``audit_run.connection_revision_id``) or, with no binding, from the journal.

**The viewer** («Наблюдатель», ``R-150w``) reads the stages but not the server nor the access: with ``include_server`` false the cells
carry neither key at all (absent, not null). The adapter decides the flag from the caller's role set and fails closed.

The module reads and decides nothing else: it writes nothing, calls no model and holds no state. :func:`assemble_run_stage_facts` is
pure over its inputs and is what the unit tests drive; :func:`read_run_stage_facts` is the database reads around it.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CHIPS",
    "CallRow",
    "CellBinding",
    "RunBinding",
    "RunRow",
    "StageRow",
    "assemble_run_stage_facts",
    "chip_of_call",
    "chip_of_phase",
    "read_run_stage_facts",
]


@dataclass(frozen=True, slots=True)
class Chip:
    """One chip: its id, the code stage and procedure ids it covers, and whether its work calls a model.

    ``row`` is the row of the stage layout whose cells are the chip's plan (``None`` for a chip with no row of its own: the AR v3 stage
    runs outside the layout)."""

    id: str
    stage_ids: tuple[str, ...]
    calls_model: bool
    row: str | None = None


#: The chips in the order the rail draws them (a display order, not the stage graph). ``comprehensive_analysis`` is not a contract stage id
#: but the extended review's procedure of that name, and it is the whole of the «Сверка» chip.
CHIPS: Final[tuple[Chip, ...]] = (
    Chip("preparation", ("source_preparation", "page_geometry_extraction", "document_context_build"), False),
    Chip("text", ("text_analysis",), True, "text"),
    Chip("blocks", ("block_analysis",), True, "blocks"),
    Chip("cross_check", ("comprehensive_analysis",), True, "cross_check"),
    Chip("merge", ("finding_merge",), False),
    Chip("norms", ("norm_verification",), True, "norms"),
    Chip("review", ("finding_review",), True, "review"),
    Chip("correction", ("finding_correction",), True, "correction"),
    Chip("ar_v3", ("ar_v3_citation_review",), True),
)

_CHIP_BY_ID: Final[Mapping[str, Chip]] = {chip.id: chip for chip in CHIPS}
_CHIP_OF_ROW: Final[Mapping[str, str]] = {chip.row: chip.id for chip in CHIPS if chip.row is not None}

#: The first word of an extended phase -> the chip whose call it is. The phases the code writes today are ``blocks:N`` and ``merge`` (the
#: first extended review), ``v2:<identity>`` and ``v3:<window>:<identity>`` (the batched reviews: ``blocks:bNNN``, ``comprehensive:N``,
#: ``comprehensive_analysis:bNNN``, ``norm_verification[:N|:bNNN]``, ``critic``, ``finding_review:bNNN``, ``corrector``,
#: ``finding_correction:bNNN``, each with an optional ``:repair:1``), ``v3:global-cross-window:<identity>`` and
#: ``v3:project-parameters:bNNN`` (the parameter passport belongs to the cross-check). An ensemble identity such as ``blocks:N:leg1``
#: starts with the same word.
_KIND_CHIP: Final[Mapping[str, str]] = {
    "blocks": "blocks",
    "block_analysis": "blocks",
    "comprehensive": "cross_check",
    "comprehensive_analysis": "cross_check",
    "project-parameters": "cross_check",
    "norm_verification": "norms",
    "critic": "review",
    "finding_review": "review",
    "corrector": "correction",
    "finding_correction": "correction",
    "merge": "merge",
}

#: The ``phase_coverage`` key of each chip that keeps batches (the extended review's ``kind``).
_COVERAGE_KIND: Final[Mapping[str, str]] = {
    "blocks": "block_analysis",
    "cross_check": "comprehensive_analysis",
    "norms": "norm_verification",
    "review": "finding_review",
    "correction": "finding_correction",
}

_WINDOW: Final = re.compile(r"w[0-9]{3}\Z")
_CODE: Final = re.compile(r"[a-z][a-z0-9_]{2,63}\Z")
_REASON: Final = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_CELL_KEY: Final = re.compile(r"([a-z][a-z0-9_]{0,63}):(main|leg1|leg2|judge)\Z")
_ROLE_ORDER: Final[Mapping[str, int]] = {"main": 0, "leg1": 1, "leg2": 2, "judge": 3}
_EFFORTS: Final = frozenset({"low", "medium", "high"})
_ACCESSES: Final = frozenset({"subscription", "api"})

#: ``stage_result.metrics`` key a reused row carries (``runs.stage_reuse.REUSED_FROM_METRIC``; a unit test holds the two equal).
_REUSED_FROM_METRIC: Final[str] = "reused_from_run_id"

#: Sorts a failed call that has no time before every call that has one.
_EPOCH: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)

_TERMINAL_RUN_STATES: Final = frozenset({"published", "partial", "failed", "cancelled"})
_FINISHED_STATES: Final = frozenset({"done", "partial", "failed", "skipped", "unavailable"})

#: ``provider_call_effect.state`` -> how the call ended. A call with a ``model_call`` row is read from that row's status instead.
_EFFECT_OUTCOME: Final[Mapping[str, str]] = {
    "completed": "succeeded",
    "prepared": "in_flight",
    "response_received": "in_flight",
    "outcome_unknown": "failed",
    "not_processed": "failed",
    "abandoned": "failed",
}
_CALL_OUTCOME: Final[Mapping[str, str]] = {"succeeded": "succeeded", "truncated": "succeeded", "failed": "failed"}


def _integrity(role: str) -> DomainError:
    return DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role=role)


# --- inputs ---------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunRow:
    """The run: its state, the plan it froze (or ``None``) and, for a run without a plan, the executor its binding names."""

    run_id: str
    state: str
    stage_plan: Mapping[str, Any] | None
    binding: "RunBinding | None"


@dataclass(frozen=True, slots=True)
class RunBinding:
    """What a run without a stage plan was bound to: the connection's display name, the model its revision pins and how it is paid."""

    server: str
    model_id: str
    access: str | None


@dataclass(frozen=True, slots=True)
class CellBinding:
    """The member a cell of a planned run was bound to: the host's display name (the connection's, for a connection with no host) and
    how the member's connection is paid."""

    server: str
    access: str | None


@dataclass(frozen=True, slots=True)
class StageRow:
    """One ``stage_result``: ``status`` is the stage vocabulary (``succeeded``, ``partial``, ``failed``, ``skipped``)."""

    stage_id: str
    status: str
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    reused_from_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class CallRow:
    """One call of the journal, placed on its chip. ``outcome`` is ``succeeded``, ``failed`` or ``in_flight``.

    ``request_key`` is what two attempts of the same request share (the request digest and the model); ``subscription`` says the call
    ran on a subscription (``access`` ``subscription``, or no ``access`` and an unmetered cost basis: a row written before ``0062``)."""

    call_id: str
    chip: str
    outcome: str
    request_key: tuple[str, str]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_micros: int | None = None
    subscription: bool = False
    error_code: str | None = None
    model_id: str | None = None


# --- the map from a journal row to a chip ---------------------------------------------------------------------------------


def chip_of_phase(phase: str) -> str | None:
    """The chip of an ``extended_phase`` string, or ``None`` for a phase the map does not know.

    The version prefix (``v2`` or ``v3``) and, after ``v3``, a window (``w001``) or ``global-cross-window`` are stripped; the next
    word names the work. Nothing is matched by prefix or by guess: an unknown word is ``None`` and the caller refuses."""
    tokens = phase.split(":")
    if tokens and tokens[0] in ("v2", "v3"):
        tokens = tokens[1:]
        if tokens and (tokens[0] == "global-cross-window" or _WINDOW.fullmatch(tokens[0])):
            tokens = tokens[1:]
    return _KIND_CHIP.get(tokens[0]) if tokens else None


def chip_of_call(stage_key: str | None, parameters: Mapping[str, Any] | None) -> str:
    """The chip a journal row belongs to.

    In order: the ``stage_key`` the row carries (since ``0062``: a row of the stage layout, which is a chip's id); else its extended
    phase; else an AR v3 candidate (the run's one call of the AR v3 profile); else the text stage, whose windows are the only calls with
    no phase. A key or a phase the map does not know is ``storage_integrity_error``."""
    if stage_key is not None:
        chip = _CHIP_OF_ROW.get(stage_key)
        if chip is None:
            raise _integrity("model_call.stage_key")
        return chip
    parameters = parameters or {}
    phase = parameters.get("extended_phase")
    if phase is not None:
        chip = chip_of_phase(phase) if isinstance(phase, str) else None
        if chip is None:
            raise _integrity("model_call.extended_phase")
        return chip
    if "ar_v3_candidate_sha256" in parameters:
        return "ar_v3"
    return "text"


# --- the pure assembly ---------------------------------------------------------------------------------------------------


def _non_negative(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _procedures(review: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """The extended review's procedures that carry an id and a status, in the artifact's order. A member that is not an object, or
    has no string id and status, is not a procedure (the artifact's own reader is what proved the envelope)."""
    result = (review or {}).get("result")
    procedures = result.get("procedures") if isinstance(result, Mapping) else None
    if not isinstance(procedures, list):
        return []
    return [
        item for item in procedures
        if isinstance(item, Mapping) and isinstance(item.get("id"), str) and isinstance(item.get("status"), str)
    ]


def _coverage(review: Mapping[str, Any] | None) -> dict[str, tuple[int, int]]:
    """``chip -> (planned, completed)`` batches, summed over the review's windows and its cross-window phase. A chip the review keeps
    no coverage for is absent."""
    result = (review or {}).get("result")
    if not isinstance(result, Mapping):
        return {}
    sources: list[Mapping[str, Any]] = []
    for holder in (result, result.get("global_cross_window")):
        coverage = holder.get("phase_coverage") if isinstance(holder, Mapping) else None
        if isinstance(coverage, Mapping):
            sources.append(coverage)
    found: dict[str, tuple[int, int]] = {}
    for chip, kind in _COVERAGE_KIND.items():
        planned = completed = 0
        seen = False
        for coverage in sources:
            entry = coverage.get(kind)
            if not isinstance(entry, Mapping):
                continue
            entry_planned, entry_completed = _non_negative(entry.get("planned")), _non_negative(entry.get("completed"))
            if entry_planned is None or entry_completed is None:
                continue
            seen = True
            planned += entry_planned
            completed += entry_completed
        if seen:
            found[chip] = (planned, completed)
    return found


def _state_of_rows(rows: Sequence[StageRow], expected: int, run_open: bool) -> str | None:
    """The state the stage results give a chip, or ``None`` when they say nothing (a chip is then read from the procedures)."""
    if not rows:
        return None
    statuses = [row.status for row in rows]
    if "failed" in statuses:
        return "failed"
    if "partial" in statuses:
        return "partial"
    if len(rows) < expected:
        return "running" if run_open else "partial"
    return "skipped" if all(status == "skipped" for status in statuses) else "done"


def _state_of_procedures(statuses: Sequence[str]) -> str | None:
    if not statuses:
        return None
    if "failed" in statuses:
        return "failed"
    if any(status in ("running", "repairing") for status in statuses):
        return "running"
    if "partial" in statuses:
        return "partial"
    if all(status == "completed" for status in statuses):
        return "done"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    if all(status == "unavailable" for status in statuses):
        return "unavailable"
    if all(status == "queued" for status in statuses):
        return "pending"
    if all(status in ("completed", "skipped") for status in statuses):
        return "done"
    return "running" if "queued" in statuses else "partial"


def _plan_cells(stage_plan: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    """The frozen cells of a planned run, by chip, in the order of their roles. A malformed plan is ``storage_integrity_error``: the
    database checks the shape of the array and the cell key and model that binding reads, and nothing else about a cell. A plan frozen before
    `LIMITS-01` holds an answer limit and a timeout per cell; they are **not shown** (the contract's cell has neither)."""
    if stage_plan is None:
        return {}
    cells = stage_plan.get("cells") if isinstance(stage_plan, Mapping) else None
    if not isinstance(cells, list):
        raise _integrity("audit_run.stage_plan")
    by_chip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        key = cell.get("cell_key") if isinstance(cell, Mapping) else None
        matched = _CELL_KEY.fullmatch(key) if isinstance(key, str) else None
        if matched is None:
            raise _integrity("audit_run.stage_plan")
        row, role = matched.groups()
        chip = _CHIP_OF_ROW.get(row)
        if chip is None:
            continue  # a row that is not a stage of a run (a comparison row, later): not drawn here
        view: dict[str, Any] = {"cell_key": key, "role": role}
        for field, valid in (
            ("model_id", lambda v: isinstance(v, str) and 1 <= len(v) <= 200),
            ("effort", lambda v: v in _EFFORTS),
            ("access", lambda v: v in _ACCESSES),
        ):
            if field in cell:
                if not valid(cell[field]):
                    raise _integrity("audit_run.stage_plan")
                view[field] = cell[field]
        by_chip[chip].append(view)
    for chip in by_chip:
        by_chip[chip].sort(key=lambda view: _ROLE_ORDER[view["role"]])
    return by_chip


def _journal_model(calls: Sequence[CallRow]) -> str | None:
    """The one model the journal names for these calls, or ``None`` when it names none or several."""
    models = {call.model_id for call in calls if call.model_id}
    return next(iter(models)) if len(models) == 1 else None


def _cell_view(
    cell: Mapping[str, Any], *, binding: CellBinding | None, include_server: bool,
) -> dict[str, Any]:
    view = dict(cell)
    if not include_server:
        view.pop("access", None)
        return view
    if binding is not None:
        view["server"] = binding.server
        if "access" not in view and binding.access is not None:
            view["access"] = binding.access
    return view


def _legacy_cell(run: RunRow, calls: Sequence[CallRow], *, include_server: bool) -> dict[str, Any]:
    """The one line of a run that froze no stage plan: the model of its binding, else of its journal."""
    view: dict[str, Any] = {"role": "main"}
    model = run.binding.model_id if run.binding is not None else _journal_model(calls)
    if model is not None:
        view["model_id"] = model
    if include_server and run.binding is not None:
        view["server"] = run.binding.server
        if run.binding.access is not None:
            view["access"] = run.binding.access
    return view


def _facts(
    chip: Chip,
    *,
    rows: Sequence[StageRow],
    statuses: Sequence[str],
    procedures: Sequence[Mapping[str, Any]],
    calls: Sequence[CallRow],
    coverage: tuple[int, int] | None,
    run_open: bool,
) -> dict[str, Any]:
    in_flight = sum(call.outcome == "in_flight" for call in calls)
    state = _state_of_rows(rows, len(chip.stage_ids), run_open) or _state_of_procedures(statuses) or "pending"
    if state == "pending" and in_flight:
        state = "running"

    succeeded = sum(call.outcome == "succeeded" for call in calls)
    failed = sum(call.outcome == "failed" for call in calls)
    retried = sum(count - 1 for count in Counter(call.request_key for call in calls).values())
    facts: dict[str, Any] = {
        "state": state,
        "calls_succeeded": succeeded,
        "calls_failed": failed,
        "calls_retried": retried,
        "input_tokens": sum(call.input_tokens or 0 for call in calls),
        "output_tokens": sum(call.output_tokens or 0 for call in calls),
        "subscription_input_tokens": sum(call.input_tokens or 0 for call in calls if call.subscription),
        "subscription_output_tokens": sum(call.output_tokens or 0 for call in calls if call.subscription),
        "cost_micros": sum(call.cost_micros or 0 for call in calls),
    }

    # The times: a chip that calls a model is timed by its calls; otherwise (or before any call) by the stage results it computed.
    # A row taken from an earlier run carries that run's times, which are not this run's, so it is not timed -- it is named.
    computed = [row for row in rows if row.reused_from_run_id is None]
    started = [call.started_at for call in calls if call.started_at is not None]
    finished = [call.finished_at for call in calls if call.finished_at is not None]
    if not started:
        started = [row.started_at for row in computed if row.started_at is not None]
        finished = [row.finished_at for row in computed if row.finished_at is not None]
        all_finished = len(finished) == len(computed)
    else:
        all_finished = in_flight == 0
    if started:
        facts["started_at"] = min(started)
    if finished and all_finished and state in _FINISHED_STATES:
        facts["finished_at"] = max(finished)
    if rows and len(computed) == 0:
        facts["reused_from_run_id"] = sorted({row.reused_from_run_id for row in rows if row.reused_from_run_id})[0]

    # The last error: a stage that failed names its own code; otherwise the latest call that failed; otherwise the procedure's.
    error = next((row.error_code for row in rows if row.status in ("failed", "partial") and row.error_code), None)
    if error is None:
        failed_calls = [call for call in calls if call.outcome == "failed" and call.error_code]
        if failed_calls:
            error = max(failed_calls, key=lambda call: call.finished_at or call.started_at or _EPOCH).error_code
    if error is None:
        error = next((p.get("error_code") for p in procedures if isinstance(p.get("error_code"), str)), None)
    if isinstance(error, str) and _CODE.fullmatch(error):
        facts["last_error_code"] = error

    if state != "done":
        reason = next(
            (p.get("reason") for p in procedures if p["status"] != "completed" and isinstance(p.get("reason"), str)), None
        )
        if isinstance(reason, str) and _REASON.fullmatch(reason):
            facts["reason"] = reason
    if coverage is not None:
        facts["planned"], facts["completed"] = coverage
    return facts


def assemble_run_stage_facts(
    *,
    run: RunRow,
    stage_rows: Sequence[StageRow],
    calls: Sequence[CallRow],
    review: Mapping[str, Any] | None,
    cell_bindings: Mapping[str, CellBinding],
    include_server: bool,
) -> dict[str, Any]:
    """The answer of ``getRunStages`` as a plain document, from what the three places hold. Pure: no read, no write, no clock.

    ``review`` is what the extended review reader returned (``{"status", "result"}``). With ``include_server`` false no cell carries
    ``server`` or ``access`` (and none is looked up)."""
    run_open = run.state not in _TERMINAL_RUN_STATES
    rows_by_stage = {row.stage_id: row for row in stage_rows}
    procedures = _procedures(review)
    coverage = _coverage(review)
    plan_cells = _plan_cells(run.stage_plan)
    calls_by_chip: dict[str, list[CallRow]] = defaultdict(list)
    for call in calls:
        if call.chip not in _CHIP_BY_ID:
            raise _integrity("model_call.stage_key")
        calls_by_chip[call.chip].append(call)

    items: list[dict[str, Any]] = []
    for chip in CHIPS:
        rows = [rows_by_stage[stage_id] for stage_id in chip.stage_ids if stage_id in rows_by_stage]
        chip_procedures = [p for p in procedures if p["id"] in chip.stage_ids]
        cells = plan_cells.get(chip.id, [])
        chip_calls = calls_by_chip.get(chip.id, [])
        if not (rows or chip_procedures or cells or chip_calls):
            continue  # a chip no place mentions is not in this run
        # A chip whose every procedure says it called no model (`V2-ORIGINAL-REVIEW-01`: the original's critic and corrector under plan v2) has
        # no plan line either: no cell was bound for it, and «модель прогона» would name a model that did none of its work.
        deterministic = bool(chip_procedures) and all(p.get("model_called") is False for p in chip_procedures)
        if not chip.calls_model or deterministic:
            plan: list[dict[str, Any]] = []
        elif run.stage_plan is not None:
            plan = [
                _cell_view(cell, binding=cell_bindings.get(cell["cell_key"]) if include_server else None,
                           include_server=include_server)
                for cell in cells
            ]
        else:
            plan = [_legacy_cell(run, chip_calls, include_server=include_server)]
        items.append({
            "chip": chip.id,
            "stage_ids": list(chip.stage_ids),
            "plan": plan,
            "facts": _facts(
                chip, rows=rows, statuses=[p["status"] for p in chip_procedures], procedures=chip_procedures,
                calls=chip_calls, coverage=coverage.get(chip.id), run_open=run_open,
            ),
        })
    return {
        "run_id": run.run_id,
        "state": run.state,
        "plan_source": "stage_plan" if run.stage_plan is not None else "run_binding",
        "items": items,
    }


# --- the reads -----------------------------------------------------------------------------------------------------------

_SELECT_RUN = text(
    "SELECT r.run_id, r.state, r.stage_plan, r.connection_revision_id FROM audit_run r WHERE r.run_id = :run_id"
)
_SELECT_REVISION = text(
    "SELECT c.display_name AS server, cr.pin_id AS model_id, cr.billing AS billing "
    "FROM executor_connection_revision cr JOIN executor_connection c ON c.connection_id = cr.connection_id "
    "WHERE cr.revision_id = :revision_id"
)
_SELECT_CELL_BINDINGS = text(
    "SELECT b.cell_key AS cell_key, COALESCE(h.display_name, c.display_name) AS server, cr.billing AS billing "
    "FROM audit_run_cell_binding b "
    "JOIN executor_connection_revision cr ON cr.revision_id = b.connection_revision_id "
    "JOIN executor_connection c ON c.connection_id = cr.connection_id "
    "LEFT JOIN executor_host h ON h.host_id = c.host_id "
    "WHERE b.run_id = :run_id"
)
_SELECT_STAGE_ROWS = text(
    "SELECT stage_id, status, error ->> 'code' AS error_code, started_at, finished_at, "
    f"metrics ->> '{_REUSED_FROM_METRIC}' AS reused_from_run_id "
    "FROM stage_result WHERE run_id = :run_id ORDER BY stage_id"
)
#: Every call the journal holds for the run: each effect with the ``model_call`` row it ended in (``final_model_call_id``, else its own id),
#: and each ``model_call`` row no effect names (written before the effects existed). ``UNION ALL`` of two disjoint sets: the second
#: excludes every row the first joins.
_SELECT_CALLS = text(
    """
    SELECT e.model_call_id AS call_id, e.state AS effect_state, e.error_code AS effect_error,
           e.input_tokens AS effect_in, e.output_tokens AS effect_out, e.stage_key AS effect_stage_key,
           e.access AS effect_access, e.parameters AS effect_parameters, e.request_sha256 AS request_sha256,
           e.model_identity AS model_id, e.prepared_at AS prepared_at, e.updated_at AS updated_at,
           m.model_call_id AS m_id, m.status AS call_status, m.error_code AS call_error, m.input_tokens AS call_in,
           m.output_tokens AS call_out, m.cost_micros AS cost_micros, m.cost_basis AS cost_basis,
           m.stage_key AS call_stage_key, m.access AS call_access, m.parameters AS call_parameters,
           m.latency_ms AS latency_ms, m.created_at AS call_created_at
      FROM provider_call_effect e
      LEFT JOIN model_call m
        ON m.run_id = e.run_id AND m.model_call_id = COALESCE(e.final_model_call_id, e.model_call_id)
     WHERE e.run_id = :run_id
    UNION ALL
    SELECT m.model_call_id, NULL, NULL, NULL, NULL, NULL, NULL, NULL, m.request_sha256, m.model_identity, NULL, NULL,
           m.model_call_id, m.status, m.error_code, m.input_tokens, m.output_tokens, m.cost_micros, m.cost_basis,
           m.stage_key, m.access, m.parameters, m.latency_ms, m.created_at
      FROM model_call m
     WHERE m.run_id = :run_id
       AND NOT EXISTS (
           SELECT 1 FROM provider_call_effect e
            WHERE e.run_id = m.run_id AND (e.model_call_id = m.model_call_id OR e.final_model_call_id = m.model_call_id))
    """
)


def _access_of_billing(billing: Any) -> str | None:
    """``not_metered`` is a subscription and ``metered`` an API key (ADR-0028 decision 2); anything else says nothing."""
    return {"not_metered": "subscription", "metered": "api"}.get(billing)


def _read_run(session: Session, run_id: str) -> RunRow:
    row = session.execute(_SELECT_RUN, {"run_id": run_id}).mappings().first()
    if row is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    binding = None
    if row["stage_plan"] is None and row["connection_revision_id"] is not None:
        bound = session.execute(_SELECT_REVISION, {"revision_id": row["connection_revision_id"]}).mappings().first()
        if bound is not None:
            binding = RunBinding(str(bound["server"]), str(bound["model_id"]), _access_of_billing(bound["billing"]))
    return RunRow(str(row["run_id"]), str(row["state"]), row["stage_plan"], binding)


def _read_cell_bindings(session: Session, run: RunRow) -> dict[str, CellBinding]:
    if run.stage_plan is None:
        return {}
    rows = session.execute(_SELECT_CELL_BINDINGS, {"run_id": run.run_id}).mappings().all()
    return {str(row["cell_key"]): CellBinding(str(row["server"]), _access_of_billing(row["billing"])) for row in rows}


def _read_stage_rows(session: Session, run_id: str) -> list[StageRow]:
    rows = session.execute(_SELECT_STAGE_ROWS, {"run_id": run_id}).mappings().all()
    return [
        StageRow(
            stage_id=str(row["stage_id"]), status=str(row["status"]), error_code=row["error_code"],
            started_at=row["started_at"], finished_at=row["finished_at"], reused_from_run_id=row["reused_from_run_id"],
        )
        for row in rows
    ]


def _first(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _call_from_row(row: Mapping[str, Any]) -> CallRow:
    """One journal row as a :class:`CallRow`. A ``model_call`` row decides how the call ended; an effect with no ``model_call`` row
    decides it by its state (a call still in flight is neither succeeded nor failed)."""
    if row["m_id"] is not None:
        outcome = _CALL_OUTCOME.get(row["call_status"])
        if outcome is None:
            raise _integrity("model_call.status")
    else:
        outcome = _EFFECT_OUTCOME.get(row["effect_state"])
        if outcome is None:
            raise _integrity("provider_call_effect.state")
    parameters = _first(row["call_parameters"], row["effect_parameters"])
    access = _first(row["call_access"], row["effect_access"])
    chip = chip_of_call(_first(row["call_stage_key"], row["effect_stage_key"]), parameters)

    created = row["call_created_at"]
    latency = row["latency_ms"]
    started = row["prepared_at"]
    if started is None and created is not None:
        started = created - timedelta(milliseconds=latency) if type(latency) is int and latency >= 0 else created
    finished = None if outcome == "in_flight" else _first(created, row["updated_at"])

    return CallRow(
        call_id=str(row["call_id"]),
        chip=chip,
        outcome=outcome,
        request_key=(str(row["request_sha256"]), str(row["model_id"])),
        started_at=started,
        finished_at=finished,
        input_tokens=_non_negative(_first(row["call_in"], row["effect_in"])),
        output_tokens=_non_negative(_first(row["call_out"], row["effect_out"])),
        cost_micros=_non_negative(row["cost_micros"]),
        subscription=access == "subscription" or (access is None and row["cost_basis"] == "unmetered"),
        error_code=_first(row["call_error"], row["effect_error"]),
        model_id=None if row["model_id"] is None else str(row["model_id"]),
    )


def _read_calls(session: Session, run_id: str) -> list[CallRow]:
    return [_call_from_row(row) for row in session.execute(_SELECT_CALLS, {"run_id": run_id}).mappings().all()]


def read_run_stage_facts(
    sessions: Callable[[], AbstractContextManager[Session]],
    blob_store: Any,
    *,
    run_id: str,
    include_server: bool,
) -> dict[str, Any]:
    """The stages of one run, plan and fact, as ``RunStages`` of the contract (a plain document the adapter validates).

    ``sessions`` is a session factory and ``blob_store`` the store the extended review artifact is read from, as for
    ``read_extended_review``. The run, the stage results, the journal and the bindings are one read-only snapshot; the extended review is
    read after it by its own reader (a second snapshot: a call journalled between the two is counted in the journal and not yet in the
    review's coverage, which is why ``planned`` and ``completed`` are the review's own figures and never derived from the journal).
    An unknown run is ``404 not_found``. ``include_server`` false omits the server and the access of every cell (the viewer, ``R-150w``).
    """
    from auditmanager.runs.extended_review import read_extended_review

    with sessions() as session:
        session.connection(execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True})
        run = _read_run(session, run_id)
        stage_rows = _read_stage_rows(session, run_id)
        calls = _read_calls(session, run_id)
        cell_bindings = _read_cell_bindings(session, run) if include_server else {}
    review = read_extended_review(sessions, blob_store, run_id)
    return assemble_run_stage_facts(
        run=run, stage_rows=stage_rows, calls=calls, review=review, cell_bindings=cell_bindings, include_server=include_server,
    )
