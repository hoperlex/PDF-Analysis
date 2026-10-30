"""Accepted native-window planning authority; missing metadata is legacy."""
from __future__ import annotations

from copy import deepcopy
import os
from sqlalchemy import text
from auditmanager.comparison.stage_ai.validation import StageAiValidationError

VERSION = "windowed-v1"
GLOBAL_VERSION = "windowed-global-v1"
LIMITS = {"pages": 64, "characters": 240_000, "fragments": 1600,
          "pack_characters": 60_000, "pack_blocks": 64, "catalogue_blocks_per_page": 2,
          "catalogue_snippet_characters": 256, "classification_units": 128,
          "events": 512, "parameters": 1024, "request_characters": 240_000}
GLOBAL_LIMITS = {**LIMITS, "global_candidate_pairs": 128, "global_pairs_per_call": 4}


def _windowed_policy():
    from .windowed import BUNDLE
    return {"plan_version": VERSION, "bundle": BUNDLE, "limits": deepcopy(LIMITS)}


def _policy(version):
    if version == VERSION: return _windowed_policy()
    if version == GLOBAL_VERSION:
        from .consolidation import BUNDLE
        return {"plan_version": GLOBAL_VERSION, "bundle": BUNDLE, "limits": deepcopy(GLOBAL_LIMITS)}
    raise StageAiValidationError("v3_plan_configuration_unsupported")


def fresh_policy():
    """Only new estimates/commands consult the rollback switch."""
    selected = os.environ.get("AUDITMANAGER_STAGE_V3_PLAN", GLOBAL_VERSION).strip()
    if selected == "legacy": return None
    return _policy(selected)


def validate_policy(value):
    if value is None:
        return None
    # Accepted windowed authority remains selected even when the fresh-start
    # rollback switch is subsequently set to legacy.
    if not isinstance(value, dict) or value != _policy(value.get("plan_version")):
        raise StageAiValidationError("v3_windowed_policy_changed_requires_fresh_run")
    return deepcopy(value)


def stored_policy(value):
    """Read historical authority without substituting the current code bundle."""
    if value is None: return None
    if (not isinstance(value, dict) or set(value) != {"plan_version", "bundle", "limits"}
            or value["plan_version"] not in {VERSION, GLOBAL_VERSION} or not isinstance(value["bundle"], str)
            or len(value["bundle"]) != 64 or not isinstance(value["limits"], dict)):
        raise StageAiValidationError("v3_windowed_saved_policy_invalid")
    return deepcopy(value)


def policy_for_run(session, run_id):
    return stored_policy(session.execute(text(
        "SELECT c.outcome->'stage_v3_policy' FROM stage_chain_run r "
        "JOIN command_record c ON c.command_id=r.command_id WHERE r.stage_chain_run_id=:run"
    ), {"run": run_id}).scalar_one_or_none())


def policy_for_batch(session, batch_id):
    return stored_policy(session.execute(text(
        "SELECT c.outcome->'stage_v3_policy' FROM stage_chain_batch b "
        "JOIN command_record c ON c.command_id=b.command_id WHERE b.stage_chain_batch_id=:batch"
    ), {"batch": batch_id}).scalar_one_or_none())


def bundle_for(policy):
    from .procedures import BUNDLE
    return BUNDLE if policy is None else validate_policy(policy)["bundle"]
