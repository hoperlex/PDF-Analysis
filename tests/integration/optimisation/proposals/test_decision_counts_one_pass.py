"""`D-574`: the decision counts of a pass, taken in one pass over the decisions, equal what replaying every history says.

``getOptimisationPass`` and ``listOptimisationPasses`` return each pass with its ``decision_counts``. The first statement looked the
latest decision of every proposal of every returned pass up with one index probe each: on a stand, 200 passes of ~530 proposals cost
0.7 s. The statement now reads the latest decisions of the chosen passes' proposals once and takes the pending ones as the pass's
``proposal_count`` minus the decided ones. This suite is the proof the answer did not move: passes whose proposals carry every
shape of history the table can hold (none, one verdict, withdrawn, withdrawn and decided again, a change of mind, a lone
withdrawal the command would refuse but the table permits), several passes to a version and a pass without proposals, read three ways --

* by an oracle that replays each history in Python (the latest decision decides; ``revoke`` and no decision are ``pending``);
* by the statement the module used to run, kept here as the reference (a ``LATERAL`` "latest decision" per proposal), raw ``jsonb``
  against raw ``jsonb``;
* through the three readers that use the statement (``get_pass``, ``find_pass``, ``list_passes``), which fill the unheld states with zero.

Rows are written by plain SQL with every trigger on (``tests/integration/optimisation/pass_seeding.py``); the database is a fresh
clone of the migrated template.
"""

from __future__ import annotations

import importlib
import random

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from auditmanager.optimisation.proposals.repository import ProposalRepository
from tests.integration.optimisation.pass_seeding import HISTORIES, Scaffold, expected_counts

module = importlib.import_module("auditmanager.optimisation.proposals.repository")
repository = ProposalRepository()

#: The count of one pass as the module read it before `D-574` (``_COUNTS``): the latest decision of every proposal by one index probe.
_PER_PROPOSAL_REFERENCE = text(
    """
    SELECT s.optimisation_pass_id,
           (SELECT jsonb_object_agg(k.verdict, k.n) FROM (
               SELECT COALESCE(NULLIF(cur.verdict, 'revoke'), 'pending') AS verdict, count(*) AS n
               FROM optimisation_proposal q
               LEFT JOIN LATERAL (SELECT d.verdict FROM optimisation_proposal_decision d
                 WHERE d.optimisation_proposal_id = q.optimisation_proposal_id
                 ORDER BY d.seq DESC LIMIT 1) cur ON TRUE
               WHERE q.optimisation_pass_id = s.optimisation_pass_id
               GROUP BY 1) k) AS decision_counts
    FROM optimisation_pass s
    WHERE s.optimisation_pass_id IN :ids
    """
).bindparams(bindparam("ids", expanding=True))

ZEROES = {"pending": 0, "accept": 0, "reject": 0, "revise": 0}


