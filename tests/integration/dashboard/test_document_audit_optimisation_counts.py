"""`D-463`: the optimisation counts of a document's audit equal what replaying every proposal's decision history says.

``DocumentAuditReadModel.audits`` reads, for each listed version, the proposals of its latest optimisation pass and how many of
them have no decision in force (none, or a withdrawn one). The first statement looked up the latest decision of every proposal of
the pass, one index probe each; measured on a stand (200 documents x ~530 proposals) that was ~0.8 s of a 1.3 s page. The statement
now aggregates the decisions of the pass's proposals once. This suite is the proof the answer did not move: passes whose
proposals carry every shape of history the table can hold (none, one verdict, withdrawn, withdrawn and decided again, a change of
mind, a lone withdrawal that the command would refuse but the table permits), read two ways --

* by an oracle that replays each history in Python (the latest decision decides; ``revoke`` and no decision are undecided), and
* by the statement the module used to run, kept here as the reference (a LATERAL "latest decision" per proposal).

Rows are written by plain SQL with every trigger on; a price list and a vendor list are the scaffolding the pass's scope trigger
asks for. The database is a fresh clone of the migrated template.
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, bindparam, text
from sqlalchemy.orm import Session

from auditmanager.dashboard import DocumentAuditReadModel
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.optimisation.pass_seeding import HISTORIES, Scaffold, expected_undecided

model = DocumentAuditReadModel()
module = importlib.import_module("auditmanager.dashboard.audit_state")

#: The statement this module ran before `D-463`: the latest decision of every proposal by one index probe each.
_PER_PROPOSAL_REFERENCE = text(
    """
    WITH latest_pass AS (
        SELECT DISTINCT ON (p.version_uid) p.version_uid, p.optimisation_pass_id, p.proposal_count
        FROM optimisation_pass p
        WHERE p.version_uid IN :version_uids
        ORDER BY p.version_uid, p.started_at DESC, p.optimisation_pass_id DESC
    )
    SELECT lp.version_uid, lp.proposal_count,
           (SELECT count(*)
              FROM optimisation_proposal q
              LEFT JOIN LATERAL (
                  SELECT d.verdict FROM optimisation_proposal_decision d
                  WHERE d.optimisation_proposal_id = q.optimisation_proposal_id
                  ORDER BY d.seq DESC LIMIT 1
              ) cur ON TRUE
             WHERE q.optimisation_pass_id = lp.optimisation_pass_id
               AND (cur.verdict IS NULL OR cur.verdict = 'revoke'))
    FROM latest_pass lp
    """
).bindparams(bindparam("version_uids", expanding=True))


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def test_every_history_shape_is_what_the_table_can_hold_and_is_decided_or_not_as_ruled() -> None:
    """The oracle's own table: a guard that the set is not vacuous (both answers, withdrawn and re-decided shapes)."""
    assert {answer for _, answer in HISTORIES} == {True, False}
    for history, undecided in HISTORIES:
        assert expected_undecided((history,)) == int(undecided), history
    assert any("revoke" in h and h[-1] != "revoke" for h, _ in HISTORIES), "a withdrawn-then-decided history is covered"


