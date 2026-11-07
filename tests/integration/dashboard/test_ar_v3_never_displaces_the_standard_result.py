"""`AR-V3-OPT-IN` (`Q3`) on real PostgreSQL rows: a published AR v3 run never becomes «the result of a version».

One definition -- the newest published or partial run of the STANDARD analysis, derived from the run's pinned
profile/bundle pair (`runs/analysis_kind.py`) -- is read by four consumers, and each is shown here with a v3 run that
is NEWER than the standard one and would win under the old rule «the newest published run, of any kind»:

1. the audit state of a document and every counter read off it (`dashboard/audit_state.py`, one statement);
2. the schedule's facts, «Выполнено» (`schedule/service.py`);
3. the run a comparison reads by default (`_AnalysisReader`, which marks each candidate);
4. the run the optimisation reads its specification text from (the two `SavedTextReader` adapters).

The v3 runs here are plain `audit_run` rows with the sealed pair; what the consumers read is the pair, which the
database ties to a group's members (migration 0032) and the group start writes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.public import AccountRepository
from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID
from auditmanager.bootstrap.adapters import _AnalysisReader, _ProposalTextReader, _SpecificationTextReader
from auditmanager.dashboard import AuditCountsRecord, DocumentAuditReadModel, tally
from auditmanager.optimisation.project_match import _newest_published
from auditmanager.schedule.public import read_schedule_month
from auditmanager.shared.identity import AnalysisProfileId, DecisionId, FindingObservationId, FindingUid, PromptBundleId, RunId
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import Seeder

model = DocumentAuditReadModel()
V3 = (str(AR_V3_BETA_PROFILE_ID), str(AR_V3_BETA_BUNDLE_ID))
_PATH = {
    "published": ("queued", "running", "validating", "published"),
    "partial": ("queued", "running", "validating", "partial"),
}


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _run(session: Session, project: str, version: str, state: str, *, age: int, v3: bool) -> str:
    """A run created ``age`` seconds ago, of the sealed v3 pair or of a standard pair, walked to ``state``."""
    run_id = str(RunId.new())
    profile, bundle = V3 if v3 else (str(AnalysisProfileId.new()), str(PromptBundleId.new()))
    session.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, "
        "provider_mode, frozen_input_digest, created_at) VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, "
        "now() - make_interval(secs => CAST(:age AS double precision)))"),
        {"r": run_id, "p": project, "v": version, "ap": profile, "pb": bundle,
         "s": hashlib.sha256(run_id.encode()).hexdigest(), "age": age})
    for step in _PATH[state]:
        session.execute(text(
            "UPDATE audit_run SET state = :s, terminal_at = CASE WHEN :s IN ('published', 'partial') THEN now() END, "
            "degradation_set = CASE WHEN :s = 'partial' THEN '[\"block_analysis\"]'::jsonb "
            "WHEN :s = 'published' THEN '[]'::jsonb ELSE degradation_set END WHERE run_id = :r"),
            {"s": step, "r": run_id})
    return run_id


def _finding(session: Session, project: str, version: str, run_id: str, *, decided_by: str | None) -> None:
    """One published finding of ``run_id``; accepted by ``decided_by`` when given, else undecided."""
    finding, observation = str(FindingUid.new()), str(FindingObservationId.new())
    session.execute(text(
        "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
        "VALUES (:f, :p, :v, :r, 'internal_contradiction')"), {"f": finding, "p": project, "v": version, "r": run_id})
    session.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, "
        "finding_text, recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
        "VALUES (:o, :r, :f, 'text_analysis', 'internal_contradiction', 'text', 'recommendation', true, :ap, :pb, 'recorded')"),
        {"o": observation, "r": run_id, "f": finding, "ap": str(AnalysisProfileId.new()), "pb": str(PromptBundleId.new())})
    if decided_by is not None:
        session.execute(text(
            "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, verdict, "
            "author_label, author_user_uid) VALUES (:d, :f, :o, 'accept', 'accepted', 'v3 suite', :u)"),
            {"d": str(DecisionId.new()), "f": finding, "o": observation, "u": decided_by})


class World:
    """Four documents of one project, each with the runs its name says. Every standard result is fully decided."""

    def __init__(self, session: Session) -> None:
        seed = Seeder(session)
        self.expert = seed.expert
        self.project = seed.project("АР v3 не подменяет результат")
        self.documents: dict[str, str] = {}
        self.versions: dict[str, str] = {}
        self.runs: dict[str, str] = {}
        for name in ("both", "v3_only", "partial_v3", "standard_only"):
            document = seed.document(self.project, name)
            self.documents[name] = document
            self.versions[name] = seed.version(document, classified=("R", "AR"))
        self._run(session, "both", "standard", "published", age=100, v3=False, decided=True)
        self._run(session, "both", "v3", "published", age=10, v3=True, decided=False)
        self._run(session, "v3_only", "v3", "published", age=10, v3=True, decided=True)
        self._run(session, "partial_v3", "standard", "published", age=100, v3=False, decided=True)
        self._run(session, "partial_v3", "v3", "partial", age=10, v3=True, decided=False)
        self._run(session, "standard_only", "standard", "published", age=100, v3=False, decided=True)
        session.commit()

    def _run(self, session: Session, name: str, label: str, state: str, *, age: int, v3: bool, decided: bool) -> None:
        run = _run(session, self.project, self.versions[name], state, age=age, v3=v3)
        _finding(session, self.project, self.versions[name], run, decided_by=self.expert if decided else None)
        self.runs[f"{name}/{label}"] = run


@pytest.fixture
def world(session: Session) -> World:
    return World(session)


def test_the_audit_state_and_every_counter_read_the_standard_result(session: Session, world: World) -> None:
    """«both»: checked by its standard run, though a newer v3 run with an undecided finding exists. «v3_only»: not run -- its
    only published result is v3. «partial_v3»: a newer PARTIAL v3 run neither displaces the result nor sets the flag."""
    groups = model.groups(session, project_uid=world.project)
    assert tally(groups) == AuditCountsRecord(
        document_count=4, not_run=1, clean=0, awaiting_decision=0, checked=3, partial=0,
    )
    audits = model.audits(session, version_uids=list(world.versions.values()))
    by_document = {name: audits[version] for name, version in world.versions.items()}
    assert {name: audit.state for name, audit in by_document.items()} == {
        "both": "checked", "v3_only": "not_run", "partial_v3": "checked", "standard_only": "checked",
    }
    assert not any(audit.partial for audit in by_document.values())


def test_the_schedule_counts_the_documents_checked_by_their_standard_result(session: Session, world: World) -> None:
    """«v3_only» would be a fourth done document if a v3 run could be the result; it is not one."""
    today = session.execute(text("SELECT (now() AT TIME ZONE 'UTC')::date")).scalar_one()
    month = read_schedule_month(
        session, month=today.replace(day=1), viewer_uid=world.expert,
        viewer_roles=AccountRepository().roles_of(session, world.expert),
    )
    (engineer,) = month.engineers
    assert {item.document_uid for item in engineer.done} == {
        world.documents["both"], world.documents["partial_v3"], world.documents["standard_only"],
    }


def test_a_comparison_marks_each_candidate_and_the_optimisation_picks_the_standard_run(
    session: Session, world: World,
) -> None:
    both = world.versions["both"]
    candidates = _AnalysisReader(None).runs_newest_first(session, version_uid=both)
    assert [(c.run_id, c.state, c.standard_analysis) for c in candidates] == [
        (world.runs["both/v3"], "published", False), (world.runs["both/standard"], "published", True),
    ], "newest first, each marked by its pinned pair"
    for reader in (_SpecificationTextReader(None), _ProposalTextReader(None)):
        assert _newest_published(reader, session, both) == world.runs["both/standard"]
        assert _newest_published(reader, session, world.versions["v3_only"]) is None
        assert _newest_published(reader, session, world.versions["partial_v3"]) == world.runs["partial_v3/standard"]
