"""`UI-PARITY-P0B`: the audit state of a document and its counters, on real PostgreSQL rows.

Two seeded data sets, both built here from the rulings (`R-150n` ... `R-150u`) and not read back from the module:

* **Cases** (one document each, in a project of its own): every situation the owner ruled on, with the state and the
  `partial` flag it must be in -- zero findings is `clean`, a failed or cancelled run is `not_run`, a partial result is a
  result with the flag, a newer run still in flight does not displace the result, a V2 with no run is `not_run`, all
  findings decided is `checked`, and the ties and reversals the read model has to get right (two results created in the
  same instant, a verdict revoked, a comment that decides nothing).
* **The world** (three projects, twelve documents): the three outputs -- `Project.audit_counts` of ``listProjects``,
  `SectionDocumentCount` and `DashboardSummary.awaiting_decision_findings` of ``getDashboardSummary`` -- read through the
  shipped adapters and rendered with the shipped wire functions, and shown to agree with each other and with the figures
  counted by hand below. The project scope applies to the section panel and the findings tile.

The database is a fresh clone of the migrated template, so every number is absolute.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.schemas.dashboard import dashboard_summary_body
from auditmanager.api.schemas.documents import document_audit_body
from auditmanager.api.schemas.projects import project_body
from auditmanager.bootstrap.adapters import DashboardAdapter, DocumentAdapter, ProjectAdapter
from auditmanager.dashboard import (
    AUDIT_STATES,
    AuditCountsRecord,
    DocumentAuditReadModel,
    counts_by_section,
    tally,
)
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    FindingObservationId,
    FindingUid,
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

model = DocumentAuditReadModel()

#: Edges ``contract_state_transition`` declares; a run is walked along them and never written at its target.
_PATH = {
    "created": (),
    "queued": ("queued",),
    "running": ("queued", "running"),
    "validating": ("queued", "running", "validating"),
    "published": ("queued", "running", "validating", "published"),
    "partial": ("queued", "running", "validating", "partial"),
    "failed": ("queued", "failed"),
    "cancelled": ("cancelled",),
}
_TERMINAL = {"published", "partial", "failed", "cancelled"}


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _run(
    session: Session,
    project_uid: str,
    version_uid: str,
    state: str,
    *,
    age: int,
    run_id: str | None = None,
) -> str:
    """One run on a version, created ``age`` seconds ago (a larger age is an older run), walked to ``state``."""
    run_id = run_id or str(RunId.new())
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest, created_at) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, "
            "now() - make_interval(secs => CAST(:age AS double precision)))"
        ),
        {
            "r": run_id,
            "p": project_uid,
            "v": version_uid,
            "ap": str(AnalysisProfileId.new()),
            "pb": str(PromptBundleId.new()),
            "s": _digest(f"counters-{run_id}"),
            "age": age,
        },
    )
    for step in _PATH[state]:
        session.execute(
            text(
                "UPDATE audit_run SET state = :s, "
                "terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
                "terminal_reason = CASE WHEN :s = 'failed' THEN 'analysis_failed' ELSE NULL END, "
                "degradation_set = CASE WHEN :s = 'partial' THEN '[\"block_analysis\"]'::jsonb "
                "WHEN :s = 'published' THEN '[]'::jsonb ELSE degradation_set END "
                "WHERE run_id = :r"
            ),
            {"s": step, "t": step in _TERMINAL, "r": run_id},
        )
    return run_id


def _event(session: Session, finding_uid: str, observation_id: str, event_type: str, verdict: str | None, comment: str | None) -> None:
    session.execute(
        text(
            "INSERT INTO expert_decision_event (decision_id, finding_uid, finding_observation_id, event_type, "
            "verdict, comment, author_label) VALUES (:d, :f, :o, :et, :v, :c, 'audit-state suite')"
        ),
        {"d": str(DecisionId.new()), "f": finding_uid, "o": observation_id, "et": event_type, "v": verdict, "c": comment},
    )


def _finding(session: Session, project_uid: str, version_uid: str, run_id: str, kind: str) -> str:
    """One published finding of a run -- a ``finding`` and the grounded observation that publishes it -- whose current
    verdict is the one ``kind`` names: ``pending`` (no event), ``accepted``, ``rejected``, ``revoked`` (accepted and then
    revoked: back to ``pending``) or ``commented`` (a comment decides nothing: ``pending``)."""
    finding_uid = str(FindingUid.new())
    observation_id = str(FindingObservationId.new())
    session.execute(
        text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
            "VALUES (:f, :p, :v, :r, 'internal_contradiction')"
        ),
        {"f": finding_uid, "p": project_uid, "v": version_uid, "r": run_id},
    )
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
    if kind == "accepted":
        _event(session, finding_uid, observation_id, "accept", "accepted", None)
    elif kind == "rejected":
        _event(session, finding_uid, observation_id, "reject", "rejected", None)
    elif kind == "revoked":
        _event(session, finding_uid, observation_id, "accept", "accepted", None)
        _event(session, finding_uid, observation_id, "revoke", "pending", None)
    elif kind == "commented":
        _event(session, finding_uid, observation_id, "comment", None, "посмотрю позже")
    else:
        assert kind == "pending", kind
    return finding_uid


@dataclass
class Spec:
    """A run to seed on one of a document's versions: its state, age, the findings it published and the version."""

    state: str
    age: int
    findings: tuple[str, ...] = ()
    version: int = 1
    run_id: str | None = None


