"""Read immutable accepted cost authority for a worker; no provider or route choice.

`EXEC2-GROUP-RUN-01` (ADR-0026 decisions 13 and 14). The consent of a Run admitted on a group names the **group
revision** and no connection: the connection is chosen at dispatch. Two readers hold it:

* :func:`read_run_cost_policy` -- the worker's policy. For a group Run the consent's group revision must be the one the
  Run froze, and the connection revision it then carries is the one dispatch **bound** (``None`` while the Run is still
  ``pending``, which no model call may follow: ``analysis.text.cost.require_approved_model`` refuses it);
* :func:`group_consent_holds` -- the dispatcher's re-check, inside the claim transaction and before anything is bound.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from auditmanager.analysis.public import model_rate_sha256, pinned_models
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
    native_page_piece_policy: dict | None = None
    #: The group revision the accepted consent names, ``None`` for a Run whose executor was frozen at start. Set, a
    #: ``None`` ``connection_revision_id`` means *pending* (no member has taken the Run yet), not ``environment``.
    executor_group_revision_id: str | None = None
    #: `HOSTS-LAYOUT-01` (consent v2). For a Run frozen with a stage plan: the models its consent approved (model id -> ``rate_sha256`` and
    #: ``access``) and the digest of the plan it was given for. ``None`` for a Run whose consent names one model.
    models: dict | None = None
    stage_plan_digest: str | None = None


def _binding_changed() -> DomainError:
    return DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_estimate_binding_changed")


def _consent_models(value, plan) -> dict:
    """The model map of a consent v2, checked against the plan of the Run it governs: exactly the plan's models, each with a rate digest
    and the access the plan froze. Anything else is a consent that does not bind this Run's work."""
    if (not isinstance(value, dict) or set(value) != set(plan.models)
            or any(not isinstance(entry, dict) or set(entry) != {"rate_sha256", "access"}
                   or not isinstance(entry["rate_sha256"], str) or len(entry["rate_sha256"]) != 64
                   or any(ch not in "0123456789abcdef" for ch in entry["rate_sha256"])
                   or entry["access"] != plan.access_of(model) for model, entry in value.items())):
        raise _binding_changed()
    return {model: dict(entry) for model, entry in value.items()}


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
    stage_plan = getattr(run, "stage_plan", None)
    if consent is None:
        if stage_plan is not None:
            # A Run frozen with a stage plan is never started without the consent that binds its models (`HOSTS-LAYOUT-01`).
            raise _binding_changed()
        return RunCostPolicy(False, float(default_ceiling_usd), not bool(outcome.get("relaxed_limits", False)))
    try:
        digest, billing = consent["estimate_digest"], consent["billing"]
        ceiling = consent.get("run_limits_micros", {}).get(run_id, consent["ceiling_micros"])
        uncapped_stats = consent.get("uncapped_stats", False)
        # The section-run bounds hold unless the run asked for relaxed_limits (`REVIEW-FIX-BOUNDS-1102`).
        lifted = outcome.get("relaxed_limits", False) is True
        section_sources, section_pages = (2**31 - 1, 2**31 - 1) if lifted else (1000, 500)
        window, maximum = consent.get("window_characters"), consent.get("max_windows")
        model, rates = consent["model_id"], consent["rate_sha256"]
        revision = consent.get("connection_revision_id")
        group_revision = consent.get("executor_group_revision_id")
        extended = consent.get("extended_review")
        page_pieces = consent.get("native_page_piece_policy")
        if page_pieces is not None:
            from auditmanager.analysis.public import validate_native_page_piece_policy
            if not validate_native_page_piece_policy(page_pieces, compare_bundle=False):
                raise ValueError()
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
                        or type(blocks) is not int or not 1 <= blocks <= section_sources
                        or type(extended.get("window_size")) is not int or extended["window_size"] != 16
                        or type(extended.get("max_windows")) is not int
                        or type(text_limit) is not int or not 1 <= text_limit <= section_pages
                        or extended.get("unbounded_stats") is True and not lifted
                        or extended["max_windows"] != max((blocks + 15) // 16, (text_limit + 15) // 16)
                        or extended.get("review") is not True
                        or not isinstance(rules, str) or len(rules) != 64
                        or any(character not in "0123456789abcdef" for character in rules)):
                    raise ValueError()
                if "coverage_version" in extended or "phase_call_limits" in extended:
                    from auditmanager.analysis.public import validate_extended_coverage_policy
                    if not validate_extended_coverage_policy(extended):
                        raise ValueError()
                if "completion_policy" in extended or "semantic_repair_attempts" in extended:
                    if (extended.get("completion_policy") != "source-complete-v1"
                            or type(extended.get("semantic_repair_attempts")) is not int
                            or extended["semantic_repair_attempts"] != 1
                            or extended.get("coverage_version") != "batched-v1"):
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
                if "project_parameter_review_context_policy" in extended:
                    from auditmanager.analysis.public import validate_project_parameter_review_context_policy
                    if (extended.get("coverage_version") != "batched-v1"
                            or "project_parameter_context_policy" not in extended
                            or not validate_project_parameter_review_context_policy(extended["project_parameter_review_context_policy"],
                                parameters_policy=extended["project_parameters_policy"], compare_bundle=False)):
                        raise ValueError()
            else:
                raise ValueError()
        if (not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
                or billing not in {"metered", "unmetered", "mixed"} or type(ceiling) is not int or ceiling < 0
                or billing == "mixed" and consent.get("stage_plan_digest") is None
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
    plan_digest, models = consent.get("stage_plan_digest"), None
    if (stage_plan is not None) != (plan_digest is not None):
        # A plan with a consent that names none, or a consent v2 on a Run with no plan: the consent does not bind this work.
        raise _binding_changed()
    if stage_plan is not None:
        from .stage_layout import parse_plan

        plan = parse_plan(stage_plan)
        if (plan.digest != plan_digest or group_revision is not None or revision is not None
                or model != plan.cell("text:main").model_id):
            raise _binding_changed()
        models = _consent_models(consent.get("models"), plan)
        revision = None
    elif group_revision is not None or getattr(run, "binding_state", "frozen_at_start") != "frozen_at_start":
        # Admitted on a group: the consent names the group revision and the Run froze the same one. The connection
        # revision is the one dispatch wrote -- ``None`` until then -- and is never compared with the consent, which
        # holds none (the DB only lets it go NULL -> a member of that group revision, once).
        if (group_revision is None or revision is not None
                or group_revision != getattr(run, "executor_group_revision_id", None)):
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_estimate_binding_changed")
        revision = getattr(run, "connection_revision_id", None)
    elif revision != getattr(run, "connection_revision_id", None):
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="cost_estimate_binding_changed")
    return RunCostPolicy(True, ceiling / 1_000_000 if ceiling else float(default_ceiling_usd),
                         billing in {"metered", "mixed"} and not uncapped_stats, window, maximum,
                         digest, model, rates, revision, extended, page_pieces, group_revision, models, plan_digest)


