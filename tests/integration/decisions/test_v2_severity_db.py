"""PostgreSQL proof that 0022's append-only ledger and view agree on severity."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.api.schemas.decisions import decision_event_body
from auditmanager.api.schemas.findings import finding_body
from auditmanager.bootstrap.adapters import _event_view, _finding_view
from auditmanager.decisions import (
    append_decision_under_key,
    current_verdict,
    decision_history,
    decision_journal,
    rebuild_current_verdict,
)
from auditmanager.findings.queries import (
    finding_by_uid,
    published_finding_evidence,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import FindingObservationId, FindingUid


def _key() -> str:
    return f"w56severity-{uuid.uuid4().hex[:20]}"


def _v2_target(session: Session, published):  # noqa: ANN201
    """Create a bounded schema-level v2 row until runtime publication exists."""
    finding_uid = FindingUid.new().value
    observation_id = FindingObservationId.new().value
    session.execute(
        text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, "
            "allocated_by_run_id, category) VALUES (:f, :p, :v, :r, 'layout')"
        ),
        {"f": finding_uid, "p": published.project_uid,
         "v": published.version_uid, "r": published.run_id},
    )
    quote = "Степень огнестойкости здания — II."
    session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, "
            "finding_uid, stage_id, category, finding_text, recommendation_text, "
            "grounded, analysis_profile_id, prompt_bundle_id, provider_mode, "
            "proposed_severity) VALUES (:o, :r, :f, 'text_analysis', 'layout', "
            "'Проверить согласованность планов.', 'Согласовать планы.', true, "
            ":ap, :pb, 'recorded', 'critical')"
        ),
        {"o": observation_id, "r": published.run_id, "f": finding_uid,
         "ap": published.analysis_profile_id, "pb": published.prompt_bundle_id},
    )
    session.execute(
        text(
            "UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"
        ),
        {"o": observation_id, "f": finding_uid},
    )
    session.execute(
        text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, "
            "page_number, quote, char_start, char_end) VALUES (:o, 0, 1, :q, 0, :end)"
        ),
        {"o": observation_id, "q": quote, "end": len(quote)},
    )
    return SimpleNamespace(finding_uid=finding_uid, finding_observation_id=observation_id)


def _append(session: Session, published, event_type: str,
            severity: str | None = None, comment: str | None = None):  # noqa: ANN201
    return append_decision_under_key(
        session,
        finding_uid=published.finding_uid,
        finding_observation_id=published.finding_observation_id,
        event_type=event_type,
        severity=severity,
        comment=comment,
        idempotency_key=_key(),
        author_label="Эксперт",
        author_user_uid=None,
    )[0]


def test_accept_comment_reject_and_reaccept_follow_0022_view(
    session: Session, published
) -> None:
    target = _v2_target(session, published)
    accept = _append(session, target, "accept", "critical")
    stored = session.execute(
        text("SELECT severity FROM expert_decision_event WHERE decision_id = :d"),
        {"d": accept.decision_id},
    ).scalar_one()
    assert stored == "critical"

    def projected():  # noqa: ANN202
        view = current_verdict(session, target.finding_uid)
        fold = rebuild_current_verdict(session, target.finding_uid)
        assert view is not None and fold is not None
        assert view.comparable() == fold.comparable()
        return view

    assert projected().decided_severity == "critical"
    comment = _append(session, target, "comment", comment="Проверено")
    assert projected().decided_severity == "critical"
    assert projected().latest_verdict_decision_id == accept.decision_id
    reject = _append(session, target, "reject")
    assert projected().decided_severity is None
    assert projected().latest_verdict_decision_id == reject.decision_id
    reaccept = _append(session, target, "accept", "economic")
    assert projected().decided_severity == "economic"

    history = decision_history(session, target.finding_uid)
    assert [event.severity for event in history] == ["critical", None, None, "economic"]
    assert [event.decision_id for event in history] == [
        accept.decision_id, comment.decision_id, reject.decision_id,
        reaccept.decision_id,
    ]
    journal = {entry.decision_id: entry for entry in decision_journal(session)}
    assert journal[accept.decision_id].severity == "critical"
    assert journal[reject.decision_id].severity is None

    row = finding_by_uid(session, target.finding_uid)
    assert row is not None
    evidence = published_finding_evidence(session, row.run_id)
    body = finding_body(_finding_view(row, evidence, projected()))
    assert body["decided_severity"] == "economic"
    assert decision_event_body(_event_view(accept))["severity"] == "critical"
    assert "severity" not in decision_event_body(_event_view(comment))


def test_idempotent_severity_replay_and_reuse(session: Session, published) -> None:
    target = _v2_target(session, published)
    key = _key()
    arguments = dict(
        finding_uid=target.finding_uid,
        finding_observation_id=target.finding_observation_id,
        event_type="accept", severity="operational", idempotency_key=key,
        author_label="Эксперт", author_user_uid=None,
    )
    first, replayed = append_decision_under_key(session, **arguments)
    assert replayed is False
    second, replayed = append_decision_under_key(session, **arguments)
    assert replayed is True
    assert second.decision_id == first.decision_id
    assert second.severity == "operational"

    with pytest.raises(DomainError) as caught:
        append_decision_under_key(session, **{**arguments, "severity": "economic"})
    assert caught.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert len(decision_history(session, target.finding_uid)) == 1


def test_legacy_unset_severity_is_absent_on_wire(session: Session, published) -> None:
    with pytest.raises(DomainError) as caught:
        _append(session, published, "accept", "critical")
    assert caught.value.code is ErrorCode.VALIDATION_FAILED
    assert decision_history(session, published.finding_uid) == ()

    event = _append(session, published, "accept")
    assert event.severity is None
    assert "severity" not in decision_event_body(_event_view(event))
    assert "severity" not in decision_event_body(
        _event_view(decision_history(session, published.finding_uid)[0])
    )
    assert current_verdict(session, published.finding_uid).decided_severity is None
    row = finding_by_uid(session, published.finding_uid)
    assert row is not None
    evidence = published_finding_evidence(session, row.run_id)
    body = finding_body(
        _finding_view(row, evidence, current_verdict(session, published.finding_uid))
    )
    assert "decided_severity" not in body