@dataclass
class Case:
    name: str
    runs: list[Spec] = field(default_factory=list)
    versions: int = 1
    expected: tuple[str, bool] = ("not_run", False)


def _two_run_ids() -> tuple[str, str]:
    """Two run identities in ascending order (the later sorts after the earlier), minted apart."""
    low, high = sorted(str(RunId.new()) for _ in range(2))
    assert low < high
    return low, high


def _cases() -> list[Case]:
    low, high = _two_run_ids()
    return [
        Case("never run", expected=("not_run", False)),
        Case("only a failed run", [Spec("failed", 100)], expected=("not_run", False)),
        Case("only a cancelled run", [Spec("cancelled", 100)], expected=("not_run", False)),
        Case("only a run in flight", [Spec("running", 100)], expected=("not_run", False)),
        Case("a queued run", [Spec("queued", 100)], expected=("not_run", False)),
        Case("a published run with no finding", [Spec("published", 100)], expected=("clean", False)),
        Case("a result with every finding pending", [Spec("published", 100, ("pending", "pending"))], expected=("awaiting_decision", False)),
        Case("a result with one finding undecided among decided ones", [Spec("published", 100, ("accepted", "rejected", "pending"))], expected=("awaiting_decision", False)),
        Case("a result with every finding decided", [Spec("published", 100, ("accepted", "rejected"))], expected=("checked", False)),
        Case("a verdict revoked is undecided again", [Spec("published", 100, ("revoked",))], expected=("awaiting_decision", False)),
        Case("a comment decides nothing", [Spec("published", 100, ("commented",))], expected=("awaiting_decision", False)),
        Case("a partial result, all decided", [Spec("partial", 100, ("accepted",))], expected=("checked", True)),
        Case("a partial result, no finding", [Spec("partial", 100)], expected=("clean", True)),
        Case("a partial result, one undecided", [Spec("partial", 100, ("pending", "accepted"))], expected=("awaiting_decision", True)),
        Case(
            "a newer run in flight does not displace the result",
            [Spec("published", 100, ("pending",)), Spec("running", 10)],
            expected=("awaiting_decision", False),
        ),
        Case(
            "a newer failed run does not displace the result",
            [Spec("published", 100, ("accepted",)), Spec("failed", 10), Spec("cancelled", 5)],
            expected=("checked", False),
        ),
        Case(
            "a newer published run replaces the older one",
            [Spec("published", 100, ("pending", "pending", "pending")), Spec("published", 10)],
            expected=("clean", False),
        ),
        Case(
            "a newer partial run replaces an older published one and carries the flag",
            [Spec("published", 100, ("pending",)), Spec("partial", 10, ("accepted",))],
            expected=("checked", True),
        ),
        Case(
            "two results made in the same instant: the greater run_id is the latest, as listRuns orders them",
            [Spec("published", 50, ("pending", "pending"), run_id=low), Spec("published", 50, (), run_id=high)],
            expected=("clean", False),
        ),
        Case(
            "a version 2 with no run is not run, however well version 1 was checked",
            [Spec("published", 100, ("accepted", "accepted"), version=1)],
            versions=2,
            expected=("not_run", False),
        ),
        Case(
            "a version 2 with its own result is read on its own",
            [Spec("published", 100, ("accepted",), version=1), Spec("published", 50, ("pending",), version=2)],
            versions=2,
            expected=("awaiting_decision", False),
        ),
    ]


