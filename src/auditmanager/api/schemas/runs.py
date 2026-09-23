"""``RunStatus``, ``StageState`` and ``StartRunRequest``.

The producer of these values is session ``B5`` (``auditmanager.runs``), which is built
in parallel with this session and may not exist in this tree yet. That is why the
router depends on the *shape* declared by ``contracts/api/v1/openapi.json`` rather than
on a module: :class:`RunStatusView` restates the frozen ``RunStatus`` property set
exactly, and :class:`auditmanager.api.routers.ports.RunPort` is the narrow seam a
composition root satisfies.

The success terminal is ``published``. **There is no ``succeeded`` run state** --
``succeeded`` is a ``StageResult`` status on a different aggregate, and
:data:`RUN_STATES` is asserted against the frozen enum so the two cannot be confused.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.errors import ErrorCode, screen_details

__all__ = ["RunStatusView", "StageStateView", "run_status_body", "stage_state_body"]

@dataclass(frozen=True, slots=True)
class StageStateView:
    """Exactly the frozen ``StageState``."""

    stage_id: str
    status: str
    stage_version: str | None = None
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunStatusView:
    """Exactly the frozen ``RunStatus``."""

    run_id: str
    project_uid: str
    version_uid: str
    state: str
    provider_mode: str
    created_at: datetime
    stages: tuple[StageStateView, ...] = ()
    analysis_profile_id: str | None = None
    prompt_bundle_id: str | None = None
    degradation_set: tuple[str, ...] | None = None
    terminal_reason: str | None = None
    #: `D-46`. Safe scalar classifiers saying **which** dependency a failed run terminated
    #: on, restricted to the ``safe_detail_keys`` the frozen catalog declares for
    #: :attr:`terminal_reason`. ``None`` when there is none; never an empty object.
    terminal_detail: Mapping[str, Any] | None = None
    interrupted_reason: str | None = None
    published_finding_count: int | None = None
    diagnostic_observation_count: int | None = None
    #: `D-21`. What the run spent at the provider, in the stored integer unit, summed
    #: over **every** ``model_call`` row of the run including every retry attempt. The
    #: three cost fields are set together or not at all: a run that made no provider call
    #: has no cost to report, and ``0`` would be an answer to a question nothing asked.
    cost_micros: int | None = None
    #: ``measured`` only when every contributing call reported its own cost; ``estimated``
    #: the moment one did not. An aggregate over the calls the sum spans -- never the last
    #: call's basis, which is the `D-15` defect.
    cost_basis: str | None = None
    #: How many ``model_call`` rows ``cost_micros`` sums. Published rather than inferred:
    #: without it a reader cannot tell a one-attempt run from a retried one, and that is
    #: exactly the ambiguity `D-15` records.
    model_call_count: int | None = None
    terminal_at: datetime | None = None


def stage_state_body(view: StageStateView) -> dict[str, Any]:
    body: dict[str, Any] = {"stage_id": view.stage_id, "status": view.status}
    if view.stage_version is not None:
        body["stage_version"] = view.stage_version
    # `error_code` is null exactly when the status is `succeeded`, so it is emitted
    # whenever the stage is not succeeded -- including as an explicit null, which the
    # schema's `oneOf [string, null]` accepts and which says "no code" rather than
    # "field forgotten".
    if view.status != "succeeded" or view.error_code is not None:
        body["error_code"] = view.error_code
    if view.started_at is not None:
        body["started_at"] = timestamp(view.started_at)
    if view.finished_at is not None:
        body["finished_at"] = timestamp(view.finished_at)
    return body


def run_status_body(view: RunStatusView) -> dict[str, Any]:
    body: dict[str, Any] = {
        "run_id": view.run_id,
        "project_uid": view.project_uid,
        "version_uid": view.version_uid,
        "state": view.state,
        "provider_mode": view.provider_mode,
        "stages": [stage_state_body(stage) for stage in view.stages],
        "created_at": timestamp(view.created_at),
    }
    if view.analysis_profile_id is not None:
        body["analysis_profile_id"] = view.analysis_profile_id
    if view.prompt_bundle_id is not None:
        body["prompt_bundle_id"] = view.prompt_bundle_id
    if view.degradation_set is not None:
        body["degradation_set"] = list(view.degradation_set)
    if view.terminal_reason is not None:
        body["terminal_reason"] = view.terminal_reason
        # `D-46`, and the third of the three screens. The first is
        # `TerminalSelection.__post_init__`, when the run terminates; the second is the
        # UPDATE that writes the row. **This one is the only one that covers a row this
        # code did not write** -- one written by an older process, restored from a backup,
        # or edited by hand -- and an unrestricted detail object is exactly how internals
        # reach a client.
        #
        # It is inside the `terminal_reason` branch because the allowlist is a property of
        # the reported code: a detail with no reason has nothing to be screened against,
        # and the correct thing to do with one is not to publish it. The database refuses
        # that combination too (`ck_audit_run_terminal_detail_needs_a_reason`), so this
        # branch is the second line of one rule rather than the only one.
        if view.terminal_detail:
            screened = screen_details(
                ErrorCode(view.terminal_reason), view.terminal_detail
            )
            if screened:
                body["terminal_detail"] = dict(screened)
    if view.interrupted_reason is not None:
        body["interrupted_reason"] = view.interrupted_reason
    if view.published_finding_count is not None:
        body["published_finding_count"] = view.published_finding_count
    if view.diagnostic_observation_count is not None:
        body["diagnostic_observation_count"] = view.diagnostic_observation_count
    # The three move together. A partially emitted cost -- a figure with no basis, or a
    # basis with no figure -- would be less legible than no cost at all, so the producer
    # sets all three or none and this renders what it set.
    if view.cost_micros is not None:
        body["cost_micros"] = view.cost_micros
    if view.cost_basis is not None:
        body["cost_basis"] = view.cost_basis
    if view.model_call_count is not None:
        body["model_call_count"] = view.model_call_count
    if view.terminal_at is not None:
        body["terminal_at"] = timestamp(view.terminal_at)
    return body
