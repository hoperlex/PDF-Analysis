"""Builders for the precedent-core tests: plain values with defaults that satisfy every rule, so a test changes the one fact it is about."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from auditmanager.precedents.advice import PrecedentAdvice, evaluate
from auditmanager.precedents.models import (
    CaseComment,
    CriticCandidate,
    DecisionEvent,
    FindingContext,
    PrecedentCase,
    ScoredCase,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ACCEPTED = "accepted"
REJECTED = "rejected"


def ago(days: float, base: datetime = NOW) -> datetime:
    return base - timedelta(days=days)


def case(
    case_id: str,
    verdict: str | None = REJECTED,
    *,
    days_ago: float = 30,
    section: str | None = "S1",
    data_class: str = "real",
    project: str = "p1",
    document: str | None = None,
    version: str | None = None,
    run: str | None = None,
    active: bool = True,
    origin: str = "direct",
    label: str | None = None,
    history: str | None = None,
    comments: tuple[CaseComment, ...] = (),
    decisions: tuple[DecisionEvent, ...] | None = None,
) -> PrecedentCase:
    """A case with one decision (or the ``decisions`` given). Each case gets its own document, version and run unless told otherwise."""
    if decisions is None:
        decisions = (DecisionEvent(verdict, ago(days_ago), origin, label, history),)
    return PrecedentCase(
        case_id=case_id,
        section=section,
        data_class=data_class,
        project_uid=project,
        document_uid=document or f"doc-{case_id}",
        version_uid=version or f"ver-{case_id}",
        run_id=run or f"run-{case_id}",
        active=active,
        decisions=decisions,
        comments=comments,
    )


def scored(c: PrecedentCase, cosine: float = 0.90) -> ScoredCase:
    return ScoredCase(c, cosine)


def finding(**overrides: object) -> FindingContext:
    values: dict[str, object] = {
        "finding_uid": "f-1",
        "section": "S1",
        "data_class": "real",
        "run_id": "run-F",
        "document_uid": "doc-F",
        "version_uid": "ver-F",
        "finding_text": "Толщина защитного слоя не соответствует проекту.",
        "recommendation_text": "Уточнить у проектировщика.",
        "primary_source_id": "primary_text_k1",
    }
    values.update(overrides)
    return FindingContext(**values)  # type: ignore[arg-type]


def critic(decision: str | None = "reject", *, candidate_id: str = "cand-1", sources: tuple[str, ...] = ("primary_text_k1",)) -> CriticCandidate:
    return CriticCandidate(candidate_id=candidate_id, source_ids=sources, decision=decision)


def corpus(rejected: int, accepted: int = 0, *, projects: int = 2, prefix: str = "c", cosine: float = 0.90) -> list[ScoredCase]:
    """Independent voters: ``rejected`` rejections and ``accepted`` acceptances, spread over ``projects`` projects, rejections older first."""
    items: list[ScoredCase] = []
    for index in range(rejected):
        items.append(scored(case(f"{prefix}r{index:02d}", REJECTED, days_ago=200 - index, project=f"p{index % projects}"), cosine))
    for index in range(accepted):
        items.append(scored(case(f"{prefix}a{index:02d}", ACCEPTED, days_ago=300 - index, project=f"p{index % projects}"), cosine))
    return items


def advise(
    items: Sequence[ScoredCase] | None,
    candidates: Sequence[CriticCandidate] = (),
    *,
    f: FindingContext | None = None,
    critic_in_plan: bool = True,
    **kwargs: object,
) -> PrecedentAdvice:
    """``evaluate`` at ``NOW`` for the default finding, with a critic in the plan unless a test says otherwise."""
    return evaluate(f or finding(), items, candidates, now=NOW, critic_in_plan=critic_in_plan, **kwargs)  # type: ignore[arg-type]