def _seed_case(session: Session, seed: Seeder, case: Case) -> str:
    """One project holding one document that is in the situation ``case`` describes. Returns the project."""
    project = seed.project(f"Случай: {case.name}")
    document = seed.document(project, "Документ")
    versions = [seed.version(document, classified=("R", "AR")) for _ in range(case.versions)]
    for spec in case.runs:
        version = versions[spec.version - 1]
        run_id = _run(session, project, version, spec.state, age=spec.age, run_id=spec.run_id)
        for kind in spec.findings:
            _finding(session, project, version, run_id, kind)
    return project


def test_every_ruled_situation_puts_the_document_in_its_state(session: Session) -> None:
    seed = Seeder(session)
    cases = _cases()
    projects = {case.name: _seed_case(session, seed, case) for case in cases}
    session.commit()

    wrong: list[str] = []
    for case in cases:
        groups = model.groups(session, project_uid=projects[case.name])
        counts = tally(groups)
        state, partial = case.expected
        expected = AuditCountsRecord(
            document_count=1,
            not_run=int(state == "not_run"),
            clean=int(state == "clean"),
            awaiting_decision=int(state == "awaiting_decision"),
            checked=int(state == "checked"),
            partial=int(partial),
        )
        if counts != expected:
            wrong.append(f"{case.name}: expected {expected}, read {counts}")
    assert not wrong, "\n".join(wrong)


def test_the_cases_are_not_vacuous() -> None:
    """The set exercises all four states, the flag, and every kind of run that is not a result."""
    states = {case.expected for case in _cases()}
    assert {state for state, _ in states} == {"not_run", "clean", "awaiting_decision", "checked"}
    assert {partial for _, partial in states} == {True, False}
    used = {spec.state for case in _cases() for spec in case.runs}
    assert {"failed", "cancelled", "running", "queued", "published", "partial"} <= used


# --- the world ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class World:
    school: str
    clinic: str
    empty: str


def _doc(
    session: Session, seed: Seeder, project: str, title: str, section: tuple[str, str] | None, versions: int = 1
) -> tuple[str, list[str]]:
    document = seed.document(project, title)
    uids = [seed.version(document, classified=section) for _ in range(versions)]
    return document, uids


@pytest.fixture
def world(session: Session) -> World:
    """Twelve documents in three projects. Counted by hand:

    School, AR (seven documents): ``d_clean`` (clean); ``d_await`` (published, findings pending x2 + accepted, and a
    newer run still running: awaiting, 2 undecided); ``d_partial_checked`` (partial, accepted: checked + partial);
    ``d_v2`` (version 1 had a result with a pending and an accepted finding, version 2 is current and was never run:
    not run); ``d_rerun`` (an older result with three pending findings, a newer one with none: clean); ``d_revoked``
    (accepted and revoked: awaiting, 1); ``d_commented`` (awaiting, 1). School, KJ (three): ``d_checked`` (accepted +
    rejected: checked), ``d_failed`` and ``d_cancelled`` (not run). School, PS (one): ``d_partial_await`` (partial, one
    pending: awaiting + partial, 1).

    Clinic: ``c_unclassified``, no section, a result with two pending findings (awaiting, 2). Empty: nothing.
    """
    seed = Seeder(session)
    school, clinic, empty = seed.project("Школа"), seed.project("Поликлиника"), seed.project("Пустой")

    def result(project: str, version: str, findings: tuple[str, ...], *, state: str = "published", age: int = 100) -> str:
        run_id = _run(session, project, version, state, age=age)
        for kind in findings:
            _finding(session, project, version, run_id, kind)
        return run_id

    _, (v,) = _doc(session, seed, school, "d_clean", ("R", "AR"))
    result(school, v, ())
    _, (v,) = _doc(session, seed, school, "d_await", ("R", "AR"))
    result(school, v, ("pending", "pending", "accepted"))
    _run(session, school, v, "running", age=5)
    _, (v,) = _doc(session, seed, school, "d_partial_checked", ("R", "AR"))
    result(school, v, ("accepted",), state="partial")
    _, (v1, v2) = _doc(session, seed, school, "d_v2", ("R", "AR"), versions=2)
    result(school, v1, ("pending", "accepted"))
    _, (v,) = _doc(session, seed, school, "d_rerun", ("R", "AR"))
    result(school, v, ("pending", "pending", "pending"), age=200)
    result(school, v, (), age=20)
    _, (v,) = _doc(session, seed, school, "d_revoked", ("R", "AR"))
    result(school, v, ("revoked",))
    _, (v,) = _doc(session, seed, school, "d_commented", ("R", "AR"))
    result(school, v, ("commented",))
    _, (v,) = _doc(session, seed, school, "d_checked", ("R", "KJ"))
    result(school, v, ("accepted", "rejected"))
    _, (v,) = _doc(session, seed, school, "d_failed", ("R", "KJ"))
    _run(session, school, v, "failed", age=100)
    _, (v,) = _doc(session, seed, school, "d_cancelled", ("R", "KJ"))
    _run(session, school, v, "cancelled", age=100)
    _, (v,) = _doc(session, seed, school, "d_partial_await", ("P", "PS"))
    result(school, v, ("pending",), state="partial")

    _, (v,) = _doc(session, seed, clinic, "c_unclassified", None)
    result(clinic, v, ("pending", "pending"))
    # A set that never got a published head is counted nowhere, whatever it holds.
    seed.document(clinic, "c_no_head")
    session.commit()
    return World(school=school, clinic=clinic, empty=empty)


