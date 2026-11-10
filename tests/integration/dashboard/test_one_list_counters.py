"""`F8-COUNT-XLSX`: the counters of a ``one_list`` run, on real PostgreSQL rows (plan-v5 section 4 item 6, section 3.6).

The counters are the tallies of ``audit_state``'s one statement over the findings the version's result run published. A candidate finding of a
``one_list`` run is such a finding (one ``finding``, N observations of ``grounding_kind = portal_block``, written by the real publisher, see
``one_list_seed``), so the run's marker needs no branch in the statement: a ``text_only`` run counts as it always did and a ``one_list`` run counts
its candidates too, in the same words. What these tests pin, each with its control:

* a run with no marker, or with ``text_only``, counts by its text findings -- clean, awaiting a decision, checked -- as before;
* a ``one_list`` run counts a block finding: it is a finding (``findings``), it is undecided until the expert decides it (``awaiting_decision``),
  and a document whose only findings are candidates is not ``clean``;
* a group of three candidates is **one** finding, not three;
* the result run decides which marker applies: a newer ``one_list`` run replaces an older ``text_only`` one and the other way round;
* the marker alone moves nothing: the same text findings count the same under either mode;
* the three outputs (the tally, the per-document read and the tile of ``getDashboardSummary``) agree.

The database is a fresh clone of the migrated template, so every number is absolute.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.dashboard import (
    AuditCountsRecord,
    DocumentAuditReadModel,
    awaiting_decision_findings,
    tally,
)
from auditmanager.dashboard.repository import DashboardRepository
from tests.integration.dashboard.one_list_seed import (
    BLK_A,
    BLK_B,
    block_finding,
    insert_run,
    mode_of,
    text_finding,
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


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


@dataclass(frozen=True)
class Doc:
    project: str
    version: str


@pytest.fixture
def seed(session: Session) -> Seeder:
    """One seeder per test: it confirms sections with one expert account, created on first use."""
    return Seeder(session)


def _doc(seed: Seeder, name: str) -> Doc:
    project = seed.project(name)
    version = seed.version(seed.document(project, "Документ"), classified=("R", "AR"))
    return Doc(project, version)


def _counts(session: Session, doc: Doc) -> AuditCountsRecord:
    return tally(model.groups(session, project_uid=doc.project))


def _one(state: str, *, partial: bool = False) -> AuditCountsRecord:
    """The counters of a project of one document that is in ``state``."""
    return AuditCountsRecord(
        document_count=1,
        not_run=int(state == "not_run"),
        clean=int(state == "clean"),
        awaiting_decision=int(state == "awaiting_decision"),
        checked=int(state == "checked"),
        partial=int(partial),
    )


def _audit(session: Session, doc: Doc):  # type: ignore[no-untyped-def]
    return model.audits(session, version_uids=[doc.version])[doc.version]


# --- a text_only run counts as it always did --------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", [None, "text_only"])
def test_a_text_only_run_counts_by_its_text_findings_as_before(session: Session, seed: Seeder, mode: str | None) -> None:
    """``mode=None`` writes no marker: the run is ``text_only`` by the column's default, and so are all runs older than the marker."""
    expected = {
        "no finding": ((), "clean", 0, 0),
        "one undecided among decided": (("accepted", "rejected", "pending"), "awaiting_decision", 3, 1),
        "every finding decided": (("accepted", "rejected"), "checked", 2, 0),
    }
    for name, (verdicts, state, findings, undecided) in expected.items():
        doc = _doc(seed, name)
        run = insert_run(session, doc.project, doc.version, mode=mode)
        for verdict in verdicts:
            text_finding(session, doc.project, doc.version, run, verdict)
        session.commit()
        assert mode_of(session, run) == "text_only", name
        assert _counts(session, doc) == _one(state), name
        audit = _audit(session, doc)
        assert (audit.state, audit.finding_count, audit.undecided_finding_count) == (state, findings, undecided), name
        assert awaiting_decision_findings(model.groups(session, project_uid=doc.project)) == undecided, name


# --- a one_list run counts its candidate findings --------------------------------------------------------------------------


def test_a_one_list_block_finding_is_counted_and_awaits_a_decision(session: Session, seed: Seeder) -> None:
    doc = _doc(seed, "один список")
    run = insert_run(session, doc.project, doc.version, mode="one_list")
    text_finding(session, doc.project, doc.version, run, "accepted")
    candidate = block_finding(session, doc.project, doc.version, run, "pending")
    session.commit()

    # the seed is the publisher's: a block-grounded observation with its block evidence, under a run marked one_list
    assert mode_of(session, run) == "one_list"
    assert session.execute(
        text("SELECT grounding_kind FROM finding_observation WHERE finding_uid = :f"), {"f": candidate.finding_uid}
    ).scalars().all() == ["portal_block"]
    assert session.execute(
        text("SELECT count(*) FROM finding_block_evidence b JOIN finding_observation o USING (finding_observation_id) WHERE o.finding_uid = :f"),
        {"f": candidate.finding_uid},
    ).scalar_one() == 1

    assert _counts(session, doc) == _one("awaiting_decision")
    audit = _audit(session, doc)
    assert (audit.state, audit.finding_count, audit.undecided_finding_count) == ("awaiting_decision", 2, 1)
    assert awaiting_decision_findings(model.groups(session, project_uid=doc.project)) == 1


