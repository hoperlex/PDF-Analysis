"""Read immutable accepted cost authority for a worker; no provider or route choice."""

from __future__ import annotations

from dataclasses import dataclass
import math

from auditmanager.ingest.public import CommandRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId

from .repository import RunRepository


@dataclass(frozen=True, slots=True)
class RunCostPolicy:
    approved: bool
    ceiling_usd: float
    enforce_ceiling: bool
    window_characters: int | None = None
    max_windows: int | None = None
    estimate_digest: str | None = None
    model_id: str | None = None
    rate_sha256: str | None = None
    connection_revision_id: str | None = None
    extended_review: dict | None = None


def read_run_cost_policy(session, *, run_id: str, default_ceiling_usd: float,
                         runs: RunRepository | None = None) -> RunCostPolicy:
    if type(default_ceiling_usd) not in {int, float} or not math.isfinite(default_ceiling_usd) or default_ceiling_usd <= 0:
        raise ValueError("default ceiling must be a positive finite amount")
    run = (runs or RunRepository()).get(session, run_id)
    outcome = {}
    if run.command_id is not None:
        command = CommandRepository().get(session, CommandId.parse(run.command_id))
        if command.state != "succeeded":
            raise DomainError(ErrorCode.INTERNAL_ERROR, message="run cost authority is not accepted")
        outcome = command.outcome or {}
    consent = outcome.get("cost_consent")
    if consent is None:
        return RunCostPolicy(False, float(default_ceiling_usd), not bool(outcome.get("relaxed_limits", False)))
    try:
        digest, billing = consent["estimate_digest"], consent["billing"]
        ceiling = consent.get("run_limits_micros", {}).get(run_id, consent["ceiling_micros"])
        window, maximum = consent.get("window_characters"), consent.get("max_windows")
        model, rates = consent["model_id"], consent["rate_sha256"]
        revision = consent.get("connection_revision_id")
        extended = consent.get("extended_review")
        if extended is not None and (
            not isinstance(extended, dict) or extended.get("enabled") is not True
            or extended.get("plan_version") != "extended-review-v1"
            or type(extended.get("max_blocks")) is not int
            or not 1 <= extended["max_blocks"] <= 16
        ):
            raise ValueError()
        if (not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
                or billing not in {"metered", "unmetered"} or type(ceiling) is not int or ceiling < 0
                or billing == "metered" and ceiling == 0
                or not isinstance(model, str) or not model or not isinstance(rates, str) or len(rates) != 64
                or window is not None and (type(window) is not int or window <= 0)
                or maximum is not None and (type(maximum) is not int or maximum < 1)):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="accepted run cost authority is invalid") from None
    # Unmetered still has a positive operational configuration; no monetary halt applies.
    if revision != getattr(run, "connection_revision_id", None):
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_estimate_binding_changed")
    return RunCostPolicy(True, ceiling / 1_000_000 if ceiling else float(default_ceiling_usd),
                         billing == "metered", window, maximum, digest, model, rates, revision, extended)
