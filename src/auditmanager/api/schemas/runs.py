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
from typing import Any, Final, Mapping, Sequence

from auditmanager.api.schemas.common import timestamp
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "PROVIDER_MODES",
    "RUN_STATES",
    "RunStatusView",
    "StageStateView",
    "parse_start_run_request",
    "run_status_body",
]

#: ``#/components/schemas/RunState``. `succeeded` is deliberately absent.
RUN_STATES: Final[frozenset[str]] = frozenset(
    {
        "created",
        "queued",
        "running",
        "validating",
        "published",
        "partial",
        "failed",
        "cancelled",
    }
)

#: ``#/components/schemas/ProviderMode``.
PROVIDER_MODES: Final[frozenset[str]] = frozenset({"live", "recorded"})

#: ``#/components/schemas/VersionUid``.
_VERSION_PREFIX: Final[str] = "ver_"


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
    interrupted_reason: str | None = None
    published_finding_count: int | None = None
    diagnostic_observation_count: int | None = None
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
    if view.interrupted_reason is not None:
        body["interrupted_reason"] = view.interrupted_reason
    if view.published_finding_count is not None:
        body["published_finding_count"] = view.published_finding_count
    if view.diagnostic_observation_count is not None:
        body["diagnostic_observation_count"] = view.diagnostic_observation_count
    if view.terminal_at is not None:
        body["terminal_at"] = timestamp(view.terminal_at)
    return body


@dataclass(frozen=True, slots=True)
class StartRunCommand:
    """A validated ``StartRunRequest``."""

    version_uid: str
    provider_mode: str | None


def parse_start_run_request(payload: Mapping[str, Any]) -> StartRunCommand:
    """Validate ``StartRunRequest``.

    Refusals here are ``analysis_input_invalid`` only where the *declared analysis
    inputs* are what is wrong. A malformed body is ``validation_failed``: the frozen
    ``RunInputInvalid`` response describes exactly that split.
    """
    unknown = sorted(set(payload) - {"version_uid", "provider_mode"})
    if unknown:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="The request body carries a property the schema does not declare.",
            field=unknown[0],
            constraint="additionalProperties",
        )
    version_uid = payload.get("version_uid")
    if not isinstance(version_uid, str) or not version_uid.startswith(_VERSION_PREFIX):
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="The run must declare the version_uid of a published version.",
        )
    provider_mode = payload.get("provider_mode")
    if provider_mode is not None:
        if not isinstance(provider_mode, str) or provider_mode not in PROVIDER_MODES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="provider_mode must be one of: live, recorded.",
                field="provider_mode",
                constraint="enum",
            )
    return StartRunCommand(version_uid=version_uid, provider_mode=provider_mode)
