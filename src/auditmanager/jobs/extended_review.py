"""Durable paid-effect fence for bounded extended-review units; no new tables."""
from __future__ import annotations
from typing import Sequence
from sqlalchemy import text
from sqlalchemy.orm import Session
from auditmanager.shared.errors import DomainError, ErrorCode


def extended_context_unit(session: Session, *, run_id: str, phase: str,
                          source_sha256: str, base_request_sha256: str) -> dict | None:
    """Replay a paid context-bearing unit before reading today's memory.

    The base is the exact frozen model request before reference data. A changed
    memory block never causes another payment for the same logical unit.
    Unknown/abandoned outcomes require the existing reconciliation path first.
    """
    params = {"run": run_id, "phase": phase, "source": source_sha256, "base": base_request_sha256}
    rows = session.execute(text("""
        SELECT model_call_id, provider, model_identity, provider_mode, parameters, request_sha256,
               response_sha256, input_tokens, output_tokens, latency_ms, cost_micros, cost_basis, status
          FROM model_call
         WHERE run_id = :run AND parameters ->> 'extended_phase' = :phase
           AND parameters ->> 'flow_base_request_sha256' = :base
           AND parameters ->> 'extended_source_sha256' = :source
           AND (parameters ? 'extended_reply_blob_id' OR status IN ('succeeded', 'truncated'))
         ORDER BY created_at, model_call_id
    """), params).mappings().all()
    if len(rows) > 1:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="analysis.extended_reply")
    if rows:
        return dict(rows[0])
    ambiguous = session.execute(text("""
        SELECT 1 FROM provider_call_effect WHERE run_id = :run
          AND parameters ->> 'extended_phase' = :phase
          AND parameters ->> 'flow_base_request_sha256' = :base
          AND state <> 'not_processed' LIMIT 1
    """), params).first()
    if ambiguous is not None:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="extended_provider_outcome_unknown")
    return None


def extended_unit(session: Session, *, run_id: str, unit_key: str, source_sha256: str,
                  phase: str | None = None, replay_received_only: bool = False) -> dict | None:
    if phase is not None:
        changed = session.execute(text("""
            SELECT 1 FROM provider_call_effect WHERE run_id=:run
            AND parameters ->> 'extended_phase'=:phase
            AND parameters ->> 'extended_unit_key' IS DISTINCT FROM :unit
            AND state <> 'not_processed' LIMIT 1
        """), {"run": run_id, "phase": phase, "unit": unit_key}).scalar_one_or_none()
        if changed is not None:
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="extended_request_changed")
    different = session.execute(text("""
        SELECT 1 FROM provider_call_effect WHERE run_id=:run
        AND parameters ? 'extended_unit_key'
        AND parameters ->> 'extended_source_sha256' IS DISTINCT FROM :source LIMIT 1
    """), {"run": run_id, "source": source_sha256}).scalar_one_or_none()
    if different is not None:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="extended_source_changed")
    rows = session.execute(text("""
        SELECT model_call_id,provider,model_identity,provider_mode,parameters,request_sha256,
               response_sha256,input_tokens,output_tokens,latency_ms,cost_micros,cost_basis,status
        FROM model_call WHERE run_id=:run AND parameters ->> 'extended_unit_key'=:unit
        AND (NOT :received_only OR parameters ? 'extended_reply_blob_id' OR status IN ('succeeded', 'truncated'))
        ORDER BY created_at,model_call_id
    """), {"run": run_id, "unit": unit_key, "received_only": replay_received_only}).mappings().all()
    if len(rows) > 1:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="analysis.extended_reply")
    if rows:
        return dict(rows[0])
    ambiguous = session.execute(text("""
        SELECT 1 FROM provider_call_effect WHERE run_id=:run
        AND parameters ->> 'extended_unit_key'=:unit
        AND state NOT IN ('not_processed','abandoned') LIMIT 1
    """), {"run": run_id, "unit": unit_key}).scalar_one_or_none()
    if ambiguous is not None:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="extended_provider_outcome_unknown")
    # An abandoned effect retains its outcome ambiguity; abandonment is not proof
    # that a provider did no work. Only proven not_processed permits a new effect.
    abandoned = session.execute(text("""
        SELECT 1 FROM provider_call_effect WHERE run_id=:run
        AND parameters ->> 'extended_unit_key'=:unit AND state='abandoned' LIMIT 1
    """), {"run": run_id, "unit": unit_key}).scalar_one_or_none()
    if abandoned is not None:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, stage_id="text_analysis", reason="extended_provider_outcome_unknown")
    return None