def group_consent_holds(session, *, run_id: str, group_revision_id: str, pin_id: str, billing: str,
                        runs: RunRepository | None = None) -> bool:
    """Does the consent a Run was accepted under still hold for the group revision it froze? (ADR-0026 decision 14.)

    Called by the claim, inside its transaction, before any member is bound. The group revision is immutable and its
    members share one pin, model and billing, so what can still differ is small and is checked, never assumed:

    * the consent names **this** group revision;
    * the model and the billing it approved are the group revision's (``billing`` in the estimate's spelling,
      ``metered`` or ``unmetered``);
    * the rate it approved is the rate the provider lock publishes for that pin **now** -- the call-time guard
      (``analysis.text.cost.require_approved_model``) compares the same two digests, so a lock that moved since the
      consent would refuse every call after the member was bound.

    A Run accepted with no cost consent at all (a deployment that does not ask for it) has no envelope to break and
    holds. ``False`` means *call nothing*: the dispatcher records ``needs_reconsent`` and binds no member.
    """
    run = (runs or RunRepository()).get(session, run_id)
    outcome = {}
    if run.command_id is not None:
        command = CommandRepository().get(session, CommandId.parse(run.command_id))
        if command.state != "succeeded":
            return False
        outcome = command.outcome or {}
    consent = outcome.get("cost_consent")
    if consent is None:
        return True
    if (consent.get("executor_group_revision_id") != group_revision_id
            or consent.get("model_id") != pin_id or consent.get("billing") != billing):
        return False
    pin = next((row for row in pinned_models() if row.model_id == pin_id), None)
    return pin is not None and consent.get("rate_sha256") == model_rate_sha256(pin)