def _record(**counts: int) -> AuditCountsRecord:
    return AuditCountsRecord(**counts)


SCHOOL = _record(document_count=11, not_run=3, clean=2, awaiting_decision=4, checked=2, partial=2)
CLINIC = _record(document_count=1, awaiting_decision=1)
SCHOOL_AR = _record(document_count=7, not_run=1, clean=2, awaiting_decision=3, checked=1, partial=1)
SCHOOL_KJ = _record(document_count=3, not_run=2, checked=1)
SCHOOL_PS = _record(document_count=1, awaiting_decision=1, partial=1)


def test_the_world_tallies_are_the_ones_counted_by_hand(session: Session, world: World) -> None:
    school = model.groups(session, project_uid=world.school)
    assert tally(school) == SCHOOL
    assert SCHOOL.no_expert_decision == 3 + 4, "not run + awaiting, and not the two clean documents"
    sections = counts_by_section(school)
    assert {code: (row.counts, row.finding_count) for code, row in sections.items()} == {
        "AR": (SCHOOL_AR, 6),
        "KJ": (SCHOOL_KJ, 2),
        "PS": (SCHOOL_PS, 1),
    }
    assert tally(model.groups(session, project_uid=world.clinic)) == CLINIC
    assert tally(model.groups(session, project_uid=world.empty)) == AuditCountsRecord()
    whole = model.groups(session)
    assert tally(whole) == _record(document_count=12, not_run=3, clean=2, awaiting_decision=5, checked=2, partial=2)


# --- the three outputs, through the shipped adapters ------------------------------------------------


