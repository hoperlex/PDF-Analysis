"""Widen the stored-error vocabulary with the two run-routing refusal codes.

Revision ID: 0029_routing_refusal_codes
Revises: 0028_classification_corrections

`BETA-CONTRACT-SEAL-01` phase A (`D-179`). ``startRun`` and ``reauditRun`` refuse a version no
expert has classified and a confirmed section no text profile serves. Until this revision both
refusals reused ``required_norm_unavailable`` and told themselves apart by
``details.reference_kind``; the error catalogue now gives each its own code,
``version_classification_required`` and ``section_profile_unavailable``.

What this revision does
-----------------------
It replaces the four ``CHECK`` constraints that hold the catalogue's stored vocabulary --
``command_record.error_code``, ``audit_run.terminal_reason``, ``model_call.error_code`` and
``provider_call_effect.error_code`` -- with the twenty-five codes the catalogue stores. A
column list and a table are unchanged and no row is rewritten; ``rate_limited`` and
``analysis_input_budget_exceeded`` stay outside the vocabulary, as before (the edge answers the
first, the second is refused before any run exists).

Both new refusals also precede the idempotency key's claim and write nothing today, so no row
carries them when this revision is applied. The vocabulary admits them anyway: the catalogue is
the one list of codes, the stored side is derived from it, and a later path that records one
(a worker re-routing a queued re-audit, say) must not need a second widening.

The vocabulary is restated, not imported: a migration is history and must not move when the
application does. ``tests/contract/domain_p02/test_contract_vocabulary.py`` holds this tuple
equal to the catalogue minus the edge-only codes.

Downgrade
---------
Refuses while any of the four columns holds one of the two new codes: narrowing the
``CHECK`` under such a row would either fail half-way or hide the row from the vocabulary
that validates it. With no such row it restores ``0022``'s constraints exactly.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0029_routing_refusal_codes"
down_revision: str | None = "0028_classification_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The stored vocabulary ``0022_findings_v2`` left behind (twenty-three codes).
_OLD_ERROR_CODES = (
    "validation_failed", "not_found", "authentication_required", "permission_denied",
    "conflict", "state_transition_not_allowed", "idempotency_key_reuse",
    "idempotency_key_in_progress", "idempotency_key_stale",
    "unsupported_contract_version", "storage_integrity_error", "dependency_unavailable",
    "dependency_credential_refused", "staged_upload_lost", "required_norm_unavailable",
    "analysis_input_invalid", "analysis_failed", "partial_result_not_publishable",
    "cost_budget_exceeded", "stale_attempt", "execution_token_invalid", "internal_error",
    "model_identity_mismatch",
)
#: The two codes this revision admits.
_ADDED_ERROR_CODES = ("version_classification_required", "section_profile_unavailable")
_NEW_ERROR_CODES = (*_OLD_ERROR_CODES, *_ADDED_ERROR_CODES)

#: ``(table, column, constraint)`` -- the four places the vocabulary is enforced.
_CHECKS = (
    ("command_record", "error_code", "ck_command_record_error_code"),
    ("audit_run", "terminal_reason", "ck_audit_run_terminal_reason"),
    ("model_call", "error_code", "ck_model_call_error_code"),
    ("provider_call_effect", "error_code", "ck_provider_effect_error_code"),
)


def _sql_values(values: tuple[str, ...]) -> str:
    """Quote only fixed, source-controlled enum literals, never database input."""
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _error_checks(values: tuple[str, ...]) -> None:
    allowed = _sql_values(values)
    for table, column, name in _CHECKS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} "
            f"CHECK ({column} IS NULL OR {column} IN ({allowed}))"
        )


def upgrade() -> None:
    _error_checks(_NEW_ERROR_CODES)


def downgrade() -> None:
    added = _sql_values(_ADDED_ERROR_CODES)
    selects = " UNION ALL ".join(
        f"SELECT 1 FROM {table} WHERE {column} IN ({added})" for table, column, _ in _CHECKS
    )
    retained = op.get_bind().execute(text(f"SELECT EXISTS ({selects})")).scalar_one()
    if retained:
        raise RuntimeError(
            "0029 downgrade refused: a stored error or terminal reason carries "
            "version_classification_required or section_profile_unavailable"
        )
    _error_checks(_OLD_ERROR_CODES)
