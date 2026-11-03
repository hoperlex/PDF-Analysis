"""`UI-PARITY-P0A`: ``getDashboardSummary`` restricted to one project, by the definitions it already has.

The header of the product names the project the expert works in. With ``project_uid`` every one of the four
panels -- ``documents_by_project``, ``findings_by_verdict``, ``run_activity`` (with its ``spend``) and
``section_breakdown`` -- is that project's, and the numbers are the whole deployment's minus the rows of every other
project. Nothing is defined twice: the scoped statement is the unscoped one with one predicate.

The database is a **fresh clone** of the migrated template (the fixtures of ``test_section_breakdown``), so every
number below is absolute and not a delta. Three projects are seeded with figures that differ in every panel, which is
what makes a filter that is applied to the wrong column (or not applied) show: a scoped read that returned the
deployment, or another project's figures, fails on a number that is not its own.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.dashboard.repository import (
    PROJECT_SECTIONS,
    RUN_STATES,
    VERDICTS,
    DashboardRepository,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    FindingObservationId,
    FindingUid,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
)
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import Seeder

dashboard = DashboardRepository()

#: Edges ``contract_state_transition`` declares; a run is walked along them and never written at its target.
_PATH = {
    "published": ("queued", "running", "validating", "published"),
    "running": ("queued", "running"),
    "failed": ("queued", "running", "validating", "failed"),
}
_TERMINAL = {"published", "failed"}


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _run(session: Session, project_uid: str, version_uid: str, tag: str, state: str) -> str:
    run_id = str(RunId.new())
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
            "prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
        ),
        {
            "r": run_id,
            "p": project_uid,
            "v": version_uid,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
            "s": _digest(f"{tag}-{run_id}"),
        },
    )
    for step in _PATH[state]:
        session.execute(
            text(
                "UPDATE audit_run SET state = :s, "
                "terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
                "terminal_reason = CASE WHEN :s = 'failed' THEN 'analysis_failed' ELSE NULL END, "
                "degradation_set = CASE WHEN :s = 'published' THEN '[]'::jsonb ELSE degradation_set END "
                "WHERE run_id = :r"
            ),
            {"s": step, "t": step in _TERMINAL, "r": run_id},
        )
    return run_id


def _finding(session: Session, project_uid: str, version_uid: str, run_id: str, verdict: str) -> None:
    """One finding at ``pending``, ``accepted`` or ``rejected`` (the two decided ones need an event)."""
    finding_uid = str(FindingUid.new())
    observation_id = str(FindingObservationId.new())
    session.execute(
        text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
            "VALUES (:f, :p, :v, :r, 'internal_contradiction')"
        ),
        {"f": finding_uid, "p": project_uid, "v": version_uid, "r": run_id},
    )
    if verdict == "pending":
        return
    session.execute(
        text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, "
            "finding_text, recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
            "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', 'text', 'recommendation', true, "
            ":ap, :pb, 'recorded')"
        ),
        {
            "o": observation_id,
            "r": run_id,
            "f": finding_uid,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
        },
    )
    session.execute(
        text(
            "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, "
            "verdict, author_label) VALUES (:d, :f, :o, :et, :v, 'project-scope suite')"
        ),
        {
            "d": str(DecisionId.new()),
            "f": finding_uid,
            "o": observation_id,
            "et": {"accepted": "accept", "rejected": "reject"}[verdict],
            "v": verdict,
        },
    )


def _model_call(session: Session, run_id: str, cost_micros: int) -> None:
    session.execute(
        text(
            "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, model_identity, provider_mode, "
            "request_sha256, response_sha256, cost_micros, cost_basis, status) "
            "VALUES (:m, :r, 'text_analysis', 'anthropic', 'claude-scope-suite', 'recorded', :q, :a, :c, "
            "'measured', 'succeeded')"
        ),
        {
            "m": str(ModelCallId.new()),
            "r": run_id,
            "q": _digest(f"q-{run_id}-{cost_micros}"),
            "a": _digest(f"a-{run_id}-{cost_micros}"),
            "c": cost_micros,
        },
    )


@dataclass(frozen=True)
class World:
    school: str
    clinic: str
    empty: str


@pytest.fixture
def world(session: Session) -> World:
    """Three projects whose figures differ in every panel.

    * ``school``: 3 sets (AR, AR, KJ); a published and a running run; findings pending x2 and accepted x1;
      two calls, 100 + 200 micros.
    * ``clinic``: 2 sets (PS, one unclassified); one failed run; one rejected finding; one call, 5000 micros.
    * ``empty``: nothing at all.
    """
    seed = Seeder(session)
    school, clinic, empty = seed.project("Школа"), seed.project("Поликлиника"), seed.project("Пустой")
    ar_one = seed.version(seed.document(school, "АР-1"), classified=("R", "AR"))
    seed.version(seed.document(school, "АР-2"), classified=("R", "AR"))
    seed.version(seed.document(school, "КЖ"), classified=("R", "KJ"))
    clinic_ps = seed.version(seed.document(clinic, "ПЗ"), classified=("P", "PS"))
    seed.version(seed.document(clinic, "Без раздела"))

    published = _run(session, school, ar_one, "school-published", "published")
    _run(session, school, ar_one, "school-running", "running")
    for verdict in ("pending", "pending", "accepted"):
        _finding(session, school, ar_one, published, verdict)
    _model_call(session, published, 100)
    _model_call(session, published, 200)

    failed = _run(session, clinic, clinic_ps, "clinic-failed", "failed")
    _finding(session, clinic, clinic_ps, failed, "rejected")
    _model_call(session, failed, 5000)
    session.commit()
    return World(school=school, clinic=clinic, empty=empty)


def _verdicts(summary) -> dict[str, int]:
    return {row.verdict: row.count for row in summary.findings_by_verdict}


def _states(summary) -> dict[str, int]:
    return {row.state: row.count for row in summary.run_activity}


def _sections(summary) -> dict[str | None, int]:
    return {row.section: row.document_count for row in summary.section_breakdown}


def _spend(summary) -> tuple[int, int, str] | None:
    spend = summary.run_spend
    return None if spend is None else (spend.model_call_count, spend.cost_micros, spend.basis)


def test_the_school_panels_are_the_schools_and_only_the_schools(session: Session, world: World) -> None:
    summary = dashboard.summary(session, project_uid=world.school)
    assert [(r.project_uid, r.name, r.document_count) for r in summary.documents_by_project] == [
        (world.school, "Школа", 3)
    ]
    assert _verdicts(summary) == {"pending": 2, "accepted": 1, "rejected": 0, "needs_manual_review": 0}
    assert _states(summary) == {**{s: 0 for s in RUN_STATES}, "published": 1, "running": 1}
    assert _spend(summary) == (2, 300, "measured")
    assert _sections(summary) == {**{s: 0 for s in (*PROJECT_SECTIONS, None)}, "AR": 2, "KJ": 1}


def test_the_clinic_panels_are_the_clinics_with_its_own_unclassified_row(
    session: Session, world: World
) -> None:
    summary = dashboard.summary(session, project_uid=world.clinic)
    assert [(r.project_uid, r.document_count) for r in summary.documents_by_project] == [(world.clinic, 2)]
    assert _verdicts(summary) == {"pending": 0, "accepted": 0, "rejected": 1, "needs_manual_review": 0}
    assert _states(summary) == {**{s: 0 for s in RUN_STATES}, "failed": 1}
    assert _spend(summary) == (1, 5000, "measured")
    assert _sections(summary) == {**{s: 0 for s in (*PROJECT_SECTIONS, None)}, "PS": 1, None: 1}


def test_a_project_with_nothing_is_a_row_at_zero_in_every_panel_and_has_no_spend(
    session: Session, world: World
) -> None:
    """Absent is not empty, and "nothing spent" is an absent ``spend``, never a zero labelled ``measured``."""
    summary = dashboard.summary(session, project_uid=world.empty)
    assert [(r.project_uid, r.document_count) for r in summary.documents_by_project] == [(world.empty, 0)]
    assert set(_verdicts(summary)) == set(VERDICTS) and set(_verdicts(summary).values()) == {0}
    assert set(_states(summary)) == set(RUN_STATES) and set(_states(summary).values()) == {0}
    assert summary.run_spend is None
    assert list(_sections(summary)) == [*PROJECT_SECTIONS, None] and set(_sections(summary).values()) == {0}


def test_without_a_project_the_panels_are_the_whole_deployment_and_equal_the_sum_of_the_scoped_ones(
    session: Session, world: World
) -> None:
    whole = dashboard.summary(session)
    parts = [dashboard.summary(session, project_uid=p) for p in (world.school, world.clinic, world.empty)]
    assert dashboard.summary(session, project_uid=None) == whole, "the parameter's absence is the old behaviour"
    assert {r.project_uid: r.document_count for r in whole.documents_by_project} == {
        world.school: 3,
        world.clinic: 2,
        world.empty: 0,
    }
    for verdict in VERDICTS:
        assert _verdicts(whole)[verdict] == sum(_verdicts(part)[verdict] for part in parts)
    for state in RUN_STATES:
        assert _states(whole)[state] == sum(_states(part)[state] for part in parts)
    for section in (*PROJECT_SECTIONS, None):
        assert _sections(whole)[section] == sum(_sections(part)[section] for part in parts)
    assert _spend(whole) == (3, 5300, "measured")
    assert _spend(whole) != _spend(parts[0]) != _spend(parts[1]), "the figures differ, so a passthrough shows"


def test_a_project_that_does_not_exist_is_not_found_and_not_a_summary_of_zeros(
    session: Session, world: World
) -> None:
    with pytest.raises(DomainError) as caught:
        dashboard.summary(session, project_uid=str(ProjectUid.new()))
    assert caught.value.code is ErrorCode.NOT_FOUND
    assert caught.value.detail_fields == {"aggregate_type": "Project"}