class _Listing:
    """The part of ``IngestService`` the project adapter reads: the listing, as the documents boundary gives it."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def list_projects(self) -> Any:
        with self._factory() as session:
            return DocumentRepository().list_projects(session)


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


def _projects_body(factory: sessionmaker[Session]) -> dict[str, dict[str, Any]]:
    adapter = ProjectAdapter(_Listing(factory), factory)
    return {view.project_uid: project_body(view) for view in adapter.list_projects()}


def _summary_body(factory: sessionmaker[Session], project_uid: str | None) -> dict[str, Any]:
    return dashboard_summary_body(DashboardAdapter(factory).get_summary(project_uid=project_uid))


def _section_counts(body: dict[str, Any]) -> dict[str | None, dict[str, int]]:
    return {row.get("section"): row["audit_counts"] for row in body["section_breakdown"]}


def _as_wire(record: AuditCountsRecord) -> dict[str, int]:
    return {
        "document_count": record.document_count,
        "not_run": record.not_run,
        "clean": record.clean,
        "awaiting_decision": record.awaiting_decision,
        "checked": record.checked,
        "partial": record.partial,
        "no_expert_decision": record.no_expert_decision,
    }


def test_list_projects_carries_each_projects_counters(factory: sessionmaker[Session], world: World) -> None:
    items = _projects_body(factory)
    assert items[world.school]["audit_counts"] == _as_wire(SCHOOL)
    assert items[world.clinic]["audit_counts"] == _as_wire(CLINIC)
    assert items[world.empty]["audit_counts"] == _as_wire(AuditCountsRecord()), "a project with nothing reports zeros"
    for item in items.values():
        assert item["audit_counts"]["document_count"] == item["document_count"], "one definition of a document"
    assert items[world.school]["audit_counts"]["no_expert_decision"] == 7
    assert items[world.school]["audit_counts"]["awaiting_decision"] == 4


def test_the_section_panel_carries_the_counters_and_the_findings_of_the_result_runs(
    factory: sessionmaker[Session], world: World
) -> None:
    body = _summary_body(factory, world.school)
    sections = _section_counts(body)
    assert sections["AR"] == _as_wire(SCHOOL_AR)
    assert sections["KJ"] == _as_wire(SCHOOL_KJ)
    assert sections["PS"] == _as_wire(SCHOOL_PS)
    assert sections[None] == _as_wire(AuditCountsRecord()), "the unclassified bucket is present at zero"
    assert all(sections[code]["document_count"] == 0 for code in sections if code not in {"AR", "KJ", "PS"})
    findings = {row.get("section"): row["finding_count"] for row in body["section_breakdown"]}
    assert (findings["AR"], findings["KJ"], findings["PS"], findings[None]) == (6, 2, 1, 0)
    for row in body["section_breakdown"]:
        assert row["document_count"] == row["audit_counts"]["document_count"]


def test_the_tile_counts_undecided_findings_of_current_result_runs_and_the_verdict_panel_stays_all_time(
    factory: sessionmaker[Session], world: World
) -> None:
    school = _summary_body(factory, world.school)
    # d_await 2, d_partial_await 1, d_revoked 1, d_commented 1. Not d_v2's version-1 pending, not d_rerun's older three.
    assert school["awaiting_decision_findings"] == 5
    verdicts = {row["verdict"]: row["count"] for row in school["findings_by_verdict"]}
    assert verdicts["pending"] == 2 + 1 + 1 + 1 + 1 + 3 == 9, "every finding of every run, «за всё время»"
    assert verdicts["pending"] > school["awaiting_decision_findings"]
    assert _summary_body(factory, world.clinic)["awaiting_decision_findings"] == 2
    assert _summary_body(factory, world.empty)["awaiting_decision_findings"] == 0


def test_the_three_outputs_agree_on_one_data_set(factory: sessionmaker[Session], world: World) -> None:
    items = _projects_body(factory)
    whole = _summary_body(factory, None)

    # The section panel of the whole deployment adds up to the sum of the projects' counters, key by key.
    keys = ("document_count", "not_run", "clean", "awaiting_decision", "checked", "partial", "no_expert_decision")
    by_projects = {key: sum(item["audit_counts"][key] for item in items.values()) for key in keys}
    by_sections = {key: sum(row["audit_counts"][key] for row in whole["section_breakdown"]) for key in keys}
    assert by_projects == by_sections == _as_wire(
        _record(document_count=12, not_run=3, clean=2, awaiting_decision=5, checked=2, partial=2)
    )
    # And project by project: the item of `listProjects` is the sum of the project's own section rows.
    for project in (world.school, world.clinic, world.empty):
        scoped = _summary_body(factory, project)
        per_section = {key: sum(row["audit_counts"][key] for row in scoped["section_breakdown"]) for key in keys}
        assert per_section == items[project]["audit_counts"], project
        assert [row["project_uid"] for row in scoped["documents_by_project"]] == [project]
    # The tile is the sum of the scoped tiles, and the findings of the sections are the findings the tile is part of.
    assert whole["awaiting_decision_findings"] == 7 == 5 + 2 + 0
    assert sum(row["finding_count"] for row in whole["section_breakdown"]) == 9 + 2
    assert whole["awaiting_decision_findings"] <= sum(row["finding_count"] for row in whole["section_breakdown"])


def test_the_project_scope_applies_to_the_new_figures_and_an_unknown_project_is_not_found(
    factory: sessionmaker[Session], world: World
) -> None:
    clinic = _summary_body(factory, world.clinic)
    assert clinic["awaiting_decision_findings"] == 2
    assert _section_counts(clinic)[None] == _as_wire(CLINIC), "the clinic's only document is unclassified"
    assert _section_counts(clinic)["AR"]["document_count"] == 0, "the school's documents are not the clinic's"
    with pytest.raises(DomainError) as caught:
        DashboardAdapter(factory).get_summary(project_uid=str(ProjectUid.new()))
    assert caught.value.code is ErrorCode.NOT_FOUND


def test_a_fresh_deployment_reports_zero_everywhere(factory: sessionmaker[Session]) -> None:
    body = _summary_body(factory, None)
    assert body["awaiting_decision_findings"] == 0
    assert all(
        row["audit_counts"] == _as_wire(AuditCountsRecord()) and row["finding_count"] == 0
        for row in body["section_breakdown"]
    )
    assert _projects_body(factory) == {}


# --- the audit of each listed document (`UI-PARITY-DOC-AUDIT`, `UI-A-46`, `UI-A-38`, `UI-A-49`) -------------------


class _Documents:
    """The part of ``IngestService`` the document adapter reads for a listing: the current version of every document."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def list_documents(self, project_uid: Any) -> Any:
        with self._factory() as session:
            return DocumentRepository().list_documents(session, project_uid)


