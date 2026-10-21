"""Add the recorded-only AR v2 finding vocabulary and canonical observation.

Revision ID: 0022_findings_v2
Revises: 0021_portal_bundles

This migration does not activate a provider or select a model. New columns are
nullable so v1 publications and decisions keep their existing wire shape.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0022_findings_v2"
down_revision: str | None = "0021_portal_bundles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CATEGORIES = ("internal_contradiction", "explicit_placeholder")
_NEW_CATEGORIES = (*_OLD_CATEGORIES, "dimensions", "layout", "facade", "roof", "documentation")
_SEVERITIES = ("critical", "economic", "operational", "recommendation", "check_adjacent")
_OLD_REASONS = (
    "quotation_absent",
    "quotation_on_different_page",
    "span_outside_page",
    "span_outside_block",
    "span_length_mismatch",
)
_NEW_REASONS = (*_OLD_REASONS, "quote_in_recognised_text")
_OLD_ERROR_CODES = (
    "validation_failed", "not_found", "authentication_required", "permission_denied",
    "conflict", "state_transition_not_allowed", "idempotency_key_reuse",
    "idempotency_key_in_progress", "idempotency_key_stale",
    "unsupported_contract_version", "storage_integrity_error", "dependency_unavailable",
    "dependency_credential_refused", "staged_upload_lost", "required_norm_unavailable",
    "analysis_input_invalid", "analysis_failed", "partial_result_not_publishable",
    "cost_budget_exceeded", "stale_attempt", "execution_token_invalid", "internal_error",
)
_NEW_ERROR_CODES = (*_OLD_ERROR_CODES, "model_identity_mismatch")


def _sql_values(values: tuple[str, ...]) -> str:
    """Quote only fixed, source-controlled enum literals, never database input."""
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _replace_check(table: str, name: str, expression: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})")


def _current_verdict_view(*, with_severity: bool) -> None:
    # Preserve the existing column order; PostgreSQL allows an added final
    # column through CREATE OR REPLACE VIEW without dropping dependent readers.
    added = (
        ", CASE WHEN v.event_type = 'accept' THEN v.severity ELSE NULL END "
        "AS decided_severity"
        if with_severity else ""
    )
    select = "e.decision_id, e.verdict, e.recorded_at"
    if with_severity:
        select += ", e.event_type, e.severity"
    op.execute(
        f"""
        CREATE OR REPLACE VIEW finding_current_verdict AS
        SELECT f.finding_uid,
               COALESCE(v.verdict, 'pending') AS current_verdict,
               v.decision_id AS latest_verdict_decision_id,
               v.recorded_at AS latest_verdict_recorded_at,
               c.comment AS latest_comment,
               c.decision_id AS latest_comment_decision_id,
               l.decision_id AS latest_decision_id,
               l.recorded_at AS decision_recorded_at,
               COALESCE(n.event_count, 0) AS decision_event_count
               {added}
        FROM finding f
        LEFT JOIN LATERAL (
            SELECT {select}
            FROM expert_decision_event e
            WHERE e.finding_uid = f.finding_uid AND e.verdict IS NOT NULL
            ORDER BY e.sequence_no DESC LIMIT 1
        ) v ON TRUE
        LEFT JOIN LATERAL (
            SELECT e.decision_id, e.comment
            FROM expert_decision_event e
            WHERE e.finding_uid = f.finding_uid AND e.comment IS NOT NULL
            ORDER BY e.sequence_no DESC LIMIT 1
        ) c ON TRUE
        LEFT JOIN LATERAL (
            SELECT e.decision_id, e.recorded_at
            FROM expert_decision_event e
            WHERE e.finding_uid = f.finding_uid
            ORDER BY e.sequence_no DESC LIMIT 1
        ) l ON TRUE
        LEFT JOIN LATERAL (
            SELECT count(*) AS event_count
            FROM expert_decision_event e
            WHERE e.finding_uid = f.finding_uid
        ) n ON TRUE
        """
    )


def _error_checks(values: tuple[str, ...]) -> None:
    allowed = _sql_values(values)
    for table, name, expression in (
        ("command_record", "ck_command_record_error_code", f"error_code IS NULL OR error_code IN ({allowed})"),
        ("audit_run", "ck_audit_run_terminal_reason", f"terminal_reason IS NULL OR terminal_reason IN ({allowed})"),
        ("model_call", "ck_model_call_error_code", f"error_code IS NULL OR error_code IN ({allowed})"),
        ("provider_call_effect", "ck_provider_effect_error_code", f"error_code IS NULL OR error_code IN ({allowed})"),
    ):
        _replace_check(table, name, expression)


def upgrade() -> None:
    categories = _sql_values(_NEW_CATEGORIES)
    _replace_check("finding", "ck_finding_category", f"category IN ({categories})")
    _replace_check("finding_observation", "ck_finding_observation_category", f"category IN ({categories})")
    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_sql_values(_NEW_REASONS)})",
    )

    severities = _sql_values(_SEVERITIES)
    op.execute("ALTER TABLE finding_observation ADD COLUMN proposed_severity text NULL")
    op.execute(
        "ALTER TABLE finding_observation ADD CONSTRAINT ck_finding_observation_proposed_severity "
        f"CHECK (proposed_severity IS NULL OR proposed_severity IN ({severities}))"
    )
    op.execute("ALTER TABLE expert_decision_event ADD COLUMN severity text NULL")
    op.execute(
        "ALTER TABLE expert_decision_event ADD CONSTRAINT ck_expert_decision_event_severity "
        f"CHECK (severity IS NULL OR severity IN ({severities}))"
    )
    op.execute(
        "ALTER TABLE expert_decision_event ADD CONSTRAINT ck_expert_decision_event_severity_accept_only "
        "CHECK (severity IS NULL OR event_type = 'accept')"
    )

    op.execute("ALTER TABLE finding ADD COLUMN canonical_observation_id text NULL")
    op.execute(
        "ALTER TABLE finding_observation ADD CONSTRAINT uq_finding_observation_finding_id "
        "UNIQUE (finding_uid, finding_observation_id)"
    )
    # An existing finding must have exactly one grounded observation. This
    # assertion detects corrupt legacy rows instead of picking an arbitrary ID.
    connection = op.get_bind()
    bad = connection.execute(
        text(
            "SELECT f.finding_uid FROM finding f "
            "LEFT JOIN finding_observation o ON o.finding_uid = f.finding_uid "
            "GROUP BY f.finding_uid HAVING count(o.finding_observation_id) <> 1 LIMIT 1"
        )
    ).scalar_one_or_none()
    if bad is not None:
        raise RuntimeError("0022 backfill refused: finding without exactly one grounded observation")
    op.execute(
        "UPDATE finding f SET canonical_observation_id = o.finding_observation_id "
        "FROM finding_observation o WHERE o.finding_uid = f.finding_uid"
    )
    op.execute(
        "ALTER TABLE finding ADD CONSTRAINT fk_finding_canonical_observation "
        "FOREIGN KEY (finding_uid, canonical_observation_id) "
        "REFERENCES finding_observation (finding_uid, finding_observation_id)"
    )
    _current_verdict_view(with_severity=True)
    _error_checks(_NEW_ERROR_CODES)


def _downgrade_verdict_view() -> None:
    """Give ``finding_current_verdict`` back its nine ``0021`` columns.

    ``CREATE OR REPLACE VIEW`` can append columns (the upgrade relies on that) but can never
    remove one: PostgreSQL stops with ``cannot drop columns from view``, so the first
    downgrade through this revision failed. The view is dropped and created again in its
    ``0021`` shape by the same helper the upgrade uses. The drop has no ``CASCADE``: a reader
    that came to depend on the view stops the downgrade instead of being dropped with it.
    A drop also discards the view's comment (``0002``'s, which ``CREATE OR REPLACE`` kept on
    the way up), so the comment is read from the catalog first and set again afterwards.
    """
    connection = op.get_bind()
    restore = connection.execute(
        text(
            "SELECT format('COMMENT ON VIEW finding_current_verdict IS %L', "
            "obj_description('finding_current_verdict'::regclass, 'pg_class'))"
        )
    ).scalar_one()
    op.execute("DROP VIEW finding_current_verdict")
    _current_verdict_view(with_severity=False)
    # ``\:`` keeps a colon inside the comment from being read as a bind parameter.
    op.execute(text(restore.replace(":", "\\:")))


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM finding UNION ALL "
            "SELECT 1 FROM finding_observation UNION ALL "
            "SELECT 1 FROM expert_decision_event UNION ALL "
            "SELECT 1 FROM command_record WHERE error_code = 'model_identity_mismatch' UNION ALL "
            "SELECT 1 FROM audit_run WHERE terminal_reason = 'model_identity_mismatch' UNION ALL "
            "SELECT 1 FROM model_call WHERE error_code = 'model_identity_mismatch' UNION ALL "
            "SELECT 1 FROM provider_call_effect WHERE error_code = 'model_identity_mismatch')"
        )
    ).scalar_one()
    if retained:
        raise RuntimeError("0022 downgrade refused: retained finding, decision or v2 error data")

    _error_checks(_OLD_ERROR_CODES)
    _downgrade_verdict_view()
    op.execute("ALTER TABLE finding DROP CONSTRAINT fk_finding_canonical_observation")
    op.execute("ALTER TABLE finding DROP COLUMN canonical_observation_id")
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT uq_finding_observation_finding_id")
    op.execute("ALTER TABLE expert_decision_event DROP CONSTRAINT ck_expert_decision_event_severity_accept_only")
    op.execute("ALTER TABLE expert_decision_event DROP CONSTRAINT ck_expert_decision_event_severity")
    op.execute("ALTER TABLE expert_decision_event DROP COLUMN severity")
    op.execute("ALTER TABLE finding_observation DROP CONSTRAINT ck_finding_observation_proposed_severity")
    op.execute("ALTER TABLE finding_observation DROP COLUMN proposed_severity")
    _replace_check(
        "finding_observation", "ck_finding_observation_ungrounded_reason",
        f"ungrounded_reason IS NULL OR ungrounded_reason IN ({_sql_values(_OLD_REASONS)})",
    )
    categories = _sql_values(_OLD_CATEGORIES)
    _replace_check("finding_observation", "ck_finding_observation_category", f"category IN ({categories})")
    _replace_check("finding", "ck_finding_category", f"category IN ({categories})")