def has_ambiguous_provider_effect(session: Session, *, run_id: str) -> bool:
    """An unfinished/abandoned effect anywhere in this Run forbids new paid work.

    A completed effect is cleared atomically by the existing call journal. An
    abandoned row preserves uncertainty; it is never proof of no provider spend.
    Callers may still read and reuse an already committed response before this
    guard, since reuse dispatches nothing.
    """
    return session.execute(text("""
        SELECT 1 FROM provider_call_effect
        WHERE run_id=:run AND state IN
          ('prepared','response_received','outcome_unknown','abandoned')
        LIMIT 1
    """), {"run": run_id}).scalar_one_or_none() is not None


# --- the replies of a restart (`RUN-RESTART-01`) ------------------------------------------------------------------------------------
#
# A restart run takes the model replies of the chips before the one it restarts from out of its source chain: the run it restarts, that run's
# own restart source and so on (``runs.restart.restart_chain``). A replay writes no ``model_call`` row, so the chain is walked to the run that
# made the call. Only a row that carries its reply blob and ended ``succeeded`` or ``truncated`` is a reply; a failed or unknown call is not one.
# The run's own rows are read first by ``extended_unit`` / ``extended_context_unit`` above; these read the ancestors, nearest first.

_CHAIN_COLUMNS = """model_call_id, provider, model_identity, provider_mode, parameters, request_sha256,
               response_sha256, input_tokens, output_tokens, latency_ms, cost_micros, cost_basis, status"""


def extended_unit_in_chain(session: Session, *, run_ids: Sequence[str], unit_key: str) -> dict | None:
    """The saved reply of the unit ``unit_key`` in the nearest run of ``run_ids`` (nearest first) that holds one, else ``None``.

    The unit key already binds the source digest, the phase, the request and the model, so a hit is the reply to exactly this question. Two replies
    of one run to one key would be a broken journal (``storage_integrity_error``), as in :func:`extended_unit`."""
    if not run_ids:
        return None
    rows = session.execute(text(f"""
        SELECT run_id, {_CHAIN_COLUMNS} FROM model_call
         WHERE run_id = ANY(:runs) AND parameters ->> 'extended_unit_key' = :unit
           AND parameters ? 'extended_reply_blob_id' AND status IN ('succeeded', 'truncated')
         ORDER BY array_position(CAST(:runs AS text[]), run_id), created_at, model_call_id
    """), {"runs": list(run_ids), "unit": unit_key}).mappings().all()
    if not rows:
        return None
    first = rows[0]["run_id"]
    if sum(1 for row in rows if row["run_id"] == first) > 1:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="analysis.extended_reply")
    return {key: value for key, value in dict(rows[0]).items() if key != "run_id"}


def extended_context_unit_in_chain(session: Session, *, run_ids: Sequence[str], phase: str, source_sha256: str,
                                   base_request_sha256: str) -> dict | None:
    """The context-bearing counterpart of :func:`extended_unit_in_chain`: the saved reply of ``phase`` asked on the base request ``base_request_sha256``
    over ``source_sha256``, in the nearest run of the chain that holds one (the critic's calls, whose human-reference block is attached after the base)."""
    if not run_ids:
        return None
    rows = session.execute(text(f"""
        SELECT run_id, {_CHAIN_COLUMNS} FROM model_call
         WHERE run_id = ANY(:runs) AND parameters ->> 'extended_phase' = :phase
           AND parameters ->> 'flow_base_request_sha256' = :base
           AND parameters ->> 'extended_source_sha256' = :source
           AND parameters ? 'extended_reply_blob_id' AND status IN ('succeeded', 'truncated')
         ORDER BY array_position(CAST(:runs AS text[]), run_id), created_at, model_call_id
    """), {"runs": list(run_ids), "phase": phase, "base": base_request_sha256, "source": source_sha256}).mappings().all()
    if not rows:
        return None
    first = rows[0]["run_id"]
    if sum(1 for row in rows if row["run_id"] == first) > 1:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="analysis.extended_reply")
    return {key: value for key, value in dict(rows[0]).items() if key != "run_id"}


def extended_phase_in_chain(session: Session, *, run_ids: Sequence[str], phase: str) -> bool:
    """Whether any run of the chain answered ``phase`` at all (for another request). Tells «a saved reply exists for another request» from «no saved
    reply»: the two refusals of a replay (`restart_request_changed`, `restart_reply_missing`)."""
    if not run_ids:
        return False
    return session.execute(text("""
        SELECT 1 FROM model_call
         WHERE run_id = ANY(:runs) AND parameters ->> 'extended_phase' = :phase
           AND parameters ? 'extended_reply_blob_id' AND status IN ('succeeded', 'truncated') LIMIT 1
    """), {"runs": list(run_ids), "phase": phase}).first() is not None