#: The school's eleven documents as the ``world`` fixture builds them, counted by hand: the state, the partial flag, the
#: findings of the result run and how many of them are undecided.
SCHOOL_DOCUMENTS: dict[str, tuple[str, bool, int, int]] = {
    "d_clean": ("clean", False, 0, 0),
    "d_await": ("awaiting_decision", False, 3, 2),
    "d_partial_checked": ("checked", True, 1, 0),
    "d_v2": ("not_run", False, 0, 0),
    "d_rerun": ("clean", False, 0, 0),
    "d_revoked": ("awaiting_decision", False, 1, 1),
    "d_commented": ("awaiting_decision", False, 1, 1),
    "d_checked": ("checked", False, 2, 0),
    "d_failed": ("not_run", False, 0, 0),
    "d_cancelled": ("not_run", False, 0, 0),
    "d_partial_await": ("awaiting_decision", True, 1, 1),
}


def _documents(factory: sessionmaker[Session]) -> DocumentAdapter:
    return DocumentAdapter(_Documents(factory), factory)


def test_the_audit_of_each_listed_document_is_the_one_counted_by_hand_and_agrees_with_the_counters(
    factory: sessionmaker[Session], world: World
) -> None:
    adapter = _documents(factory)
    views = [view for state in AUDIT_STATES for view in adapter.list_documents(project_uid=world.school, audit_state=state)]
    assert len(views) == len(SCHOOL_DOCUMENTS) == 11, "the four states partition the listing"
    seen: dict[str, tuple[str, bool, int, int]] = {}
    for view in views:
        assert view.audit is not None and view.display_title is not None
        audit = view.audit
        seen[view.display_title] = (audit.state, audit.partial, audit.finding_count, audit.undecided_finding_count)
        # The result run is named exactly when there is one, and the wire omits it exactly when there is none.
        assert (audit.result_run_id is None) == (audit.state == "not_run"), view.display_title
        assert ("result_run_id" in document_audit_body(audit)) == (audit.state != "not_run")
    assert seen == SCHOOL_DOCUMENTS
    # The per-document states are the counters' states: the same tally of the same documents.
    wanted = _as_wire(SCHOOL)
    by_state = {state: sum(1 for entry in seen.values() if entry[0] == state) for state in AUDIT_STATES}
    assert by_state == {key: wanted[key] for key in AUDIT_STATES}
    assert sum(1 for entry in seen.values() if entry[1]) == wanted["partial"]


def test_the_audit_filter_keeps_exactly_the_documents_in_that_state(
    factory: sessionmaker[Session], world: World
) -> None:
    adapter = _documents(factory)
    expected = {
        state: {title for title, entry in SCHOOL_DOCUMENTS.items() if entry[0] == state} for state in AUDIT_STATES
    }
    assert {state: len(titles) for state, titles in expected.items()} == {
        "not_run": 3, "clean": 2, "awaiting_decision": 4, "checked": 2,
    }
    for state, titles in expected.items():
        listed = adapter.list_documents(project_uid=world.school, audit_state=state)
        assert {view.display_title for view in listed} == titles, state
    everything = adapter.list_documents(project_uid=world.school)
    assert len(everything) == 11 and all(view.audit is None for view in everything), (
        "without the filter or the order nothing is read here; the router reads the page it cut"
    )
    # It composes with the section filter: the school's АР section holds seven documents, one of them never run.
    in_section = adapter.list_documents(project_uid=world.school, section_code="AR", audit_state="not_run")
    assert {view.display_title for view in in_section} == {"d_v2"}
    # The clinic's only document is awaiting a decision, and its project has none that was never run.
    assert adapter.list_documents(project_uid=world.clinic, audit_state="not_run") == ()
    assert [view.display_title for view in adapter.list_documents(project_uid=world.clinic, audit_state="awaiting_decision")] == [
        "c_unclassified"
    ]


