"""Both active v1 and recorded v2 stamp the resealed text stage identity."""

from __future__ import annotations

from datetime import datetime, timezone

from auditmanager.analysis.engine.registry import default_registry
from auditmanager.analysis.public import TEXT_STAGE_VERSION
from auditmanager.analysis.text.artifact import ARTIFACT_VERSION
from auditmanager.analysis.text.stage import STAGE_VERSION, TextAnalysisOutcome
from auditmanager.runs.executor import _text_stage_result
from auditmanager.shared.errors import DomainError, ErrorCode


class _NoAttempts:
    def metrics(self) -> dict[str, int]:
        return {}


def test_v1_executor_result_matches_the_1_1_registry_without_changing_artifact_version() -> None:
    definition = default_registry().stage('text_analysis')
    assert definition.stage_version == STAGE_VERSION == TEXT_STAGE_VERSION == '1.1.0'
    assert ARTIFACT_VERSION == '1.0.0'
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    outcome = TextAnalysisOutcome(
        status='failed', artifact=None, model_calls=(),
        error=DomainError(ErrorCode.ANALYSIS_FAILED, stage_id='text_analysis'),
        metrics={'stage_id': 'text_analysis', 'stage_version': STAGE_VERSION},
    )
    result = _text_stage_result(
        outcome, artifact_ref=None, attempts=_NoAttempts(), started=now, finished=now,
    )
    assert result.stage_version == definition.stage_version
    assert result.metrics['stage_version'] == definition.stage_version
