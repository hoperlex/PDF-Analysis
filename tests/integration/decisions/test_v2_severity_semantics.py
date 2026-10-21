"""Offline checks for the severity ledger, fold, fingerprint and wire mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from auditmanager.api.schemas.decisions import decision_event_body, decision_record_body
from auditmanager.api.schemas.findings import finding_body
from auditmanager.bootstrap.adapters import _event_view, _finding_view, _record_view
from auditmanager.decisions import ledger, projection
from auditmanager.ingest import public as ingest_public
from auditmanager.shared.errors import DomainError, ErrorCode


class _Rows:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> _Rows:
        return self

    def first(self):  # noqa: ANN201 - test double for SQLAlchemy Result
        return self.rows[0] if self.rows else None

    def __iter__(self):  # noqa: ANN204 - test double for SQLAlchemy Result
        return iter(self.rows)


class _FoldSession:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def execute(self, statement, _parameters):  # noqa: ANN001, ANN201
        sql = str(statement)
        if "SELECT 1 FROM finding" in sql:
            return _Rows([{"found": 1}])
        if "FROM expert_decision_event" in sql:
            return _Rows(self.rows)
        raise AssertionError(sql)


def _row(decision_id: str, event_type: str, verdict: str | None,
         severity: str | None = None, comment: str | None = None) -> dict:
    return {
        "decision_id": decision_id,
        "event_type": event_type,
        "verdict": verdict,
        "severity": severity,
        "comment": comment,
        "recorded_at": datetime(2026, 10, 15, tzinfo=timezone.utc),
    }


def test_fold_uses_last_verdict_and_comment_preserves_severity() -> None:
    rows = [_row("d1", "accept", "accepted", "critical")]
    first = projection.rebuild_current_verdict(_FoldSession(rows), "f1")
    assert first is not None
    assert first.current_verdict == "accepted"
    assert first.decided_severity == "critical"

    rows.append(_row("d2", "comment", None, comment="Исправлено"))
    after_comment = projection.rebuild_current_verdict(_FoldSession(rows), "f1")
    assert after_comment is not None
    assert after_comment.decided_severity == "critical"
    assert after_comment.latest_decision_id == "d2"
    assert after_comment.latest_verdict_decision_id == "d1"

    rows.append(_row("d3", "reject", "rejected"))
    after_reject = projection.rebuild_current_verdict(_FoldSession(rows), "f1")
    assert after_reject is not None
    assert after_reject.current_verdict == "rejected"
    assert after_reject.decided_severity is None

    rows.append(_row("d4", "accept", "accepted", "economic"))
    after_new_accept = projection.rebuild_current_verdict(_FoldSession(rows), "f1")
    assert after_new_accept is not None
    assert after_new_accept.decided_severity == "economic"

    rows.append(_row("d5", "revoke", "pending"))
    after_revoke = projection.rebuild_current_verdict(_FoldSession(rows), "f1")
    assert after_revoke is not None
    assert after_revoke.current_verdict == "pending"
    assert after_revoke.decided_severity is None


@pytest.mark.parametrize("event_type", ["reject", "comment", "revoke"])
def test_non_accept_severity_is_refused_before_command_claim(
    monkeypatch: pytest.MonkeyPatch, event_type: str
) -> None:
    claims = Mock()
    monkeypatch.setattr(ingest_public, "CommandRepository", lambda: claims)
    with pytest.raises(DomainError) as caught:
        ledger.append_decision_under_key(
            Mock(), finding_uid="f1", finding_observation_id="o1",
            event_type=event_type, severity="critical", idempotency_key="one",
            author_label="Эксперт", author_user_uid=None,
        )
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    claims.begin.assert_not_called()


def test_legacy_target_cannot_receive_decided_severity_before_command_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claims = Mock()
    monkeypatch.setattr(ingest_public, "CommandRepository", lambda: claims)
    session = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = False
    with pytest.raises(DomainError) as caught:
        ledger.append_decision_under_key(
            session, finding_uid="f1", finding_observation_id="o1",
            event_type="accept", severity="critical", idempotency_key="one",
            author_label="Эксперт", author_user_uid=None,
        )
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    claims.begin.assert_not_called()


def test_optional_severity_changes_fingerprint_only_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads: list[dict] = []
    real_fingerprint = ingest_public.payload_fingerprint

    def fingerprint(payload: dict):  # noqa: ANN201
        payloads.append(dict(payload))
        return real_fingerprint(payload)

    class Repository:
        def begin(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN201
            return SimpleNamespace(command_id="cmd_01")

        def succeed(self, *_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
            pass

    monkeypatch.setattr(ingest_public, "payload_fingerprint", fingerprint)
    monkeypatch.setattr(ingest_public, "CommandRepository", Repository)
    recorded: list[str | None] = []

    def record(_session, **kwargs):  # noqa: ANN001, ANN003, ANN201
        recorded.append(kwargs["severity"])
        return SimpleNamespace(decision_id="dec_01")

    monkeypatch.setattr(ledger, "record_decision", record)
    for severity in (None, "critical"):
        ledger.append_decision_under_key(
            Mock(), finding_uid="f1", finding_observation_id="o1",
            event_type="accept", severity=severity, idempotency_key="one",
            author_label="Эксперт", author_user_uid=None,
        )

    assert "severity" not in payloads[0]
    assert payloads[1]["severity"] == "critical"
    assert real_fingerprint(payloads[0]) != real_fingerprint(payloads[1])
    assert recorded == [None, "critical"]


def test_event_record_and_finding_wire_omit_absent_severity() -> None:
    now = datetime(2026, 10, 15, tzinfo=timezone.utc)
    event = SimpleNamespace(
        decision_id="d1", finding_uid="f1", finding_observation_id="o1",
        event_type="accept", author_label="Эксперт", recorded_at=now,
        verdict="accepted", comment=None, severity="critical",
    )
    event_body = decision_event_body(_event_view(event))
    assert event_body["severity"] == "critical"
    event.severity = None
    assert "severity" not in decision_event_body(_event_view(event))

    record = SimpleNamespace(
        **vars(event), project_uid="p1", run_id="r1", category="layout",
        finding_text="Текст", current_verdict="accepted", decision_event_count=1,
    )
    assert "severity" not in decision_record_body(_record_view(record))
    record.severity = "operational"
    assert decision_record_body(_record_view(record))["severity"] == "operational"

    finding = SimpleNamespace(
        finding_uid="f1", project_uid="p1", version_uid="v1", run_id="r1",
        category="layout", finding_observation_id="o1", finding_text="Текст",
        recommendation_text="Проверить", stage_id="text_analysis",
        analysis_profile_id="ap1", prompt_bundle_id="pb1", provider_mode="recorded",
        model_call_id=None,
    )
    verdict = SimpleNamespace(current_verdict="accepted", decided_severity="critical")
    assert finding_body(_finding_view(finding, (), verdict))["decided_severity"] == "critical"
    verdict.decided_severity = None
    assert "decided_severity" not in finding_body(_finding_view(finding, (), verdict))