def test_the_counts_of_the_latest_pass_equal_the_replayed_histories_and_the_old_statement(session: Session) -> None:
    scaffold = Scaffold(session)
    seed = scaffold.seed
    project = seed.project("Проект с оптимизацией")
    rng = random.Random(463)

    versions: dict[str, tuple[str, ...]] = {}  # version -> expected histories of its latest pass
    expected: dict[str, tuple[int, int] | None] = {}

    def add_version(title: str, *, latest: tuple[tuple[str, ...], ...] | None, older: tuple[tuple[str, ...], ...] | None = None) -> str:
        document = seed.document(project, title)
        version = seed.version(document, classified=("R", "AR"))
        run = scaffold.run(project, version)
        if older is not None:
            scaffold.pass_(project, document, version, run, older, started="2026-11-01T10:00:00+00", generator="gen-1")
        if latest is not None:
            scaffold.pass_(project, document, version, run, latest, started="2026-11-02T10:00:00+00", generator="gen-2")
            expected[version] = (len(latest), expected_undecided(latest))
        else:
            expected[version] = None
        return version

    every_shape = tuple(history for history, _ in HISTORIES)
    add_version("Все формы историй", latest=every_shape)
    add_version("Ничего не решено", latest=((), (), ()))
    add_version("Всё решено", latest=(("accept",), ("reject",), ("accept", "revoke", "revise")))
    add_version("Всё снято", latest=(("accept", "revoke"), ("revoke",)))
    add_version("Пустой проход", latest=())
    add_version("Прохода нет", latest=None)
    # an older pass that disagrees with the latest one: only the latest counts
    add_version("Старый проход иной", latest=(("accept",), ("accept",)), older=((), (), (), ()))
    for index in range(8):  # random mixes, a fixed seed
        mix = tuple(rng.choice(HISTORIES)[0] for _ in range(rng.randint(1, 40)))
        older = tuple(rng.choice(HISTORIES)[0] for _ in range(rng.randint(1, 10))) if index % 2 else None
        add_version(f"Случайный набор {index}", latest=mix, older=older)
    session.commit()

    names = list(expected)
    audits = model.audits(session, version_uids=names)
    assert set(audits) == set(names)
    wrong = []
    for version, pair in expected.items():
        record = audits[version]
        got = (record.optimisation_proposal_count, record.optimisation_undecided_count)
        if pair is None:
            if got != (None, None):
                wrong.append(f"{version}: no pass, read {got}")
        elif got != pair:
            wrong.append(f"{version}: expected {pair} (replayed), read {got}")
    assert not wrong, "\n".join(wrong)

    # and the statement it replaced says the same, version by version
    reference = {str(row[0]): (int(row[1]), int(row[2])) for row in session.execute(_PER_PROPOSAL_REFERENCE, {"version_uids": names})}
    assert reference == {version: pair for version, pair in expected.items() if pair is not None}
    for version, pair in reference.items():
        record = audits[version]
        assert (record.optimisation_proposal_count, record.optimisation_undecided_count) == pair


def test_the_counts_are_a_fact_beside_the_audit_state(session: Session) -> None:
    """`R-150u`: a pass moves none of the four words (a version with a pass and no run of findings is still ``clean`` or ``not_run``)."""
    scaffold = Scaffold(session)
    project = scaffold.seed.project("Проект")
    document = scaffold.seed.document(project, "АР")
    version = scaffold.seed.version(document, classified=("R", "AR"))
    run = scaffold.run(project, version)
    scaffold.pass_(project, document, version, run, ((), ("accept",)), started="2026-11-02T10:00:00+00", generator="gen-2")
    session.commit()
    record = model.audits(session, version_uids=[version])[version]
    assert (record.optimisation_proposal_count, record.optimisation_undecided_count) == (2, 1)
    assert (record.state, record.partial) == ("not_run", False)  # the run was never walked to a result


def test_the_comparison_can_fail(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """A guard needs a way to fail: the shipped statement with its one rule bent -- a withdrawal counted as a decision in force --
    answers differently from the replayed histories, so the comparison above is not satisfied by any statement that merely runs."""
    scaffold = Scaffold(session)
    project = scaffold.seed.project("Проект")
    document = scaffold.seed.document(project, "АР")
    version = scaffold.seed.version(document, classified=("R", "AR"))
    run = scaffold.run(project, version)
    histories = ((), ("accept",), ("accept", "revoke"), ("accept", "revoke", "accept"), ("revoke",))
    scaffold.pass_(project, document, version, run, histories, started="2026-11-02T10:00:00+00", generator="gen-2")
    session.commit()

    honest = model.audits(session, version_uids=[version])[version]
    assert (honest.optimisation_proposal_count, honest.optimisation_undecided_count) == (5, expected_undecided(histories)) == (5, 3)

    original = module._DOCUMENT_AUDITS.text  # the source text, with its `:version_uids`; str() would show the expanded placeholder
    assert "cur.verdict <> 'revoke'" in original
    bent = original.replace("cur.verdict <> 'revoke'", "cur.verdict IS NOT NULL")  # any decision, a withdrawal included, is "decided"
    monkeypatch.setattr(module, "_DOCUMENT_AUDITS", text(bent).bindparams(bindparam("version_uids", expanding=True)))
    wrong = model.audits(session, version_uids=[version])[version]
    assert wrong.optimisation_undecided_count == 1  # only the never-decided proposal: the two withdrawn ones are miscounted
    assert wrong.optimisation_undecided_count != honest.optimisation_undecided_count