def test_the_audit_order_is_checked_then_processed_then_never_run_and_by_name_within_each(
    factory: sessionmaker[Session], world: World
) -> None:
    adapter = _documents(factory)
    ordered = adapter.list_documents(project_uid=world.school, order="audit")
    assert [view.display_title for view in ordered] == [
        "d_checked", "d_partial_checked",
        "d_await", "d_clean", "d_commented", "d_partial_await", "d_rerun", "d_revoked",
        "d_cancelled", "d_failed", "d_v2",
    ]
    published = adapter.list_documents(project_uid=world.school, order="published")
    assert [view.display_title for view in published] == [
        view.display_title for view in adapter.list_documents(project_uid=world.school)
    ], "`published` is the order the operation always had"
    assert [view.display_title for view in published] != [view.display_title for view in ordered], (
        "the two orders must differ on this data set or the test proves nothing"
    )
    # The filter and the order compose: the narrowed listing is in the audit order.
    narrowed = adapter.list_documents(project_uid=world.school, audit_state="awaiting_decision", order="audit")
    assert [view.display_title for view in narrowed] == ["d_await", "d_commented", "d_partial_await", "d_revoked"]


def test_an_unknown_audit_state_or_order_is_refused_and_an_unknown_version_is_not_found(
    factory: sessionmaker[Session], world: World
) -> None:
    adapter = _documents(factory)
    with pytest.raises(ValueError):
        adapter.list_documents(project_uid=world.school, audit_state="failed")
    with pytest.raises(ValueError):
        adapter.list_documents(project_uid=world.school, order="newest")
    with pytest.raises(DomainError) as caught:
        adapter.document_audits(version_uids=["ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"])
    assert caught.value.code is ErrorCode.NOT_FOUND
    assert adapter.document_audits(version_uids=[]) == {}, "no names, no statement"
    with pytest.raises(RuntimeError):
        DocumentAdapter(_Documents(factory)).list_documents(project_uid=world.school, audit_state="clean")


# --- the run in flight (`UI-A-47`, contract 1.40.0) ------------------------------------------------------------------


def test_only_a_run_in_flight_is_an_active_run_and_it_is_read_in_the_audit_statement(
    factory: sessionmaker[Session], world: World
) -> None:
    """On the world above exactly one document has a run in flight (``d_await``: a newer run still running over its
    result). Its state is the one counted by hand -- the active run is a fact beside it -- and no other record has one."""
    adapter = _documents(factory)
    views = adapter.list_documents(project_uid=world.school, order="audit")
    assert len(views) == 11
    active = {view.display_title: view.audit.active_run for view in views if view.audit is not None}
    assert {title for title, run in active.items() if run is not None} == {"d_await"}
    run = active["d_await"]
    assert run is not None and run.state == "running" and run.run_id.startswith("run_")
    by_title = {view.display_title: view.audit for view in views}
    assert by_title["d_await"] is not None and by_title["d_await"].state == "awaiting_decision", (
        "a run in flight over a result changes none of the four words"
    )
    body = document_audit_body(by_title["d_await"])
    assert body["active_run"] == {"run_id": run.run_id, "state": "running"} and body["state"] == "awaiting_decision"
    assert all("active_run" not in document_audit_body(audit) for title, audit in by_title.items() if title != "d_await" and audit)
    # The counters never read it: the figures of the school are the hand count the tests above assert, with this run in
    # flight over ``d_await``.


def _active_cases() -> list[tuple[str, list[Spec], int, dict[int, str | None]]]:
    """``(name, runs, versions, {version number: what its active run's state must be, None for none})``."""
    low, high = _two_run_ids()
    return [
        ("never run", [], 1, {1: None}),
        ("a queued run", [Spec("queued", 100)], 1, {1: "queued"}),
        ("a running run", [Spec("running", 100)], 1, {1: "running"}),
        ("a validating run", [Spec("validating", 100)], 1, {1: "validating"}),
        ("a created run has not been admitted", [Spec("created", 100)], 1, {1: None}),
        ("a failed run", [Spec("failed", 100)], 1, {1: None}),
        ("a cancelled run", [Spec("cancelled", 100)], 1, {1: None}),
        ("a published result alone", [Spec("published", 100, ("pending",))], 1, {1: None}),
        ("a partial result alone", [Spec("partial", 100, ("accepted",))], 1, {1: None}),
        ("a re-run in flight over a result", [Spec("published", 100, ("accepted",)), Spec("queued", 10)], 1, {1: "queued"}),
        ("the newest of two in flight", [Spec("queued", 100), Spec("running", 10)], 1, {1: "running"}),
        ("the newer in flight, the older terminal", [Spec("failed", 100), Spec("validating", 10)], 1, {1: "validating"}),
        ("the older in flight, the newer terminal", [Spec("running", 100), Spec("failed", 10)], 1, {1: "running"}),
        (
            "two made in the same instant: the greater run_id is the latest, as the result run is chosen",
            [Spec("queued", 50, run_id=low), Spec("running", 50, run_id=high)], 1, {1: "running"},
        ),
        (
            "only the current version is read: a run in flight on version 1 is not version 2's",
            [Spec("running", 100, version=1)], 2, {2: None},
        ),
        (
            "and a run in flight on the current version is",
            [Spec("running", 100, version=1), Spec("queued", 10, version=2)], 2, {2: "queued"},
        ),
    ]