class Passes:
    """Passes of every shape in two projects, and what the oracle says each must count."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.scaffold = Scaffold(session)
        self.project = self.scaffold.seed.project("Проект с проходами")
        self.other_project = self.scaffold.seed.project("Другой проект")
        self.expected: dict[str, dict[str, int]] = {}  # pass -> the counts the oracle holds
        self.proposals: dict[str, int] = {}  # pass -> its proposal_count
        self.keys: dict[str, dict[str, str]] = {}  # pass -> the values find_pass names it by
        self.documents: dict[str, str] = {}  # pass -> its document
        self.projects: dict[str, str] = {}  # pass -> its project
        self.started: dict[str, str] = {}
        self.every_shape_pass = ""
        self._clock = 0

    def add(self, project: str, title: str, passes: tuple[tuple[tuple[str, ...], ...], ...]) -> list[str]:
        """One document with one version and a pass per entry of ``passes`` (oldest first), each a tuple of proposal histories."""
        scaffold = self.scaffold
        document = scaffold.seed.document(project, title)
        version = scaffold.seed.version(document, classified=("R", "AR"))
        run = scaffold.run(project, version)
        ids = []
        for index, histories in enumerate(passes, start=1):
            self._clock += 1
            started = f"2026-11-{self._clock // 24 + 1:02d}T{self._clock % 24:02d}:00:00+00"
            generator = f"gen-{index}"
            pass_id = scaffold.pass_(project, document, version, run, histories, started=started, generator=generator)
            self.expected[pass_id] = expected_counts(histories)
            self.proposals[pass_id] = len(histories)
            self.documents[pass_id] = document
            self.projects[pass_id] = project
            self.started[pass_id] = started
            self.keys[pass_id] = {
                "version_uid": version,
                "run_id": run,
                "price_list_id": scaffold.price_list_of(project)[0],
                "vendor_list_id": scaffold.vendor_list,
                "extraction_algorithm": "ext-1",
                "match_algorithm": "match-1",
                "generator_version": generator,
            }
            ids.append(pass_id)
        return ids


@pytest.fixture
def passes(session: Session) -> Passes:
    built = Passes(session)
    rng = random.Random(574)
    every_shape = tuple(history for history, _ in HISTORIES)
    built.every_shape_pass = built.add(built.project, "Все формы историй", (every_shape,))[0]
    built.add(built.project, "Ничего не решено", (((), (), ()),))
    built.add(built.project, "Всё решено", ((("accept",), ("reject",), ("accept", "revoke", "revise")),))
    built.add(built.project, "Всё снято", ((("accept", "revoke"), ("revoke",)),))
    built.add(built.project, "Пустой проход", ((),))
    built.add(
        built.project,
        "Несколько проходов",
        (((), (), (), ()), (("accept",), ("accept",)), (("reject",), (), ("revise", "revoke"))),
    )
    for index in range(8):  # random mixes, a fixed seed
        mixes = tuple(
            tuple(rng.choice(HISTORIES)[0] for _ in range(rng.randint(1, 40))) for _ in range(rng.randint(1, 3))
        )
        built.add(built.project, f"Случайный набор {index}", mixes)
    built.add(built.other_project, "Чужой проект", ((("accept",), ()), (("revoke",),)))
    session.commit()
    return built


def _filled(counts: dict[str, int]) -> dict[str, int]:
    return {**ZEROES, **counts}


def test_the_raw_counts_equal_the_replayed_histories_and_the_statement_they_replaced(session: Session, passes: Passes) -> None:
    ids = list(passes.expected)
    reference = {str(row[0]): row[1] for row in session.execute(_PER_PROPOSAL_REFERENCE, {"ids": ids})}
    assert set(reference) == set(ids)
    wrong = []
    for pass_id, counts in passes.expected.items():
        row = session.execute(module._SELECT_PASS, {"id": pass_id}).first()
        assert row is not None
        read = row[18]
        held = counts or None  # a pass without proposals has no key at all: NULL, as the old statement answered
        if read != held:
            wrong.append(f"{pass_id}: replayed {held}, read {read}")
        if reference[pass_id] != read:
            wrong.append(f"{pass_id}: the old statement said {reference[pass_id]}, read {read}")
    assert not wrong, "\n".join(wrong)
    # the set is not vacuous: every state is held somewhere, and withdrawn proposals are somewhere counted pending
    assert {state for counts in passes.expected.values() for state in counts} == set(ZEROES)
    assert any(not counts for counts in passes.expected.values()), "a pass without proposals is covered"


def test_the_readers_fill_the_states_nobody_holds_with_zero(session: Session, passes: Passes) -> None:
    for pass_id, counts in passes.expected.items():
        record = repository.get_pass(session, pass_id)
        assert record is not None
        assert dict(record.decision_counts) == _filled(counts), pass_id
        assert record.proposal_count == passes.proposals[pass_id]
        assert sum(record.decision_counts.values()) == record.proposal_count, "every proposal is in exactly one count"
        found = repository.find_pass(session, **passes.keys[pass_id])
        assert found is not None and found.optimisation_pass_id == pass_id
        assert dict(found.decision_counts) == _filled(counts)
    assert repository.get_pass(session, "opp_" + "0" * 26) is None


def test_the_list_is_cut_before_the_counts_and_keeps_its_order(session: Session, passes: Passes) -> None:
    in_project = sorted(
        (pass_id for pass_id, project in passes.projects.items() if project == passes.project),
        key=lambda pass_id: (passes.started[pass_id], pass_id),
        reverse=True,
    )
    assert len(in_project) > 10
    for limit in (1, 3, 7, 1000):
        listed = repository.list_passes(session, project_uid=passes.project, document_uid=None, limit=limit)
        assert [record.optimisation_pass_id for record in listed] == in_project[:limit], limit
        for record in listed:
            assert dict(record.decision_counts) == _filled(passes.expected[record.optimisation_pass_id])
    several = next(document for document in passes.documents.values() if list(passes.documents.values()).count(document) == 3)
    of_document = repository.list_passes(session, project_uid=passes.project, document_uid=several, limit=10)
    assert len(of_document) == 3
    assert {record.document_uid for record in of_document} == {several}
    assert [dict(record.decision_counts) for record in of_document] == [
        _filled(passes.expected[record.optimisation_pass_id]) for record in of_document
    ]
    elsewhere = repository.list_passes(session, project_uid=passes.other_project, document_uid=None, limit=100)
    assert {record.optimisation_pass_id for record in elsewhere} == {
        pass_id for pass_id, project in passes.projects.items() if project == passes.other_project
    }


def test_the_comparison_can_fail(session: Session, passes: Passes, monkeypatch: pytest.MonkeyPatch) -> None:
    """A guard needs a way to fail: the shipped statement with its one rule bent -- a withdrawal counted as a decision in force --
    answers differently from the replayed histories, so the comparison above is not satisfied by any statement that merely runs."""
    shapes = passes.every_shape_pass  # three of its proposals end in a withdrawal and one was never decided
    honest = repository.get_pass(session, shapes)
    assert honest is not None and dict(honest.decision_counts) == _filled(passes.expected[shapes])
    assert honest.decision_counts["pending"] == 4

    original = module._SELECT_PASS.text
    assert "verdict <> 'revoke'" in original
    bent = original.replace("verdict <> 'revoke'", "verdict IS NOT NULL")  # a withdrawal is "decided"
    monkeypatch.setattr(module, "_SELECT_PASS", text(bent))
    wrong = repository.get_pass(session, shapes)
    assert wrong is not None
    assert wrong.decision_counts["pending"] == 1  # only the never-decided proposal: the three withdrawn ones are miscounted
    assert dict(wrong.decision_counts) != dict(honest.decision_counts)