def test_the_control_a_decided_block_finding_leaves_the_document_checked(session: Session, seed: Seeder) -> None:
    """The same document with the candidate decided: if the statement left candidates out, the two documents would read alike."""
    doc = _doc(seed, "один список, всё решено")
    run = insert_run(session, doc.project, doc.version, mode="one_list")
    text_finding(session, doc.project, doc.version, run, "accepted")
    block_finding(session, doc.project, doc.version, run, "rejected")
    session.commit()
    assert _counts(session, doc) == _one("checked")
    assert _audit(session, doc).finding_count == 2


def test_a_document_whose_only_findings_are_candidates_is_not_clean(session: Session, seed: Seeder) -> None:
    """In a ``text_only`` run such a document would be ``clean``: its candidates were never findings. In a ``one_list`` run they are."""
    only_candidates = _doc(seed, "только кандидаты")
    run = insert_run(session, only_candidates.project, only_candidates.version, mode="one_list")
    block_finding(session, only_candidates.project, only_candidates.version, run, "pending")
    nothing = _doc(seed, "ничего")
    insert_run(session, nothing.project, nothing.version, mode="one_list")
    session.commit()
    assert _counts(session, only_candidates) == _one("awaiting_decision")
    assert _counts(session, nothing) == _one("clean")


def test_a_group_of_three_candidates_is_one_finding(session: Session, seed: Seeder) -> None:
    doc = _doc(seed, "группа")
    run = insert_run(session, doc.project, doc.version, mode="one_list")
    candidate = block_finding(session, doc.project, doc.version, run, "pending", members=((BLK_A,), (BLK_A, BLK_B), (BLK_B,)))
    session.commit()
    assert len(candidate.observation_ids) == 3
    assert session.execute(
        text("SELECT count(*) FROM finding_observation WHERE run_id = :r AND finding_uid IS NOT NULL"), {"r": run}
    ).scalar_one() == 3
    audit = _audit(session, doc)
    assert (audit.state, audit.finding_count, audit.undecided_finding_count) == ("awaiting_decision", 1, 1)
    groups = model.groups(session, project_uid=doc.project)
    assert sum(group.findings for group in groups) == 1 and awaiting_decision_findings(groups) == 1


# --- the result run decides which marker applies ---------------------------------------------------------------------------


def test_a_newer_one_list_run_replaces_an_older_text_only_result(session: Session, seed: Seeder) -> None:
    doc = _doc(seed, "сначала текст, потом один список")
    old = insert_run(session, doc.project, doc.version, mode="text_only", age=100)
    for _ in range(2):
        text_finding(session, doc.project, doc.version, old, "accepted")
    assert _counts(session, doc) == _one("checked")
    new = insert_run(session, doc.project, doc.version, mode="one_list", age=10)
    block_finding(session, doc.project, doc.version, new, "pending")
    session.commit()
    assert _counts(session, doc) == _one("awaiting_decision")
    audit = _audit(session, doc)
    assert (audit.result_run_id, audit.finding_count, audit.undecided_finding_count) == (new, 1, 1)


def test_a_newer_text_only_run_replaces_an_older_one_list_result(session: Session, seed: Seeder) -> None:
    doc = _doc(seed, "сначала один список, потом текст")
    old = insert_run(session, doc.project, doc.version, mode="one_list", age=100)
    block_finding(session, doc.project, doc.version, old, "pending")
    assert _counts(session, doc) == _one("awaiting_decision")
    new = insert_run(session, doc.project, doc.version, mode="text_only", age=10)
    session.commit()
    assert _counts(session, doc) == _one("clean")
    assert _audit(session, doc).result_run_id == new


def test_the_marker_alone_moves_nothing(session: Session, seed: Seeder) -> None:
    """The same text findings, once under ``text_only`` and once under ``one_list``: the same state, findings and undecided."""
    reads = {}
    for mode in ("text_only", "one_list"):
        doc = _doc(seed, f"те же замечания: {mode}")
        run = insert_run(session, doc.project, doc.version, mode=mode)
        for verdict in ("accepted", "pending", "rejected"):
            text_finding(session, doc.project, doc.version, run, verdict)
        session.commit()
        audit = _audit(session, doc)
        reads[mode] = (_counts(session, doc), audit.state, audit.finding_count, audit.undecided_finding_count)
    assert reads["text_only"] == reads["one_list"] == (_one("awaiting_decision"), "awaiting_decision", 3, 1)


# --- the three outputs agree ------------------------------------------------------------------------------------------------


def test_the_tile_the_section_panel_and_the_document_read_agree_on_a_one_list_run(session: Session, seed: Seeder) -> None:
    doc = _doc(seed, "три вывода")
    run = insert_run(session, doc.project, doc.version, mode="one_list")
    text_finding(session, doc.project, doc.version, run, "pending")
    block_finding(session, doc.project, doc.version, run, "pending", group_id="xgrp_1")
    block_finding(session, doc.project, doc.version, run, "accepted", members=((BLK_B,),), group_id="xgrp_2")
    session.commit()

    summary = DashboardRepository().summary(session, project_uid=doc.project)
    section = next(item for item in summary.section_breakdown if item.section == "AR")
    audit = _audit(session, doc)
    assert (audit.state, audit.finding_count, audit.undecided_finding_count) == ("awaiting_decision", 3, 2)
    assert section.audit_counts == _counts(session, doc) == _one("awaiting_decision")
    assert section.finding_count == audit.finding_count == 3
    assert summary.awaiting_decision_findings == audit.undecided_finding_count == 2