def test_each_situation_of_the_active_run_reads_as_ruled_and_leaves_the_audit_state_alone(session: Session) -> None:
    seed = Seeder(session)
    cases = _active_cases()
    seeded: dict[str, tuple[str, list[str]]] = {}
    for name, runs, versions, _ in cases:
        project = seed.project(f"Активный прогон: {name}")
        document = seed.document(project, "Документ")
        uids = [seed.version(document, classified=("R", "AR")) for _ in range(versions)]
        for spec in runs:
            run_id = _run(session, project, uids[spec.version - 1], spec.state, age=spec.age, run_id=spec.run_id)
            for kind in spec.findings:
                _finding(session, project, uids[spec.version - 1], run_id, kind)
        seeded[name] = (project, uids)
    session.commit()

    wrong: list[str] = []
    for name, runs, _, wanted in cases:
        project, uids = seeded[name]
        current = uids[-1]
        record = model.audits(session, version_uids=[current])[current]
        (version_number, state), = wanted.items()
        assert uids[version_number - 1] == current, name
        if record.active_run_state != state:
            wrong.append(f"{name}: expected {state!r}, read {record.active_run_state!r}")
        assert (record.active_run_id is None) == (record.active_run_state is None), name
        # The four words are what the result run alone makes them -- the same call as the counters'.
        from auditmanager.dashboard.audit_state import audit_state

        assert (record.state, record.partial) == (
            audit_state(record.result_state, record.finding_count > 0, record.undecided_finding_count > 0).state,
            record.result_state == "partial",
        ), name
        # Both reads agree on the state of the document: the counters' statement does not read the active run.
        counted = tally(model.groups(session, project_uid=project))
        assert getattr(counted, record.state) == 1 and counted.document_count == 1, name
    assert not wrong, "\n".join(wrong)
    assert {case[3][max(case[3])] for case in cases} == {None, "queued", "running", "validating"}, "not vacuous"


def test_a_run_of_an_ar_v3_group_in_flight_is_not_an_active_run(session: Session) -> None:
    """The sealed v3 pair is the one condition shared with the result run (``STANDARD_RUN_SQL``): a v3 member in flight
    is a run of its version and listed with the others, but the document's card does not name it, as it never names a
    v3 result."""
    from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID

    seed = Seeder(session)
    project = seed.project("v3 в работе")
    document = seed.document(project, "Документ")
    version = seed.version(document, classified=("R", "AR"))
    standard = _run(session, project, version, "queued", age=100)
    v3 = str(RunId.new())
    session.execute(
        text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, "
            "provider_mode, frozen_input_digest, created_at) VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, "
            "now() - make_interval(secs => 5))"
        ),
        {"r": v3, "p": project, "v": version, "ap": str(AR_V3_BETA_PROFILE_ID), "pb": str(AR_V3_BETA_BUNDLE_ID),
         "s": _digest(f"v3-{v3}")},
    )
    for step in ("queued", "running"):
        session.execute(text("UPDATE audit_run SET state = :s WHERE run_id = :r"), {"s": step, "r": v3})
    session.commit()
    record = model.audits(session, version_uids=[version])[version]
    assert (record.active_run_id, record.active_run_state) == (standard, "queued"), (
        "the newer v3 run is not the active run; the older standard one is"
    )
    session.execute(text("UPDATE audit_run SET state = 'cancelled', terminal_at = now() WHERE run_id = :r"), {"r": standard})
    session.commit()
    record = model.audits(session, version_uids=[version])[version]
    assert (record.active_run_id, record.active_run_state) == (None, None), "a v3 run alone names nothing"
