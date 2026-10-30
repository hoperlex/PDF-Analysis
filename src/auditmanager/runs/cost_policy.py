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
        uncapped_stats = consent.get("uncapped_stats", False)
        window, maximum = consent.get("window_characters"), consent.get("max_windows")
        model, rates = consent["model_id"], consent["rate_sha256"]
        revision = consent.get("connection_revision_id")
        extended = consent.get("extended_review")
        if extended is not None:
            if not isinstance(extended, dict) or extended.get("enabled") is not True:
                raise ValueError()
            plan = extended.get("plan_version")
            blocks = extended.get("max_blocks")
            if plan in {"extended-review-v1", "extended-review-v2"}:
                if not (type(blocks) is int and blocks == 16 or plan == "extended-review-v2" and blocks == "all"):
                    raise ValueError()
            elif plan == "extended-review-v3":
                rules = extended.get("rules_sha256")
                text_limit = extended.get("text_page_limit")
                section = extended.get("section_code")
                if (not isinstance(section, str) or not 1 <= len(section) <= 8
                        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in section)
                        or type(blocks) is not int or not 1 <= blocks <= 2**31 - 1
                        or type(extended.get("window_size")) is not int or extended["window_size"] != 16
                        or type(extended.get("max_windows")) is not int
                        or type(text_limit) is not int or not 1 <= text_limit <= 2**31 - 1
                        or extended["max_windows"] != max((blocks + 15) // 16, (text_limit + 15) // 16)
                        or extended.get("review") is not True
                        or not isinstance(rules, str) or len(rules) != 64
                        or any(character not in "0123456789abcdef" for character in rules)):
                    raise ValueError()
                if "coverage_version" in extended or "phase_call_limits" in extended:
                    from auditmanager.analysis.public import validate_extended_coverage_policy
                    if not validate_extended_coverage_policy(extended):
                        raise ValueError()
                if "global_cross_window_policy" in extended:
                    from auditmanager.analysis.public import validate_extended_cross_window_policy
                    if (extended.get("coverage_version") != "batched-v1"
                            or not validate_extended_cross_window_policy(extended["global_cross_window_policy"])):
                        raise ValueError()
                if "project_parameters_policy" in extended:
                    from auditmanager.analysis.public import validate_project_parameters_policy
                    if not validate_project_parameters_policy(extended["project_parameters_policy"], section=section, compare_bundle=False):
                        raise ValueError()
                if "norm_paragraph_context_policy" in extended:
                    from .norm_context import validate_policy as validate_norm_context_policy
                    if (extended.get("coverage_version") != "batched-v1"
                            or not validate_norm_context_policy(extended["norm_paragraph_context_policy"], compare_bundle=False)):
                        raise ValueError()
                if "project_parameter_context_policy" in extended:
                    from auditmanager.analysis.public import validate_project_parameter_context_policy
                    if (not isinstance(extended.get("project_parameters_policy"), dict)
                            or not validate_project_parameter_context_policy(extended["project_parameter_context_policy"],
                                parameters_policy=extended["project_parameters_policy"], compare_bundle=False)):
                        raise ValueError()
            else:
                raise ValueError()
        if (not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
                or billing not in {"metered", "unmetered"} or type(ceiling) is not int or ceiling < 0
                or type(uncapped_stats) is not bool
                or uncapped_stats and (not outcome.get("relaxed_limits", False) or ceiling != 0)
                or billing == "metered" and ceiling == 0 and not uncapped_stats
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
                         billing == "metered" and not uncapped_stats, window, maximum,
                         digest, model, rates, revision, extended)
