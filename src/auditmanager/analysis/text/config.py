"""Provider configuration, read from the process environment.

Read ``docs/program/P02_LOCK.json`` -> ``provider_configuration`` before changing
anything here. Provider configuration is deliberately **not** in the lane ``.env``:
``make`` enforces a strict allowlist of exactly the fifteen names ``FF-01`` section 3
freezes, and its stated purpose is to refuse anything that selects what code runs.
``AUDITMANAGER_PROVIDER_MODE`` is precisely that. So the application reads these four
names from its own environment at run time, and ``ANTHROPIC_API_KEY`` is an injected
secret that is never written to a file in this repository.

``ProviderMode`` is a closed enum rather than a string. That is the first half of the
``PC-01`` acceptance criterion that a recorded run must never be presentable as a live
one; the second half is in :mod:`auditmanager.analysis.text.provenance`, where the
mode stamped on the artifact is taken from the adapter that actually ran and from
nowhere else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, Mapping

from auditmanager.analysis.text.lock import STAGE_ID, ProviderLock, provider_lock
from auditmanager.shared.errors import DomainError, ErrorCode

ENV_API_KEY: Final[str] = "ANTHROPIC_API_KEY"
ENV_PROVIDER_MODE: Final[str] = "AUDITMANAGER_PROVIDER_MODE"
ENV_MODEL_ID: Final[str] = "AUDITMANAGER_MODEL_ID"
ENV_COST_CEILING: Final[str] = "AUDITMANAGER_RUN_COST_CEILING_USD"

#: A stable dependency class name for the error envelope. Never a host, a URL, a
#: vendor endpoint or a credential: ``dependency_unavailable`` declares exactly one
#: safe detail key and the catalog note pins what may go in it.
DEPENDENCY_NAME: Final[str] = "model_provider"

#: Fallback per-run ceiling in USD, used when the operator sets no explicit one.
#: ``OD-03`` owns the figure and has not recorded a machine-readable number in either
#: lock, so this is a deliberately conservative stand-in and not the owner's decision:
#: one AR document under the PC-01 envelope costs cents at the pinned rates, so a
#: run that reaches a dollar has gone wrong in a way that should halt.
DEFAULT_RUN_COST_CEILING_USD: Final[float] = 1.00


class ProviderMode(str, Enum):
    """How a model response was obtained. Closed on purpose.

    There is no ``UNKNOWN`` member and no way to widen the set at a call site, so
    every model call record and every published artifact carries one of exactly two
    values and a consumer never has to infer which.
    """

    LIVE = "live"
    RECORDED = "recorded"

    @classmethod
    def parse(cls, value: str) -> "ProviderMode":
        try:
            return cls(value)
        except ValueError:
            raise DomainError(
                ErrorCode.ANALYSIS_INPUT_INVALID,
                message="provider mode must be either live or recorded",
                stage_id=STAGE_ID,
                reason="provider_mode_invalid",
            ) from None


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """What the operator asked for. Not evidence of what actually happened.

    ``mode`` here is an *intent*. The mode written into run provenance is read off the
    adapter that produced the responses, so a mislabelled configuration cannot make a
    replay look like a call.
    """

    mode: ProviderMode
    model_id: str
    run_cost_ceiling_usd: float
    api_key: str | None
    #: ``True`` when the operator set the ceiling rather than inheriting the
    #: stand-in above. Recorded so a run report can say which number was in force.
    ceiling_is_explicit: bool
    approved_window_characters: int | None = None
    approved_max_windows: int | None = None
    approved_cost_ceiling: bool = False
    approved_model_id: str | None = None
    approved_rate_sha256: str | None = None
    #: The connection revision the accepted run command approved. ``None`` is "no revision is pinned": a run of the
    #: ``environment`` source froze none. It is **not** what a run admitted on a group has before dispatch -- that run
    #: carries :attr:`approved_group_revision_id` and refuses every model call until a member is bound
    #: (`EXEC2-GROUP-RUN-01`, ``analysis.text.cost.require_approved_model``).
    approved_connection_revision_id: str | None = None
    approved_native_page_pieces: dict | None = None
    #: `EXEC2-GROUP-RUN-01` (ADR-0026 decisions 13 and 14). The group revision the accepted command admitted the run
    #: on, ``None`` for a run whose executor was frozen at start. Set, :attr:`approved_connection_revision_id` is the
    #: member dispatch bound, and ``None`` there means the run is still pending, so no call may be made.
    approved_group_revision_id: str | None = None
    #: `HOSTS-LAYOUT-01` (ADR-0028 decision 8, consent v2). For a run frozen with a stage plan, the models its consent approved:
    #: model id -> ``{"rate_sha256", "access"}``. Set, :func:`~auditmanager.analysis.text.cost.require_approved_model` checks that the
    #: model of a call is a member, at the rate and with the access approved, instead of comparing one ``approved_model_id``.
    #: ``None`` is every run whose consent names one model.
    approved_models: Mapping[str, Mapping[str, str]] | None = None
    #: The digest of the stage plan the consent was given for (a planned run only).
    approved_stage_plan_digest: str | None = None
    #: The cell this configuration serves (model, effort, answer limit, timeout, access); ``None`` outside a planned run. The text
    #: analysis reads its effort and answer limit from here, and ``model_id`` is then the cell's model.
    cell_settings: Any = None


def _read_ceiling(environ: Mapping[str, str]) -> tuple[float, bool]:
    raw = environ.get(ENV_COST_CEILING)
    if raw is None or raw.strip() == "":
        return DEFAULT_RUN_COST_CEILING_USD, False
    try:
        ceiling = float(raw)
    except ValueError:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the run cost ceiling must be a number of US dollars",
            stage_id=STAGE_ID,
            reason="cost_ceiling_invalid",
        ) from None
    if ceiling <= 0:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="the run cost ceiling must be greater than zero",
            stage_id=STAGE_ID,
            reason="cost_ceiling_invalid",
        )
    return ceiling, True


def load_provider_config(
    environ: Mapping[str, str] | None = None,
    *,
    lock: ProviderLock | None = None,
) -> ProviderConfig:
    """Build the configuration from the process environment.

    ``OD-13`` makes ``recorded`` the default so an automated suite that forgets to set
    anything cannot reach the network. Choosing ``live`` is always an explicit act.
    """
    env = os.environ if environ is None else environ
    resolved_lock = lock or provider_lock()
    mode = ProviderMode.parse(env.get(ENV_PROVIDER_MODE, ProviderMode.RECORDED.value))
    model_id = env.get(ENV_MODEL_ID) or resolved_lock.primary_model_id
    resolved_lock.model(model_id)  # refuses an unpinned identity here, not mid-run
    ceiling, explicit = _read_ceiling(env)
    return ProviderConfig(
        mode=mode,
        model_id=model_id,
        run_cost_ceiling_usd=ceiling,
        api_key=env.get(ENV_API_KEY) or None,
        ceiling_is_explicit=explicit,
    )
