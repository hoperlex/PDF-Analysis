"""Durable paid-effect fence for bounded extended-review units; no new tables."""
from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.orm import Session
from auditmanager.shared.errors import DomainError, ErrorCode


def extended_unit(session: Session, *, run_id: str, unit_key: str, source_sha256: str,
                  phase: str | None = None) -> dict | None:
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
        ORDER BY created_at,model_call_id
    """), {"run": run_id, "unit": unit_key}).mappings().all()
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
